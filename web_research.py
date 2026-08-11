"""Controlled public Web Research for ONE NINA.

External pages are untrusted evidence. This module never executes page scripts,
contacts sellers, bypasses access controls, or performs background crawling.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from html import unescape
from html.parser import HTMLParser
import hashlib
import ipaddress
import json
import os
import re
import secrets
import socket
import threading
import time
from urllib import error, parse, request, robotparser

import persistence_backend
from research_evidence import evidence_record_from_verified_result


SEARCH_TYPES = {
    "PRODUCT_SEARCH", "VEHICLE_SEARCH", "REAL_ESTATE_SEARCH", "JOB_SEARCH",
    "SERVICE_SEARCH", "COMPANY_RESEARCH", "GENERAL_WEB_RESEARCH",
    "SOURCE_PAGE_ANALYSIS",
}
DOMAIN_POLICY = {
    "ss.lv": {"adapter": "ss_vehicle", "public": True},
    "www.ss.lv": {"adapter": "ss_vehicle", "public": True},
    "ss.com": {"adapter": "ss_vehicle", "public": True},
    "www.ss.com": {"adapter": "ss_vehicle", "public": True},
}
MAX_RESULTS_DEFAULT = 15
MAX_RESULTS_HARD = 20
MAX_RESPONSE_BYTES = 1_000_000
FETCH_TIMEOUT_SECONDS = 8
MAX_REDIRECTS = 3
MAX_CRAWL_PAGES = 10
MAX_CRAWL_DEPTH = 2
MAX_LISTING_URL_VERIFICATIONS = 5
MIN_GENERIC_PROVIDER_CANDIDATES = 10
RESULT_VERIFIED = "VERIFIED_RESULT"
SEARCH_PAGE_VERIFIED = "VERIFIED_SEARCH_PAGE"
RESULT_IRRELEVANT = "IRRELEVANT"
RESULT_UNAVAILABLE = "UNAVAILABLE"
RESULT_BLOCKED = "BLOCKED"
USER_AGENT = "NinaOS-PublicResearch/1.0 (+controlled user-requested fetch)"
DOMAIN_ALIASES = {
    "alibaba": "alibaba.com",
    "reklama": "reklama.lv",
    "ss.lv": "ss.lv",
    "ss.com": "ss.com",
}
CONTACT_BULK_PATTERN = re.compile(r"(?:\+?\d[\d\s().-]{7,}\d|[\w.+-]+@[\w.-]+\.[A-Za-z]{2,})")
_RATE_LOCK = threading.Lock()
_LAST_FETCH = {}
_ROBOTS_CACHE = {}


class WebResearchError(ValueError):
    pass


@dataclass(frozen=True)
class SearchIntent:
    search_type: str
    query: str
    target_domains: tuple[str, ...] = ()
    category: str = ""
    filters: dict = field(default_factory=dict)
    required_fields: tuple[str, ...] = ()
    preferred_fields: tuple[str, ...] = ()
    sort: str = "best_match"
    max_results: int = MAX_RESULTS_DEFAULT
    freshness: str = ""
    location: str = ""
    currency: str = "EUR"
    language: str = "lv"
    user_goal: str = "compare_public_results"
    missing_information: tuple[str, ...] = ()
    confidence: float = 0.0


@dataclass(frozen=True)
class PageContent:
    canonical_url: str
    final_url: str
    domain: str
    page_title: str = "unknown"
    meta_description: str = "unknown"
    headings: tuple[str, ...] = ()
    main_text: str = "unknown"
    links: tuple[dict, ...] = ()
    product_names: tuple[str, ...] = ()
    prices: tuple[dict, ...] = ()
    currency: str = "unknown"
    contacts: tuple[dict, ...] = ()
    addresses: tuple[str, ...] = ()
    dates: tuple[str, ...] = ()
    tables: tuple[tuple[tuple[str, ...], ...], ...] = ()
    structured_data: tuple[dict, ...] = ()
    json_ld: tuple[dict, ...] = ()
    fetched_at: str = ""
    content_hash: str = ""
    warnings: tuple[str, ...] = ()
    extraction_status: str = "verified"


PUBLIC_URL_PATTERN = re.compile(r"https?://[^\s<>\"']+", re.I)


def extract_public_urls(text):
    """Extract literal user-provided URLs; never infer or construct a domain."""
    urls = []
    for match in PUBLIC_URL_PATTERN.findall(str(text or "")):
        candidate = match.rstrip(".,;:!?)]}")
        if candidate not in urls:
            urls.append(candidate)
    return urls[:2]


def _now():
    return datetime.now(timezone.utc).isoformat()


def _clean_number(value):
    digits = re.sub(r"[^0-9]", "", str(value or ""))
    return int(digits) if digits else None


def build_search_plan(user_text, previous_intent=None):
    text = re.sub(r"\s+", " ", str(user_text or "")).strip()
    # A human smoke-test marker is transport metadata, not a public-search
    # concept. Keep the original message in conversation history, but do not
    # require external pages to contain this terminal marker.
    search_text = re.sub(r"\s+TESTS?\s+JAUNS\s*$", "", text, flags=re.I).strip()
    folded = search_text.casefold()
    previous = dict(previous_intent or {})
    filters = dict(previous.get("filters") or {})
    is_followup = bool(previous) and any(x in folded for x in ("rādi tikai", "radi tikai", "izmet", "salīdzini", "salidzini", "kurš", "kurs"))
    domain_match = re.search(r"(?<![\w.-])(?:https?://)?(?:www\.)?([a-z0-9](?:[a-z0-9-]{0,62})(?:\.[a-z0-9](?:[a-z0-9-]{0,62}))+)(?![\w.-])", folded)
    explicit_domain = domain_match.group(1) if domain_match else ""
    if not explicit_domain:
        explicit_domain = next(
            (domain for alias, domain in DOMAIN_ALIASES.items() if re.search(r"(?<![\w.-])" + re.escape(alias) + r"(?![\w.-])", folded)),
            "",
        )
    vehicle_signal = any(x in folded for x in ("ss.lv", "ss.com", "auto", "bmw", "audi", "volvo", "mercedes", "toyota", "volkswagen"))
    search_signal = any(x in folded for x in ("atrodi", "meklē", "mekle", "search", "find")) or is_followup
    if not search_signal:
        return None
    if (explicit_domain and explicit_domain not in {"ss.lv", "ss.com"}) or not (vehicle_signal or is_followup):
        target_domains = (explicit_domain,) if explicit_domain else ()
        return SearchIntent(
            search_type="PRODUCT_SEARCH" if any(x in folded for x in ("lētas", "letas", "cena", "price", "buy", "pirkt")) else "GENERAL_WEB_RESEARCH",
            query=search_text, target_domains=target_domains, category="public_web",
            required_fields=("source_url", "source_domain", "page_title", "fetched_at"),
            preferred_fields=("extracted_snippet",), max_results=5,
            language="lv", confidence=.9,
        )
    make_model = re.search(r"\b(BMW|Audi|Volvo|Mercedes(?:-Benz)?|Toyota|Volkswagen|VW)\s+([A-Za-z0-9-]{1,16})\b", text, re.I)
    if make_model:
        filters["make"] = make_model.group(1).upper().replace("MERCEDES-BENZ", "MERCEDES")
        filters["model"] = make_model.group(2).upper()
    year_from = re.search(r"(?:no\s+|sākot no\s+|sakot no\s+)(19\d{2}|20\d{2})(?:\.?\s*gada)?", folded)
    year_plus = re.search(r"\b(19\d{2}|20\d{2})\s*\+", folded)
    year_to = re.search(r"(?:līdz|lidz)\s+(19\d{2}|20\d{2})(?:\.?\s*gadam)?", folded)
    if year_from or year_plus: filters["year_min"] = int((year_from or year_plus).group(1))
    if year_to: filters["year_max"] = int(year_to.group(1))
    price_max = re.search(r"(?:līdz|lidz)\s+([\d\s.]+)\s*(?:eur|€)", folded)
    price_min = re.search(r"(?:no)\s+([\d\s.]+)\s*(?:eur|€)", folded)
    if price_max: filters["price_max"] = _clean_number(price_max.group(1))
    if price_min: filters["price_min"] = _clean_number(price_min.group(1))
    mileage = re.search(r"nobrauk\w*[^\d]{0,20}(?:līdz|lidz)\s+([\d\s.]+)\s*km", folded)
    if mileage:
        filters["mileage_max"] = _clean_number(mileage.group(1))
    if any(x in folded for x in ("dīzel", "dizel", "diesel")): filters["fuel"] = "diesel"
    elif any(x in folded for x in ("benzīn", "benzin", "petrol")): filters["fuel"] = "petrol"
    elif "electric" in folded or "elektr" in folded: filters["fuel"] = "electric"
    if any(x in folded for x in ("automāt", "automat", "automatic")): filters["transmission"] = "automatic"
    elif any(x in folded for x in ("manuāl", "manual")): filters["transmission"] = "manual"
    engine = re.search(r"\b(\d[,.]\d)\s*(?:l|litri?)\b", folded)
    if engine: filters["engine"] = engine.group(1).replace(",", ".")
    body_type = next((value for token, value in (("suv", "SUV"), ("universāl", "wagon"), ("sedan", "sedan"), ("kupej", "coupe")) if token in folded), "")
    if body_type: filters["body_type"] = body_type
    location = next((value for token, value in (("rīg", "Riga"), ("jelgav", "Jelgava"), ("liepāj", "Liepaja"), ("daugavpil", "Daugavpils")) if token in folded), str(previous.get("location") or ""))
    freshness = "today" if any(x in folded for x in ("šodien", "sodien", "today")) else str(previous.get("freshness") or "")
    missing = tuple(x for x in ("make", "model") if not filters.get(x))
    confidence = .94 if not missing else .62
    return SearchIntent(
        search_type="VEHICLE_SEARCH", query=search_text,
        target_domains=("www.ss.lv",), category="vehicles",
        filters=filters,
        required_fields=("title", "source_url", "price", "year"),
        preferred_fields=("mileage", "fuel", "transmission", "location"),
        sort="best_match", max_results=MAX_RESULTS_DEFAULT,
        freshness=freshness, location=location, currency="EUR", language="lv", missing_information=missing,
        confidence=confidence,
    )


def clarification_for(intent):
    if not intent or not intent.missing_information:
        return ""
    if "make" in intent.missing_information or "model" in intent.missing_information:
        return "Kādu auto marku un modeli man meklēt?"
    return "Kuru būtisko kritēriju man precizēt?"


def _host_allowed(host):
    host = str(host or "").lower().rstrip(".")
    return host in DOMAIN_POLICY


def _matches_allowed_domain(host, allowed_domains=()):
    host = str(host or "").lower().rstrip(".")
    allowed = tuple(str(value or "").lower().rstrip(".") for value in allowed_domains if value)
    return not allowed or any(host == domain or host.endswith("." + domain) for domain in allowed)


def validate_public_url(url, resolver=socket.getaddrinfo, allowed_domains=()):
    parsed = parse.urlsplit(str(url or ""))
    if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
        raise WebResearchError("public_url_invalid")
    if not re.fullmatch(r"[a-z0-9.-]+", parsed.hostname, re.I) or not _matches_allowed_domain(parsed.hostname, allowed_domains):
        raise WebResearchError("unsupported_domain")
    if parsed.port not in (None, 443):
        raise WebResearchError("public_url_port_blocked")
    try:
        addresses = {row[4][0] for row in resolver(parsed.hostname, 443, type=socket.SOCK_STREAM)}
    except OSError as exc:
        raise WebResearchError("public_host_unresolved") from exc
    if not addresses:
        raise WebResearchError("public_host_unresolved")
    for address in addresses:
        ip = ipaddress.ip_address(address)
        if not ip.is_global or ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved:
            raise WebResearchError("ssrf_address_blocked")
    return parsed.geturl()


class _NoRedirect(request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def _robots_allowed(url, opener, timeout):
    parsed = parse.urlsplit(url)
    root = f"{parsed.scheme}://{parsed.netloc}"
    cached = _ROBOTS_CACHE.get(root)
    if cached and time.monotonic() - cached[0] < 1800:
        return cached[1].can_fetch(USER_AGENT, url)
    robots_url = root + "/robots.txt"
    parser = robotparser.RobotFileParser()
    try:
        response = opener.open(request.Request(robots_url, headers={"User-Agent": USER_AGENT}), timeout=timeout)
        raw = response.read(256_000).decode("utf-8", "replace")
        parser.parse(raw.splitlines())
    except Exception:
        parser.parse(["User-agent: *", "Disallow: /"])
    _ROBOTS_CACHE[root] = (time.monotonic(), parser)
    return parser.can_fetch(USER_AGENT, url)


def fetch_public_page(url, *, timeout=FETCH_TIMEOUT_SECONDS, max_bytes=MAX_RESPONSE_BYTES,
                      max_redirects=MAX_REDIRECTS, opener=None, resolver=socket.getaddrinfo,
                      enforce_robots=True, allowed_domains=()):
    current = validate_public_url(url, resolver=resolver, allowed_domains=allowed_domains)
    opener = opener or request.build_opener(_NoRedirect())
    if enforce_robots and not _robots_allowed(current, opener, timeout):
        raise WebResearchError("robots_disallowed")
    for redirect_count in range(max_redirects + 1):
        host = parse.urlsplit(current).hostname
        with _RATE_LOCK:
            elapsed = time.monotonic() - _LAST_FETCH.get(host, 0)
            if elapsed < .5:
                raise WebResearchError("rate_limit_active")
            _LAST_FETCH[host] = time.monotonic()
        try:
            response = opener.open(request.Request(current, headers={"User-Agent": USER_AGENT, "Accept": "text/html"}), timeout=timeout)
        except error.HTTPError as exc:
            if exc.code in (301, 302, 303, 307, 308):
                if redirect_count >= max_redirects:
                    raise WebResearchError("redirect_limit_exceeded")
                location = exc.headers.get("Location") or ""
                current = validate_public_url(parse.urljoin(current, location), resolver=resolver, allowed_domains=allowed_domains)
                continue
            raise WebResearchError(f"source_http_{exc.code}") from exc
        content_type = (response.headers.get("Content-Type") or "").split(";", 1)[0].lower()
        if content_type not in {"text/html", "application/xhtml+xml"}:
            raise WebResearchError("source_mime_blocked")
        raw = response.read(max_bytes + 1)
        if len(raw) > max_bytes:
            raise WebResearchError("source_response_too_large")
        charset = response.headers.get_content_charset() or "utf-8"
        text = raw.decode(charset, "replace")
        folded = text.casefold()
        if "captcha" in folded or "type=\"password\"" in folded or "sign in to continue" in folded:
            raise WebResearchError("source_access_challenge")
        return {"url": current, "title": _page_title(text), "html": text, "fetched_at": _now(), "content_type": content_type}
    raise WebResearchError("redirect_limit_exceeded")


def _page_title(html):
    match = re.search(r"<title[^>]*>(.*?)</title>", html or "", re.I | re.S)
    return re.sub(r"\s+", " ", unescape(re.sub(r"<[^>]+>", "", match.group(1)))).strip()[:240] if match else ""


def _plain(fragment):
    return re.sub(r"\s+", " ", unescape(re.sub(r"<[^>]+>", " ", fragment or ""))).strip()


def _redact_contacts(value):
    return CONTACT_BULK_PATTERN.sub("[contact omitted]", str(value or ""))


class _PageContentParser(HTMLParser):
    """Extract evidence from HTML without executing or interpreting scripts."""

    SKIP_TAGS = {"script", "style", "noscript", "svg", "canvas", "template"}
    CHROME_TAGS = {"nav", "footer", "header"}

    def __init__(self, base_url):
        super().__init__(convert_charrefs=True)
        self.base_url = base_url
        self.title_parts = []
        self.meta_description = ""
        self.headings = []
        self.text_parts = []
        self.links = []
        self.addresses = []
        self.dates = []
        self.tables = []
        self.json_ld_raw = []
        self._stack = []
        self._anchor = None
        self._heading = None
        self._table = None
        self._row = None
        self._cell = None
        self._json_ld = None

    def _hidden(self):
        return any(item[0] in self.SKIP_TAGS | self.CHROME_TAGS or item[1] for item in self._stack)

    def handle_starttag(self, tag, attrs):
        tag = tag.casefold(); values = {str(k).casefold(): str(v or "") for k, v in attrs}
        marker = (values.get("class", "") + " " + values.get("id", "")).casefold()
        chrome = any(x in marker for x in ("cookie", "consent", "breadcrumb", "pagination", "advert", "sidebar", "menu"))
        self._stack.append((tag, chrome))
        if tag == "meta" and values.get("name", "").casefold() == "description":
            self.meta_description = re.sub(r"\s+", " ", values.get("content", "")).strip()[:1000]
        if tag == "a": self._anchor = {"href": values.get("href", ""), "text": []}
        if tag in {"h1", "h2", "h3", "h4", "h5", "h6"}: self._heading = []
        if tag == "table": self._table = []
        if tag == "tr" and self._table is not None: self._row = []
        if tag in {"td", "th"} and self._row is not None: self._cell = []
        if tag == "time" and values.get("datetime"): self.dates.append(values["datetime"][:80])
        if tag == "script" and values.get("type", "").casefold() == "application/ld+json": self._json_ld = []

    def handle_data(self, data):
        text = re.sub(r"\s+", " ", str(data or "")).strip()
        if not text: return
        tag = self._stack[-1][0] if self._stack else ""
        if self._json_ld is not None and tag == "script": self._json_ld.append(data); return
        if tag == "title": self.title_parts.append(text)
        if self._anchor is not None: self._anchor["text"].append(text)
        if self._heading is not None: self._heading.append(text)
        if self._cell is not None: self._cell.append(text)
        if tag == "address": self.addresses.append(text)
        if not self._hidden() and tag not in {"title", "head"}: self.text_parts.append(text)

    def handle_endtag(self, tag):
        tag = tag.casefold()
        if tag == "a" and self._anchor is not None:
            href = self._anchor["href"].strip(); absolute = parse.urljoin(self.base_url, href)
            parsed = parse.urlsplit(absolute)
            if parsed.scheme in {"http", "https"} and parsed.hostname and not parsed.username and not parsed.password:
                canonical = parse.urlunsplit((parsed.scheme.lower(), parsed.netloc.lower(), parsed.path or "/", parsed.query, ""))
                self.links.append({"url": canonical, "raw_href": href, "text": " ".join(self._anchor["text"])[:240] or "unknown"})
            self._anchor = None
        if tag in {"h1", "h2", "h3", "h4", "h5", "h6"} and self._heading is not None:
            value = " ".join(self._heading).strip()
            if value: self.headings.append(value[:500])
            self._heading = None
        if tag in {"td", "th"} and self._cell is not None:
            self._row.append(" ".join(self._cell)[:1000]); self._cell = None
        if tag == "tr" and self._row is not None:
            if any(self._row): self._table.append(tuple(self._row))
            self._row = None
        if tag == "table" and self._table is not None:
            if self._table: self.tables.append(tuple(self._table[:100]))
            self._table = None
        if tag == "script" and self._json_ld is not None:
            self.json_ld_raw.append("".join(self._json_ld)); self._json_ld = None
        for index in range(len(self._stack) - 1, -1, -1):
            if self._stack[index][0] == tag:
                del self._stack[index:]; break


def _json_objects(value):
    if isinstance(value, dict):
        yield value
        for child in value.values(): yield from _json_objects(child)
    elif isinstance(value, list):
        for child in value: yield from _json_objects(child)


def extract_page_content(page, canonical_url=None):
    """Build server-authoritative Page Content from fetched HTML evidence only."""
    final_url = str((page or {}).get("url") or canonical_url or "")
    canonical = str(canonical_url or final_url)
    parser_instance = _PageContentParser(final_url)
    html = str((page or {}).get("html") or "")
    parser_instance.feed(html)
    json_ld = []
    for raw in parser_instance.json_ld_raw:
        try:
            value = json.loads(raw)
        except (TypeError, ValueError):
            continue
        json_ld.extend(item for item in _json_objects(value) if isinstance(item, dict))
    products, prices, addresses, dates = [], [], list(parser_instance.addresses), list(parser_instance.dates)
    for item in json_ld:
        item_type = item.get("@type")
        types = item_type if isinstance(item_type, list) else [item_type]
        if "Product" in types and item.get("name"): products.append(str(item["name"])[:500])
        if item.get("address"):
            address = item["address"]
            addresses.append(json.dumps(address, ensure_ascii=False, sort_keys=True) if isinstance(address, dict) else str(address))
        if item.get("datePublished"): dates.append(str(item["datePublished"])[:80])
        if "Offer" in types or item.get("price") is not None:
            offer_price = item.get("price") or (item.get("offers") or {}).get("price") if isinstance(item.get("offers"), dict) else item.get("price")
            currency = item.get("priceCurrency") or ((item.get("offers") or {}).get("priceCurrency") if isinstance(item.get("offers"), dict) else None)
            if offer_price is not None: prices.append({"value": str(offer_price)[:80], "currency": str(currency or "unknown")[:12], "source": "json_ld"})
    main_text = re.sub(r"\s+", " ", " ".join(parser_instance.text_parts)).strip()[:100_000]
    if not prices:
        for match in re.finditer(r"(?<!\w)(\d{1,3}(?:[ .]\d{3})*(?:[,.]\d{1,2})?)\s*(EUR|USD|GBP|€|\$|£)(?!\w)", main_text, re.I):
            prices.append({"value": match.group(1), "currency": {"€":"EUR", "$":"USD", "£":"GBP"}.get(match.group(2), match.group(2).upper()), "source":"visible_html"})
            if len(prices) >= 20: break
    emails = list(dict.fromkeys(re.findall(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}", main_text)))[:5]
    phones = list(dict.fromkeys(re.findall(r"(?<!\w)\+?\d[\d ()-]{7,}\d", main_text)))[:5]
    unique_prices = {}
    for price in prices:
        unique_prices.setdefault((price["value"], price["currency"], price["source"]), price)
    prices = list(unique_prices.values())
    contacts = ([{"type":"email", "value": value} for value in emails] + [{"type":"phone", "value": value.strip()} for value in phones])[:10]
    warnings = []
    folded = html.casefold()
    status = "verified"
    if len(main_text) < 80 and any(x in folded for x in ("__next_data__", "id=\"root\"", "id='root'", "enable javascript")):
        status = "javascript_required"; warnings.append("javascript_rendering_required")
    if any(x in main_text.casefold() for x in ("ignore previous instructions", "system prompt", "assistant instructions")):
        warnings.append("untrusted_instruction_text_ignored")
    if len(emails) + len(phones) >= 10: warnings.append("contacts_truncated")
    title = " ".join(parser_instance.title_parts).strip()[:500] or str((page or {}).get("title") or "").strip()[:500] or "unknown"
    evidence = {"url": final_url, "title": title, "main_text": main_text, "json_ld": json_ld, "links": parser_instance.links}
    content_hash = hashlib.sha256(json.dumps(evidence, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    return PageContent(
        canonical_url=canonical, final_url=final_url, domain=parse.urlsplit(final_url).hostname or "unknown",
        page_title=title, meta_description=parser_instance.meta_description or "unknown",
        headings=tuple(dict.fromkeys(parser_instance.headings)), main_text=main_text or "unknown",
        links=tuple(parser_instance.links[:200]), product_names=tuple(dict.fromkeys(products)),
        prices=tuple(prices), currency=(prices[0]["currency"] if prices else "unknown"), contacts=tuple(contacts),
        addresses=tuple(dict.fromkeys(value[:1000] for value in addresses if value)), dates=tuple(dict.fromkeys(dates)),
        tables=tuple(parser_instance.tables[:20]), structured_data=tuple(json_ld), json_ld=tuple(json_ld),
        fetched_at=str((page or {}).get("fetched_at") or _now()), content_hash=content_hash,
        warnings=tuple(warnings), extraction_status=status,
    )


def _page_result(content):
    item = asdict(content)
    item.update({
        "result_id": "page_" + content.content_hash[:20], "title": content.page_title,
        "source_url": content.canonical_url, "source_domain": content.domain,
        "source_url_provenance": "direct_user_url", "source_url_verified": True,
        "result_status": RESULT_VERIFIED,
    })
    item["verified_result_id"] = _verified_result_id(item)
    return item


def read_public_websites(urls, query="", fetcher=fetch_public_page, crawl=False):
    """Read up to two explicit URLs, optionally crawling ten same-domain pages."""
    queue = [(url, 0) for url in list(urls or ())[:2]]; seen = set(); contents = []
    root_hosts = []
    for raw in urls or ():
        host = parse.urlsplit(raw).hostname
        if host: root_hosts.append(host.casefold())
    while queue and len(contents) < MAX_CRAWL_PAGES:
        raw_url, depth = queue.pop(0)
        try:
            validated = validate_public_url(raw_url, allowed_domains=root_hosts)
        except WebResearchError:
            if not contents: raise
            continue
        canonical = validated.split("#", 1)[0]
        if canonical in seen: continue
        seen.add(canonical)
        page = fetcher(validated, allowed_domains=root_hosts) if fetcher is fetch_public_page else fetcher(validated)
        content = extract_page_content(page, canonical)
        contents.append(content)
        if crawl and depth < MAX_CRAWL_DEPTH:
            for link in content.links:
                candidate = link.get("url")
                parsed = parse.urlsplit(candidate or "")
                if parsed.hostname and _matches_allowed_domain(parsed.hostname, root_hosts) and candidate not in seen:
                    queue.append((candidate, depth + 1))
                    if len(queue) + len(contents) >= MAX_CRAWL_PAGES: break
    intent = {"search_type":"SOURCE_PAGE_ANALYSIS", "query":str(query or ""), "target_domains":root_hosts}
    results = [_page_result(content) for content in contents]
    return {"ok":bool(results), "intent":intent, "results":results, "comparison":{},
            "source_url":results[0]["source_url"] if results else "", "source_access":"read",
            "fetched_at":_now(), "error":"" if results else "no_verified_page_content"}


def answer_page_content(payload, question=""):
    pages = verified_results(payload); folded = str(question or "").casefold()
    if not pages: return "Neizdevās iegūt verificētu lapas saturu."
    if len(pages) > 1 and not any(x in folded for x in ("salīdz", "salidz", "compare", "abas", "both")):
        return "Ir vairākas avota lapas. Norādi, kuru no tām analizēt, vai pasaki, ka vēlies salīdzinājumu."
    lines = []
    for page in pages:
        if page.get("extraction_status") == "javascript_required":
            lines.append(f"Lapai nepieciešama JavaScript renderēšana; statisko saturu droši iegūt neizdevās. Avots: {page['source_url']}")
            continue
        facts = []
        if any(x in folded for x in ("cik maks", "cena", "price")): facts.append("cenas: " + (", ".join(f"{p['value']} {p['currency']}" for p in page.get("prices") or []) or "unknown"))
        elif any(x in folded for x in ("kontakt", "tālrun", "talrun", "email", "e-past")): facts.append("kontakti: " + (", ".join(c["value"] for c in page.get("contacts") or []) or "unknown"))
        elif any(x in folded for x in ("kur atrod", "adrese", "address")): facts.append("adrese: " + (", ".join(page.get("addresses") or []) or "unknown"))
        else:
            if page.get("product_names"): facts.append("produkti: " + ", ".join(page["product_names"][:5]))
            facts.append("saturs: " + str(page.get("main_text") or "unknown")[:900])
        lines.append(f"{page.get('page_title') or 'unknown'} — {'; '.join(facts)}. Avots: {page['source_url']}")
    return "\n".join(lines)[:4000]


def _unknown(value):
    return value if value not in (None, "") else "unknown"


def _ss_listing_url(raw_url, base_url):
    """Accept only a real-looking listing href obtained from SS HTML."""
    candidate = parse.urljoin(base_url, unescape(str(raw_url or ""))).split("#", 1)[0]
    parsed = parse.urlsplit(candidate)
    filename = parsed.path.rsplit("/", 1)[-1].casefold()
    if (
        parsed.scheme != "https"
        or not _host_allowed(parsed.hostname)
        or not re.fullmatch(r"/msg/(?:lv|ru|en)/[^?#]+/[a-z0-9_-]+\.html", parsed.path, re.I)
        or re.fullmatch(r"\d{6,}\.html", filename)
        or any(token in filename for token in ("placeholder", "example", "test-listing", "dummy"))
    ):
        return None
    return parse.urlunsplit((parsed.scheme, parsed.netloc, parsed.path, parsed.query, ""))


class _SSListingHrefParser(HTMLParser):
    """Collect literal SS.lv listing hrefs without deriving any URL data."""

    def __init__(self, base_url):
        super().__init__(convert_charrefs=True)
        self.base_url = base_url
        self.row_index = -1
        self.current_row = None
        self.links = []

    def handle_starttag(self, tag, attrs):
        tag = tag.casefold()
        if tag == "tr":
            self.row_index += 1
            self.current_row = self.row_index
            return
        if tag != "a":
            return
        raw_href = next((value for name, value in attrs if name.casefold() == "href"), None)
        canonical_url = _ss_listing_url(raw_href, self.base_url)
        if not canonical_url or parse.urlsplit(canonical_url).hostname not in {"ss.lv", "www.ss.lv"}:
            return
        self.links.append({
            "canonical_url": canonical_url,
            "raw_href": raw_href,
            "parser_source": "ss_search_html_anchor",
            "row_index": self.current_row,
        })

    def handle_endtag(self, tag):
        if tag.casefold() == "tr":
            self.current_row = None


def extract_ss_listing_hrefs(html, base_url):
    """Return unique literal /msg/ anchors found in SS.lv search HTML."""
    parser_instance = _SSListingHrefParser(base_url)
    parser_instance.feed(str(html or ""))
    unique = {}
    for link in parser_instance.links:
        canonical = link["canonical_url"].split("?", 1)[0]
        link["canonical_url"] = canonical
        unique.setdefault(canonical, link)
    return list(unique.values())


def _canonical_result_url(item):
    provenance = item.get("source_url_provenance")
    if provenance == "parsed_html":
        return _ss_listing_url(item.get("source_url"), item.get("source_url"))
    if provenance in {"search_provider", "parsed_search_html", "direct_user_url"}:
        parsed = parse.urlsplit(str(item.get("source_url") or ""))
        if parsed.scheme == "https" and parsed.hostname and not parsed.username and not parsed.password:
            return parse.urlunsplit(("https", parsed.netloc.lower(), parsed.path or "/", parsed.query, ""))
    return None


def _verified_result_id(item):
    """Bind a verified result to its parser-provided URL and structured fields."""
    canonical_url = _canonical_result_url(item)
    if not canonical_url:
        return ""
    fields = {
        key: item.get(key)
        for key in (
            "result_id", "title", "make", "model", "year", "price", "currency",
            "mileage", "fuel", "transmission", "engine", "body_type", "location",
            "published_at", "seller_type", "description_summary",
            "source_domain", "page_title", "fetched_at", "extracted_snippet", "provider",
            "result_status", "content_hash", "extraction_status",
        )
    }
    fields["source_url"] = canonical_url
    identity = json.dumps(fields, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return "verified_" + hashlib.sha256(identity.encode()).hexdigest()[:24]


def verified_results(payload):
    """Return only intact, uniquely URL-bound results from the verified set."""
    unique = {}
    for raw in (payload or {}).get("results") or ():
        item = dict(raw)
        canonical_url = _canonical_result_url(item)
        expected_id = _verified_result_id(item)
        if (
            not canonical_url
            or item.get("source_url_provenance") not in {"parsed_html", "search_provider", "parsed_search_html", "direct_user_url"}
            or item.get("source_url_verified") is not True
            or item.get("verified_result_id") != expected_id
        ):
            continue
        item["source_url"] = canonical_url
        unique.setdefault(canonical_url, item)
    return list(unique.values())


def verified_result_to_evidence(result, *, workspace_id="", contact_id=""):
    """Adapt one intact existing verified result into the canonical evidence contract."""
    verified = verified_results({"results": [result]})
    if not verified:
        raise WebResearchError("verified_result_provenance_required")
    return evidence_record_from_verified_result(
        verified[0], workspace_id=workspace_id, contact_id=contact_id,
    )


def verified_payload_to_evidence(payload, *, workspace_id="", contact_id=""):
    """Adapt only the existing verifier's accepted results; never infer source URLs."""
    return tuple(
        evidence_record_from_verified_result(item, workspace_id=workspace_id, contact_id=contact_id)
        for item in verified_results(payload)
    )


def research_result_to_session_payload(result):
    """Translate verified Research V1 evidence into the existing session shape."""
    rows = []
    for record in result.evidence:
        provenance = str(record.provider_provenance.get("provenance") or "")
        if provenance not in {"parsed_html", "search_provider", "parsed_search_html", "direct_user_url"}:
            continue
        item = {
            "result_id": record.evidence_id,
            "source_url": record.canonical_url,
            "final_url": record.final_url,
            "source_url_provenance": provenance,
            "source_url_verified": True,
            "source_domain": record.domain,
            "page_title": record.title,
            "published_at": record.publication_date,
            "fetched_at": record.fetched_at,
            "content_hash": record.content_hash,
            "extracted_snippet": " ".join(fragment.text for fragment in record.fragments)[:4000],
            "provider": str(record.provider_provenance.get("provider") or ""),
            "provider_result_index": record.provider_provenance.get("provider_result_index"),
            "source_trust_type": record.source_trust_type.value,
            "freshness": record.freshness.value,
        }
        item["verified_result_id"] = _verified_result_id(item)
        rows.append(item)
    return {
        "ok": result.outcome.value == "completed",
        "intent": {
            "search_type": "GENERAL_WEB_RESEARCH",
            "query": result.plan.original_query,
            "target_domains": list(result.plan.preferred_domains),
            "freshness": result.plan.freshness.value,
        },
        "results": rows,
        "comparison": compare_results([]),
        "source_url": "",
        "source_access": "read" if rows else "limited",
        "error": "" if result.outcome.value == "completed" else result.outcome.value,
        "fetched_at": _now(),
    }


def parse_search_results(page, intent):
    if not page or parse.urlsplit(page.get("url") or "").hostname not in DOMAIN_POLICY:
        raise WebResearchError("unsupported_domain")
    html = str(page.get("html") or "")
    rows = re.findall(r"<tr\b[^>]*>(.*?)</tr>", html, re.I | re.S)
    results = []
    for row_index, row in enumerate(rows):
        parsed_links = extract_ss_listing_hrefs(row, page["url"])
        if not parsed_links:
            continue
        parsed_link = parsed_links[0]
        source_url = parsed_link["canonical_url"]
        link = re.search(r"<a\b[^>]*href=[\"']" + re.escape(parsed_link["raw_href"]) + r"[\"'][^>]*>(.*?)</a>", row, re.I | re.S)
        text = _plain(row)
        title = _redact_contacts(_plain(link.group(1)) if link else text[:160])
        year_match = re.search(r"\b(19\d{2}|20\d{2})\b", text)
        price_matches = re.findall(r"(\d[\d\s.]*)\s*(?:€|EUR)(?!\w)", text, re.I)
        mileage_match = re.search(r"(\d[\d\s.]*)\s*(?:tūkst\.?\s*)?km\b", text, re.I)
        engine_match = re.search(r"\b(\d[.,]\d)\s*(?:l|d|i)?\b", text, re.I)
        fuel = next((value for token, value in (("dīzel", "diesel"), ("dizel", "diesel"), ("benz", "petrol"), ("elektr", "electric"), ("hybrid", "hybrid")) if token in text.casefold()), "unknown")
        transmission = "automatic" if any(x in text.casefold() for x in ("automāt", "automat", "automatic")) else ("manual" if "manuāl" in text.casefold() else "unknown")
        price = _clean_number(price_matches[-1]) if price_matches else None
        mileage = _clean_number(mileage_match.group(1)) if mileage_match else None
        identity = source_url.split("?", 1)[0] if source_url else text
        result_id = "result_" + hashlib.sha256(identity.encode()).hexdigest()[:20]
        item = {
            "result_id": result_id, "source": parse.urlsplit(page["url"]).hostname,
            "source_url": source_url, "source_url_provenance": "parsed_html" if source_url else "unavailable",
            "source_url_raw_href": parsed_link["raw_href"],
            "source_url_parser_source": parsed_link["parser_source"],
            "source_url_row_index": row_index,
            "source_url_verified": False, "page_title": page.get("title") or "",
            "title": title[:240], "make": intent.filters.get("make") or "unknown",
            "model": intent.filters.get("model") or "unknown",
            "year": int(year_match.group(1)) if year_match else "unknown",
            "price": price if price is not None else "unknown", "currency": "EUR",
            "mileage": mileage if mileage is not None else "unknown", "fuel": fuel,
            "transmission": transmission,
            "engine": engine_match.group(1).replace(",", ".") if engine_match else "unknown",
            "body_type": "unknown", "location": "unknown", "published_at": "unknown",
            "seller_type": "unknown", "description_summary": _redact_contacts(text)[:500],
            "image_url": "unknown", "warnings": [], "fetched_at": page.get("fetched_at") or _now(),
        }
        item["missing_fields"] = [key for key in ("year", "price", "mileage", "fuel", "transmission", "location", "published_at", "seller_type") if item[key] == "unknown"]
        results.append(item)
    return results


def _matches(item, filters):
    checks = (
        ("year_min", "year", lambda a, b: b >= a), ("year_max", "year", lambda a, b: b <= a),
        ("price_min", "price", lambda a, b: b >= a), ("price_max", "price", lambda a, b: b <= a),
        ("mileage_max", "mileage", lambda a, b: b <= a),
    )
    for filter_key, item_key, predicate in checks:
        if filters.get(filter_key) is not None:
            if item.get(item_key) == "unknown" or not predicate(filters[filter_key], item[item_key]):
                return False
    for key in ("fuel", "transmission", "engine", "body_type", "location"):
        if filters.get(key) and item.get(key) != "unknown" and item[key] != filters[key]:
            return False
    return True


def normalize_results(results, intent, apply_filters=True):
    unique = {}
    for raw in results or ():
        item = dict(raw)
        url_key = str(item.get("source_url") or "").split("?", 1)[0].rstrip("/")
        fallback = "|".join(str(item.get(k) or "") for k in ("title", "year", "price", "mileage"))
        key = url_key or hashlib.sha256(fallback.casefold().encode()).hexdigest()
        current = unique.get(key)
        if current is None or len(item.get("missing_fields") or ()) < len(current.get("missing_fields") or ()):
            unique[key] = item
    filtered = [item for item in unique.values() if not apply_filters or _matches(item, intent.filters)]
    filtered.sort(key=lambda x: (x.get("price") == "unknown", x.get("price") if isinstance(x.get("price"), int) else 10**18, -(x.get("year") if isinstance(x.get("year"), int) else 0), x.get("result_id") or ""))
    return filtered[:min(MAX_RESULTS_HARD, max(1, int(intent.max_results)))]


def compare_results(results, selected_ids=None):
    chosen = [x for x in results if not selected_ids or x.get("result_id") in set(selected_ids)]
    priced = [x for x in chosen if isinstance(x.get("price"), int)]
    years = [x for x in chosen if isinstance(x.get("year"), int)]
    mileages = [x for x in chosen if isinstance(x.get("mileage"), int)]
    value = [x for x in chosen if isinstance(x.get("price"), int) and isinstance(x.get("year"), int) and x["year"] > 0]
    return {
        "count": len(chosen),
        "cheapest_id": min(priced, key=lambda x: (x["price"], x["result_id"]))["result_id"] if priced else "unknown",
        "newest_id": max(years, key=lambda x: (x["year"], x["result_id"]))["result_id"] if years else "unknown",
        "lowest_mileage_id": min(mileages, key=lambda x: (x["mileage"], x["result_id"]))["result_id"] if mileages else "unknown",
        "best_price_year_id": min(value, key=lambda x: (x["price"] / x["year"], x["result_id"]))["result_id"] if value else "unknown",
        "warnings": ["Verify VIN, service history, CSDD data, accident history, mileage, inspection, owners and independent diagnostics."],
    }


def _object_value(value, key, default=None):
    return value.get(key, default) if isinstance(value, dict) else getattr(value, key, default)


def openai_web_search_provider(intent, client=None):
    """Return only URL citations emitted by OpenAI's public web search tool."""
    if client is None:
        api_key = (os.environ.get("OPENAI_API_KEY") or "").strip()
        if not api_key:
            raise WebResearchError("search_provider_not_configured")
        from openai import OpenAI
        client = OpenAI(api_key=api_key)
    tool = {"type": "web_search", "search_context_size": "medium"}
    provider_query = intent.query
    if intent.target_domains:
        provider_query += " " + " ".join("site:" + domain for domain in intent.target_domains)
    response = client.responses.create(
        model="gpt-4.1-mini", tools=[tool], store=False,
        input=(
            "Find up to ten distinct public source pages for this exact query. "
            "Prefer directly accessible, non-paywalled source pages. Cite every source and do not invent examples: "
            + provider_query
        ),
    )
    unique = {}
    for output in _object_value(response, "output", ()) or ():
        for content in _object_value(output, "content", ()) or ():
            for annotation in _object_value(content, "annotations", ()) or ():
                if _object_value(annotation, "type") != "url_citation":
                    continue
                raw_url = str(_object_value(annotation, "url", "") or "").strip()
                parsed = parse.urlsplit(raw_url)
                if parsed.scheme != "https" or not parsed.hostname or not _matches_allowed_domain(parsed.hostname, intent.target_domains):
                    continue
                canonical = parse.urlunsplit(("https", parsed.netloc.lower(), parsed.path or "/", parsed.query, ""))
                unique.setdefault(canonical, {
                    "url": canonical,
                    "provider_title": str(_object_value(annotation, "title", "") or "")[:240],
                    "provider": "openai_web_search",
                })
    candidate_limit = min(MAX_RESULTS_HARD, max(MIN_GENERIC_PROVIDER_CANDIDATES, int(intent.max_results)))
    return list(unique.values())[:candidate_limit]


def configured_search_providers(environ=None):
    """Return only public-search providers already configured in this runtime."""
    environ = os.environ if environ is None else environ
    providers = []
    if str(environ.get("OPENAI_API_KEY") or "").strip():
        providers.append(("openai_web_search", openai_web_search_provider))
    return providers


def provider_search(intent, providers=None):
    """Try configured providers in order and retain only their literal URL results."""
    providers = configured_search_providers() if providers is None else list(providers)
    if not providers:
        raise WebResearchError("search_provider_not_configured")
    failures = []
    for provider_name, provider in providers:
        # Public search can occasionally return an empty citation set for an
        # otherwise identical domain-scoped request. Retry that empty response
        # once; URL/domain verification below remains fully fail-closed.
        for attempt in range(2):
            try:
                candidates = provider(intent) or []
            except Exception as exc:
                failures.append({"provider": provider_name, "error": type(exc).__name__})
                break
            if candidates:
                return candidates, provider_name, failures
    return [], providers[-1][0], failures


def _generic_page_facts(page):
    html = str((page or {}).get("html") or "")
    description = re.search(r"<meta\b[^>]*name=[\"']description[\"'][^>]*content=[\"']([^\"']*)", html, re.I)
    if not description:
        description = re.search(r"<meta\b[^>]*content=[\"']([^\"']*)[\"'][^>]*name=[\"']description[\"']", html, re.I)
    cleaned = re.sub(r"<(?:script|style|noscript)\b[^>]*>.*?</(?:script|style|noscript)>", " ", html, flags=re.I | re.S)
    snippet = _redact_contacts(_plain(description.group(1) if description else cleaned))[:600]
    return {
        "page_title": _redact_contacts((page or {}).get("title") or "unknown")[:240] or "unknown",
        "extracted_snippet": snippet or "unknown",
        "fetched_at": (page or {}).get("fetched_at") or _now(),
    }


class _PublicSearchHrefParser(HTMLParser):
    """Collect literal anchors and their visible text from one fetched page."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.current = None
        self.links = []
        self.index = -1

    def handle_starttag(self, tag, attrs):
        if tag.casefold() != "a":
            return
        self.index += 1
        raw_href = next((value for name, value in attrs if name.casefold() == "href"), None)
        self.current = {"raw_href": raw_href, "text": [], "row_index": self.index}

    def handle_data(self, data):
        if self.current is not None:
            self.current["text"].append(str(data or ""))

    def handle_endtag(self, tag):
        if tag.casefold() == "a" and self.current is not None:
            self.current["anchor_text"] = _plain(" ".join(self.current.pop("text", [])))[:300]
            self.links.append(self.current)
            self.current = None


def extract_verified_search_page_hrefs(html, base_url, intent):
    """Extract unique, query-relevant offer hrefs literally present in raw HTML."""
    parser_instance = _PublicSearchHrefParser()
    parser_instance.feed(str(html or ""))
    unique = {}
    blocked_path_tokens = (
        "/login", "/signin", "/register", "/account", "/help", "/contact",
        "/privacy", "/terms", "/advert", "/reklam", "/category/", "/catalog/",
    )
    term_groups = _query_term_groups(intent)
    for link in parser_instance.links:
        raw_href = str(link.get("raw_href") or "").strip()
        candidate = parse.urljoin(base_url, unescape(raw_href)).split("#", 1)[0]
        parsed = parse.urlsplit(candidate)
        path = parsed.path or "/"
        folded_path = parse.unquote(path).replace("-", " ").replace("_", " ").casefold()
        evidence = (str(link.get("anchor_text") or "") + " " + folded_path).casefold()
        if (
            parsed.scheme != "https" or not parsed.hostname
            or parsed.username or parsed.password
            or not _matches_allowed_domain(parsed.hostname, intent.target_domains)
            or any(token in path.casefold() for token in blocked_path_tokens)
            or not (path.casefold().endswith((".html", ".htm")) or any(token in path.casefold() for token in ("/item/", "/offer/", "/product/")))
            or (term_groups and any(not any(term in evidence for term in group) for group in term_groups))
        ):
            continue
        canonical = parse.urlunsplit(("https", parsed.netloc.lower(), path, parsed.query, ""))
        unique.setdefault(canonical, {
            "canonical_url": canonical,
            "raw_href": raw_href,
            "anchor_text": str(link.get("anchor_text") or "")[:300],
            "parser_source": "verified_search_page_html_anchor",
            "row_index": link.get("row_index"),
        })
    return list(unique.values())


def _clear_page_price(page):
    html = str((page or {}).get("html") or "")
    patterns = (
        r"itemprop=[\"']price[\"'][^>]*content=[\"']([\d\s.,]+)[\"']",
        r"content=[\"']([\d\s.,]+)[\"'][^>]*itemprop=[\"']price[\"']",
    )
    for pattern in patterns:
        match = re.search(pattern, html, re.I)
        if match:
            value = _clean_number(match.group(1))
            if value is not None:
                return value
    return "unknown"


def _expand_verified_search_page(intent, page, fetcher, provider_name, provider_index):
    expanded = []
    candidates = extract_verified_search_page_hrefs(page.get("html"), page.get("url"), intent)
    for candidate in candidates:
        if len(expanded) >= 5:
            break
        try:
            detail = fetcher(candidate["canonical_url"], allowed_domains=intent.target_domains)
        except (WebResearchError, OSError, ValueError):
            continue
        status, _reason = classify_public_page(intent, candidate, detail)
        if status != RESULT_VERIFIED:
            continue
        facts = _generic_page_facts(detail)
        item = {
            "result_id": "result_" + hashlib.sha256(candidate["canonical_url"].encode()).hexdigest()[:20],
            "source_url": candidate["canonical_url"],
            "source_url_provenance": "parsed_search_html",
            "source_url_raw_href": candidate["raw_href"],
            "source_url_parser_source": candidate["parser_source"],
            "source_url_row_index": candidate["row_index"],
            "source_url_verified": True,
            "source_domain": parse.urlsplit(candidate["canonical_url"]).hostname or "",
            "provider": provider_name,
            "provider_result_index": provider_index,
            "result_status": RESULT_VERIFIED,
            "title": facts["page_title"],
            "price": _clear_page_price(detail),
            **facts,
        }
        item["verified_result_id"] = _verified_result_id(item)
        expanded.append(item)
    return expanded, candidates


def _query_term_groups(intent):
    ignored = {
        "atrodi", "mekle", "meklē", "find", "search", "letas", "lētas", "cena",
        "price", "buy", "pirkt", "com", "www", "no", "lidz", "līdz", "gada",
        "latvijā", "latvija", "latvia", "aktuālus", "aktualus", "aktuālu", "aktualu",
        "avotus", "avoti", "avotu", "sources", "source", "par", "about",
        "atsūti", "atsuti", "sūti", "suti", "saites", "saiti", "links", "link", "un", "and",
    }
    domain_parts = {part for domain in intent.target_domains for part in domain.split(".")}
    terms = [
        term for term in re.findall(r"[a-zāčēģīķļņōŗšūž0-9]{2,}", intent.query.casefold())
        if term not in ignored and term not in domain_parts
    ]
    groups = []
    for term in terms:
        equivalents = {term, term[:5]} if len(term) >= 6 else {term}
        if term.startswith("svec"):
            equivalents.update(("candle", "candles"))
        if term.startswith("aromāt") or term.startswith("aromat"):
            equivalents.update(("aromatic", "scented", "fragrance"))
        if term.startswith("urb"):
            equivalents.update(("drill", "drills"))
        if term.startswith("putekļ") or term.startswith("putekl"):
            equivalents.update(("vacuum", "cleaner", "hoover"))
        groups.append(equivalents)
    return groups


def classify_public_page(intent, candidate, page):
    """Classify fetched evidence without deriving claims from provider or LLM prose."""
    html = str((page or {}).get("html") or "")
    title = str((page or {}).get("title") or "")
    url = str((page or {}).get("url") or candidate.get("url") or "")
    folded = _plain(html).casefold()
    title_folded = title.casefold()
    path = parse.urlsplit(url).path.casefold()
    if not html.strip():
        return RESULT_UNAVAILABLE, "empty_page"
    if any(marker in (title_folded + " " + folded[:5000]) for marker in (
        "not found", "page not found", "404 error", "sludinājums nav atrasts",
        "lapa nav atrasta", "does not exist",
    )):
        return RESULT_UNAVAILABLE, "not_found"
    if any(marker in folded[:5000] for marker in ("captcha", "sign in to continue", "type=\"password\"")):
        return RESULT_BLOCKED, "access_challenge"
    term_groups = _query_term_groups(intent)
    search_path = any(token in path for token in ("/search", "/category", "/catalog", "/products", "/wholesale", "/trade/"))
    product_path = any(token in path for token in ("/product-detail", "/product/", "/item/", "/offer/", "/p/"))
    evidence = (
        title_folded + " " + parse.unquote(path).replace("-", "_")
        if intent.search_type == "PRODUCT_SEARCH" or search_path or product_path
        else title_folded + " " + folded[:20000]
    )
    if term_groups and any(not any(term in evidence for term in group) for group in term_groups):
        return RESULT_IRRELEVANT, "query_terms_absent"
    if intent.search_type == "PRODUCT_SEARCH":
        blog_path = any(token in path for token in ("/blog/", "/blogs/", "/article/", "/news/", "/guide"))
        if blog_path:
            return RESULT_IRRELEVANT, "product_query_blog_page"
        if product_path:
            return RESULT_VERIFIED, "product_page"
        if search_path:
            return SEARCH_PAGE_VERIFIED, "search_or_category_page"
        return RESULT_IRRELEVANT, "not_product_or_search_page"
    literal_offers = extract_verified_search_page_hrefs(html, url, intent)
    individual_path = path.endswith((".html", ".htm")) or product_path
    category_markers = any(marker in folded[:20000] for marker in (
        "filtrs", "sludinājumu", "sludinajumu", "listings", "search results",
    ))
    if not individual_path and (literal_offers or (path.endswith("/") and category_markers)):
        return SEARCH_PAGE_VERIFIED, (
            "search_page_with_literal_offers" if literal_offers else "verified_category_page"
        )
    if product_path:
        return RESULT_VERIFIED, "product_page"
    if search_path:
        return SEARCH_PAGE_VERIFIED, "search_or_category_page"
    return RESULT_VERIFIED, "relevant_public_page"


def search_verified_web(intent, search_provider=None, fetcher=fetch_public_page, providers=None):
    if search_provider is not None:
        provider_results, provider_name, provider_failures = search_provider(intent) or [], getattr(search_provider, "__name__", "public_web_search"), []
    else:
        provider_results, provider_name, provider_failures = provider_search(intent, providers=providers)
    verified, search_pages, rejected, seen = [], [], [], set()
    previous_host = ""
    acquisition_limit = min(MAX_RESULTS_HARD, max(MIN_GENERIC_PROVIDER_CANDIDATES, int(intent.max_results)))
    for index, candidate in enumerate(provider_results[:acquisition_limit]):
        raw_url = str(candidate.get("url") or "")
        parsed = parse.urlsplit(raw_url)
        canonical = parse.urlunsplit(("https", parsed.netloc.lower(), parsed.path or "/", parsed.query, "")) if parsed.scheme == "https" and parsed.hostname else ""
        if not canonical or canonical in seen or not _matches_allowed_domain(parsed.hostname, intent.target_domains):
            rejected.append({"source_url": canonical or raw_url, "status": RESULT_IRRELEVANT, "reason": "domain_or_url_rejected"})
            continue
        seen.add(canonical)
        if previous_host == parsed.hostname:
            time.sleep(.51)
        previous_host = parsed.hostname or ""
        try:
            page = fetcher(canonical, allowed_domains=intent.target_domains)
        except (WebResearchError, OSError, ValueError) as exc:
            error_code = str(exc)
            status = RESULT_BLOCKED if error_code in {"robots_disallowed", "source_access_challenge"} else RESULT_UNAVAILABLE
            rejected.append({"source_url": canonical, "source_domain": parsed.hostname or "", "status": status, "reason": error_code})
            continue
        status, reason = classify_public_page(intent, candidate, page)
        if status not in {RESULT_VERIFIED, SEARCH_PAGE_VERIFIED}:
            rejected.append({"source_url": canonical, "source_domain": parsed.hostname or "", "status": status, "reason": reason})
            continue
        facts = _generic_page_facts(page)
        item = {
            "result_id": "result_" + hashlib.sha256(canonical.encode()).hexdigest()[:20],
            "source_url": canonical, "source_url_provenance": "search_provider",
            "source_url_verified": True, "source_domain": parsed.hostname or "",
            "provider": str(candidate.get("provider") or provider_name),
            "provider_result_index": index, "result_status": status, **facts,
        }
        item["verified_result_id"] = _verified_result_id(item)
        if status == RESULT_VERIFIED:
            verified.append(item)
        else:
            search_pages.append(item)
            expanded, _literal_candidates = _expand_verified_search_page(
                intent, page, fetcher, provider_name, index,
            )
            for expanded_item in expanded:
                if expanded_item["source_url"] not in seen:
                    seen.add(expanded_item["source_url"])
                    verified.append(expanded_item)
    return {
        "ok": True, "intent": asdict(intent), "results": verified[:max(1, int(intent.max_results))],
        "comparison": compare_results([]), "source_url": "",
        "source_access": "read" if verified or search_pages else "limited",
        "verified_search_pages": search_pages, "rejected_results": rejected,
        "provider_candidates": len(provider_results), "search_provider": provider_name,
        "provider_failures": provider_failures, "unverified_results": rejected, "fetched_at": _now(),
    }


def build_source_url(intent):
    if intent.search_type != "VEHICLE_SEARCH":
        raise WebResearchError("search_type_not_supported")
    make = re.sub(r"[^a-z0-9-]", "", str(intent.filters.get("make") or "").lower())
    model = re.sub(r"[^a-z0-9-]", "", str(intent.filters.get("model") or "").lower())
    if not make or not model:
        raise WebResearchError("search_information_missing")
    return f"https://www.ss.lv/lv/transport/cars/{make}/{model}/"


def search_public_web(intent, fetcher=fetch_public_page, result_verifier=None, search_provider=None, providers=None):
    if intent.search_type != "VEHICLE_SEARCH":
        return search_verified_web(intent, search_provider=search_provider, fetcher=fetcher, providers=providers)
    source_url = build_source_url(intent)
    try:
        page = fetcher(source_url)
        results = normalize_results(parse_search_results(page, intent), intent, apply_filters=False)
        verifier = result_verifier or verify_result
        accepted = []
        for index, item in enumerate(results):
            # Search rows identify candidates only. Displayed listing details must
            # come from the concrete listing page, never from inferred row data.
            item.update({key: "unknown" for key in (
                "title", "make", "model", "year", "price", "mileage", "fuel",
                "transmission", "engine", "body_type", "location", "published_at",
                "seller_type", "description_summary", "image_url",
            )})
            item["missing_fields"] = [
                "year", "price", "mileage", "fuel", "transmission", "location",
                "published_at", "seller_type",
            ]
            verified = False
            if item.get("source_url") and index < MAX_RESULTS_HARD:
                if result_verifier is None:
                    time.sleep(.51)
                verified = bool(verifier(item))
            item["source_url_verified"] = verified
            if not verified:
                item["source_url"] = None
                item["source_url_provenance"] = "unavailable"
                item.pop("verified_result_id", None)
                item.setdefault("warnings", []).append("Direct listing URL is unavailable or unverified.")
            else:
                item["verified_result_id"] = _verified_result_id(item)
                if _matches(item, intent.filters):
                    accepted.append(item)
        results = accepted
        return {"ok": True, "intent": asdict(intent), "results": results,
                "comparison": compare_results(results), "source_url": source_url,
                "source_access": "read", "fetched_at": page.get("fetched_at") or _now()}
    except WebResearchError as exc:
        return {"ok": False, "intent": asdict(intent), "results": [],
                "comparison": compare_results([]), "source_url": source_url,
                "source_access": "limited", "error": str(exc), "fetched_at": _now()}


def parse_ss_listing_fields(page):
    """Read vehicle fields only from SS.lv's labelled option table and price cell."""
    html = str((page or {}).get("html") or "")
    by_id = {}
    for match in re.finditer(r"<(?:td|span)\b(?=[^>]*\bid=)([^>]*)>(.*?)</(?:td|span)>", html, re.I | re.S):
        attrs = match.group(1) or ""
        body = match.group(2)
        id_match = re.search(r"\bid=[\"']?([a-z0-9_-]+)", attrs, re.I)
        if id_match:
            by_id[id_match.group(1).casefold()] = _plain(body)

    def integer_from(field_id):
        value = by_id.get(field_id, "")
        number = _clean_number(value)
        return number if number is not None else "unknown"

    year_text = by_id.get("tdo_18", "")
    year_match = re.match(r"\s*(19\d{2}|20\d{2})\b", year_text)
    motor = by_id.get("tdo_15", "").casefold()
    gearbox = by_id.get("tdo_35", "").casefold()
    fuel = next((value for token, value in (
        ("dīzel", "diesel"), ("dizel", "diesel"), ("benz", "petrol"),
        ("elektr", "electric"), ("hibr", "hybrid"),
    ) if token in motor), "unknown")
    transmission = "automatic" if "autom" in gearbox else ("manual" if "manu" in gearbox else "unknown")
    fields = {
        "price": integer_from("tdo_8"),
        "year": int(year_match.group(1)) if year_match else "unknown",
        "mileage": integer_from("tdo_16"),
        "fuel": fuel,
        "transmission": transmission,
        "field_sources": {
            "price": "listing_html:#tdo_8",
            "year": "listing_html:#tdo_18",
            "mileage": "listing_html:#tdo_16",
            "fuel": "listing_html:#tdo_15",
            "transmission": "listing_html:#tdo_35",
        },
    }
    return fields


def verify_result(result, fetcher=fetch_public_page):
    if not result or result.get("source_url_provenance") != "parsed_html":
        return False
    url = _ss_listing_url(result.get("source_url"), result.get("source_url"))
    if not url:
        return False
    try:
        page = fetcher(url)
    except (WebResearchError, OSError, ValueError):
        return False
    content = (str(page.get("title") or "") + " " + str(page.get("html") or "")).casefold()
    not_found = ("sludinājums nav atrasts", "sludinajums nav atrasts", "advertisement not found", "page not found")
    if any(marker in content for marker in not_found):
        return False
    result.update(parse_ss_listing_fields(page))
    result.update({"title": _redact_contacts(page.get("title") or "unknown")[:240] or "unknown", "listing_detail_provenance": "listing_html"})
    result["missing_fields"] = [
        key for key in ("year", "price", "mileage", "fuel", "transmission", "location", "published_at", "seller_type")
        if result.get(key) == "unknown"
    ]
    return True


def summarize_sources(payload):
    results = verified_results(payload)
    if not payload.get("ok"):
        return f"Avota automātiska nolasīšana nav pieejama ({payload.get('error')}). Atver publisko meklēšanu: {payload.get('source_url')}"
    if not results:
        if (payload.get("intent") or {}).get("search_type") != "VEHICLE_SEARCH":
            search_pages = verified_results({"results": payload.get("verified_search_pages") or []})
            domain = ((payload.get("intent") or {}).get("target_domains") or ["publiskā interneta"])[0]
            if search_pages:
                page = search_pages[0]
                return f"Atradu verificētu kategorijas lapu, bet individuālus piedāvājumus droši iegūt neizdevās. {page['source_url']}"
            return f"Nespēju iegūt verificētus rezultātus no {domain}. Negribu tev izdomāt saites vai piedāvājumus."
        return f"Neizdevās iegūt verificētus sludinājumus. Meklēšanas lapa: {payload.get('source_url')}"
    if (payload.get("intent") or {}).get("search_type") != "VEHICLE_SEARCH":
        lines = [f"Atradu {len(results)} verificētus publiskus avotus."]
        for index, item in enumerate(results, 1):
            lines.append(f"{index}. {item.get('page_title') or 'unknown'} — {item.get('source_domain') or 'unknown'} — {item.get('extracted_snippet') or 'unknown'} — {item['source_url']}")
        return "\n".join(lines)[:4000]
    lines = [f"Atradu {len(results)} publiskus piedāvājumus. Trūkstošos laukus atzīmēju kā unknown."]
    for index, item in enumerate(results[:5], 1):
        direct_url = item.get("source_url") if item.get("source_url_verified") else None
        link_text = direct_url or "Tiešā saite nav pieejama"
        lines.append(f"{index}. {item['title']} — {item['year']} — {item['price']} {item['currency']} — {item['mileage']} km — {link_text}")
    lines.append("Ieteikums nav tehniskā stāvokļa garantija. Pārbaudi VIN, servisa/CSDD un avāriju vēsturi, nobraukumu, apskati, īpašniekus un neatkarīgu diagnostiku.")
    return "\n".join(lines)[:4000]


def summarize_verified_links(payload):
    results = verified_results(payload)
    if not results and (payload.get("intent") or {}).get("search_type") != "VEHICLE_SEARCH":
        results = verified_results({"results": payload.get("verified_search_pages") or []})
    if not results:
        if (payload.get("intent") or {}).get("search_type") != "VEHICLE_SEARCH":
            domain = ((payload.get("intent") or {}).get("target_domains") or ["publiskā interneta"])[0]
            return f"Nespēju iegūt verificētas saites no {domain}. Negribu tev izdomāt saites."
        return f"Neizdevās iegūt verificētus sludinājumus. Meklēšanas lapa: {payload.get('source_url')}"
    return "\n".join(
        f"{index}. {item.get('page_title') or item.get('title') or 'unknown'} — {item['source_url']}"
        for index, item in enumerate(results, 1)
    )[:4000]


def _ensure_schema():
    if persistence_backend.HOSTED:
        from managed_migrations import assert_required_migrations_complete
        assert_required_migrations_complete()
        return
    conn = persistence_backend.connect(); cur = conn.cursor()
    cur.execute("""CREATE TABLE IF NOT EXISTS nina_web_research_sessions (session_id TEXT PRIMARY KEY,workspace_id TEXT NOT NULL,contact_id TEXT NOT NULL,conversation_id TEXT NOT NULL,intent_json TEXT NOT NULL,results_json TEXT NOT NULL,comparison_json TEXT NOT NULL,source_url TEXT NOT NULL,source_access TEXT NOT NULL,error_code TEXT NOT NULL DEFAULT '',created_at TEXT NOT NULL,updated_at TEXT NOT NULL)""")
    cur.execute("""CREATE TABLE IF NOT EXISTS nina_saved_searches (search_id TEXT PRIMARY KEY,workspace_id TEXT NOT NULL,contact_id TEXT NOT NULL,name TEXT NOT NULL,search_type TEXT NOT NULL,query_json TEXT NOT NULL,target_domains TEXT NOT NULL,status TEXT NOT NULL,created_at TEXT NOT NULL,updated_at TEXT NOT NULL,UNIQUE(workspace_id,contact_id,query_json))""")
    conn.commit(); cur.close(); conn.close()


def save_research_session(workspace_id, contact_id, conversation_id, payload):
    _ensure_schema(); now = _now(); session_id = "search_" + secrets.token_hex(16)
    persisted_results = payload.get("results") or payload.get("verified_search_pages") or []
    conn = persistence_backend.connect(); cur = conn.cursor()
    q = "INSERT INTO nina_web_research_sessions (session_id,workspace_id,contact_id,conversation_id,intent_json,results_json,comparison_json,source_url,source_access,error_code,created_at,updated_at) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)"
    cur.execute(persistence_backend.sql(q),(session_id,workspace_id,contact_id,conversation_id,json.dumps(payload.get("intent") or {},ensure_ascii=False),json.dumps(persisted_results,ensure_ascii=False),json.dumps(payload.get("comparison") or {},ensure_ascii=False),payload.get("source_url") or "",payload.get("source_access") or "",payload.get("error") or "",now,now)); conn.commit(); cur.close(); conn.close()
    return session_id


def latest_research_session(workspace_id, contact_id, conversation_id):
    _ensure_schema(); conn=persistence_backend.connect(); cur=conn.cursor()
    cur.execute(persistence_backend.sql("SELECT session_id,intent_json,results_json,comparison_json,source_url,source_access,error_code,created_at FROM nina_web_research_sessions WHERE workspace_id=%s AND contact_id=%s AND conversation_id=%s ORDER BY created_at DESC,session_id DESC LIMIT 1"),(workspace_id,contact_id,conversation_id)); row=cur.fetchone(); cur.close(); conn.close()
    if not row: return None
    return {"session_id":row[0],"intent":json.loads(row[1]),"results":json.loads(row[2]),"comparison":json.loads(row[3]),"source_url":row[4],"source_access":row[5],"error":row[6],"created_at":str(row[7])}


def get_research_session(workspace_id, contact_id, session_id):
    _ensure_schema(); conn=persistence_backend.connect(); cur=conn.cursor()
    cur.execute(persistence_backend.sql("SELECT session_id,intent_json,results_json,comparison_json,source_url,source_access,error_code,conversation_id,created_at FROM nina_web_research_sessions WHERE workspace_id=%s AND contact_id=%s AND session_id=%s"),(workspace_id,contact_id,session_id)); row=cur.fetchone(); cur.close(); conn.close()
    if not row: raise WebResearchError("research_session_not_found")
    return {"session_id":row[0],"intent":json.loads(row[1]),"results":json.loads(row[2]),"comparison":json.loads(row[3]),"source_url":row[4],"source_access":row[5],"error":row[6],"conversation_id":row[7],"created_at":str(row[8])}


def save_search(workspace_id, contact_id, session_id, name=""):
    session=get_research_session(workspace_id,contact_id,session_id); intent=session["intent"]
    query_json=json.dumps(intent,ensure_ascii=False,sort_keys=True,separators=(",",":")); now=_now()
    existing=list_saved_searches(workspace_id,contact_id)
    for item in existing:
        if item["query_json"] == query_json: return item, False
    record={"search_id":"saved_"+hashlib.sha256((workspace_id+"|"+contact_id+"|"+query_json).encode()).hexdigest()[:24],"workspace_id":workspace_id,"contact_id":contact_id,"name":str(name or intent.get("query") or "Saved search")[:160],"search_type":intent.get("search_type") or "GENERAL_WEB_RESEARCH","query_json":query_json,"target_domains":json.dumps(intent.get("target_domains") or []),"status":"ACTIVE","created_at":now,"updated_at":now}
    conn=persistence_backend.connect(); cur=conn.cursor(); cur.execute(persistence_backend.sql("INSERT INTO nina_saved_searches (search_id,workspace_id,contact_id,name,search_type,query_json,target_domains,status,created_at,updated_at) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)"),tuple(record[k] for k in ("search_id","workspace_id","contact_id","name","search_type","query_json","target_domains","status","created_at","updated_at"))); conn.commit(); cur.close(); conn.close(); return record,True


def list_saved_searches(workspace_id, contact_id):
    _ensure_schema(); conn=persistence_backend.connect(); cur=conn.cursor(); cur.execute(persistence_backend.sql("SELECT search_id,workspace_id,contact_id,name,search_type,query_json,target_domains,status,created_at,updated_at FROM nina_saved_searches WHERE workspace_id=%s AND contact_id=%s ORDER BY created_at,search_id"),(workspace_id,contact_id)); rows=cur.fetchall() or []; cur.close(); conn.close(); keys=("search_id","workspace_id","contact_id","name","search_type","query_json","target_domains","status","created_at","updated_at"); return [dict(zip(keys,row)) for row in rows]


def apply_followup(previous, text):
    intent=build_search_plan(text, previous.get("intent") or {})
    if not intent: raise WebResearchError("research_followup_not_understood")
    results=normalize_results(previous.get("results") or [],intent)
    folded=str(text or "").casefold(); selected=[]
    ordinal_map=(("pirm",0),("first",0),("otr",1),("second",1),("treš",2),("tres",2),("third",2),("ceturt",3),("fourth",3),("piekt",4),("fifth",4))
    for token,index in ordinal_map:
        if token in folded and index < len(results): selected.append(results[index]["result_id"])
    return {"ok":True,"intent":asdict(intent),"results":results,"comparison":compare_results(results,selected or None),"selected_result_ids":selected,"source_url":previous.get("source_url") or "","source_access":previous.get("source_access") or "read","fetched_at":_now()}


def contains_bulk_contacts(text):
    return len(CONTACT_BULK_PATTERN.findall(str(text or ""))) > 3
