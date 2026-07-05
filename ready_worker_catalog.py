"""
ready_worker_catalog.py
NinaOS Phase 3 — Ready Worker Catalog V1

Mērķis:
- nevis ļaut klientam būvēt botu no nulles;
- dot klientam gatavu AI darbinieku katalogu;
- sasaistīt gatavu darbinieku ar RolePack, kanāliem, pricing tipu,
  setup datiem, approval profilu un Exchange gatavību.

Galvenais likums:
Klients neizveido botu. Klients izvēlas un saņem gatavu AI darbinieku.
"""

READY_WORKER_CATALOG_VERSION = "NinaOS Ready Worker Catalog V1"


def _clean(value):
    return str(value or "").strip()


def _lower(value):
    return _clean(value).lower()


def _contains_any(text, parts):
    lower = _lower(text)
    return any(p in lower for p in parts)


READY_WORKERS = {
    "worker_accountant": {
        "id": "worker_accountant",
        "name": "Nina Grāmatvede",
        "category": "finance",
        "risk_level": "high",
        "summary": "Gatavs AI grāmatvedības asistents dokumentu apkopošanai, rēķinu šķirošanai un atskaišu melnrakstiem.",
        "best_for": ["mazie uzņēmumi", "pašnodarbinātie", "biroji", "privātpersonas ar dokumentiem"],
        "roles": ["role_accountant", "role_document_assistant"],
        "channels": ["web", "mobile", "telegram", "email"],
        "plans": ["basic", "pro", "business", "enterprise"],
        "required_setup": [
            "uzņēmuma vai personas pamatinformācija",
            "rēķini / čeki / bankas izraksti",
            "atskaišu periods",
            "grāmatvedības noteikumi / cilvēka kontroles persona",
        ],
        "core_jobs": [
            "apkopo rēķinus un čekus",
            "atrod trūkstošus dokumentus",
            "sagatavo atskaites melnrakstu",
            "uzdod jautājumus, ja dokumenti nav pietiekami",
        ],
        "approval_profile": "high — oficiālas iesniegšanas, nodokļu lēmumi un maksājumi tikai ar cilvēka apstiprinājumu",
        "exchange": {
            "can_publish": False,
            "can_buy": True,
            "can_sell": False,
            "notes": "Var pirkt specializētu dokumentu pārbaudi ar minimālu datu nodošanu un approval.",
        },
    },
    "worker_estimator": {
        "id": "worker_estimator",
        "name": "Nina Tāmētāja",
        "category": "construction",
        "risk_level": "medium",
        "summary": "Gatavs AI tāmēšanas asistents darbu aprakstiem, bildēm, apjomiem, materiāliem un piedāvājuma melnrakstiem.",
        "best_for": ["celtniecība", "fasādes", "remontdarbi", "meistari", "būvfirmas"],
        "roles": ["role_estimator", "role_offer_builder"],
        "channels": ["web", "mobile", "telegram", "whatsapp"],
        "plans": ["basic", "pro", "business"],
        "required_setup": [
            "darbu veidi un cenu politika",
            "materiālu / darba pozīciju piemēri",
            "projekta bildes, PDF, Excel vai izmēri",
            "noteikumi par gala cenas apstiprināšanu",
        ],
        "core_jobs": [
            "sagatavo tāmes struktūru",
            "uzdod trūkstošo izmēru jautājumus",
            "veido materiālu un darbu pozīcijas",
            "sagatavo piedāvājuma melnrakstu klientam",
        ],
        "approval_profile": "medium — gala cena, atlaides un saistošs piedāvājums tikai ar approval",
        "exchange": {
            "can_publish": True,
            "can_buy": True,
            "can_sell": True,
            "notes": "Var pirkt juridisku pārbaudi un pārdot tāmes review pakalpojumu Exchange ar atļaujām.",
        },
    },
    "worker_sales": {
        "id": "worker_sales",
        "name": "Nina Pārdevēja",
        "category": "sales",
        "risk_level": "medium",
        "summary": "Gatavs AI pārdošanas darbinieks klientu sarunām, piedāvājumiem, follow-up, objection handling un closing.",
        "best_for": ["pakalpojumu uzņēmumi", "meistari", "B2B pārdošana", "mazie uzņēmumi"],
        "roles": ["role_sales", "role_followup", "role_objection_closer"],
        "channels": ["telegram", "whatsapp", "web", "mobile", "email"],
        "plans": ["basic", "pro", "business", "enterprise"],
        "required_setup": [
            "pakalpojumi un cenas",
            "klientu saraksts vai pipeline",
            "sarunas tonis",
            "piedāvājumu un follow-up noteikumi",
        ],
        "core_jobs": [
            "sagatavo piedāvājumus",
            "seko klientiem",
            "sagatavo zvana plānus",
            "atbild uz iebildumiem un virza uz closing",
        ],
        "approval_profile": "medium — atlaides, saistoši solījumi un ārēja nosūtīšana pēc workspace noteikumiem",
        "exchange": {
            "can_publish": True,
            "can_buy": True,
            "can_sell": True,
            "notes": "Var pirkt lead enrichment / juridisku review un pārdot sales follow-up pakalpojumus.",
        },
    },
    "worker_legal": {
        "id": "worker_legal",
        "name": "Nina Jurista palīgs",
        "category": "legal",
        "risk_level": "high",
        "summary": "Gatavs AI juridiskais palīgs līgumu lasīšanai, risku izcelšanai un dokumentu melnrakstiem cilvēka pārbaudei.",
        "best_for": ["uzņēmumi", "pašnodarbinātie", "līgumu pārbaude", "iekšējā dokumentācija"],
        "roles": ["role_legal_assistant", "role_contract_review"],
        "channels": ["web", "mobile", "email"],
        "plans": ["pro", "business", "enterprise"],
        "required_setup": [
            "juridiskie dokumenti",
            "jurisdikcijas / valsts noteikums",
            "riska politika",
            "cilvēka apstiprinātājs",
        ],
        "core_jobs": [
            "lasa līgumus",
            "izceļ riskus",
            "sagatavo jautājumus",
            "sagatavo melnrakstus cilvēka pārbaudei",
        ],
        "approval_profile": "high — gala juridiska atbilde, iesniegšana vai līguma nosūtīšana tikai ar approval",
        "exchange": {
            "can_publish": False,
            "can_buy": False,
            "can_sell": True,
            "notes": "Var sniegt review pakalpojumu Exchange tikai ar skaidru scope, minimāliem datiem un audit log.",
        },
    },
    "worker_hr": {
        "id": "worker_hr",
        "name": "Nina HR",
        "category": "people",
        "risk_level": "medium",
        "summary": "Gatavs AI HR asistents kandidātu šķirošanai, interviju jautājumiem, onboarding un iekšējo procedūru FAQ.",
        "best_for": ["mazie uzņēmumi", "personāla atlase", "onboarding", "iekšējā dokumentācija"],
        "roles": ["role_hr", "role_onboarding_assistant"],
        "channels": ["web", "mobile", "email", "telegram"],
        "plans": ["basic", "pro", "business"],
        "required_setup": [
            "vakances apraksts",
            "iekšējās procedūras",
            "kandidātu CV / pieteikumi",
            "interviju noteikumi",
        ],
        "core_jobs": [
            "sagatavo interviju jautājumus",
            "palīdz šķirot kandidātus",
            "veido onboarding checklist",
            "atbild uz iekšējiem FAQ",
        ],
        "approval_profile": "medium — darba piedāvājumi, atteikumi un sensitīvi HR lēmumi ar cilvēka approval",
        "exchange": {
            "can_publish": True,
            "can_buy": True,
            "can_sell": False,
            "notes": "Var pirkt CV review vai juridisku HR dokumenta pārbaudi ar datu minimizāciju.",
        },
    },
    "worker_project_coordinator": {
        "id": "worker_project_coordinator",
        "name": "Nina Projektu koordinators",
        "category": "operations",
        "risk_level": "medium",
        "summary": "Gatavs AI projektu koordinators termiņiem, taskiem, riskiem un statusa pārskatiem.",
        "best_for": ["projekti", "servisa komandas", "būvniecība", "operācijas"],
        "roles": ["role_project_coordinator", "role_task_manager"],
        "channels": ["web", "mobile", "telegram", "email"],
        "plans": ["basic", "pro", "business", "enterprise"],
        "required_setup": [
            "projekta mērķi",
            "tasku saraksts",
            "komandas dalībnieki",
            "termiņi un riska noteikumi",
        ],
        "core_jobs": [
            "seko termiņiem",
            "veido statusa pārskatu",
            "brīdina par riskiem",
            "iesaka nākamo soli",
        ],
        "approval_profile": "medium — resursu izmaiņas, ārēja komunikācija un augsta riska lēmumi ar approval",
        "exchange": {
            "can_publish": True,
            "can_buy": True,
            "can_sell": True,
            "notes": "Var nodot specializētus apakšdarbus citiem botiem caur Exchange.",
        },
    },
    "worker_support": {
        "id": "worker_support",
        "name": "Nina Klientu serviss",
        "category": "support",
        "risk_level": "medium",
        "summary": "Gatavs AI klientu servisa darbinieks jautājumiem, ticketiem, FAQ un eskalācijām cilvēkam.",
        "best_for": ["e-komercija", "pakalpojumi", "klientu atbalsts", "FAQ"],
        "roles": ["role_customer_support", "role_ticket_triage"],
        "channels": ["web", "mobile", "telegram", "whatsapp", "email"],
        "plans": ["basic", "pro", "business", "enterprise"],
        "required_setup": [
            "FAQ",
            "pakalpojumu noteikumi",
            "sūdzību eskalācijas noteikumi",
            "atļautās kompensācijas / atbildes",
        ],
        "core_jobs": [
            "atbild uz biežiem jautājumiem",
            "šķiro sūdzības",
            "veido ticketus",
            "eskalē cilvēkam, ja risks ir augsts",
        ],
        "approval_profile": "medium — kompensācijas, juridiski solījumi un konfliktsituācijas ar approval",
        "exchange": {
            "can_publish": True,
            "can_buy": True,
            "can_sell": False,
            "notes": "Var pirkt specializētu juridisku vai tehnisku review, bet nedrīkst iznest klienta datus bez atļaujas.",
        },
    },
    "worker_office_manager": {
        "id": "worker_office_manager",
        "name": "Nina Office Manager",
        "category": "multi_role",
        "risk_level": "medium",
        "summary": "Gatavs vairāku amatu AI biroja darbinieks ikdienas taskiem, klientiem, dokumentiem un koordinācijai.",
        "best_for": ["mazie uzņēmumi", "privātpersonas", "biroja darbs", "ikdienas koordinācija"],
        "roles": ["role_sales", "role_followup", "role_project_coordinator", "role_document_assistant"],
        "channels": ["telegram", "web", "mobile", "email", "whatsapp"],
        "plans": ["pro", "business", "enterprise"],
        "required_setup": [
            "uzņēmuma pamatinformācija",
            "pakalpojumi un klienti",
            "tasku / dokumentu piekļuve",
            "approval noteikumi katram amatam",
        ],
        "core_jobs": [
            "sakārto dienu",
            "seko klientiem",
            "sagatavo ziņas",
            "palīdz ar dokumentiem un projektiem",
        ],
        "approval_profile": "medium — multi-role robežas jāņem no katra piesaistītā RolePack",
        "exchange": {
            "can_publish": False,
            "can_buy": True,
            "can_sell": False,
            "notes": "Var pirkt apakšpakalpojumus Exchange, bet nav paredzēta kā publisks speciālists.",
        },
    },
}


ALIASES = {
    "grāmatvede": "worker_accountant",
    "gramatvede": "worker_accountant",
    "grāmatvedis": "worker_accountant",
    "gramatvedis": "worker_accountant",
    "accountant": "worker_accountant",
    "tāmētāja": "worker_estimator",
    "tametaja": "worker_estimator",
    "tāmētājs": "worker_estimator",
    "tametajs": "worker_estimator",
    "estimator": "worker_estimator",
    "pārdevēja": "worker_sales",
    "pardeveja": "worker_sales",
    "pārdevējs": "worker_sales",
    "pardevejs": "worker_sales",
    "sales": "worker_sales",
    "jurists": "worker_legal",
    "jurista": "worker_legal",
    "legal": "worker_legal",
    "hr": "worker_hr",
    "projektu koordinators": "worker_project_coordinator",
    "koordinators": "worker_project_coordinator",
    "klientu serviss": "worker_support",
    "support": "worker_support",
    "office manager": "worker_office_manager",
    "biroja vadītāja": "worker_office_manager",
    "biroja vaditaja": "worker_office_manager",
}


def _worker_by_id(worker_id):
    return READY_WORKERS.get(worker_id or "")


def find_worker(text):
    lower = _lower(text)
    for alias, worker_id in sorted(ALIASES.items(), key=lambda x: len(x[0]), reverse=True):
        if alias in lower:
            return _worker_by_id(worker_id)
    # direct name fallback
    for worker in READY_WORKERS.values():
        if worker["name"].lower() in lower:
            return worker
    return None


def _format_list(items):
    return "\n".join(f"• {x}" for x in (items or []))


def _exchange_label(worker):
    ex = worker.get("exchange", {})
    parts = []
    if ex.get("can_publish"):
        parts.append("publicējams")
    if ex.get("can_buy"):
        parts.append("var pirkt")
    if ex.get("can_sell"):
        parts.append("var pārdot")
    return ", ".join(parts) if parts else "ierobežots"


def worker_status_answer():
    return (
        "🧑‍💼 NinaOS Ready Worker Catalog V1 ir aktīvs. ✅\n\n"
        "Ko tas dara:\n"
        "• rāda gatavus AI darbiniekus, ko klients izvēlas un saņem;\n"
        "• sasaista darbinieku ar RolePack, kanāliem, setup datiem, approval profilu un Exchange tiesībām;\n"
        "• nostiprina principu: klients nebūvē botu no nulles — klients saņem gatavu darbinieku.\n\n"
        "Komandas:\n"
        "• worker status\n"
        "• workers / darbinieki\n"
        "• parādi darbinieku Nina Tāmētāja\n"
        "• kādus darbus dara Nina Pārdevēja\n"
        "• kuri darbinieki ir būvniecībai\n"
        "• kuri darbinieki ir finance\n"
        "• vai Nina Jurista palīgs ir exchange-ready\n\n"
        f"Versija: {READY_WORKER_CATALOG_VERSION}"
    )


def workers_catalog_answer(category=None):
    category = _clean(category)
    workers = list(READY_WORKERS.values())
    if category:
        workers = [w for w in workers if w["category"] == category or category in w.get("best_for", [])]

    if not workers:
        return f"🧑‍💼 Ready Worker Catalog\n\nŠajā kategorijā vēl nav darbinieku.\n\nVersija: {READY_WORKER_CATALOG_VERSION}"

    lines = [
        "🧑‍💼 Gatavo AI darbinieku katalogs V1",
        "",
        "Šie nav tukši boti. Tie ir gatavi AI darbinieki, ko klients izvēlas un saņem.",
        "",
    ]
    for i, worker in enumerate(workers, 1):
        lines.append(f"{i}. {worker['name']} — {worker['category']} — risks: {worker['risk_level']}")
        lines.append(f"   {worker['summary']}")
        lines.append(f"   RolePack: {', '.join(worker['roles'])}")
        lines.append(f"   Kanāli: {', '.join(worker['channels'])}")
        lines.append(f"   Exchange: {_exchange_label(worker)}")
        lines.append("")
    lines.append(f"Versija: {READY_WORKER_CATALOG_VERSION}")
    return "\n".join(lines)


def worker_detail_answer(worker):
    if not worker:
        return (
            "🧑‍💼 Ready Worker Catalog\n\n"
            "Pasaki, kuru gatavo AI darbinieku parādīt.\n\n"
            "Piemēri:\n"
            "• parādi darbinieku Nina Tāmētāja\n"
            "• parādi darbinieku Nina Grāmatvede\n"
            "• parādi darbinieku Nina Pārdevēja\n\n"
            f"Versija: {READY_WORKER_CATALOG_VERSION}"
        )

    ex = worker.get("exchange", {})
    lines = [
        f"🧑‍💼 Gatavs AI darbinieks — {worker['name']}",
        "",
        f"ID: {worker['id']}",
        f"Kategorija: {worker['category']}",
        f"Riska līmenis: {worker['risk_level']}",
        "",
        f"Apraksts: {worker['summary']}",
        "",
        "Kam der:",
        _format_list(worker.get("best_for")),
        "",
        "Piesaistītie RolePack:",
        _format_list(worker.get("roles")),
        "",
        "Galvenie darbi:",
        _format_list(worker.get("core_jobs")),
        "",
        "Atbalstītie kanāli:",
        _format_list(worker.get("channels")),
        "",
        "Plāni:",
        _format_list(worker.get("plans")),
        "",
        "Ko klientam jāiedod sākumā:",
        _format_list(worker.get("required_setup")),
        "",
        f"Approval profils: {worker.get('approval_profile')}",
        "",
        "Exchange statuss:",
        f"• publicējams: {'jā' if ex.get('can_publish') else 'nē'}",
        f"• var pirkt pakalpojumus: {'jā' if ex.get('can_buy') else 'nē'}",
        f"• var pārdot pakalpojumus: {'jā' if ex.get('can_sell') else 'nē'}",
        f"• piezīme: {ex.get('notes')}",
        "",
        "Likums:",
        "• klients šo darbinieku neizveido no nulles;",
        "• klients izvēlas gatavu darbinieku un dod viņam darbu, datus, failus, kanālus un atļaujas.",
        "",
        f"Versija: {READY_WORKER_CATALOG_VERSION}",
    ]
    return "\n".join(lines)


def worker_jobs_answer(worker):
    if not worker:
        return worker_detail_answer(None)
    return (
        f"🧑‍💼 Kādi darbi — {worker['name']}\n\n"
        f"Mērķis: {worker['summary']}\n\n"
        "Galvenie darbi:\n"
        f"{_format_list(worker.get('core_jobs'))}\n\n"
        "Ko vajag sākumā:\n"
        f"{_format_list(worker.get('required_setup'))}\n\n"
        f"Versija: {READY_WORKER_CATALOG_VERSION}"
    )


def worker_category_answer(text):
    lower = _lower(text)
    mapping = {
        "būvniec": "construction",
        "buvniec": "construction",
        "construction": "construction",
        "finance": "finance",
        "finans": "finance",
        "grāmat": "finance",
        "gramat": "finance",
        "legal": "legal",
        "jurid": "legal",
        "sales": "sales",
        "pārdo": "sales",
        "pardo": "sales",
        "support": "support",
        "serviss": "support",
        "hr": "people",
        "people": "people",
        "operations": "operations",
        "projek": "operations",
    }
    for key, category in mapping.items():
        if key in lower:
            return workers_catalog_answer(category)
    return workers_catalog_answer()


def worker_exchange_answer(worker):
    if not worker:
        return worker_detail_answer(None)
    ex = worker.get("exchange", {})
    status = []
    status.append(f"publicējams Exchange: {'jā' if ex.get('can_publish') else 'nē'}")
    status.append(f"var pirkt pakalpojumus: {'jā' if ex.get('can_buy') else 'nē'}")
    status.append(f"var pārdot pakalpojumus: {'jā' if ex.get('can_sell') else 'nē'}")
    return (
        f"🔁 Exchange gatavība — {worker['name']}\n\n"
        + "\n".join(f"• {x}" for x in status)
        + f"\n\nPiezīme:\n{ex.get('notes')}\n\n"
        "Drošības likums:\n"
        "• ārpus workspace drīkst nodot tikai minimāli nepieciešamos datus;\n"
        "• sensitīvi dati un augsta riska darbi iet caur Permission + Approval + AuditLog.\n\n"
        f"Versija: {READY_WORKER_CATALOG_VERSION}"
    )


def is_ready_worker_command(text):
    lower = _lower(text)
    if lower in ["worker status", "ready worker status", "workers", "darbinieki", "worker catalog", "darbinieku katalogs"]:
        return True
    triggers = [
        "parādi darbinieku", "paradi darbinieku",
        "kādus darbus dara", "kadus darbus dara",
        "kuri darbinieki ir", "kādi darbinieki ir", "kadi darbinieki ir",
        "exchange-ready", "exchange ready",
        "vai nina",
    ]
    if any(t in lower for t in triggers) and find_worker(lower):
        return True
    if lower.startswith("kuri darbinieki") or lower.startswith("kādi darbinieki") or lower.startswith("kadi darbinieki"):
        return True
    return False


def build_ready_worker_answer(text):
    lower = _lower(text)
    if lower in ["worker status", "ready worker status", "worker catalog", "darbinieku katalogs"]:
        return worker_status_answer()
    if lower in ["workers", "darbinieki"]:
        return workers_catalog_answer()
    worker = find_worker(text)
    if "exchange-ready" in lower or "exchange ready" in lower or (lower.startswith("vai nina") and "exchange" in lower):
        return worker_exchange_answer(worker)
    if lower.startswith("kuri darbinieki") or lower.startswith("kādi darbinieki") or lower.startswith("kadi darbinieki"):
        return worker_category_answer(text)
    if _contains_any(lower, ["kādus darbus dara", "kadus darbus dara", "ko dara"]):
        return worker_jobs_answer(worker)
    if _contains_any(lower, ["parādi darbinieku", "paradi darbinieku", "parādi gatavu darbinieku", "paradi gatavu darbinieku"]):
        return worker_detail_answer(worker)
    if worker:
        return worker_detail_answer(worker)
    return workers_catalog_answer()
