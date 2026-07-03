"""
presentation_language.py
NinaOS Presentation / Language Layer — V1.0

Mērķis:
- atdalīt iekšējos tehniskos terminus no lietotājam redzamās valodas;
- lietotājam rādīt skaidru, cilvēcīgu valodu;
- sagatavot NinaOS vēlākai daudzvalodu paplašināšanai bez sāpēm.

Šis modulis nemaina datubāzi.
"""

PRESENTATION_LANGUAGE_VERSION = "Presentation / Language Layer V1.0"

DEFAULT_LOCALE = "lv"
FALLBACK_LOCALE = "en"


LABELS = {
    "lv": {
        "client_overview": "Klientu pārskats",
        "my_clients": "Mani klienti",
        "clients": "Klienti",
        "client_status": "Klienta statuss",
        "offer_status": "Piedāvājums",
        "active_tasks": "Aktīvie darbi",
        "next_step": "Nākamais solis",
        "risk": "Risks",
        "low_risk": "zems",
        "offer_to_send": "jānosūta piedāvājums",
        "waiting_reply": "jāgaida atbilde",
        "needs_reminder": "kam jāatgādina",
        "needs_offer": "kam jānosūta piedāvājums",
        "stuck_clients": "Klienti ar risku / iestrēgumu",
        "quick_client_views": "Ātrie klientu skati",
        "what_next": "Ko vari darīt tālāk",
    },
    "en": {
        "client_overview": "Client overview",
        "my_clients": "My clients",
        "clients": "Clients",
        "client_status": "Client status",
        "offer_status": "Offer",
        "active_tasks": "Active tasks",
        "next_step": "Next step",
        "risk": "Risk",
        "low_risk": "low",
        "offer_to_send": "offer to send",
        "waiting_reply": "waiting for reply",
        "needs_reminder": "who needs a reminder",
        "needs_offer": "who needs an offer",
        "stuck_clients": "Clients with risk / stuck work",
        "quick_client_views": "Quick client views",
        "what_next": "What you can do next",
    }
}


def normalize_locale(locale=""):
    locale = (locale or "").strip().lower()
    if not locale:
        return DEFAULT_LOCALE
    if locale in LABELS:
        return locale
    for sep in ["-", "_"]:
        if sep in locale:
            short = locale.split(sep, 1)[0]
            if short in LABELS:
                return short
    return DEFAULT_LOCALE


def label(key, locale=DEFAULT_LOCALE):
    loc = normalize_locale(locale)
    if key in LABELS.get(loc, {}):
        return LABELS[loc][key]
    if key in LABELS.get(FALLBACK_LOCALE, {}):
        return LABELS[FALLBACK_LOCALE][key]
    return key.replace("_", " ")


def humanize_public_text(text, locale=DEFAULT_LOCALE):
    """
    V1.0 drošs publisko tekstu polish.
    Neaiztiek iekšējo loģiku, tikai lietotājam redzamo tekstu.
    """
    out = text or ""
    loc = normalize_locale(locale)

    if loc == "lv":
        replacements = [
            ("📊 Sales Pipeline / Client CRM", "📊 Klientu pārskats"),
            ("Sales Pipeline / Client CRM V1.2", "Klientu pārskats V1.2"),
            ("Sales Pipeline / Client CRM V1.1", "Klientu pārskats V1.1"),
            ("Sales Pipeline / Client CRM V1.0", "Klientu pārskats V1.0"),
            ("Pipeline:", "Klienta statuss:"),
            ("pipeline", "klientu pārskats"),
            ("Pipeline", "Klientu pārskats"),
            ("CRM", "klientiem"),
            ("follow-up", "atgādinājums"),
            ("Follow-up", "Atgādinājums"),
            ("kam jātaisa atgādinājums", "kam jāatgādina"),
            ("kam jātaisa follow-up", "kam jāatgādina"),
            ("Ātrie CRM skati:", "Ātrie klientu skati:"),
            ("Client Work View", "Klientu darba skats"),
            ("client work", "klienta darbi"),
        ]
        for old, new in replacements:
            out = out.replace(old, new)

    out = polish_followup_hint_text(out, locale=loc)
    return out


def presentation_status_answer():
    return (
        "🌍 Presentation / Language Layer V1.0 ir aktīvs. ✅\n\n"
        "Uzdevums:\n"
        "- iekšējos tehniskos terminus atstāt kodā;\n"
        "- lietotājam rādīt skaidru, cilvēcīgu valodu;\n"
        "- sagatavot NinaOS vēlākai daudzvalodu paplašināšanai.\n\n"
        "Publiski lietojam:\n"
        "- klienti\n"
        "- klientu pārskats\n"
        "- kam jānosūta piedāvājums\n"
        "- kam jāatgādina\n\n"
        "Tehniskie aliasi joprojām strādā, bet Nina tos vairs nereklamē.\n\n"
        f"Versija: {PRESENTATION_LANGUAGE_VERSION}"
    )



def polish_followup_hint_text(text, locale=DEFAULT_LOCALE):
    out = text or ""
    if normalize_locale(locale) == "lv":
        out = out.replace("Ja klients jāatgādina:", "Ja klientam jāatgādina:")
        out = out.replace("uzraksti atgādinājums darbu", "uzraksti atgādinājuma uzdevumu")
        out = out.replace("Ātrie klientu darbi skati:", "Ātrie klientu skati:")
        out = out.replace("sales klientu pārskats", "klientu pārskats")
        out = out.replace("Sales klientu pārskats", "Klientu pārskats")
    return out

