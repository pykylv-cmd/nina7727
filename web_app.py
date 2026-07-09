# web_app.py
# NinaOS Web App V45.4 FIX — Thread Type Classifier Polish
# Web service start command: python web_app.py
# Telegram service start command stays: python app.py

import os
from datetime import datetime
from flask import Flask, Response, redirect, request

WEB_APP_VERSION = "Web App V45.4 FIX — Thread Type Classifier Polish"
app = Flask(__name__)

# V45.4 safe in-memory workspace preview store + client work thread bridge.
# This does NOT write to Postgres yet and does NOT touch Telegram app.py.
# Telegram remains its own runtime; web_app.py only reads/surfaces shared intake/work data.
WORKSPACE_ACTION_PREVIEWS = []
LAST_VOICE_INTAKE_PREVIEW = None


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
        "safe_note": {"en": "V43.4 safe mode: approved previews are surfaced as real workspace work across Dashboard, Tasks and Office Manager. Postgres write bridge comes next.", "lv": "V43.4 drošais režīms: apstiprināti preview darbi redzami kā īsti darba vides darbi Dashboard, Uzdevumos un Office Manager. Postgres bridge nāks nākamais.", "ru": "V43.4 безопасный режим: подтверждённые preview задачи видны как реальные рабочие элементы в Dashboard, Tasks и Office Manager. Postgres bridge — следующий."},
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
        "workspace_preview_queue": {"en": "Workspace Preview Queue", "lv": "Darba vides priekšskatījumu rinda", "ru": "Очередь предпросмотра рабочего пространства"},
        "all_workspace_work": {"en": "All Workspace Work", "lv": "Visi darba vides darbi", "ru": "Вся рабочая очередь"},
        "source_preview": {"en": "web preview", "lv": "web priekšskatījums", "ru": "web предпросмотр"},
        "source_database": {"en": "database", "lv": "datu bāze", "ru": "база данных"},
        "source_demo": {"en": "demo data", "lv": "demo dati", "ru": "демо данные"},
        "source_workspace": {"en": "workspace", "lv": "darba vide", "ru": "рабочее пространство"},
        "preview_approval_layer": {"en": "Preview Approval Layer", "lv": "Priekšskatījumu apstiprināšanas slānis", "ru": "Слой подтверждения предпросмотра"},
        "approval_state": {"en": "Approval state", "lv": "Apstiprinājuma statuss", "ru": "Статус подтверждения"},
        "pending_approval": {"en": "pending approval", "lv": "gaida apstiprinājumu", "ru": "ожидает подтверждения"},
        "approved_preview": {"en": "approved preview", "lv": "apstiprināts preview", "ru": "предпросмотр подтверждён"},
        "held_preview": {"en": "held preview", "lv": "aizturēts preview", "ru": "предпросмотр удержан"},
        "rejected_preview": {"en": "rejected preview", "lv": "noraidīts preview", "ru": "предпросмотр отклонён"},
        "approve": {"en": "Approve", "lv": "Apstiprināt", "ru": "Подтвердить"},
        "hold": {"en": "Hold", "lv": "Aizturēt", "ru": "Удержать"},
        "reject": {"en": "Reject", "lv": "Noraidīt", "ru": "Отклонить"},
        "approved_safe_note": {"en": "Approved in safe preview only. DB write is still disabled.", "lv": "Apstiprināts tikai drošajā priekšskatījumā. DB rakstīšana vēl ir izslēgta.", "ru": "Подтверждено только в безопасном предпросмотре. Запись в DB всё ещё отключена."},
        "approval_workspace_bridge": {"en": "Approval → Workspace Queue Bridge", "lv": "Apstiprinājums → darba rindas bridge", "ru": "Подтверждение → рабочая очередь"},
        "approved_workspace_queue": {"en": "Approved Workspace Queue", "lv": "Apstiprinātā darba rinda", "ru": "Подтверждённая рабочая очередь"},
        "held_preview_queue": {"en": "Held Preview Queue", "lv": "Aizturēto preview rinda", "ru": "Удержанные preview"},
        "rejected_preview_log": {"en": "Rejected Preview Log", "lv": "Noraidīto preview žurnāls", "ru": "Журнал отклонённых preview"},
        "pending_or_held": {"en": "Pending / held approvals", "lv": "Gaida / aizturēti apstiprinājumi", "ru": "Ожидает / удержано"},
        "approved_work_note": {"en": "Approved preview work is now promoted into the active workspace surfaces, but still not written to Postgres.", "lv": "Apstiprinātais preview darbs tagad ir pacelts aktīvajās darba virsmās, bet vēl nav rakstīts Postgres.", "ru": "Подтверждённая preview работа поднята в активные рабочие поверхности, но ещё не записана в Postgres."},
        "real_task_surface_bridge": {"en": "Preview → Real Task Surface Bridge", "lv": "Preview → īstā darba virsmas bridge", "ru": "Preview → мост реальной рабочей поверхности"},
        "active_workspace_queue": {"en": "Active Workspace Queue", "lv": "Aktīvā darba rinda", "ru": "Активная рабочая очередь"},
        "inbox": {"en": "Inbox", "lv": "Ienākošie", "ru": "Входящие"},
        "channel_hub": {"en": "Channel Hub", "lv": "Kanālu centrs", "ru": "Центр каналов"},
        "channel_hub_sub": {"en": "One modern intake layer for voice, WhatsApp, Telegram, files and client work.", "lv": "Viena moderna ienākošā darba kārta balsij, WhatsApp, Telegram, failiem un klientu darbiem.", "ru": "Единый современный слой входящей работы для голоса, WhatsApp, Telegram, файлов и клиентов."},
        "voice_command": {"en": "Voice Command", "lv": "Balss komanda", "ru": "Голосовая команда"},
        "voice_command_hint": {"en": "Say it once. Nina turns it into client work, tasks, documents and approvals.", "lv": "Pasaki vienreiz. Nina to pārvērš klienta darbā, uzdevumos, dokumentos un apstiprinājumos.", "ru": "Скажи один раз. Nina превращает это в клиентскую работу, задачи, документы и подтверждения."},
        "connected_channels": {"en": "Connected Channels", "lv": "Savienotie kanāli", "ru": "Подключённые каналы"},
        "whatsapp_business": {"en": "WhatsApp Business", "lv": "WhatsApp Business", "ru": "WhatsApp Business"},
        "telegram_channel": {"en": "Telegram", "lv": "Telegram", "ru": "Telegram"},
        "email_channel": {"en": "Email", "lv": "E-pasts", "ru": "Почта"},
        "files_channel": {"en": "Files / scans", "lv": "Faili / skeni", "ru": "Файлы / сканы"},
        "modern_intake": {"en": "Modern Work Intake", "lv": "Moderna darba ievade", "ru": "Современный приём работы"},
        "client_timeline": {"en": "Client Timeline", "lv": "Klienta laika līnija", "ru": "Лента клиента"},
        "owner_send_back": {"en": "Send Back to Client", "lv": "Nosūtīt atpakaļ klientam", "ru": "Отправить клиенту"},
        "ai_auto_prepare": {"en": "AI Auto-Prepare", "lv": "AI automātiskā sagatavošana", "ru": "AI автоподготовка"},
        "owner_approval_gate": {"en": "Owner Approval Gate", "lv": "Īpašnieka apstiprinājuma vārti", "ru": "Подтверждение владельца"},
        "voice_intake_form": {"en": "Voice Intake Form", "lv": "Balss darba ievade", "ru": "Форма голосового ввода"},
        "voice_intake_hint": {"en": "Paste or type what the owner/client said. Nina converts it into a safe preview work object.", "lv": "Ielīmē vai ieraksti, ko īpašnieks/klients pateica. Nina to pārvērš drošā darba priekšskatījumā.", "ru": "Вставь или напиши, что сказал владелец/клиент. Nina превратит это в безопасный preview-объект."},
        "voice_text": {"en": "Voice text", "lv": "Balss teksts", "ru": "Текст голоса"},
        "source_channel": {"en": "Source channel", "lv": "Avota kanāls", "ru": "Канал источника"},
        "nina_prepare": {"en": "Nina, prepare work", "lv": "Nina, sagatavo darbu", "ru": "Nina, подготовь работу"},
        "voice_preview_created": {"en": "Voice intake preview created", "lv": "Balss ievades priekšskatījums izveidots", "ru": "Preview из голосового ввода создан"},
        "voice_safe_note": {"en": "V45.4 FIX safe mode: Web reads existing Telegram memory, deduplicates it, and classifies client work threads more accurately. New DB writes still come later.", "lv": "V45.4 FIX drošais režīms: web lasa esošo Telegram atmiņu, noņem dublikātus un precīzāk klasificē klienta darba pavedienus. Jauna DB rakstīšana nāks vēlāk.", "ru": "Безопасный режим V45.2: web читает существующую память Telegram и task backups. Новая запись в DB — позже."},
        "detected_intent": {"en": "Detected intent", "lv": "Atpazītais nodoms", "ru": "Распознанное намерение"},
        "twenty_second_century": {"en": "22nd-century work surface: clients speak, send photos and documents; Nina organizes the work.", "lv": "22. gadsimta darba virsma: klienti runā, sūta bildes un dokumentus; Nina sakārto darbu.", "ru": "Рабочая поверхность 22 века: клиенты говорят, отправляют фото и документы; Nina организует работу."},
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



def infer_work_type_from_text(text, fallback="task"):
    low = (text or "").lower()
    if any(w in low for w in ["tāme", "tame", "estimate", "quote", "offer", "piedāvāj", "piedavaj"]):
        return "estimate"
    if any(w in low for w in ["rēķin", "rekin", "invoice", "bill"]):
        return "invoice"
    if any(w in low for w in ["piezvan", "atgādin", "atgadin", "follow", "sazin", "pajaut", "uzrakst", "atsūti", "atsuti"]):
        return "followup_task"
    if any(w in low for w in ["dokuments", "document", "pdf", "bilde", "foto", "scan", "skens"]):
        return "document_intake"
    return fallback or "task"


def telegram_intake_demo_items():
    """V45 demo/safe fallback: shows the intended sync shape when DB has no Telegram rows yet."""
    now = datetime.utcnow().isoformat() + "Z"
    demo = [
        {
            "object_id": "telegram_sync_demo_voice_1",
            "object_type": "estimate",
            "title": "Telegram voice: sagatavot tāmi vannas istabas remontam",
            "status": "synced_preview",
            "priority": "normal",
            "client_id": "Klients",
            "project_id": "",
            "due_date": "",
            "metadata": {
                "client_name": "Klients",
                "owner": "Telegram Nina",
                "source": "telegram_intake_sync",
                "source_channel": "Telegram voice",
                "intake_kind": "voice_transcript",
                "raw_text": "Nina, man vajag sagatavot tāmi klientam par vannas istabas remontu un atsūtīt WhatsApp.",
                "storage_target": "NinaOS client workspace",
                "approval_state": "pending_approval",
                "db_write": False,
                "synced_at": now,
            },
        },
        {
            "object_id": "telegram_sync_demo_followup_2",
            "object_type": "followup_task",
            "title": "Telegram intake: piektdien jāpajautā Andrim par atbildi",
            "status": "synced_preview",
            "priority": "normal",
            "client_id": "Andris",
            "project_id": "",
            "due_date": "friday",
            "metadata": {
                "client_name": "Andris",
                "owner": "Telegram Nina",
                "source": "telegram_intake_sync",
                "source_channel": "Telegram text/voice",
                "intake_kind": "followup_capture",
                "raw_text": "piektdien jāpajautā Andrim par atbildi",
                "storage_target": "NinaOS client workspace",
                "approval_state": "pending_approval",
                "db_write": False,
                "synced_at": now,
            },
        },
        {
            "object_id": "telegram_sync_demo_doc_3",
            "object_type": "document_intake",
            "title": "Telegram files/photos: klienta objekta bildes un dokumenti",
            "status": "document_intake",
            "priority": "normal",
            "client_id": "Klients",
            "project_id": "",
            "due_date": "",
            "metadata": {
                "client_name": "Klients",
                "owner": "Telegram Nina",
                "source": "telegram_intake_sync",
                "source_channel": "Telegram photo/document",
                "intake_kind": "document_photo_intake",
                "raw_text": "Photos, scans and PDFs should be stored under the client workspace.",
                "storage_target": "NinaOS client workspace",
                "approval_state": "pending_approval",
                "db_write": False,
                "synced_at": now,
            },
        },
    ]
    return demo





def extract_client_name_from_text(text):
    raw = str(text or "")
    lower = raw.lower()
    patterns = [
        r"\b(?:andrim|andri)\b",
        r"\b(?:klientam|klients|klientei)\s+([A-ZĀČĒĢĪĶĻŅŠŪŽ][\wĀČĒĢĪĶĻŅŠŪŽāčēģīķļņšūž-]{2,})",
        r"\b(?:client|customer)\s+([A-Z][\w-]{2,})",
    ]
    if "andri" in lower or "andrim" in lower:
        return "Andris"
    try:
        import re
        for pat in patterns[1:]:
            m = re.search(pat, raw)
            if m:
                return m.group(1).strip()
    except Exception:
        pass
    return ""


def _first_value(row, keys, default=""):
    for key in keys:
        if key in row and row.get(key) not in [None, ""]:
            return row.get(key)
    return default



def db_url_info():
    """Return the first usable Postgres connection URL and rich env diagnostics.

    Railway can expose database URLs under different names depending on whether
    the variable was added manually, referenced from Postgres, or generated by
    a plugin. This helper is intentionally broad and read-only. It never prints
    secret values, only the source key and a masked URL.
    """
    candidates = [
        "DATABASE_URL",
        "POSTGRES_URL",
        "POSTGRES_PRIVATE_URL",
        "POSTGRES_PUBLIC_URL",
        "DATABASE_PRIVATE_URL",
        "DATABASE_PUBLIC_URL",
        "PGURL",
        "PG_URL",
        "RAILWAY_DATABASE_URL",
        "RAILWAY_POSTGRES_URL",
        "POSTGRES_CONNECTION_URL",
        "DATABASE_CONNECTION_URL",
    ]

    found = []
    for key in candidates:
        value = os.environ.get(key)
        if value:
            found.append({"key": key, "safe": mask_db_url(value), "length": len(value)})

    # Also expose names of relevant env keys so we can debug Railway without leaking values.
    relevant_env_keys = sorted([
        k for k in os.environ.keys()
        if any(token in k.upper() for token in ["DATABASE", "POSTGRES", "PG", "RAILWAY"])
    ])

    url = ""
    source = ""
    if found:
        # Prefer DATABASE_URL when it exists, otherwise use the first available candidate.
        preferred = next((x for x in found if x["key"] == "DATABASE_URL"), found[0])
        source = preferred["key"]
        url = os.environ.get(source) or ""

    return {
        "url": url,
        "source": source,
        "safe": mask_db_url(url),
        "found": found,
        "relevant_env_keys": relevant_env_keys,
    }


def _db_url():
    return db_url_info().get("url") or ""


def load_real_intake_events_from_db(limit=50):
    """V45.1/V45.2 compatibility: read future shared intake_events table if it exists.

    This remains read-only. V45.2 does not require intake_events yet because app.py
    already stores useful Telegram work memory in memory_backups and conversation_state.
    """
    database_url = _db_url()
    if not database_url:
        return []
    conn = None
    try:
        import psycopg2
        conn = psycopg2.connect(database_url)
        cur = conn.cursor()
        cur.execute("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = 'intake_events'
        """)
        columns = [r[0] for r in cur.fetchall()]
        if not columns:
            cur.close()
            conn.close()
            return []

        order_col = "created_at" if "created_at" in columns else ("id" if "id" in columns else columns[0])
        cur.execute(f"SELECT * FROM intake_events ORDER BY {order_col} DESC LIMIT %s", (int(limit),))
        names = [d[0] for d in cur.description]
        rows = [dict(zip(names, r)) for r in cur.fetchall()]
        cur.close()
        conn.close()

        objects = []
        now = datetime.utcnow().isoformat() + "Z"
        for idx, row in enumerate(rows):
            raw_text = _first_value(row, ["raw_text", "message_text", "transcript", "text", "body", "content", "caption"], "")
            title = _first_value(row, ["title", "summary", "subject"], "") or str(raw_text or "Incoming Telegram intake")[:140]
            source_channel = _first_value(row, ["source_channel", "channel", "source", "platform"], "Telegram")
            event_type = _first_value(row, ["event_type", "intake_kind", "kind", "type", "content_type"], "telegram_intake")
            client_name = _first_value(row, ["client_name", "client", "customer_name", "contact_name", "sender_name"], "")
            priority = _first_value(row, ["priority"], "normal") or "normal"
            status = _first_value(row, ["status", "state"], "synced_preview") or "synced_preview"
            approval_state = _first_value(row, ["approval_state", "approval", "owner_state"], "pending_approval") or "pending_approval"
            object_type = _first_value(row, ["object_type", "work_type"], "") or infer_work_type_from_text(str(title) + " " + str(raw_text), "task")
            file_name = _first_value(row, ["file_name", "filename", "document_name", "attachment_name"], "")
            if file_name and object_type == "task":
                object_type = "document_intake"
            object_id = _first_value(row, ["object_id", "event_id", "id"], f"intake_event_{idx}")
            created_at = _first_value(row, ["created_at", "timestamp", "received_at"], "")
            if created_at:
                created_at = str(created_at)
            meta = {
                "client_name": client_name,
                "owner": "Telegram Nina",
                "source": "real_intake_store",
                "source_channel": source_channel,
                "intake_kind": event_type,
                "raw_text": raw_text,
                "file_name": file_name,
                "storage_target": "NinaOS client workspace",
                "approval_state": approval_state,
                "db_read": True,
                "db_write_by_web": False,
                "synced_at": now,
                "created_at": created_at,
            }
            objects.append({
                "object_id": f"intake_event_{object_id}",
                "object_type": object_type,
                "title": title or "Incoming Telegram intake",
                "status": status,
                "priority": priority,
                "client_id": client_name,
                "project_id": _first_value(row, ["project_id", "project_name"], ""),
                "due_date": _first_value(row, ["due_date", "deadline"], ""),
                "metadata": meta,
            })
        return objects
    except Exception:
        try:
            if conn:
                conn.close()
        except Exception:
            pass
        return []


def _row_get(row, index, default=""):
    try:
        return row[index]
    except Exception:
        return default


def load_existing_task_engine_memory_from_db(limit=80):
    """V45.2: read the existing app.py task memory store.

    app.py already saves detected tasks/follow-ups as JSON into memory_backups
    with source='task_engine'. Web should bridge to that before inventing a new table.
    """
    database_url = _db_url()
    if not database_url:
        return []
    conn = None
    try:
        import psycopg2, json
        conn = psycopg2.connect(database_url)
        cur = conn.cursor()
        cur.execute("""
            SELECT id, user_id, backup_text, created_at
            FROM memory_backups
            WHERE source = %s
            ORDER BY id DESC
            LIMIT %s
        """, ("task_engine", int(limit)))
        rows = cur.fetchall() or []
        cur.close()
        conn.close()

        objects = []
        now = datetime.utcnow().isoformat() + "Z"
        for row in rows:
            backup_id = _row_get(row, 0)
            user_id = _row_get(row, 1)
            backup_text = _row_get(row, 2) or ""
            created_at = str(_row_get(row, 3) or "")
            try:
                obj = json.loads(str(backup_text)) if backup_text else {}
                if not isinstance(obj, dict):
                    obj = {"title": str(backup_text)}
            except Exception:
                obj = {"title": str(backup_text)}

            title = obj.get("title") or obj.get("raw_text") or obj.get("text") or "Telegram task memory"
            obj_type = obj.get("object_type") or obj.get("type") or infer_work_type_from_text(str(title) + " " + str(obj.get("raw_text", "")), "task")
            if obj.get("followup") or obj.get("is_followup") or "follow" in str(obj_type).lower():
                obj_type = "followup_task"
            client_name = obj.get("client") or obj.get("client_name") or obj.get("contact") or obj.get("person") or ""
            due_date = obj.get("deadline") or obj.get("due_date") or obj.get("date") or ""
            priority = obj.get("priority") or "normal"
            status = obj.get("status") or "synced_preview"
            meta = dict(obj.get("metadata", {}) if isinstance(obj.get("metadata"), dict) else {})
            meta.update({
                "client_name": client_name or meta.get("client_name", ""),
                "owner": "Telegram Nina",
                "source": "existing_task_memory",
                "source_channel": "Telegram",
                "intake_kind": "task_engine_memory",
                "raw_text": obj.get("raw_text") or obj.get("text") or title,
                "storage_target": "memory_backups/source=task_engine",
                "approval_state": meta.get("approval_state") or "synced_from_existing_memory",
                "db_read": True,
                "db_write_by_web": False,
                "telegram_user_id": str(user_id or ""),
                "memory_backup_id": str(backup_id or ""),
                "created_at": created_at,
                "synced_at": now,
            })
            objects.append({
                "object_id": f"task_memory_{backup_id}",
                "object_type": obj_type,
                "title": title,
                "status": status,
                "priority": priority,
                "client_id": client_name or "",
                "project_id": obj.get("project_id") or obj.get("project") or "",
                "due_date": due_date,
                "metadata": meta,
            })
        return objects
    except Exception:
        try:
            if conn:
                conn.close()
        except Exception:
            pass
        return []


def load_existing_voice_photo_state_from_db(limit=80):
    """V45.2: read voice/photo records already saved by app.py in conversation_state."""
    database_url = _db_url()
    if not database_url:
        return []
    conn = None
    try:
        import psycopg2
        conn = psycopg2.connect(database_url)
        cur = conn.cursor()
        cur.execute("""
            SELECT id, user_id, user_text, nina_text, intent, topic, created_at
            FROM conversation_state
            WHERE user_text LIKE %s OR user_text LIKE %s OR intent IN (%s, %s)
            ORDER BY id DESC
            LIMIT %s
        """, ("[VOICE]%", "[PHOTO]%", "voice_transcript", "photo", int(limit)))
        rows = cur.fetchall() or []
        cur.close()
        conn.close()

        objects = []
        now = datetime.utcnow().isoformat() + "Z"
        for row in rows:
            state_id = _row_get(row, 0)
            user_id = _row_get(row, 1)
            user_text = str(_row_get(row, 2) or "")
            nina_text = str(_row_get(row, 3) or "")
            intent = str(_row_get(row, 4) or "")
            topic = str(_row_get(row, 5) or "")
            created_at = str(_row_get(row, 6) or "")

            is_voice = user_text.startswith("[VOICE]") or intent == "voice_transcript" or topic == "voice"
            is_photo = user_text.startswith("[PHOTO]") or intent == "photo" or topic == "vision"
            clean_text = user_text.replace("[VOICE]", "", 1).replace("[PHOTO]", "", 1).strip()
            if not clean_text:
                clean_text = "Telegram voice/photo intake"
            obj_type = "document_intake" if is_photo else infer_work_type_from_text(clean_text, "task")
            title_prefix = "Telegram voice" if is_voice else ("Telegram photo/document" if is_photo else "Telegram message")
            meta = {
                "client_name": "",
                "owner": "Telegram Nina",
                "source": "existing_conversation_state",
                "source_channel": "Telegram voice" if is_voice else ("Telegram photo/vision" if is_photo else "Telegram"),
                "intake_kind": "voice_transcript" if is_voice else ("photo_vision" if is_photo else "conversation_state"),
                "raw_text": clean_text,
                "nina_text": nina_text[:600],
                "storage_target": "conversation_state",
                "approval_state": "synced_from_existing_memory",
                "db_read": True,
                "db_write_by_web": False,
                "telegram_user_id": str(user_id or ""),
                "conversation_state_id": str(state_id or ""),
                "created_at": created_at,
                "synced_at": now,
            }
            objects.append({
                "object_id": f"conversation_state_{state_id}",
                "object_type": obj_type,
                "title": f"{title_prefix}: {clean_text[:110]}",
                "status": "synced_preview",
                "priority": "normal",
                "client_id": "",
                "project_id": "",
                "due_date": "",
                "metadata": meta,
            })
        return objects
    except Exception:
        try:
            if conn:
                conn.close()
        except Exception:
            pass
        return []




def load_recent_conversation_state_from_db(limit=80):
    """V45.3: read recent Telegram conversation_state, not only voice/photo.

    app.py saves many Telegram routes into conversation_state with intents/topics such as
    human_mode, work_layer, followup, web_surface, task/work replies etc. A fresh Telegram
    message may be stored here even when it is not [VOICE] or [PHOTO].
    """
    database_url = _db_url()
    if not database_url:
        return []
    conn = None
    try:
        import psycopg2
        conn = psycopg2.connect(database_url)
        cur = conn.cursor()
        cur.execute("""
            SELECT id, user_id, user_text, nina_text, intent, topic, created_at
            FROM conversation_state
            ORDER BY id DESC
            LIMIT %s
        """, (int(limit),))
        rows = cur.fetchall() or []
        cur.close()
        conn.close()

        objects = []
        now = datetime.utcnow().isoformat() + "Z"
        skipped_prefixes = ("/start", "health", "admin", "premium", "stripe")
        for row in rows:
            state_id = _row_get(row, 0)
            user_id = _row_get(row, 1)
            user_text = str(_row_get(row, 2) or "").strip()
            nina_text = str(_row_get(row, 3) or "")
            intent = str(_row_get(row, 4) or "")
            topic = str(_row_get(row, 5) or "")
            created_at = str(_row_get(row, 6) or "")
            if not user_text:
                continue
            lower = user_text.lower().strip()
            if lower.startswith(skipped_prefixes):
                continue

            is_voice = user_text.startswith("[VOICE]") or intent == "voice_transcript" or topic == "voice"
            is_photo = user_text.startswith("[PHOTO]") or intent == "photo" or topic == "vision"
            clean_text = user_text.replace("[VOICE]", "", 1).replace("[PHOTO]", "", 1).strip()
            if not clean_text:
                continue

            obj_type = "document_intake" if is_photo else infer_work_type_from_text(clean_text, "task")
            # Mark likely client/follow-up work more usefully.
            if any(x in clean_text.lower() for x in ["pajautā", "pajauta", "piezvani", "atgādini", "atgadini", "follow"]):
                obj_type = "followup_task"
            if any(x in clean_text.lower() for x in ["tāme", "tami", "estimate", "quote", "piedāvāj"]):
                obj_type = "estimate"

            source_channel = "Telegram voice" if is_voice else ("Telegram photo/vision" if is_photo else "Telegram text")
            intake_kind = "voice_transcript" if is_voice else ("photo_vision" if is_photo else (intent or topic or "telegram_text"))
            meta = {
                "client_name": extract_client_name_from_text(clean_text),
                "owner": "Telegram Nina",
                "source": "existing_conversation_state_recent",
                "source_channel": source_channel,
                "intake_kind": intake_kind,
                "raw_text": clean_text,
                "nina_text": nina_text[:600],
                "storage_target": "conversation_state/recent",
                "approval_state": "synced_from_existing_memory",
                "db_read": True,
                "db_write_by_web": False,
                "telegram_user_id": str(user_id or ""),
                "conversation_state_id": str(state_id or ""),
                "created_at": created_at,
                "synced_at": now,
            }
            objects.append({
                "object_id": f"conversation_recent_{state_id}",
                "object_type": obj_type,
                "title": f"Telegram: {clean_text[:120]}",
                "status": "synced_preview",
                "priority": "normal",
                "client_id": meta.get("client_name", ""),
                "project_id": "",
                "due_date": "",
                "metadata": meta,
            })
        return objects
    except Exception:
        try:
            if conn:
                conn.close()
        except Exception:
            pass
        return []


def load_existing_tasks_table_from_db(limit=80):
    """V45.3: read existing app.py tasks table when present.

    Some app versions write Telegram tasks/follow-ups into a tasks table instead of only
    memory_backups. The schema has changed over time, so this reads columns dynamically.
    """
    database_url = _db_url()
    if not database_url:
        return []
    conn = None
    try:
        import psycopg2
        conn = psycopg2.connect(database_url)
        cur = conn.cursor()
        cur.execute("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = 'tasks'
        """)
        columns = [r[0] for r in cur.fetchall()]
        if not columns:
            cur.close(); conn.close(); return []
        order_col = "id" if "id" in columns else ("created_at" if "created_at" in columns else columns[0])
        cur.execute(f"SELECT * FROM tasks ORDER BY {order_col} DESC LIMIT %s", (int(limit),))
        names = [d[0] for d in cur.description]
        rows = [dict(zip(names, r)) for r in cur.fetchall()]
        cur.close(); conn.close()

        objects = []
        now = datetime.utcnow().isoformat() + "Z"
        for idx, row in enumerate(rows):
            raw_text = _first_value(row, ["raw_text", "text", "body", "message", "description"], "")
            title = _first_value(row, ["title", "task_title", "name"], "") or str(raw_text or "Telegram task")[:140]
            client_name = _first_value(row, ["client", "client_name", "contact", "person"], "") or extract_client_name_from_text(str(title) + " " + str(raw_text))
            is_followup = bool(_first_value(row, ["followup", "is_followup"], False))
            obj_type = "followup_task" if is_followup else infer_work_type_from_text(str(title) + " " + str(raw_text), "task")
            task_id = _first_value(row, ["id", "task_id", "object_id"], idx)
            meta = {
                "client_name": client_name,
                "owner": "Telegram Nina",
                "source": "existing_tasks_table",
                "source_channel": "Telegram",
                "intake_kind": "tasks_table",
                "raw_text": raw_text or title,
                "storage_target": "tasks",
                "approval_state": "synced_from_existing_memory",
                "db_read": True,
                "db_write_by_web": False,
                "task_table_id": str(task_id or ""),
                "created_at": str(_first_value(row, ["created_at", "created"], "")),
                "synced_at": now,
            }
            objects.append({
                "object_id": f"tasks_table_{task_id}",
                "object_type": obj_type,
                "title": title,
                "status": _first_value(row, ["status", "state"], "synced_preview") or "synced_preview",
                "priority": _first_value(row, ["priority"], "normal") or "normal",
                "client_id": client_name,
                "project_id": _first_value(row, ["project", "project_id", "project_name"], ""),
                "due_date": _first_value(row, ["deadline", "due_date", "date"], ""),
                "metadata": meta,
            })
        return objects
    except Exception:
        try:
            if conn:
                conn.close()
        except Exception:
            pass
        return []


def _canonical_text_key(value):
    """V45.3: stable key for deduping the same Telegram work across task_memory, voice and conversation_state."""
    raw = str(value or "").strip().lower()
    for prefix in ["[voice]", "[photo]", "telegram voice:", "telegram intake:", "telegram files/photos:"]:
        if raw.startswith(prefix):
            raw = raw[len(prefix):].strip()
    # Normalize common Latvian chars lightly while keeping readable text.
    replacements = {
        "ā":"a", "č":"c", "ē":"e", "ģ":"g", "ī":"i", "ķ":"k", "ļ":"l", "ņ":"n", "š":"s", "ū":"u", "ž":"z",
        "ä":"a", "ö":"o", "ü":"u"
    }
    raw = "".join(replacements.get(ch, ch) for ch in raw)
    import re
    raw = re.sub(r"[^a-z0-9€]+", " ", raw).strip()
    raw = re.sub(r"\s+", " ", raw)
    return raw[:180]


def _source_badge_for_obj(obj):
    meta = obj.get("metadata", {}) if isinstance(obj.get("metadata"), dict) else {}
    source = meta.get("source") or "workspace"
    kind = meta.get("intake_kind") or obj.get("object_type") or "work"
    if source == "existing_task_memory":
        return "Task Memory"
    if source == "existing_conversation_state":
        if "voice" in str(kind).lower():
            return "Voice"
        if "photo" in str(kind).lower() or "vision" in str(kind).lower():
            return "Photo"
        return "Conversation"
    if source == "telegram_intake_sync":
        return "Telegram"
    if source == "real_intake_store":
        return "Intake Store"
    if source == "existing_tasks_table":
        return "Tasks Table"
    return str(source).replace("_", " ").title()


def _rank_intake_obj(obj):
    """Higher number wins as the canonical visible card."""
    meta = obj.get("metadata", {}) if isinstance(obj.get("metadata"), dict) else {}
    source = meta.get("source") or ""
    obj_type = obj.get("object_type") or ""
    score = 0
    if source == "existing_task_memory":
        score += 100
    if source == "existing_tasks_table":
        score += 90
    if source == "real_intake_store":
        score += 80
    if source == "existing_conversation_state":
        score += 50
    if source == "telegram_intake_sync":
        score += 20
    if obj_type in ["followup_task", "estimate", "invoice", "document_intake"]:
        score += 10
    if meta.get("client_name") or obj.get("client_id"):
        score += 5
    return score


def dedupe_and_unify_intake_items(items, limit=30):
    """V45.3: collapse repeated Telegram memory rows into one clean Inbox card.

    app.py currently writes the same real work to more than one memory layer:
    - memory_backups source=task_engine;
    - conversation_state text/voice/photo;
    - optional tasks/intake tables.

    Web should show one useful work card and preserve the evidence as source badges,
    not flood the owner with duplicates.
    """
    groups = {}
    order = []
    for obj in items or []:
        if not isinstance(obj, dict):
            continue
        meta = dict(obj.get("metadata", {}) if isinstance(obj.get("metadata"), dict) else {})
        title = obj.get("title") or meta.get("raw_text") or meta.get("transcript_text") or "Telegram intake work"
        client = meta.get("client_name") or obj.get("client_id") or ""
        # Use title+client as the primary dedup identity; do not use object_id because every DB row has a different one.
        key = _canonical_text_key(client) + "|" + _canonical_text_key(title)
        if not key.strip("|"):
            key = str(obj.get("object_id") or title)
        badge = _source_badge_for_obj(obj)
        if key not in groups:
            copy = dict(obj)
            copy["metadata"] = meta
            meta["source_badges"] = [badge]
            meta["dedup_count"] = 1
            meta["dedup_sources"] = [str(obj.get("object_id") or badge)]
            meta["unified_card"] = True
            groups[key] = copy
            order.append(key)
            continue
        current = groups[key]
        current_meta = current.get("metadata", {}) if isinstance(current.get("metadata"), dict) else {}
        current_badges = list(current_meta.get("source_badges") or [])
        if badge and badge not in current_badges:
            current_badges.append(badge)
        current_meta["source_badges"] = current_badges
        current_meta["dedup_count"] = int(current_meta.get("dedup_count") or 1) + 1
        ds = list(current_meta.get("dedup_sources") or [])
        obj_id = str(obj.get("object_id") or badge)
        if obj_id not in ds:
            ds.append(obj_id)
        current_meta["dedup_sources"] = ds[:12]
        # Prefer the strongest object as the visible card, but keep dedup metadata.
        if _rank_intake_obj(obj) > _rank_intake_obj(current):
            replacement = dict(obj)
            replacement_meta = dict(obj.get("metadata", {}) if isinstance(obj.get("metadata"), dict) else {})
            replacement_meta.update({
                "source_badges": current_badges,
                "dedup_count": current_meta.get("dedup_count"),
                "dedup_sources": current_meta.get("dedup_sources"),
                "unified_card": True,
            })
            replacement["metadata"] = replacement_meta
            groups[key] = replacement
        else:
            current["metadata"] = current_meta
    unified = [groups[k] for k in order if k in groups]
    # newest/highest ranked first when possible
    unified.sort(key=lambda o: (_rank_intake_obj(o), str((o.get("metadata") or {}).get("created_at") or "")), reverse=True)
    return unified[:int(limit or 30)]


def _thread_family_for_obj(obj):
    """V45.4 FIX: classify related NinaOS work into broad thread families.

    Important polish:
    - Follow-up wording must not become a document thread just because the card has photo/voice evidence.
    - Estimate/offer wording wins over generic document/photo words.
    - Only real document/photo-only intake stays in the documents family.
    """
    meta = obj.get("metadata", {}) if isinstance(obj.get("metadata"), dict) else {}
    text = " ".join([
        str(obj.get("title") or ""),
        str(meta.get("raw_text") or ""),
        str(meta.get("transcript_text") or ""),
        str(meta.get("caption") or ""),
        str(obj.get("object_type") or ""),
    ]).lower()
    obj_type = str(obj.get("object_type") or "").lower()

    followup_terms = [
        "follow", "pajaut", "atgādin", "atgadin", "zvana", "zvanīt", "zvanit",
        "raksti", "uzraksti", "atbild", "sazin", "piezvan", "jāpajaut", "japajaut",
    ]
    estimate_terms = ["tāme", "tame", "estimate", "piedāvāj", "piedavaj", "offer", "quote", "€", "eur"]
    invoice_terms = ["rēķin", "rekin", "invoice"]
    document_terms = ["foto", "photo", "bild", "image", "pdf", "dok", "document", "scan", "skan", "fails", "file"]

    has_followup = obj_type == "followup_task" or any(x in text for x in followup_terms)
    has_estimate = obj_type in ["estimate", "offer"] or any(x in text for x in estimate_terms)
    has_invoice = obj_type == "invoice" or any(x in text for x in invoice_terms)
    has_document = obj_type == "document_intake" or any(x in text for x in document_terms)

    # Business intent wins over attachment/evidence hints.
    if has_estimate:
        return "estimate"
    if has_invoice:
        return "invoice"
    if has_followup:
        return "followup"
    if has_document:
        return "documents"
    return "task"


def _thread_client_for_obj(obj):
    meta = obj.get("metadata", {}) if isinstance(obj.get("metadata"), dict) else {}
    client = meta.get("client_name") or obj.get("client_id") or ""
    title = str(obj.get("title") or meta.get("raw_text") or "")
    if not client:
        # Small practical Latvian client extraction fallback for existing task memory.
        import re
        m = re.search(r"\b(?:Andrim|Andri|Andris)\b", title, flags=re.IGNORECASE)
        if m:
            client = "Andris"
    return str(client or "Workspace").strip() or "Workspace"


def _thread_sort_time(obj):
    meta = obj.get("metadata", {}) if isinstance(obj.get("metadata"), dict) else {}
    return str(meta.get("created_at") or meta.get("synced_at") or "")


def build_client_work_threads(items, limit=20):
    """V45.4: group deduplicated intake cards into client work threads.

    This is intentionally read-only. It does not mutate Postgres or app.py.
    Several similar Andris follow-ups become one follow-up thread with evidence count/source badges.
    """
    groups = {}
    order = []
    for obj in items or []:
        if not isinstance(obj, dict):
            continue
        client = _thread_client_for_obj(obj)
        family = _thread_family_for_obj(obj)
        key = _canonical_text_key(client) + "|" + family
        if key not in groups:
            meta = dict(obj.get("metadata", {}) if isinstance(obj.get("metadata"), dict) else {})
            meta["thread_client"] = client
            meta["thread_family"] = family
            meta["thread_items_count"] = 1
            meta["thread_evidence_titles"] = [str(obj.get("title") or "Telegram work")[:140]]
            meta["thread_latest_at"] = _thread_sort_time(obj)
            badges = list(meta.get("source_badges") or [])
            badge = _source_badge_for_obj(obj)
            if badge and badge not in badges:
                badges.append(badge)
            meta["source_badges"] = badges[:6]
            thread_obj = dict(obj)
            thread_obj["metadata"] = meta
            thread_obj["object_id"] = "client_thread_" + key.replace("|", "_")[:120]
            thread_obj["client_id"] = client
            # Human-friendly title for the thread.
            label = {
                "followup": "Follow-up thread",
                "estimate": "Estimate / offer thread",
                "invoice": "Invoice thread",
                "documents": "Document intake thread",
                "task": "Task thread",
            }.get(family, "Work thread")
            if client != "Workspace":
                thread_obj["title"] = f"{client} — {label}"
            else:
                thread_obj["title"] = label
            groups[key] = thread_obj
            order.append(key)
            continue

        current = groups[key]
        cm = current.get("metadata", {}) if isinstance(current.get("metadata"), dict) else {}
        cm["thread_items_count"] = int(cm.get("thread_items_count") or 1) + 1
        ev = list(cm.get("thread_evidence_titles") or [])
        t = str(obj.get("title") or "Telegram work")[:140]
        if t and t not in ev:
            ev.append(t)
        cm["thread_evidence_titles"] = ev[:8]
        # Merge source badges.
        badges = list(cm.get("source_badges") or [])
        for b in (obj.get("metadata", {}) if isinstance(obj.get("metadata"), dict) else {}).get("source_badges", []) or []:
            if b and b not in badges:
                badges.append(b)
        b = _source_badge_for_obj(obj)
        if b and b not in badges:
            badges.append(b)
        cm["source_badges"] = badges[:6]
        if _thread_sort_time(obj) > str(cm.get("thread_latest_at") or ""):
            cm["thread_latest_at"] = _thread_sort_time(obj)
        # Prefer canonical visible details from strongest work object.
        if _rank_intake_obj(obj) > _rank_intake_obj(current):
            replacement = dict(current)
            replacement["object_type"] = obj.get("object_type") or current.get("object_type")
            replacement["status"] = obj.get("status") or current.get("status")
            replacement["priority"] = obj.get("priority") or current.get("priority")
            replacement["metadata"] = cm
            groups[key] = replacement
        else:
            current["metadata"] = cm

    threads = [groups[k] for k in order if k in groups]
    threads.sort(key=lambda o: (_rank_intake_obj(o), str((o.get("metadata") or {}).get("thread_latest_at") or "")), reverse=True)
    return threads[:int(limit or 20)]


def load_client_work_threads():
    return build_client_work_threads(load_existing_telegram_intake_sync(), limit=20)


def client_thread_rows(items, empty_text=None, limit=None):
    lang = current_language()
    if limit:
        items = items[:limit]
    if not items:
        label = empty_text or tx("no_items", lang)
        return f"<div class='row'><div><b>{html_escape(label)}</b><span class='muted'>—</span></div><span class='pill'>idle</span></div>"
    rows = ""
    for obj in items:
        meta = obj.get("metadata", {}) if isinstance(obj.get("metadata"), dict) else {}
        client = meta.get("thread_client") or obj.get("client_id") or "Workspace"
        family = meta.get("thread_family") or obj.get("object_type") or "work"
        count = int(meta.get("thread_items_count") or 1)
        badges = meta.get("source_badges") or []
        if isinstance(badges, str):
            badges = [badges]
        badge_text = " + ".join(str(b) for b in badges[:5] if b) or object_source_label(obj, lang)
        evidence = meta.get("thread_evidence_titles") or []
        evidence_text = " | ".join(str(x) for x in evidence[:3] if x)
        if len(evidence) > 3:
            evidence_text += f" | +{len(evidence)-3} more"
        muted = f"{client} · {family} · {count} linked item{'s' if count != 1 else ''} · {badge_text}"
        rows += (
            "<div class='row'><div>"
            f"<b>{html_escape(obj.get('title'))}</b>"
            f"<span class='muted'>{html_escape(muted)}</span>"
            + (f"<span class='muted'>{html_escape(evidence_text)}</span>" if evidence_text else "")
            + f"{preview_approval_controls(obj)}"
            "</div>"
            f"<span class='pill'>{html_escape(obj.get('status'))} · {html_escape(obj.get('priority', 'normal'))} · thread</span></div>"
        )
    return rows

def load_existing_telegram_intake_sync():
    """V45.2: bridge Web Inbox to the Telegram memory that already exists in app.py.

    Correct priority now:
    1) existing task_engine memory_backups (real Telegram work objects);
    2) existing conversation_state voice/photo records;
    3) future intake_events table if someone adds it later;
    4) safe demo fallback.
    """
    task_memory = load_existing_task_engine_memory_from_db()
    voice_photo_memory = load_existing_voice_photo_state_from_db()
    recent_conversation = load_recent_conversation_state_from_db()
    tasks_table = load_existing_tasks_table_from_db()
    real_intake = load_real_intake_events_from_db()

    merged = []
    seen = set()
    for source_list in [task_memory, tasks_table, voice_photo_memory, recent_conversation, real_intake]:
        for obj in source_list or []:
            key = str(obj.get("object_id") or obj.get("title") or "")
            if not key or key in seen:
                continue
            seen.add(key)
            merged.append(obj)

    if merged:
        return dedupe_and_unify_intake_items(merged, limit=30)

    # Older app.py/web bridge fallback: tasks table if present.
    live = load_live_objects_from_app_db()
    synced = []
    for obj in live:
        meta = dict(obj.get("metadata", {}) if isinstance(obj.get("metadata"), dict) else {})
        raw_title = obj.get("title") or meta.get("raw_text") or "Telegram intake work"
        obj_type = obj.get("object_type") or infer_work_type_from_text(raw_title)
        if obj_type == "task":
            obj_type = infer_work_type_from_text(raw_title, "task")
        meta.update({
            "source": "telegram_intake_sync",
            "source_channel": meta.get("source_channel") or "Telegram",
            "intake_kind": meta.get("intake_kind") or ("followup_capture" if obj_type == "followup_task" else "telegram_work_intake"),
            "storage_target": "NinaOS client workspace",
            "approval_state": meta.get("approval_state") or "synced_from_telegram",
            "db_write": False,
            "synced_at": datetime.utcnow().isoformat() + "Z",
        })
        synced.append({
            "object_id": str(obj.get("object_id") or "telegram_sync_item"),
            "object_type": obj_type,
            "title": raw_title,
            "status": obj.get("status") or "synced",
            "priority": obj.get("priority") or "normal",
            "client_id": obj.get("client_id") or meta.get("client_name") or "",
            "project_id": obj.get("project_id") or "",
            "due_date": obj.get("due_date") or "",
            "metadata": meta,
        })
    if synced:
        return dedupe_and_unify_intake_items(synced, limit=12)
    return telegram_intake_demo_items()


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
        "approval_state": "pending_approval",
        "approval_updated_at": "",
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


def is_preview_object(obj):
    meta = obj.get("metadata", {}) if isinstance(obj.get("metadata"), dict) else {}
    return meta.get("source") in ["web_action_preview", "web_preview", "web_voice_intake_preview", "telegram_intake_sync", "real_intake_store", "existing_task_memory", "existing_conversation_state"]


def preview_approval_state(obj):
    meta = obj.get("metadata", {}) if isinstance(obj.get("metadata"), dict) else {}
    return meta.get("approval_state") or "pending_approval"


def approved_preview_items():
    return [o for o in WORKSPACE_ACTION_PREVIEWS if preview_approval_state(o) == "approved"]


def pending_or_held_preview_items():
    return [o for o in WORKSPACE_ACTION_PREVIEWS if preview_approval_state(o) in ["pending_approval", "hold"]]


def rejected_preview_items():
    return [o for o in WORKSPACE_ACTION_PREVIEWS if preview_approval_state(o) == "rejected"]


def active_preview_items():
    return [o for o in WORKSPACE_ACTION_PREVIEWS if preview_approval_state(o) != "rejected"]


def approval_label_from_state(state, lang=None):
    state = state or "pending_approval"
    key_map = {
        "pending_approval": "pending_approval",
        "approved": "approved_preview",
        "hold": "held_preview",
        "rejected": "rejected_preview",
    }
    return tx(key_map.get(state, "pending_approval"), lang or current_language())


def apply_preview_approval(object_id, decision):
    decision = (decision or "").strip().lower()
    if decision not in ["approve", "hold", "reject"]:
        return None
    state_map = {"approve": "approved", "hold": "hold", "reject": "rejected"}
    for obj in WORKSPACE_ACTION_PREVIEWS:
        if obj.get("object_id") == object_id:
            meta = obj.setdefault("metadata", {})
            new_state = state_map[decision]
            meta["approval_state"] = new_state
            meta["approval_updated_at"] = datetime.utcnow().isoformat() + "Z"
            meta["db_write"] = False
            meta["workspace_queue_state"] = "active_approved" if new_state == "approved" else new_state
            if new_state == "approved":
                # Keep the business status stable, but mark routing clearly in metadata.
                obj["status"] = obj.get("status") or "open"
                meta["approved_queue_visible"] = True
            elif new_state == "rejected":
                meta["approved_queue_visible"] = False
            return obj
    return None


@app.before_request
def handle_preview_approval_query():
    object_id = request.args.get("preview_object_id") or ""
    decision = request.args.get("preview_decision") or ""
    if object_id and decision:
        apply_preview_approval(object_id, decision)


def preview_approval_controls(obj):
    # V43.3 FIX: show decision buttons only for preview objects that are still actionable.
    # Approved work must move to the approved workspace queue without action buttons.
    # Rejected work must stay in the rejected log without action buttons.
    if not is_preview_object(obj):
        return ""
    state = preview_approval_state(obj)
    if state not in ["pending_approval", "hold"]:
        return ""
    lang = current_language()
    object_id = html_escape(obj.get("object_id"))
    path = request.path or "/tasks"
    base = f"{path}?lang={lang}&preview_object_id={object_id}"
    return (
        "<div class='btns' style='justify-content:flex-start;margin-top:10px'>"
        f"<a class='btn primary' href='{base}&preview_decision=approve'>{tx('approve', lang)}</a>"
        f"<a class='btn' href='{base}&preview_decision=hold'>{tx('hold', lang)}</a>"
        f"<a class='btn' href='{base}&preview_decision=reject'>{tx('reject', lang)}</a>"
        "</div>"
    )


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

    approved_previews = approved_preview_items()
    if approved_previews:
        normalized = list(approved_previews) + normalized

    if not normalized:
        normalized = [
            {"object_id": "task_1", "object_type": "task", "title": "Prepare today workspace priorities", "status": "open", "priority": "high", "client_id": "", "project_id": "", "due_date": "today", "metadata": {"client_name": "", "owner": "Nina Office Manager"}},
            {"object_id": "followup_1", "object_type": "followup_task", "title": "Follow up with Demo Client about offer", "status": "scheduled", "priority": "normal", "client_id": "demo_client", "project_id": "", "due_date": "friday", "metadata": {"client_name": "Demo Client", "owner": "Nina Sales"}},
            {"object_id": "estimate_1", "object_type": "estimate", "title": "Demo estimate draft", "status": "draft", "priority": "normal", "client_id": "demo_client", "project_id": "project_1", "due_date": "", "metadata": {"client_name": "Demo Client", "owner": "Nina Estimator"}},
            {"object_id": "invoice_1", "object_type": "invoice", "title": "Demo invoice follow-up", "status": "sent", "priority": "normal", "client_id": "demo_client", "project_id": "project_1", "due_date": "today", "metadata": {"client_name": "Demo Client", "owner": "Nina Office Manager"}},
            {"object_id": "project_1", "object_type": "project", "title": "Demo active project", "status": "active", "priority": "normal", "client_id": "demo_client", "project_id": "project_1", "due_date": "", "metadata": {"client_name": "Demo Client", "owner": "Nina Office Manager"}},
        ]

    activity = [
        {"title": "V45.4 FIX thread classifier polish", "body": "Inbox now groups real app.py memory into client work threads with follow-up merge.", "kind": "sync"},
        {"title": "V43.4 preview to real task surface", "body": "Approved preview objects now appear across Dashboard, Tasks and Office Manager surfaces in safe mode.", "kind": "work"},
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
        ("inbox", tx("inbox", lang), "/inbox", "✦"),
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
    approved_dashboard_rows = work_object_rows(approved_preview_items(), empty_text=tx("no_items", lang), limit=4, show_source=True)
    snapshot_kpis = (
        kpi_card(tx("clients", lang), c["clients"], {"text": tx("crm", lang), "href": "/clients"})
        + kpi_card(tx("workers", lang), c["workers"], {"text": tx("ai_workforce", lang), "href": "/workers"})
        + kpi_card(tx("estimates", lang), c["estimates"], {"text": tx("in_progress", lang), "href": "/tasks"})
        + kpi_card(tx("invoices", lang), c["invoices"], {"text": tx("due_sent", lang), "href": "/clients"})
    )
    return f"<div class='grid'><div class='hero-grid'><section class='card card-pad hero-card'><div class='hero-lockup'>{nina_logo_html('hero')}<div><div class='hero-title'>Nina<span>OS</span></div><div class='subtitle'>AI WORKFORCE OPERATING SYSTEM</div></div></div><div class='bigline'>{tx('hero_line', lang)}</div><br><div class='btns'><a class='btn primary' href='{q('/inbox')}'>{tx('channel_hub', lang)}</a><a class='btn' href='{q('/tasks')}'>{tx('open_work', lang)}</a><a class='btn' href='{q('/exchange')}'>{tx('explore', lang)}</a></div><div class='trust'><span>GLOBAL</span><span>WORKFORCE</span><span>SECURE</span><span>SCALE</span></div></section><section class='card card-pad'><div class='page-title'><h1>{tx('good_morning', lang)}</h1><p>{tx('workspace_today', lang)}</p></div><br>{kpis}<br><div class='card card-pad' style='background:rgba(27,84,255,.16)'><div class='section-title'>{tx('global', lang)}</div><p class='muted'>{tx('connected', lang)}</p><a class='btn' href='{q('/exchange')}'>{tx('view_global', lang)}</a></div></section></div><section><div class='section-title'>{tx('your_workers', lang)}</div><div class='worker-grid'>{workers}</div></section><div class='two-col'><section class='card card-pad'><div class='section-title'>{tx('recent', lang)}</div><div class='list'>{activity}</div></section><section class='card card-pad'><div class='section-title'>{tx('snapshot', lang)}</div><div class='kpis'>{snapshot_kpis}</div><br><div class='btns'><a class='btn primary' href='{q('/tasks')}'>{tx('tasks', lang)}</a><a class='btn' href='{q('/clients')}'>{tx('clients', lang)}</a><a class='btn' href='{q('/projects')}'>{tx('projects', lang)}</a><a class='btn' href='{q('/workers')}'>{tx('workers', lang)}</a></div></section></div><section class='card card-pad'><div class='section-title'>{tx('active_workspace_queue', lang)}</div><div class='list'>{approved_dashboard_rows}</div><div class='safe-note'>{tx('approved_work_note', lang)}</div></section></div>"


def work_page_header(title, subtitle):
    return f"<div class='grid'><section class='card card-pad'><div class='page-title'><h1>{html_escape(title)}</h1><p>{html_escape(subtitle)}</p></div><br><div class='btns'><a class='btn primary' href='{q('/dashboard')}'>{tx('dashboard')}</a><a class='btn' href='{q('/tasks')}'>{tx('tasks')}</a><a class='btn' href='{q('/clients')}'>{tx('clients')}</a><a class='btn' href='{q('/workers')}'>{tx('workers')}</a><a class='btn' href='{q('/exchange')}'>{tx('exchange')}</a></div></section></div><br>"

def object_source_label(obj, lang=None):
    lang = lang or current_language()
    meta = obj.get("metadata", {}) if isinstance(obj.get("metadata"), dict) else {}
    source = meta.get("source") or "workspace"
    if source in ["web_action_preview", "web_preview", "web_voice_intake_preview"]:
        return tx("source_preview", lang)
    if source == "telegram_intake_sync":
        return "Telegram sync"
    if source == "existing_task_memory":
        return "Existing task memory" if lang == "en" else ("Esošā task atmiņa" if lang == "lv" else "Память задач")
    if source == "existing_conversation_state":
        return "Existing voice/photo memory" if lang == "en" else ("Esošā balss/foto atmiņa" if lang == "lv" else "Память голоса/фото")
    if source == "real_intake_store":
        return "Real intake store" if lang == "en" else ("Intake store" if lang == "lv" else "Intake store")
    if source == "database":
        return tx("source_database", lang)
    if source == "demo":
        return tx("source_demo", lang)
    return tx("source_workspace", lang)


def work_object_rows(items, empty_text=None, limit=None, show_source=True, show_approval=True):
    lang = current_language()
    if limit:
        items = items[:limit]
    if not items:
        label = empty_text or tx("no_items", lang)
        return f"<div class='row'><div><b>{html_escape(label)}</b><span class='muted'>—</span></div><span class='pill'>idle</span></div>"
    rows = ""
    for obj in items:
        meta = obj.get("metadata", {}) if isinstance(obj.get("metadata"), dict) else {}
        client = meta.get("client_name") or obj.get("client_id") or "Workspace"
        source = object_source_label(obj, lang)
        badges = meta.get("source_badges") or []
        if isinstance(badges, str):
            badges = [badges]
        badge_suffix = ""
        if badges:
            badge_suffix = " · " + html_escape(" + ".join(str(b) for b in badges[:4] if b))
        source_part = f" · {html_escape(source)}{badge_suffix}" if show_source else ""
        approval_state = meta.get("approval_state") or ("pending_approval" if is_preview_object(obj) else "")
        approval_part = f" · {html_escape(approval_label_from_state(approval_state, lang))}" if show_approval and is_preview_object(obj) else ""
        badge = f"{html_escape(obj.get('status'))} · {html_escape(obj.get('priority', 'normal'))}{approval_part}"
        rows += (
            "<div class='row'><div>"
            f"<b>{html_escape(obj.get('title'))}</b>"
            f"<span class='muted'>{html_escape(client)} · {html_escape(obj.get('object_type'))}{source_part}</span>"
            f"{preview_approval_controls(obj)}"
            "</div>"
            f"<span class='pill'>{badge}</span></div>"
        )
    return rows


def tasks_body(data):
    lang = current_language()
    approved_items = approved_preview_items()
    pending_items = pending_or_held_preview_items()
    rejected_items = rejected_preview_items()
    all_rows = work_object_rows(data["tasks"], empty_text=tx("no_items", lang), show_source=True)
    approved_rows = work_object_rows(approved_items, empty_text=tx("no_items", lang), show_source=True)
    pending_rows = work_object_rows(pending_items, empty_text=tx("no_items", lang), show_source=True)
    rejected_rows = work_object_rows(rejected_items, empty_text=tx("no_items", lang), show_source=True)
    telegram_sync_rows = client_thread_rows(load_client_work_threads(), empty_text=tx("no_items", lang), limit=8)
    return (
        work_page_header(tx("tasks"), tx("tasks_sub"))
        + "<section class='card card-pad'><div class='section-title'>Client Work Threads</div><div class='list'>" + telegram_sync_rows + "</div><div class='safe-note'>V45.4 FIX: thread classification is polished so follow-up text no longer falls into document intake just because it has photo/voice evidence. Telegram runtime is not modified.</div></section><br>"
        + f"<section class='card card-pad'><div class='section-title'>{tx('real_task_surface_bridge', lang)}</div><div class='list'>{approved_rows}</div><div class='safe-note'>{tx('approved_work_note', lang)}</div></section><br>"
        + f"<section class='card card-pad'><div class='section-title'>{tx('approval_workspace_bridge', lang)}</div><div class='list'>{pending_rows}</div><div class='safe-note'>{tx('safe_note', lang)}</div></section><br>"
        + f"<section class='card card-pad'><div class='section-title'>{tx('all_workspace_work', lang)}</div><div class='list'>{all_rows}</div></section><br>"
        + f"<section class='card card-pad'><div class='section-title'>{tx('rejected_preview_log', lang)}</div><div class='list'>{rejected_rows}</div></section>"
    )


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



def channel_card(title, body, status, icon="●"):
    return (
        "<div class='card card-pad'>"
        f"<div class='section-title'>{icon} {html_escape(title)}</div>"
        f"<p class='muted'>{html_escape(body)}</p>"
        f"<span class='pill'>{html_escape(status)}</span>"
        "</div>"
    )



def detect_voice_intake_action(voice_text, source_channel="voice", priority="normal"):
    text = (voice_text or "").strip()
    low = text.lower()

    if any(w in low for w in ["tāme", "tame", "tami", "estimate", "quote", "offer", "piedāvāj", "piedavaj"]):
        form_type = "estimate"
    elif any(w in low for w in ["rēķin", "rekin", "rekins", "invoice", "bill"]):
        form_type = "invoice"
    elif any(w in low for w in ["piezvan", "atgādin", "atgadin", "follow", "sazin", "pajaut", "uzrakst", "atsūti", "atsuti"]):
        form_type = "followup"
    else:
        form_type = "new_task"

    client_name = ""
    # Simple V44.1 FIX extraction: enough for safe preview; real CRM extraction comes later.
    for name in ["andris", "jānis", "janis", "marija", "katrin", "klients", "client"]:
        if name in low:
            client_name = "Klients" if name in ["klients", "client"] else name[:1].upper() + name[1:]
            break

    title = text[:140] if text else "Inbox intake work"
    if form_type == "estimate" and "tāme" not in low and "estimate" not in low:
        title = "Prepare estimate from inbox intake"
    elif form_type == "invoice":
        title = "Prepare invoice/admin record from inbox intake"
    elif form_type == "followup":
        title = "Follow up from inbox intake"

    return {
        "form_type": form_type,
        "task_title": title,
        "client_name": client_name,
        "project_name": "",
        "amount": "",
        "due_date": "",
        "priority": priority or "normal",
        "notes": f"Omnichannel intake from {source_channel}: {text}",
    }

def get_voice_intake_preview():
    global LAST_VOICE_INTAKE_PREVIEW
    if request.method != "POST":
        return None
    voice_text = (request.form.get("voice_text", "") or "").strip()
    source_channel = request.form.get("source_channel", "voice")
    priority = request.form.get("priority", "normal")
    # V44.1 POST FIX: browsers show placeholder text but do not submit it.
    # For the current safe preview sprint, an empty submit creates a demo intake preview
    # instead of silently returning to "No items yet".
    if not voice_text:
        voice_text = (request.form.get("fallback_voice_text", "") or "").strip()
    if not voice_text:
        voice_text = "Nina, man vajag sagatavot tāmi klientam par vannas istabas remontu un atsūtīt WhatsApp"

    action = detect_voice_intake_action(voice_text, source_channel, priority)
    obj = normalize_action_to_work_object(action)
    meta = obj.get("metadata", {}) if isinstance(obj.get("metadata"), dict) else {}
    meta["source"] = "web_voice_intake_preview"
    meta["source_channel"] = source_channel
    meta["voice_text"] = voice_text.strip()
    meta["intake_kind"] = "omnichannel_voice_text"
    meta["document_intake"] = True
    meta["storage_target"] = "NinaOS client workspace"
    meta["send_back_channels"] = "WhatsApp / Telegram / Email"
    meta["approval_state"] = "pending_approval"
    obj["metadata"] = meta
    obj["object_id"] = obj.get("object_id", "web_preview_voice") .replace("web_preview_", "web_voice_preview_", 1)

    WORKSPACE_ACTION_PREVIEWS.insert(0, obj)
    del WORKSPACE_ACTION_PREVIEWS[25:]
    LAST_VOICE_INTAKE_PREVIEW = obj
    return obj

def voice_intake_form_html(created_obj=None):
    lang = current_language()
    source_options = ["voice", "WhatsApp", "Telegram", "Email", "Files", "Web"]
    options = "".join(f"<option value='{html_escape(x)}'>{html_escape(x)}</option>" for x in source_options)
    created = ""
    if created_obj:
        meta = created_obj.get("metadata", {}) if isinstance(created_obj.get("metadata"), dict) else {}
        created = (
            "<div class='preview-box'>"
            f"<b>{tx('voice_preview_created', lang)}</b>"
            "<div class='list'>"
            f"<div class='row'><div><b>{html_escape(created_obj.get('title'))}</b><span class='muted'>{html_escape(created_obj.get('object_type'))} · {html_escape(meta.get('source_channel','voice'))}</span></div><span class='pill'>{tx('pending_preview', lang)}</span></div>"
            f"<div class='row'><div><b>{tx('detected_intent', lang)}</b><span class='muted'>{html_escape(created_obj.get('object_type'))}</span></div><span class='pill'>V44.1</span></div>"
            "</div>"
            f"<div class='safe-note'>{tx('voice_safe_note', lang)}</div>"
            "</div>"
        )
    return f"""
    <section class='card card-pad'>
      <div class='section-title'>🎙 {tx('voice_intake_form', lang)}</div>
      <p class='muted'>{tx('voice_intake_hint', lang)}</p>
      {created}
      <form method='post' action='/inbox?lang={lang}'>
        <div class='form-grid'>
          <div class='field'>
            <label>{tx('source_channel', lang)}</label>
            <select name='source_channel'>{options}</select>
          </div>
          <div class='field'>
            <label>{tx('priority', lang)}</label>
            <select name='priority'><option value='normal'>{tx('normal', lang)}</option><option value='high'>{tx('high', lang)}</option></select>
          </div>
        </div>
        <br>
        <div class='field'>
          <label>{tx('voice_text', lang)}</label>
          <textarea name='voice_text' placeholder='Nina, man vajag sagatavot tāmi klientam par vannas istabas remontu un atsūtīt WhatsApp...'></textarea><input type='hidden' name='fallback_voice_text' value='Nina, man vajag sagatavot tāmi klientam par vannas istabas remontu un atsūtīt WhatsApp'>
        </div>
        <div class='form-actions'>
          <button class='btn primary' type='submit'>{tx('nina_prepare', lang)}</button>
          <a class='btn' href='{q('/office-manager/actions')}'>{tx('approval_required', lang)}</a>
        </div>
        <div class='safe-note'>{tx('voice_safe_note', lang)}</div>
      </form>
    </section>
    """



# =========================
# V45.3
# =========================

def mask_db_url(url):
    """Show only safe DB connection signal, never expose credentials."""
    url = str(url or "")
    if not url:
        return "missing"
    try:
        if "@" in url:
            prefix, rest = url.split("@", 1)
            scheme = prefix.split(":", 1)[0] if ":" in prefix else "db"
            host = rest.split("/", 1)[0]
            return f"{scheme}://***@{host}/***"
        return url[:18] + "..." if len(url) > 18 else "configured"
    except Exception:
        return "configured"


def _diag_table_exists(cur, table_name):
    try:
        cur.execute("""
            SELECT EXISTS (
                SELECT 1
                FROM information_schema.tables
                WHERE table_name = %s
            )
        """, (table_name,))
        row = cur.fetchone()
        return bool(row[0]) if row else False
    except Exception:
        return False


def _diag_count(cur, sql, params=()):
    try:
        cur.execute(sql, params)
        row = cur.fetchone()
        return int(row[0] or 0) if row else 0
    except Exception as e:
        return f"error: {str(e)[:160]}"


def _diag_latest_rows(cur, sql, params=(), limit=5):
    try:
        cur.execute(sql, params)
        rows = cur.fetchall() or []
        names = [d[0] for d in cur.description]
        out = []
        for r in rows[:limit]:
            item = {}
            for name, value in zip(names, r):
                text = str(value or "")
                if len(text) > 220:
                    text = text[:220] + "…"
                item[name] = text
            out.append(item)
        return out
    except Exception as e:
        return [{"error": str(e)[:220]}]


def telegram_bridge_db_diagnostics():
    """Visible read-only diagnostics for the Telegram → Web sync bridge."""
    info = db_url_info()
    database_url = info.get("url") or ""
    diag = {
        "version": WEB_APP_VERSION,
        "database_url_present": bool(database_url),
        "database_url_source": info.get("source") or "",
        "database_url_safe": info.get("safe") or "missing",
        "database_url_candidates_found": info.get("found") or [],
        "relevant_env_keys": info.get("relevant_env_keys") or [],
        "postgres_driver": "unknown",
        "db_connect_ok": False,
        "db_error": "",
        "tables": {},
        "counts": {},
        "latest": {},
        "web_reader_counts": {},
        "note": "Read-only diagnostic. Web does not write DB in this sprint.",
    }

    try:
        import psycopg2
        diag["postgres_driver"] = "psycopg2 available"
    except Exception as e:
        diag["postgres_driver"] = "psycopg2 missing"
        diag["db_error"] = str(e)[:220]
        return diag

    if not database_url:
        diag["db_error"] = "No usable Postgres URL found in Web service env. Checked DATABASE_URL, POSTGRES_URL and Railway/Postgres variants."
        return diag

    conn = None
    try:
        import psycopg2
        conn = psycopg2.connect(database_url)
        cur = conn.cursor()
        diag["db_connect_ok"] = True

        for table in ["conversation_state", "memory_backups", "tasks", "intake_events"]:
            diag["tables"][table] = _diag_table_exists(cur, table)

        if diag["tables"].get("conversation_state"):
            diag["counts"]["conversation_state_total"] = _diag_count(cur, "SELECT COUNT(*) FROM conversation_state")
            diag["counts"]["conversation_state_voice"] = _diag_count(cur, "SELECT COUNT(*) FROM conversation_state WHERE user_text LIKE %s OR intent = %s OR topic = %s", ("[VOICE]%", "voice_transcript", "voice"))
            diag["counts"]["conversation_state_photo"] = _diag_count(cur, "SELECT COUNT(*) FROM conversation_state WHERE user_text LIKE %s OR intent = %s OR topic = %s", ("[PHOTO]%", "photo", "vision"))
            diag["counts"]["conversation_state_recent_text"] = _diag_count(cur, "SELECT COUNT(*) FROM conversation_state WHERE COALESCE(user_text,'') <> ''")
            diag["latest"]["conversation_state"] = _diag_latest_rows(cur, """
                SELECT id, user_id, user_text, intent, topic, created_at
                FROM conversation_state
                ORDER BY id DESC
                LIMIT 5
            """)
        else:
            diag["counts"]["conversation_state_total"] = "table missing"

        if diag["tables"].get("memory_backups"):
            diag["counts"]["memory_backups_total"] = _diag_count(cur, "SELECT COUNT(*) FROM memory_backups")
            diag["counts"]["memory_backups_task_engine"] = _diag_count(cur, "SELECT COUNT(*) FROM memory_backups WHERE source = %s", ("task_engine",))
            diag["latest"]["memory_backups_task_engine"] = _diag_latest_rows(cur, """
                SELECT id, user_id, source, backup_text, created_at
                FROM memory_backups
                WHERE source = %s
                ORDER BY id DESC
                LIMIT 5
            """, ("task_engine",))
            diag["latest"]["memory_backups_any"] = _diag_latest_rows(cur, """
                SELECT id, user_id, source, backup_text, created_at
                FROM memory_backups
                ORDER BY id DESC
                LIMIT 5
            """)
        else:
            diag["counts"]["memory_backups_total"] = "table missing"

        if diag["tables"].get("tasks"):
            diag["counts"]["tasks_total"] = _diag_count(cur, "SELECT COUNT(*) FROM tasks")
            diag["latest"]["tasks"] = _diag_latest_rows(cur, "SELECT * FROM tasks ORDER BY id DESC LIMIT 5")
        else:
            diag["counts"]["tasks_total"] = "table missing"

        if diag["tables"].get("intake_events"):
            diag["counts"]["intake_events_total"] = _diag_count(cur, "SELECT COUNT(*) FROM intake_events")
            diag["latest"]["intake_events"] = _diag_latest_rows(cur, "SELECT * FROM intake_events ORDER BY id DESC LIMIT 5")
        else:
            diag["counts"]["intake_events_total"] = "table missing"

        cur.close()
        conn.close()
    except Exception as e:
        diag["db_error"] = str(e)[:500]
        try:
            if conn:
                conn.close()
        except Exception:
            pass

    # These are the actual web reader outputs, so we can compare DB truth vs UI reader.
    try:
        diag["web_reader_counts"]["task_engine_memory_reader"] = len(load_existing_task_engine_memory_from_db())
    except Exception as e:
        diag["web_reader_counts"]["task_engine_memory_reader"] = "error: " + str(e)[:160]
    try:
        diag["web_reader_counts"]["voice_photo_reader"] = len(load_existing_voice_photo_state_from_db())
    except Exception as e:
        diag["web_reader_counts"]["voice_photo_reader"] = "error: " + str(e)[:160]
    try:
        diag["web_reader_counts"]["recent_conversation_reader"] = len(load_recent_conversation_state_from_db())
    except Exception as e:
        diag["web_reader_counts"]["recent_conversation_reader"] = "error: " + str(e)[:160]
    try:
        diag["web_reader_counts"]["tasks_table_reader"] = len(load_existing_tasks_table_from_db())
    except Exception as e:
        diag["web_reader_counts"]["tasks_table_reader"] = "error: " + str(e)[:160]
    try:
        unified_items = load_existing_telegram_intake_sync()
        diag["web_reader_counts"]["merged_telegram_intake_sync"] = len(unified_items)
        diag["web_reader_counts"]["unified_dedup_cards"] = len(unified_items)
        diag["web_reader_counts"]["client_work_threads"] = len(build_client_work_threads(unified_items, limit=50))
    except Exception as e:
        diag["web_reader_counts"]["merged_telegram_intake_sync"] = "error: " + str(e)[:160]

    return diag


def diagnostic_rows_html(diag):
    rows = []
    def add(label, value, pill="diag"):
        rows.append(f"<div class='row'><div><b>{html_escape(label)}</b><span class='muted'>{html_escape(value)}</span></div><span class='pill'>{html_escape(pill)}</span></div>")

    add("DB URL source", diag.get("database_url_source") or "missing", "env")
    add("DB URL safe", diag.get("database_url_safe", "missing"), "env")
    candidates = diag.get("database_url_candidates_found") or []
    if candidates:
        add("DB env candidates", ", ".join([str(x.get("key")) for x in candidates]), "env")
    else:
        add("DB env candidates", "none", "env")
    env_keys = diag.get("relevant_env_keys") or []
    add("Relevant env key names", ", ".join(env_keys[:30]) if env_keys else "none visible", "env")
    add("DB connect", "OK" if diag.get("db_connect_ok") else (diag.get("db_error") or "not connected"), "OK" if diag.get("db_connect_ok") else "check")
    for table, exists in (diag.get("tables") or {}).items():
        add(f"table: {table}", "exists" if exists else "missing", "table")
    for key, value in (diag.get("counts") or {}).items():
        add(key, value, "count")
    for key, value in (diag.get("web_reader_counts") or {}).items():
        add(key, value, "reader")
    if diag.get("db_error"):
        add("DB error", diag.get("db_error"), "error")
    return "".join(rows)


def latest_debug_rows_html(diag):
    blocks = []
    latest = diag.get("latest") or {}
    for group, rows in latest.items():
        inner = ""
        for item in rows[:5]:
            title = str(item.get("user_text") or item.get("backup_text") or item.get("title") or item.get("raw_text") or item.get("id") or "row")
            meta = " · ".join([f"{k}: {v}" for k, v in item.items() if k not in ["user_text", "backup_text", "title", "raw_text"]])
            inner += f"<div class='row'><div><b>{html_escape(title)}</b><span class='muted'>{html_escape(meta)}</span></div><span class='pill'>{html_escape(group)}</span></div>"
        if not inner:
            inner = "<div class='row'><div><b>No rows</b><span class='muted'>—</span></div><span class='pill'>empty</span></div>"
        blocks.append(f"<section class='card card-pad'><div class='section-title'>Latest: {html_escape(group)}</div><div class='list'>{inner}</div></section>")
    return "<div class='stack-grid'>" + "".join(blocks) + "</div>" if blocks else ""


def telegram_db_diagnostic_block_html():
    diag = telegram_bridge_db_diagnostics()
    return (
        "<section class='card card-pad'>"
        "<div class='section-title'>🧪 V45.4 DB Diagnostic</div>"
        "<p class='muted'>Read-only check: does Web service see the same Postgres memory that Telegram app.py writes?</p>"
        "<div class='list'>" + diagnostic_rows_html(diag) + "</div>"
        "<div class='safe-note'>Open JSON: <a href='/diagnostics/telegram-sync'>/diagnostics/telegram-sync</a>. If counts are zero here but Telegram works, Railway services may not share the same DATABASE_URL or app.py writes to a different table/source.</div>"
        "</section><br>"
        + latest_debug_rows_html(diag)
        + "<br>"
    )

def channel_hub_body(data):
    lang = current_language()
    created_voice_obj = get_voice_intake_preview()
    telegram_sync_items = load_existing_telegram_intake_sync()
    client_threads = build_client_work_threads(telegram_sync_items, limit=20)
    telegram_sync_rows = client_thread_rows(client_threads, empty_text=tx("no_items", lang), limit=8)
    approved_rows = work_object_rows(approved_preview_items(), empty_text=tx("no_items", lang), limit=5, show_source=True)
    pending_items = client_threads + pending_or_held_preview_items()
    if created_voice_obj and all(o.get("object_id") != created_voice_obj.get("object_id") for o in pending_items):
        pending_items = [created_voice_obj] + pending_items
    pending_rows = work_object_rows(pending_items, empty_text=tx("no_items", lang), limit=5, show_source=True)
    intake_cards = (
        channel_card(tx("voice_command", lang), tx("voice_command_hint", lang), "ready · voice first", "🎙")
        + channel_card(tx("whatsapp_business", lang), "Client messages, photos, object images, documents and estimate requests flow into NinaOS work intake.", "connector foundation", "🟢")
        + channel_card(tx("telegram_channel", lang), "Telegram remains the fast owner/work-intake channel and stays separate from web runtime.", "active runtime", "✈")
        + channel_card(tx("email_channel", lang), "Offers, invoices and formal files can later be received and sent back through email.", "planned bridge", "✉")
        + channel_card(tx("files_channel", lang), "Scanned documents, phone photos, PDFs and object images become client work material.", "document intake", "▤")
        + channel_card(tx("owner_approval_gate", lang), "Nina prepares the work; owner approves sensitive sending, finance and client-facing actions.", "safe mode", "✓")
    )
    timeline = "".join([
        "<div class='row'><div><b>1. Client sends voice/photo/document</b><span class='muted'>WhatsApp / Telegram / web upload / email</span></div><span class='pill'>intake</span></div>",
        "<div class='row'><div><b>2. Nina understands and structures it</b><span class='muted'>client · task · estimate · invoice · files · notes</span></div><span class='pill'>AI prepare</span></div>",
        "<div class='row'><div><b>3. Owner approves</b><span class='muted'>Approve / Hold / Reject before sending or saving permanently</span></div><span class='pill'>control</span></div>",
        "<div class='row'><div><b>4. Nina sends back</b><span class='muted'>WhatsApp / Telegram / email with prepared documents or answer</span></div><span class='pill'>send back</span></div>",
    ])
    return (
        work_page_header(tx("channel_hub", lang), tx("channel_hub_sub", lang))
        + f"<section class='card card-pad hero-card'><div class='hero-lockup'>{nina_logo_html('hero')}<div><div class='hero-title'>Nina<span>OS</span></div><div class='subtitle'>{tx('modern_intake', lang).upper()}</div></div></div><div class='bigline'>{tx('twenty_second_century', lang)}</div><br><div class='btns'><a class='btn primary' href='{q('/office-manager/actions')}'>{tx('voice_command', lang)}</a><a class='btn' href='{q('/tasks')}'>{tx('tasks', lang)}</a><a class='btn' href='{q('/clients')}'>{tx('clients', lang)}</a></div></section><br>"
        + voice_intake_form_html(created_voice_obj)
        + "<br>"
        + telegram_db_diagnostic_block_html()
        + "<section class='card card-pad'><div class='section-title'>✈ Telegram → Client Work Threads</div><p class='muted'>V45.4 FIX groups existing app.py memory into cleaner client work threads: follow-ups stay follow-ups, estimates stay estimates, and only real photos/files become document intake threads.</p><div class='list'>" + telegram_sync_rows + "</div><div class='safe-note'>V45.4 FIX safe mode: existing Telegram memory is grouped into cleaner client work threads and approval/work queues. Web reads only; DB writes still come later.</div></section><br>"
        + f"<section><div class='section-title'>{tx('connected_channels', lang)}</div><div class='worker-grid'>{intake_cards}</div></section><br>"
        + f"<section class='card card-pad'><div class='section-title'>🧠 Omnichannel Client Memory</div><div class='list'><div class='row'><div><b>WhatsApp / Telegram / voice / files</b><span class='muted'>Every client message, audio transcript, photo, scan and document is designed to land in NinaOS, attach to the client workspace, and wait for owner approval.</span></div><span class='pill'>V45.4 FIX thread classifier</span></div><div class='row'><div><b>Nina organizes, owner controls</b><span class='muted'>Nina prepares tasks, estimates, invoices, document packs and send-back actions; the owner approves before sensitive client-facing actions.</span></div><span class='pill'>safe mode</span></div></div></section><br>"
        + "<div class='two-col'>"
        + f"<section class='card card-pad'><div class='section-title'>{tx('client_timeline', lang)}</div><div class='list'>{timeline}</div></section>"
        + f"<section class='card card-pad'><div class='section-title'>{tx('ai_auto_prepare', lang)}</div><div class='list'>{pending_rows}</div><div class='safe-note'>{tx('safe_note', lang)}</div></section>"
        + "</div><br>"
        + f"<section class='card card-pad'><div class='section-title'>{tx('owner_send_back', lang)}</div><div class='list'>{approved_rows}</div><div class='safe-note'>{tx('approved_work_note', lang)}</div></section>"
    )


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
        rows += f"<div class='row'><div><b>{tx('object_id', lang)}</b><span class='muted'>{html_escape(obj.get('object_id'))}</span></div><span class='pill'>V43.3</span></div>"
        rows += f"<div class='row'><div><b>{tx('object_type', lang)}</b><span class='muted'>{html_escape(obj.get('object_type'))}</span></div><span class='pill'>{html_escape(obj.get('status'))}</span></div>"
        meta = obj.get('metadata', {}) if isinstance(obj.get('metadata'), dict) else {}
        rows += f"<div class='row'><div><b>{tx('approval_state', lang)}</b><span class='muted'>{html_escape(approval_label_from_state(meta.get('approval_state'), lang))}</span></div><span class='pill'>safe</span></div>"
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
    preview_rows = work_object_rows(pending_or_held_preview_items(), empty_text=tx("no_items", lang), limit=5, show_source=True, show_approval=True)
    approved_rows = work_object_rows(approved_preview_items(), empty_text=tx("no_items", lang), limit=5, show_source=True, show_approval=True)
    rejected_rows = work_object_rows(rejected_preview_items(), empty_text=tx("no_items", lang), limit=5, show_source=True, show_approval=True)
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
        + f"<section class='card card-pad'><div class='section-title'>{tx('approval_workspace_bridge', lang)}</div><div class='list'>{preview_rows}</div><div class='safe-note'>{tx('safe_note', lang)}</div></section><br>"
        + f"<section class='card card-pad'><div class='section-title'>{tx('approved_workspace_queue', lang)}</div><div class='list'>{approved_rows}</div><div class='safe-note'>{tx('approved_work_note', lang)}</div></section><br>"
        + f"<section class='card card-pad'><div class='section-title'>{tx('rejected_preview_log', lang)}</div><div class='list'>{rejected_rows}</div></section><br>"
        + forms
    )



def office_manager_body(data):
    lang = current_language()
    tasks = [o for o in data["tasks"] if o.get("object_type") in ["task", "followup_task"]]
    invoices = [o for o in data["tasks"] if o.get("object_type") == "invoice"]
    estimates = [o for o in data["tasks"] if o.get("object_type") == "estimate"]

    def mini_list(items, empty_text):
        return work_object_rows(items, empty_text=empty_text, limit=5, show_source=True)

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
        + "<br>"
        + f"<section class='card card-pad'><div class='section-title'>{tx('real_task_surface_bridge', lang)}</div><div class='list'>{work_object_rows(approved_preview_items(), empty_text=tx('no_items', lang), limit=5, show_source=True)}</div><div class='safe-note'>{tx('approved_work_note', lang)}</div></section>"
        + "<br>"
        + f"<section class='card card-pad'><div class='section-title'>{tx('approval_workspace_bridge', lang)}</div><div class='list'>{work_object_rows(pending_or_held_preview_items(), empty_text=tx('no_items', lang), limit=5, show_source=True)}</div><div class='safe-note'>{tx('safe_note', lang)}</div></section>"
        + "<br>"
        + f"<section class='card card-pad'><div class='section-title'>{tx('approved_workspace_queue', lang)}</div><div class='list'>{work_object_rows(approved_preview_items(), empty_text=tx('no_items', lang), limit=5, show_source=True)}</div><div class='safe-note'>{tx('approved_work_note', lang)}</div></section>"
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


@app.route("/inbox", methods=["GET", "POST"])
def inbox():
    return Response(page(tx("channel_hub"), channel_hub_body(load_workspace_data()), "inbox"), mimetype="text/html")


@app.route("/channel-hub")
def channel_hub():
    return redirect(q("/inbox"))


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


@app.route("/diagnostics/telegram-sync")
def diagnostics_telegram_sync():
    return telegram_bridge_db_diagnostics()

@app.route("/health")
def health():
    
    diag = telegram_bridge_db_diagnostics()
    return {
        "ok": True,
        "runtime": "web_app.py",
        "version": WEB_APP_VERSION,
        "language": current_language(),
        "preview_objects": len(WORKSPACE_ACTION_PREVIEWS),
        "approved_preview_objects": len(approved_preview_items()),
        "pending_or_held_preview_objects": len(pending_or_held_preview_items()),
        "rejected_preview_objects": len(rejected_preview_items()),
        "telegram_intake_sync_items": len(load_existing_telegram_intake_sync()),
        "real_intake_store_items": len(load_real_intake_events_from_db()),
        "existing_task_memory_items": len(load_existing_task_engine_memory_from_db()),
        "existing_voice_photo_items": len(load_existing_voice_photo_state_from_db()),
        "existing_recent_conversation_items": len(load_recent_conversation_state_from_db()),
        "existing_tasks_table_items": len(load_existing_tasks_table_from_db()),
        "db_diagnostic": {
            "database_url_present": diag.get("database_url_present"),
            "db_connect_ok": diag.get("db_connect_ok"),
            "tables": diag.get("tables"),
            "counts": diag.get("counts"),
            "web_reader_counts": diag.get("web_reader_counts"),
            "db_error": diag.get("db_error"),
        },
        "time": datetime.utcnow().isoformat() + "Z",
    }


if __name__ == "__main__":
    port = safe_int(os.environ.get("PORT"), 8080)
    app.run(host="0.0.0.0", port=port)
