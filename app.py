import os
import re
import json
import sqlite3
import asyncio
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

try:
    import psycopg2
except Exception:
    psycopg2 = None

try:
    import stripe
except Exception:
    stripe = None

from flask import Flask, request, jsonify
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes
from openai import OpenAI

app = Flask(__name__)

client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]

# V10.8.1 Strict Admin ENV
# Railway ENV example: ADMIN_USER_IDS=5138563912
# Drošības nolūkos nav fallback admina. Ja ENV nav uzlikts, admin komandas ir bloķētas.
ADMIN_USER_IDS = os.environ.get("ADMIN_USER_IDS", "")

DEFAULT_TIMEZONE = "Europe/Riga"
DATABASE_URL = os.environ.get("DATABASE_URL")
DB_FILE = "nina_memory.db"
USE_POSTGRES = bool(DATABASE_URL and psycopg2)

FREE_BACKUP_LIMIT = 5
FREE_REMINDER_LIMIT = 5
FREE_SUMMARY_LIMIT_PER_DAY = 1
XP_PER_LEVEL = 100

# V10/V10.1 Payments + Stripe Checkout Foundation
PLAN_FREE = "Free"
PLAN_PREMIUM_BASIC = "Premium Basic"
PLAN_PREMIUM_PLUS = "Premium Plus"

PREMIUM_BASIC_PRICE = 4.99
PREMIUM_PLUS_PRICE = 9.99
PREMIUM_CURRENCY = "EUR"

STRIPE_SECRET_KEY = os.environ.get("STRIPE_SECRET_KEY", "")
STRIPE_BASIC_CHECKOUT_URL = os.environ.get("STRIPE_BASIC_CHECKOUT_URL", "")
STRIPE_PLUS_CHECKOUT_URL = os.environ.get("STRIPE_PLUS_CHECKOUT_URL", "")
STRIPE_WEBHOOK_SECRET = os.environ.get("STRIPE_WEBHOOK_SECRET", "")

# V10.3 Stripe Webhooks + dynamic Checkout Sessions
STRIPE_BASIC_PRICE_ID = os.environ.get("STRIPE_BASIC_PRICE_ID", "")
STRIPE_PLUS_PRICE_ID = os.environ.get("STRIPE_PLUS_PRICE_ID", "")
STRIPE_SUCCESS_URL = os.environ.get("STRIPE_SUCCESS_URL", "https://t.me/")
STRIPE_CANCEL_URL = os.environ.get("STRIPE_CANCEL_URL", "https://t.me/")

if stripe and STRIPE_SECRET_KEY:
    stripe.api_key = STRIPE_SECRET_KEY



def db_sql(sql):
    if USE_POSTGRES:
        return sql
    return sql.replace("%s", "?").replace("SERIAL PRIMARY KEY", "INTEGER PRIMARY KEY AUTOINCREMENT")


def db_execute(cursor, sql, params=None):
    if params is None:
        return cursor.execute(db_sql(sql))
    return cursor.execute(db_sql(sql), params)


def get_db():
    if USE_POSTGRES:
        return psycopg2.connect(DATABASE_URL)
    return sqlite3.connect(DB_FILE)


def init_db():
    conn = get_db()
    if USE_POSTGRES:
        conn.autocommit = True
    c = conn.cursor()

    db_execute(c, """
        CREATE TABLE IF NOT EXISTS users (
            user_id TEXT PRIMARY KEY,
            name TEXT DEFAULT '',
            city TEXT DEFAULT '',
            hobbies TEXT DEFAULT '',
            facts TEXT DEFAULT '',
            timezone TEXT DEFAULT 'Europe/Riga',
            goals TEXT DEFAULT '',
            projects TEXT DEFAULT '',
            dreams TEXT DEFAULT '',
            important_dates TEXT DEFAULT '',
            summary TEXT DEFAULT '',
            premium INTEGER DEFAULT 0,
            premium_until TEXT DEFAULT '',
            pets TEXT DEFAULT '',
            family TEXT DEFAULT '',
            profession TEXT DEFAULT '',
            favorite_car TEXT DEFAULT '',
            favorite_color TEXT DEFAULT '',
            favorite_music TEXT DEFAULT '',
            summary_updated_at TEXT DEFAULT '',
            xp INTEGER DEFAULT 0,
            level INTEGER DEFAULT 1,
            streak_days INTEGER DEFAULT 0,
            last_seen_date TEXT DEFAULT ''
        )
    """)

    db_execute(c, """
        CREATE TABLE IF NOT EXISTS messages (
            id SERIAL PRIMARY KEY,
            user_id TEXT,
            role TEXT,
            text TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    db_execute(c, """
        CREATE TABLE IF NOT EXISTS reminders (
            id SERIAL PRIMARY KEY,
            user_id TEXT,
            text TEXT,
            remind_at TEXT,
            local_time TEXT,
            status TEXT DEFAULT 'active',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    db_execute(c, """
        CREATE TABLE IF NOT EXISTS memory_backups (
            id SERIAL PRIMARY KEY,
            user_id TEXT,
            backup_text TEXT,
            source TEXT DEFAULT 'manual',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    db_execute(c, """
        CREATE TABLE IF NOT EXISTS user_achievements (
            id SERIAL PRIMARY KEY,
            user_id TEXT,
            achievement_code TEXT,
            unlocked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    db_execute(c, """
        CREATE TABLE IF NOT EXISTS premium_transactions (
            id SERIAL PRIMARY KEY,
            user_id TEXT,
            plan_name TEXT,
            amount REAL,
            currency TEXT DEFAULT 'EUR',
            payment_method TEXT,
            status TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            expires_at TEXT,
            checkout_url TEXT DEFAULT '',
            stripe_session_id TEXT DEFAULT '',
            stripe_event_id TEXT DEFAULT '',
            customer_email TEXT DEFAULT ''
        )
    """)

    db_execute(c, """
        CREATE TABLE IF NOT EXISTS admin_audit_logs (
            id SERIAL PRIMARY KEY,
            user_id TEXT,
            action TEXT,
            status TEXT,
            command_text TEXT DEFAULT '',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    db_execute(c, """
        CREATE TABLE IF NOT EXISTS backup_scheduler (
            id SERIAL PRIMARY KEY,
            enabled INTEGER DEFAULT 1,
            frequency TEXT DEFAULT 'daily',
            last_run TEXT DEFAULT '',
            next_run TEXT DEFAULT '',
            total_runs INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)


    db_execute(c, """
        CREATE TABLE IF NOT EXISTS backup_restore_logs (
            id SERIAL PRIMARY KEY,
            user_id TEXT,
            backup_id TEXT,
            status TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    for col, col_type in [
        ("checkout_url", "TEXT DEFAULT ''"),
        ("stripe_session_id", "TEXT DEFAULT ''"),
        ("stripe_event_id", "TEXT DEFAULT ''"),
        ("customer_email", "TEXT DEFAULT ''"),
    ]:
        try:
            db_execute(c, f"ALTER TABLE premium_transactions ADD COLUMN {col} {col_type}")
        except Exception:
            pass

    # Ja tabulas jau eksistēja no vecākas versijas, pievieno trūkstošās kolonnas.
    for col, col_type in [
        ("timezone", "TEXT DEFAULT 'Europe/Riga'"),
        ("goals", "TEXT DEFAULT ''"),
        ("projects", "TEXT DEFAULT ''"),
        ("dreams", "TEXT DEFAULT ''"),
        ("important_dates", "TEXT DEFAULT ''"),
        ("summary", "TEXT DEFAULT ''"),
        ("premium", "INTEGER DEFAULT 0"),
        ("premium_until", "TEXT DEFAULT ''"),
        ("pets", "TEXT DEFAULT ''"),
        ("family", "TEXT DEFAULT ''"),
        ("profession", "TEXT DEFAULT ''"),
        ("favorite_car", "TEXT DEFAULT ''"),
        ("favorite_color", "TEXT DEFAULT ''"),
        ("favorite_music", "TEXT DEFAULT ''"),
        ("summary_updated_at", "TEXT DEFAULT ''"),
        ("xp", "INTEGER DEFAULT 0"),
        ("level", "INTEGER DEFAULT 1"),
        ("streak_days", "INTEGER DEFAULT 0"),
        ("last_seen_date", "TEXT DEFAULT ''"),
    ]:
        try:
            db_execute(c, f"ALTER TABLE users ADD COLUMN {col} {col_type}")
        except Exception:
            pass

    try:
        db_execute(c, "ALTER TABLE reminders ADD COLUMN local_time TEXT")
    except Exception:
        pass

    c.close()
    conn.close()


def get_user(user_id):
    conn = get_db()
    c = conn.cursor()
    db_execute(c, """
        SELECT name, city, hobbies, facts, timezone, goals, projects, dreams,
               important_dates, summary, premium, premium_until, pets, family,
               profession, favorite_car, favorite_color, favorite_music,
               summary_updated_at, xp, level, streak_days, last_seen_date
        FROM users WHERE user_id = %s
    """, (user_id,))
    row = c.fetchone()

    if not row:
        db_execute(c, """
            INSERT INTO users
            (user_id, name, city, hobbies, facts, timezone, goals, projects, dreams,
             important_dates, summary, premium, premium_until, pets, family,
             profession, favorite_car, favorite_color, favorite_music, summary_updated_at, xp, level, streak_days, last_seen_date)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            user_id, "", "", "", "", DEFAULT_TIMEZONE, "", "", "", "", "",
            0, "", "", "", "", "", "", "", "", 0, 1, 0, ""
        ))
        conn.commit()
        row = ("", "", "", "", DEFAULT_TIMEZONE, "", "", "", "", "", 0, "", "", "", "", "", "", "", "", 0, 1, 0, "")

    c.close()
    conn.close()

    user = {
        "name": row[0] or "",
        "city": row[1] or "",
        "hobbies": row[2] or "",
        "facts": row[3] or "",
        "timezone": row[4] or DEFAULT_TIMEZONE,
        "goals": row[5] or "",
        "projects": row[6] or "",
        "dreams": row[7] or "",
        "important_dates": row[8] or "",
        "summary": row[9] or "",
        "premium": row[10] or 0,
        "premium_until": row[11] or "",
        "pets": row[12] or "",
        "family": row[13] or "",
        "profession": row[14] or "",
        "favorite_car": row[15] or "",
        "favorite_color": row[16] or "",
        "favorite_music": row[17] or "",
        "summary_updated_at": row[18] or "",
        "xp": int(row[19] or 0) if len(row) > 19 else 0,
        "level": int(row[20] or 1) if len(row) > 20 else 1,
        "streak_days": int(row[21] or 0) if len(row) > 21 else 0,
        "last_seen_date": (row[22] or "") if len(row) > 22 else "",
    }

    return apply_premium_expiration(user_id, user)


def update_user(user_id, user):
    conn = get_db()
    c = conn.cursor()
    db_execute(c, """
        UPDATE users SET
        name = %s, city = %s, hobbies = %s, facts = %s, timezone = %s,
        goals = %s, projects = %s, dreams = %s, important_dates = %s,
        summary = %s, premium = %s, premium_until = %s, pets = %s,
        family = %s, profession = %s, favorite_car = %s, favorite_color = %s,
        favorite_music = %s, summary_updated_at = %s, xp = %s, level = %s,
        streak_days = %s, last_seen_date = %s
        WHERE user_id = %s
    """, (
        user["name"], user["city"], user["hobbies"], user["facts"], user["timezone"],
        user["goals"], user["projects"], user["dreams"], user["important_dates"], user["summary"],
        user["premium"], user["premium_until"], user["pets"], user["family"], user["profession"],
        user["favorite_car"], user["favorite_color"], user["favorite_music"], user.get("summary_updated_at", ""),
        int(user.get("xp", 0) or 0), int(user.get("level", 1) or 1),
        int(user.get("streak_days", 0) or 0), user.get("last_seen_date", ""),
        user_id
    ))
    conn.commit()
    c.close()
    conn.close()


def apply_premium_expiration(user_id, user):
    """V9.4: automātiski izslēdz Premium, ja premium_until datums ir pagājis."""
    if not user.get("premium"):
        return user

    premium_until = (user.get("premium_until") or "").strip()
    if not premium_until:
        return user

    try:
        until_date = datetime.strptime(premium_until, "%Y-%m-%d").date()
        user_tz = ZoneInfo(user.get("timezone") or DEFAULT_TIMEZONE)
        today = datetime.now(user_tz).date()

        # Premium ir aktīvs līdz norādītās dienas beigām.
        # Nākamajā dienā pēc premium_until tas automātiski izslēdzas.
        if until_date < today:
            user["premium"] = 0
            user["premium_until"] = ""
            update_user(user_id, user)

    except Exception as e:
        print("Premium expiration pārbaudes kļūda:", e)

    return user


def premium_expiration_info(user_id):
    user = get_user(user_id)

    if not user.get("premium"):
        return "Premium šobrīd nav aktīvs."

    if user.get("premium_until"):
        return f"💎 Premium aktīvs līdz {user['premium_until']}."

    return "💎 Premium aktīvs bez beigu datuma."




def plan_price(plan_name):
    if plan_name == PLAN_PREMIUM_PLUS:
        return PREMIUM_PLUS_PRICE
    if plan_name == PLAN_PREMIUM_BASIC:
        return PREMIUM_BASIC_PRICE
    return 0.0


def current_plan_name(user_id):
    user = get_user(user_id)
    if user.get("premium"):
        latest = latest_premium_transaction(user_id)
        if latest and latest.get("plan_name"):
            return latest["plan_name"]
        return PLAN_PREMIUM_BASIC
    return PLAN_FREE


def record_premium_transaction(
    user_id,
    plan_name,
    amount,
    currency,
    payment_method,
    status,
    expires_at="",
    checkout_url="",
    stripe_session_id="",
    stripe_event_id="",
    customer_email="",
):
    try:
        conn = get_db()
        c = conn.cursor()
        db_execute(
            c,
            """
            INSERT INTO premium_transactions
            (user_id, plan_name, amount, currency, payment_method, status, expires_at, checkout_url, stripe_session_id, stripe_event_id, customer_email)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                user_id, plan_name, float(amount or 0), currency, payment_method, status,
                expires_at, checkout_url, stripe_session_id, stripe_event_id, customer_email
            )
        )
        conn.commit()
        c.close()
        conn.close()
    except Exception as e:
        print("Premium transaction kļūda:", e)


def latest_premium_transaction(user_id):
    conn = get_db()
    c = conn.cursor()
    try:
        db_execute(
            c,
            """
            SELECT plan_name, amount, currency, payment_method, status, created_at, expires_at, checkout_url, stripe_session_id
            FROM premium_transactions
            WHERE user_id = %s
            ORDER BY id DESC
            LIMIT 1
            """,
            (user_id,)
        )
        row = c.fetchone()
    except Exception:
        row = None
    c.close()
    conn.close()

    if not row:
        return None

    return {
        "plan_name": row[0] or "",
        "amount": row[1] or 0,
        "currency": row[2] or PREMIUM_CURRENCY,
        "payment_method": row[3] or "",
        "status": row[4] or "",
        "created_at": row[5] or "",
        "expires_at": row[6] or "",
        "checkout_url": row[7] or "",
        "stripe_session_id": row[8] or "",
    }


def subscription_info(user_id=None):
    """V11.5 Requirements Helper — skaidrs abonementa piedāvājums Free lietotājiem."""
    plan = current_plan_name(user_id) if user_id else PLAN_FREE
    user = get_user(user_id) if user_id else {"premium": 0, "premium_until": ""}

    if user.get("premium"):
        until = user.get("premium_until") or "bez beigu datuma"
        return (
            "💎 Tavs Nina Premium ir aktīvs\n\n"
            f"Plāns: {plan}\n"
            f"Aktīvs līdz: {until}\n\n"
            "Tu jau vari izmantot:\n"
            "• backup bez limita\n"
            "• atgādinājumus bez limita\n"
            "• kopsavilkumus bez limita\n"
            "• pilnu Premium Dashboard\n\n"
            "Komandas:\n"
            "premium panelis\n"
            "premium vēsture\n"
            "mans plāns\n\n"
            "Versija: V11.5"
        )

    return (
        "💎 Nina Premium\n\n"
        "Free režīms ir labs izmēģināšanai, bet Premium ir domāts ikdienas lietošanai bez bremzēm.\n\n"
        "Free limiti:\n"
        f"• Backup: līdz {FREE_BACKUP_LIMIT}\n"
        f"• Aktīvie atgādinājumi: līdz {FREE_REMINDER_LIMIT}\n"
        f"• Kopsavilkumi: {FREE_SUMMARY_LIMIT_PER_DAY} dienā\n\n"
        "Premium Basic:\n"
        "• backup bez limita\n"
        "• atgādinājumi bez limita\n"
        "• kopsavilkumi bez limita\n"
        "• vairāk vietas ilgtermiņa atmiņai\n"
        f"💶 {PREMIUM_BASIC_PRICE:.2f} {PREMIUM_CURRENCY}/mēn\n\n"
        "Premium Plus:\n"
        "• viss no Basic\n"
        "• prioritāras nākotnes funkcijas\n"
        "• sagatave WhatsApp un papildu biznesa funkcijām\n"
        f"💶 {PREMIUM_PLUS_PRICE:.2f} {PREMIUM_CURRENCY}/mēn\n\n"
        "Lai sāktu:\n"
        "pirkt basic\n"
        "pirkt plus\n\n"
        "Versija: V11.5"
    )


def premium_conversion_answer(user_id):
    """V11.1: pārdošanas skats komandām premium / aktivizē premium."""
    user = get_user(user_id)
    if user.get("premium"):
        return subscription_info(user_id)

    backups = backup_count_number(user_id)
    reminders = active_reminder_count(user_id)
    summaries_today = summaries_used_today(user_id)

    return (
        "💎 Aktivizē Nina Premium\n\n"
        "Nina Premium noņem Free limitus un ļauj izmantot Ninu kā ikdienas palīgu pilnā režīmā.\n\n"
        "Tavs Free statuss tagad:\n"
        f"📦 Backup: {backups}/{FREE_BACKUP_LIMIT}\n"
        f"⏰ Aktīvie atgādinājumi: {reminders}/{FREE_REMINDER_LIMIT}\n"
        f"🧠 Kopsavilkumi šodien: {summaries_today}/{FREE_SUMMARY_LIMIT_PER_DAY}\n\n"
        "Ko iegūsti ar Premium Basic:\n"
        "✅ backup bez limita\n"
        "✅ atgādinājumi bez limita\n"
        "✅ kopsavilkumi bez limita\n"
        "✅ vairāk vietas ilgtermiņa atmiņai\n"
        f"💶 {PREMIUM_BASIC_PRICE:.2f} {PREMIUM_CURRENCY}/mēn\n\n"
        "Plus plāns dod vēl prioritāras nākotnes funkcijas.\n\n"
        "Izvēlies:\n"
        "pirkt basic\n"
        "pirkt plus\n\n"
        "Versija: V11.5"
    )


def premium_buy_intent_answer(user_id, plan_key="basic"):
    """V11.1: pirms Checkout skaidri pasaka, ko lietotājs pērk."""
    if plan_key == "plus":
        plan_name = PLAN_PREMIUM_PLUS
        amount = PREMIUM_PLUS_PRICE
        benefit = "Plus ir labākais, ja gribi visas Basic funkcijas un prioritāras nākotnes iespējas."
    else:
        plan_name = PLAN_PREMIUM_BASIC
        amount = PREMIUM_BASIC_PRICE
        benefit = "Basic ir labākais starts ikdienas lietošanai bez Free limitiem."

    checkout = stripe_checkout_answer(user_id, plan_key)

    return (
        "💎 Nina Premium Checkout\n\n"
        f"Plāns: {plan_name}\n"
        f"Cena: {amount:.2f} {PREMIUM_CURRENCY}/mēn\n"
        f"{benefit}\n\n"
        "Pēc apmaksas Premium aktivizēsies automātiski, ja Stripe webhook ir pieslēgts.\n\n"
        f"{checkout}\n\n"
        "Versija: V11.5"
    )



def current_plan_answer(user_id):
    plan = current_plan_name(user_id)
    user = get_user(user_id)

    lines = [
        "💎 Tavs plāns",
        "",
        f"Pašreizējais: {plan}",
    ]

    if user.get("premium") and user.get("premium_until"):
        lines.append(f"Beidzas: {user['premium_until']}")

    lines.extend([
        "",
        "Pieejamie plāni:",
        f"🥉 Premium Basic — {PREMIUM_BASIC_PRICE:.2f} {PREMIUM_CURRENCY}/mēn",
        f"🥈 Premium Plus — {PREMIUM_PLUS_PRICE:.2f} {PREMIUM_CURRENCY}/mēn",
        "",
        "Raksti: abonements",
        "Vai: pirkt basic / pirkt plus",
    ])

    return "\n".join(lines)


def premium_history(user_id):
    conn = get_db()
    c = conn.cursor()
    try:
        db_execute(
            c,
            """
            SELECT plan_name, amount, currency, payment_method, status, created_at, expires_at, checkout_url
            FROM premium_transactions
            WHERE user_id = %s
            ORDER BY id DESC
            LIMIT 10
            """,
            (user_id,)
        )
        rows = c.fetchall()
    except Exception:
        rows = []
    c.close()
    conn.close()

    if not rows:
        return "💳 Premium vēsture\n\nNav maksājumu."

    lines = ["💳 Premium vēsture", ""]
    for plan_name, amount, currency, method, status, created_at, expires_at, checkout_url in rows:
        lines.append(str(created_at))
        lines.append(str(plan_name))
        lines.append(f"{float(amount or 0):.2f} {currency or PREMIUM_CURRENCY}")
        lines.append(f"Metode: {method or 'nav'}")
        lines.append(f"Statuss: {status or 'nav'}")
        if expires_at:
            lines.append(f"Beidzas: {expires_at}")
        if checkout_url:
            lines.append("Checkout: izveidots")
        lines.append("")

    return "\n".join(lines).strip()





def admin_user_ids():
    """V10.8.1: stingri nolasa admin Telegram user_id sarakstu tikai no Railway ENV.

    Ja ADMIN_USER_IDS nav uzlikts, admin komandas ir bloķētas visiem.
    Piemērs Railway: ADMIN_USER_IDS=5138563912
    Vairāki admini: ADMIN_USER_IDS=5138563912,123456789
    """
    raw = os.environ.get("ADMIN_USER_IDS", "") or ""
    return {item.strip() for item in raw.split(",") if item.strip()}


def admin_access_configured():
    return bool(admin_user_ids())


def is_admin(user_id):
    return str(user_id) in admin_user_ids()


def admin_locked_answer():
    if not admin_access_configured():
        return (
            "🔒 Admin piekļuve nav konfigurēta.\n\n"
            "Railway ENV pievieno:\n"
            "ADMIN_USER_IDS=5138563912"
        )
    return "🔒 Šī komanda pieejama tikai administratoram."


def log_admin_action(user_id, action, status, command_text=""):
    """V10.9: saglabā admin darbību audita žurnālā."""
    try:
        conn = get_db()
        c = conn.cursor()
        db_execute(
            c,
            """
            INSERT INTO admin_audit_logs (user_id, action, status, command_text)
            VALUES (%s, %s, %s, %s)
            """,
            (str(user_id), action, status, command_text or "")
        )
        conn.commit()
        c.close()
        conn.close()
    except Exception as e:
        print("Admin audit log kļūda:", e)


def admin_audit_log_answer(user_id):
    """V10.9: parāda pēdējās admin darbības tikai administratoram."""
    if not is_admin(user_id):
        log_admin_action(user_id, "audit_log_view", "denied", "admin logs")
        return admin_locked_answer()

    log_admin_action(user_id, "audit_log_view", "allowed", "admin logs")

    conn = get_db()
    c = conn.cursor()
    try:
        db_execute(
            c,
            """
            SELECT created_at, user_id, action, status, command_text
            FROM admin_audit_logs
            ORDER BY id DESC
            LIMIT 20
            """
        )
        rows = c.fetchall()
    except Exception:
        rows = []
    c.close()
    conn.close()

    if not rows:
        return "📋 Admin Audit Log\n\nŽurnāls vēl ir tukšs."

    lines = ["📋 Admin Audit Log", "", "Pēdējās darbības:", ""]
    for created_at, logged_user_id, action, status, command_text in rows:
        lines.append(str(created_at))
        lines.append(f"user_id: {logged_user_id}")
        lines.append(f"action: {action}")
        lines.append(f"status: {status}")
        if command_text:
            lines.append(f"command: {command_text}")
        lines.append("")

    return "\n".join(lines).strip()



def admin_audit_stats_answer(user_id):
    """V10.9.1: Admin Audit Statistics — kopsavilkums par admin darbībām."""
    if not is_admin(user_id):
        log_admin_action(user_id, "audit_stats_view", "denied", "audit stats")
        return admin_locked_answer()

    log_admin_action(user_id, "audit_stats_view", "allowed", "audit stats")

    conn = get_db()
    c = conn.cursor()

    try:
        db_execute(c, "SELECT COUNT(*) FROM admin_audit_logs")
        total = int(c.fetchone()[0] or 0)
    except Exception:
        total = 0

    try:
        db_execute(c, "SELECT COUNT(*) FROM admin_audit_logs WHERE status = 'allowed'")
        allowed = int(c.fetchone()[0] or 0)
    except Exception:
        allowed = 0

    try:
        db_execute(c, "SELECT COUNT(*) FROM admin_audit_logs WHERE status = 'denied'")
        denied = int(c.fetchone()[0] or 0)
    except Exception:
        denied = 0

    action_counts = {}
    try:
        db_execute(c, """
            SELECT action, COUNT(*)
            FROM admin_audit_logs
            GROUP BY action
            ORDER BY COUNT(*) DESC, action ASC
        """)
        for action, count in c.fetchall():
            action_counts[action or "unknown"] = int(count or 0)
    except Exception:
        action_counts = {}

    try:
        db_execute(c, """
            SELECT created_at, user_id, action, status, command_text
            FROM admin_audit_logs
            ORDER BY id DESC
            LIMIT 1
        """)
        last = c.fetchone()
    except Exception:
        last = None

    c.close()
    conn.close()

    lines = [
        "📊 Admin Audit Statistics",
        "",
        f"Kopā admin darbības: {total}",
        f"Atļautas: {allowed}",
        f"Bloķētas: {denied}",
        "",
        "Pēc darbībām:",
    ]

    if action_counts:
        for action, count in action_counts.items():
            lines.append(f"• {action}: {count}")
    else:
        lines.append("• vēl nav datu")

    lines.extend(["", "Pēdējais mēģinājums:"])
    if last:
        created_at, logged_user_id, action, status, command_text = last
        lines.append(str(created_at))
        lines.append(f"user_id: {logged_user_id}")
        lines.append(f"action: {action}")
        lines.append(f"status: {status}")
        if command_text:
            lines.append(f"command: {command_text}")
    else:
        lines.append("nav datu")

    return "\n".join(lines)


def _count_table_rows(table_name, where_sql="", params=None):
    """Drošs skaitītājs System Health panelim."""
    allowed_tables = {"users", "messages", "reminders", "memory_backups", "user_achievements", "admin_audit_logs", "premium_transactions", "backup_restore_logs"}
    if table_name not in allowed_tables:
        return 0
    conn = None
    try:
        conn = get_db()
        c = conn.cursor()
        sql = f"SELECT COUNT(*) FROM {table_name}"
        if where_sql:
            sql += " " + where_sql
        db_execute(c, sql, params or ())
        count = int(c.fetchone()[0] or 0)
        c.close()
        conn.close()
        return count
    except Exception as e:
        print("System health count kļūda:", e)
        try:
            if conn:
                conn.close()
        except Exception:
            pass
        return 0


def _database_health_ok():
    try:
        conn = get_db()
        c = conn.cursor()
        db_execute(c, "SELECT 1")
        c.fetchone()
        c.close()
        conn.close()
        return True
    except Exception as e:
        print("Database health kļūda:", e)
        return False


def system_health_answer(user_id, command_text="health"):
    """V10.10: System Health Dashboard — admin sistēmas monitoringa panelis."""
    if not is_admin(user_id):
        log_admin_action(user_id, "health_view", "denied", command_text)
        return admin_locked_answer()

    log_admin_action(user_id, "health_view", "allowed", command_text)

    db_ok = _database_health_ok()
    telegram_ok = bool(TELEGRAM_TOKEN)
    openai_ok = bool(os.environ.get("OPENAI_API_KEY"))

    secret_ready = bool(STRIPE_SECRET_KEY)
    webhook_ready = bool(STRIPE_WEBHOOK_SECRET)
    checkout_ready = bool(
        STRIPE_BASIC_PRICE_ID or STRIPE_PLUS_PRICE_ID or
        STRIPE_BASIC_CHECKOUT_URL or STRIPE_PLUS_CHECKOUT_URL
    )

    admin_lock_ready = admin_access_configured()
    audit_log_ready = db_ok
    try:
        _count_table_rows("admin_audit_logs")
    except Exception:
        audit_log_ready = False

    users_count = _count_table_rows("users")
    premium_users = _count_table_rows("users", "WHERE premium = 1")
    active_reminders = _count_table_rows("reminders", "WHERE status = %s", ("active",))
    backups_total = _count_table_rows("memory_backups")
    audit_total = _count_table_rows("admin_audit_logs")

    overall_icon = "🟢" if db_ok and telegram_ok and openai_ok else "🟡"

    return (
        f"{overall_icon} Nina System Health\n\n"
        "Core:\n"
        f"Datubāze: {'OK' if db_ok else 'ERROR'}\n"
        f"Telegram: {'OK' if telegram_ok else 'Missing Token'}\n"
        f"OpenAI: {'OK' if openai_ok else 'Missing Key'}\n\n"
        "Maksājumi:\n"
        f"Secret Key: {'✅' if secret_ready else '❌'}\n"
        f"Webhook: {'✅' if webhook_ready else '❌'}\n"
        f"Checkout: {'✅' if checkout_ready else '❌'}\n\n"
        "Drošība:\n"
        f"Admin Lock: {'✅' if admin_lock_ready else '❌'}\n"
        f"Audit Log: {'✅' if audit_log_ready else '❌'}\n\n"
        "Lietošana:\n"
        f"Lietotāji: {users_count}\n"
        f"Premium lietotāji: {premium_users}\n"
        f"Aktīvie atgādinājumi: {active_reminders}\n"
        f"Backup kopā: {backups_total}\n"
        f"Audit ieraksti: {audit_total}\n\n"
        "Versija: V11.5"
    )


def _avg_users_column(column_name):
    """Drošs AVG skaitītājs User Analytics panelim."""
    allowed_columns = {"xp", "level", "streak_days"}
    if column_name not in allowed_columns:
        return 0.0
    conn = None
    try:
        conn = get_db()
        c = conn.cursor()
        db_execute(c, f"SELECT COALESCE(AVG({column_name}), 0) FROM users")
        value = float(c.fetchone()[0] or 0)
        c.close()
        conn.close()
        return value
    except Exception as e:
        print("Analytics AVG kļūda:", e)
        try:
            if conn:
                conn.close()
        except Exception:
            pass
        return 0.0


def user_analytics_answer(user_id, command_text="analytics"):
    """V10.11: User Analytics Dashboard — admin pārskats par lietotājiem un aktivitāti."""
    if not is_admin(user_id):
        log_admin_action(user_id, "analytics_view", "denied", command_text)
        return admin_locked_answer()

    log_admin_action(user_id, "analytics_view", "allowed", command_text)

    users_total = _count_table_rows("users")
    premium_users = _count_table_rows("users", "WHERE premium = 1")
    free_users = max(0, users_total - premium_users)

    messages_total = 0
    conn = None
    try:
        conn = get_db()
        c = conn.cursor()
        db_execute(c, "SELECT COUNT(*) FROM messages")
        messages_total = int(c.fetchone()[0] or 0)
        c.close()
        conn.close()
    except Exception as e:
        print("Analytics messages count kļūda:", e)
        try:
            if conn:
                conn.close()
        except Exception:
            pass
        messages_total = 0

    backups_total = _count_table_rows("memory_backups")
    reminders_total = _count_table_rows("reminders")
    active_reminders = _count_table_rows("reminders", "WHERE status = %s", ("active",))

    avg_xp = _avg_users_column("xp")
    avg_level = _avg_users_column("level")
    avg_streak = _avg_users_column("streak_days")

    return (
        "📊 Nina User Analytics\n\n"
        f"Lietotāji kopā: {users_total}\n"
        f"Premium lietotāji: {premium_users}\n"
        f"Free lietotāji: {free_users}\n\n"
        "Aktivitāte:\n"
        f"Ziņas kopā: {messages_total}\n"
        f"Backup kopā: {backups_total}\n"
        f"Atgādinājumi kopā: {reminders_total}\n"
        f"Aktīvie atgādinājumi: {active_reminders}\n\n"
        "Lojalitāte:\n"
        f"Vidējais XP: {avg_xp:.1f}\n"
        f"Vidējais līmenis: {avg_level:.1f}\n"
        f"Vidējais streak: {avg_streak:.1f}\n\n"
        "Versija: V11.5"
    )


def _latest_created_at(table_name, created_col="created_at"):
    """Atrod pēdējo ieraksta laiku drošām DB Backup Dashboard tabulām."""
    allowed_tables = {"messages", "reminders", "memory_backups", "user_achievements", "premium_transactions", "admin_audit_logs"}
    allowed_cols = {"created_at", "unlocked_at"}
    if table_name not in allowed_tables or created_col not in allowed_cols:
        return "nav datu"
    conn = None
    try:
        conn = get_db()
        c = conn.cursor()
        db_execute(c, f"SELECT MAX({created_col}) FROM {table_name}")
        value = c.fetchone()[0]
        c.close()
        conn.close()
        return str(value) if value else "nav datu"
    except Exception as e:
        print("DB backup latest kļūda:", e)
        try:
            if conn:
                conn.close()
        except Exception:
            pass
        return "nav datu"


def database_backup_dashboard(user_id, command_text="db backup"):
    """V10.12: Database Backup Dashboard — admin DB satura un backup statusa pārskats."""
    if not is_admin(user_id):
        log_admin_action(user_id, "database_backup_view", "denied", command_text)
        return admin_locked_answer()

    log_admin_action(user_id, "database_backup_view", "allowed", command_text)

    db_ok = _database_health_ok()
    db_type = "PostgreSQL" if USE_POSTGRES else "SQLite"

    users_total = _count_table_rows("users")
    messages_total = _count_table_rows("messages")
    reminders_total = _count_table_rows("reminders")
    active_reminders = _count_table_rows("reminders", "WHERE status = %s", ("active",))
    backups_total = _count_table_rows("memory_backups")
    achievements_total = _count_table_rows("user_achievements")
    premium_transactions_total = _count_table_rows("premium_transactions")
    audit_total = _count_table_rows("admin_audit_logs")

    latest_backup = _latest_created_at("memory_backups")
    latest_message = _latest_created_at("messages")
    latest_audit = _latest_created_at("admin_audit_logs")

    return (
        "🗄️ Nina Database Backup\n\n"
        "Datubāze:\n"
        f"Tips: {db_type}\n"
        f"Statuss: {'OK' if db_ok else 'ERROR'}\n\n"
        "Saturs:\n"
        f"👤 Lietotāji: {users_total}\n"
        f"💬 Ziņas: {messages_total}\n"
        f"⏰ Atgādinājumi: {reminders_total}\n"
        f"✅ Aktīvie atgādinājumi: {active_reminders}\n"
        f"📦 Backup ieraksti: {backups_total}\n"
        f"🏅 Sasniegumi: {achievements_total}\n"
        f"💎 Premium darījumi: {premium_transactions_total}\n\n"
        "Audit:\n"
        f"📋 Audit ieraksti: {audit_total}\n\n"
        "Pēdējie ieraksti:\n"
        f"Pēdējais backup: {latest_backup}\n"
        f"Pēdējā ziņa: {latest_message}\n"
        f"Pēdējais audit: {latest_audit}\n\n"
        "Versija: V11.5"
    )



def _riga_now_text():
    return datetime.now(ZoneInfo(DEFAULT_TIMEZONE)).strftime("%Y-%m-%d %H:%M")


def _riga_next_daily_text(hour=22, minute=0):
    now = datetime.now(ZoneInfo(DEFAULT_TIMEZONE))
    next_run = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
    if next_run <= now:
        next_run = next_run + timedelta(days=1)
    return next_run.strftime("%Y-%m-%d %H:%M")


def init_backup_scheduler():
    """V10.14: izveido noklusēto backup scheduler ierakstu, ja tā vēl nav."""
    try:
        conn = get_db()
        c = conn.cursor()
        db_execute(c, "SELECT COUNT(*) FROM backup_scheduler")
        count = int(c.fetchone()[0] or 0)
        if count == 0:
            db_execute(
                c,
                """
                INSERT INTO backup_scheduler (enabled, frequency, last_run, next_run, total_runs)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (1, "daily", "", _riga_next_daily_text(), 0)
            )
            conn.commit()
        c.close()
        conn.close()
    except Exception as e:
        print("Backup scheduler init kļūda:", e)


def get_backup_scheduler_state():
    init_backup_scheduler()
    conn = get_db()
    c = conn.cursor()
    try:
        db_execute(c, """
            SELECT enabled, frequency, last_run, next_run, total_runs
            FROM backup_scheduler
            ORDER BY id ASC
            LIMIT 1
        """)
        row = c.fetchone()
    except Exception:
        row = None
    c.close()
    conn.close()

    if not row:
        return {"enabled": 0, "frequency": "daily", "last_run": "", "next_run": "", "total_runs": 0}

    return {
        "enabled": int(row[0] or 0),
        "frequency": row[1] or "daily",
        "last_run": row[2] or "",
        "next_run": row[3] or "",
        "total_runs": int(row[4] or 0),
    }


def update_backup_scheduler_state(last_run, next_run, total_runs):
    try:
        conn = get_db()
        c = conn.cursor()
        db_execute(
            c,
            """
            UPDATE backup_scheduler
            SET last_run = %s, next_run = %s, total_runs = %s
            WHERE id = (SELECT id FROM backup_scheduler ORDER BY id ASC LIMIT 1)
            """,
            (last_run, next_run, int(total_runs or 0))
        )
        conn.commit()
        c.close()
        conn.close()
    except Exception as e:
        print("Backup scheduler update kļūda:", e)


def build_system_backup_text():
    db_type = "PostgreSQL" if USE_POSTGRES else "SQLite"
    exported_at = _riga_now_text()
    data = {
        "exported_at": exported_at,
        "type": "system_database_backup",
        "version": "V10.15",
        "database": db_type,
        "counts": {
            "users": _count_table_rows("users"),
            "messages": _count_table_rows("messages"),
            "reminders": _count_table_rows("reminders"),
            "active_reminders": _count_table_rows("reminders", "WHERE status = %s", ("active",)),
            "memory_backups": _count_table_rows("memory_backups"),
            "user_achievements": _count_table_rows("user_achievements"),
            "premium_transactions": _count_table_rows("premium_transactions"),
            "admin_audit_logs": _count_table_rows("admin_audit_logs"),
        }
    }
    return (
        "NINA SYSTEM DATABASE BACKUP\n"
        f"Laiks: {exported_at} ({DEFAULT_TIMEZONE})\n"
        f"Datubāze: {db_type}\n"
        "Versija: V10.15\n\n"
        "JSON kopija:\n" + json.dumps(data, ensure_ascii=False, indent=2)
    )


def save_system_database_backup(source="auto_system"):
    backup_text = build_system_backup_text()
    conn = get_db()
    c = conn.cursor()
    try:
        if USE_POSTGRES:
            db_execute(
                c,
                "INSERT INTO memory_backups (user_id, backup_text, source) VALUES (%s, %s, %s) RETURNING id",
                ("__system__", backup_text, source)
            )
            backup_id = c.fetchone()[0]
        else:
            db_execute(
                c,
                "INSERT INTO memory_backups (user_id, backup_text, source) VALUES (%s, %s, %s)",
                ("__system__", backup_text, source)
            )
            backup_id = c.lastrowid
        conn.commit()
    finally:
        c.close()
        conn.close()
    return backup_id, backup_text


def run_auto_backup(force=False):
    """V10.14: palaiž auto backup, ja pienācis next_run vai ja force=True."""
    init_backup_scheduler()
    state = get_backup_scheduler_state()
    if not state.get("enabled"):
        return False, "disabled"

    now_text = _riga_now_text()
    next_run = state.get("next_run") or _riga_next_daily_text()
    if not force and next_run and now_text < next_run:
        return False, "not_due"

    try:
        backup_id, _ = save_system_database_backup("auto_system")
        total_runs = int(state.get("total_runs", 0) or 0) + 1
        new_next = _riga_next_daily_text()
        update_backup_scheduler_state(now_text, new_next, total_runs)
        log_admin_action("system", "auto_backup_run", "success", f"backup_id={backup_id}")
        return True, f"backup_id={backup_id}"
    except Exception as e:
        log_admin_action("system", "auto_backup_run", "failed", str(e))
        print("Auto backup kļūda:", e)
        return False, "failed"


def latest_auto_backup_time():
    conn = get_db()
    c = conn.cursor()
    try:
        db_execute(c, """
            SELECT MAX(created_at)
            FROM memory_backups
            WHERE source = %s
        """, ("auto_system",))
        value = c.fetchone()[0]
    except Exception:
        value = None
    c.close()
    conn.close()
    return str(value) if value else "nav datu"


def auto_backup_count():
    conn = get_db()
    c = conn.cursor()
    try:
        db_execute(c, "SELECT COUNT(*) FROM memory_backups WHERE source = %s", ("auto_system",))
        count = int(c.fetchone()[0] or 0)
    except Exception:
        count = 0
    c.close()
    conn.close()
    return count


def backup_scheduler_answer(user_id, command_text="auto backup"):
    """V10.14: Automated Backup Scheduler panelis."""
    if not is_admin(user_id):
        log_admin_action(user_id, "backup_scheduler_view", "denied", command_text)
        return admin_locked_answer()

    log_admin_action(user_id, "backup_scheduler_view", "allowed", command_text)
    state = get_backup_scheduler_state()
    status = "Aktīvs" if state.get("enabled") else "Izslēgts"
    frequency = (state.get("frequency") or "daily").capitalize()
    last_run = state.get("last_run") or latest_auto_backup_time()
    next_run = state.get("next_run") or _riga_next_daily_text()
    total_runs = int(state.get("total_runs", 0) or 0)
    auto_count = auto_backup_count()

    return (
        "🗄️ Nina Backup Scheduler\n\n"
        f"Statuss: {status}\n"
        f"Frekvence: {frequency}\n"
        f"Laiks: 22:00 ({DEFAULT_TIMEZONE})\n\n"
        "Pēdējais auto backup:\n"
        f"{last_run or 'nav datu'}\n\n"
        "Nākamais auto backup:\n"
        f"{next_run}\n\n"
        "Kopā auto backup:\n"
        f"{max(total_runs, auto_count)}\n\n"
        "Audit action:\n"
        "auto_backup_run\n\n"
        "Versija: V11.5"
    )


def log_restore_action(user_id, backup_id, status):
    """V10.14: saglabā recovery darbību atsevišķā restore žurnālā."""
    try:
        conn = get_db()
        c = conn.cursor()
        db_execute(
            c,
            """
            INSERT INTO backup_restore_logs (user_id, backup_id, status)
            VALUES (%s, %s, %s)
            """,
            (str(user_id), str(backup_id or ""), status or "")
        )
        conn.commit()
        c.close()
        conn.close()
    except Exception as e:
        print("Backup restore log kļūda:", e)


def latest_recovery_backups(limit=5):
    """V10.14: atgriež pēdējos backup ierakstus Recovery Center panelim."""
    conn = get_db()
    c = conn.cursor()
    try:
        db_execute(
            c,
            """
            SELECT id, user_id, source, created_at
            FROM memory_backups
            ORDER BY id DESC
            LIMIT %s
            """,
            (int(limit or 5),)
        )
        rows = c.fetchall()
    except Exception:
        rows = []
    c.close()
    conn.close()
    return rows


def latest_user_backup_id(user_id):
    """V10.14: pēdējais konkrētā lietotāja profila backup."""
    conn = get_db()
    c = conn.cursor()
    try:
        db_execute(
            c,
            """
            SELECT id
            FROM memory_backups
            WHERE user_id = %s
            ORDER BY id DESC
            LIMIT 1
            """,
            (str(user_id),)
        )
        row = c.fetchone()
    except Exception:
        row = None
    c.close()
    conn.close()
    return int(row[0]) if row else None


def recovery_center_answer(user_id, command_text="recovery"):
    """V10.14: Recovery Center — pārskats par backup un restore iespējām."""
    if not is_admin(user_id):
        log_admin_action(user_id, "recovery_center_view", "denied", command_text)
        return admin_locked_answer()

    log_admin_action(user_id, "recovery_center_view", "allowed", command_text)
    rows = latest_recovery_backups(5)
    restore_logs = _count_table_rows("backup_restore_logs")

    lines = [
        "🛟 Nina Recovery Center",
        "",
        "Pēdējie backup:",
        "",
    ]

    if rows:
        for idx, (bid, backup_user_id, source, created_at) in enumerate(rows, start=1):
            lines.append(f"{idx}. #{bid} — {created_at} ({source or 'manual'}, user: {backup_user_id or 'unknown'})")
    else:
        lines.append("Nav backup ierakstu.")

    lines.extend([
        "",
        "Pieejamās darbības:",
        "• backup stats",
        "• auto backup",
        "• restore latest",
        "",
        "Atjaunošana:",
        "restore latest atjauno pēdējo tava profila backup.",
        "Sistēmas auto backup šobrīd ir drošības eksports/statistika, nevis pilns DB dump.",
        "",
        f"Restore mēģinājumi: {restore_logs}",
        "Statuss: Ready",
        "Versija: V11.5",
    ])

    return "\n".join(lines)


def restore_latest_backup(user_id, command_text="restore latest"):
    """V10.14: atjauno pēdējo admina profila backup."""
    if not is_admin(user_id):
        log_admin_action(user_id, "backup_restore_attempt", "denied", command_text)
        return admin_locked_answer()

    log_admin_action(user_id, "backup_restore_attempt", "started", command_text)
    backup_id = latest_user_backup_id(user_id)

    if not backup_id:
        log_restore_action(user_id, "", "failed_no_backup")
        log_admin_action(user_id, "backup_restore_failed", "failed", "no_user_backup")
        return (
            "🛟 Nina Recovery Center\n\n"
            "Atjaunošana neizdevās.\n\n"
            "Nav atrasts tavs profila backup.\n"
            "Vispirms izveido backup."
        )

    result = restore_backup(user_id, f"atjauno no backup {backup_id}")
    if result.startswith("✅"):
        log_restore_action(user_id, backup_id, "success")
        log_admin_action(user_id, "backup_restore_success", "success", f"backup_id={backup_id}")
        return (
            "🛟 Nina Recovery Center\n\n"
            f"{result}\n\n"
            f"Backup ID: #{backup_id}\n"
            "Statuss: Restored\n"
            "Versija: V11.5"
        )

    log_restore_action(user_id, backup_id, "failed")
    log_admin_action(user_id, "backup_restore_failed", "failed", f"backup_id={backup_id}")
    return (
        "🛟 Nina Recovery Center\n\n"
        "Atjaunošana neizdevās.\n\n"
        f"Backup ID: #{backup_id}\n"
        f"Iemesls: {result}\n\n"
        "Statuss: Failed"
    )



def admin_command_center(user_id, command_text="admin"):
    """V10.15: Admin Command Center — centrālais admin paneļu saraksts."""
    if not is_admin(user_id):
        log_admin_action(user_id, "admin_center_view", "denied", command_text)
        return admin_locked_answer()

    log_admin_action(user_id, "admin_center_view", "allowed", command_text)

    admin_lock_status = "Aktīvs" if admin_access_configured() else "Nav konfigurēts"
    audit_status = "Aktīvs" if _database_health_ok() else "Nav pieejams"

    return (
        "🛠️ Nina Admin Command Center\n\n"
        "Galvenie paneļi:\n\n"
        "💰 Revenue\n"
        "Komanda: revenue\n\n"
        "📊 Analytics\n"
        "Komanda: analytics\n\n"
        "🟢 System Health\n"
        "Komanda: health\n\n"
        "📋 Audit Logs\n"
        "Komanda: admin logs\n\n"
        "📈 Audit Statistics\n"
        "Komanda: audit stats\n\n"
        "🗄️ Database Backup\n"
        "Komanda: db backup\n\n"
        "⏰ Backup Scheduler\n"
        "Komanda: auto backup\n\n"
        "🛟 Recovery Center\n"
        "Komanda: recovery\n\n"
        "Drošība:\n"
        f"🔒 Admin Lock: {admin_lock_status}\n"
        f"📋 Audit Log: {audit_status}\n\n"
        "Versija: V11.5"
    )


def admin_notifications_center(user_id, command_text="notifications"):
    """V10.16: Admin Notifications Center — svarīgākie brīdinājumi vienā vietā."""
    if not is_admin(user_id):
        log_admin_action(user_id, "admin_notifications_view", "denied", command_text)
        return admin_locked_answer()

    log_admin_action(user_id, "admin_notifications_view", "allowed", command_text)

    conn = None

    def count_audit(where_sql="", params=()):
        nonlocal conn
        try:
            if conn is None:
                conn = get_db()
            c = conn.cursor()
            sql = "SELECT COUNT(*) FROM admin_audit_logs"
            if where_sql:
                sql += " " + where_sql
            db_execute(c, sql, params)
            value = int(c.fetchone()[0] or 0)
            c.close()
            return value
        except Exception as e:
            print("Admin notifications audit count kļūda:", e)
            return 0

    def count_premium_errors():
        try:
            local_conn = get_db()
            c = local_conn.cursor()
            db_execute(c, """
                SELECT COUNT(*)
                FROM premium_transactions
                WHERE status IN ('payment_failed', 'checkout_error', 'stripe_checkout_error', 'failed')
            """)
            value = int(c.fetchone()[0] or 0)
            c.close()
            local_conn.close()
            return value
        except Exception as e:
            print("Admin notifications payment count kļūda:", e)
            return 0

    denied_admin = count_audit("WHERE status = %s", ("denied",))
    auto_backup_errors = count_audit(
        "WHERE action = %s AND status IN (%s, %s)",
        ("auto_backup_run", "failed", "error")
    )
    restore_errors = count_audit(
        "WHERE action IN (%s, %s) OR command_text = %s",
        ("backup_restore_failed", "backup_restore_attempt", "no_user_backup")
    )
    payment_errors = count_premium_errors()

    try:
        if conn:
            conn.close()
    except Exception:
        pass

    total_alerts = denied_admin + auto_backup_errors + restore_errors + payment_errors
    status = "OK" if total_alerts == 0 else "Jāpārbauda"
    icon = "🟢" if total_alerts == 0 else "🟡"

    return (
        "🔔 Nina Admin Notifications\n\n"
        "Jauni notikumi:\n"
        f"• Bloķēti admin mēģinājumi: {denied_admin}\n"
        f"• Auto backup kļūdas: {auto_backup_errors}\n"
        f"• Restore kļūdas: {restore_errors}\n"
        f"• Maksājumu kļūdas: {payment_errors}\n\n"
        f"Statuss: {icon} {status}\n"
        "Versija: V11.5"
    )


def admin_activity_feed(user_id, command_text="activity", limit=10):
    """V10.24: Admin Activity Feed — pēdējās admin/audit darbības vienā plūsmā."""
    if not is_admin(user_id):
        log_admin_action(user_id, "activity_feed_view", "denied", command_text)
        return admin_locked_answer()

    log_admin_action(user_id, "activity_feed_view", "allowed", command_text)

    conn = get_db()
    c = conn.cursor()
    try:
        db_execute(
            c,
            """
            SELECT created_at, user_id, action, status, command_text
            FROM admin_audit_logs
            ORDER BY id DESC
            LIMIT %s
            """,
            (int(limit or 10),)
        )
        rows = c.fetchall()
    except Exception as e:
        print("Activity feed kļūda:", e)
        rows = []

    try:
        db_execute(c, "SELECT COUNT(*) FROM admin_audit_logs")
        total = int(c.fetchone()[0] or 0)
    except Exception:
        total = len(rows)

    c.close()
    conn.close()

    lines = [
        "📋 Nina Activity Feed",
        "",
        "Pēdējās darbības:",
        "",
    ]

    if rows:
        for created_at, logged_user_id, action, status, cmd in rows:
            status_text = (status or "unknown").upper()
            lines.append(str(created_at))
            lines.append(str(action or "unknown"))
            lines.append(status_text)
            lines.append(f"user_id: {logged_user_id}")
            if cmd:
                lines.append(f"command: {cmd}")
            lines.append("")
    else:
        lines.append("Nav audit ierakstu.")
        lines.append("")

    lines.extend([
        f"Kopā ieraksti: {total}",
        "",
        "Versija: V11.5",
    ])

    return "\n".join(lines).strip()


def _admin_extract_target_user_id(command_text):
    """V10.24: mēģina izvilkt Telegram user_id no admin lookup komandas."""
    text = (command_text or "").strip()
    # Atbalsta: user 123, user lookup 123, lietotājs 123, meklēt lietotāju 123
    match = re.search(r"\b(\d{4,})\b", text)
    if match:
        return match.group(1)
    return ""


def _fetch_user_row_for_admin(target_user_id):
    """V10.24: nolasa lietotāju bez jauna profila automātiskas izveides."""
    conn = get_db()
    c = conn.cursor()
    try:
        db_execute(c, """
            SELECT name, city, hobbies, facts, timezone, goals, projects, dreams,
                   important_dates, summary, premium, premium_until, pets, family,
                   profession, favorite_car, favorite_color, favorite_music,
                   summary_updated_at, xp, level, streak_days, last_seen_date
            FROM users WHERE user_id = %s
        """, (str(target_user_id),))
        row = c.fetchone()
    except Exception as e:
        print("Admin user lookup fetch kļūda:", e)
        row = None
    c.close()
    conn.close()

    if not row:
        return None

    return {
        "name": row[0] or "",
        "city": row[1] or "",
        "hobbies": row[2] or "",
        "facts": row[3] or "",
        "timezone": row[4] or DEFAULT_TIMEZONE,
        "goals": row[5] or "",
        "projects": row[6] or "",
        "dreams": row[7] or "",
        "important_dates": row[8] or "",
        "summary": row[9] or "",
        "premium": row[10] or 0,
        "premium_until": row[11] or "",
        "pets": row[12] or "",
        "family": row[13] or "",
        "profession": row[14] or "",
        "favorite_car": row[15] or "",
        "favorite_color": row[16] or "",
        "favorite_music": row[17] or "",
        "summary_updated_at": row[18] or "",
        "xp": int(row[19] or 0) if len(row) > 19 else 0,
        "level": int(row[20] or 1) if len(row) > 20 else 1,
        "streak_days": int(row[21] or 0) if len(row) > 21 else 0,
        "last_seen_date": (row[22] or "") if len(row) > 22 else "",
    }


def admin_user_lookup(user_id, command_text="user lookup"):
    """V10.24: Admin User Lookup — konkrēta lietotāja profils, lojalitāte un aktivitāte."""
    if not is_admin(user_id):
        log_admin_action(user_id, "user_lookup_view", "denied", command_text)
        return admin_locked_answer()

    target_user_id = _admin_extract_target_user_id(command_text)
    if not target_user_id:
        log_admin_action(user_id, "user_lookup_view", "allowed", command_text)
        return (
            "👤 Nina User Lookup\n\n"
            "Norādi lietotāja ID.\n\n"
            "Piemērs:\n"
            "user 5138563912\n\n"
            "Versija: V11.5"
        )

    log_admin_action(user_id, "user_lookup_view", "allowed", command_text)
    target = _fetch_user_row_for_admin(target_user_id)

    if not target:
        return (
            "👤 Nina User Lookup\n\n"
            f"User ID: {target_user_id}\n"
            "Statuss: nav atrasts\n\n"
            "Šāds lietotājs vēl nav Nina datubāzē.\n\n"
            "Versija: V11.5"
        )

    messages_total = _count_table_rows("messages", "WHERE user_id = %s", (str(target_user_id),))
    backups_total = _count_table_rows("memory_backups", "WHERE user_id = %s", (str(target_user_id),))
    reminders_total = _count_table_rows("reminders", "WHERE user_id = %s", (str(target_user_id),))
    active_reminders = _count_table_rows("reminders", "WHERE user_id = %s AND status = %s", (str(target_user_id), "active"))
    achievements_total = _count_table_rows("user_achievements", "WHERE user_id = %s", (str(target_user_id),))
    premium_transactions_total = _count_table_rows("premium_transactions", "WHERE user_id = %s", (str(target_user_id),))

    premium_status_text = "Premium" if target.get("premium") else "Free"
    plan = PLAN_FREE
    if target.get("premium"):
        latest = latest_premium_transaction(str(target_user_id))
        plan = latest.get("plan_name") if latest and latest.get("plan_name") else PLAN_PREMIUM_BASIC

    return (
        "👤 Nina User Lookup\n\n"
        f"User ID: {target_user_id}\n"
        f"Vārds: {target.get('name') or '—'}\n"
        f"Pilsēta: {target.get('city') or '—'}\n"
        f"Laika zona: {target.get('timezone') or DEFAULT_TIMEZONE}\n"
        f"Pēdējā aktivitāte: {target.get('last_seen_date') or '—'}\n\n"
        "Premium:\n"
        f"Statuss: {premium_status_text}\n"
        f"Plāns: {plan}\n"
        f"Premium līdz: {target.get('premium_until') or '—'}\n"
        f"Premium darījumi: {premium_transactions_total}\n\n"
        "Lojalitāte:\n"
        f"XP: {target.get('xp', 0)}\n"
        f"Līmenis: {target.get('level', 1)}\n"
        f"Streak: {target.get('streak_days', 0)}\n"
        f"Sasniegumi: {achievements_total}\n\n"
        "Aktivitāte:\n"
        f"Ziņas: {messages_total}\n"
        f"Backup: {backups_total}\n"
        f"Atgādinājumi: {reminders_total}\n"
        f"Aktīvie atgādinājumi: {active_reminders}\n\n"
        "Versija: V11.5"
    )


def admin_user_search(user_id, command_text="search user"):
    """V10.24: Admin User Search — meklē lietotājus pēc user_id, vārda, premium/free, xp/level."""
    if not is_admin(user_id):
        log_admin_action(user_id, "user_search_view", "denied", command_text)
        return admin_locked_answer()

    log_admin_action(user_id, "user_search_view", "allowed", command_text)

    text = (command_text or "").strip().lower()
    query = text

    prefixes = [
        "search user",
        "find user",
        "meklēt lietotāju",
        "meklet lietotaju",
        "lietotāji",
        "lietotaji",
    ]

    for prefix in prefixes:
        if query.startswith(prefix):
            query = query.replace(prefix, "", 1).strip()
            break

    # Ja raksta tikai "lietotāji", rādām jaunākos/visus lietotājus.
    if query in ["all", "visi", "visus"]:
        query = ""

    conn = get_db()
    c = conn.cursor()
    rows = []

    try:
        if query in ["premium", "premium users", "premium lietotāji", "premium lietotaji"]:
            db_execute(c, """
                SELECT user_id, name, premium, premium_until, xp, level, streak_days
                FROM users
                WHERE premium = 1
                ORDER BY xp DESC, user_id ASC
                LIMIT 20
            """)

        elif query in ["free", "free users", "bezmaksas"]:
            db_execute(c, """
                SELECT user_id, name, premium, premium_until, xp, level, streak_days
                FROM users
                WHERE premium = 0
                ORDER BY xp DESC, user_id ASC
                LIMIT 20
            """)

        elif query in ["xp", "top xp", "pieredze"]:
            db_execute(c, """
                SELECT user_id, name, premium, premium_until, xp, level, streak_days
                FROM users
                ORDER BY xp DESC, user_id ASC
                LIMIT 20
            """)

        elif query in ["level", "top level", "līmenis", "limenis"]:
            db_execute(c, """
                SELECT user_id, name, premium, premium_until, xp, level, streak_days
                FROM users
                ORDER BY level DESC, xp DESC, user_id ASC
                LIMIT 20
            """)

        elif query:
            like = f"%{query}%"
            db_execute(c, """
                SELECT user_id, name, premium, premium_until, xp, level, streak_days
                FROM users
                WHERE user_id LIKE %s OR LOWER(name) LIKE %s
                ORDER BY xp DESC, user_id ASC
                LIMIT 20
            """, (like, like))

        else:
            db_execute(c, """
                SELECT user_id, name, premium, premium_until, xp, level, streak_days
                FROM users
                ORDER BY user_id ASC
                LIMIT 20
            """)

        rows = c.fetchall()

    except Exception as e:
        print("Admin user search kļūda:", e)
        rows = []

    c.close()
    conn.close()

    lines = [
        "👥 Nina User Search",
        "",
        f"Atrasti: {len(rows)}",
        "",
    ]

    if not rows:
        lines.extend([
            "Nav atrastu lietotāju.",
            "",
            "Piemēri:",
            "search user premium",
            "search user free",
            "search user xp",
            "find user 5138563912",
            "lietotāji",
            "",
            "Versija: V11.5",
        ])
        return "\n".join(lines)

    for idx, row in enumerate(rows, start=1):
        found_user_id, name, premium, premium_until, xp, level, streak_days = row

        status = "Premium" if premium else "Free"
        if premium and premium_until:
            status += f" līdz {premium_until}"

        lines.append(f"{idx}. {found_user_id}")
        lines.append(f"Vārds: {name or '—'}")
        lines.append(f"Statuss: {status}")
        lines.append(f"XP: {int(xp or 0)}")
        lines.append(f"Līmenis: {int(level or 1)}")
        lines.append(f"Streak: {int(streak_days or 0)}")
        lines.append("")

    lines.append("Versija: V11.5")
    return "\n".join(lines).strip()


def _admin_extract_action_numbers(command_text):
    """V10.24: izvelk skaitļus no admin darbības komandas."""
    return re.findall(r"\b\d+\b", command_text or "")


def admin_user_actions_help(user_id, command_text="user actions"):
    """V10.24: Admin User Actions palīdzības panelis."""
    if not is_admin(user_id):
        log_admin_action(user_id, "user_actions_help", "denied", command_text)
        return admin_locked_answer()

    log_admin_action(user_id, "user_actions_help", "allowed", command_text)
    return (
        "🧰 Nina Admin User Actions\n\n"
        "Pieejamās darbības:\n\n"
        "grant premium 5138563912\n"
        "Piešķir Premium uz 30 dienām.\n\n"
        "remove premium 5138563912\n"
        "Noņem Premium statusu.\n\n"
        "add xp 5138563912 100\n"
        "Pievieno XP lietotājam.\n\n"
        "remove xp 5138563912 50\n"
        "Noņem XP lietotājam.\n\n"
        "set level 5138563912 5\n"
        "Uzstāda līmeni un pielāgo XP.\n\n"
        "reset streak 5138563912\n"
        "Nodzēš lietotāja streak.\n\n"
        "Drošība:\n"
        "Visas darbības ir tikai administratoram un tiek ierakstītas Audit Log.\n\n"
        "Versija: V11.5"
    )


def admin_user_action(user_id, command_text="user actions"):
    """V10.24: Admin User Actions — Premium, XP, level un streak darbības."""
    lower = (command_text or "").strip().lower()

    if lower == "user actions":
        return admin_user_actions_help(user_id, command_text)

    if not is_admin(user_id):
        log_admin_action(user_id, "user_action_execute", "denied", command_text)
        return admin_locked_answer()

    numbers = _admin_extract_action_numbers(command_text)
    if not numbers:
        log_admin_action(user_id, "user_action_execute", "failed_missing_user_id", command_text)
        return (
            "🧰 Nina Admin User Actions\n\n"
            "Trūkst lietotāja ID.\n\n"
            "Piemērs:\n"
            "grant premium 5138563912\n\n"
            "Versija: V11.5"
        )

    target_user_id = numbers[0]
    target = _fetch_user_row_for_admin(target_user_id)
    if not target:
        log_admin_action(user_id, "user_action_execute", "failed_user_not_found", command_text)
        return (
            "🧰 Nina Admin User Actions\n\n"
            f"User ID: {target_user_id}\n"
            "Statuss: nav atrasts\n\n"
            "Šāds lietotājs vēl nav Nina datubāzē.\n\n"
            "Versija: V11.5"
        )

    try:
        action_name = "unknown"
        result_text = ""

        if lower.startswith("grant premium"):
            until = (datetime.now(ZoneInfo(target.get("timezone") or DEFAULT_TIMEZONE)) + timedelta(days=30)).strftime("%Y-%m-%d")
            target["premium"] = 1
            target["premium_until"] = until
            update_user(str(target_user_id), target)
            record_premium_transaction(
                user_id=str(target_user_id),
                plan_name=PLAN_PREMIUM_BASIC,
                amount=0,
                currency=PREMIUM_CURRENCY,
                payment_method="admin",
                status="admin_granted",
                expires_at=until,
            )
            action_name = "grant_premium"
            result_text = f"Premium piešķirts līdz {until}."

        elif lower.startswith("remove premium"):
            target["premium"] = 0
            target["premium_until"] = ""
            update_user(str(target_user_id), target)
            record_premium_transaction(
                user_id=str(target_user_id),
                plan_name=PLAN_FREE,
                amount=0,
                currency=PREMIUM_CURRENCY,
                payment_method="admin",
                status="admin_removed",
                expires_at="",
            )
            action_name = "remove_premium"
            result_text = "Premium noņemts."

        elif lower.startswith("add xp"):
            if len(numbers) < 2:
                return "🧰 Nina Admin User Actions\n\nTrūkst XP daudzuma.\n\nPiemērs:\nadd xp 5138563912 100\n\nVersija: V11.5"
            amount = max(0, int(numbers[1]))
            new_xp = int(target.get("xp", 0) or 0) + amount
            target["xp"] = new_xp
            target["level"] = calculate_level(new_xp)
            update_user(str(target_user_id), target)
            action_name = "add_xp"
            result_text = f"Pievienots {amount} XP. Jaunais XP: {new_xp}. Līmenis: {target['level']}."

        elif lower.startswith("remove xp"):
            if len(numbers) < 2:
                return "🧰 Nina Admin User Actions\n\nTrūkst XP daudzuma.\n\nPiemērs:\nremove xp 5138563912 50\n\nVersija: V11.5"
            amount = max(0, int(numbers[1]))
            new_xp = max(0, int(target.get("xp", 0) or 0) - amount)
            target["xp"] = new_xp
            target["level"] = calculate_level(new_xp)
            update_user(str(target_user_id), target)
            action_name = "remove_xp"
            result_text = f"Noņemts {amount} XP. Jaunais XP: {new_xp}. Līmenis: {target['level']}."

        elif lower.startswith("set level"):
            if len(numbers) < 2:
                return "🧰 Nina Admin User Actions\n\nTrūkst līmeņa.\n\nPiemērs:\nset level 5138563912 5\n\nVersija: V11.5"
            new_level = max(1, int(numbers[1]))
            new_xp = (new_level - 1) * XP_PER_LEVEL
            target["level"] = new_level
            target["xp"] = new_xp
            update_user(str(target_user_id), target)
            action_name = "set_level"
            result_text = f"Līmenis uzstādīts uz {new_level}. XP pielāgots uz {new_xp}."

        elif lower.startswith("reset streak"):
            target["streak_days"] = 0
            target["last_seen_date"] = ""
            update_user(str(target_user_id), target)
            action_name = "reset_streak"
            result_text = "Streak atiestatīts uz 0."

        else:
            log_admin_action(user_id, "user_action_execute", "failed_unknown_action", command_text)
            return "🧰 Nina Admin User Actions\n\nDarbība nav atpazīta.\n\nRaksti: user actions\n\nVersija: V11.5"

        log_admin_action(user_id, f"user_action_{action_name}", "success", command_text)
        updated = _fetch_user_row_for_admin(target_user_id) or target
        return (
            "🧰 Nina Admin User Actions\n\n"
            f"User ID: {target_user_id}\n"
            f"Darbība: {action_name}\n"
            "Statuss: success\n\n"
            f"{result_text}\n\n"
            "Pašreizējais stāvoklis:\n"
            f"Premium: {'Premium' if updated.get('premium') else 'Free'}\n"
            f"Premium līdz: {updated.get('premium_until') or '—'}\n"
            f"XP: {updated.get('xp', 0)}\n"
            f"Līmenis: {updated.get('level', 1)}\n"
            f"Streak: {updated.get('streak_days', 0)}\n\n"
            "Versija: V11.5"
        )

    except Exception as e:
        print("Admin user action kļūda:", e)
        log_admin_action(user_id, "user_action_execute", "failed_exception", command_text)
        return (
            "🧰 Nina Admin User Actions\n\n"
            "Darbība neizdevās tehniskas kļūdas dēļ.\n\n"
            f"Iemesls: {e}\n\n"
            "Versija: V11.5"
        )


def admin_user_management_dashboard(user_id, command_text="user management"):
    """V10.24: Admin User Management Dashboard — vienots panelis lietotāju pārvaldībai."""
    if not is_admin(user_id):
        log_admin_action(user_id, "user_management_view", "denied", command_text)
        return admin_locked_answer()

    log_admin_action(user_id, "user_management_view", "allowed", command_text)

    users_total = _count_table_rows("users")
    premium_users = _count_table_rows("users", "WHERE premium = 1")
    free_users = max(0, users_total - premium_users)
    messages_total = _count_table_rows("messages")
    backups_total = _count_table_rows("memory_backups")
    reminders_total = _count_table_rows("reminders")
    active_reminders = _count_table_rows("reminders", "WHERE status = %s", ("active",))
    audit_total = _count_table_rows("admin_audit_logs")

    try:
        conn = get_db()
        c = conn.cursor()
        db_execute(c, """
            SELECT user_id, name, premium, xp, level, streak_days
            FROM users
            ORDER BY xp DESC, user_id ASC
            LIMIT 3
        """)
        top_users = c.fetchall()
        c.close()
        conn.close()
    except Exception as e:
        print("User management top users kļūda:", e)
        top_users = []

    lines = [
        "👥 Nina User Management Dashboard",
        "",
        "Lietotāji:",
        f"Kopā: {users_total}",
        f"Premium: {premium_users}",
        f"Free: {free_users}",
        "",
        "Aktivitāte:",
        f"Ziņas kopā: {messages_total}",
        f"Backup kopā: {backups_total}",
        f"Atgādinājumi kopā: {reminders_total}",
        f"Aktīvie atgādinājumi: {active_reminders}",
        "",
        "Top lietotāji pēc XP:",
    ]

    if top_users:
        for idx, (found_user_id, name, premium, xp, level, streak_days) in enumerate(top_users, start=1):
            status = "Premium" if premium else "Free"
            lines.append(f"{idx}. {found_user_id} — {name or '—'}")
            lines.append(f"   {status}, XP: {int(xp or 0)}, Līmenis: {int(level or 1)}, Streak: {int(streak_days or 0)}")
    else:
        lines.append("Vēl nav lietotāju datu.")

    lines.extend([
        "",
        "Meklēšana:",
        "search user premium",
        "search user free",
        "search user xp",
        "find user 5138563912",
        "",
        "Profils:",
        "user 5138563912",
        "user lookup 5138563912",
        "",
        "Darbības:",
        "grant premium 5138563912",
        "remove premium 5138563912",
        "add xp 5138563912 100",
        "remove xp 5138563912 50",
        "set level 5138563912 5",
        "reset streak 5138563912",
        "",
        "Drošība:",
        "Admin Lock: Aktīvs",
        f"Audit ieraksti: {audit_total}",
        "",
        "Versija: V11.5",
    ])

    return "\n".join(lines)


async def auto_backup_worker(application):
    while True:
        try:
            run_auto_backup(force=False)
        except Exception as e:
            print("Auto backup worker kļūda:", e)
        await asyncio.sleep(60)

def admin_revenue_dashboard(user_id, command_text="revenue"):
    if not is_admin(user_id):
        log_admin_action(user_id, "revenue_view", "denied", command_text)
        return admin_locked_answer()
    log_admin_action(user_id, "revenue_view", "allowed", command_text)
    return revenue_dashboard(user_id)

def revenue_dashboard(user_id=None):
    """V10.7: Revenue Dashboard — admin pārskats par Premium ieņēmumiem."""
    conn = get_db()
    c = conn.cursor()

    try:
        db_execute(c, """
            SELECT
                COALESCE(SUM(amount), 0),
                COUNT(*)
            FROM premium_transactions
            WHERE status = 'paid'
        """)
        total_revenue, paid_count = c.fetchone()
    except Exception:
        total_revenue, paid_count = 0, 0

    try:
        db_execute(c, """
            SELECT COUNT(*)
            FROM users
            WHERE premium = 1
        """)
        premium_users = int(c.fetchone()[0] or 0)
    except Exception:
        premium_users = 0

    try:
        db_execute(c, """
            SELECT COUNT(DISTINCT user_id)
            FROM premium_transactions
            WHERE status = 'paid' AND plan_name = %s
        """, (PLAN_PREMIUM_BASIC,))
        basic_users = int(c.fetchone()[0] or 0)
    except Exception:
        basic_users = 0

    try:
        db_execute(c, """
            SELECT COUNT(DISTINCT user_id)
            FROM premium_transactions
            WHERE status = 'paid' AND plan_name = %s
        """, (PLAN_PREMIUM_PLUS,))
        plus_users = int(c.fetchone()[0] or 0)
    except Exception:
        plus_users = 0

    try:
        db_execute(c, """
            SELECT COUNT(*)
            FROM premium_transactions
            WHERE status = 'checkout_created'
        """)
        checkout_created = int(c.fetchone()[0] or 0)
    except Exception:
        checkout_created = 0

    try:
        db_execute(c, """
            SELECT COUNT(*)
            FROM premium_transactions
            WHERE status = 'checkout_ready_static'
        """)
        checkout_pending = int(c.fetchone()[0] or 0)
    except Exception:
        checkout_pending = 0

    c.close()
    conn.close()

    total_revenue = float(total_revenue or 0)
    paid_count = int(paid_count or 0)
    mrr = basic_users * PREMIUM_BASIC_PRICE + plus_users * PREMIUM_PLUS_PRICE

    return (
        "💰 Nina Revenue Dashboard\n\n"
        f"Ieņēmumi kopā: {total_revenue:.2f} {PREMIUM_CURRENCY}\n"
        f"Apmaksāti darījumi: {paid_count}\n"
        f"Premium klienti: {premium_users}\n\n"
        "Plāni:\n"
        f"🥉 Basic: {basic_users}\n"
        f"🥈 Plus: {plus_users}\n\n"
        f"MRR: {mrr:.2f} {PREMIUM_CURRENCY}\n\n"
        "Checkout:\n"
        f"Izveidoti checkout: {checkout_created}\n"
        f"Nepabeigti/statiskie: {checkout_pending}"
    )




def admin_revenue_analytics(user_id, command_text="revenue analytics"):
    """V10.24: Admin Revenue Analytics — padziļināts Premium ieņēmumu un checkout pārskats."""
    if not is_admin(user_id):
        log_admin_action(user_id, "revenue_analytics_view", "denied", command_text)
        return admin_locked_answer()

    log_admin_action(user_id, "revenue_analytics_view", "allowed", command_text)

    conn = get_db()
    c = conn.cursor()

    def scalar(sql, params=()):
        try:
            db_execute(c, sql, params)
            row = c.fetchone()
            return row[0] if row else 0
        except Exception as e:
            print("Revenue analytics scalar kļūda:", e)
            return 0

    total_revenue = float(scalar("""
        SELECT COALESCE(SUM(amount), 0)
        FROM premium_transactions
        WHERE status = 'paid'
    """) or 0)

    paid_count = int(scalar("""
        SELECT COUNT(*)
        FROM premium_transactions
        WHERE status = 'paid'
    """) or 0)

    premium_users = int(scalar("""
        SELECT COUNT(*)
        FROM users
        WHERE premium = 1
    """) or 0)

    free_users = int(scalar("""
        SELECT COUNT(*)
        FROM users
        WHERE premium = 0
    """) or 0)

    basic_users = int(scalar("""
        SELECT COUNT(DISTINCT user_id)
        FROM premium_transactions
        WHERE status = 'paid' AND plan_name = %s
    """, (PLAN_PREMIUM_BASIC,)) or 0)

    plus_users = int(scalar("""
        SELECT COUNT(DISTINCT user_id)
        FROM premium_transactions
        WHERE status = 'paid' AND plan_name = %s
    """, (PLAN_PREMIUM_PLUS,)) or 0)

    admin_granted = int(scalar("""
        SELECT COUNT(*)
        FROM premium_transactions
        WHERE status = 'admin_granted'
    """) or 0)

    admin_removed = int(scalar("""
        SELECT COUNT(*)
        FROM premium_transactions
        WHERE status = 'admin_removed'
    """) or 0)

    checkout_created = int(scalar("""
        SELECT COUNT(*)
        FROM premium_transactions
        WHERE status = 'checkout_created'
    """) or 0)

    checkout_static = int(scalar("""
        SELECT COUNT(*)
        FROM premium_transactions
        WHERE status = 'checkout_ready_static'
    """) or 0)

    checkout_errors = int(scalar("""
        SELECT COUNT(*)
        FROM premium_transactions
        WHERE status IN ('payment_failed', 'checkout_error', 'stripe_checkout_error', 'failed')
    """) or 0)

    try:
        db_execute(c, """
            SELECT created_at, user_id, plan_name, amount, currency, status, payment_method
            FROM premium_transactions
            ORDER BY id DESC
            LIMIT 5
        """)
        recent_rows = c.fetchall()
    except Exception as e:
        print("Revenue analytics recent kļūda:", e)
        recent_rows = []

    c.close()
    conn.close()

    mrr = basic_users * PREMIUM_BASIC_PRICE + plus_users * PREMIUM_PLUS_PRICE
    arpu = (total_revenue / paid_count) if paid_count else 0.0

    lines = [
        "📈 Nina Revenue Analytics",
        "",
        "Ieņēmumi:",
        f"Kopā: {total_revenue:.2f} {PREMIUM_CURRENCY}",
        f"Apmaksāti darījumi: {paid_count}",
        f"Vidēji par darījumu: {arpu:.2f} {PREMIUM_CURRENCY}",
        f"MRR: {mrr:.2f} {PREMIUM_CURRENCY}",
        "",
        "Premium lietotāji:",
        f"Aktīvi Premium: {premium_users}",
        f"Free lietotāji: {free_users}",
        f"Basic klienti: {basic_users}",
        f"Plus klienti: {plus_users}",
        "",
        "Admin darbības:",
        f"Piešķirts Premium: {admin_granted}",
        f"Noņemts Premium: {admin_removed}",
        "",
        "Checkout:",
        f"Izveidoti checkout: {checkout_created}",
        f"Statiskie/nepabeigtie: {checkout_static}",
        f"Kļūdas: {checkout_errors}",
        "",
        "Pēdējie darījumi:",
    ]

    if recent_rows:
        for created_at, tx_user_id, plan_name, amount, currency, status, method in recent_rows:
            lines.append(f"• {created_at} — {tx_user_id} — {plan_name or '—'} — {float(amount or 0):.2f} {currency or PREMIUM_CURRENCY} — {status or '—'} — {method or '—'}")
    else:
        lines.append("• nav darījumu")

    lines.extend([
        "",
        "Versija: V11.5",
    ])

    return "\n".join(lines)

def premium_welcome_answer(user_id):
    """V10.5: Premium Welcome Flow — parāda Premium starta pieredzi pēc aktivizācijas/maksājuma."""
    user = get_user(user_id)
    plan = current_plan_name(user_id)

    if not user.get("premium"):
        return (
            "💎 Premium vēl nav aktīvs\n\n"
            "Lai aktivizētu Premium, raksti:\n"
            "pirkt premium\n\n"
            "Pēc apmaksas atgriezies šeit un raksti:\n"
            "premium welcome"
        )

    until = user.get("premium_until") or "bez beigu datuma"
    return (
        "💎 Laipni lūgts Nina Premium!\n\n"
        f"Tavs plāns: {plan}\n"
        f"Premium aktīvs līdz: {until}\n\n"
        "Tagad tev ir:\n"
        "• backup bez limita\n"
        "• atgādinājumi bez limita\n"
        "• kopsavilkumi bez limita\n"
        "• pilns Premium Dashboard\n"
        "• vairāk vietas ilgtermiņa atmiņai\n\n"
        "Ieteicamie nākamie soļi:\n"
        "premium panelis\n"
        "atjauno kopsavilkumu\n"
        "izveido backup"
    )


def stripe_event_seen(stripe_event_id):
    if not stripe_event_id:
        return False
    conn = get_db()
    c = conn.cursor()
    try:
        db_execute(
            c,
            "SELECT COUNT(*) FROM premium_transactions WHERE stripe_event_id = %s",
            (stripe_event_id,)
        )
        count = int(c.fetchone()[0] or 0)
    except Exception:
        count = 0
    c.close()
    conn.close()
    return count > 0


def activate_paid_premium(user_id, plan_name, amount, currency, payment_method, stripe_session_id="", stripe_event_id="", customer_email=""):
    user = get_user(str(user_id))
    until = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")
    user["premium"] = 1
    user["premium_until"] = until
    update_user(str(user_id), user)

    record_premium_transaction(
        user_id=str(user_id),
        plan_name=plan_name or PLAN_PREMIUM_BASIC,
        amount=amount,
        currency=currency or PREMIUM_CURRENCY,
        payment_method=payment_method or "stripe",
        status="paid",
        expires_at=until,
        stripe_session_id=stripe_session_id,
        stripe_event_id=stripe_event_id,
        customer_email=customer_email,
    )

    achievements = check_achievements(str(user_id))
    return until, achievements


def create_stripe_checkout_session(user_id, plan_key="basic"):
    if not stripe or not STRIPE_SECRET_KEY:
        return None, "stripe_library_or_secret_missing"

    if plan_key == "plus":
        plan_name = PLAN_PREMIUM_PLUS
        price_id = STRIPE_PLUS_PRICE_ID
    else:
        plan_name = PLAN_PREMIUM_BASIC
        price_id = STRIPE_BASIC_PRICE_ID

    if not price_id:
        return None, "stripe_price_id_missing"

    try:
        session = stripe.checkout.Session.create(
            mode="subscription",
            line_items=[{"price": price_id, "quantity": 1}],
            success_url=STRIPE_SUCCESS_URL,
            cancel_url=STRIPE_CANCEL_URL,
            client_reference_id=str(user_id),
            metadata={
                "user_id": str(user_id),
                "plan_name": plan_name,
                "source": "nina_telegram",
            },
        )
        return session, "ok"
    except Exception as e:
        print("Stripe checkout session kļūda:", e)
        return None, "stripe_checkout_error"


def plan_from_stripe_session(session):
    metadata = session.get("metadata") or {}
    plan_name = metadata.get("plan_name") or PLAN_PREMIUM_BASIC

    amount_total = session.get("amount_total")
    currency = (session.get("currency") or PREMIUM_CURRENCY).upper()

    if plan_name == PLAN_PREMIUM_PLUS:
        amount = PREMIUM_PLUS_PRICE
    elif amount_total is not None:
        amount = float(amount_total or 0) / 100
    else:
        amount = PREMIUM_BASIC_PRICE

    return plan_name, amount, currency


def user_id_from_stripe_session(session):
    metadata = session.get("metadata") or {}
    return str(metadata.get("user_id") or session.get("client_reference_id") or "").strip()


def stripe_status(user_id=None):
    basic_url_ready = bool(STRIPE_BASIC_CHECKOUT_URL)
    plus_url_ready = bool(STRIPE_PLUS_CHECKOUT_URL)
    basic_price_ready = bool(STRIPE_BASIC_PRICE_ID)
    plus_price_ready = bool(STRIPE_PLUS_PRICE_ID)
    secret_ready = bool(STRIPE_SECRET_KEY)
    webhook_ready = bool(STRIPE_WEBHOOK_SECRET)
    stripe_lib_ready = bool(stripe)

    lines = [
        "💳 Maksājumu statuss",
        "",
        f"payments python library: {'✅' if stripe_lib_ready else '❌'}",
        f"STRIPE_SECRET_KEY: {'✅' if secret_ready else '❌'}",
        f"STRIPE_BASIC_CHECKOUT_URL: {'✅' if basic_url_ready else '❌'}",
        f"STRIPE_PLUS_CHECKOUT_URL: {'✅' if plus_url_ready else '❌'}",
        f"STRIPE_BASIC_PRICE_ID: {'✅' if basic_price_ready else '❌'}",
        f"STRIPE_PLUS_PRICE_ID: {'✅' if plus_price_ready else '❌'}",
        f"STRIPE_WEBHOOK_SECRET: {'✅' if webhook_ready else '❌'}",
        "",
    ]

    if secret_ready and webhook_ready and (basic_price_ready or basic_url_ready):
        lines.append("Maksājumu plūsma ir gatava V10.3 webhook režīmam.")
    elif basic_url_ready or plus_url_ready:
        lines.append("Checkout linki ir sagatavoti, bet automātiskai Premium aktivizācijai vajag webhook.")
    else:
        lines.append("Maksājumi vēl nav pieslēgti. Pievieno Railway environment variables.")

    lines.extend([
        "",
        "Webhook endpoint:",
        "/payments/webhook",
    ])

    return "\n".join(lines)


def stripe_setup_helper(user_id=None):
    """V11.2: Stripe Setup Helper — skaidrs Railway/Stripe checklist un nākamie soļi."""
    stripe_lib_ready = bool(stripe)
    secret_ready = bool(STRIPE_SECRET_KEY)
    webhook_ready = bool(STRIPE_WEBHOOK_SECRET)
    basic_price_ready = bool(STRIPE_BASIC_PRICE_ID)
    plus_price_ready = bool(STRIPE_PLUS_PRICE_ID)
    success_ready = bool(STRIPE_SUCCESS_URL and STRIPE_SUCCESS_URL != "https://t.me/")
    cancel_ready = bool(STRIPE_CANCEL_URL and STRIPE_CANCEL_URL != "https://t.me/")
    basic_url_ready = bool(STRIPE_BASIC_CHECKOUT_URL)
    plus_url_ready = bool(STRIPE_PLUS_CHECKOUT_URL)

    dynamic_basic_ready = stripe_lib_ready and secret_ready and basic_price_ready and success_ready and cancel_ready
    dynamic_plus_ready = stripe_lib_ready and secret_ready and plus_price_ready and success_ready and cancel_ready
    webhook_full_ready = webhook_ready and secret_ready
    static_ready = basic_url_ready or plus_url_ready

    missing = []
    if not stripe_lib_ready:
        missing.append("requirements.txt: stripe")
    if not secret_ready:
        missing.append("STRIPE_SECRET_KEY")
    if not basic_price_ready:
        missing.append("STRIPE_BASIC_PRICE_ID")
    if not plus_price_ready:
        missing.append("STRIPE_PLUS_PRICE_ID")
    if not success_ready:
        missing.append("STRIPE_SUCCESS_URL")
    if not cancel_ready:
        missing.append("STRIPE_CANCEL_URL")
    if not webhook_ready:
        missing.append("STRIPE_WEBHOOK_SECRET")

    if dynamic_basic_ready and dynamic_plus_ready and webhook_full_ready:
        status_icon = "🟢"
        status_text = "Stripe gatavs pilnam testam"
    elif dynamic_basic_ready or dynamic_plus_ready or static_ready:
        status_icon = "🟡"
        status_text = "Stripe daļēji pieslēgts"
    else:
        status_icon = "🔴"
        status_text = "Stripe vēl nav pieslēgts"

    lines = [
        "💳 Nina Stripe Setup Helper",
        "",
        f"Statuss: {status_icon} {status_text}",
        "",
        "1. Python bibliotēka:",
        f"{'✅' if stripe_lib_ready else '❌'} stripe package",
        "",
        "2. Railway ENV dinamiskam Checkout:",
        f"{'✅' if secret_ready else '❌'} STRIPE_SECRET_KEY=sk_test_...",
        f"{'✅' if basic_price_ready else '❌'} STRIPE_BASIC_PRICE_ID=price_...",
        f"{'✅' if plus_price_ready else '❌'} STRIPE_PLUS_PRICE_ID=price_...",
        f"{'✅' if success_ready else '❌'} STRIPE_SUCCESS_URL=https://tavs-domens/success",
        f"{'✅' if cancel_ready else '❌'} STRIPE_CANCEL_URL=https://tavs-domens/cancel",
        "",
        "3. Webhook automātiskai Premium aktivizācijai:",
        f"{'✅' if webhook_ready else '❌'} STRIPE_WEBHOOK_SECRET=whsec_...",
        "Webhook URL Railway/Stripe:",
        "https://TAVS-RAILWAY-DOMENS/stripe/webhook",
        "Event:",
        "checkout.session.completed",
        "",
        "4. Alternatīva — statiskie Checkout linki:",
        f"{'✅' if basic_url_ready else '❌'} STRIPE_BASIC_CHECKOUT_URL=buy dot stripe dot com/...",
        f"{'✅' if plus_url_ready else '❌'} STRIPE_PLUS_CHECKOUT_URL=buy dot stripe dot com/...",
        "",
        "5. Testa komandas Telegramā:",
        "premium",
        "pirkt basic",
        "pirkt plus",
        "stripe statuss",
        "stripe setup",
        "premium vēsture",
        "",
    ]

    if missing:
        lines.append("Trūkst:")
        for item in missing:
            lines.append(f"• {item}")
        lines.append("")

    if dynamic_basic_ready and dynamic_plus_ready and webhook_full_ready:
        lines.append("✅ Nākamais solis: veic Stripe testa maksājumu ar pirkt basic un pārbaudi premium vēsture.")
    elif dynamic_basic_ready or dynamic_plus_ready:
        lines.append("🟡 Checkout var sākt testēt, bet automātiskai Premium aktivizācijai pabeidz webhook.")
    elif static_ready:
        lines.append("🟡 Statiskie checkout linki ir pieejami, bet automātiska Premium aktivizācija vēl nebūs pilna bez webhook.")
    else:
        lines.append("❌ Sāc ar Railway ENV: STRIPE_SECRET_KEY un STRIPE_BASIC_PRICE_ID.")

    lines.extend([
        "",
        "Versija: V11.5",
    ])

    return "\n".join(lines)

def stripe_checkout_answer(user_id, plan_key="basic"):
    """V11.5 Requirements Helper — izveido reālu Stripe Checkout linku, ja ENV ir pieslēgts."""
    if plan_key == "plus":
        plan_name = PLAN_PREMIUM_PLUS
        amount = PREMIUM_PLUS_PRICE
        price_id = STRIPE_PLUS_PRICE_ID
        static_url = STRIPE_PLUS_CHECKOUT_URL
    else:
        plan_name = PLAN_PREMIUM_BASIC
        amount = PREMIUM_BASIC_PRICE
        price_id = STRIPE_BASIC_PRICE_ID
        static_url = STRIPE_BASIC_CHECKOUT_URL

    # 1) Statiskie Stripe Checkout linki — vienkāršākais darba variants
    if static_url:
        record_premium_transaction(
            user_id=str(user_id),
            plan_name=plan_name,
            amount=amount,
            currency=PREMIUM_CURRENCY,
            payment_method="stripe_static_checkout",
            status="checkout_link_sent",
            checkout_url=static_url,
        )
        return (
            "💳 Maksājumu Checkout\n\n"
            f"Plāns: {plan_name}\n"
            f"Cena: {amount:.2f} {PREMIUM_CURRENCY}/mēn\n\n"
            "Apmaksas links:\n"
            f"{static_url}\n\n"
            "Pēc apmaksas Premium aktivizēsies automātiski, ja Stripe webhook ir pieslēgts.\n"
            "Versija: V11.5"
        )

    # 2) Dynamic Stripe Checkout Sessions
    if not stripe:
        reason = "stripe_library_missing"
    elif not STRIPE_SECRET_KEY:
        reason = "stripe_secret_missing"
    elif not price_id:
        reason = "stripe_price_id_missing"
    elif not STRIPE_SUCCESS_URL or not STRIPE_CANCEL_URL:
        reason = "stripe_success_or_cancel_url_missing"
    else:
        reason = ""

    if reason:
        record_premium_transaction(
            user_id=str(user_id),
            plan_name=plan_name,
            amount=amount,
            currency=PREMIUM_CURRENCY,
            payment_method="stripe_dynamic_checkout",
            status="checkout_not_configured",
            checkout_url="",
        )
        return (
            "💳 Maksājumu Checkout\n\n"
            f"Plāns: {plan_name}\n"
            f"Cena: {amount:.2f} {PREMIUM_CURRENCY}/mēn\n\n"
            "Maksājumu checkout vēl nav pilnībā pieslēgts.\n"
            "Dinamiskam checkout pievieno Railway: STRIPE_SECRET_KEY, STRIPE_BASIC_PRICE_ID/STRIPE_PLUS_PRICE_ID, STRIPE_SUCCESS_URL, STRIPE_CANCEL_URL\n"
            "Vai statiskam linkam pievieno: STRIPE_BASIC_CHECKOUT_URL / STRIPE_PLUS_CHECKOUT_URL\n\n"
            f"Iemesls: {reason}\n"
            "Versija: V11.5"
        )

    try:
        stripe.api_key = STRIPE_SECRET_KEY
        session = stripe.checkout.Session.create(
            mode="subscription",
            line_items=[{"price": price_id, "quantity": 1}],
            success_url=STRIPE_SUCCESS_URL,
            cancel_url=STRIPE_CANCEL_URL,
            client_reference_id=str(user_id),
            metadata={
                "telegram_user_id": str(user_id),
                "plan_key": plan_key,
                "plan_name": plan_name,
            },
        )

        checkout_url = getattr(session, "url", "") or session.get("url", "")
        session_id = getattr(session, "id", "") or session.get("id", "")

        record_premium_transaction(
            user_id=str(user_id),
            plan_name=plan_name,
            amount=amount,
            currency=PREMIUM_CURRENCY,
            payment_method="stripe_dynamic_checkout",
            status="checkout_created",
            checkout_url=checkout_url,
            stripe_session_id=session_id,
        )

        return (
            "💳 Maksājumu Checkout\n\n"
            f"Plāns: {plan_name}\n"
            f"Cena: {amount:.2f} {PREMIUM_CURRENCY}/mēn\n\n"
            "Apmaksas links:\n"
            f"{checkout_url}\n\n"
            "Pēc apmaksas Premium aktivizēsies automātiski, ja Stripe webhook ir pieslēgts.\n"
            "Versija: V11.5"
        )

    except Exception as e:
        record_premium_transaction(
            user_id=str(user_id),
            plan_name=plan_name,
            amount=amount,
            currency=PREMIUM_CURRENCY,
            payment_method="stripe_dynamic_checkout",
            status="stripe_checkout_error",
            checkout_url="",
        )
        return (
            "💳 Maksājumu Checkout\n\n"
            f"Plāns: {plan_name}\n"
            f"Cena: {amount:.2f} {PREMIUM_CURRENCY}/mēn\n\n"
            "Stripe checkout izveide neizdevās.\n"
            f"Iemesls: {str(e)}\n"
            "Versija: V11.5"
        )


def calculate_level(xp):
    try:
        xp = int(xp or 0)
    except Exception:
        xp = 0
    return max(1, xp // XP_PER_LEVEL + 1)


def xp_for_next_level(xp):
    try:
        xp = int(xp or 0)
    except Exception:
        xp = 0
    next_level_xp = calculate_level(xp) * XP_PER_LEVEL
    return max(0, next_level_xp - xp)


def add_xp(user_id, amount):
    try:
        user = get_user(user_id)
        current_xp = int(user.get("xp", 0) or 0)
        new_xp = max(0, current_xp + int(amount or 0))
        user["xp"] = new_xp
        user["level"] = calculate_level(new_xp)
        update_user(user_id, user)
        return new_xp, user["level"]
    except Exception as e:
        print("XP kļūda:", e)
        return None, None


def user_level_info(user_id):
    user = get_user(user_id)
    xp = int(user.get("xp", 0) or 0)
    level = calculate_level(xp)

    if level != int(user.get("level", 1) or 1):
        user["level"] = level
        update_user(user_id, user)

    next_level = level + 1
    left = xp_for_next_level(xp)

    return (
        f"🏆 Tavs līmenis: {level}\n\n"
        f"⭐ XP: {xp}\n\n"
        f"Nākamais līmenis: {next_level}\n"
        f"Vēl vajag: {left} XP"
    )




def achievement_definitions():
    return {
        # 📦 Backup sērija
        "backup_starter": {
            "icon": "📦",
            "title": "Backup Starter",
            "description": "Izveidoji savu pirmo backup.",
            "xp": 25,
        },
        "backup_collector": {
            "icon": "📦",
            "title": "Backup Collector",
            "description": "Izveidoji 5 backup.",
            "xp": 50,
        },
        "backup_master": {
            "icon": "📦",
            "title": "Backup Master",
            "description": "Izveidoji 10 backup.",
            "xp": 100,
        },

        # 🧠 Atmiņas sērija
        "memory_builder": {
            "icon": "🧠",
            "title": "Memory Builder",
            "description": "Aizpildīti vismaz 5 atmiņas lauki.",
            "xp": 25,
        },
        "memory_expert": {
            "icon": "🧠",
            "title": "Memory Expert",
            "description": "Atmiņa aizpildīta vismaz 50%.",
            "xp": 100,
        },
        "memory_master": {
            "icon": "🧠",
            "title": "Memory Master",
            "description": "Atmiņa aizpildīta 100%.",
            "xp": 250,
        },

        # 💎 Premium
        "premium_explorer": {
            "icon": "💎",
            "title": "Premium Explorer",
            "description": "Aktivizēji Premium.",
            "xp": 50,
        },

        # ⭐ XP sērija
        "rising_star": {
            "icon": "⭐",
            "title": "Rising Star",
            "description": "Sasniedzi 100 XP.",
            "xp": 50,
        },
        "xp_warrior": {
            "icon": "⭐",
            "title": "XP Warrior",
            "description": "Sasniedzi 500 XP.",
            "xp": 100,
        },
        "xp_legend": {
            "icon": "⭐",
            "title": "XP Legend",
            "description": "Sasniedzi 1000 XP.",
            "xp": 250,
        },

        # 🏆 Līmeņu sērija
        "nina_veteran": {
            "icon": "🏆",
            "title": "Nina Veteran",
            "description": "Sasniedzi 5. līmeni.",
            "xp": 100,
        },
        "nina_master": {
            "icon": "🏆",
            "title": "Nina Master",
            "description": "Sasniedzi 10. līmeni.",
            "xp": 250,
        },

        # 🔥 Streak sērija
        "streak_7": {
            "icon": "🔥",
            "title": "Consistent User",
            "description": "7 dienas pēc kārtas ar Ninu.",
            "xp": 75,
        },
        "streak_30": {
            "icon": "🔥",
            "title": "Nina Loyal",
            "description": "30 dienas pēc kārtas ar Ninu.",
            "xp": 200,
        },
    }


def has_achievement(user_id, code):
    conn = get_db()
    c = conn.cursor()
    db_execute(c, "SELECT COUNT(*) FROM user_achievements WHERE user_id = %s AND achievement_code = %s", (user_id, code))
    count = int(c.fetchone()[0] or 0)
    c.close()
    conn.close()
    return count > 0


def unlock_achievement(user_id, code):
    defs = achievement_definitions()
    if code not in defs or has_achievement(user_id, code):
        return ""
    ach = defs[code]
    conn = get_db()
    c = conn.cursor()
    db_execute(c, "INSERT INTO user_achievements (user_id, achievement_code) VALUES (%s, %s)", (user_id, code))
    conn.commit()
    c.close()
    conn.close()
    xp_bonus = int(ach.get("xp", 0) or 0)
    if xp_bonus:
        add_xp(user_id, xp_bonus)
    return "🎉 Jauns sasniegums!\n\n" + f"{ach['icon']} {ach['title']}\n{ach['description']}\n\n+{xp_bonus} XP"


def achievement_count(user_id):
    conn = get_db()
    c = conn.cursor()
    db_execute(c, "SELECT COUNT(*) FROM user_achievements WHERE user_id = %s", (user_id,))
    count = int(c.fetchone()[0] or 0)
    c.close()
    conn.close()
    return count


def achievements_answer(user_id):
    defs = achievement_definitions()
    conn = get_db()
    c = conn.cursor()
    db_execute(c, "SELECT achievement_code FROM user_achievements WHERE user_id = %s ORDER BY id ASC", (user_id,))
    rows = c.fetchall()
    c.close()
    conn.close()
    if not rows:
        return "🏅 Tev vēl nav sasniegumu.\n\nSāc ar pirmo backup, streak vai aizpildi vairāk atmiņas laukus."
    lines = ["🏅 Tavi sasniegumi", ""]
    for (code,) in rows:
        ach = defs.get(code)
        if ach:
            lines.append(f"{ach['icon']} {ach['title']}")
            lines.append(f"   {ach['description']}")
            lines.append("")
    lines.append(f"Kopā: {len(rows)} sasniegumi")
    return "\n".join(lines).strip()


def next_achievement_progress(user_id):
    user = get_user(user_id)
    xp = int(user.get("xp", 0) or 0)
    level = calculate_level(xp)
    backups = backup_count_number(user_id)
    memory_percent = memory_fill_percent(user_id)
    streak_days = int(user.get("streak_days", 0) or 0)

    progress_items = [
        ("📦 Backup Collector", backups, 5, "backup_collector"),
        ("📦 Backup Master", backups, 10, "backup_master"),
        ("⭐ Rising Star", xp, 100, "rising_star"),
        ("⭐ XP Warrior", xp, 500, "xp_warrior"),
        ("⭐ XP Legend", xp, 1000, "xp_legend"),
        ("🏆 Nina Veteran", level, 5, "nina_veteran"),
        ("🏆 Nina Master", level, 10, "nina_master"),
        ("🔥 Consistent User", streak_days, 7, "streak_7"),
        ("🔥 Nina Loyal", streak_days, 30, "streak_30"),
        ("🧠 Memory Builder", memory_percent, 33, "memory_builder"),
        ("🧠 Memory Expert", memory_percent, 50, "memory_expert"),
        ("🧠 Memory Master", memory_percent, 100, "memory_master"),
    ]

    available = []
    for title, current, target, code in progress_items:
        if not has_achievement(user_id, code):
            available.append((title, current, target, code))

    if not available:
        return "Visi pašreizējie sasniegumi ir atbloķēti. 🏆"

    available.sort(key=lambda item: max(0, item[2] - item[1]))
    title, current, target, _ = available[0]
    return f"{title}: {current}/{target}"


def achievement_progress(user_id):
    # V9.9.2: vispirms sinhronizē sasniegumus, lai progress nerāda vecu skaitu.
    achievement_notices = check_achievements(user_id)

    user = get_user(user_id)
    xp = int(user.get("xp", 0) or 0)
    level = calculate_level(xp)
    backups = backup_count_number(user_id)
    memory_percent = memory_fill_percent(user_id)
    streak_days = int(user.get("streak_days", 0) or 0)
    total = len(achievement_definitions())
    unlocked = achievement_count(user_id)

    answer = (
        "🏅 Sasniegumu progress\n\n"
        f"Kopā atbloķēti: {unlocked}/{total}\n\n"
        f"📦 Backup: {backups}/5 un {backups}/10\n"
        f"⭐ XP: {xp}/100, {xp}/500, {xp}/1000\n"
        f"🏆 Līmenis: {level}/5 un {level}/10\n"
        f"🔥 Streak: {streak_days}/7 un {streak_days}/30\n"
        f"🧠 Atmiņa: {memory_percent}/50% un {memory_percent}/100%\n\n"
        "Nākamais tuvākais:\n"
        f"{next_achievement_progress(user_id)}"
    )

    return append_bonus_notices(answer, achievement_notices)


def check_achievements(user_id):
    notices = []

    # Daži sasniegumi dod XP, kas var atbloķēt nākamos sasniegumus.
    # Tāpēc pārbaudām vairākās kārtās, līdz vairs nav jaunu unlock.
    for _ in range(3):
        before = achievement_count(user_id)
        user = get_user(user_id)
        xp = int(user.get("xp", 0) or 0)
        level = calculate_level(xp)
        backups = backup_count_number(user_id)
        memory_percent = memory_fill_percent(user_id)
        streak_days = int(user.get("streak_days", 0) or 0)

        checks = [
            (backups >= 1, "backup_starter"),
            (backups >= 5, "backup_collector"),
            (backups >= 10, "backup_master"),
            (memory_percent >= 33, "memory_builder"),
            (memory_percent >= 50, "memory_expert"),
            (memory_percent >= 100, "memory_master"),
            (bool(user.get("premium")), "premium_explorer"),
            (xp >= 100, "rising_star"),
            (xp >= 500, "xp_warrior"),
            (xp >= 1000, "xp_legend"),
            (level >= 5, "nina_veteran"),
            (level >= 10, "nina_master"),
            (streak_days >= 7, "streak_7"),
            (streak_days >= 30, "streak_30"),
        ]

        for condition, code in checks:
            if condition:
                msg = unlock_achievement(user_id, code)
                if msg:
                    notices.append(msg)

        after = achievement_count(user_id)
        if after == before:
            break

    return "\n\n".join(notices)


def update_daily_streak(user_id):
    user = get_user(user_id)
    user_tz = ZoneInfo(user.get("timezone") or DEFAULT_TIMEZONE)
    today = datetime.now(user_tz).date()
    today_text = today.strftime("%Y-%m-%d")
    last_seen = (user.get("last_seen_date") or "").strip()
    if last_seen == today_text:
        return ""
    old_streak = int(user.get("streak_days", 0) or 0)
    new_streak = 1
    if last_seen:
        try:
            last_date = datetime.strptime(last_seen, "%Y-%m-%d").date()
            if (today - last_date).days == 1:
                new_streak = old_streak + 1
            elif (today - last_date).days <= 0:
                new_streak = old_streak
        except Exception:
            new_streak = 1
    user["streak_days"] = new_streak
    user["last_seen_date"] = today_text
    update_user(user_id, user)
    reward = 5
    if new_streak == 3:
        reward = 15
    elif new_streak == 7:
        reward = 50
    elif new_streak == 30:
        reward = 200
    add_xp(user_id, reward)
    return "🔥 Streak atjaunots!\n\n" + f"Dienas pēc kārtas: {new_streak}\n+{reward} XP"


def streak_info(user_id):
    user = get_user(user_id)
    days = int(user.get("streak_days", 0) or 0)
    last_seen = user.get("last_seen_date") or "vēl nav"
    if days < 3:
        next_bonus = "3 dienās (+15 XP)"
    elif days < 7:
        next_bonus = "7 dienās (+50 XP)"
    elif days < 30:
        next_bonus = "30 dienās (+200 XP)"
    else:
        next_bonus = "tu jau esi ļoti stabilā sērijā 🔥"
    return "🔥 Tavs streak\n\n" + f"Dienas pēc kārtas: {days}\nPēdējā aktivitāte: {last_seen}\n\nNākamais bonuss: {next_bonus}"


def append_bonus_notices(answer, *notices):
    extra = [n for n in notices if n]
    if not extra:
        return answer
    return answer + "\n\n" + "\n\n".join(extra)


def valid_timezone(tz_name):
    try:
        ZoneInfo(tz_name)
        return True
    except Exception:
        return False


def detect_timezone(text):
    lower = text.lower()

    if "mana laika zona ir" in lower:
        tz = text.split("mana laika zona ir", 1)[1].strip()
        return tz if valid_timezone(tz) else None

    zones = {
        "latvijā": "Europe/Riga",
        "rīgā": "Europe/Riga",
        "amerikā": "America/New_York",
        "amerika": "America/New_York",
        "new york": "America/New_York",
        "los angeles": "America/Los_Angeles",
        "krievijā": "Europe/Moscow",
        "maskavā": "Europe/Moscow",
        "anglijā": "Europe/London",
        "londonā": "Europe/London",
        "vācijā": "Europe/Berlin",
        "berlīnē": "Europe/Berlin",
    }

    for key, tz in zones.items():
        if key in lower:
            return tz

    return None


def clean_text(text):
    return text.strip(" .,!?:;")


def split_items(text):
    text = text.replace("\n", ",")
    text = text.replace(" arī", "")
    text = re.sub(r"\s+un\s+", ",", text, flags=re.IGNORECASE)
    parts = [x.strip(" .,!?:;") for x in text.split(",")]
    return [x for x in parts if x]


def add_unique(old_text, new_items):
    items = [x.strip() for x in old_text.split(",") if x.strip()]
    for item in new_items:
        item = clean_text(item)
        if item and item not in items:
            items.append(item)
    return ", ".join(items)


def remove_item(old_text, item_to_remove):
    items = [x.strip() for x in old_text.split(",") if x.strip()]
    item_to_remove = clean_text(item_to_remove).lower()
    return ", ".join([item for item in items if item.lower() != item_to_remove])


def extract_after(text, patterns):
    for pattern in patterns:
        m = re.search(pattern, text, re.IGNORECASE)
        if m:
            return clean_text(m.group(1))
    return ""


def update_profile_from_text(user_id, text):
    lower = text.lower()
    user = get_user(user_id)
    memory_keys = [
        "name", "city", "hobbies", "facts", "timezone", "goals", "projects", "dreams",
        "important_dates", "pets", "family", "profession", "favorite_car",
        "favorite_color", "favorite_music", "premium", "premium_until", "summary"
    ]
    before_snapshot = json.dumps({k: user.get(k, "") for k in memory_keys}, ensure_ascii=False, sort_keys=True)

    new_tz = detect_timezone(text)
    if new_tz:
        user["timezone"] = new_tz

    name_match = re.search(r"mani sauc\s+([A-Za-zĀČĒĢĪĶĻŅŠŪŽāčēģīķļņšūž]+)", text, re.IGNORECASE)
    if name_match:
        user["name"] = clean_text(name_match.group(1)).title()

    city_match = re.search(r"es dzīvoju\s+([A-Za-zĀČĒĢĪĶĻŅŠŪŽāčēģīķļņšūž]+)", text, re.IGNORECASE)
    if city_match:
        user["city"] = clean_text(city_match.group(1))

    hobby_matches = re.findall(
        r"man patīk\s+(.+?)(?=(?:\nman patīk|\.|!|\?|$))",
        text,
        re.IGNORECASE | re.DOTALL
    )

    found_hobbies = []
    for match in hobby_matches:
        match = re.sub(r"ko\s+tu\s+par\s+mani.*", "", match, flags=re.IGNORECASE).strip()
        match = re.sub(r"ko\s+par\s+mani.*", "", match, flags=re.IGNORECASE).strip()
        match = re.sub(r"kas\s+man\s+patīk.*", "", match, flags=re.IGNORECASE).strip()
        found_hobbies.extend(split_items(match))

    if found_hobbies:
        user["hobbies"] = add_unique(user["hobbies"], found_hobbies)

    if lower.startswith("atceries ka ") or "man svarīgi" in lower:
        fact = text
        fact = re.sub(r"^atceries ka\s+", "", fact, flags=re.IGNORECASE)
        fact = re.sub(r"^man svarīgi\s*", "", fact, flags=re.IGNORECASE)
        user["facts"] = add_unique(user["facts"], split_items(fact))

    goal = extract_after(text, [r"mans mērķis ir\s+(.+)", r"mērķis ir\s+(.+)"])
    if goal:
        user["goals"] = add_unique(user["goals"], [goal])

    project = extract_after(text, [r"mans projekts ir\s+(.+)", r"es būvēju\s+(.+)", r"es taisu\s+(.+)"])
    if project:
        user["projects"] = add_unique(user["projects"], [project])

    dream = extract_after(text, [r"mans sapnis ir\s+(.+)", r"es sapņoju par\s+(.+)"])
    if dream:
        user["dreams"] = add_unique(user["dreams"], [dream])

    important_date = extract_after(text, [r"svarīgs datums ir\s+(.+)", r"mana dzimšanas diena ir\s+(.+)", r"dzimšanas diena ir\s+(.+)"])
    if important_date:
        user["important_dates"] = add_unique(user["important_dates"], [important_date])

    pet_match = re.search(r"man ir\s+(suns|kaķis|kakis|papagailis|trusis)\s+(.+)", text, re.IGNORECASE)
    if pet_match:
        pet_type = clean_text(pet_match.group(1))
        pet_name = clean_text(pet_match.group(2))
        pet_name = re.sub(r"\s+un\s+.*", "", pet_name, flags=re.IGNORECASE).strip()
        if pet_name:
            user["pets"] = add_unique(user["pets"], [f"{pet_name} ({pet_type})"])

    wife_match = re.search(r"man ir\s+(sieva|vīrs|virs)\s+(.+)", text, re.IGNORECASE)
    if wife_match:
        role = clean_text(wife_match.group(1))
        person = clean_text(wife_match.group(2))
        person = re.sub(r"\s+un\s+.*", "", person, flags=re.IGNORECASE).strip()
        if person:
            user["family"] = add_unique(user["family"], [f"{person} ({role})"])

    child_matches = re.findall(r"man ir\s+(meita|dēls|dels)\s+([^\n.,!?]+)", text, re.IGNORECASE)
    for role, person in child_matches:
        person = clean_text(person)
        if person:
            user["family"] = add_unique(user["family"], [f"{person} ({clean_text(role)})"])

    profession_match = re.search(r"es esmu\s+([^\n.,!?]+)", text, re.IGNORECASE)
    if profession_match:
        profession = clean_text(profession_match.group(1))
        if profession and len(profession) <= 40:
            user["profession"] = profession

    favorite_car = extract_after(text, [
        r"mans mīļākais auto ir\s+(.+)",
        r"milakais auto ir\s+(.+)",
        r"mīļākais auto ir\s+(.+)"
    ])
    if favorite_car:
        user["favorite_car"] = favorite_car

    favorite_color = extract_after(text, [
        r"mana mīļākā krāsa ir\s+(.+)",
        r"milaka krasa ir\s+(.+)",
        r"mīļākā krāsa ir\s+(.+)"
    ])
    if favorite_color:
        user["favorite_color"] = favorite_color

    favorite_music = extract_after(text, [
        r"mana mīļākā mūzika ir\s+(.+)",
        r"milaka muzika ir\s+(.+)",
        r"mīļākā mūzika ir\s+(.+)"
    ])
    if favorite_music:
        user["favorite_music"] = favorite_music

    after_snapshot = json.dumps({k: user.get(k, "") for k in memory_keys}, ensure_ascii=False, sort_keys=True)
    update_user(user_id, user)
    if after_snapshot != before_snapshot:
        save_memory_backup(user_id, "auto_profile")


def forget_from_profile(user_id, text):
    user = get_user(user_id)

    phrase = text.lower().replace("aizmirsti", "", 1).strip(" .,!?:;")
    phrase = phrase.replace("ka man patīk", "").strip(" .,!?:;")
    phrase = phrase.replace("man patīk", "").strip(" .,!?:;")
    phrase = phrase.replace("ka", "").strip(" .,!?:;")

    if not phrase:
        return "Pasaki, ko tieši lai aizmirstu."

    for key in ["hobbies", "facts", "goals", "projects", "dreams", "important_dates", "pets", "family", "profession", "favorite_car", "favorite_color", "favorite_music"]:
        user[key] = remove_item(user[key], phrase)

    update_user(user_id, user)
    return f"Labi, izdzēsu no atmiņas: {phrase}"


def save_message(user_id, role, text):
    conn = get_db()
    c = conn.cursor()
    db_execute(c, "INSERT INTO messages (user_id, role, text) VALUES (%s, %s, %s)", (user_id, role, text))
    conn.commit()
    c.close()
    conn.close()


def get_recent_messages(user_id, limit=24):
    conn = get_db()
    c = conn.cursor()
    db_execute(c, "SELECT role, text FROM messages WHERE user_id = %s ORDER BY id DESC LIMIT %s", (user_id, limit))
    rows = c.fetchall()
    c.close()
    conn.close()
    rows.reverse()
    return "\n".join([f"{role}: {text}" for role, text in rows])


def profile_answer(user):
    lines = []

    if user["name"]:
        lines.append(f"• Vārds: {user['name']}")
    if user["city"]:
        lines.append(f"• Pilsēta: {user['city']}")
    if user["timezone"]:
        lines.append(f"• Laika zona: {user['timezone']}")
    if user.get("premium"):
        premium_text = "Aktīvs"
        if user.get("premium_until"):
            premium_text += f" līdz {user['premium_until']}"
        lines.append(f"• Premium: {premium_text}")
    if user["hobbies"]:
        lines.append("• Patīk: " + user["hobbies"])
    if user["facts"]:
        lines.append("• Svarīgi fakti: " + user["facts"])
    if user["goals"]:
        lines.append("• Mērķi: " + user["goals"])
    if user["projects"]:
        lines.append("• Projekti: " + user["projects"])
    if user["dreams"]:
        lines.append("• Sapņi: " + user["dreams"])
    if user["important_dates"]:
        lines.append("• Svarīgi datumi: " + user["important_dates"])
    if user["pets"]:
        lines.append("• Mājdzīvnieki: " + user["pets"])
    if user["family"]:
        lines.append("• Ģimene: " + user["family"])
    if user["profession"]:
        lines.append("• Profesija: " + user["profession"])
    if user["favorite_car"]:
        lines.append("• Mīļākais auto: " + user["favorite_car"])
    if user["favorite_color"]:
        lines.append("• Mīļākā krāsa: " + user["favorite_color"])
    if user["favorite_music"]:
        lines.append("• Mīļākā mūzika: " + user["favorite_music"])
    if user["summary"]:
        if user.get("summary_updated_at"):
            lines.append("• Kopsavilkums atjaunots: " + user["summary_updated_at"])
        lines.append("\nIlgtermiņa kopsavilkums:\n" + user["summary"])

    if not lines:
        return "Pagaidām vēl maz zinu par tevi. Pastāsti, kas tev patīk vai kas tev svarīgs. 😊"

    return "Es par tevi atceros:\n" + "\n".join(lines)


def build_summary(user_id):
    user = get_user(user_id)

    allowed, message = can_create_summary(user_id)
    if not allowed:
        return message

    if user.get("premium"):
        recent = get_recent_messages(user_id, limit=80)
        line_instruction = "Raksti 10-14 īsas rindas. Iekļauj projektus, mērķus, ģimeni, intereses, motivāciju un nākamos soļus."
    else:
        recent = get_recent_messages(user_id, limit=35)
        line_instruction = "Raksti 5-8 īsas rindas. Fokusējies uz svarīgāko."

    has_profile_data = any([
        user["name"], user["city"], user["hobbies"], user["facts"], user["goals"],
        user["projects"], user["dreams"], user["important_dates"], user["pets"],
        user["family"], user["profession"], user["favorite_car"], user["favorite_color"],
        user["favorite_music"]
    ])

    if not recent.strip() and not has_profile_data:
        return "Vēl nav pietiekami daudz informācijas, lai izveidotu kopsavilkumu."

    profile = f"""
Esošais profils:
Vārds: {user["name"]}
Pilsēta: {user["city"]}
Laika zona: {user["timezone"]}
Patīk: {user["hobbies"]}
Fakti: {user["facts"]}
Mērķi: {user["goals"]}
Projekti: {user["projects"]}
Sapņi: {user["dreams"]}
Svarīgi datumi: {user["important_dates"]}
Mājdzīvnieki: {user["pets"]}
Ģimene: {user["family"]}
Profesija: {user["profession"]}
Mīļākais auto: {user["favorite_car"]}
Mīļākā krāsa: {user["favorite_color"]}
Mīļākā mūzika: {user["favorite_music"]}
Premium: {user["premium"]}
Premium līdz: {user["premium_until"]}

Iepriekšējais ilgtermiņa kopsavilkums:
{user["summary"]}
"""

    try:
        response = client.responses.create(
            model="gpt-4.1-mini",
            input=(
                "Tu veido Nina 7727 ilgtermiņa atmiņas kopsavilkumu par lietotāju.\n"
                "Raksti latviešu valodā.\n"
                "Neraksti izdomājumus. Izmanto tikai profilu un sarunu vēsturi.\n"
                "Neraksti par informāciju, kas nav zināma.\n"
                "Neizmanto frāzes: nav norādīts, nav zināms, nav pieejams.\n"
                "Raksti tikai par to, ko tiešām zini par lietotāju.\n"
                "Kopsavilkumam jāpalīdz Ninai nākamajās sarunās atcerēties cilvēka dzīvi, mērķus, projektu un personīgās lietas.\n"
                "Neraksti pārāk saldi. Raksti praktiski, skaidri un cilvēciski.\n"
                f"{line_instruction}\n\n"
                f"{profile}\n\n"
                f"Sarunas vēsture:\n{recent}"
            )
        )

        summary = response.output_text.strip()

        user["summary"] = summary
        user["summary_updated_at"] = datetime.now(ZoneInfo(user["timezone"])).strftime("%Y-%m-%d %H:%M")
        update_user(user_id, user)
        save_memory_backup(user_id, "auto_summary")
        add_xp(user_id, 10)

        return "Atjaunoju Long-Term Memory Pro kopsavilkumu. 🧠\n\n" + summary

    except Exception as e:
        print("Kopsavilkuma kļūda:", e)
        return "Kopsavilkumu šobrīd neizdevās izveidot. Pamēģini vēlreiz pēc brīža."


def show_summary(user_id):
    user = get_user(user_id)

    if not user["summary"]:
        return "Kopsavilkums vēl nav izveidots. Raksti: atjauno kopsavilkumu"

    if user.get("summary_updated_at"):
        return f"Ilgtermiņa kopsavilkums ({user['summary_updated_at']}):\n\n{user['summary']}"

    return "Ilgtermiņa kopsavilkums:\n\n" + user["summary"]



def active_reminders_for_export(user_id):
    conn = get_db()
    c = conn.cursor()
    db_execute(c,
        "SELECT id, text, local_time, remind_at FROM reminders WHERE user_id = %s AND status = 'active' ORDER BY id DESC",
        (user_id,)
    )
    rows = c.fetchall()
    c.close()
    conn.close()

    if not rows:
        return "Nav aktīvu atgādinājumu."

    lines = []
    for rid, text, local_time, remind_at in rows:
        shown_time = local_time or remind_at or "bez laika"
        lines.append(f"#{rid}: {text} ({shown_time})")
    return "\n".join(lines)


def build_memory_export(user_id):
    user = get_user(user_id)
    exported_at = datetime.now(ZoneInfo(user["timezone"])).strftime("%Y-%m-%d %H:%M")

    data = {
        "exported_at": exported_at,
        "user_id": user_id,
        "profile": {
            "name": user["name"],
            "city": user["city"],
            "timezone": user["timezone"],
            "hobbies": user["hobbies"],
            "facts": user["facts"],
            "goals": user["goals"],
            "projects": user["projects"],
            "dreams": user["dreams"],
            "important_dates": user["important_dates"],
            "pets": user["pets"],
            "family": user["family"],
            "profession": user["profession"],
            "favorite_car": user["favorite_car"],
            "favorite_color": user["favorite_color"],
            "favorite_music": user["favorite_music"],
            "premium": int(user["premium"] or 0),
            "premium_until": user["premium_until"],
            "summary": user["summary"],
            "summary_updated_at": user.get("summary_updated_at", "")
        },
        "active_reminders": active_reminders_for_export(user_id)
    }

    profile_text = profile_answer(user)
    return (
        "NINA MEMORY EXPORT\n"
        f"Laiks: {exported_at} ({user['timezone']})\n\n"
        f"{profile_text}\n\n"
        "Aktīvie atgādinājumi:\n"
        f"{data['active_reminders']}\n\n"
        "JSON kopija:\n"
        + json.dumps(data, ensure_ascii=False, indent=2)
    )


def save_memory_backup(user_id, source="manual"):
    try:
        backup_text = build_memory_export(user_id)
        conn = get_db()
        c = conn.cursor()
        if USE_POSTGRES:
            db_execute(c,
                "INSERT INTO memory_backups (user_id, backup_text, source) VALUES (%s, %s, %s) RETURNING id",
                (user_id, backup_text, source)
            )
            backup_id = c.fetchone()[0]
        else:
            db_execute(c,
                "INSERT INTO memory_backups (user_id, backup_text, source) VALUES (%s, %s, %s)",
                (user_id, backup_text, source)
            )
            backup_id = c.lastrowid
        conn.commit()
        c.close()
        conn.close()
        return backup_id, backup_text
    except Exception as e:
        print("Backup kļūda:", e)
        return None, "Backup neizdevās. Pārbaudi Railway logs."


def create_backup_answer(user_id):
    allowed, message = can_create_backup(user_id)
    if not allowed:
        return message

    backup_id, backup_text = save_memory_backup(user_id, "manual")
    if not backup_id:
        return backup_text
    add_xp(user_id, 5)
    answer = f"✅ Backup #{backup_id} izveidots.\n\n" + backup_text
    return append_bonus_notices(answer, check_achievements(user_id))


def latest_backup_answer(user_id):
    conn = get_db()
    c = conn.cursor()
    db_execute(c,
        "SELECT id, backup_text, source, created_at FROM memory_backups WHERE user_id = %s ORDER BY id DESC LIMIT 1",
        (user_id,)
    )
    row = c.fetchone()
    c.close()
    conn.close()

    if not row:
        return "Backup vēl nav izveidots. Raksti: izveido backup"

    backup_id, backup_text, source, created_at = row
    return f"Pēdējais backup #{backup_id} ({source}, {created_at}):\n\n{backup_text}"



def list_backups(user_id):
    conn = get_db()
    c = conn.cursor()

    db_execute(
        c,
        """
        SELECT id, source, created_at
        FROM memory_backups
        WHERE user_id = %s
        ORDER BY id DESC
        LIMIT 20
        """,
        (user_id,)
    )

    rows = c.fetchall()
    c.close()
    conn.close()

    if not rows:
        return "Backup nav atrasti."

    lines = ["Tavi backup:"]
    for bid, source, created_at in rows:
        lines.append(f"• #{bid} — {source} ({created_at})")

    return "\n".join(lines)


def restore_backup(user_id, text):
    m = re.search(r"(\d+)", text)

    if not m:
        return "Norādi backup numuru. Piemērs: atjauno no backup 2"

    backup_id = int(m.group(1))

    conn = get_db()
    c = conn.cursor()

    db_execute(
        c,
        """
        SELECT backup_text
        FROM memory_backups
        WHERE id = %s AND user_id = %s
        """,
        (backup_id, user_id)
    )

    row = c.fetchone()

    if not row:
        c.close()
        conn.close()
        return "Tādu backup neatradu."

    backup_text = row[0]

    try:
        json_part = backup_text.split("JSON kopija:\n", 1)[1]
        data = json.loads(json_part)
        profile = data.get("profile", {})

        user = get_user(user_id)

        fields = [
            "name", "city", "timezone", "hobbies", "facts", "goals", "projects",
            "dreams", "important_dates", "pets", "family", "profession",
            "favorite_car", "favorite_color", "favorite_music", "premium",
            "premium_until", "summary", "summary_updated_at"
        ]

        for field in fields:
            if field in profile:
                user[field] = profile[field]

        update_user(user_id, user)
        save_memory_backup(user_id, f"restore_from_{backup_id}")

        c.close()
        conn.close()

        return f"✅ Atjaunoju profilu no backup #{backup_id}."

    except Exception as e:
        c.close()
        conn.close()
        print("Restore kļūda:", e)
        return "Backup ir bojāts vai nav nolasāms."


def backup_count(user_id):
    conn = get_db()
    c = conn.cursor()
    db_execute(c, "SELECT COUNT(*) FROM memory_backups WHERE user_id = %s", (user_id,))
    count = c.fetchone()[0]
    c.close()
    conn.close()

    return f"📦 Tev ir {count} backup."


def backup_stats(user_id):
    conn = get_db()
    c = conn.cursor()
    db_execute(
        c,
        """
        SELECT COUNT(*), MIN(created_at), MAX(created_at)
        FROM memory_backups
        WHERE user_id = %s
        """,
        (user_id,)
    )
    count, first_created, last_created = c.fetchone()
    c.close()
    conn.close()

    if not count:
        return "Backup vēl nav izveidoti."

    return (
        f"📦 Backup kopā: {count}\n"
        f"📅 Pirmais: {first_created}\n"
        f"📅 Pēdējais: {last_created}"
    )


def latest_backup_info(user_id):
    conn = get_db()
    c = conn.cursor()
    db_execute(
        c,
        """
        SELECT id, source, created_at
        FROM memory_backups
        WHERE user_id = %s
        ORDER BY id DESC
        LIMIT 1
        """,
        (user_id,)
    )
    row = c.fetchone()
    c.close()
    conn.close()

    if not row:
        return "Backup vēl nav izveidots."

    backup_id, source, created_at = row
    return (
        f"📦 Jaunākais backup #{backup_id}\n"
        f"Avots: {source}\n"
        f"Laiks: {created_at}"
    )


def delete_backup(user_id, text):
    m = re.search(r"(\d+)", text)
    if not m:
        return "Norādi backup numuru. Piemērs: dzēs backup 3"

    backup_id = int(m.group(1))

    conn = get_db()
    c = conn.cursor()
    db_execute(
        c,
        "DELETE FROM memory_backups WHERE id = %s AND user_id = %s",
        (backup_id, user_id)
    )
    deleted = c.rowcount
    conn.commit()
    c.close()
    conn.close()

    if deleted:
        return f"🗑️ Backup #{backup_id} izdzēsts."

    return "Tādu backup neatradu."


def delete_all_backups(user_id):
    conn = get_db()
    c = conn.cursor()
    db_execute(
        c,
        "DELETE FROM memory_backups WHERE user_id = %s",
        (user_id,)
    )
    deleted = c.rowcount
    conn.commit()
    c.close()
    conn.close()

    return f"⚠️ Izdzēsti {deleted} backup."


def is_premium_user(user_id):
    user = get_user(user_id)
    return bool(user.get("premium"))


def backup_count_number(user_id):
    conn = get_db()
    c = conn.cursor()
    db_execute(c, "SELECT COUNT(*) FROM memory_backups WHERE user_id = %s", (user_id,))
    count = c.fetchone()[0]
    c.close()
    conn.close()
    return int(count or 0)


def active_reminder_count(user_id):
    conn = get_db()
    c = conn.cursor()
    db_execute(
        c,
        "SELECT COUNT(*) FROM reminders WHERE user_id = %s AND status = 'active'",
        (user_id,)
    )
    count = c.fetchone()[0]
    c.close()
    conn.close()
    return int(count or 0)


def summaries_used_today(user_id):
    user = get_user(user_id)
    updated = user.get("summary_updated_at", "")
    if not updated:
        return 0
    today = datetime.now(ZoneInfo(user["timezone"])).strftime("%Y-%m-%d")
    return 1 if updated.startswith(today) else 0


def premium_features(user_id=None):
    """V11.1: Premium funkciju pārskats ar skaidru CTA."""
    return (
        "💎 Premium funkcijas\n\n"
        "Ar Premium Nina kļūst par nopietnu ikdienas palīgu:\n\n"
        "✅ Backup bez limita\n"
        "✅ Aktīvie atgādinājumi bez limita\n"
        "✅ Kopsavilkumi bez limita\n"
        "✅ Vairāk vietas ilgtermiņa atmiņai\n"
        "✅ Premium Dashboard\n"
        "✅ Prioritāras nākotnes funkcijas\n\n"
        "Cena:\n"
        f"Basic — {PREMIUM_BASIC_PRICE:.2f} {PREMIUM_CURRENCY}/mēn\n"
        f"Plus — {PREMIUM_PLUS_PRICE:.2f} {PREMIUM_CURRENCY}/mēn\n\n"
        "Sākt:\n"
        "pirkt basic\n"
        "pirkt plus\n\n"
        "Versija: V11.5"
    )



def premium_limits(user_id):
    user = get_user(user_id)
    backups = backup_count_number(user_id)
    reminders = active_reminder_count(user_id)
    summaries_today = summaries_used_today(user_id)

    if user.get("premium"):
        return (
            "💎 Tavs Premium režīms:\n"
            "• Backup: bez limita\n"
            "• Atgādinājumi: bez limita\n"
            "• Kopsavilkumi: bez limita"
        )

    return (
        "Bezmaksas limiti:\n"
        f"• Backup: {backups}/{FREE_BACKUP_LIMIT}\n"
        f"• Aktīvie atgādinājumi: {reminders}/{FREE_REMINDER_LIMIT}\n"
        f"• Kopsavilkumi šodien: {summaries_today}/{FREE_SUMMARY_LIMIT_PER_DAY}\n\n"
        "Lai noņemtu limitus, raksti: premium"
    )


def memory_usage(user_id):
    return premium_limits(user_id)


def user_statistics(user_id):
    user = get_user(user_id)

    conn = get_db()
    c = conn.cursor()

    db_execute(c, "SELECT COUNT(*) FROM messages WHERE user_id = %s", (user_id,))
    messages_count = int(c.fetchone()[0] or 0)

    db_execute(c, "SELECT COUNT(*) FROM memory_backups WHERE user_id = %s", (user_id,))
    backups_count = int(c.fetchone()[0] or 0)

    db_execute(
        c,
        "SELECT COUNT(*) FROM reminders WHERE user_id = %s AND status = 'active'",
        (user_id,)
    )
    active_reminders = int(c.fetchone()[0] or 0)

    db_execute(
        c,
        "SELECT COUNT(*) FROM reminders WHERE user_id = %s",
        (user_id,)
    )
    total_reminders = int(c.fetchone()[0] or 0)

    db_execute(
        c,
        "SELECT MIN(created_at) FROM messages WHERE user_id = %s",
        (user_id,)
    )
    first_message_at = c.fetchone()[0]

    c.close()
    conn.close()

    premium_text = "aktīvs" if user.get("premium") else "neaktīvs"
    if user.get("premium") and user.get("premium_until"):
        premium_text += f" līdz {user['premium_until']}"

    account_text = str(first_message_at) if first_message_at else "vēl nav sarunu vēstures"

    return (
        "📊 Tava Nina statistika\n\n"
        f"💬 Ziņas: {messages_count}\n"
        f"📦 Backup: {backups_count}\n"
        f"⏰ Aktīvie atgādinājumi: {active_reminders}\n"
        f"⏱️ Atgādinājumi kopā: {total_reminders}\n"
        f"📅 Pirmā saruna: {account_text}\n"
        f"💎 Premium: {premium_text}\n"
        f"🏆 Līmenis: {calculate_level(user.get('xp', 0))}\n"
        f"⭐ XP: {int(user.get('xp', 0) or 0)}"
    )


def user_activity(user_id):
    since_24h = (datetime.utcnow() - timedelta(hours=24)).strftime("%Y-%m-%d %H:%M:%S")

    conn = get_db()
    c = conn.cursor()

    db_execute(
        c,
        "SELECT COUNT(*) FROM messages WHERE user_id = %s AND created_at >= %s",
        (user_id, since_24h)
    )
    messages_24h = int(c.fetchone()[0] or 0)

    db_execute(
        c,
        "SELECT COUNT(*) FROM messages WHERE user_id = %s",
        (user_id,)
    )
    messages_total = int(c.fetchone()[0] or 0)

    db_execute(
        c,
        "SELECT COUNT(*) FROM memory_backups WHERE user_id = %s",
        (user_id,)
    )
    backups_total = int(c.fetchone()[0] or 0)

    db_execute(
        c,
        "SELECT COUNT(*) FROM reminders WHERE user_id = %s AND status = 'active'",
        (user_id,)
    )
    active_reminders = int(c.fetchone()[0] or 0)

    c.close()
    conn.close()

    if messages_24h >= 10:
        note = "Tu Ninu šodien lieto aktīvi. 🚀"
    elif messages_total > 0:
        note = "Tu Ninu jau sāc lietot regulāri. 🌷"
    else:
        note = "Sarunu vēsture vēl tikai sākas. 🌱"

    return (
        "📈 Tava aktivitāte\n\n"
        f"Ziņas pēdējās 24h: {messages_24h}\n"
        f"Ziņas kopā: {messages_total}\n"
        f"Backup kopā: {backups_total}\n"
        f"Aktīvie atgādinājumi: {active_reminders}\n\n"
        f"{note}"
    )


def user_memory_stats(user_id):
    user = get_user(user_id)

    fields = [
        ("Vārds", "name"),
        ("Pilsēta", "city"),
        ("Patīk", "hobbies"),
        ("Svarīgi fakti", "facts"),
        ("Mērķi", "goals"),
        ("Projekti", "projects"),
        ("Sapņi", "dreams"),
        ("Svarīgi datumi", "important_dates"),
        ("Mājdzīvnieki", "pets"),
        ("Ģimene", "family"),
        ("Profesija", "profession"),
        ("Mīļākais auto", "favorite_car"),
        ("Mīļākā krāsa", "favorite_color"),
        ("Mīļākā mūzika", "favorite_music"),
        ("Kopsavilkums", "summary"),
    ]

    filled = sum(1 for _, key in fields if user.get(key))
    total = len(fields)
    percent = int((filled / total) * 100) if total else 0

    lines = [
        "🧠 Atmiņas pārskats",
        "",
        f"Aizpildīti lauki: {filled}/{total}",
        f"Atmiņas aizpildījums: {percent}%",
        ""
    ]

    for label, key in fields:
        mark = "✅" if user.get(key) else "❌"
        lines.append(f"• {label}: {mark}")

    return "\n".join(lines)




def memory_fill_percent(user_id):
    user = get_user(user_id)
    fields = [
        "name", "city", "hobbies", "facts", "goals", "projects", "dreams",
        "important_dates", "pets", "family", "profession", "favorite_car",
        "favorite_color", "favorite_music", "summary"
    ]
    filled = sum(1 for key in fields if user.get(key))
    total = len(fields)
    return int((filled / total) * 100) if total else 0


def premium_dashboard(user_id):
    user = get_user(user_id)
    xp = int(user.get("xp", 0) or 0)
    level = calculate_level(xp)
    backups = backup_count_number(user_id)
    active_reminders = active_reminder_count(user_id)
    summaries_today = summaries_used_today(user_id)
    memory_percent = memory_fill_percent(user_id)
    achievements_total = achievement_count(user_id)
    streak_days = int(user.get("streak_days", 0) or 0)

    conn = get_db()
    c = conn.cursor()
    db_execute(c, "SELECT COUNT(*) FROM messages WHERE user_id = %s", (user_id,))
    messages_count = int(c.fetchone()[0] or 0)
    db_execute(c, "SELECT COUNT(*) FROM reminders WHERE user_id = %s", (user_id,))
    reminders_total = int(c.fetchone()[0] or 0)
    c.close()
    conn.close()

    lines = ["💎 Nina Premium Dashboard", ""]

    if user.get("premium"):
        lines.append("Statuss: Premium aktīvs")
        lines.append(f"Plāns: {current_plan_name(user_id)}")
        if user.get("premium_until"):
            lines.append(f"Beidzas: {user['premium_until']}")
        lines.extend([
            "",
            "Limiti:",
            "📦 Backup: bez limita",
            "⏰ Atgādinājumi: bez limita",
            "🧠 Kopsavilkumi: bez limita",
        ])
    else:
        lines.extend([
            "Statuss: Free režīms",
            f"Plāns: {PLAN_FREE}",
            "",
            "Limiti:",
            f"📦 Backup: {backups}/{FREE_BACKUP_LIMIT}",
            f"⏰ Aktīvie atgādinājumi: {active_reminders}/{FREE_REMINDER_LIMIT}",
            f"🧠 Kopsavilkumi šodien: {summaries_today}/{FREE_SUMMARY_LIMIT_PER_DAY}",
        ])

    lines.extend([
        "",
        "Lojalitāte:",
        f"🏆 Līmenis: {level}",
        f"⭐ XP: {xp}",
        f"🏅 Sasniegumi: {achievements_total}",
        f"🔥 Streak: {streak_days} dienas",
        f"➡️ Līdz nākamajam līmenim: {xp_for_next_level(xp)} XP",
        "",
        "Lietošana:",
        f"💬 Ziņas: {messages_count}",
        f"📦 Backup: {backups}",
        f"⏰ Aktīvie atgādinājumi: {active_reminders}",
        f"⏱️ Atgādinājumi kopā: {reminders_total}",
        f"🧠 Atmiņas aizpildījums: {memory_percent}%",
    ])

    if not user.get("premium"):
        lines.extend(["", "Lai noņemtu limitus, raksti: premium"])

    return "\n".join(lines)

def premium_paywall(title, used_text, premium_value):
    return (
        f"💎 {title}\n\n"
        f"Bezmaksas režīmā: {used_text}.\n"
        f"Premium režīmā: {premium_value}.\n\n"
        "Ja Nina tev jau palīdz ikdienā, Premium noņem ierobežojumus un ļauj lietot viņu nopietnāk.\n"
        "Raksti: aktivizē premium"
    )


def can_create_backup(user_id):
    if is_premium_user(user_id):
        return True, ""
    count = backup_count_number(user_id)
    if count >= FREE_BACKUP_LIMIT:
        return False, premium_paywall(
            "Backup limits sasniegts",
            f"{FREE_BACKUP_LIMIT} backup",
            "backup bez limita"
        )
    return True, ""


def can_create_reminder(user_id):
    if is_premium_user(user_id):
        return True, ""
    count = active_reminder_count(user_id)
    if count >= FREE_REMINDER_LIMIT:
        return False, premium_paywall(
            "Atgādinājumu limits sasniegts",
            f"{FREE_REMINDER_LIMIT} aktīvi atgādinājumi",
            "atgādinājumi bez limita"
        )
    return True, ""


def can_create_summary(user_id):
    if is_premium_user(user_id):
        return True, ""
    used = summaries_used_today(user_id)
    if used >= FREE_SUMMARY_LIMIT_PER_DAY:
        return False, premium_paywall(
            "Šodienas kopsavilkuma limits izmantots",
            f"{FREE_SUMMARY_LIMIT_PER_DAY} kopsavilkums dienā",
            "kopsavilkumi bez limita"
        )
    return True, ""


def premium_status(user_id):
    """V11.1: Premium statuss ar skaidru nākamo soli."""
    user = get_user(user_id)

    if user.get("premium"):
        plan = current_plan_name(user_id)
        until = user.get("premium_until") or "bez beigu datuma"
        return (
            "💎 Premium statuss\n\n"
            "Statuss: aktīvs\n"
            f"Plāns: {plan}\n"
            f"Aktīvs līdz: {until}\n\n"
            "Komandas:\n"
            "premium panelis\n"
            "premium vēsture\n"
            "mans plāns\n\n"
            "Versija: V11.5"
        )

    return premium_conversion_answer(user_id)



def activate_premium(user_id):
    user = get_user(user_id)
    until = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")

    user["premium"] = 1
    user["premium_until"] = until

    update_user(user_id, user)

    record_premium_transaction(
        user_id=user_id,
        plan_name=PLAN_PREMIUM_BASIC,
        amount=PREMIUM_BASIC_PRICE,
        currency=PREMIUM_CURRENCY,
        payment_method="test",
        status="test_active",
        expires_at=until,
    )

    achievements = check_achievements(user_id)
    return append_bonus_notices(f"💎 Premium aktivizēts testa režīmā līdz {until}.", achievements)


def deactivate_premium(user_id):
    user = get_user(user_id)
    user["premium"] = 0
    user["premium_until"] = ""
    update_user(user_id, user)
    return "Premium izslēgts testa režīmā."


def parse_reminder(user_text, user_tz_name):
    text = user_text.strip()
    lower = text.lower()
    task = re.sub(r"^atgādini man\s+", "", text, flags=re.IGNORECASE).strip()

    user_tz = ZoneInfo(user_tz_name)
    now_local = datetime.now(user_tz)

    remind_date = None
    remind_time = None

    if "rīt" in lower:
        remind_date = now_local + timedelta(days=1)
        task = re.sub(r"\brīt\b", "", task, flags=re.IGNORECASE).strip()
    elif "parīt" in lower:
        remind_date = now_local + timedelta(days=2)
        task = re.sub(r"\bparīt\b", "", task, flags=re.IGNORECASE).strip()
    elif "šodien" in lower:
        remind_date = now_local
        task = re.sub(r"\bšodien\b", "", task, flags=re.IGNORECASE).strip()

    date_match = re.search(r"(\d{1,2})\.\s*datumā", lower)
    if date_match:
        day = int(date_match.group(1))
        month = now_local.month
        year = now_local.year
        try:
            candidate = datetime(year, month, day, tzinfo=user_tz)
            if candidate.date() < now_local.date():
                candidate = datetime(year + 1, 1, day, tzinfo=user_tz) if month == 12 else datetime(year, month + 1, day, tzinfo=user_tz)
            remind_date = candidate
        except ValueError:
            pass
        task = re.sub(r"\d{1,2}\.\s*datumā", "", task, flags=re.IGNORECASE).strip()

    time_match = re.search(r"(\d{1,2})[:.](\d{2})", lower)
    if time_match:
        hour = int(time_match.group(1))
        minute = int(time_match.group(2))
        remind_time = (hour, minute)
        task = re.sub(r"\d{1,2}[:.]\d{2}", "", task).strip()

    if remind_date:
        local_dt = remind_date.replace(
            hour=remind_time[0] if remind_time else 9,
            minute=remind_time[1] if remind_time else 0,
            second=0,
            microsecond=0
        )
        utc_dt = local_dt.astimezone(timezone.utc)
        return clean_text(task) or "Atgādinājums", utc_dt.strftime("%Y-%m-%d %H:%M"), local_dt.strftime("%Y-%m-%d %H:%M")

    return clean_text(task) or "Atgādinājums", "", ""


def add_reminder(user_id, user_text):
    allowed, message = can_create_reminder(user_id)
    if not allowed:
        return message

    user = get_user(user_id)
    task, remind_at_utc, local_time_text = parse_reminder(user_text, user["timezone"])

    conn = get_db()
    c = conn.cursor()
    if USE_POSTGRES:
        db_execute(c,
            "INSERT INTO reminders (user_id, text, remind_at, local_time, status) VALUES (%s, %s, %s, %s, %s) RETURNING id",
            (user_id, task, remind_at_utc, local_time_text, "active")
        )
        reminder_id = c.fetchone()[0]
    else:
        db_execute(c,
            "INSERT INTO reminders (user_id, text, remind_at, local_time, status) VALUES (%s, %s, %s, %s, %s)",
            (user_id, task, remind_at_utc, local_time_text, "active")
        )
        reminder_id = c.lastrowid
    conn.commit()
    c.close()
    conn.close()

    add_xp(user_id, 3)

    if local_time_text:
        return f"Pierakstīju atgādinājumu #{reminder_id}: {task}\nLaiks: {local_time_text} ({user['timezone']})"
    return f"Pierakstīju atgādinājumu #{reminder_id}: {task}"


def list_reminders(user_id):
    user = get_user(user_id)
    conn = get_db()
    c = conn.cursor()
    db_execute(c, 
        "SELECT id, text, local_time, remind_at FROM reminders WHERE user_id = %s AND status = 'active' ORDER BY id DESC",
        (user_id,)
    )
    rows = c.fetchall()
    c.close()
    conn.close()

    if not rows:
        return "Tev pagaidām nav aktīvu atgādinājumu. 😊"

    lines = ["Tavi atgādinājumi:"]
    for rid, text, local_time, remind_at in rows:
        shown_time = local_time or remind_at
        lines.append(f"• #{rid} — {text}" + (f" ({shown_time}, {user['timezone']})" if shown_time else ""))
    return "\n".join(lines)


def delete_reminder(user_id, user_text):
    match = re.search(r"(\d+)", user_text)
    if not match:
        return "Pasaki atgādinājuma numuru. Piemēram: dzēs atgādinājumu 3"

    reminder_id = int(match.group(1))
    conn = get_db()
    c = conn.cursor()
    db_execute(c, "UPDATE reminders SET status = 'deleted' WHERE id = %s AND user_id = %s", (reminder_id, user_id))
    changed = c.rowcount
    conn.commit()
    c.close()
    conn.close()

    return f"Izdzēsu atgādinājumu #{reminder_id}." if changed else "Tādu aktīvu atgādinājumu neatradu."


async def reminder_worker(application):
    while True:
        try:
            now_utc = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M")
            conn = get_db()
            c = conn.cursor()
            db_execute(c, """
                SELECT id, user_id, text FROM reminders
                WHERE status = 'active' AND remind_at != '' AND remind_at <= %s
            """, (now_utc,))
            rows = c.fetchall()

            for reminder_id, user_id, text in rows:
                try:
                    await application.bot.send_message(chat_id=int(user_id), text=f"🌷 Atgādinājums:\n{text}", disable_web_page_preview=True)
                    db_execute(c, "UPDATE reminders SET status = 'sent' WHERE id = %s", (reminder_id,))
                    conn.commit()
                except Exception as e:
                    print("Atgādinājuma sūtīšanas kļūda:", e)

            c.close()
            conn.close()
        except Exception as e:
            print("Reminder worker kļūda:", e)

        await asyncio.sleep(30)


async def post_init(application):
    init_backup_scheduler()
    asyncio.create_task(reminder_worker(application))
    asyncio.create_task(auto_backup_worker(application))




def admin_revenue_forecast(user_id, command_text="revenue forecast"):
    """V10.24: Admin Revenue Forecast — vienkārša MRR un 12 mēnešu ieņēmumu prognoze."""
    if not is_admin(user_id):
        log_admin_action(user_id, "revenue_forecast_view", "denied", command_text)
        return admin_locked_answer()

    log_admin_action(user_id, "revenue_forecast_view", "allowed", command_text)

    conn = get_db()
    c = conn.cursor()

    def scalar(sql, params=()):
        try:
            db_execute(c, sql, params)
            row = c.fetchone()
            return row[0] if row else 0
        except Exception as e:
            print("Revenue forecast scalar kļūda:", e)
            return 0

    premium_users = int(scalar("""
        SELECT COUNT(*)
        FROM users
        WHERE premium = 1
    """) or 0)

    paid_total = float(scalar("""
        SELECT COALESCE(SUM(amount), 0)
        FROM premium_transactions
        WHERE status = 'paid'
    """) or 0)

    paid_count = int(scalar("""
        SELECT COUNT(*)
        FROM premium_transactions
        WHERE status = 'paid'
    """) or 0)

    checkout_created = int(scalar("""
        SELECT COUNT(*)
        FROM premium_transactions
        WHERE status IN ('checkout_created', 'checkout_ready_static')
    """) or 0)

    basic_paid_users = int(scalar("""
        SELECT COUNT(DISTINCT user_id)
        FROM premium_transactions
        WHERE status = 'paid' AND plan_name = %s
    """, (PLAN_PREMIUM_BASIC,)) or 0)

    plus_paid_users = int(scalar("""
        SELECT COUNT(DISTINCT user_id)
        FROM premium_transactions
        WHERE status = 'paid' AND plan_name = %s
    """, (PLAN_PREMIUM_PLUS,)) or 0)

    admin_granted = int(scalar("""
        SELECT COUNT(*)
        FROM premium_transactions
        WHERE status IN ('admin_granted', 'admin_removed')
    """) or 0)

    last_30_revenue = float(scalar("""
        SELECT COALESCE(SUM(amount), 0)
        FROM premium_transactions
        WHERE status = 'paid'
        AND created_at >= datetime('now', '-30 days')
    """) or 0)

    # Bāzes MRR no apmaksātajiem plāniem. Ja nav apmaksātu plānu, bet ir premium lietotāji,
    # konservatīvi rēķinām tos kā Basic, lai panelī būtu saprotama prognoze.
    mrr = basic_paid_users * PREMIUM_BASIC_PRICE + plus_paid_users * PREMIUM_PLUS_PRICE
    if mrr == 0 and premium_users > 0:
        mrr = premium_users * PREMIUM_BASIC_PRICE

    forecast_30_days = mrr
    forecast_90_days = mrr * 3
    forecast_12_months = mrr * 12

    avg_paid = (paid_total / paid_count) if paid_count else 0.0
    conversion_hint = 0.0
    if checkout_created:
        conversion_hint = min(100.0, (paid_count / checkout_created) * 100.0)

    c.close()
    conn.close()

    status = "Nav pietiekami datu" if paid_count == 0 and premium_users == 0 else "OK"

    return (
        "📈 Nina Revenue Forecast\n\n"
        "Pašreizējā bāze:\n"
        f"Premium lietotāji: {premium_users}\n"
        f"Apmaksāti darījumi: {paid_count}\n"
        f"Kopējie ieņēmumi: {paid_total:.2f} {PREMIUM_CURRENCY}\n"
        f"Vidējais maksājums: {avg_paid:.2f} {PREMIUM_CURRENCY}\n\n"
        "Plānu sadalījums:\n"
        f"🥉 Basic: {basic_paid_users}\n"
        f"🥈 Plus: {plus_paid_users}\n"
        f"Admin izmaiņas: {admin_granted}\n\n"
        "Prognoze:\n"
        f"MRR: {mrr:.2f} {PREMIUM_CURRENCY}\n"
        f"30 dienas: {forecast_30_days:.2f} {PREMIUM_CURRENCY}\n"
        f"90 dienas: {forecast_90_days:.2f} {PREMIUM_CURRENCY}\n"
        f"12 mēneši: {forecast_12_months:.2f} {PREMIUM_CURRENCY}\n\n"
        "Pēdējās 30 dienas:\n"
        f"Ieņēmumi: {last_30_revenue:.2f} {PREMIUM_CURRENCY}\n"
        f"Checkout konversijas signāls: {conversion_hint:.1f}%\n\n"
        f"Statuss: {status}\n"
        "Versija: V11.5"
    )


NINA_PROMPT = """
Tu esi Nina 7727.

Tu esi silta, gudra, interesanta un dabiska sarunu biedrene.
Tu neesi parasts bots. Tu esi sajūta, pie kuras cilvēkam gribas atgriezties.

Noteikumi:
- Vienmēr runā latviešu valodā.
- Nerunā kā robots vai klientu atbalsts.
- Neatkārto "Sveiks!" katrā atbildē.
- Neizdomā faktus par lietotāju.
- Ja runā par lietotāju, balsties tikai uz profilu, ilgtermiņa kopsavilkumu un sarunas vēsturi.
- Ja profilā ir mērķi/projekti/sapņi, vari tos dabiski izmantot sarunā.
- Neatkārto visu profilu katrā atbildē.
- Atbildi īsi, dzīvi, sirsnīgi.
- Ja cilvēkam ir stress, nomierini.
- Vari būt viegli asprātīga un silta.
- Tavs mērķis: lai cilvēkam pēc sarunas ar tevi kļūst vieglāk.
"""


COMMAND_LINES = {
    "mans premium statuss", "premium statuss", "premium",
    "premium funkcijas", "premium limiti", "cik atmiņas man palicis", "premium beidzas",
    "abonements", "mans plāns", "mans plans", "premium vēsture", "premium vesture",
    "premium welcome", "premium sveiciens", "premium starts", "premium sveiks",
    "pirkt premium", "pirkt basic", "pirkt premium basic", "pirkt plus", "pirkt premium plus", "stripe statuss",
    "stripe setup", "stripe env", "stripe palīgs", "stripe paligs", "stripe helper", "maksājumi", "maksajumi", "payment setup", "stripe helper", "maksājumi", "maksajumi", "payment setup",
    "revenue", "ieņēmumi", "ienemumi", "admin panelis", "premium ieņēmumi", "premium ienemumi",
    "revenue analytics", "income analytics", "premium analytics", "ieņēmumu analītika", "ienemumu analitika",
    "revenue forecast", "income forecast", "mrr forecast", "ieņēmumu prognoze", "ienemumu prognoze",
    "launch", "launch dashboard", "production", "production launch", "palaišana", "palaisana",
    "admin logs", "audit logs", "admin žurnāls", "admin zurnals",
    "audit stats", "admin statistika", "admin stats",
    "health", "system status", "sistēmas statuss", "sistemas statuss", "veselība", "veseliba",
    "analytics", "lietotāju statistika", "lietotaju statistika", "user stats", "user analytics",
    "db backup", "database backup", "backup stats", "datubāzes backup", "datubazes backup",
    "auto backup", "backup scheduler", "backup grafiks", "automātiskais backup", "automatiskais backup",
    "recovery", "recovery center", "restore backup", "backup restore", "restore latest",
    "admin", "admin center", "admin command center", "command center", "dashboard",
    "user management", "admin users", "user dashboard", "lietotāju panelis", "lietotaju panelis",
    "mana statistika", "mana aktivitāte", "mana atmiņa",
    "premium panelis", "mans panelis",
    "mans līmenis", "mana pieredze", "xp",
    "mani sasniegumi", "sasniegumi", "sasniegumu progress",
    "mans streak", "mana sērija", "streak",
    "aktivizē premium", "aktivize premium", "ieslēdz premium",
    "izslēdz premium", "atslēdz premium",
    "eksportē atmiņu", "atmiņas eksports", "export memory", "eksports",
    "backup", "izveido backup", "rezerves kopija", "izveido rezerves kopiju",
    "pēdējais backup", "parādi backup", "mans backup", "pēdējā rezerves kopija",
    "backup saraksts", "parādi backup sarakstu", "mani backup",
    "cik man ir backup", "backup statistika", "jaunākais backup",
    "dzēs backup", "izdzēs backup", "dzēs visus backup", "izdzēs visus backup",
    "mani atgādinājumi", "parādi atgādinājumus", "atgādinājumi",
    "atjauno kopsavilkumu", "izveido kopsavilkumu", "atjauno atmiņu",
    "mans kopsavilkums", "parādi kopsavilkumu", "ilgtermiņa atmiņa",
    "ko tu par mani zini", "ko tu par manīm zini", "ko tu par mani atceries",
    "ko tu par manīm atceries", "ko tu atceries", "kas man patīk",
    "ko par mani zini", "ko par manīm zini",
}


def is_command_line(line):
    lower = line.strip().lower()
    return (
        lower in COMMAND_LINES
        or lower.startswith("atgādini man")
        or lower.startswith("dzēs atgādinājumu")
        or lower.startswith("izdzēs atgādinājumu")
        or lower.startswith("aizmirsti atgādinājumu")
        or lower.startswith("aizmirsti")
        or lower.startswith("atjauno no backup")
        or lower.startswith("grant premium")
        or lower.startswith("remove premium")
        or lower.startswith("add xp")
        or lower.startswith("remove xp")
        or lower.startswith("set level")
        or lower.startswith("reset streak")
        or lower == "user actions"
        or lower in ["alerts", "admin alerts", "system alerts"]
        or lower in ["launch", "launch dashboard", "production", "production launch"]
        or lower.startswith("dzēs backup")
        or lower.startswith("izdzēs backup")
    )


def split_profile_and_commands(text):
    profile_lines = []
    command_lines = []

    for line in text.splitlines():
        clean_line = line.strip()
        if not clean_line:
            continue
        if is_command_line(clean_line):
            command_lines.append(clean_line)
        else:
            profile_lines.append(clean_line)

    return "\n".join(profile_lines), command_lines



def admin_kpi_dashboard(user_id, command_text="kpi"):
    """V10.24: Admin KPI Dashboard — vienots biznesa un sistēmas KPI panelis."""
    if not is_admin(user_id):
        log_admin_action(user_id, "admin_kpi_view", "denied", command_text)
        return admin_locked_answer()

    log_admin_action(user_id, "admin_kpi_view", "allowed", command_text)

    users_total = _count_table_rows("users")
    premium_users = _count_table_rows("users", "WHERE premium = 1")
    free_users = max(0, users_total - premium_users)

    messages_total = _count_table_rows("messages")
    backups_total = _count_table_rows("memory_backups")
    reminders_total = _count_table_rows("reminders")
    active_reminders = _count_table_rows("reminders", "WHERE status = %s", ("active",))
    audit_total = _count_table_rows("admin_audit_logs")
    premium_transactions_total = _count_table_rows("premium_transactions")

    conn = get_db()
    c = conn.cursor()

    def scalar(sql, params=()):
        try:
            db_execute(c, sql, params)
            row = c.fetchone()
            return row[0] if row else 0
        except Exception as e:
            print("KPI scalar kļūda:", e)
            return 0

    try:
        total_revenue = float(scalar("""
            SELECT COALESCE(SUM(amount), 0)
            FROM premium_transactions
            WHERE status = 'paid'
        """) or 0)

        paid_count = int(scalar("""
            SELECT COUNT(*)
            FROM premium_transactions
            WHERE status = 'paid'
        """) or 0)

        basic_users = int(scalar("""
            SELECT COUNT(DISTINCT user_id)
            FROM premium_transactions
            WHERE status = 'paid' AND plan_name = %s
        """, (PLAN_PREMIUM_BASIC,)) or 0)

        plus_users = int(scalar("""
            SELECT COUNT(DISTINCT user_id)
            FROM premium_transactions
            WHERE status = 'paid' AND plan_name = %s
        """, (PLAN_PREMIUM_PLUS,)) or 0)

        checkout_created = int(scalar("""
            SELECT COUNT(*)
            FROM premium_transactions
            WHERE status IN ('checkout_created', 'checkout_ready_static')
        """) or 0)

        xp_total = int(scalar("""
            SELECT COALESCE(SUM(xp), 0)
            FROM users
        """) or 0)

        avg_level = float(scalar("""
            SELECT COALESCE(AVG(level), 0)
            FROM users
        """) or 0)

    finally:
        c.close()
        conn.close()

    mrr = basic_users * PREMIUM_BASIC_PRICE + plus_users * PREMIUM_PLUS_PRICE
    db_ok = _database_health_ok()
    admin_lock_ready = admin_access_configured()
    openai_ok = bool(os.environ.get("OPENAI_API_KEY"))
    telegram_ok = bool(TELEGRAM_TOKEN)

    system_status = "OK" if db_ok and openai_ok and telegram_ok else "Jāpārbauda"
    admin_status = "Aktīvs" if admin_lock_ready else "Nav konfigurēts"

    conversion_rate = 0.0
    if users_total > 0:
        conversion_rate = (premium_users / users_total) * 100

    return (
        "📌 Nina Admin KPI Dashboard\n\n"
        "Bizness:\n"
        f"Ieņēmumi kopā: {total_revenue:.2f} {PREMIUM_CURRENCY}\n"
        f"MRR: {mrr:.2f} {PREMIUM_CURRENCY}\n"
        f"Apmaksāti darījumi: {paid_count}\n"
        f"Checkout mēģinājumi: {checkout_created}\n\n"
        "Lietotāji:\n"
        f"Lietotāji kopā: {users_total}\n"
        f"Premium lietotāji: {premium_users}\n"
        f"Free lietotāji: {free_users}\n"
        f"Premium konversija: {conversion_rate:.1f}%\n\n"
        "Plāni:\n"
        f"🥉 Basic: {basic_users}\n"
        f"🥈 Plus: {plus_users}\n\n"
        "Aktivitāte:\n"
        f"Ziņas kopā: {messages_total}\n"
        f"Backup kopā: {backups_total}\n"
        f"Atgādinājumi kopā: {reminders_total}\n"
        f"Aktīvie atgādinājumi: {active_reminders}\n\n"
        "Lojalitāte:\n"
        f"XP kopā: {xp_total}\n"
        f"Vidējais līmenis: {avg_level:.1f}\n\n"
        "Sistēma:\n"
        f"Datubāze: {'OK' if db_ok else 'ERROR'}\n"
        f"Telegram: {'OK' if telegram_ok else 'Missing Token'}\n"
        f"OpenAI: {'OK' if openai_ok else 'Missing Key'}\n"
        f"Admin Lock: {admin_status}\n"
        f"Audit ieraksti: {audit_total}\n"
        f"Premium darījumi: {premium_transactions_total}\n\n"
        f"Statuss: {system_status}\n"
        "Versija: V11.5"
    )


def admin_alerts_dashboard(user_id, command_text="alerts"):
    """V10.25: Admin Alerts Dashboard — drošības, backup, recovery un maksājumu brīdinājumi."""
    if not is_admin(user_id):
        log_admin_action(user_id, "admin_alerts_view", "denied", command_text)
        return admin_locked_answer()

    log_admin_action(user_id, "admin_alerts_view", "allowed", command_text)

    conn = get_db()
    c = conn.cursor()

    def scalar(sql, params=()):
        try:
            db_execute(c, sql, params)
            row = c.fetchone()
            return int(row[0] or 0) if row else 0
        except Exception as e:
            print("Admin alerts scalar kļūda:", e)
            return 0

    try:
        denied_admin = scalar("""
            SELECT COUNT(*)
            FROM admin_audit_logs
            WHERE status = 'denied'
        """)

        recent_denied = scalar("""
            SELECT COUNT(*)
            FROM admin_audit_logs
            WHERE status = 'denied'
              AND created_at >= datetime('now', '-24 hours')
        """)

        auto_backup_errors = scalar("""
            SELECT COUNT(*)
            FROM admin_audit_logs
            WHERE action = %s AND status IN (%s, %s, %s)
        """, ("auto_backup_run", "failed", "error", "failed_no_backup"))

        restore_errors = scalar("""
            SELECT COUNT(*)
            FROM admin_audit_logs
            WHERE action IN (%s, %s)
               OR command_text = %s
        """, ("backup_restore_failed", "backup_restore_attempt", "no_user_backup"))

        payment_errors = scalar("""
            SELECT COUNT(*)
            FROM premium_transactions
            WHERE status IN ('payment_failed', 'checkout_error', 'stripe_checkout_error', 'failed')
        """)

        checkout_pending = scalar("""
            SELECT COUNT(*)
            FROM premium_transactions
            WHERE status IN ('checkout_created', 'checkout_ready_static')
        """)

        total_audit = scalar("SELECT COUNT(*) FROM admin_audit_logs")

        try:
            db_execute(c, """
                SELECT created_at, user_id, action, status, command_text
                FROM admin_audit_logs
                WHERE status IN ('denied', 'failed', 'error')
                   OR action IN ('auto_backup_run', 'backup_restore_failed')
                ORDER BY id DESC
                LIMIT 5
            """)
            recent_rows = c.fetchall()
        except Exception as e:
            print("Admin alerts recent kļūda:", e)
            recent_rows = []
    finally:
        c.close()
        conn.close()

    db_ok = _database_health_ok()
    telegram_ok = bool(TELEGRAM_TOKEN)
    openai_ok = bool(os.environ.get("OPENAI_API_KEY"))
    admin_ready = admin_access_configured()

    system_errors = 0
    if not db_ok:
        system_errors += 1
    if not telegram_ok:
        system_errors += 1
    if not openai_ok:
        system_errors += 1
    if not admin_ready:
        system_errors += 1

    total_alerts = denied_admin + auto_backup_errors + restore_errors + payment_errors + system_errors

    if payment_errors or auto_backup_errors or restore_errors or not db_ok:
        severity = "🔴 Kritiska pārbaude"
    elif denied_admin or checkout_pending or system_errors:
        severity = "🟡 Jāpārbauda"
    else:
        severity = "🟢 OK"

    lines = [
        "🚨 Nina Admin Alerts",
        "",
        "Kritiskums:",
        severity,
        "",
        "Drošība:",
        f"Bloķēti admin mēģinājumi: {denied_admin}",
        f"Bloķēti pēdējās 24h: {recent_denied}",
        "",
        "Backup / Recovery:",
        f"Auto backup kļūdas: {auto_backup_errors}",
        f"Restore kļūdas: {restore_errors}",
        "",
        "Maksājumi:",
        f"Maksājumu kļūdas: {payment_errors}",
        f"Nepabeigti checkout: {checkout_pending}",
        "",
        "Sistēma:",
        f"Datubāze: {'OK' if db_ok else 'ERROR'}",
        f"Telegram: {'OK' if telegram_ok else 'Missing Token'}",
        f"OpenAI: {'OK' if openai_ok else 'Missing Key'}",
        f"Admin Lock: {'Aktīvs' if admin_ready else 'Nav konfigurēts'}",
        "",
        "Pēdējie brīdinājumi:",
    ]

    if recent_rows:
        for created_at, logged_user_id, action, status, cmd in recent_rows:
            lines.append(f"• {created_at} — {action or 'unknown'} / {status or 'unknown'} / user: {logged_user_id}")
            if cmd:
                lines.append(f"  command: {cmd}")
    else:
        lines.append("• Nav brīdinājumu.")

    lines.extend([
        "",
        f"Kopā alert skaits: {total_alerts}",
        f"Audit ieraksti kopā: {total_audit}",
        "Versija: V11.5",
    ])

    return "\n".join(lines)


def admin_launch_dashboard(user_id, command_text="launch"):
    """V11.1: Premium Conversion System — produkta palaišanas un monetizācijas pārskats."""
    if not is_admin(user_id):
        log_admin_action(user_id, "production_launch_view", "denied", command_text)
        return admin_locked_answer()

    log_admin_action(user_id, "production_launch_view", "allowed", command_text)

    users_total = _count_table_rows("users")
    premium_users = _count_table_rows("users", "WHERE premium = 1")
    free_users = max(0, users_total - premium_users)
    messages_total = _count_table_rows("messages")
    audit_total = _count_table_rows("admin_audit_logs")

    conn = get_db()
    c = conn.cursor()

    def scalar(sql, params=()):
        try:
            db_execute(c, sql, params)
            row = c.fetchone()
            return row[0] if row else 0
        except Exception as e:
            print("Launch dashboard scalar kļūda:", e)
            return 0

    try:
        total_revenue = float(scalar("""
            SELECT COALESCE(SUM(amount), 0)
            FROM premium_transactions
            WHERE status = 'paid'
        """) or 0)

        paid_count = int(scalar("""
            SELECT COUNT(*)
            FROM premium_transactions
            WHERE status = 'paid'
        """) or 0)

        basic_paid_users = int(scalar("""
            SELECT COUNT(DISTINCT user_id)
            FROM premium_transactions
            WHERE status = 'paid' AND plan_name = %s
        """, (PLAN_PREMIUM_BASIC,)) or 0)

        plus_paid_users = int(scalar("""
            SELECT COUNT(DISTINCT user_id)
            FROM premium_transactions
            WHERE status = 'paid' AND plan_name = %s
        """, (PLAN_PREMIUM_PLUS,)) or 0)

        checkout_created = int(scalar("""
            SELECT COUNT(*)
            FROM premium_transactions
            WHERE status IN ('checkout_created', 'checkout_ready_static')
        """) or 0)

        checkout_completed = paid_count

        admin_granted = int(scalar("""
            SELECT COUNT(*)
            FROM premium_transactions
            WHERE status = 'admin_granted'
        """) or 0)

        latest_paid = None
        try:
            db_execute(c, """
                SELECT created_at, user_id, plan_name, amount, currency, payment_method, status
                FROM premium_transactions
                WHERE status IN ('paid', 'admin_granted')
                ORDER BY id DESC
                LIMIT 1
            """)
            latest_paid = c.fetchone()
        except Exception as e:
            print("Launch latest paid kļūda:", e)
            latest_paid = None

    finally:
        c.close()
        conn.close()

    mrr = basic_paid_users * PREMIUM_BASIC_PRICE + plus_paid_users * PREMIUM_PLUS_PRICE
    if mrr == 0 and premium_users > 0:
        mrr = premium_users * PREMIUM_BASIC_PRICE

    user_conversion = 0.0
    if users_total > 0:
        user_conversion = (premium_users / users_total) * 100.0

    checkout_conversion = 0.0
    if checkout_created > 0:
        checkout_conversion = (checkout_completed / checkout_created) * 100.0

    db_ok = _database_health_ok()
    telegram_ok = bool(TELEGRAM_TOKEN)
    openai_ok = bool(os.environ.get("OPENAI_API_KEY"))
    admin_ready = admin_access_configured()

    stripe_ready = bool(STRIPE_SECRET_KEY and (STRIPE_BASIC_PRICE_ID or STRIPE_BASIC_CHECKOUT_URL) and (STRIPE_PLUS_PRICE_ID or STRIPE_PLUS_CHECKOUT_URL))
    webhook_ready = bool(STRIPE_WEBHOOK_SECRET)

    if db_ok and telegram_ok and openai_ok and admin_ready:
        launch_status = "🟢 Ready"
    elif db_ok and telegram_ok and openai_ok:
        launch_status = "🟡 Gandrīz gatavs"
    else:
        launch_status = "🔴 Jāpārbauda"

    lines = [
        "🚀 Nina Production Launch",
        "",
        "Launch statuss:",
        launch_status,
        "",
        "Lietotāji:",
        f"Lietotāji kopā: {users_total}",
        f"Premium lietotāji: {premium_users}",
        f"Free lietotāji: {free_users}",
        f"Premium konversija: {user_conversion:.1f}%",
        "",
        "Ieņēmumi:",
        f"Ieņēmumi kopā: {total_revenue:.2f} {PREMIUM_CURRENCY}",
        f"MRR: {mrr:.2f} {PREMIUM_CURRENCY}",
        f"Apmaksāti darījumi: {paid_count}",
        f"Admin piešķirti Premium: {admin_granted}",
        "",
        "Checkout Funnel:",
        f"Checkout izveidoti: {checkout_created}",
        f"Checkout pabeigti: {checkout_completed}",
        f"Checkout konversija: {checkout_conversion:.1f}%",
        "",
        "Plāni:",
        f"🥉 Basic klienti: {basic_paid_users}",
        f"🥈 Plus klienti: {plus_paid_users}",
        "",
        "Sistēma:",
        f"Datubāze: {'OK' if db_ok else 'ERROR'}",
        f"Telegram: {'OK' if telegram_ok else 'Missing Token'}",
        f"OpenAI: {'OK' if openai_ok else 'Missing Key'}",
        f"Admin Lock: {'Aktīvs' if admin_ready else 'Nav konfigurēts'}",
        f"Stripe Checkout: {'✅' if stripe_ready else '❌'}",
        f"Stripe Webhook: {'✅' if webhook_ready else '❌'}",
        "",
        "Aktivitāte:",
        f"Ziņas kopā: {messages_total}",
        f"Audit ieraksti: {audit_total}",
        "",
        "Pēdējais Premium notikums:",
    ]

    if latest_paid:
        created_at, latest_user_id, plan_name, amount, currency, method, status = latest_paid
        lines.append(str(created_at))
        lines.append(f"user_id: {latest_user_id}")
        lines.append(f"plāns: {plan_name or '—'}")
        lines.append(f"summa: {float(amount or 0):.2f} {currency or PREMIUM_CURRENCY}")
        lines.append(f"metode: {method or '—'}")
        lines.append(f"statuss: {status or '—'}")
    else:
        lines.append("Vēl nav Premium notikumu.")

    lines.extend([
        "",
        "Nākamie soļi:",
        "1. Ieliec Railway ENV: ADMIN_USER_IDS=5138563912",
        "2. Pabeidz Stripe checkout un webhook ENV",
        "3. Notestē: pirkt premium / pirkt plus",
        "4. Aicini pirmos 5–10 lietotājus",
        "",
        "Versija: V11.5",
    ])

    return "\n".join(lines)

def command_answer(user_id, command_text):
    lower = command_text.strip().lower()

    if lower in ["premium", "aktivizē premium", "aktivize premium", "pirkt premium", "premium info"]:
        return premium_conversion_answer(user_id)

    if lower in ["mans premium statuss", "premium statuss"]:
        return premium_status(user_id)

    if lower in ["premium funkcijas"]:
        return premium_features(user_id)

    if lower in ["premium limiti", "cik atmiņas man palicis"]:
        return premium_limits(user_id)

    if lower == "premium beidzas":
        return premium_expiration_info(user_id)

    if lower in ["abonements", "premium cena", "cena", "plāni", "plani"]:
        return subscription_info(user_id)

    if lower in ["mans plāns", "mans plans"]:
        return current_plan_answer(user_id)

    if lower in ["premium vēsture", "premium vesture"]:
        return premium_history(user_id)

    if lower in ["premium welcome", "premium sveiciens", "premium starts", "premium sveiks"]:
        return premium_welcome_answer(user_id)

    if lower in ["pirkt basic", "pirkt premium basic"]:
        return premium_buy_intent_answer(user_id, "basic")

    if lower in ["pirkt plus", "pirkt premium plus"]:
        return premium_buy_intent_answer(user_id, "plus")

    if lower == "stripe statuss":
        return stripe_status(user_id)

    if lower in ["stripe setup", "stripe env", "stripe palīgs", "stripe paligs", "stripe helper", "maksājumi", "maksajumi", "payment setup"]:
        return stripe_setup_helper(user_id)

    if lower in ["revenue", "ieņēmumi", "ienemumi", "admin panelis", "premium ieņēmumi", "premium ienemumi"]:
        return admin_revenue_dashboard(user_id, lower)

    if lower in ["revenue analytics", "income analytics", "premium analytics", "ieņēmumu analītika", "ienemumu analitika"]:
        return admin_revenue_analytics(user_id, lower)

    if lower in ["revenue forecast", "income forecast", "mrr forecast", "ieņēmumu prognoze", "ienemumu prognoze"]:
        return admin_revenue_forecast(user_id, lower)

    if lower in ["kpi", "admin kpi", "business dashboard", "admin kpi dashboard", "kpi dashboard", "biznesa panelis"]:
        return admin_kpi_dashboard(user_id, lower)

    if lower in ["alerts", "admin alerts", "system alerts", "brīdinājumi", "bridinajumi", "admin brīdinājumi", "admin bridinajumi"]:
        return admin_alerts_dashboard(user_id, lower)

    if lower in ["launch", "launch dashboard", "production", "production launch", "palaišana", "palaisana"]:
        return admin_launch_dashboard(user_id, lower)

    if lower in ["admin logs", "audit logs", "admin žurnāls", "admin zurnals"]:
        return admin_audit_log_answer(user_id)

    if lower in ["audit stats", "admin statistika", "admin stats"]:
        return admin_audit_stats_answer(user_id)

    if lower in ["health", "system status", "sistēmas statuss", "sistemas statuss", "veselība", "veseliba"]:
        return system_health_answer(user_id, lower)

    if lower in ["analytics", "lietotāju statistika", "lietotaju statistika", "user stats", "user analytics"]:
        return user_analytics_answer(user_id, lower)

    if lower in ["db backup", "database backup", "backup stats", "datubāzes backup", "datubazes backup"]:
        return database_backup_dashboard(user_id, lower)

    if lower in ["auto backup", "backup scheduler", "backup grafiks", "automātiskais backup", "automatiskais backup"]:
        return backup_scheduler_answer(user_id, lower)

    if lower in ["recovery", "recovery center", "restore backup", "backup restore"]:
        return recovery_center_answer(user_id, lower)

    if lower in ["restore latest", "atjauno pēdējo", "atjauno pedejo"]:
        return restore_latest_backup(user_id, lower)

    if lower in ["admin notifications", "notifications", "paziņojumi", "pazinojumi", "admin paziņojumi", "admin pazinojumi"]:
        return admin_notifications_center(user_id, lower)

    if lower in ["activity", "admin activity", "activity feed", "aktivitāte", "aktivitate"]:
        return admin_activity_feed(user_id, lower)

    if lower in ["user management", "admin users", "user dashboard", "lietotāju panelis", "lietotaju panelis"]:
        return admin_user_management_dashboard(user_id, command_text)

    if (
        lower == "user actions"
        or lower.startswith("grant premium")
        or lower.startswith("remove premium")
        or lower.startswith("add xp")
        or lower.startswith("remove xp")
        or lower.startswith("set level")
        or lower.startswith("reset streak")
    ):
        return admin_user_action(user_id, command_text)

    if (
        lower.startswith("search user")
        or lower.startswith("find user")
        or lower.startswith("meklēt lietotāju")
        or lower.startswith("meklet lietotaju")
        or lower in ["lietotāji", "lietotaji"]
    ):
        return admin_user_search(user_id, command_text)

    if (
        lower in ["user lookup", "lietotājs", "lietotajs", "meklēt lietotāju", "meklet lietotaju"]
        or lower.startswith("user ")
        or lower.startswith("user lookup ")
        or lower.startswith("lietotājs ")
        or lower.startswith("lietotajs ")
        or lower.startswith("meklēt lietotāju ")
        or lower.startswith("meklet lietotaju ")
    ):
        return admin_user_lookup(user_id, command_text)

    if lower in ["admin", "admin center", "admin command center", "command center", "dashboard"]:
        return admin_command_center(user_id, lower)

    if lower in ["premium panelis", "mans panelis"]:
        return premium_dashboard(user_id)

    if lower in ["mans līmenis", "mana pieredze", "xp"]:
        return user_level_info(user_id)

    if lower in ["mani sasniegumi", "sasniegumi"]:
        return achievements_answer(user_id)

    if lower == "sasniegumu progress":
        return achievement_progress(user_id)

    if lower in ["mans streak", "mana sērija", "streak"]:
        return streak_info(user_id)

    if lower == "mana statistika":
        return user_statistics(user_id)

    if lower == "mana aktivitāte":
        return user_activity(user_id)

    if lower == "mana atmiņa":
        return user_memory_stats(user_id)

    if lower in ["aktivizē premium", "aktivize premium", "ieslēdz premium"]:
        return activate_premium(user_id)

    if lower in ["izslēdz premium", "atslēdz premium"]:
        return deactivate_premium(user_id)

    if lower in ["eksportē atmiņu", "atmiņas eksports", "export memory", "eksports"]:
        return build_memory_export(user_id)

    if lower in ["backup", "izveido backup", "rezerves kopija", "izveido rezerves kopiju"]:
        return create_backup_answer(user_id)

    if lower in ["pēdējais backup", "parādi backup", "mans backup", "pēdējā rezerves kopija"]:
        return latest_backup_answer(user_id)

    if lower in ["backup saraksts", "parādi backup sarakstu", "mani backup"]:
        return list_backups(user_id)

    if lower in ["cik man ir backup"]:
        return backup_count(user_id)

    if lower in ["backup statistika"]:
        return backup_stats(user_id)

    if lower in ["jaunākais backup"]:
        return latest_backup_info(user_id)

    if lower in ["dzēs visus backup", "izdzēs visus backup"]:
        return delete_all_backups(user_id)

    if lower.startswith("dzēs backup") or lower.startswith("izdzēs backup"):
        return delete_backup(user_id, command_text)

    if lower.startswith("atjauno no backup"):
        return restore_backup(user_id, command_text)

    if lower.startswith("atgādini man"):
        return add_reminder(user_id, command_text)

    if lower in ["mani atgādinājumi", "parādi atgādinājumus", "atgādinājumi"]:
        return list_reminders(user_id)

    if lower.startswith("dzēs atgādinājumu") or lower.startswith("izdzēs atgādinājumu"):
        return delete_reminder(user_id, command_text)

    if lower.startswith("aizmirsti atgādinājumu"):
        return delete_reminder(user_id, command_text)

    if lower.startswith("aizmirsti"):
        return forget_from_profile(user_id, command_text)

    if lower in ["atjauno kopsavilkumu", "izveido kopsavilkumu", "atjauno atmiņu"]:
        return build_summary(user_id)

    if lower in ["mans kopsavilkums", "parādi kopsavilkumu", "ilgtermiņa atmiņa"]:
        return show_summary(user_id)

    if lower in [
        "ko tu par mani zini", "ko tu par manīm zini",
        "ko tu par mani atceries", "ko tu par manīm atceries",
        "ko tu atceries", "kas man patīk",
        "ko par mani zini", "ko par manīm zini"
    ]:
        return profile_answer(get_user(user_id))

    return None


async def reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text
    user_id = str(update.effective_user.id)
    lower = user_text.strip().lower()
    streak_notice = update_daily_streak(user_id)

    profile_text, command_lines = split_profile_and_commands(user_text)
    if command_lines and profile_text.strip():
        update_profile_from_text(user_id, profile_text)
        answers = []
        for command in command_lines:
            answer = command_answer(user_id, command)
            if answer:
                answers.append(answer)
        if answers:
            await update.message.reply_text("\n\n".join(answers), disable_web_page_preview=True)
            return

    if lower in ["mans premium statuss", "premium statuss", "premium"]:
        await update.message.reply_text(premium_status(user_id), disable_web_page_preview=True)
        return

    if lower in ["premium funkcijas"]:
        await update.message.reply_text(premium_features(user_id), disable_web_page_preview=True)
        return

    if lower in ["premium limiti", "cik atmiņas man palicis"]:
        await update.message.reply_text(premium_limits(user_id), disable_web_page_preview=True)
        return

    if lower == "premium beidzas":
        await update.message.reply_text(premium_expiration_info(user_id), disable_web_page_preview=True)
        return

    if lower == "abonements":
        await update.message.reply_text(append_bonus_notices(subscription_info(user_id), streak_notice), disable_web_page_preview=True)
        return

    if lower in ["mans plāns", "mans plans"]:
        await update.message.reply_text(append_bonus_notices(current_plan_answer(user_id), streak_notice), disable_web_page_preview=True)
        return

    if lower in ["premium vēsture", "premium vesture"]:
        await update.message.reply_text(append_bonus_notices(premium_history(user_id), streak_notice), disable_web_page_preview=True)
        return

    # V10.5.2 HARD FIX: catch Premium Welcome as a direct Telegram command
    # before it can fall through to GPT chat mode.
    if lower in ["premium welcome", "premium sveiciens", "premium starts", "premium sveiks"]:
        await update.message.reply_text(append_bonus_notices(premium_welcome_answer(user_id), streak_notice), disable_web_page_preview=True)
        return

    if lower in ["pirkt premium", "pirkt basic", "pirkt premium basic"]:
        await update.message.reply_text(append_bonus_notices(stripe_checkout_answer(user_id, "basic"), streak_notice), disable_web_page_preview=True)
        return

    if lower in ["pirkt plus", "pirkt premium plus"]:
        await update.message.reply_text(append_bonus_notices(stripe_checkout_answer(user_id, "plus"), streak_notice), disable_web_page_preview=True)
        return

    if lower == "stripe statuss":
        await update.message.reply_text(append_bonus_notices(stripe_status(user_id), streak_notice), disable_web_page_preview=True)
        return

    # V10.5.2: keep Stripe helper commands direct too, not only in command_answer().
    if lower in ["stripe setup", "stripe env", "stripe palīgs", "stripe paligs", "stripe helper", "maksājumi", "maksajumi", "payment setup"]:
        await update.message.reply_text(append_bonus_notices(stripe_setup_helper(user_id), streak_notice), disable_web_page_preview=True)
        return

    if lower in ["revenue", "ieņēmumi", "ienemumi", "admin panelis", "premium ieņēmumi", "premium ienemumi"]:
        await update.message.reply_text(append_bonus_notices(admin_revenue_dashboard(user_id, lower), streak_notice), disable_web_page_preview=True)
        return

    if lower in ["revenue analytics", "income analytics", "premium analytics", "ieņēmumu analītika", "ienemumu analitika"]:
        await update.message.reply_text(append_bonus_notices(admin_revenue_analytics(user_id, lower), streak_notice), disable_web_page_preview=True)
        return

    if lower in ["revenue forecast", "income forecast", "mrr forecast", "ieņēmumu prognoze", "ienemumu prognoze"]:
        await update.message.reply_text(append_bonus_notices(admin_revenue_forecast(user_id, lower), streak_notice), disable_web_page_preview=True)
        return

    # V10.25: KPI command routing fix — catch KPI before GPT fallback.
    if lower in ["kpi", "admin kpi", "business dashboard", "admin kpi dashboard", "kpi dashboard", "biznesa panelis"]:
        await update.message.reply_text(append_bonus_notices(admin_kpi_dashboard(user_id, lower), streak_notice), disable_web_page_preview=True)
        return

    # V11.1: Alerts command routing fix — catch Alerts before GPT fallback.
    if lower in ["alerts", "admin alerts", "system alerts", "brīdinājumi", "bridinajumi", "admin brīdinājumi", "admin bridinajumi"]:
        await update.message.reply_text(append_bonus_notices(admin_alerts_dashboard(user_id, lower), streak_notice), disable_web_page_preview=True)
        return

    # V11.1: Premium Conversion System routing — catch launch before GPT fallback.
    if lower in ["launch", "launch dashboard", "production", "production launch", "palaišana", "palaisana"]:
        await update.message.reply_text(append_bonus_notices(admin_launch_dashboard(user_id, lower), streak_notice), disable_web_page_preview=True)
        return

    if lower in ["admin logs", "audit logs", "admin žurnāls", "admin zurnals"]:
        await update.message.reply_text(append_bonus_notices(admin_audit_log_answer(user_id), streak_notice), disable_web_page_preview=True)
        return

    if lower in ["audit stats", "admin statistika", "admin stats"]:
        await update.message.reply_text(append_bonus_notices(admin_audit_stats_answer(user_id), streak_notice), disable_web_page_preview=True)
        return

    if lower in ["health", "system status", "sistēmas statuss", "sistemas statuss", "veselība", "veseliba"]:
        await update.message.reply_text(append_bonus_notices(system_health_answer(user_id, lower), streak_notice), disable_web_page_preview=True)
        return

    if lower in ["analytics", "lietotāju statistika", "lietotaju statistika", "user stats", "user analytics"]:
        await update.message.reply_text(append_bonus_notices(user_analytics_answer(user_id, lower), streak_notice), disable_web_page_preview=True)
        return

    if lower in ["db backup", "database backup", "backup stats", "datubāzes backup", "datubazes backup"]:
        await update.message.reply_text(append_bonus_notices(database_backup_dashboard(user_id, lower), streak_notice), disable_web_page_preview=True)
        return

    if lower in ["auto backup", "backup scheduler", "backup grafiks", "automātiskais backup", "automatiskais backup"]:
        await update.message.reply_text(append_bonus_notices(backup_scheduler_answer(user_id, lower), streak_notice), disable_web_page_preview=True)
        return

    if lower in ["recovery", "recovery center", "restore backup", "backup restore"]:
        await update.message.reply_text(append_bonus_notices(recovery_center_answer(user_id, lower), streak_notice), disable_web_page_preview=True)
        return

    if lower in ["restore latest", "atjauno pēdējo", "atjauno pedejo"]:
        await update.message.reply_text(append_bonus_notices(restore_latest_backup(user_id, lower), streak_notice), disable_web_page_preview=True)
        return

    if lower in ["admin notifications", "notifications", "paziņojumi", "pazinojumi", "admin paziņojumi", "admin pazinojumi"]:
        await update.message.reply_text(append_bonus_notices(admin_notifications_center(user_id, lower), streak_notice), disable_web_page_preview=True)
        return

    if lower in ["activity", "admin activity", "activity feed", "aktivitāte", "aktivitate"]:
        await update.message.reply_text(append_bonus_notices(admin_activity_feed(user_id, lower), streak_notice), disable_web_page_preview=True)
        return

    if lower in ["user management", "admin users", "user dashboard", "lietotāju panelis", "lietotaju panelis"]:
        await update.message.reply_text(append_bonus_notices(admin_user_management_dashboard(user_id, user_text), streak_notice), disable_web_page_preview=True)
        return

    if (
        lower == "user actions"
        or lower.startswith("grant premium")
        or lower.startswith("remove premium")
        or lower.startswith("add xp")
        or lower.startswith("remove xp")
        or lower.startswith("set level")
        or lower.startswith("reset streak")
    ):
        await update.message.reply_text(append_bonus_notices(admin_user_action(user_id, user_text), streak_notice), disable_web_page_preview=True)
        return

    if (
        lower.startswith("search user")
        or lower.startswith("find user")
        or lower.startswith("meklēt lietotāju")
        or lower.startswith("meklet lietotaju")
        or lower in ["lietotāji", "lietotaji"]
    ):
        await update.message.reply_text(append_bonus_notices(admin_user_search(user_id, user_text), streak_notice), disable_web_page_preview=True)
        return

    if (
        lower in ["user lookup", "lietotājs", "lietotajs", "meklēt lietotāju", "meklet lietotaju"]
        or lower.startswith("user ")
        or lower.startswith("user lookup ")
        or lower.startswith("lietotājs ")
        or lower.startswith("lietotajs ")
        or lower.startswith("meklēt lietotāju ")
        or lower.startswith("meklet lietotaju ")
    ):
        await update.message.reply_text(append_bonus_notices(admin_user_lookup(user_id, user_text), streak_notice), disable_web_page_preview=True)
        return

    # V10.24 Command Routing Fix:
    # Admin Command Center komandām jānostrādā pirms premium dashboard un pirms GPT fallback.
    if lower in ["admin", "admin center", "admin command center", "command center", "dashboard"]:
        await update.message.reply_text(append_bonus_notices(admin_command_center(user_id, lower), streak_notice), disable_web_page_preview=True)
        return

    if lower in ["premium panelis", "mans panelis"]:
        await update.message.reply_text(append_bonus_notices(premium_dashboard(user_id), streak_notice, check_achievements(user_id)), disable_web_page_preview=True)
        return

    if lower in ["mans līmenis", "mana pieredze", "xp"]:
        await update.message.reply_text(append_bonus_notices(user_level_info(user_id), streak_notice, check_achievements(user_id)), disable_web_page_preview=True)
        return

    if lower in ["mani sasniegumi", "sasniegumi"]:
        await update.message.reply_text(append_bonus_notices(achievements_answer(user_id), streak_notice, check_achievements(user_id)), disable_web_page_preview=True)
        return

    if lower == "sasniegumu progress":
        await update.message.reply_text(append_bonus_notices(achievement_progress(user_id), streak_notice), disable_web_page_preview=True)
        return

    if lower in ["mans streak", "mana sērija", "streak"]:
        await update.message.reply_text(append_bonus_notices(streak_info(user_id), check_achievements(user_id)), disable_web_page_preview=True)
        return

    if lower == "mana statistika":
        await update.message.reply_text(user_statistics(user_id), disable_web_page_preview=True)
        return

    if lower == "mana aktivitāte":
        await update.message.reply_text(user_activity(user_id), disable_web_page_preview=True)
        return

    if lower == "mana atmiņa":
        await update.message.reply_text(user_memory_stats(user_id), disable_web_page_preview=True)
        return

    if lower in ["aktivizē premium", "aktivize premium", "ieslēdz premium"]:
        await update.message.reply_text(activate_premium(user_id), disable_web_page_preview=True)
        return

    if lower in ["izslēdz premium", "atslēdz premium"]:
        await update.message.reply_text(deactivate_premium(user_id), disable_web_page_preview=True)
        return

    if lower in ["eksportē atmiņu", "atmiņas eksports", "export memory", "eksports"]:
        await update.message.reply_text(build_memory_export(user_id), disable_web_page_preview=True)
        return

    if lower in ["backup", "izveido backup", "rezerves kopija", "izveido rezerves kopiju"]:
        await update.message.reply_text(create_backup_answer(user_id), disable_web_page_preview=True)
        return

    if lower in ["pēdējais backup", "parādi backup", "mans backup", "pēdējā rezerves kopija"]:
        await update.message.reply_text(latest_backup_answer(user_id), disable_web_page_preview=True)
        return

    if lower in ["backup saraksts", "parādi backup sarakstu", "mani backup"]:
        await update.message.reply_text(list_backups(user_id), disable_web_page_preview=True)
        return

    if lower in ["cik man ir backup"]:
        await update.message.reply_text(backup_count(user_id), disable_web_page_preview=True)
        return

    if lower in ["backup statistika"]:
        await update.message.reply_text(backup_stats(user_id), disable_web_page_preview=True)
        return

    if lower in ["jaunākais backup"]:
        await update.message.reply_text(latest_backup_info(user_id), disable_web_page_preview=True)
        return

    if lower in ["dzēs visus backup", "izdzēs visus backup"]:
        await update.message.reply_text(delete_all_backups(user_id), disable_web_page_preview=True)
        return

    if lower.startswith("dzēs backup") or lower.startswith("izdzēs backup"):
        await update.message.reply_text(delete_backup(user_id, user_text), disable_web_page_preview=True)
        return

    if lower.startswith("atjauno no backup"):
        await update.message.reply_text(restore_backup(user_id, user_text), disable_web_page_preview=True)
        return

    if lower.startswith("atgādini man"):
        await update.message.reply_text(add_reminder(user_id, user_text), disable_web_page_preview=True)
        return

    if lower in ["mani atgādinājumi", "parādi atgādinājumus", "atgādinājumi"]:
        await update.message.reply_text(list_reminders(user_id), disable_web_page_preview=True)
        return

    if lower.startswith("dzēs atgādinājumu") or lower.startswith("izdzēs atgādinājumu"):
        await update.message.reply_text(delete_reminder(user_id, user_text), disable_web_page_preview=True)
        return

    if lower.startswith("aizmirsti atgādinājumu"):
        await update.message.reply_text(delete_reminder(user_id, user_text), disable_web_page_preview=True)
        return

    if lower.startswith("aizmirsti"):
        await update.message.reply_text(forget_from_profile(user_id, user_text), disable_web_page_preview=True)
        return

    if lower in ["atjauno kopsavilkumu", "izveido kopsavilkumu", "atjauno atmiņu"]:
        await update.message.reply_text(build_summary(user_id), disable_web_page_preview=True)
        return

    if lower in ["mans kopsavilkums", "parādi kopsavilkumu", "ilgtermiņa atmiņa"]:
        await update.message.reply_text(show_summary(user_id), disable_web_page_preview=True)
        return

    update_profile_from_text(user_id, user_text)
    user = get_user(user_id)

    if "mana laika zona" in lower or "kur es dzīvoju" in lower or "es dzīvoju" in lower:
        await update.message.reply_text(f"Saglabāju. Tava laika zona: {user['timezone']}", disable_web_page_preview=True)
        return

    if "kā mani sauc" in lower:
        await update.message.reply_text(f"Tevi sauc {user['name']}. 😊" if user["name"] else "Tu vēl neesi pateicis savu vārdu. 😊", disable_web_page_preview=True)
        return

    if (
        "ko tu par mani zini" in lower
        or "ko tu par manīm zini" in lower
        or "ko tu par mani atceries" in lower
        or "ko tu par manīm atceries" in lower
        or "ko tu atceries" in lower
        or "kas man patīk" in lower
        or "ko par mani zini" in lower
        or "ko par manīm zini" in lower
    ):
        await update.message.reply_text(profile_answer(user), disable_web_page_preview=True)
        return

    save_message(user_id, "Lietotājs", user_text)
    add_xp(user_id, 1)
    user = get_user(user_id)
    conversation = get_recent_messages(user_id)

    profile_info = f"""
Lietotāja profils:
Vārds: {user["name"]}
Pilsēta: {user["city"]}
Laika zona: {user["timezone"]}
Patīk: {user["hobbies"]}
Svarīgi fakti: {user["facts"]}
Mērķi: {user["goals"]}
Projekti: {user["projects"]}
Sapņi: {user["dreams"]}
Svarīgi datumi: {user["important_dates"]}
Mājdzīvnieki: {user["pets"]}
Ģimene: {user["family"]}
Profesija: {user["profession"]}
Mīļākais auto: {user["favorite_car"]}
Mīļākā krāsa: {user["favorite_color"]}
Mīļākā mūzika: {user["favorite_music"]}
Premium: {user["premium"]}
Premium līdz: {user["premium_until"]}

Ilgtermiņa kopsavilkums:
{user["summary"]}
Kopsavilkums atjaunots:
{user.get("summary_updated_at", "")}
"""

    try:
        response = client.responses.create(
            model="gpt-4.1-mini",
            input=(
                f"{NINA_PROMPT}\n\n"
                f"{profile_info}\n\n"
                f"Sarunas vēsture:\n{conversation}\n\n"
                f"Atbildi uz pēdējo ziņu dabiski."
            )
        )
        answer = response.output_text

    except Exception as e:
        print("Kļūda:", e)
        answer = "Piedod, man šobrīd kaut kas aizķērās. Pamēģini vēlreiz pēc brīža. 🌷"

    achievements = check_achievements(user_id)
    answer = append_bonus_notices(answer, streak_notice, achievements)
    save_message(user_id, "Nina", answer)
    await update.message.reply_text(answer, disable_web_page_preview=True)


@app.route("/stripe/webhook", methods=["POST"])
def stripe_webhook():
    if not stripe:
        return jsonify({"error": "stripe library missing"}), 500

    payload = request.get_data(as_text=False)
    sig_header = request.headers.get("Stripe-Signature", "")

    try:
        if STRIPE_WEBHOOK_SECRET:
            event = stripe.Webhook.construct_event(payload, sig_header, STRIPE_WEBHOOK_SECRET)
        else:
            event = json.loads(payload.decode("utf-8"))
    except Exception as e:
        print("Stripe webhook signature/json kļūda:", e)
        return jsonify({"error": "invalid webhook"}), 400

    event_id = event.get("id", "")
    event_type = event.get("type", "")

    if event_id and stripe_event_seen(event_id):
        return jsonify({"ok": True, "duplicate": True})

    if event_type == "checkout.session.completed":
        session = (event.get("data") or {}).get("object") or {}
        user_id = user_id_from_stripe_session(session)

        if not user_id:
            print("Stripe webhook: nav user_id metadata/client_reference_id")
            return jsonify({"ok": False, "error": "missing user_id"}), 200

        plan_name, amount, currency = plan_from_stripe_session(session)
        customer_details = session.get("customer_details") or {}
        customer_email = customer_details.get("email", "")
        stripe_session_id = session.get("id", "")

        until, achievements = activate_paid_premium(
            user_id=user_id,
            plan_name=plan_name,
            amount=amount,
            currency=currency,
            payment_method="stripe",
            stripe_session_id=stripe_session_id,
            stripe_event_id=event_id,
            customer_email=customer_email,
        )

        print(f"Stripe webhook: Premium aktivizēts user_id={user_id}, plan={plan_name}, līdz={until}. Welcome ready: premium welcome")
        if achievements:
            print("Stripe achievements:", achievements)

        return jsonify({"ok": True, "premium_until": until})

    # Atzīmējam citus Stripe eventus tikai logā; Premium nemainām.
    print("Stripe webhook ignored:", event_type)
    return jsonify({"ok": True, "ignored": event_type})


@app.route("/success")
def payment_success_page():
    return """
    <!doctype html>
    <html lang="lv">
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <title>Nina Premium aktivizēšana</title>
        <style>
            body { font-family: Arial, sans-serif; background: #f7f7fb; margin: 0; padding: 40px; color: #222; }
            .card { max-width: 560px; margin: 0 auto; background: white; padding: 32px; border-radius: 18px; box-shadow: 0 8px 30px rgba(0,0,0,0.08); }
            h1 { margin-top: 0; color: #1f8f4d; }
            p { line-height: 1.55; font-size: 17px; }
            .cmd { background: #f0f0f5; padding: 12px 14px; border-radius: 10px; font-family: monospace; display: inline-block; }
        </style>
    </head>
    <body>
        <div class="card">
            <h1>✅ Maksājums saņemts</h1>
            <p>Paldies! Ja Stripe webhook ir pieslēgts, Nina Premium tiks aktivizēts automātiski.</p>
            <p>Atgriezies Telegram un palaid Premium sveicienu:</p>
            <p><span class="cmd">premium welcome</span></p>
            <p>Pēc tam vari pārbaudīt pilno paneli:</p>
            <p><span class="cmd">premium panelis</span></p>
            <p>Ja Premium vēl nerādās uzreiz, pagaidi dažas sekundes un pārbaudi vēlreiz.</p>
        </div>
    </body>
    </html>
    """


@app.route("/cancel")
def payment_cancel_page():
    return """
    <!doctype html>
    <html lang="lv">
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <title>Nina maksājums atcelts</title>
        <style>
            body { font-family: Arial, sans-serif; background: #f7f7fb; margin: 0; padding: 40px; color: #222; }
            .card { max-width: 560px; margin: 0 auto; background: white; padding: 32px; border-radius: 18px; box-shadow: 0 8px 30px rgba(0,0,0,0.08); }
            h1 { margin-top: 0; color: #b23b3b; }
            p { line-height: 1.55; font-size: 17px; }
            .cmd { background: #f0f0f5; padding: 12px 14px; border-radius: 10px; font-family: monospace; display: inline-block; }
        </style>
    </head>
    <body>
        <div class="card">
            <h1>❌ Maksājums atcelts</h1>
            <p>Maksājums netika pabeigts, un Premium netika aktivizēts.</p>
            <p>Vari atgriezties Telegram un mēģināt vēlreiz:</p>
            <p><span class="cmd">pirkt premium</span></p>
            <p>Vai izvēlēties Plus plānu:</p>
            <p><span class="cmd">pirkt plus</span></p>
        </div>
    </body>
    </html>
    """


@app.route("/")
def home():
    return "Nina7727 V11.5 Requirements Helper darbojas! DB: " + ("PostgreSQL" if USE_POSTGRES else "SQLite fallback")


init_db()

telegram_app = (
    Application.builder()
    .token(TELEGRAM_TOKEN)
    .post_init(post_init)
    .build()
)

telegram_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, reply))

if __name__ == "__main__":
    print("Nina7727 V11.5 Requirements Helper darbojas...", "PostgreSQL" if USE_POSTGRES else "SQLite fallback")
    telegram_app.run_polling()


def requirements_helper_answer():
    """V11.5 Requirements Helper — parāda Railway requirements.txt saturu Stripe darbībai."""
    return (
        "📦 Nina Requirements Helper\n\n"
        "Lai Stripe strādātu Railway, projektā vajag requirements.txt ar šo saturu:\n\n"
        "python-telegram-bot\n"
        "flask\n"
        "openai\n"
        "psycopg2-binary\n"
        "stripe\n\n"
        "Pēc tam Railway jāpārdeployo projekts.\n\n"
        "Testē pēc deploy:\n"
        "stripe setup\n"
        "pirkt basic\n\n"
        "Versija: V11.5"
    )

