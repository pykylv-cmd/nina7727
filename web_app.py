# web_app.py
# NinaOS Web App V42 CLEAN MERGE — V40 Console + V41 Actions
# Web service start command: python web_app.py
# Telegram service start command stays: python app.py

import os
from datetime import datetime
from flask import Flask, Response, redirect, request

WEB_APP_VERSION = "Web App V42 CLEAN MERGE — V40 Console + V41 Actions"
app = Flask(__name__)

# web_app.py
# NinaOS Web App V43 — Form Save to Workspace Preview / DB Bridge
# Web service start command: python web_app.py
# Telegram service start command stays: python app.py

import os
from datetime import datetime
from flask import Flask, Response, redirect, request

WEB_APP_VERSION = "Web App V43 — Form Save to Workspace Preview / DB Bridge"
app = Flask(__name__)

# V43 safe in-memory workspace preview store.
# This does NOT write to Postgres yet and does NOT touch Telegram app.py.
WORKSPACE_ACTION_PREVIEWS = []


def safe_int(value, default=0):
    try:
        return int(value)
    except Exception:
        return default


def html_escape(s):
    return str(s or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def current_language():
    lang = (request.args.get("lang") or "en").strip().lower()
    return lang if lang in ["en", "lv", "ru"] else "en"


def q(path):
    return f"{path}?lang={current_language()}"


def tx(key, lang=None):
    lang = lang or current_language()
    d = {
        "search": {"en": "Search anything...", "lv": "Meklēt jebko...", "ru": "Искать..."},
        "dashboard": {"en": "Dashboard", "lv": "Panelis", "ru": "Панель"},
        "workers": {"en": "Workers", "lv": "Darbinieki", "ru": "Работники"},
        "tasks": {"en": "Tasks", "lv": "Uzdevumi", "ru": "Задачи"},
        "clients": {"en": "Clients", "lv": "Klienti", "ru": "Клиенты"},
        "projects": {"en": "Projects", "lv": "Projekti", "ru": "Проекты"},
        "calendar": {"en": "Calendar", "lv": "Kalendārs", "ru": "Календарь"},
        "files": {"en": "Files", "lv": "Faili", "ru": "Файлы"},
        "analytics": {"en": "Analytics", "lv": "Analītika", "ru": "Аналитика"},
        "exchange": {"en": "Exchange", "lv": "Birža", "ru": "Биржа"},
        "good_morning": {"en": "Good morning, Katrin 👋", "lv": "Labrīt, Katrin 👋", "ru": "Доброе утро, Katrin 👋"},
        "workspace_today": {
            "en": "Here’s what needs attention in your NinaOS workspace today.",
            "lv": "Šeit ir tas, kam šodien jāpievērš uzmanība NinaOS darba vidē.",
            "ru": "Вот что сегодня требует внимания в рабочем пространстве NinaOS.",
        },
        "hero_line": {
            "en": "One Platform. Unlimited AI Workers.<br>For every business. Everywhere.",
            "lv": "Viena platforma. Neierobežoti AI darbinieki.<br>Katram biznesam. Visur.",
            "ru": "Одна платформа. Неограниченные AI-работники.<br>Для любого бизнеса. Везде.",
        },
        "open_work": {"en": "Open Work Queue", "lv": "Atvērt darbu rindu", "ru": "Открыть задачи"},
        "explore": {"en": "Explore Exchange", "lv": "Apskatīt biržu", "ru": "Открыть биржу"},
        "global": {"en": "Global AI Workforce", "lv": "Globālais AI darbaspēks", "ru": "Глобальная AI-команда"},
        "connected": {"en": "Connected. Intelligent. Tireless.", "lv": "Savienots. Gudrs. Nenogurstošs.", "ru": "Связано. Умно. Без усталости."},
        "your_workers": {"en": "Your AI Workforce", "lv": "Tavi AI darbinieki", "ru": "Твои AI-работники"},
        "recent": {"en": "Recent Activity", "lv": "Pēdējā aktivitāte", "ru": "Последняя активность"},
        "snapshot": {"en": "Workspace Snapshot", "lv": "Darba vides pārskats", "ru": "Снимок рабочей среды"},
        "tasks_today": {"en": "Tasks Today", "lv": "Šodienas uzdevumi", "ru": "Задачи сегодня"},
        "followups": {"en": "Follow-ups", "lv": "Atkārtoti kontakti", "ru": "Повторные контакты"},
        "invoices": {"en": "Invoices", "lv": "Rēķini", "ru": "Счета"},
        "projects_kpi": {"en": "Projects", "lv": "Projekti", "ru": "Проекты"},
        "open_work_label": {"en": "Open work", "lv": "Atvērts darbs", "ru": "Открытая работа"},
        "need_attention": {"en": "Need attention", "lv": "Jāpievērš uzmanība", "ru": "Требует внимания"},
        "finance": {"en": "Finance", "lv": "Finanses", "ru": "Финансы"},
        "active": {"en": "Active", "lv": "Aktīvs", "ru": "Активно"},
        "view_global": {"en": "View Global Network →", "lv": "Skatīt globālo tīklu →", "ru": "Смотреть глобальную сеть →"},
        "crm": {"en": "CRM", "lv": "CRM", "ru": "CRM"},
        "ai_workforce": {"en": "AI workforce", "lv": "AI darbinieki", "ru": "AI-команда"},
        "estimates": {"en": "Estimates", "lv": "Tāmes", "ru": "Сметы"},
        "in_progress": {"en": "In progress", "lv": "Procesā", "ru": "В работе"},
        "due_sent": {"en": "Due / sent", "lv": "Termiņš / nosūtīts", "ru": "К оплате / отправлено"},
        "tasks_sub": {"en": "Live task and follow-up queue from NinaOS workspace.", "lv": "Dzīvā uzdevumu un atkārtoto kontaktu rinda no NinaOS darba vides.", "ru": "Живая очередь задач и повторных контактов из NinaOS."},
        "clients_sub": {"en": "CRM workspace for client work, follow-ups, estimates and invoices.", "lv": "CRM darba vide klientiem, follow-upiem, tāmēm un rēķiniem.", "ru": "CRM для клиентов, повторных контактов, смет и счетов."},
        "projects_sub": {"en": "Project operations view with linked client work.", "lv": "Projektu darba skats ar piesaistītiem klientu darbiem.", "ru": "Проектный вид с привязанной клиентской работой."},
        "workers_sub": {"en": "AI workforce control surface.", "lv": "AI darbinieku vadības panelis.", "ru": "Панель управления AI-работниками."},
        "exchange_sub": {"en": "AI Workers Marketplace — preview catalog.", "lv": "AI darbinieku birža — kataloga priekšskatījums.", "ru": "Маркетплейс AI-работников — предпросмотр каталога."},
        "calendar_sub": {"en": "Schedule and due work preview.", "lv": "Grafika un termiņu darba priekšskatījums.", "ru": "Расписание и задачи по срокам."},
        "files_sub": {"en": "Document workspace for client and project files.", "lv": "Dokumentu darba vide klientu un projektu failiem.", "ru": "Документы клиентов и проектов."},
        "analytics_sub": {"en": "Operational workspace analytics preview.", "lv": "Darba vides operatīvās analītikas priekšskatījums.", "ru": "Операционная аналитика рабочей среды."},
        "open_work_action": {"en": "Open work", "lv": "Atvērt darbus", "ru": "Открыть работу"},
        "view_details": {"en": "View Details", "lv": "Skatīt detaļas", "ru": "Подробнее"},
        "today": {"en": "today", "lv": "šodien", "ru": "сегодня"},
        "attention": {"en": "attention", "lv": "uzmanība", "ru": "внимание"},
        "office_manager": {"en": "Nina Office Manager", "lv": "Nina Office Manager", "ru": "Nina Office Manager"},
        "worker_detail_sub": {"en": "Main desktop control center for the first ready AI worker.", "lv": "Galvenais vadības centrs pirmajam gatavajam AI darbiniekam.", "ru": "Главный центр управления первым готовым AI-работником."},
        "role_stack": {"en": "Role Stack", "lv": "Lomu steks", "ru": "Стек ролей"},
        "approval_required": {"en": "Approval Required", "lv": "Vajadzīgs apstiprinājums", "ru": "Требуется подтверждение"},
        "allowed_tools": {"en": "Allowed Tools", "lv": "Atļautie rīki", "ru": "Разрешённые инструменты"},
        "memory_scopes": {"en": "Memory Scopes", "lv": "Atmiņas zonas", "ru": "Области памяти"},
        "permissions": {"en": "Permissions", "lv": "Atļaujas", "ru": "Права"},
        "worker_summary": {"en": "Worker Summary", "lv": "Darbinieka pārskats", "ru": "Сводка работника"},
        "linked_work": {"en": "Linked Work", "lv": "Piesaistītie darbi", "ru": "Связанная работа"},
        "quick_actions": {"en": "Quick Actions", "lv": "Ātrās darbības", "ru": "Быстрые действия"},
        "ask_nina": {"en": "Ask Nina", "lv": "Jautāt Ninai", "ru": "Спросить Нину"},
        "new_task": {"en": "New Task", "lv": "Jauns uzdevums", "ru": "Новая задача"},
        "followup_client": {"en": "Follow-up Client", "lv": "Sazināties ar klientu", "ru": "Повторно связаться"},
        "create_estimate": {"en": "Create Estimate Draft", "lv": "Izveidot tāmes melnrakstu", "ru": "Создать черновик сметы"},
        "create_invoice": {"en": "Create Invoice Admin Record", "lv": "Izveidot rēķina ierakstu", "ru": "Создать запись счёта"},
        "upload_document": {"en": "Upload Document", "lv": "Augšupielādēt dokumentu", "ru": "Загрузить документ"},
        "open_office_manager": {"en": "Open Office Manager", "lv": "Atvērt Office Manager", "ru": "Открыть Office Manager"},
        "action_panels": {"en": "Action Panels", "lv": "Darbību paneļi", "ru": "Панели действий"},
        "task_panel": {"en": "Task Panel", "lv": "Uzdevumu panelis", "ru": "Панель задач"},
        "followup_panel": {"en": "Follow-up Panel", "lv": "Follow-up panelis", "ru": "Панель повторных контактов"},
        "estimate_panel": {"en": "Estimate Panel", "lv": "Tāmju panelis", "ru": "Панель смет"},
        "invoice_panel": {"en": "Invoice Panel", "lv": "Rēķinu panelis", "ru": "Панель счетов"},
        "document_panel": {"en": "Document Panel", "lv": "Dokumentu panelis", "ru": "Панель документов"},
        "approval_queue": {"en": "Approval Queue", "lv": "Apstiprinājumu rinda", "ru": "Очередь подтверждений"},
        "create_task_hint": {"en": "Create and organize daily work.", "lv": "Izveido un sakārto dienas darbus.", "ru": "Создать и организовать работу дня."},
        "followup_hint": {"en": "Track repeated client contact.", "lv": "Sekot atkārtotai klientu saziņai.", "ru": "Отслеживать повторный контакт с клиентом."},
        "estimate_hint": {"en": "Draft offers and estimates.", "lv": "Sagatavot piedāvājumus un tāmes.", "ru": "Готовить предложения и сметы."},
        "invoice_hint": {"en": "Track sent and due invoice records.", "lv": "Sekot nosūtītiem un termiņa rēķiniem.", "ru": "Отслеживать счета и сроки оплаты."},
        "document_hint": {"en": "Link client and project documents.", "lv": "Piesaistīt klientu un projektu dokumentus.", "ru": "Привязать документы клиентов и проектов."},
        "approval_hint": {"en": "Owner confirmation before sensitive actions.", "lv": "Īpašnieka apstiprinājums pirms svarīgām darbībām.", "ru": "Подтверждение владельца перед важными действиями."},
        "open_panel": {"en": "Open Panel", "lv": "Atvērt paneli", "ru": "Открыть панель"},
        "no_approvals": {"en": "No approvals waiting.", "lv": "Nav gaidošu apstiprinājumu.", "ru": "Нет ожидающих подтверждений."},
        "next_step": {"en": "Next step", "lv": "Nākamais solis", "ru": "Следующий шаг"},
        "work_console": {"en": "Work Console", "lv": "Darba konsole", "ru": "Рабочая консоль"},
        "today_queue": {"en": "Today Queue", "lv": "Šodienas rinda", "ru": "Очередь на сегодня"},
        "followups_due": {"en": "Follow-ups Due", "lv": "Follow-up termiņi", "ru": "Повторные контакты"},
        "finance_queue": {"en": "Finance Queue", "lv": "Finanšu rinda", "ru": "Финансовая очередь"},
        "documents": {"en": "Documents", "lv": "Dokumenti", "ru": "Документы"},
        "pending_items": {"en": "Pending Items", "lv": "Gaidošie darbi", "ru": "Ожидающие элементы"},
        "owner_control": {"en": "Owner Control", "lv": "Īpašnieka kontrole", "ru": "Контроль владельца"},
        "worker_status": {"en": "Worker Status", "lv": "Darbinieka statuss", "ru": "Статус работника"},
        "active_worker": {"en": "Active worker", "lv": "Aktīvs darbinieks", "ru": "Активный работник"},
        "data_source": {"en": "Data source", "lv": "Datu avots", "ru": "Источник данных"},
        "no_items": {"en": "No items yet.", "lv": "Pagaidām nav ierakstu.", "ru": "Пока нет элементов."},
        "status_ready": {"en": "Ready", "lv": "Gatavs", "ru": "Готов"},
        "system_safe": {"en": "Safe mode", "lv": "Drošais režīms", "ru": "Безопасный режим"},
        "open_tasks": {"en": "Open tasks", "lv": "Atvērt uzdevumus", "ru": "Открыть задачи"},
        "open_clients": {"en": "Open clients", "lv": "Atvērt klientus", "ru": "Открыть клиентов"},
        "open_files": {"en": "Open files", "lv": "Atvērt failus", "ru": "Открыть файлы"},
        "console_sub": {"en": "What Nina Office Manager is handling right now.", "lv": "Ko Nina Office Manager šobrīd apstrādā.", "ru": "Что сейчас обрабатывает Nina Office Manager."},
        "action_center": {"en": "Action Center", "lv": "Darbību centrs", "ru": "Центр действий"},
        "action_center_sub": {"en": "Create operational work from the Office Manager console.", "lv": "Izveido operatīvos darbus no Office Manager konsoles.", "ru": "Создать рабочие элементы из консоли Office Manager."},
        "task_title": {"en": "Task title", "lv": "Uzdevuma nosaukums", "ru": "Название задачи"},
        "client_name": {"en": "Client name", "lv": "Klienta vārds", "ru": "Имя клиента"},
        "project_name": {"en": "Project name", "lv": "Projekta nosaukums", "ru": "Название проекта"},
        "amount": {"en": "Amount", "lv": "Summa", "ru": "Сумма"},
        "due_date": {"en": "Due date", "lv": "Termiņš", "ru": "Срок"},
        "notes": {"en": "Notes", "lv": "Piezīmes", "ru": "Заметки"},
        "priority": {"en": "Priority", "lv": "Prioritāte", "ru": "Приоритет"},
        "normal": {"en": "Normal", "lv": "Normāla", "ru": "Обычный"},
        "high": {"en": "High", "lv": "Augsta", "ru": "Высокий"},
        "submit_preview": {"en": "Save Preview", "lv": "Saglabāt priekšskatījumu", "ru": "Сохранить предпросмотр"},
        "safe_note": {"en": "V43 safe mode: forms create workspace preview objects first. Postgres write bridge comes next.", "lv": "V43 drošais režīms: formas vispirms izveido darba objektus priekšskatījumā. Postgres rakstīšanas bridge nāks nākamais.", "ru": "V43 безопасный режим: формы сначала создают рабочие объекты предпросмотра. Запись в Postgres — следующий bridge."},
        "created_preview": {"en": "Preview created", "lv": "Priekšskatījums izveidots", "ru": "Предпросмотр создан"},
        "form_type": {"en": "Form type", "lv": "Formas tips", "ru": "Тип формы"},
        "new_task_form": {"en": "New Task", "lv": "Jauns uzdevums", "ru": "Новая задача"},
        "followup_form": {"en": "Follow-up Client", "lv": "Follow-up klientam", "ru": "Повторный контакт"},
        "estimate_form": {"en": "Estimate Draft", "lv": "Tāmes melnraksts", "ru": "Черновик сметы"},
        "invoice_form": {"en": "Invoice Admin Record", "lv": "Rēķina ieraksts", "ru": "Запись счёта"},
        "saved_to_workspace": {"en": "Saved to workspace preview", "lv": "Saglabāts darba vides priekšskatījumā", "ru": "Сохранено в предпросмотр рабочего пространства"},
        "workspace_object": {"en": "Workspace object", "lv": "Darba objekts", "ru": "Рабочий объект"},
        "object_type": {"en": "Object type", "lv": "Objekta tips", "ru": "Тип объекта"},
        "object_id": {"en": "Object ID", "lv": "Objekta ID", "ru": "ID объекта"},
        "status": {"en": "Status", "lv": "Statuss", "ru": "Статус"},
        "preview_queue": {"en": "Preview Queue", "lv": "Priekšskatījumu rinda", "ru": "Очередь предпросмотра"},
    }
    return d.get(key, {}).get(lang) or d.get(key, {}).get("en") or key


def object_to_dict(obj):
    if isinstance(obj, dict):
        data = dict(obj)
    else:
        data = {
            "object_id": getattr(obj, "object_id", ""),
            "object_type": getattr(obj, "object_type", ""),
            "title": getattr(obj, "title", ""),
            "status": getattr(obj, "status", ""),
            "priority": getattr(obj, "priority", "normal"),
            "client_id": getattr(obj, "client_id", ""),
            "project_id": getattr(obj, "project_id", ""),
            "due_date": getattr(obj, "due_date", ""),
            "metadata": getattr(obj, "metadata", {}) or {},
        }
    data.setdefault("metadata", {})
    return data


def build_clients_from_objects(objects):
    clients = {}
    for obj in objects:
        meta = obj.get("metadata", {}) if isinstance(obj.get("metadata"), dict) else {}
        name = meta.get("client_name") or obj.get("client_name") or obj.get("client_id") or ""
        if not name:
            continue
        clients.setdefault(name, {"name": name, "objects": [], "followups": 0, "estimates": 0, "invoices": 0, "projects": 0})
        clients[name]["objects"].append(obj)
        t = obj.get("object_type")
        if t == "followup_task":
            clients[name]["followups"] += 1
        if t in ["estimate", "offer"]:
            clients[name]["estimates"] += 1
        if t == "invoice":
            clients[name]["invoices"] += 1
        if t == "project":
            clients[name]["projects"] += 1
    if not clients:
        clients["Demo Client"] = {"name": "Demo Client", "objects": [], "followups": 1, "estimates": 1, "invoices": 1, "projects": 1}
    return list(clients.values())


def load_live_objects_from_app_db():
    objects = []
    database_url = os.environ.get("DATABASE_URL") or os.environ.get("POSTGRES_URL") or ""
    if not database_url:
        return objects
    try:
        import psycopg2
        conn = psycopg2.connect(database_url)
        cur = conn.cursor()
        queries = [
            "SELECT id, title, status, priority, client, deadline, raw_text, followup FROM tasks ORDER BY id DESC LIMIT 100",
            "SELECT id, title, status, priority, client_name, due_date, raw_text, followup FROM tasks ORDER BY id DESC LIMIT 100",
        ]
        rows = []
        for query in queries:
            try:
                cur.execute(query)
                rows = cur.fetchall()
                break
            except Exception:
                conn.rollback()
        for row in rows:
            object_id, title, status, priority, client, due, raw_text, followup = row
            obj_type = "followup_task" if bool(followup) else "task"
            objects.append({
                "object_id": f"db_task_{object_id}",
                "object_type": obj_type,
                "title": title or raw_text or "Untitled task",
                "status": status or "open",
                "priority": priority or "normal",
                "client_id": client or "",
                "project_id": "",
                "due_date": due or "",
                "metadata": {"client_name": client or "", "owner": "Telegram Nina", "source": "database"},
            })
        cur.close()
        conn.close()
    except Exception:
        return []
    return objects



def normalize_action_to_work_object(action):
    form_type = (action.get("form_type") or "new_task").strip()
    title = (action.get("task_title") or "").strip()
    client_name = (action.get("client_name") or "").strip()
    project_name = (action.get("project_name") or "").strip()
    amount = (action.get("amount") or "").strip()
    due_date = (action.get("due_date") or "").strip()
    priority = (action.get("priority") or "normal").strip() or "normal"
    notes = (action.get("notes") or "").strip()

    type_map = {
        "new_task": "task",
        "followup": "followup_task",
        "estimate": "estimate",
        "invoice": "invoice",
    }
    status_map = {
        "new_task": "open",
        "followup": "scheduled",
        "estimate": "draft",
        "invoice": "admin_preview",
    }
    fallback_title = {
        "new_task": "New workspace task",
        "followup": "Follow up with client",
        "estimate": "Create estimate draft",
        "invoice": "Create invoice admin record",
    }

    object_type = type_map.get(form_type, "task")
    status = status_map.get(form_type, "open")
    now = datetime.utcnow().strftime("%Y%m%d%H%M%S")
    safe_title = title or fallback_title.get(form_type, "Workspace action")

    metadata = {
        "client_name": client_name,
        "project_name": project_name,
        "amount": amount,
        "notes": notes,
        "owner": "Nina Office Manager",
        "source": "web_action_preview",
        "safe_mode": True,
        "db_write": False,
        "created_at": datetime.utcnow().isoformat() + "Z",
    }

    return {
        "object_id": f"web_preview_{form_type}_{now}_{len(WORKSPACE_ACTION_PREVIEWS) + 1}",
        "object_type": object_type,
        "title": safe_title,
        "status": status,
        "priority": priority,
        "client_id": client_name,
        "project_id": project_name,
        "due_date": due_date,
        "metadata": metadata,
    }


def create_workspace_action_preview(action):
    obj = normalize_action_to_work_object(action)
    WORKSPACE_ACTION_PREVIEWS.insert(0, obj)
    del WORKSPACE_ACTION_PREVIEWS[25:]
    return obj


def load_workspace_data():
    workers = [
        {"name": "Nina Sales", "role": "AI Sales Executive", "status": "ACTIVE", "detail": "1 follow-up to handle", "tone": "purple", "price": "€99/month", "category": "Sales & Growth"},
        {"name": "Nina Estimator", "role": "AI Estimator", "status": "ACTIVE", "detail": "1 estimate in progress", "tone": "blue", "price": "€119/month", "category": "Construction"},
        {"name": "Nina Office Manager", "role": "AI Office Manager", "status": "ACTIVE", "detail": "1 task · 1 active project", "tone": "green", "price": "€89/month", "category": "Operations", "route": "/workers/office-manager"},
        {"name": "Nina Support", "role": "AI Support Specialist", "status": "IDLE", "detail": "No support queue yet", "tone": "orange", "price": "€79/month", "category": "Support"},
    ]
    objects = []
    try:
        from work_objects import list_work_objects, seed_demo_work_objects
        try:
            seed_demo_work_objects()
        except Exception:
            pass
        try:
            objects = list_work_objects(workspace_id="demo_small_business") or []
        except TypeError:
            objects = list_work_objects() or []
    except Exception:
        objects = []

    normalized = [object_to_dict(o) for o in objects]
    live_objects = load_live_objects_from_app_db()
    if live_objects:
        normalized = live_objects

    if WORKSPACE_ACTION_PREVIEWS:
        normalized = list(WORKSPACE_ACTION_PREVIEWS) + normalized

    if not normalized:
        normalized = [
            {"object_id": "task_1", "object_type": "task", "title": "Prepare today workspace priorities", "status": "open", "priority": "high", "client_id": "", "project_id": "", "due_date": "today", "metadata": {"client_name": "", "owner": "Nina Office Manager"}},
            {"object_id": "followup_1", "object_type": "followup_task", "title": "Follow up with Demo Client about offer", "status": "scheduled", "priority": "normal", "client_id": "demo_client", "project_id": "", "due_date": "friday", "metadata": {"client_name": "Demo Client", "owner": "Nina Sales"}},
            {"object_id": "estimate_1", "object_type": "estimate", "title": "Demo estimate draft", "status": "draft", "priority": "normal", "client_id": "demo_client", "project_id": "project_1", "due_date": "", "metadata": {"client_name": "Demo Client", "owner": "Nina Estimator"}},
            {"object_id": "invoice_1", "object_type": "invoice", "title": "Demo invoice follow-up", "status": "sent", "priority": "normal", "client_id": "demo_client", "project_id": "project_1", "due_date": "today", "metadata": {"client_name": "Demo Client", "owner": "Nina Office Manager"}},
            {"object_id": "project_1", "object_type": "project", "title": "Demo active project", "status": "active", "priority": "normal", "client_id": "demo_client", "project_id": "project_1", "due_date": "", "metadata": {"client_name": "Demo Client", "owner": "Nina Office Manager"}},
        ]

    activity = [
        {"title": "V43 workspace preview bridge", "body": "Office Manager forms now create safe workspace preview objects.", "kind": "work"},
        {"title": "Web service online", "body": "NinaOS web runtime is separated from Telegram runtime.", "kind": "info"},
        {"title": "Workspace loaded", "body": "V36 clean workspace data layer is active.", "kind": "info"},
        {"title": "Client follow-up scheduled", "body": "Ask Andris about reply.", "kind": "work"},
        {"title": "Exchange preview visible", "body": "AI worker catalog is available inside the web product.", "kind": "api"},
    ]

    active_statuses = ["open", "scheduled", "draft", "sent", "active", "in_progress"]
    tasks = [o for o in normalized if o.get("object_type") in ["task", "followup_task", "estimate", "invoice"]]
    clients = build_clients_from_objects(normalized)
    projects = [o for o in normalized if o.get("object_type") == "project"]
    counts = {
        "tasks_today": len([o for o in normalized if o.get("object_type") == "task" and o.get("status") in active_statuses]),
        "followups": len([o for o in normalized if o.get("object_type") == "followup_task" and o.get("status") in active_statuses]),
        "invoices": len([o for o in normalized if o.get("object_type") == "invoice" and o.get("status") in active_statuses]),
        "estimates": len([o for o in normalized if o.get("object_type") in ["estimate", "offer"] and o.get("status") in active_statuses]),
        "projects": len([o for o in normalized if o.get("object_type") == "project" and o.get("status") in active_statuses]),
        "clients": len(clients),
        "workers": len(workers),
    }
    return {"owner": "Katrin", "workers": workers, "objects": normalized, "tasks": tasks, "clients": clients, "projects": projects, "activity": activity, "counts": counts}


def nina_logo_html(size="small"):
    return "<div class='nina-logo " + size + "'><div class='dot-grid'></div><div class='orbit orbit-a'></div><div class='orbit orbit-b'></div></div>"


def css():
    return """
:root{--line:rgba(120,153,255,.26);--line2:rgba(255,255,255,.08);--text:#f8fbff;--muted:#a8b7d4;--green:#34e6a4;--shadow:0 30px 100px rgba(0,0,0,.36)}*{box-sizing:border-box}body{margin:0;min-height:100vh;color:var(--text);font-family:Inter,Segoe UI,Arial,sans-serif;background:radial-gradient(circle at 13% 14%,rgba(30,105,255,.20),transparent 25%),radial-gradient(circle at 80% 12%,rgba(80,70,255,.20),transparent 28%),linear-gradient(135deg,#080910 0%,#0a0d19 48%,#05060b 100%)}body:before{content:"";position:fixed;inset:0;pointer-events:none;background:linear-gradient(rgba(255,255,255,.026) 1px,transparent 1px),linear-gradient(90deg,rgba(255,255,255,.021) 1px,transparent 1px);background-size:44px 44px;mask-image:linear-gradient(to bottom,rgba(0,0,0,.5),transparent 70%)}a{color:inherit;text-decoration:none}.layout{display:grid;grid-template-columns:210px 1fr;min-height:100vh}.sidebar{position:sticky;top:0;height:100vh;padding:22px 14px;background:radial-gradient(circle at 28px 28px,rgba(44,142,255,.24),transparent 75px),linear-gradient(180deg,rgba(18,22,37,.86),rgba(8,9,15,.83));border-right:1px solid var(--line2);backdrop-filter:blur(16px)}.brand{display:flex;align-items:center;gap:10px;margin:0 6px 28px;font-weight:950}.brand-word span:last-child{color:#2a91ff}
.nina-logo{position:relative;border-radius:50%;overflow:hidden;background:radial-gradient(circle at 30% 30%,rgba(255,255,255,.9),transparent 5%),radial-gradient(circle at 65% 25%,rgba(84,232,255,.9),transparent 10%),radial-gradient(circle at 50% 50%,#1de0ff 0%,#2358ff 38%,#7f45ff 72%,#11152a 100%);box-shadow:0 0 24px rgba(49,140,255,.52),inset 0 0 30px rgba(255,255,255,.12)}.nina-logo.small{width:34px;height:34px}.nina-logo.hero{width:156px;height:156px;flex:0 0 156px}.dot-grid{position:absolute;inset:0;background:radial-gradient(circle,rgba(255,255,255,.86) 0 2px,transparent 2.8px);background-size:16px 16px;transform:rotate(-18deg) scale(1.1);opacity:.58;mask-image:radial-gradient(circle,#000 62%,transparent 70%)}.orbit{position:absolute;left:-22%;right:-22%;top:44%;height:2px;background:rgba(255,255,255,.45);border-radius:999px;transform:rotate(-16deg);box-shadow:0 0 14px rgba(90,190,255,.8)}.orbit-b{transform:rotate(28deg);opacity:.28;top:54%}.nav{display:flex;flex-direction:column;gap:7px}.nav-item{display:flex;align-items:center;gap:10px;padding:11px 12px;border-radius:13px;color:#dce7ff;font-size:14px;border:1px solid transparent}.nav-item:hover{background:rgba(255,255,255,.06)}.nav-item.active{background:linear-gradient(90deg,rgba(28,128,255,.95),rgba(90,63,255,.86));color:#fff;box-shadow:0 14px 32px rgba(23,109,255,.23)}.new{margin-left:auto;font-size:10px;padding:2px 7px;border-radius:999px;background:#5638ff}.user{position:absolute;bottom:18px;left:14px;right:14px;border:1px solid var(--line);background:rgba(255,255,255,.045);border-radius:16px;padding:12px;color:var(--muted);font-size:13px}.user b{color:#fff}
.main{padding:22px 26px 40px;max-width:1460px;width:100%;margin:0 auto}.topbar{display:flex;justify-content:space-between;align-items:center;margin-bottom:18px}.search{width:min(520px,55vw);border:1px solid var(--line);border-radius:18px;padding:14px 18px;color:var(--muted);background:rgba(16,24,45,.72);box-shadow:inset 0 0 0 1px rgba(255,255,255,.03),0 12px 34px rgba(0,0,0,.18)}.icons{display:flex;gap:10px;align-items:center}.icon{width:34px;height:34px;border-radius:50%;display:grid;place-items:center;background:rgba(255,255,255,.07);border:1px solid rgba(255,255,255,.10)}.avatar{background:linear-gradient(135deg,#7c43ff,#dc42ff);font-weight:950}.lang-switch{display:flex;gap:6px}.lang-switch a{font-size:12px;font-weight:950;padding:8px 9px;border-radius:999px;border:1px solid rgba(255,255,255,.10);background:rgba(255,255,255,.06);color:#dbe8ff}.lang-switch a.active{background:linear-gradient(90deg,#168dff,#6443ff);color:#fff}.grid{display:grid;gap:18px}.hero-grid{display:grid;grid-template-columns:1.02fr .98fr;gap:18px}.card{background:linear-gradient(180deg,rgba(26,36,68,.72),rgba(9,12,24,.70)),radial-gradient(circle at 25% 15%,rgba(40,140,255,.12),transparent 38%);border:1px solid var(--line);border-radius:24px;box-shadow:var(--shadow);backdrop-filter:blur(18px)}.card-pad{padding:24px}.hero-card{min-height:390px;display:flex;flex-direction:column;justify-content:center;align-items:center;text-align:center}.hero-lockup{display:flex;align-items:center;justify-content:center;gap:26px}.hero-title{font-size:78px;line-height:.9;font-weight:1000;letter-spacing:-5px;text-shadow:0 10px 40px rgba(0,0,0,.5)}.hero-title span{color:#2493ff}.subtitle{color:#dbe8ff;font-weight:900;letter-spacing:2px;font-size:13px;margin-top:10px}.bigline{margin-top:34px;font-size:25px;line-height:1.35;font-weight:950}.trust{display:flex;gap:8px;justify-content:center;flex-wrap:wrap;margin-top:24px}.trust span{font-size:12px;font-weight:900;padding:7px 12px;border:1px solid var(--line);background:rgba(255,255,255,.04);border-radius:999px}.kpis{display:grid;grid-template-columns:repeat(4,1fr);gap:12px}.kpi{display:block;padding:18px;border:1px solid var(--line);background:linear-gradient(180deg,rgba(255,255,255,.06),rgba(255,255,255,.025));border-radius:18px;min-height:118px}.kpi small{color:#dbe7ff;font-weight:900}.kpi strong{display:block;font-size:38px;margin:9px 0 2px}.kpi em{color:#71e9ff;font-style:normal;font-size:13px;font-weight:900}.page-title h1{margin:0;font-size:42px;letter-spacing:-1.8px;line-height:1}.page-title p{margin:8px 0 0;color:#c3d4f5;font-weight:800}.section-title{font-size:21px;font-weight:1000;margin:6px 0 13px}.worker-grid{display:grid;grid-template-columns:repeat(4,minmax(160px,1fr));gap:16px}.worker-card{overflow:hidden;border-radius:20px;border:1px solid var(--line);background:linear-gradient(180deg,rgba(28,35,60,.78),rgba(9,12,24,.78));min-height:248px;box-shadow:0 20px 55px rgba(0,0,0,.22)}.worker-top{height:112px;display:grid;place-items:center;position:relative;overflow:hidden}.worker-top:before{content:"";position:absolute;inset:0;background:repeating-linear-gradient(110deg,rgba(255,255,255,.10) 0 2px,transparent 2px 10px);opacity:.35}.tone-purple{background:linear-gradient(135deg,#4830d8,#6322b7)}.tone-blue{background:linear-gradient(135deg,#058aff,#053c8c)}.tone-green{background:linear-gradient(135deg,#02b973,#095a3b)}.tone-orange{background:linear-gradient(135deg,#d47418,#56321c)}.worker-avatar{position:relative;z-index:1;width:82px;height:82px;border-radius:50%;background:radial-gradient(circle at 36% 30%,#ffe8c8 0 16%,transparent 17%),radial-gradient(circle at 53% 65%,#ffdba8 0 23%,transparent 24%),radial-gradient(circle at 46% 45%,#ef973a 0 45%,#5d3928 46% 62%,#f6c58b 63% 100%);box-shadow:0 16px 34px rgba(0,0,0,.32)}.worker-body{padding:16px}.worker-body h3{margin:0 0 4px;font-size:20px;line-height:1.02}.muted{color:var(--muted)}.status{font-weight:950;font-size:12px;margin:10px 0}.active-dot{color:var(--green)}.idle-dot{color:#ffd057}.two-col{display:grid;grid-template-columns:1fr 1fr;gap:18px}.list{display:flex;flex-direction:column;gap:10px}.row{display:flex;justify-content:space-between;align-items:center;gap:12px;padding:14px 15px;border:1px solid var(--line);border-radius:16px;background:linear-gradient(90deg,rgba(28,111,255,.12),rgba(255,255,255,.035))}.row b{display:block;margin-bottom:4px}.pill{display:inline-flex;align-items:center;padding:7px 11px;border-radius:999px;background:rgba(31,124,255,.16);border:1px solid rgba(76,147,255,.32);color:#d7e8ff;font-size:12px;font-weight:950;white-space:nowrap}.btns{display:flex;gap:12px;flex-wrap:wrap;justify-content:center}.btn{display:inline-flex;align-items:center;justify-content:center;padding:13px 18px;border-radius:14px;border:1px solid var(--line);font-weight:950;background:rgba(255,255,255,.055);box-shadow:0 12px 26px rgba(0,0,0,.18)}.btn.primary{background:linear-gradient(90deg,#168dff,#6443ff);border-color:transparent}.footer-note{margin-top:22px;color:var(--muted);font-size:13px;text-align:center;font-weight:700}.console-nav{display:flex;gap:10px;flex-wrap:wrap;margin-bottom:16px}.console-nav a{padding:10px 13px;border-radius:999px;border:1px solid var(--line);background:rgba(255,255,255,.055);font-weight:950}.console-nav a.primary{background:linear-gradient(90deg,#168dff,#6443ff);border-color:transparent}.metric-strip{display:grid;grid-template-columns:repeat(6,1fr);gap:10px}.metric-mini{padding:13px;border:1px solid var(--line);border-radius:16px;background:rgba(255,255,255,.045)}.metric-mini small{color:var(--muted);font-weight:900}.metric-mini b{display:block;font-size:24px;margin-top:4px}.panel-grid{display:grid;grid-template-columns:1.1fr .9fr;gap:18px}.stack-grid{display:grid;gap:12px}.form-grid{display:grid;grid-template-columns:repeat(2,1fr);gap:12px}.field{display:flex;flex-direction:column;gap:6px}.field label{font-size:12px;font-weight:950;color:#dbe7ff}.field input,.field select,.field textarea{width:100%;border:1px solid var(--line);border-radius:14px;background:rgba(5,9,20,.58);color:var(--text);padding:12px 13px;font:inherit;outline:none}.field textarea{min-height:92px;resize:vertical}.form-actions{display:flex;gap:10px;flex-wrap:wrap;margin-top:14px}.preview-box{border:1px solid var(--line);border-radius:18px;background:rgba(31,124,255,.10);padding:16px;margin-bottom:16px}.preview-box b{display:block;margin-bottom:6px}.safe-note{color:#8fe7ff;font-weight:800;font-size:13px;margin-top:10px}@media(max-width:1100px){.layout{grid-template-columns:1fr}.sidebar{position:relative;height:auto}.user{position:static;margin-top:18px}.hero-grid,.two-col{grid-template-columns:1fr}.worker-grid{grid-template-columns:repeat(2,1fr)}.kpis{grid-template-columns:repeat(2,1fr)}}@media(max-width:640px){.main{padding:16px}.worker-grid,.kpis{grid-template-columns:1fr}.hero-lockup{flex-direction:column}.hero-title{font-size:56px;letter-spacing:-3px}.nina-logo.hero{width:128px;height:128px;flex-basis:128px}.search{width:58vw}}
"""


def page(title, body, active="dashboard"):
    lang = current_language()
    nav = [
        ("dashboard", tx("dashboard", lang), "/dashboard", "⌂"),
        ("workers", tx("workers", lang), "/workers", "♙"),
        ("tasks", tx("tasks", lang), "/tasks", "☑"),
        ("clients", tx("clients", lang), "/clients", "●"),
        ("projects", tx("projects", lang), "/projects", "▣"),
        ("calendar", tx("calendar", lang), "/calendar", "◫"),
        ("files", tx("files", lang), "/files", "▤"),
        ("analytics", tx("analytics", lang), "/analytics", "⌁"),
        ("exchange", tx("exchange", lang), "/exchange", "◎"),
    ]
    nav_html = ""
    for key, label, href, icon in nav:
        cls = "nav-item active" if key == active else "nav-item"
        badge = "<span class='new'>NEW</span>" if key == "exchange" else ""
        nav_html += f"<a class='{cls}' href='{href}?lang={lang}'><span>{icon}</span><b>{label}</b>{badge}</a>"
    def lang_link(l):
        cls = "active" if lang == l else ""
        return f'<a class="{cls}" href="?lang={l}">{l.upper()}</a>'
    return f"""<!doctype html><html lang="{lang}"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>{html_escape(title)} · NinaOS</title><style>{css()}</style></head><body><div class="layout"><aside class="sidebar"><a href="/dashboard?lang={lang}" class="brand">{nina_logo_html("small")}<div class="brand-word"><span>Nina</span><span>OS</span></div></a><nav class="nav">{nav_html}</nav><div class="user"><b>Katrin</b><br>Owner<br><br><span class="pill">Runtime: web_app.py</span></div></aside><main class="main"><div class="topbar"><div class="search">{tx("search", lang)}</div><div class="icons"><div class="icon">🔔</div><div class="icon">🌐</div><div class="lang-switch">{lang_link("en")}{lang_link("lv")}{lang_link("ru")}</div><div class="icon">☼</div><div class="icon avatar">K</div></div></div>{body}<div class="footer-note">{WEB_APP_VERSION} · Web service separate from Telegram app.py</div></main></div></body></html>"""


def kpi_card(label, value, hint):
    return f"<a class='kpi' href='{hint.get('href', '#')}?lang={current_language()}'><small>{label}</small><strong>{value}</strong><em>{hint.get('text','Live data')}</em></a>"


def worker_card(w, marketplace=False):
    if marketplace:
        extra = f"<div class='status'>★ 4.8 · {html_escape(w.get('category',''))}</div><b>{html_escape(w.get('price',''))}</b><br><br><span class='btn'>{tx('view_details')}</span>"
    else:
        dot = "active-dot" if w["status"] == "ACTIVE" else "idle-dot"
        extra = f"<div class='status'><span class='{dot}'>●</span> {html_escape(w['status'])}</div><b>{html_escape(w['detail'])}</b>"
    return f"<a class='worker-card' href='{w.get('route','/workers')}?lang={current_language()}'><div class='worker-top tone-{w.get('tone','blue')}'><div class='worker-avatar'></div></div><div class='worker-body'><h3>{html_escape(w['name'])}</h3><div class='muted'>{html_escape(w['role'])}</div>{extra}</div></a>"


def activity_row(a):
    return f"<div class='row'><div><b>{html_escape(a.get('title'))}</b><span class='muted'>{html_escape(a.get('body'))}</span></div><span class='pill'>{html_escape(a.get('kind','info'))}</span></div>"


def dashboard_body(data):
    lang = current_language()
    c = data["counts"]
    kpis = (
        "<div class='kpis'>"
        + kpi_card(tx("tasks_today", lang), c["tasks_today"], {"text": tx("open_work_label", lang), "href": "/tasks"})
        + kpi_card(tx("followups", lang), c["followups"], {"text": tx("need_attention", lang), "href": "/tasks"})
        + kpi_card(tx("invoices", lang), c["invoices"], {"text": tx("finance", lang), "href": "/clients"})
        + kpi_card(tx("projects_kpi", lang), c["projects"], {"text": tx("active", lang), "href": "/projects"})
        + "</div>"
    )
    workers = "".join(worker_card(w) for w in data["workers"])
    activity = "".join(activity_row(a) for a in data["activity"][:6])
    snapshot_kpis = (
        kpi_card(tx("clients", lang), c["clients"], {"text": tx("crm", lang), "href": "/clients"})
        + kpi_card(tx("workers", lang), c["workers"], {"text": tx("ai_workforce", lang), "href": "/workers"})
        + kpi_card(tx("estimates", lang), c["estimates"], {"text": tx("in_progress", lang), "href": "/tasks"})
        + kpi_card(tx("invoices", lang), c["invoices"], {"text": tx("due_sent", lang), "href": "/clients"})
    )
    return f"<div class='grid'><div class='hero-grid'><section class='card card-pad hero-card'><div class='hero-lockup'>{nina_logo_html('hero')}<div><div class='hero-title'>Nina<span>OS</span></div><div class='subtitle'>AI WORKFORCE OPERATING SYSTEM</div></div></div><div class='bigline'>{tx('hero_line', lang)}</div><br><div class='btns'><a class='btn primary' href='{q('/tasks')}'>{tx('open_work', lang)}</a><a class='btn' href='{q('/exchange')}'>{tx('explore', lang)}</a></div><div class='trust'><span>GLOBAL</span><span>WORKFORCE</span><span>SECURE</span><span>SCALE</span></div></section><section class='card card-pad'><div class='page-title'><h1>{tx('good_morning', lang)}</h1><p>{tx('workspace_today', lang)}</p></div><br>{kpis}<br><div class='card card-pad' style='background:rgba(27,84,255,.16)'><div class='section-title'>{tx('global', lang)}</div><p class='muted'>{tx('connected', lang)}</p><a class='btn' href='{q('/exchange')}'>{tx('view_global', lang)}</a></div></section></div><section><div class='section-title'>{tx('your_workers', lang)}</div><div class='worker-grid'>{workers}</div></section><div class='two-col'><section class='card card-pad'><div class='section-title'>{tx('recent', lang)}</div><div class='list'>{activity}</div></section><section class='card card-pad'><div class='section-title'>{tx('snapshot', lang)}</div><div class='kpis'>{snapshot_kpis}</div><br><div class='btns'><a class='btn primary' href='{q('/tasks')}'>{tx('tasks', lang)}</a><a class='btn' href='{q('/clients')}'>{tx('clients', lang)}</a><a class='btn' href='{q('/projects')}'>{tx('projects', lang)}</a><a class='btn' href='{q('/workers')}'>{tx('workers', lang)}</a></div></section></div></div>"


def work_page_header(title, subtitle):
    return f"<div class='grid'><section class='card card-pad'><div class='page-title'><h1>{html_escape(title)}</h1><p>{html_escape(subtitle)}</p></div><br><div class='btns'><a class='btn primary' href='{q('/dashboard')}'>{tx('dashboard')}</a><a class='btn' href='{q('/tasks')}'>{tx('tasks')}</a><a class='btn' href='{q('/clients')}'>{tx('clients')}</a><a class='btn' href='{q('/workers')}'>{tx('workers')}</a><a class='btn' href='{q('/exchange')}'>{tx('exchange')}</a></div></section></div><br>"


def tasks_body(data):
    rows = ""
    for obj in data["tasks"]:
        meta = obj.get("metadata", {}) if isinstance(obj.get("metadata"), dict) else {}
        client = meta.get("client_name") or obj.get("client_id") or "Workspace"
        rows += f"<div class='row'><div><b>{html_escape(obj.get('title'))}</b><span class='muted'>{html_escape(client)} · {html_escape(obj.get('object_type'))}</span></div><span class='pill'>{html_escape(obj.get('status'))} · {html_escape(obj.get('priority'))}</span></div>"
    return work_page_header(tx("tasks"), tx("tasks_sub")) + f"<section class='card card-pad'><div class='list'>{rows}</div></section>"


def clients_body(data):
    rows = ""
    for client in data["clients"]:
        rows += f"<div class='row'><div><b>{html_escape(client.get('name'))}</b><span class='muted'>follow-ups: {client.get('followups',0)} · estimates: {client.get('estimates',0)} · invoices: {client.get('invoices',0)} · projects: {client.get('projects',0)}</span></div><a class='pill' href='{q('/tasks')}'>{tx('open_work_action')}</a></div>"
    return work_page_header(tx("clients"), tx("clients_sub")) + f"<section class='card card-pad'><div class='list'>{rows}</div></section>"


def projects_body(data):
    items = data["projects"] or [{"title":"Demo active project", "status":"active", "priority":"normal", "metadata":{"client_name":"Demo Client"}}]
    rows = ""
    for p in items:
        meta = p.get("metadata", {}) if isinstance(p.get("metadata"), dict) else {}
        rows += f"<div class='row'><div><b>{html_escape(p.get('title'))}</b><span class='muted'>{html_escape(meta.get('client_name','Workspace'))}</span></div><span class='pill'>{html_escape(p.get('status'))} · {html_escape(p.get('priority','normal'))}</span></div>"
    return work_page_header(tx("projects"), tx("projects_sub")) + f"<section class='card card-pad'><div class='list'>{rows}</div></section>"


def workers_body(data):
    lang = current_language()
    cards = ''.join(worker_card(w) for w in data['workers'])
    top = work_page_header(tx("workers"), tx("workers_sub"))
    top += f"<section class='card card-pad'><div class='section-title'>{tx('quick_actions', lang)}</div><div class='btns'><a class='btn primary' href='{q('/workers/office-manager')}'>{tx('open_office_manager', lang)}</a><a class='btn' href='{q('/exchange')}'>{tx('explore', lang)}</a></div></section><br>"
    return top + f"<div class='worker-grid'>{cards}</div>"


def exchange_body(data):
    catalog = [
        {"name": "Nina Sales", "role": "AI Sales Executive", "price": "€99/month", "category": "Sales & Growth", "tone": "purple"},
        {"name": "Nina Estimator", "role": "AI Estimator", "price": "€119/month", "category": "Construction", "tone": "blue"},
        {"name": "Nina Office Manager", "role": "AI Office Manager", "price": "€89/month", "category": "Operations", "tone": "green"},
        {"name": "Nina Support", "role": "AI Support Specialist", "price": "€79/month", "category": "Support", "tone": "orange"},
        {"name": "Nina Marketing", "role": "AI Marketing Specialist", "price": "€99/month", "category": "Marketing", "tone": "purple"},
        {"name": "Nina HR", "role": "AI HR Assistant", "price": "€89/month", "category": "HR", "tone": "orange"},
    ]
    return work_page_header(tx("exchange"), tx("exchange_sub")) + f"<div class='worker-grid'>{''.join(worker_card(w, marketplace=True) for w in catalog)}</div>"


def simple_module_body(title, subtitle, blocks):
    rows = "".join(f"<div class='row'><div><b>{html_escape(b[0])}</b><span class='muted'>{html_escape(b[1])}</span></div><span class='pill'>{html_escape(b[2])}</span></div>" for b in blocks)
    return work_page_header(title, subtitle) + f"<section class='card card-pad'><div class='list'>{rows}</div></section>"




def action_panel_card(title, hint, count, href, tone="normal"):
    return (
        "<div class='card card-pad'>"
        f"<div class='section-title'>{html_escape(title)}</div>"
        f"<p class='muted'>{html_escape(hint)}</p>"
        f"<div class='kpi'><small>{tx('active')}</small><strong>{count}</strong><em>{tx('open_work_label')}</em></div>"
        "<br>"
        f"<a class='btn primary' href='{href}'>{tx('open_panel')}</a>"
        "</div>"
    )


def office_manager_action_panels(data):
    lang = current_language()
    tasks = len([o for o in data["tasks"] if o.get("object_type") == "task"])
    followups = len([o for o in data["tasks"] if o.get("object_type") == "followup_task"])
    estimates = len([o for o in data["tasks"] if o.get("object_type") == "estimate"])
    invoices = len([o for o in data["tasks"] if o.get("object_type") == "invoice"])
    documents = 3
    approvals = 0

    return (
        f"<section class='card card-pad'><div class='section-title'>{tx('action_panels', lang)}</div>"
        "<div class='worker-grid'>"
        + action_panel_card(tx("task_panel", lang), tx("create_task_hint", lang), tasks, q("/tasks"))
        + action_panel_card(tx("followup_panel", lang), tx("followup_hint", lang), followups, q("/tasks"))
        + action_panel_card(tx("estimate_panel", lang), tx("estimate_hint", lang), estimates, q("/tasks"))
        + action_panel_card(tx("invoice_panel", lang), tx("invoice_hint", lang), invoices, q("/clients"))
        + action_panel_card(tx("document_panel", lang), tx("document_hint", lang), documents, q("/files"))
        + action_panel_card(tx("approval_queue", lang), tx("approval_hint", lang), approvals, q("/workers/office-manager"))
        + "</div></section>"
    )




def get_action_preview():
    if request.method != "POST":
        return None
    form = request.form
    action = {
        "form_type": form.get("form_type", ""),
        "task_title": form.get("task_title", ""),
        "client_name": form.get("client_name", ""),
        "project_name": form.get("project_name", ""),
        "amount": form.get("amount", ""),
        "due_date": form.get("due_date", ""),
        "priority": form.get("priority", "normal"),
        "notes": form.get("notes", ""),
    }
    obj = create_workspace_action_preview(action)
    action["workspace_object"] = obj
    return action


def action_preview_html(preview):
    if not preview:
        return ""
    lang = current_language()
    labels = [
        ("form_type", tx("form_type", lang)),
        ("task_title", tx("task_title", lang)),
        ("client_name", tx("client_name", lang)),
        ("project_name", tx("project_name", lang)),
        ("amount", tx("amount", lang)),
        ("due_date", tx("due_date", lang)),
        ("priority", tx("priority", lang)),
        ("notes", tx("notes", lang)),
    ]
    rows = ""
    for key, label in labels:
        value = preview.get(key) or "—"
        rows += f"<div class='row'><div><b>{html_escape(label)}</b><span class='muted'>{html_escape(value)}</span></div><span class='pill'>preview</span></div>"
    obj = preview.get("workspace_object") or {}
    if obj:
        rows += f"<div class='row'><div><b>{tx('object_id', lang)}</b><span class='muted'>{html_escape(obj.get('object_id'))}</span></div><span class='pill'>V43</span></div>"
        rows += f"<div class='row'><div><b>{tx('object_type', lang)}</b><span class='muted'>{html_escape(obj.get('object_type'))}</span></div><span class='pill'>{html_escape(obj.get('status'))}</span></div>"
    return f"<div class='preview-box'><b>{tx('saved_to_workspace', lang)}</b><div class='list'>{rows}</div><div class='safe-note'>{tx('safe_note', lang)}</div></div>"


def action_form_card(form_type, title, hint, defaults=None):
    lang = current_language()
    defaults = defaults or {}
    action = q("/office-manager/actions")
    return f"""
    <section class='card card-pad'>
      <div class='section-title'>{html_escape(title)}</div>
      <p class='muted'>{html_escape(hint)}</p>
      <form method='post' action='{action}'>
        <input type='hidden' name='form_type' value='{html_escape(form_type)}'>
        <div class='form-grid'>
          <div class='field'>
            <label>{tx('task_title', lang)}</label>
            <input name='task_title' placeholder='{tx('task_title', lang)}' value='{html_escape(defaults.get('task_title',''))}'>
          </div>
          <div class='field'>
            <label>{tx('client_name', lang)}</label>
            <input name='client_name' placeholder='{tx('client_name', lang)}' value='{html_escape(defaults.get('client_name',''))}'>
          </div>
          <div class='field'>
            <label>{tx('project_name', lang)}</label>
            <input name='project_name' placeholder='{tx('project_name', lang)}' value='{html_escape(defaults.get('project_name',''))}'>
          </div>
          <div class='field'>
            <label>{tx('due_date', lang)}</label>
            <input name='due_date' placeholder='today / friday / 2026-07-10' value='{html_escape(defaults.get('due_date',''))}'>
          </div>
          <div class='field'>
            <label>{tx('amount', lang)}</label>
            <input name='amount' placeholder='€0.00' value='{html_escape(defaults.get('amount',''))}'>
          </div>
          <div class='field'>
            <label>{tx('priority', lang)}</label>
            <select name='priority'>
              <option value='normal'>{tx('normal', lang)}</option>
              <option value='high'>{tx('high', lang)}</option>
            </select>
          </div>
        </div>
        <br>
        <div class='field'>
          <label>{tx('notes', lang)}</label>
          <textarea name='notes' placeholder='{tx('notes', lang)}'>{html_escape(defaults.get('notes',''))}</textarea>
        </div>
        <div class='form-actions'>
          <button class='btn primary' type='submit'>{tx('submit_preview', lang)}</button>
          <a class='btn' href='{q('/office-manager')}'>{tx('work_console', lang)}</a>
        </div>
        <div class='safe-note'>{tx('safe_note', lang)}</div>
      </form>
    </section>
    """


def action_center_body(data):
    lang = current_language()
    preview = get_action_preview()
    if preview and preview.get("workspace_object"):
        obj = preview["workspace_object"]
        data["objects"].insert(0, obj)
        if obj.get("object_type") in ["task", "followup_task", "estimate", "invoice"]:
            data["tasks"].insert(0, obj)
    preview_rows = ""
    for obj in WORKSPACE_ACTION_PREVIEWS[:5]:
        meta = obj.get("metadata", {}) if isinstance(obj.get("metadata"), dict) else {}
        client = meta.get("client_name") or obj.get("client_id") or "Workspace"
        preview_rows += f"<div class='row'><div><b>{html_escape(obj.get('title'))}</b><span class='muted'>{html_escape(client)} · {html_escape(obj.get('object_type'))}</span></div><span class='pill'>{html_escape(obj.get('status'))}</span></div>"
    if not preview_rows:
        preview_rows = f"<div class='row'><div><b>{tx('no_items', lang)}</b><span class='muted'>—</span></div><span class='pill'>preview</span></div>"
    forms = (
        "<div class='stack-grid'>"
        + action_form_card("new_task", tx("new_task_form", lang), tx("create_task_hint", lang))
        + action_form_card("followup", tx("followup_form", lang), tx("followup_hint", lang), {"task_title": "Follow up with client"})
        + action_form_card("estimate", tx("estimate_form", lang), tx("estimate_hint", lang), {"task_title": "Create estimate draft"})
        + action_form_card("invoice", tx("invoice_form", lang), tx("invoice_hint", lang), {"task_title": "Create invoice admin record"})
        + "</div>"
    )
    return (
        work_page_header(tx("action_center", lang), tx("action_center_sub", lang))
        + action_preview_html(preview)
        + "<div class='console-nav'>"
        + f"<a class='primary' href='{q('/office-manager/actions')}'>{tx('action_center', lang)}</a>"
        + f"<a href='{q('/office-manager')}'>{tx('work_console', lang)}</a>"
        + f"<a href='{q('/office-manager/panels')}'>{tx('action_panels', lang)}</a>"
        + f"<a href='{q('/tasks')}'>{tx('tasks', lang)}</a>"
        + f"<a href='{q('/clients')}'>{tx('clients', lang)}</a>"
        + "</div>"
        + f"<section class='card card-pad'><div class='section-title'>{tx('preview_queue', lang)}</div><div class='list'>{preview_rows}</div></section><br>"
        + forms
    )



def office_manager_body(data):
    lang = current_language()
    tasks = [o for o in data["tasks"] if o.get("object_type") in ["task", "followup_task"]]
    invoices = [o for o in data["tasks"] if o.get("object_type") == "invoice"]
    estimates = [o for o in data["tasks"] if o.get("object_type") == "estimate"]

    def mini_list(items, empty_text):
        if not items:
            return f"<div class='row'><div><b>{html_escape(empty_text)}</b><span class='muted'>—</span></div><span class='pill'>idle</span></div>"
        rows = ""
        for item in items[:5]:
            meta = item.get("metadata", {}) if isinstance(item.get("metadata"), dict) else {}
            client = meta.get("client_name") or item.get("client_id") or "Workspace"
            rows += f"<div class='row'><div><b>{html_escape(item.get('title'))}</b><span class='muted'>{html_escape(client)} · {html_escape(item.get('object_type'))}</span></div><span class='pill'>{html_escape(item.get('status'))}</span></div>"
        return rows

    role_rows = [
        ("Office Manager", "Coordinates daily workspace operations", "active"),
        ("Task Router", "Organizes tasks, follow-ups and due work", "active"),
        ("Client Admin", "Keeps client work visible in one place", "active"),
        ("Finance Admin", "Tracks invoice and estimate admin records", "preview"),
    ]
    role_html = "".join(f"<div class='row'><div><b>{html_escape(a)}</b><span class='muted'>{html_escape(b)}</span></div><span class='pill'>{html_escape(c)}</span></div>" for a,b,c in role_rows)

    right_blocks = "".join([
        f"<div class='row'><div><b>{tx('approval_required', lang)}</b><span class='muted'>No approval queue yet</span></div><span class='pill'>0</span></div>",
        f"<div class='row'><div><b>{tx('allowed_tools', lang)}</b><span class='muted'>tasks · clients · files · estimates · invoices</span></div><span class='pill'>safe</span></div>",
        f"<div class='row'><div><b>{tx('memory_scopes', lang)}</b><span class='muted'>workspace · client · project</span></div><span class='pill'>read</span></div>",
        f"<div class='row'><div><b>{tx('permissions', lang)}</b><span class='muted'>write_task · write_client · write_document</span></div><span class='pill'>limited</span></div>",
    ])

    quick = "".join([
        f"<a class='btn primary' href='{q('/office-manager/actions')}'>{tx('action_center', lang)}</a>",
        f"<a class='btn' href='{q('/tasks')}'>{tx('new_task', lang)}</a>",
        f"<a class='btn' href='{q('/clients')}'>{tx('followup_client', lang)}</a>",
        f"<a class='btn' href='{q('/tasks')}'>{tx('create_estimate', lang)}</a>",
        f"<a class='btn' href='{q('/clients')}'>{tx('create_invoice', lang)}</a>",
        f"<a class='btn' href='{q('/files')}'>{tx('upload_document', lang)}</a>",
    ])

    return (
        work_page_header(tx("office_manager", lang), tx("worker_detail_sub", lang))
        + "<div class='hero-grid'>"
        + "<section class='card card-pad'>"
        + f"<div class='section-title'>{tx('worker_summary', lang)}</div>"
        + "<div class='row'><div><b>Nina Office Manager SMB</b><span class='muted'>AI Office Manager · ACTIVE · Operations</span></div><span class='pill'>ready</span></div>"
        + "<br><div class='kpis'>"
        + kpi_card(tx("tasks_today", lang), data["counts"]["tasks_today"], {"text": tx("open_work_label", lang), "href": "/tasks"})
        + kpi_card(tx("followups", lang), data["counts"]["followups"], {"text": tx("need_attention", lang), "href": "/tasks"})
        + kpi_card(tx("invoices", lang), data["counts"]["invoices"], {"text": tx("finance", lang), "href": "/clients"})
        + kpi_card(tx("projects_kpi", lang), data["counts"]["projects"], {"text": tx("active", lang), "href": "/projects"})
        + "</div><br>"
        + f"<div class='section-title'>{tx('role_stack', lang)}</div><div class='list'>{role_html}</div>"
        + "</section>"
        + "<section class='card card-pad'>"
        + f"<div class='section-title'>{tx('quick_actions', lang)}</div><div class='btns'>{quick}</div><br>"
        + f"<div class='section-title'>{tx('approval_required', lang)}</div><div class='list'>{right_blocks}</div>"
        + "</section>"
        + "</div><br>"
        + office_manager_action_panels(data)
        + "<br><div class='two-col'>"
        + f"<section class='card card-pad'><div class='section-title'>{tx('linked_work', lang)}</div><div class='list'>{mini_list(tasks, 'No task queue yet')}</div></section>"
        + f"<section class='card card-pad'><div class='section-title'>{tx('estimates', lang)} / {tx('invoices', lang)}</div><div class='list'>{mini_list(estimates + invoices, 'No finance admin queue yet')}</div></section>"
        + "</div>"
    )



@app.route("/")
def home():
    return redirect(q("/dashboard"))


@app.route("/dashboard")
def dashboard():
    data = load_workspace_data()
    return Response(page(tx("dashboard"), dashboard_body(data), active="dashboard"), mimetype="text/html")


@app.route("/workers")
def workers():
    data = load_workspace_data()
    return Response(page(tx("workers"), workers_body(data), active="workers"), mimetype="text/html")


@app.route("/office-manager")
def office_manager_short():
    data = load_workspace_data()
    return Response(page(tx("office_manager"), office_manager_body(data), active="workers"), mimetype="text/html")


@app.route("/office-manager/console")
def office_manager_console():
    data = load_workspace_data()
    return Response(page(tx("office_manager"), office_manager_body(data), active="workers"), mimetype="text/html")


@app.route("/office-manager/panels")
def office_manager_panels():
    data = load_workspace_data()
    body = work_page_header(tx("action_panels"), tx("worker_detail_sub")) + office_manager_action_panels(data)
    return Response(page(tx("action_panels"), body, active="workers"), mimetype="text/html")


@app.route("/office-manager/actions", methods=["GET", "POST"])
def office_manager_actions():
    data = load_workspace_data()
    return Response(page(tx("action_center"), action_center_body(data), active="workers"), mimetype="text/html")


@app.route("/workers/office-manager")
def office_manager():
    data = load_workspace_data()
    return Response(page(tx("office_manager"), office_manager_body(data), active="workers"), mimetype="text/html")


@app.route("/tasks")
def tasks():
    data = load_workspace_data()
    return Response(page(tx("tasks"), tasks_body(data), active="tasks"), mimetype="text/html")


@app.route("/clients")
def clients():
    data = load_workspace_data()
    return Response(page(tx("clients"), clients_body(data), active="clients"), mimetype="text/html")


@app.route("/projects")
def projects():
    data = load_workspace_data()
    return Response(page(tx("projects"), projects_body(data), active="projects"), mimetype="text/html")


@app.route("/calendar")
def calendar():
    body = simple_module_body(tx("calendar"), tx("calendar_sub"), [("Today", "Workspace priorities and follow-ups", "live"), ("Follow-up Friday", "Ask Andris about reply", "scheduled"), ("Upcoming", "Calendar integration placeholder", "next")])
    return Response(page(tx("calendar"), body, active="calendar"), mimetype="text/html")


@app.route("/files")
def files():
    body = simple_module_body(tx("files"), tx("files_sub"), [("Demo client package", "Ready for organization", "document"), ("Invoice admin record", "Linked to workspace", "finance"), ("Estimate draft", "Linked to Demo Client", "estimate")])
    return Response(page(tx("files"), body, active="files"), mimetype="text/html")


@app.route("/analytics")
def analytics():
    data = load_workspace_data()
    c = data["counts"]
    body = work_page_header(tx("analytics"), tx("analytics_sub"))
    body += (
        "<section class='card card-pad'><div class='kpis'>"
        + kpi_card(tx("tasks"), c["tasks_today"], {"text": tx("today"), "href": "/tasks"})
        + kpi_card(tx("followups"), c["followups"], {"text": tx("attention"), "href": "/tasks"})
        + kpi_card(tx("clients"), c["clients"], {"text": tx("crm"), "href": "/clients"})
        + kpi_card(tx("workers"), c["workers"], {"text": tx("active"), "href": "/workers"})
        + "</div></section>"
    )
    return Response(page(tx("analytics"), body, active="analytics"), mimetype="text/html")


@app.route("/exchange")
def exchange():
    data = load_workspace_data()
    return Response(page(tx("exchange"), exchange_body(data), active="exchange"), mimetype="text/html")


@app.route("/health")
def health():
    return {"ok": True, "runtime": "web_app.py", "version": WEB_APP_VERSION, "language": current_language(), "preview_objects": len(WORKSPACE_ACTION_PREVIEWS), "time": datetime.utcnow().isoformat() + "Z"}


if __name__ == "__main__":
    port = safe_int(os.environ.get("PORT"), 8080)
    app.run(host="0.0.0.0", port=port)
def safe_int(value, default=0):
    try:
        return int(value)
    except Exception:
        return default


def html_escape(s):
    return str(s or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def current_language():
    lang = (request.args.get("lang") or "en").strip().lower()
    return lang if lang in ["en", "lv", "ru"] else "en"


def q(path):
    return f"{path}?lang={current_language()}"


def tx(key, lang=None):
    lang = lang or current_language()
    d = {
        "search": {"en": "Search anything...", "lv": "Meklēt jebko...", "ru": "Искать..."},
        "dashboard": {"en": "Dashboard", "lv": "Panelis", "ru": "Панель"},
        "workers": {"en": "Workers", "lv": "Darbinieki", "ru": "Работники"},
        "tasks": {"en": "Tasks", "lv": "Uzdevumi", "ru": "Задачи"},
        "clients": {"en": "Clients", "lv": "Klienti", "ru": "Клиенты"},
        "projects": {"en": "Projects", "lv": "Projekti", "ru": "Проекты"},
        "calendar": {"en": "Calendar", "lv": "Kalendārs", "ru": "Календарь"},
        "files": {"en": "Files", "lv": "Faili", "ru": "Файлы"},
        "analytics": {"en": "Analytics", "lv": "Analītika", "ru": "Аналитика"},
        "exchange": {"en": "Exchange", "lv": "Birža", "ru": "Биржа"},
        "good_morning": {"en": "Good morning, Katrin 👋", "lv": "Labrīt, Katrin 👋", "ru": "Доброе утро, Katrin 👋"},
        "workspace_today": {
            "en": "Here’s what needs attention in your NinaOS workspace today.",
            "lv": "Šeit ir tas, kam šodien jāpievērš uzmanība NinaOS darba vidē.",
            "ru": "Вот что сегодня требует внимания в рабочем пространстве NinaOS.",
        },
        "hero_line": {
            "en": "One Platform. Unlimited AI Workers.<br>For every business. Everywhere.",
            "lv": "Viena platforma. Neierobežoti AI darbinieki.<br>Katram biznesam. Visur.",
            "ru": "Одна платформа. Неограниченные AI-работники.<br>Для любого бизнеса. Везде.",
        },
        "open_work": {"en": "Open Work Queue", "lv": "Atvērt darbu rindu", "ru": "Открыть задачи"},
        "explore": {"en": "Explore Exchange", "lv": "Apskatīt biržu", "ru": "Открыть биржу"},
        "global": {"en": "Global AI Workforce", "lv": "Globālais AI darbaspēks", "ru": "Глобальная AI-команда"},
        "connected": {"en": "Connected. Intelligent. Tireless.", "lv": "Savienots. Gudrs. Nenogurstošs.", "ru": "Связано. Умно. Без усталости."},
        "your_workers": {"en": "Your AI Workforce", "lv": "Tavi AI darbinieki", "ru": "Твои AI-работники"},
        "recent": {"en": "Recent Activity", "lv": "Pēdējā aktivitāte", "ru": "Последняя активность"},
        "snapshot": {"en": "Workspace Snapshot", "lv": "Darba vides pārskats", "ru": "Снимок рабочей среды"},
        "tasks_today": {"en": "Tasks Today", "lv": "Šodienas uzdevumi", "ru": "Задачи сегодня"},
        "followups": {"en": "Follow-ups", "lv": "Atkārtoti kontakti", "ru": "Повторные контакты"},
        "invoices": {"en": "Invoices", "lv": "Rēķini", "ru": "Счета"},
        "projects_kpi": {"en": "Projects", "lv": "Projekti", "ru": "Проекты"},
        "open_work_label": {"en": "Open work", "lv": "Atvērts darbs", "ru": "Открытая работа"},
        "need_attention": {"en": "Need attention", "lv": "Jāpievērš uzmanība", "ru": "Требует внимания"},
        "finance": {"en": "Finance", "lv": "Finanses", "ru": "Финансы"},
        "active": {"en": "Active", "lv": "Aktīvs", "ru": "Активно"},
        "view_global": {"en": "View Global Network →", "lv": "Skatīt globālo tīklu →", "ru": "Смотреть глобальную сеть →"},
        "crm": {"en": "CRM", "lv": "CRM", "ru": "CRM"},
        "ai_workforce": {"en": "AI workforce", "lv": "AI darbinieki", "ru": "AI-команда"},
        "estimates": {"en": "Estimates", "lv": "Tāmes", "ru": "Сметы"},
        "in_progress": {"en": "In progress", "lv": "Procesā", "ru": "В работе"},
        "due_sent": {"en": "Due / sent", "lv": "Termiņš / nosūtīts", "ru": "К оплате / отправлено"},
        "tasks_sub": {"en": "Live task and follow-up queue from NinaOS workspace.", "lv": "Dzīvā uzdevumu un atkārtoto kontaktu rinda no NinaOS darba vides.", "ru": "Живая очередь задач и повторных контактов из NinaOS."},
        "clients_sub": {"en": "CRM workspace for client work, follow-ups, estimates and invoices.", "lv": "CRM darba vide klientiem, follow-upiem, tāmēm un rēķiniem.", "ru": "CRM для клиентов, повторных контактов, смет и счетов."},
        "projects_sub": {"en": "Project operations view with linked client work.", "lv": "Projektu darba skats ar piesaistītiem klientu darbiem.", "ru": "Проектный вид с привязанной клиентской работой."},
        "workers_sub": {"en": "AI workforce control surface.", "lv": "AI darbinieku vadības panelis.", "ru": "Панель управления AI-работниками."},
        "exchange_sub": {"en": "AI Workers Marketplace — preview catalog.", "lv": "AI darbinieku birža — kataloga priekšskatījums.", "ru": "Маркетплейс AI-работников — предпросмотр каталога."},
        "calendar_sub": {"en": "Schedule and due work preview.", "lv": "Grafika un termiņu darba priekšskatījums.", "ru": "Расписание и задачи по срокам."},
        "files_sub": {"en": "Document workspace for client and project files.", "lv": "Dokumentu darba vide klientu un projektu failiem.", "ru": "Документы клиентов и проектов."},
        "analytics_sub": {"en": "Operational workspace analytics preview.", "lv": "Darba vides operatīvās analītikas priekšskatījums.", "ru": "Операционная аналитика рабочей среды."},
        "open_work_action": {"en": "Open work", "lv": "Atvērt darbus", "ru": "Открыть работу"},
        "view_details": {"en": "View Details", "lv": "Skatīt detaļas", "ru": "Подробнее"},
        "today": {"en": "today", "lv": "šodien", "ru": "сегодня"},
        "attention": {"en": "attention", "lv": "uzmanība", "ru": "внимание"},
        "office_manager": {"en": "Nina Office Manager", "lv": "Nina Office Manager", "ru": "Nina Office Manager"},
        "worker_detail_sub": {"en": "Main desktop control center for the first ready AI worker.", "lv": "Galvenais vadības centrs pirmajam gatavajam AI darbiniekam.", "ru": "Главный центр управления первым готовым AI-работником."},
        "role_stack": {"en": "Role Stack", "lv": "Lomu steks", "ru": "Стек ролей"},
        "approval_required": {"en": "Approval Required", "lv": "Vajadzīgs apstiprinājums", "ru": "Требуется подтверждение"},
        "allowed_tools": {"en": "Allowed Tools", "lv": "Atļautie rīki", "ru": "Разрешённые инструменты"},
        "memory_scopes": {"en": "Memory Scopes", "lv": "Atmiņas zonas", "ru": "Области памяти"},
        "permissions": {"en": "Permissions", "lv": "Atļaujas", "ru": "Права"},
        "worker_summary": {"en": "Worker Summary", "lv": "Darbinieka pārskats", "ru": "Сводка работника"},
        "linked_work": {"en": "Linked Work", "lv": "Piesaistītie darbi", "ru": "Связанная работа"},
        "quick_actions": {"en": "Quick Actions", "lv": "Ātrās darbības", "ru": "Быстрые действия"},
        "ask_nina": {"en": "Ask Nina", "lv": "Jautāt Ninai", "ru": "Спросить Нину"},
        "new_task": {"en": "New Task", "lv": "Jauns uzdevums", "ru": "Новая задача"},
        "followup_client": {"en": "Follow-up Client", "lv": "Sazināties ar klientu", "ru": "Повторно связаться"},
        "create_estimate": {"en": "Create Estimate Draft", "lv": "Izveidot tāmes melnrakstu", "ru": "Создать черновик сметы"},
        "create_invoice": {"en": "Create Invoice Admin Record", "lv": "Izveidot rēķina ierakstu", "ru": "Создать запись счёта"},
        "upload_document": {"en": "Upload Document", "lv": "Augšupielādēt dokumentu", "ru": "Загрузить документ"},
        "open_office_manager": {"en": "Open Office Manager", "lv": "Atvērt Office Manager", "ru": "Открыть Office Manager"},
        "action_panels": {"en": "Action Panels", "lv": "Darbību paneļi", "ru": "Панели действий"},
        "task_panel": {"en": "Task Panel", "lv": "Uzdevumu panelis", "ru": "Панель задач"},
        "followup_panel": {"en": "Follow-up Panel", "lv": "Follow-up panelis", "ru": "Панель повторных контактов"},
        "estimate_panel": {"en": "Estimate Panel", "lv": "Tāmju panelis", "ru": "Панель смет"},
        "invoice_panel": {"en": "Invoice Panel", "lv": "Rēķinu panelis", "ru": "Панель счетов"},
        "document_panel": {"en": "Document Panel", "lv": "Dokumentu panelis", "ru": "Панель документов"},
        "approval_queue": {"en": "Approval Queue", "lv": "Apstiprinājumu rinda", "ru": "Очередь подтверждений"},
        "create_task_hint": {"en": "Create and organize daily work.", "lv": "Izveido un sakārto dienas darbus.", "ru": "Создать и организовать работу дня."},
        "followup_hint": {"en": "Track repeated client contact.", "lv": "Sekot atkārtotai klientu saziņai.", "ru": "Отслеживать повторный контакт с клиентом."},
        "estimate_hint": {"en": "Draft offers and estimates.", "lv": "Sagatavot piedāvājumus un tāmes.", "ru": "Готовить предложения и сметы."},
        "invoice_hint": {"en": "Track sent and due invoice records.", "lv": "Sekot nosūtītiem un termiņa rēķiniem.", "ru": "Отслеживать счета и сроки оплаты."},
        "document_hint": {"en": "Link client and project documents.", "lv": "Piesaistīt klientu un projektu dokumentus.", "ru": "Привязать документы клиентов и проектов."},
        "approval_hint": {"en": "Owner confirmation before sensitive actions.", "lv": "Īpašnieka apstiprinājums pirms svarīgām darbībām.", "ru": "Подтверждение владельца перед важными действиями."},
        "open_panel": {"en": "Open Panel", "lv": "Atvērt paneli", "ru": "Открыть панель"},
        "no_approvals": {"en": "No approvals waiting.", "lv": "Nav gaidošu apstiprinājumu.", "ru": "Нет ожидающих подтверждений."},
        "next_step": {"en": "Next step", "lv": "Nākamais solis", "ru": "Следующий шаг"},
        "work_console": {"en": "Work Console", "lv": "Darba konsole", "ru": "Рабочая консоль"},
        "today_queue": {"en": "Today Queue", "lv": "Šodienas rinda", "ru": "Очередь на сегодня"},
        "followups_due": {"en": "Follow-ups Due", "lv": "Follow-up termiņi", "ru": "Повторные контакты"},
        "finance_queue": {"en": "Finance Queue", "lv": "Finanšu rinda", "ru": "Финансовая очередь"},
        "documents": {"en": "Documents", "lv": "Dokumenti", "ru": "Документы"},
        "pending_items": {"en": "Pending Items", "lv": "Gaidošie darbi", "ru": "Ожидающие элементы"},
        "owner_control": {"en": "Owner Control", "lv": "Īpašnieka kontrole", "ru": "Контроль владельца"},
        "worker_status": {"en": "Worker Status", "lv": "Darbinieka statuss", "ru": "Статус работника"},
        "active_worker": {"en": "Active worker", "lv": "Aktīvs darbinieks", "ru": "Активный работник"},
        "data_source": {"en": "Data source", "lv": "Datu avots", "ru": "Источник данных"},
        "no_items": {"en": "No items yet.", "lv": "Pagaidām nav ierakstu.", "ru": "Пока нет элементов."},
        "status_ready": {"en": "Ready", "lv": "Gatavs", "ru": "Готов"},
        "system_safe": {"en": "Safe mode", "lv": "Drošais režīms", "ru": "Безопасный режим"},
        "open_tasks": {"en": "Open tasks", "lv": "Atvērt uzdevumus", "ru": "Открыть задачи"},
        "open_clients": {"en": "Open clients", "lv": "Atvērt klientus", "ru": "Открыть клиентов"},
        "open_files": {"en": "Open files", "lv": "Atvērt failus", "ru": "Открыть файлы"},
        "console_sub": {"en": "What Nina Office Manager is handling right now.", "lv": "Ko Nina Office Manager šobrīd apstrādā.", "ru": "Что сейчас обрабатывает Nina Office Manager."},
        "action_center": {"en": "Action Center", "lv": "Darbību centrs", "ru": "Центр действий"},
        "action_center_sub": {"en": "Create operational work from the Office Manager console.", "lv": "Izveido operatīvos darbus no Office Manager konsoles.", "ru": "Создать рабочие элементы из консоли Office Manager."},
        "task_title": {"en": "Task title", "lv": "Uzdevuma nosaukums", "ru": "Название задачи"},
        "client_name": {"en": "Client name", "lv": "Klienta vārds", "ru": "Имя клиента"},
        "project_name": {"en": "Project name", "lv": "Projekta nosaukums", "ru": "Название проекта"},
        "amount": {"en": "Amount", "lv": "Summa", "ru": "Сумма"},
        "due_date": {"en": "Due date", "lv": "Termiņš", "ru": "Срок"},
        "notes": {"en": "Notes", "lv": "Piezīmes", "ru": "Заметки"},
        "priority": {"en": "Priority", "lv": "Prioritāte", "ru": "Приоритет"},
        "normal": {"en": "Normal", "lv": "Normāla", "ru": "Обычный"},
        "high": {"en": "High", "lv": "Augsta", "ru": "Высокий"},
        "submit_preview": {"en": "Save Preview", "lv": "Saglabāt priekšskatījumu", "ru": "Сохранить предпросмотр"},
        "safe_note": {"en": "Safe UI mode: forms create a web preview first. Database write comes in the next sprint.", "lv": "Drošais UI režīms: formas vispirms izveido web priekšskatījumu. Datu bāzes ieraksts nāks nākamajā sprintā.", "ru": "Безопасный режим UI: формы сначала создают предпросмотр. Запись в базу — в следующем спринте."},
        "created_preview": {"en": "Preview created", "lv": "Priekšskatījums izveidots", "ru": "Предпросмотр создан"},
        "form_type": {"en": "Form type", "lv": "Formas tips", "ru": "Тип формы"},
        "new_task_form": {"en": "New Task", "lv": "Jauns uzdevums", "ru": "Новая задача"},
        "followup_form": {"en": "Follow-up Client", "lv": "Follow-up klientam", "ru": "Повторный контакт"},
        "estimate_form": {"en": "Estimate Draft", "lv": "Tāmes melnraksts", "ru": "Черновик сметы"},
        "invoice_form": {"en": "Invoice Admin Record", "lv": "Rēķina ieraksts", "ru": "Запись счёта"},
    }
    return d.get(key, {}).get(lang) or d.get(key, {}).get("en") or key


def object_to_dict(obj):
    if isinstance(obj, dict):
        data = dict(obj)
    else:
        data = {
            "object_id": getattr(obj, "object_id", ""),
            "object_type": getattr(obj, "object_type", ""),
            "title": getattr(obj, "title", ""),
            "status": getattr(obj, "status", ""),
            "priority": getattr(obj, "priority", "normal"),
            "client_id": getattr(obj, "client_id", ""),
            "project_id": getattr(obj, "project_id", ""),
            "due_date": getattr(obj, "due_date", ""),
            "metadata": getattr(obj, "metadata", {}) or {},
        }
    data.setdefault("metadata", {})
    return data


def build_clients_from_objects(objects):
    clients = {}
    for obj in objects:
        meta = obj.get("metadata", {}) if isinstance(obj.get("metadata"), dict) else {}
        name = meta.get("client_name") or obj.get("client_name") or obj.get("client_id") or ""
        if not name:
            continue
        clients.setdefault(name, {"name": name, "objects": [], "followups": 0, "estimates": 0, "invoices": 0, "projects": 0})
        clients[name]["objects"].append(obj)
        t = obj.get("object_type")
        if t == "followup_task":
            clients[name]["followups"] += 1
        if t in ["estimate", "offer"]:
            clients[name]["estimates"] += 1
        if t == "invoice":
            clients[name]["invoices"] += 1
        if t == "project":
            clients[name]["projects"] += 1
    if not clients:
        clients["Demo Client"] = {"name": "Demo Client", "objects": [], "followups": 1, "estimates": 1, "invoices": 1, "projects": 1}
    return list(clients.values())


def load_live_objects_from_app_db():
    objects = []
    database_url = os.environ.get("DATABASE_URL") or os.environ.get("POSTGRES_URL") or ""
    if not database_url:
        return objects
    try:
        import psycopg2
        conn = psycopg2.connect(database_url)
        cur = conn.cursor()
        queries = [
            "SELECT id, title, status, priority, client, deadline, raw_text, followup FROM tasks ORDER BY id DESC LIMIT 100",
            "SELECT id, title, status, priority, client_name, due_date, raw_text, followup FROM tasks ORDER BY id DESC LIMIT 100",
        ]
        rows = []
        for query in queries:
            try:
                cur.execute(query)
                rows = cur.fetchall()
                break
            except Exception:
                conn.rollback()
        for row in rows:
            object_id, title, status, priority, client, due, raw_text, followup = row
            obj_type = "followup_task" if bool(followup) else "task"
            objects.append({
                "object_id": f"db_task_{object_id}",
                "object_type": obj_type,
                "title": title or raw_text or "Untitled task",
                "status": status or "open",
                "priority": priority or "normal",
                "client_id": client or "",
                "project_id": "",
                "due_date": due or "",
                "metadata": {"client_name": client or "", "owner": "Telegram Nina", "source": "database"},
            })
        cur.close()
        conn.close()
    except Exception:
        return []
    return objects


def load_workspace_data():
    workers = [
        {"name": "Nina Sales", "role": "AI Sales Executive", "status": "ACTIVE", "detail": "1 follow-up to handle", "tone": "purple", "price": "€99/month", "category": "Sales & Growth"},
        {"name": "Nina Estimator", "role": "AI Estimator", "status": "ACTIVE", "detail": "1 estimate in progress", "tone": "blue", "price": "€119/month", "category": "Construction"},
        {"name": "Nina Office Manager", "role": "AI Office Manager", "status": "ACTIVE", "detail": "1 task · 1 active project", "tone": "green", "price": "€89/month", "category": "Operations", "route": "/workers/office-manager"},
        {"name": "Nina Support", "role": "AI Support Specialist", "status": "IDLE", "detail": "No support queue yet", "tone": "orange", "price": "€79/month", "category": "Support"},
    ]
    objects = []
    try:
        from work_objects import list_work_objects, seed_demo_work_objects
        try:
            seed_demo_work_objects()
        except Exception:
            pass
        try:
            objects = list_work_objects(workspace_id="demo_small_business") or []
        except TypeError:
            objects = list_work_objects() or []
    except Exception:
        objects = []

    normalized = [object_to_dict(o) for o in objects]
    live_objects = load_live_objects_from_app_db()
    if live_objects:
        normalized = live_objects

    if not normalized:
        normalized = [
            {"object_id": "task_1", "object_type": "task", "title": "Prepare today workspace priorities", "status": "open", "priority": "high", "client_id": "", "project_id": "", "due_date": "today", "metadata": {"client_name": "", "owner": "Nina Office Manager"}},
            {"object_id": "followup_1", "object_type": "followup_task", "title": "Follow up with Demo Client about offer", "status": "scheduled", "priority": "normal", "client_id": "demo_client", "project_id": "", "due_date": "friday", "metadata": {"client_name": "Demo Client", "owner": "Nina Sales"}},
            {"object_id": "estimate_1", "object_type": "estimate", "title": "Demo estimate draft", "status": "draft", "priority": "normal", "client_id": "demo_client", "project_id": "project_1", "due_date": "", "metadata": {"client_name": "Demo Client", "owner": "Nina Estimator"}},
            {"object_id": "invoice_1", "object_type": "invoice", "title": "Demo invoice follow-up", "status": "sent", "priority": "normal", "client_id": "demo_client", "project_id": "project_1", "due_date": "today", "metadata": {"client_name": "Demo Client", "owner": "Nina Office Manager"}},
            {"object_id": "project_1", "object_type": "project", "title": "Demo active project", "status": "active", "priority": "normal", "client_id": "demo_client", "project_id": "project_1", "due_date": "", "metadata": {"client_name": "Demo Client", "owner": "Nina Office Manager"}},
        ]

    activity = [
        {"title": "Web service online", "body": "NinaOS web runtime is separated from Telegram runtime.", "kind": "info"},
        {"title": "Workspace loaded", "body": "V36 clean workspace data layer is active.", "kind": "info"},
        {"title": "Client follow-up scheduled", "body": "Ask Andris about reply.", "kind": "work"},
        {"title": "Exchange preview visible", "body": "AI worker catalog is available inside the web product.", "kind": "api"},
    ]

    active_statuses = ["open", "scheduled", "draft", "sent", "active", "in_progress"]
    tasks = [o for o in normalized if o.get("object_type") in ["task", "followup_task", "estimate", "invoice"]]
    clients = build_clients_from_objects(normalized)
    projects = [o for o in normalized if o.get("object_type") == "project"]
    counts = {
        "tasks_today": len([o for o in normalized if o.get("object_type") == "task" and o.get("status") in active_statuses]),
        "followups": len([o for o in normalized if o.get("object_type") == "followup_task" and o.get("status") in active_statuses]),
        "invoices": len([o for o in normalized if o.get("object_type") == "invoice" and o.get("status") in active_statuses]),
        "estimates": len([o for o in normalized if o.get("object_type") in ["estimate", "offer"] and o.get("status") in active_statuses]),
        "projects": len([o for o in normalized if o.get("object_type") == "project" and o.get("status") in active_statuses]),
        "clients": len(clients),
        "workers": len(workers),
    }
    return {"owner": "Katrin", "workers": workers, "objects": normalized, "tasks": tasks, "clients": clients, "projects": projects, "activity": activity, "counts": counts}


def nina_logo_html(size="small"):
    return "<div class='nina-logo " + size + "'><div class='dot-grid'></div><div class='orbit orbit-a'></div><div class='orbit orbit-b'></div></div>"


def css():
    return """
:root{--line:rgba(120,153,255,.26);--line2:rgba(255,255,255,.08);--text:#f8fbff;--muted:#a8b7d4;--green:#34e6a4;--shadow:0 30px 100px rgba(0,0,0,.36)}*{box-sizing:border-box}body{margin:0;min-height:100vh;color:var(--text);font-family:Inter,Segoe UI,Arial,sans-serif;background:radial-gradient(circle at 13% 14%,rgba(30,105,255,.20),transparent 25%),radial-gradient(circle at 80% 12%,rgba(80,70,255,.20),transparent 28%),linear-gradient(135deg,#080910 0%,#0a0d19 48%,#05060b 100%)}body:before{content:"";position:fixed;inset:0;pointer-events:none;background:linear-gradient(rgba(255,255,255,.026) 1px,transparent 1px),linear-gradient(90deg,rgba(255,255,255,.021) 1px,transparent 1px);background-size:44px 44px;mask-image:linear-gradient(to bottom,rgba(0,0,0,.5),transparent 70%)}a{color:inherit;text-decoration:none}.layout{display:grid;grid-template-columns:210px 1fr;min-height:100vh}.sidebar{position:sticky;top:0;height:100vh;padding:22px 14px;background:radial-gradient(circle at 28px 28px,rgba(44,142,255,.24),transparent 75px),linear-gradient(180deg,rgba(18,22,37,.86),rgba(8,9,15,.83));border-right:1px solid var(--line2);backdrop-filter:blur(16px)}.brand{display:flex;align-items:center;gap:10px;margin:0 6px 28px;font-weight:950}.brand-word span:last-child{color:#2a91ff}
.nina-logo{position:relative;border-radius:50%;overflow:hidden;background:radial-gradient(circle at 30% 30%,rgba(255,255,255,.9),transparent 5%),radial-gradient(circle at 65% 25%,rgba(84,232,255,.9),transparent 10%),radial-gradient(circle at 50% 50%,#1de0ff 0%,#2358ff 38%,#7f45ff 72%,#11152a 100%);box-shadow:0 0 24px rgba(49,140,255,.52),inset 0 0 30px rgba(255,255,255,.12)}.nina-logo.small{width:34px;height:34px}.nina-logo.hero{width:156px;height:156px;flex:0 0 156px}.dot-grid{position:absolute;inset:0;background:radial-gradient(circle,rgba(255,255,255,.86) 0 2px,transparent 2.8px);background-size:16px 16px;transform:rotate(-18deg) scale(1.1);opacity:.58;mask-image:radial-gradient(circle,#000 62%,transparent 70%)}.orbit{position:absolute;left:-22%;right:-22%;top:44%;height:2px;background:rgba(255,255,255,.45);border-radius:999px;transform:rotate(-16deg);box-shadow:0 0 14px rgba(90,190,255,.8)}.orbit-b{transform:rotate(28deg);opacity:.28;top:54%}.nav{display:flex;flex-direction:column;gap:7px}.nav-item{display:flex;align-items:center;gap:10px;padding:11px 12px;border-radius:13px;color:#dce7ff;font-size:14px;border:1px solid transparent}.nav-item:hover{background:rgba(255,255,255,.06)}.nav-item.active{background:linear-gradient(90deg,rgba(28,128,255,.95),rgba(90,63,255,.86));color:#fff;box-shadow:0 14px 32px rgba(23,109,255,.23)}.new{margin-left:auto;font-size:10px;padding:2px 7px;border-radius:999px;background:#5638ff}.user{position:absolute;bottom:18px;left:14px;right:14px;border:1px solid var(--line);background:rgba(255,255,255,.045);border-radius:16px;padding:12px;color:var(--muted);font-size:13px}.user b{color:#fff}
.main{padding:22px 26px 40px;max-width:1460px;width:100%;margin:0 auto}.topbar{display:flex;justify-content:space-between;align-items:center;margin-bottom:18px}.search{width:min(520px,55vw);border:1px solid var(--line);border-radius:18px;padding:14px 18px;color:var(--muted);background:rgba(16,24,45,.72);box-shadow:inset 0 0 0 1px rgba(255,255,255,.03),0 12px 34px rgba(0,0,0,.18)}.icons{display:flex;gap:10px;align-items:center}.icon{width:34px;height:34px;border-radius:50%;display:grid;place-items:center;background:rgba(255,255,255,.07);border:1px solid rgba(255,255,255,.10)}.avatar{background:linear-gradient(135deg,#7c43ff,#dc42ff);font-weight:950}.lang-switch{display:flex;gap:6px}.lang-switch a{font-size:12px;font-weight:950;padding:8px 9px;border-radius:999px;border:1px solid rgba(255,255,255,.10);background:rgba(255,255,255,.06);color:#dbe8ff}.lang-switch a.active{background:linear-gradient(90deg,#168dff,#6443ff);color:#fff}.grid{display:grid;gap:18px}.hero-grid{display:grid;grid-template-columns:1.02fr .98fr;gap:18px}.card{background:linear-gradient(180deg,rgba(26,36,68,.72),rgba(9,12,24,.70)),radial-gradient(circle at 25% 15%,rgba(40,140,255,.12),transparent 38%);border:1px solid var(--line);border-radius:24px;box-shadow:var(--shadow);backdrop-filter:blur(18px)}.card-pad{padding:24px}.hero-card{min-height:390px;display:flex;flex-direction:column;justify-content:center;align-items:center;text-align:center}.hero-lockup{display:flex;align-items:center;justify-content:center;gap:26px}.hero-title{font-size:78px;line-height:.9;font-weight:1000;letter-spacing:-5px;text-shadow:0 10px 40px rgba(0,0,0,.5)}.hero-title span{color:#2493ff}.subtitle{color:#dbe8ff;font-weight:900;letter-spacing:2px;font-size:13px;margin-top:10px}.bigline{margin-top:34px;font-size:25px;line-height:1.35;font-weight:950}.trust{display:flex;gap:8px;justify-content:center;flex-wrap:wrap;margin-top:24px}.trust span{font-size:12px;font-weight:900;padding:7px 12px;border:1px solid var(--line);background:rgba(255,255,255,.04);border-radius:999px}.kpis{display:grid;grid-template-columns:repeat(4,1fr);gap:12px}.kpi{display:block;padding:18px;border:1px solid var(--line);background:linear-gradient(180deg,rgba(255,255,255,.06),rgba(255,255,255,.025));border-radius:18px;min-height:118px}.kpi small{color:#dbe7ff;font-weight:900}.kpi strong{display:block;font-size:38px;margin:9px 0 2px}.kpi em{color:#71e9ff;font-style:normal;font-size:13px;font-weight:900}.page-title h1{margin:0;font-size:42px;letter-spacing:-1.8px;line-height:1}.page-title p{margin:8px 0 0;color:#c3d4f5;font-weight:800}.section-title{font-size:21px;font-weight:1000;margin:6px 0 13px}.worker-grid{display:grid;grid-template-columns:repeat(4,minmax(160px,1fr));gap:16px}.worker-card{overflow:hidden;border-radius:20px;border:1px solid var(--line);background:linear-gradient(180deg,rgba(28,35,60,.78),rgba(9,12,24,.78));min-height:248px;box-shadow:0 20px 55px rgba(0,0,0,.22)}.worker-top{height:112px;display:grid;place-items:center;position:relative;overflow:hidden}.worker-top:before{content:"";position:absolute;inset:0;background:repeating-linear-gradient(110deg,rgba(255,255,255,.10) 0 2px,transparent 2px 10px);opacity:.35}.tone-purple{background:linear-gradient(135deg,#4830d8,#6322b7)}.tone-blue{background:linear-gradient(135deg,#058aff,#053c8c)}.tone-green{background:linear-gradient(135deg,#02b973,#095a3b)}.tone-orange{background:linear-gradient(135deg,#d47418,#56321c)}.worker-avatar{position:relative;z-index:1;width:82px;height:82px;border-radius:50%;background:radial-gradient(circle at 36% 30%,#ffe8c8 0 16%,transparent 17%),radial-gradient(circle at 53% 65%,#ffdba8 0 23%,transparent 24%),radial-gradient(circle at 46% 45%,#ef973a 0 45%,#5d3928 46% 62%,#f6c58b 63% 100%);box-shadow:0 16px 34px rgba(0,0,0,.32)}.worker-body{padding:16px}.worker-body h3{margin:0 0 4px;font-size:20px;line-height:1.02}.muted{color:var(--muted)}.status{font-weight:950;font-size:12px;margin:10px 0}.active-dot{color:var(--green)}.idle-dot{color:#ffd057}.two-col{display:grid;grid-template-columns:1fr 1fr;gap:18px}.list{display:flex;flex-direction:column;gap:10px}.row{display:flex;justify-content:space-between;align-items:center;gap:12px;padding:14px 15px;border:1px solid var(--line);border-radius:16px;background:linear-gradient(90deg,rgba(28,111,255,.12),rgba(255,255,255,.035))}.row b{display:block;margin-bottom:4px}.pill{display:inline-flex;align-items:center;padding:7px 11px;border-radius:999px;background:rgba(31,124,255,.16);border:1px solid rgba(76,147,255,.32);color:#d7e8ff;font-size:12px;font-weight:950;white-space:nowrap}.btns{display:flex;gap:12px;flex-wrap:wrap;justify-content:center}.btn{display:inline-flex;align-items:center;justify-content:center;padding:13px 18px;border-radius:14px;border:1px solid var(--line);font-weight:950;background:rgba(255,255,255,.055);box-shadow:0 12px 26px rgba(0,0,0,.18)}.btn.primary{background:linear-gradient(90deg,#168dff,#6443ff);border-color:transparent}.footer-note{margin-top:22px;color:var(--muted);font-size:13px;text-align:center;font-weight:700}.console-nav{display:flex;gap:10px;flex-wrap:wrap;margin-bottom:16px}.console-nav a{padding:10px 13px;border-radius:999px;border:1px solid var(--line);background:rgba(255,255,255,.055);font-weight:950}.console-nav a.primary{background:linear-gradient(90deg,#168dff,#6443ff);border-color:transparent}.metric-strip{display:grid;grid-template-columns:repeat(6,1fr);gap:10px}.metric-mini{padding:13px;border:1px solid var(--line);border-radius:16px;background:rgba(255,255,255,.045)}.metric-mini small{color:var(--muted);font-weight:900}.metric-mini b{display:block;font-size:24px;margin-top:4px}.panel-grid{display:grid;grid-template-columns:1.1fr .9fr;gap:18px}.stack-grid{display:grid;gap:12px}.form-grid{display:grid;grid-template-columns:repeat(2,1fr);gap:12px}.field{display:flex;flex-direction:column;gap:6px}.field label{font-size:12px;font-weight:950;color:#dbe7ff}.field input,.field select,.field textarea{width:100%;border:1px solid var(--line);border-radius:14px;background:rgba(5,9,20,.58);color:var(--text);padding:12px 13px;font:inherit;outline:none}.field textarea{min-height:92px;resize:vertical}.form-actions{display:flex;gap:10px;flex-wrap:wrap;margin-top:14px}.preview-box{border:1px solid var(--line);border-radius:18px;background:rgba(31,124,255,.10);padding:16px;margin-bottom:16px}.preview-box b{display:block;margin-bottom:6px}.safe-note{color:#8fe7ff;font-weight:800;font-size:13px;margin-top:10px}@media(max-width:1100px){.layout{grid-template-columns:1fr}.sidebar{position:relative;height:auto}.user{position:static;margin-top:18px}.hero-grid,.two-col{grid-template-columns:1fr}.worker-grid{grid-template-columns:repeat(2,1fr)}.kpis{grid-template-columns:repeat(2,1fr)}}@media(max-width:640px){.main{padding:16px}.worker-grid,.kpis{grid-template-columns:1fr}.hero-lockup{flex-direction:column}.hero-title{font-size:56px;letter-spacing:-3px}.nina-logo.hero{width:128px;height:128px;flex-basis:128px}.search{width:58vw}}
"""


def page(title, body, active="dashboard"):
    lang = current_language()
    nav = [
        ("dashboard", tx("dashboard", lang), "/dashboard", "⌂"),
        ("workers", tx("workers", lang), "/workers", "♙"),
        ("tasks", tx("tasks", lang), "/tasks", "☑"),
        ("clients", tx("clients", lang), "/clients", "●"),
        ("projects", tx("projects", lang), "/projects", "▣"),
        ("calendar", tx("calendar", lang), "/calendar", "◫"),
        ("files", tx("files", lang), "/files", "▤"),
        ("analytics", tx("analytics", lang), "/analytics", "⌁"),
        ("exchange", tx("exchange", lang), "/exchange", "◎"),
    ]
    nav_html = ""
    for key, label, href, icon in nav:
        cls = "nav-item active" if key == active else "nav-item"
        badge = "<span class='new'>NEW</span>" if key == "exchange" else ""
        nav_html += f"<a class='{cls}' href='{href}?lang={lang}'><span>{icon}</span><b>{label}</b>{badge}</a>"
    def lang_link(l):
        cls = "active" if lang == l else ""
        return f'<a class="{cls}" href="?lang={l}">{l.upper()}</a>'
    return f"""<!doctype html><html lang="{lang}"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>{html_escape(title)} · NinaOS</title><style>{css()}</style></head><body><div class="layout"><aside class="sidebar"><a href="/dashboard?lang={lang}" class="brand">{nina_logo_html("small")}<div class="brand-word"><span>Nina</span><span>OS</span></div></a><nav class="nav">{nav_html}</nav><div class="user"><b>Katrin</b><br>Owner<br><br><span class="pill">Runtime: web_app.py</span></div></aside><main class="main"><div class="topbar"><div class="search">{tx("search", lang)}</div><div class="icons"><div class="icon">🔔</div><div class="icon">🌐</div><div class="lang-switch">{lang_link("en")}{lang_link("lv")}{lang_link("ru")}</div><div class="icon">☼</div><div class="icon avatar">K</div></div></div>{body}<div class="footer-note">{WEB_APP_VERSION} · Web service separate from Telegram app.py</div></main></div></body></html>"""


def kpi_card(label, value, hint):
    return f"<a class='kpi' href='{hint.get('href', '#')}?lang={current_language()}'><small>{label}</small><strong>{value}</strong><em>{hint.get('text','Live data')}</em></a>"


def worker_card(w, marketplace=False):
    if marketplace:
        extra = f"<div class='status'>★ 4.8 · {html_escape(w.get('category',''))}</div><b>{html_escape(w.get('price',''))}</b><br><br><span class='btn'>{tx('view_details')}</span>"
    else:
        dot = "active-dot" if w["status"] == "ACTIVE" else "idle-dot"
        extra = f"<div class='status'><span class='{dot}'>●</span> {html_escape(w['status'])}</div><b>{html_escape(w['detail'])}</b>"
    return f"<a class='worker-card' href='{w.get('route','/workers')}?lang={current_language()}'><div class='worker-top tone-{w.get('tone','blue')}'><div class='worker-avatar'></div></div><div class='worker-body'><h3>{html_escape(w['name'])}</h3><div class='muted'>{html_escape(w['role'])}</div>{extra}</div></a>"


def activity_row(a):
    return f"<div class='row'><div><b>{html_escape(a.get('title'))}</b><span class='muted'>{html_escape(a.get('body'))}</span></div><span class='pill'>{html_escape(a.get('kind','info'))}</span></div>"


def dashboard_body(data):
    lang = current_language()
    c = data["counts"]
    kpis = (
        "<div class='kpis'>"
        + kpi_card(tx("tasks_today", lang), c["tasks_today"], {"text": tx("open_work_label", lang), "href": "/tasks"})
        + kpi_card(tx("followups", lang), c["followups"], {"text": tx("need_attention", lang), "href": "/tasks"})
        + kpi_card(tx("invoices", lang), c["invoices"], {"text": tx("finance", lang), "href": "/clients"})
        + kpi_card(tx("projects_kpi", lang), c["projects"], {"text": tx("active", lang), "href": "/projects"})
        + "</div>"
    )
    workers = "".join(worker_card(w) for w in data["workers"])
    activity = "".join(activity_row(a) for a in data["activity"][:6])
    snapshot_kpis = (
        kpi_card(tx("clients", lang), c["clients"], {"text": tx("crm", lang), "href": "/clients"})
        + kpi_card(tx("workers", lang), c["workers"], {"text": tx("ai_workforce", lang), "href": "/workers"})
        + kpi_card(tx("estimates", lang), c["estimates"], {"text": tx("in_progress", lang), "href": "/tasks"})
        + kpi_card(tx("invoices", lang), c["invoices"], {"text": tx("due_sent", lang), "href": "/clients"})
    )
    return f"<div class='grid'><div class='hero-grid'><section class='card card-pad hero-card'><div class='hero-lockup'>{nina_logo_html('hero')}<div><div class='hero-title'>Nina<span>OS</span></div><div class='subtitle'>AI WORKFORCE OPERATING SYSTEM</div></div></div><div class='bigline'>{tx('hero_line', lang)}</div><br><div class='btns'><a class='btn primary' href='{q('/tasks')}'>{tx('open_work', lang)}</a><a class='btn' href='{q('/exchange')}'>{tx('explore', lang)}</a></div><div class='trust'><span>GLOBAL</span><span>WORKFORCE</span><span>SECURE</span><span>SCALE</span></div></section><section class='card card-pad'><div class='page-title'><h1>{tx('good_morning', lang)}</h1><p>{tx('workspace_today', lang)}</p></div><br>{kpis}<br><div class='card card-pad' style='background:rgba(27,84,255,.16)'><div class='section-title'>{tx('global', lang)}</div><p class='muted'>{tx('connected', lang)}</p><a class='btn' href='{q('/exchange')}'>{tx('view_global', lang)}</a></div></section></div><section><div class='section-title'>{tx('your_workers', lang)}</div><div class='worker-grid'>{workers}</div></section><div class='two-col'><section class='card card-pad'><div class='section-title'>{tx('recent', lang)}</div><div class='list'>{activity}</div></section><section class='card card-pad'><div class='section-title'>{tx('snapshot', lang)}</div><div class='kpis'>{snapshot_kpis}</div><br><div class='btns'><a class='btn primary' href='{q('/tasks')}'>{tx('tasks', lang)}</a><a class='btn' href='{q('/clients')}'>{tx('clients', lang)}</a><a class='btn' href='{q('/projects')}'>{tx('projects', lang)}</a><a class='btn' href='{q('/workers')}'>{tx('workers', lang)}</a></div></section></div></div>"


def work_page_header(title, subtitle):
    return f"<div class='grid'><section class='card card-pad'><div class='page-title'><h1>{html_escape(title)}</h1><p>{html_escape(subtitle)}</p></div><br><div class='btns'><a class='btn primary' href='{q('/dashboard')}'>{tx('dashboard')}</a><a class='btn' href='{q('/tasks')}'>{tx('tasks')}</a><a class='btn' href='{q('/clients')}'>{tx('clients')}</a><a class='btn' href='{q('/workers')}'>{tx('workers')}</a><a class='btn' href='{q('/exchange')}'>{tx('exchange')}</a></div></section></div><br>"


def tasks_body(data):
    rows = ""
    for obj in data["tasks"]:
        meta = obj.get("metadata", {}) if isinstance(obj.get("metadata"), dict) else {}
        client = meta.get("client_name") or obj.get("client_id") or "Workspace"
        rows += f"<div class='row'><div><b>{html_escape(obj.get('title'))}</b><span class='muted'>{html_escape(client)} · {html_escape(obj.get('object_type'))}</span></div><span class='pill'>{html_escape(obj.get('status'))} · {html_escape(obj.get('priority'))}</span></div>"
    return work_page_header(tx("tasks"), tx("tasks_sub")) + f"<section class='card card-pad'><div class='list'>{rows}</div></section>"


def clients_body(data):
    rows = ""
    for client in data["clients"]:
        rows += f"<div class='row'><div><b>{html_escape(client.get('name'))}</b><span class='muted'>follow-ups: {client.get('followups',0)} · estimates: {client.get('estimates',0)} · invoices: {client.get('invoices',0)} · projects: {client.get('projects',0)}</span></div><a class='pill' href='{q('/tasks')}'>{tx('open_work_action')}</a></div>"
    return work_page_header(tx("clients"), tx("clients_sub")) + f"<section class='card card-pad'><div class='list'>{rows}</div></section>"


def projects_body(data):
    items = data["projects"] or [{"title":"Demo active project", "status":"active", "priority":"normal", "metadata":{"client_name":"Demo Client"}}]
    rows = ""
    for p in items:
        meta = p.get("metadata", {}) if isinstance(p.get("metadata"), dict) else {}
        rows += f"<div class='row'><div><b>{html_escape(p.get('title'))}</b><span class='muted'>{html_escape(meta.get('client_name','Workspace'))}</span></div><span class='pill'>{html_escape(p.get('status'))} · {html_escape(p.get('priority','normal'))}</span></div>"
    return work_page_header(tx("projects"), tx("projects_sub")) + f"<section class='card card-pad'><div class='list'>{rows}</div></section>"


def workers_body(data):
    lang = current_language()
    cards = ''.join(worker_card(w) for w in data['workers'])
    top = work_page_header(tx("workers"), tx("workers_sub"))
    top += f"<section class='card card-pad'><div class='section-title'>{tx('quick_actions', lang)}</div><div class='btns'><a class='btn primary' href='{q('/workers/office-manager')}'>{tx('open_office_manager', lang)}</a><a class='btn' href='{q('/exchange')}'>{tx('explore', lang)}</a></div></section><br>"
    return top + f"<div class='worker-grid'>{cards}</div>"


def exchange_body(data):
    catalog = [
        {"name": "Nina Sales", "role": "AI Sales Executive", "price": "€99/month", "category": "Sales & Growth", "tone": "purple"},
        {"name": "Nina Estimator", "role": "AI Estimator", "price": "€119/month", "category": "Construction", "tone": "blue"},
        {"name": "Nina Office Manager", "role": "AI Office Manager", "price": "€89/month", "category": "Operations", "tone": "green"},
        {"name": "Nina Support", "role": "AI Support Specialist", "price": "€79/month", "category": "Support", "tone": "orange"},
        {"name": "Nina Marketing", "role": "AI Marketing Specialist", "price": "€99/month", "category": "Marketing", "tone": "purple"},
        {"name": "Nina HR", "role": "AI HR Assistant", "price": "€89/month", "category": "HR", "tone": "orange"},
    ]
    return work_page_header(tx("exchange"), tx("exchange_sub")) + f"<div class='worker-grid'>{''.join(worker_card(w, marketplace=True) for w in catalog)}</div>"


def simple_module_body(title, subtitle, blocks):
    rows = "".join(f"<div class='row'><div><b>{html_escape(b[0])}</b><span class='muted'>{html_escape(b[1])}</span></div><span class='pill'>{html_escape(b[2])}</span></div>" for b in blocks)
    return work_page_header(title, subtitle) + f"<section class='card card-pad'><div class='list'>{rows}</div></section>"




def action_panel_card(title, hint, count, href, tone="normal"):
    return (
        "<div class='card card-pad'>"
        f"<div class='section-title'>{html_escape(title)}</div>"
        f"<p class='muted'>{html_escape(hint)}</p>"
        f"<div class='kpi'><small>{tx('active')}</small><strong>{count}</strong><em>{tx('open_work_label')}</em></div>"
        "<br>"
        f"<a class='btn primary' href='{href}'>{tx('open_panel')}</a>"
        "</div>"
    )


def office_manager_action_panels(data):
    lang = current_language()
    tasks = len([o for o in data["tasks"] if o.get("object_type") == "task"])
    followups = len([o for o in data["tasks"] if o.get("object_type") == "followup_task"])
    estimates = len([o for o in data["tasks"] if o.get("object_type") == "estimate"])
    invoices = len([o for o in data["tasks"] if o.get("object_type") == "invoice"])
    documents = 3
    approvals = 0

    return (
        f"<section class='card card-pad'><div class='section-title'>{tx('action_panels', lang)}</div>"
        "<div class='worker-grid'>"
        + action_panel_card(tx("task_panel", lang), tx("create_task_hint", lang), tasks, q("/tasks"))
        + action_panel_card(tx("followup_panel", lang), tx("followup_hint", lang), followups, q("/tasks"))
        + action_panel_card(tx("estimate_panel", lang), tx("estimate_hint", lang), estimates, q("/tasks"))
        + action_panel_card(tx("invoice_panel", lang), tx("invoice_hint", lang), invoices, q("/clients"))
        + action_panel_card(tx("document_panel", lang), tx("document_hint", lang), documents, q("/files"))
        + action_panel_card(tx("approval_queue", lang), tx("approval_hint", lang), approvals, q("/workers/office-manager"))
        + "</div></section>"
    )




def get_action_preview():
    if request.method != "POST":
        return None
    form = request.form
    return {
        "form_type": form.get("form_type", ""),
        "task_title": form.get("task_title", ""),
        "client_name": form.get("client_name", ""),
        "project_name": form.get("project_name", ""),
        "amount": form.get("amount", ""),
        "due_date": form.get("due_date", ""),
        "priority": form.get("priority", "normal"),
        "notes": form.get("notes", ""),
    }


def action_preview_html(preview):
    if not preview:
        return ""
    lang = current_language()
    labels = [
        ("form_type", tx("form_type", lang)),
        ("task_title", tx("task_title", lang)),
        ("client_name", tx("client_name", lang)),
        ("project_name", tx("project_name", lang)),
        ("amount", tx("amount", lang)),
        ("due_date", tx("due_date", lang)),
        ("priority", tx("priority", lang)),
        ("notes", tx("notes", lang)),
    ]
    rows = ""
    for key, label in labels:
        value = preview.get(key) or "—"
        rows += f"<div class='row'><div><b>{html_escape(label)}</b><span class='muted'>{html_escape(value)}</span></div><span class='pill'>preview</span></div>"
    return f"<div class='preview-box'><b>{tx('created_preview', lang)}</b><div class='list'>{rows}</div><div class='safe-note'>{tx('safe_note', lang)}</div></div>"


def action_form_card(form_type, title, hint, defaults=None):
    lang = current_language()
    defaults = defaults or {}
    action = q("/office-manager/actions")
    return f"""
    <section class='card card-pad'>
      <div class='section-title'>{html_escape(title)}</div>
      <p class='muted'>{html_escape(hint)}</p>
      <form method='post' action='{action}'>
        <input type='hidden' name='form_type' value='{html_escape(form_type)}'>
        <div class='form-grid'>
          <div class='field'>
            <label>{tx('task_title', lang)}</label>
            <input name='task_title' placeholder='{tx('task_title', lang)}' value='{html_escape(defaults.get('task_title',''))}'>
          </div>
          <div class='field'>
            <label>{tx('client_name', lang)}</label>
            <input name='client_name' placeholder='{tx('client_name', lang)}' value='{html_escape(defaults.get('client_name',''))}'>
          </div>
          <div class='field'>
            <label>{tx('project_name', lang)}</label>
            <input name='project_name' placeholder='{tx('project_name', lang)}' value='{html_escape(defaults.get('project_name',''))}'>
          </div>
          <div class='field'>
            <label>{tx('due_date', lang)}</label>
            <input name='due_date' placeholder='today / friday / 2026-07-10' value='{html_escape(defaults.get('due_date',''))}'>
          </div>
          <div class='field'>
            <label>{tx('amount', lang)}</label>
            <input name='amount' placeholder='€0.00' value='{html_escape(defaults.get('amount',''))}'>
          </div>
          <div class='field'>
            <label>{tx('priority', lang)}</label>
            <select name='priority'>
              <option value='normal'>{tx('normal', lang)}</option>
              <option value='high'>{tx('high', lang)}</option>
            </select>
          </div>
        </div>
        <br>
        <div class='field'>
          <label>{tx('notes', lang)}</label>
          <textarea name='notes' placeholder='{tx('notes', lang)}'>{html_escape(defaults.get('notes',''))}</textarea>
        </div>
        <div class='form-actions'>
          <button class='btn primary' type='submit'>{tx('submit_preview', lang)}</button>
          <a class='btn' href='{q('/office-manager')}'>{tx('work_console', lang)}</a>
        </div>
        <div class='safe-note'>{tx('safe_note', lang)}</div>
      </form>
    </section>
    """


def action_center_body(data):
    lang = current_language()
    preview = get_action_preview()
    forms = (
        "<div class='stack-grid'>"
        + action_form_card("new_task", tx("new_task_form", lang), tx("create_task_hint", lang))
        + action_form_card("followup", tx("followup_form", lang), tx("followup_hint", lang), {"task_title": "Follow up with client"})
        + action_form_card("estimate", tx("estimate_form", lang), tx("estimate_hint", lang), {"task_title": "Create estimate draft"})
        + action_form_card("invoice", tx("invoice_form", lang), tx("invoice_hint", lang), {"task_title": "Create invoice admin record"})
        + "</div>"
    )
    return (
        work_page_header(tx("action_center", lang), tx("action_center_sub", lang))
        + action_preview_html(preview)
        + "<div class='console-nav'>"
        + f"<a class='primary' href='{q('/office-manager/actions')}'>{tx('action_center', lang)}</a>"
        + f"<a href='{q('/office-manager')}'>{tx('work_console', lang)}</a>"
        + f"<a href='{q('/office-manager/panels')}'>{tx('action_panels', lang)}</a>"
        + f"<a href='{q('/tasks')}'>{tx('tasks', lang)}</a>"
        + f"<a href='{q('/clients')}'>{tx('clients', lang)}</a>"
        + "</div>"
        + forms
    )



def office_manager_body(data):
    lang = current_language()
    tasks = [o for o in data["tasks"] if o.get("object_type") in ["task", "followup_task"]]
    invoices = [o for o in data["tasks"] if o.get("object_type") == "invoice"]
    estimates = [o for o in data["tasks"] if o.get("object_type") == "estimate"]

    def mini_list(items, empty_text):
        if not items:
            return f"<div class='row'><div><b>{html_escape(empty_text)}</b><span class='muted'>—</span></div><span class='pill'>idle</span></div>"
        rows = ""
        for item in items[:5]:
            meta = item.get("metadata", {}) if isinstance(item.get("metadata"), dict) else {}
            client = meta.get("client_name") or item.get("client_id") or "Workspace"
            rows += f"<div class='row'><div><b>{html_escape(item.get('title'))}</b><span class='muted'>{html_escape(client)} · {html_escape(item.get('object_type'))}</span></div><span class='pill'>{html_escape(item.get('status'))}</span></div>"
        return rows

    role_rows = [
        ("Office Manager", "Coordinates daily workspace operations", "active"),
        ("Task Router", "Organizes tasks, follow-ups and due work", "active"),
        ("Client Admin", "Keeps client work visible in one place", "active"),
        ("Finance Admin", "Tracks invoice and estimate admin records", "preview"),
    ]
    role_html = "".join(f"<div class='row'><div><b>{html_escape(a)}</b><span class='muted'>{html_escape(b)}</span></div><span class='pill'>{html_escape(c)}</span></div>" for a,b,c in role_rows)

    right_blocks = "".join([
        f"<div class='row'><div><b>{tx('approval_required', lang)}</b><span class='muted'>No approval queue yet</span></div><span class='pill'>0</span></div>",
        f"<div class='row'><div><b>{tx('allowed_tools', lang)}</b><span class='muted'>tasks · clients · files · estimates · invoices</span></div><span class='pill'>safe</span></div>",
        f"<div class='row'><div><b>{tx('memory_scopes', lang)}</b><span class='muted'>workspace · client · project</span></div><span class='pill'>read</span></div>",
        f"<div class='row'><div><b>{tx('permissions', lang)}</b><span class='muted'>write_task · write_client · write_document</span></div><span class='pill'>limited</span></div>",
    ])

    quick = "".join([
        f"<a class='btn primary' href='{q('/office-manager/actions')}'>{tx('action_center', lang)}</a>",
        f"<a class='btn' href='{q('/tasks')}'>{tx('new_task', lang)}</a>",
        f"<a class='btn' href='{q('/clients')}'>{tx('followup_client', lang)}</a>",
        f"<a class='btn' href='{q('/tasks')}'>{tx('create_estimate', lang)}</a>",
        f"<a class='btn' href='{q('/clients')}'>{tx('create_invoice', lang)}</a>",
        f"<a class='btn' href='{q('/files')}'>{tx('upload_document', lang)}</a>",
    ])

    return (
        work_page_header(tx("office_manager", lang), tx("worker_detail_sub", lang))
        + "<div class='hero-grid'>"
        + "<section class='card card-pad'>"
        + f"<div class='section-title'>{tx('worker_summary', lang)}</div>"
        + "<div class='row'><div><b>Nina Office Manager SMB</b><span class='muted'>AI Office Manager · ACTIVE · Operations</span></div><span class='pill'>ready</span></div>"
        + "<br><div class='kpis'>"
        + kpi_card(tx("tasks_today", lang), data["counts"]["tasks_today"], {"text": tx("open_work_label", lang), "href": "/tasks"})
        + kpi_card(tx("followups", lang), data["counts"]["followups"], {"text": tx("need_attention", lang), "href": "/tasks"})
        + kpi_card(tx("invoices", lang), data["counts"]["invoices"], {"text": tx("finance", lang), "href": "/clients"})
        + kpi_card(tx("projects_kpi", lang), data["counts"]["projects"], {"text": tx("active", lang), "href": "/projects"})
        + "</div><br>"
        + f"<div class='section-title'>{tx('role_stack', lang)}</div><div class='list'>{role_html}</div>"
        + "</section>"
        + "<section class='card card-pad'>"
        + f"<div class='section-title'>{tx('quick_actions', lang)}</div><div class='btns'>{quick}</div><br>"
        + f"<div class='section-title'>{tx('approval_required', lang)}</div><div class='list'>{right_blocks}</div>"
        + "</section>"
        + "</div><br>"
        + office_manager_action_panels(data)
        + "<br><div class='two-col'>"
        + f"<section class='card card-pad'><div class='section-title'>{tx('linked_work', lang)}</div><div class='list'>{mini_list(tasks, 'No task queue yet')}</div></section>"
        + f"<section class='card card-pad'><div class='section-title'>{tx('estimates', lang)} / {tx('invoices', lang)}</div><div class='list'>{mini_list(estimates + invoices, 'No finance admin queue yet')}</div></section>"
        + "</div>"
    )



@app.route("/")
def home():
    return redirect(q("/dashboard"))


@app.route("/dashboard")
def dashboard():
    data = load_workspace_data()
    return Response(page(tx("dashboard"), dashboard_body(data), active="dashboard"), mimetype="text/html")


@app.route("/workers")
def workers():
    data = load_workspace_data()
    return Response(page(tx("workers"), workers_body(data), active="workers"), mimetype="text/html")


@app.route("/office-manager")
def office_manager_short():
    data = load_workspace_data()
    return Response(page(tx("office_manager"), office_manager_body(data), active="workers"), mimetype="text/html")


@app.route("/office-manager/console")
def office_manager_console():
    data = load_workspace_data()
    return Response(page(tx("office_manager"), office_manager_body(data), active="workers"), mimetype="text/html")


@app.route("/office-manager/panels")
def office_manager_panels():
    data = load_workspace_data()
    body = work_page_header(tx("action_panels"), tx("worker_detail_sub")) + office_manager_action_panels(data)
    return Response(page(tx("action_panels"), body, active="workers"), mimetype="text/html")


@app.route("/office-manager/actions", methods=["GET", "POST"])
def office_manager_actions():
    data = load_workspace_data()
    return Response(page(tx("action_center"), action_center_body(data), active="workers"), mimetype="text/html")


@app.route("/workers/office-manager")
def office_manager():
    data = load_workspace_data()
    return Response(page(tx("office_manager"), office_manager_body(data), active="workers"), mimetype="text/html")


@app.route("/tasks")
def tasks():
    data = load_workspace_data()
    return Response(page(tx("tasks"), tasks_body(data), active="tasks"), mimetype="text/html")


@app.route("/clients")
def clients():
    data = load_workspace_data()
    return Response(page(tx("clients"), clients_body(data), active="clients"), mimetype="text/html")


@app.route("/projects")
def projects():
    data = load_workspace_data()
    return Response(page(tx("projects"), projects_body(data), active="projects"), mimetype="text/html")


@app.route("/calendar")
def calendar():
    body = simple_module_body(tx("calendar"), tx("calendar_sub"), [("Today", "Workspace priorities and follow-ups", "live"), ("Follow-up Friday", "Ask Andris about reply", "scheduled"), ("Upcoming", "Calendar integration placeholder", "next")])
    return Response(page(tx("calendar"), body, active="calendar"), mimetype="text/html")


@app.route("/files")
def files():
    body = simple_module_body(tx("files"), tx("files_sub"), [("Demo client package", "Ready for organization", "document"), ("Invoice admin record", "Linked to workspace", "finance"), ("Estimate draft", "Linked to Demo Client", "estimate")])
    return Response(page(tx("files"), body, active="files"), mimetype="text/html")


@app.route("/analytics")
def analytics():
    data = load_workspace_data()
    c = data["counts"]
    body = work_page_header(tx("analytics"), tx("analytics_sub"))
    body += (
        "<section class='card card-pad'><div class='kpis'>"
        + kpi_card(tx("tasks"), c["tasks_today"], {"text": tx("today"), "href": "/tasks"})
        + kpi_card(tx("followups"), c["followups"], {"text": tx("attention"), "href": "/tasks"})
        + kpi_card(tx("clients"), c["clients"], {"text": tx("crm"), "href": "/clients"})
        + kpi_card(tx("workers"), c["workers"], {"text": tx("active"), "href": "/workers"})
        + "</div></section>"
    )
    return Response(page(tx("analytics"), body, active="analytics"), mimetype="text/html")


@app.route("/exchange")
def exchange():
    data = load_workspace_data()
    return Response(page(tx("exchange"), exchange_body(data), active="exchange"), mimetype="text/html")


@app.route("/health")
def health():
    return {"ok": True, "runtime": "web_app.py", "version": WEB_APP_VERSION, "language": current_language(), "time": datetime.utcnow().isoformat() + "Z"}


if __name__ == "__main__":
    port = safe_int(os.environ.get("PORT"), 8080)
    app.run(host="0.0.0.0", port=port)
