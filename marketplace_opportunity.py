"""Canonical, channel-neutral marketplace scouting on existing Work Objects."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import hashlib
import re
from typing import Any

import web_research
from work_objects import get_work_object_by_source_key, save_or_get_work_object, update_work_object


@dataclass(frozen=True)
class SearchJob:
    transaction: str = "sale"
    property_type: str = "apartment"
    max_price: int = 0
    currency: str = "EUR"
    location: str = ""
    source_preference: str = ""
    owner_preference: str = ""


@dataclass(frozen=True)
class ListingRecord:
    canonical_url: str
    price: int
    location: str = ""
    rooms: str = ""
    area: str = ""
    description: str = ""
    transaction_type: str = "sale"
    property_type: str = "apartment"
    observed_at: str = ""
    evidence_reference: str = ""


@dataclass(frozen=True)
class DemandRecord:
    canonical_url: str
    location: str = ""
    max_price: int = 0
    property_type: str = "apartment"
    description: str = ""
    transaction_type: str = "buyer_wanted"
    observed_at: str = ""
    evidence_reference: str = ""


@dataclass(frozen=True)
class OpportunityMatch:
    seller_url: str
    buyer_url: str
    price_compatible: bool | None
    location_compatible: bool | None
    property_type_compatible: bool | None
    unknowns: tuple[str, ...] = ()


_SALE = re.compile(r"\b(?:pārdod|pardod|pārdošan|pardosan|for sale)\b", re.I)
_BUY = re.compile(r"(?:\bpērku\b|\bperku\b|\bvēlos nopirkt\b|\bvelos nopirkt\b|\bmeklēju iegādei\b|\bmekleju iegadei\b|\bpircēj\w*|\bpircej\w*|\bgrib pirkt\b)", re.I)
_RENT = re.compile(r"\b(?:izīrē|izire|īrē|ire|īrei|irei|rent)\b", re.I)


def _key(workspace_id: str, contact_id: str) -> str:
    owner = hashlib.sha256(f"{workspace_id}\0{contact_id}".encode()).hexdigest()[:24]
    return f"marketplace:apartment:{owner}"


def _intent(text: str, *, has_job: bool) -> bool:
    folded = text.casefold()
    return bool(
        re.search(r"(?:\bss\.lv\b|\bdzīvok\w*|\bdzivok\w*|\bpircēj\w*|\bpircej\w*|\bgrib pirkt\b)", folded)
        or (has_job and re.search(r"(?:\bturpini\b|\bjebkur\b|\blīdz\s+\d|\blidz\s+\d|\bbudžet\w*|\bbudzet\w*|\bvērtīb\w*|\bvertib\w*|\bbild\w*|\beiro\b|\bero\b|\beur\b)", folded))
    )


def _updates(text: str, current: SearchJob) -> SearchJob:
    folded = text.casefold()
    prices = re.findall(r"(?<!\d)(\d{4,6})(?!\d)", folded.replace(" ", ""))
    max_price = int(prices[-1]) if prices else current.max_price
    location = "Latvia" if re.search(r"\b(?:jebkur|latvij)\b", folded) else current.location
    source = "ss.lv" if "ss.lv" in folded else current.source_preference
    preference = current.owner_preference
    if "bild" in folded and re.search(r"\b(?:pats|pati)\b", folded):
        preference = "prioritize_price_owner_reviews_images"
    return SearchJob("sale", "apartment", max_price, "EUR", location, source, preference)


def _mode(text: str) -> str:
    if _BUY.search(text):
        return "buyer_demand"
    return "seller_listing"


def classify_transaction(text: str) -> str:
    value = str(text or "")
    if _RENT.search(value):
        return "rent"
    if _BUY.search(value):
        return "buyer_wanted"
    if _SALE.search(value):
        return "sale"
    return "other"


def _search(job: SearchJob, mode: str) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    if mode == "buyer_demand":
        query = f'site:ss.lv pērku dzīvokli {job.location or "Latvija"}'
    else:
        query = f'site:ss.lv dzīvoklis pārdod {job.location or "Latvija"} līdz {job.max_price} EUR'
    intent = web_research.build_search_plan("Atrodi internetā " + query)
    payload = web_research.search_verified_web(intent)
    return list(web_research.verified_results(payload)), payload


def _seller(item: dict[str, Any], job: SearchJob) -> ListingRecord | None:
    text = " ".join(str(item.get(k) or "") for k in ("title", "page_title", "description_summary", "extracted_snippet"))
    if classify_transaction(text) != "sale":
        return None
    raw_price = str(item.get("price") or "")
    found = re.search(r"\d[\d .]*", raw_price)
    price = int(re.sub(r"\D", "", found.group(0))) if found else 0
    if not price or (job.max_price and price > job.max_price):
        return None
    return ListingRecord(
        str(item.get("source_url") or ""), price, str(item.get("location") or ""),
        str(item.get("rooms") or ""), str(item.get("area") or ""), text[:240],
        "sale", "apartment", str(item.get("fetched_at") or datetime.now(timezone.utc).isoformat()),
        str(item.get("verified_result_id") or ""),
    )


def _buyer(item: dict[str, Any]) -> DemandRecord | None:
    text = " ".join(str(item.get(k) or "") for k in ("title", "page_title", "description_summary", "extracted_snippet"))
    if classify_transaction(text) != "buyer_wanted":
        return None
    raw = str(item.get("price") or "")
    digits = re.sub(r"\D", "", raw)
    return DemandRecord(
        str(item.get("source_url") or ""), str(item.get("location") or ""), int(digits or 0),
        "apartment", text[:240], "buyer_wanted",
        str(item.get("fetched_at") or datetime.now(timezone.utc).isoformat()),
        str(item.get("verified_result_id") or ""),
    )


def match_opportunity(seller: ListingRecord, buyer: DemandRecord) -> OpportunityMatch:
    location = None if not seller.location or not buyer.location else seller.location.casefold() == buyer.location.casefold()
    price = None if not buyer.max_price else seller.price <= buyer.max_price
    property_type = seller.property_type == buyer.property_type
    unknowns = tuple(name for name, known in (("buyer_budget", buyer.max_price > 0), ("location", location is not None)) if not known)
    return OpportunityMatch(seller.canonical_url, buyer.canonical_url, price, location, property_type, unknowns)


def _render(rows, mode: str, payload: dict[str, Any]) -> str:
    if not rows:
        candidates = len(payload.get("results") or ()) + len(payload.get("rejected_results") or ())
        if candidates:
            return "Kandidāti tika atrasti, bet tos nevarēju droši verificēt atbilstoši filtriem, tāpēc neatsūtīšu neapstiprinātus sludinājumus."
        return "Šajā meklējumā neatradu nevienu verificētu atbilstošu sludinājumu."
    if mode == "buyer_demand":
        return "Potenciāls pircēja pieprasījums:\n" + "\n".join(
            f"- {row.location or 'vieta nav norādīta'} — {row.description[:120]}\n  {row.canonical_url}" for row in rows
        )
    lines = []
    for row in rows:
        sqm = ""
        try:
            sqm = f"; {row.price / float(str(row.area).replace(',', '.')):.0f} EUR/m²" if row.area else ""
        except ValueError:
            pass
        lines.append(f"- {row.price} EUR; {row.location or 'vieta nav norādīta'}; {row.rooms or '?'} ist.; {row.area or '?'} m²{sqm}\n  {row.canonical_url}")
    return "Interesanti kandidāti pārbaudei:\n" + "\n".join(lines)


def handle_marketplace_message(text: str, *, workspace_id: str, contact_id: str) -> dict[str, Any] | None:
    source_key = _key(workspace_id, contact_id)
    project = get_work_object_by_source_key(source_key, workspace_id)
    if not _intent(text, has_job=project is not None):
        return None
    if project is not None and project.origin_user_id != contact_id:
        return None
    current = SearchJob(**{k: v for k, v in dict((project.metadata if project else {}) or {}).get("search_job", {}).items() if k in SearchJob.__dataclass_fields__})
    job = _updates(text, current)
    mode = _mode(text)
    metadata = dict((project.metadata if project else {}) or {})
    seen = set(metadata.get("seen_listing_urls") or ())
    should_search = bool(re.search(r"(?:\batrod\w*|\bmekl\w*|\batsūt\w*|\batsut\w*|\bturpini\b|\bpircēj\w*|\bpircej\w*)", text, re.I))
    if mode == "seller_listing" and not job.max_price:
        rows, payload = [], {"error": "price_filter_required"}
    elif not should_search:
        rows, payload = [], {"error": "filters_updated"}
    else:
        try:
            rows, payload = _search(job, mode)
        except (web_research.WebResearchError, OSError, ValueError):
            rows, payload = [], {"error": "acquisition_unavailable"}
    parsed = [(_buyer(item) if mode == "buyer_demand" else _seller(item, job)) for item in rows]
    fresh = [row for row in parsed if row is not None and row.canonical_url not in seen]
    seen.update(row.canonical_url for row in fresh)
    seller_records = list(metadata.get("verified_seller_records") or ())
    buyer_records = list(metadata.get("verified_buyer_records") or ())
    if mode == "seller_listing":
        seller_records.extend(asdict(row) for row in fresh)
    else:
        buyer_records.extend(asdict(row) for row in fresh)
    matches = []
    if seller_records and buyer_records:
        matches.append(asdict(match_opportunity(
            ListingRecord(**seller_records[-1]), DemandRecord(**buyer_records[-1]),
        )))
    metadata.update({
        "marketplace_scouting": True, "search_job": asdict(job), "last_mode": mode,
        "seen_listing_urls": sorted(seen), "last_verified_count": len(fresh),
        "external_action_executed": False, "acquisition_error": str(payload.get("error") or ""),
        "verified_seller_records": seller_records[-20:],
        "verified_buyer_records": buyer_records[-20:],
        "opportunity_matches": matches,
    })
    if project is None:
        project, _ = save_or_get_work_object(
            object_type="project", title="Marketplace opportunity scouting", source_key=source_key,
            workspace_id=workspace_id, origin_user_id=contact_id, metadata=metadata,
        )
    else:
        project = update_work_object(project.object_id, metadata=metadata)
    answer = (
        "Kāds ir maksimālais pirkuma budžets EUR?"
        if payload.get("error") == "price_filter_required" else _render(fresh, mode, payload)
    )
    if payload.get("error") == "filters_updated":
        answer = "Meklēšanas filtri saglabāti."
    elif payload.get("error") == "acquisition_unavailable":
        answer = "Šobrīd meklētājs neatdeva nevienu pārbaudāmu SS.lv sludinājumu."
    return {
        "ok": True, "text": answer, "source": "marketplace_opportunity",
        "work_object_id": project.object_id, "mode": mode, "verified_count": len(fresh),
        "external_action_executed": False,
    }
