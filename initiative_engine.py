"""
NinaOS — Core 2.6.1
Initiative Engine

Šis modulis NEVEIDO gala atbildes tekstu.
Tas tikai nosaka, vai Ninai vajag piedāvāt nākamo soli,
un atgriež strukturētu Initiative Object.

Gala tekstu drīkst veidot tikai Reply Builder.
"""

from datetime import datetime, timezone


CORE_VERSION = "Core 2.6.1"
MODULE_NAME = "Initiative Engine"
MODULE_STATUS = "active"


def initiative_status_object():
    return {
        "enabled": True,
        "core": CORE_VERSION,
        "module": MODULE_NAME,
        "status": MODULE_STATUS,
        "type": "status",
        "priority": "normal",
        "reason": "manual_status_check",
        "message": (
            "Core 2.6.1 — Initiative Detector ir aktīvs. "
            "Tas nozīmē, ka Nina var sākt pamanīt situācijas, "
            "kurās lietotājam noder nākamais solis."
        ),
        "action": "none",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }


def is_initiative_status_command(text):
    lower = (text or "").strip().lower()
    return lower in {
        "core 2.6.1",
        "initiative detector status",
        "initiative status",
        "initiative engine status",
        "core initiative",
    }


def detect_initiative(user_text="", user_context=None, reply_object=None):
    """
    Atgriež strukturētu Initiative Object.

    enabled = False nozīmē: Initiative šajā brīdī neiejaucas.
    enabled = True nozīmē: Reply Builder drīkst iekļaut iniciatīvu gala atbildē.
    """

    text = (user_text or "").strip()
    lower = text.lower()
    user_context = user_context or {}
    reply_object = reply_object or {}

    if not lower:
        return {
            "enabled": False,
            "type": "none",
            "priority": "low",
            "reason": "empty_message",
            "message": "",
            "action": "none",
            "metadata": {},
        }

    if is_initiative_status_command(text):
        return initiative_status_object()

    # Termiņi / nākotnes lietas → piedāvāt atgādinājumu
    reminder_markers = [
        "rīt", "rit", "parīt", "parit",
        "pirmdien", "otrdien", "trešdien", "tresdien",
        "ceturtdien", "piektdien", "sestdien", "svētdien", "svetdien",
        "10:00", "9:00", "8:00", "sapulce", "klients", "klientam",
        "jāzvana", "jazvana", "jāsatiek", "jasatiek",
        "neaizmirst", "atgādini", "atgadini",
    ]

    if "?" not in lower and any(marker in lower for marker in reminder_markers):
        return {
            "enabled": True,
            "type": "reminder_offer",
            "priority": "medium",
            "reason": "future_or_deadline_detected",
            "message": "Vai gribi, lai es šo pārvēršu arī par īstu atgādinājumu?",
            "action": "offer_reminder",
            "metadata": {
                "source_text": text,
            },
        }

    # Projekti / lieli darbi → piedāvāt sadalīt soļos
    planning_markers = [
        "projekts", "projektu", "jāuztaisa", "jauztaisa",
        "jāpabeidz", "japabeidz", "jāsakārto", "jasakarto",
        "daudz darbu", "haoss", "plāns", "plans",
    ]

    if any(marker in lower for marker in planning_markers):
        return {
            "enabled": True,
            "type": "planning_offer",
            "priority": "medium",
            "reason": "planning_context_detected",
            "message": "Varam šo sadalīt mazākos soļos, lai nav viss jātur galvā.",
            "action": "offer_planning",
            "metadata": {
                "source_text": text,
            },
        }

    # Nogurums / smagums → piedāvāt mīkstu nākamo soli
    emotional_markers = [
        "grūti", "gruti", "smagi", "noguris", "nogurusi",
        "nav spēka", "nav speka", "slikta diena", "besī", "besi",
    ]

    if any(marker in lower for marker in emotional_markers):
        return {
            "enabled": True,
            "type": "support_offer",
            "priority": "medium",
            "reason": "emotional_load_detected",
            "message": "Gribi, lai palīdzam to sadalīt pa vienam mazam solim?",
            "action": "offer_support_planning",
            "metadata": {
                "source_text": text,
            },
        }

    return {
        "enabled": False,
        "type": "none",
        "priority": "low",
        "reason": "no_useful_initiative_detected",
        "message": "",
        "action": "none",
        "metadata": {
            "source_text": text,
        },
    }


def build_initiative_status_text():
    """
    Pagaidu statusa teksts testam.

    Šo drīkst izmantot tikai komandas testam app.py līmenī.
    Normālā sarunā gala tekstu vēlāk veidos Reply Builder.
    """
    return (
        "🧠 Core 2.6.1 — Initiative Detector ir aktīvs.\n\n"
        "Nina tagad var noteikt, kad lietotājam noder nākamais solis.\n\n"
        "Svarīgi:\n"
        "• Initiative Engine neveido gala atbildi;\n"
        "• tas sagatavo strukturētu iniciatīvu;\n"
        "• gala tekstu sakārto Reply Builder;\n"
        "• vecais V115.2 sarunas ceļš šai testa komandai vairs netiek izmantots.\n\n"
        "Nākamais solis: Core 2.6.2 — Initiative Generator."
    )
