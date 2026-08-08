"""Deterministic, fail-closed intent resolution for the ONE NINA Developer surface."""

DEVELOPER_INTENTS = (
    "repository_analysis", "ui_analysis", "architecture_analysis", "risk_analysis",
    "code_search", "diff_request", "release_request",
)


def developer_intents(command):
    normalized = " ".join(str(command or "").strip().casefold().split())
    tokens = set(normalized.replace(":", " ").replace(",", " ").replace(".", " ").split())
    found = []

    def add(intent, condition):
        if condition and intent not in found:
            found.append(intent)

    analytical = any(term in normalized for term in (
        "analiz", "izskaidro", "parādi", "show", "explain", "review", "uzlab",
    ))
    add("repository_analysis", analytical and any(term in normalized for term in (
        "repository", "repo", "projekta fail", "koda bāz",
    )))
    add("ui_analysis", analytical and any(term in normalized for term in (
        " ui", "interfeis", "developer console", "statusu kart", "status card", "lapa",
    )))
    add("architecture_analysis", any(term in normalized for term in (
        "arhitekt", "architecture", "call chain", "message flow", "plūsma", "moduļi", "modules",
    )) or (
        "developer" in normalized and "web research" in normalized
        and any(term in normalized for term in ("kāpēc", "kapec", "why"))
    ))
    add("risk_analysis", any(term in normalized for term in (
        "risks", "riskanti", "risk analysis", "blakusefekt", "side effect", "regresij",
    )))
    add("code_search", (
        any(term in normalized for term in ("atrodi", "meklē", "search", "find", "kur tiek defin", "where is"))
        and any(term in normalized for term in ("kod", "defin", "funkc", "class", "fail", "send_message_to_nina"))
    ))
    add("diff_request", any(term in normalized for term in (
        "diff", "patch", "izmaiņu priekšlik", "proposed change", "sagatavo laboj",
        "prepare change", "sagatavo minim", "minimālo drošo risinājumu",
    )))
    add("release_request", bool(tokens & {
        "release", "deploy", "deployment", "commit", "push", "izlaid", "deployo", "commitot", "pushot",
    }))
    return tuple(intent for intent in DEVELOPER_INTENTS if intent in found)
