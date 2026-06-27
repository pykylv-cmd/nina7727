
"""
relationship.py — V16.3

Nina AI Platform
Relationship Engine

Glabā vienkāršu informāciju par attiecību līmeni ar lietotāju.
Neatkarīgs no Telegram un datubāzes.
"""

from dataclasses import dataclass


@dataclass
class RelationshipState:
    messages: int = 0
    trust: int = 0
    first_seen: bool = True


def update_state(state: RelationshipState) -> RelationshipState:
    state.messages += 1

    if state.messages >= 3:
        state.first_seen = False

    if state.trust < 100:
        state.trust += 1

    return state


def greeting(state: RelationshipState) -> str:
    if state.first_seen:
        return (
            "Prieks iepazīties. 😊 "
            "Nesatraucies, man nav jārunā tikai par darbu. "
            "Vari ar mani runāt pavisam cilvēcīgi."
        )

    if state.messages < 10:
        return (
            "Prieks tevi atkal redzēt. 🙂 "
            "Kas šodien tev ir svarīgākais?"
        )

    return (
        "Sveiks! Patīkami, ka atgriezies. "
        "Turpinām no vietas, kur palikām. 😉"
    )


def relationship_debug(state: RelationshipState) -> str:
    return (
        "🤝 Relationship Engine\n\n"
        f"Ziņas: {state.messages}\n"
        f"Uzticība: {state.trust}\n"
        f"Pirmais kontakts: {state.first_seen}"
    )
