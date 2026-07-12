from __future__ import annotations

from io import BytesIO
import csv
import hashlib
import json
import re
import zipfile
from typing import Any, Callable, Dict, List
from xml.etree import ElementTree

try:
    from pypdf import PdfReader
except Exception:
    PdfReader = None

DOCUMENT_INTAKE_VERSION = "Document Work Intake V1.7 — ONE NINA Document Intake Structured Facts V1"
MAX_EXTRACTED_CHARS = 50000
MAX_FACTS = 12


def _clean(value: Any) -> str:
    return str(value or "").strip()


def _collapse(text: str) -> str:
    return re.sub(r"\s+", " ", _clean(text)).strip()


def document_fingerprint(data: bytes) -> str:
    return hashlib.sha256(data or b"").hexdigest()


def _decode_text(data: bytes) -> str:
    for encoding in ("utf-8-sig", "utf-8", "cp1257", "cp1251", "latin-1"):
        try:
            return data.decode(encoding)
        except Exception:
            continue
    return data.decode("utf-8", errors="replace")


def _extract_docx(data: bytes) -> str:
    with zipfile.ZipFile(BytesIO(data)) as archive:
        xml_data = archive.read("word/document.xml")
    root = ElementTree.fromstring(xml_data)
    parts: List[str] = []
    for node in root.iter():
        if node.tag.endswith("}t") and node.text:
            parts.append(node.text)
        elif node.tag.endswith("}p"):
            parts.append("\n")
    return " ".join(parts).replace(" \n ", "\n")


def _extract_pdf(data: bytes) -> str:
    if PdfReader is None:
        raise RuntimeError("pypdf dependency is not available")
    reader = PdfReader(BytesIO(data))
    pages: List[str] = []
    for page in reader.pages[:120]:
        page_text = ""
        try:
            # Preserve visual rows/columns whenever pypdf supports layout mode.
            # Deterministic estimate parsing depends on row shape, not prose order.
            page_text = page.extract_text(extraction_mode="layout") or ""
        except TypeError:
            page_text = page.extract_text() or ""
        except Exception:
            page_text = page.extract_text() or ""
        page_text = str(page_text or "").strip()
        if page_text:
            pages.append(page_text)
    return "\n\n".join(pages)


def _extract_csv(data: bytes) -> str:
    text = _decode_text(data)
    rows = []
    for row in csv.reader(text.splitlines()):
        rows.append(" | ".join(_clean(cell) for cell in row))
        if len(rows) >= 1000:
            break
    return "\n".join(rows)


def extract_document_text(data: bytes, filename: str = "", mime_type: str = "") -> Dict[str, Any]:
    filename = _clean(filename)
    mime = _clean(mime_type).lower()
    extension = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    method = ""
    try:
        if extension == "pdf" or mime == "application/pdf":
            text = _extract_pdf(data)
            method = "pypdf"
        elif extension == "docx" or mime == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
            text = _extract_docx(data)
            method = "docx_xml"
        elif extension == "csv" or mime in {"text/csv", "application/csv"}:
            text = _extract_csv(data)
            method = "csv"
        elif extension in {"txt", "md", "json", "xml", "html", "htm", "rtf", "log"} or mime.startswith("text/") or mime in {"application/json", "application/xml"}:
            text = _decode_text(data)
            method = "text_decode"
        else:
            return {"ok": False, "text": "", "method": "unsupported", "error": "unsupported_document_type"}
    except Exception as exc:
        return {"ok": False, "text": "", "method": method or "extract", "error": repr(exc)}

    text = _clean(text)
    if not text:
        return {"ok": False, "text": "", "method": method, "error": "no_extractable_text"}
    return {
        "ok": True,
        "text": text[:MAX_EXTRACTED_CHARS],
        "text_chars": len(text),
        "truncated": len(text) > MAX_EXTRACTED_CHARS,
        "method": method,
    }


def classify_document_kind(filename: str, mime_type: str, text: str) -> str:
    haystack = " ".join([_clean(filename), _clean(mime_type), _clean(text[:10000])]).lower()
    if any(x in haystack for x in ["līgums", "ligums", "contract", "договор", "vienošanās", "vienosanas"]):
        return "contract"
    if any(x in haystack for x in ["rēķins", "rekins", "invoice", "счет", "счёт"]):
        return "invoice"
    if any(x in haystack for x in ["tāme", "tame", "estimate", "quote", "quotation", "смета", "смет"]):
        return "estimate"
    if any(x in haystack for x in ["projekts", "project", "проект", "plāns", "plans", "drawing", "rasēj", "rasej", "чертеж"]):
        return "project_document"
    return "document"


def canonical_document_object_type(document_kind: str) -> str:
    return {
        "contract": "contract",
        "invoice": "invoice",
        "estimate": "estimate",
        "project_document": "document_case",
        "document": "document_case",
    }.get(_clean(document_kind), "document_case")


def _normalize_for_match(text: str) -> str:
    return _collapse(text).casefold()


def _extract_json_object(raw: str) -> Dict[str, Any]:
    match = re.search(r"\{.*\}", _clean(raw), flags=re.DOTALL)
    if not match:
        return {}
    try:
        value = json.loads(match.group(0))
        return value if isinstance(value, dict) else {}
    except Exception:
        return {}


def extract_grounded_document_facts(
    text: str,
    document_kind: str,
    generator: Callable[[str], str] | None,
) -> Dict[str, Any]:
    source = _clean(text)
    if not source or generator is None:
        return {"ok": False, "facts": [], "error": "missing_source_or_generator"}

    prompt = f"""
Tu esi ONE NINA dokumentu darba faktu ekstraktors.
Dokumenta veids: {document_kind}.

Atrodi līdz {MAX_FACTS} biznesā svarīgākajiem faktiem.
Katram faktam obligāti dod ĪSU PRECĪZU CITĀTU no avota laukā evidence.
Nedrīkst interpretēt, vērtēt, secināt risku vai izdomāt faktus.
Ja fakts nav skaidri dokumentā, to neiekļauj.

Atbildi TIKAI ar JSON:
{{"facts":[{{"label":"īss nosaukums","value":"īsa fakta vērtība","evidence":"precīzs fragments no avota"}}]}}

DOKUMENTA TEKSTS:
{source[:MAX_EXTRACTED_CHARS]}
""".strip()
    try:
        data = _extract_json_object(generator(prompt))
    except Exception as exc:
        return {"ok": False, "facts": [], "error": repr(exc)}

    normalized_source = _normalize_for_match(source)
    validated: List[Dict[str, str]] = []
    seen = set()
    for item in data.get("facts") or []:
        if not isinstance(item, dict):
            continue
        label = _clean(item.get("label"))[:100]
        value = _clean(item.get("value"))[:500]
        evidence = _clean(item.get("evidence"))[:1000]
        evidence_norm = _normalize_for_match(evidence)
        if not label or not value or len(evidence_norm) < 3:
            continue
        if evidence_norm not in normalized_source:
            continue
        key = (label.casefold(), value.casefold(), evidence_norm)
        if key in seen:
            continue
        seen.add(key)
        validated.append({"label": label, "value": value, "evidence": evidence})
        if len(validated) >= MAX_FACTS:
            break
    return {"ok": bool(validated), "facts": validated, "validated_count": len(validated)}


def build_document_acknowledgement(filename: str, document_kind: str, facts: List[Dict[str, str]]) -> str:
    labels = {
        "contract": "līgumu",
        "invoice": "rēķinu",
        "estimate": "tāmi / piedāvājumu",
        "project_document": "projekta / plāna dokumentu",
        "document": "dokumentu",
    }
    kind_label = labels.get(document_kind, "dokumentu")
    first = f"Saņēmu {kind_label} “{_clean(filename) or 'dokuments'}” un piesaistīju to darba kontekstam."
    if not facts:
        return first + " Dokumenta tekstu izlasīju, bet droši izceļamus faktus šoreiz neatradu."
    lines = [first, "", "Svarīgākais, ko atradu dokumentā:"]
    for fact in facts[:8]:
        lines.append(f"• {fact['label']}: {fact['value']}")
    return "\n".join(lines)


def prepare_document_intake(
    *,
    file_bytes: bytes,
    filename: str,
    mime_type: str,
    generator: Callable[[str], str] | None,
) -> Dict[str, Any]:
    extracted = extract_document_text(file_bytes, filename=filename, mime_type=mime_type)
    fingerprint = document_fingerprint(file_bytes)
    if not extracted.get("ok"):
        return {
            "ok": False,
            "fingerprint": fingerprint,
            "filename": _clean(filename),
            "mime_type": _clean(mime_type),
            "error": extracted.get("error", "extract_failed"),
            "extraction": extracted,
        }
    text = _clean(extracted.get("text"))
    kind = classify_document_kind(filename, mime_type, text)

    structured_rows: List[Dict[str, Any]] = []
    fact_source = "grounded_llm_facts"
    if kind == "estimate":
        # ONE NINA Document Intake Structured Facts V1:
        # the SAME deterministic estimate row parser feeds both intake summary
        # and later document calculations/actions. No second estimate truth.
        structured_rows = parse_deterministic_estimate_cost_items(text)
        facts: List[Dict[str, str]] = []
        for row in structured_rows[:8]:
            label = _clean(row.get("label"))
            amount = float(row.get("amount") or 0)
            amount_text = _clean(row.get("amount_text"))
            evidence = _clean(row.get("evidence"))[:1000]
            if not label or amount <= 0 or not evidence:
                continue
            facts.append({
                "label": f"{label} kopējās izmaksas",
                "value": _format_business_amount(amount, amount_text),
                "evidence": evidence,
            })
        fact_source = "deterministic_estimate_row_schema"
    else:
        grounded = extract_grounded_document_facts(text, kind, generator)
        facts = grounded.get("facts") if grounded.get("ok") else []

    return {
        "ok": True,
        "fingerprint": fingerprint,
        "filename": _clean(filename),
        "mime_type": _clean(mime_type),
        "document_kind": kind,
        "object_type": canonical_document_object_type(kind),
        "extracted_text": text,
        "extraction_method": extracted.get("method"),
        "text_chars": extracted.get("text_chars", len(text)),
        "truncated": bool(extracted.get("truncated")),
        "facts": facts,
        "grounded_fact_count": len(facts),
        "fact_source": fact_source,
        "structured_estimate_rows": structured_rows,
        "structured_estimate_row_count": len(structured_rows),
        "acknowledgement": build_document_acknowledgement(filename, kind, facts),
    }


def answer_document_followup(
    *,
    question: str,
    source_text: str,
    document_kind: str,
    grounded_facts: List[Dict[str, str]] | None,
    generator: Callable[[str], str] | None,
) -> Dict[str, Any]:
    """Answer one question from the already-persisted canonical document source.

    The model may select or explain source facts, but every answer must carry at
    least one exact source evidence fragment. Evidence is validated before the
    answer is accepted. This keeps document follow-up inside the same ONE NINA
    canonical document truth instead of falling back to generic chat memory.
    """
    question = _clean(question)
    source = _clean(source_text)
    facts = list(grounded_facts or [])
    if not question or not source or generator is None:
        return {"ok": False, "error": "missing_question_source_or_generator", "answer": ""}

    fact_context = "\n".join(
        f"- { _clean(item.get('label')) }: { _clean(item.get('value')) } | evidence: { _clean(item.get('evidence')) }"
        for item in facts[:MAX_FACTS]
        if isinstance(item, dict)
    )
    prompt = f"""
Tu esi ONE NINA dokumentu darba jautājumu dzinējs.
Atbildi TIKAI no zemāk dotā kanoniskā dokumenta teksta.
Dokumenta veids: {document_kind}.

LIETOTĀJA JAUTĀJUMS:
{question}

JAU VALIDĒTIE FAKTI:
{fact_context or '(nav)'}

LIKUMI:
- neatbildi no vispārīgām zināšanām;
- neizdomā trūkstošu summu, datumu, personu vai nosacījumu;
- ja dokumentā ir tieša atbilde, atbildi īsi un konkrēti;
- ja atbildi nevar droši noteikt no dokumenta, answer laukā pasaki tieši to;
- evidence masīvā dod 1 līdz 4 ĪSUS PRECĪZUS CITĀTUS no dokumenta teksta, kas tieši pamato atbildi;
- ja drošas evidence nav, dod tukšu evidence masīvu un confident=false.

Atbildi TIKAI ar JSON:
{{"answer":"īsa atbilde lietotājam","evidence":["precīzs citāts"],"confident":true}}

KANONISKAIS DOKUMENTA TEKSTS:
{source[:MAX_EXTRACTED_CHARS]}
""".strip()

    try:
        data = _extract_json_object(generator(prompt))
    except Exception as exc:
        return {"ok": False, "error": repr(exc), "answer": ""}

    answer = _clean(data.get("answer"))[:2000]
    evidence_items = data.get("evidence") or []
    if not isinstance(evidence_items, list):
        evidence_items = []
    normalized_source = _normalize_for_match(source)
    validated_evidence: List[str] = []
    seen = set()
    for raw in evidence_items[:4]:
        evidence = _clean(raw)[:1500]
        evidence_norm = _normalize_for_match(evidence)
        if len(evidence_norm) < 3 or evidence_norm not in normalized_source:
            continue
        if evidence_norm in seen:
            continue
        seen.add(evidence_norm)
        validated_evidence.append(evidence)

    confident = bool(data.get("confident")) and bool(validated_evidence) and bool(answer)
    if not confident:
        return {
            "ok": False,
            "error": "no_validated_document_evidence",
            "answer": "No šī dokumenta saglabātā teksta to nevaru droši noteikt.",
            "evidence": validated_evidence,
        }
    return {
        "ok": True,
        "answer": answer,
        "evidence": validated_evidence,
        "validated_evidence_count": len(validated_evidence),
    }

# =========================
# ONE NINA Document Work Actions V1
# =========================

DOCUMENT_WORK_ACTIONS_VERSION = "ONE NINA Document Work Actions V1.2 — Document-to-Client Action V1"
DOCUMENT_TO_CLIENT_ACTION_VERSION = "ONE NINA Document-to-Client Action V1.1 — Safe Neutral Fallback"
_DOCUMENT_ACTIONS = {"client_message", "top_cost_items", "risk_review", "summary", "compare"}


def classify_document_work_action(text: str) -> Dict[str, Any]:
    """Deterministically detect explicit owner instructions to work with a document.

    This is intentionally narrow: ordinary questions remain in canonical document
    follow-up. Only clear work verbs/actions enter the action executor.
    """
    value = _collapse(text).casefold()
    if not value:
        return {"matched": False, "action": ""}

    compare_markers = ("salīdzini", "salidzini", "salīdzināt", "salidzinat", "compare", "сравни")
    if any(x in value for x in compare_markers) and any(x in value for x in ("tām", "tam", "dokument", "rēķ", "rekin", "līgum", "ligum", "pdf", "fail", "смет", "счет", "договор")):
        return {"matched": True, "action": "compare"}

    client_markers = (
        "uztaisi klientam", "sagatavo klientam", "uzraksti klientam", "īsu ziņu klientam",
        "isu zinu klientam", "ziņu par šo tāmi", "zinu par so tami", "par šo tāmi klientam",
        "par so tami klientam", "ko sūtīt klientam", "ko sutit klientam", "atbildi klientam",
        "pārsūtīt klientam", "parsutit klientam", "client message", "message to client",
        "send to client", "сообщение клиенту", "написать клиенту", "ответ клиенту",
    )
    if any(x in value for x in client_markers):
        return {"matched": True, "action": "client_message"}

    cost_markers = (
        "dārgāk", "dargak", "lielākās pozīc", "lielakas pozic", "top pozīc", "top pozic",
        "highest cost", "most expensive", "дорог", "самые большие позиции",
    )
    if any(x in value for x in cost_markers):
        return {"matched": True, "action": "top_cost_items"}

    risk_markers = ("atrodi risk", "riski līgum", "riski ligum", "izvērtē risk", "izverte risk", "risk review", "find risks", "найди риск")
    if any(x in value for x in risk_markers):
        return {"matched": True, "action": "risk_review"}

    summary_markers = ("apkopo šo", "apkopo so", "īss kopsavilk", "iss kopsavilk", "summarize this", "summary of this", "кратко резюм")
    if any(x in value for x in summary_markers):
        return {"matched": True, "action": "summary"}

    return {"matched": False, "action": ""}


def _validated_action_payload(raw: str, source_text: str) -> Dict[str, Any]:
    data = _extract_json_object(raw)
    answer = _clean(data.get("answer"))[:4000]
    evidence_items = data.get("evidence") or []
    if not isinstance(evidence_items, list):
        evidence_items = []
    normalized_source = _normalize_for_match(source_text)
    validated: List[str] = []
    seen = set()
    for raw_evidence in evidence_items[:8]:
        evidence = _clean(raw_evidence)[:1500]
        norm = _normalize_for_match(evidence)
        if len(norm) < 3 or norm not in normalized_source or norm in seen:
            continue
        seen.add(norm)
        validated.append(evidence)
    confident = bool(data.get("confident")) and bool(answer) and bool(validated)
    return {"ok": confident, "answer": answer, "evidence": validated, "validated_evidence_count": len(validated)}



# =========================
# ONE NINA Estimate Row Schema Parser V1
# =========================

DETERMINISTIC_DOCUMENT_CALCULATIONS_VERSION = "ONE NINA Estimate Row Schema Parser V1"

_AMOUNT_CELL_RE = re.compile(
    r"(?<![\w])(?:\d{1,3}(?:[ \u00a0]\d{3})+|\d+)(?:[\.,]\d{1,2})?(?:\s*(?:EUR|euro|€))?(?![\w])",
    flags=re.IGNORECASE,
)

_TABLE_HEADER_MARKERS = {
    "nr", "n.p.k", "pozīcija", "pozicija", "darba nosaukums", "nosaukums",
    "mērvienība", "mervieniba", "apjoms", "daudzums", "vienības cena",
    "vienibas cena", "cena", "kopā", "kopa", "summa", "izmaksas",
    "materiāli", "materiali", "mehānismi", "mehanismi", "darba alga",
}

_SUMMARY_ROW_MARKERS = (
    "pavisam", "kopā bez", "kopa bez", "kopā ar", "kopa ar", "pvn",
    "subtotal", "grand total", "kopsumma", "gala summa", "virsizdevumi",
    "peļņa", "pelna", "atlaide",
)

_UNIT_TOKEN_RE = re.compile(
    r"(?i)(?<![\w])(m2|m²|m3|m³|gab\.?|kompl\.?|k-?ta|kg|dienas?|reizes?|st\.?|h|t|m)(?=(?:\s|$|[|;,:]))"
)
_UNIT_ONLY_RE = re.compile(
    r"^(?:m2|m²|m3|m³|m|gab\.?|kompl\.?|k-?ta|kg|t|h|st\.?|diena|dienas|reize|reizes|%|eur|€)$",
    flags=re.IGNORECASE,
)
_ROW_NUMBER_RE = re.compile(r"^\s*(\d{1,3})[\.)]?\s+")


def _parse_business_amount(value: Any) -> float | None:
    raw = _clean(value)
    if not raw:
        return None
    text = raw.replace("\u00a0", " ").strip()
    text = re.sub(r"(?i)(eur|euro|€)", "", text).strip()
    text = re.sub(r"[^0-9,.' -]", "", text).strip()
    text = text.replace("'", "").replace(" ", "")
    if not text or not re.search(r"\d", text):
        return None
    if "," in text and "." in text:
        if text.rfind(",") > text.rfind("."):
            text = text.replace(".", "").replace(",", ".")
        else:
            text = text.replace(",", "")
    elif "," in text:
        parts = text.split(",")
        text = parts[0] + "." + parts[1] if len(parts) == 2 and 1 <= len(parts[1]) <= 2 else "".join(parts)
    elif "." in text:
        parts = text.split(".")
        if not (len(parts) == 2 and 1 <= len(parts[1]) <= 2):
            text = "".join(parts)
    try:
        amount = float(text)
    except Exception:
        return None
    return amount if 0 <= amount <= 1_000_000_000 else None


def _format_business_amount(amount: float, amount_text: str = "") -> str:
    decimals = 2 if abs(amount - round(amount)) > 0.000001 else 0
    rendered = f"{amount:,.{decimals}f}".replace(",", " ").replace(".", ",")
    return f"{rendered} EUR"


def _source_lines(source_text: str) -> List[str]:
    return [raw.strip() for raw in _clean(source_text).replace("\r", "\n").split("\n") if raw.strip()]


def _amount_cells(line: str) -> List[Dict[str, Any]]:
    cells: List[Dict[str, Any]] = []
    for match in _AMOUNT_CELL_RE.finditer(_clean(line)):
        token = _collapse(match.group(0))
        amount = _parse_business_amount(token)
        if amount is not None:
            cells.append({"text": token, "amount": amount, "start": match.start(), "end": match.end()})
    return cells


def _strip_row_number(label: str) -> str:
    value = _collapse(label)
    value = re.sub(r"^\s*\d{1,3}[\.)]?\s+", "", value)
    return value.strip(" -–—|;:")


def _header_marker_count(value: str) -> int:
    folded = _collapse(value).casefold()
    return sum(1 for marker in _TABLE_HEADER_MARKERS if marker in folded)


def _is_table_header(line: str) -> bool:
    value = _collapse(line).casefold().strip(" .:;|-–—")
    return not value or value in _TABLE_HEADER_MARKERS or _header_marker_count(value) >= 2


def _is_summary_row(label: str) -> bool:
    value = _collapse(label).casefold()
    return any(marker in value for marker in _SUMMARY_ROW_MARKERS)


def _is_unit_only(line: str) -> bool:
    return bool(_UNIT_ONLY_RE.fullmatch(_collapse(line).replace(" ", "")))


def _looks_like_label(line: str) -> bool:
    value = _strip_row_number(line)
    if not value or _is_table_header(value) or _is_unit_only(value) or _is_summary_row(value):
        return False
    if _header_marker_count(value) >= 2:
        return False
    letters = re.findall(r"[^\W\d_]", value, flags=re.UNICODE)
    return len(letters) >= 3 and not bool(_AMOUNT_CELL_RE.fullmatch(value))


def _schema_row_from_inline(line: str, line_index: int) -> Dict[str, Any] | None:
    raw = _clean(line)
    unit_match = _UNIT_TOKEN_RE.search(raw)
    if not unit_match:
        return None
    prefix = _strip_row_number(raw[:unit_match.start()])
    if not _looks_like_label(prefix):
        return None
    tail = raw[unit_match.end():]
    numeric = _amount_cells(tail)
    # Valid estimate row schema requires quantity plus at least one price/total column.
    if len(numeric) < 2:
        return None
    total = numeric[-1]
    if total["amount"] <= 0:
        return None
    return {
        "label": prefix, "unit": unit_match.group(1),
        "quantity_text": numeric[0]["text"],
        "numeric_columns": [cell["text"] for cell in numeric],
        "amount": float(total["amount"]), "amount_text": total["text"],
        "evidence": raw, "source_line_start": line_index, "source_line_end": line_index,
        "parser_path": "estimate_row_schema_inline",
    }


def _schema_row_from_flattened(lines: List[str], start_index: int) -> Dict[str, Any] | None:
    label_line = lines[start_index]
    # Flattened fallback must have a visible row number. This prevents column/header
    # fragments such as 'EUR Materiāli, EUR Mehānismi' from becoming fake positions.
    if not _ROW_NUMBER_RE.match(label_line) or not _looks_like_label(label_line):
        return None
    label = _strip_row_number(label_line)
    unit = ""
    numeric: List[Dict[str, Any]] = []
    evidence = [label_line]
    end_index = start_index
    for idx in range(start_index + 1, min(len(lines), start_index + 12)):
        line = lines[idx]
        if idx > start_index + 1 and _ROW_NUMBER_RE.match(line) and _looks_like_label(line):
            break
        if _is_summary_row(line):
            break
        if not unit and _is_unit_only(line):
            unit = _collapse(line)
        evidence.append(line)
        end_index = idx
        numeric.extend(_amount_cells(line))
    if not unit or len(numeric) < 2:
        return None
    total = numeric[-1]
    if total["amount"] <= 0:
        return None
    return {
        "label": label, "unit": unit, "quantity_text": numeric[0]["text"],
        "numeric_columns": [cell["text"] for cell in numeric],
        "amount": float(total["amount"]), "amount_text": total["text"],
        "evidence": " | ".join(evidence), "source_line_start": start_index,
        "source_line_end": end_index, "parser_path": "estimate_row_schema_flattened",
    }


def parse_deterministic_estimate_cost_items(source_text: str) -> List[Dict[str, Any]]:
    lines = _source_lines(source_text)
    candidates: List[Dict[str, Any]] = []
    for idx, line in enumerate(lines):
        row = _schema_row_from_inline(line, idx)
        if row:
            candidates.append(row)
    for idx in range(len(lines)):
        row = _schema_row_from_flattened(lines, idx)
        if row:
            candidates.append(row)

    deduped: Dict[str, Dict[str, Any]] = {}
    for item in candidates:
        key = re.sub(r"\s+", " ", _clean(item.get("label")).casefold()).strip()
        if not key or _is_summary_row(key) or _is_table_header(key):
            continue
        current = deduped.get(key)
        # Prefer inline layout-preserved schema over flattened fallback; then larger total.
        if current is None:
            deduped[key] = item
        elif item.get("parser_path") == "estimate_row_schema_inline" and current.get("parser_path") != "estimate_row_schema_inline":
            deduped[key] = item
        elif item.get("parser_path") == current.get("parser_path") and float(item["amount"]) > float(current["amount"]):
            deduped[key] = item

    items = list(deduped.values())
    items.sort(key=lambda row: (-float(row["amount"]), _clean(row["label"]).casefold()))
    return items


def extract_deterministic_cost_items(*, source_text: str, generator: Callable[[str], str] | None = None) -> Dict[str, Any]:
    source = _clean(source_text)
    if not source:
        return {"ok": False, "items": [], "error": "missing_source"}
    items = parse_deterministic_estimate_cost_items(source)
    return {
        "ok": bool(items), "items": items, "validated_count": len(items),
        "calculation_version": DETERMINISTIC_DOCUMENT_CALCULATIONS_VERSION,
        "candidate_discovery": "deterministic_estimate_row_schema",
    }


def build_deterministic_top_cost_answer(items: List[Dict[str, Any]], limit: int = 15) -> str:
    ranked = list(items or [])[:max(1, int(limit))]
    if not ranked:
        return "No dokumenta saglabātā teksta nevaru droši noteikt pozīciju kopējās summas."
    lines = ["Dārgākās pozīcijas šajā tāmē no lielākās uz mazāko:"]
    for index, item in enumerate(ranked, start=1):
        lines.append(f"{index}. {_clean(item.get('label'))} — {_format_business_amount(float(item.get('amount') or 0), _clean(item.get('amount_text')))}")
    return "\n".join(lines)

def execute_document_to_client_action(
    *,
    instruction: str,
    source_text: str,
    document_kind: str,
    grounded_facts: List[Dict[str, str]] | None,
    generator: Callable[[str], str] | None,
) -> Dict[str, Any]:
    """Prepare one owner-ready client message from the SAME canonical document source.

    The result is a deliverable for the owner to forward in the current channel.
    It does not send, create a second Work Object, or expose NinaOS/AI wording.
    """
    instruction = _clean(instruction)
    source = _clean(source_text)
    facts = list(grounded_facts or [])
    if not instruction or not source or generator is None:
        return {"ok": False, "error": "missing_document_to_client_source", "answer": ""}

    fact_context = "\n".join(
        f"- {_clean(item.get('label'))}: {_clean(item.get('value'))} | evidence: {_clean(item.get('evidence'))}"
        for item in facts[:MAX_FACTS] if isinstance(item, dict)
    )
    prompt = f"""
Tu esi ONE NINA dokumenta-to-client darba darbība.
Tu strādā īpašnieka aizkulisēs. Gala tekstu īpašnieks var uzreiz pārsūtīt savam klientam Telegram, WhatsApp vai citā saziņas kanālā.
Dokumenta veids: {document_kind}.
Īpašnieka instrukcija: {instruction}

JAU VALIDĒTIE FAKTI:
{fact_context or '(nav)'}

UZDEVUMS:
Sagatavo īsu, dabisku un profesionālu ziņu klientam par šo dokumentu.

STINGRIE LIKUMI:
- raksti tikai gala ziņu klientam;
- neraksti ievadu "Te ir gatavs teksts";
- neraksti "Versija", "ONE NINA", "NinaOS", "AI" vai tehnisku tekstu;
- neraksti, ka ziņu sagatavoja palīgs, robots vai Nina;
- neizdomā klienta vārdu, ja tas nav dokumentā;
- neizdomā summas, termiņus, PVN, garantijas, apmaksas vai citus nosacījumus;
- konkrētus dokumenta faktus izmanto tikai tad, ja tos pamato avots;
- ja dokumentā ir skaidra gala summa un tā ir būtiska instrukcijai, drīksti to iekļaut;
- neraksti garu visu pozīciju sarakstu, ja īpašnieks to nav prasījis;
- saglabā cilvēka dabisku saziņas stilu;
- evidence masīvā dod 1 līdz 8 ĪSUS PRECĪZUS citātus no avota, kas pamato gala ziņas konkrētos faktus;
- ja drošu klienta ziņu no dokumenta nevar sagatavot, confident=false.

Atbildi TIKAI ar JSON:
{{"answer":"tikai gatava klienta ziņa","evidence":["precīzs citāts"],"confident":true}}

KANONISKAIS DOKUMENTA TEKSTS:
{source[:MAX_EXTRACTED_CHARS]}
""".strip()
    try:
        result = _validated_action_payload(generator(prompt), source)
    except Exception as exc:
        return {"ok": False, "error": repr(exc), "answer": ""}
    if not result.get("ok"):
        # V1.1: a client deliverable does not need to fail merely because the model
        # did not return a byte-exact evidence quote. When no document fact can be
        # safely validated, return a deterministic neutral message with ZERO
        # document claims. This is still grounded-safe: no amount, date, person,
        # tax, warranty, payment term or other source fact is invented.
        result = {
            "ok": True,
            "answer": (
                "Labdien! Nosūtu sagatavoto tāmi. "
                "Lūdzu, apskatiet to un dodiet ziņu, ja ir jautājumi vai vēlaties ko precizēt."
            ),
            "evidence": [],
            "validated_evidence_count": 0,
            "grounding_mode": "safe_neutral_no_document_claims",
        }
    else:
        result["grounding_mode"] = "validated_document_evidence"
    result["action"] = "client_message"
    result["action_version"] = DOCUMENT_TO_CLIENT_ACTION_VERSION
    result["deliverable_type"] = "client_message"
    result["owner_forward_ready"] = True
    return result


def execute_document_work_action(
    *,
    action: str,
    instruction: str,
    source_text: str,
    document_kind: str,
    grounded_facts: List[Dict[str, str]] | None,
    generator: Callable[[str], str] | None,
) -> Dict[str, Any]:
    """Execute a grounded work action against one canonical document source."""
    action = _clean(action)
    instruction = _clean(instruction)
    source = _clean(source_text)
    facts = list(grounded_facts or [])
    if action not in _DOCUMENT_ACTIONS - {"compare"} or not instruction or not source or generator is None:
        return {"ok": False, "error": "invalid_action_or_missing_source", "answer": ""}

    if action == "client_message":
        return execute_document_to_client_action(
            instruction=instruction,
            source_text=source,
            document_kind=document_kind,
            grounded_facts=facts,
            generator=generator,
        )

    if action == "top_cost_items":
        deterministic = extract_deterministic_cost_items(source_text=source, generator=generator)
        if not deterministic.get("ok"):
            return {
                "ok": False,
                "error": "no_validated_deterministic_cost_items",
                "answer": "No šī dokumenta saglabātā teksta nevaru droši noteikt pozīciju kopējās summas.",
                "evidence": [],
            }
        items = list(deterministic.get("items") or [])
        return {
            "ok": True,
            "answer": build_deterministic_top_cost_answer(items),
            "evidence": [str(item.get("evidence") or "") for item in items[:8]],
            "validated_evidence_count": min(len(items), 8),
            "action": action,
            "action_version": DOCUMENT_WORK_ACTIONS_VERSION,
            "calculation_version": deterministic.get("calculation_version"),
            "calculated_items": items[:15],
        }

    action_rules = {
        "client_message": "Sagatavo īsu, dabisku, klientam pārsūtāmu ziņu. Neraksti, ka to sagatavoja AI/Nina. Neizdomā klienta vārdu. Iekļauj tikai dokumentā pamatotus faktus.",
        "top_cost_items": "Atrodi dokumentā dārgākās pozīcijas. Salīdzini tikai summas, kas skaidri piesaistītas konkrētām pozīcijām. Atbildē sakārto no lielākās uz mazāko.",
        "risk_review": "Atrodi dokumentā redzamus biznesa riskus vai neskaidrus nosacījumus. Katru risku pamato ar dokumenta tekstu. Nesniedz juridisku spriedumu un neizdomā neesošus nosacījumus.",
        "summary": "Dod īsu darba kopsavilkumu tikai no dokumenta faktiem.",
    }
    fact_context = "\n".join(
        f"- {_clean(item.get('label'))}: {_clean(item.get('value'))} | evidence: {_clean(item.get('evidence'))}"
        for item in facts[:MAX_FACTS] if isinstance(item, dict)
    )
    prompt = f"""
Tu esi ONE NINA dokumentu darba darbību dzinējs.
Strādā ar VIENU jau saglabātu canonical dokumenta Work Object.
Dokumenta veids: {document_kind}.
Darbība: {action}.
Lietotāja instrukcija: {instruction}

DARBĪBAS LIKUMS:
{action_rules[action]}

JAU VALIDĒTIE FAKTI:
{fact_context or '(nav)'}

OBLIGĀTI:
- atbildi tikai no dokumenta avota;
- neizdomā summas, datumus, personas, pozīcijas vai nosacījumus;
- visi konkrētie dokumenta fakti gala atbildē jābalsta ar evidence;
- evidence masīvā dod 1 līdz 8 ĪSUS PRECĪZUS citātus no avota;
- ja darbību nevar droši izdarīt no avota, confident=false;
- gala answer nedrīkst saturēt "Versija", "ONE NINA", "NinaOS" vai AI tehnisku tekstu.

Atbildi TIKAI ar JSON:
{{"answer":"gatavs darba rezultāts","evidence":["precīzs citāts"],"confident":true}}

KANONISKAIS DOKUMENTA TEKSTS:
{source[:MAX_EXTRACTED_CHARS]}
""".strip()
    try:
        result = _validated_action_payload(generator(prompt), source)
    except Exception as exc:
        return {"ok": False, "error": repr(exc), "answer": ""}
    if not result.get("ok"):
        return {"ok": False, "error": "no_validated_document_action_evidence", "answer": "No šī dokumenta saglabātā teksta šo darbību nevaru droši izpildīt.", "evidence": result.get("evidence", [])}
    result["action"] = action
    result["action_version"] = DOCUMENT_WORK_ACTIONS_VERSION
    return result


def compare_canonical_documents(
    *,
    instruction: str,
    first_source_text: str,
    first_label: str,
    second_source_text: str,
    second_label: str,
    generator: Callable[[str], str] | None,
) -> Dict[str, Any]:
    """Compare two already-persisted canonical document sources with source-tagged evidence."""
    first = _clean(first_source_text)
    second = _clean(second_source_text)
    if not first or not second or generator is None:
        return {"ok": False, "error": "two_document_sources_required", "answer": "Lai salīdzinātu, vajag divus saglabātus dokumentus."}
    prompt = f"""
Tu esi ONE NINA canonical dokumentu salīdzināšanas dzinējs.
Lietotāja instrukcija: {_clean(instruction)}
Salīdzini tikai zemāk dotos DIVUS dokumentus.
Neizdomā faktus un nevērtē pēc ārējām zināšanām.
Katram konkrētam secinājumam jābūt pamatotam ar precīzu citātu.
Evidence ieraksti formā "A: precīzs citāts" vai "B: precīzs citāts".
Ja drošu salīdzinājumu nevar izdarīt, confident=false.
Atbildi TIKAI JSON:
{{"answer":"īss praktisks salīdzinājums","evidence":["A: citāts","B: citāts"],"confident":true}}

DOKUMENTS A — {_clean(first_label)}:
{first[:MAX_EXTRACTED_CHARS // 2]}

DOKUMENTS B — {_clean(second_label)}:
{second[:MAX_EXTRACTED_CHARS // 2]}
""".strip()
    try:
        data = _extract_json_object(generator(prompt))
    except Exception as exc:
        return {"ok": False, "error": repr(exc), "answer": ""}
    answer = _clean(data.get("answer"))[:4000]
    raw_evidence = data.get("evidence") or []
    if not isinstance(raw_evidence, list):
        raw_evidence = []
    first_norm = _normalize_for_match(first)
    second_norm = _normalize_for_match(second)
    validated = []
    for item in raw_evidence[:10]:
        evidence = _clean(item)
        if len(evidence) < 4 or ":" not in evidence:
            continue
        tag, quote = evidence.split(":", 1)
        quote_norm = _normalize_for_match(quote)
        if tag.strip().upper() == "A" and quote_norm and quote_norm in first_norm:
            validated.append(evidence)
        elif tag.strip().upper() == "B" and quote_norm and quote_norm in second_norm:
            validated.append(evidence)
    if not (bool(data.get("confident")) and answer and validated):
        return {"ok": False, "error": "no_validated_comparison_evidence", "answer": "No abiem saglabātajiem dokumentiem drošu salīdzinājumu šoreiz nevaru izveidot.", "evidence": validated}
    return {"ok": True, "action": "compare", "answer": answer, "evidence": validated, "action_version": DOCUMENT_WORK_ACTIONS_VERSION}

