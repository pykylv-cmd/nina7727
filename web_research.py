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
import re
import secrets
import socket
import threading
import time
from urllib import error, parse, request, robotparser

import persistence_backend


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
USER_AGENT = "NinaOS-PublicResearch/1.0 (+controlled user-requested fetch)"
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


def _now():
    return datetime.now(timezone.utc).isoformat()


def _clean_number(value):
    digits = re.sub(r"[^0-9]", "", str(value or ""))
    return int(digits) if digits else None


def build_search_plan(user_text, previous_intent=None):
    text = re.sub(r"\s+", " ", str(user_text or "")).strip()
    folded = text.casefold()
    previous = dict(previous_intent or {})
    filters = dict(previous.get("filters") or {})
    is_followup = bool(previous) and any(x in folded for x in ("rādi tikai", "radi tikai", "izmet", "salīdzini", "salidzini", "kurš", "kurs"))
    vehicle_signal = any(x in folded for x in ("ss.lv", "ss.com", "auto", "bmw", "audi", "volvo", "mercedes", "toyota", "volkswagen"))
    search_signal = any(x in folded for x in ("atrodi", "meklē", "mekle", "search", "find")) or is_followup
    if not ((vehicle_signal or is_followup) and search_signal):
        return None
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
        search_type="VEHICLE_SEARCH", query=text,
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


def validate_public_url(url, resolver=socket.getaddrinfo):
    parsed = parse.urlsplit(str(url or ""))
    if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
        raise WebResearchError("public_url_invalid")
    if not _host_allowed(parsed.hostname):
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
                      enforce_robots=True):
    current = validate_public_url(url, resolver=resolver)
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
                current = validate_public_url(parse.urljoin(current, location), resolver=resolver)
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


def _unknown(value):
    return value if value not in (None, "") else "unknown"


def parse_search_results(page, intent):
    if not page or parse.urlsplit(page.get("url") or "").hostname not in DOMAIN_POLICY:
        raise WebResearchError("unsupported_domain")
    html = str(page.get("html") or "")
    rows = re.findall(r"<tr\b[^>]*>(.*?)</tr>", html, re.I | re.S)
    results = []
    for row in rows:
        link = re.search(r"<a\b[^>]*href=[\"']([^\"']*/msg/[^\"']+)[\"'][^>]*>(.*?)</a>", row, re.I | re.S)
        if not link:
            continue
        source_url = parse.urljoin(page["url"], unescape(link.group(1)))
        if not _host_allowed(parse.urlsplit(source_url).hostname):
            continue
        text = _plain(row)
        title = _redact_contacts(_plain(link.group(2)) or text[:160])
        year_match = re.search(r"\b(19\d{2}|20\d{2})\b", text)
        price_matches = re.findall(r"(\d[\d\s.]*)\s*(?:€|EUR)(?!\w)", text, re.I)
        mileage_match = re.search(r"(\d[\d\s.]*)\s*(?:tūkst\.?\s*)?km\b", text, re.I)
        engine_match = re.search(r"\b(\d[.,]\d)\s*(?:l|d|i)?\b", text, re.I)
        fuel = next((value for token, value in (("dīzel", "diesel"), ("dizel", "diesel"), ("benz", "petrol"), ("elektr", "electric"), ("hybrid", "hybrid")) if token in text.casefold()), "unknown")
        transmission = "automatic" if any(x in text.casefold() for x in ("automāt", "automat", "automatic")) else ("manual" if "manuāl" in text.casefold() else "unknown")
        price = _clean_number(price_matches[-1]) if price_matches else None
        mileage = _clean_number(mileage_match.group(1)) if mileage_match else None
        result_id = "result_" + hashlib.sha256(source_url.split("?", 1)[0].encode()).hexdigest()[:20]
        item = {
            "result_id": result_id, "source": parse.urlsplit(source_url).hostname,
            "source_url": source_url, "page_title": page.get("title") or "",
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
        if filters.get(filter_key) is not None and item.get(item_key) != "unknown" and not predicate(filters[filter_key], item[item_key]):
            return False
    for key in ("fuel", "transmission", "engine", "body_type", "location"):
        if filters.get(key) and item.get(key) != "unknown" and item[key] != filters[key]:
            return False
    return True


def normalize_results(results, intent):
    unique = {}
    for raw in results or ():
        item = dict(raw)
        url_key = str(item.get("source_url") or "").split("?", 1)[0].rstrip("/")
        fallback = "|".join(str(item.get(k) or "") for k in ("title", "year", "price", "mileage"))
        key = url_key or hashlib.sha256(fallback.casefold().encode()).hexdigest()
        current = unique.get(key)
        if current is None or len(item.get("missing_fields") or ()) < len(current.get("missing_fields") or ()):
            unique[key] = item
    filtered = [item for item in unique.values() if _matches(item, intent.filters)]
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


def build_source_url(intent):
    if intent.search_type != "VEHICLE_SEARCH":
        raise WebResearchError("search_type_not_supported")
    make = re.sub(r"[^a-z0-9-]", "", str(intent.filters.get("make") or "").lower())
    model = re.sub(r"[^a-z0-9-]", "", str(intent.filters.get("model") or "").lower())
    if not make or not model:
        raise WebResearchError("search_information_missing")
    return f"https://www.ss.lv/lv/transport/cars/{make}/{model}/"


def search_public_web(intent, fetcher=fetch_public_page):
    source_url = build_source_url(intent)
    try:
        page = fetcher(source_url)
        results = normalize_results(parse_search_results(page, intent), intent)
        return {"ok": True, "intent": asdict(intent), "results": results,
                "comparison": compare_results(results), "source_url": source_url,
                "source_access": "read", "fetched_at": page.get("fetched_at") or _now()}
    except WebResearchError as exc:
        return {"ok": False, "intent": asdict(intent), "results": [],
                "comparison": compare_results([]), "source_url": source_url,
                "source_access": "limited", "error": str(exc), "fetched_at": _now()}


def verify_result(result):
    return bool(result and result.get("source_url") and _host_allowed(parse.urlsplit(result["source_url"]).hostname))


def summarize_sources(payload):
    results = payload.get("results") or []
    if not payload.get("ok"):
        return f"Avota automātiska nolasīšana nav pieejama ({payload.get('error')}). Atver publisko meklēšanu: {payload.get('source_url')}"
    if not results:
        return f"Publiskajā lapā neatradu filtriem atbilstošus rezultātus. Avots: {payload.get('source_url')}"
    lines = [f"Atradu {len(results)} publiskus piedāvājumus. Trūkstošos laukus atzīmēju kā unknown."]
    for index, item in enumerate(results[:5], 1):
        lines.append(f"{index}. {item['title']} — {item['year']} — {item['price']} {item['currency']} — {item['mileage']} km — {item['source_url']}")
    lines.append("Ieteikums nav tehniskā stāvokļa garantija. Pārbaudi VIN, servisa/CSDD un avāriju vēsturi, nobraukumu, apskati, īpašniekus un neatkarīgu diagnostiku.")
    return "\n".join(lines)[:4000]


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
    conn = persistence_backend.connect(); cur = conn.cursor()
    q = "INSERT INTO nina_web_research_sessions (session_id,workspace_id,contact_id,conversation_id,intent_json,results_json,comparison_json,source_url,source_access,error_code,created_at,updated_at) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)"
    cur.execute(persistence_backend.sql(q),(session_id,workspace_id,contact_id,conversation_id,json.dumps(payload.get("intent") or {},ensure_ascii=False),json.dumps(payload.get("results") or [],ensure_ascii=False),json.dumps(payload.get("comparison") or {},ensure_ascii=False),payload.get("source_url") or "",payload.get("source_access") or "",payload.get("error") or "",now,now)); conn.commit(); cur.close(); conn.close()
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
