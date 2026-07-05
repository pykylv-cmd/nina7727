# web_app.py
# NinaOS Web App V1.0
# Build target: NinaOS Constitution V4.2
#
# Purpose:
# - First real visual browser app for NinaOS
# - Responsive web surface for desktop + mobile
# - Routes:
#   /
#   /dashboard
#   /workers
#   /office-manager
#   /exchange
#
# Run locally:
#   python web_app.py
#
# Then open:
#   http://127.0.0.1:8000
#
# Render:
#   Start command can be: python web_app.py

from __future__ import annotations

import os
from typing import Dict, Any, List


WEB_APP_VERSION = "Web App V1.0"


try:
    from flask import Flask, jsonify, redirect, url_for
except Exception as e:
    raise RuntimeError(
        "Flask is required for web_app.py. Add 'Flask' to requirements.txt."
    ) from e


try:
    from demo_setup import run_demo_setup
except Exception:
    def run_demo_setup(workspace_id: str = "demo_small_business", language: str = "en") -> Dict[str, Any]:
        return {"ok": False, "message": "demo_setup not connected"}


try:
    from work_objects import dashboard_counts
except Exception:
    def dashboard_counts(workspace_id: str = "demo_small_business") -> Dict[str, int]:
        return {
            "tasks_today": 0,
            "followups": 0,
            "invoices_due": 0,
            "estimates_in_progress": 0,
            "projects_active": 0,
        }


try:
    from activity_feed import list_activity_events
except Exception:
    def list_activity_events(workspace_id: str = "demo_small_business", limit: int = 6, event_type=None):
        return []


try:
    from product_demo import build_short_product_demo
except Exception:
    def build_short_product_demo(workspace_id: str = "demo_small_business", language: str = "en") -> str:
        return "NinaOS gives small businesses ready AI workers — not bot builders."


try:
    from app_surface import app_surface_schema
except Exception:
    def app_surface_schema() -> Dict[str, Any]:
        return {}


app = Flask(__name__)


# Seed demo data on web app boot.
try:
    run_demo_setup("demo_small_business", "en")
except Exception:
    pass


def get_dashboard_data() -> Dict[str, Any]:
    counts = dashboard_counts("demo_small_business")

    try:
        events = list_activity_events("demo_small_business", limit=6)
        activity = [
            {
                "title": getattr(e, "title", "Activity"),
                "description": getattr(e, "description", ""),
                "severity": getattr(e, "severity", "info"),
            }
            for e in events
        ]
    except Exception:
        activity = []

    if not activity:
        activity = [
            {
                "title": "Nina Office Manager SMB active",
                "description": "The first NinaOS ready worker is visible inside the product.",
                "severity": "success",
            },
            {
                "title": "Dashboard initialized",
                "description": "Small Business Workspace dashboard surface is connected.",
                "severity": "success",
            },
        ]

    return {
        "counts": counts,
        "activity": activity,
        "exchange": [
            {"name": "Nina Office Manager SMB", "status": "active", "tag": "Office"},
            {"name": "Nina Sales", "status": "planned", "tag": "Sales"},
            {"name": "Nina Estimator", "status": "planned", "tag": "Estimating"},
            {"name": "Nina Finance", "status": "planned", "tag": "Finance"},
            {"name": "Nina Support", "status": "planned", "tag": "Support"},
        ],
    }


def base_html(title: str, active: str, body: str) -> str:
    nav = [
        ("Dashboard", "/dashboard", "dashboard"),
        ("Workers", "/workers", "workers"),
        ("Office Manager", "/office-manager", "office"),
        ("Exchange", "/exchange", "exchange"),
    ]

    nav_html = "".join(
        f'<a class="nav-item {"active" if key == active else ""}" href="{href}">{label}</a>'
        for label, href, key in nav
    )

    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{title} · NinaOS</title>
  <style>
    :root {{
      --bg: #090b16;
      --panel: rgba(255,255,255,0.065);
      --panel2: rgba(255,255,255,0.095);
      --line: rgba(255,255,255,0.12);
      --text: #f5f7ff;
      --muted: #aab2d5;
      --muted2: #71799d;
      --accent: #8b5cf6;
      --accent2: #22d3ee;
      --success: #2dd4bf;
      --warning: #fbbf24;
      --danger: #fb7185;
      --shadow: 0 20px 70px rgba(0,0,0,0.35);
      --radius: 22px;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: Inter, ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, Arial, sans-serif;
      background:
        radial-gradient(circle at 15% 10%, rgba(139,92,246,.28), transparent 32%),
        radial-gradient(circle at 80% 0%, rgba(34,211,238,.18), transparent 30%),
        linear-gradient(135deg, #070914 0%, #0c1022 50%, #090b16 100%);
      color: var(--text);
      min-height: 100vh;
    }}
    a {{ color: inherit; text-decoration: none; }}
    .app-shell {{
      display: grid;
      grid-template-columns: 260px 1fr;
      min-height: 100vh;
    }}
    .sidebar {{
      padding: 24px;
      border-right: 1px solid var(--line);
      background: rgba(6,8,18,.72);
      backdrop-filter: blur(18px);
      position: sticky;
      top: 0;
      height: 100vh;
    }}
    .brand {{
      display: flex;
      align-items: center;
      gap: 12px;
      margin-bottom: 28px;
    }}
    .logo {{
      width: 42px;
      height: 42px;
      border-radius: 50%;
      background:
        radial-gradient(circle, rgba(34,211,238,.95), rgba(139,92,246,.9) 46%, rgba(255,255,255,.08) 48%),
        linear-gradient(135deg, var(--accent), var(--accent2));
      box-shadow: 0 0 40px rgba(139,92,246,.45);
      position: relative;
    }}
    .logo:after {{
      content: "";
      position: absolute;
      inset: 9px;
      border: 1px solid rgba(255,255,255,.45);
      border-radius: 50%;
    }}
    .brand-title {{ font-size: 20px; font-weight: 800; letter-spacing: -.03em; }}
    .brand-sub {{ font-size: 12px; color: var(--muted); margin-top: 2px; }}
    .nav {{
      display: grid;
      gap: 8px;
      margin-top: 20px;
    }}
    .nav-item {{
      padding: 12px 14px;
      border-radius: 14px;
      color: var(--muted);
      border: 1px solid transparent;
    }}
    .nav-item:hover, .nav-item.active {{
      color: var(--text);
      background: rgba(255,255,255,.08);
      border-color: var(--line);
    }}
    .side-card {{
      margin-top: 28px;
      padding: 16px;
      border-radius: var(--radius);
      background: linear-gradient(135deg, rgba(139,92,246,.18), rgba(34,211,238,.10));
      border: 1px solid var(--line);
    }}
    .side-card b {{ display:block; margin-bottom:6px; }}
    .side-card p {{ margin: 0; color: var(--muted); font-size: 13px; line-height: 1.45; }}
    .main {{
      padding: 22px;
      max-width: 1500px;
      width: 100%;
      margin: 0 auto;
    }}
    .topbar {{
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 16px;
      padding: 14px 0 22px;
    }}
    .search {{
      flex: 1;
      max-width: 520px;
      padding: 13px 16px;
      border-radius: 16px;
      border: 1px solid var(--line);
      background: rgba(255,255,255,.06);
      color: var(--muted);
    }}
    .btn {{
      border: 0;
      border-radius: 15px;
      padding: 12px 16px;
      background: linear-gradient(135deg, var(--accent), var(--accent2));
      color: white;
      font-weight: 700;
      box-shadow: 0 14px 40px rgba(139,92,246,.28);
      display: inline-flex;
      align-items: center;
      gap: 8px;
    }}
    .hero {{
      border-radius: 30px;
      padding: 30px;
      background:
        linear-gradient(135deg, rgba(255,255,255,.10), rgba(255,255,255,.045)),
        radial-gradient(circle at 80% 10%, rgba(34,211,238,.22), transparent 28%);
      border: 1px solid var(--line);
      box-shadow: var(--shadow);
      margin-bottom: 22px;
      overflow: hidden;
      position: relative;
    }}
    .hero h1 {{
      font-size: clamp(30px, 4vw, 58px);
      line-height: .98;
      margin: 0 0 14px;
      letter-spacing: -.06em;
    }}
    .hero p {{
      color: var(--muted);
      max-width: 760px;
      line-height: 1.65;
      margin: 0;
      font-size: 16px;
    }}
    .grid {{
      display: grid;
      grid-template-columns: repeat(12, 1fr);
      gap: 16px;
    }}
    .card {{
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: var(--radius);
      padding: 18px;
      box-shadow: 0 14px 45px rgba(0,0,0,.18);
    }}
    .span-3 {{ grid-column: span 3; }}
    .span-4 {{ grid-column: span 4; }}
    .span-5 {{ grid-column: span 5; }}
    .span-6 {{ grid-column: span 6; }}
    .span-7 {{ grid-column: span 7; }}
    .span-8 {{ grid-column: span 8; }}
    .span-12 {{ grid-column: span 12; }}
    .metric-label {{ color: var(--muted); font-size: 13px; }}
    .metric-value {{ font-size: 38px; font-weight: 850; letter-spacing: -.06em; margin-top: 8px; }}
    .section-title {{ font-size: 18px; font-weight: 800; margin: 0 0 14px; }}
    .muted {{ color: var(--muted); }}
    .list {{ display: grid; gap: 10px; }}
    .item {{
      padding: 12px;
      border-radius: 15px;
      background: rgba(255,255,255,.055);
      border: 1px solid rgba(255,255,255,.08);
    }}
    .item-title {{ font-weight: 700; }}
    .item-sub {{ color: var(--muted); font-size: 13px; margin-top: 4px; }}
    .pill {{
      display: inline-flex;
      padding: 5px 10px;
      border-radius: 999px;
      background: rgba(139,92,246,.18);
      border: 1px solid rgba(139,92,246,.35);
      color: #ddd6fe;
      font-size: 12px;
      font-weight: 700;
      margin: 3px 5px 3px 0;
    }}
    .pill.success {{ background: rgba(45,212,191,.13); border-color: rgba(45,212,191,.35); color: #99f6e4; }}
    .pill.planned {{ background: rgba(251,191,36,.12); border-color: rgba(251,191,36,.35); color: #fde68a; }}
    .worker-card {{
      display: grid;
      gap: 10px;
    }}
    .worker-head {{
      display: flex;
      justify-content: space-between;
      align-items: flex-start;
      gap: 12px;
    }}
    .worker-name {{ font-size: 22px; font-weight: 850; letter-spacing: -.04em; }}
    .mobile-bottom {{
      display: none;
      position: fixed;
      left: 12px;
      right: 12px;
      bottom: 12px;
      z-index: 20;
      background: rgba(9,11,22,.9);
      border: 1px solid var(--line);
      border-radius: 22px;
      backdrop-filter: blur(18px);
      padding: 8px;
      box-shadow: var(--shadow);
    }}
    .mobile-bottom a {{
      flex: 1;
      text-align: center;
      padding: 10px 4px;
      font-size: 12px;
      color: var(--muted);
      border-radius: 14px;
    }}
    .mobile-bottom a.active {{
      color: var(--text);
      background: rgba(255,255,255,.08);
    }}
    @media (max-width: 980px) {{
      .app-shell {{ grid-template-columns: 1fr; }}
      .sidebar {{ display: none; }}
      .main {{ padding: 14px 14px 88px; }}
      .topbar {{ padding-top: 8px; }}
      .search {{ display:none; }}
      .hero {{ padding: 22px; border-radius: 24px; }}
      .span-3, .span-4, .span-5, .span-6, .span-7, .span-8, .span-12 {{ grid-column: span 12; }}
      .mobile-bottom {{ display:flex; }}
      .btn {{ padding: 11px 13px; }}
    }}
  </style>
</head>
<body>
  <div class="app-shell">
    <aside class="sidebar">
      <a href="/" class="brand">
        <div class="logo"></div>
        <div>
          <div class="brand-title">NinaOS</div>
          <div class="brand-sub">AI Workforce OS</div>
        </div>
      </a>
      <nav class="nav">{nav_html}</nav>
      <div class="side-card">
        <b>Nina Office Manager SMB</b>
        <p>First ready AI worker for small businesses. Tasks, follow-ups, invoices, estimates, documents.</p>
      </div>
    </aside>
    <main class="main">
      <div class="topbar">
        <div class="search">Search workspace, clients, invoices, estimates...</div>
        <a class="btn" href="/dashboard">Open Dashboard</a>
      </div>
      {body}
    </main>
  </div>
  <nav class="mobile-bottom">
    <a class="{'active' if active == 'dashboard' else ''}" href="/dashboard">Dashboard</a>
    <a class="{'active' if active == 'workers' else ''}" href="/workers">Workers</a>
    <a class="{'active' if active == 'office' else ''}" href="/office-manager">Nina</a>
    <a class="{'active' if active == 'exchange' else ''}" href="/exchange">Exchange</a>
  </nav>
</body>
</html>"""


def metric_card(label: str, value: Any, description: str) -> str:
    return f"""
    <div class="card span-3">
      <div class="metric-label">{label}</div>
      <div class="metric-value">{value}</div>
      <div class="item-sub">{description}</div>
    </div>
    """


def dashboard_body() -> str:
    data = get_dashboard_data()
    counts = data["counts"]

    activity_html = "".join(
        f"""
        <div class="item">
          <div class="item-title">{event['title']}</div>
          <div class="item-sub">{event['description']}</div>
        </div>
        """
        for event in data["activity"][:6]
    )

    exchange_html = "".join(
        f"""
        <div class="item">
          <div class="worker-head">
            <div>
              <div class="item-title">{w['name']}</div>
              <div class="item-sub">{w['tag']}</div>
            </div>
            <span class="pill {'success' if w['status'] == 'active' else 'planned'}">{w['status']}</span>
          </div>
        </div>
        """
        for w in data["exchange"]
    )

    return f"""
    <section class="hero">
      <h1>Small Business Workspace</h1>
      <p>Your AI office surface for tasks, follow-ups, invoices, estimates, documents and ready AI workers.</p>
    </section>

    <section class="grid">
      {metric_card("Tasks Today", counts.get("tasks_today", 0), "Open or in-progress tasks.")}
      {metric_card("Follow-ups", counts.get("followups", 0), "Client follow-ups needing attention.")}
      {metric_card("Invoices Due", counts.get("invoices_due", 0), "Sent or overdue invoices.")}
      {metric_card("Estimates", counts.get("estimates_in_progress", 0), "Estimate or offer drafts.")}
      <div class="card span-8">
        <h2 class="section-title">Recent Activities</h2>
        <div class="list">{activity_html}</div>
      </div>
      <div class="card span-4">
        <h2 class="section-title">Nina Office Manager SMB</h2>
        <p class="muted">AI office manager for small businesses.</p>
        <div>
          <span class="pill">Office</span>
          <span class="pill">Finance Admin</span>
          <span class="pill">Estimating</span>
          <span class="pill">Follow-up</span>
          <span class="pill">Documents</span>
        </div>
        <br>
        <a class="btn" href="/office-manager">Open Worker</a>
      </div>
      <div class="card span-7">
        <h2 class="section-title">Exchange Preview</h2>
        <div class="list">{exchange_html}</div>
      </div>
      <div class="card span-5">
        <h2 class="section-title">Quick Actions</h2>
        <div class="list">
          <div class="item">New Task</div>
          <div class="item">New Estimate</div>
          <div class="item">New Invoice</div>
          <div class="item">Add Client</div>
          <div class="item">Upload Document</div>
        </div>
      </div>
    </section>
    """


@app.route("/")
def home():
    body = """
    <section class="hero">
      <h1>Ready AI workers for small businesses.</h1>
      <p>NinaOS is an AI workforce operating system. Customers do not build bots — they activate ready AI workers and give them work.</p>
      <br>
      <a class="btn" href="/dashboard">View Live Dashboard</a>
    </section>
    <section class="grid">
      <div class="card span-4">
        <h2 class="section-title">First Worker</h2>
        <div class="worker-name">Nina Office Manager SMB</div>
        <p class="muted">Tasks, clients, follow-ups, invoices, estimates and documents.</p>
      </div>
      <div class="card span-4">
        <h2 class="section-title">Mobile-first</h2>
        <p class="muted">Works on phones and desktop. Owners can follow up, check invoices and ask Nina anywhere.</p>
      </div>
      <div class="card span-4">
        <h2 class="section-title">Exchange-ready</h2>
        <p class="muted">NinaOS grows into a marketplace for ready AI workers and bot-to-bot collaboration.</p>
      </div>
    </section>
    """
    return base_html("Home", "home", body)


@app.route("/dashboard")
def dashboard():
    return base_html("Dashboard", "dashboard", dashboard_body())


@app.route("/workers")
def workers():
    body = """
    <section class="hero">
      <h1>Workers</h1>
      <p>Ready AI workers assigned to your workspace.</p>
    </section>
    <section class="grid">
      <div class="card span-6 worker-card">
        <div class="worker-head">
          <div>
            <div class="worker-name">Nina Office Manager SMB</div>
            <div class="muted">AI office manager for small businesses.</div>
          </div>
          <span class="pill success">active</span>
        </div>
        <div>
          <span class="pill">Office Manager Core</span>
          <span class="pill">Finance Admin</span>
          <span class="pill">Estimating</span>
          <span class="pill">Client Follow-up</span>
          <span class="pill">Document Admin</span>
        </div>
        <a class="btn" href="/office-manager">Open Worker</a>
      </div>
      <div class="card span-6">
        <h2 class="section-title">Planned Workers</h2>
        <div class="list">
          <div class="item">Nina Sales <span class="pill planned">planned</span></div>
          <div class="item">Nina Estimator <span class="pill planned">planned</span></div>
          <div class="item">Nina Finance <span class="pill planned">planned</span></div>
          <div class="item">Nina Support <span class="pill planned">planned</span></div>
        </div>
      </div>
    </section>
    """
    return base_html("Workers", "workers", body)


@app.route("/office-manager")
def office_manager():
    body = """
    <section class="hero">
      <h1>Nina Office Manager SMB</h1>
      <p>AI office manager for small businesses. She keeps tasks, clients, follow-ups, invoices, estimates and documents under control.</p>
    </section>
    <section class="grid">
      <div class="card span-7">
        <h2 class="section-title">What Nina handles</h2>
        <div class="list">
          <div class="item"><b>Tasks & deadlines</b><div class="item-sub">Daily priorities, reminders and follow-up work.</div></div>
          <div class="item"><b>Client follow-ups</b><div class="item-sub">Offers, meetings, invoices and unanswered clients.</div></div>
          <div class="item"><b>Invoice admin</b><div class="item-sub">Invoice tracking and payment follow-up support.</div></div>
          <div class="item"><b>Estimate drafts</b><div class="item-sub">Initial estimate and offer draft support.</div></div>
          <div class="item"><b>Documents</b><div class="item-sub">Files linked to clients, projects, invoices and estimates.</div></div>
        </div>
      </div>
      <div class="card span-5">
        <h2 class="section-title">Approval required</h2>
        <p class="muted">High-risk actions require human approval.</p>
        <span class="pill">send_invoice</span>
        <span class="pill">approve_payment</span>
        <span class="pill">send_final_estimate</span>
        <span class="pill">export_client_data</span>
        <span class="pill">share_document_external</span>
      </div>
    </section>
    """
    return base_html("Office Manager", "office", body)


@app.route("/exchange")
def exchange():
    data = get_dashboard_data()
    cards = "".join(
        f"""
        <div class="card span-4">
          <div class="worker-head">
            <div>
              <div class="worker-name" style="font-size:20px">{w['name']}</div>
              <div class="muted">{w['tag']} worker</div>
            </div>
            <span class="pill {'success' if w['status'] == 'active' else 'planned'}">{w['status']}</span>
          </div>
          <br>
          <a class="btn" href="/workers">View</a>
        </div>
        """
        for w in data["exchange"]
    )
    body = f"""
    <section class="hero">
      <h1>Nina Exchange</h1>
      <p>Marketplace for ready AI workers. First catalog starts with Office, Sales, Estimating, Finance and Support workers.</p>
    </section>
    <section class="grid">{cards}</section>
    """
    return base_html("Exchange", "exchange", body)


@app.route("/api/dashboard")
def api_dashboard():
    return jsonify(get_dashboard_data())


@app.route("/api/app-surface")
def api_app_surface():
    return jsonify(app_surface_schema())


@app.route("/health")
def health():
    return jsonify({"ok": True, "version": WEB_APP_VERSION})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8000"))
    app.run(host="0.0.0.0", port=port)
