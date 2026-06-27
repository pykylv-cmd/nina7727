"""
memory.py — V14.2

Atmiņas un dienas mērķu loģika atsevišķā modulī.
Šeit nav Stripe, Premium vai webhook koda.
Datubāzes funkcijas tiek padotas no app.py, lai modulis būtu drošs un viegli testējams.
"""

import re
from datetime import datetime
from zoneinfo import ZoneInfo


def build_memory_saved_answer(saved_text, version="V14.2"):
    return (
        "🧠 Pierakstīju. ✅\n\n"
        f"Atcerēšos: {saved_text}\n\n"
        "Ja vajadzēs, vēlāk varēsim no tā izveidot atgādinājumu vai papildināt šo domu.\n\n"
        f"Versija: {version}"
    )


def build_goal_saved_answer(goal_text, version="V14.2"):
    return (
        "🎯 Saglabāju šodienas mērķi. ✅\n\n"
        f"Mērķis: {goal_text}\n\n"
        "Tagad dienai ir skaidrs virziens. Ja gribi, vari man pastāstīt pirmo mazo soli.\n\n"
        f"Versija: {version}"
    )


def clean_memory_text(memory_text):
    memory_text = (memory_text or "").strip()
    cleaned = re.sub(r"^(nina[, ]*)?atceries[, ]*(ka)?\s*", "", memory_text, flags=re.IGNORECASE).strip()
    return cleaned or memory_text


def save_natural_memory_logic(get_db_fn, db_execute_fn, user_id, memory_text):
    cleaned = clean_memory_text(memory_text)
    if not cleaned:
        return ""

    try:
        conn = get_db_fn()
        c = conn.cursor()
        db_execute_fn(
            c,
            """
            INSERT INTO memory_backups (user_id, backup_text, source)
            VALUES (%s, %s, %s)
            """,
            (str(user_id), cleaned, "natural_memory")
        )
        conn.commit()
        c.close()
        conn.close()
        return cleaned
    except Exception as e:
        print("Natural memory save kļūda:", e)
        return ""


def latest_natural_memories_logic(get_db_fn, db_execute_fn, user_id, limit=3):
    try:
        conn = get_db_fn()
        c = conn.cursor()
        db_execute_fn(
            c,
            """
            SELECT backup_text, created_at
            FROM memory_backups
            WHERE user_id = %s AND source = %s
            ORDER BY id DESC
            LIMIT %s
            """,
            (str(user_id), "natural_memory", int(limit or 3))
        )
        rows = c.fetchall()
        c.close()
        conn.close()
        return rows or []
    except Exception as e:
        print("Natural memories read kļūda:", e)
        return []


def save_daily_goal_logic(get_db_fn, db_execute_fn, default_timezone, user_id, goal_text):
    goal_text = (goal_text or "").strip()
    if not goal_text:
        return False

    today = datetime.now(ZoneInfo(default_timezone)).strftime("%Y-%m-%d")

    try:
        conn = get_db_fn()
        c = conn.cursor()

        # Vienam lietotājam viena aktīva galvenā mērķa rinda dienā.
        db_execute_fn(
            c,
            """
            UPDATE daily_goals
            SET status = %s
            WHERE user_id = %s AND goal_date = %s AND status = %s
            """,
            ("replaced", str(user_id), today, "active")
        )

        db_execute_fn(
            c,
            """
            INSERT INTO daily_goals (user_id, goal_text, goal_date, status)
            VALUES (%s, %s, %s, %s)
            """,
            (str(user_id), goal_text, today, "active")
        )
        conn.commit()
        c.close()
        conn.close()
        return True
    except Exception as e:
        print("Daily goal save kļūda:", e)
        return False


def latest_daily_goals_logic(get_db_fn, db_execute_fn, default_timezone, user_id, limit=3):
    today = datetime.now(ZoneInfo(default_timezone)).strftime("%Y-%m-%d")

    try:
        conn = get_db_fn()
        c = conn.cursor()
        db_execute_fn(
            c,
            """
            SELECT goal_text, status, created_at
            FROM daily_goals
            WHERE user_id = %s AND goal_date = %s AND status = %s
            ORDER BY id DESC
            LIMIT %s
            """,
            (str(user_id), today, "active", int(limit or 3))
        )
        rows = c.fetchall()
        c.close()
        conn.close()
        return rows or []
    except Exception as e:
        print("Daily goals read kļūda:", e)
        return []
