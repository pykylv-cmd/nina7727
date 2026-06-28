"""
vision_engine.py — V23.0

Nina AI Platform Vision Engine

Mērķis:
- Nina saprot Telegram bildes;
- var aprakstīt, kas redzams;
- var palīdzēt ar darbu, dokumentiem, celtniecību, ikdienu;
- vēlāk šo izmantos arī Tāmētājs, Juris un citi AI darbinieki.
"""

import base64


def image_to_base64(image_bytes: bytes) -> str:
    return base64.b64encode(image_bytes).decode("utf-8")


def build_vision_prompt(user_caption: str = "") -> str:
    caption = (user_caption or "").strip()

    base = (
        "Tu esi Nina — draudzīga AI asistente. "
        "Lietotājs atsūtīja bildi. "
        "Atbildi latviski, cilvēcīgi un praktiski. "
        "Apraksti, ko redzi bildē, un piedāvā nākamo soli. "
        "Ja bildē ir dokuments, teksts, būvniecība, defekts, prece, vieta vai situācija, "
        "palīdzi saprast, ko ar to darīt. "
        "Nedod medicīnisku, juridisku vai finanšu garantiju. "
        "Ja neesi pārliecināta, pasaki to godīgi. "
    )

    if caption:
        base += f" Lietotāja piebilde pie bildes: {caption}"

    return base


def build_no_vision_fallback(version="V23.0") -> str:
    return (
        "Es redzu, ka atsūtīji bildi. 😊\n\n"
        "Šobrīd man vēl nav ieslēgta pilna attēlu saprašana šajā vidē, "
        "bet mēs to jau pieslēdzam.\n\n"
        "Kad Vision būs aktīvs, varēšu pateikt, kas redzams bildē, "
        "palīdzēt ar dokumentiem, darbiem, defektiem, tāmes materiāliem un citām lietām.\n\n"
        f"Versija: {version}"
    )


def build_vision_answer_from_openai(client, image_bytes: bytes, caption: str = "", version="V23.0") -> str:
    """
    Izmanto OpenAI vision modeli.
    Vajag, lai app.py padod:
    - client = OpenAI(...)
    - image_bytes no Telegram foto
    """
    try:
        image_b64 = image_to_base64(image_bytes)
        prompt = build_vision_prompt(caption)

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Tu esi Nina, latviski runājoša AI asistente. "
                        "Esi silta, praktiska, īsa un noderīga."
                    )
                },
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{image_b64}"
                            }
                        }
                    ]
                }
            ],
            max_tokens=700,
        )

        answer = response.choices[0].message.content.strip()

        if "Versija:" not in answer:
            answer += f"\n\nVersija: {version}"

        return answer

    except Exception as e:
        print("Vision Engine kļūda:", e)
        return build_no_vision_fallback(version=version)


def build_photo_received_answer(version="V23.0") -> str:
    return (
        "Bildīti saņēmu. 😊\n\n"
        "Tūlīt paskatīšos, kas tur redzams.\n\n"
        f"Versija: {version}"
    )
