# web_app.py
# NinaOS Web App V35 — C1.1 Visual Restore
#
# Purpose:
# - Keep Sprint C1 routes and separate web runtime.
# - Restore visual direction closer to earlier NinaOS dashboard.
# - Railway Web service start command: python web_app.py
# - Telegram service start command stays: python app.py

import os
from datetime import datetime
from flask import Flask, Response, redirect

WEB_APP_VERSION = "Web App V35 — C1.1 Visual Restore"
APP_NAME = "NinaOS"

app = Flask(__name__)


def safe_int(value, default=0):
    try:
        return int(value)
    except Exception:
        return default


def html_escape(s):
    return str(s or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


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


def normalize_activity(events):
    result = []
    for e in events or []:
        if isinstance(e, dict):
            result.append({
                "title": e.get("title", "Activity"),
                "body": e.get("body") or e.get("description") or e.get("message", ""),
                "kind": e.get("kind") or e.get("event_type") or "info",
                "time": e.get("time") or e.get("created_at") or "",
            })
        else:
            result.append({
                "title": getattr(e, "title", "Activity"),
                "body": getattr(e, "body", "") or getattr(e, "description", ""),
                "kind": getattr(e, "kind", "info"),
                "time": getattr(e, "created_at", ""),
            })
    return result[:8]


def build_clients_from_objects(objects):
    clients = {}
    for obj in objects:
        meta = obj.get("metadata", {}) if isinstance(obj.get("metadata"), dict) else {}
        name = meta.get("client_name") or obj.get("client_name") or obj.get("client_id") or ""
        if not name:
            continue
        clients.setdefault(name, {
            "name": name,
            "objects": [],
            "followups": 0,
            "estimates": 0,
            "invoices": 0,
            "projects": 0,
        })
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


def load_workspace_data():
    workspace = {
        "workspace_id": "demo_small_business",
        "workspace_name": "Demo Small Business Workspace",
        "owner": "Katrin",
        "workers": [],
        "objects": [],
        "tasks": [],
        "clients": [],
        "projects": [],
        "activity": [],
        "counts": {},
    }

    workspace["workers"] = [
        {"name": "Nina Sales", "role": "AI Sales Executive", "status": "ACTIVE", "detail": "1 follow-up to handle", "tone": "purple", "route": "/workers", "price": "€99/month", "category": "Sales & Growth"},
        {"name": "Nina Estimator", "role": "AI Estimator", "status": "ACTIVE", "detail": "1 estimate in progress", "tone": "blue", "route": "/workers", "price": "€119/month", "category": "Construction"},
        {"name": "Nina Office Manager", "role": "AI Office Manager", "status": "ACTIVE", "detail": "1 task · 1 active project", "tone": "green", "route": "/workers", "price": "€89/month", "category": "Operations"},
        {"name": "Nina Support", "role": "AI Support Specialist", "status": "IDLE", "detail": "No support queue yet", "tone": "orange", "route": "/workers", "price": "€79/month", "category": "Support"},
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

    if not normalized:
        normalized = [
            {"object_id": "task_1", "object_type": "task", "title": "Prepare today workspace priorities", "status": "open", "priority": "high", "client_id": "", "project_id": "", "due_date": "today", "metadata": {"client_name": "", "owner": "Nina Office Manager"}},
            {"object_id": "followup_1", "object_type": "followup_task", "title": "Follow up with Demo Client about offer", "status": "scheduled", "priority": "normal", "client_id": "demo_client", "project_id": "", "due_date": "friday", "metadata": {"client_name": "Demo Client", "owner": "Nina Sales"}},
            {"object_id": "estimate_1", "object_type": "estimate", "title": "Demo estimate draft", "status": "draft", "priority": "normal", "client_id": "demo_client", "project_id": "project_1", "due_date": "", "metadata": {"client_name": "Demo Client", "owner": "Nina Estimator"}},
            {"object_id": "invoice_1", "object_type": "invoice", "title": "Demo invoice follow-up", "status": "sent", "priority": "normal", "client_id": "demo_client", "project_id": "project_1", "due_date": "today", "metadata": {"client_name": "Demo Client", "owner": "Nina Office Manager"}},
            {"object_id": "project_1", "object_type": "project", "title": "Demo active project", "status": "active", "priority": "normal", "client_id": "demo_client", "project_id": "project_1", "due_date": "", "metadata": {"client_name": "Demo Client", "owner": "Nina Office Manager"}},
        ]

    workspace["objects"] = normalized
    workspace["tasks"] = [o for o in normalized if o.get("object_type") in ["task", "followup_task", "estimate", "invoice"]]
    workspace["clients"] = build_clients_from_objects(normalized)
    workspace["projects"] = [o for o in normalized if o.get("object_type") == "project"]

    try:
        from activity_feed import seed_demo_activity_events, list_activity_events
        try:
            seed_demo_activity_events()
        except Exception:
            pass
        try:
            events = list_activity_events(workspace_id="demo_small_business", limit=8) or []
        except TypeError:
            events = list_activity_events(limit=8) or []
        workspace["activity"] = normalize_activity(events)
    except Exception:
        workspace["activity"] = []

    if not workspace["activity"]:
        workspace["activity"] = [
            {"title": "Web service online", "body": "NinaOS web runtime is separated from Telegram runtime.", "kind": "info", "time": "now"},
            {"title": "Workspace loaded", "body": "Shared C1 workspace data layer is active.", "kind": "info", "time": "now"},
            {"title": "Client follow-up scheduled", "body": "Ask Andris about reply.", "kind": "work", "time": "today"},
            {"title": "Exchange preview visible", "body": "AI worker catalog is available inside the web product.", "kind": "api", "time": "today"},
        ]

    active_statuses = ["open", "scheduled", "draft", "sent", "active", "in_progress"]
    workspace["counts"] = {
        "tasks_today": len([o for o in normalized if o.get("object_type") == "task" and o.get("status") in active_statuses]),
        "followups": len([o for o in normalized if o.get("object_type") == "followup_task" and o.get("status") in active_statuses]),
        "invoices": len([o for o in normalized if o.get("object_type") == "invoice" and o.get("status") in active_statuses]),
        "estimates": len([o for o in normalized if o.get("object_type") in ["estimate", "offer"] and o.get("status") in active_statuses]),
        "projects": len([o for o in normalized if o.get("object_type") == "project" and o.get("status") in active_statuses]),
        "clients": len(workspace["clients"]),
        "workers": len(workspace["workers"]),
    }
    return workspace


def nina_logo_html(size="small"):
    return f"""
    <div class="nina-logo {size}">
      <div class="dot-grid"></div>
      <div class="orbit orbit-a"></div>
      <div class="orbit orbit-b"></div>
    </div>
    """


def page(title, body, active="dashboard"):
    nav = [
        ("dashboard", "Dashboard", "/dashboard", "⌂"),
        ("workers", "Workers", "/workers", "♙"),
        ("tasks", "Tasks", "/tasks", "☑"),
        ("clients", "Clients", "/clients", "●"),
        ("projects", "Projects", "/projects", "▣"),
        ("calendar", "Calendar", "/calendar", "◫"),
        ("files", "Files", "/files", "▤"),
        ("analytics", "Analytics", "/analytics", "⌁"),
        ("exchange", "Exchange", "/exchange", "◎"),
    ]
    nav_html = ""
    for key, label, href, icon in nav:
        cls = "nav-item active" if key == active else "nav-item"
        badge = "<span class='new'>NEW</span>" if key == "exchange" else ""
        nav_html += f"<a class='{cls}' href='{href}'><span>{icon}</span><b>{label}</b>{badge}</a>"

    return f'''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html_escape(title)} · NinaOS</title>
<style>
:root {{
  --bg:#06070d; --panel:rgba(18,24,43,.72); --line:rgba(120,153,255,.26); --line2:rgba(255,255,255,.08);
  --text:#f8fbff; --muted:#a8b7d4; --blue:#168dff; --purple:#7c4dff; --green:#34e6a4; --orange:#ffa64d;
  --shadow:0 30px 100px rgba(0,0,0,.36);
}}
* {{ box-sizing:border-box; }}
body {{ margin:0; min-height:100vh; color:var(--text); font-family:Inter, Segoe UI, Arial, sans-serif; background:radial-gradient(circle at 13% 14%, rgba(30,105,255,.20), transparent 25%), radial-gradient(circle at 80% 12%, rgba(80,70,255,.20), transparent 28%), linear-gradient(135deg, #080910 0%, #0a0d19 48%, #05060b 100%); }}
body::before {{ content:""; position:fixed; inset:0; pointer-events:none; background:linear-gradient(rgba(255,255,255,.026) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,.021) 1px, transparent 1px); background-size:44px 44px; mask-image:linear-gradient(to bottom, rgba(0,0,0,.5), transparent 70%); }}
a {{ color:inherit; text-decoration:none; }}
.layout {{ display:grid; grid-template-columns:210px 1fr; min-height:100vh; }}
.sidebar {{ position:sticky; top:0; height:100vh; padding:22px 14px; background:radial-gradient(circle at 28px 28px, rgba(44,142,255,.24), transparent 75px), linear-gradient(180deg, rgba(18,22,37,.86), rgba(8,9,15,.83)); border-right:1px solid var(--line2); backdrop-filter:blur(16px); }}
.brand {{ display:flex; align-items:center; gap:10px; margin:0 6px 28px; font-weight:950; }} .brand-word span:last-child {{ color:#2a91ff; }}
.nina-logo {{ position:relative; border-radius:50%; overflow:hidden; background:radial-gradient(circle at 30% 30%, rgba(255,255,255,.9), transparent 5%), radial-gradient(circle at 65% 25%, rgba(84,232,255,.9), transparent 10%), radial-gradient(circle at 50% 50%, #1de0ff 0%, #2358ff 38%, #7f45ff 72%, #11152a 100%); box-shadow:0 0 24px rgba(49,140,255,.52), inset 0 0 30px rgba(255,255,255,.12); }}
.nina-logo.small {{ width:34px; height:34px; }} .nina-logo.hero {{ width:156px; height:156px; flex:0 0 156px; }}
.dot-grid {{ position:absolute; inset:0; background:radial-gradient(circle, rgba(255,255,255,.86) 0 2px, transparent 2.8px); background-size:16px 16px; transform:rotate(-18deg) scale(1.1); opacity:.58; mask-image:radial-gradient(circle, #000 62%, transparent 70%); }}
.orbit {{ position:absolute; left:-22%; right:-22%; top:44%; height:2px; background:rgba(255,255,255,.45); border-radius:999px; transform:rotate(-16deg); box-shadow:0 0 14px rgba(90,190,255,.8); }} .orbit-b {{ transform:rotate(28deg); opacity:.28; top:54%; }}
.nav {{ display:flex; flex-direction:column; gap:7px; }} .nav-item {{ display:flex; align-items:center; gap:10px; padding:11px 12px; border-radius:13px; color:#dce7ff; font-size:14px; border:1px solid transparent; }}
.nav-item:hover {{ background:rgba(255,255,255,.06); border-color:rgba(255,255,255,.10); }} .nav-item.active {{ background:linear-gradient(90deg, rgba(28,128,255,.95), rgba(90,63,255,.86)); color:#fff; box-shadow:0 14px 32px rgba(23,109,255,.23); }} .new {{ margin-left:auto; font-size:10px; padding:2px 7px; border-radius:999px; background:#5638ff; }}
.user {{ position:absolute; bottom:18px; left:14px; right:14px; border:1px solid var(--line); background:rgba(255,255,255,.045); border-radius:16px; padding:12px; color:var(--muted); font-size:13px; }} .user b {{ color:#fff; }}
.main {{ padding:22px 26px 40px; max-width:1460px; width:100%; margin:0 auto; }} .topbar {{ display:flex; justify-content:space-between; align-items:center; margin-bottom:18px; }}
.search {{ width:min(520px, 55vw); border:1px solid var(--line); border-radius:18px; padding:14px 18px; color:var(--muted); background:rgba(16,24,45,.72); box-shadow:inset 0 0 0 1px rgba(255,255,255,.03), 0 12px 34px rgba(0,0,0,.18); }}
.icons {{ display:flex; gap:10px; }} .icon {{ width:34px; height:34px; border-radius:50%; display:grid; place-items:center; background:rgba(255,255,255,.07); border:1px solid rgba(255,255,255,.10); }} .avatar {{ background:linear-gradient(135deg, #7c43ff, #dc42ff); font-weight:950; }}
.grid {{ display:grid; gap:18px; }} .hero-grid {{ display:grid; grid-template-columns:1.02fr .98fr; gap:18px; }}
.card {{ background:linear-gradient(180deg, rgba(26,36,68,.72), rgba(9,12,24,.70)), radial-gradient(circle at 25% 15%, rgba(40,140,255,.12), transparent 38%); border:1px solid var(--line); border-radius:24px; box-shadow:var(--shadow); backdrop-filter:blur(18px); }} .card-pad {{ padding:24px; }}
.hero-card {{ min-height:390px; display:flex; flex-direction:column; justify-content:center; align-items:center; text-align:center; }} .hero-lockup {{ display:flex; align-items:center; justify-content:center; gap:26px; }}
.hero-title {{ font-size:78px; line-height:.9; font-weight:1000; letter-spacing:-5px; text-shadow:0 10px 40px rgba(0,0,0,.5); }} .hero-title span {{ color:#2493ff; }}
.subtitle {{ color:#dbe8ff; font-weight:900; letter-spacing:2px; font-size:13px; margin-top:10px; }} .bigline {{ margin-top:34px; font-size:25px; line-height:1.35; font-weight:950; }}
.trust {{ display:flex; gap:8px; justify-content:center; flex-wrap:wrap; margin-top:24px; }} .trust span {{ font-size:12px; font-weight:900; padding:7px 12px; border:1px solid var(--line); background:rgba(255,255,255,.04); border-radius:999px; }}
.kpis {{ display:grid; grid-template-columns:repeat(4, 1fr); gap:12px; }} .kpi {{ display:block; padding:18px; border:1px solid var(--line); background:linear-gradient(180deg, rgba(255,255,255,.06), rgba(255,255,255,.025)); border-radius:18px; min-height:118px; }} .kpi small {{ color:#dbe7ff; font-weight:900; }} .kpi strong {{ display:block; font-size:38px; margin:9px 0 2px; }} .kpi em {{ color:#71e9ff; font-style:normal; font-size:13px; font-weight:900; }}
.page-title h1 {{ margin:0; font-size:42px; letter-spacing:-1.8px; line-height:1; }} .page-title p {{ margin:8px 0 0; color:#c3d4f5; font-weight:800; }} .section-title {{ font-size:21px; font-weight:1000; margin:6px 0 13px; }}
.worker-grid {{ display:grid; grid-template-columns:repeat(4, minmax(160px, 1fr)); gap:16px; }} .worker-card {{ overflow:hidden; border-radius:20px; border:1px solid var(--line); background:linear-gradient(180deg, rgba(28,35,60,.78), rgba(9,12,24,.78)); min-height:248px; box-shadow:0 20px 55px rgba(0,0,0,.22); }} .worker-top {{ height:112px; display:grid; place-items:center; position:relative; overflow:hidden; }} .worker-top::before {{ content:""; position:absolute; inset:0; background:repeating-linear-gradient(110deg, rgba(255,255,255,.10) 0 2px, transparent 2px 10px); opacity:.35; }}
.tone-purple {{ background:linear-gradient(135deg, #4830d8, #6322b7); }} .tone-blue {{ background:linear-gradient(135deg, #058aff, #053c8c); }} .tone-green {{ background:linear-gradient(135deg, #02b973, #095a3b); }} .tone-orange {{ background:linear-gradient(135deg, #d47418, #56321c); }}
.worker-avatar {{ position:relative; z-index:1; width:82px; height:82px; border-radius:50%; background:radial-gradient(circle at 36% 30%, #ffe8c8 0 16%, transparent 17%), radial-gradient(circle at 53% 65%, #ffdba8 0 23%, transparent 24%), radial-gradient(circle at 46% 45%, #ef973a 0 45%, #5d3928 46% 62%, #f6c58b 63% 100%); box-shadow:0 16px 34px rgba(0,0,0,.32); }} .worker-body {{ padding:16px; }} .worker-body h3 {{ margin:0 0 4px; font-size:20px; line-height:1.02; }}
.muted {{ color:var(--muted); }} .status {{ font-weight:950; font-size:12px; margin:10px 0; }} .active-dot {{ color:var(--green); }} .idle-dot {{ color:#ffd057; }}
.two-col {{ display:grid; grid-template-columns:1fr 1fr; gap:18px; }} .list {{ display:flex; flex-direction:column; gap:10px; }} .row {{ display:flex; justify-content:space-between; align-items:center; gap:12px; padding:14px 15px; border:1px solid var(--line); border-radius:16px; background:linear-gradient(90deg, rgba(28,111,255,.12), rgba(255,255,255,.035)); }} .row b {{ display:block; margin-bottom:4px; }}
.pill {{ display:inline-flex; align-items:center; padding:7px 11px; border-radius:999px; background:rgba(31,124,255,.16); border:1px solid rgba(76,147,255,.32); color:#d7e8ff; font-size:12px; font-weight:950; white-space:nowrap; }}
.btns {{ display:flex; gap:12px; flex-wrap:wrap; justify-content:center; }} .btn {{ display:inline-flex; align-items:center; justify-content:center; padding:13px 18px; border-radius:14px; border:1px solid var(--line); font-weight:950; background:rgba(255,255,255,.055); box-shadow:0 12px 26px rgba(0,0,0,.18); }} .btn.primary {{ background:linear-gradient(90deg, #168dff, #6443ff); border-color:transparent; }}
.footer-note {{ margin-top:22px; color:var(--muted); font-size:13px; text-align:center; font-weight:700; }}
@media (max-width:1100px) {{ .layout {{ grid-template-columns:1fr; }} .sidebar {{ position:relative; height:auto; }} .user {{ position:static; margin-top:18px; }} .hero-grid, .two-col {{ grid-template-columns:1fr; }} .worker-grid {{ grid-template-columns:repeat(2, 1fr); }} .kpis {{ grid-template-columns:repeat(2, 1fr); }} }}
@media (max-width:640px) {{ .main {{ padding:16px; }} .worker-grid, .kpis {{ grid-template-columns:1fr; }} .hero-lockup {{ flex-direction:column; }} .hero-title {{ font-size:56px; letter-spacing:-3px; }} .nina-logo.hero {{ width:128px; height:128px; flex-basis:128px; }} .search {{ width:58vw; }} }}
</style>
</head>
<body>
<div class="layout">
  <aside class="sidebar">
    <a href="/dashboard" class="brand">{nina_logo_html("small")}<div class="brand-word"><span>Nina</span><span>OS</span></div></a>
    <nav class="nav">{nav_html}</nav>
    <div class="user"><b>Katrin</b><br>Owner<br><br><span class="pill">Runtime: web_app.py</span></div>
  </aside>
  <main class="main">
    <div class="topbar"><div class="search">Search anything...</div><div class="icons"><div class="icon">🔔</div><div class="icon">🌐</div><div class="icon">☼</div><div class="icon avatar">K</div></div></div>
    {body}
    <div class="footer-note">{WEB_APP_VERSION} · Web service separate from Telegram app.py</div>
  </main>
</div>
</body>
</html>'''


def kpi_card(label, value, hint):
    return f"<a class='kpi' href='{hint.get('href', '#')}'><small>{label}</small><strong>{value}</strong><em>{hint.get('text','Live data')}</em></a>"


def worker_card(w, marketplace=False):
    if marketplace:
        extra = f"<div class='status'>★ 4.8 · {html_escape(w.get('category',''))}</div><b>{html_escape(w.get('price',''))}</b><br><br><span class='btn'>View Details</span>"
    else:
        dot = "active-dot" if w["status"] == "ACTIVE" else "idle-dot"
        extra = f"<div class='status'><span class='{dot}'>●</span> {html_escape(w['status'])}</div><b>{html_escape(w['detail'])}</b>"
    return f"""
    <a class="worker-card" href="{w.get('route','/workers')}">
      <div class="worker-top tone-{w.get('tone','blue')}"><div class="worker-avatar"></div></div>
      <div class="worker-body"><h3>{html_escape(w['name'])}</h3><div class="muted">{html_escape(w['role'])}</div>{extra}</div>
    </a>
    """


def activity_row(a):
    return f"<div class='row'><div><b>{html_escape(a.get('title'))}</b><span class='muted'>{html_escape(a.get('body'))}</span></div><span class='pill'>{html_escape(a.get('kind','info'))}</span></div>"


def dashboard_body(data):
    c = data["counts"]
    kpis = f"""
    <div class="kpis">
      {kpi_card('Tasks Today', c['tasks_today'], {'text':'Open work', 'href':'/tasks'})}
      {kpi_card('Follow-ups', c['followups'], {'text':'Need attention', 'href':'/tasks'})}
      {kpi_card('Invoices', c['invoices'], {'text':'Finance', 'href':'/clients'})}
      {kpi_card('Projects', c['projects'], {'text':'Active', 'href':'/projects'})}
    </div>"""
    workers = "".join(worker_card(w) for w in data["workers"])
    activity = "".join(activity_row(a) for a in data["activity"][:6])
    return f"""
    <div class="grid">
      <div class="hero-grid">
        <section class="card card-pad hero-card">
          <div class="hero-lockup">{nina_logo_html('hero')}<div><div class="hero-title">Nina<span>OS</span></div><div class="subtitle">AI WORKFORCE OPERATING SYSTEM</div></div></div>
          <div class="bigline">One Platform. Unlimited AI Workers.<br>For every business. Everywhere.</div><br>
          <div class="btns"><a class="btn primary" href="/tasks">Open Work Queue</a><a class="btn" href="/exchange">Explore Exchange</a></div>
          <div class="trust"><span>GLOBAL</span><span>WORKFORCE</span><span>SECURE</span><span>SCALE</span></div>
        </section>
        <section class="card card-pad">
          <div class="page-title"><h1>Good morning, {html_escape(data['owner'])} 👋</h1><p>Here’s what needs attention in your NinaOS workspace today.</p></div><br>{kpis}<br>
          <div class="card card-pad" style="background:rgba(27,84,255,.16)"><div class="section-title">Global AI Workforce</div><p class="muted">Connected. Intelligent. Tireless.</p><a class="btn" href="/exchange">View Global Network →</a></div>
        </section>
      </div>
      <section><div class="section-title">Your AI Workforce</div><div class="worker-grid">{workers}</div></section>
      <div class="two-col"><section class="card card-pad"><div class="section-title">Recent Activity</div><div class="list">{activity}</div></section><section class="card card-pad"><div class="section-title">Workspace Snapshot</div><div class="kpis">{kpi_card('Clients', c['clients'], {'text':'CRM', 'href':'/clients'})}{kpi_card('Workers', c['workers'], {'text':'AI workforce', 'href':'/workers'})}{kpi_card('Estimates', c['estimates'], {'text':'In progress', 'href':'/tasks'})}{kpi_card('Invoices', c['invoices'], {'text':'Due / sent', 'href':'/clients'})}</div><br><div class="btns"><a class="btn primary" href="/tasks">Tasks</a><a class="btn" href="/clients">Clients</a><a class="btn" href="/projects">Projects</a><a class="btn" href="/workers">Workers</a></div></section></div>
    </div>"""


def work_page_header(title, subtitle):
    return f"""<div class="grid"><section class="card card-pad"><div class="page-title"><h1>{html_escape(title)}</h1><p>{html_escape(subtitle)}</p></div><br><div class="btns"><a class="btn primary" href="/dashboard">Dashboard</a><a class="btn" href="/tasks">Tasks</a><a class="btn" href="/clients">Clients</a><a class="btn" href="/workers">Workers</a><a class="btn" href="/exchange">Exchange</a></div></section></div><br>"""


def tasks_body(data):
    rows = ""
    for obj in data["tasks"]:
        meta = obj.get("metadata", {}) if isinstance(obj.get("metadata"), dict) else {}
        client = meta.get("client_name") or obj.get("client_id") or "Workspace"
        rows += f"<div class='row'><div><b>{html_escape(obj.get('title'))}</b><span class='muted'>{html_escape(client)} · {html_escape(obj.get('object_type'))}</span></div><span class='pill'>{html_escape(obj.get('status'))} · {html_escape(obj.get('priority'))}</span></div>"
    return work_page_header("Tasks", "Live task and follow-up queue from NinaOS workspace.") + f"<section class='card card-pad'><div class='list'>{rows}</div></section>"


def clients_body(data):
    rows = ""
    for client in data["clients"]:
        rows += f"<div class='row'><div><b>{html_escape(client.get('name'))}</b><span class='muted'>follow-ups: {client.get('followups',0)} · estimates: {client.get('estimates',0)} · invoices: {client.get('invoices',0)} · projects: {client.get('projects',0)}</span></div><a class='pill' href='/tasks'>Open work</a></div>"
    return work_page_header("Clients", "CRM workspace for client work, follow-ups, estimates and invoices.") + f"<section class='card card-pad'><div class='list'>{rows}</div></section>"


def projects_body(data):
    items = data["projects"] or [{"title":"Demo active project", "status":"active", "priority":"normal", "metadata":{"client_name":"Demo Client"}}]
    rows = ""
    for p in items:
        meta = p.get("metadata", {}) if isinstance(p.get("metadata"), dict) else {}
        rows += f"<div class='row'><div><b>{html_escape(p.get('title'))}</b><span class='muted'>{html_escape(meta.get('client_name','Workspace'))}</span></div><span class='pill'>{html_escape(p.get('status'))} · {html_escape(p.get('priority','normal'))}</span></div>"
    return work_page_header("Projects", "Project operations view with linked client work.") + f"<section class='card card-pad'><div class='list'>{rows}</div></section>"


def workers_body(data):
    return work_page_header("Workers", "AI workforce control surface.") + f"<div class='worker-grid'>{''.join(worker_card(w) for w in data['workers'])}</div>"


def exchange_body(data):
    catalog = [
        {"name": "Nina Sales", "role": "AI Sales Executive", "price": "€99/month", "category": "Sales & Growth", "tone": "purple", "route": "/workers"},
        {"name": "Nina Estimator", "role": "AI Estimator", "price": "€119/month", "category": "Construction", "tone": "blue", "route": "/workers"},
        {"name": "Nina Office Manager", "role": "AI Office Manager", "price": "€89/month", "category": "Operations", "tone": "green", "route": "/workers"},
        {"name": "Nina Support", "role": "AI Support Specialist", "price": "€79/month", "category": "Support", "tone": "orange", "route": "/workers"},
        {"name": "Nina Marketing", "role": "AI Marketing Specialist", "price": "€99/month", "category": "Marketing", "tone": "purple", "route": "/workers"},
        {"name": "Nina HR", "role": "AI HR Assistant", "price": "€89/month", "category": "HR", "tone": "orange", "route": "/workers"},
    ]
    return work_page_header("Exchange", "AI Workers Marketplace — preview catalog.") + f"<div class='worker-grid'>{''.join(worker_card(w, marketplace=True) for w in catalog)}</div>"


def simple_module_body(title, subtitle, blocks):
    rows = "".join(f"<div class='row'><div><b>{html_escape(b[0])}</b><span class='muted'>{html_escape(b[1])}</span></div><span class='pill'>{html_escape(b[2])}</span></div>" for b in blocks)
    return work_page_header(title, subtitle) + f"<section class='card card-pad'><div class='list'>{rows}</div></section>"


@app.route("/")
def home():
    return redirect("/dashboard")

@app.route("/dashboard")
def dashboard():
    data = load_workspace_data()
    return Response(page("Dashboard", dashboard_body(data), active="dashboard"), mimetype="text/html")

@app.route("/workers")
def workers():
    data = load_workspace_data()
    return Response(page("Workers", workers_body(data), active="workers"), mimetype="text/html")

@app.route("/tasks")
def tasks():
    data = load_workspace_data()
    return Response(page("Tasks", tasks_body(data), active="tasks"), mimetype="text/html")

@app.route("/clients")
def clients():
    data = load_workspace_data()
    return Response(page("Clients", clients_body(data), active="clients"), mimetype="text/html")

@app.route("/projects")
def projects():
    data = load_workspace_data()
    return Response(page("Projects", projects_body(data), active="projects"), mimetype="text/html")

@app.route("/calendar")
def calendar():
    body = simple_module_body("Calendar", "Schedule and due work preview.", [("Today", "Workspace priorities and follow-ups", "live"), ("Follow-up Friday", "Ask Andris about reply", "scheduled"), ("Upcoming", "Calendar integration placeholder", "next")])
    return Response(page("Calendar", body, active="calendar"), mimetype="text/html")

@app.route("/files")
def files():
    body = simple_module_body("Files", "Document workspace for client and project files.", [("Demo client package", "Ready for organization", "document"), ("Invoice admin record", "Linked to workspace", "finance"), ("Estimate draft", "Linked to Demo Client", "estimate")])
    return Response(page("Files", body, active="files"), mimetype="text/html")

@app.route("/analytics")
def analytics():
    data = load_workspace_data()
    c = data["counts"]
    body = work_page_header("Analytics", "Operational workspace analytics preview.")
    body += f"<section class='card card-pad'><div class='kpis'>{kpi_card('Tasks', c['tasks_today'], {'text':'today', 'href':'/tasks'})}{kpi_card('Follow-ups', c['followups'], {'text':'attention', 'href':'/tasks'})}{kpi_card('Clients', c['clients'], {'text':'CRM', 'href':'/clients'})}{kpi_card('Workers', c['workers'], {'text':'active', 'href':'/workers'})}</div></section>"
    return Response(page("Analytics", body, active="analytics"), mimetype="text/html")

@app.route("/exchange")
def exchange():
    data = load_workspace_data()
    return Response(page("Exchange", exchange_body(data), active="exchange"), mimetype="text/html")

@app.route("/health")
def health():
    return {"ok": True, "runtime": "web_app.py", "version": WEB_APP_VERSION, "time": datetime.utcnow().isoformat() + "Z"}

if __name__ == "__main__":
    port = safe_int(os.environ.get("PORT"), 8080)
    app.run(host="0.0.0.0", port=port)
