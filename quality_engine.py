"""
quality_engine.py
Nina Core Evolution 2.5 — Quality Engine

Šis modulis neatbild lietotājam tieši.
Tas pārbauda Ninas atbildi pirms nosūtīšanas:
- vai atbilde ir konkrēta;
- vai tā nav robotiska;
- vai tai ir nākamais solis;
- vai tā izmanto darbinieces principu.
"""

QUALITY_VERSION = "Quality Engine 2.5"


def _clean(value):
    return (value or "").strip()


def evaluate_answer(answer, context=None, thought=None):
    """Atgriež kvalitātes vērtējumu un labošanas ieteikumus."""
    context = context or {}
    thought = thought or {}
    answer = _clean(answer)
    lower = answer.lower()

    score = 100
    issues = []

    if not answer:
        score -= 80
        issues.append("empty_answer")

    weak_phrases = [
        "interesants jautājums",
        "pastāsti vairāk",
        "pastasti vairak",
        "esmu tikai ai",
        "kā ai modelis",
        "ka ai modelis",
        "nevaru palīdzēt bez vairāk informācijas",
        "pasaki, vai tas ir uzdevums, jautājums, ideja",
    ]
    for phrase in weak_phrases:
        if phrase in lower:
            score -= 20
            issues.append("robotic_or_weak_phrase")
            break

    if "nākamais" not in lower and "solis" not in lower:
        score -= 25
        issues.append("missing_next_step")

    if len(answer) < 80:
        score -= 15
        issues.append("too_short")

    if len(answer) > 1800:
        score -= 10
        issues.append("too_long")

    display_name = _clean(context.get("display_name"))
    if display_name and display_name != "kolēģi" and display_name.lower() not in lower:
        # Ne katrai atbildei vajag vārdu, bet identitātei jābūt redzamai biežāk.
        if thought.get("intent") in ["NEXT_STEP", "WORK", "MISSION", "RESPONSIBILITY"]:
            score -= 10
            issues.append("identity_not_used")

    if thought.get("intent") in ["MISTAKE", "QUALITY", "LEARNING"]:
        if not any(x in lower for x in ["iemāc", "nedrīkst", "labo", "mainu", "kļūd"]):
            score -= 20
            issues.append("no_learning_or_correction")

    score = max(0, min(100, score))
    status = "PASS" if score >= 80 else "REWRITE"
    return {
        "score": score,
        "status": status,
        "issues": issues,
        "version": QUALITY_VERSION,
    }


def improve_answer(answer, context=None, thought=None, review=None):
    """Drošs, vienkāršs atbildes uzlabotājs pirms nosūtīšanas."""
    context = context or {}
    thought = thought or {}
    review = review or evaluate_answer(answer, context, thought)
    answer = _clean(answer)

    if not answer:
        answer = "Es sapratu. Tagad jādod skaidrs, praktisks nākamais solis."

    lower = answer.lower()

    if "pasaki, vai tas ir uzdevums, jautājums, ideja" in lower:
        answer = (
            f"{context.get('display_name') or 'kolēģi'}, šo vēl neuztveršu kā parastu čatu.\n\n"
            "Man jānoskaidro īstais nodoms un jādod praktisks virziens, nevis jāliek tev pašam klasificēt tekstu.\n\n"
            "Nākamais solis: uzraksti vienu konkrētu rezultātu, ko gribi panākt, un es to sadalīšu darba soļos."
        )

    if "missing_next_step" in review.get("issues", []):
        answer = answer.rstrip() + "\n\nNākamais solis: izvēlamies vienu konkrētu darbu un virzām to līdz pārbaudāmam rezultātam."

    if "robotic_or_weak_phrase" in review.get("issues", []):
        answer = answer.replace("Interesants jautājums.", "Sapratu.")
        answer = answer.replace("Pastāsti vairāk", "Dod man vienu konkrētu detaļu")
        answer = answer.replace("pastāsti vairāk", "dod man vienu konkrētu detaļu")

    return answer


def format_quality_review(review):
    issues = review.get("issues") or []
    if not issues:
        issue_text = "nav kritisku problēmu"
    else:
        issue_text = ", ".join(issues)
    return (
        f"Quality score: {review.get('score', 0)}/100\n"
        f"Statuss: {review.get('status', 'UNKNOWN')}\n"
        f"Atrasts: {issue_text}\n"
        f"Versija: {review.get('version', QUALITY_VERSION)}"
    )
