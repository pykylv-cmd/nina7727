"""
think_engine.py
Nina Core Evolution 2.5 — Think Engine

Šis fails neatbild lietotājam.
Tas tikai nosaka, kas patiesībā notiek lietotāja ziņā.
Employee Brain pēc tam izvēlas pareizo atbildes ceļu.
"""

THINK_VERSION = "Think Engine 2.5"


def _clean(text):
    return (text or "").strip()


def _lower(text):
    return _clean(text).lower()


def _contains_any(lower, phrases):
    return any(p in lower for p in phrases)


def classify_intent(text):
    """
    Atgriež strukturētu nodoma rezultātu.
    Think Engine NEKAD neveido gala atbildi lietotājam.
    """
    raw = _clean(text)
    lower = raw.lower()

    if not lower:
        return _result("EMPTY", raw, confidence=1.0, reason="Tukša ziņa")

    # 1) Statuss un Core komandas
    if lower in [
        "core", "core status", "employee status", "employee brain", "nina core",
        "core 2.0", "core 2.1", "core 2.2", "core 2.3", "core 2.4", "core 2.5", "quality engine", "quality status", "learning engine", "learning status", "core evolution",
        "think engine", "think status"
    ]:
        return _result("STATUS", raw, confidence=1.0, reason="Core statusa pieprasījums")

    # 2) Identitāte
    if _contains_any(lower, [
        "kā mani sauc", "ka mani sauc", "zini manu vārdu", "zini manu vardu",
        "vai tu zini manu vārdu", "vai tu zini manu vardu", "mans vārds", "mans vards",
        "atceries manu vārdu", "atceries manu vardu"
    ]):
        return _result("IDENTITY", raw, confidence=0.98, reason="Jautājums par lietotāja identitāti")

    # 3) Kļūdas analīze — jābūt pirms vispārīgas kritikas
    if _contains_any(lower, [
        "kur tu kļūdījies", "kur tu kludijies", "kā tu kļūdījies", "ka tu kludijies",
        "ko tu izdarīji nepareizi", "ko tu izdariji nepareizi",
        "kāda bija kļūda", "kada bija kluda", "kas bija kļūda", "kas bija kluda",
        "kļūdu analīze", "kludu analize"
    ]):
        return _result("MISTAKE", raw, confidence=0.99, reason="Lietotājs prasa konkrētu kļūdas atzīšanu/analīzi")

    # 4) Atbildība
    if _contains_any(lower, [
        "ko tu uzņemies", "ko tu uznemies", "uzņemies", "uznemies",
        "kas ir tavs uzdevums", "tavs uzdevums", "tava atbildība", "tava atbildiba",
        "paņem atbildību", "panem atbildibu", "par ko tu atbildi"
    ]):
        return _result("RESPONSIBILITY", raw, confidence=0.96, reason="Jautājums par Ninas atbildību")

    # 5) Misija / virziens
    if _contains_any(lower, [
        "ninaos misija", "ninaos mērķis", "ninaos merkis", "kāda ir misija", "kada ir misija",
        "mūsu misija", "musu misija", "projekta misija", "kas ir ninaos",
        "kāpēc ninaos", "kapec ninaos"
    ]):
        return _result("MISSION", raw, confidence=0.97, reason="Jautājums par NinaOS misiju")

    # 6) Nākamais solis / iniciatīva
    if _contains_any(lower, [
        "kas tālāk", "kas talak", "ko tālāk", "ko talak", "nākamais solis", "nakamais solis",
        "ko šodien darām", "ko sodien daram", "ko tu iesaki", "ko iesaki",
        "turpinām", "turpinam", "ejam tālāk", "ejam talak", "ko darām tagad", "ko daram tagad"
    ]):
        return _result("NEXT_STEP", raw, confidence=0.95, reason="Lietotājs prasa nākamo praktisko soli")

    # 7) Darba pieprasījums / būvēšana
    if _contains_any(lower, [
        "palīdzi būvēt", "palidzi buvet", "palīdzi uzbūvēt", "palidzi uzbuvet",
        "palīdzi", "palidzi", "vajag uztaisīt", "vajag uztaisit", "vajag pabeigt",
        "strādājam", "stradajam", "būvēt ninaos", "buvet ninaos", "taisam", "sākam", "sakam"
    ]):
        return _result("WORK", raw, confidence=0.88, reason="Lietotājs dod darba uzdevumu vai lūdz palīdzēt virzīt projektu")

    # 8) Kvalitātes/kritikas signāls
    if _contains_any(lower, [
        "tu esi robots", "kā robots", "ka robots", "garlaicīgi", "garlaicigi",
        "nepareizi", "slikti atbildi", "tev jāmācās", "tev jamacas", "nav labi",
        "šādi nedrīkst", "sadi nedrikst", "tu kļūdies", "tu kludies", "nerunā normāli", "neruna normali"
    ]):
        return _result("QUALITY", raw, confidence=0.93, reason="Kvalitātes komentārs par Ninas atbildi")

    # 9) Mācīšanās
    if _contains_any(lower, [
        "ko tu iemācījies", "ko tu iemacijies", "mācies", "macies", "iemācies", "iemacies",
        "kā tu mācies", "ka tu macies", "ko no tā mācies", "ko no ta macies",
        "ko nedrīksti atkārtot", "ko nedriksti atkartot", "kā mainīsi rīcību", "ka mainisi ricibu"
    ]):
        return _result("LEARNING", raw, confidence=0.90, reason="Jautājums par mācīšanos")

    # 10) Atmiņa
    if _contains_any(lower, [
        "ko tu atceries", "ko atceries", "atceries ka", "atceries, ka", "paturi prātā", "paturi prata"
    ]):
        return _result("MEMORY", raw, confidence=0.86, reason="Atmiņas jautājums vai atmiņas pieprasījums")

    # 11) Vision
    if _contains_any(lower, [
        "bilde", "foto", "attēls", "attels", "apskati šo", "apskati so", "ko redzi"
    ]):
        return _result("VISION", raw, confidence=0.80, reason="Iespējams attēla/vision pieprasījums")

    return _result("GENERAL", raw, confidence=0.50, reason="Nav atrasts specifisks Core nodoms")


def _result(intent, raw, confidence=0.5, reason=""):
    return {
        "intent": intent,
        "raw_text": raw,
        "confidence": float(confidence),
        "reason": reason,
        "version": THINK_VERSION,
    }
