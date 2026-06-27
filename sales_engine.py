"""
sales_engine.py
V20.0

Nina Smart Sales Engine

Ideja:
Nina nepārdod Premium uzreiz.
Viņa piedāvā Premium tikai tad, kad tas tiešām palīdz lietotājam.
"""

import random


class SalesEngine:

    def __init__(self):
        self.max_frequency = 5  # nepiedāvāt katrā ziņā

    def should_offer(
        self,
        memories=0,
        reminders=0,
        goals=0,
        user_messages=0,
        is_premium=False,
    ):

        if is_premium:
            return False

        if reminders >= 3:
            return True

        if memories >= 5:
            return True

        if goals >= 3:
            return True

        if user_messages >= 25:
            return True

        return False

    def build_offer(
        self,
        memories=0,
        reminders=0,
        goals=0,
    ):

        offers = []

        if reminders >= 3:
            offers.append(
                "💡 Starp citu... redzu, ka bieži izmanto atgādinājumus. "
                "Premium režīmā es varu palīdzēt tos pārvaldīt daudz plašāk."
            )

        if memories >= 5:
            offers.append(
                "🧠 Es jau atceros diezgan daudz lietu. "
                "Premium ļauj man paturēt prātā vēl vairāk."
            )

        if goals >= 3:
            offers.append(
                "🎯 Redzu, ka tev patīk plānot. "
                "Premium palīdz sekot mērķiem daudz ērtāk."
            )

        if not offers:
            offers.append(
                "✨ Ja kādreiz gribēsi, lai es kļūstu par pilnvērtīgu ikdienas palīgu, "
                "vari apskatīt Premium iespējas."
            )

        ending = random.choice([
            "😊 Bet nesteidzies. Vispirms pamēģini mani.",
            "😉 Izlem tikai tad, kad sajutīsi, ka tas tev tiešām noder.",
            "💙 Man svarīgāk ir palīdzēt, nevis pārdot."
        ])

        return random.choice(offers) + "\n\n" + ending


sales_engine = SalesEngine()
