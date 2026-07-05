from flask import Flask, jsonify

app = Flask(__name__)

APP_VERSION = "Web App V3.1 — Layout Fix"
CORE_VERSION = "V115.4 + Core 2.5.2"

WORKERS = [
    {"name": "Nina Sales", "role": "AI Sales Executive", "status": "ACTIVE", "work": "Following up with 15 leads", "color": "purple", "price": "€99", "rating": "4.9"},
    {"name": "Nina Estimator", "role": "AI Estimator", "status": "ACTIVE", "work": "Working on 3 estimates", "color": "blue", "price": "€119", "rating": "4.9"},
    {"name": "Nina Office Manager", "role": "AI Office Manager", "status": "ACTIVE", "work": "Managing your schedule", "color": "green", "price": "€89", "rating": "4.8"},
    {"name": "Nina Support", "role": "AI Support Specialist", "status": "IDLE", "work": "Waiting for new tasks", "color": "orange", "price": "€79", "rating": "4.8"},
]

CSS = """
<style>
:root{--bg:#050814;--panel:#0b1020;--line:rgba(255,255,255,.10);--text:#f8fbff;--muted:#9aa6c5;--violet:#7c3aed;--blue:#2563eb;--green:#22c55e;--shadow:0 22px 60px rgba(0,0,0,.40)}
*{box-sizing:border-box}body{margin:0;background:radial-gradient(circle at 20% 0%,rgba(124,58,237,.18),transparent 28%),radial-gradient(circle at 80% 10%,rgba(37,99,235,.18),transparent 30%),linear-gradient(180deg,#040711,#070b16);color:var(--text);font-family:Inter,system-ui,Segoe UI,Arial,sans-serif}a{text-decoration:none;color:inherit}
.shell{max-width:1680px;margin:auto;padding:14px}.app{display:grid;grid-template-columns:210px minmax(0,1fr) 310px;gap:14px;min-height:calc(100vh - 28px)}
.sidebar,.main,.rightbar,.section,.card{border:1px solid var(--line);background:rgba(10,15,30,.82);backdrop-filter:blur(18px);box-shadow:var(--shadow)}.sidebar{border-radius:28px;padding:16px;display:flex;flex-direction:column;gap:14px}.brand{display:flex;align-items:center;gap:12px;padding:6px 4px 14px}.logo{width:38px;height:38px;border-radius:50%;background:radial-gradient(circle,#22d3ee 0 10%,#7c3aed 45%,#2563eb 68%,transparent 70%),linear-gradient(135deg,#7c3aed,#2563eb);box-shadow:0 0 34px rgba(124,58,237,.55)}.brand b{font-size:19px}.brand span{display:block;color:var(--muted);font-size:11px}
.nav{display:grid;gap:7px}.nav a{padding:11px 12px;border-radius:14px;color:#dbe4ff;font-size:14px;display:flex;gap:10px;align-items:center;border:1px solid transparent}.nav a:hover,.nav a.active{background:linear-gradient(90deg,rgba(124,58,237,.42),rgba(37,99,235,.22));border-color:rgba(124,58,237,.35)}.badge{margin-left:auto;background:rgba(124,58,237,.28);font-size:10px;border-radius:999px;padding:3px 7px}.sideWorker{margin-top:auto;background:linear-gradient(180deg,rgba(124,58,237,.18),rgba(37,99,235,.10));border:1px solid rgba(124,58,237,.28);border-radius:20px;padding:15px}.sideWorker b{display:block;margin-bottom:7px}.sideWorker p{color:var(--muted);font-size:13px;line-height:1.45;margin:0}
.main{border-radius:28px;padding:18px;overflow:hidden;min-width:0}.top{display:flex;align-items:center;justify-content:space-between;gap:12px;margin-bottom:16px}.search{width:min(560px,100%);background:rgba(255,255,255,.045);border:1px solid var(--line);border-radius:999px;padding:13px 18px;color:#dbe4ff}.topIcons{display:flex;gap:9px;align-items:center}.ico{width:34px;height:34px;border-radius:50%;display:grid;place-items:center;border:1px solid var(--line);background:rgba(255,255,255,.04)}
.hero{position:relative;display:grid;grid-template-columns:1fr 300px;gap:16px;min-height:245px;padding:22px;border:1px solid var(--line);border-radius:26px;background:radial-gradient(circle at 77% 48%,rgba(34,211,238,.15),transparent 24%),linear-gradient(135deg,rgba(17,24,48,.96),rgba(8,13,27,.96));overflow:hidden}.hero h1{margin:0;font-size:29px;letter-spacing:-.04em}.hero p{margin:8px 0 0;color:var(--muted)}.kpis{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin-top:22px}.kpi{background:rgba(255,255,255,.045);border:1px solid rgba(255,255,255,.075);border-radius:18px;padding:14px;min-height:105px}.kpi small{color:#dbe4ff}.kpi .v{font-size:37px;font-weight:900;margin:7px 0 3px}.delta{font-size:13px;color:#86efac}.pink{color:#f0abfc}.blue{color:#93c5fd}
.globeBox{position:relative;display:grid;place-items:center}.globe{width:220px;height:220px;border-radius:50%;position:relative;background:radial-gradient(circle,rgba(37,99,235,.12),rgba(124,58,237,.06) 54%,transparent 68%)}.globe:before{content:"";position:absolute;inset:15px;border-radius:50%;background-image:radial-gradient(circle,rgba(124,58,237,.95) 0 2px,transparent 3px),radial-gradient(circle,rgba(96,165,250,.95) 0 2px,transparent 3px);background-size:18px 18px;background-position:0 0,9px 9px}.orb{position:absolute;border:1px solid rgba(124,58,237,.35);border-radius:50%;width:280px;height:110px;transform:rotate(22deg)}.orb2{transform:rotate(-25deg);height:145px;border-color:rgba(37,99,235,.30)}.globeText{position:absolute;right:4px;top:56px;width:135px}.globeText b{font-size:26px;line-height:1.02;display:block}.globeText span{display:block;color:var(--muted);margin:8px 0 12px;font-size:13px}
.btn{display:inline-flex;align-items:center;justify-content:center;border-radius:13px;padding:11px 15px;font-weight:800;border:1px solid var(--line);background:rgba(255,255,255,.045)}.btn.primary{background:linear-gradient(90deg,var(--violet),var(--blue));border-color:transparent}
.workforce{margin-top:16px}.sectionTitle{font-size:23px;font-weight:900;margin:0 0 12px}.workerGrid{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:14px}.worker{min-height:270px;border-radius:22px;overflow:hidden;background:rgba(255,255,255,.035);border:1px solid var(--line)}.workerTop{height:135px;position:relative}.purple{background:linear-gradient(135deg,#3b1265,#0d1224)}.blueBg{background:linear-gradient(135deg,#0a4d87,#0d1224)}.greenBg{background:linear-gradient(135deg,#0b5b37,#0d1224)}.orangeBg{background:linear-gradient(135deg,#7c3f12,#0d1224)}.face{position:absolute;left:50%;top:55%;transform:translate(-50%,-50%);width:98px;height:98px;border-radius:50%;background:radial-gradient(circle at 35% 31%,#ffe0c9 0 13%,#c88463 14% 24%,transparent 25%),radial-gradient(circle at 50% 56%,#f3c5aa 0 30%,#bd7758 31% 36%,transparent 37%),radial-gradient(circle at 38% 43%,#23140f 0 3%,transparent 4%),radial-gradient(circle at 62% 43%,#23140f 0 3%,transparent 4%),radial-gradient(circle at 50% 20%,#3f2419 0 30%,transparent 31%),linear-gradient(180deg,#6b3d2d,#d39a7b);box-shadow:0 15px 38px rgba(0,0,0,.42),0 0 0 4px rgba(255,255,255,.08)}.workerBody{padding:15px}.workerBody h3{font-size:25px;line-height:1.02;margin:0 0 4px}.workerBody p{margin:0 0 10px;color:var(--muted);font-size:13px}.status{font-size:12px;margin:8px 0}.active{color:#86efac}.idle{color:#fcd34d}.work{font-size:14px;line-height:1.35}
.rightbar{border-radius:28px;padding:18px;display:flex;flex-direction:column;gap:14px;min-width:0}.rbCard{border-radius:22px;border:1px solid var(--line);background:rgba(255,255,255,.035);padding:16px}.rbCard h3{margin:0 0 10px}.ok{color:#86efac;font-weight:800}.chart{height:84px;border-radius:14px;background:linear-gradient(180deg,rgba(124,58,237,.12),transparent);border:1px solid rgba(255,255,255,.05);position:relative;overflow:hidden}.chart svg{position:absolute;inset:0}.ws{display:flex;gap:8px;flex-wrap:wrap}.ws span{width:34px;height:34px;border-radius:50%;display:grid;place-items:center;font-weight:900;font-size:11px;background:linear-gradient(135deg,#7c3aed,#2563eb)}.snapshot{display:grid;gap:9px}.row{display:flex;justify-content:space-between;color:#dbe4ff}.row strong{color:white}.bubble{background:rgba(255,255,255,.045);border:1px solid var(--line);padding:11px;border-radius:16px;margin-top:8px;color:#dbe4ff;font-size:13px}
.bottom{display:grid;grid-template-columns:1fr;gap:14px;margin-top:14px}.section{border-radius:26px;padding:16px;min-width:0;overflow:hidden}.phoneGrid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:11px}.phone{background:#070b16;border:1px solid var(--line);border-radius:27px;padding:10px;min-height:360px}.phoneScreen{border-radius:20px;background:linear-gradient(180deg,#0c1224,#080d18);min-height:338px;padding:12px}.miniStats{display:grid;grid-template-columns:repeat(2,1fr);gap:8px}.mini{padding:10px;border-radius:13px;background:rgba(255,255,255,.04);text-align:center}.mini b{font-size:24px}.mini span{display:block;color:var(--muted);font-size:11px}.miniItem{padding:10px;border-radius:13px;background:rgba(255,255,255,.04);margin-top:8px;font-size:12px}.miniItem span{display:block;color:var(--muted);margin-top:3px}
.exchangeGrid{display:grid;grid-template-columns:repeat(auto-fit,minmax(210px,1fr));gap:12px}.market{border:1px solid var(--line);background:rgba(255,255,255,.035);border-radius:20px;overflow:hidden;min-width:0}.market .workerTop{height:118px}.marketBody{padding:12px}.marketBody b{font-size:20px}.marketBody span{display:block;color:var(--muted);font-size:12px;margin:3px 0}.price{font-weight:900;font-size:20px;margin-top:8px}
.map{height:255px;border-radius:20px;background:radial-gradient(circle at 20% 35%,rgba(124,58,237,.20),transparent 18%),radial-gradient(circle at 75% 45%,rgba(37,99,235,.18),transparent 20%),linear-gradient(180deg,#0b1020,#080c18);border:1px solid var(--line);position:relative;overflow:hidden}.dot{position:absolute;width:10px;height:10px;border-radius:50%;background:#a855f7;box-shadow:0 0 18px #a855f7}.stats{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:8px;margin-top:12px}.stat{background:rgba(255,255,255,.035);border:1px solid var(--line);border-radius:14px;padding:10px}.stat b{font-size:22px}.stat span{display:block;color:var(--muted);font-size:11px}
.pageOnly{max-width:1300px;margin:auto}.simple{display:grid;grid-template-columns:repeat(3,1fr);gap:14px;margin-top:16px}.simple .card{border-radius:22px;padding:18px}.card h2{margin:0 0 10px}.card p,.card li{color:var(--muted);line-height:1.55}
.mobileNav{display:none;position:fixed;left:12px;right:12px;bottom:12px;background:rgba(8,12,24,.92);border:1px solid var(--line);border-radius:22px;z-index:20;padding:8px;backdrop-filter:blur(18px)}.mobileNav a{flex:1;text-align:center;padding:10px 4px;border-radius:14px;font-size:12px;color:#dbe4ff}.mobileNav a.active{background:rgba(124,58,237,.32)}
@media(max-width:1450px){.app{grid-template-columns:200px minmax(0,1fr)}.rightbar{grid-column:2}.workerGrid{grid-template-columns:repeat(2,minmax(0,1fr))}}@media(max-width:980px){.shell{padding:10px 10px 86px}.app{grid-template-columns:1fr}.sidebar{display:none}.main,.rightbar{border-radius:22px}.hero{grid-template-columns:1fr}.kpis{grid-template-columns:repeat(2,1fr)}.workerGrid{grid-template-columns:1fr}.exchangeGrid{grid-template-columns:1fr}.phoneGrid{grid-template-columns:1fr}.stats{grid-template-columns:repeat(2,1fr)}.simple{grid-template-columns:1fr}.mobileNav{display:flex}.top{align-items:stretch;flex-direction:column}.search{width:100%}}@media(max-width:620px){.kpis{grid-template-columns:1fr}.hero h1{font-size:25px}.globe{width:170px;height:170px}.orb{width:230px}.globeText{position:static;width:auto;margin-top:8px}.topIcons{justify-content:flex-end}}
</style>
"""

def nav(active):
    items=[("Dashboard","/dashboard","dashboard","⌂",""),("Workers","/workers","workers","◌",""),("Tasks","/dashboard","tasks","☑",""),("Clients","/dashboard","clients","●",""),("Projects","/dashboard","projects","▣",""),("Calendar","/dashboard","calendar","◫",""),("Files","/dashboard","files","▤",""),("Analytics","/dashboard","analytics","⌁",""),("Exchange","/exchange","exchange","◎","NEW"),("Marketplace","/exchange","market","✦",""),("Integrations","/dashboard","integrations","◇",""),("Settings","/dashboard","settings","⚙","")]
    links="".join(f'<a class="{"active" if active==key else ""}" href="{href}"><span>{icon}</span>{label}{"<span class=badge>"+badge+"</span>" if badge else ""}</a>' for label,href,key,icon,badge in items)
    return f'<aside class="sidebar"><a class="brand" href="/"><div class="logo"></div><div><b>NinaOS</b><span>AI Workforce OS</span></div></a><nav class="nav">{links}</nav><div class="sideWorker"><b>Nina Office Manager SMB</b><p>First ready AI worker for small businesses. Tasks, follow-ups, invoices, estimates and documents.</p></div></aside>'

def top():
    return '<div class="top"><input class="search" placeholder="Search anything..." /><div class="topIcons"><div class="ico">🔔</div><div class="ico">🌐</div><div class="ico">☼</div><div class="ico">K</div></div></div>'

def worker_card(w):
    cls={"purple":"purple","blue":"blueBg","green":"greenBg","orange":"orangeBg"}[w["color"]]
    st="active" if w["status"]=="ACTIVE" else "idle"
    return f'<div class="worker"><div class="workerTop {cls}"><div class="face"></div></div><div class="workerBody"><h3>{w["name"]}</h3><p>{w["role"]}</p><div class="status {st}">● {w["status"]}</div><div class="work">{w["work"]}</div></div></div>'

def hero():
    return '<section class="hero"><div><h1>Good morning, Katrin 👋</h1><p>Here’s what’s happening in your workspace today.</p><div class="kpis"><div class="kpi"><small>AI Workers</small><div class="v">12</div><div class="delta blue">↑ 2 today</div></div><div class="kpi"><small>Tasks in Progress</small><div class="v">28</div><div class="delta pink">↑ 5 today</div></div><div class="kpi"><small>Completed Today</small><div class="v">15</div><div class="delta">↑ 7 today</div></div><div class="kpi"><small>Upcoming</small><div class="v">6</div><div class="delta blue">Today</div></div></div></div><div class="globeBox"><div class="globe"></div><div class="orb"></div><div class="orb orb2"></div><div class="globeText"><b>Global AI Workforce</b><span>Connected. Intelligent. Tireless.</span><a class="btn" href="/exchange">View Global Network →</a></div></div></section>'

def rightbar():
    return '<aside class="rightbar"><div class="rbCard"><h3>System Status</h3><div class="ok">● All Systems Operational <span style="float:right;color:#dbe4ff">Live ↗</span></div><div class="muted">99.9% Uptime</div><div class="chart"><svg viewBox="0 0 300 90" preserveAspectRatio="none"><polyline fill="none" stroke="#a855f7" stroke-width="4" points="0,70 28,64 55,72 83,55 112,62 140,44 168,52 196,36 224,42 252,25 280,19 300,8"/></svg></div></div><div class="rbCard"><h3>Active Workspaces</h3><div class="ws"><span>AB</span><span>NB</span><span>VG</span><span>HF</span><span>CP</span><span>AX</span><span>+</span></div></div><div class="rbCard"><h3>Nina Office Manager SMB</h3><p class="muted">First ready AI worker for small businesses. Handles tasks, follow-ups, invoices, estimates and documents.</p><a class="btn primary" href="/office-manager" style="width:100%">Open Worker</a><br><br><a class="btn" href="/dashboard" style="width:100%">Open Dashboard</a></div><div class="rbCard snapshot"><h3>Live Workspace Snapshot</h3><div class="row"><span>Tasks Today</span><strong>1</strong></div><div class="row"><span>Follow-ups</span><strong>1</strong></div><div class="row"><span>Invoices Due</span><strong>1</strong></div><div class="row"><span>Estimates</span><strong>1</strong></div><div class="row"><span>Projects Active</span><strong>1</strong></div></div><div class="rbCard"><h3>Nina Chat</h3><div class="bubble">Good morning 👋 Here’s your agenda for today.</div><div class="bubble">Can you prepare the project review report?</div><div class="bubble">Sure. I’m preparing the report for your 15:00 meeting.</div></div></aside>'

def mobile_preview():
    return '<section class="section"><h2 class="sectionTitle">Mobile App Preview</h2><div class="phoneGrid"><div class="phone"><div class="phoneScreen"><b>Good morning, Katrin 👋</b><div class="miniStats" style="margin-top:12px"><div class="mini"><b>12</b><span>Workers</span></div><div class="mini"><b>28</b><span>Tasks</span></div><div class="mini"><b>15</b><span>Done</span></div><div class="mini"><b>6</b><span>Upcoming</span></div></div><div class="miniItem">Nina Sales <span>Following up with 15 leads</span></div><div class="miniItem">Nina Estimator <span>Working on 3 estimates</span></div><div class="miniItem">Nina Office Manager <span>Managing your schedule</span></div></div></div><div class="phone"><div class="phoneScreen"><b>Tasks</b><div class="miniItem">Follow up with Acme Corp <span>Nina Sales · 2 min ago</span></div><div class="miniItem">Create estimate for Project X <span>Nina Estimator · 15 min ago</span></div><div class="miniItem">Schedule meeting with Client Y <span>Nina Office Manager · 45 min ago</span></div></div></div></div></section>'

def exchange_block():
    allw=WORKERS+[{"name":"Nina Marketing","role":"AI Marketing Specialist","color":"purple","price":"€99","rating":"4.8","status":"ACTIVE","work":""},{"name":"Nina HR","role":"AI HR Assistant","color":"orange","price":"€89","rating":"4.8","status":"ACTIVE","work":""}]
    cards=""
    for w in allw:
        cls={"purple":"purple","blue":"blueBg","green":"greenBg","orange":"orangeBg"}[w["color"]]
        cards += f'<div class="market"><div class="workerTop {cls}"><div class="face"></div></div><div class="marketBody"><b>{w["name"]}</b><span>{w["role"]}</span><span>★ {w["rating"]}</span><div class="price">{w["price"]}<span>/month</span></div><a class="btn primary" href="/workers">View Details</a></div></div>'
    return f'<section class="section"><h2 class="sectionTitle">Exchange — AI Workers Marketplace</h2><div class="exchangeGrid">{cards}</div></section>'

def network_block():
    return '<section class="section"><h2 class="sectionTitle">Global Network</h2><div class="map"><div class="dot" style="left:16%;top:38%"></div><div class="dot" style="left:26%;top:55%"></div><div class="dot" style="left:44%;top:42%"></div><div class="dot" style="left:58%;top:35%"></div><div class="dot" style="left:72%;top:48%"></div><div class="dot" style="left:82%;top:60%"></div></div><div class="stats"><div class="stat"><b>12,458</b><span>AI Workers Online</span></div><div class="stat"><b>1,247</b><span>Workspaces</span></div><div class="stat"><b>98</b><span>Countries</span></div><div class="stat"><b>2.4M</b><span>Tasks Completed</span></div></div><div class="bubble">Nina Estimator completed estimate for Project X</div><div class="bubble">Nina Sales closed a deal with Beta Ltd</div><div class="bubble">Nina Office Manager scheduled meeting with Client Y</div></section>'

def dashboard_content():
    workers = "".join(worker_card(w) for w in WORKERS)
    return f'{hero()}<section class="workforce"><h2 class="sectionTitle">Your AI Workforce</h2><div class="workerGrid">{workers}</div></section>'

def layout(active, content):
    body=f'<div class="shell"><div class="app">{nav(active)}<main class="main">{top()}{content}</main>{rightbar()}</div><nav class="mobileNav"><a class="{"active" if active=="dashboard" else ""}" href="/dashboard">Dashboard</a><a class="{"active" if active=="workers" else ""}" href="/workers">Workers</a><a href="/office-manager">Nina</a><a class="{"active" if active=="exchange" else ""}" href="/exchange">Exchange</a></nav></div>'
    return f'<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>NinaOS</title>{CSS}</head><body>{body}</body></html>'

@app.route("/")
def home():
    return layout("dashboard", dashboard_content() + f'<div class="bottom">{mobile_preview()}{exchange_block()}{network_block()}</div>')

@app.route("/dashboard")
def dashboard():
    return layout("dashboard", dashboard_content() + f'<div class="bottom">{mobile_preview()}{exchange_block()}{network_block()}</div>')

@app.route("/workers")
def workers():
    workers_html="".join(worker_card(w) for w in WORKERS)
    content=f'<section class="pageOnly"><h1>Your AI Workers</h1><p class="muted">Ready AI workers assigned to your workspace.</p><div class="workerGrid">{workers_html}</div><div class="simple"><div class="card"><h2>Office Manager</h2><p>Tasks, follow-ups, invoices, estimates, documents.</p></div><div class="card"><h2>Sales</h2><p>Lead follow-up, pipeline, offers and client messaging.</p></div><div class="card"><h2>Estimator</h2><p>Estimate draft support, scopes and offer structure.</p></div></div></section>'
    return layout("workers", content)

@app.route("/office-manager")
def office_manager():
    content = """<section class='pageOnly'><h1>Nina Office Manager SMB</h1><p class='muted'>The first strategic NinaOS ready worker for small businesses.</p><div class='simple'><div class='card'><h2>Role Stack</h2><ul><li>Office Manager Core</li><li>Finance Admin Assistant</li><li>Estimating Assistant Basic</li><li>Client Follow-up Manager</li><li>Document Admin</li></ul></div><div class='card'><h2>What Nina Handles</h2><ul><li>Tasks and daily priorities</li><li>Client follow-ups</li><li>Invoice admin</li><li>Estimate / offer drafts</li><li>Documents</li></ul></div><div class='card'><h2>Approval Required</h2><ul><li>send_invoice</li><li>approve_payment</li><li>send_final_estimate</li><li>share_document_external</li><li>export_financial_data</li></ul></div></div></section>"""
    return layout("workers", content)

@app.route("/exchange")
def exchange():
    return layout("exchange", exchange_block() + network_block())

@app.route("/health")
def health():
    return jsonify({"ok": True, "version": APP_VERSION, "core": CORE_VERSION})

if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", "8080"))
    app.run(host="0.0.0.0", port=port, debug=False)
