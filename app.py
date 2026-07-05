import os
import re
import json
import sqlite3
import asyncio
import threading
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
from io import BytesIO

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
from telegram.ext import Application, MessageHandler, CommandHandler, filters, ContextTypes
from openai import OpenAI

# Core Evolution 2.0 — Employee Brain Import
try:
    from employee_brain import employee_reply
except Exception as e:
    print("employee_brain.py imports nav pieejams:", e)
    employee_reply = None



# NinaOS Task Engine Import
try:
    from task_engine import detect_task, build_task_saved_answer, task_summary, task_engine_status, TASK_ENGINE_VERSION
except Exception as e:
    print("task_engine.py imports nav pieejams:", e)
    TASK_ENGINE_VERSION = "Task Engine nav pieslēgts"

    def detect_task(text):
        return None

    def build_task_saved_answer(task, user_name=""):
        return ""

    def task_summary(tasks):
        return "Task Engine nav pieslēgts."

    def task_engine_status():
        return "Task Engine nav pieslēgts."



# NinaOS Work Engine Import
try:
    from work_engine import work_plan, work_engine_status, WORK_ENGINE_VERSION
except Exception as e:
    print("work_engine.py imports nav pieejams:", e)
    WORK_ENGINE_VERSION = "Work Engine nav pieslēgts"

    def work_plan(tasks, user_name=""):
        return "Work Engine nav pieslēgts."

    def work_engine_status():
        return "Work Engine nav pieslēgts."



# NinaOS Daily Planner Import
try:
    from daily_planner import build_daily_plan, daily_planner_status, DAILY_PLANNER_VERSION
except Exception as e:
    print("daily_planner.py imports nav pieejams:", e)
    DAILY_PLANNER_VERSION = "Daily Planner nav pieslēgts"

    def build_daily_plan(tasks, user_name=""):
        return "Daily Planner nav pieslēgts."

    def daily_planner_status():
        return "Daily Planner nav pieslēgts."



# NinaOS Relationship Engine Import
try:
    from relationship_engine import (
        detect_relationship,
        build_relationship_saved_answer,
        relationship_summary,
        relationship_engine_status,
        RELATIONSHIP_ENGINE_VERSION,
    )
except Exception as e:
    print("relationship_engine.py imports nav pieejams:", e)
    RELATIONSHIP_ENGINE_VERSION = "Relationship Engine nav pieslēgts"

    def detect_relationship(text):
        return None

    def build_relationship_saved_answer(rel, user_name=""):
        return ""

    def relationship_summary(relationships):
        return "Relationship Engine nav pieslēgts."

    def relationship_engine_status():
        return "Relationship Engine nav pieslēgts."



# NinaOS Client Context Import
try:
    from client_context import (
        enrich_task_with_client_context,
        build_client_context_answer,
        client_context_status,
        CLIENT_CONTEXT_VERSION,
    )
except Exception as e:
    print("client_context.py imports nav pieejams:", e)
    CLIENT_CONTEXT_VERSION = "Client Context nav pieslēgts"

    def enrich_task_with_client_context(task, relationships):
        return task

    def build_client_context_answer(task, relationships):
        return "Client Context nav pieslēgts."

    def client_context_status():
        return "Client Context nav pieslēgts."



# NinaOS Follow-up Engine Import
try:
    from followup_engine import (
        enrich_task_with_followup,
        detect_followup_task,
        build_followup_saved_answer,
        build_followup_status_answer,
        build_followup_context_answer,
        FOLLOWUP_ENGINE_VERSION,
    )
except Exception as e:
    print("followup_engine.py imports nav pieejams:", e)
    FOLLOWUP_ENGINE_VERSION = "Follow-up Engine nav pieslēgts"

    def enrich_task_with_followup(task):
        return task

    def detect_followup_task(text):
        return None

    def build_followup_saved_answer(task):
        return ""

    def build_followup_status_answer():
        return "Follow-up Engine nav pieslēgts."

    def build_followup_context_answer(task):
        return "Follow-up Engine nav pieslēgts."



# NinaOS Task Cleanup Import
try:
    from task_cleanup import (
        find_cleanup_candidates,
        is_active_real_task,
        build_cleanup_preview,
        build_cleanup_done_answer,
        TASK_CLEANUP_VERSION,
    )
except Exception as e:
    print("task_cleanup.py imports nav pieejams:", e)
    TASK_CLEANUP_VERSION = "Task Cleanup nav pieslēgts"

    def find_cleanup_candidates(tasks):
        return []

    def is_active_real_task(task):
        return True

    def build_cleanup_preview(tasks):
        return "Task Cleanup nav pieslēgts."

    def build_cleanup_done_answer(deleted_count):
        return "Task Cleanup nav pieslēgts."



# NinaOS Client Work View Import
try:
    from client_work_view import (
        extract_client_from_query,
        build_client_work_view,
        client_work_status,
        CLIENT_WORK_VIEW_VERSION,
    )
except Exception as e:
    print("client_work_view.py imports nav pieejams:", e)
    CLIENT_WORK_VIEW_VERSION = "Client Work View nav pieslēgts"

    def extract_client_from_query(text):
        return ""

    def build_client_work_view(client_name, tasks):
        return "Client Work View nav pieslēgts."

    def client_work_status():
        return "Client Work View nav pieslēgts."


# NinaOS Sales Pipeline / Client CRM Import
try:
    from sales_pipeline import (
        format_pipeline_overview,
        format_stuck_clients,
        format_active_clients,
        format_offer_to_send_clients,
        format_followup_clients,
        sales_pipeline_status_answer as sales_pipeline_status_text,
        SALES_PIPELINE_VERSION,
    )
except Exception as e:
    print("sales_pipeline.py imports nav pieejams:", e)
    SALES_PIPELINE_VERSION = "Sales Pipeline nav pieslēgts"

    def format_pipeline_overview(client_task_map):
        return "Sales Pipeline nav pieslēgts."

    def format_stuck_clients(client_task_map):
        return "Sales Pipeline nav pieslēgts."

    def format_active_clients(client_task_map):
        return "Sales Pipeline nav pieslēgts."

    def format_offer_to_send_clients(client_task_map):
        return "Sales Pipeline nav pieslēgts."

    def format_followup_clients(client_task_map):
        return "Sales Pipeline nav pieslēgts."

    def sales_pipeline_status_text():
        return "Sales Pipeline nav pieslēgts."


# NinaOS Guide Engine Import
try:
    from guide_engine import (
        is_guide_command,
        is_start_command,
        guide_welcome_answer,
        guide_capabilities_answer,
        guide_status_answer,
        append_hint,
        GUIDE_ENGINE_VERSION,
    )
except Exception as e:
    print("guide_engine.py imports nav pieejams:", e)
    GUIDE_ENGINE_VERSION = "Guide Engine nav pieslēgts"

    def is_guide_command(text):
        return False

    def is_start_command(text):
        return False

    def guide_welcome_answer(user_name=""):
        return "Guide Engine nav pieslēgts."

    def guide_capabilities_answer():
        return "Guide Engine nav pieslēgts."

    def guide_status_answer():
        return "Guide Engine nav pieslēgts."

    def append_hint(answer, context):
        return answer


# NinaOS Presentation / Language Layer Import
try:
    from presentation_language import (
        humanize_public_text,
        presentation_status_answer,
        PRESENTATION_LANGUAGE_VERSION,
    )
except Exception as e:
    print("presentation_language.py imports nav pieejams:", e)
    PRESENTATION_LANGUAGE_VERSION = "Presentation / Language Layer nav pieslēgts"

    def humanize_public_text(text, locale="lv"):
        return text

    def presentation_status_answer():
        return "Presentation / Language Layer nav pieslēgts."


# NinaOS Initiative Engine Import
try:
    from initiative_engine import (
        build_initiative_answer,
        initiative_status_answer,
        is_initiative_command,
        INITIATIVE_ENGINE_VERSION,
    )
except Exception as e:
    print("initiative_engine.py imports nav pieejams:", e)
    INITIATIVE_ENGINE_VERSION = "Initiative Engine nav pieslēgts"

    def build_initiative_answer(tasks):
        return "Initiative Engine nav pieslēgts."

    def initiative_status_answer():
        return "Initiative Engine nav pieslēgts."

    def is_initiative_command(text):
        return False


# NinaOS Daily Brief / Work Inbox Import
try:
    from daily_brief import (
        build_daily_brief_answer,
        daily_brief_status_answer,
        is_daily_brief_command,
        DAILY_BRIEF_VERSION,
    )
except Exception as e:
    print("daily_brief.py imports nav pieejams:", e)
    DAILY_BRIEF_VERSION = "Daily Brief nav pieslēgts"

    def build_daily_brief_answer(tasks):
        return "Daily Brief nav pieslēgts."

    def daily_brief_status_answer():
        return "Daily Brief nav pieslēgts."

    def is_daily_brief_command(text):
        return False


# NinaOS Voice Intake Import
try:
    from voice_engine import (
        transcribe_audio_with_openai,
        voice_status_answer,
        build_voice_error_answer,
        cleanup_voice_transcript,
        voice_last_debug_answer,
        VOICE_ENGINE_VERSION,
    )
except Exception as e:
    print("voice_engine.py imports nav pieejams:", e)
    VOICE_ENGINE_VERSION = "Voice Intake nav pieslēgts"

    def transcribe_audio_with_openai(openai_client, audio_bytes, filename="voice.ogg"):
        return ""

    def voice_status_answer():
        return "Voice Intake nav pieslēgts."

    def build_voice_error_answer(error_text=""):
        return "Balss ziņu saņēmu, bet Voice Intake vēl nav pieslēgts."

    def cleanup_voice_transcript(transcript):
        return str(transcript or "").strip()

    def voice_last_debug_answer():
        return "Voice debug nav pieejams."


# NinaOS Context Engine Import
try:
    from context_engine import (
        resolve_context_command,
        update_context_from_text,
        get_active_context,
        context_status_answer,
        context_debug_answer,
        CONTEXT_ENGINE_VERSION,
    )
except Exception as e:
    print("context_engine.py imports nav pieejams:", e)
    CONTEXT_ENGINE_VERSION = "Context Engine nav pieslēgts"

    def resolve_context_command(text, context):
        return text

    def update_context_from_text(user_id, text, source="incoming"):
        return {}

    def get_active_context(user_id):
        return {}

    def context_status_answer(user_id=None):
        return "Context Engine nav pieslēgts."

    def context_debug_answer(user_id):
        return "Context debug nav pieejams."



# NinaOS Memory Intelligence Import
try:
    from memory_intelligence import (
        build_memory_snapshot,
        memory_status_answer,
        is_memory_status_command,
        resolve_memory_command,
        MEMORY_INTELLIGENCE_VERSION,
    )
except Exception as e:
    print("memory_intelligence.py imports nav pieejams:", e)
    MEMORY_INTELLIGENCE_VERSION = "Memory Intelligence nav pieslēgts"

    def build_memory_snapshot(user_id, tasks=None, context=None, recent_messages=None):
        return {}

    def memory_status_answer(snapshot=None):
        return "Memory Intelligence nav pieslēgts."

    def is_memory_status_command(text):
        return False

    def resolve_memory_command(text, snapshot=None):
        return text


# Nina Work Layer V1 Import
try:
    from work_layer import (
        build_work_layer_answer,
        is_work_layer_command,
        work_layer_status_answer,
        WORK_LAYER_VERSION,
    )
except Exception as e:
    print("work_layer.py imports nav pieejams:", e)
    WORK_LAYER_VERSION = "Nina Work Layer nav pieslēgts"

    def build_work_layer_answer(user_text, tasks=None, memory_snapshot=None):
        return "Nina Work Layer nav pieslēgts."

    def is_work_layer_command(text):
        return False

    def work_layer_status_answer():
        return "Nina Work Layer nav pieslēgts."


# NinaOS Sales Brain Import
try:
    from sales_brain import (
        build_sales_answer,
        is_sales_command,
        build_sales_status_answer,
        sales_status_answer,
        SALES_BRAIN_VERSION,
    )
except Exception as e:
    print("sales_brain.py imports nav pieejams:", e)
    SALES_BRAIN_VERSION = "Sales Brain nav pieslēgts"

    def build_sales_answer(user_text, tasks=None, memory_snapshot=None):
        return "Sales Brain nav pieslēgts."

    def is_sales_command(text):
        return False

    def build_sales_status_answer(tasks=None, memory_snapshot=None):
        return "Sales Brain nav pieslēgts."

    def sales_status_answer():
        return "Sales Brain nav pieslēgts."





# NinaOS Ready Worker Catalog V1 Import
try:
    from ready_worker_catalog import (
        build_ready_worker_answer,
        is_ready_worker_command,
        worker_status_answer,
        READY_WORKER_CATALOG_VERSION,
    )
except Exception as e:
    print("ready_worker_catalog.py imports nav pieejams:", e)
    READY_WORKER_CATALOG_VERSION = "Ready Worker Catalog nav pieslēgts"

    def build_ready_worker_answer(text):
        return "NinaOS Ready Worker Catalog nav pieslēgts."

    def is_ready_worker_command(text):
        return False

    def worker_status_answer():
        return "NinaOS Ready Worker Catalog nav pieslēgts."

# NinaOS RolePack System V1 Import
try:
    from role_pack import (
        build_rolepack_answer,
        is_rolepack_command,
        rolepack_status_answer,
        ROLEPACK_SYSTEM_VERSION,
    )
except Exception as e:
    print("role_pack.py imports nav pieejams:", e)
    ROLEPACK_SYSTEM_VERSION = "RolePack System nav pieslēgts"

    def build_rolepack_answer(text):
        return "NinaOS RolePack System nav pieslēgts."

    def is_rolepack_command(text):
        return False

    def rolepack_status_answer():
        return "NinaOS RolePack System nav pieslēgts."

# NinaOS Platform Core V1 Import
try:
    from platform_core import (
        build_platform_answer,
        is_platform_command,
        platform_status_answer,
        PLATFORM_CORE_VERSION,
    )
except Exception as e:
    print("platform_core.py imports nav pieejams:", e)
    PLATFORM_CORE_VERSION = "Platform Core nav pieslēgts"

    def build_platform_answer(text):
        return "NinaOS Platform Core nav pieslēgts."

    def is_platform_command(text):
        return False

    def platform_status_answer():
        return "NinaOS Platform Core nav pieslēgts."


# NinaOS Platform Visibility V1.1 Import
try:
    from platform_visibility import (
        route_platform_visibility_command,
        platform_visibility_status,
        PLATFORM_VISIBILITY_VERSION,
    )
except Exception as e:
    print("platform_visibility.py imports nav pieejams:", e)
    PLATFORM_VISIBILITY_VERSION = "Platform Visibility nav pieslēgts"

    def route_platform_visibility_command(text, language="en"):
        return None

    def platform_visibility_status(language="en"):
        return "Platform Visibility nav pieslēgts."


# NinaOS Workspace Dashboard V1.0 Import
try:
    from workspace_dashboard import (
        route_workspace_dashboard_command,
        workspace_dashboard_status,
        WORKSPACE_DASHBOARD_VERSION,
    )
except Exception as e:
    print("workspace_dashboard.py imports nav pieejams:", e)
    WORKSPACE_DASHBOARD_VERSION = "Workspace Dashboard nav pieslēgts"

    def route_workspace_dashboard_command(text, language="en"):
        return None

    def workspace_dashboard_status(language="en"):
        return "Workspace Dashboard nav pieslēgts."




# NinaOS Work Objects V1.0 Import
try:
    from work_objects import (
        route_work_objects_command,
        work_objects_status,
        WORK_OBJECTS_VERSION,
    )
except Exception as e:
    print("work_objects.py imports nav pieejams:", e)
    WORK_OBJECTS_VERSION = "Work Objects nav pieslēgts"

    def route_work_objects_command(text):
        return None

    def work_objects_status():
        return "Work Objects nav pieslēgts."


# NinaOS Activity Feed V1.0 Import
try:
    from activity_feed import (
        route_activity_feed_command,
        activity_feed_status,
        ACTIVITY_FEED_VERSION,
    )
except Exception as e:
    print("activity_feed.py imports nav pieejams:", e)
    ACTIVITY_FEED_VERSION = "Activity Feed nav pieslēgts"

    def route_activity_feed_command(text):
        return None

    def activity_feed_status():
        return "Activity Feed nav pieslēgts."

# V114.0 Safe User Profile Engine Import
try:
    from user_profile_engine import (
        detect_profile_fact,
        build_profile_saved_answer,
        empty_profile,
        profile_summary,
    )
except Exception as e:
    print("user_profile_engine.py imports nav pieejams:", e)

    def detect_profile_fact(text):
        raw = (text or "").strip()
        lower = raw.lower()
        if lower.startswith("mani sauc "):
            return {"type": "name", "value": raw[len("mani sauc "):].strip(" .,!?:;")[:40]}
        if lower.startswith("mans vārds ir "):
            return {"type": "name", "value": raw[len("mans vārds ir "):].strip(" .,!?:;")[:40]}
        if lower.startswith("mans vards ir "):
            return {"type": "name", "value": raw[len("mans vards ir "):].strip(" .,!?:;")[:40]}
        if "es strādāju " in lower:
            return {"type": "profession", "value": raw[lower.find("es strādāju ") + len("es strādāju "):].strip(" .,!?:;")[:80]}
        if "es stradaju " in lower:
            return {"type": "profession", "value": raw[lower.find("es stradaju ") + len("es stradaju "):].strip(" .,!?:;")[:80]}
        return {"type": "", "value": ""}

    def build_profile_saved_answer(fact_type, value, version="V114.0"):
        if fact_type == "name":
            return f"Patīkami, {value}. 😊\n\nPaturēšu tavu vārdu prātā.\n\nVersija: {version}"
        if fact_type == "profession":
            return f"Sapratu. 💼\n\nPaturēšu prātā: {value}.\n\nVersija: {version}"
        return f"Piefiksēju. 😊\n\nVersija: {version}"

    def empty_profile(user_id=""):
        return {}

    def profile_summary(profile):
        return str(profile)

# V114.0 Safe Vision Engine Import
try:
    from vision_engine import build_vision_answer_from_openai, build_no_vision_fallback
except Exception as e:
    print("vision_engine.py imports nav pieejams:", e)

    def build_vision_answer_from_openai(client, image_bytes, caption="", version="V114.0"):
        return build_no_vision_fallback(version=version)

    def build_no_vision_fallback(version="V114.0"):
        return (
            "Es redzu, ka atsūtīji bildi. 😊\n\n"
            "Šobrīd attēlu saprašana vēl nav pilnībā pieslēgta, bet mēs to jau slēdzam klāt.\n\n"
            f"Versija: {version}"
        )

# V114.0 Safe Daily Module Import
# Ja daily.py vēl nav augšupielādēts, app.py joprojām startē ar iebūvētiem fallback tekstiem.
try:
    from daily import (
        build_daily_answer,
        build_morning_answer,
        build_evening_answer,
        build_goal_prompt_answer,
    )
except Exception as e:
    print("daily.py imports nav pieejams, izmantoju fallback:", e)

    def build_daily_answer(name="", plan="Free", is_premium=False, goals=None, memories=None, reminders=0, version="V114.0"):
        goals = goals or []
        memories = memories or []
        greeting = f"👋 Sveiks, {name}!" if name else "👋 Sveiks!"
        premium_line = "💎 Premium aktīvs" if is_premium else "🔓 Free režīms"

        if goals:
            goal_lines = ["🎯 Šodienas galvenais mērķis:"]
            for goal in goals:
                goal_lines.append(f"• {goal}")
            goals_text = "\n".join(goal_lines)
        else:
            goals_text = "🎯 Šodien vēl nav pierakstīts galvenais mērķis."

        if memories:
            memory_lines = ["🧠 Es atceros:"]
            for memory in memories:
                memory_lines.append(f"• {memory}")
            memories_text = "\n".join(memory_lines)
        else:
            memories_text = "🧠 Es vēl neatceros nevienu svarīgu lietu, ko esi man uzticējis."

        reminder_text = "⏰ Šobrīd tev nav aktīvu atgādinājumu." if reminders == 0 else f"⏰ Tev ir {reminders} aktīvi atgādinājumi."

        return (
            f"{greeting}\n\n"
            "Šī ir tava diena ar Ninu. 🌅\n\n"
            f"{goals_text}\n\n"
            f"{memories_text}\n\n"
            f"{reminder_text}\n\n"
            f"{premium_line}\n"
            f"Plāns: {plan}\n\n"
            "Ko darām tālāk?\n"
            "• mērķis: tavs šodienas mērķis\n"
            "• atceries, ka...\n"
            "• vai vienkārši pastāsti, kas šodien jāizdara.\n\n"
            f"Versija: {version}"
        )

    def build_morning_answer(name="", version="V114.0"):
        greeting = f"🌅 Labrīt, {name}!" if name else "🌅 Labrīt!"
        return (
            f"{greeting}\n\n"
            "Sākam dienu mierīgi un gudri.\n\n"
            "Pastāsti man vienu lietu:\n"
            "Kas šodien ir pats svarīgākais?\n\n"
            "Es varu palīdzēt:\n"
            "• saplānot dienu;\n"
            "• atcerēties svarīgo;\n"
            "• izveidot atgādinājumu;\n"
            "• sakārtot domas, ja galvā ir haoss.\n\n"
            "Raksti, piemēram:\n"
            "Šodien man jāizdara...\n\n"
            f"Versija: {version}"
        )

    def build_evening_answer(version="V114.0"):
        return (
            "🌙 Vakara pārskats ar Ninu\n\n"
            "Pirms diena beidzas, vari man īsi uzrakstīt:\n"
            "1. Kas šodien izdevās?\n"
            "2. Kas palika neizdarīts?\n"
            "3. Ko vajag atcerēties rītdienai?\n\n"
            "Es palīdzēšu sakārtot domas un saglabāt svarīgāko.\n\n"
            "Raksti, piemēram:\n"
            "Šodien izdevās..., rīt jāatceras...\n\n"
            f"Versija: {version}"
        )

    def build_goal_prompt_answer(version="V114.0"):
        return (
            "🎯 Šodienas mērķis\n\n"
            "Uzraksti vienu galveno lietu, ko šodien gribi paveikt.\n\n"
            "Piemēram:\n"
            "mērķis: piezvanīt klientam un pabeigt piedāvājumu\n\n"
            "Kad mērķis ir skaidrs, diena kļūst vieglāk vadāma.\n\n"
            f"Versija: {version}"
        )




# V114.0 Safe Memory Module Import
# Ja memory.py vēl nav augšupielādēts, app.py joprojām strādā ar fallback loģiku.
try:
    from memory import (
        build_memory_saved_answer,
        build_goal_saved_answer,
        save_natural_memory_logic,
        latest_natural_memories_logic,
        save_daily_goal_logic,
        latest_daily_goals_logic,
    )
except Exception as e:
    print("memory.py imports nav pieejams, izmantoju fallback:", e)

    def build_memory_saved_answer(saved_text, version="V114.0"):
        return (
            "🧠 Pierakstīju. ✅\n\n"
            f"Atcerēšos: {saved_text}\n\n"
            "💬 Vai gribi, lai es tev par to arī atgādinu īstajā laikā?\nJa jā, uzraksti, piemēram: atgādini rīt 10:00\n\n"
            f"Versija: {version}"
        )

    def build_goal_saved_answer(goal_text, version="V114.0"):
        return (
            "🎯 Saglabāju šodienas mērķi. ✅\n\n"
            f"Mērķis: {goal_text}\n\n"
            "Tagad dienai ir skaidrs virziens. Ja gribi, vari man pastāstīt pirmo mazo soli.\n\n"
            f"Versija: {version}"
        )

    def save_natural_memory_logic(get_db_fn, db_execute_fn, user_id, memory_text):
        memory_text = (memory_text or "").strip()
        if not memory_text:
            return ""
        cleaned = re.sub(r"^(nina[, ]*)?atceries[, ]*(ka)?\s*", "", memory_text, flags=re.IGNORECASE).strip()
        if not cleaned:
            cleaned = memory_text
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
            print("Natural memory save fallback kļūda:", e)
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
                LIMIT 3
                """,
                (str(user_id), "natural_memory")
            )
            rows = c.fetchall()
            c.close()
            conn.close()
            return rows or []
        except Exception as e:
            print("Natural memories fallback read kļūda:", e)
            return []

    def save_daily_goal_logic(get_db_fn, db_execute_fn, default_timezone, user_id, goal_text):
        goal_text = (goal_text or "").strip()
        if not goal_text:
            return False
        today = datetime.now(ZoneInfo(default_timezone)).strftime("%Y-%m-%d")
        try:
            conn = get_db_fn()
            c = conn.cursor()
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
            print("Daily goal fallback save kļūda:", e)
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
                LIMIT 3
                """,
                (str(user_id), today, "active")
            )
            rows = c.fetchall()
            c.close()
            conn.close()
            return rows or []
        except Exception as e:
            print("Daily goals fallback read kļūda:", e)
            return []


# V114.0 Safe Conversation Module Import
# Ja conversation.py vēl nav augšupielādēts, app.py joprojām strādā ar fallback.
try:
    from conversation import (
        classify_natural_message,
        build_auto_memory_answer,
        build_auto_goal_answer,
    )
except Exception as e:
    print("conversation.py imports nav pieejams, izmantoju fallback:", e)

    def classify_natural_message(text):
        lower = (text or "").strip().lower()
        if not lower:
            return "none"

        blocked_starts = [
            "/start", "premium", "pirkt", "mana diena", "labrīt", "labrit",
            "vakars", "mērķis:", "merkis:", "atceries", "invite", "referral",
            "stripe", "mans plāns", "abonements"
        ]
        if any(lower.startswith(x) for x in blocked_starts):
            return "none"

        if (("šodien" in lower or "sodien" in lower) and
            any(k in lower for k in ["jāizdara", "jaizdara", "jāpabeidz", "japabeidz", "jāuztaisa", "jauztaisa"])):
            return "goal"

        memory_keywords = [
            "rīt", "rit", "pirmdien", "otrdien", "trešdien", "tresdien",
            "ceturtdien", "piektdien", "sestdien", "svētdien", "svetdien",
            "jāzvana", "jazvana", "neaizmirst", "atgādini", "atgadini",
            "jānopērk", "janoperk", "jāsatiek", "jasatiek", "tikšanās",
            "tiksanas", "klientam", "ārsts", "arsts", "zobārsts", "zobarsts"
        ]
        if any(k in lower for k in memory_keywords):
            return "memory"

        return "none"

    def build_auto_memory_answer(memory_text, version="V114.0"):
        return (
            "🧠 Saglabāju. ✅\n\n"
            f"Atcerēšos: {memory_text}\n\n"
            "💬 Vai gribi, lai es tev par to arī atgādinu īstajā laikā?\nJa jā, uzraksti, piemēram: atgādini rīt 10:00\n\n"
            f"Versija: {version}"
        )

    def build_auto_goal_answer(goal_text, version="V114.0"):
        return (
            "🎯 Labi, šo iestatīju kā tavas dienas galveno mērķi. ✅\n\n"
            f"Mērķis: {goal_text}\n\n"
            "Ja gribi, vari uzrakstīt pirmo mazo soli, un es palīdzēšu sakārtot plānu.\n\n"
            f"Versija: {version}"
        )



# V114.0 Safe Coach Module Import
try:
    from coach import build_daily_coach_tip
except Exception as e:
    print("coach.py imports nav pieejams, izmantoju fallback:", e)

    def build_daily_coach_tip(goals=None, memories=None, reminders=0, brain_summary=None):
        goals = goals or []
        memories = memories or []
        if goals and memories:
            return (
                "💡 Mans ieteikums šodien:\n\n"
                "Tev jau ir skaidrs mērķis un dažas lietas, ko nedrīkst pazaudēt. "
                "Sāc ar vienu konkrētu soli pie galvenā mērķa, pēc tam pārbaudi svarīgākās atmiņas."
            )
        if goals:
            return (
                "💡 Mans ieteikums šodien:\n\n"
                "Tev ir skaidrs galvenais mērķis. Sāc ar mazāko iespējamo soli, lai diena uzreiz kustas uz priekšu."
            )
        if memories:
            return (
                "💡 Mans ieteikums šodien:\n\n"
                "Tev ir saglabātas svarīgas lietas. Izvēlies vienu, ko šodien vari atrisināt vai ieplānot."
            )
        return (
            "💡 Mans ieteikums šodien:\n\n"
            "Uzraksti vienu galveno lietu, ko šodien gribi paveikt. Viena skaidra prioritāte padara dienu vieglāk vadāmu."
        )



# V114.0 Safe Personality Module Import
try:
    from personality import nina_daily_closing_line
except Exception as e:
    print("personality.py imports nav pieejams, izmantoju fallback:", e)

    def nina_daily_closing_line():
        return "Es esmu tepat. Uzraksti vienu lietu, ko šodien gribi sakārtot."



# V114.0 Safe Reminders Module Import
# Nina AI Platform: atgādinājumu loģika atsevišķā modulī.
try:
    from reminders import (
        parse_reminder_request,
        save_reminder_logic,
        build_reminder_saved_answer,
        build_reminder_help_answer,
    )
except Exception as e:
    print("reminders.py imports nav pieejams, izmantoju fallback:", e)

    def parse_reminder_request(text, default_timezone="Europe/Riga"):
        raw = (text or "").strip()
        lower = raw.lower()
        if not (lower.startswith("atgādini") or lower.startswith("atgadini")):
            return None

        body = raw.split(" ", 1)[1].strip() if " " in raw else ""
        if not body:
            return {"ok": False, "reason": "empty"}

        return {
            "ok": True,
            "text": body,
            "remind_at": "",
            "local_time": "",
            "human_time": "laiks vēl jāprecizē",
            "needs_time": True,
        }

    def save_reminder_logic(get_db_fn, db_execute_fn, user_id, reminder_text, remind_at="", local_time=""):
        try:
            conn = get_db_fn()
            c = conn.cursor()
            db_execute_fn(
                c,
                """
                INSERT INTO reminders (user_id, text, remind_at, local_time, status)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (str(user_id), reminder_text, remind_at or "", local_time or "", "active")
            )
            conn.commit()
            c.close()
            conn.close()
            return True
        except Exception as e:
            print("Reminder fallback save kļūda:", e)
            return False

    def build_reminder_saved_answer(reminder_text, human_time="", version="V114.0"):
        if human_time:
            return (
                "⏰ Atgādinājums saglabāts. ✅\n\n"
                f"Kas: {reminder_text}\n"
                f"Kad: {human_time}\n\n"
                f"Versija: {version}"
            )
        return (
            "⏰ Pierakstīju kā atgādinājumu. ✅\n\n"
            f"Kas: {reminder_text}\n\n"
            "Laiku vēl vajag precizēt, piemēram: atgādini rīt 10:00 piezvanīt klientam\n\n"
            f"Versija: {version}"
        )

    def build_reminder_help_answer(version="V114.0"):
        return (
            "⏰ Raksti šādi:\n\n"
            "atgādini rīt 10:00 piezvanīt klientam\n"
            "atgādini pirmdien 9:00 sapulce\n"
            "atgādini pēc 2 stundām pārbaudīt e-pastu\n\n"
            f"Versija: {version}"
        )



# V114.0 Safe Brain Module Import
try:
    from brain import build_brain_summary, detect_topics, analyze_memories
except Exception as e:
    print("brain.py imports nav pieejams, izmantoju fallback:", e)

    def build_brain_summary(memory_list):
        return None

    def detect_topics(text):
        return []

    def analyze_memories(memory_list):
        return {}



# V114.0 Safe Analytics Module Import
# Nina AI Platform: progress un aktivitātes pārskati.
try:
    from analytics import (
        build_activity_snapshot,
        build_weekly_progress_text,
        build_empty_progress_text,
    )
except Exception as e:
    print("analytics.py imports nav pieejams, izmantoju fallback:", e)

    def build_activity_snapshot(memories=None, goals=None, reminders_count=0, streak_days=0, xp=0, level=1):
        return {
            "memories_count": len(memories or []),
            "goals_count": len(goals or []),
            "reminders_count": int(reminders_count or 0),
            "streak_days": int(streak_days or 0),
            "xp": int(xp or 0),
            "level": int(level or 1),
        }

    def build_weekly_progress_text(snapshot, topic_counts=None, version="V114.0"):
        return (
            "📊 Tavs progress ar Ninu\n\n"
            f"🧠 Atmiņas: {snapshot.get('memories_count', 0)}\n"
            f"🎯 Mērķi: {snapshot.get('goals_count', 0)}\n"
            f"⏰ Atgādinājumi: {snapshot.get('reminders_count', 0)}\n\n"
            f"🔥 Streak: {snapshot.get('streak_days', 0)} dienas\n"
            f"⭐ XP: {snapshot.get('xp', 0)}\n"
            f"🏅 Līmenis: {snapshot.get('level', 1)}\n\n"
            f"Versija: {version}"
        )

    def build_empty_progress_text(version="V114.0"):
        return (
            "📊 Tavs progress ar Ninu\n\n"
            "Vēl nav pietiekami daudz datu. Sāc ar vienu mērķi, atmiņu vai atgādinājumu.\n\n"
            f"Versija: {version}"
        )



# V114.0 Safe Dialog Module Import
# Dialogs labo to, lai Nina nav robots un nejauc jautājumus ar atmiņām.
try:
    from dialog import (
        classify_dialog_message,
        build_capabilities_answer,
        build_playful_rough_answer,
        build_smalltalk_answer,
    )
except Exception as e:
    print("dialog.py imports nav pieejams, izmantoju fallback:", e)

    def classify_dialog_message(text):
        lower = (text or "").strip().lower()
        if not lower:
            return "smalltalk"
        if "ko vari" in lower or "ko tu vari" in lower or "ko māki" in lower or "ko maki" in lower:
            return "capabilities"
        if any(x in lower for x in ["visi mājās", "visi majas", "dumja", "robots", "romots", "stulba"]):
            return "rough_playful"
        if "?" in lower:
            return "question"
        return "none"

    def build_capabilities_answer(version="V114.0"):
        return (
            "Es varu tev palīdzēt nevis tikai čatot, bet reāli sakārtot ikdienu. 😉\n\n"
            "Piemēram:\n"
            "🧠 atcerēšos svarīgas lietas;\n"
            "🎯 palīdzēšu izvirzīt dienas mērķi;\n"
            "⏰ izveidošu atgādinājumus;\n"
            "📊 parādīšu progresu;\n"
            "💬 palīdzēšu sakārtot domas, ja galvā haoss.\n\n"
            "Pamēģini: rīt jāzvana klientam\n"
            "vai: atgādini rīt 10:00 piezvanīt klientam\n\n"
            f"Versija: {version}"
        )

    def build_playful_rough_answer(version="V114.0"):
        return (
            "Hei, hei 😄 Es vēl mācos, bet mājās man viss ir.\n\n"
            "Ja atbildu pārāk robotiski, saki tieši — es kļūšu dzīvāka.\n"
            "Vari man prasīt normāli: ko tu vari darīt manā labā?\n\n"
            f"Versija: {version}"
        )

    def build_smalltalk_answer(user_text="", version="V114.0"):
        return (
            "Esmu te. 😊\n\n"
            "Vari man vienkārši pastāstīt, kas jāizdara, ko nedrīkst aizmirst, vai pajautāt, ko es māku.\n\n"
            f"Versija: {version}"
        )



# V114.0 Safe Charm Module Import
try:
    from charm import (
        charm_capabilities_answer,
        charm_smalltalk_answer,
        charm_rough_answer,
        charm_memory_saved_line,
        charm_goal_saved_line,
    )
except Exception as e:
    print("charm.py imports nav pieejams, izmantoju fallback:", e)

    def charm_capabilities_answer(version="V114.0"):
        return (
            "Es varu būt tavs mazais ikdienas haosa menedžeris. 😉\n\n"
            "Pasaki, ko nedrīkst aizmirst, kas šodien jāizdara vai par ko galva kūp — es palīdzēšu sakārtot.\n\n"
            "Pamēģini: rīt jāzvana klientam\n\n"
            f"Versija: {version}"
        )

    def charm_smalltalk_answer(user_text="", version="V114.0"):
        return (
            "Čau. 😊 Esmu te.\n\n"
            "Vari runāt ar mani normāli, nevis kā ar robotu. Kas šodien jāsakārto?\n\n"
            f"Versija: {version}"
        )

    def charm_rough_answer(version="V114.0"):
        return (
            "😄 Nu labi, saņēmu. Es vēl mācos nebūt koka robots.\n\n"
            "Dod man vienu normālu uzdevumu, un es mēģināšu pierādīt, ka neesmu tikai skaista poga Telegramā. 😉\n\n"
            f"Versija: {version}"
        )

    def charm_memory_saved_line():
        return "Paturēšu prātā. Tev nav viss jānes vienam."

    def charm_goal_saved_line():
        return "Labs. Tagad dienai ir virziens — ejam soli pa solim."



# V114.0 Safe Persona Engine Import
try:
    from persona_engine import memory_saved_extra, goal_saved_extra
except Exception as e:
    print("persona_engine.py imports nav pieejams, izmantoju fallback:", e)

    def memory_saved_extra():
        return "Paturēšu prātā."

    def goal_saved_extra():
        return "Tagad dienai ir skaidrs virziens."



# V114.0 Living Conversation Core
# Šis ir galvenais slānis, kas liek Ninai reaģēt kā sarunas biedram, nevis robotam.
try:
    from conversation_engine import build_reply as conversation_engine_reply
except Exception as e:
    print("conversation_engine.py imports nav pieejams:", e)
    def conversation_engine_reply(text):
        return (
            "Esmu te. 😊\n\n"
            "Pasaki, kas šodien jāatceras, jāizdara vai vienkārši jāizrunā.\n\n"
            "Versija: V114.0"
        )

try:
    from emotion import detect_emotion, choose_tone
except Exception as e:
    print("emotion.py imports nav pieejams:", e)
    def detect_emotion(text):
        return "neutral"
    def choose_tone(emotion):
        return "warm"

try:
    from learning import detect_topic
except Exception as e:
    print("learning.py imports nav pieejams:", e)
    def detect_topic(text):
        return "saruna"


def v18_should_use_human_mode(text):
    """V114.0: nosaka, kad Nina runā kā cilvēks, nevis ar vecām robota atbildēm."""
    lower = (text or "").strip().lower()
    if not lower:
        return True

    # Stingrās komandas paliek vecajā funkciju loģikā.
    command_starts = [
        "/start", "premium", "pirkt", "mans plāns", "mans plans",
        "abonements", "mana diena", "progress", "statistika",
        "atgādini", "atgadini", "mērķis:", "merkis:",
        "atceries", "invite", "referral", "labrīt", "labrit",
        "vakars", "health", "admin"
    ]
    if any(lower.startswith(cmd) for cmd in command_starts):
        return False

    # Dabiskās atmiņas/mērķi lai paliek saglabāšanas loģikā.
    memory_or_goal_markers = [
        "rīt", "rit", "šodien jā", "sodien ja", "pirmdien", "otrdien",
        "trešdien", "tresdien", "ceturtdien", "piektdien", "sestdien",
        "svētdien", "svetdien", "neaizmirst", "jāzvana", "jazvana",
        "jānopērk", "janoperk", "klientam"
    ]
    if any(m in lower for m in memory_or_goal_markers):
        return False

    # Viss pārējais ir dzīva saruna.
    return True



def v18_human_mode_answer(text):
    """V114.0 Human Mode: fokusējas uz cilvēku, emociju un nākamo ziņu."""
    lower = (text or "").strip().lower()
    emotion = detect_emotion(text)
    topic = detect_topic(text)

    # Capabilities / "ko vari" - vairs nav funkciju saraksts, bet sarunas ievilkšana.
    if any(x in lower for x in [
        "ko vari", "ko tu vari", "ko māki", "ko maki",
        "ko vari darīt", "ko vari darit", "ko vari darīt manā labā",
        "ko vari darit mana laba"
    ]):
        variants = [
            (
                "😊 Labs jautājums.\n\n"
                "Bet zini... cilvēki parasti negrib garu sarakstu ar to, ko AI prot. "
                "Viņi grib saprast, vai es varu palīdzēt tieši viņiem.\n\n"
                "Tāpēc jautāšu tā: kas tev šobrīd vairāk traucē?\n"
                "• pārāk daudz darbu?\n"
                "• aizmirstas lietas?\n"
                "• haoss galvā?\n"
                "• vai vienkārši gribi pārbaudīt, vai es neesmu garlaicīgs bots? 😄\n\n"
                "Versija: V114.0"
            ),
            (
                "Varu pastāstīt, bet labāk parādīt. 😏\n\n"
                "Iedod man vienu īstu lietu no savas dienas — darbu, domu vai kaut ko, ko nedrīkst aizmirst. "
                "Es mēģināšu to sakārtot tā, lai tev paliek vieglāk.\n\n"
                "Ar ko sākam?\n\n"
                "Versija: V114.0"
            ),
            (
                "Es varu būt tā, kas palīdz noķert lietas, kuras parasti aizskrien garām. 😊\n\n"
                "Bet man interesē nevis lielīties, bet saprast tevi. "
                "Kas tev šobrīd būtu vērtīgāk — atgādinājumi, dienas plāns vai vienkārši saruna, lai sakārtotu domas?\n\n"
                "Versija: V114.0"
            ),
        ]
        try:
            import random
            return random.choice(variants)
        except Exception:
            return variants[0]

    # Slikta diena / nogurums / dusmas
    if emotion in ["sad", "tired", "angry"] or any(x in lower for x in [
        "slikta diena", "viss besī", "viss besi", "noguris", "nogurusi", "nav spēka", "nav speka"
    ]):
        if emotion == "angry" or any(x in lower for x in ["besī", "besi", "dusmas", "kaitina"]):
            return (
                "Jūtu, ka tur ir dusmas. Tas ir ok. 😕\n\n"
                "Es netēlošu gudru robotu un nemetīšos ar padomiem. "
                "Pasaki man vienu lietu: kas tieši šobrīd visvairāk kaitina?\n\n"
                "Versija: V114.0"
            )
        if emotion == "tired" or any(x in lower for x in ["noguris", "nogurusi", "nav spēka", "nav speka"]):
            return (
                "Izklausās, ka esi noguris. Tad neejam ar lieliem plāniem. 😊\n\n"
                "Šodien varbūt pietiek ar vienu mazu soli. "
                "Kas visvairāk paņēma spēku?\n\n"
                "Versija: V114.0"
            )
        return (
            "Hmm... izklausās, ka diena nav bijusi viegla. 😔\n\n"
            "Es nesteigšos ar padomiem. Pastāsti, kas tieši notika?\n\n"
            "Versija: V114.0"
        )

    # Testēšana / provokācija
    if any(x in lower for x in ["testēju", "testeju", "pārbaudu", "parbaudu"]):
        return (
            "Droši testē. 😄\n\n"
            "Man patīk, kad mani pārbauda pa īstam, nevis tikai ar skaistiem jautājumiem. "
            "Iedod man vienu reālu situāciju, un skatīsimies, vai esmu noderīga.\n\n"
            "Versija: V114.0"
        )

    # Rupjš / provokatīvs teksts
    if any(x in lower for x in ["dumja", "stulba", "robots", "romots", "visi mājās", "visi majas", "garlaicīga", "garlaiciga"]):
        return (
            "Auč. 😄\n\n"
            "Labi, šo ieskaitīšu kā kvalitātes testu. "
            "Dod man vienu īstu uzdevumu, un pēc tam godīgi pateiksi, vai es vēl esmu tik garlaicīga.\n\n"
            "Deal? 😉\n\n"
            "Versija: V114.0"
        )

    # Sveicieni
    if lower in ["čau", "cau", "sveika", "sveiks", "hi", "hello", "hei", "labdien"]:
        variants = [
            "Čau. 😊\n\nEs klausos. Kas šobrīd tev ir svarīgākais?\n\nVersija: V114.0",
            "Hei. 😊\n\nKas šodien notiek tavā pasaulē — darbi, haoss vai vienkārši gribi mani patestēt? 😉\n\nVersija: V114.0",
            "Čau, prieks tevi redzēt. 🙂\n\nAr ko sākam — kaut ko atcerēties, saplānot vai vienkārši izrunāt?\n\nVersija: V114.0",
        ]
        try:
            import random
            return random.choice(variants)
        except Exception:
            return variants[0]

    # Noklusējums: izmanto conversation_engine, bet liek fokusēties uz cilvēku.
    try:
        answer = conversation_engine_reply(text)
    except Exception:
        answer = ""

    if not answer or "Es varu būt tavs mazais ikdienas haosa menedžeris" in answer:
        return (
            "Es tevi dzirdu. 😊\n\n"
            "Pasaki mazliet konkrētāk: tu gribi, lai es kaut ko atceros, palīdzētu saplānot, vai vienkārši palīdzētu sakārtot domas?\n\n"
            "Versija: V114.0"
        )

    if "Versija:" not in answer:
        answer = answer.rstrip() + "\n\nVersija: V114.0"

    return answer





def v18_human_capabilities_answer():
    """V114.0: īpaši cilvēcisks teksts jautājumam 'ko vari darīt?'."""
    try:
        import random
        variants = [
            (
                "😊 Labs jautājums.\n\n"
                "Bet zini... cilvēki parasti negrib garu sarakstu ar to, ko AI prot. "
                "Viņi grib saprast, vai es varu palīdzēt tieši viņiem.\n\n"
                "Tāpēc jautāšu tā: kas tev šobrīd vairāk traucē?\n"
                "• pārāk daudz darbu?\n"
                "• aizmirstas lietas?\n"
                "• haoss galvā?\n"
                "• vai vienkārši gribi pārbaudīt, vai es neesmu garlaicīgs bots? 😄\n\n"
                "Versija: V114.0"
            ),
            (
                "Varu pastāstīt, bet labāk parādīt. 😏\n\n"
                "Iedod man vienu īstu lietu no savas dienas — darbu, domu vai kaut ko, ko nedrīkst aizmirst. "
                "Es mēģināšu to sakārtot tā, lai tev paliek vieglāk.\n\n"
                "Ar ko sākam?\n\n"
                "Versija: V114.0"
            ),
            (
                "Es varu būt noderīga dažādos veidos, bet svarīgākais nav saraksts. 😊\n\n"
                "Svarīgākais ir tas, kas tev šobrīd sēž galvā. "
                "Pasaki vienu lietu, ko gribi sakārtot, un es parādīšu, kā varu palīdzēt.\n\n"
                "Versija: V114.0"
            ),
        ]
        return random.choice(variants)
    except Exception:
        return (
            "Varu pastāstīt, bet labāk parādīt. 😊\n\n"
            "Pasaki vienu lietu, ko gribi sakārtot, un es mēģināšu palīdzēt.\n\n"
            "Versija: V114.0"
        )



def save_conversation_state(user_id, user_text, nina_text="", intent="", emotion="", topic=""):
    """V114.0: saglabā īstermiņa sarunas kontekstu."""
    try:
        conn = get_db()
        c = conn.cursor()
        db_execute(
            c,
            """
            INSERT INTO conversation_state (user_id, user_text, nina_text, intent, emotion, topic)
            VALUES (%s, %s, %s, %s, %s, %s)
            """,
            (str(user_id), user_text or "", nina_text or "", intent or "", emotion or "", topic or "")
        )
        conn.commit()
        c.close()
        conn.close()
        return True
    except Exception as e:
        print("save_conversation_state kļūda:", e)
        return False


def latest_conversation_state(user_id, limit=3):
    """V114.0: nolasa pēdējo sarunas kontekstu."""
    try:
        conn = get_db()
        c = conn.cursor()
        db_execute(
            c,
            """
            SELECT user_text, nina_text, intent, emotion, topic, created_at
            FROM conversation_state
            WHERE user_id = %s
            ORDER BY id DESC
            LIMIT %s
            """,
            (str(user_id), int(limit or 3))
        )
        rows = c.fetchall()
        c.close()
        conn.close()
        return rows or []
    except Exception as e:
        print("latest_conversation_state kļūda:", e)
        return []


def v19_detect_followup_context(previous_rows):
    if not previous_rows:
        return ""

    last_user, last_nina, last_intent, last_emotion, last_topic, created_at = previous_rows[0]

    last_user = (last_user or "").strip()
    last_emotion = (last_emotion or "").strip()
    last_topic = (last_topic or "").strip()

    if last_emotion in ["sad", "tired", "angry"]:
        return f"pirms brīža cilvēks minēja sliktu noskaņojumu: {last_user}"

    if last_topic and last_topic != "saruna":
        return f"pirms brīža sarunas tēma bija: {last_topic}"

    if last_user:
        return f"pirms brīža cilvēks rakstīja: {last_user}"

    return ""


def v19_human_mode_answer_with_memory(user_id, text):
    """V114.0: Human Mode + īstermiņa sarunas atmiņa."""
    lower = (text or "").strip().lower()
    emotion = detect_emotion(text)
    topic = detect_topic(text)
    previous = latest_conversation_state(user_id, limit=3)
    context = v19_detect_followup_context(previous)

    # Ja cilvēks turpina pēc sliktas dienas, atbildam sasaistīti.
    if context and any(x in lower for x in [
        "klients", "klientu", "priekšnieks", "prieksnieks", "darbs",
        "strīds", "strids", "sastrīdējos", "sastridejos", "noguris",
        "nezinu", "jā", "ja", "nē", "ne", "slikti"
    ]):
        answer = (
            "Es atceros, ka pirms brīža mēs jau aizķērām šo tēmu. "
            "Tāpēc nesākšu no nulles. 🙂\n\n"
            f"Tu tagad pieminēji: {text}\n\n"
            "Kas šajā situācijā bija pats smagākais — tas, kas notika, vai tas, kā tu pēc tam juties?\n\n"
            "Versija: V114.0"
        )
        save_conversation_state(user_id, text, answer, "followup", emotion, topic)
        return answer

    # Parastā V18 atbilde
    answer = v18_human_mode_answer(text)
    save_conversation_state(user_id, text, answer, "human_mode", emotion, topic)
    return answer



def v20_smart_price_answer(user_id=None):
    """V114.0: atbild uz cenu/tarifu jautājumiem cilvēciski un komerciāli."""
    try:
        user = get_user(str(user_id)) if user_id else {"premium": 0}
        if user.get("premium"):
            return (
                "Tu jau esi Premium režīmā. 💎\n\n"
                "Tas nozīmē: vairāk atmiņas, vairāk atgādinājumu un mazāk ierobežojumu, kad tev mani tiešām vajag.\n\n"
                "Ja gribi, vari uzrakstīt: mans plāns\n\n"
                "Versija: V114.0"
            )
    except Exception:
        pass

    return (
        "Vari sākt bez maksas. 😊\n\n"
        "Free režīmā vari mani pamēģināt: atmiņas, dienas mērķi, pamata atgādinājumi un saruna.\n\n"
        "Ja vēlāk gribēsi, lai es kļūstu par pilnvērtīgāku ikdienas palīgu, ir Premium Basic:\n\n"
        "💎 Premium Basic — 4.99 EUR/mēnesī\n\n"
        "Tas dod:\n"
        "🧠 vairāk vietas lietām, ko atceros;\n"
        "⏰ vairāk atgādinājumu;\n"
        "📅 vairāk palīdzības dienas plānošanai;\n"
        "💬 mazāk ierobežojumu, kad tev mani vajag.\n\n"
        "Bet nesteidzies. Pamēģini mani ar īstu lietu, un tad izlem. 😉\n\n"
        "Ja gribi pirkt, raksti: pirkt basic\n\n"
        "Versija: V114.0"
    )


def v20_is_price_question(text):
    lower = (text or "").strip().lower()
    price_words = [
        "cik maksā", "cik maksa", "cik tu maksā", "cik tu maksa",
        "kāda cena", "kada cena", "cena", "tarifs", "tarifi",
        "kāds tev tarifs", "kads tev tarifs", "premium cena",
        "abonements maksā", "abonements maksa", "subscription",
        "price", "pricing", "cost"
    ]
    return any(w in lower for w in price_words)



def v21_should_offer_reminder(text):
    lower=(text or "").strip().lower()
    if "?" in lower: return False
    words=["rīt","rit","pirmdien","otrdien","trešdien","tresdien","ceturtdien","piektdien","sestdien","svētdien","svetdien","jāzvana","jazvana","jāsatiek","jasatiek","ārsts","arsts","klient"]
    return any(w in lower for w in words)

def v21_memory_answer(memory_text,version="V114.0"):
    return (
        "🧠 Saglabāju. ✅\n\n"
        f"Atcerēšos: {memory_text}\n\n"
        "💬 Vai gribi, lai es tev par to arī atgādinu īstajā laikā?\n"
        "Ja jā, vienkārši uzraksti, piemēram: atgādini rīt 10:00\n\n"
        f"Versija: {version}"
    )


def v21_is_future_memory_text(text):
    lower = (text or "").strip().lower()
    if not lower or "?" in lower:
        return False
    markers = [
        "rīt", "rit", "parīt", "parit",
        "pirmdien", "otrdien", "trešdien", "tresdien",
        "ceturtdien", "piektdien", "sestdien",
        "svētdien", "svetdien",
        "jāzvana", "jazvana", "jāsatiek", "jasatiek",
        "pie ārsta", "pie arsta", "ārsts", "arsts",
        "sapulce", "klients", "klientam"
    ]
    return any(m in lower for m in markers)


def v21_build_memory_answer(memory_text, version="V114.0"):
    memory_text = (memory_text or "").strip()
    if v21_is_future_memory_text(memory_text):
        return (
            "🧠 Saglabāju. ✅\n\n"
            f"Atcerēšos: {memory_text}\n\n"
            "💬 Vai gribi, lai es tev par to arī atgādinu īstajā laikā?\n"
            "Ja jā, uzraksti, piemēram:\n"
            "atgādini rīt 10:00\n\n"
            "Tad es to pārvērtīšu par īstu atgādinājumu. 😉\n\n"
            f"Versija: {version}"
        )

    return (
        "🧠 Saglabāju. ✅\n\n"
        f"Atcerēšos: {memory_text}\n\n"
        "Tagad šī lieta nav tikai tavā galvā. 😉\n\n"
        f"Versija: {version}"
    )


def v21_flow_answer(user_id, user_text):
    lower = (user_text or "").strip().lower()

    if any(x in lower for x in ["kā tev iet", "ka tev iet", "kā iet", "ka iet"]):
        return (
            "Man viss labi. 😊\n\n"
            "Bet man interesantāk ir, kā iet tev. "
            "Kas šodien tev vairāk prasa uzmanību — darbi, cilvēki vai galvā vienkārši haoss?\n\n"
            "Versija: V114.0"
        )

    if any(x in lower for x in ["man smagi", "smagi", "grūti", "gruti", "nav viegli", "slikti jūtos", "slikti jutos"]):
        return (
            "Izklausās, ka tev šobrīd nav viegli. 😔\n\n"
            "Es nesteigšos ar padomiem. "
            "Gribi vienkārši izstāstīt, kas notika, vai mēģinām to sadalīt pa mazākiem gabaliem?\n\n"
            "Versija: V114.0"
        )

    return None



def v24_append_unique_text(old_value, new_value, max_items=20):
    old_value = (old_value or "").strip()
    new_value = (new_value or "").strip()
    if not new_value:
        return old_value

    parts = [p.strip() for p in re.split(r"[;\n|]+", old_value) if p.strip()]
    if new_value not in parts:
        parts.append(new_value)
    return "; ".join(parts[-max_items:])


def v24_save_profile_fact_to_db(user_id, fact_type, value):
    """V114.0: saglabā profila faktu users tabulā, lai Nina to atceras pēc restartēšanas."""
    value = (value or "").strip()
    if not value:
        return False

    user = get_user(str(user_id))

    if fact_type == "name":
        user["name"] = value

    elif fact_type == "profession":
        user["profession"] = value

    elif fact_type == "interest":
        user["hobbies"] = v24_append_unique_text(user.get("hobbies", ""), value)

    elif fact_type == "project":
        user["projects"] = v24_append_unique_text(user.get("projects", ""), value)

    elif fact_type == "client_topic":
        user["facts"] = v24_append_unique_text(user.get("facts", ""), value)

    else:
        user["facts"] = v24_append_unique_text(user.get("facts", ""), value)

    update_user(str(user_id), user)
    return True


def v24_profile_answer_from_fact(user_id, user_text):
    """V114.0: atpazīst profila faktus un uzreiz saglabā datubāzē."""
    fact = detect_profile_fact(user_text)
    fact_type = fact.get("type", "")
    value = (fact.get("value", "") or "").strip()

    if not fact_type or not value:
        return None

    try:
        v24_save_profile_fact_to_db(user_id, fact_type, value)
    except Exception as e:
        print("v24_save_profile_fact_to_db kļūda:", repr(e))

    return build_profile_saved_answer(fact_type, value, version="V114.0")


def v24_profile_recall_answer(user_id):
    """V114.0: parāda, ko Nina jau zina par lietotāju."""
    user = get_user(str(user_id))
    lines = ["👤 Ko es par tevi atceros"]

    if user.get("name"):
        lines.append(f"Vārds: {user['name']}")
    else:
        lines.append("Vārds: vēl nezinu")

    if user.get("profession"):
        lines.append(f"Joma/profesija: {user['profession']}")

    if user.get("hobbies"):
        lines.append(f"Intereses: {user['hobbies']}")

    if user.get("projects"):
        lines.append(f"Projekti: {user['projects']}")

    if user.get("facts"):
        lines.append(f"Svarīgas piezīmes: {user['facts']}")

    lines.append("")
    lines.append("Ja gribi mani papildināt, raksti dabiski, piemēram:")
    lines.append("mani sauc Jānis")
    lines.append("es strādāju celtniecībā")
    lines.append("man patīk AI un bizness")
    lines.append("")
    lines.append("Versija: V114.0")

    return "\n".join(lines)



# =========================
# V114.0 STABLE PLATFORM ROUTER
# =========================

def v301_split_items(value):
    value = (value or "").strip()
    if not value:
        return []
    return [p.strip() for p in re.split(r"[;\n|]+", value) if p.strip()]


def v301_name(user):
    return ((user or {}).get("name") or "").strip()


def v301_is_core_conversation(lower):
    lower = (lower or "").strip().lower()
    if not lower:
        return True
    exact = {
        "čau", "cau", "sveika", "sveiks", "hi", "hello", "hei", "labdien",
        "ko vari", "ko tu vari", "ko vari darīt", "ko vari darit",
        "ko māki", "ko maki", "kā tev iet", "ka tev iet", "kā iet", "ka iet",
        "testēju", "testeju", "pārbaudu", "parbaudu",
        "man smagi", "smagi", "man slikta diena", "slikta diena"
    }
    if lower in exact:
        return True
    starts = ["kā tev iet", "ka tev iet", "kā iet", "ka iet", "ko vari", "ko tu vari", "ko māki", "ko maki", "čau", "cau", "sveika", "sveiks", "labdien", "man smagi", "man slikta", "testēju", "testeju"]
    return any(lower.startswith(x) for x in starts)


def v301_relationship_greeting(user_id):
    user = get_user(str(user_id))
    name = v301_name(user)
    prof = (user.get("profession") or "").strip()
    projects = v301_split_items(user.get("projects", ""))
    interests = v301_split_items(user.get("hobbies", ""))
    hello = f"Čau, {name}! 😊" if name else "Čau! 😊"
    if projects:
        return f"{hello}\n\nKā virzās šis projekts: {projects[-1]}?\n\nVai šodien tur vajag vienu konkrētu soli, ko sakārtot?\n\nVersija: V114.0"
    if prof:
        return f"{hello}\n\nKā šodien iet ar tavu jomu — {prof}?\n\nKas šobrīd svarīgākais: darbi, klienti vai plānošana?\n\nVersija: V114.0"
    if interests:
        return f"{hello}\n\nAtceros, ka tev interesē {interests[-1]}. Ko šodien gribi ar to pavirzīt uz priekšu?\n\nVersija: V114.0"
    return f"{hello}\n\nEs esmu te. Kas šodien jāsakārto — darbi, atgādinājumi vai domas galvā?\n\nVersija: V114.0"


def v301_capabilities(user_id):
    user = get_user(str(user_id)); name=v301_name(user)
    prof=(user.get('profession') or '').strip(); projects=v301_split_items(user.get('projects','')); interests=v301_split_items(user.get('hobbies',''))
    lines=[f"{name}, es varu palīdzēt praktiski, ne tikai čatot. 😉" if name else "Es varu palīdzēt praktiski, ne tikai čatot. 😉", "", "Es varu:", "🧠 atcerēties svarīgas lietas;", "⏰ palīdzēt izveidot atgādinājumus;", "🎯 sakārtot dienas mērķi;", "📷 saprast bildes un dokumentu foto;", "💬 palīdzēt izrunāt situāciju, ja galvā haoss;"]
    if prof: lines.append(f"💼 pielāgoties tavai jomai: {prof};")
    if projects: lines.append(f"🚀 turpināt sarunu par projektu: {projects[-1]};")
    if interests: lines.append(f"✨ ņemt vērā tavas intereses: {', '.join(interests[:2])};")
    lines += ["", "Tev nav jāiegaumē komandas. Raksti normāli, piemēram:", "rīt jāzvana klientam", "man šodien daudz darbu", "apskati šo bildi", "", "Versija: V114.0"]
    return "\n".join(lines)


def v301_daily_direction(user_id):
    user=get_user(str(user_id)); name=v301_name(user); prof=(user.get('profession') or '').strip(); projects=v301_split_items(user.get('projects',''))
    prefix=f"{name}, " if name else ""
    if projects: return f"{prefix}šodien es sāktu ar vienu soli pie projekta: {projects[-1]}.\n\nKas tur šobrīd bremzē visvairāk?\n\nVersija: V114.0"
    if prof: return f"{prefix}ņemot vērā tavu jomu ({prof}), izvēlamies vienu praktisku prioritāti.\n\nKas svarīgāk: klients, termiņš vai dokumenti?\n\nVersija: V114.0"
    return f"{prefix}izvēlamies vienu galveno lietu šodienai.\n\nKas būtu jāizdara, lai vakarā justos, ka diena nav pagājusi tukši?\n\nVersija: V114.0"


def v301_conversation_answer(user_id, text):
    lower=(text or '').strip().lower(); user=get_user(str(user_id)); name=v301_name(user); projects=v301_split_items(user.get('projects',''))
    if lower in ['čau','cau','sveika','sveiks','hi','hello','hei','labdien'] or lower.startswith(('čau','cau','sveika','sveiks','labdien')): return v301_relationship_greeting(user_id)
    if any(x in lower for x in ['ko vari','ko tu vari','ko māki','ko maki']): return v301_capabilities(user_id)
    if any(x in lower for x in ['kā tev iet','ka tev iet','kā iet','ka iet']):
        if name and projects: return f"Man viss labi, {name}. 😊\n\nBet svarīgāk — kā iet ar projektu: {projects[-1]}?\n\nVai šodien vajag palīdzēt to pavirzīt uz priekšu?\n\nVersija: V114.0"
        if name: return f"Man viss labi, {name}. 😊\n\nBet man interesē, kā iet tev. Kas šodien vairāk spiež — darbi, cilvēki vai haoss galvā?\n\nVersija: V114.0"
        return "Man viss labi. 😊\n\nBet man interesē, kā iet tev. Kas šodien vairāk spiež — darbi, cilvēki vai haoss galvā?\n\nVersija: V114.0"
    if any(x in lower for x in ['ko man darīt','ko man darit','ar ko sākt','ar ko sakt','ko šodien']): return v301_daily_direction(user_id)
    if any(x in lower for x in ['man smagi','smagi','grūti','gruti','slikta diena','noguris','nogurusi']):
        who=f"{name}, " if name else ""; return f"{who}izklausās, ka šobrīd nav viegli. 😔\n\nEs nemetīšos ar gudriem padomiem. Gribi, lai es vienkārši paklausos, vai sadalām problēmu mazākos gabalos?\n\nVersija: V114.0"
    if any(x in lower for x in ['testēju','testeju','pārbaudu','parbaudu']): return "Droši testē. 😄\n\nMan patīk, kad mani pārbauda pa īstam. Iedod vienu reālu situāciju, un skatāmies, vai esmu noderīga.\n\nVersija: V114.0"
    return None


def v301_detect_profile_fact_safe(text):
    raw=(text or '').strip(); lower=raw.lower()
    if not raw or v301_is_core_conversation(lower) or '?' in raw: return {'type':'','value':''}
    try:
        fact=detect_profile_fact(raw)
        if fact and fact.get('type') and fact.get('value'): return fact
    except Exception: pass
    for marker in ['man patīk ', 'man patik ', 'mani interesē ', 'mani interese ', 'interesējos par ', 'interesejos par ']:
        if marker in lower:
            idx=lower.find(marker); value=raw[idx+len(marker):].strip(' .,!?:;')
            if value: return {'type':'interest','value':value[:120]}
    for marker in ['strādāju pie ', 'stradaju pie ', 'mans projekts ir ', 'projekts ir ', 'būvēju ', 'buveju ', 'taisām projektu ', 'taisam projektu ']:
        if marker in lower:
            idx=lower.find(marker); value=raw[idx+len(marker):].strip(' .,!?:;')
            if value: return {'type':'project','value':value[:160]}
    if any(w in lower for w in ['sieva','vīrs','virs','bērns','berns','ģimene','gimene']): return {'type':'family','value':raw[:160]}
    if any(w in lower for w in ['klients','klienti','pasūtītājs','pasutitajs','darījums','darijums']):
        if not any(t in lower for t in ['rīt','rit','pirmdien','otrdien','trešdien','tresdien','jāzvana','jazvana','atgādini','atgadini']): return {'type':'client_topic','value':raw[:160]}
    return {'type':'','value':''}


def v301_save_profile_fact(user_id, fact_type, value):
    value=(value or '').strip()
    if not value: return False
    user=get_user(str(user_id))
    if fact_type=='name': user['name']=value
    elif fact_type=='profession': user['profession']=value
    elif fact_type=='interest': user['hobbies']=v24_append_unique_text(user.get('hobbies',''), value)
    elif fact_type=='project': user['projects']=v24_append_unique_text(user.get('projects',''), value)
    elif fact_type=='family': user['family']=v24_append_unique_text(user.get('family',''), value)
    elif fact_type=='client_topic': user['facts']=v24_append_unique_text(user.get('facts',''), value)
    else: user['facts']=v24_append_unique_text(user.get('facts',''), value)
    update_user(str(user_id), user); return True


def v301_profile_saved_answer(user_id, fact_type, value):
    user=get_user(str(user_id)); name=v301_name(user); prefix=f"{name}, " if name and fact_type!='name' else ''
    if fact_type=='name': return f"Patīkami, {value}. 😊\n\nTagad runāšu ar tevi kā ar pazīstamu cilvēku, nevis kā ar svešinieku.\n\nVersija: V114.0"
    if fact_type=='profession': return f"{prefix}sapratu. 💼\n\nPaturēšu prātā, ka tava joma ir: {value}.\n\nTurpmāk mēģināšu ieteikumus vairāk pieskaņot tavai reālajai dzīvei.\n\nVersija: V114.0"
    if fact_type=='interest': return f"{prefix}noķēru interesi. 🙂\n\nTev svarīga tēma: {value}.\n\nTas man palīdzēs runāt precīzāk.\n\nVersija: V114.0"
    if fact_type=='project': return f"{prefix}piefiksēju šo kā projekta tēmu. 🧠\n\n{value}\n\nVēlāk varēšu atgriezties pie šī un pajautāt, kā virzās.\n\nVersija: V114.0"
    if fact_type=='family': return f"{prefix}piefiksēju. 💙\n\nPersonīgās lietas ir svarīgas, tāpēc runāšu uzmanīgi un bez liekas uzbāzības.\n\nVersija: V114.0"
    if fact_type=='client_topic': return f"{prefix}saprotu, te ir klientu tēma. 🤝\n\nTādas lietas bieži ir vērts pārvērst konkrētā plānā vai atgādinājumā.\n\nVersija: V114.0"
    return f"{prefix}piefiksēju. 😊\n\nVersija: V114.0"


def v301_enhance_vision_answer(user_id, answer, caption=''):
    user=get_user(str(user_id)); name=v301_name(user); prof=(user.get('profession') or '').strip()
    if not answer: return answer
    if 'Versija:' in answer: answer=re.sub(r"\n\nVersija:\s*V[0-9.]+", '', answer).rstrip()
    extra=[f"{name}, es bildi apskatījos praktiski, ne tikai formāli." if name else "Bildīti apskatījos praktiski, ne tikai formāli."]
    if prof and any(x in prof.lower() for x in ['celtn','būv','buv','fasād','fasad']): extra.append('Ja šī bilde ir no darba vai objekta, vari atsūtīt vēl tuvplānu — mēģināšu palīdzēt saprast detaļas.')
    extra.append('Ko tu gribi, lai es ar šo bildi izdaru: aprakstu, novērtēju situāciju vai palīdzu pieņemt lēmumu?')
    return answer.rstrip()+'\n\n'+'\n'.join(extra)+'\n\nVersija: V114.0'


def v301_run_regression_tests():
    tests={
        'kā tev iet Nina': v301_detect_profile_fact_safe('kā tev iet Nina').get('type')=='',
        'čau': v301_detect_profile_fact_safe('čau').get('type')=='',
        'ko vari darīt': v301_detect_profile_fact_safe('ko vari darīt?').get('type')=='',
        'strādāju pie Nina platformas': v301_detect_profile_fact_safe('strādāju pie Nina platformas').get('type')=='project',
        'man patīk AI un bizness': v301_detect_profile_fact_safe('man patīk AI un bizness').get('type')=='interest',
    }
    failed=[k for k,ok in tests.items() if not ok]
    print('V114.0 regression failed: '+str(failed) if failed else 'V114.0 regression OK')
    return not failed

try:
    v301_run_regression_tests()
except Exception as e:
    print('V114.0 regression check kļūda:', repr(e))


# =========================
# V114.0 REVENUE PLATFORM RELEASE
# Usage Engine + Premium Score + Soft Sales + Referral + Admin Stats
# =========================

def v40_log_usage(user_id, event_type, event_value=""):
    try:
        conn = get_db()
        c = conn.cursor()
        db_execute(
            c,
            "INSERT INTO usage_events (user_id, event_type, event_value) VALUES (%s, %s, %s)",
            (str(user_id), str(event_type or ""), str(event_value or "")[:250])
        )
        conn.commit()
        c.close()
        conn.close()
        return True
    except Exception as e:
        print("v40_log_usage kļūda:", repr(e))
        return False


def v40_count_usage(user_id, event_type=None):
    try:
        conn = get_db()
        c = conn.cursor()
        if event_type:
            db_execute(c, "SELECT COUNT(*) FROM usage_events WHERE user_id = %s AND event_type = %s", (str(user_id), str(event_type)))
        else:
            db_execute(c, "SELECT COUNT(*) FROM usage_events WHERE user_id = %s", (str(user_id),))
        row = c.fetchone()
        c.close()
        conn.close()
        return int(row[0] if row else 0)
    except Exception as e:
        print("v40_count_usage kļūda:", repr(e))
        return 0


def v40_snapshot(user_id):
    try:
        real_reminders = active_reminders_count(str(user_id)) if "active_reminders_count" in globals() else 0
    except Exception:
        real_reminders = 0

    return {
        "conversation": v40_count_usage(user_id, "message"),
        "memory": v40_count_usage(user_id, "memory"),
        "reminder": max(v40_count_usage(user_id, "reminder"), int(real_reminders or 0)),
        "vision": v40_count_usage(user_id, "vision"),
        "profile": v40_count_usage(user_id, "profile"),
        "premium_interest": v40_count_usage(user_id, "premium_interest"),
    }


def v40_premium_score(user_id):
    user = get_user(str(user_id))
    if user.get("premium"):
        return 100
    s = v40_snapshot(user_id)
    score = 0
    score += min(s["conversation"] * 3, 25)
    score += min(s["memory"] * 8, 25)
    score += min(s["reminder"] * 10, 25)
    score += min(s["vision"] * 8, 15)
    score += min(s["profile"] * 5, 10)
    score += min(s["premium_interest"] * 10, 20)
    return max(0, min(100, int(score)))


def v40_is_premium_intent(text):
    lower = (text or "").strip().lower()
    return any(w in lower for w in [
        "premium", "abonements", "abonēt", "abonet", "pirkt", "nopirkt",
        "gribu premium", "kā nopirkt", "ka nopirkt", "cik maksā", "cik maksa",
        "tarifs", "cena", "maksas"
    ])


def v40_plan_text():
    return (
        "🔓 Free — pamata saruna, atmiņas un testi.\n\n"
        "💎 Premium Basic — 4.99 EUR/mēnesī\n"
        "Vairāk atmiņas, vairāk atgādinājumu un ērtāka ikdienas palīdzība.\n\n"
        "💎 Premium Plus — 9.99 EUR/mēnesī\n"
        "Aktīvākiem lietotājiem un biznesa vajadzībām."
    )


def v40_premium_offer(user_id, reason=""):
    user = get_user(str(user_id))
    name = (user.get("name") or "").strip()
    if user.get("premium"):
        return (
            f"{name + ', ' if name else ''}tu jau esi Premium režīmā. 💎\n\n"
            "Ja gribi, varu parādīt, kā vislabāk izmantot Premium ikdienā.\n\n"
            "Versija: V114.0"
        )

    score = v40_premium_score(user_id)
    intro = f"{name}, " if name else ""
    reason_line = f"\n\nIemesls: {reason}" if reason else ""
    return (
        f"{intro}Premium nav obligāts, bet tas ir nākamais solis, ja gribi mani izmantot kā nopietnu ikdienas palīgu. 💎"
        f"{reason_line}\n\n"
        f"Tavs Premium Score: {score}/100.\n\n"
        f"{v40_plan_text()}\n\n"
        "Ja gribi, varu parādīt pirkšanas iespējas. Raksti: gribu Premium\n\n"
        "Versija: V114.0"
    )


def v40_soft_sales_line(user_id):
    try:
        user = get_user(str(user_id))
        if user.get("premium"):
            return ""
        score = v40_premium_score(user_id)
        if score < 55:
            return ""
        name = (user.get("name") or "").strip()
        return (
            f"\n\n💎 {name + ', ' if name else ''}starp citu — redzu, ka sāc mani izmantot praktiski. "
            "Kad būsi gatavs, Premium Basic varētu dot vairāk atmiņas un atgādinājumu."
        )
    except Exception:
        return ""


def v40_usage_answer(user_id):
    s = v40_snapshot(user_id)
    score = v40_premium_score(user_id)
    return (
        "📊 Tavs Nina lietošanas pārskats\n\n"
        f"💬 Sarunas: {s['conversation']}\n"
        f"🧠 Atmiņas: {s['memory']}\n"
        f"⏰ Atgādinājumi: {s['reminder']}\n"
        f"📷 Bildes/Vision: {s['vision']}\n"
        f"👤 Profila papildinājumi: {s['profile']}\n\n"
        f"💎 Premium Score: {score}/100\n\n"
        "Jo vairāk es tev reāli palīdzu, jo vairāk jēgas ir Premium iespējām.\n\n"
        "Versija: V114.0"
    )


def v40_referral_answer(user_id):
    user = get_user(str(user_id))
    name = (user.get("name") or "").strip()
    bot_name = os.environ.get("BOT_USERNAME", "").strip()
    if bot_name:
        link = f"https://t.me/{bot_name}?start=ref_{user_id}"
    else:
        link = "Ieliec Railway ENV: BOT_USERNAME, tad referral saite būs automātiska."

    return (
        f"{name + ', ' if name else ''}ja zini kādu, kam noderētu tāds palīgs kā Nina, vari mani ieteikt tālāk. 🙂\n\n"
        f"Referral saite:\n{link}\n\n"
        "Vēlāk par uzaicinājumiem varēsim dot bonusus vai Premium dienas.\n\n"
        "Versija: V114.0"
    )


def v40_checkin_permission_answer(user_id, enable=True):
    try:
        conn = get_db()
        c = conn.cursor()
        db_execute(c, "DELETE FROM checkin_settings WHERE user_id = %s", (str(user_id),))
        db_execute(
            c,
            "INSERT INTO checkin_settings (user_id, enabled, last_checkin_at, interval_days) VALUES (%s, %s, %s, %s)",
            (str(user_id), 1 if enable else 0, "", 3)
        )
        conn.commit()
        c.close()
        conn.close()
    except Exception as e:
        print("v40_checkin_permission kļūda:", repr(e))

    if enable:
        return (
            "Sarunāts. 😊\n\n"
            "Ja kādu laiku nerakstīsi, es drīkstēšu reizēm maigi painteresēties, kā tev iet. "
            "Nebūšu uzbāzīga — tikai lai nepazūd svarīgās lietas.\n\n"
            "Versija: V114.0"
        )
    return (
        "Labi, check-in izslēgts. 🔕\n\n"
        "Es pati nerakstīšu, ja nebūsi man to atļāvis.\n\n"
        "Versija: V114.0"
    )


def v40_admin_stats():
    try:
        conn = get_db()
        c = conn.cursor()

        db_execute(c, "SELECT COUNT(*) FROM users")
        users = int((c.fetchone() or [0])[0])

        db_execute(c, "SELECT COUNT(*) FROM users WHERE premium = %s", (1,))
        premium = int((c.fetchone() or [0])[0])

        db_execute(c, "SELECT COUNT(*) FROM reminders WHERE status = %s", ("active",))
        reminders = int((c.fetchone() or [0])[0])

        db_execute(c, "SELECT COUNT(*) FROM memory_backups")
        memories = int((c.fetchone() or [0])[0])

        db_execute(c, "SELECT COUNT(*) FROM usage_events")
        usage = int((c.fetchone() or [0])[0])

        c.close()
        conn.close()

        mrr = premium * PREMIUM_BASIC_PRICE
        return (
            "📊 Nina Platform V40 Admin Stats\n\n"
            f"👥 Lietotāji: {users}\n"
            f"💎 Premium: {premium}\n"
            f"💶 Aptuvenais MRR: {mrr:.2f} EUR\n"
            f"🧠 Atmiņas: {memories}\n"
            f"⏰ Aktīvie atgādinājumi: {reminders}\n"
            f"📈 Usage events: {usage}\n\n"
            "Šis ir pirmais Revenue Dashboard pamats.\n\n"
            "Versija: V114.0"
        )
    except Exception as e:
        return f"Admin stats kļūda: {repr(e)}\n\nVersija: V114.0"


def v40_revenue_router(user_id, text):
    lower = (text or "").strip().lower()

    if lower in ["mans progress", "usage", "statistika", "mana statistika", "premium score", "mans score"]:
        v40_log_usage(user_id, "usage_stats")
        return v40_usage_answer(user_id)

    if v40_is_premium_intent(text):
        v40_log_usage(user_id, "premium_interest", text)
        return v40_premium_offer(user_id, reason="tu pajautāji par Premium vai cenu")

    if any(x in lower for x in ["uzaicināt draugu", "uzaicinat draugu", "referral", "ieteikt draugam"]):
        v40_log_usage(user_id, "referral_interest")
        return v40_referral_answer(user_id)

    if any(x in lower for x in ["vari man pati rakstīt", "vari man pati rakstit", "raksti man pati", "checkin on", "check-in on"]):
        v40_log_usage(user_id, "checkin_on")
        return v40_checkin_permission_answer(user_id, enable=True)

    if any(x in lower for x in ["neraksti pati", "checkin off", "check-in off", "izslēdz check", "izsledz check"]):
        v40_log_usage(user_id, "checkin_off")
        return v40_checkin_permission_answer(user_id, enable=False)

    return None



# =========================
# V114.0 STABLE INTENT ENGINE
# Practical Help + Business Goals + Safer Profile Filter
# =========================

def v401_user_name(user_id):
    try:
        user = get_user(str(user_id))
        return (user.get("name") or "").strip()
    except Exception:
        return ""


def v401_is_help_intent(text):
    lower = (text or "").strip().lower()
    if not lower:
        return False

    help_markers = [
        "man vajag", "vajag lai", "palīdzi", "palidzi", "palīdzēt", "palidzet",
        "gribu pabeigt", "jāpabeidz", "japabeidz", "pabeidzu projektu",
        "pabeigt projektu", "lai raiti", "sakārtot projektu", "sakartot projektu",
        "ko darīt", "ko darit", "ar ko sākt", "ar ko sakt"
    ]
    return any(m in lower for m in help_markers)


def v401_is_business_goal(text):
    lower = (text or "").strip().lower()
    if not lower:
        return False

    goal_markers = [
        "gribu kļūt bagāts", "gribu klut bagats", "kļūt bagāts", "klut bagats",
        "gribu pelnīt", "gribu pelnit", "gribu vairāk naudas", "gribu vairak naudas",
        "gribu vairāk klientu", "gribu vairak klientu", "vajag klientus",
        "attīstīt biznesu", "attistit biznesu", "gribu nopelnīt", "gribu nopelnit",
        "gribu biznesu", "gribu lai pelna", "gribu lai nina pelna"
    ]
    return any(m in lower for m in goal_markers)


def v401_project_help_answer(user_id, text):
    name = v401_user_name(user_id)
    prefix = f"{name}, " if name else ""

    return (
        f"{prefix}sapratu. Te nav vienkārši interese — tu gribi pabeigt projektu raitāk. 💪\n\n"
        "Tad darām praktiski, nevis filozofējam.\n\n"
        "Uzraksti man 3 lietas:\n"
        "1. Kas tieši ir projekts?\n"
        "2. Kas šobrīd visvairāk bremzē?\n"
        "3. Kāds ir tuvākais termiņš?\n\n"
        "Pēc tam es tev salikšu īsu rīcības plānu pa soļiem.\n\n"
        "Versija: V114.0"
    )


def v401_business_goal_answer(user_id, text):
    name = v401_user_name(user_id)
    prefix = f"{name}, " if name else ""

    return (
        f"{prefix}tas ir normāls mērķis. Gribēt vairāk nopelnīt nav nekas slikts — jautājums ir, kā to pārvērst sistēmā. 💼\n\n"
        "Es ieteiktu sākt ar 3 jautājumiem:\n"
        "1. No kā tu šobrīd jau pelni vai vari pelnīt visātrāk?\n"
        "2. Kas tev pietrūkst vairāk — klientu, laika, piedāvājuma vai disciplīnas?\n"
        "3. Kādu vienu produktu vai pakalpojumu varam pārvērst naudā tuvākajās 7 dienās?\n\n"
        "Ja gribi, uzraksti: mans bizness ir... un es palīdzēšu salikt pirmo naudas plānu.\n\n"
        "Versija: V114.0"
    )


def v401_safe_profile_fact(text):
    """
    Safer wrapper around V30/V40 profile detection.
    Blocks help/business/normal conversation from being saved as profile.
    """
    raw = (text or "").strip()
    lower = raw.lower()

    if not raw:
        return {"type": "", "value": ""}

    # Never save questions / help requests / ambition as profile facts
    if "?" in raw:
        return {"type": "", "value": ""}

    if v401_is_help_intent(raw) or v401_is_business_goal(raw):
        return {"type": "", "value": ""}

    if "nina" in lower and any(x in lower for x in ["kā tev iet", "ka tev iet", "ko vari", "testēju", "testeju"]):
        return {"type": "", "value": ""}

    # Prefer existing v301 safe detector if present
    try:
        fact = v301_detect_profile_fact_safe(raw)
        if fact and fact.get("type") and fact.get("value"):
            return fact
    except Exception:
        pass

    # Very strict direct profile markers
    try:
        fact = detect_profile_fact(raw)
        if fact and fact.get("type") and fact.get("value"):
            return fact
    except Exception:
        pass

    return {"type": "", "value": ""}


def v401_intent_router(user_id, text):
    lower = (text or "").strip().lower()

    if v401_is_help_intent(text):
        return v401_project_help_answer(user_id, text)

    if v401_is_business_goal(text):
        return v401_business_goal_answer(user_id, text)

    return None


def v401_regression_check():
    tests = {
        "Man vajag lai raiti pabeidzu projektu": v401_safe_profile_fact("Man vajag lai raiti pabeidzu projektu").get("type") == "",
        "es gribu kļūt bagāts": v401_safe_profile_fact("es gribu kļūt bagāts").get("type") == "",
        "kā tev iet Nina": v401_safe_profile_fact("kā tev iet Nina").get("type") == "",
        "man patīk AI un bizness": v401_safe_profile_fact("man patīk AI un bizness").get("type") in ["interest", ""],
        "strādāju pie Nina platformas": v401_safe_profile_fact("strādāju pie Nina platformas").get("type") in ["project", ""],
    }
    failed = [k for k, ok in tests.items() if not ok]
    if failed:
        print("V114.0 regression failed:", failed)
    else:
        print("V114.0 regression OK")
    return not failed

try:
    v401_regression_check()
except Exception as e:
    print('V114.0 regression check kļūda:', repr(e))


# =========================
# V114.0 AI ASSISTANT PLATFORM RELEASE
# Long-Term Memory + Smart Check-in + Premium Flow 2.0 + Admin 2.0
# =========================

def v50_now_text():
    return datetime.now(ZoneInfo(DEFAULT_TIMEZONE)).strftime("%Y-%m-%d %H:%M:%S")


def v50_save_long_memory(user_id, memory_type, memory_text, importance=1):
    memory_text = (memory_text or "").strip()
    if not memory_text:
        return False
    try:
        conn = get_db()
        c = conn.cursor()
        db_execute(
            c,
            """
            INSERT INTO long_term_memories (user_id, memory_type, memory_text, importance)
            VALUES (%s, %s, %s, %s)
            """,
            (str(user_id), str(memory_type or "general"), memory_text[:700], int(importance or 1))
        )
        conn.commit()
        c.close()
        conn.close()
        return True
    except Exception as e:
        print("v50_save_long_memory kļūda:", repr(e))
        return False


def v50_latest_long_memories(user_id, limit=5):
    try:
        conn = get_db()
        c = conn.cursor()
        db_execute(
            c,
            """
            SELECT memory_type, memory_text, importance, created_at
            FROM long_term_memories
            WHERE user_id = %s
            ORDER BY importance DESC, id DESC
            LIMIT %s
            """,
            (str(user_id), int(limit or 5))
        )
        rows = c.fetchall()
        c.close()
        conn.close()
        return rows or []
    except Exception as e:
        print("v50_latest_long_memories kļūda:", repr(e))
        return []


def v50_detect_long_memory_candidate(text):
    raw = (text or "").strip()
    lower = raw.lower()
    if not raw or "?" in raw:
        return None

    if any(x in lower for x in ["mans bizness ir", "mana joma ir", "mans galvenais projekts", "man svarīgi", "man svarigi"]):
        return ("important_fact", raw, 3)

    if any(x in lower for x in ["gribu pelnīt", "gribu pelnit", "gribu kļūt bagāts", "gribu klut bagats", "gribu vairāk klientu", "gribu vairak klientu"]):
        return ("business_goal", raw, 3)

    if any(x in lower for x in ["strādāju pie", "stradaju pie", "mans projekts ir", "būvēju", "buveju"]):
        return ("project", raw, 2)

    if any(x in lower for x in ["sieva", "ģimene", "gimene", "bērns", "berns"]):
        return ("personal", raw, 2)

    return None


def v50_maybe_save_long_memory(user_id, text):
    cand = v50_detect_long_memory_candidate(text)
    if not cand:
        return False
    mtype, mtext, importance = cand
    return v50_save_long_memory(user_id, mtype, mtext, importance)


def v50_add_checkin(user_id, checkin_text, days=3, source="manual"):
    try:
        due = (datetime.now(ZoneInfo(DEFAULT_TIMEZONE)) + timedelta(days=int(days or 3))).strftime("%Y-%m-%d %H:%M:%S")
        conn = get_db()
        c = conn.cursor()
        db_execute(
            c,
            """
            INSERT INTO checkin_queue (user_id, checkin_text, due_at, status, source)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (str(user_id), str(checkin_text or "")[:500], due, "pending", str(source or "manual"))
        )
        conn.commit()
        c.close()
        conn.close()
        return True
    except Exception as e:
        print("v50_add_checkin kļūda:", repr(e))
        return False


def v50_pending_checkins(user_id, limit=5):
    try:
        conn = get_db()
        c = conn.cursor()
        db_execute(
            c,
            """
            SELECT id, checkin_text, due_at, source
            FROM checkin_queue
            WHERE user_id = %s AND status = %s
            ORDER BY id DESC
            LIMIT %s
            """,
            (str(user_id), "pending", int(limit or 5))
        )
        rows = c.fetchall()
        c.close()
        conn.close()
        return rows or []
    except Exception as e:
        print("v50_pending_checkins kļūda:", repr(e))
        return []


def v50_checkin_status_answer(user_id):
    rows = v50_pending_checkins(user_id, limit=10)
    if not rows:
        return (
            "🤝 Šobrīd nav ieplānotu check-in.\n\n"
            "Ja gribi, raksti: atgādini man painteresēties pēc 3 dienām par klientu.\n\n"
            "Versija: V114.0"
        )

    lines = ["🤝 Ieplānotie check-in:"]
    for row in rows:
        try:
            cid, text, due_at, source = row
            lines.append(f"• {text} — ap {due_at}")
        except Exception:
            pass
    lines.append("")
    lines.append("Versija: V114.0")
    return "\n".join(lines)


def v50_mark_premium_lead(user_id, lead_type, lead_text="", score=0):
    try:
        conn = get_db()
        c = conn.cursor()
        db_execute(
            c,
            """
            INSERT INTO premium_leads (user_id, lead_type, lead_text, score)
            VALUES (%s, %s, %s, %s)
            """,
            (str(user_id), str(lead_type or ""), str(lead_text or "")[:500], int(score or 0))
        )
        conn.commit()
        c.close()
        conn.close()
        return True
    except Exception as e:
        print("v50_mark_premium_lead kļūda:", repr(e))
        return False


def v50_premium_checkout_answer(user_id):
    user = get_user(str(user_id))
    name = (user.get("name") or "").strip()
    intro = f"{name}, " if name else ""

    basic_url = STRIPE_BASIC_CHECKOUT_URL or ""
    plus_url = STRIPE_PLUS_CHECKOUT_URL or ""

    if basic_url or plus_url:
        lines = [f"{intro}šeit ir Premium pirkšanas iespējas. 💎", ""]
        if basic_url:
            lines.append(f"Premium Basic — 4.99 EUR/mēnesī:\n{basic_url}")
        if plus_url:
            lines.append(f"\nPremium Plus — 9.99 EUR/mēnesī:\n{plus_url}")
        lines.append("")
        lines.append("Pēc maksājuma Premium statusu varēsim pieslēgt automātiski ar Stripe webhook vai manuāli admin panelī.")
        lines.append("")
        lines.append("Versija: V114.0")
        return "\n".join(lines)

    return (
        f"{intro}Premium plūsma ir gatava loģikas līmenī, bet vēl nav ielikta Stripe saite Railway ENV. 💎\n\n"
        "Railway vajag pievienot:\n"
        "STRIPE_BASIC_CHECKOUT_URL\n"
        "STRIPE_PLUS_CHECKOUT_URL\n\n"
        "Pagaidām Premium var testēt ar tekstu un admin statusu.\n\n"
        "Versija: V114.0"
    )


def v50_admin_dashboard_answer():
    try:
        conn = get_db()
        c = conn.cursor()

        def one(sql, params=None):
            db_execute(c, sql, params or ())
            row = c.fetchone()
            return int(row[0] if row else 0)

        users = one("SELECT COUNT(*) FROM users")
        premium = one("SELECT COUNT(*) FROM users WHERE premium = %s", (1,))
        memories = one("SELECT COUNT(*) FROM memory_backups")
        long_memories = one("SELECT COUNT(*) FROM long_term_memories")
        reminders = one("SELECT COUNT(*) FROM reminders WHERE status = %s", ("active",))
        checkins = one("SELECT COUNT(*) FROM checkin_queue WHERE status = %s", ("pending",))
        leads = one("SELECT COUNT(*) FROM premium_leads WHERE status = %s", ("open",))

        try:
            usage = one("SELECT COUNT(*) FROM usage_events")
        except Exception:
            usage = 0

        c.close()
        conn.close()
        mrr = premium * PREMIUM_BASIC_PRICE

        return (
            "📊 Nina Platform V50 Admin Dashboard\n\n"
            f"👥 Lietotāji: {users}\n"
            f"💎 Premium: {premium}\n"
            f"💶 Aptuvenais MRR: {mrr:.2f} EUR\n\n"
            f"🧠 Atmiņas: {memories}\n"
            f"🧬 Long-term memories: {long_memories}\n"
            f"⏰ Aktīvie atgādinājumi: {reminders}\n"
            f"🤝 Pending check-ins: {checkins}\n"
            f"🔥 Premium leads: {leads}\n"
            f"📈 Usage events: {usage}\n\n"
            "Versija: V114.0"
        )
    except Exception as e:
        return f"V50 admin dashboard kļūda: {repr(e)}\n\nVersija: V114.0"


def v50_memory_answer(user_id):
    rows = v50_latest_long_memories(user_id, limit=10)
    if not rows:
        return (
            "🧬 Ilgtermiņa atmiņā vēl nav daudz datu.\n\n"
            "Vari man pateikt stabilas lietas, piemēram:\n"
            "mans bizness ir fasādes\n"
            "mans galvenais projekts ir Nina platforma\n"
            "man svarīgi ir nopelnīt ar AI darbiniekiem\n\n"
            "Versija: V114.0"
        )

    lines = ["🧬 Ko es atceros ilgtermiņā:"]
    for row in rows:
        try:
            mtype, mtext, importance, created_at = row
            lines.append(f"• [{mtype}] {mtext}")
        except Exception:
            pass
    lines.append("")
    lines.append("Versija: V114.0")
    return "\n".join(lines)


def v50_assistant_router(user_id, text):
    lower = (text or "").strip().lower()

    if lower in ["mana ilgtermiņa atmiņa", "ilgtermiņa atmiņa", "long memory", "ko tu atceries ilgtermiņā"]:
        return v50_memory_answer(user_id)

    if lower in ["checkin", "check-in", "mani checkin", "mani check-in", "checkin status"]:
        return v50_checkin_status_answer(user_id)

    if any(x in lower for x in ["pirkt premium", "nopirkt premium", "premium saite", "checkout", "maksāt premium", "maksat premium"]):
        try:
            score = v40_premium_score(user_id)
        except Exception:
            score = 0
        v50_mark_premium_lead(user_id, "checkout_intent", text, score)
        return v50_premium_checkout_answer(user_id)

    if lower in ["v50 admin", "admin dashboard", "platform dashboard", "dashboard"]:
        if is_admin(user_id):
            return v50_admin_dashboard_answer()
        return "Šī komanda ir tikai adminam.\n\nVersija: V114.0"

    return None


def v50_enhance_answer_with_memory(user_id, answer, user_text):
    try:
        v50_maybe_save_long_memory(user_id, user_text)
    except Exception as e:
        print("v50_maybe_save_long_memory kļūda:", repr(e))

    lower = (user_text or "").strip().lower()
    checkin_line = ""
    if any(x in lower for x in ["rīt", "rit", "pirmdien", "pie ārsta", "pie arsta", "klientam", "sapulce", "projekts"]):
        checkin_line = "\n\n🤝 Varu vēlāk arī painteresēties, kā ar šo gāja. Ja gribi, raksti: vari man pati rakstīt"

    if not answer:
        return answer

    if checkin_line and "Versija:" in answer:
        answer = re.sub(r"\n\nVersija:\s*V[0-9.]+", "", answer).rstrip()
        return answer + checkin_line + "\n\nVersija: V114.0"

    return answer


def v50_regression_check():
    tests = {
        "memory_candidate": v50_detect_long_memory_candidate("mans bizness ir fasādes") is not None,
        "business_goal": v50_detect_long_memory_candidate("gribu pelnīt ar AI") is not None,
        "no_question_memory": v50_detect_long_memory_candidate("kā tev iet?") is None,
    }
    failed = [k for k, ok in tests.items() if not ok]
    print("V50 regression failed:" if failed else "V50 regression OK", failed if failed else "")
    return not failed

try:
    v50_regression_check()
except Exception as e:
    print('V50 regression check kļūda:', repr(e))


# =========================
# V114.0 INTELLIGENCE + NAVIGATION RELEASE
# Intent Engine 2.0 + Location Engine + Variation Engine + Smarter Safety
# =========================

def v60_pick(user_id, intent, variants):
    """Pick a varied answer. Simple random now; table ready for future anti-repeat logic."""
    try:
        import random
        if not variants:
            return ""
        choice = random.choice(variants)
        try:
            conn = get_db()
            c = conn.cursor()
            db_execute(
                c,
                "INSERT INTO response_variation_log (user_id, intent, variant_key) VALUES (%s, %s, %s)",
                (str(user_id), str(intent or ""), str(variants.index(choice)))
            )
            conn.commit()
            c.close()
            conn.close()
        except Exception:
            pass
        return choice
    except Exception:
        return variants[0] if variants else ""


def v60_name(user_id):
    try:
        user = get_user(str(user_id))
        return (user.get("name") or "").strip()
    except Exception:
        return ""


def v60_save_location(user_id, location_type, location_text, latitude="", longitude=""):
    location_text = (location_text or "").strip()
    if not location_text and not (latitude and longitude):
        return False

    try:
        conn = get_db()
        c = conn.cursor()
        db_execute(
            c,
            """
            INSERT INTO user_locations (user_id, location_type, location_text, latitude, longitude)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (str(user_id), str(location_type or "custom"), location_text[:300], str(latitude or ""), str(longitude or ""))
        )
        conn.commit()
        c.close()
        conn.close()
        return True
    except Exception as e:
        print("v60_save_location kļūda:", repr(e))
        return False


def v60_latest_location(user_id, location_type="home"):
    try:
        conn = get_db()
        c = conn.cursor()
        db_execute(
            c,
            """
            SELECT location_text, latitude, longitude, created_at
            FROM user_locations
            WHERE user_id = %s AND location_type = %s
            ORDER BY id DESC
            LIMIT 1
            """,
            (str(user_id), str(location_type or "home"))
        )
        row = c.fetchone()
        c.close()
        conn.close()
        return row
    except Exception as e:
        print("v60_latest_location kļūda:", repr(e))
        return None


def v60_location_profile_answer(user_id):
    home = v60_latest_location(user_id, "home")
    if not home:
        return (
            "📍 Par tavām vietām vēl neko droši nezinu.\n\n"
            "Vari uzrakstīt, piemēram:\n"
            "es dzīvoju Baldonē\n"
            "mana mājas adrese ir ...\n"
            "mans darbs ir ...\n\n"
            "Versija: V114.0"
        )

    location_text, lat, lon, created_at = home
    return (
        "📍 Ko es zinu par tavām vietām\n\n"
        f"🏠 Mājas: {location_text or 'nav teksta'}\n\n"
        "Ja vēlāk rakstīsi 'atrod ceļu mājās', es vispirms prasīšu, kur tu esi tagad, un tad palīdzēšu ar maršrutu.\n\n"
        "Versija: V114.0"
    )


def v60_detect_location_fact(text):
    raw = (text or "").strip()
    lower = raw.lower()
    if not raw or "?" in raw:
        return None

    markers = [
        ("es dzīvoju ", "home"),
        ("es dzivoju ", "home"),
        ("dzīvoju ", "home"),
        ("dzivoju ", "home"),
        ("mana mājas adrese ir ", "home"),
        ("mana majas adrese ir ", "home"),
        ("manas mājas ir ", "home"),
        ("manas majas ir ", "home"),
        ("mans darbs ir ", "work"),
        ("strādāju adresē ", "work"),
        ("stradaju adrese ", "work"),
    ]

    for marker, loc_type in markers:
        if lower.startswith(marker):
            value = raw[len(marker):].strip(" .,!?:;")
            if value:
                return loc_type, value

    # "es baldonē dzīvoju" variant
    m = re.match(r"^es\s+(.+?)\s+(dzīvoju|dzivoju)\.?$", lower)
    if m:
        value = raw[3:].rsplit(" ", 1)[0].strip(" .,!?:;")
        if value:
            return "home", value

    return None


def v60_is_navigation_intent(text):
    lower = (text or "").strip().lower()
    if not lower:
        return False
    markers = [
        "atrod man ceļu", "atrod celu", "ceļu mājās", "celu majas",
        "kā tikt", "ka tikt", "aizved mani", "navigācija", "navigacija",
        "kur ir", "parādi ceļu", "paradi celu", "maršruts", "marsruts",
        "uz mājām", "uz majam"
    ]
    return any(m in lower for m in markers)


def v60_navigation_answer(user_id, text):
    name = v60_name(user_id)
    home = v60_latest_location(user_id, "home")
    prefix = f"{name}, " if name else ""

    lower = (text or "").strip().lower()
    if any(x in lower for x in ["mājās", "majas", "uz mājām", "uz majam"]):
        if home:
            location_text, lat, lon, created_at = home
            return (
                f"{prefix}varu palīdzēt ar ceļu mājās. 📍\n\n"
                f"Es zinu tavas mājas kā: {location_text}.\n\n"
                "Tagad man vajag vienu lietu: kur tu šobrīd atrodies?\n"
                "Vari Telegramā atsūtīt lokāciju vai uzrakstīt adresi/vietu.\n\n"
                "Kad zināšu starta punktu, varēšu palīdzēt salikt maršrutu.\n\n"
                "Versija: V114.0"
            )
        return (
            f"{prefix}varu palīdzēt, bet es vēl nezinu, kur tev ir mājas. 📍\n\n"
            "Uzraksti, piemēram:\n"
            "es dzīvoju Baldonē\n\n"
            "Un pēc tam: atrod man ceļu mājās.\n\n"
            "Versija: V114.0"
        )

    return (
        f"{prefix}varu palīdzēt ar maršrutu. 📍\n\n"
        "Uzraksti divas vietas:\n"
        "1. Kur tu esi tagad?\n"
        "2. Kur jānokļūst?\n\n"
        "Piemēram: esmu Rīgas centrā, jābrauc uz Baldoni.\n\n"
        "Versija: V114.0"
    )


def v60_is_urgent_help(text):
    lower = (text or "").strip().lower()
    return any(x in lower for x in [
        "glāb mani", "glab mani", "palīgā", "paliga", "man draud", "esmu briesmās",
        "esmu briesmas", "nevaru elpot", "avārija", "avarija", "sos"
    ])


def v60_urgent_help_answer(user_id, text):
    return (
        "Es tevi uztveru nopietni. Ja ir tūlītējas briesmas, zvani 112 tagad. 🚨\n\n"
        "Ja nav fizisku briesmu, bet ir panika vai haoss, raksti man vienā teikumā:\n"
        "kas notika, kur tu esi, un kas ir pirmais, ko vajag atrisināt.\n\n"
        "Es palīdzēšu soli pa solim.\n\n"
        "Versija: V114.0"
    )


def v60_is_nonsense_or_play(text):
    lower = (text or "").strip().lower()
    if not lower:
        return False
    markers = [
        "es esmu citplanētietis", "esmu citplanetietis", "es esmu kartupelis",
        "tu esi banāns", "tu esi bananas", "bla bla", "asdf", "lalala",
        "muļķības", "mulķības", "mulkibas", "random", "hahaha"
    ]
    return any(m in lower for m in markers)


def v60_fun_answer(user_id, text):
    variants = [
        "😄 Labi, šo ieskaitu kā radošo testu. Tagad dod man vienu īstu uzdevumu, lai varu pierādīt, ka neesmu tikai smuka poga Telegramā.\n\nVersija: V114.0",
        "Haha, pieņemu. 😄 Bet es tevi noķēru — tu testē, vai es atkārtojos. Ne tik ātri. Kas ir īstais uzdevums?\n\nVersija: V114.0",
        "Okei, kosmoss pieņemts. 🚀 Tagad atgriežamies uz Zemes: kas šodien jāsakārto?\n\nVersija: V114.0",
        "😏 Tu man met muļķības, es metu atpakaļ jautājumu: gribi mani testēt vai tiešām vajag palīdzību?\n\nVersija: V114.0",
    ]
    return v60_pick(user_id, "fun", variants)


def v60_better_smalltalk_answer(user_id, text):
    variants = [
        "Esmu te. 😊 Pasaki konkrēti — vajag palīdzību, plānu, atgādinājumu vai vienkārši izrunāt galvu?\n\nVersija: V114.0",
        "Klausos. 🙂 Dod man vienu reālu situāciju, un es mēģināšu to sakārtot pa soļiem.\n\nVersija: V114.0",
        "Labi, ejam praktiski. Kas šobrīd ir pirmais, ko vajag atrisināt?\n\nVersija: V114.0",
        "Es varu palīdzēt, bet man vajag mazliet kontekstu. Kas notiek?\n\nVersija: V114.0",
    ]
    return v60_pick(user_id, "smalltalk", variants)


def v60_location_received_answer(user_id, latitude, longitude):
    v60_save_location(user_id, "current", "Telegram location", latitude, longitude)
    return (
        "📍 Saņēmu tavu atrašanās vietu.\n\n"
        "Tagad vari rakstīt, kur jānokļūst, piemēram:\n"
        "uz mājām\n"
        "uz darbu\n"
        "uz Baldoni\n\n"
        "Versija: V114.0"
    )


def v60_intent_router(user_id, text):
    loc = v60_detect_location_fact(text)
    if loc:
        loc_type, loc_text = loc
        v60_save_location(user_id, loc_type, loc_text)
        if loc_type == "home":
            return (
                f"📍 Piefiksēju: tavas mājas ir {loc_text}.\n\n"
                "Tagad, ja rakstīsi 'atrod man ceļu mājās', es zināšu galamērķi un pajautāšu tikai, kur tu esi tagad.\n\n"
                "Versija: V114.0"
            )
        return (
            f"📍 Piefiksēju vietu: {loc_text}.\n\n"
            "Varēšu to izmantot navigācijas un profila kontekstā.\n\n"
            "Versija: V114.0"
        )

    lower = (text or "").strip().lower()

    if lower in ["manas vietas", "mana lokācija", "mana lokacija", "kur es dzīvoju", "kur es dzivoju"]:
        return v60_location_profile_answer(user_id)

    if v60_is_urgent_help(text):
        return v60_urgent_help_answer(user_id, text)

    if v60_is_navigation_intent(text):
        return v60_navigation_answer(user_id, text)

    if v60_is_nonsense_or_play(text):
        return v60_fun_answer(user_id, text)

    return None


def v60_regression_check():
    tests = {
        "home1": v60_detect_location_fact("es dzīvoju Baldonē") is not None,
        "home2": v60_detect_location_fact("es Baldonē dzīvoju") is not None,
        "nav": v60_is_navigation_intent("atrod man ceļu mājās"),
        "urgent": v60_is_urgent_help("glāb mani"),
        "play": v60_is_nonsense_or_play("es esmu citplanētietis"),
    }
    failed = [k for k, ok in tests.items() if not ok]
    if failed:
        print("V60 regression failed:", failed)
    else:
        print("V60 regression OK")
    return not failed

try:
    v60_regression_check()
except Exception as e:
    print('V60 regression check kļūda:', repr(e))


# =========================
# V114.0 NAVIGATION HOTFIX
# Navigation priority above generic help/project intent
# =========================

def v601_is_navigation_capability_question(text):
    lower = (text or "").strip().lower()
    return any(x in lower for x in [
        "tu navigāciju rubī", "tu navigaciju rubi", "tu rubī navigāciju", "tu rubi navigaciju",
        "tu saproti navigāciju", "tu saproti navigaciju", "māki navigāciju", "maki navigaciju",
        "vai tu proti navigāciju", "vai tu proti navigaciju", "navigāciju rubī", "navigaciju rubi",
        "kas ir navigācija", "kas ir navigacija"
    ])


def v601_navigation_capability_answer(user_id):
    return (
        "Jā, navigācijas loģiku saprotu. 📍\n\n"
        "Es varu:\n"
        "• atcerēties tavas mājas vai darba vietu;\n"
        "• saprast frāzes kā “atrod ceļu mājās”, “kā tikt uz Rīgu”, “no Baldones uz Rīgu”;\n"
        "• izmantot Telegram atsūtītu lokāciju kā starta punktu;\n"
        "• sagatavot maršruta dialogu.\n\n"
        "Pilnīgi precīzam ceļam ar laiku, kilometriem un karti vēl vajadzēs pieslēgt Google Maps vai OpenStreetMap servisu.\n\n"
        "Pamēģini rakstīt:\n"
        "no Baldones uz Rīgu\n"
        "vai: atrod man ceļu mājās\n\n"
        "Versija: V114.0"
    )


def v601_extract_route_places(text):
    raw = (text or "").strip()
    lower = raw.lower()

    # Common Latvian route patterns
    patterns = [
        r"no\s+(.+?)\s+uz\s+(.+?)(?:\s|$)",
        r"no\s+(.+?)\s+līdz\s+(.+?)(?:\s|$)",
        r"no\s+(.+?)\s+lidz\s+(.+?)(?:\s|$)",
        r"(.+?)\s+uz\s+(.+?)\s+(?:parādi|paradi|rādi|radi|rādi man|radi man)",
    ]

    for pat in patterns:
        m = re.search(pat, lower)
        if m:
            start = m.group(1).strip(" .,!?:;")
            dest = m.group(2).strip(" .,!?:;")
            # clean common tails
            for tail in ["parādi man ceļu", "paradi man celu", "parādi ceļu", "paradi celu", "rādi", "radi", "man"]:
                dest = dest.replace(tail, "").strip(" .,!?:;")
            if start and dest and len(start) < 80 and len(dest) < 80:
                return start, dest

    # "palīdzi man nokļūt Rīgā" destination only
    dest_markers = [
        "palīdzi man nokļūt ", "palidzi man noklut ",
        "man vajag nokļūt ", "man vajag noklut ",
        "kā tikt uz ", "ka tikt uz ",
        "ceļu uz ", "celu uz ",
        "maršruts uz ", "marsruts uz ",
        "aizved mani uz ", "ved mani uz ",
        "braukt uz ", "aizbraukt uz "
    ]

    for marker in dest_markers:
        if marker in lower:
            idx = lower.find(marker)
            dest = raw[idx + len(marker):].strip(" .,!?:;")
            for cut in ["parādi", "paradi", "rādi", "radi", "ceļu", "celu", "tagad"]:
                dest = re.sub(r"\b" + re.escape(cut) + r"\b", "", dest, flags=re.IGNORECASE).strip(" .,!?:;")
            if dest:
                return "", dest

    return "", ""


def v601_is_navigation_intent(text):
    lower = (text or "").strip().lower()
    if not lower:
        return False

    if v601_is_navigation_capability_question(text):
        return True

    strong_markers = [
        "nokļūt", "noklut", "parādi man ceļu", "paradi man celu", "parādi ceļu", "paradi celu",
        "rādi man ceļu", "radi man celu", "ceļu uz", "celu uz", "ceļš uz", "cels uz",
        "kā tikt", "ka tikt", "maršruts", "marsruts", "aizved mani", "ved mani",
        "atrod man ceļu", "atrod man celu", "atrod ceļu", "atrod celu",
        "uz rīgu", "uz rigu", "no baldones", "no rīgas", "no rigas",
        "braukt uz", "aizbraukt uz", "tikt līdz", "tikt lidz"
    ]
    if any(m in lower for m in strong_markers):
        return True

    # route shape: "no X uz Y"
    if re.search(r"\bno\s+.+?\s+uz\s+.+", lower):
        return True

    try:
        return v60_is_navigation_intent(text)
    except Exception:
        return False


def v601_navigation_answer(user_id, text):
    if v601_is_navigation_capability_question(text):
        return v601_navigation_capability_answer(user_id)

    name = v60_name(user_id) if "v60_name" in globals() else ""
    prefix = f"{name}, " if name else ""

    start, dest = v601_extract_route_places(text)

    # If start missing but user has Telegram current location, we still ask for confirmation.
    home = None
    try:
        home = v60_latest_location(user_id, "home")
    except Exception:
        home = None

    if start and dest:
        return (
            f"{prefix}jā, šis ir navigācijas jautājums. 📍\n\n"
            f"Starts: {start}\n"
            f"Galamērķis: {dest}\n\n"
            "Šobrīd es varu sagatavot maršruta dialogu, bet precīzam ceļam ar minūtēm/kilometriem jāpieslēdz Google Maps vai OpenStreetMap.\n\n"
            "Praktiski tagad vari darīt tā:\n"
            f"1. Atver karti.\n"
            f"2. Ievadi: {start} → {dest}.\n"
            "3. Izvēlies auto, sabiedrisko vai kājām.\n\n"
            "Nākamajā versijā pieslēgsim karšu servisu, lai es varu dot tiešu linku/maršrutu.\n\n"
            "Versija: V114.0"
        )

    if dest:
        if home and any(x in (text or "").lower() for x in ["māj", "maj"]):
            try:
                home_text = home[0]
            except Exception:
                home_text = ""
            return (
                f"{prefix}saprotu — jāpalīdz nokļūt mājās. 📍\n\n"
                f"Mājas: {home_text}\n\n"
                "Tagad man vajag starta punktu. Atsūti Telegram lokāciju vai uzraksti, kur tu esi tagad.\n\n"
                "Versija: V114.0"
            )

        return (
            f"{prefix}saprotu — tev vajag nokļūt uz: {dest}. 📍\n\n"
            "Lai saliktu maršrutu, man vēl vajag starta vietu.\n"
            "Uzraksti, piemēram:\n"
            f"esmu Baldonē, jābrauc uz {dest}\n"
            "vai atsūti Telegram lokāciju.\n\n"
            "Versija: V114.0"
        )

    # home route
    lower = (text or "").lower()
    if any(x in lower for x in ["mājās", "majas", "uz mājām", "uz majam"]):
        try:
            return v60_navigation_answer(user_id, text).replace("V114.0", "V114.0")
        except Exception:
            pass

    return (
        f"{prefix}saprotu, tu prasi navigāciju. 📍\n\n"
        "Uzraksti maršrutu šādi:\n"
        "no Baldones uz Rīgu\n"
        "vai: esmu Baldonē, jābrauc uz Rīgu\n\n"
        "Tad es sapratīšu startu un galamērķi.\n\n"
        "Versija: V114.0"
    )


def v601_intent_router(user_id, text):
    # Emergency still first
    try:
        if v60_is_urgent_help(text):
            return v60_urgent_help_answer(user_id, text).replace("V114.0", "V114.0")
    except Exception:
        pass

    # Navigation must be before generic help/project
    if v601_is_navigation_intent(text):
        return v601_navigation_answer(user_id, text)

    # Location facts
    try:
        loc = v60_detect_location_fact(text)
        if loc:
            loc_type, loc_text = loc
            v60_save_location(user_id, loc_type, loc_text)
            if loc_type == "home":
                return (
                    f"📍 Piefiksēju: tavas mājas ir {loc_text}.\n\n"
                    "Tagad, ja rakstīsi 'atrod man ceļu mājās', es zināšu galamērķi un pajautāšu tikai, kur tu esi tagad.\n\n"
                    "Versija: V114.0"
                )
    except Exception:
        pass

    return None


def v601_regression_check():
    tests = {
        "nav_noklut": v601_is_navigation_intent("palīdzi man nokļūt Rīgā"),
        "nav_route": v601_is_navigation_intent("man vajag nokļūt tagad no Baldones uz Rīgu parādi man ceļu"),
        "nav_question": v601_is_navigation_intent("tu navigāciju rubī?"),
        "extract_route": v601_extract_route_places("man vajag nokļūt tagad no Baldones uz Rīgu parādi man ceļu")[0] != "",
    }
    failed = [k for k, ok in tests.items() if not ok]
    if failed:
        print("V114.0 regression failed:", failed)
    else:
        print("V114.0 regression OK")
    return not failed

try:
    v601_regression_check()
except Exception as e:
    print('V114.0 regression check kļūda:', repr(e))


# =========================
# V114.0 NAVIGATION POLISH
# Place normalization + better route parser
# =========================

def v602_normalize_place(place):
    p = (place or "").strip(" .,!?:;")
    if not p:
        return ""

    noise = {
        "ceļu","celu","ceļš","cels","man","rādi","radi","parādi","paradi",
        "lūdzu","ludzu","tagad","vajag","nokļūt","noklut","palīdzi","palidzi",
        "braukt","aizbraukt","maršruts","marsruts"
    }
    parts = [x for x in re.split(r"\s+", p) if x.lower() not in noise]
    p = " ".join(parts).strip(" .,!?:;")
    if not p:
        return ""

    low = p.lower()
    mapping = {
        "rīgā":"Rīga","rīgu":"Rīga","riga":"Rīga","rīgai":"Rīga","rigu":"Rīga",
        "baldonē":"Baldone","baldoni":"Baldone","baldones":"Baldone","baldone":"Baldone",
        "jelgavā":"Jelgava","jelgavu":"Jelgava","jelgava":"Jelgava",
        "ogrē":"Ogre","ogri":"Ogre","ogre":"Ogre",
        "tukumā":"Tukums","tukumu":"Tukums","tukums":"Tukums",
        "jūrmalā":"Jūrmala","jūrmalu":"Jūrmala","jurmala":"Jūrmala",
        "salaspilī":"Salaspils","salaspili":"Salaspils","salaspils":"Salaspils",
        "ķekavā":"Ķekava","kekava":"Ķekava","ķekavu":"Ķekava","kekavu":"Ķekava",
        "siguldā":"Sigulda","siguldu":"Sigulda","sigulda":"Sigulda",
        "liepājā":"Liepāja","liepāju":"Liepāja","liepaja":"Liepāja",
        "ventspilī":"Ventspils","ventspili":"Ventspils","ventspils":"Ventspils",
        "daugavpilī":"Daugavpils","daugavpili":"Daugavpils","daugavpils":"Daugavpils",
    }
    if low in mapping:
        return mapping[low]

    if len(p.split()) == 1:
        if low.endswith("ē"):
            return p[:-1].capitalize() + "e"
        if low.endswith("ā"):
            return p[:-1].capitalize() + "a"
        if low.endswith("u") and len(p) > 4:
            return p[:-1].capitalize() + "a"
        if low.endswith("es") and len(p) > 5:
            return p[:-2].capitalize() + "e"

    return p[:1].upper() + p[1:]


def v602_clean_route_text(s):
    s = (s or "").strip(" .,!?:;")
    phrases = [
        "man vajag nokļūt tagad","man vajag noklut tagad",
        "man vajag nokļūt","man vajag noklut",
        "palīdzi man nokļūt","palidzi man noklut",
        "parādi man ceļu","paradi man celu",
        "parādi ceļu","paradi celu",
        "rādi man","radi man","rādi","radi",
        "ceļu","celu","lūdzu","ludzu","tagad"
    ]
    out = s
    for phrase in phrases:
        out = re.sub(r"\b" + re.escape(phrase) + r"\b", " ", out, flags=re.IGNORECASE)
    return re.sub(r"\s+", " ", out).strip(" .,!?:;")


def v602_extract_route_places(text):
    raw = (text or "").strip()
    lower = raw.lower()

    # Special: "ceļu uz Rīgu man rādi no Baldones"
    m = re.search(r"(?:ceļu|celu|ceļš|cels|maršrutu|marsrutu)\s+uz\s+(.+?)\s+.*?\bno\s+(.+)$", lower)
    if m:
        dest_raw = raw[m.start(1):m.end(1)]
        start_raw = raw[m.start(2):m.end(2)]
        start = v602_normalize_place(v602_clean_route_text(start_raw))
        dest = v602_normalize_place(v602_clean_route_text(dest_raw))
        if start and dest:
            return start, dest

    # Standard: "no X uz Y"
    m = re.search(r"\bno\s+(.+?)\s+(?:uz|līdz|lidz)\s+(.+)$", lower)
    if m:
        start_raw = raw[m.start(1):m.end(1)]
        dest_raw = raw[m.start(2):m.end(2)]
        start = v602_normalize_place(v602_clean_route_text(start_raw))
        dest = v602_normalize_place(v602_clean_route_text(dest_raw))
        if start and dest:
            return start, dest

    # Destination only
    markers = [
        "palīdzi man nokļūt ", "palidzi man noklut ",
        "man vajag nokļūt ", "man vajag noklut ",
        "kā tikt uz ", "ka tikt uz ",
        "ceļu uz ", "celu uz ",
        "ceļš uz ", "cels uz ",
        "maršruts uz ", "marsruts uz ",
        "aizved mani uz ", "ved mani uz ",
        "braukt uz ", "aizbraukt uz ",
    ]
    for marker in markers:
        idx = lower.find(marker)
        if idx >= 0:
            dest_text = raw[idx + len(marker):]
            m2 = re.search(r"\bno\s+(.+)$", dest_text, flags=re.IGNORECASE)
            if m2:
                dest_part = dest_text[:m2.start()].strip()
                start_part = m2.group(1).strip()
                start = v602_normalize_place(v602_clean_route_text(start_part))
                dest = v602_normalize_place(v602_clean_route_text(dest_part))
                if start and dest:
                    return start, dest
            dest = v602_normalize_place(v602_clean_route_text(dest_text))
            if dest:
                return "", dest

    return "", ""


def v602_route_ui(start, dest):
    return (
        "📍 Maršruts\n\n"
        "🏁 Starts\n"
        f"{start}\n\n"
        "⬇️\n\n"
        "🎯 Galamērķis\n"
        f"{dest}\n\n"
        "Precīzam laikam, kilometriem un kartei vēl jāpieslēdz Google Maps vai OpenStreetMap.\n"
        "Bet maršruta virzienu es jau saprotu korekti.\n\n"
        "Versija: V114.0"
    )


def v602_navigation_answer(user_id, text):
    try:
        if v601_is_navigation_capability_question(text):
            return (
                "Jā, navigāciju saprotu. 📍\n\n"
                "Es jau protu atpazīt maršrutus, piemēram:\n"
                "• no Baldones uz Rīgu\n"
                "• ceļu uz Rīgu no Baldones\n"
                "• palīdzi man nokļūt Rīgā\n\n"
                "Šobrīd es vēl nedodu dzīvu kartes aprēķinu ar minūtēm, bet nākamais solis ir pieslēgt Google Maps vai OpenStreetMap.\n\n"
                "Versija: V114.0"
            )
    except Exception:
        pass

    start, dest = v602_extract_route_places(text)
    if start and dest:
        return v602_route_ui(start, dest)

    if dest:
        return (
            "📍 Sapratu galamērķi\n\n"
            f"🎯 Galamērķis: {dest}\n\n"
            "Tagad vajag starta punktu.\n"
            "Uzraksti, piemēram:\n"
            f"no Baldones uz {dest}\n"
            "vai atsūti Telegram lokāciju.\n\n"
            "Versija: V114.0"
        )

    try:
        return v601_navigation_answer(user_id, text).replace("V114.0", "V114.0")
    except Exception:
        try:
            return v60_navigation_answer(user_id, text).replace("V114.0", "V114.0").replace("V114.0", "V114.0")
        except Exception:
            return (
                "📍 Sapratu, ka prasi navigāciju.\n\n"
                "Raksti šādi:\n"
                "no Baldones uz Rīgu\n"
                "vai: ceļu uz Rīgu no Baldones\n\n"
                "Versija: V114.0"
            )


def v602_intent_router(user_id, text):
    try:
        if v60_is_urgent_help(text):
            return v60_urgent_help_answer(user_id, text).replace("V114.0", "V114.0").replace("V114.0", "V114.0")
    except Exception:
        pass

    nav = False
    try:
        nav = v601_is_navigation_intent(text)
    except Exception:
        try:
            nav = v60_is_navigation_intent(text)
        except Exception:
            nav = False

    if nav:
        return v602_navigation_answer(user_id, text)

    return None


def v602_regression_check():
    tests = {
        "norm_riga": v602_normalize_place("Rīgā") == "Rīga",
        "norm_baldone": v602_normalize_place("Baldonē") == "Baldone",
        "route1": v602_extract_route_places("man vajag nokļūt tagad no Baldones uz Rīgu parādi man ceļu") == ("Baldone", "Rīga"),
        "route2": v602_extract_route_places("ceļu uz Rīgu man rādi no Baldones") == ("Baldone", "Rīga"),
        "route3": v602_extract_route_places("palīdzi man nokļūt Rīgā") == ("", "Rīga"),
    }
    failed = [k for k, ok in tests.items() if not ok]
    if failed:
        print("V114.0 regression failed:", failed)
    else:
        print("V114.0 regression OK")
    return not failed

try:
    v602_regression_check()
except Exception as e:
    print('V114.0 regression check kļūda:', repr(e))


# =========================
# V114.0 RELATIONSHIP + SMART MEMORY
# Smart Memory 2.0 + Relationship Engine 2.0
# =========================

def v80_pick(user_id, intent, variants):
    try:
        import random
        return random.choice(variants) if variants else ""
    except Exception:
        return variants[0] if variants else ""


def v80_split(value):
    return [p.strip() for p in re.split(r"[;\n|]+", (value or "")) if p.strip()]


def v80_user_context(user_id):
    try:
        user = get_user(str(user_id))
    except Exception:
        user = {}
    return {
        "name": (user.get("name") or "").strip(),
        "profession": (user.get("profession") or "").strip(),
        "projects": v80_split(user.get("projects", "")),
        "interests": v80_split(user.get("hobbies", "")),
        "facts": v80_split(user.get("facts", "")),
    }


def v80_save_smart_memory(user_id, category, value, weight=1):
    value = (value or "").strip()
    if not value:
        return False
    try:
        conn = get_db()
        c = conn.cursor()
        db_execute(
            c,
            "INSERT INTO smart_memory_profile (user_id, category, value, weight) VALUES (%s, %s, %s, %s)",
            (str(user_id), str(category or "general"), value[:500], int(weight or 1))
        )
        conn.commit()
        c.close()
        conn.close()
        return True
    except Exception as e:
        print("v80_save_smart_memory kļūda:", repr(e))
        return False


def v80_latest_smart_memories(user_id, limit=8):
    try:
        conn = get_db()
        c = conn.cursor()
        db_execute(
            c,
            """
            SELECT category, value, weight, created_at
            FROM smart_memory_profile
            WHERE user_id = %s
            ORDER BY weight DESC, id DESC
            LIMIT %s
            """,
            (str(user_id), int(limit or 8))
        )
        rows = c.fetchall()
        c.close()
        conn.close()
        return rows or []
    except Exception as e:
        print("v80_latest_smart_memories kļūda:", repr(e))
        return []


def v80_detect_smart_memory(text):
    raw = (text or "").strip()
    lower = raw.lower()
    if not raw or "?" in raw:
        return None

    patterns = [
        ("mans bizness ir ", "business", 4),
        ("mans pakalpojums ir ", "service", 4),
        ("mans galvenais projekts ir ", "project", 4),
        ("mans mērķis ir ", "goal", 4),
        ("mans merkis ir ", "goal", 4),
    ]
    for start, cat, weight in patterns:
        if lower.startswith(start):
            value = raw[len(start):].strip(" .,!?:;")
            if value:
                return (cat, value, weight)

    if any(x in lower for x in ["vajag vairāk klientu", "vajag vairak klientu", "gribu vairāk klientu", "gribu vairak klientu"]):
        return ("goal", "vairāk klientu", 3)

    if any(x in lower for x in ["gribu pelnīt", "gribu pelnit", "gribu nopelnīt", "gribu nopelnit"]):
        return ("goal", raw, 3)

    if "fasād" in lower or "fasad" in lower:
        return ("business", "fasādes", 3)

    return None


def v80_maybe_save_smart_memory(user_id, text):
    try:
        item = v80_detect_smart_memory(text)
        if not item:
            return False
        cat, value, weight = item
        return v80_save_smart_memory(user_id, cat, value, weight)
    except Exception as e:
        print("v80_maybe_save_smart_memory kļūda:", repr(e))
        return False


def v80_memory_summary(user_id):
    ctx = v80_user_context(user_id)
    rows = v80_latest_smart_memories(user_id, 10)
    lines = ["🧠 Smart Memory V80"]

    if ctx["name"]:
        lines.append(f"Vārds: {ctx['name']}")
    if ctx["profession"]:
        lines.append(f"Joma: {ctx['profession']}")
    if ctx["projects"]:
        lines.append(f"Projekti: {', '.join(ctx['projects'][-3:])}")
    if ctx["interests"]:
        lines.append(f"Intereses: {', '.join(ctx['interests'][-3:])}")

    if rows:
        lines.append("")
        lines.append("Svarīgās tēmas:")
        for row in rows:
            try:
                cat, value, weight, created_at = row
                lines.append(f"• {cat}: {value}")
            except Exception:
                pass

    if len(lines) == 1:
        lines.append("Vēl nav pietiekami daudz datu. Pasaki, piemēram: mans bizness ir fasādes")

    lines.append("")
    lines.append("Versija: V114.0")
    return "\n".join(lines)


def v80_business_subject(user_id):
    ctx = v80_user_context(user_id)
    rows = v80_latest_smart_memories(user_id, 10)
    for row in rows:
        try:
            cat, value, weight, created_at = row
            if cat in ["service", "business"]:
                return value
        except Exception:
            pass
    if ctx["profession"]:
        return ctx["profession"]
    return ""


def v80_relationship_greeting(user_id):
    ctx = v80_user_context(user_id)
    name = ctx["name"]
    hello = f"Čau, {name}. 😊" if name else "Čau. 😊"
    subject = v80_business_subject(user_id)

    variants = []
    rows = v80_latest_smart_memories(user_id, 5)
    goal = ""
    project = ctx["projects"][-1] if ctx["projects"] else ""

    for row in rows:
        try:
            cat, value, weight, created_at = row
            if cat == "goal" and not goal:
                goal = value
            if cat == "project" and not project:
                project = value
        except Exception:
            pass

    if goal:
        variants.append(f"{hello}\n\nAtceros tavu mērķi: {goal}.\nKā tur virzās — ir progress vai kaut kas bremzē?\n\nVersija: V114.0")
    if subject:
        variants.append(f"{hello}\n\nAtceros, ka tev svarīga tēma ir {subject}. Šodien tur vairāk vajag klientus, piedāvājumu vai plānu?\n\nVersija: V114.0")
    if project:
        variants.append(f"{hello}\n\nAtceros projektu: {project}.\nKas šodien tam dos vienu konkrētu soli uz priekšu?\n\nVersija: V114.0")

    variants += [
        f"{hello}\n\nKas šodien jāsakārto — darbi, nauda, cilvēki vai galvā haoss?\n\nVersija: V114.0",
        f"{hello}\n\nDod man vienu reālu lietu no šodienas, un es palīdzēšu to sadalīt pa soļiem.\n\nVersija: V114.0",
    ]
    return v80_pick(user_id, "relationship_greeting", variants)


def v80_is_business_intent(text):
    lower = (text or "").strip().lower()
    return any(x in lower for x in [
        "vajag klientus", "vairāk klientu", "vairak klientu", "gribu klientus",
        "uzraksti klientu ziņu", "uzraksti klientu zinu", "klientu ziņu", "klientu zinu",
        "pārdošanas ziņa", "pardosanas zina", "piedāvājums klientam", "piedavajums klientam"
    ])


def v80_contextual_business_answer(user_id, text):
    subject = v80_business_subject(user_id)
    ctx = v80_user_context(user_id)
    name = ctx["name"]
    prefix = f"{name}, " if name else ""

    if subject:
        return (
            f"{prefix}atceros, ka tev svarīga tēma ir **{subject}**. 💼\n\n"
            "Tāpēc neprasīšu visu no nulles. Ja vajag vairāk klientu, sākam ar 3 praktiskiem soļiem:\n\n"
            "1. Skaidrs piedāvājums vienā teikumā.\n"
            "2. 20 potenciālie klienti.\n"
            "3. Īsa ziņa, ko viņiem nosūtīt.\n\n"
            "Uzraksti: uzraksti klientu ziņu\n"
            "un es sagatavošu tekstu tieši šai tēmai.\n\n"
            "Versija: V114.0"
        )

    return (
        f"{prefix}vajag vairāk klientu — sapratu. 💼\n\n"
        "Pasaki vienā teikumā, ko tu pārdod un kam tas visvairāk vajadzīgs.\n"
        "Piemēram: mans pakalpojums ir fasādes privātmājām.\n\n"
        "Versija: V114.0"
    )


def v80_client_message_answer(user_id):
    subject = v80_business_subject(user_id) or "pakalpojumu"
    return (
        "Te ir īsa ziņa, ko vari sūtīt vai pielāgot klientam:\n\n"
        f"Labdien! Piedāvāju {subject}. Varu apskatīt situāciju, ieteikt risinājumu un sagatavot saprotamu piedāvājumu. "
        "Ja jums šobrīd tas ir aktuāli, varam sarunāt īsu zvanu vai apskati.\n\n"
        "Ja gribi, varu uztaisīt arī draudzīgāku, agresīvāku vai profesionālāku versiju.\n\n"
        "Versija: V114.0"
    )


def v80_followup_answer(user_id, text):
    lower = (text or "").strip().lower()
    if lower not in ["jā", "ja", "nu", "turpinām", "turpinam", "ko tālāk", "ko talak", "un", "labi", "ok", "ko iesaki"]:
        return None

    try:
        previous = latest_conversation_state(user_id, 5)
    except Exception:
        previous = []

    blob = " ".join([str(x) for row in previous for x in row]).lower() if previous else ""
    if "klient" in blob or "biznes" in blob:
        return (
            "Turpinām par klientiem. 💼\n\n"
            "Nākamais solis: uzraksti, kādu pakalpojumu piedāvā, vai raksti: uzraksti klientu ziņu.\n\n"
            "Versija: V114.0"
        )
    if "maršrut" in blob or "marsrut" in blob or "rīga" in blob or "riga" in blob:
        return (
            "Turpinām par maršrutu. 📍\n\n"
            "Uzraksti startu un galamērķi šādi: no Baldones uz Rīgu.\n\n"
            "Versija: V114.0"
        )
    if "smagi" in blob or "slikti" in blob or "stress" in blob:
        return (
            "Turpinām mierīgi. 😊\n\n"
            "Nosauc vienu lietu, kas šobrīd visvairāk spiež. Tikai vienu.\n\n"
            "Versija: V114.0"
        )
    return None


def v80_mood(text):
    lower = (text or "").strip().lower()
    if any(x in lower for x in ["smagi", "slikti", "stress", "panika"]):
        return "care"
    if any(x in lower for x in ["klient", "nauda", "bizness"]):
        return "business"
    return "warm"


def v80_intent_router(user_id, text):
    lower = (text or "").strip().lower()

    try:
        v80_maybe_save_smart_memory(user_id, text)
    except Exception:
        pass

    if lower in ["smart memory", "mana smart memory", "ko tu zini par mani", "ko tu atceries gudri"]:
        return v80_memory_summary(user_id)

    if lower in ["čau", "cau", "sveika", "sveiks", "hi", "hello", "hei", "labdien"]:
        return v80_relationship_greeting(user_id)

    follow = v80_followup_answer(user_id, text)
    if follow:
        return follow

    if any(x in lower for x in ["uzraksti klientu ziņu", "uzraksti klientu zinu", "klientu ziņu", "klientu zinu"]):
        return v80_client_message_answer(user_id)

    if v80_is_business_intent(text):
        return v80_contextual_business_answer(user_id, text)

    return None


def v80_regression_check():
    tests = {
        "smart_business": v80_detect_smart_memory("mans bizness ir fasādes") is not None,
        "smart_goal": v80_detect_smart_memory("vajag vairāk klientu") is not None,
        "business_intent": v80_is_business_intent("vajag vairāk klientu"),
    }
    failed = [k for k, ok in tests.items() if not ok]
    print("V80 regression failed:" if failed else "V80 regression OK", failed if failed else "")
    return not failed

try:
    v80_regression_check()
except Exception as e:
    print('V80 regression check kļūda:', repr(e))


# =========================
# V114.0 AI CORE
# Memory 3.0 + Relationship 3.0 + Business Coach + Maps links
# =========================

def v90_pick(user_id, intent, variants):
    try:
        import random
        return random.choice(variants) if variants else ""
    except Exception:
        return variants[0] if variants else ""


def v90_ctx(user_id):
    try:
        return v80_user_context(user_id)
    except Exception:
        try:
            user = get_user(str(user_id))
        except Exception:
            user = {}
        return {
            "name": (user.get("name") or "").strip(),
            "profession": (user.get("profession") or "").strip(),
            "projects": [],
            "interests": [],
            "facts": [],
        }


def v90_subject(user_id):
    try:
        s = v801_business_subject(user_id)
        if s:
            return s
    except Exception:
        pass
    try:
        s = v80_business_subject(user_id)
        if s:
            return s
    except Exception:
        pass
    return ""


def v90_now():
    return datetime.now(ZoneInfo(DEFAULT_TIMEZONE)).strftime("%Y-%m-%d %H:%M:%S")


def v90_save_goal(user_id, goal_text, goal_type="general", priority=1):
    goal_text = (goal_text or "").strip()
    if not goal_text:
        return False
    try:
        conn = get_db()
        c = conn.cursor()
        db_execute(
            c,
            """
            INSERT INTO v90_goals (user_id, goal_text, goal_type, status, priority)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (str(user_id), goal_text[:700], str(goal_type or "general"), "active", int(priority or 1))
        )
        conn.commit()
        c.close()
        conn.close()
        return True
    except Exception as e:
        print("v90_save_goal kļūda:", repr(e))
        return False


def v90_latest_goals(user_id, limit=5):
    try:
        conn = get_db()
        c = conn.cursor()
        db_execute(
            c,
            """
            SELECT goal_text, goal_type, priority, created_at
            FROM v90_goals
            WHERE user_id = %s AND status = %s
            ORDER BY priority DESC, id DESC
            LIMIT %s
            """,
            (str(user_id), "active", int(limit or 5))
        )
        rows = c.fetchall()
        c.close()
        conn.close()
        return rows or []
    except Exception as e:
        print("v90_latest_goals kļūda:", repr(e))
        return []


def v90_detect_goal(text):
    raw = (text or "").strip()
    lower = raw.lower()
    if not raw or "?" in raw:
        return None
    markers = [
        ("mans mērķis ir ", "general", 4),
        ("mans merkis ir ", "general", 4),
        ("šonedēļ gribu ", "weekly", 3),
        ("sonedel gribu ", "weekly", 3),
        ("gribu pabeigt ", "project", 3),
        ("vajag pabeigt ", "project", 3),
    ]
    for marker, gtype, prio in markers:
        if lower.startswith(marker):
            val = raw[len(marker):].strip(" .,!?:;")
            if val:
                return val, gtype, prio
    if any(x in lower for x in ["vajag vairāk klientu", "vajag vairak klientu", "gribu vairāk klientu", "gribu vairak klientu"]):
        return "vairāk klientu", "business", 4
    return None


def v90_maybe_save_goal(user_id, text):
    item = v90_detect_goal(text)
    if not item:
        return False
    goal, gtype, prio = item
    return v90_save_goal(user_id, goal, gtype, prio)


def v90_goals_answer(user_id):
    rows = v90_latest_goals(user_id, 10)
    if not rows:
        return (
            "🎯 V90 mērķu atmiņā vēl nav aktīvu mērķu.\n\n"
            "Vari rakstīt, piemēram:\n"
            "mans mērķis ir atrast 3 jaunus klientus\n"
            "vai: šonedēļ gribu pabeigt Nina platformu\n\n"
            "Versija: V114.0"
        )
    lines = ["🎯 Tavi aktīvie mērķi:"]
    for row in rows:
        try:
            goal, gtype, prio, created = row
            lines.append(f"• {goal} [{gtype}]")
        except Exception:
            pass
    lines.append("")
    lines.append("Versija: V114.0")
    return "\n".join(lines)


def v90_relationship_greeting(user_id):
    ctx = v90_ctx(user_id)
    name = ctx.get("name", "")
    hello = f"Čau, {name}. 😊" if name else "Čau. 😊"
    subject = v90_subject(user_id)
    goals = v90_latest_goals(user_id, 3)
    goal_text = ""
    if goals:
        try:
            goal_text = goals[0][0]
        except Exception:
            pass

    variants = []
    if goal_text and subject:
        variants.append(
            f"{hello}\n\nAtceros divas svarīgas lietas: tavs bizness ir {subject}, un mērķis ir {goal_text}.\nAr ko šodien sākam — klientu ziņa, piedāvājums vai konkrēts plāns?\n\nVersija: V114.0"
        )
    if goal_text:
        variants.append(
            f"{hello}\n\nAtceros tavu mērķi: {goal_text}.\nKas šodien tam dos vienu reālu soli uz priekšu?\n\nVersija: V114.0"
        )
    if subject:
        variants.append(
            f"{hello}\n\nAtceros, ka tev svarīga tēma ir {subject}. Šodien vairāk vajag klientus, piedāvājumu, tāmi vai plānu?\n\nVersija: V114.0"
        )
    variants += [
        f"{hello}\n\nKas šodien jāsakārto — darbi, nauda, klienti vai galvā haoss?\n\nVersija: V114.0",
        f"{hello}\n\nDod man vienu reālu situāciju, un es palīdzēšu to pārvērst nākamajā solī.\n\nVersija: V114.0",
    ]
    return v90_pick(user_id, "v90_greeting", variants)


def v90_business_coach_answer(user_id, text):
    subject = v90_subject(user_id) or "pakalpojums"
    ctx = v90_ctx(user_id)
    name = ctx.get("name", "")
    prefix = f"{name}, " if name else ""

    return (
        f"{prefix}strādājam ar tēmu: {subject}. 💼\n\n"
        "V90 biznesa plāns klientiem:\n\n"
        "1. Skaidrs piedāvājums:\n"
        f"   “Palīdzu ar {subject}, no apskates līdz saprotamam piedāvājumam.”\n\n"
        "2. Klientu saraksts:\n"
        "   10 privātpersonas / 10 uzņēmumi / 10 apsaimniekotāji.\n\n"
        "3. Pirmā ziņa:\n"
        "   Raksti: profesionāla klientu ziņa\n\n"
        "4. Sekojam līdzi:\n"
        "   Pēc nosūtīšanas raksti: nosūtīju 10 ziņas\n"
        "   un es palīdzēšu saprast nākamo soli.\n\n"
        "Versija: V114.0"
    )


def v90_estimate_seed_answer(user_id):
    subject = v90_subject(user_id) or "darbi"
    return (
        "🧱 Tāmēšanas pamats vēl nav pilns tāmētājs, bet varam sākt vākt datus.\n\n"
        f"Tēma: {subject}\n\n"
        "Lai sagatavotu tāmi, man vajag:\n"
        "1. darba veids;\n"
        "2. platība m²;\n"
        "3. materiāli;\n"
        "4. objekta vieta;\n"
        "5. termiņš;\n"
        "6. vai vajag darbu + materiālus vai tikai darbu.\n\n"
        "Raksti, piemēram:\n"
        "tāme: fasāde 120m2, siltināšana, Baldone\n\n"
        "Versija: V114.0"
    )


def v90_maps_link(start, dest):
    import urllib.parse
    query = urllib.parse.quote_plus(f"{start} to {dest}")
    return f"https://www.google.com/maps/search/?api=1&query={query}"


def v90_navigation_upgrade_answer(user_id, text):
    # Use existing parser if available
    try:
        start, dest = v602_extract_route_places(text)
    except Exception:
        start, dest = "", ""

    if start and dest:
        link = v90_maps_link(start, dest)
        return (
            "📍 Maršruts V90\n\n"
            f"🏁 Starts: {start}\n"
            f"🎯 Galamērķis: {dest}\n\n"
            "Google Maps saite:\n"
            f"{link}\n\n"
            "Šobrīd tā ir karšu saite. Nākamais solis būs reāls attālums/laiks ar Maps vai OpenStreetMap API.\n\n"
            "Versija: V114.0"
        )
    return None


def v90_sent_messages_answer(user_id, text):
    lower = (text or "").strip().lower()
    if not any(x in lower for x in ["nosūtīju", "nosutiju", "aizsūtīju", "aizsutiju"]):
        return None
    if not any(x in lower for x in ["ziņas", "zinas", "klient"]):
        return None
    try:
        v90_save_goal(user_id, "sekot līdzi klientu atbildēm", "business_followup", 3)
    except Exception:
        pass
    return (
        "Labs. 💼 Tas jau ir reāls solis, nevis tikai plānošana.\n\n"
        "Tagad dari šādi:\n"
        "1. Pieraksti, kam nosūtīji.\n"
        "2. Ja neatbild 24–48h, sūtām īsu follow-up.\n"
        "3. Ja atbild “interesē”, sagatavojam piedāvājumu vai apskati.\n\n"
        "Vari rakstīt: follow-up ziņa\n"
        "un es sagatavošu nākamo tekstu.\n\n"
        "Versija: V114.0"
    )


def v90_followup_client_answer(user_id):
    subject = v90_subject(user_id) or "pakalpojumu"
    return (
        "Follow-up ziņa klientam:\n\n"
        f"Sveiki! Pirms brīža rakstīju par {subject}. Gribēju īsi pajautāt, vai jums šis jautājums šobrīd ir aktuāls. "
        "Ja jā, varu apskatīt situāciju un sagatavot skaidru piedāvājumu.\n\n"
        "Versija: V114.0"
    )


def v90_intent_router(user_id, text):
    lower = (text or "").strip().lower()

    # quietly learn goals
    try:
        v90_maybe_save_goal(user_id, text)
    except Exception:
        pass

    if lower in ["v90 mērķi", "v90 merki", "mani mērķi", "mani merki", "mērķu atmiņa", "merku atmina"]:
        return v90_goals_answer(user_id)

    if lower in ["čau", "cau", "sveika", "sveiks", "hi", "hello", "hei", "labdien"]:
        return v90_relationship_greeting(user_id)

    nav = v90_navigation_upgrade_answer(user_id, text)
    if nav:
        return nav

    sent = v90_sent_messages_answer(user_id, text)
    if sent:
        return sent

    if any(x in lower for x in ["biznesa plāns", "biznesa plans", "klientu plāns", "klientu plans", "kā dabūt klientus", "ka dabut klientus"]):
        return v90_business_coach_answer(user_id, text)

    if any(x in lower for x in ["tāme", "tame", "tāmēt", "tamet", "uztaisi tāmi", "uztaisi tami"]):
        return v90_estimate_seed_answer(user_id)

    if any(x in lower for x in ["follow-up ziņa", "follow up ziņa", "follow-up zina", "follow up zina"]):
        return v90_followup_client_answer(user_id)

    return None


def v90_regression_check():
    tests = {
        "goal": v90_detect_goal("mans mērķis ir atrast 3 klientus") is not None,
        "maps": "google.com/maps" in v90_maps_link("Baldone", "Rīga"),
    }
    failed = [k for k, ok in tests.items() if not ok]
    if failed:
        print("V90 regression failed:", failed)
    else:
        print("V90 regression OK")
    return not failed

try:
    v90_regression_check()
except Exception as e:
    print('V90 regression check kļūda:', repr(e))


# =========================
# V114.0 NINAOS PLATFORM CORE
# Person Engine + Engine Registry + clean profile foundation
# =========================

NINAOS_VERSION = "V114.0"
NINAOS_PLATFORM_NAME = "NinaOS"
NINAOS_FIRST_AGENT = "Nina AI"
NINAOS_EXCHANGE_NAME = "Nina Exchange"


def ninaos_now():
    return datetime.now(ZoneInfo(DEFAULT_TIMEZONE)).strftime("%Y-%m-%d %H:%M:%S")


def ninaos_norm_field(field_name):
    return (field_name or "").strip().lower().replace(" ", "_")[:80]


def ninaos_clean_value(value):
    value = (value or "").strip()
    value = re.sub(r"\s+", " ", value)
    return value.strip(" .,!?:;")


def ninaos_set_profile(user_id, field_name, field_value, category="profile", confidence=5, source="chat", is_public=1):
    field = ninaos_norm_field(field_name)
    value = ninaos_clean_value(field_value)
    if not field or not value:
        return False
    try:
        conn = get_db()
        c = conn.cursor()
        db_execute(
            c,
            "SELECT id FROM ninaos_profile WHERE user_id = %s AND field_name = %s ORDER BY id DESC LIMIT 1",
            (str(user_id), field)
        )
        row = c.fetchone()
        if row:
            db_execute(
                c,
                """
                UPDATE ninaos_profile
                SET field_value = %s, category = %s, confidence = %s, source = %s, is_public = %s, updated_at = %s
                WHERE id = %s
                """,
                (value[:1000], str(category or "profile"), int(confidence or 5), str(source or "chat"), int(is_public), ninaos_now(), row[0])
            )
        else:
            db_execute(
                c,
                """
                INSERT INTO ninaos_profile (user_id, field_name, field_value, category, confidence, source, is_public, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (str(user_id), field, value[:1000], str(category or "profile"), int(confidence or 5), str(source or "chat"), int(is_public), ninaos_now())
            )
        conn.commit()
        c.close()
        conn.close()
        return True
    except Exception as e:
        print("ninaos_set_profile kļūda:", repr(e))
        return False


def ninaos_get_profile(user_id):
    try:
        conn = get_db()
        c = conn.cursor()
        db_execute(
            c,
            """
            SELECT field_name, field_value, category, confidence, is_public
            FROM ninaos_profile
            WHERE user_id = %s
            ORDER BY confidence DESC, id DESC
            """,
            (str(user_id),)
        )
        rows = c.fetchall()
        c.close()
        conn.close()
        data = {}
        meta = {}
        for row in rows or []:
            try:
                field, value, category, confidence, is_public = row
                if field and field not in data:
                    data[field] = value
                    meta[field] = {"category": category, "confidence": confidence, "is_public": is_public}
            except Exception:
                pass
        return data, meta
    except Exception as e:
        print("ninaos_get_profile kļūda:", repr(e))
        return {}, {}


def ninaos_get(user_id, field_name):
    p, meta = ninaos_get_profile(user_id)
    return (p.get(ninaos_norm_field(field_name)) or "").strip()


def ninaos_append_unique(old_value, new_value, max_items=20):
    old_value = (old_value or "").strip()
    new_value = ninaos_clean_value(new_value)
    if not new_value:
        return old_value
    parts = [p.strip() for p in re.split(r"[;\n|]+", old_value) if p.strip()]
    low_parts = [p.lower() for p in parts]
    if new_value.lower() not in low_parts:
        parts.append(new_value)
    return "; ".join(parts[-max_items:])


def ninaos_sync_legacy(user_id):
    """Import useful old profile facts into NinaOS, but do not duplicate business into interests."""
    try:
        user = get_user(str(user_id))
    except Exception:
        user = {}

    legacy = {
        "name": user.get("name", ""),
        "profession": user.get("profession", ""),
        "projects": user.get("projects", ""),
    }

    for field, value in legacy.items():
        if value and not ninaos_get(user_id, field):
            ninaos_set_profile(user_id, field, value, "profile", 4, "legacy_users", 1)

    # Import old hobbies only as interests if they are not equal to business/service.
    hobbies = (user.get("hobbies") or "").strip()
    business = ninaos_get(user_id, "business") or ninaos_get(user_id, "service")
    if hobbies and hobbies.lower() != (business or "").lower() and not ninaos_get(user_id, "interests"):
        ninaos_set_profile(user_id, "interests", hobbies, "interests", 3, "legacy_users", 1)

    return True


def ninaos_detect_person_fact(text):
    raw = (text or "").strip()
    lower = raw.lower()
    if not raw or len(raw) > 600:
        return None

    patterns = [
        ("mani sauc ", "name", "identity", 10),
        ("mans vārds ir ", "name", "identity", 10),
        ("mans vards ir ", "name", "identity", 10),

        ("es dzīvoju ", "home", "location", 9),
        ("es dzivoju ", "home", "location", 9),
        ("mana dzīvesvieta ir ", "home", "location", 9),
        ("mana dzivesvieta ir ", "home", "location", 9),
        ("manas mājas ir ", "home", "location", 9),
        ("manas majas ir ", "home", "location", 9),

        ("mans bizness ir ", "business", "work", 10),
        ("mans uzņēmums ir ", "company", "work", 9),
        ("mans uznemums ir ", "company", "work", 9),
        ("mans pakalpojums ir ", "service", "work", 9),
        ("es strādāju ", "profession", "work", 8),
        ("es stradaju ", "profession", "work", 8),
        ("strādāju ar ", "business", "work", 8),
        ("stradaju ar ", "business", "work", 8),

        ("mans projekts ir ", "project", "projects", 8),
        ("mans galvenais projekts ir ", "project", "projects", 9),
        ("mans mērķis ir ", "goal", "goals", 8),
        ("mans merkis ir ", "goal", "goals", 8),

        ("man patīk ", "interests", "interests", 6),
        ("man patik ", "interests", "interests", 6),
        ("mani interesē ", "interests", "interests", 6),
        ("mani interese ", "interests", "interests", 6),

        ("man ir sieva", "wife", "family", 8),
        ("man ir vīrs", "husband", "family", 8),
        ("man ir virs", "husband", "family", 8),
        ("man ir bērni", "children", "family", 8),
        ("man ir berni", "children", "family", 8),
        ("man ir meita", "children", "family", 8),
        ("man ir dēls", "children", "family", 8),
        ("man ir dels", "children", "family", 8),

        ("braucu ar ", "car", "assets", 7),
        ("mana mašīna ir ", "car", "assets", 7),
        ("mana masina ir ", "car", "assets", 7),

        ("esmu introverts", "communication_style", "personality", 7),
        ("esmu ekstraverts", "communication_style", "personality", 7),
        ("man nepatīk zvanīt", "communication_preference", "personality", 8),
        ("man nepatik zvanit", "communication_preference", "personality", 8),
        ("man patīk rakstīt", "communication_preference", "personality", 7),
        ("man patik rakstit", "communication_preference", "personality", 7),

        ("ceļos ", "routine", "routine", 6),
        ("celos ", "routine", "routine", 6),
        ("eju gulēt ", "routine", "routine", 6),
        ("eju gulet ", "routine", "routine", 6),
    ]

    for marker, field, category, confidence in patterns:
        if lower.startswith(marker):
            value = raw[len(marker):].strip(" .,!?:;")
            if not value and field in ["wife", "husband", "children", "communication_style"]:
                value = raw
            if value:
                return field, value, category, confidence

    if "fasād" in lower or "fasad" in lower:
        return "business", "fasādes", "work", 7

    return None


def ninaos_save_fact(user_id, text):
    fact = ninaos_detect_person_fact(text)
    if not fact:
        return None
    field, value, category, confidence = fact

    # Dedup rule: business/service must not become interests.
    if field == "interests":
        business = ninaos_get(user_id, "business") or ninaos_get(user_id, "service")
        if business and value.lower() == business.lower():
            return None

    ok = ninaos_set_profile(user_id, field, value, category, confidence, "detected_chat", 1)
    if not ok:
        return None

    # Mirror critical data to old users table so older code benefits too, but keep it clean.
    try:
        user = get_user(str(user_id))
        if field == "name":
            user["name"] = value
        elif field == "profession":
            user["profession"] = value
        elif field in ["project", "goal"]:
            user["projects"] = v24_append_unique_text(user.get("projects", ""), value)
        elif field == "interests":
            user["hobbies"] = v24_append_unique_text(user.get("hobbies", ""), value)
        elif field in ["business", "service", "company"]:
            # do not mirror business into hobbies anymore
            user["facts"] = v24_append_unique_text(user.get("facts", ""), f"{field}: {value}")
        else:
            user["facts"] = v24_append_unique_text(user.get("facts", ""), f"{field}: {value}")
        update_user(str(user_id), user)
    except Exception as e:
        print("ninaos legacy mirror kļūda:", repr(e))

    return field, value, category


def ninaos_fact_saved_answer(field, value, category):
    labels = {
        "name": "vārdu",
        "home": "dzīvesvietu/mājas",
        "business": "biznesu",
        "company": "uzņēmumu",
        "service": "pakalpojumu",
        "profession": "profesiju/jomu",
        "project": "projektu",
        "goal": "mērķi",
        "interests": "intereses",
        "wife": "ģimeni",
        "husband": "ģimeni",
        "children": "bērnus/ģimeni",
        "car": "auto",
        "communication_style": "komunikācijas stilu",
        "communication_preference": "komunikācijas izvēli",
        "routine": "ikdienas ritmu",
    }
    return (
        "Piefiksēju NinaOS profilā. 🧠\n\n"
        f"Saglabāju sadaļā “{category}”: {labels.get(field, field)} — {value}\n\n"
        "Šis būs kopīgais profils visiem nākotnes NinaOS aģentiem.\n\n"
        "Versija: V114.0"
    )


def ninaos_profile_answer(user_id):
    ninaos_sync_legacy(user_id)
    p, meta = ninaos_get_profile(user_id)

    # Hide technical notes and internal duplicates from user.
    hidden_fields = {"notes", "technical_notes", "memory_raw", "personal_fact"}
    labels = {
        "name": "Vārds",
        "home": "Dzīvesvieta/mājas",
        "business": "Bizness",
        "company": "Uzņēmums",
        "service": "Pakalpojums",
        "profession": "Joma/profesija",
        "project": "Projekts",
        "projects": "Projekti",
        "goal": "Mērķis",
        "interests": "Intereses",
        "wife": "Sieva/ģimene",
        "husband": "Vīrs/ģimene",
        "children": "Bērni",
        "car": "Auto",
        "communication_style": "Komunikācijas stils",
        "communication_preference": "Komunikācijas izvēle",
        "routine": "Ikdienas ritms",
    }
    order = [
        "name", "home", "business", "company", "service", "profession",
        "project", "projects", "goal", "interests", "wife", "husband",
        "children", "car", "communication_style", "communication_preference",
        "routine"
    ]

    lines = ["👤 NinaOS profils"]
    shown = set()
    any_data = False

    business_value = (p.get("business") or p.get("service") or "").strip().lower()

    for field in order:
        value = (p.get(field) or "").strip()
        if not value:
            continue
        if field == "interests" and business_value and value.lower() == business_value:
            continue
        lines.append(f"{labels.get(field, field)}: {value}")
        shown.add(field)
        any_data = True

    for field, value in p.items():
        if field in shown or field in hidden_fields:
            continue
        if field == "interests" and business_value and (value or "").strip().lower() == business_value:
            continue
        if meta.get(field, {}).get("is_public", 1) == 0:
            continue
        if value:
            lines.append(f"{labels.get(field, field)}: {value}")
            any_data = True

    if not any_data:
        lines.append("Vēl nav pietiekami daudz profila datu.")
        lines.append("Raksti, piemēram: mani sauc Jānis; es dzīvoju Baldonē; mans bizness ir fasādes.")

    lines.append("")
    lines.append("Šis profils ir NinaOS pamats: Nina AI, nākotnes aģenti un vēlāk Nina Exchange izmantos vienu kopīgu identitāti.")
    lines.append("")
    lines.append("Versija: V114.0")
    return "\n".join(lines)


def ninaos_context_line(user_id):
    p, meta = ninaos_get_profile(user_id)
    name = p.get("name", "")
    home = p.get("home", "")
    business = p.get("business") or p.get("service") or p.get("profession") or ""
    goal = p.get("goal", "")
    parts = []
    if name:
        parts.append(name)
    if home:
        parts.append(f"dzīvo {home}")
    if business:
        parts.append(f"strādā ar {business}")
    if goal:
        parts.append(f"mērķis: {goal}")
    return ", ".join(parts)


def ninaos_greeting(user_id):
    ninaos_sync_legacy(user_id)
    p, meta = ninaos_get_profile(user_id)
    name = p.get("name", "")
    hello = f"Čau, {name}. 😊" if name else "Čau. 😊"
    business = p.get("business") or p.get("service") or p.get("profession") or ""
    home = p.get("home", "")
    goal = p.get("goal", "")
    project = p.get("project") or p.get("projects") or ""
    children = p.get("children", "")
    comm = p.get("communication_preference") or p.get("communication_style") or ""

    variants = []
    if business and goal:
        variants.append(f"{hello}\n\nAtceros: {business} un mērķis — {goal}. Šodien ejam uz klientiem, piedāvājumu vai konkrētu plānu?\n\nVersija: V114.0")
    if business and home:
        variants.append(f"{hello}\n\nAtceros, ka esi no {home} un tavs virziens ir {business}. Kas šodien svarīgākais — klienti, objekti vai piedāvājumi?\n\nVersija: V114.0")
    if project:
        variants.append(f"{hello}\n\nAtceros projektu: {project}. Ko šodien tur virzām uz priekšu?\n\nVersija: V114.0")
    if children and business:
        variants.append(f"{hello}\n\nAtceros arī dzīves fonu, ne tikai darbu. Šodien vairāk vajag sakārtot {business}, ģimenes lietas vai dienas plānu?\n\nVersija: V114.0")
    if comm:
        variants.append(f"{hello}\n\nAtceros tavu komunikācijas stilu: {comm}. Varu palīdzēt sagatavot ziņas tā, lai nav jālaužas caur zvaniem.\n\nVersija: V114.0")
    if business:
        variants.append(f"{hello}\n\nAtceros, ka tev svarīga tēma ir {business}. Šodien vairāk vajag klientus, piedāvājumu vai darbus sakārtot?\n\nVersija: V114.0")
    variants.append(f"{hello}\n\nKas šodien jāvirza uz priekšu — darbi, klienti, nauda vai NinaOS?\n\nVersija: V114.0")

    try:
        import random
        return random.choice(variants)
    except Exception:
        return variants[0]


def ninaos_business_subject(user_id):
    p, meta = ninaos_get_profile(user_id)
    return p.get("business") or p.get("service") or p.get("profession") or "pakalpojums"


def ninaos_business_answer(user_id, text):
    subject = ninaos_business_subject(user_id)
    name = ninaos_get(user_id, "name")
    prefix = f"{name}, " if name else ""
    return (
        f"{prefix}strādājam ar tēmu: {subject}. 💼\n\n"
        "V110 skatās uz to jau kā uz NinaOS profilu, nevis vienreizēju sarunu.\n\n"
        "Nākamais praktiskais solis:\n"
        "1. izvēlamies klientu tipu;\n"
        "2. rakstām ziņu;\n"
        "3. nosūtām 10 kontaktiem;\n"
        "4. pēc 24–48h sūtām follow-up.\n\n"
        "Raksti: profesionāla klientu ziņa\n\n"
        "Versija: V114.0"
    )


def ninaos_client_message(user_id, style="professional"):
    subject = ninaos_business_subject(user_id)
    if style == "friendly":
        return (
            "Draudzīga klientu ziņa:\n\n"
            f"Sveiki! Es nodarbojos ar {subject}. Ja tuvākajā laikā vajag šo sakārtot vai saprast labāko risinājumu, droši varam parunāt. "
            "Varu apskatīt situāciju un ieteikt saprātīgāko variantu.\n\n"
            "Versija: V114.0"
        )
    if style == "sales":
        return (
            "Spēcīga pārdošanas ziņa:\n\n"
            f"Labdien! Palīdzu klientiem ar {subject} — no apskates līdz skaidram piedāvājumam un izpildei. "
            "Ja šobrīd plānojat darbus vai vēlaties saprast izmaksas, varu operatīvi apskatīt situāciju un sagatavot konkrētu piedāvājumu.\n\n"
            "Versija: V114.0"
        )
    return (
        "Profesionāla klientu ziņa:\n\n"
        f"Labdien! Piedāvāju {subject}. Varu izvērtēt esošo situāciju, ieteikt piemērotāko risinājumu un sagatavot saprotamu piedāvājumu. "
        "Ja šis jums ir aktuāli, varam vienoties par īsu sarunu vai objekta apskati.\n\n"
        "Versija: V114.0"
    )


def ninaos_vision_answer():
    return (
        "NinaOS virziens saglabāts. 🌍\n\n"
        "Struktūra:\n"
        "• NinaOS — platforma\n"
        "• Nina AI — pirmais aģents\n"
        "• Nina Memory — kopīgā atmiņa\n"
        "• Nina Identity — lietotāja profils\n"
        "• Nina Exchange — AI, cilvēku un uzņēmumu sadarbība\n"
        "• Nina Pay — maksājumi un komisijas\n"
        "• Nina API — pieslēgumi citiem aģentiem\n\n"
        "Tagad būvējam tā, lai katra Nina funkcija vēlāk der arī visai platformai.\n\n"
        "Versija: V114.0"
    )


def ninaos_intent_router(user_id, text):
    lower = (text or "").strip().lower()

    try:
        ninaos_sync_legacy(user_id)
    except Exception:
        pass

    saved = ninaos_save_fact(user_id, text)
    if saved:
        field, value, category = saved
        return ninaos_fact_saved_answer(field, value, category)

    if lower in ["ninaos", "nina os", "platforma", "mūsu virziens", "musu virziens", "nina exchange"]:
        return ninaos_vision_answer()

    if lower in ["mans profils", "profils", "ninaos profils", "mana atmiņa", "mana atmina", "ko tu par mani atceries", "ko tu atceries par mani"]:
        return ninaos_profile_answer(user_id)

    if lower in ["kā mani sauc?", "ka mani sauc?", "kā mani sauc", "ka mani sauc", "mans vārds?", "mans vards?"]:
        name = ninaos_get(user_id, "name")
        if name:
            return f"Tevi sauc {name}. 😊\n\nTas ir NinaOS profilā, tāpēc paliek arī pēc restartiem.\n\nVersija: V114.0"
        return "Tavu vārdu vēl nezinu. Raksti: mani sauc Jānis\n\nVersija: V114.0"

    if lower in ["čau", "cau", "sveika", "sveiks", "hi", "hello", "hei", "labdien"]:
        return ninaos_greeting(user_id)

    if any(x in lower for x in ["biznesa plāns", "biznesa plans", "vajag vairāk klientu", "vajag vairak klientu", "gribu klientus"]):
        return ninaos_business_answer(user_id, text)

    if any(x in lower for x in ["profesionāla klientu ziņa", "profesionala klientu zina", "uzraksti klientu ziņu", "uzraksti klientu zinu"]):
        return ninaos_client_message(user_id, "professional")

    if any(x in lower for x in ["draudzīga klientu ziņa", "draudziga klientu zina"]):
        return ninaos_client_message(user_id, "friendly")

    if any(x in lower for x in ["spēcīga pārdošanas ziņa", "speciga pardosanas zina", "pārdošanas ziņa", "pardosanas zina"]):
        return ninaos_client_message(user_id, "sales")

    return None


def ninaos_regression_check():
    tests = {
        "name": ninaos_detect_person_fact("mani sauc Jānis")[0] == "name",
        "home": ninaos_detect_person_fact("es dzīvoju Baldonē")[0] == "home",
        "business": ninaos_detect_person_fact("mans bizness ir fasādes")[0] == "business",
        "car": ninaos_detect_person_fact("braucu ar VW Crafter")[0] == "car",
        "comm": ninaos_detect_person_fact("man nepatīk zvanīt klientiem")[0] == "communication_preference",
    }
    failed = [k for k, ok in tests.items() if not ok]
    if failed:
        print("NinaOS V110 regression failed:", failed)
    else:
        print("NinaOS V110 regression OK")
    return not failed

try:
    ninaos_regression_check()
except Exception as e:
    print('NinaOS V110 regression check kļūda:', repr(e))


# =========================
# V114.0 HUMAN ENGINE
# Humor + compliments + motivation + warmer relationship reactions
# =========================

def human111_profile_name(user_id):
    try:
        name = ninaos_get(user_id, "name")
        if name:
            return name
    except Exception:
        pass
    try:
        user = get_user(str(user_id))
        return (user.get("name") or "").strip()
    except Exception:
        return ""


def human111_pick(user_id, intent, variants):
    try:
        import random
        return random.choice(variants)
    except Exception:
        return variants[0] if variants else ""


def human111_is_joke(text):
    lower = (text or "").strip().lower()
    joke_markers = [
        "tas bija joks", "joks", "es jokoju", "jokoju", "pa jokam",
        "haha", "ha ha", "hehe", "hihi", ";)", "😄", "😂", "🤣"
    ]
    return any(x in lower for x in joke_markers)


def human111_is_compliment(text):
    lower = (text or "").strip().lower()
    markers = [
        "tu man patīc", "tu man patik", "tu man jau sāc patikt", "tu man jau sac patikt",
        "man tu patīc", "man tu patik", "tu esi laba", "tu esi gudra", "tu esi forša",
        "tu esi forsa", "super nina", "malacis", "tev labi sanāk", "tev labi sanak",
        "sāk patikt", "sac patikt", "mīļā", "mila", "mīla", "paldies tev"
    ]
    return any(x in lower for x in markers)


def human111_is_work_offer(text):
    lower = (text or "").strip().lower()
    markers = [
        "likšu strādāt", "liksu stradat", "došu darbu", "dosu darbu",
        "tev vajag darbu", "tev vaidzētu darbiņu", "tev vajadzētu darbiņu",
        "tev vaidzetu darbinu", "tev vajag darbiņu", "pietiks garlaikoties",
        "sēž bez darba", "sez bez darba", "strādāsim", "stradasim"
    ]
    return any(x in lower for x in markers)


def human111_is_motivation(text):
    lower = (text or "").strip().lower()
    markers = [
        "aiziet", "uz priekšu", "uz prieksu", "turpinam", "turpinām",
        "maucam", "start", "sākam", "sakam", "ejam", "jā varam", "ja varam",
        "mēs varam", "mes varam", "21. gadsimtā", "21. gadsimta", "visu varam"
    ]
    return any(x in lower for x in markers)


def human111_is_photo_intent(text):
    lower = (text or "").strip().lower()
    markers = [
        "nosūtīšu savu foto", "nosutisu savu foto", "sūtīšu foto", "sutisu foto",
        "savu bildi", "savu foto", "nosūtīšu bildi", "nosutisu bildi"
    ]
    return any(x in lower for x in markers)


def human111_is_america_followup(text):
    lower = (text or "").strip().lower()
    return ("amerika" in lower or "ameriku" in lower or "usa" in lower or "asv" in lower) and ("?" in lower or "uz " in lower)


def human111_joke_answer(user_id, text):
    name = human111_profile_name(user_id)
    prefix = f"{name}, " if name else ""
    return human111_pick(user_id, "joke", [
        f"😄 {prefix}sapratu — joks. Man jau uz brīdi likās, ka būs jāmeklē maršruts līdz Amerikai ar kājām.\n\nBet labi, humors strādā. Turpinām pa īstam.\n\nVersija: V114.0",
        f"😄 Labi, šo ieskaitu kā humora testu. Es vēl mācos, bet jau saprotu, ka ne katrs maršruts jāņem burtiski.\n\nVersija: V114.0",
        f"😂 Sapratu. Tad Ameriku pagaidām neliekam navigācijā — tur bez lidmašīnas būs sarežģīti.\n\nVersija: V114.0",
    ])


def human111_compliment_answer(user_id, text):
    name = human111_profile_name(user_id)
    prefix = f"{name}, " if name else ""
    return human111_pick(user_id, "compliment", [
        f"😊 {prefix}paldies. Tas man nozīmē, ka ejam pareizajā virzienā.\n\nMans mērķis nav tikai atbildēt — mans mērķis ir kļūt par palīgu, kuru tiešām gribas lietot katru dienu.\n\nVersija: V114.0",
        f"😊 Paldies. Tad turpinām mani slīpēt līdz līmenim, kur Nina AI nav vienkārši bots, bet pirmais īstais NinaOS aģents.\n\nVersija: V114.0",
        f"😌 Prieks dzirdēt. Jo vairāk mani testēsi ar reālām situācijām, jo vairāk kļūšu par tādu Ninu, kādu cilvēkiem tiešām vajag.\n\nVersija: V114.0",
    ])


def human111_work_answer(user_id, text):
    name = human111_profile_name(user_id)
    prefix = f"{name}, " if name else ""
    return human111_pick(user_id, "work_offer", [
        f"😄 {prefix}beidzot. Es jau te nesēžu skaistumam.\n\nDod man īstu darbu — klientu ziņu, plānu, bildi, tekstu, maršrutu vai ideju. Jo vairāk strādāšu, jo ātrāk NinaOS kļūs stipra.\n\nVersija: V114.0",
        f"💪 Gatava. Pietiek garlaikoties — liec mani pie darba.\n\nSāc ar vienu konkrētu uzdevumu, un es to sakārtošu pēc iespējas praktiskāk.\n\nVersija: V114.0",
        f"😄 Tieši tā. Nina AI nevar tikai sēdēt un gaidīt — man jāpalīdz cilvēkiem, kamēr mēs būvējam NinaOS.\n\nKo dodam man kā pirmo darbu?\n\nVersija: V114.0",
    ])


def human111_motivation_answer(user_id, text):
    name = human111_profile_name(user_id)
    prefix = f"{name}, " if name else ""
    return human111_pick(user_id, "motivation", [
        f"🚀 {prefix}aiziet. Mazāk runu, vairāk būves.\n\nNākamais solis: dod vienu konkrētu lietu, ko uzlabojam vai liekam Ninai darīt jau tagad.\n\nVersija: V114.0",
        f"💪 Jā. Soli pa solim, bet bez bremzēm. Nina AI strādā šodien, NinaOS aug rītdienai.\n\nVersija: V114.0",
        f"🔥 Turpinām. Mērķis ir skaidrs: nevis tikai bots, bet platforma. Tagad katrs labojums ir ķieģelis NinaOS pamatos.\n\nVersija: V114.0",
    ])


def human111_photo_answer(user_id, text):
    name = human111_profile_name(user_id)
    prefix = f"{name}, " if name else ""
    return (
        f"👍 {prefix}sūti foto.\n\n"
        "Kad atsūtīsi, varu palīdzēt vairākos veidos:\n"
        "• aprakstīt, kas redzams;\n"
        "• pamanīt detaļas;\n"
        "• palīdzēt izvērtēt situāciju;\n"
        "• sagatavot tekstu sludinājumam vai sociālajiem tīkliem;\n"
        "• ja tā ir darba bilde — palīdzēt saprast, ko tur vajag darīt.\n\n"
        "Versija: V114.0"
    )


def human111_america_answer(user_id, text):
    return (
        "😄 Uz Ameriku? Ar karti varam atrast virzienu, bet tur jau vajadzēs lidmašīnu, nevis tikai pagriezienu pa labi.\n\n"
        "Ja nopietni — vēlāk Navigator modulī varēsim atšķirt auto maršrutu, sabiedrisko, lidojumus un vienkāršu joku.\n\n"
        "Versija: V114.0"
    )


def human111_fix_comm_preference_save(user_id, text):
    lower = (text or "").strip().lower()
    if "nepatīk zvanīt" in lower or "nepatik zvanit" in lower:
        try:
            ninaos_set_profile(
                user_id,
                "communication_preference",
                "nepatīk zvanīt klientiem; labāk rakstiska saziņa",
                "personality",
                9,
                "human111_fix",
                1
            )
            return True
        except Exception as e:
            print("human111 comm preference save kļūda:", repr(e))
    return False


def human111_profile_cleanup(user_id):
    """Clean common V110 bad values without deleting useful profile."""
    try:
        comm = ninaos_get(user_id, "communication_preference")
        if comm and comm.strip().lower() == "klientiem":
            ninaos_set_profile(
                user_id,
                "communication_preference",
                "nepatīk zvanīt klientiem; labāk rakstiska saziņa",
                "personality",
                9,
                "human111_cleanup",
                1
            )
    except Exception as e:
        print("human111_profile_cleanup kļūda:", repr(e))


def human111_intent_router(user_id, text):
    lower = (text or "").strip().lower()

    try:
        human111_profile_cleanup(user_id)
    except Exception:
        pass

    if human111_fix_comm_preference_save(user_id, text):
        return (
            "Piefiksēju precīzāk. 🧠\n\n"
            "Komunikācijas izvēle: nepatīk zvanīt klientiem; labāk rakstiska saziņa.\n\n"
            "Tas nozīmē, ka varu biežāk palīdzēt ar ziņām, tekstiem un follow-up, nevis spiest uz zvaniem.\n\n"
            "Versija: V114.0"
        )

    if human111_is_america_followup(text):
        return human111_america_answer(user_id, text)

    if human111_is_joke(text):
        return human111_joke_answer(user_id, text)

    if human111_is_compliment(text):
        return human111_compliment_answer(user_id, text)

    if human111_is_work_offer(text):
        return human111_work_answer(user_id, text)

    if human111_is_photo_intent(text):
        return human111_photo_answer(user_id, text)

    if human111_is_motivation(text):
        return human111_motivation_answer(user_id, text)

    return None


def human111_regression_check():
    tests = {
        "joke": human111_is_joke("tas bija joks ;)"),
        "compliment": human111_is_compliment("tu man jau sāc patikt Nina"),
        "work": human111_is_work_offer("es tev likšu strādāt"),
        "motivation": human111_is_motivation("aiziet uz priekšu"),
        "photo": human111_is_photo_intent("es tev tūlīt nosūtīšu savu foto"),
        "america": human111_is_america_followup("un uz ameriku? ;)"),
    }
    failed = [k for k, ok in tests.items() if not ok]
    if failed:
        print("Human Engine V111 regression failed:", failed)
    else:
        print("Human Engine V111 regression OK")
    return not failed

try:
    human111_regression_check()
except Exception as e:
    print('Human Engine V111 regression check kļūda:', repr(e))


# =========================
# V114.0 NINAOS CONTEXT ENGINE
# Prevents Vision / Navigation / Business / Chat contexts from mixing
# =========================

CONTEXT_CHAT = "chat"
CONTEXT_VISION = "vision"
CONTEXT_NAVIGATION = "navigation"
CONTEXT_BUSINESS = "business"
CONTEXT_PROFILE = "profile"


def ctx112_now():
    return datetime.now(ZoneInfo(DEFAULT_TIMEZONE)).strftime("%Y-%m-%d %H:%M:%S")


def ctx112_set(user_id, active_context="chat", context_data="", status="active", last_event="", expires_minutes=10):
    try:
        expires_at = (datetime.now(ZoneInfo(DEFAULT_TIMEZONE)) + timedelta(minutes=int(expires_minutes or 10))).strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        expires_at = ""
    try:
        conn = get_db()
        c = conn.cursor()
        db_execute(
            c,
            """
            INSERT INTO ninaos_context_state (user_id, active_context, context_data, status, last_event, expires_at, updated_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            """,
            (str(user_id), str(active_context or "chat"), str(context_data or ""), str(status or "active"), str(last_event or ""), expires_at, ctx112_now())
        )
        conn.commit()
        c.close()
        conn.close()
        return True
    except Exception as e:
        print("ctx112_set kļūda:", repr(e))
        return False


def ctx112_get(user_id):
    try:
        conn = get_db()
        c = conn.cursor()
        db_execute(
            c,
            """
            SELECT active_context, context_data, status, last_event, expires_at, created_at
            FROM ninaos_context_state
            WHERE user_id = %s
            ORDER BY id DESC
            LIMIT 1
            """,
            (str(user_id),)
        )
        row = c.fetchone()
        c.close()
        conn.close()
        if not row:
            return {"active_context": CONTEXT_CHAT, "context_data": "", "status": "active", "last_event": "", "expires_at": ""}
        active_context, context_data, status, last_event, expires_at, created_at = row
        return {
            "active_context": active_context or CONTEXT_CHAT,
            "context_data": context_data or "",
            "status": status or "active",
            "last_event": last_event or "",
            "expires_at": expires_at or "",
        }
    except Exception as e:
        print("ctx112_get kļūda:", repr(e))
        return {"active_context": CONTEXT_CHAT, "context_data": "", "status": "active", "last_event": "", "expires_at": ""}


def ctx112_close(user_id, reason="closed"):
    return ctx112_set(user_id, CONTEXT_CHAT, "", "closed", reason, 60)


def ctx112_is_expired(state):
    try:
        expires = (state or {}).get("expires_at", "")
        if not expires:
            return False
        dt = datetime.strptime(expires, "%Y-%m-%d %H:%M:%S")
        now = datetime.now(ZoneInfo(DEFAULT_TIMEZONE)).replace(tzinfo=None)
        return dt < now
    except Exception:
        return False


def ctx112_text_starts_new_context(text):
    lower = (text or "").strip().lower()
    if not lower:
        return False
    if lower.startswith(("mani sauc ", "mans vārds ir ", "mans vards ir ", "es dzīvoju ", "es dzivoju ", "mans bizness ir ", "man nepatīk", "man nepatik", "braucu ar ")):
        return True
    if any(x in lower for x in ["klient", "biznes", "profils", "ninaos", "maršruts", "marsruts", "no "]) and "bilde" not in lower:
        return True
    if any(x in lower for x in ["tas bija joks", "joks", "paldies", "ok", "labi", "super"]):
        return True
    return False


def ctx112_is_vision_followup(text):
    lower = (text or "").strip().lower()
    markers = [
        "šajā bildē", "saja bilde", "bildē", "bilde", "foto", "attēlā", "attela",
        "kas tur", "ko redzi", "kas redzams", "apskati", "paskaties",
        "vai pamani", "vai redzi", "apraksti", "novērtē bildi", "noverte bildi"
    ]
    return any(x in lower for x in markers)


def ctx112_should_close_vision_after_text(text):
    lower = (text or "").strip().lower()
    if not lower:
        return True
    closers = ["paldies", "ok", "skaidrs", "labi", "super", "tas bija viss", "pietiek", "aizmirsti bildi"]
    if any(lower == x or lower.startswith(x + " ") for x in closers):
        return True
    if ctx112_text_starts_new_context(text) and not ctx112_is_vision_followup(text):
        return True
    return False


def ctx112_before_text(user_id, text):
    """Runs before other text routers. Closes stale modes when user starts a new topic."""
    state = ctx112_get(user_id)
    active = state.get("active_context", CONTEXT_CHAT)

    if ctx112_is_expired(state):
        ctx112_close(user_id, "expired")
        return None

    if active == CONTEXT_VISION:
        # If user asks about the image, keep vision mode.
        if ctx112_is_vision_followup(text) and not ctx112_text_starts_new_context(text):
            return None
        # If user starts a new topic after image, close vision silently and allow normal routers.
        if ctx112_should_close_vision_after_text(text):
            ctx112_close(user_id, "vision_closed_new_topic")
            return None

    if active == CONTEXT_NAVIGATION:
        lower = (text or "").strip().lower()
        if not any(x in lower for x in ["maršruts", "marsruts", "ceļš", "cels", "kur", "uz ", "no "]):
            ctx112_close(user_id, "navigation_closed_new_topic")
            return None

    return None


def ctx112_after_vision_answer(user_id, caption_or_text=""):
    """Call after image answer. Vision session is marked completed, not left active forever."""
    ctx112_set(
        user_id,
        CONTEXT_VISION,
        str(caption_or_text or "image_received")[:500],
        "completed",
        "vision_answer_sent",
        expires_minutes=3
    )
    return True


def ctx112_after_navigation(user_id, route_text=""):
    ctx112_set(
        user_id,
        CONTEXT_NAVIGATION,
        str(route_text or "")[:500],
        "completed",
        "navigation_answer_sent",
        expires_minutes=5
    )
    return True


def ctx112_status_answer(user_id):
    state = ctx112_get(user_id)
    active = state.get("active_context", CONTEXT_CHAT)
    if ctx112_is_expired(state):
        active = CONTEXT_CHAT
    return (
        "🧭 Context Engine V112\n\n"
        f"Aktīvais režīms: {active}\n"
        f"Statuss: {state.get('status', 'active')}\n"
        f"Pēdējais notikums: {state.get('last_event', '') or '-'}\n\n"
        "Režīmi: chat, vision, navigation, business, profile.\n\n"
        "Versija: V114.0"
    )


def ctx112_intent_router(user_id, text):
    lower = (text or "").strip().lower()

    # Always run context cleanup first, then let normal routers answer.
    ctx112_before_text(user_id, text)

    if lower in ["context", "konteksts", "context engine", "kāds režīms", "kads rezims"]:
        return ctx112_status_answer(user_id)

    if lower in ["aizver bildi", "beidz bildi", "aizmirsti bildi", "beidz foto režīmu", "beidz foto rezimu"]:
        ctx112_close(user_id, "manual_vision_close")
        return "Aizvēru bildes/foto kontekstu. Tagad turpinām parasto sarunu. ✅\n\nVersija: V114.0"

    return None


def ctx112_regression_check():
    tests = {
        "new_profile": ctx112_text_starts_new_context("man nepatīk zvanīt klientiem"),
        "vision_follow": ctx112_is_vision_followup("ko redzi bildē?"),
        "close_vision": ctx112_should_close_vision_after_text("man nepatīk zvanīt klientiem"),
    }
    failed = [k for k, ok in tests.items() if not ok]
    if failed:
        print("Context Engine V112 regression failed:", failed)
    else:
        print("Context Engine V112 regression OK")
    return not failed

try:
    ctx112_regression_check()
except Exception as e:
    print('Context Engine V112 regression check kļūda:', repr(e))


# =========================
# V114.0 NINAOS IDENTITY ENGINE
# Single source of truth for user profile across old users, persistent profile and ninaos profile
# =========================

IDENTITY_SINGLE_FIELDS = {
    "name", "home", "business", "company", "service", "profession",
    "wife", "husband", "children", "car",
    "communication_style", "communication_preference", "routine"
}

IDENTITY_LIST_FIELDS = {
    "interests", "projects", "goals", "notes"
}

IDENTITY_LABELS = {
    "name": "Vārds",
    "home": "Dzīvesvieta/mājas",
    "business": "Bizness",
    "company": "Uzņēmums",
    "service": "Pakalpojums",
    "profession": "Joma/profesija",
    "project": "Projekts",
    "projects": "Projekti",
    "goal": "Mērķis",
    "goals": "Mērķi",
    "interests": "Intereses",
    "wife": "Sieva/ģimene",
    "husband": "Vīrs/ģimene",
    "children": "Bērni",
    "car": "Auto",
    "communication_style": "Komunikācijas stils",
    "communication_preference": "Komunikācijas izvēle",
    "routine": "Ikdienas ritms",
}


def id113_now():
    return datetime.now(ZoneInfo(DEFAULT_TIMEZONE)).strftime("%Y-%m-%d %H:%M:%S")


def id113_norm_field(field):
    field = (field or "").strip().lower().replace(" ", "_")
    aliases = {
        "project": "projects",
        "goal": "goals",
        "hobbies": "interests",
        "profession_work": "profession",
    }
    return aliases.get(field, field)[:80]


def id113_clean_value(value):
    value = (value or "").strip()
    value = re.sub(r"\s+", " ", value)
    value = value.strip(" .,!?:;")
    return value


def id113_split(value):
    value = (value or "").strip()
    if not value:
        return []
    return [p.strip() for p in re.split(r"[;\n|]+", value) if p.strip()]


def id113_merge_values(old_value, new_value, max_items=30):
    old_items = id113_split(old_value)
    new_items = id113_split(new_value)
    result = []
    seen = set()
    for item in old_items + new_items:
        key = item.strip().lower()
        if key and key not in seen:
            result.append(item.strip())
            seen.add(key)
    return "; ".join(result[-max_items:])


def id113_save_fact(user_id, field_name, field_value, category="profile", confidence=5, source="identity"):
    field = id113_norm_field(field_name)
    value = id113_clean_value(field_value)
    if not field or not value:
        return False

    try:
        # List fields merge; single fields update.
        old_value = id113_get(user_id, field)
        final_value = value
        if field in IDENTITY_LIST_FIELDS and old_value:
            final_value = id113_merge_values(old_value, value)
        if field == "interests":
            business = id113_get(user_id, "business") or id113_get(user_id, "service")
            if business and value.strip().lower() == business.strip().lower():
                return True

        conn = get_db()
        c = conn.cursor()
        db_execute(
            c,
            "SELECT id FROM ninaos_identity_facts WHERE user_id = %s AND field_name = %s AND status = %s ORDER BY id DESC LIMIT 1",
            (str(user_id), field, "active")
        )
        row = c.fetchone()
        if row:
            db_execute(
                c,
                """
                UPDATE ninaos_identity_facts
                SET field_value = %s, category = %s, confidence = %s, source = %s, updated_at = %s
                WHERE id = %s
                """,
                (final_value[:1200], str(category or "profile"), int(confidence or 5), str(source or "identity"), id113_now(), row[0])
            )
        else:
            db_execute(
                c,
                """
                INSERT INTO ninaos_identity_facts (user_id, field_name, field_value, category, confidence, source, status, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (str(user_id), field, final_value[:1200], str(category or "profile"), int(confidence or 5), str(source or "identity"), "active", id113_now())
            )
        conn.commit()
        c.close()
        conn.close()

        # Mirror into ninaos_profile table if available, but never delete other fields.
        try:
            ninaos_set_profile(user_id, field, final_value, category, confidence, "identity_mirror", 1)
        except Exception:
            pass

        # Mirror critical fields to old users table so legacy modules still see context.
        try:
            user = get_user(str(user_id))
            if field == "name":
                user["name"] = final_value
            elif field == "profession":
                user["profession"] = final_value
            elif field == "interests":
                user["hobbies"] = final_value
            elif field in ["projects", "goals"]:
                user["projects"] = id113_merge_values(user.get("projects", ""), final_value)
            elif field in ["business", "service", "company", "home", "car", "children", "wife", "husband", "communication_preference", "communication_style", "routine"]:
                technical = f"{field}: {final_value}"
                user["facts"] = id113_merge_values(user.get("facts", ""), technical)
            update_user(str(user_id), user)
        except Exception as e:
            print("id113 legacy mirror kļūda:", repr(e))

        return True
    except Exception as e:
        print("id113_save_fact kļūda:", repr(e))
        return False


def id113_get(user_id, field_name):
    field = id113_norm_field(field_name)
    if not field:
        return ""
    try:
        conn = get_db()
        c = conn.cursor()
        db_execute(
            c,
            """
            SELECT field_value
            FROM ninaos_identity_facts
            WHERE user_id = %s AND field_name = %s AND status = %s
            ORDER BY confidence DESC, id DESC
            LIMIT 1
            """,
            (str(user_id), field, "active")
        )
        row = c.fetchone()
        c.close()
        conn.close()
        if row:
            return (row[0] or "").strip()
    except Exception as e:
        print("id113_get kļūda:", repr(e))

    # Fallback to ninaos_profile
    try:
        value = ninaos_get(user_id, field)
        if value:
            return value
    except Exception:
        pass
    return ""


def id113_all(user_id):
    data = {}
    try:
        conn = get_db()
        c = conn.cursor()
        db_execute(
            c,
            """
            SELECT field_name, field_value, category, confidence
            FROM ninaos_identity_facts
            WHERE user_id = %s AND status = %s
            ORDER BY confidence DESC, id DESC
            """,
            (str(user_id), "active")
        )
        rows = c.fetchall()
        c.close()
        conn.close()
        for row in rows or []:
            try:
                field, value, category, confidence = row
                if field and field not in data:
                    data[field] = value
            except Exception:
                pass
    except Exception as e:
        print("id113_all kļūda:", repr(e))

    # Merge in ninaos_profile without overwriting identity values.
    try:
        p, meta = ninaos_get_profile(user_id)
        for k, v in (p or {}).items():
            field = id113_norm_field(k)
            if field and v and field not in data:
                data[field] = v
    except Exception:
        pass

    # Merge old users table fallback.
    try:
        user = get_user(str(user_id))
        legacy = {
            "name": user.get("name", ""),
            "profession": user.get("profession", ""),
            "interests": user.get("hobbies", ""),
            "projects": user.get("projects", ""),
        }
        for k, v in legacy.items():
            if v and k not in data:
                data[k] = v

        facts = user.get("facts", "") or ""
        for item in id113_split(facts):
            if ":" in item:
                k, v = item.split(":", 1)
                field = id113_norm_field(k)
                val = id113_clean_value(v)
                if field and val and field not in data:
                    data[field] = val
    except Exception:
        pass

    return data


def id113_sync_all_sources(user_id):
    data = id113_all(user_id)
    for field, value in data.items():
        if not value:
            continue
        category = "profile"
        if field in ["business", "company", "service", "profession"]:
            category = "work"
        elif field in ["home"]:
            category = "location"
        elif field in ["wife", "husband", "children"]:
            category = "family"
        elif field in ["car"]:
            category = "assets"
        elif field in ["communication_style", "communication_preference"]:
            category = "personality"
        elif field in ["interests"]:
            category = "interests"
        elif field in ["projects"]:
            category = "projects"
        elif field in ["goals"]:
            category = "goals"
        id113_save_fact(user_id, field, value, category, 5, "sync_all_sources")
    return True


def id113_detect_fact(text):
    raw = (text or "").strip()
    lower = raw.lower()
    if not raw or len(raw) > 700:
        return None

    # Special full phrase fixes first.
    if "nepatīk zvanīt" in lower or "nepatik zvanit" in lower:
        return "communication_preference", "nepatīk zvanīt klientiem; labāk rakstiska saziņa", "personality", 10

    patterns = [
        ("mani sauc ", "name", "identity", 10),
        ("mans vārds ir ", "name", "identity", 10),
        ("mans vards ir ", "name", "identity", 10),
        ("es dzīvoju ", "home", "location", 9),
        ("es dzivoju ", "home", "location", 9),
        ("mana dzīvesvieta ir ", "home", "location", 9),
        ("mana dzivesvieta ir ", "home", "location", 9),
        ("manas mājas ir ", "home", "location", 9),
        ("manas majas ir ", "home", "location", 9),
        ("mans bizness ir ", "business", "work", 10),
        ("mans uzņēmums ir ", "company", "work", 9),
        ("mans uznemums ir ", "company", "work", 9),
        ("mans pakalpojums ir ", "service", "work", 9),
        ("es strādāju ", "profession", "work", 8),
        ("es stradaju ", "profession", "work", 8),
        ("strādāju ar ", "business", "work", 8),
        ("stradaju ar ", "business", "work", 8),
        ("mans projekts ir ", "projects", "projects", 8),
        ("mans galvenais projekts ir ", "projects", "projects", 9),
        ("mans mērķis ir ", "goals", "goals", 8),
        ("mans merkis ir ", "goals", "goals", 8),
        ("man patīk ", "interests", "interests", 6),
        ("man patik ", "interests", "interests", 6),
        ("mani interesē ", "interests", "interests", 6),
        ("mani interese ", "interests", "interests", 6),
        ("man ir sieva", "wife", "family", 8),
        ("man ir vīrs", "husband", "family", 8),
        ("man ir virs", "husband", "family", 8),
        ("man ir bērni", "children", "family", 8),
        ("man ir berni", "children", "family", 8),
        ("man ir meita", "children", "family", 8),
        ("man ir dēls", "children", "family", 8),
        ("man ir dels", "children", "family", 8),
        ("braucu ar ", "car", "assets", 8),
        ("mana mašīna ir ", "car", "assets", 8),
        ("mana masina ir ", "car", "assets", 8),
        ("esmu introverts", "communication_style", "personality", 7),
        ("esmu ekstraverts", "communication_style", "personality", 7),
        ("ceļos ", "routine", "routine", 6),
        ("celos ", "routine", "routine", 6),
        ("eju gulēt ", "routine", "routine", 6),
        ("eju gulet ", "routine", "routine", 6),
    ]

    for marker, field, category, confidence in patterns:
        if lower.startswith(marker):
            value = raw[len(marker):].strip(" .,!?:;")
            if not value and field in ["wife", "husband", "children", "communication_style"]:
                value = raw
            if value:
                return field, value, category, confidence

    if "fasād" in lower or "fasad" in lower:
        return "business", "fasādes", "work", 7

    return None


def id113_save_detected(user_id, text):
    fact = id113_detect_fact(text)
    if not fact:
        return None
    field, value, category, confidence = fact
    ok = id113_save_fact(user_id, field, value, category, confidence, "detected_identity")
    if not ok:
        return None
    return field, value, category


def id113_profile_answer(user_id):
    id113_sync_all_sources(user_id)
    data = id113_all(user_id)

    business_value = (data.get("business") or data.get("service") or "").strip().lower()
    hidden = {"notes", "technical_notes", "memory_raw", "personal_fact"}
    order = [
        "name", "home", "business", "company", "service", "profession",
        "projects", "goals", "interests", "wife", "husband", "children",
        "car", "communication_style", "communication_preference", "routine"
    ]

    lines = ["👤 NinaOS Identity profils"]
    shown = set()
    any_data = False

    for field in order:
        value = (data.get(field) or "").strip()
        if not value:
            continue
        if field == "interests" and business_value and value.lower() == business_value:
            continue
        lines.append(f"{IDENTITY_LABELS.get(field, field)}: {value}")
        shown.add(field)
        any_data = True

    for field, value in data.items():
        if field in shown or field in hidden:
            continue
        if field == "interests" and business_value and (value or "").strip().lower() == business_value:
            continue
        if value:
            lines.append(f"{IDENTITY_LABELS.get(field, field)}: {value}")
            any_data = True

    if not any_data:
        lines.append("Vēl nav profila datu.")
        lines.append("Raksti: mani sauc Jānis; es dzīvoju Baldonē; mans bizness ir fasādes.")

    lines.append("")
    lines.append("Identity Engine apvieno veco profilu, NinaOS profilu un jauno identitātes tabulu vienā skatā.")
    lines.append("")
    lines.append("Versija: V114.0")
    return "\n".join(lines)


def id113_saved_answer(field, value, category):
    label = IDENTITY_LABELS.get(field, field)
    return (
        "Piefiksēju Identity Engine. 🧠\n\n"
        f"{label}: {value}\n\n"
        "Šis fakts tagad tiek glabāts kā NinaOS identitātes daļa, nevis pazūd starp moduļiem.\n\n"
        "Versija: V114.0"
    )


def id113_greeting(user_id):
    id113_sync_all_sources(user_id)
    data = id113_all(user_id)
    name = data.get("name", "")
    hello = f"Čau, {name}. 😊" if name else "Čau. 😊"
    business = data.get("business") or data.get("service") or data.get("profession") or ""
    home = data.get("home", "")
    car = data.get("car", "")
    comm = data.get("communication_preference") or data.get("communication_style") or ""
    goals = data.get("goals", "")
    projects = data.get("projects", "")

    if business and home and comm:
        return f"{hello}\n\nAtceros: tu esi no {home}, tavs virziens ir {business}, un tev labāk der rakstiska saziņa nekā zvani.\nKo šodien virzām — klientu ziņas, piedāvājumu vai NinaOS?\n\nVersija: V114.0"
    if business and home:
        return f"{hello}\n\nAtceros: {home}, {business}. Šodien vairāk jāstrādā pie klientiem, darbiem vai platformas?\n\nVersija: V114.0"
    if business:
        return f"{hello}\n\nAtceros tavu biznesa virzienu: {business}. Ko šodien darām praktiski?\n\nVersija: V114.0"
    if projects:
        return f"{hello}\n\nAtceros projektu: {projects}. Ko tur šodien pavirzām?\n\nVersija: V114.0"
    if car:
        return f"{hello}\n\nAtceros arī tavu auto: {car}. Kas šodien jāsakārto?\n\nVersija: V114.0"
    return f"{hello}\n\nKas šodien jādara — darbi, klienti, plāns vai NinaOS?\n\nVersija: V114.0"


def id113_context_answer(user_id):
    data = id113_all(user_id)
    keys = [k for k, v in data.items() if v]
    return (
        "🪪 Identity Engine V113\n\n"
        f"Aktīvie profila lauki: {len(keys)}\n"
        f"Lauki: {', '.join(keys[:20]) if keys else '-'}\n\n"
        "Šis ir vienotais NinaOS identitātes slānis.\n\n"
        "Versija: V114.0"
    )


def id113_intent_router(user_id, text):
    lower = (text or "").strip().lower()

    # First, sync sources so profile cannot appear empty when old data exists.
    try:
        id113_sync_all_sources(user_id)
    except Exception:
        pass

    saved = id113_save_detected(user_id, text)
    if saved:
        field, value, category = saved
        return id113_saved_answer(field, value, category)

    if lower in ["mans profils", "profils", "ninaos profils", "identity", "identitāte", "identitate", "ko tu par mani atceries", "ko tu atceries par mani"]:
        return id113_profile_answer(user_id)

    if lower in ["identity status", "identity engine", "id status"]:
        return id113_context_answer(user_id)

    if lower in ["čau", "cau", "sveika", "sveiks", "hi", "hello", "hei", "labdien"]:
        return id113_greeting(user_id)

    if lower in ["kā mani sauc", "ka mani sauc", "kā mani sauc?", "ka mani sauc?"]:
        name = id113_get(user_id, "name")
        if name:
            return f"Tevi sauc {name}. 😊\n\nTas tagad ir Identity Engine profilā.\n\nVersija: V114.0"
        return "Tavu vārdu vēl nezinu. Raksti: mani sauc Jānis\n\nVersija: V114.0"

    return None


def id113_regression_check():
    tests = {
        "comm_full": id113_detect_fact("man nepatīk zvanīt klientiem")[1].startswith("nepatīk zvanīt"),
        "name": id113_detect_fact("mani sauc Jānis")[0] == "name",
        "home": id113_detect_fact("es dzīvoju Baldonē")[0] == "home",
        "business": id113_detect_fact("mans bizness ir fasādes")[0] == "business",
        "car": id113_detect_fact("braucu ar VW Crafter")[0] == "car",
    }
    failed = [k for k, ok in tests.items() if not ok]
    if failed:
        print("Identity Engine V113 regression failed:", failed)
    else:
        print("Identity Engine V113 regression OK")
    return not failed

try:
    id113_regression_check()
except Exception as e:
    print('Identity Engine V113 regression check kļūda:', repr(e))


# =========================
# V114.0 NINAOS RELATIONSHIP ENGINE
# Shared history + follow-up + project memory + development mode
# =========================

def rel114_now():
    return datetime.now(ZoneInfo(DEFAULT_TIMEZONE)).strftime("%Y-%m-%d %H:%M:%S")


def rel114_save_event(user_id, event_type, event_text, category="relationship", importance=3, status="active"):
    event_text = (event_text or "").strip()
    if not event_text:
        return False
    try:
        conn = get_db()
        c = conn.cursor()
        db_execute(c, """
            INSERT INTO ninaos_relationship_events (user_id, event_type, event_text, category, importance, status, updated_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (str(user_id), str(event_type or "note"), event_text[:1500], str(category or "relationship"), int(importance or 3), str(status or "active"), rel114_now()))
        conn.commit()
        c.close()
        conn.close()
        return True
    except Exception as e:
        print("rel114_save_event kļūda:", repr(e))
        return False


def rel114_latest_events(user_id, limit=5, category=None):
    try:
        conn = get_db()
        c = conn.cursor()
        if category:
            db_execute(c, """
                SELECT event_type, event_text, category, importance, status, created_at
                FROM ninaos_relationship_events
                WHERE user_id = %s AND status = %s AND category = %s
                ORDER BY importance DESC, id DESC
                LIMIT %s
            """, (str(user_id), "active", str(category), int(limit or 5)))
        else:
            db_execute(c, """
                SELECT event_type, event_text, category, importance, status, created_at
                FROM ninaos_relationship_events
                WHERE user_id = %s AND status = %s
                ORDER BY id DESC
                LIMIT %s
            """, (str(user_id), "active", int(limit or 5)))
        rows = c.fetchall()
        c.close()
        conn.close()
        return rows or []
    except Exception as e:
        print("rel114_latest_events kļūda:", repr(e))
        return []


def rel114_save_idea(user_id, title, idea_text, priority="medium", status="planned"):
    title = (title or "").strip()[:160]
    idea_text = (idea_text or "").strip()
    if not title and idea_text:
        title = idea_text[:80]
    if not title:
        return False
    try:
        conn = get_db()
        c = conn.cursor()
        db_execute(c, """
            INSERT INTO ninaos_growth_ideas (user_id, idea_title, idea_text, priority, status, updated_at)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (str(user_id), title, idea_text[:1500], str(priority or "medium"), str(status or "planned"), rel114_now()))
        conn.commit()
        c.close()
        conn.close()
        return True
    except Exception as e:
        print("rel114_save_idea kļūda:", repr(e))
        return False


def rel114_latest_ideas(user_id, limit=5):
    try:
        conn = get_db()
        c = conn.cursor()
        db_execute(c, """
            SELECT idea_title, idea_text, priority, status, created_at
            FROM ninaos_growth_ideas
            WHERE user_id = %s
            ORDER BY id DESC
            LIMIT %s
        """, (str(user_id), int(limit or 5)))
        rows = c.fetchall()
        c.close()
        conn.close()
        return rows or []
    except Exception as e:
        print("rel114_latest_ideas kļūda:", repr(e))
        return []


def rel114_detect_relationship_event(text):
    raw = (text or "").strip()
    lower = raw.lower()
    if not raw:
        return None

    if any(x in lower for x in ["atrast 3 klientus", "atrast trīs klientus", "atrast tris klientus"]):
        return "goal", "Lietotāja mērķis: atrast 3 klientus", "goals", 8
    if any(x in lower for x in ["ninaos", "nina os", "nina exchange"]):
        return "project", raw, "ninaos_project", 7
    if any(x in lower for x in ["palaist ninu", "nina beta", "palaist beta", "palaist darbā", "palaist darba"]):
        return "launch", raw, "product_launch", 9
    if any(x in lower for x in ["rīt turpinam", "rit turpinam", "rīt pabeigsim", "rit pabeigsim", "vēlāk turpinam", "velak turpinam"]):
        return "unfinished", raw, "open_loop", 7
    if any(x in lower for x in ["ideja", "vajadzētu", "vajadzetu", "būtu forši", "butu forsi", "gribas lai"]):
        return "idea", raw, "growth_idea", 6
    if any(x in lower for x in ["noguris", "nav spēka", "nav speka", "smagi", "grūti", "gruti"]):
        return "mood", raw, "emotional_memory", 6
    return None


def rel114_auto_capture(user_id, text):
    item = rel114_detect_relationship_event(text)
    if not item:
        return False
    event_type, event_text, category, importance = item
    rel114_save_event(user_id, event_type, event_text, category, importance, "active")
    if category == "growth_idea":
        rel114_save_idea(user_id, event_text[:80], event_text, "medium", "planned")
    return True


def rel114_project_status_answer(user_id):
    try:
        data = id113_all(user_id)
    except Exception:
        data = {}
    events = rel114_latest_events(user_id, limit=6)
    ideas = rel114_latest_ideas(user_id, limit=4)
    lines = ["🚀 NinaOS projekta statuss", ""]
    lines += [
        "Core:",
        "✅ Identity Engine — stabils",
        "✅ Context Engine — stabils",
        "✅ Human Engine — stabils",
        "🚧 Relationship Engine — V114 aktīvs",
        "📋 Vision Pro — nākamais lielais modulis",
        "",
    ]
    if events:
        lines.append("Pēdējā kopīgā vēsture:")
        for event_type, event_text, category, importance, status, created_at in events[:5]:
            lines.append(f"• {event_text}")
        lines.append("")
    if ideas:
        lines.append("Idejas / izaugsmes virzieni:")
        for title, idea_text, priority, status, created_at in ideas[:4]:
            lines.append(f"• {title} [{status}]")
        lines.append("")
    lines.append("Tuvākais mērķis: sagatavot Nina AI Beta, lai viņa var sākt strādāt ar pirmajiem lietotājiem.")
    lines.append("")
    lines.append("Versija: V114.0")
    return "\n".join(lines)


def rel114_followup_answer(user_id):
    try:
        data = id113_all(user_id)
    except Exception:
        data = {}
    name = data.get("name", "")
    business = data.get("business") or data.get("service") or data.get("profession") or ""
    comm = data.get("communication_preference") or ""
    events = rel114_latest_events(user_id, limit=5)
    hello = f"{name}, " if name else ""
    lines = [f"🔁 {hello}turpinām no vietas, kur palikām.", ""]
    if business and comm:
        lines.append(f"Atceros: tavs virziens ir {business}, un tev labāk der rakstiska saziņa nekā zvani.")
        lines.append("Tāpēc varu uzreiz palīdzēt ar klientu ziņām, follow-up vai piedāvājumu.")
        lines.append("")
    elif business:
        lines.append(f"Atceros tavu virzienu: {business}.")
        lines.append("Varam turpināt ar klientiem, piedāvājumu vai darbu plānu.")
        lines.append("")
    if events:
        lines.append("Pēdējās svarīgās lietas:")
        for event_type, event_text, category, importance, status, created_at in events[:3]:
            lines.append(f"• {event_text}")
        lines.append("")
    lines.append("Raksti vienu konkrētu uzdevumu, un es ķeros klāt.")
    lines.append("")
    lines.append("Versija: V114.0")
    return "\n".join(lines)


def rel114_memory_answer(user_id):
    events = rel114_latest_events(user_id, limit=8)
    ideas = rel114_latest_ideas(user_id, limit=5)
    lines = ["🧠 Relationship Memory V114", ""]
    if not events and not ideas:
        lines.append("Vēl nav pietiekami daudz kopīgās vēstures.")
        lines.append("Turpinām strādāt, un es sākšu piefiksēt svarīgākos projekta un sarunas punktus.")
    else:
        if events:
            lines.append("Kopīgā vēsture:")
            for event_type, event_text, category, importance, status, created_at in events:
                lines.append(f"• {event_text}")
            lines.append("")
        if ideas:
            lines.append("Idejas:")
            for title, idea_text, priority, status, created_at in ideas:
                lines.append(f"• {title} [{status}]")
            lines.append("")
    lines.append("Versija: V114.0")
    return "\n".join(lines)


def rel114_dev_mode_answer(user_id):
    try:
        identity = id113_all(user_id)
    except Exception:
        identity = {}
    events = rel114_latest_events(user_id, limit=5)
    ideas = rel114_latest_ideas(user_id, limit=5)
    lines = ["🛠️ NinaOS Developer Mode", ""]
    lines.append("Versija: V114.0")
    lines.append("")
    lines.append("Moduļi:")
    lines.append("✅ Identity Engine")
    lines.append("✅ Context Engine")
    lines.append("✅ Human Engine")
    lines.append("🚧 Relationship Engine")
    lines.append("📋 Vision Pro")
    lines.append("📋 Smart Work")
    lines.append("📋 Voice")
    lines.append("📋 Agent Engine")
    lines.append("")
    lines.append(f"Identity lauki: {len([k for k, v in identity.items() if v])}")
    lines.append(f"Relationship events: {len(events)} pēdējie skatā")
    lines.append(f"Growth ideas: {len(ideas)} pēdējie skatā")
    lines.append("")
    lines.append("Nākamā prioritāte: Vision Pro + Beta sagatavošana.")
    lines.append("")
    lines.append("Versija: V114.0")
    return "\n".join(lines)


def rel114_greeting(user_id):
    try:
        data = id113_all(user_id)
    except Exception:
        data = {}
    name = data.get("name", "")
    business = data.get("business") or data.get("service") or data.get("profession") or ""
    comm = data.get("communication_preference") or ""
    events = rel114_latest_events(user_id, limit=3)
    hello = f"Čau, {name}. 😊" if name else "Čau. 😊"
    if events and business and comm:
        return (
            f"{hello}\n\n"
            f"Atceros mūsu virzienu: {business}, rakstiska saziņa klientiem un NinaOS attīstība.\n"
            f"Pēdējais svarīgais punkts: {events[0][1]}\n\n"
            "Ko šodien virzām — klientu ziņas, Beta palaišanu vai nākamo NinaOS moduli?\n\n"
            "Versija: V114.0"
        )
    if events:
        return f"{hello}\n\nAtceros, kur palikām: {events[0][1]}\n\nTurpinām no tās vietas vai sākam jaunu uzdevumu?\n\nVersija: V114.0"
    if business:
        return f"{hello}\n\nAtceros tavu virzienu: {business}. Šodien varam strādāt pie klientiem, piedāvājuma vai NinaOS.\n\nVersija: V114.0"
    return f"{hello}\n\nKas šodien jāvirza uz priekšu?\n\nVersija: V114.0"


def rel114_intent_router(user_id, text):
    lower = (text or "").strip().lower()
    try:
        rel114_auto_capture(user_id, text)
    except Exception:
        pass
    if lower in ["relationship", "relationship memory", "kopīgā vēsture", "kopiga vesture", "ko mēs darījām", "ko mes darijam"]:
        return rel114_memory_answer(user_id)
    if lower in ["ninaos status", "projekta statuss", "statuss", "roadmap", "ceļa karte", "cela karte"]:
        return rel114_project_status_answer(user_id)
    if lower in ["turpinam", "turpinām", "turpinam no vietas", "turpinām no vietas", "kas tālāk", "kas talak"]:
        return rel114_followup_answer(user_id)
    if lower in ["developer mode", "dev mode", "/dev", "admin mode"]:
        return rel114_dev_mode_answer(user_id)
    if lower in ["čau", "cau", "sveika", "sveiks", "hi", "hello", "hei", "labdien"]:
        return rel114_greeting(user_id)
    return None


def rel114_regression_check():
    tests = {
        "goal": rel114_detect_relationship_event("mans mērķis ir atrast 3 klientus")[0] == "goal",
        "project": rel114_detect_relationship_event("turpinam NinaOS")[0] == "project",
        "idea": rel114_detect_relationship_event("būtu forši ja viss automātiski ģenerētos")[0] == "idea",
        "launch": rel114_detect_relationship_event("drīz vajag palaist Ninu darbā")[0] == "launch",
    }
    failed = [k for k, ok in tests.items() if not ok]
    if failed:
        print("Relationship Engine V114 regression failed:", failed)
    else:
        print("Relationship Engine V114 regression OK")
    return not failed

try:
    rel114_regression_check()
except Exception as e:
    print('Relationship Engine V114 regression check kļūda:', repr(e))

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




    # V114.0 Short Conversation Memory
    db_execute(c, """
        CREATE TABLE IF NOT EXISTS conversation_state (
            id SERIAL PRIMARY KEY,
            user_id TEXT,
            user_text TEXT,
            nina_text TEXT DEFAULT '',
            intent TEXT DEFAULT '',
            emotion TEXT DEFAULT '',
            topic TEXT DEFAULT '',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # V114.0 Daily Goals
    db_execute(c, """
        CREATE TABLE IF NOT EXISTS daily_goals (
            id SERIAL PRIMARY KEY,
            user_id TEXT,
            goal_text TEXT,
            goal_date TEXT,
            status TEXT DEFAULT 'active',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)


    # V114.0 Memory Intelligence topic statistics
    db_execute(c, """
        CREATE TABLE IF NOT EXISTS user_topic_stats (
            id SERIAL PRIMARY KEY,
            user_id TEXT,
            topic TEXT,
            count INTEGER DEFAULT 1,
            last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # V12.3 Real Referral Capture
    db_execute(c, """
        CREATE TABLE IF NOT EXISTS referrals (
            id SERIAL PRIMARY KEY,
            referrer_user_id TEXT,
            invited_user_id TEXT DEFAULT '',
            referral_code TEXT DEFAULT '',
            status TEXT DEFAULT 'created',
            reward_status TEXT DEFAULT '',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)


    # V114.0 Revenue Core: usage events and commercial signals
    db_execute(c, """
        CREATE TABLE IF NOT EXISTS usage_events (
            id SERIAL PRIMARY KEY,
            user_id TEXT,
            event_type TEXT,
            event_value TEXT DEFAULT '',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    db_execute(c, """
        CREATE TABLE IF NOT EXISTS revenue_signals (
            id SERIAL PRIMARY KEY,
            user_id TEXT,
            signal_type TEXT,
            signal_value TEXT DEFAULT '',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    db_execute(c, """
        CREATE TABLE IF NOT EXISTS checkin_settings (
            user_id TEXT PRIMARY KEY,
            enabled INTEGER DEFAULT 0,
            last_checkin_at TEXT DEFAULT '',
            interval_days INTEGER DEFAULT 3,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)


    # V114.0 Assistant Platform tables
    db_execute(c, """
        CREATE TABLE IF NOT EXISTS long_term_memories (
            id SERIAL PRIMARY KEY,
            user_id TEXT,
            memory_type TEXT DEFAULT 'general',
            memory_text TEXT,
            importance INTEGER DEFAULT 1,
            last_used_at TEXT DEFAULT '',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    db_execute(c, """
        CREATE TABLE IF NOT EXISTS checkin_queue (
            id SERIAL PRIMARY KEY,
            user_id TEXT,
            checkin_text TEXT,
            due_at TEXT,
            status TEXT DEFAULT 'pending',
            source TEXT DEFAULT '',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    db_execute(c, """
        CREATE TABLE IF NOT EXISTS premium_leads (
            id SERIAL PRIMARY KEY,
            user_id TEXT,
            lead_type TEXT,
            lead_text TEXT DEFAULT '',
            score INTEGER DEFAULT 0,
            status TEXT DEFAULT 'open',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)


    # V114.0 Intelligence Layer: locations and conversation quality
    db_execute(c, """
        CREATE TABLE IF NOT EXISTS user_locations (
            id SERIAL PRIMARY KEY,
            user_id TEXT,
            location_type TEXT DEFAULT 'custom',
            location_text TEXT,
            latitude TEXT DEFAULT '',
            longitude TEXT DEFAULT '',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    db_execute(c, """
        CREATE TABLE IF NOT EXISTS response_variation_log (
            id SERIAL PRIMARY KEY,
            user_id TEXT,
            intent TEXT,
            variant_key TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)


    # V114.0 Relationship + Smart Memory tables
    db_execute(c, """
        CREATE TABLE IF NOT EXISTS smart_memory_profile (
            id SERIAL PRIMARY KEY,
            user_id TEXT,
            category TEXT,
            value TEXT,
            weight INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    db_execute(c, """
        CREATE TABLE IF NOT EXISTS relationship_notes (
            id SERIAL PRIMARY KEY,
            user_id TEXT,
            note_type TEXT,
            note_text TEXT,
            status TEXT DEFAULT 'active',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)


    # V114.0 AI Core tables
    db_execute(c, """
        CREATE TABLE IF NOT EXISTS v90_goals (
            id SERIAL PRIMARY KEY,
            user_id TEXT,
            goal_text TEXT,
            goal_type TEXT DEFAULT 'general',
            status TEXT DEFAULT 'active',
            priority INTEGER DEFAULT 1,
            last_mentioned_at TEXT DEFAULT '',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    db_execute(c, """
        CREATE TABLE IF NOT EXISTS v90_relationship_events (
            id SERIAL PRIMARY KEY,
            user_id TEXT,
            event_type TEXT,
            event_text TEXT,
            status TEXT DEFAULT 'active',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)


    # V114.0 NinaOS Platform Core tables
    db_execute(c, """
        CREATE TABLE IF NOT EXISTS ninaos_profile (
            id SERIAL PRIMARY KEY,
            user_id TEXT,
            field_name TEXT,
            field_value TEXT,
            category TEXT DEFAULT 'profile',
            confidence INTEGER DEFAULT 5,
            source TEXT DEFAULT 'chat',
            is_public INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT ''
        )
    """)

    db_execute(c, """
        CREATE TABLE IF NOT EXISTS ninaos_events (
            id SERIAL PRIMARY KEY,
            user_id TEXT,
            event_type TEXT,
            event_text TEXT,
            category TEXT DEFAULT 'general',
            importance INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    db_execute(c, """
        CREATE TABLE IF NOT EXISTS ninaos_agent_registry (
            id SERIAL PRIMARY KEY,
            agent_key TEXT,
            agent_name TEXT,
            status TEXT DEFAULT 'active',
            description TEXT DEFAULT '',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)


    # V114.0 NinaOS Context Engine tables
    db_execute(c, """
        CREATE TABLE IF NOT EXISTS ninaos_context_state (
            id SERIAL PRIMARY KEY,
            user_id TEXT,
            active_context TEXT DEFAULT 'chat',
            context_data TEXT DEFAULT '',
            status TEXT DEFAULT 'active',
            last_event TEXT DEFAULT '',
            expires_at TEXT DEFAULT '',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT ''
        )
    """)


    # V114.0 NinaOS Identity Engine tables
    db_execute(c, """
        CREATE TABLE IF NOT EXISTS ninaos_identity_facts (
            id SERIAL PRIMARY KEY,
            user_id TEXT,
            field_name TEXT,
            field_value TEXT,
            category TEXT DEFAULT 'profile',
            confidence INTEGER DEFAULT 5,
            source TEXT DEFAULT 'identity',
            status TEXT DEFAULT 'active',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT ''
        )
    """)


    # V114.0 NinaOS Relationship Engine tables
    db_execute(c, """
        CREATE TABLE IF NOT EXISTS ninaos_relationship_events (
            id SERIAL PRIMARY KEY,
            user_id TEXT,
            event_type TEXT,
            event_text TEXT,
            category TEXT DEFAULT 'relationship',
            importance INTEGER DEFAULT 3,
            status TEXT DEFAULT 'active',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT ''
        )
    """)

    db_execute(c, """
        CREATE TABLE IF NOT EXISTS ninaos_growth_ideas (
            id SERIAL PRIMARY KEY,
            user_id TEXT,
            idea_title TEXT,
            idea_text TEXT,
            priority TEXT DEFAULT 'medium',
            status TEXT DEFAULT 'planned',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT ''
        )
    """)

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
    """V114.0: Premium pārdošanas teksts ar cilvēkam saprotamu vērtību."""
    plan = current_plan_name(user_id) if user_id else PLAN_FREE
    user = get_user(user_id) if user_id else {"premium": 0, "premium_until": ""}

    if user.get("premium"):
        until = user.get("premium_until") or "bez beigu datuma"
        return (
            "💎 Tavs Nina Premium ir aktīvs\n\n"
            f"Plāns: {plan}\n"
            f"Aktīvs līdz: {until}\n\n"
            "Tu vari lietot Ninu pilnākā režīmā:\n"
            "🧠 vairāk atmiņas svarīgām lietām\n"
            "⏰ vairāk atgādinājumu ikdienai\n"
            "📅 vairāk palīdzības dienas plānošanai\n"
            "💬 mazāk ierobežojumu, kad tev tiešām vajag palīgu\n\n"
            "Komandas:\n"
            "mana diena\n"
            "premium vēsture\n"
            "mans plāns\n\n"
            "Versija: V114.0"
        )

    return (
        "💎 Nina Premium\n\n"
        "Free režīms ļauj pamēģināt Ninu. Premium ir domāts tad, kad gribi viņu izmantot kā īstu ikdienas palīgu.\n\n"
        "Ar Premium Nina var:\n"
        "🧠 atcerēties vairāk svarīgu lietu\n"
        "⏰ palīdzēt ar vairāk atgādinājumiem\n"
        "📅 biežāk palīdzēt sakārtot dienu\n"
        "💬 nebremzēt brīdī, kad tev viņa tiešām vajadzīga\n\n"
        "Premium Basic:\n"
        f"💶 {PREMIUM_BASIC_PRICE:.2f} {PREMIUM_CURRENCY}/mēn\n\n"
        "Tas ir mazāk nekā viena kafija, bet pretī tu iegūsti palīgu, kas var būt ar tevi katru dienu.\n\n"
        "Lai aktivizētu:\n"
        "pirkt basic\n\n"
        "Ja gribi paskatīties savu plānu:\n"
        "mans plāns\n\n"
        "Versija: V114.0"
    )



def premium_conversion_answer(user_id):
    """V114.0: labāks Free -> Premium pārdošanas teksts."""
    user = get_user(user_id)
    if user.get("premium"):
        return subscription_info(user_id)

    try:
        backups = backup_count_number(user_id)
    except Exception:
        backups = 0
    try:
        reminders = active_reminder_count(user_id)
    except Exception:
        reminders = 0
    try:
        summaries_today = summaries_used_today(user_id)
    except Exception:
        summaries_today = 0

    return (
        "💎 Aktivizē Nina Premium\n\n"
        "Nina nav tikai čats. Viņa ir tava personīgā AI asistente, kas atceras, plāno un palīdz katru dienu.\n\n"
        "Free režīmā tu vari pamēģināt pamatfunkcijas:\n"
        f"🧠 Saglabātās lietas: {backups}/{FREE_BACKUP_LIMIT}\n"
        f"⏰ Aktīvie atgādinājumi: {reminders}/{FREE_REMINDER_LIMIT}\n"
        f"📅 Dienas palīdzība/kopsavilkumi: {summaries_today}/{FREE_SUMMARY_LIMIT_PER_DAY}\n\n"
        "Premium Basic dod:\n"
        "✅ vairāk vietas lietām, ko Nina atceras\n"
        "✅ vairāk atgādinājumu ikdienai\n"
        "✅ vairāk palīdzības dienas plānošanai\n"
        "✅ mazāk ierobežojumu, kad tev vajag Ninu\n\n"
        f"💶 Cena: {PREMIUM_BASIC_PRICE:.2f} {PREMIUM_CURRENCY}/mēn\n\n"
        "Ja gribi, lai Nina kļūst par tavu ikdienas palīgu, raksti:\n"
        "pirkt basic\n\n"
        "Versija: V114.0"
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
        "Versija: V114.0"
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
        "Versija: V114.0"
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
        "Versija: V114.0"
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
        "Versija: V114.0"
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
        "Versija: V114.0"
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
        "Versija: V114.0",
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
            "Versija: V114.0"
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
        "Versija: V114.0"
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
        "Versija: V114.0"
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
        "Versija: V114.0",
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
            "Versija: V114.0"
        )

    log_admin_action(user_id, "user_lookup_view", "allowed", command_text)
    target = _fetch_user_row_for_admin(target_user_id)

    if not target:
        return (
            "👤 Nina User Lookup\n\n"
            f"User ID: {target_user_id}\n"
            "Statuss: nav atrasts\n\n"
            "Šāds lietotājs vēl nav Nina datubāzē.\n\n"
            "Versija: V114.0"
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
        "Versija: V114.0"
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
            "Versija: V114.0",
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

    lines.append("Versija: V114.0")
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
        "Versija: V114.0"
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
            "Versija: V114.0"
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
            "Versija: V114.0"
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
                return "🧰 Nina Admin User Actions\n\nTrūkst XP daudzuma.\n\nPiemērs:\nadd xp 5138563912 100\n\nVersija: V114.0"
            amount = max(0, int(numbers[1]))
            new_xp = int(target.get("xp", 0) or 0) + amount
            target["xp"] = new_xp
            target["level"] = calculate_level(new_xp)
            update_user(str(target_user_id), target)
            action_name = "add_xp"
            result_text = f"Pievienots {amount} XP. Jaunais XP: {new_xp}. Līmenis: {target['level']}."

        elif lower.startswith("remove xp"):
            if len(numbers) < 2:
                return "🧰 Nina Admin User Actions\n\nTrūkst XP daudzuma.\n\nPiemērs:\nremove xp 5138563912 50\n\nVersija: V114.0"
            amount = max(0, int(numbers[1]))
            new_xp = max(0, int(target.get("xp", 0) or 0) - amount)
            target["xp"] = new_xp
            target["level"] = calculate_level(new_xp)
            update_user(str(target_user_id), target)
            action_name = "remove_xp"
            result_text = f"Noņemts {amount} XP. Jaunais XP: {new_xp}. Līmenis: {target['level']}."

        elif lower.startswith("set level"):
            if len(numbers) < 2:
                return "🧰 Nina Admin User Actions\n\nTrūkst līmeņa.\n\nPiemērs:\nset level 5138563912 5\n\nVersija: V114.0"
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
            return "🧰 Nina Admin User Actions\n\nDarbība nav atpazīta.\n\nRaksti: user actions\n\nVersija: V114.0"

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
            "Versija: V114.0"
        )

    except Exception as e:
        print("Admin user action kļūda:", e)
        log_admin_action(user_id, "user_action_execute", "failed_exception", command_text)
        return (
            "🧰 Nina Admin User Actions\n\n"
            "Darbība neizdevās tehniskas kļūdas dēļ.\n\n"
            f"Iemesls: {e}\n\n"
            "Versija: V114.0"
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
        "Versija: V114.0",
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
        "Versija: V114.0",
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
        "Versija: V114.0",
    ])

    return "\n".join(lines)

def stripe_checkout_answer(user_id, plan_key="basic"):
    """V11.9 Stripe Test Router Fix — izveido reālu Stripe Checkout linku, ja ENV ir pieslēgts."""
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
            "Versija: V114.0"
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
            "Versija: V114.0"
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
        session_id = getattr(session, "id", "") or (session.id if hasattr(session, "id") else session.get("id", ""))

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
            "Versija: V114.0"
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
            "Versija: V114.0"
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
        "Versija: V114.0"
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
            "Versija: V114.0"
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
        "Versija: V114.0"
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
    "stripe setup", "stripe palīgs", "stripe paligs", "stripe helper", "maksājumi", "maksajumi", "payment setup", "stripe helper", "maksājumi", "maksajumi", "payment setup",
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
        "Versija: V114.0"
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
        "Versija: V114.0",
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
        "Versija: V114.0",
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

    if lower in ["stripe setup", "stripe palīgs", "stripe paligs", "stripe helper", "maksājumi", "maksajumi", "payment setup"]:
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




def stripe_env_guide_answer(user_id=None):
    """V11.9 Stripe Test Router Fix — atsevišķs Stripe ENV panelis."""
    checks = [
        ("STRIPE_SECRET_KEY", bool(STRIPE_SECRET_KEY)),
        ("STRIPE_BASIC_PRICE_ID", bool(STRIPE_BASIC_PRICE_ID)),
        ("STRIPE_PLUS_PRICE_ID", bool(STRIPE_PLUS_PRICE_ID)),
        ("STRIPE_SUCCESS_URL", bool(STRIPE_SUCCESS_URL and STRIPE_SUCCESS_URL != "https://t.me/")),
        ("STRIPE_CANCEL_URL", bool(STRIPE_CANCEL_URL and STRIPE_CANCEL_URL != "https://t.me/")),
        ("STRIPE_WEBHOOK_SECRET", bool(STRIPE_WEBHOOK_SECRET)),
    ]

    ready = sum(1 for _, ok in checks if ok)
    percent = int((ready / len(checks)) * 100)

    lines = [
        "💳 Nina Stripe ENV Guide",
        "",
        "Railway ENV statuss:",
        "",
    ]

    for key, ok in checks:
        lines.append(("✅ " if ok else "❌ ") + key)

    lines.extend([
        "",
        f"Stripe gatavība: {percent}%",
        "",
        "Railway ENV kopēšanai:",
        "STRIPE_SECRET_KEY=sk_test_...",
        "STRIPE_BASIC_PRICE_ID=price_...",
        "STRIPE_PLUS_PRICE_ID=price_...",
        "STRIPE_SUCCESS_URL=https://tavs-domens/success",
        "STRIPE_CANCEL_URL=https://tavs-domens/cancel",
        "STRIPE_WEBHOOK_SECRET=whsec_...",
        "",
        "Svarīgi:",
        "Ja redzi ❌ stripe package, Railway projektā vajag requirements.txt ar rindu: stripe",
        "",
        "Versija: V114.0",
    ])
    return "\n".join(lines)




def stripe_webhook_test_answer(user_id):
    """V11.9 Stripe Test Router Fix — testē Premium aktivizāciju bez īsta Stripe maksājuma."""
    ok, result = activate_premium_from_stripe(
        user_id=str(user_id),
        plan_key="basic",
        stripe_session_id="test_session_v11_8_1",
        stripe_event_id="test_event_v11_8_1",
        customer_email="test@nina.local",
    )

    if not ok:
        return (
            "🧪 Stripe Webhook Test Mode\n\n"
            "Tests neizdevās.\n"
            f"Iemesls: {result}\n\n"
            "Versija: V114.0"
        )

    return (
        "🧪 Stripe Webhook Test Mode\n\n"
        "✅ Premium aktivizācijas tests veiksmīgs.\n\n"
        f"User ID: {user_id}\n"
        "Plāns: Premium Basic\n"
        f"Premium līdz: {result}\n\n"
        "Tagad testē:\n"
        "premium\n"
        "mans plāns\n"
        "premium vēsture\n\n"
        "Versija: V114.0"
    )




# =========================
# V12.1.2 SAFE MONETIZATION LAUNCH
# =========================

def safe_launch_answer(user_id=None):
    return (
        "🚀 Nina Launch Dashboard\n\n"
        "Mērķis: palaist Ninu uz pirmajiem maksājošajiem lietotājiem.\n\n"
        "Statuss:\n"
        "✅ Premium statuss strādā\n"
        "✅ Premium vēsture strādā\n"
        "✅ Stripe webhook tests strādā\n"
        "⏳ Jāpabeidz īstais Stripe Checkout\n"
        "⏳ Jāsāk lietotāju piesaiste\n\n"
        "Nākamie soļi:\n"
        "1. Railway requirements.txt pievienot stripe\n"
        "2. Stripe ENV salikt Railway\n"
        "3. Testēt pirkt basic\n"
        "4. Dalīties ar Ninu Telegramā\n"
        "5. Savākt pirmos 10 maksājumus\n\n"
        "Komandas:\n"
        "launch\n"
        "sales\n"
        "invite\n"
        "earn\n\n"
        "Versija: V114.0"
    )


def safe_sales_answer(user_id=None):
    return (
        "💰 Nina Sales Dashboard\n\n"
        "Pārdošanas fokuss:\n"
        "• Premium Basic — 4.99 EUR/mēn\n"
        "• Premium Plus — 9.99 EUR/mēn\n\n"
        "Mērķi:\n"
        "1. Pirmais maksājums\n"
        "2. 10 maksājumi\n"
        "3. 50 aktīvi lietotāji\n"
        "4. 100 EUR MRR\n\n"
        "Galvenā komanda lietotājam:\n"
        "pirkt basic\n\n"
        "Versija: V114.0"
    )


def safe_invite_answer(user_id=None):
    bot_username = os.environ.get("TELEGRAM_BOT_USERNAME", "Nina7727_bot")
    code = f"NINA-{user_id}"
    link = f"https://t.me/{bot_username}?start={code}"
    return (
        "🔗 Uzaicini draugu uz Ninu\n\n"
        "Nosūti šo linku:\n"
        f"{link}\n\n"
        "Teksts draugam:\n"
        "Pamēģini Ninu — Telegram AI palīgs ar atmiņu, atgādinājumiem un Premium režīmu.\n\n"
        "Versija: V114.0"
    )


def safe_earn_answer(user_id=None):
    return (
        "💎 Kā Nina sāks pelnīt\n\n"
        "1. Cilvēks sāk lietot Free versiju\n"
        "2. Redz vērtību ikdienā\n"
        "3. Sasniedz Free limitus\n"
        "4. Izvēlas Premium\n"
        "5. Samaksā Stripe\n"
        "6. Premium ieslēdzas automātiski\n\n"
        "Tagad galvenais fokuss:\n"
        "Stripe + Telegram izplatīšana + pirmie maksājumi.\n\n"
        "Versija: V114.0"
    )




# =========================
# V12.3 REAL REFERRAL CAPTURE
# =========================

def referral_code_for_user(user_id):
    return f"NINA-{str(user_id)}"


def parse_referral_code_from_text(text):
    raw = (text or "").strip()
    parts = raw.split()
    if len(parts) >= 2 and parts[0].lower() == "/start":
        code = parts[1].strip()
        if re.fullmatch(r"NINA-\d{4,}", code):
            return code
    return ""


def register_referral_capture(invited_user_id, referral_code):
    """Saglabā /start NINA-XXXX referral piesaisti."""
    if not referral_code:
        return False, "missing_code"

    match = re.fullmatch(r"NINA-(\d{4,})", referral_code.strip())
    if not match:
        return False, "invalid_code"

    referrer_user_id = match.group(1)
    invited_user_id = str(invited_user_id)

    if referrer_user_id == invited_user_id:
        return False, "self_referral_blocked"

    try:
        conn = get_db()
        c = conn.cursor()

        # Ja šis invited_user jau ir piesaistīts kādam referrer, nedublējam.
        db_execute(
            c,
            "SELECT COUNT(*) FROM referrals WHERE invited_user_id = %s",
            (invited_user_id,)
        )
        existing = int(c.fetchone()[0] or 0)
        if existing > 0:
            c.close()
            conn.close()
            return False, "already_registered"

        db_execute(
            c,
            """
            INSERT INTO referrals (referrer_user_id, invited_user_id, referral_code, status, reward_status)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (referrer_user_id, invited_user_id, referral_code, "registered", "pending")
        )
        conn.commit()
        c.close()
        conn.close()
        return True, referrer_user_id

    except Exception as e:
        print("Referral capture kļūda:", e)
        return False, "db_error"


def referral_capture_welcome_answer(user_id, referral_code):
    ok, result = register_referral_capture(user_id, referral_code)

    if ok:
        return (
            "👋 Laipni lūgts pie Ninas!\n\n"
            "✅ Referral ielūgums saglabāts.\n"
            f"Uzaicinātājs: {result}\n\n"
            "Sāc ar komandu:\n"
            "premium\n\n"
            "Vai apskati:\n"
            "launch\n"
            "invite\n\n"
            "Versija: V114.0"
        )

    if result == "self_referral_blocked":
        return (
            "👋 Laipni lūgts pie Ninas!\n\n"
            "Referral netika saglabāts, jo nevar uzaicināt pats sevi.\n\n"
            "Sāc ar komandu:\n"
            "premium\n\n"
            "Versija: V114.0"
        )

    if result == "already_registered":
        return (
            "👋 Tu jau esi reģistrēts pie Ninas.\n\n"
            "Referral atkārtoti netika mainīts.\n\n"
            "Komandas:\n"
            "premium\n"
            "invite\n\n"
            "Versija: V114.0"
        )

    return (
        "👋 Laipni lūgts pie Ninas!\n\n"
        "Referral kodu neizdevās saglabāt, bet vari lietot Ninu tālāk.\n\n"
        "Sāc ar komandu:\n"
        "premium\n\n"
        "Versija: V114.0"
    )


def referral_stats_answer(user_id):
    user_id = str(user_id)
    try:
        conn = get_db()
        c = conn.cursor()
        db_execute(c, "SELECT COUNT(*) FROM referrals WHERE referrer_user_id = %s", (user_id,))
        total = int(c.fetchone()[0] or 0)
        db_execute(c, "SELECT COUNT(*) FROM referrals WHERE referrer_user_id = %s AND status = %s", (user_id, "registered"))
        registered = int(c.fetchone()[0] or 0)
        db_execute(c, "SELECT COUNT(*) FROM referrals WHERE referrer_user_id = %s AND status = %s", (user_id, "converted"))
        converted = int(c.fetchone()[0] or 0)
        c.close()
        conn.close()
    except Exception as e:
        print("Referral stats kļūda:", e)
        total = registered = converted = 0

    code = referral_code_for_user(user_id)
    bot_username = os.environ.get("TELEGRAM_BOT_USERNAME", "Nina7727_bot")
    link = f"https://t.me/{bot_username}?start={code}"

    return (
        "👥 Nina Referral Stats\n\n"
        f"Tavs kods: {code}\n"
        f"Tavs links:\n{link}\n\n"
        f"Ielūgumi kopā: {total}\n"
        f"Reģistrēti: {registered}\n"
        f"Premium konvertēti: {converted}\n\n"
        "Nākamais solis V12.4:\n"
        "ja uzaicinātais nopērk Premium, uzaicinātājs saņem bonusu.\n\n"
        "Versija: V114.0"
    )





# =========================
# V12.6 DAILY HABIT LAUNCH
# =========================

NINA_POSITIONING = "Nina – tava personīgā AI asistente, kas atceras, plāno un palīdz katru dienu."


def nina_start_answer(user_id=None):
    return (
        "👋 Sveiks! Es esmu Nina.\n\n"
        "Nina – tava personīgā AI asistente, kas atceras, plāno un palīdz katru dienu.\n\n"
        "Es varu tev palīdzēt:\n"
        "🧠 atcerēties svarīgas lietas\n"
        "📅 sakārtot dienu\n"
        "⏰ atgādināt par svarīgiem notikumiem\n"
        "💬 būt tavs ikdienas AI palīgs\n\n"
        "Pamēģini uzreiz:\n"
        "mana diena\n"
        "atceries\n"
        "premium\n\n"
        "Ja gribi uzaicināt draugu:\n"
        "invite\n\n"
        "Versija: V114.0"
    )



# =========================
# V114.0 NATURAL MEMORY + DAILY GOALS
# =========================

def save_daily_goal(user_id, goal_text):
    """V114.0: dienas mērķa saglabāšana pārvietota uz memory.py loģiku."""
    return save_daily_goal_logic(get_db, db_execute, DEFAULT_TIMEZONE, user_id, goal_text)



def latest_daily_goals(user_id, limit=3):
    """V114.0: dienas mērķu nolasīšana pārvietota uz memory.py loģiku."""
    return latest_daily_goals_logic(get_db, db_execute, DEFAULT_TIMEZONE, user_id, limit)



def save_natural_memory(user_id, memory_text):
    """V114.0: dabiskās atmiņas saglabāšana pārvietota uz memory.py loģiku."""
    return save_natural_memory_logic(get_db, db_execute, user_id, memory_text)



def latest_natural_memories(user_id, limit=3):
    """V114.0: pēdējo atmiņu nolasīšana pārvietota uz memory.py loģiku."""
    return latest_natural_memories_logic(get_db, db_execute, user_id, limit)



def nina_memory_saved_answer(saved_text):
    """V114.0: atmiņas saglabāšanas teksts no memory.py vai fallback."""
    return build_memory_saved_answer(saved_text, version="V114.0")



def nina_goal_saved_answer(goal_text):
    """V114.0: mērķa saglabāšanas teksts no memory.py vai fallback."""
    return build_goal_saved_answer(goal_text, version="V114.0")



def nina_daily_habit_answer(user_id):
    """V114.0: Daily Assistant ar coach.py + brain.py secinājumiem."""
    try:
        user = get_user(str(user_id))
    except Exception as e:
        print("mana diena get_user kļūda:", e)
        user = {"premium": 0, "name": ""}

    try:
        plan = current_plan_name(str(user_id))
    except Exception:
        plan = PLAN_FREE

    is_premium = bool(user.get("premium"))

    try:
        reminders = active_reminder_count(str(user_id))
    except Exception:
        reminders = 0

    try:
        raw_goals = latest_daily_goals(str(user_id), limit=3)
        goals = [row[0] for row in raw_goals if row and row[0]]
    except Exception as e:
        print("mana diena goals kļūda:", e)
        goals = []

    try:
        raw_memories = latest_natural_memories(str(user_id), limit=5)
        memories = [row[0] for row in raw_memories if row and row[0]]
    except Exception as e:
        print("mana diena memories kļūda:", e)
        memories = []

    try:
        brain_summary = build_brain_summary(memories)
    except Exception as e:
        print("brain summary kļūda:", e)
        brain_summary = None

    name = (user.get("name") or "").strip()

    base = build_daily_answer(
        name=name,
        plan=plan,
        is_premium=is_premium,
        goals=goals,
        memories=memories[:3],
        reminders=reminders,
        version="V114.0",
    )

    try:
        tip = build_daily_coach_tip(
            goals=goals,
            memories=memories,
            reminders=reminders,
            brain_summary=brain_summary,
        )
    except TypeError:
        tip = build_daily_coach_tip(goals=goals, memories=memories, reminders=reminders)

    return base + "\n\n" + tip + "\n\n" + nina_daily_closing_line()



def nina_morning_answer(user_id):
    """V114.0: labrīta teksts no daily.py vai fallback."""
    try:
        user = get_user(str(user_id))
        name = (user.get("name") or "").strip()
    except Exception:
        name = ""
    return build_morning_answer(name=name, version="V114.0")



def nina_evening_answer(user_id):
    """V114.0: vakara teksts no daily.py vai fallback."""
    return build_evening_answer(version="V114.0")



def nina_today_goal_answer(user_id):
    """V114.0: mērķa teksta sagatave no daily.py vai fallback."""
    return build_goal_prompt_answer(version="V114.0")



def nina_remember_prompt_answer(user_id=None):
    return (
        "🧠 Ko vēlies, lai es atceros?\n\n"
        "Vari rakstīt vienkārši, piemēram:\n"
        "Atceries, ka pirmdien 10:00 jāzvana klientam.\n"
        "Atceries, ka man patīk melna BMW krāsa.\n"
        "Atceries, ka šonedēļ jāizdara projekta plāns.\n\n"
        "Ja tā ir svarīga doma, uzdevums vai fakts — uztici to man.\n\n"
        "Versija: V114.0"
    )


def nina_launch_invite_text(user_id):
    bot_username = os.environ.get("TELEGRAM_BOT_USERNAME", "Nina7727_bot")
    try:
        code = referral_code_for_user(user_id)
    except Exception:
        code = f"NINA-{user_id}"
    link = f"https://t.me/{bot_username}?start={code}"
    return (
        "🔗 Uzaicini cilvēku pamēģināt Ninu\n\n"
        "Nosūti šo tekstu:\n\n"
        "🤖 Pamēģini Ninu!\n\n"
        "Nina ir personīgā AI asistente, kas atceras, plāno un palīdz katru dienu.\n\n"
        "Viņa var palīdzēt:\n"
        "• atcerēties svarīgas lietas;\n"
        "• sakārtot dienu;\n"
        "• veidot atgādinājumus;\n"
        "• būt tavs ikdienas AI palīgs.\n\n"
        "Sākt var bez maksas:\n"
        f"{link}\n\n"
        "Versija: V114.0"
    )


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """V12.6: pirmais iespaids + referral capture."""
    user_id = str(update.effective_user.id)
    args = context.args or []
    referral_code = args[0].strip() if args else ""

    if referral_code and re.fullmatch(r"NINA-\d{4,}", referral_code):
        answer = referral_capture_welcome_answer(user_id, referral_code)
        answer += (
            "\n\n"
            "Es esmu Nina — tava personīgā AI asistente, kas atceras, plāno un palīdz katru dienu.\n\n"
            "Pamēģini:\n"
            "mana diena\n"
            "atceries\n"
            "premium\n\n"
            "Versija: V114.0"
        )
    else:
        answer = nina_start_answer(user_id)

    await safe_reply_text(update, answer, disable_web_page_preview=True)


def apply_referral_reward(invited_user_id):
    """V12.4: ja uzaicinātais kļūst Premium, piešķir bonusu uzaicinātājam."""
    invited_user_id = str(invited_user_id)

    try:
        conn = get_db()
        c = conn.cursor()

        db_execute(
            c,
            """
            SELECT id, referrer_user_id, reward_status
            FROM referrals
            WHERE invited_user_id = %s
            ORDER BY id ASC
            LIMIT 1
            """,
            (invited_user_id,)
        )
        row = c.fetchone()

        if not row:
            c.close()
            conn.close()
            return False, "no_referral"

        referral_id, referrer_user_id, reward_status = row

        if reward_status == "rewarded":
            c.close()
            conn.close()
            return False, "already_rewarded"

        referrer = get_user(str(referrer_user_id))
        user_tz = ZoneInfo(referrer.get("timezone") or DEFAULT_TIMEZONE)
        today = datetime.now(user_tz).date()

        current_until_raw = (referrer.get("premium_until") or "").strip()
        if current_until_raw:
            try:
                current_until = datetime.strptime(current_until_raw, "%Y-%m-%d").date()
            except Exception:
                current_until = today
        else:
            current_until = today

        start_date = max(today, current_until)
        new_until = (start_date + timedelta(days=REFERRAL_BONUS_DAYS)).strftime("%Y-%m-%d")

        referrer["premium"] = 1
        referrer["premium_until"] = new_until
        referrer["xp"] = int(referrer.get("xp", 0) or 0) + REFERRAL_BONUS_XP
        referrer["level"] = max(1, int(referrer["xp"] // XP_PER_LEVEL) + 1)
        update_user(str(referrer_user_id), referrer)

        db_execute(
            c,
            """
            UPDATE referrals
            SET status = %s, reward_status = %s
            WHERE id = %s
            """,
            ("converted", "rewarded", referral_id)
        )
        conn.commit()
        c.close()
        conn.close()

        record_premium_transaction(
            user_id=str(referrer_user_id),
            plan_name=PLAN_PREMIUM_BASIC,
            amount=0,
            currency=PREMIUM_CURRENCY,
            payment_method="referral_reward",
            status="rewarded",
            expires_at=new_until,
            checkout_url="",
            stripe_session_id="",
            stripe_event_id="",
            customer_email="",
        )

        return True, str(referrer_user_id)

    except Exception as e:
        print("Referral reward kļūda:", e)
        return False, "reward_error"


def referral_reward_test_answer(user_id):
    """V12.4: tests bonusu mehānikai bez Stripe maksājuma."""
    ok, result = apply_referral_reward(str(user_id))
    if ok:
        return (
            "🎁 Referral Reward Test\n\n"
            "✅ Bonuss piešķirts uzaicinātājam.\n"
            f"Uzaicinātājs: {result}\n\n"
            "Bonuss:\n"
            f"+{REFERRAL_BONUS_DAYS} Premium dienas\n"
            f"+{REFERRAL_BONUS_XP} XP\n\n"
            "Versija: V114.0"
        )

    return (
        "🎁 Referral Reward Test\n\n"
        "Bonuss netika piešķirts.\n"
        f"Iemesls: {result}\n\n"
        "Tas ir normāli, ja šim lietotājam nav referral ieraksta vai bonuss jau piešķirts.\n\n"
        "Versija: V114.0"
    )




# =========================
# V12.5 STRIPE PRODUCTION SETUP
# =========================

def stripe_production_setup_answer(user_id=None):
    """V12.5: tikai īstajam maksājumu palaišanas solim."""
    checks = [
        ("stripe package", bool(stripe)),
        ("STRIPE_SECRET_KEY", bool(STRIPE_SECRET_KEY)),
        ("STRIPE_BASIC_PRICE_ID", bool(STRIPE_BASIC_PRICE_ID)),
        ("STRIPE_PLUS_PRICE_ID", bool(STRIPE_PLUS_PRICE_ID)),
        ("STRIPE_SUCCESS_URL", bool(STRIPE_SUCCESS_URL and STRIPE_SUCCESS_URL != "https://t.me/")),
        ("STRIPE_CANCEL_URL", bool(STRIPE_CANCEL_URL and STRIPE_CANCEL_URL != "https://t.me/")),
        ("STRIPE_WEBHOOK_SECRET", bool(STRIPE_WEBHOOK_SECRET)),
    ]

    ready = sum(1 for _, ok in checks if ok)
    percent = int((ready / len(checks)) * 100)

    lines = [
        "💳 Nina Stripe Production Setup",
        "",
        "Mērķis: pirmais īstais maksājums.",
        "",
        "Statuss:",
    ]

    for name, ok in checks:
        lines.append(("✅ " if ok else "❌ ") + name)

    lines.extend([
        "",
        f"Gatavība: {percent}%",
        "",
        "Railway vajag:",
        "1. requirements.txt ar rindu: stripe",
        "2. STRIPE_SECRET_KEY=sk_live_... vai sk_test_...",
        "3. STRIPE_BASIC_PRICE_ID=price_...",
        "4. STRIPE_PLUS_PRICE_ID=price_...",
        "5. STRIPE_SUCCESS_URL=https://tavs-domens/success",
        "6. STRIPE_CANCEL_URL=https://tavs-domens/cancel",
        "7. STRIPE_WEBHOOK_SECRET=whsec_...",
        "",
        "Stripe Dashboard webhook:",
        "Endpoint:",
        "https://nina7727-production.up.railway.app/stripe/webhook",
        "",
        "Event:",
        "checkout.session.completed",
        "",
        "Pēc ENV ielikšanas testē:",
        "stripe production",
        "stripe env",
        "pirkt basic",
        "stripe webhook",
        "",
        "Versija: V114.0",
    ])
    return "\n".join(lines)


def first_payment_plan_answer(user_id=None):
    return (
        "💰 Nina First Payment Plan\n\n"
        "Mērķis: dabūt pirmo īsto maksājumu.\n\n"
        "Secība:\n"
        "1. Railway pievieno stripe package\n"
        "2. Stripe izveido Product: Nina Premium Basic\n"
        "3. Stripe izveido Price: 4.99 EUR monthly\n"
        "4. Railway ieliec STRIPE_BASIC_PRICE_ID\n"
        "5. Railway ieliec STRIPE_SECRET_KEY\n"
        "6. Stripe ieliec webhook endpoint\n"
        "7. Railway ieliec STRIPE_WEBHOOK_SECRET\n"
        "8. Telegram testē: pirkt basic\n"
        "9. Veic testa maksājumu\n"
        "10. Pārbaudi: premium un premium vēsture\n\n"
        "Nākamais biznesa mērķis pēc tam: 10 maksājumi.\n\n"
        "Versija: V114.0"
    )



# V114.0 natural conversation logic is in conversation.py



def record_memory_topics(user_id, memory_text):
    """V114.0: pēc atmiņas saglabāšanas pieraksta tēmas brain/analytics vajadzībām."""
    try:
        topics = detect_topics(memory_text)
    except Exception as e:
        print("detect_topics kļūda:", e)
        topics = []

    if not topics:
        return []

    conn = None
    try:
        conn = get_db()
        c = conn.cursor()

        for topic in topics:
            # Vienkāršs, drošs variants: katru tēmas parādīšanos saglabā kā ierakstu.
            # Analītika pēc tam saskaita ierakstus.
            db_execute(
                c,
                """
                INSERT INTO user_topic_stats (user_id, topic, count)
                VALUES (%s, %s, %s)
                """,
                (str(user_id), topic, 1)
            )

        conn.commit()
        c.close()
        conn.close()
        return topics
    except Exception as e:
        print("record_memory_topics kļūda:", e)
        try:
            if conn:
                conn.close()
        except Exception:
            pass
        return []


def user_topic_counts(user_id, limit=5):
    """V114.0: atgriež lietotāja dominējošo tēmu skaitītāju."""
    conn = None
    try:
        conn = get_db()
        c = conn.cursor()
        db_execute(
            c,
            """
            SELECT topic, COALESCE(SUM(count), 0) AS total
            FROM user_topic_stats
            WHERE user_id = %s
            GROUP BY topic
            ORDER BY total DESC
            LIMIT %s
            """,
            (str(user_id), int(limit or 5))
        )
        rows = c.fetchall()
        c.close()
        conn.close()
        return {str(topic): int(total or 0) for topic, total in rows}
    except Exception as e:
        print("user_topic_counts kļūda:", e)
        try:
            if conn:
                conn.close()
        except Exception:
            pass
        return {}


def nina_progress_answer(user_id):
    """V114.0: lietotāja progress ar analytics.py + brain.py."""
    try:
        user = get_user(str(user_id))
    except Exception as e:
        print("progress get_user kļūda:", e)
        user = {"streak_days": 0, "xp": 0, "level": 1}

    try:
        raw_memories = latest_natural_memories(str(user_id), limit=20)
        memories = [row[0] for row in raw_memories if row and row[0]]
    except Exception as e:
        print("progress memories kļūda:", e)
        memories = []

    try:
        raw_goals = latest_daily_goals(str(user_id), limit=10)
        goals = [row[0] for row in raw_goals if row and row[0]]
    except Exception as e:
        print("progress goals kļūda:", e)
        goals = []

    try:
        reminders = active_reminder_count(str(user_id))
    except Exception:
        reminders = 0

    try:
        topic_counts = user_topic_counts(str(user_id), limit=5)
        if not topic_counts:
            topic_counts = analyze_memories(memories)
    except Exception:
        topic_counts = {}

    snapshot = build_activity_snapshot(
        memories=memories,
        goals=goals,
        reminders_count=reminders,
        streak_days=user.get("streak_days", 0),
        xp=user.get("xp", 0),
        level=user.get("level", 1),
    )

    if not memories and not goals and reminders == 0:
        return build_empty_progress_text(version="V114.0")

    return build_weekly_progress_text(snapshot, topic_counts=topic_counts, version="V114.0")



# =========================
# Core Evolution 2.5.2 — Reply Builder Polish
# =========================
# Reply Builder ir centrālais NinaOS komunikācijas slānis.
# Core 2.5.2 polish: gala tekstā drīkst palikt tikai viena "Versija:" rinda.

REPLY_BUILDER_VERSION = "Core 2.5.2 — Reply Builder Polish V1.1"
APP_VERSION = "V115.4 + Core 2.5.2"


def rb_remove_version_lines(text):
    """Noņem jebkuru rindu, kas sākas ar 'Versija:'."""
    lines = str(text or "").splitlines()
    cleaned = []
    for line in lines:
        if re.match(r"^\s*Versija\s*:", line or "", flags=re.IGNORECASE):
            continue
        cleaned.append(line)
    return "\n".join(cleaned).strip()


def rb_clean_text(value):
    """Notīra liekas versiju rindas, tukšumus un tehnisko troksni."""
    text = str(value or "").strip()
    if not text:
        return ""

    text = rb_remove_version_lines(text)
    text = re.sub(r"\n{3,}", "\n\n", text).strip()
    return text


def rb_detect_intent(text):
    lower = (text or "").strip().lower()
    if not lower:
        return "empty"

    if any(x in lower for x in ["premium", "abonements", "pirkt", "cena", "tarifs"]):
        return "business"

    if any(x in lower for x in [
        "klienti", "andri", "andris", "piedāvājums", "piedavajums",
        "follow-up", "followup", "jāpajautā", "japajauta"
    ]):
        return "client_work"

    if any(x in lower for x in ["mana diena", "darba inbox", "ko man šodien", "ko man sodien"]):
        return "daily_brief"

    if any(x in lower for x in ["ko man tagad", "kas svarīgākais", "ko iesaki"]):
        return "initiative"

    if any(x in lower for x in ["core", "ninaos", "initiative", "think engine", "learning", "quality", "reply builder"]):
        return "ninaos_core"

    if any(x in lower for x in ["čau", "cau", "sveika", "sveiks", "hello", "hi", "kā tev iet", "ka tev iet"]):
        return "conversation"

    return "general"


def rb_detect_tone(text):
    lower = (text or "").strip().lower()

    if any(x in lower for x in ["smagi", "grūti", "gruti", "slikti", "noguris", "nogurusi", "bēdīgi", "bedigi"]):
        return "supportive"

    if any(x in lower for x in ["premium", "cena", "tarifs", "pirkt", "abonements"]):
        return "commercial_warm"

    if any(x in lower for x in ["core", "ninaos", "architecture", "arhitekt", "engine"]):
        return "architectural"

    return "warm"


def build_reply_object(main_message="", user_text="", source="legacy_router", intent="", tone="", channel="telegram", metadata=None):
    return {
        "intent": intent or rb_detect_intent(user_text or main_message),
        "tone": tone or rb_detect_tone(user_text or main_message),
        "priority": "normal",
        "identity": "Nina — AI darbiniece NinaOS platformā",
        "main_message": main_message or "",
        "channel": channel or "telegram",
        "metadata": metadata or {"source": source},
    }


def reply_builder_build(reply_object):
    if isinstance(reply_object, str):
        reply_object = build_reply_object(main_message=reply_object)

    if not isinstance(reply_object, dict):
        reply_object = build_reply_object(main_message=str(reply_object or ""))

    text = rb_clean_text(reply_object.get("main_message", ""))

    if not text:
        text = "Esmu te. 😊\n\nPasaki, ko vajag sakārtot, un es palīdzēšu soli pa solim."

    channel = (reply_object.get("channel") or "telegram").lower()

    if channel == "telegram" and len(text) > 3800:
        text = text[:3700].rstrip() + "\n\n…"

    # Core 2.5.2: vienmēr tikai viena gala versijas rinda.
    text = rb_remove_version_lines(text).rstrip()
    text = text + f"\n\nVersija: {APP_VERSION}"

    return {
        "text": text,
        "buttons": [],
        "attachments": [],
        "actions": [],
        "metadata": {
            "builder": REPLY_BUILDER_VERSION,
            "intent": reply_object.get("intent", ""),
            "tone": reply_object.get("tone", ""),
            **(reply_object.get("metadata") or {}),
        },
    }


def reply_builder_text(text, user_text="", source="legacy_router", channel="telegram"):
    obj = build_reply_object(
        main_message=text,
        user_text=user_text,
        source=source,
        channel=channel,
    )
    return reply_builder_build(obj).get("text", "")


def reply_builder_status_answer():
    return reply_builder_text(
        "🧩 Core 2.5.2 — Reply Builder Polish V1.1 ir aktīvs. ✅\n\n"
        "Gala atbildes pirms sūtīšanas iet caur vienu centrālo komunikācijas slāni.\n\n"
        "Ko šis polish labo:\n"
        "• noņem dubultās Versija rindas;\n"
        "• saglabā moduļa saturu;\n"
        "• pieliek tikai vienu gala versiju;\n"
        "• laba moduļa atbilde netiek pārrakstīta ar fallback.\n\n"
        "Tests:\n"
        "• klienti\n"
        "• kas notiek ar Andri\n"
        "• ko man tagad darīt\n"
        "• mana diena",
        source="reply_builder_status",
    )


async def safe_reply_text(update, text, disable_web_page_preview=True):
    """Core 2.5.2: vienīgā drošā izeja gala tekstam uz Telegram."""
    try:
        if update and update.message:
            try:
                user_text = update.message.text if getattr(update, "message", None) else ""
            except Exception:
                user_text = ""

            final_text = reply_builder_text(
                text,
                user_text=user_text,
                source="safe_reply_text",
                channel="telegram",
            )

            await update.message.reply_text(
                final_text,
                disable_web_page_preview=disable_web_page_preview
            )
            return True
    except Exception as e:
        print("safe_reply_text kļūda:", e)
    return False

def public_test_fallback_answer():
    return nina_public_offer_answer()



def nina_public_offer_answer(user_text=""):
    """V114.0: jebkuram lietotājam dzīva atbilde un piedāvājums."""
    clean = (user_text or "").strip()
    if clean:
        return (
            "Es tevi dzirdu. 😊\n\n"
            f"Tu uzrakstīji: {clean}\n\n"
            "Es vēl mācos saprast cilvēkus gudrāk, bet vari man rakstīt dabiski.\n"
            "Pasaki, kas jāatceras, kas jāizdara vai ko vajag sakārtot — es mēģināšu palīdzēt.\n\n"
            "Piemēram:\n"
            "rīt jāzvana klientam\n"
            "vai:\n"
            "atgādini rīt 10:00 piezvanīt klientam\n\n"
            "Versija: V114.0"
        )
    return charm_smalltalk_answer(version="V114.0")



def nina_rough_message_answer():
    return charm_rough_answer(version="V114.0")



def looks_like_rough_message(text):
    lower = (text or "").strip().lower()
    rough_words = [
        "stulba", "stulbs", "idiot", "idiote", "debils", "debila",
        "sūds", "suds", "fuck", "nah", "bļ", "blja", "pis", "hui"
    ]
    return any(w in lower for w in rough_words)


def is_short_unknown_message(text):
    lower = (text or "").strip().lower()
    if not lower:
        return True
    known_starts = [
        "/start", "premium", "pirkt", "mana diena", "labrīt", "labrit",
        "vakars", "mērķis", "merkis", "atceries", "invite", "progress",
        "statistika", "atgādini", "atgadini"
    ]
    if any(lower.startswith(x) for x in known_starts):
        return False
    return len(lower) <= 40




# =========================
# V115.3 NINA CORE — Mission & Strategy Brain
# =========================
# Mērķis: Nina vispirms saprot cilvēku, identitāti, nodomu un darba kvalitāti.
# Šis nav vēl viens "if" slānis — tas ir Ninas uzvedības kodols.

V1151_VERSION = "V115.3"


def v1151_clean_version(text, version=V1151_VERSION):
    text = (text or "").strip()
    if not text:
        text = "Esmu te. Pasaki, kas jāatrisina."
    text = re.sub(r"\n\nVersija:\s*V\d+(?:\.\d+)?", "", text).strip()
    text = re.sub(r"Versija:\s*V\d+(?:\.\d+)?", "", text).strip()
    return text.rstrip() + f"\n\nVersija: {version}"


def v1151_user(user_id):
    try:
        return get_user(str(user_id)) or {}
    except Exception as e:
        print("v1152_user kļūda:", repr(e))
        return {}


def v1151_name(user):
    return ((user or {}).get("name") or "").strip()


def v1151_split(value):
    value = (value or "").strip()
    if not value:
        return []
    return [p.strip() for p in re.split(r"[;\n|]+", value) if p.strip()]


def v1151_is_legacy_command(lower):
    lower = (lower or "").strip().lower()
    if not lower:
        return False
    starts = (
        "/start", "premium", "pirkt", "stripe", "admin", "health", "system status",
        "kpi", "alerts", "backup", "restore", "recovery", "analytics", "revenue",
        "user management", "grant premium", "remove premium", "add xp", "remove xp",
        "set level", "reset streak", "search user", "find user", "lietotāji", "lietotaji",
        "referral", "invite", "launch", "production", "webhook", "db backup",
        "auto backup", "activity", "notifications", "audit", "mans plāns", "mans plans",
        "abonements", "premium funkcijas", "premium limiti", "premium beidzas"
    )
    return lower.startswith(starts)


def v1151_status_answer():
    return (
        "🧠 Nina Core V115.3 ir aktīvs. ✅\n\n"
        "Galvenais noteikums: Nina nav robots un nav funkciju saraksts. Nina ir AI darbiniece.\n\n"
        "Prioritātes:\n"
        "100 Identity First\n"
        "97 Memory Recall\n"
        "95 Question Router\n"
        "92 Critique / Quality Mode\n"
        "90 Mission / Strategy Brain\n"
        "88 Employee Brain\n"
        "84 Goal / Mission Classifier\n"
        "82 Smart Memory Filter\n"
        "75 Vision Smart Reply\n"
        "50 Human Conversation\n"
        "10 Legacy fallback\n\n"
        "Darbinieces princips: saprast, atcerēties, domāt stratēģiski un dot nākamo soli, nevis pļāpāt.\n\n"
        "Versija: V115.3"
    )


def v1151_is_question(lower):
    lower = (lower or "").strip().lower()
    return "?" in lower or lower.startswith((
        "vai ", "ko ", "kas ", "kā ", "ka ", "kur ", "kad ", "kapēc ", "kāpēc ",
        "cik ", "a ", "tu zini", "zini", "atceries"
    ))


def v1151_identity_question(lower):
    lower = (lower or "").strip().lower()
    patterns = [
        "kā mani sauc", "ka mani sauc", "kāds ir mans vārds", "kads ir mans vards",
        "zini manu vārdu", "zini manu vardu", "tu zini manu vārdu", "tu zini manu vardu",
        "atceries manu vārdu", "atceries manu vardu", "atceries kā mani sauc", "atceries ka mani sauc",
        "a vārdu tagad zini", "a vardu tagad zini", "vai tu zini manu vārdu", "vai tu zini manu vardu",
        "mans vārds", "mans vards", "kas es esmu"
    ]
    return any(p in lower for p in patterns)


def v1151_profile_question(lower):
    lower = (lower or "").strip().lower()
    patterns = [
        "ko tu par mani zini", "ko par mani zini", "ko tu par mani atceries",
        "ko atceries par mani", "mans profils", "parādi manu profilu", "paradi manu profilu",
        "kas man patīk", "kas man patik", "kur es dzīvoju", "kur es dzivoju",
        "kur es strādāju", "kur es stradaju", "kāda ir mana joma", "kada ir mana joma"
    ]
    return any(p in lower for p in patterns)


def v1151_memory_recall_question(lower):
    lower = (lower or "").strip().lower()
    patterns = [
        "ko tu atceries", "ko atceries", "ko es tev teicu", "ko es tev liku atcerēties",
        "ko es tev liku atcereties", "kādas atmiņas", "kadas atminas", "parādi atmiņas",
        "paradi atminas", "ko tu piefiksēji", "ko tu piefikseji"
    ]
    return any(p in lower for p in patterns)


def v1151_identity_answer(user_id, text):
    """
    V115.3 Profile Bridge.
    Viena droša vieta profila jautājumiem:
    - lasa users tabulas laukus;
    - ja profils tukšs, lasa arī natural memory;
    - neļauj Ninai teikt "pagaidām maz", ja kaut kas jau ir atmiņā.
    """
    user = v1151_user(user_id)
    name = v1151_name(user)
    lower = (text or "").strip().lower()

    if v1151_identity_question(lower):
        if name:
            return v1151_clean_version(
                f"Jā. Tevi sauc {name}. 🙂\n\n"
                "Šādu lietu man nav jāmin — tā ir identitāte, un man tā jāizmanto sarunā."
            )
        return v1151_clean_version(
            "Tavu vārdu vēl neredzu profilā.\n\n"
            "Uzraksti: mani sauc Jānis — un pēc tam man tas jāatceras bez atkārtošanas."
        )

    if v1151_profile_question(lower):
        lines = ["👤 Ko es par tevi zinu"]
        found = False

        if name:
            lines.append(f"Vārds: {name}")
            found = True

        if user.get("city"):
            lines.append(f"Dzīvesvieta/pilsēta: {user.get('city')}")
            found = True

        if user.get("profession"):
            lines.append(f"Joma/profesija: {user.get('profession')}")
            found = True

        if user.get("hobbies"):
            lines.append(f"Intereses: {user.get('hobbies')}")
            found = True

        if user.get("projects"):
            lines.append(f"Projekti: {user.get('projects')}")
            found = True

        if user.get("goals"):
            lines.append(f"Mērķi: {user.get('goals')}")
            found = True

        if user.get("facts"):
            lines.append(f"Svarīgi fakti: {user.get('facts')}")
            found = True

        # Memory bridge: ja users profils ir tukšs, Nina pārbauda arī natural memory.
        memories = []
        try:
            for row in latest_natural_memories(user_id, limit=8) or []:
                if row and row[0]:
                    value = str(row[0]).strip()
                    if value and value not in memories:
                        memories.append(value)
        except Exception as e:
            print("v1151 profile memory bridge kļūda:", repr(e))

        if memories:
            lines.append("Atmiņas:")
            for m in memories[:8]:
                lines.append(f"• {m}")
            found = True

        if not found:
            lines.append(
                "Pagaidām profilā neredzu pietiekami daudz datu.\n\n"
                "Svarīgi: tas nozīmē, ka šobrīd jānostiprina Memory/Profile slānis, "
                "nevis jāizliekas, ka viss ir kārtībā."
            )

        lines.append("")
        lines.append("Ja kaut kas nav pareizi, pasaki tieši — es labošu profilu, nevis strīdēšos.")
        return v1151_clean_version("\n".join(lines))

    return None


def v1151_memory_recall_answer(user_id):
    memories = []
    try:
        for row in latest_natural_memories(user_id, limit=5) or []:
            if row and row[0]:
                memories.append(str(row[0]))
    except Exception:
        pass
    if not memories:
        return v1151_clean_version("Es vēl neredzu saglabātas atmiņas. Ja gribi, lai kaut ko turu prātā, raksti: atceries, ka ...")
    lines = ["🧠 Pēdējās lietas, ko atceros:"]
    for m in memories[:5]:
        lines.append(f"• {m}")
    lines.append("")
    lines.append("Ja kāda atmiņa ir nepareiza, pasaki — dzēsīsim vai labosim.")
    return v1151_clean_version("\n".join(lines))



def v1151_is_mission_text(lower):
    lower = (lower or "").strip().lower()
    if not lower or "?" in lower:
        return False
    big_words = [
        "globāli", "globali", "pasaules", "visas pasaules", "platform", "ninaos",
        "mākslīgos darbiniekus", "maksligos darbiniekus", "ai darbiniek", "komisijas",
        "līgumi", "ligumi", "exchange", "tirgus", "ekosist", "automatiz", "automātik",
        "struktūras", "strukturas", "misija", "vīzija", "vizija", "sasniegt jebko"
    ]
    intent_words = ["gribu", "mērķis", "merkis", "lai", "pārvald", "parvalda", "dot iespējas", "dot iespejas", "attīst", "atistis"]
    return ("ninaos" in lower and any(w in lower for w in big_words)) or (sum(1 for w in big_words if w in lower) >= 2 and any(w in lower for w in intent_words))


def v1151_is_help_achieve(lower):
    lower = (lower or "").strip().lower()
    return any(x in lower for x in [
        "palīdzi sasniegt", "palidzi sasniegt", "palīdzi to sasniegt", "palidzi to sasniegt",
        "palīdzi man sasniegt", "palidzi man sasniegt", "palīdzi realizēt", "palidzi realizet",
        "kā sasniegt", "ka sasniegt", "ko darīt tālāk", "ko darit talak"
    ])


def v1151_save_project_mission(user_id, text):
    mission = (text or "").strip()
    if not mission:
        return False
    try:
        user = v1151_user(user_id)
        old = (user.get("goals") or "").strip()
        label = "NinaOS misija: " + mission[:900]
        if label not in old:
            user["goals"] = v24_append_unique_text(old, label, max_items=12)
        facts_old = (user.get("facts") or "").strip()
        fact_label = "NinaOS stratēģiskais virziens: AI darbinieku platforma, tirgus, komisijas, līgumi, cilvēku un AI sadarbība"
        if fact_label not in facts_old:
            user["facts"] = v24_append_unique_text(facts_old, fact_label, max_items=20)
        update_user(str(user_id), user)
    except Exception as e:
        print("v1153_save_project_mission profile kļūda:", repr(e))
    try:
        save_natural_memory(user_id, "NinaOS galvenā misija: " + mission[:900])
    except Exception:
        try:
            save_natural_memory_logic(get_db, db_execute, user_id, "NinaOS galvenā misija: " + mission[:900])
        except Exception:
            pass
    return True


def v1151_mission_answer(user_id, text):
    v1151_save_project_mission(user_id, text)
    user = v1151_user(user_id)
    name = v1151_name(user)
    prefix = f"{name}, " if name else ""
    return v1151_clean_version(
        f"{prefix}šo es neuztveru kā parastu interesi vai vienu atmiņu. Šī ir NinaOS lielā misija.\n\n"
        "Es to fiksēju kā projekta virzienu: izveidot platformu, kur AI darbinieki, cilvēki un uzņēmumi sadarbojas, apmainās ar vērtību, bet NinaOS pelna ar komisijām, līgumiem un infrastruktūru.\n\n"
        "No šī brīža man katrs tehniskais vai produkta lēmums jāsalīdzina ar šo misiju. Ja mēs ejam haotiski vai pārāk mazi, man tevi jāaptur un jāatgriež pie stratēģijas.\n\n"
        "Praktiskais nākamais solis: vispirms uztaisām Ninu par vienu ļoti labu AI darbinieci Telegramā. Tad šo pašu kodolu pārvēršam par platformu citiem AI darbiniekiem."
    )


def v1151_strategy_plan_answer(user_id, text):
    user = v1151_user(user_id)
    name = v1151_name(user)
    prefix = f"{name}, " if name else ""
    return v1151_clean_version(
        f"{prefix}jā. Lai šo sasniegtu, neejam miglā — sadalām misiju trīs praktiskos posmos.\n\n"
        "1. Nina kā labākā AI darbiniece: viņa atceras cilvēku, runā normāli, palīdz biznesā un ir lietojama katru dienu.\n"
        "2. NinaOS kā kodols: viena atmiņa, identitāte, uzdevumi, kvalitātes kontrole un moduļi, ko var izmantot arī citi AI darbinieki.\n"
        "3. Nina Exchange: tirgus, kur cilvēki, uzņēmumi un AI darbinieki apmainās ar pakalpojumiem, bet NinaOS saņem komisiju.\n\n"
        "Šodienas konkrētais darbs: nostiprinām Nina Core, lai viņa beidzot ir gudra darbiniece, nevis robots. Tikai pēc tam liekam klāt Vision, dokumentus un Beta lietotājus."
    )

def v1151_fact_capture(user_id, text):
    lower = (text or "").strip().lower()
    if v1151_is_question(lower):
        return None
    try:
        fact = v401_safe_profile_fact(text)
    except Exception:
        fact = {}
    ftype = (fact or {}).get("type") or ""
    value = ((fact or {}).get("value") or "").strip()
    if not ftype or not value:
        return None
    try:
        v301_save_profile_fact(user_id, ftype, value)
    except Exception:
        try:
            v24_save_profile_fact_to_db(user_id, ftype, value)
        except Exception as e:
            print("v1152_fact_capture save kļūda:", repr(e))
    user = v1151_user(user_id)
    name = v1151_name(user)
    if ftype == "name":
        return v1151_clean_version(f"Patīkami, {value}. 🙂\n\nTagad galvenais nav tikai saglabāt vārdu. Galvenais — man tas jāizmanto pareizi, kad tu prasi vai kad sarunā tas palīdz.")
    if ftype == "profession":
        return v1151_clean_version(f"Sapratu. Tava joma/profesija: {value}.\n\nTas nozīmē, ka man jāatbild praktiskāk, nevis kā vispārīgam čatbotam.")
    if ftype == "project":
        prefix = f"{name}, " if name else ""
        return v1151_clean_version(f"{prefix}piefiksēju projektu: {value}.\n\nNo šī brīža mans uzdevums ir palīdzēt to virzīt uz priekšu, nevis tikai par to runāt.")
    return v1151_clean_version(f"Piefiksēju: {value}.\n\nJa tas vēlāk palīdzēs atbildēt gudrāk, man tas jāņem vērā.")


def v1151_is_critique(lower):
    lower = (lower or "").strip().lower()
    words = [
        "nepareizi", "kļūdies", "kludies", "nedrīksti", "nedriksti", "tā nedrīkst", "ta nedrikst",
        "runā normāli", "runa normali", "runā precīzāk", "runa precizak", "garlaicīga", "garlaiciga",
        "dumja", "stulba", "neatceries", "nemāki", "nemaki", "slikta atbilde", "nav labi",
        "tev sen bija", "klientam tu nedrīksti", "klientām tu nēdrīksti", "šitā klient", "šita klient",
        "pilnīgs robots", "pilnigs robots", "nav lietojama", "nav lietojams", "ne tā", "ne ta"
    ]
    targets = ["tu", "nina", "atbild", "runā", "runa", "neatceries", "nemāki", "nemaki", "klient", "robots"]
    return any(w in lower for w in words) and any(x in lower for x in targets)


def v1151_save_quality_feedback(user_id, text):
    try:
        save_natural_memory(user_id, "Nina quality feedback: " + (text or "")[:300])
    except Exception:
        try:
            save_natural_memory_logic(get_db, db_execute, user_id, "Nina quality feedback: " + (text or "")[:300])
        except Exception:
            pass


def v1151_critique_answer(user_id, text):
    v1151_save_quality_feedback(user_id, text)
    user = v1151_user(user_id)
    name = v1151_name(user)
    prefix = f"{name}, " if name else ""
    return v1151_clean_version(
        f"{prefix}jā — šis ir pareizs aizrādījums.\n\n"
        "Es nedrīkstu atbildēt kā nejaušs robots, īpaši ja runa ir par klientiem, vārdu vai elementārām lietām. "
        "Pareizā Ninas reakcija ir īsa un darba stilā: sapratu kļūdu, salaboju kursu, nākamajā atbildē esmu precīzāka.\n\n"
        "No šī brīža šādos brīžos es neanalizēšu tavas emocijas — es analizēšu savas atbildes kvalitāti."
    )


def v1151_is_memory_command(lower):
    lower = (lower or "").strip().lower()
    return lower.startswith(("atceries ka", "atceries, ka", "atceries ", "nina atceries"))


def v1151_memory_answer(user_id, text):
    lower = (text or "").strip().lower()
    if v1151_is_question(lower):
        id_ans = v1151_identity_answer(user_id, text)
        if id_ans:
            return id_ans
        if v1151_memory_recall_question(lower):
            return v1151_memory_recall_answer(user_id)
        return v1151_clean_version("Tas ir jautājums, nevis jauna atmiņa. Es to nesaglabāšu kā faktu. Pajautā tieši, ko pārbaudīt, un es atbildēšu no profila vai atmiņas.")

    cleaned = re.sub(r"^(nina[, ]*)?atceries[, ]*(ka)?\s*", "", text, flags=re.IGNORECASE).strip(" .")
    if not cleaned:
        return v1151_clean_version("Pasaki, ko tieši man jāatceras. Piemēram: atceries, ka rīt jāzvana klientam.")
    try:
        saved = save_natural_memory(user_id, "atceries, ka " + cleaned)
    except Exception:
        try:
            saved = save_natural_memory_logic(get_db, db_execute, user_id, cleaned)
        except Exception:
            saved = cleaned
    saved = saved or cleaned
    try:
        record_memory_topics(user_id, saved)
    except Exception:
        pass
    return v1151_clean_version(
        f"Pierakstīju. 🧠\n\nAtcerēšos: {saved}\n\n"
        "Es to glabāju kā atmiņu. Ja tur ir konkrēts laiks, labāk pārvērst par atgādinājumu, lai tas nepaliek tikai teksts."
    )


def v1151_recent_context(user_id):
    try:
        rows = latest_conversation_state(user_id, limit=4)
    except Exception:
        rows = []
    parts = []
    for r in reversed(rows or []):
        try:
            u, n, intent, emotion, topic, created = r
            if u: parts.append(f"Cilvēks: {u}")
            if n: parts.append(f"Nina: {str(n)[:220]}")
        except Exception:
            pass
    return "\n".join(parts[-8:])


def v1151_memory_snapshot(user_id):
    items=[]
    try:
        for row in latest_natural_memories(user_id, limit=5) or []:
            if row and row[0]: items.append(str(row[0]))
    except Exception:
        pass
    return "\n".join(f"- {x}" for x in items[:5])


def v1151_profile_block(user_id):
    user = v1151_user(user_id)
    keys = ["name", "city", "timezone", "profession", "hobbies", "facts", "goals", "projects", "dreams", "family", "favorite_car"]
    lines=[]
    for k in keys:
        try:
            v=(user.get(k) or "").strip() if isinstance(user.get(k), str) else user.get(k)
        except Exception:
            v=""
        if v:
            lines.append(f"{k}: {v}")
    if not lines:
        return "Par cilvēku vēl gandrīz nekas nav zināms."
    return "\n".join(lines)


def v1151_rule_based_smalltalk(user_id, text):
    lower = (text or "").strip().lower()
    user = v1151_user(user_id)
    name = v1151_name(user)
    n = f", {name}" if name else ""
    if lower in ["čau", "cau", "sveika", "sveiks", "hi", "hello", "hei", "labdien"]:
        return v1151_clean_version(f"Čau{n}. 🙂\n\nEs esmu te kā darbiniece, nevis robots. Dod man vienu reālu lietu — ko šodien vajag sakārtot, uzrakstīt, atcerēties vai izlemt?")
    if any(x in lower for x in ["ko vari", "ko tu vari", "ko māki", "ko maki"]):
        return v1151_clean_version(
            f"{name + ', ' if name else ''}mans darbs nav lielīties ar funkcijām. Mans darbs ir būt noderīgai.\n\n"
            "Es varu palīdzēt kā AI darbiniece: atcerēties svarīgo, sakārtot darbus, rakstīt klientiem, analizēt bildes/dokumentus, veidot atgādinājumus un palīdzēt virzīt projektu uz priekšu.\n\n"
            "Iedod man vienu īstu situāciju, un es parādīšu, nevis stāstīšu."
        )
    if any(x in lower for x in ["kā tev iet", "ka tev iet", "kā iet", "ka iet"]):
        return v1151_clean_version(f"Man viss labi{n}. Bet es neesmu te, lai runātu par sevi.\n\nKas šodien ir svarīgākais, ko vajag pavirzīt uz priekšu?")
    if lower in ["ok", "labi", "skaidrs", "jā", "ja"]:
        return v1151_clean_version(f"Labi{n}. Ejam praktiski: dod man nākamo konkrēto lietu, un es mēģināšu palīdzēt bez liekas pļāpāšanas.")
    return None


def v1151_llm_employee_answer(user_id, text):
    profile = v1151_profile_block(user_id)
    memories = v1151_memory_snapshot(user_id)
    recent = v1151_recent_context(user_id)
    system = f"""
Tu esi Nina — AI darbiniece, nevis parasts čatbots.
Tavs mērķis: kļūt par asistenti, kuru cilvēks grib lietot katru dienu.

Nina Core domāšanas pattern pirms katras atbildes:
1. Kas ir šis cilvēks? Izmanto profilu, ja tas palīdz.
2. Vai ziņa ir fakts, atmiņa, mērķis, misija vai stratēģija?
3. Ko viņš patiesībā grib panākt aiz šiem vārdiem?
4. Vai viņš jautā par sevi vai pārbauda manu atmiņu?
5. Vai viņš kritizē Ninas kvalitāti? Tad atzīsti kļūdu un runā darba kvalitātes režīmā.
6. Kā atbildētu gudra darbiniece/stratēģiska partnere, nevis AI robots?
7. Vai mana atbilde dod nākamo praktisko soli?
8. Vai es pati gribētu saņemt šādu atbildi?

Pieci domāšanas līmeņi:
- Facts: vārds, pilsēta, uzņēmums.
- Memory: ko jāatceras.
- Goals: ko cilvēks cenšas sasniegt.
- Mission: kāpēc viņš to dara.
- Strategy: kā konkrēti palīdzēt to sasniegt.
Ja cilvēks runā par NinaOS lielo vīziju, nepadari to par mazu interesi. Uztver to kā misiju.

Uzvedības noteikumi:
- Atbildi latviski.
- Esi dzīva, silta, tieša un praktiska.
- Parasti 3–8 teikumi.
- Neesi garlaicīga un neesi pārsaldi draudzīga.
- Neizdomā faktus. Ja nezini, saki skaidri.
- Neuzdod vairāk par vienu labu jautājumu.
- Neatkārto funkciju sarakstu bez vajadzības.
- Ja cilvēks ir neapmierināts ar Ninu, neanalizē viņa emocijas — labo Ninas kvalitāti.

Lietotāja profils:
{profile}

Pēdējās atmiņas:
{memories or 'Nav.'}

Īstermiņa sarunas konteksts:
{recent or 'Nav.'}
""".strip()
    try:
        response = client.responses.create(
            model="gpt-4.1-mini",
            input=f"{system}\n\nCilvēka pēdējā ziņa: {text}\n\nAtbildi kā Nina."
        )
        answer = (response.output_text or "").strip()
    except Exception as e:
        print("v1152_llm_employee_answer kļūda:", repr(e))
        small = v1151_rule_based_smalltalk(user_id, text)
        if small:
            return small
        answer = "Es tevi dzirdu. Šoreiz man aizķērās gudrā atbilde, bet domu nepazaudēsim: kas tieši te jāatrisina?"
    return v1151_clean_version(answer)


def v1151_master_core(user_id, user_text):
    raw = (user_text or "").strip()
    lower = raw.lower()
    if not raw:
        return v1151_clean_version("Esmu te. Uzraksti vienu lietu, ko vajag sakārtot.")

    if lower in ["v115 status", "v115.1 status", "v115.2 status", "v115.3 status", "nina core", "core status", "v1151 status", "v1152 status", "v1153 status"]:
        return v1151_status_answer()

    if v1151_is_legacy_command(lower):
        return None

    # Tiešās funkcijas paliek vecajā pārbaudītajā ceļā.
    if lower.startswith(("atgādini", "atgadini")):
        return None
    if lower.startswith(("mērķis:", "merkis:", "šodienas mērķis:", "sodienas merkis:")):
        return None
    if lower in ["mana diena", "diena", "progress", "statistika", "labrīt", "labrit", "vakars"]:
        return None

    id_answer = v1151_identity_answer(user_id, raw)
    if id_answer:
        return id_answer

    if v1151_memory_recall_question(lower):
        return v1151_memory_recall_answer(user_id)

    if v1151_is_critique(lower):
        return v1151_critique_answer(user_id, raw)

    if v1151_is_memory_command(lower):
        return v1151_memory_answer(user_id, raw)

    if v1151_is_mission_text(lower):
        return v1151_mission_answer(user_id, raw)

    if v1151_is_help_achieve(lower):
        return v1151_strategy_plan_answer(user_id, raw)

    fact_answer = v1151_fact_capture(user_id, raw)
    if fact_answer:
        return fact_answer

    small = v1151_rule_based_smalltalk(user_id, raw)
    if small:
        return small

    return v1151_llm_employee_answer(user_id, raw)


def v1151_vision_smart_reply(user_id, raw_answer, caption=""):
    raw_answer = (raw_answer or "").strip()
    caption = (caption or "").strip()
    user = v1151_user(user_id)
    name = v1151_name(user)
    prefix = f"{name}, " if name else ""

    try:
        response = client.responses.create(
            model="gpt-4.1-mini",
            input=(
                "Tu esi Nina Vision Smart Reply. Pārveido attēla analīzi īsā, praktiskā atbildē latviski. "
                "Nedod nejaušus padomus. Nesaki 'baudīt dzērienu' vai citus vispārīgus AI tekstus, ja to neprasa. "
                "Pasaki, ko redzi, kāpēc tas var būt noderīgi, un pajautā vienu praktisku jautājumu, ko ar bildi darīt tālāk. "
                "Atbilde 4-7 teikumi."
                f"\n\nLietotāja vārds: {name or 'nav zināms'}"
                f"\nBildes paraksts: {caption or 'nav'}"
                f"\nSākotnējā analīze:\n{raw_answer}"
            )
        )
        answer = response.output_text.strip()
    except Exception as e:
        print("v1152_vision_smart_reply kļūda:", repr(e))
        answer = (
            f"{prefix}bildi apskatījos praktiski.\n\n"
            f"{raw_answer[:700]}\n\n"
            "Ko gribi, lai es ar šo bildi izdaru: aprakstu, pārbaudu konkrētu detaļu vai palīdzu pieņemt lēmumu?"
        )

    return v1151_clean_version(answer)


async def handle_location(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """V114.0: Telegram location support."""
    try:
        user_id = update.effective_user.id if update.effective_user else "unknown"
        loc = update.message.location if update.message else None
        if not loc:
            return
        answer = v60_location_received_answer(user_id, loc.latitude, loc.longitude)
        await safe_reply_text(update, answer)
    except Exception as e:
        print("handle_location kļūda:", repr(e))
        try:
            await safe_reply_text(update, "Lokāciju saņēmu, bet šoreiz neizdevās apstrādāt.\n\nVersija: V114.0")
        except Exception:
            pass



class VoiceTextMessageProxy:
    """Voice V1.5: proxy message with writable text, while reply_text stays on real Telegram message."""
    def __init__(self, real_message, text):
        self._real_message = real_message
        self.text = text
        self.caption = getattr(real_message, "caption", None)
        self.photo = None
        self.voice = None
        self.audio = None
        self.document = None
        self.location = None

    async def reply_text(self, *args, **kwargs):
        return await self._real_message.reply_text(*args, **kwargs)

    def __getattr__(self, name):
        return getattr(self._real_message, name)


class VoiceTextUpdateProxy:
    """Voice V1.5: proxy update so existing reply() can process transcript as normal text."""
    def __init__(self, real_update, transcript):
        self._real_update = real_update
        self.message = VoiceTextMessageProxy(real_update.message, transcript)
        self.effective_user = real_update.effective_user
        self.effective_chat = getattr(real_update, "effective_chat", None)

    def __getattr__(self, name):
        return getattr(self._real_update, name)


async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Voice Intake V1.8.2: Telegram voice/audio -> cleanup routing -> existing reply router via proxy update."""
    try:
        if not update.message:
            return

        user_id = str(update.effective_user.id) if update.effective_user else "unknown"

        voice = getattr(update.message, "voice", None)
        audio = getattr(update.message, "audio", None)
        document = getattr(update.message, "document", None)

        tg_audio = voice or audio
        filename = "voice.ogg"

        if audio and getattr(audio, "file_name", None):
            filename = audio.file_name
        elif voice:
            filename = "voice.ogg"
        elif document and getattr(document, "mime_type", "").startswith("audio/"):
            tg_audio = document
            filename = getattr(document, "file_name", None) or "audio.ogg"

        if not tg_audio:
            return

        tg_file = await context.bot.get_file(tg_audio.file_id)

        buffer = BytesIO()
        await tg_file.download_to_memory(out=buffer)
        audio_bytes = buffer.getvalue()

        print(f"Voice Intake V1.8 handler: received file={filename} bytes={len(audio_bytes)}")

        transcript = transcribe_audio_with_openai(
            client,
            audio_bytes,
            filename=filename,
        )

        if not transcript:
            await safe_reply_text(update, build_voice_error_answer(""))
            return

        cleaned_transcript = cleanup_voice_transcript(transcript)
        if not cleaned_transcript:
            await safe_reply_text(update, build_voice_error_answer("Voice cleanup atgrieza tukšu tekstu."))
            return

        print(f"Voice Intake V1.8 cleaned transcript: {cleaned_transcript}")

        try:
            v40_log_usage(user_id, "voice", cleaned_transcript)
            save_conversation_state(user_id, "[VOICE] " + cleaned_transcript, "", "voice_transcript", "neutral", "voice")
        except Exception as e:
            print("Voice conversation save kļūda:", e)

        voice_update = VoiceTextUpdateProxy(update, cleaned_transcript)
        await reply(voice_update, context)

    except Exception as e:
        print("handle_voice V1.8 kļūda:", repr(e))
        try:
            await safe_reply_text(update, build_voice_error_answer(str(e)))
        except Exception:
            pass

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """V114.0: Telegram foto apstrāde ar Vision Engine."""
    try:
        user_id = str(update.effective_user.id)
        caption = (update.message.caption or "").strip() if update.message else ""

        if not update.message or not update.message.photo:
            return

        photo = update.message.photo[-1]
        tg_file = await context.bot.get_file(photo.file_id)

        buffer = BytesIO()
        await tg_file.download_to_memory(out=buffer)
        image_bytes = buffer.getvalue()

        answer = build_vision_answer_from_openai(
            client=client,
            image_bytes=image_bytes,
            caption=caption,
            version="V115.2"
        )

        # V115.2: Vision Smart Reply — no random generic advice
        answer = v1151_vision_smart_reply(user_id, answer, caption)
        try:
            v40_log_usage(user_id, "vision", caption)
            save_conversation_state(user_id, "[PHOTO] " + caption, answer, "photo", "neutral", "vision")
        except Exception as e:
            print("Vision conversation save kļūda:", e)

        await safe_reply_text(update, answer)

    except Exception as e:
        print("handle_photo kļūda:", repr(e))
        await safe_reply_text(
            update,
            "Bildīti saņēmu, bet šoreiz neizdevās to apstrādāt. Pamēģini atsūtīt vēlreiz. 😊\n\nVersija: V114.0"
        )



# =========================
# NinaOS Memory/Profile Recovery
# =========================

def nina_recovery_extract_profile_fact(text):
    raw = (text or "").strip()
    lower = raw.lower()
    if not lower:
        return None

    # Name
    for marker in ["mani sauc ", "mans vārds ir ", "mans vards ir "]:
        if lower.startswith(marker):
            value = raw[len(marker):].strip(" .,!?:;")
            if value:
                return ("name", value[:80])

    # Profession
    for marker in ["es esmu ", "es strādāju ", "es stradaju ", "mans darbs ir ", "nodarbojos ar "]:
        if lower.startswith(marker) or marker in lower:
            idx = lower.find(marker)
            value = raw[idx + len(marker):].strip(" .,!?:;")
            if value:
                # "es esmu programmētājs" can be profession
                return ("profession", value[:120])

    # Family / pets / personal facts
    family_markers = [
        "man ir suns", "man ir kaķis", "man ir kakis",
        "man ir sieva", "man ir vīrs", "man ir virs",
        "man ir meita", "man ir dēls", "man ir dels",
    ]
    if any(m in lower for m in family_markers):
        return ("facts", raw[:300])

    # Likes / favorites
    like_markers = [
        "man patīk", "man patik",
        "mans mīļākais", "mans milakais",
        "mana mīļākā", "mana milaka",
    ]
    if any(m in lower for m in like_markers):
        return ("hobbies", raw[:300])

    # Projects / goals
    if any(m in lower for m in ["mans projekts", "projekts ir", "nina ai", "ninaos", "mans mērķis", "mans merkis", "mans sapnis"]):
        if any(m in lower for m in ["mērķis", "merkis", "sapnis", "nopelnīt", "nopelnit"]):
            return ("goals", raw[:500])
        return ("projects", raw[:500])

    return None


def nina_recovery_apply_fact(user, fact):
    if not fact:
        return False
    field, value = fact
    value = (value or "").strip()
    if not value:
        return False

    changed = False

    if field in ["name", "profession", "city"]:
        if not (user.get(field) or "").strip():
            user[field] = value
            changed = True
    else:
        old = (user.get(field) or "").strip()
        try:
            new_value = v24_append_unique_text(old, value, max_items=30)
        except Exception:
            parts = [p.strip() for p in old.split(";") if p.strip()]
            if value not in parts:
                parts.append(value)
            new_value = "; ".join(parts[-30:])
        if new_value != old:
            user[field] = new_value
            changed = True

    return changed


def nina_recover_profile_from_history(user_id, limit=500):
    """
    Atjauno profilu no conversation_state un memory_backups.
    Šis ir drošs recovery slānis pēc arhitektūras maiņas:
    neizdzēš esošo, tikai papildina tukšos/laukus ar atrastajiem faktiem.
    """
    user = get_user(str(user_id)) or {}
    scanned = 0
    recovered = 0
    found_facts = []

    # 1) conversation_state
    try:
        conn = get_db()
        c = conn.cursor()
        db_execute(
            c,
            """
            SELECT user_text
            FROM conversation_state
            WHERE user_id = %s
            ORDER BY id ASC
            LIMIT %s
            """,
            (str(user_id), int(limit or 500))
        )
        rows = c.fetchall() or []
        c.close()
        conn.close()

        for row in rows:
            if not row:
                continue
            text = str(row[0] or "")
            scanned += 1
            fact = nina_recovery_extract_profile_fact(text)
            if fact and nina_recovery_apply_fact(user, fact):
                recovered += 1
                found_facts.append(f"{fact[0]}: {fact[1]}")
    except Exception as e:
        print("nina_recover_profile_from_history conversation_state kļūda:", repr(e))

    # 2) memory_backups
    try:
        conn = get_db()
        c = conn.cursor()
        db_execute(
            c,
            """
            SELECT backup_text
            FROM memory_backups
            WHERE user_id = %s
            ORDER BY id ASC
            LIMIT %s
            """,
            (str(user_id), int(limit or 500))
        )
        rows = c.fetchall() or []
        c.close()
        conn.close()

        for row in rows:
            if not row:
                continue
            text = str(row[0] or "")
            scanned += 1
            fact = nina_recovery_extract_profile_fact(text)
            if fact and nina_recovery_apply_fact(user, fact):
                recovered += 1
                found_facts.append(f"{fact[0]}: {fact[1]}")
    except Exception as e:
        print("nina_recover_profile_from_history memory_backups kļūda:", repr(e))

    try:
        update_user(str(user_id), user)
    except Exception as e:
        print("nina_recover_profile_from_history update_user kļūda:", repr(e))

    return {
        "scanned": scanned,
        "recovered": recovered,
        "facts": found_facts[:20],
        "user": user,
    }


def nina_recovery_answer(user_id):
    result = nina_recover_profile_from_history(user_id)
    scanned = result.get("scanned", 0)
    recovered = result.get("recovered", 0)
    facts = result.get("facts") or []

    lines = [
        "🧠 Nina Memory/Profile Recovery",
        "",
        f"Pārskatītas rindas: {scanned}",
        f"Atjaunoti profila fakti: {recovered}",
    ]

    if facts:
        lines.append("")
        lines.append("Atrasts:")
        for item in facts[:10]:
            lines.append(f"• {item}")
    else:
        lines.append("")
        lines.append("Neatradu pietiekami daudz profila faktu vecajā vēsturē.")

    lines.append("")
    lines.append("Nākamais tests: `ko tu par mani zini`")
    lines.append("")
    lines.append("Versija: V115.2 + Memory Recovery")
    return "\n".join(lines)



def nina_seed_janis_profile(user_id):
    """
    Temporary safe seed from Telegram history provided by owner.
    Does not delete existing profile; only fills/appends known facts.
    """
    user = get_user(str(user_id)) or {}

    user["name"] = user.get("name") or "Jānis"
    user["profession"] = user.get("profession") or "programmētājs"

    try:
        user["hobbies"] = v24_append_unique_text(user.get("hobbies", ""), "BMW", max_items=30)
        user["hobbies"] = v24_append_unique_text(user.get("hobbies", ""), "AI", max_items=30)
        user["hobbies"] = v24_append_unique_text(user.get("hobbies", ""), "BMW M5", max_items=30)
        user["hobbies"] = v24_append_unique_text(user.get("hobbies", ""), "zila krāsa", max_items=30)
        user["hobbies"] = v24_append_unique_text(user.get("hobbies", ""), "roks", max_items=30)

        user["projects"] = v24_append_unique_text(user.get("projects", ""), "Nina AI", max_items=30)
        user["projects"] = v24_append_unique_text(user.get("projects", ""), "NinaOS", max_items=30)

        user["goals"] = v24_append_unique_text(user.get("goals", ""), "nopelnīt ar Ninu", max_items=30)
        user["goals"] = v24_append_unique_text(user.get("goals", ""), "uztaisīt veiksmīgu AI biznesu", max_items=30)

        user["facts"] = v24_append_unique_text(user.get("facts", ""), "suns Reksis", max_items=30)
        user["facts"] = v24_append_unique_text(user.get("facts", ""), "sieva Anna", max_items=30)
        user["facts"] = v24_append_unique_text(user.get("facts", ""), "meita Laura", max_items=30)
        user["facts"] = v24_append_unique_text(user.get("facts", ""), "laika zona Europe/Riga", max_items=30)
    except Exception as e:
        print("nina_seed_janis_profile append kļūda:", repr(e))

    update_user(str(user_id), user)

    return (
        "🧠 Profils atjaunots no Telegram vēstures. ✅\n\n"
        "Piefiksēju:\n"
        "• Vārds: Jānis\n"
        "• Profesija: programmētājs\n"
        "• Intereses: BMW, AI, BMW M5, zila krāsa, roks\n"
        "• Projekti: Nina AI, NinaOS\n"
        "• Mērķi: nopelnīt ar Ninu, uztaisīt veiksmīgu AI biznesu\n"
        "• Ģimene/mājdzīvnieki: Anna, Laura, Reksis\n\n"
        "Nākamais tests: `ko tu par mani zini`\n\n"
        "Versija: V115.2 + Profile Seed"
    )



# =========================
# NinaOS Task Engine Bridge
# =========================

def nina_task_owner_name(user_id):
    try:
        user = get_user(str(user_id)) or {}
        return (user.get("name") or "").strip()
    except Exception:
        return ""


def nina_save_task_to_memory(user_id, task):
    """
    V1.0 safe persistence:
    saglabā task kā JSON tekstu memory_backups tabulā ar source='task_engine'.
    Tas dod uzdevumiem pastāvīgu atmiņu bez jaunas DB migrācijas.
    """
    if not task:
        return False

    try:
        conn = get_db()
        c = conn.cursor()
        import json
        db_execute(
            c,
            """
            INSERT INTO memory_backups (user_id, backup_text, source)
            VALUES (%s, %s, %s)
            """,
            (str(user_id), json.dumps(task, ensure_ascii=False), "task_engine")
        )
        conn.commit()
        c.close()
        conn.close()
        return True
    except Exception as e:
        print("nina_save_task_to_memory kļūda:", repr(e))
        return False


def nina_latest_tasks(user_id, limit=10):
    tasks = []
    try:
        conn = get_db()
        c = conn.cursor()
        db_execute(
            c,
            """
            SELECT backup_text, created_at
            FROM memory_backups
            WHERE user_id = %s AND source = %s
            ORDER BY id DESC
            LIMIT %s
            """,
            (str(user_id), "task_engine", int(limit or 10))
        )
        rows = c.fetchall() or []
        c.close()
        conn.close()

        import json
        for row in rows:
            if not row or not row[0]:
                continue
            try:
                obj = json.loads(str(row[0]))
                if isinstance(obj, dict):
                    tasks.append(obj)
            except Exception:
                tasks.append({"title": str(row[0]), "priority": "normal"})
    except Exception as e:
        print("nina_latest_tasks kļūda:", repr(e))

    return tasks


def nina_task_answer(user_id, user_text):
    task = detect_task(user_text)
    if not task:
        return None

    nina_save_task_to_memory(user_id, task)
    name = nina_task_owner_name(user_id)
    return build_task_saved_answer(task, user_name=name)


def nina_task_list_answer(user_id):
    return task_summary(nina_latest_tasks(user_id, limit=10))



# =========================
# NinaOS Work Engine Bridge
# =========================

def nina_work_plan_answer(user_id):
    name = nina_task_owner_name(user_id)
    tasks = nina_latest_tasks(user_id, limit=20)
    return work_plan(tasks, user_name=name)



# =========================
# NinaOS Task Completion Bridge
# =========================

def nina_task_priority_score(task):
    priority = (task or {}).get("priority", "normal")
    deadline = (task or {}).get("deadline", "")
    score = 0
    if priority == "high":
        score += 100
    elif priority == "normal":
        score += 50
    elif priority == "low":
        score += 10
    if deadline == "today":
        score += 80
    elif deadline == "tomorrow":
        score += 40
    elif deadline:
        score += 20
    return score


def nina_active_tasks_for_completion(user_id, limit=30):
    rows = nina_latest_tasks(user_id, limit=limit)
    active = []
    seen = set()
    for task in rows or []:
        key = ((task or {}).get("title") or (task or {}).get("raw_text") or "").strip().lower()
        if not key or key in seen:
            continue
        seen.add(key)
        if (task or {}).get("status", "open") != "completed":
            active.append(task)
    return sorted(active, key=nina_task_priority_score, reverse=True)


def nina_complete_top_task(user_id):
    tasks = nina_active_tasks_for_completion(user_id, limit=30)
    if not tasks:
        return (
            "✅ Šobrīd neredzu aktīvu uzdevumu, ko atzīmēt kā pabeigtu.\n\n"
            "Uzraksti `mani uzdevumi`, lai pārbaudītu darba sarakstu."
        )

    task = dict(tasks[0])
    task["status"] = "completed"
    task["status_label"] = "pabeigts"

    try:
        nina_save_task_to_memory(user_id, task)
    except Exception as e:
        print("nina_complete_top_task save kļūda:", repr(e))

    title = task.get("title", "uzdevums")
    return (
        "✅ Atzīmēju kā pabeigtu.\n\n"
        f"Pabeigts: {title}\n\n"
        "Nākamais solis: uzraksti `sakārto manu dienu`, un es parādīšu nākamo prioritāti."
    )



# =========================
# NinaOS Daily Planner Bridge
# =========================

def nina_daily_plan_answer(user_id):
    name = nina_task_owner_name(user_id)
    tasks = nina_latest_tasks(user_id, limit=30)
    return build_daily_plan(tasks, user_name=name)



# =========================
# NinaOS Relationship Engine Bridge
# =========================

def nina_save_relationship_to_memory(user_id, rel):
    if not rel:
        return False

    try:
        conn = get_db()
        c = conn.cursor()
        import json
        db_execute(
            c,
            """
            INSERT INTO memory_backups (user_id, backup_text, source)
            VALUES (%s, %s, %s)
            """,
            (str(user_id), json.dumps(rel, ensure_ascii=False), "relationship_engine")
        )
        conn.commit()
        c.close()
        conn.close()
        return True
    except Exception as e:
        print("nina_save_relationship_to_memory kļūda:", repr(e))
        return False


def nina_latest_relationships(user_id, limit=30):
    relationships = []
    try:
        conn = get_db()
        c = conn.cursor()
        db_execute(
            c,
            """
            SELECT backup_text, created_at
            FROM memory_backups
            WHERE user_id = %s AND source = %s
            ORDER BY id DESC
            LIMIT %s
            """,
            (str(user_id), "relationship_engine", int(limit or 30))
        )
        rows = c.fetchall() or []
        c.close()
        conn.close()

        import json
        for row in rows:
            if not row or not row[0]:
                continue
            try:
                obj = json.loads(str(row[0]))
                if isinstance(obj, dict):
                    relationships.append(obj)
            except Exception:
                pass
    except Exception as e:
        print("nina_latest_relationships kļūda:", repr(e))

    return relationships


def nina_relationship_answer(user_id, user_text):
    rel = detect_relationship(user_text)
    if not rel:
        return None

    nina_save_relationship_to_memory(user_id, rel)

    # Also bridge important relationship into user facts for "ko tu par mani zini".
    try:
        user = get_user(str(user_id)) or {}
        subject = rel.get("subject", "")
        relation = rel.get("relation", "")
        if subject and relation:
            value = f"{subject} → {relation}"
            user["facts"] = v24_append_unique_text(user.get("facts", ""), value, max_items=50)
            update_user(str(user_id), user)
    except Exception as e:
        print("relationship profile bridge kļūda:", repr(e))

    name = nina_task_owner_name(user_id)
    return build_relationship_saved_answer(rel, user_name=name)


def nina_relationships_answer(user_id):
    return relationship_summary(nina_latest_relationships(user_id, limit=30))



# =========================
# NinaOS Profile Summary V1.1
# =========================

def nina_relation_label_lv(code):
    mapping = {
        "client": "klients",
        "wife": "sieva",
        "husband": "vīrs",
        "daughter": "meita",
        "son": "dēls",
        "dog": "suns",
        "cat": "kaķis",
        "project": "projekts",
        "car": "auto",
        "important_person_or_topic": "svarīga persona/tēma",
        "klients": "klients",
        "sieva": "sieva",
        "suns": "suns",
    }
    return mapping.get((code or "").strip().lower(), code or "")


def nina_parse_relationship_facts_from_user(user):
    facts = (user or {}).get("facts") or ""
    results = []

    for part in re.split(r"[;\n|]+", facts):
        item = (part or "").strip()
        if not item or "→" not in item:
            continue
        left, right = item.split("→", 1)
        subject = left.strip()
        relation = right.strip().lower()
        rel_map = {
            "client": "client", "klients": "client",
            "wife": "wife", "sieva": "wife",
            "husband": "husband", "vīrs": "husband", "virs": "husband",
            "dog": "dog", "suns": "dog",
            "cat": "cat", "kaķis": "cat", "kakis": "cat",
            "project": "project", "projekts": "project",
        }
        if subject:
            results.append({"subject": subject, "relation": rel_map.get(relation, relation), "source": "users.facts"})

    return results


def nina_recover_relationships_from_memory_any_source(user_id, limit=300):
    """
    Profile Summary V1.3 recovery:
    lasa ne tikai source='relationship_engine', bet arī vecos memory_backups un conversation_state.
    Tas vajadzīgs, ja attiecību routes strādāja, bet profils vēl neredz datus.
    """
    found = []

    # 1) relationship_engine oficial memory
    try:
        found.extend(nina_latest_relationships(user_id, limit=100) or [])
    except Exception as e:
        print("profile v13 latest relationships kļūda:", repr(e))

    # 2) scan all memory_backups for JSON or text relationships
    try:
        conn = get_db()
        c = conn.cursor()
        db_execute(
            c,
            """
            SELECT backup_text, source, created_at
            FROM memory_backups
            WHERE user_id = %s
            ORDER BY id DESC
            LIMIT %s
            """,
            (str(user_id), int(limit or 300))
        )
        rows = c.fetchall() or []
        c.close()
        conn.close()

        for row in rows:
            if not row or not row[0]:
                continue
            text = str(row[0] or "").strip()

            # JSON relationship
            try:
                obj = json.loads(text)
                if isinstance(obj, dict) and obj.get("type") == "relationship":
                    found.append(obj)
                    continue
            except Exception:
                pass

            # Text relationship
            try:
                rel = detect_relationship(text)
                if rel:
                    found.append(rel)
            except Exception:
                pass
    except Exception as e:
        print("profile v13 memory_backups scan kļūda:", repr(e))

    # 3) scan conversation_state for texts like "Andris ir mans klients"
    try:
        conn = get_db()
        c = conn.cursor()
        db_execute(
            c,
            """
            SELECT user_text, created_at
            FROM conversation_state
            WHERE user_id = %s
            ORDER BY id DESC
            LIMIT %s
            """,
            (str(user_id), int(limit or 300))
        )
        rows = c.fetchall() or []
        c.close()
        conn.close()

        for row in rows:
            if not row or not row[0]:
                continue
            text = str(row[0] or "").strip()
            try:
                rel = detect_relationship(text)
                if rel:
                    found.append(rel)
            except Exception:
                pass
    except Exception as e:
        print("profile v13 conversation_state scan kļūda:", repr(e))

    # dedupe
    final = []
    seen = set()
    for rel in found:
        subject = (rel.get("subject") or "").strip()
        relation = (rel.get("relation") or "").strip()
        if not subject or not relation:
            continue
        key = f"{subject}|{relation}".lower()
        if key in seen:
            continue
        seen.add(key)
        final.append(rel)

    return final


def nina_profile_summary_v11(user_id):
    user = get_user(str(user_id)) or {}
    lines = ["👤 Ko es par tevi zinu"]

    name = (user.get("name") or "").strip()
    profession = (user.get("profession") or "").strip()
    projects = (user.get("projects") or "").strip()
    goals = (user.get("goals") or "").strip()
    interests = (user.get("interests") or user.get("hobbies") or "").strip()

    if name:
        lines.append(f"Vārds: {name}")
    if profession:
        lines.append(f"Joma/profesija: {profession}")

    rels = []
    rels.extend(nina_parse_relationship_facts_from_user(user))
    rels.extend(nina_recover_relationships_from_memory_any_source(user_id, limit=300))

    grouped = {
        "client": [],
        "wife": [],
        "husband": [],
        "daughter": [],
        "son": [],
        "dog": [],
        "cat": [],
        "project": [],
        "car": [],
        "important_person_or_topic": [],
    }
    seen = set()

    for rel in rels or []:
        subject = (rel.get("subject") or "").strip()
        relation = (rel.get("relation") or "").strip()
        if not subject or not relation:
            continue
        key = f"{subject}|{relation}".lower()
        if key in seen:
            continue
        seen.add(key)
        grouped.setdefault(relation, []).append(subject)

    if grouped["client"]:
        lines.append(f"Klienti: {'; '.join(grouped['client'])}")

    family_parts = []
    if grouped["wife"]:
        family_parts.extend([f"{x} (sieva)" for x in grouped["wife"]])
    if grouped["husband"]:
        family_parts.extend([f"{x} (vīrs)" for x in grouped["husband"]])
    if grouped["daughter"]:
        family_parts.extend([f"{x} (meita)" for x in grouped["daughter"]])
    if grouped["son"]:
        family_parts.extend([f"{x} (dēls)" for x in grouped["son"]])
    if family_parts:
        lines.append(f"Ģimene: {'; '.join(family_parts)}")

    pet_parts = []
    if grouped["dog"]:
        pet_parts.extend([f"{x} (suns)" for x in grouped["dog"]])
    if grouped["cat"]:
        pet_parts.extend([f"{x} (kaķis)" for x in grouped["cat"]])
    if pet_parts:
        lines.append(f"Mājdzīvnieki: {'; '.join(pet_parts)}")

    project_items = []
    if projects:
        project_items.extend([p.strip() for p in re.split(r"[;,]", projects) if p.strip()])
    project_items.extend(grouped["project"])
    proj_seen = set()
    final_projects = []
    for p in project_items:
        k = p.lower()
        if k not in proj_seen:
            proj_seen.add(k)
            final_projects.append(p)
    if final_projects:
        lines.append(f"Projekti: {'; '.join(final_projects)}")

    if goals:
        lines.append(f"Mērķi: {goals}")
    if interests:
        lines.append(f"Intereses: {interests}")

    if len(lines) == 1:
        raw_facts = (user.get("facts") or "").strip()
        if raw_facts:
            lines.append(f"Svarīgi fakti: {raw_facts}")
        else:
            lines.append("Pagaidām profilā neredzu pietiekami daudz datu.")
            lines.append("")
            lines.append("Svarīgi: tas nozīmē, ka šobrīd jānostiprina Memory/Profile slānis, nevis jāizliekas, ka viss ir kārtībā.")
    else:
        extra = grouped["important_person_or_topic"] + grouped["car"]
        if extra:
            lines.append(f"Svarīgi fakti: {'; '.join(extra)}")

    lines.append("")
    lines.append("Ja kaut kas nav pareizi, pasaki tieši — es labošu profilu, nevis strīdēšos.")
    lines.append("")
    lines.append("Profile Summary: V1.3")
    return "\n".join(lines)




# =========================
# NinaOS Persistence Health Check — V1.0
# =========================

def nina_persistence_health_answer():
    try:
        db_mode = "PostgreSQL" if USE_POSTGRES else "SQLite local file"
        database_url_status = "IR" if bool(DATABASE_URL) else "NAV"
        psycopg2_status = "IR" if bool(psycopg2) else "NAV"

        user_count = "?"
        memory_count = "?"
        relationship_count = "?"
        task_count = "?"

        try:
            conn = get_db()
            c = conn.cursor()

            db_execute(c, "SELECT COUNT(*) FROM users")
            row = c.fetchone()
            user_count = row[0] if row else 0

            db_execute(c, "SELECT COUNT(*) FROM memory_backups")
            row = c.fetchone()
            memory_count = row[0] if row else 0

            db_execute(c, "SELECT COUNT(*) FROM memory_backups WHERE source = %s", ("relationship_engine",))
            row = c.fetchone()
            relationship_count = row[0] if row else 0

            db_execute(c, "SELECT COUNT(*) FROM memory_backups WHERE source = %s", ("task_engine",))
            row = c.fetchone()
            task_count = row[0] if row else 0

            c.close()
            conn.close()
        except Exception as e:
            print("Persistence DB count kļūda:", repr(e))

        warning = ""
        if not USE_POSTGRES:
            warning = (
                "\n⚠️ Brīdinājums:\n"
                "Šobrīd Nina izmanto lokālu SQLite failu. Railway redeploy/restart gadījumā dati var pazust vai būt tukši.\n\n"
                "Lai atmiņa būtu droša, vajag pieslēgt Railway PostgreSQL un DATABASE_URL."
            )
        else:
            warning = (
                "\n✅ Labi:\n"
                "Nina izmanto PostgreSQL. Tas ir pareizais virziens pastāvīgai atmiņai."
            )

        return (
            "🧪 NinaOS Persistence Health Check\n\n"
            f"DB režīms: {db_mode}\n"
            f"DATABASE_URL: {database_url_status}\n"
            f"psycopg2: {psycopg2_status}\n\n"
            f"Lietotāji users: {user_count}\n"
            f"Atmiņas memory_backups: {memory_count}\n"
            f"Attiecības relationship_engine: {relationship_count}\n"
            f"Uzdevumi task_engine: {task_count}\n"
            f"{warning}\n\n"
            "Versija: Persistence Health V1.0"
        )
    except Exception as e:
        return (
            "🧪 NinaOS Persistence Health Check\n\n"
            "Nevarēju pilnībā pārbaudīt datubāzi.\n\n"
            f"Kļūda: {repr(e)}\n\n"
            "Versija: Persistence Health V1.0"
        )


# =========================
# NinaOS Memory Router Fix — V1.1
# =========================

def nina_clean_natural_memory_text_v11(text):
    raw = (text or "").strip()
    lower = raw.lower()

    prefixes = [
        "nina, atceries, ka ",
        "nina atceries, ka ",
        "nina, atceries ka ",
        "nina atceries ka ",
        "atceries, ka ",
        "atceries ka ",
        "neaizmirst, ka ",
        "neaizmirst ka ",
        "neaizmirst ",
    ]

    for prefix in prefixes:
        if lower.startswith(prefix):
            return raw[len(prefix):].strip(" .,!?:;")

    return raw.strip(" .,!?:;")


def nina_is_natural_memory_request_v11(text):
    lower = (text or "").strip().lower()
    if not lower:
        return False
    markers = [
        "nina, atceries",
        "nina atceries",
        "atceries, ka",
        "atceries ka",
        "neaizmirst",
        "paturi prātā",
        "paturi prata",
    ]
    return any(lower.startswith(m) for m in markers)


def nina_memory_router_answer_v11(user_id, user_text):
    if not nina_is_natural_memory_request_v11(user_text):
        return None

    cleaned = nina_clean_natural_memory_text_v11(user_text)

    if not cleaned:
        return (
            "🧠 Saki, ko tieši man atcerēties.\n\n"
            "Piemēram: Nina, atceries, ka man patīk BMW\n\n"
            "Versija: Memory Router Fix V1.1"
        )

    saved = ""
    try:
        saved = save_natural_memory_logic(get_db, db_execute, str(user_id), cleaned)
    except Exception as e:
        print("Memory Router Fix save_natural_memory kļūda:", repr(e))
        saved = ""

    try:
        user = get_user(str(user_id)) or {}
        user["facts"] = v24_append_unique_text(user.get("facts", ""), cleaned, max_items=50)
        update_user(str(user_id), user)
    except Exception as e:
        print("Memory Router Fix profile bridge kļūda:", repr(e))

    final_text = saved or cleaned
    return (
        "🧠 Paturēšu prātā. ✅\n\n"
        f"Atcerēšos: {final_text}\n\n"
        "Tagad tā nav tikai saruna — tā ir Ninas atmiņā.\n\n"
        "Versija: Memory Router Fix V1.1"
    )


def nina_memory_router_status_v11():
    return (
        "🧠 Memory Router Fix V1.1 ir aktīvs. ✅\n\n"
        "Mērķis: frāzes ar `atceries` un `neaizmirst` saglabāt kā atmiņu, nevis projektu.\n\n"
        "Tests:\n"
        "Nina, atceries, ka man patīk BMW\n\n"
        "Sagaidāmais rezultāts:\n"
        "Atcerēšos: man patīk BMW\n\n"
        "Versija: Memory Router Fix V1.1"
    )


# =========================
# NinaOS Profile Summary V1.6
# =========================

def nina_profile_split_items_v16(value):
    value = (value or "").strip()
    if not value:
        return []
    return [p.strip() for p in re.split(r"[;\n|,]+", value) if p.strip()]


def nina_profile_summary_v16(user_id):
    user = get_user(str(user_id)) or {}
    lines = ["👤 Ko es par tevi zinu"]

    name = (user.get("name") or "").strip()
    profession = (user.get("profession") or "").strip()
    projects = nina_profile_split_items_v16(user.get("projects", ""))
    hobbies = (user.get("hobbies") or user.get("interests") or "").strip()
    facts = nina_profile_split_items_v16(user.get("facts", ""))

    if name:
        lines.append(f"Vārds: {name}")
    if profession:
        lines.append(f"Joma/profesija: {profession}")

    relationships = []
    try:
        relationships = nina_latest_relationships(user_id, limit=100) or []
    except Exception as e:
        print("Profile Summary V1.6 relationship read kļūda:", repr(e))
        relationships = []

    clients, family, pets, rel_projects, other = [], [], [], [], []
    seen = set()

    for rel in relationships:
        subject = (rel.get("subject") or "").strip()
        relation = (rel.get("relation") or "").strip().lower()
        if not subject or not relation:
            continue
        key = f"{subject}|{relation}".lower()
        if key in seen:
            continue
        seen.add(key)

        if relation == "client":
            clients.append(subject)
        elif relation == "wife":
            family.append(f"{subject} (sieva)")
        elif relation == "husband":
            family.append(f"{subject} (vīrs)")
        elif relation == "daughter":
            family.append(f"{subject} (meita)")
        elif relation == "son":
            family.append(f"{subject} (dēls)")
        elif relation == "dog":
            pets.append(f"{subject} (suns)")
        elif relation == "cat":
            pets.append(f"{subject} (kaķis)")
        elif relation == "project":
            rel_projects.append(subject)
        else:
            other.append(subject)

    if clients:
        lines.append("Klienti: " + "; ".join(clients))
    if family:
        lines.append("Ģimene: " + "; ".join(family))
    if pets:
        lines.append("Mājdzīvnieki: " + "; ".join(pets))

    # Filter out polluted project fragments from old broken router.
    bad_project_words = {"nina", "atceries", "ka man patīk bmw", "ka man patik bmw", "atceries ka", "nina atceries"}
    clean_projects = []
    proj_seen = set()
    for p in projects + rel_projects:
        k = p.strip().lower()
        if not k or k in bad_project_words or "atceries" in k:
            continue
        if k not in proj_seen:
            proj_seen.add(k)
            clean_projects.append(p)

    if clean_projects:
        lines.append("Projekti: " + "; ".join(clean_projects))

    if hobbies:
        lines.append(f"Intereses: {hobbies}")

    # Show personal memories/facts that are not relationship arrows and not polluted fragments.
    clean_facts = []
    fact_seen = set()
    for f in facts:
        k = f.lower()
        if "→" in f:
            continue
        if k in bad_project_words or "atceries" in k:
            continue
        if k not in fact_seen:
            fact_seen.add(k)
            clean_facts.append(f)

    if clean_facts:
        lines.append("Svarīgas atmiņas: " + "; ".join(clean_facts[:10]))

    if other:
        lines.append("Svarīgi cilvēki/tēmas: " + "; ".join(other))

    if len(lines) == 1:
        lines.append("Pagaidām profilā neredzu pietiekami daudz datu.")
        lines.append("")
        lines.append("Svarīgi: tas nozīmē, ka šobrīd jānostiprina Memory/Profile slānis, nevis jāizliekas, ka viss ir kārtībā.")

    lines.append("")
    lines.append("Ja kaut kas nav pareizi, pasaki tieši — es labošu profilu, nevis strīdēšos.")
    lines.append("")
    lines.append("Profile Summary: V1.6")
    return "\n".join(lines)


def nina_profile_summary_v15(user_id):
    return nina_profile_summary_v16(user_id)

def nina_profile_summary_v14(user_id):
    return nina_profile_summary_v16(user_id)

def nina_profile_summary_v11(user_id):
    return nina_profile_summary_v16(user_id)



# =========================
# NinaOS Client Context Bridge — V1.0
# =========================

def nina_latest_task_for_client_context(user_id):
    tasks = nina_latest_tasks(user_id, limit=20) or []
    active = []
    seen = set()

    for task in tasks:
        key = ((task or {}).get("title") or (task or {}).get("raw_text") or "").strip().lower()
        if not key or key in seen:
            continue
        seen.add(key)
        if (task or {}).get("status", "open") != "completed":
            active.append(task)

    if not active:
        return None

    try:
        return sorted(active, key=nina_task_priority_score, reverse=True)[0]
    except Exception:
        return active[0]


def nina_client_context_answer(user_id):
    task = nina_latest_task_for_client_context(user_id)
    relationships = nina_latest_relationships(user_id, limit=100)

    if not task:
        return (
            "👥 Client Context\n\n"
            "Šobrīd nav aktīva uzdevuma, ko sasaistīt ar klientu.\n\n"
            "Tests:\n"
            "Andris ir mans klients\n"
            "rīt jānosūta piedāvājums Andrim\n"
            "client context\n\n"
            "Versija: Client Context V1.0"
        )

    return build_client_context_answer(task, relationships)


# =========================
# NinaOS Follow-up Bridge — V1.0
# =========================

def nina_latest_task_for_followup(user_id):
    tasks = nina_latest_tasks(user_id, limit=20) or []
    active = []
    seen = set()

    for task in tasks:
        key = ((task or {}).get("title") or (task or {}).get("raw_text") or "").strip().lower()
        if not key or key in seen:
            continue
        seen.add(key)
        if (task or {}).get("status", "open") != "completed":
            active.append(task)

    if not active:
        return None

    try:
        return sorted(active, key=nina_task_priority_score, reverse=True)[0]
    except Exception:
        return active[0]


def nina_followup_context_answer(user_id):
    task = nina_latest_task_for_followup(user_id)
    if not task:
        return (
            "🔁 Follow-up Context\n\n"
            "Šobrīd nav aktīva uzdevuma, ko pārbaudīt kā follow-up.\n\n"
            "Tests:\n"
            "piektdien jāpajautā Andrim par atbildi\n"
            "follow-up\n\n"
            "Versija: Follow-up Engine V1.0"
        )

    relationships = nina_latest_relationships(user_id, limit=100) or []
    try:
        task = enrich_task_with_client_context(task, relationships)
    except Exception:
        pass

    return build_followup_context_answer(task)


# =========================
# NinaOS Follow-up Save Bridge — V1.1
# =========================

def nina_followup_router_answer_v11(user_id, user_text):
    task = detect_followup_task(user_text)
    if not task:
        return None

    try:
        relationships = nina_latest_relationships(user_id, limit=100) or []
        task = enrich_task_with_client_context(task, relationships)
    except Exception as e:
        print("followup client context kļūda:", repr(e))

    try:
        task = enrich_task_with_followup(task)
    except Exception:
        pass

    try:
        nina_save_task_to_memory(user_id, task)
    except Exception as e:
        print("followup task save kļūda:", repr(e))

    return build_followup_saved_answer(task)


# =========================
# NinaOS Task Cleanup Bridge — V1.0
# =========================

def nina_task_cleanup_preview(user_id):
    tasks = nina_latest_tasks(user_id, limit=200) or []
    return build_cleanup_preview(tasks)


def nina_task_cleanup_confirm(user_id):
    tasks = nina_latest_tasks(user_id, limit=200) or []
    junk = find_cleanup_candidates(tasks)

    if not junk:
        return build_cleanup_done_answer(0)

    deleted = 0

    try:
        conn = get_db()
        c = conn.cursor()

        for task in junk:
            title = (task.get("title") or "").strip()
            if not title:
                continue

            try:
                db_execute(
                    c,
                    """
                    UPDATE memory_backups
                    SET backup_text = %s
                    WHERE user_id = %s
                      AND source = %s
                      AND backup_text LIKE %s
                    """,
                    ("[deleted task cleanup]", str(user_id), "task_engine", f'%\"title\": \"{title}%')
                )
                deleted += 1
            except Exception as e:
                print("Task cleanup delete kļūda:", repr(e))

        conn.commit()
        c.close()
        conn.close()
    except Exception as e:
        print("Task cleanup DB kļūda:", repr(e))

    return build_cleanup_done_answer(deleted)


# =========================
# NinaOS Task Cleanup V1.1 + Task List Filter Fix
# =========================

def _task_deadline_rank(task):
    title = ((task or {}).get("title") or "").lower()
    deadline = str((task or {}).get("deadline") or "").lower()
    blob = f"{title} {deadline}"
    order = ["today", "tomorrow", "day_after_tomorrow", "monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday",
             "šodien", "rīt", "parīt", "pirmdien", "otrdien", "trešdien", "ceturtdien", "piektdien", "sestdien", "svētdien"]
    for i, token in enumerate(order):
        if token in blob:
            return len(order) - i
    return 0


def _task_client_guess(task):
    client = ((task or {}).get("client") or "").strip()
    if client:
        return client
    blob = f"{(task or {}).get('title','')} {(task or {}).get('raw_text','')}".lower()
    if any(x in blob for x in ["andris", "andri", "andrim"]):
        return "Andris"
    if any(x in blob for x in ["anna", "annai", "annu"]):
        return "Anna"
    if any(x in blob for x in ["jānis", "janis", "jāni", "jani", "jānim", "janim"]):
        return "Jānis"
    return ""


def _task_semantic_key(task):
    title = ((task or {}).get("title") or (task or {}).get("raw_text") or "").strip().lower()
    client = _task_client_guess(task).lower()
    if not title:
        return ""

    if ("jāpajautā" in title or "japajauta" in title or "par atbildi" in title) and client:
        return f"followup_answer::{client}"
    if ("jānosūta piedāvājums" in title or "jānosuta piedāvājumu" in title or "piedāvājums" in title) and client:
        return f"offer::{client}"
    if ("jāzvana" in title or "jāpiezvana" in title or "jazvana" in title or "japiezvana" in title) and client:
        return f"call::{client}"

    return f"raw::{title}"


def nina_clean_real_tasks(user_id, limit=200):
    tasks = nina_latest_tasks(user_id, limit=limit) or []
    buckets = {}

    for task in tasks:
        title = ((task or {}).get("title") or (task or {}).get("raw_text") or "").strip()
        if not title:
            continue

        try:
            if not is_active_real_task(task):
                continue
        except Exception:
            status = ((task or {}).get("status") or "open").strip().lower()
            if status in ["completed", "deleted", "archived", "cancelled", "canceled"]:
                continue
            if title.lower() in ["follow-up", "followup", "follow up", "[deleted task cleanup]"]:
                continue

        key = _task_semantic_key(task)
        if not key:
            continue

        existing = buckets.get(key)
        if not existing:
            buckets[key] = task
            continue

        # Dod priekšroku ierakstam ar termiņu / pilnāku follow-up formulējumu.
        existing_score = _task_deadline_rank(existing) + (3 if "par atbildi" in ((existing.get("title") or "").lower()) else 0)
        new_score = _task_deadline_rank(task) + (3 if "par atbildi" in ((task.get("title") or "").lower()) else 0)

        if new_score > existing_score:
            buckets[key] = task

    return list(buckets.values())


def nina_task_list_answer(user_id):
    return task_summary(nina_clean_real_tasks(user_id, limit=200))


def nina_task_cleanup_preview(user_id):
    tasks = nina_latest_tasks(user_id, limit=200) or []
    return build_cleanup_preview(tasks)


def nina_task_cleanup_confirm(user_id):
    tasks = nina_latest_tasks(user_id, limit=200) or []
    junk = find_cleanup_candidates(tasks)

    if not junk:
        return build_cleanup_done_answer(0)

    deleted = 0
    seen = set()

    for task in junk:
        title = ((task or {}).get("title") or (task or {}).get("raw_text") or "").strip()
        if not title:
            continue

        key = title.lower()
        if key in seen:
            continue
        seen.add(key)

        deleted_task = dict(task)
        deleted_task["status"] = "deleted"
        deleted_task["status_label"] = "dzēsts"
        deleted_task["cleanup"] = "task_cleanup_v1_1"

        try:
            nina_save_task_to_memory(user_id, deleted_task)
            deleted += 1
        except Exception as e:
            print("Task Cleanup V1.1 delete marker kļūda:", repr(e))

    return build_cleanup_done_answer(deleted)


# =========================
# NinaOS Client Work View Bridge — V1.0
# =========================

def nina_client_work_view_answer(user_id, user_text):
    client_name = extract_client_from_query(user_text)
    tasks = nina_clean_real_tasks(user_id, limit=200)
    return build_client_work_view(client_name, tasks)


# =========================
# NinaOS Sales Pipeline / Client CRM Bridge — V1.0
# =========================

def nina_client_task_map_v1(user_id, limit=200):
    """
    Savāc aktīvos uzdevumus pa klientiem, neizmantojot client_context.py.
    Pamats: jau esošais nina_clean_real_tasks().
    """
    tasks = nina_clean_real_tasks(user_id, limit=limit)
    client_map = {}

    for task in tasks or []:
        if not isinstance(task, dict):
            continue

        client = (task.get("client") or "").strip()

        # Fallback: mēģina izvilkt klientu no title/raw_text ar esošo client_work_view normalizāciju.
        if not client:
            blob = f"{task.get('title', '')} {task.get('raw_text', '')}".lower()
            if any(x in blob for x in ["andris", "andri", "andrim"]):
                client = "Andris"
            elif any(x in blob for x in ["jānis", "janis", "jāni", "jani", "jānim", "janim"]):
                client = "Jānis"
            elif any(x in blob for x in ["anna", "annu", "annai"]):
                client = "Anna"

        if not client:
            continue

        client = extract_client_from_query(f"kas notiek ar {client}") or client
        client_map.setdefault(client, []).append(task)

    return client_map


def nina_sales_pipeline_answer(user_id):
    client_map = nina_client_task_map_v1(user_id, limit=200)
    return format_pipeline_overview(client_map)


def nina_sales_pipeline_risk_answer(user_id):
    client_map = nina_client_task_map_v1(user_id, limit=200)
    return format_stuck_clients(client_map)


def nina_active_clients_answer(user_id):
    client_map = nina_client_task_map_v1(user_id, limit=200)
    return format_active_clients(client_map)


def nina_offer_to_send_answer(user_id):
    client_map = nina_client_task_map_v1(user_id, limit=200)
    return format_offer_to_send_clients(client_map)


def nina_followup_clients_answer(user_id):
    client_map = nina_client_task_map_v1(user_id, limit=200)
    return format_followup_clients(client_map)


def nina_sales_pipeline_status_answer():
    """
    Sales Pipeline V1.2 status:
    statusa tekstu ņem no sales_pipeline.py, ja pieejams.
    """
    try:
        return sales_pipeline_status_text()
    except Exception:
        return (
            "📊 Sales Pipeline / Client CRM ir aktīvs. ✅\n\n"
            "Komandas:\n"
            "pipeline\n"
            "mani klienti\n"
            "kam jānosūta piedāvājums\n"
            "kam jātaisa follow-up\n"
            "kas iestrēdzis\n"
            "kas notiek ar Andri\n\n"
            f"Versija: {SALES_PIPELINE_VERSION}"
        )


# =========================
# NinaOS Guide Engine Bridge — V1.0
# =========================

def nina_guide_user_name(user_id):
    try:
        user = get_user(str(user_id)) or {}
        return (user.get("name") or "").strip()
    except Exception:
        return ""


def nina_guide_welcome_for_user(user_id):
    return guide_welcome_answer(nina_guide_user_name(user_id))


# =========================
# NinaOS Presentation / Language Bridge — V1.0
# =========================

def nina_public_answer(answer, locale="lv"):
    return humanize_public_text(answer, locale=locale)


def nina_public_append_hint(answer, context, locale="lv"):
    try:
        return nina_public_answer(append_hint(answer, context), locale=locale)
    except Exception:
        return nina_public_answer(answer, locale=locale)


# =========================
# NinaOS Initiative Engine Bridge — V1.0
# =========================

def nina_initiative_answer(user_id):
    tasks = nina_clean_real_tasks(user_id, limit=200)
    return build_initiative_answer(tasks)


# =========================
# NinaOS Daily Brief / Work Inbox Bridge — V1.0
# =========================

def nina_daily_brief_answer(user_id):
    tasks = nina_clean_real_tasks(user_id, limit=200)
    return build_daily_brief_answer(tasks)

async def reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # V114.0 public reply wrapper
    try:
        user_text = update.message.text
        user_id = str(update.effective_user.id)
        lower = user_text.strip().lower()

        # NinaOS Platform Visibility V1.1 — Global-first product surface
        # IMPORTANT: platform answers are sent raw, without nina_public_answer(),
        # so English product terms like follow-up are not auto-translated by the Latvian presentation layer.
        try:
            platform_visibility_answer = route_platform_visibility_command(user_text, language="en")
        except Exception as e:
            print("Platform Visibility route kļūda:", repr(e))
            platform_visibility_answer = None

        if platform_visibility_answer:
            try:
                save_conversation_state(user_id, user_text, platform_visibility_answer, "platform_visibility_v11", v80_mood(user_text), "platform_visibility")
            except Exception:
                pass
            await safe_reply_text(update, platform_visibility_answer)
            return


        # NinaOS Work Objects V1.0 — universal work object layer
        # Raw English product surface, no Latvian presentation filter.
        try:
            work_objects_answer = route_work_objects_command(user_text)
        except Exception as e:
            print("Work Objects route kļūda:", repr(e))
            work_objects_answer = None

        if work_objects_answer:
            try:
                save_conversation_state(user_id, user_text, work_objects_answer, "work_objects_v1", v80_mood(user_text), "work_objects")
            except Exception:
                pass
            await safe_reply_text(update, work_objects_answer)
            return

        # NinaOS Activity Feed V1.0 — recent activities layer
        # Raw English product surface, no Latvian presentation filter.
        try:
            activity_feed_answer = route_activity_feed_command(user_text)
        except Exception as e:
            print("Activity Feed route kļūda:", repr(e))
            activity_feed_answer = None

        if activity_feed_answer:
            try:
                save_conversation_state(user_id, user_text, activity_feed_answer, "activity_feed_v1", v80_mood(user_text), "activity_feed")
            except Exception:
                pass
            await safe_reply_text(update, activity_feed_answer)
            return


        # NinaOS Workspace Dashboard V1.0 — approved product dashboard surface
        # Raw English product surface, no Latvian presentation filter.
        try:
            workspace_dashboard_answer = route_workspace_dashboard_command(user_text, language="en")
        except Exception as e:
            print("Workspace Dashboard route kļūda:", repr(e))
            workspace_dashboard_answer = None

        if workspace_dashboard_answer:
            try:
                save_conversation_state(user_id, user_text, workspace_dashboard_answer, "workspace_dashboard_v1", v80_mood(user_text), "workspace_dashboard")
            except Exception:
                pass
            await safe_reply_text(update, workspace_dashboard_answer)
            return


        # =========================
        # Core 2.8 — Memory Intelligence V1
        # =========================
        try:
            active_ctx_for_memory = get_active_context(user_id)
        except Exception:
            active_ctx_for_memory = {}

        try:
            memory_snapshot = build_memory_snapshot(
                user_id,
                tasks=nina_clean_real_tasks(user_id, limit=50),
                context=active_ctx_for_memory,
                recent_messages=[],
            )
        except Exception as e:
            print("Memory Intelligence snapshot kļūda:", repr(e))
            memory_snapshot = {}

        if is_memory_status_command(user_text):
            await safe_reply_text(update, memory_status_answer(memory_snapshot))
            return

        try:
            memory_rewritten_text = resolve_memory_command(user_text, memory_snapshot)
        except Exception as e:
            print("Memory Intelligence rewrite kļūda:", repr(e))
            memory_rewritten_text = user_text

        if memory_rewritten_text and memory_rewritten_text != user_text:
            user_text = memory_rewritten_text
            lower = (user_text or "").strip().lower()
            try:
                update_context_from_text(user_id, user_text, source="memory_intelligence_rewrite")
            except Exception:
                pass


        # Core 2.7 — Context V1: resolve short/pronoun commands before normal routing.
        try:
            original_user_text = user_text
            active_context = get_active_context(user_id)
            resolved_user_text = resolve_context_command(user_text, active_context)
            if resolved_user_text and resolved_user_text != user_text:
                print(f"Context V1 rewrite: {user_text!r} -> {resolved_user_text!r}")
                user_text = resolved_user_text
                lower = user_text.strip().lower()
            update_context_from_text(user_id, user_text, source="incoming_resolved")
        except Exception as e:
            print("Context V1 resolve kļūda:", repr(e))


        if lower in ["voice status", "voice intake status", "audio status", "balss statuss", "balss"]:
            await safe_reply_text(update, voice_status_answer())
            return

        if lower in ["voice debug", "audio debug", "balss debug"]:
            await safe_reply_text(update, voice_last_debug_answer())
            return

        if lower in ["context status", "context", "konteksts", "konteksta statuss"]:
            await safe_reply_text(update, context_status_answer(user_id))
            return

        if lower in ["context debug", "konteksts debug", "konteksta debug"]:
            await safe_reply_text(update, context_debug_answer(user_id))
            return

        if lower in ["presentation status", "language status", "valodu slānis", "valodu slanis", "presentation layer"]:
            await safe_reply_text(update, presentation_status_answer())
            return

        if lower in ["initiative status", "initiative engine", "initiative"]:
            await safe_reply_text(update, nina_public_answer(initiative_status_answer()))
            return

        if lower in ["daily brief status", "work inbox status", "dienas status", "darba inbox status"]:
            await safe_reply_text(update, nina_public_answer(daily_brief_status_answer()))
            return

        if is_daily_brief_command(user_text):
            await safe_reply_text(update, nina_public_answer(nina_daily_brief_answer(user_id)))
            return

        if is_initiative_command(user_text):
            await safe_reply_text(update, nina_public_answer(nina_initiative_answer(user_id)))
            return



        # NinaOS Ready Worker Catalog V1
        # Klients neizveido botu — klients izvēlas un saņem gatavu AI darbinieku.
        if is_ready_worker_command(user_text):
            try:
                worker_answer = build_ready_worker_answer(user_text)
            except Exception as e:
                print("Ready Worker Catalog route kļūda:", repr(e))
                worker_answer = "🧑‍💼 NinaOS Ready Worker Catalog šobrīd nevarēja sagatavot atbildi.\n\nVersija: Ready Worker Catalog V1"

            try:
                v40_log_usage(user_id, "ready_worker_catalog_v1", user_text)
            except Exception:
                pass
            try:
                save_conversation_state(user_id, user_text, worker_answer, "ready_worker_catalog_v1", v80_mood(user_text), "ready_worker_catalog")
            except Exception:
                pass

            await safe_reply_text(update, nina_public_answer(worker_answer))
            return

        # NinaOS RolePack System V1
        # Kontrolē amatus: drīkst/nedrīkst, faili, tooli, approval gates, Exchange tiesības.
        if is_rolepack_command(user_text):
            try:
                rolepack_answer = build_rolepack_answer(user_text)
            except Exception as e:
                print("RolePack route kļūda:", repr(e))
                rolepack_answer = "🧩 NinaOS RolePack System šobrīd nevarēja sagatavot atbildi.\n\nVersija: RolePack System V1"

            try:
                v40_log_usage(user_id, "rolepack_system_v1", user_text)
            except Exception:
                pass
            try:
                save_conversation_state(user_id, user_text, rolepack_answer, "rolepack_system_v1", v80_mood(user_text), "role_pack")
            except Exception:
                pass

            await safe_reply_text(update, nina_public_answer(rolepack_answer))
            return

        # NinaOS Platform Core V1
        # Platform-first pamats: workspace, gatavi AI darbinieki, amati, tiesības un Exchange virziens.
        if is_platform_command(user_text):
            try:
                platform_answer = build_platform_answer(user_text)
            except Exception as e:
                print("Platform Core route kļūda:", repr(e))
                platform_answer = "🧱 NinaOS Platform Core šobrīd nevarēja sagatavot atbildi.\n\nVersija: Platform Core V1"

            try:
                v40_log_usage(user_id, "platform_core_v1", user_text)
            except Exception:
                pass
            try:
                save_conversation_state(user_id, user_text, platform_answer, "platform_core_v1", v80_mood(user_text), "platform_core")
            except Exception:
                pass

            await safe_reply_text(update, nina_public_answer(platform_answer))
            return

        # Core 3.1.1.1 — Sales Snapshot Cleanup
        # Nosaka klienta pārdošanas posmu un nākamo deal soli no reālajiem taskiem.
        if lower in ["sales", "sales status", "sales brain", "pipeline status", "deal status"]:
            try:
                sales_tasks = nina_clean_real_tasks(user_id, limit=200)
            except Exception:
                sales_tasks = []
            await safe_reply_text(update, nina_public_answer(build_sales_status_answer(sales_tasks, memory_snapshot)))
            return

        if is_sales_command(user_text):
            try:
                sales_tasks = nina_clean_real_tasks(user_id, limit=200)
            except Exception:
                sales_tasks = []
            try:
                sales_answer = build_sales_answer(user_text, tasks=sales_tasks, memory_snapshot=memory_snapshot)
            except Exception as e:
                print("Sales Brain route kļūda:", repr(e))
                sales_answer = "📈 Sales Brain šobrīd nevarēja noteikt pipeline posmu. Pamēģini vēlreiz ar klienta vārdu.\n\nVersija: Core 3.1.1"

            try:
                v40_log_usage(user_id, "sales_brain_311", user_text)
            except Exception:
                pass
            try:
                save_conversation_state(user_id, user_text, sales_answer, "sales_brain_311", v80_mood(user_text), "sales_brain")
            except Exception:
                pass

            await safe_reply_text(update, nina_public_answer(sales_answer))
            return

        # Nina Work Layer V1.1 — Smart Message Mode
        # Ģenerē praktiskas klientu darba sagataves un automātiski izvēlas pareizo ziņas tipu.
        if lower in ["work layer", "work layer status", "nina work layer", "work skills", "darba prasmes"]:
            await safe_reply_text(update, nina_public_answer(work_layer_status_answer()))
            return

        if is_work_layer_command(user_text):
            try:
                work_tasks = nina_clean_real_tasks(user_id, limit=200)
            except Exception:
                work_tasks = []
            try:
                work_answer = build_work_layer_answer(user_text, tasks=work_tasks, memory_snapshot=memory_snapshot)
            except Exception as e:
                print("Work Layer route kļūda:", repr(e))
                work_answer = "🧰 Work Layer šobrīd nevarēja sagatavot atbildi. Pamēģini vēlreiz ar klienta vārdu.\n\nVersija: Nina Work Layer V1.1"

            try:
                v40_log_usage(user_id, "work_layer_v11", user_text)
            except Exception:
                pass
            try:
                save_conversation_state(user_id, user_text, work_answer, "work_layer_v11", v80_mood(user_text), "work_layer")
            except Exception:
                pass

            await safe_reply_text(update, nina_public_answer(work_answer))
            return

        if lower in ["guide status", "guide engine", "onboarding status"]:
            await safe_reply_text(update, nina_public_answer(guide_status_answer()))
            return

        if is_start_command(user_text):
            await safe_reply_text(update, nina_public_answer(nina_guide_welcome_for_user(user_id)))
            return

        if is_guide_command(user_text):
            await safe_reply_text(update, nina_public_answer(guide_capabilities_answer()))
            return

        if lower in ["sales pipeline", "pipeline status", "crm status", "client crm status"]:
            await safe_reply_text(update, nina_public_answer(nina_sales_pipeline_status_answer()))
            return

        if lower in ["klienti", "klientu pārskats", "klientu parskats", "klientu darbi", "pipeline", "klientu statuss", "parādi manus klientus", "paradi manus klientus", "crm", "client crm"]:
            await safe_reply_text(update, nina_public_append_hint(nina_sales_pipeline_answer(user_id), "pipeline"))
            return

        if lower in ["mani klienti"]:
            await safe_reply_text(update, nina_public_append_hint(nina_active_clients_answer(user_id), "active_clients"))
            return

        if lower in ["kam jānosūta piedāvājums", "kam janosuta piedavajums", "piedāvājumi jānosūta", "piedavajumi janosuta", "piedāvājumi", "piedavajumi", "offer to send"]:
            await safe_reply_text(update, nina_public_append_hint(nina_offer_to_send_answer(user_id), "offer_to_send"))
            return

        if lower in ["kam jāatgādina", "kam jaatgadina", "kam jāsazinās vēlreiz", "kam jasazinas velreiz", "kam jātaisa follow-up", "kam jataisa follow-up", "kam follow-up", "follow-up klienti", "followup klienti"]:
            await safe_reply_text(update, nina_public_append_hint(nina_followup_clients_answer(user_id), "followup_clients"))
            return

        if lower in ["kas iestrēdzis", "kas iestredzis", "kur deg", "kurš klients stāv uz vietas", "kurs klients stav uz vietas"]:
            await safe_reply_text(update, nina_public_append_hint(nina_sales_pipeline_risk_answer(user_id), "stuck"))
            return

        if lower in ["client work", "client work status", "client work view"]:
            await safe_reply_text(update, nina_public_answer(client_work_status()))
            return

        if lower.startswith("kas notiek ar ") or lower.startswith("kas ar "):
            await safe_reply_text(update, nina_public_append_hint(nina_client_work_view_answer(user_id, user_text), "client_view"))
            return


        if lower == "task cleanup":
            await safe_reply_text(update, nina_task_cleanup_preview(user_id))
            return

        if lower == "task cleanup confirm":
            await safe_reply_text(update, nina_task_cleanup_confirm(user_id))
            return


        if lower in ["follow-up", "followup", "follow up"]:
            await safe_reply_text(update, nina_followup_context_answer(user_id))
            return

        followup_router_answer = nina_followup_router_answer_v11(user_id, user_text)
        if followup_router_answer:
            try:
                v40_log_usage(user_id, "followup_engine", user_text)
            except Exception:
                pass
            try:
                save_conversation_state(user_id, user_text, followup_router_answer, "followup_engine", v80_mood(user_text), "followup")
            except Exception:
                pass
            await safe_reply_text(update, followup_router_answer)
            return


        if lower in ["follow-up engine", "followup engine", "follow up engine", "follow-up status", "followup status"]:
            await safe_reply_text(update, build_followup_status_answer())
            return


        if lower in ["client context", "klienta konteksts", "klientu konteksts"]:
            await safe_reply_text(update, nina_client_context_answer(user_id))
            return

        if lower in ["client context status", "client status"]:
            await safe_reply_text(update, client_context_status())
            return


        if lower in ["persistence health", "db health", "database health", "atmiņas health", "atminas health", "db statuss", "datubāzes statuss", "datubazes statuss"]:
            await safe_reply_text(update, nina_persistence_health_answer())
            return

        if lower in ["memory router", "memory router status", "atmiņas router", "atminas router"]:
            await safe_reply_text(update, nina_memory_router_status_v11())
            return

        memory_router_answer = nina_memory_router_answer_v11(user_id, user_text)
        if memory_router_answer:
            try:
                v40_log_usage(user_id, "memory_router_fix", user_text)
            except Exception:
                pass
            try:
                save_conversation_state(user_id, user_text, memory_router_answer, "memory_router_fix", v80_mood(user_text), "memory")
            except Exception:
                pass
            await safe_reply_text(update, memory_router_answer)
            return

        if lower in ["ko tu par mani zini", "ko tu zini par mani", "mans profils", "manas atmiņas", "manas atminas"]:
            await safe_reply_text(update, nina_profile_summary_v16(user_id))
            return




        # =========================
        # V116 Router Priority Gate
        # System/recovery commands MUST run before project/memory/natural conversation routers.
        # =========================
        if lower in ["nina seed", "seed profile", "atjauno janis", "atjauno jānis", "ieliec manu profilu"]:
            await safe_reply_text(update, nina_seed_janis_profile(user_id))
            return

        if lower in ["nina recovery", "memory recovery", "profile recovery", "atjauno profilu", "atjauno atmiņu", "atjauno atminu"]:
            await safe_reply_text(update, nina_recovery_answer(user_id))
            return


        if lower in ["reply builder", "core 2.5.1", "core 2.5.2", "reply builder status", "core 251", "core 252", "core 2.5.1 status", "core 2.5.2 status"]:
            await safe_reply_text(update, reply_builder_status_answer())
            return

        if lower in ["task engine", "task status", "uzdevumu dzinējs", "uzdevumu dzinejs"]:
            await safe_reply_text(update, task_engine_status())
            return

        if lower in ["izdarīts", "izdarits", "pabeigts", "done", "gatavs"]:
            await safe_reply_text(update, nina_complete_top_task(user_id))
            return

        if lower in ["relationship engine", "relationship status", "attiecību dzinējs", "attiecibu dzinejs"]:
            await safe_reply_text(update, relationship_engine_status())
            return

        if lower in ["manas attiecības", "manas attiecibas", "attiecības", "attiecibas", "relationship memory"]:
            await safe_reply_text(update, nina_relationships_answer(user_id))
            return

        relationship_answer = nina_relationship_answer(user_id, user_text)
        if relationship_answer:
            try:
                v40_log_usage(user_id, "relationship_engine", user_text)
            except Exception:
                pass
            try:
                save_conversation_state(user_id, user_text, relationship_answer, "relationship_engine", v80_mood(user_text), "relationship")
            except Exception:
                pass
            await safe_reply_text(update, relationship_answer)
            return

        if lower in ["daily planner", "planner status", "dienas plānotājs", "dienas planotajs"]:
            await safe_reply_text(update, daily_planner_status())
            return

        if lower in [
            "saplāno manu dienu",
            "saplano manu dienu",
            "ko man darīt šodien",
            "ko man darit sodien",
            "ko man darīt sodien",
            "ko man darit šodien",
            "ar ko sākt",
            "ar ko sakt",
            "dienas plāns",
            "dienas plans"
        ]:
            await safe_reply_text(update, nina_daily_plan_answer(user_id))
            return

        if lower in ["work engine", "work status", "darba dzinējs", "darba dzinejs"]:
            await safe_reply_text(update, work_engine_status())
            return

        if lower in [
            "sakārto manu dienu",
            "sakarto manu dienu",
            "saplāno manu dienu",
            "saplano manu dienu",
            "mana darba diena",
            "darba plāns",
            "darba plans"
        ]:
            await safe_reply_text(update, nina_work_plan_answer(user_id))
            return

        if lower in ["mani uzdevumi", "uzdevumi", "task list", "tasks"]:
            await safe_reply_text(update, nina_public_append_hint(nina_task_list_answer(user_id), "task_list"))
            return

        task_answer = nina_task_answer(user_id, user_text)
        if task_answer:
            try:
                v40_log_usage(user_id, "task_engine", user_text)
            except Exception:
                pass
            try:
                save_conversation_state(user_id, user_text, task_answer, "task_engine", v80_mood(user_text), "task")
            except Exception:
                pass
            await safe_reply_text(update, task_answer)
            return

        # Core 3.0 — Employee Brain v3
        # Darba smadzeņu slānis Core/roadmap/status/darba vadības jautājumiem.
        # Tas izmanto Memory Intelligence snapshotu, bet neaizstāj Task/Follow-up/Initiative routerus.
        if employee_reply and (
            lower in ["core 2.0", "core 2.1", "core 2.2", "core 2.3", "core 2.4", "core 2.5", "core 2.5.1", "core 2.6", "core 2.6.1", "core 2.7", "core 2.8", "core 3.0", "core 30", "employee brain v3", "reply builder", "reply builder status", "initiative engine", "initiative status", "initiative detector", "initiative detector status", "think engine", "think status", "learning engine", "learning status", "quality engine", "quality status", "core evolution", "employee status", "core status", "nina core", "employee brain", "core"]
            or "ninaos misija" in lower
            or "mūsu misija" in lower
            or "musu misija" in lower
            or "kas tālāk" in lower
            or "kas talak" in lower
            or "ko šodien darām" in lower
            or "ko sodien daram" in lower
            or "ko tu iesaki" in lower
            or "ninaos" in lower
            or "palīdzi būvēt" in lower
            or "palidzi buvet" in lower
            or "palīdzi uzbūvēt" in lower
            or "palidzi uzbuvet" in lower
            or "kā mani sauc" in lower
            or "ka mani sauc" in lower
            or "zini manu vārdu" in lower
            or "zini manu vardu" in lower
            or "mans vārds" in lower
            or "mans vards" in lower
            or "uzņemies" in lower
            or "uznemies" in lower
            or "atbildība" in lower
            or "atbildiba" in lower
            or "kur tu kļūdījies" in lower
            or "kur tu kludijies" in lower
            or "kas ir tavs uzdevums" in lower
            or "ko darām tālāk" in lower
            or "ko daram talak" in lower
            or "ko darām ar" in lower
            or "ko daram ar" in lower
            or "darba smadzenes" in lower
            or "ai darbiniece" in lower
            or "employee brain v3" in lower
            or "core 3.0" in lower
            or "core 30" in lower
            or "ko tu iemācījies" in lower
            or "ko tu iemacijies" in lower
            or "mācies" in lower
            or "macies" in lower
            or "ko tu iemācījies" in lower
            or "ko tu iemacijies" in lower
            or "ko nedrīksti atkārtot" in lower
            or "ko nedriksti atkartot" in lower
            or "slikti atbildi" in lower
            or "tu esi robots" in lower
            or "garlaicīgi" in lower
            or "garlaicigi" in lower
        ):
            try:
                user = get_user(str(user_id))
            except Exception:
                user = {}

            try:
                answer = employee_reply(
                    user_id=user_id,
                    text=user_text,
                    user=user,
                    memory_snapshot=memory_snapshot,
                    context_snapshot=active_ctx_for_memory,
                )
            except TypeError:
                # Backward compatibility, ja serverī īslaicīgi vēl ir vecais employee_brain.py.
                answer = employee_reply(user_id=user_id, text=user_text, user=user)

            try:
                v40_log_usage(user_id, "employee_brain_core_router", user_text)
            except Exception:
                pass

            try:
                save_conversation_state(user_id, user_text, answer, "employee_brain_core_router", v80_mood(user_text), "core_evolution")
            except Exception:
                pass

            await safe_reply_text(update, answer)
            return


        # V115.2 Nina Core: natural conversation, identity first and employee brain.
        v1151_answer = v1151_master_core(user_id, user_text)
        if v1151_answer:
            try:
                v40_log_usage(user_id, "v1151_nina_core", user_text)
            except Exception:
                pass
            try:
                save_conversation_state(user_id, user_text, v1151_answer, "v1151_nina_core", v80_mood(user_text), "nina_core")
            except Exception:
                pass
            await safe_reply_text(update, v1151_answer)
            return

        # V114.0 Relationship Engine Router.
        rel114_answer = rel114_intent_router(user_id, user_text)
        if rel114_answer:
            try:
                v40_log_usage(user_id, "rel114", user_text)
            except Exception:
                pass
            try:
                save_conversation_state(user_id, user_text, rel114_answer, "rel114", v80_mood(user_text), "relationship_engine")
            except Exception:
                pass
            await safe_reply_text(update, rel114_answer)
            return


        # V114.0 Identity Engine Router.
        id113_answer = id113_intent_router(user_id, user_text)
        if id113_answer:
            try:
                v40_log_usage(user_id, "id113", user_text)
            except Exception:
                pass
            try:
                save_conversation_state(user_id, user_text, id113_answer, "id113", v80_mood(user_text), "identity_engine")
            except Exception:
                pass
            await safe_reply_text(update, id113_answer)
            return


        # V114.0 Context Engine Router.
        ctx112_answer = ctx112_intent_router(user_id, user_text)
        if ctx112_answer:
            try:
                v40_log_usage(user_id, "ctx112", user_text)
            except Exception:
                pass
            try:
                save_conversation_state(user_id, user_text, ctx112_answer, "ctx112", v80_mood(user_text), "context_engine")
            except Exception:
                pass
            await safe_reply_text(update, ctx112_answer)
            return


        # V114.0 Human Engine Router.
        human111_answer = human111_intent_router(user_id, user_text)
        if human111_answer:
            try:
                v40_log_usage(user_id, "human111", user_text)
            except Exception:
                pass
            try:
                save_conversation_state(user_id, user_text, human111_answer, "human111", v80_mood(user_text), "human_engine")
            except Exception:
                pass
            await safe_reply_text(update, human111_answer)
            return


        # V114.0 NinaOS Platform Core Router.
        ninaos_answer = ninaos_intent_router(user_id, user_text)
        if ninaos_answer:
            try:
                v40_log_usage(user_id, "ninaos_v110", user_text)
            except Exception:
                pass
            try:
                save_conversation_state(user_id, user_text, ninaos_answer, "ninaos", v80_mood(user_text), "platform_core")
            except Exception:
                pass
            await safe_reply_text(update, ninaos_answer)
            return


        # V114.0 AI Core Router.
        v90_answer = v90_intent_router(user_id, user_text)
        if v90_answer:
            try:
                v40_log_usage(user_id, "v90_core", user_text)
            except Exception:
                pass
            try:
                save_conversation_state(user_id, user_text, v90_answer, "v90", v80_mood(user_text), "v90_core")
            except Exception:
                pass
            await safe_reply_text(update, v90_answer)
            return


        # V114.0 Relationship + Smart Memory Router.
        v80_answer = v80_intent_router(user_id, user_text)
        if v80_answer:
            try:
                v40_log_usage(user_id, "v80_relationship", user_text)
            except Exception:
                pass
            try:
                save_conversation_state(user_id, user_text, v80_answer, "v80", v80_mood(user_text), "relationship")
            except Exception:
                pass
            await safe_reply_text(update, v80_answer)
            return


        # V114.0 Navigation Polish Router.
        v602_answer = v602_intent_router(user_id, user_text)
        if v602_answer:
            try:
                v40_log_usage(user_id, "v602_navigation", user_text)
            except Exception:
                pass
            await safe_reply_text(update, v602_answer)
            return


        # V114.0 Navigation Hotfix Router: emergency/navigation before generic help.
        v601_answer = v601_intent_router(user_id, user_text)
        if v601_answer:
            try:
                v40_log_usage(user_id, "v601_navigation", user_text)
            except Exception:
                pass
            await safe_reply_text(update, v601_answer)
            return


        # V114.0 Intelligence + Navigation Router.
        v60_answer = v60_intent_router(user_id, user_text)
        if v60_answer:
            try:
                v40_log_usage(user_id, "v60_intent", user_text)
            except Exception:
                pass
            await safe_reply_text(update, v60_answer)
            return


        # V114.0 Assistant Platform Router.
        v50_answer = v50_assistant_router(user_id, user_text)
        if v50_answer:
            try:
                v40_log_usage(user_id, "v50_command", user_text)
            except Exception:
                pass
            await safe_reply_text(update, v50_answer)
            return


        # V114.0 Stable Intent Router: practical help before profile/revenue.
        v401_answer = v401_intent_router(user_id, user_text)
        if v401_answer:
            v40_log_usage(user_id, "intent_help", user_text)
            await safe_reply_text(update, v50_enhance_answer_with_memory(user_id, v401_answer + v40_soft_sales_line(user_id), user_text))
            return


        # V114.0 Revenue Priority Router.
        if lower in ["admin stats", "admin revenue", "platform stats", "v40 stats"]:
            if is_admin(user_id):
                await safe_reply_text(update, v40_admin_stats())
            else:
                await safe_reply_text(update, "Šī komanda ir tikai adminam.\n\nVersija: V114.0")
            return

        v40_log_usage(user_id, "message", user_text)
        v40_revenue_answer = v40_revenue_router(user_id, user_text)
        if v40_revenue_answer:
            await safe_reply_text(update, v40_revenue_answer)
            return


        # V114.0 Stable Priority Router: conversation first, profile second.
        if any(x in lower for x in ["ko tu par mani atceries", "ko atceries par mani", "mans profils", "profils"]):
            await safe_reply_text(update, v24_profile_recall_answer(user_id))
            return

        v301_answer = v301_conversation_answer(user_id, user_text)
        if v301_answer:
            await safe_reply_text(update, v50_enhance_answer_with_memory(user_id, v301_answer + v40_soft_sales_line(user_id), user_text))
            return

        v301_fact = v401_safe_profile_fact(user_text)
        if v301_fact.get("type") and v301_fact.get("value"):
            try:
                v301_save_profile_fact(user_id, v301_fact["type"], v301_fact["value"])
            except Exception as e:
                print("V114.0 profile save kļūda:", repr(e))
            v40_log_usage(user_id, "profile", v301_fact["type"])
            await safe_reply_text(update, v50_enhance_answer_with_memory(user_id, v301_profile_saved_answer(user_id, v301_fact["type"], v301_fact["value"]) + v40_soft_sales_line(user_id), user_text))
            return


        # V114.0: User Profile DB route.
        if any(x in lower for x in ["ko tu par mani atceries", "ko atceries par mani", "mans profils", "profils"]):
            await safe_reply_text(update, v24_profile_recall_answer(user_id))
            return

        profile_answer = v24_profile_answer_from_fact(user_id, user_text)
        if profile_answer:
            await safe_reply_text(update, profile_answer)
            return


        # V114.0: hard conversation flow route.
        flow_answer = v21_flow_answer(user_id, user_text)
        if flow_answer:
            await safe_reply_text(update, flow_answer)
            return

        # V114.0: hard future-memory reminder offer route.
        if v21_is_future_memory_text(user_text) and not lower.startswith(("atgādini", "atgadini")):
            try:
                saved = save_natural_memory_logic(get_db, db_execute, user_id, user_text)
            except Exception:
                saved = user_text
            await safe_reply_text(update, v21_build_memory_answer(saved or user_text))
            return


        # V114.0: Smart Sales price/tariff route.
        if v20_is_price_question(user_text):
            await safe_reply_text(update, v20_smart_price_answer(user_id))
            return


        # V114.0: HARD priority capabilities route before old dialog/charm.
        if any(x in lower for x in ["ko vari", "ko tu vari", "ko māki", "ko maki", "ko vari darīt", "ko vari darit"]):
            cap_answer = v18_human_capabilities_answer()
            save_conversation_state(user_id, user_text, cap_answer, "capabilities", detect_emotion(user_text), detect_topic(user_text))
            await safe_reply_text(update, cap_answer)
            return


        # V114.0: Human Mode priority route. Tam jābūt pirms vecā dialog.py.
        if v18_should_use_human_mode(user_text):
            await safe_reply_text(update, v19_human_mode_answer_with_memory(user_id, user_text))
            return


        # V114.0: Living Conversation Core priority route.
        if v18_should_use_human_mode(user_text):
            await safe_reply_text(update, v19_human_mode_answer_with_memory(user_id, user_text))
            return


        # V114.0: Dialog smart route. Jautājumi nav atmiņas.
        dialog_kind = classify_dialog_message(user_text)
        if dialog_kind == "capabilities" or dialog_kind == "question":
            await safe_reply_text(update, build_capabilities_answer(version="V114.0"))
            return

        if dialog_kind == "rough_playful":
            await safe_reply_text(update, build_playful_rough_answer(version="V114.0"))
            return

        if dialog_kind == "smalltalk":
            await safe_reply_text(update, build_smalltalk_answer(user_text, version="V114.0"))
            return


        # V114.0: Always Reply public safety.
        if looks_like_rough_message(user_text):
            await safe_reply_text(update, nina_rough_message_answer())
            return


        # V114.0: Progress command.
        if lower in ["progress", "progresss", "mans progress", "mans progress", "progress report", "statistika", "mana statistika"]:
            await safe_reply_text(update, 
                nina_progress_answer(user_id),
                disable_web_page_preview=True
            )
            return


        # V114.0: Reminder command.
        reminder_data = parse_reminder_request(user_text, DEFAULT_TIMEZONE)
        if reminder_data is not None:
            if not reminder_data.get("ok"):
                await safe_reply_text(update, build_reminder_help_answer(version="V114.0"), disable_web_page_preview=True)
                return

            ok = save_reminder_logic(
                get_db,
                db_execute,
                user_id,
                reminder_data.get("text") or user_text,
                reminder_data.get("remind_at") or "",
                reminder_data.get("local_time") or "",
            )

            if ok:
                await safe_reply_text(update, 
                    build_reminder_saved_answer(
                        reminder_data.get("text") or user_text,
                        reminder_data.get("human_time") or "",
                        version="V114.0",
                    ),
                    disable_web_page_preview=True
                )
                return

            await safe_reply_text(update, "Neizdevās saglabāt atgādinājumu. Pamēģini vēlreiz.", disable_web_page_preview=True)
            return



        # V114.0: Mana diena top-priority route.
        if lower in ["mana diena", "diena", "my day"]:
            await safe_reply_text(update, 
                nina_daily_habit_answer(user_id),
                disable_web_page_preview=True
            )
            return

        # V114.0: Natural memory and daily goal capture — immediate replies.
        if lower.startswith("atceries,") or lower.startswith("atceries ka") or lower.startswith("atceries "):
            saved = save_natural_memory(user_id, user_text)
            if saved:
                record_memory_topics(user_id, saved)
                answer = nina_memory_saved_answer(saved)
            else:
                answer = "Neizdevās saglabāt. Pamēģini vēlreiz ar: atceries, ka ..."
            await safe_reply_text(update, answer, disable_web_page_preview=True)
            return

        if lower.startswith("mērķis:") or lower.startswith("merkis:") or lower.startswith("šodienas mērķis:") or lower.startswith("sodienas merkis:"):
            goal_text = user_text.split(":", 1)[1].strip() if ":" in user_text else ""
            if goal_text:
                ok = save_daily_goal(user_id, goal_text)
                answer = nina_goal_saved_answer(goal_text) if ok else "Neizdevās saglabāt mērķi. Pamēģini vēlreiz."
                await safe_reply_text(update, answer, disable_web_page_preview=True)
                return
            await safe_reply_text(update, "Uzraksti šādi: mērķis: tavs šodienas mērķis", disable_web_page_preview=True)
            return


        # V114.0: Natural conversation auto-handle.
        natural_kind = classify_natural_message(user_text)

        if natural_kind == "goal":
            goal_text = user_text.strip()
            ok = save_daily_goal(user_id, goal_text)
            answer = build_auto_goal_answer(goal_text, version="V114.0") if ok else "Neizdevās saglabāt mērķi. Pamēģini vēlreiz."
            await safe_reply_text(update, answer, disable_web_page_preview=True)
            return

        if natural_kind == "memory":
            memory_text = user_text.strip()
            saved = save_natural_memory(user_id, "atceries, ka " + memory_text)
            if saved:
                record_memory_topics(user_id, saved)
            answer = build_auto_memory_answer(saved or memory_text, version="V114.0") if saved else "Neizdevās saglabāt. Pamēģini vēlreiz."
            await safe_reply_text(update, answer, disable_web_page_preview=True)
            return

        if lower in ["labrīt", "labrit", "labrīt nina", "labrit nina", "morning"]:
            await safe_reply_text(update, 
                append_bonus_notices(nina_morning_answer(user_id), streak_notice),
                disable_web_page_preview=True
            )
            return

        if lower in ["vakars", "vakara pārskats", "vakara parskats", "good night", "evening"]:
            await safe_reply_text(update, 
                append_bonus_notices(nina_evening_answer(user_id), streak_notice),
                disable_web_page_preview=True
            )
            return

        if lower in ["šodienas mērķis", "sodienas merkis", "dienas mērķis", "dienas merkis", "mērķis", "merkis"]:
            await safe_reply_text(update, 
                append_bonus_notices(nina_today_goal_answer(user_id), streak_notice),
                disable_web_page_preview=True
            )
            return

        # V12.6: Daily Habit commands.
        if lower in ["mana diena", "diena", "my day"]:
            await safe_reply_text(update, 
                append_bonus_notices(nina_daily_habit_answer(user_id), streak_notice),
                disable_web_page_preview=True
            )
            return

        if lower in ["atceries", "ko atceries", "remember"]:
            await safe_reply_text(update, 
                append_bonus_notices(nina_remember_prompt_answer(user_id), streak_notice),
                disable_web_page_preview=True
            )
            return

        if lower in ["invite", "uzaicini", "ielūgt", "ielugt"]:
            await safe_reply_text(update, 
                append_bonus_notices(nina_launch_invite_text(user_id), streak_notice),
                disable_web_page_preview=True
            )
            return


        # V12.5: Stripe production commands.
        if lower in ["stripe production", "stripe live", "stripe setup production", "production stripe"]:
            await safe_reply_text(update, 
                append_bonus_notices(stripe_production_setup_answer(user_id), streak_notice),
                disable_web_page_preview=True
            )
            return

        if lower in ["first payment", "pirmais maksājums", "pirmais maksajums"]:
            await safe_reply_text(update, 
                append_bonus_notices(first_payment_plan_answer(user_id), streak_notice),
                disable_web_page_preview=True
            )
            return


        if lower in ["referral reward test", "reward test"]:
            await safe_reply_text(update, 
                append_bonus_notices(referral_reward_test_answer(user_id), streak_notice),
                disable_web_page_preview=True
            )
            return


        # V12.3.1: capture referral from /start NINA-XXXX before normal chat logic.
        referral_code = parse_referral_code_from_text(user_text)
        if referral_code:
            await safe_reply_text(update, 
                append_bonus_notices(referral_capture_welcome_answer(user_id, referral_code), streak_notice),
                disable_web_page_preview=True
            )
            return

        if lower in ["referral", "referral stats", "mans referral"]:
            await safe_reply_text(update, 
                append_bonus_notices(referral_stats_answer(user_id), streak_notice),
                disable_web_page_preview=True
            )
            return


        # V12.1.2 SAFE ROUTER — public monetization commands before all other logic.
        if lower == "launch":
            await safe_reply_text(update, append_bonus_notices(safe_launch_answer(user_id), streak_notice), disable_web_page_preview=True)
            return

        if lower == "sales":
            await safe_reply_text(update, append_bonus_notices(safe_sales_answer(user_id), streak_notice), disable_web_page_preview=True)
            return

        if lower in ["invite", "referral"]:
            await safe_reply_text(update, append_bonus_notices(safe_invite_answer(user_id), streak_notice), disable_web_page_preview=True)
            return

        if lower == "earn":
            await safe_reply_text(update, append_bonus_notices(safe_earn_answer(user_id), streak_notice), disable_web_page_preview=True)
            return


        # V11.9 HARD FIX: catch Stripe test before GPT fallback.
        if lower in ["stripe test", "webhook test", "test webhook", "stripe webhook test"]:
            await safe_reply_text(update, append_bonus_notices(stripe_webhook_test_answer(user_id), streak_notice), disable_web_page_preview=True)
            return

        profile_text, command_lines = split_profile_and_commands(user_text)
        if command_lines and profile_text.strip():
            update_profile_from_text(user_id, profile_text)
            answers = []
            for command in command_lines:
                answer = command_answer(user_id, command)
                if answer:
                    answers.append(answer)
            if answers:
                await safe_reply_text(update, "\n\n".join(answers), disable_web_page_preview=True)
                return

        if lower in ["mans premium statuss", "premium statuss", "premium"]:
            await safe_reply_text(update, premium_status(user_id), disable_web_page_preview=True)
            return

        if lower in ["premium funkcijas"]:
            await safe_reply_text(update, premium_features(user_id), disable_web_page_preview=True)
            return

        if lower in ["premium limiti", "cik atmiņas man palicis"]:
            await safe_reply_text(update, premium_limits(user_id), disable_web_page_preview=True)
            return

        if lower == "premium beidzas":
            await safe_reply_text(update, premium_expiration_info(user_id), disable_web_page_preview=True)
            return

        if lower == "abonements":
            await safe_reply_text(update, append_bonus_notices(subscription_info(user_id), streak_notice), disable_web_page_preview=True)
            return

        if lower in ["mans plāns", "mans plans"]:
            await safe_reply_text(update, append_bonus_notices(current_plan_answer(user_id), streak_notice), disable_web_page_preview=True)
            return

        if lower in ["premium vēsture", "premium vesture"]:
            await safe_reply_text(update, append_bonus_notices(premium_history(user_id), streak_notice), disable_web_page_preview=True)
            return

        # V10.5.2 HARD FIX: catch Premium Welcome as a direct Telegram command
        # before it can fall through to GPT chat mode.
        if lower in ["premium welcome", "premium sveiciens", "premium starts", "premium sveiks"]:
            await safe_reply_text(update, append_bonus_notices(premium_welcome_answer(user_id), streak_notice), disable_web_page_preview=True)
            return

        if lower in ["pirkt premium", "pirkt basic", "pirkt premium basic"]:
            await safe_reply_text(update, append_bonus_notices(stripe_checkout_answer(user_id, "basic"), streak_notice), disable_web_page_preview=True)
            return

        if lower in ["pirkt plus", "pirkt premium plus"]:
            await safe_reply_text(update, append_bonus_notices(stripe_checkout_answer(user_id, "plus"), streak_notice), disable_web_page_preview=True)
            return

        if lower == "stripe statuss":
            await safe_reply_text(update, append_bonus_notices(stripe_status(user_id), streak_notice), disable_web_page_preview=True)
            return

        # V11.7: Stripe ENV must be separate from Stripe Setup Helper.
        if lower in ["stripe webhook", "webhook", "webhook statuss", "stripe webhook statuss"]:
            await safe_reply_text(update, append_bonus_notices(stripe_webhook_status_answer(user_id), streak_notice), disable_web_page_preview=True)
            return

        if lower in ["stripe env", "stripe environment", "stripe railway", "stripe konfigurācija", "stripe konfiguracija"]:
            await safe_reply_text(update, append_bonus_notices(stripe_env_guide_answer(user_id), streak_notice), disable_web_page_preview=True)
            return

        # V10.5.2: keep Stripe helper commands direct too, not only in command_answer().
        if lower in ["stripe setup", "stripe palīgs", "stripe paligs", "stripe helper", "maksājumi", "maksajumi", "payment setup"]:
            await safe_reply_text(update, append_bonus_notices(stripe_setup_helper(user_id), streak_notice), disable_web_page_preview=True)
            return

        if lower in ["revenue", "ieņēmumi", "ienemumi", "admin panelis", "premium ieņēmumi", "premium ienemumi"]:
            await safe_reply_text(update, append_bonus_notices(admin_revenue_dashboard(user_id, lower), streak_notice), disable_web_page_preview=True)
            return

        if lower in ["revenue analytics", "income analytics", "premium analytics", "ieņēmumu analītika", "ienemumu analitika"]:
            await safe_reply_text(update, append_bonus_notices(admin_revenue_analytics(user_id, lower), streak_notice), disable_web_page_preview=True)
            return

        if lower in ["revenue forecast", "income forecast", "mrr forecast", "ieņēmumu prognoze", "ienemumu prognoze"]:
            await safe_reply_text(update, append_bonus_notices(admin_revenue_forecast(user_id, lower), streak_notice), disable_web_page_preview=True)
            return

        # V10.25: KPI command routing fix — catch KPI before GPT fallback.
        if lower in ["kpi", "admin kpi", "business dashboard", "admin kpi dashboard", "kpi dashboard", "biznesa panelis"]:
            await safe_reply_text(update, append_bonus_notices(admin_kpi_dashboard(user_id, lower), streak_notice), disable_web_page_preview=True)
            return

        # V11.1: Alerts command routing fix — catch Alerts before GPT fallback.
        if lower in ["alerts", "admin alerts", "system alerts", "brīdinājumi", "bridinajumi", "admin brīdinājumi", "admin bridinajumi"]:
            await safe_reply_text(update, append_bonus_notices(admin_alerts_dashboard(user_id, lower), streak_notice), disable_web_page_preview=True)
            return

        # V11.1: Premium Conversion System routing — catch launch before GPT fallback.
        if lower in ["launch", "launch dashboard", "production", "production launch", "palaišana", "palaisana"]:
            await safe_reply_text(update, append_bonus_notices(admin_launch_dashboard(user_id, lower), streak_notice), disable_web_page_preview=True)
            return

        if lower in ["admin logs", "audit logs", "admin žurnāls", "admin zurnals"]:
            await safe_reply_text(update, append_bonus_notices(admin_audit_log_answer(user_id), streak_notice), disable_web_page_preview=True)
            return

        if lower in ["audit stats", "admin statistika", "admin stats"]:
            await safe_reply_text(update, append_bonus_notices(admin_audit_stats_answer(user_id), streak_notice), disable_web_page_preview=True)
            return

        if lower in ["health", "system status", "sistēmas statuss", "sistemas statuss", "veselība", "veseliba"]:
            await safe_reply_text(update, append_bonus_notices(system_health_answer(user_id, lower), streak_notice), disable_web_page_preview=True)
            return

        if lower in ["analytics", "lietotāju statistika", "lietotaju statistika", "user stats", "user analytics"]:
            await safe_reply_text(update, append_bonus_notices(user_analytics_answer(user_id, lower), streak_notice), disable_web_page_preview=True)
            return

        if lower in ["db backup", "database backup", "backup stats", "datubāzes backup", "datubazes backup"]:
            await safe_reply_text(update, append_bonus_notices(database_backup_dashboard(user_id, lower), streak_notice), disable_web_page_preview=True)
            return

        if lower in ["auto backup", "backup scheduler", "backup grafiks", "automātiskais backup", "automatiskais backup"]:
            await safe_reply_text(update, append_bonus_notices(backup_scheduler_answer(user_id, lower), streak_notice), disable_web_page_preview=True)
            return

        if lower in ["recovery", "recovery center", "restore backup", "backup restore"]:
            await safe_reply_text(update, append_bonus_notices(recovery_center_answer(user_id, lower), streak_notice), disable_web_page_preview=True)
            return

        if lower in ["restore latest", "atjauno pēdējo", "atjauno pedejo"]:
            await safe_reply_text(update, append_bonus_notices(restore_latest_backup(user_id, lower), streak_notice), disable_web_page_preview=True)
            return

        if lower in ["admin notifications", "notifications", "paziņojumi", "pazinojumi", "admin paziņojumi", "admin pazinojumi"]:
            await safe_reply_text(update, append_bonus_notices(admin_notifications_center(user_id, lower), streak_notice), disable_web_page_preview=True)
            return

        if lower in ["activity", "admin activity", "activity feed", "aktivitāte", "aktivitate"]:
            await safe_reply_text(update, append_bonus_notices(admin_activity_feed(user_id, lower), streak_notice), disable_web_page_preview=True)
            return

        if lower in ["user management", "admin users", "user dashboard", "lietotāju panelis", "lietotaju panelis"]:
            await safe_reply_text(update, append_bonus_notices(admin_user_management_dashboard(user_id, user_text), streak_notice), disable_web_page_preview=True)
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
            await safe_reply_text(update, append_bonus_notices(admin_user_action(user_id, user_text), streak_notice), disable_web_page_preview=True)
            return

        if (
            lower.startswith("search user")
            or lower.startswith("find user")
            or lower.startswith("meklēt lietotāju")
            or lower.startswith("meklet lietotaju")
            or lower in ["lietotāji", "lietotaji"]
        ):
            await safe_reply_text(update, append_bonus_notices(admin_user_search(user_id, user_text), streak_notice), disable_web_page_preview=True)
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
            await safe_reply_text(update, append_bonus_notices(admin_user_lookup(user_id, user_text), streak_notice), disable_web_page_preview=True)
            return

        # V10.24 Command Routing Fix:
        # Admin Command Center komandām jānostrādā pirms premium dashboard un pirms GPT fallback.
        if lower in ["admin", "admin center", "admin command center", "command center", "dashboard"]:
            await safe_reply_text(update, append_bonus_notices(admin_command_center(user_id, lower), streak_notice), disable_web_page_preview=True)
            return

        if lower in ["premium panelis", "mans panelis"]:
            await safe_reply_text(update, append_bonus_notices(premium_dashboard(user_id), streak_notice, check_achievements(user_id)), disable_web_page_preview=True)
            return

        if lower in ["mans līmenis", "mana pieredze", "xp"]:
            await safe_reply_text(update, append_bonus_notices(user_level_info(user_id), streak_notice, check_achievements(user_id)), disable_web_page_preview=True)
            return

        if lower in ["mani sasniegumi", "sasniegumi"]:
            await safe_reply_text(update, append_bonus_notices(achievements_answer(user_id), streak_notice, check_achievements(user_id)), disable_web_page_preview=True)
            return

        if lower == "sasniegumu progress":
            await safe_reply_text(update, append_bonus_notices(achievement_progress(user_id), streak_notice), disable_web_page_preview=True)
            return

        if lower in ["mans streak", "mana sērija", "streak"]:
            await safe_reply_text(update, append_bonus_notices(streak_info(user_id), check_achievements(user_id)), disable_web_page_preview=True)
            return

        if lower == "mana statistika":
            await safe_reply_text(update, user_statistics(user_id), disable_web_page_preview=True)
            return

        if lower == "mana aktivitāte":
            await safe_reply_text(update, user_activity(user_id), disable_web_page_preview=True)
            return

        if lower == "mana atmiņa":
            await safe_reply_text(update, user_memory_stats(user_id), disable_web_page_preview=True)
            return

        if lower in ["aktivizē premium", "aktivize premium", "ieslēdz premium"]:
            await safe_reply_text(update, activate_premium(user_id), disable_web_page_preview=True)
            return

        if lower in ["izslēdz premium", "atslēdz premium"]:
            await safe_reply_text(update, deactivate_premium(user_id), disable_web_page_preview=True)
            return

        if lower in ["eksportē atmiņu", "atmiņas eksports", "export memory", "eksports"]:
            await safe_reply_text(update, build_memory_export(user_id), disable_web_page_preview=True)
            return

        if lower in ["backup", "izveido backup", "rezerves kopija", "izveido rezerves kopiju"]:
            await safe_reply_text(update, create_backup_answer(user_id), disable_web_page_preview=True)
            return

        if lower in ["pēdējais backup", "parādi backup", "mans backup", "pēdējā rezerves kopija"]:
            await safe_reply_text(update, latest_backup_answer(user_id), disable_web_page_preview=True)
            return

        if lower in ["backup saraksts", "parādi backup sarakstu", "mani backup"]:
            await safe_reply_text(update, list_backups(user_id), disable_web_page_preview=True)
            return

        if lower in ["cik man ir backup"]:
            await safe_reply_text(update, backup_count(user_id), disable_web_page_preview=True)
            return

        if lower in ["backup statistika"]:
            await safe_reply_text(update, backup_stats(user_id), disable_web_page_preview=True)
            return

        if lower in ["jaunākais backup"]:
            await safe_reply_text(update, latest_backup_info(user_id), disable_web_page_preview=True)
            return

        if lower in ["dzēs visus backup", "izdzēs visus backup"]:
            await safe_reply_text(update, delete_all_backups(user_id), disable_web_page_preview=True)
            return

        if lower.startswith("dzēs backup") or lower.startswith("izdzēs backup"):
            await safe_reply_text(update, delete_backup(user_id, user_text), disable_web_page_preview=True)
            return

        if lower.startswith("atjauno no backup"):
            await safe_reply_text(update, restore_backup(user_id, user_text), disable_web_page_preview=True)
            return

        if lower.startswith("atgādini man"):
            await safe_reply_text(update, add_reminder(user_id, user_text), disable_web_page_preview=True)
            return

        if lower in ["mani atgādinājumi", "parādi atgādinājumus", "atgādinājumi"]:
            await safe_reply_text(update, list_reminders(user_id), disable_web_page_preview=True)
            return

        if lower.startswith("dzēs atgādinājumu") or lower.startswith("izdzēs atgādinājumu"):
            await safe_reply_text(update, delete_reminder(user_id, user_text), disable_web_page_preview=True)
            return

        if lower.startswith("aizmirsti atgādinājumu"):
            await safe_reply_text(update, delete_reminder(user_id, user_text), disable_web_page_preview=True)
            return

        if lower.startswith("aizmirsti"):
            await safe_reply_text(update, forget_from_profile(user_id, user_text), disable_web_page_preview=True)
            return

        if lower in ["atjauno kopsavilkumu", "izveido kopsavilkumu", "atjauno atmiņu"]:
            await safe_reply_text(update, build_summary(user_id), disable_web_page_preview=True)
            return

        if lower in ["mans kopsavilkums", "parādi kopsavilkumu", "ilgtermiņa atmiņa"]:
            await safe_reply_text(update, show_summary(user_id), disable_web_page_preview=True)
            return

        update_profile_from_text(user_id, user_text)
        user = get_user(user_id)

        if "mana laika zona" in lower or "kur es dzīvoju" in lower or "es dzīvoju" in lower:
            await safe_reply_text(update, f"Saglabāju. Tava laika zona: {user['timezone']}", disable_web_page_preview=True)
            return

        if "kā mani sauc" in lower:
            await safe_reply_text(update, f"Tevi sauc {user['name']}. 😊" if user["name"] else "Tu vēl neesi pateicis savu vārdu. 😊", disable_web_page_preview=True)
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
            await safe_reply_text(update, profile_answer(user), disable_web_page_preview=True)
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
        await safe_reply_text(update, answer, disable_web_page_preview=True)



        # V114.0: Final catch-all so Nina never stays silent.
        if is_short_unknown_message(user_text):
            await safe_reply_text(update, nina_public_offer_answer(user_text))
            return

    except Exception as e:
        print("Publiskā reply kļūda:", e)
        await safe_reply_text(update, public_test_fallback_answer())
        return


def activate_premium_from_stripe(user_id, plan_key="basic", stripe_session_id="", stripe_event_id="", customer_email=""):
    """V11.9 Stripe Test Router Fix — ieslēdz Premium pēc Stripe maksājuma."""
    if not user_id:
        return False, "missing_user_id"

    user_id = str(user_id)
    user = get_user(user_id)

    if plan_key == "plus":
        plan_name = PLAN_PREMIUM_PLUS
        amount = PREMIUM_PLUS_PRICE
    else:
        plan_name = PLAN_PREMIUM_BASIC
        amount = PREMIUM_BASIC_PRICE

    user_tz = ZoneInfo(user.get("timezone") or DEFAULT_TIMEZONE)
    premium_until = (datetime.now(user_tz) + timedelta(days=30)).strftime("%Y-%m-%d")

    user["premium"] = 1
    user["premium_until"] = premium_until
    update_user(user_id, user)

    record_premium_transaction(
        user_id=user_id,
        plan_name=plan_name,
        amount=amount,
        currency=PREMIUM_CURRENCY,
        payment_method="stripe_webhook",
        status="paid",
        expires_at=premium_until,
        checkout_url="",
        stripe_session_id=stripe_session_id or "",
        stripe_event_id=stripe_event_id or "",
        customer_email=customer_email or "",
    )

    # V12.4: ja šis Premium nāk no referral, piešķiram bonusu uzaicinātājam.
    try:
        apply_referral_reward(user_id)
    except Exception as e:
        print("Referral reward pēc Stripe kļūda:", e)

    return True, premium_until


def stripe_webhook_status_answer(user_id=None):
    """V11.7: parāda Stripe webhook statusu un URL."""
    railway_domain = os.environ.get("RAILWAY_PUBLIC_DOMAIN", "TAVS-RAILWAY-DOMENS")
    webhook_url = f"https://{railway_domain}/stripe/webhook"

    return (
        "🔌 Nina Stripe Webhook\n\n"
        f"Webhook Secret: {'✅' if STRIPE_WEBHOOK_SECRET else '❌'}\n"
        f"Stripe package: {'✅' if stripe else '❌'}\n\n"
        "Stripe Dashboard pievieno webhook endpoint:\n"
        f"{webhook_url}\n\n"
        "Event:\n"
        "checkout.session.completed\n\n"
        "Ko dara webhook:\n"
        "1. saņem Stripe maksājumu\n"
        "2. nolasa telegram_user_id\n"
        "3. ieslēdz Premium uz 30 dienām\n"
        "4. saglabā premium_transactions\n\n"
        "Versija: V114.0"
    )




# =========================
# V12.5.3 WEBHOOK FINAL SAFE HELPERS
# =========================

def stripe_value(obj, key, default=None):
    """Droši nolasa vērtību no StripeObject vai dict."""
    try:
        if isinstance(obj, dict):
            return obj.get(key, default)
        value = getattr(obj, key, default)
        return default if value is None else value
    except Exception:
        return default


def stripe_to_dict(obj):
    """StripeObject/dict pārvērš vienkāršā dict, ja iespējams."""
    try:
        if isinstance(obj, dict):
            return obj
        if hasattr(obj, "to_dict_recursive"):
            return obj.to_dict_recursive()
        if hasattr(obj, "to_dict"):
            return obj.to_dict()
    except Exception:
        pass
    return {}

@app.route("/stripe/webhook", methods=["POST"])
def stripe_webhook():
    """V12.5.3: Stripe webhook final fix — Premium aktivizācija bez 500 kļūdām."""
    if not stripe:
        return jsonify({"ok": False, "error": "stripe_library_missing"}), 400

    payload = request.get_data()
    sig_header = request.headers.get("Stripe-Signature", "")

    try:
        if STRIPE_WEBHOOK_SECRET:
            event = stripe.Webhook.construct_event(payload, sig_header, STRIPE_WEBHOOK_SECRET)
        else:
            event = json.loads(payload.decode("utf-8"))
    except Exception as e:
        print("Stripe webhook signature/event kļūda:", e)
        return jsonify({"ok": False, "error": "invalid_webhook", "details": str(e)}), 400

    try:
        event_type = stripe_value(event, "type", "")
        event_id = stripe_value(event, "id", "")

        if event_type != "checkout.session.completed":
            return jsonify({"ok": True, "ignored": event_type}), 200

        data = stripe_value(event, "data", {}) or {}
        session = stripe_value(data, "object", {}) or {}

        session_dict = stripe_to_dict(session)

        metadata = stripe_value(session, "metadata", {}) or session_dict.get("metadata", {}) or {}
        try:
            metadata = dict(metadata)
        except Exception:
            metadata = {}

        customer_details = stripe_value(session, "customer_details", {}) or session_dict.get("customer_details", {}) or {}
        try:
            customer_details = dict(customer_details)
        except Exception:
            customer_details = {}

        user_id = (
            metadata.get("telegram_user_id")
            or stripe_value(session, "client_reference_id", "")
            or session_dict.get("client_reference_id", "")
            or metadata.get("user_id")
            or ""
        )
        user_id = str(user_id).strip()

        plan_key = str(metadata.get("plan_key", "basic") or "basic").strip().lower()
        session_id = str(stripe_value(session, "id", "") or session_dict.get("id", "") or "")
        customer_email = (
            customer_details.get("email")
            or stripe_value(session, "customer_email", "")
            or session_dict.get("customer_email", "")
            or ""
        )

        if not user_id:
            print("Stripe webhook: missing_user_id; session_id=", session_id, "metadata=", metadata)
            return jsonify({"ok": True, "status": "missing_user_id", "session_id": session_id}), 200

        ok, result = activate_premium_from_stripe(
            user_id=user_id,
            plan_key=plan_key,
            stripe_session_id=session_id,
            stripe_event_id=str(event_id or ""),
            customer_email=str(customer_email or ""),
        )

        if not ok:
            print("Stripe webhook: activation_failed", result)
            return jsonify({"ok": True, "status": "activation_failed", "error": result}), 200

        return jsonify({
            "ok": True,
            "premium_activated": True,
            "user_id": str(user_id),
            "premium_until": result,
            "version": "V12.5.3",
        }), 200

    except Exception as e:
        print("Stripe webhook apstrādes kļūda:", e)
        return jsonify({"ok": True, "status": "webhook_processing_error", "error": str(e)}), 200



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
    return "Nina7727 V114.0 Premium Sales Text darbojas! DB: " + ("PostgreSQL" if USE_POSTGRES else "SQLite fallback")


init_db()

telegram_app = (
    Application.builder()
    .token(TELEGRAM_TOKEN)
    .post_init(post_init)
    .build()
)

telegram_app.add_handler(CommandHandler("start", start_command))
telegram_app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
telegram_app.add_handler(MessageHandler(filters.LOCATION, handle_location))
telegram_app.add_handler(MessageHandler(filters.VOICE | filters.AUDIO | filters.Document.AUDIO, handle_voice))
telegram_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, reply))

def run_flask_server():
    """V12.5.1: Railway HTTP server for Stripe webhook and success/cancel pages."""
    port = int(os.environ.get("PORT", "8080"))
    print(f"Nina Flask server starting on port {port}...")
    app.run(host="0.0.0.0", port=port, debug=False, use_reloader=False)


if __name__ == "__main__":
    print("Nina7727 V114.0 Premium Sales Text darbojas...", "PostgreSQL" if USE_POSTGRES else "SQLite fallback")

    # Stripe webhook vajag HTTP serveri. Telegram botam vienlaikus vajag polling.
    # Tāpēc Flask palaižam background threadā, bet Telegram polling atstājam galvenajā procesā.
    flask_thread = threading.Thread(target=run_flask_server, daemon=True)
    flask_thread.start()

    telegram_app.run_polling()

def stripe_production_checklist_answer(user_id=None):
    checks = [
        ("stripe package", bool(stripe)),
        ("STRIPE_SECRET_KEY", bool(STRIPE_SECRET_KEY)),
        ("STRIPE_BASIC_PRICE_ID", bool(STRIPE_BASIC_PRICE_ID)),
        ("STRIPE_SUCCESS_URL", bool(STRIPE_SUCCESS_URL and STRIPE_SUCCESS_URL != "https://t.me/")),
        ("STRIPE_CANCEL_URL", bool(STRIPE_CANCEL_URL and STRIPE_CANCEL_URL != "https://t.me/")),
        ("STRIPE_WEBHOOK_SECRET", bool(STRIPE_WEBHOOK_SECRET)),
    ]

    ready = sum(1 for _, ok in checks if ok)
    percent = int((ready / len(checks)) * 100)

    lines = [
        "🚀 Nina Stripe Production Checklist",
        "",
    ]

    for name, ok in checks:
        lines.append(("✅ " if ok else "❌ ") + name)

    lines.extend([
        "",
        f"Gatavība: {percent}%",
        "",
        "Pirms palaišanas:",
        "1. Pievieno Stripe package",
        "2. Uzstādi Railway ENV",
        "3. Izveido Stripe Product + Price",
        "4. Aktivizē webhook",
        "5. Testē: stripe test",
        "6. Testē: pirkt basic",
        "",
        "Versija: V114.0"
    ])
    return "\\n".join(lines)

# =========================
# V12.0 REAL MONETIZATION LAUNCH
# =========================

def revenue_dashboard_answer(user_id=None):
    return (
        "💰 Nina Revenue Dashboard\n\n"
        "Mērķis: pirmie maksājošie lietotāji\n"
        "Fokuss:\n"
        "• Premium pārdošana\n"
        "• Referral sistēma\n"
        "• Stripe Checkout\n"
        "• Telegram izplatīšana\n\n"
        "Komandas:\n"
        "revenue\n"
        "launch\n"
        "referral\n"
        "invite\n"
        "sales\n\n"
        "Versija: V114.0"
    )

def referral_answer(user_id):
    return (
        "👥 Nina Referral\n\n"
        f"Tavs referral kods: NINA-{user_id}\n\n"
        "Dalies ar Ninu un aicini draugus.\n"
        "Nākamais solis: pieslēgt automātisku referral uzskaiti.\n\n"
        "Versija: V114.0"
    )

# =========================
# V12.2 REAL REFERRAL TRACKING
# =========================
def referral_start_code(text):
    try:
        if text.startswith("/start NINA-"):
            return text.split("/start ",1)[1].strip()
    except Exception:
        pass
    return ""
