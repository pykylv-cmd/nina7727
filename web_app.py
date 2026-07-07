# web_app.py
# NinaOS Web App V34 — Sprint C1 Web Workspace Foundation
# Web Railway service start command: python web_app.py
# Telegram Railway service start command stays: python app.py

import os
from datetime import datetime
from flask import Flask, Response, redirect, jsonify

WEB_APP_VERSION = "Web App V34 — Sprint C1 Web Workspace Foundation"
app = Flask(__name__)


def _safe_int(v, default=8080):
    try:
        return int(v)
    except Exception:
        return default


def _esc(s):
    return str(s or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _obj_dict(o):
    if isinstance(o, dict):
        d = dict(o)
    else:
        d = {
            "object_id": getattr(o, "object_id", ""),
            "object_type": getattr(o, "object_type", ""),
            "title": getattr(o, "title", ""),
            "status": getattr(o, "status", ""),
            "priority": getattr(o, "priority", "normal"),
            "client_id": getattr(o, "client_id", ""),
            "project_id": getattr(o, "project_id", ""),
            "due_date": getattr(o, "due_date", ""),
            "metadata": getattr(o, "metadata", {}) or {},
        }
    d.setdefault("metadata", {})
    return d


def load_workspace_data():
    objects = []
    try:
        from work_objects import seed_demo_work_objects, list_work_objects
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

    objects = [_obj_dict(o) for o in objects]
    if not objects:
        objects = [
            {"object_id":"task_1","object_type":"task","title":"Prepare today workspace priorities","status":"open","priority":"high","due_date":"today","metadata":{"client_name":"","owner":"Nina Office Manager"}},
            {"object_id":"followup_1","object_type":"followup_task","title":"Follow up with Demo Client about offer","status":"scheduled","priority":"normal","due_date":"friday","metadata":{"client_name":"Demo Client","owner":"Nina Sales"}},
            {"object_id":"estimate_1","object_type":"estimate","title":"Demo estimate draft","status":"draft","priority":"normal","metadata":{"client_name":"Demo Client","owner":"Nina Estimator"}},
            {"object_id":"invoice_1","object_type":"invoice","title":"Demo invoice follow-up","status":"sent","priority":"normal","due_date":"today","metadata":{"client_name":"Demo Client","owner":"Nina Office Manager"}},
            {"object_id":"project_1","object_type":"project","title":"Demo active project","status":"active","priority":"normal","metadata":{"client_name":"Demo Client","owner":"Nina Office Manager"}},
        ]

    workers = [
        {"name":"Nina Sales","role":"AI Sales Executive","status":"ACTIVE","detail":"1 follow-up to handle","tone":"purple"},
        {"name":"Nina Estimator","role":"AI Estimator","status":"ACTIVE","detail":"1 estimate in progress","tone":"blue"},
        {"name":"Nina Office Manager","role":"AI Office Manager","status":"ACTIVE","detail":"1 task · 1 active project","tone":"green"},
        {"name":"Nina Support","role":"AI Support Specialist","status":"IDLE","detail":"No support queue yet","tone":"orange"},
    ]

    clients = {}
    for o in objects:
        meta = o.get("metadata") if isinstance(o.get("metadata"), dict) else {}
        name = meta.get("client_name") or o.get("client_name") or o.get("client_id") or ""
        if not name:
            continue
        clients.setdefault(name, {"name": name, "followups":0, "estimates":0, "invoices":0, "projects":0, "objects":0})
        clients[name]["objects"] += 1
        t = o.get("object_type")
        if t == "followup_task": clients[name]["followups"] += 1
        if t in ["estimate", "offer"]: clients[name]["estimates"] += 1
        if t == "invoice": clients[name]["invoices"] += 1
        if t == "project": clients[name]["projects"] += 1
    if not clients:
        clients["Demo Client"] = {"name":"Demo Client","followups":1,"estimates":1,"invoices":1,"projects":1,"objects":4}

    activity = []
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
        for e in events:
            if isinstance(e, dict):
                activity.append({"title": e.get("title","Activity"), "body": e.get("body") or e.get("description") or e.get("message", ""), "kind": e.get("kind") or e.get("event_type") or "info"})
            else:
                activity.append({"title": getattr(e,"title","Activity"), "body": getattr(e,"body","") or getattr(e,"description", ""), "kind": getattr(e,"kind","info")})
    except Exception:
        pass
    if not activity:
        activity = [
            {"title":"Web service online","body":"NinaOS web runtime is separated from Telegram runtime.","kind":"info"},
            {"title":"Workspace loaded","body":"Shared C1 workspace data layer is active.","kind":"info"},
            {"title":"Follow-up queue ready","body":"Client follow-ups are visible on work pages.","kind":"work"},
            {"title":"Exchange preview visible","body":"AI worker catalog is available inside the web product.","kind":"api"},
        ]

    active = lambda o: o.get("status") not in ["done","completed","deleted","archived","cancelled","canceled"]
    counts = {
        "tasks_today": len([o for o in objects if o.get("object_type") == "task" and active(o)]),
        "followups": len([o for o in objects if o.get("object_type") == "followup_task" and active(o)]),
        "invoices": len([o for o in objects if o.get("object_type") == "invoice" and active(o)]),
        "estimates": len([o for o in objects if o.get("object_type") in ["estimate","offer"] and active(o)]),
        "projects": len([o for o in objects if o.get("object_type") == "project" and o.get("status") in ["active","open","in_progress"]]),
        "clients": len(clients),
        "workers": len(workers),
    }
    return {"owner":"Katrin","objects":objects,"workers":workers,"clients":list(clients.values()),"activity":activity,"counts":counts}


STYLE = """
:root{--bg:#070914;--panel:#0d1224cc;--panel2:#111a31e6;--line:#263452;--text:#f6f8ff;--muted:#9fb2d6;--blue:#1688ff;--purple:#7b3cff;--green:#35e59a;--orange:#ffb65c}*{box-sizing:border-box}body{margin:0;min-height:100vh;background:radial-gradient(circle at 15% 10%,rgba(85,62,255,.22),transparent 28%),radial-gradient(circle at 80% 15%,rgba(0,153,255,.18),transparent 28%),#070914;color:var(--text);font-family:Inter,Segoe UI,Arial,sans-serif}a{color:inherit;text-decoration:none}.layout{display:grid;grid-template-columns:210px 1fr;min-height:100vh}.sidebar{position:sticky;top:0;height:100vh;padding:22px 16px;background:linear-gradient(180deg,rgba(13,18,36,.94),rgba(7,9,20,.85));border-right:1px solid var(--line)}.brand{display:flex;align-items:center;gap:10px;margin-bottom:28px;font-weight:900}.logo{width:34px;height:34px;border-radius:50%;background:radial-gradient(circle at 35% 35%,#31d9ff,transparent 20%),radial-gradient(circle at 70% 35%,#914cff,transparent 23%),#101b3c;box-shadow:0 0 22px rgba(80,120,255,.55)}.brand span{color:#338cff}.nav{display:flex;flex-direction:column;gap:7px}.nav-item{display:flex;align-items:center;gap:10px;padding:11px 12px;border-radius:12px;color:#d9e4ff;font-size:14px;border:1px solid transparent}.nav-item:hover{background:rgba(255,255,255,.055);border-color:rgba(255,255,255,.08)}.nav-item.active{background:linear-gradient(90deg,rgba(25,122,255,.95),rgba(103,58,255,.85));color:white;box-shadow:0 10px 28px rgba(25,122,255,.2)}.new{margin-left:auto;font-size:10px;padding:2px 6px;border-radius:999px;background:#5638ff}.user{position:absolute;bottom:18px;left:16px;right:16px;border:1px solid var(--line);background:rgba(255,255,255,.04);border-radius:16px;padding:12px;color:var(--muted);font-size:13px}.main{padding:22px 26px 40px;max-width:1440px;width:100%;margin:0 auto}.topbar{display:flex;justify-content:space-between;align-items:center;margin-bottom:18px}.search{width:min(520px,55vw);border:1px solid var(--line);border-radius:18px;padding:14px 18px;color:var(--muted);background:rgba(255,255,255,.045)}.icons{display:flex;align-items:center;gap:10px}.icon{width:34px;height:34px;border-radius:50%;display:grid;place-items:center;background:rgba(255,255,255,.06);border:1px solid rgba(255,255,255,.08)}.avatar{background:linear-gradient(135deg,#893cff,#d747ff);font-weight:900}.grid{display:grid;gap:18px}.hero-grid{display:grid;grid-template-columns:1.05fr 1fr;gap:18px}.card{background:linear-gradient(180deg,rgba(17,26,49,.82),rgba(10,14,29,.82));border:1px solid var(--line);border-radius:24px;box-shadow:0 18px 60px rgba(0,0,0,.22)}.card-pad{padding:24px}.hero-logo{display:flex;align-items:center;justify-content:center;gap:24px;min-height:250px}.globe{width:150px;height:150px;border-radius:50%;background:repeating-linear-gradient(90deg,transparent 0 13px,rgba(106,82,255,.55) 14px 17px),radial-gradient(circle at 35% 30%,#20d7ff,#2e58ff 38%,#7d3dff 68%,#0a1028 100%);box-shadow:0 0 42px rgba(42,137,255,.42)}.hero-title{font-size:70px;line-height:.9;font-weight:950;letter-spacing:-4px}.hero-title span{color:#208dff}.subtitle{color:var(--muted);font-weight:700;letter-spacing:2px;font-size:13px;margin-top:10px}.bigline{text-align:center;font-size:25px;line-height:1.35;font-weight:900;margin-top:18px}.kpis{display:grid;grid-template-columns:repeat(4,1fr);gap:12px}.kpi{padding:18px;border:1px solid var(--line);background:rgba(255,255,255,.045);border-radius:18px}.kpi small{color:var(--muted);font-weight:800}.kpi strong{display:block;font-size:36px;margin:8px 0 2px}.kpi em{color:#72e6ff;font-style:normal;font-size:13px;font-weight:800}.section-title{font-size:20px;font-weight:950;margin:6px 0 12px}.worker-grid{display:grid;grid-template-columns:repeat(4,minmax(160px,1fr));gap:16px}.worker-card{overflow:hidden;border-radius:20px;border:1px solid var(--line);background:rgba(255,255,255,.04);min-height:245px}.worker-top{height:108px;display:grid;place-items:center}.tone-purple{background:linear-gradient(135deg,#4431e8,#6421a8)}.tone-blue{background:linear-gradient(135deg,#0077ff,#08387d)}.tone-green{background:linear-gradient(135deg,#00b970,#125b3d)}.tone-orange{background:linear-gradient(135deg,#d77517,#56321c)}.worker-avatar{width:78px;height:78px;border-radius:50%;background:radial-gradient(circle at 35% 30%,#ffe5bd 0 18%,#e98b31 20% 52%,#5f3825 54% 72%,#f8d7ad 73%);box-shadow:0 12px 32px rgba(0,0,0,.28)}.worker-body{padding:16px}.worker-body h3{margin:0 0 4px;font-size:20px}.muted{color:var(--muted)}.status{font-weight:900;font-size:12px;margin:10px 0}.active-dot{color:var(--green)}.idle-dot{color:#ffd057}.two-col{display:grid;grid-template-columns:1fr 1fr;gap:18px}.list{display:flex;flex-direction:column;gap:10px}.row{display:flex;justify-content:space-between;gap:12px;padding:13px 14px;border:1px solid var(--line);border-radius:14px;background:rgba(255,255,255,.04)}.row b{display:block;margin-bottom:3px}.pill{display:inline-flex;align-items:center;gap:6px;padding:6px 10px;border-radius:999px;background:rgba(38,117,255,.15);border:1px solid rgba(75,145,255,.28);color:#cfe3ff;font-size:12px;font-weight:900;white-space:nowrap}.btns{display:flex;gap:12px;flex-wrap:wrap}.btn{display:inline-flex;align-items:center;justify-content:center;padding:12px 18px;border-radius:13px;border:1px solid var(--line);font-weight:900;background:rgba(255,255,255,.05)}.btn.primary{background:linear-gradient(90deg,#178cff,#6b3cff);border-color:transparent}.page-title h1{margin:0;font-size:42px;letter-spacing:-1.5px}.page-title p{margin:6px 0 0;color:var(--muted);font-weight:700}.footer-note{margin-top:22px;color:var(--muted);font-size:13px;text-align:center}@media(max-width:1050px){.layout{grid-template-columns:1fr}.sidebar{position:relative;height:auto}.user{position:static;margin-top:18px}.hero-grid,.two-col{grid-template-columns:1fr}.worker-grid{grid-template-columns:repeat(2,1fr)}.kpis{grid-template-columns:repeat(2,1fr)}}@media(max-width:620px){.main{padding:16px}.worker-grid,.kpis{grid-template-columns:1fr}.hero-logo{flex-direction:column}.hero-title{font-size:54px;text-align:center}}
"""


def page(title, body, active="dashboard"):
    nav = [("dashboard","Dashboard","/dashboard","⌂"),("workers","Workers","/workers","♙"),("tasks","Tasks","/tasks","☑"),("clients","Clients","/clients","●"),("projects","Projects","/projects","▣"),("calendar","Calendar","/calendar","◫"),("files","Files","/files","▤"),("analytics","Analytics","/analytics","⌁"),("exchange","Exchange","/exchange","◎")]
    nav_html = "".join([f"<a class='nav-item {'active' if k==active else ''}' href='{h}'><span>{i}</span><b>{l}</b>{'<span class=new>NEW</span>' if k=='exchange' else ''}</a>" for k,l,h,i in nav])
    return f"""<!doctype html><html><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'><title>{_esc(title)} · NinaOS</title><style>{STYLE}</style></head><body><div class='layout'><aside class='sidebar'><a href='/dashboard' class='brand'><div class='logo'></div><div>Nina<span>OS</span></div></a><nav class='nav'>{nav_html}</nav><div class='user'><b>Katrin</b><br>Owner<br><br><span class='pill'>Runtime: web_app.py</span></div></aside><main class='main'><div class='topbar'><div class='search'>Search anything...</div><div class='icons'><div class='icon'>🔔</div><div class='icon'>🌐</div><div class='icon'>☼</div><div class='icon avatar'>K</div></div></div>{body}<div class='footer-note'>{WEB_APP_VERSION} · Web service separate from Telegram app.py</div></main></div></body></html>"""


def kpi(label, value, href, text="Live data"):
    return f"<a class='kpi' href='{href}'><small>{label}</small><strong>{value}</strong><em>{text}</em></a>"


def worker_card(w):
    dot = "active-dot" if w["status"] == "ACTIVE" else "idle-dot"
    return f"<a class='worker-card' href='/workers'><div class='worker-top tone-{w['tone']}'><div class='worker-avatar'></div></div><div class='worker-body'><h3>{_esc(w['name'])}</h3><div class='muted'>{_esc(w['role'])}</div><div class='status'><span class='{dot}'>●</span> {_esc(w['status'])}</div><b>{_esc(w['detail'])}</b></div></a>"


def activity_row(a):
    return f"<div class='row'><div><b>{_esc(a.get('title'))}</b><span class='muted'>{_esc(a.get('body'))}</span></div><span class='pill'>{_esc(a.get('kind','info'))}</span></div>"


def header(title, subtitle):
    return f"<section class='card card-pad'><div class='page-title'><h1>{_esc(title)}</h1><p>{_esc(subtitle)}</p></div><br><div class='btns'><a class='btn primary' href='/dashboard'>Dashboard</a><a class='btn' href='/tasks'>Tasks</a><a class='btn' href='/clients'>Clients</a><a class='btn' href='/workers'>Workers</a><a class='btn' href='/exchange'>Exchange</a></div></section><br>"


def dashboard_body(d):
    c = d["counts"]
    kpis = f"<div class='kpis'>{kpi('Tasks Today',c['tasks_today'],'/tasks','Open work')}{kpi('Follow-ups',c['followups'],'/tasks','Need attention')}{kpi('Invoices',c['invoices'],'/clients','Finance')}{kpi('Projects',c['projects'],'/projects','Active')}</div>"
    workers = "".join(worker_card(w) for w in d["workers"])
    activity = "".join(activity_row(a) for a in d["activity"][:6])
    return f"""<div class='grid'><div class='hero-grid'><section class='card card-pad'><div class='hero-logo'><div class='globe'></div><div><div class='hero-title'>Nina<span>OS</span></div><div class='subtitle'>AI WORKFORCE OPERATING SYSTEM</div></div></div><div class='bigline'>One Platform. Unlimited AI Workers.<br>For every business. Everywhere.</div><br><div class='btns'><a class='btn primary' href='/tasks'>Open Work Queue</a><a class='btn' href='/exchange'>Explore Exchange</a></div></section><section class='card card-pad'><div class='page-title'><h1>Good morning, {_esc(d['owner'])} 👋</h1><p>Here’s what needs attention in your NinaOS workspace today.</p></div><br>{kpis}<br><div class='card card-pad' style='background:rgba(24,96,255,.12)'><div class='section-title'>Global AI Workforce</div><p class='muted'>Connected. Intelligent. Tireless.</p><a class='btn' href='/exchange'>View Global Network →</a></div></section></div><section><div class='section-title'>Your AI Workforce</div><div class='worker-grid'>{workers}</div></section><div class='two-col'><section class='card card-pad'><div class='section-title'>Recent Activity</div><div class='list'>{activity}</div></section><section class='card card-pad'><div class='section-title'>Workspace Snapshot</div><div class='kpis'>{kpi('Clients',c['clients'],'/clients','CRM')}{kpi('Workers',c['workers'],'/workers','AI workforce')}{kpi('Estimates',c['estimates'],'/tasks','In progress')}{kpi('Invoices',c['invoices'],'/clients','Due / sent')}</div><br><div class='btns'><a class='btn primary' href='/tasks'>Tasks</a><a class='btn' href='/clients'>Clients</a><a class='btn' href='/projects'>Projects</a><a class='btn' href='/workers'>Workers</a></div></section></div></div>"""


def rows_for_objects(objects):
    rows = ""
    for o in objects:
        meta = o.get("metadata") if isinstance(o.get("metadata"), dict) else {}
        client = meta.get("client_name") or o.get("client_id") or "Workspace"
        rows += f"<div class='row'><div><b>{_esc(o.get('title'))}</b><span class='muted'>{_esc(client)} · {_esc(o.get('object_type'))}</span></div><span class='pill'>{_esc(o.get('status'))} · {_esc(o.get('priority'))}</span></div>"
    return rows


@app.route("/")
def home():
    return redirect("/dashboard")

@app.route("/dashboard")
def dashboard():
    d = load_workspace_data()
    return Response(page("Dashboard", dashboard_body(d), "dashboard"), mimetype="text/html")

@app.route("/workers")
def workers():
    d = load_workspace_data()
    return Response(page("Workers", header("Workers", "AI workforce control surface.") + f"<div class='worker-grid'>{''.join(worker_card(w) for w in d['workers'])}</div>", "workers"), mimetype="text/html")

@app.route("/tasks")
def tasks():
    d = load_workspace_data(); objs = [o for o in d["objects"] if o.get("object_type") in ["task","followup_task","estimate","invoice"]]
    return Response(page("Tasks", header("Tasks", "Live task and follow-up queue from NinaOS workspace.") + f"<section class='card card-pad'><div class='list'>{rows_for_objects(objs)}</div></section>", "tasks"), mimetype="text/html")

@app.route("/clients")
def clients():
    d = load_workspace_data(); rows = ""
    for c in d["clients"]:
        rows += f"<div class='row'><div><b>{_esc(c['name'])}</b><span class='muted'>follow-ups: {c['followups']} · estimates: {c['estimates']} · invoices: {c['invoices']} · projects: {c['projects']}</span></div><a class='pill' href='/tasks'>Open work</a></div>"
    return Response(page("Clients", header("Clients", "CRM workspace for client work, follow-ups, estimates and invoices.") + f"<section class='card card-pad'><div class='list'>{rows}</div></section>", "clients"), mimetype="text/html")

@app.route("/projects")
def projects():
    d = load_workspace_data(); objs = [o for o in d["objects"] if o.get("object_type") == "project"] or [{"title":"Demo active project","object_type":"project","status":"active","priority":"normal","metadata":{"client_name":"Demo Client"}}]
    return Response(page("Projects", header("Projects", "Project operations view with linked client work.") + f"<section class='card card-pad'><div class='list'>{rows_for_objects(objs)}</div></section>", "projects"), mimetype="text/html")

@app.route("/calendar")
def calendar():
    body = header("Calendar", "Schedule and due work preview.") + "<section class='card card-pad'><div class='list'><div class='row'><div><b>Today</b><span class='muted'>Workspace priorities and follow-ups</span></div><span class='pill'>live</span></div><div class='row'><div><b>Follow-up Friday</b><span class='muted'>Ask Andris about reply</span></div><span class='pill'>scheduled</span></div></div></section>"
    return Response(page("Calendar", body, "calendar"), mimetype="text/html")

@app.route("/files")
def files():
    body = header("Files", "Document workspace for client and project files.") + "<section class='card card-pad'><div class='list'><div class='row'><div><b>Demo client package</b><span class='muted'>Ready for organization</span></div><span class='pill'>document</span></div><div class='row'><div><b>Invoice admin record</b><span class='muted'>Linked to workspace</span></div><span class='pill'>finance</span></div></div></section>"
    return Response(page("Files", body, "files"), mimetype="text/html")

@app.route("/analytics")
def analytics():
    d = load_workspace_data(); c = d["counts"]
    body = header("Analytics", "Operational workspace analytics preview.") + f"<section class='card card-pad'><div class='kpis'>{kpi('Tasks',c['tasks_today'],'/tasks','today')}{kpi('Follow-ups',c['followups'],'/tasks','attention')}{kpi('Clients',c['clients'],'/clients','CRM')}{kpi('Workers',c['workers'],'/workers','active')}</div></section>"
    return Response(page("Analytics", body, "analytics"), mimetype="text/html")

@app.route("/exchange")
def exchange():
    catalog = [("Nina Sales","AI Sales Executive","€99/month","purple"),("Nina Estimator","AI Estimator","€119/month","blue"),("Nina Office Manager","AI Office Manager","€89/month","green"),("Nina Support","AI Support Specialist","€79/month","orange"),("Nina Marketing","AI Marketing Specialist","€99/month","purple"),("Nina HR","AI HR Assistant","€89/month","orange")]
    cards = "".join([f"<div class='worker-card'><div class='worker-top tone-{tone}'><div class='worker-avatar'></div></div><div class='worker-body'><h3>{name}</h3><div class='muted'>{role}</div><div class='status'>★ 4.8</div><b>{price}</b><br><br><a class='btn' href='/workers'>View Details</a></div></div>" for name,role,price,tone in catalog])
    return Response(page("Exchange", header("Exchange", "AI Workers Marketplace — preview catalog.") + f"<div class='worker-grid'>{cards}</div>", "exchange"), mimetype="text/html")

@app.route("/health")
def health():
    return jsonify({"ok": True, "runtime": "web_app.py", "version": WEB_APP_VERSION, "time": datetime.utcnow().isoformat()+"Z"})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=_safe_int(os.environ.get("PORT"), 8080))
