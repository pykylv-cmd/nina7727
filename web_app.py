from flask import Flask, request

app = Flask(__name__)

APP_VERSION = "Web App V2 — Target Surface"
CORE_VERSION = "V115.4 + Core 2.5.2"
from flask import Flask, jsonify

app = Flask(__name__)

APP_VERSION = "Web App V3 — Premium Target Surface"
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
.shell{max-width:1680px;margin:auto;padding:14px}.app{display:grid;grid-template-columns:220px 1fr 330px;gap:14px;min-height:calc(100vh - 28px)}
.sidebar,.main,.rightbar,.section,.card{border:1px solid var(--line);background:rgba(10,15,30,.82);backdrop-filter:blur(18px);box-shadow:var(--shadow)}.sidebar{border-radius:28px;padding:16px;display:flex;flex-direction:column;gap:14px}.brand{display:flex;align-items:center;gap:12px;padding:6px 4px 14px}.logo{width:38px;height:38px;border-radius:50%;background:radial-gradient(circle,#22d3ee 0 10%,#7c3aed 45%,#2563eb 68%,transparent 70%),linear-gradient(135deg,#7c3aed,#2563eb);box-shadow:0 0 34px rgba(124,58,237,.55)}.brand b{font-size:19px}.brand span{display:block;color:var(--muted);font-size:11px}
.nav{display:grid;gap:7px}.nav a{padding:11px 12px;border-radius:14px;color:#dbe4ff;font-size:14px;display:flex;gap:10px;align-items:center;border:1px solid transparent}.nav a:hover,.nav a.active{background:linear-gradient(90deg,rgba(124,58,237,.42),rgba(37,99,235,.22));border-color:rgba(124,58,237,.35)}.badge{margin-left:auto;background:rgba(124,58,237,.28);font-size:10px;border-radius:999px;padding:3px 7px}.sideWorker{margin-top:auto;background:linear-gradient(180deg,rgba(124,58,237,.18),rgba(37,99,235,.10));border:1px solid rgba(124,58,237,.28);border-radius:20px;padding:15px}.sideWorker b{display:block;margin-bottom:7px}.sideWorker p{color:var(--muted);font-size:13px;line-height:1.45;margin:0}
.main{border-radius:28px;padding:18px;overflow:hidden}.top{display:flex;align-items:center;justify-content:space-between;gap:12px;margin-bottom:16px}.search{width:min(560px,100%);background:rgba(255,255,255,.045);border:1px solid var(--line);border-radius:999px;padding:13px 18px;color:#dbe4ff}.topIcons{display:flex;gap:9px;align-items:center}.ico{width:34px;height:34px;border-radius:50%;display:grid;place-items:center;border:1px solid var(--line);background:rgba(255,255,255,.04)}
.hero{position:relative;display:grid;grid-template-columns:1fr 300px;gap:16px;min-height:245px;padding:22px;border:1px solid var(--line);border-radius:26px;background:radial-gradient(circle at 77% 48%,rgba(34,211,238,.15),transparent 24%),linear-gradient(135deg,rgba(17,24,48,.96),rgba(8,13,27,.96));overflow:hidden}.hero h1{margin:0;font-size:29px;letter-spacing:-.04em}.hero p{margin:8px 0 0;color:var(--muted)}.kpis{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin-top:22px}.kpi{background:rgba(255,255,255,.045);border:1px solid rgba(255,255,255,.075);border-radius:18px;padding:14px;min-height:105px}.kpi small{color:#dbe4ff}.kpi .v{font-size:37px;font-weight:900;margin:7px 0 3px}.delta{font-size:13px;color:#86efac}.pink{color:#f0abfc}.blue{color:#93c5fd}
.globeBox{position:relative;display:grid;place-items:center}.globe{width:220px;height:220px;border-radius:50%;position:relative;background:radial-gradient(circle,rgba(37,99,235,.12),rgba(124,58,237,.06) 54%,transparent 68%)}.globe:before{content:"";position:absolute;inset:15px;border-radius:50%;background-image:radial-gradient(circle,rgba(124,58,237,.95) 0 2px,transparent 3px),radial-gradient(circle,rgba(96,165,250,.95) 0 2px,transparent 3px);background-size:18px 18px;background-position:0 0,9px 9px}.orb{position:absolute;border:1px solid rgba(124,58,237,.35);border-radius:50%;width:280px;height:110px;transform:rotate(22deg)}.orb2{transform:rotate(-25deg);height:145px;border-color:rgba(37,99,235,.30)}.globeText{position:absolute;right:4px;top:56px;width:135px}.globeText b{font-size:26px;line-height:1.02;display:block}.globeText span{display:block;color:var(--muted);margin:8px 0 12px;font-size:13px}
.btn{display:inline-flex;align-items:center;justify-content:center;border-radius:13px;padding:11px 15px;font-weight:800;border:1px solid var(--line);background:rgba(255,255,255,.045)}.btn.primary{background:linear-gradient(90deg,var(--violet),var(--blue));border-color:transparent}
.workforce{margin-top:16px}.sectionTitle{font-size:23px;font-weight:900;margin:0 0 12px}.workerGrid{display:grid;grid-template-columns:repeat(4,1fr);gap:14px}.worker{min-height:270px;border-radius:22px;overflow:hidden;background:rgba(255,255,255,.035);border:1px solid var(--line)}.workerTop{height:135px;position:relative}.purple{background:linear-gradient(135deg,#3b1265,#0d1224)}.blueBg{background:linear-gradient(135deg,#0a4d87,#0d1224)}.greenBg{background:linear-gradient(135deg,#0b5b37,#0d1224)}.orangeBg{background:linear-gradient(135deg,#7c3f12,#0d1224)}.face{position:absolute;left:50%;top:55%;transform:translate(-50%,-50%);width:98px;height:98px;border-radius:50%;background:radial-gradient(circle at 35% 31%,#ffe0c9 0 13%,#c88463 14% 24%,transparent 25%),radial-gradient(circle at 50% 56%,#f3c5aa 0 30%,#bd7758 31% 36%,transparent 37%),radial-gradient(circle at 38% 43%,#23140f 0 3%,transparent 4%),radial-gradient(circle at 62% 43%,#23140f 0 3%,transparent 4%),radial-gradient(circle at 50% 20%,#3f2419 0 30%,transparent 31%),linear-gradient(180deg,#6b3d2d,#d39a7b);box-shadow:0 15px 38px rgba(0,0,0,.42),0 0 0 4px rgba(255,255,255,.08)}.workerBody{padding:15px}.workerBody h3{font-size:25px;line-height:1.02;margin:0 0 4px}.workerBody p{margin:0 0 10px;color:var(--muted);font-size:13px}.status{font-size:12px;margin:8px 0}.active{color:#86efac}.idle{color:#fcd34d}.work{font-size:14px;line-height:1.35}
.rightbar{border-radius:28px;padding:18px;display:flex;flex-direction:column;gap:14px}.rbCard{border-radius:22px;border:1px solid var(--line);background:rgba(255,255,255,.035);padding:16px}.rbCard h3{margin:0 0 10px}.ok{color:#86efac;font-weight:800}.chart{height:84px;border-radius:14px;background:linear-gradient(180deg,rgba(124,58,237,.12),transparent);border:1px solid rgba(255,255,255,.05);position:relative;overflow:hidden}.chart svg{position:absolute;inset:0}.ws{display:flex;gap:8px;flex-wrap:wrap}.ws span{width:34px;height:34px;border-radius:50%;display:grid;place-items:center;font-weight:900;font-size:11px;background:linear-gradient(135deg,#7c3aed,#2563eb)}.snapshot{display:grid;gap:9px}.row{display:flex;justify-content:space-between;color:#dbe4ff}.row strong{color:white}.bubble{background:rgba(255,255,255,.045);border:1px solid var(--line);padding:11px;border-radius:16px;margin-top:8px;color:#dbe4ff;font-size:13px}
.bottom{display:grid;grid-template-columns:380px 1fr 430px;gap:14px;margin-top:14px}.section{border-radius:26px;padding:16px}.phoneGrid{display:grid;grid-template-columns:repeat(2,1fr);gap:11px}.phone{background:#070b16;border:1px solid var(--line);border-radius:27px;padding:10px;min-height:360px}.phoneScreen{border-radius:20px;background:linear-gradient(180deg,#0c1224,#080d18);min-height:338px;padding:12px}.miniStats{display:grid;grid-template-columns:repeat(2,1fr);gap:8px}.mini{padding:10px;border-radius:13px;background:rgba(255,255,255,.04);text-align:center}.mini b{font-size:24px}.mini span{display:block;color:var(--muted);font-size:11px}.miniItem{padding:10px;border-radius:13px;background:rgba(255,255,255,.04);margin-top:8px;font-size:12px}.miniItem span{display:block;color:var(--muted);margin-top:3px}
.exchangeGrid{display:grid;grid-template-columns:repeat(3,1fr);gap:12px}.market{border:1px solid var(--line);background:rgba(255,255,255,.035);border-radius:20px;overflow:hidden}.market .workerTop{height:118px}.marketBody{padding:12px}.marketBody b{font-size:20px}.marketBody span{display:block;color:var(--muted);font-size:12px;margin:3px 0}.price{font-weight:900;font-size:20px;margin-top:8px}
.map{height:255px;border-radius:20px;background:radial-gradient(circle at 20% 35%,rgba(124,58,237,.20),transparent 18%),radial-gradient(circle at 75% 45%,rgba(37,99,235,.18),transparent 20%),linear-gradient(180deg,#0b1020,#080c18);border:1px solid var(--line);position:relative;overflow:hidden}.dot{position:absolute;width:10px;height:10px;border-radius:50%;background:#a855f7;box-shadow:0 0 18px #a855f7}.stats{display:grid;grid-template-columns:repeat(4,1fr);gap:8px;margin-top:12px}.stat{background:rgba(255,255,255,.035);border:1px solid var(--line);border-radius:14px;padding:10px}.stat b{font-size:22px}.stat span{display:block;color:var(--muted);font-size:11px}
.pageOnly{max-width:1300px;margin:auto}.simple{display:grid;grid-template-columns:repeat(3,1fr);gap:14px;margin-top:16px}.simple .card{border-radius:22px;padding:18px}.card h2{margin:0 0 10px}.card p,.card li{color:var(--muted);line-height:1.55}
.mobileNav{display:none;position:fixed;left:12px;right:12px;bottom:12px;background:rgba(8,12,24,.92);border:1px solid var(--line);border-radius:22px;z-index:20;padding:8px;backdrop-filter:blur(18px)}.mobileNav a{flex:1;text-align:center;padding:10px 4px;border-radius:14px;font-size:12px;color:#dbe4ff}.mobileNav a.active{background:rgba(124,58,237,.32)}
@media(max-width:1450px){.app{grid-template-columns:210px 1fr}.rightbar{grid-column:2}.bottom{grid-template-columns:1fr}.workerGrid{grid-template-columns:repeat(2,1fr)}}@media(max-width:980px){.shell{padding:10px 10px 86px}.app{grid-template-columns:1fr}.sidebar{display:none}.main,.rightbar{border-radius:22px}.hero{grid-template-columns:1fr}.kpis{grid-template-columns:repeat(2,1fr)}.workerGrid{grid-template-columns:1fr}.exchangeGrid{grid-template-columns:1fr}.phoneGrid{grid-template-columns:1fr}.stats{grid-template-columns:repeat(2,1fr)}.simple{grid-template-columns:1fr}.mobileNav{display:flex}.top{align-items:stretch;flex-direction:column}.search{width:100%}}@media(max-width:620px){.kpis{grid-template-columns:1fr}.hero h1{font-size:25px}.globe{width:170px;height:170px}.orb{width:230px}.globeText{position:static;width:auto;margin-top:8px}.topIcons{justify-content:flex-end}}
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

# ============================================================
# THEME / UI HELPERS
# ============================================================

BASE_CSS = """
<style>
:root{
    --bg:#060913;
    --panel:#0b1020;
    --panel-2:#0e1529;
    --panel-3:#111a31;
    --panel-soft:#0d1427;
    --line:rgba(255,255,255,0.08);
    --line-2:rgba(147,197,253,0.18);
    --text:#f8fafc;
    --muted:#9aa6c5;
    --muted-2:#7b88aa;
    --purple:#7c3aed;
    --purple-2:#8b5cf6;
    --blue:#2563eb;
    --cyan:#22d3ee;
    --green:#22c55e;
    --amber:#f59e0b;
    --pink:#ec4899;
    --danger:#ef4444;
    --shadow:0 18px 50px rgba(0,0,0,0.42);
    --radius-xl:26px;
    --radius-lg:20px;
    --radius-md:16px;
    --radius-sm:12px;
}

*{box-sizing:border-box}
html,body{
    margin:0;
    padding:0;
    background:
      radial-gradient(circle at 10% 10%, rgba(124,58,237,0.18), transparent 26%),
      radial-gradient(circle at 90% 20%, rgba(37,99,235,0.16), transparent 28%),
      linear-gradient(180deg,#050812 0%, #060913 35%, #070b15 100%);
    color:var(--text);
    font-family: Inter, ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, Arial, sans-serif;
    min-height:100vh;
}

a{color:inherit;text-decoration:none}

.page{
    max-width: 1700px;
    margin: 0 auto;
    padding: 18px;
}

.top_shell{
    display:grid;
    grid-template-columns: 520px 1fr;
    gap:18px;
    align-items:stretch;
}

.left_brand{
    background:
      radial-gradient(circle at 18% 14%, rgba(124,58,237,0.24), transparent 22%),
      radial-gradient(circle at 65% 25%, rgba(37,99,235,0.18), transparent 26%),
      linear-gradient(180deg, rgba(10,14,28,0.96), rgba(7,10,20,0.98));
    border:1px solid var(--line);
    border-radius:30px;
    padding:30px 28px 24px;
    box-shadow:var(--shadow);
    position:relative;
    overflow:hidden;
    min-height:760px;
}

.brand_logo_row{
    display:flex;
    align-items:center;
    gap:18px;
    margin-bottom:16px;
}

.brand_globe{
    width:140px;
    height:140px;
    border-radius:50%;
    position:relative;
    flex:0 0 auto;
    background:
      radial-gradient(circle at 50% 50%, rgba(124,58,237,0.18), rgba(37,99,235,0.06) 48%, transparent 66%),
      radial-gradient(circle at 40% 40%, rgba(255,255,255,0.06), transparent 65%);
    border:1px solid rgba(255,255,255,0.08);
    overflow:hidden;
}
.brand_globe:before{
    content:"";
    position:absolute;
    inset:10px;
    border-radius:50%;
    background-image:
      radial-gradient(circle, rgba(139,92,246,0.95) 0 3px, transparent 4px),
      radial-gradient(circle, rgba(96,165,250,0.95) 0 3px, transparent 4px),
      radial-gradient(circle, rgba(168,85,247,0.92) 0 3px, transparent 4px),
      radial-gradient(circle, rgba(59,130,246,0.92) 0 3px, transparent 4px);
    background-size: 28px 28px, 28px 28px, 28px 28px, 28px 28px;
    background-position: 0 0, 14px 14px, 7px 18px, 18px 7px;
    filter: drop-shadow(0 0 12px rgba(124,58,237,0.3));
    opacity:0.95;
}
.brand_title_wrap{
    display:flex;
    flex-direction:column;
    gap:8px;
}
.brand_title{
    font-size:86px;
    line-height:0.92;
    font-weight:900;
    letter-spacing:-0.04em;
    margin:0;
}
.brand_title .accent{
    background:linear-gradient(90deg,#3b82f6,#8b5cf6 55%, #60a5fa 100%);
    -webkit-background-clip:text;
    -webkit-text-fill-color:transparent;
    background-clip:text;
    color:transparent;
}
.brand_sub{
    font-size:15px;
    letter-spacing:0.22em;
    text-transform:uppercase;
    color:#d7def3;
}

.hero_copy{
    margin-top:22px;
    font-size:20px;
    line-height:1.45;
    color:#f4f7ff;
    max-width:430px;
}
.hero_copy .soft{
    color:#d6def5;
}

.pillars{
    display:grid;
    grid-template-columns:repeat(4,1fr);
    gap:14px;
    margin-top:30px;
}
.pillar{
    background:rgba(255,255,255,0.02);
    border:1px solid rgba(255,255,255,0.06);
    border-radius:18px;
    padding:16px 12px;
    min-height:150px;
}
.pillar_icon{
    font-size:30px;
    margin-bottom:12px;
}
.pillar_title{
    font-size:13px;
    letter-spacing:0.08em;
    text-transform:uppercase;
    font-weight:800;
    margin-bottom:8px;
}
.pillar_desc{
    color:var(--muted);
    font-size:14px;
    line-height:1.5;
}

.cta_row{
    display:flex;
    gap:14px;
    margin-top:26px;
    flex-wrap:wrap;
}
.btn{
    display:inline-flex;
    align-items:center;
    justify-content:center;
    padding:14px 24px;
    border-radius:14px;
    font-weight:800;
    font-size:15px;
    border:1px solid var(--line);
    transition:all .18s ease;
}
.btn:hover{transform:translateY(-1px)}
.btn_primary{
    background:linear-gradient(90deg,#7c3aed,#2563eb);
    border-color:transparent;
    color:white;
    box-shadow:0 12px 30px rgba(124,58,237,0.3);
}
.btn_secondary{
    background:rgba(255,255,255,0.02);
    color:#eef2ff;
}

.trusted{
    margin-top:34px;
    color:var(--muted);
    font-size:15px;
}
.trusted_logos{
    margin-top:18px;
    display:grid;
    grid-template-columns:repeat(5,1fr);
    gap:10px;
}
.logo_chip{
    border:1px solid rgba(255,255,255,0.06);
    background:rgba(255,255,255,0.02);
    border-radius:14px;
    padding:12px 10px;
    text-align:center;
    font-weight:700;
    color:#dbe4ff;
    font-size:14px;
}

.right_app{
    background:
      linear-gradient(180deg, rgba(10,14,28,0.98), rgba(7,11,22,0.98));
    border:1px solid var(--line);
    border-radius:30px;
    box-shadow:var(--shadow);
    overflow:hidden;
    min-height:760px;
}

.app_shell{
    display:grid;
    grid-template-columns: 160px 1fr;
    min-height:760px;
}

.sidebar{
    border-right:1px solid var(--line);
    background:linear-gradient(180deg, rgba(9,13,24,0.98), rgba(8,11,21,0.98));
    padding:14px 12px 14px;
    display:flex;
    flex-direction:column;
    gap:12px;
}
.sidebar_brand{
    display:flex;
    align-items:center;
    gap:10px;
    padding:8px 10px 16px;
}
.sidebar_logo{
    width:28px;height:28px;border-radius:50%;
    background:linear-gradient(135deg,#7c3aed,#2563eb);
    box-shadow:0 0 24px rgba(124,58,237,0.35);
    position:relative;
}
.sidebar_logo:before{
    content:"";
    position:absolute; inset:6px;
    border-radius:50%;
    border:1px solid rgba(255,255,255,0.35);
}
.sidebar_brand_name{
    font-size:15px;
    font-weight:900;
}
.nav_group{
    display:flex;
    flex-direction:column;
    gap:6px;
}
.nav_item{
    display:flex;
    align-items:center;
    gap:10px;
    padding:10px 12px;
    border-radius:12px;
    color:#d9e2fb;
    font-size:13px;
    border:1px solid transparent;
}
.nav_item:hover{
    background:rgba(255,255,255,0.03);
    border-color:rgba(255,255,255,0.06);
}
.nav_item.active{
    background:linear-gradient(90deg, rgba(124,58,237,0.34), rgba(37,99,235,0.22));
    border-color:rgba(124,58,237,0.35);
    box-shadow: inset 0 0 0 1px rgba(255,255,255,0.04);
}
.nav_badge{
    margin-left:auto;
    font-size:10px;
    padding:3px 7px;
    border-radius:999px;
    background:rgba(124,58,237,0.18);
    color:#e9ddff;
    border:1px solid rgba(124,58,237,0.25);
}
.sidebar_worker_card{
    margin-top:auto;
    background:linear-gradient(180deg, rgba(17,26,49,0.96), rgba(12,18,34,0.96));
    border:1px solid rgba(124,58,237,0.25);
    border-radius:16px;
    padding:14px;
}
.sidebar_worker_title{
    font-weight:900;
    font-size:14px;
    margin-bottom:6px;
}
.sidebar_worker_sub{
    color:var(--muted);
    font-size:12px;
    line-height:1.5;
}
.sidebar_user{
    margin-top:12px;
    display:flex;
    align-items:center;
    gap:10px;
    padding:10px 12px;
    border-radius:14px;
    background:rgba(255,255,255,0.03);
    border:1px solid rgba(255,255,255,0.06);
}
.avatar{
    width:36px;height:36px;border-radius:50%;
    background:linear-gradient(135deg,#8b5cf6,#ec4899);
    display:flex;align-items:center;justify-content:center;
    font-weight:900;color:white;font-size:14px;
}
.user_meta .name{font-weight:800;font-size:13px}
.user_meta .role{font-size:11px;color:var(--muted)}

.main{
    padding:16px 18px 18px;
}

.topbar{
    display:flex;
    align-items:center;
    justify-content:space-between;
    gap:14px;
    margin-bottom:16px;
}
.search{
    flex:1;
    max-width:460px;
    background:rgba(255,255,255,0.02);
    border:1px solid rgba(255,255,255,0.06);
    border-radius:999px;
    padding:12px 18px;
    color:#dbe5ff;
    font-size:14px;
}
.topbar_right{
    display:flex;
    align-items:center;
    gap:14px;
}
.icon_btn{
    width:34px;height:34px;border-radius:50%;
    border:1px solid rgba(255,255,255,0.08);
    display:flex;align-items:center;justify-content:center;
    background:rgba(255,255,255,0.02);
    color:#e7eeff;
    font-size:14px;
}
.user_chip{
    display:flex;
    align-items:center;
    gap:10px;
}
.user_chip .avatar{width:38px;height:38px}
.user_chip_name{
    font-size:13px;
    font-weight:800;
}
.user_chip_role{
    font-size:11px;color:var(--muted)
}

.hero_grid{
    display:grid;
    grid-template-columns: 1fr 360px;
    gap:14px;
    margin-bottom:14px;
}
.hero_panel{
    background:
      radial-gradient(circle at 75% 25%, rgba(124,58,237,0.20), transparent 22%),
      radial-gradient(circle at 86% 12%, rgba(37,99,235,0.16), transparent 22%),
      linear-gradient(180deg, rgba(10,14,28,0.98), rgba(9,13,25,0.98));
    border:1px solid var(--line);
    border-radius:22px;
    padding:20px;
    min-height:255px;
    overflow:hidden;
    position:relative;
}
.hero_title{
    font-size:18px;
    font-weight:900;
    margin-bottom:6px;
}
.hero_sub{
    color:var(--muted);
    font-size:14px;
    margin-bottom:18px;
}
.kpi_row{
    display:grid;
    grid-template-columns:repeat(4,1fr);
    gap:12px;
    max-width:760px;
}
.kpi{
    background:linear-gradient(180deg, rgba(13,20,39,0.96), rgba(11,16,31,0.96));
    border:1px solid rgba(255,255,255,0.06);
    border-radius:18px;
    padding:14px;
    min-height:112px;
}
.kpi_head{
    display:flex;
    justify-content:space-between;
    align-items:center;
    color:#dce5ff;
    font-size:12px;
    margin-bottom:10px;
}
.kpi_value{
    font-size:40px;
    line-height:1;
    font-weight:900;
    margin-bottom:8px;
}
.kpi_delta{
    font-size:13px;
    color:#86efac;
}
.kpi_delta.pink{color:#f9a8d4}
.kpi_delta.blue{color:#93c5fd}

.globe_wrap{
    position:absolute;
    right:18px;
    top:18px;
    width:340px;
    height:220px;
    display:flex;
    align-items:center;
    justify-content:center;
}
.globe{
    width:230px;
    height:230px;
    border-radius:50%;
    position:relative;
    background:
      radial-gradient(circle at 50% 50%, rgba(59,130,246,0.10), rgba(124,58,237,0.08) 48%, transparent 68%);
    box-shadow:0 0 60px rgba(59,130,246,0.12);
}
.globe:before{
    content:"";
    position:absolute;
    inset:12px;
    border-radius:50%;
    background-image:
      radial-gradient(circle, rgba(124,58,237,0.95) 0 1.8px, transparent 2.6px),
      radial-gradient(circle, rgba(59,130,246,0.95) 0 1.8px, transparent 2.6px),
      radial-gradient(circle, rgba(167,139,250,0.95) 0 1.8px, transparent 2.6px);
    background-size: 18px 18px, 18px 18px, 18px 18px;
    background-position: 0 0, 9px 9px, 4px 13px;
    opacity:0.95;
    filter: drop-shadow(0 0 14px rgba(124,58,237,0.26));
}
.orbit, .orbit2, .orbit3{
    position:absolute;
    border:1px solid rgba(124,58,237,0.35);
    border-radius:50%;
    pointer-events:none;
}
.orbit{width:320px;height:120px;transform:rotate(18deg)}
.orbit2{width:300px;height:160px;transform:rotate(-24deg); border-color:rgba(59,130,246,0.28)}
.orbit3{width:260px;height:220px;transform:rotate(38deg); border-color:rgba(168,85,247,0.22)}
.hero_globe_text{
    position:absolute;
    right:6px;
    top:60px;
    width:150px;
    z-index:2;
}
.hero_globe_text h3{
    margin:0 0 8px 0;
    font-size:28px;
    line-height:1.05;
}
.hero_globe_text p{
    margin:0 0 16px 0;
    color:var(--muted);
    font-size:14px;
    line-height:1.5;
}

.system_card{
    background:linear-gradient(180deg, rgba(11,16,31,0.98), rgba(9,14,27,0.98));
    border:1px solid var(--line);
    border-radius:22px;
    padding:18px;
    display:flex;
    flex-direction:column;
    gap:18px;
}
.system_block_title{
    font-size:16px;
    font-weight:900;
    margin-bottom:10px;
}
.status_line{
    display:flex;
    align-items:center;
    justify-content:space-between;
    gap:12px;
    margin-bottom:8px;
    font-size:14px;
}
.live_dot{
    width:8px;height:8px;border-radius:50%;background:#22c55e;display:inline-block;margin-right:8px;
    box-shadow:0 0 14px rgba(34,197,94,0.4);
}
.chart{
    height:88px;
    border-radius:14px;
    background:
      linear-gradient(180deg, rgba(124,58,237,0.10), transparent),
      linear-gradient(90deg, rgba(255,255,255,0.03) 1px, transparent 1px);
    background-size:auto, 28px 100%;
    border:1px solid rgba(255,255,255,0.04);
    position:relative;
    overflow:hidden;
}
.chart svg{
    position:absolute; inset:0;
}
.workspaces{
    display:flex;
    align-items:center;
    gap:8px;
    flex-wrap:wrap;
}
.ws_avatar{
    width:34px;height:34px;border-radius:50%;
    border:2px solid rgba(255,255,255,0.08);
    display:flex;align-items:center;justify-content:center;
    font-size:12px;font-weight:800;color:white;
}
.ws1{background:linear-gradient(135deg,#f59e0b,#ef4444)}
.ws2{background:linear-gradient(135deg,#22c55e,#16a34a)}
.ws3{background:linear-gradient(135deg,#3b82f6,#06b6d4)}
.ws4{background:linear-gradient(135deg,#8b5cf6,#ec4899)}
.ws5{background:linear-gradient(135deg,#0ea5e9,#2563eb)}
.ws6{background:linear-gradient(135deg,#a855f7,#7c3aed)}
.ws_plus{background:rgba(255,255,255,0.04)}

.section{
    margin-top:16px;
}
.section_title{
    font-size:22px;
    font-weight:900;
    margin-bottom:14px;
}

.workforce_and_system{
    display:grid;
    grid-template-columns: 1fr 320px;
    gap:14px;
    margin-top:14px;
}
.worker_cards{
    display:grid;
    grid-template-columns:repeat(4,1fr);
    gap:14px;
}
.worker_card{
    border-radius:20px;
    overflow:hidden;
    border:1px solid rgba(255,255,255,0.08);
    background:linear-gradient(180deg, rgba(14,21,41,0.98), rgba(10,15,28,0.98));
    min-height:290px;
    box-shadow:var(--shadow);
}
.worker_img{
    height:160px;
    position:relative;
    background:
      radial-gradient(circle at 40% 30%, rgba(255,255,255,0.12), transparent 26%),
      linear-gradient(135deg,#25133d,#0e172d);
}
.worker_img.sales{
    background:
      radial-gradient(circle at 40% 30%, rgba(255,255,255,0.12), transparent 26%),
      linear-gradient(135deg,#32114d,#111827);
}
.worker_img.estimator{
    background:
      radial-gradient(circle at 40% 30%, rgba(255,255,255,0.12), transparent 26%),
      linear-gradient(135deg,#0d2858,#101827);
}
.worker_img.office{
    background:
      radial-gradient(circle at 40% 30%, rgba(255,255,255,0.12), transparent 26%),
      linear-gradient(135deg,#143522,#101827);
}
.worker_img.support{
    background:
      radial-gradient(circle at 40% 30%, rgba(255,255,255,0.12), transparent 26%),
      linear-gradient(135deg,#4a260f,#16161d);
}
.portrait{
    position:absolute;
    left:50%;
    top:50%;
    transform:translate(-50%,-46%);
    width:112px;
    height:112px;
    border-radius:50%;
    background:
      radial-gradient(circle at 35% 30%, #f8d2bf 0 14%, #c98568 15% 24%, #6d3b2a 25% 26%, transparent 27%),
      radial-gradient(circle at 50% 55%, #f3c6ae 0 26%, #cf8f73 27% 34%, transparent 35%),
      radial-gradient(circle at 38% 42%, #2b170f 0 4%, transparent 5%),
      radial-gradient(circle at 62% 42%, #2b170f 0 4%, transparent 5%),
      radial-gradient(circle at 50% 60%, #9a5f4c 0 4%, transparent 5%),
      radial-gradient(circle at 50% 18%, #3a231c 0 26%, transparent 27%),
      linear-gradient(180deg, #6d4635, #c99379);
    box-shadow:
      0 12px 40px rgba(0,0,0,0.35),
      0 0 0 4px rgba(255,255,255,0.08);
}
.worker_body{
    padding:14px 16px 18px;
}
.worker_name{
    font-size:28px;
    line-height:1.02;
    font-weight:900;
    margin-bottom:4px;
}
.worker_role{
    color:#cdd7f6;
    font-size:14px;
    margin-bottom:10px;
}
.worker_status{
    display:flex;
    align-items:center;
    gap:8px;
    font-size:12px;
    color:#d8e3ff;
    margin-bottom:12px;
}
.status_active{color:#86efac}
.status_idle{color:#fcd34d}
.worker_task{
    color:#eef3ff;
    font-size:15px;
    line-height:1.45;
}

.lower_grid{
    display:grid;
    grid-template-columns: 500px 1fr 460px;
    gap:16px;
    margin-top:16px;
}

.panel{
    background:linear-gradient(180deg, rgba(10,14,28,0.98), rgba(9,13,24,0.98));
    border:1px solid var(--line);
    border-radius:24px;
    box-shadow:var(--shadow);
    overflow:hidden;
}

.panel_header{
    display:flex;
    justify-content:space-between;
    align-items:center;
    gap:12px;
    padding:16px 18px 10px;
}
.panel_title{
    font-size:24px;
    font-weight:900;
    letter-spacing:-0.02em;
}
.panel_sub{
    color:var(--muted);
    font-size:13px;
}
.panel_link{
    color:#dce5ff;
    font-size:13px;
}

.mobile_preview{
    padding-bottom:16px;
}
.phone_row{
    display:grid;
    grid-template-columns:repeat(3,1fr);
    gap:12px;
    padding:0 16px 10px;
}
.phone{
    background:#090d18;
    border:1px solid rgba(255,255,255,0.06);
    border-radius:28px;
    padding:10px;
    box-shadow: inset 0 0 0 1px rgba(255,255,255,0.03);
}
.phone_screen{
    min-height:520px;
    border-radius:22px;
    overflow:hidden;
    background:
      linear-gradient(180deg, #0b1020, #080c16);
    border:1px solid rgba(255,255,255,0.05);
    padding:12px;
}
.phone_top{
    display:flex;
    justify-content:space-between;
    align-items:center;
    color:#eef2ff;
    font-size:12px;
    margin-bottom:14px;
}
.phone_h{
    font-weight:900;
    margin-bottom:10px;
}
.mobile_stats{
    display:grid;
    grid-template-columns:repeat(4,1fr);
    gap:8px;
    margin-bottom:12px;
}
.mobile_stat{
    background:rgba(255,255,255,0.03);
    border:1px solid rgba(255,255,255,0.05);
    border-radius:14px;
    padding:10px 8px;
    text-align:center;
}
.mobile_stat .v{font-size:22px;font-weight:900}
.mobile_stat .l{font-size:10px;color:var(--muted)}
.mobile_list{
    display:flex;
    flex-direction:column;
    gap:8px;
}
.mobile_item{
    background:rgba(255,255,255,0.03);
    border:1px solid rgba(255,255,255,0.05);
    border-radius:14px;
    padding:10px;
}
.mobile_item_title{font-size:12px;font-weight:800;margin-bottom:4px}
.mobile_item_sub{font-size:11px;color:var(--muted)}
.mobile_worker_box{
    background:linear-gradient(180deg, rgba(17,26,49,0.98), rgba(11,16,31,0.98));
    border:1px solid rgba(124,58,237,0.24);
    border-radius:16px;
    padding:12px;
}
.progress{
    height:8px;border-radius:999px;background:rgba(255,255,255,0.06);overflow:hidden;margin:10px 0 14px;
}
.progress > div{
    height:100%;
    border-radius:999px;
    background:linear-gradient(90deg,#7c3aed,#2563eb);
}

.exchange_wrap{
    display:grid;
    grid-template-columns: 180px 1fr;
    gap:14px;
    padding:0 16px 16px;
}
.exchange_side{
    display:flex;
    flex-direction:column;
    gap:10px;
}
.exchange_cat{
    padding:10px 12px;
    border-radius:12px;
    border:1px solid rgba(255,255,255,0.06);
    background:rgba(255,255,255,0.02);
    font-size:13px;
    color:#dce4fb;
}
.exchange_cat.active{
    background:linear-gradient(90deg, rgba(124,58,237,0.34), rgba(37,99,235,0.22));
    border-color:rgba(124,58,237,0.35);
}
.create_worker_box{
    margin-top:10px;
    background:linear-gradient(180deg, rgba(17,26,49,0.96), rgba(11,16,31,0.96));
    border:1px solid rgba(124,58,237,0.25);
    border-radius:18px;
    padding:14px;
}
.exchange_grid{
    display:grid;
    grid-template-columns:repeat(3,1fr);
    gap:14px;
}
.market_card{
    border-radius:18px;
    overflow:hidden;
    border:1px solid rgba(255,255,255,0.08);
    background:linear-gradient(180deg, rgba(14,21,41,0.98), rgba(10,15,28,0.98));
}
.market_img{
    height:140px;
    position:relative;
}
.market_body{
    padding:14px;
}
.market_name{
    font-size:28px;
    line-height:1.02;
    font-weight:900;
    margin-bottom:4px;
}
.market_role{
    color:#cdd7f6;
    font-size:13px;
    margin-bottom:8px;
}
.rating{
    font-size:13px;
    color:#facc15;
    margin-bottom:8px;
}
.price{
    font-size:28px;
    font-weight:900;
    margin-bottom:12px;
}
.price span{
    font-size:14px;
    color:var(--muted);
    font-weight:700;
}
.market_actions{
    display:flex;
    justify-content:space-between;
    align-items:center;
    gap:8px;
}
.small_btn{
    padding:10px 14px;
    border-radius:12px;
    font-weight:800;
    font-size:13px;
    background:linear-gradient(90deg,#7c3aed,#2563eb);
    border:none;
    color:white;
}
.icon_cart{
    width:36px;height:36px;border-radius:12px;
    display:flex;align-items:center;justify-content:center;
    border:1px solid rgba(255,255,255,0.08);
    background:rgba(255,255,255,0.03);
}

.network_body{
    padding:0 16px 16px;
}
.map_box{
    min-height:240px;
    border-radius:20px;
    background:
      radial-gradient(circle at 20% 40%, rgba(124,58,237,0.16), transparent 16%),
      radial-gradient(circle at 80% 32%, rgba(37,99,235,0.14), transparent 18%),
      linear-gradient(180deg, rgba(10,14,28,0.98), rgba(8,11,21,0.98));
    border:1px solid rgba(255,255,255,0.05);
    position:relative;
    overflow:hidden;
}
.map_svg{
    position:absolute; inset:0;
}
.map_glow{
    position:absolute;
    width:12px;height:12px;border-radius:50%;
    background:#a855f7;
    box-shadow:0 0 18px rgba(168,85,247,0.9);
}
.stats_bar{
    display:grid;
    grid-template-columns:repeat(4,1fr);
    gap:12px;
    margin-top:14px;
}
.stat_tile{
    background:rgba(255,255,255,0.02);
    border:1px solid rgba(255,255,255,0.05);
    border-radius:16px;
    padding:14px;
}
.stat_tile .v{font-size:34px;font-weight:900}
.stat_tile .l{font-size:13px;color:var(--muted)}

.network_bottom{
    display:grid;
    grid-template-columns:1fr 1fr;
    gap:14px;
    margin-top:14px;
}
.region_box, .recent_box{
    background:rgba(255,255,255,0.02);
    border:1px solid rgba(255,255,255,0.05);
    border-radius:18px;
    padding:14px;
}
.box_title{
    font-size:15px;
    font-weight:900;
    margin-bottom:12px;
}
.region_row{
    display:grid;
    grid-template-columns:120px 1fr 90px;
    gap:10px;
    align-items:center;
    margin-bottom:10px;
    font-size:13px;
}
.bar{
    height:8px;border-radius:999px;background:rgba(255,255,255,0.06);overflow:hidden;
}
.bar > div{
    height:100%;
    background:linear-gradient(90deg,#7c3aed,#2563eb);
    border-radius:999px;
}
.recent_item{
    display:flex;
    justify-content:space-between;
    gap:10px;
    font-size:13px;
    padding:10px 0;
    border-bottom:1px solid rgba(255,255,255,0.04);
}
.recent_item:last-child{border-bottom:none}
.recent_left{
    display:flex;
    gap:10px;
}
.recent_dot{
    width:8px;height:8px;border-radius:50%;background:#a855f7;margin-top:6px;
    box-shadow:0 0 14px rgba(168,85,247,0.7);
}
.muted{color:var(--muted)}
.small{font-size:12px}

.page_section{
    background:linear-gradient(180deg, rgba(10,14,28,0.98), rgba(8,11,21,0.98));
    border:1px solid var(--line);
    border-radius:24px;
    box-shadow:var(--shadow);
    padding:22px;
    margin-top:16px;
}
.page_section h1{
    margin:0 0 10px 0;
    font-size:36px;
    line-height:1.05;
}
.page_section p{
    color:var(--muted);
    line-height:1.65;
    font-size:15px;
}
.simple_grid{
    display:grid;
    grid-template-columns:repeat(3,1fr);
    gap:14px;
    margin-top:18px;
}
.simple_card{
    background:rgba(255,255,255,0.02);
    border:1px solid rgba(255,255,255,0.06);
    border-radius:18px;
    padding:18px;
}
.simple_card h3{
    margin:0 0 8px 0;
    font-size:22px;
}
.list{
    margin:0;
    padding-left:18px;
    color:#e9efff;
}
.list li{
    margin:8px 0;
    line-height:1.5;
}
.footer_note{
    margin-top:18px;
    color:var(--muted-2);
    font-size:12px;
}

@media (max-width: 1450px){
    .top_shell{grid-template-columns:1fr}
    .left_brand{min-height:auto}
    .right_app{min-height:auto}
    .app_shell{grid-template-columns:150px 1fr}
    .lower_grid{grid-template-columns:1fr}
    .hero_grid{grid-template-columns:1fr}
    .workforce_and_system{grid-template-columns:1fr}
    .worker_cards{grid-template-columns:repeat(2,1fr)}
}

@media (max-width: 1100px){
    .app_shell{grid-template-columns:1fr}
    .sidebar{
        border-right:none;
        border-bottom:1px solid var(--line);
    }
    .sidebar_worker_card{display:none}
    .hero_panel{min-height:auto}
    .globe_wrap{
        position:relative;
        right:auto; top:auto;
        width:100%; height:220px;
        margin-top:18px;
    }
    .hero_globe_text{
        position:relative;
        right:auto; top:auto; width:auto;
        margin-top:10px;
    }
    .kpi_row{grid-template-columns:repeat(2,1fr)}
    .worker_cards{grid-template-columns:repeat(2,1fr)}
    .phone_row{grid-template-columns:1fr}
    .exchange_wrap{grid-template-columns:1fr}
    .exchange_grid{grid-template-columns:repeat(2,1fr)}
    .simple_grid{grid-template-columns:1fr}
}

@media (max-width: 760px){
    .page{padding:10px}
    .brand_logo_row{flex-direction:column; align-items:flex-start}
    .brand_title{font-size:56px}
    .pillars{grid-template-columns:repeat(2,1fr)}
    .trusted_logos{grid-template-columns:repeat(2,1fr)}
    .topbar{flex-direction:column; align-items:stretch}
    .search{max-width:none}
    .topbar_right{justify-content:flex-end}
    .kpi_row{grid-template-columns:1fr}
    .worker_cards{grid-template-columns:1fr}
    .exchange_grid{grid-template-columns:1fr}
    .stats_bar{grid-template-columns:repeat(2,1fr)}
    .network_bottom{grid-template-columns:1fr}
    .simple_grid{grid-template-columns:1fr}
}
</style>
"""

# ============================================================
# DATA
# ============================================================

WORKERS = [
    {
        "name": "Nina Sales",
        "role": "AI Sales Executive",
        "status": "ACTIVE",
        "status_class": "status_active",
        "task": "Following up with 15 leads",
        "theme": "sales",
        "price": "€99",
        "rating": "4.9 (129)"
    },
    {
        "name": "Nina Estimator",
        "role": "AI Estimator",
        "status": "ACTIVE",
        "status_class": "status_active",
        "task": "Working on 3 estimates",
        "theme": "estimator",
        "price": "€119",
        "rating": "4.9 (96)"
    },
    {
        "name": "Nina Office Manager",
        "role": "AI Office Manager",
        "status": "ACTIVE",
        "status_class": "status_active",
        "task": "Managing your schedule",
        "theme": "office",
        "price": "€89",
        "rating": "4.8 (74)"
    },
    {
        "name": "Nina Support",
        "role": "AI Support Specialist",
        "status": "IDLE",
        "status_class": "status_idle",
        "task": "Waiting for new tasks",
        "theme": "support",
        "price": "€79",
        "rating": "4.8 (102)"
    },
]

EXCHANGE_WORKERS = [
    ("Nina Sales", "AI Sales Executive", "sales", "€99", "4.9 (129)"),
    ("Nina Estimator", "AI Estimator", "estimator", "€119", "4.9 (96)"),
    ("Nina Office Manager", "AI Office Manager", "office", "€89", "4.8 (74)"),
    ("Nina Support", "AI Support Specialist", "support", "€79", "4.8 (102)"),
    ("Nina Marketing", "AI Marketing Specialist", "sales", "€99", "4.8 (80)"),
    ("Nina HR", "AI HR Assistant", "sales", "€89", "4.8 (65)"),
]

# ============================================================
# SMALL HTML BUILDERS
# ============================================================

def worker_card(name, role, status, status_class, task, theme):
    return f"""
    <div class="worker_card">
        <div class="worker_img {theme}">
            <div class="portrait"></div>
        </div>
        <div class="worker_body">
            <div class="worker_name">{name}</div>
            <div class="worker_role">{role}</div>
            <div class="worker_status">
                <span class="{status_class}">● {status}</span>
            </div>
            <div class="worker_task">{task}</div>
        </div>
    </div>
    """

def market_card(name, role, theme, price, rating):
    return f"""
    <div class="market_card">
        <div class="market_img worker_img {theme}">
            <div class="portrait"></div>
        </div>
        <div class="market_body">
            <div class="market_name">{name}</div>
            <div class="market_role">{role}</div>
            <div class="rating">★ {rating}</div>
            <div class="price">{price}<span>/month</span></div>
            <div class="market_actions">
                <button class="small_btn">View Details</button>
                <div class="icon_cart">🛒</div>
            </div>
        </div>
    </div>
    """

def app_sidebar(active="dashboard"):
    def item(label, href, key, icon, badge=""):
        active_cls = "active" if active == key else ""
        badge_html = f'<span class="nav_badge">{badge}</span>' if badge else ""
        return f'<a class="nav_item {active_cls}" href="{href}"><span>{icon}</span><span>{label}</span>{badge_html}</a>'

    return f"""
    <div class="sidebar">
        <div class="sidebar_brand">
            <div class="sidebar_logo"></div>
            <div class="sidebar_brand_name">NinaOS</div>
        </div>

        <div class="nav_group">
            {item("Dashboard", "/dashboard", "dashboard", "⌂")}
            {item("Workers", "/workers", "workers", "◌")}
            {item("Tasks", "/dashboard", "tasks", "☑")}
            {item("Clients", "/dashboard", "clients", "◍")}
            {item("Projects", "/dashboard", "projects", "▣")}
            {item("Calendar", "/dashboard", "calendar", "◫")}
            {item("Files", "/dashboard", "files", "▤")}
            {item("Analytics", "/dashboard", "analytics", "⌁")}
            {item("Exchange", "/exchange", "exchange", "◎", "NEW")}
            {item("Marketplace", "/exchange", "marketplace", "✦")}
            {item("Integrations", "/dashboard", "integrations", "⟡")}
            {item("Settings", "/dashboard", "settings", "⚙")}
        </div>

        <div class="sidebar_worker_card">
            <div class="sidebar_worker_title">Nina Office Manager SMB</div>
            <div class="sidebar_worker_sub">
                First ready AI worker for small businesses.
                Tasks, follow-ups, invoices, estimates and documents.
            </div>
        </div>

        <div class="sidebar_user">
            <div class="avatar">K</div>
            <div class="user_meta">
                <div class="name">Katrin</div>
                <div class="role">Owner</div>
            </div>
        </div>
    </div>
    """

def topbar():
    return """
    <div class="topbar">
        <input class="search" placeholder="Search anything..." />
        <div class="topbar_right">
            <div class="icon_btn">🔔</div>
            <div class="icon_btn">🌐</div>
            <div class="icon_btn">☼</div>
            <div class="user_chip">
                <div class="avatar">K</div>
                <div>
                    <div class="user_chip_name">Katrin</div>
                    <div class="user_chip_role">Owner</div>
                </div>
            </div>
        </div>
    </div>
    """

def left_brand_panel():
    return """
    <div class="left_brand">
        <div class="brand_logo_row">
            <div class="brand_globe"></div>
            <div class="brand_title_wrap">
                <h1 class="brand_title">Nina<span class="accent">OS</span></h1>
                <div class="brand_sub">AI Workforce Operating System</div>
            </div>
        </div>

        <div class="hero_copy">
            <div>One Platform. Unlimited AI Workers.</div>
            <div class="soft">For every business. Everywhere.</div>
        </div>

        <div class="pillars">
            <div class="pillar">
                <div class="pillar_icon">🌐</div>
                <div class="pillar_title">Global</div>
                <div class="pillar_desc">Built for a global future and cross-border AI work.</div>
            </div>
            <div class="pillar">
                <div class="pillar_icon">👥</div>
                <div class="pillar_title">Workforce</div>
                <div class="pillar_desc">AI employees that work for you across sales, ops, finance and support.</div>
            </div>
            <div class="pillar">
                <div class="pillar_icon">🛡</div>
                <div class="pillar_title">Secure</div>
                <div class="pillar_desc">Your data. Your rules. Role-based access and approval boundaries.</div>
            </div>
            <div class="pillar">
                <div class="pillar_icon">🚀</div>
                <div class="pillar_title">Scale</div>
                <div class="pillar_desc">From 1 to 10,000+ AI workers across companies, teams and marketplaces.</div>
            </div>
        </div>

        <div class="cta_row">
            <a class="btn btn_primary" href="/dashboard">Get Started</a>
            <a class="btn btn_secondary" href="/exchange">Explore Exchange</a>
        </div>

        <div class="trusted">Trusted by forward-thinking companies worldwide</div>
        <div class="trusted_logos">
            <div class="logo_chip">Architects</div>
            <div class="logo_chip">BuildPro</div>
            <div class="logo_chip">NordBuild</div>
            <div class="logo_chip">HouseFit</div>
            <div class="logo_chip">VisionGroup</div>
        </div>
    </div>
    """

def hero_dashboard():
    return """
    <div class="hero_grid">
        <div class="hero_panel">
            <div class="hero_title">Good morning, Katrin 👋</div>
            <div class="hero_sub">Here’s what’s happening in your workspace today.</div>

            <div class="kpi_row">
                <div class="kpi">
                    <div class="kpi_head"><span>AI Workers</span><span>◌</span></div>
                    <div class="kpi_value">12</div>
                    <div class="kpi_delta blue">↑ 2 today</div>
                </div>
                <div class="kpi">
                    <div class="kpi_head"><span>Tasks in Progress</span><span>◎</span></div>
                    <div class="kpi_value">28</div>
                    <div class="kpi_delta pink">↑ 5 today</div>
                </div>
                <div class="kpi">
                    <div class="kpi_head"><span>Completed Today</span><span>✓</span></div>
                    <div class="kpi_value">15</div>
                    <div class="kpi_delta">↑ 7 today</div>
                </div>
                <div class="kpi">
                    <div class="kpi_head"><span>Upcoming</span><span>⌚</span></div>
                    <div class="kpi_value">6</div>
                    <div class="kpi_delta blue">Today</div>
                </div>
            </div>

            <div class="globe_wrap">
                <div class="globe"></div>
                <div class="orbit"></div>
                <div class="orbit2"></div>
                <div class="orbit3"></div>
            </div>

            <div class="hero_globe_text">
                <h3>Global AI Workforce</h3>
                <p>Connected. Intelligent. Tireless.</p>
                <a class="btn btn_secondary" href="/exchange">View Global Network →</a>
            </div>
        </div>

        <div class="system_card">
            <div>
                <div class="system_block_title">System Status</div>
                <div class="status_line">
                    <div><span class="live_dot"></span>All Systems Operational</div>
                    <div class="muted">Live ↗</div>
                </div>
                <div class="muted small">99.9% Uptime</div>
                <div class="chart">
                    <svg viewBox="0 0 300 100" preserveAspectRatio="none">
                        <polyline fill="none" stroke="#a855f7" stroke-width="3"
                            points="0,72 20,68 40,75 60,66 80,70 100,58 120,64 140,52 160,56 180,48 200,54 220,40 240,45 260,32 280,28 300,12"/>
                    </svg>
                </div>
            </div>

            <div>
                <div class="system_block_title">Active Workspaces</div>
                <div class="workspaces">
                    <div class="ws_avatar ws1">AB</div>
                    <div class="ws_avatar ws2">NB</div>
                    <div class="ws_avatar ws3">VG</div>
                    <div class="ws_avatar ws4">HF</div>
                    <div class="ws_avatar ws5">CP</div>
                    <div class="ws_avatar ws6">AX</div>
                    <div class="ws_avatar ws_plus">+</div>
                </div>
            </div>
        </div>
    </div>
    """

def workforce_section():
    cards = "".join(worker_card(w["name"], w["role"], w["status"], w["status_class"], w["task"], w["theme"]) for w in WORKERS)
    return f"""
    <div class="workforce_and_system">
        <div>
            <div class="section_title">Your AI Workforce</div>
            <div class="worker_cards">
                {cards}
            </div>
        </div>

        <div class="system_card">
            <div>
                <div class="system_block_title">Nina Office Manager SMB</div>
                <div class="muted" style="line-height:1.6;">
                    First ready AI worker for small businesses.
                    Handles tasks, follow-ups, invoices, estimates and documents.
                </div>
                <div style="margin-top:14px; display:flex; flex-direction:column; gap:10px;">
                    <a class="btn btn_primary" href="/office-manager">Open Worker</a>
                    <a class="btn btn_secondary" href="/dashboard">Open Dashboard</a>
                </div>
            </div>

            <div>
                <div class="system_block_title">Live Workspace Snapshot</div>
                <div class="status_line"><span>Tasks Today</span><strong>1</strong></div>
                <div class="status_line"><span>Follow-ups</span><strong>1</strong></div>
                <div class="status_line"><span>Invoices Due</span><strong>1</strong></div>
                <div class="status_line"><span>Estimates in Progress</span><strong>1</strong></div>
                <div class="status_line"><span>Active Projects</span><strong>1</strong></div>
            </div>
        </div>
    </div>
    """

def mobile_preview_panel():
    return """
    <div class="panel mobile_preview">
        <div class="panel_header">
            <div>
                <div class="panel_title">Mobile App Preview</div>
                <div class="panel_sub">Mobile-first NinaOS surfaces for owners working on the go.</div>
            </div>
        </div>

        <div class="phone_row">
            <div class="phone">
                <div class="phone_screen">
                    <div class="phone_top"><span>9:41</span><span>▮▮▮</span></div>
                    <div class="phone_h">Good morning, Katrin 👋</div>

                    <div class="mobile_stats">
                        <div class="mobile_stat"><div class="v">12</div><div class="l">Workers</div></div>
                        <div class="mobile_stat"><div class="v">28</div><div class="l">Tasks</div></div>
                        <div class="mobile_stat"><div class="v">15</div><div class="l">Done</div></div>
                        <div class="mobile_stat"><div class="v">6</div><div class="l">Upcoming</div></div>
                    </div>

                    <div class="mobile_list">
                        <div class="mobile_item">
                            <div class="mobile_item_title">Nina Sales — ACTIVE</div>
                            <div class="mobile_item_sub">Following up with 15 leads</div>
                        </div>
                        <div class="mobile_item">
                            <div class="mobile_item_title">Nina Estimator — ACTIVE</div>
                            <div class="mobile_item_sub">Working on 3 estimates</div>
                        </div>
                        <div class="mobile_item">
                            <div class="mobile_item_title">Nina Office Manager — ACTIVE</div>
                            <div class="mobile_item_sub">Managing your schedule</div>
                        </div>
                        <div class="mobile_item">
                            <div class="mobile_item_title">Nina Support — IDLE</div>
                            <div class="mobile_item_sub">Waiting for new tasks</div>
                        </div>
                    </div>
                </div>
            </div>

            <div class="phone">
                <div class="phone_screen">
                    <div class="phone_top"><span>9:41</span><span>▮▮▮</span></div>
                    <div class="phone_h">Tasks</div>

                    <div class="mobile_list">
                        <div class="mobile_item">
                            <div class="mobile_item_title">Follow up with Acme Corp</div>
                            <div class="mobile_item_sub">Nina Sales · 2 min ago</div>
                        </div>
                        <div class="mobile_item">
                            <div class="mobile_item_title">Create estimate for Project X</div>
                            <div class="mobile_item_sub">Nina Estimator · 15 min ago</div>
                        </div>
                        <div class="mobile_item">
                            <div class="mobile_item_title">Schedule meeting with Client Y</div>
                            <div class="mobile_item_sub">Nina Office Manager · 45 min ago</div>
                        </div>
                        <div class="mobile_item">
                            <div class="mobile_item_title">Send proposal to Beta Ltd</div>
                            <div class="mobile_item_sub">Nina Sales · 1 hour ago</div>
                        </div>
                    </div>
                </div>
            </div>

            <div class="phone">
                <div class="phone_screen">
                    <div class="phone_top"><span>9:41</span><span>▮▮▮</span></div>
                    <div class="mobile_worker_box">
                        <div class="phone_h" style="margin-bottom:6px;">Nina Sales</div>
                        <div class="mobile_item_sub">AI Sales Executive · ACTIVE</div>
                        <div class="progress"><div style="width:78%"></div></div>
                        <div class="mobile_list">
                            <div class="mobile_item">
                                <div class="mobile_item_title">Email sent to Acme Corp</div>
                                <div class="mobile_item_sub">2 min ago</div>
                            </div>
                            <div class="mobile_item">
                                <div class="mobile_item_title">Call with Client Y</div>
                                <div class="mobile_item_sub">15 min ago</div>
                            </div>
                            <div class="mobile_item">
                                <div class="mobile_item_title">Follow up with Gamma Inc</div>
                                <div class="mobile_item_sub">30 min ago</div>
                            </div>
                        </div>
                        <div style="margin-top:14px;">
                            <a class="btn btn_primary" href="/workers" style="width:100%; padding:12px 14px;">Message Worker</a>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>
    """

def exchange_panel():
    cards = "".join(market_card(*w) for w in EXCHANGE_WORKERS)
    return f"""
    <div class="panel">
        <div class="panel_header">
            <div>
                <div class="panel_title">Exchange — AI Workers Marketplace</div>
                <div class="panel_sub">Ready AI workers for sales, operations, finance, support and more.</div>
            </div>
            <a class="panel_link" href="/exchange">View all workers →</a>
        </div>

        <div class="exchange_wrap">
            <div class="exchange_side">
                <div class="exchange_cat active">All Categories</div>
                <div class="exchange_cat">Sales & Growth</div>
                <div class="exchange_cat">Marketing</div>
                <div class="exchange_cat">Construction</div>
                <div class="exchange_cat">Finance</div>
                <div class="exchange_cat">Operations</div>
                <div class="exchange_cat">Support</div>
                <div class="exchange_cat">HR & Recruiting</div>
                <div class="exchange_cat">Legal</div>
                <div class="exchange_cat">Custom</div>

                <div class="create_worker_box">
                    <div class="sidebar_worker_title">Create Your Own AI Worker</div>
                    <div class="sidebar_worker_sub">
                        Build and publish your custom AI worker into NinaOS Exchange later.
                    </div>
                    <div style="margin-top:14px;">
                        <a class="btn btn_primary" href="/exchange" style="width:100%; padding:12px 14px;">Create Worker</a>
                    </div>
                </div>
            </div>

            <div class="exchange_grid">
                {cards}
            </div>
        </div>
    </div>
    """

def network_panel():
    return """
    <div class="panel">
        <div class="panel_header">
            <div>
                <div class="panel_title">Global Network</div>
                <div class="panel_sub">NinaOS AI workforce network, marketplace and active workspaces.</div>
            </div>
            <a class="panel_link" href="/exchange">View network →</a>
        </div>

        <div class="network_body">
            <div class="map_box">
                <svg class="map_svg" viewBox="0 0 900 280" preserveAspectRatio="none">
                    <path d="M60 120 C120 80, 180 85, 230 110 C280 135, 330 130, 380 110 C430 90, 500 88, 560 110 C620 132, 690 135, 760 110 C810 92, 850 95, 890 120"
                          fill="none" stroke="rgba(168,85,247,0.35)" stroke-width="2"/>
                    <path d="M100 160 C170 120, 250 125, 310 155 C360 180, 420 180, 490 155 C560 130, 650 125, 730 150 C790 168, 840 165, 890 145"
                          fill="none" stroke="rgba(59,130,246,0.25)" stroke-width="2"/>
                    <path d="M150 70 C240 130, 300 150, 390 120 C470 92, 560 70, 660 95 C730 112, 800 145, 860 175"
                          fill="none" stroke="rgba(168,85,247,0.28)" stroke-width="2"/>
                </svg>

                <div class="map_glow" style="left:12%; top:40%;"></div>
                <div class="map_glow" style="left:18%; top:52%;"></div>
                <div class="map_glow" style="left:31%; top:34%;"></div>
                <div class="map_glow" style="left:47%; top:44%;"></div>
                <div class="map_glow" style="left:56%; top:30%;"></div>
                <div class="map_glow" style="left:69%; top:38%;"></div>
                <div class="map_glow" style="left:78%; top:48%;"></div>
                <div class="map_glow" style="left:84%; top:58%;"></div>
            </div>

            <div class="stats_bar">
                <div class="stat_tile"><div class="v">12,458</div><div class="l">AI Workers Online</div></div>
                <div class="stat_tile"><div class="v">1,247</div><div class="l">Workspaces</div></div>
                <div class="stat_tile"><div class="v">98</div><div class="l">Countries</div></div>
                <div class="stat_tile"><div class="v">2.4M</div><div class="l">Tasks Completed Today</div></div>
            </div>

            <div class="network_bottom">
                <div class="region_box">
                    <div class="box_title">Top Active Regions</div>

                    <div class="region_row">
                        <div>North America</div>
                        <div class="bar"><div style="width:78%"></div></div>
                        <div class="muted">3,245 workers</div>
                    </div>
                    <div class="region_row">
                        <div>Europe</div>
                        <div class="bar"><div style="width:72%"></div></div>
                        <div class="muted">2,987 workers</div>
                    </div>
                    <div class="region_row">
                        <div>Asia</div>
                        <div class="bar"><div style="width:86%"></div></div>
                        <div class="muted">4,126 workers</div>
                    </div>
                    <div class="region_row">
                        <div>Other</div>
                        <div class="bar"><div style="width:44%"></div></div>
                        <div class="muted">2,100 workers</div>
                    </div>
                </div>

                <div class="recent_box">
                    <div class="box_title">Recent Activity</div>

                    <div class="recent_item">
                        <div class="recent_left"><span class="recent_dot"></span><span>Nina Estimator completed estimate</span></div>
                        <div class="muted">2 min ago</div>
                    </div>
                    <div class="recent_item">
                        <div class="recent_left"><span class="recent_dot"></span><span>Nina Sales closed a deal</span></div>
                        <div class="muted">5 min ago</div>
                    </div>
                    <div class="recent_item">
                        <div class="recent_left"><span class="recent_dot"></span><span>Nina Office Manager scheduled meeting</span></div>
                        <div class="muted">8 min ago</div>
                    </div>
                    <div class="recent_item">
                        <div class="recent_left"><span class="recent_dot"></span><span>Nina Support resolved ticket</span></div>
                        <div class="muted">10 min ago</div>
                    </div>
                </div>
            </div>
        </div>
    </div>
    """

def app_dashboard_surface():
    return f"""
    <div class="right_app">
        <div class="app_shell">
            {app_sidebar(active="dashboard")}
            <div class="main">
                {topbar()}
                {hero_dashboard()}
                {workforce_section()}

                <div class="lower_grid">
                    {mobile_preview_panel()}
                    {exchange_panel()}
                    {network_panel()}
                </div>
            </div>
        </div>
    </div>
    """

def render_page(body, title="NinaOS"):
    return f"""
    <!doctype html>
    <html>
    <head>
        <meta charset="utf-8" />
        <meta name="viewport" content="width=device-width, initial-scale=1" />
        <title>{title}</title>
        {BASE_CSS}
    </head>
    <body>
        <div class="page">
            {body}
        </div>
    </body>
    </html>
    """

# ============================================================
# PAGE CONTENTS
# ============================================================

def home_page():
    body = f"""
    <div class="top_shell">
        {left_brand_panel()}
        {app_dashboard_surface()}
    </div>
    """
    return render_page(body, "NinaOS — AI Workforce Operating System")

def dashboard_page():
    body = f"""
    <div class="right_app">
        <div class="app_shell">
            {app_sidebar(active="dashboard")}
            <div class="main">
                {topbar()}
                {hero_dashboard()}
                {workforce_section()}
                <div class="page_section">
                    <h1>Workspace Dashboard</h1>
                    <p>
                        This dashboard is the first real NinaOS browser workspace surface.
                        It combines worker overview, KPI cards, live workspace stats, exchange visibility
                        and mobile-first product direction in one operating surface.
                    </p>

                    <div class="simple_grid">
                        <div class="simple_card">
                            <h3>Tasks Today</h3>
                            <ul class="list">
                                <li>Prepare today workspace priorities</li>
                                <li>Follow up with Demo Client about offer</li>
                                <li>Review invoice admin reminder</li>
                            </ul>
                        </div>
                        <div class="simple_card">
                            <h3>Recent Activities</h3>
                            <ul class="list">
                                <li>Exchange preview available</li>
                                <li>Estimate draft created</li>
                                <li>Invoice admin record created</li>
                            </ul>
                        </div>
                        <div class="simple_card">
                            <h3>Exchange Preview</h3>
                            <ul class="list">
                                <li>Nina Office Manager SMB — active</li>
                                <li>Nina Sales — planned / live surface</li>
                                <li>Nina Estimator — planned / live surface</li>
                            </ul>
                        </div>
                    </div>

                    <div class="footer_note">Version: {APP_VERSION} · {CORE_VERSION}</div>
                </div>
            </div>
        </div>
    </div>
    """
    return render_page(body, "NinaOS Dashboard")

def workers_page():
    cards = "".join(worker_card(w["name"], w["role"], w["status"], w["status_class"], w["task"], w["theme"]) for w in WORKERS)
    body = f"""
    <div class="right_app">
        <div class="app_shell">
            {app_sidebar(active="workers")}
            <div class="main">
                {topbar()}

                <div class="page_section">
                    <h1>Your AI Workers</h1>
                    <p>
                        NinaOS customers do not build bots manually. They activate ready AI workers.
                        This page is the live worker catalog inside the workspace.
                    </p>

                    <div class="worker_cards" style="margin-top:18px;">
                        {cards}
                    </div>

                    <div class="simple_grid" style="margin-top:18px;">
                        <div class="simple_card">
                            <h3>Nina Office Manager SMB</h3>
                            <ul class="list">
                                <li>Tasks and deadlines</li>
                                <li>Client follow-ups</li>
                                <li>Invoice admin</li>
                                <li>Estimate draft support</li>
                                <li>Document organization</li>
                            </ul>
                        </div>
                        <div class="simple_card">
                            <h3>Nina Sales</h3>
                            <ul class="list">
                                <li>Lead follow-up</li>
                                <li>Pipeline movement</li>
                                <li>Client messaging drafts</li>
                                <li>Deal reminders</li>
                            </ul>
                        </div>
                        <div class="simple_card">
                            <h3>Nina Estimator</h3>
                            <ul class="list">
                                <li>Estimate draft preparation</li>
                                <li>Project scope support</li>
                                <li>Offer structure</li>
                                <li>Client requirement organization</li>
                            </ul>
                        </div>
                    </div>

                    <div class="footer_note">Version: {APP_VERSION} · {CORE_VERSION}</div>
                </div>
            </div>
        </div>
    </div>
    """
    return render_page(body, "NinaOS Workers")

def office_manager_page():
    body = f"""
    <div class="right_app">
        <div class="app_shell">
            {app_sidebar(active="workers")}
            <div class="main">
                {topbar()}

                <div class="page_section">
                    <h1>Nina Office Manager SMB</h1>
                    <p>
                        The first strategic NinaOS ready worker for small businesses.
                        Nina Office Manager SMB combines office management, finance admin support,
                        estimating support, client follow-up and document admin into one worker.
                    </p>

                    <div class="simple_grid">
                        <div class="simple_card">
                            <h3>Role Stack</h3>
                            <ul class="list">
                                <li>Office Manager Core</li>
                                <li>Finance Admin Assistant</li>
                                <li>Estimating Assistant Basic</li>
                                <li>Client Follow-up Manager</li>
                                <li>Document Admin</li>
                            </ul>
                        </div>

                        <div class="simple_card">
                            <h3>What Nina Handles</h3>
                            <ul class="list">
                                <li>Tasks and daily priorities</li>
                                <li>Client follow-up tracking</li>
                                <li>Invoice reminders and admin</li>
                                <li>Estimate / offer draft support</li>
                                <li>Document package organization</li>
                            </ul>
                        </div>

                        <div class="simple_card">
                            <h3>Approval Required</h3>
                            <ul class="list">
                                <li>approve_payment</li>
                                <li>send_invoice</li>
                                <li>send_final_estimate</li>
                                <li>share_document_external</li>
                                <li>export_financial_data</li>
                            </ul>
                        </div>
                    </div>

                    <div class="simple_grid">
                        <div class="simple_card">
                            <h3>Allowed Tools</h3>
                            <ul class="list">
                                <li>task_tools</li>
                                <li>followup_tools</li>
                                <li>client_tools</li>
                                <li>invoice_admin_tools</li>
                                <li>estimate_draft_tools</li>
                                <li>document_tools</li>
                            </ul>
                        </div>

                        <div class="simple_card">
                            <h3>Memory Scopes</h3>
                            <ul class="list">
                                <li>Workspace Memory</li>
                                <li>Client Memory</li>
                                <li>Project Memory</li>
                                <li>Document Memory</li>
                                <li>Role Memory</li>
                            </ul>
                        </div>

                        <div class="simple_card">
                            <h3>Quick Actions</h3>
                            <ul class="list">
                                <li>Ask Nina</li>
                                <li>New Task</li>
                                <li>Follow-up Client</li>
                                <li>Create Estimate Draft</li>
                                <li>Add Invoice Reminder</li>
                                <li>Upload Document</li>
                            </ul>
                        </div>
                    </div>

                    <div class="footer_note">Version: {APP_VERSION} · {CORE_VERSION}</div>
                </div>
            </div>
        </div>
    </div>
    """
    return render_page(body, "Nina Office Manager SMB")

def exchange_page():
    cards = "".join(market_card(*w) for w in EXCHANGE_WORKERS)
    body = f"""
    <div class="right_app">
        <div class="app_shell">
            {app_sidebar(active="exchange")}
            <div class="main">
                {topbar()}

                <div class="page_section">
                    <h1>NinaOS Exchange</h1>
                    <p>
                        NinaOS is not only one AI worker. It is a ready-worker platform and future AI worker marketplace.
                        Exchange is where customers discover, activate and later trade AI workers and AI services.
                    </p>

                    <div class="exchange_wrap" style="padding:0; margin-top:18px;">
                        <div class="exchange_side">
                            <div class="exchange_cat active">All Categories</div>
                            <div class="exchange_cat">Sales & Growth</div>
                            <div class="exchange_cat">Marketing</div>
                            <div class="exchange_cat">Construction</div>
                            <div class="exchange_cat">Finance</div>
                            <div class="exchange_cat">Operations</div>
                            <div class="exchange_cat">Support</div>
                            <div class="exchange_cat">HR & Recruiting</div>
                            <div class="exchange_cat">Legal</div>

                            <div class="create_worker_box">
                                <div class="sidebar_worker_title">Create / Publish Worker</div>
                                <div class="sidebar_worker_sub">
                                    Future NinaOS Exchange flow for custom workers and partner role packs.
                                </div>
                            </div>
                        </div>

                        <div class="exchange_grid">
                            {cards}
                        </div>
                    </div>

                    <div class="footer_note">Version: {APP_VERSION} · {CORE_VERSION}</div>
                </div>
            </div>
        </div>
    </div>
    """
    return render_page(body, "NinaOS Exchange")

# ============================================================
# ROUTES
# ============================================================

@app.route("/")
def home():
    return home_page()

@app.route("/dashboard")
def dashboard():
    return dashboard_page()

@app.route("/workers")
def workers():
    return workers_page()

@app.route("/office-manager")
def office_manager():
    return office_manager_page()

@app.route("/exchange")
def exchange():
    return exchange_page()

@app.route("/health")
def health():
    return {
        "ok": True,
        "app": "NinaOS Web App",
        "version": APP_VERSION,
        "core": CORE_VERSION
    }

# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080, debug=False)
