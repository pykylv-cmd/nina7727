"""
learning_engine.py
Nina Core Evolution 2.4 — Learning Engine

Šis modulis neatbild viens pats uz visiem lietotāja jautājumiem.
Tas dod Employee Brain strukturētu mācīšanās protokolu:
- ko Nina iemācījās;
- ko nedrīkst atkārtot;
- kā jāmaina nākamā rīcība.
"""

LEARNING_VERSION = "Learning Engine 2.4"


def learning_principles():
    return [
        "Kļūdu uztvert kā darba kvalitātes signālu, nevis kā apvainojumu.",
        "Vispirms noteikt nodomu ar Think Engine, tikai pēc tam veidot atbildi.",
        "Neatkārtot vecus soļus, ja tie jau ir izdarīti.",
        "Vienmēr dot praktisku nākamo soli.",
        "Atmiņu un identitāti izmantot tikai tad, kad tas palīdz lietotājam, nevis mehāniski.",
        "NinaOS misiju turēt virs atsevišķām funkcijām.",
    ]


def current_learning_focus():
    return (
        "Core 2.4 mācīšanās fokuss: Nina vairs nedrīkst tikai atzīt kļūdu. "
        "Viņai jāpasaka, ko tieši no kļūdas iemācījās un kā tas mainīs nākamo rīcību."
    )


def build_learning_snapshot(intent="GENERAL", issue=""):
    intent = (intent or "GENERAL").strip().upper()
    issue = (issue or "").strip()

    if intent == "MISTAKE":
        learned = "Kļūdas jautājums jāmaršrutē uz MISTAKE, nevis uz vispārīgu sarunu."
        avoid = "Nedrīkst slēpties aiz frāzes 'es sapratu', ja cilvēks prasa konkrētu kļūdu."
        next_behavior = "Atbildēt ar konkrētu kļūdu, cēloni, labošanas soli un pārbaudes testu."
    elif intent == "QUALITY":
        learned = "Kritika par Ninu ir kvalitātes signāls, nevis lietotāja slikts garastāvoklis."
        avoid = "Nedrīkst prasīt lieku emocionālu skaidrojumu, ja cilvēks norāda uz produkta kvalitāti."
        next_behavior = "Atzīt kvalitātes problēmu un piedāvāt tiešu labojuma virzienu."
    elif intent == "NEXT_STEP":
        learned = "Nākamais solis nedrīkst atkārtot jau pabeigtu darbu."
        avoid = "Nedrīkst teikt 'pieslēdzam employee_brain.py', ja tas jau ir pieslēgts."
        next_behavior = "Dot aktuālo nākamo sprinta soli, balstoties uz pašreizējo Core stāvokli."
    else:
        learned = "Katra ziņa vispirms jāklasificē pēc nodoma."
        avoid = "Nedrīkst uzreiz ģenerēt tekstu bez domāšanas slāņa."
        next_behavior = "Vispirms Think Engine, tad Employee Brain, tad kvalitātes pārbaude."

    return {
        "intent": intent,
        "issue": issue,
        "learned": learned,
        "avoid": avoid,
        "next_behavior": next_behavior,
        "focus": current_learning_focus(),
        "principles": learning_principles(),
        "version": LEARNING_VERSION,
    }


def format_learning_snapshot(snapshot):
    snapshot = snapshot or build_learning_snapshot()
    principles = snapshot.get("principles") or []
    principle_lines = "\n".join([f"{i + 1}. {p}" for i, p in enumerate(principles[:4])])

    return (
        f"Ko es iemācījos: {snapshot.get('learned')}\n\n"
        f"Ko nedrīkstu atkārtot: {snapshot.get('avoid')}\n\n"
        f"Kā mainu nākamo rīcību: {snapshot.get('next_behavior')}\n\n"
        "Mācīšanās principi:\n"
        f"{principle_lines}"
    )
