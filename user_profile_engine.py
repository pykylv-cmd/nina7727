"""
user_profile_engine.py — V22.0

Nina AI Platform
User Profile Engine

Kopīgs profila modulis visiem AI darbiniekiem:
Nina, Tāmētājs, Juris, Laura un nākamie.
"""


def empty_profile(user_id: str = "") -> dict:
    return {
        "user_id": str(user_id or ""),
        "name": "",
        "profession": "",
        "interests": [],
        "projects": [],
        "clients": [],
        "communication_style": "warm",
        "likes_humor": True,
        "check_in_enabled": False,
        "last_seen": "",
        "premium": False,
        "notes": [],
    }


def detect_profile_fact(text: str) -> dict:
    raw = (text or "").strip()
    lower = raw.lower()

    result = {"type": "", "value": ""}

    if not lower:
        return result

    name_markers = ["mani sauc ", "mans vārds ir ", "mans vards ir ", "es esmu "]
    for marker in name_markers:
        if lower.startswith(marker):
            value = raw[len(marker):].strip(" .,!?:;")
            if value:
                return {"type": "name", "value": value[:40]}

    profession_markers = [
        "es strādāju ",
        "es stradaju ",
        "mans darbs ir ",
        "nodarbojos ar ",
    ]
    for marker in profession_markers:
        if marker in lower:
            idx = lower.find(marker)
            value = raw[idx + len(marker):].strip(" .,!?:;")
            if value:
                return {"type": "profession", "value": value[:80]}

    if any(w in lower for w in ["celtniecība", "celtnieciba", "fasādes", "fasades", "būvniecība", "buvnieciba"]):
        return {"type": "interest", "value": "celtniecība"}

    if any(w in lower for w in ["ai", "mākslīgais intelekts", "maksligais intelekts", "bizness"]):
        return {"type": "interest", "value": "AI/bizness"}

    if any(w in lower for w in ["projekts", "projekti", "platforma", "nina"]):
        return {"type": "project", "value": raw[:120]}

    if any(w in lower for w in ["klients", "klienti", "pasūtītājs", "pasutitajs"]):
        return {"type": "client_topic", "value": raw[:120]}

    return result


def update_profile_from_text(profile: dict, text: str) -> dict:
    profile = profile or empty_profile()
    fact = detect_profile_fact(text)

    fact_type = fact.get("type", "")
    value = (fact.get("value", "") or "").strip()

    if not fact_type or not value:
        return profile

    if fact_type == "name":
        profile["name"] = value

    elif fact_type == "profession":
        profile["profession"] = value

    elif fact_type == "interest":
        items = profile.get("interests") or []
        if value not in items:
            items.append(value)
        profile["interests"] = items[:20]

    elif fact_type == "project":
        items = profile.get("projects") or []
        if value not in items:
            items.append(value)
        profile["projects"] = items[:20]

    elif fact_type == "client_topic":
        items = profile.get("clients") or []
        if value not in items:
            items.append(value)
        profile["clients"] = items[:20]

    return profile


def build_profile_saved_answer(fact_type: str, value: str, version="V22.0") -> str:
    fact_type = (fact_type or "").strip()
    value = (value or "").strip()

    if fact_type == "name":
        return (
            f"Patīkami, {value}. 😊\n\n"
            "Paturēšu to prātā, lai nerunātu ar tevi kā ar svešinieku katru reizi.\n\n"
            f"Versija: {version}"
        )

    if fact_type == "profession":
        return (
            "Sapratu. 💼\n\n"
            f"Paturēšu prātā, ka tava joma ir: {value}.\n\n"
            "Tas man palīdzēs dot tev sakarīgākus ieteikumus.\n\n"
            f"Versija: {version}"
        )

    if fact_type == "interest":
        return (
            "Noķēru interesi. 🙂\n\n"
            f"Šī tēma tev varētu būt svarīga: {value}.\n\n"
            f"Versija: {version}"
        )

    if fact_type == "project":
        return (
            "Piefiksēju šo kā projekta tēmu. 🧠\n\n"
            f"{value}\n\n"
            "Vēlāk varēšu atgriezties pie tā, nevis sākt no nulles.\n\n"
            f"Versija: {version}"
        )

    if fact_type == "client_topic":
        return (
            "Saprotu, te ir klientu tēma. 🤝\n\n"
            "Tādas lietas bieži labāk pārvērst par konkrētu plānu vai atgādinājumu.\n\n"
            f"Versija: {version}"
        )

    return f"Piefiksēju. 😊\n\nVersija: {version}"


def profile_summary(profile: dict) -> str:
    profile = profile or empty_profile()
    lines = ["👤 Lietotāja profils"]

    if profile.get("name"):
        lines.append(f"Vārds: {profile['name']}")

    if profile.get("profession"):
        lines.append(f"Profesija/joma: {profile['profession']}")

    if profile.get("interests"):
        lines.append("Intereses: " + ", ".join(profile["interests"][:5]))

    if profile.get("projects"):
        lines.append("Projekti: " + "; ".join(profile["projects"][:3]))

    if profile.get("clients"):
        lines.append("Klientu tēmas: " + "; ".join(profile["clients"][:3]))

    lines.append(f"Komunikācijas stils: {profile.get('communication_style', 'warm')}")
    lines.append(f"Check-in: {'ON' if profile.get('check_in_enabled') else 'OFF'}")
    lines.append(f"Premium: {'ON' if profile.get('premium') else 'OFF'}")

    return "\n".join(lines)


def should_offer_check_in(profile: dict, message_count: int = 0) -> bool:
    profile = profile or empty_profile()

    if profile.get("check_in_enabled"):
        return False

    if message_count >= 5:
        return True

    if profile.get("projects") or profile.get("clients"):
        return True

    return False


def build_check_in_permission_question(version="V22.0") -> str:
    return (
        "Starp citu... 😊\n\n"
        "Ja kādu laiku nerakstīsi, vai vēlies, lai es reizēm pati painteresējos, kā tev iet?\n\n"
        "Es to darītu reti un tikai lai palīdzētu nepazaudēt svarīgas lietas.\n\n"
        "Vari atbildēt vienkārši: jā vai nē.\n\n"
        f"Versija: {version}"
    )
