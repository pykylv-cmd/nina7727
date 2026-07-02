"""
relationship_engine.py
NinaOS Relationship Engine — V1.0

Mērķis:
Pārvērst tekstu par attiecībām starp cilvēku, klientiem, ģimeni, projektiem un lietām.

Piemēri:
- Andris ir mans klients
- Anna ir mana sieva
- Reksis ir mans suns
- NinaOS ir mans galvenais projekts

Šis modulis pats nesūta Telegram ziņas.
"""

RELATIONSHIP_ENGINE_VERSION = "Relationship Engine V1.0"


def _clean(text):
    return (text or "").strip()


def _lower(text):
    return _clean(text).lower()


def normalize_name(value):
    raw = _clean(value).strip(" .,!?:;")
    if not raw:
        return ""

    known = {
        "andrim": "Andris",
        "andris": "Andris",
        "andri": "Andris",
        "annai": "Anna",
        "anna": "Anna",
        "annu": "Anna",
        "reksis": "Reksis",
        "reksi": "Reksis",
        "ninaos": "NinaOS",
        "nina ai": "Nina AI",
    }

    lower = raw.lower()
    if lower in known:
        return known[lower]

    return raw[:1].upper() + raw[1:]


def detect_relationship(text):
    raw = _clean(text)
    lower = raw.lower()

    if not raw:
        return None

    if "?" in lower:
        return None

    # Pattern: "X ir mans/mana ..."
    markers = [" ir mans ", " ir mana ", " ir mūsu ", " ir musu "]
    marker_found = ""

    for marker in markers:
        if marker in lower:
            marker_found = marker
            break

    if not marker_found:
        return None

    idx = lower.find(marker_found)
    subject = normalize_name(raw[:idx].strip())
    tail = raw[idx + len(marker_found):].strip(" .,!?:;")
    tail_lower = tail.lower()

    if not subject or not tail:
        return None

    relation_type = classify_relation(tail_lower)

    return {
        "type": "relationship",
        "subject": subject,
        "relation": relation_type,
        "raw_relation": tail,
        "raw_text": raw,
        "status": "active",
        "source": "telegram",
        "version": RELATIONSHIP_ENGINE_VERSION,
    }


def classify_relation(tail_lower):
    if any(x in tail_lower for x in ["klients", "kliente", "pasūtītājs", "pasutitajs"]):
        return "client"

    if any(x in tail_lower for x in ["sieva", "mīļotā", "milota"]):
        return "wife"

    if any(x in tail_lower for x in ["vīrs", "virs"]):
        return "husband"

    if any(x in tail_lower for x in ["meita"]):
        return "daughter"

    if any(x in tail_lower for x in ["dēls", "dels"]):
        return "son"

    if any(x in tail_lower for x in ["suns"]):
        return "dog"

    if any(x in tail_lower for x in ["kaķis", "kakis"]):
        return "cat"

    if any(x in tail_lower for x in ["projekts", "platforma", "bizness"]):
        return "project"

    if any(x in tail_lower for x in ["auto", "mašīna", "masina"]):
        return "car"

    return "important_person_or_topic"


def relation_label(code):
    labels = {
        "client": "klients",
        "wife": "sieva",
        "husband": "vīrs",
        "daughter": "meita",
        "son": "dēls",
        "dog": "suns",
        "cat": "kaķis",
        "project": "projekts",
        "car": "auto",
        "important_person_or_topic": "svarīga persona/tēma",
    }
    return labels.get(code or "", "svarīga persona/tēma")


def build_relationship_saved_answer(rel, user_name=""):
    if not rel:
        return ""

    prefix = f"{user_name}, " if user_name else ""

    subject = rel.get("subject", "")
    label = relation_label(rel.get("relation", ""))

    lines = [
        f"🧠 {prefix}piefiksēju attiecību. ✅",
        "",
        f"{subject} → {label}",
        "",
        "Tas nozīmē, ka turpmāk es šo neuztveršu kā tukšu tekstu.",
        "Es varēšu sasaistīt darbus, plānus un sarunas ar šo cilvēku vai tēmu.",
        "",
        f"Versija: {RELATIONSHIP_ENGINE_VERSION}",
    ]

    return "\n".join(lines)


def relationship_summary(relationships):
    relationships = relationships or []

    active = []
    seen = set()

    for rel in relationships:
        subject = rel.get("subject", "")
        relation = rel.get("relation", "")
        key = f"{subject}|{relation}".lower()
        if not subject or key in seen:
            continue
        seen.add(key)
        active.append(rel)

    if not active:
        return (
            "🧠 Šobrīd neredzu saglabātas attiecības.\n\n"
            "Uzraksti, piemēram:\n"
            "Andris ir mans klients\n"
            "Anna ir mana sieva\n"
            "NinaOS ir mans galvenais projekts\n\n"
            f"Versija: {RELATIONSHIP_ENGINE_VERSION}"
        )

    lines = ["🧠 Ninas attiecību atmiņa"]

    for rel in active[:20]:
        lines.append(f"• {rel.get('subject')} → {relation_label(rel.get('relation'))}")

    lines.append("")
    lines.append("Šis palīdz man runāt ar kontekstu, nevis sākt no nulles.")
    lines.append("")
    lines.append(f"Versija: {RELATIONSHIP_ENGINE_VERSION}")

    return "\n".join(lines)


def relationship_engine_status():
    return (
        "🧠 Relationship Engine V1.0 ir aktīvs. ✅\n\n"
        "Mērķis: saprast cilvēkus, klientus, ģimeni, projektus un svarīgas saites.\n\n"
        "Testi:\n"
        "Andris ir mans klients\n"
        "Anna ir mana sieva\n"
        "Reksis ir mans suns\n"
        "NinaOS ir mans galvenais projekts\n\n"
        f"Versija: {RELATIONSHIP_ENGINE_VERSION}"
    )
