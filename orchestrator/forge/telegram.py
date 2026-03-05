"""Forge orchestrator Telegram bot.

Provides /ask, /tasks, /task, /costs, /health commands.
/ask inserts a pending task and polls until the worker completes it.
start_bot() wires up the Application for polling mode.
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import datetime, timedelta, timezone

from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

from .config import config
from .db import get_db
from .router import route

log = logging.getLogger("forge.telegram")


def _authorized(update: Update) -> bool:
    if not config.telegram_chat_id or not update.effective_chat:
        return False
    return str(update.effective_chat.id) == config.telegram_chat_id


def _truncate(text: str, limit: int = 4000) -> str:
    if len(text) <= limit:
        return text
    return text[:limit] + "\n\n... (truncated)"


async def cmd_ask(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    """/ask <prompt> — Insert pending task, wait for worker to complete it."""
    if not _authorized(update):
        return

    prompt = (update.message.text or "").removeprefix("/ask").strip()
    if not prompt:
        await update.message.reply_text("Usage: /ask <prompt>")
        return

    await update.message.reply_text("Working...")

    try:
        db = get_db()
        decision = route(prompt)
        task_id = str(uuid.uuid4())

        db.table("tasks").insert({
            "id": task_id,
            "title": f"{decision.agent_name}: {prompt[:80]}",
            "description": prompt,
            "status": "pending",
            "input": {
                "prompt": prompt,
                "source": "telegram",
                "routed_agent": decision.agent_name,
                "routed_model": decision.model,
                "routed_task_type": decision.task_type,
            },
            "task_type": decision.task_type,
            "agent_name": decision.agent_name,
        }).execute()

        # Poll for completion (worker picks it up)
        for _ in range(120):  # ~6 minutes max
            await asyncio.sleep(3)
            result = db.table("tasks").select("status, output").eq("id", task_id).execute()
            if not result.data:
                break
            task = result.data[0]
            if task["status"] in ("complete", "failed"):
                break
        else:
            await update.message.reply_text("Task is still running. Check back with /task")
            return

        if task["status"] == "failed":
            error = task.get("output", {}).get("error", "Unknown error")
            await update.message.reply_text(f"Failed: {error}")
            return

        output = task.get("output") or {}
        response = output.get("response", "No response")
        judgment = output.get("judgment")

        msg = ""
        if judgment:
            msg += f"Judge: {judgment['verdict']} (attempt {judgment['attempt']})\n\n"
        msg += response

        await update.message.reply_text(_truncate(msg))

    except Exception as e:
        log.exception("Error in /ask")
        await update.message.reply_text(f"Error: {e}")


async def cmd_tasks(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    """/tasks — List 10 recent tasks."""
    if not _authorized(update):
        return

    try:
        db = get_db()
        result = (
            db.table("tasks")
            .select("id, title, status, created_at")
            .order("created_at", desc=True)
            .limit(10)
            .execute()
        )

        if not result.data:
            await update.message.reply_text("No tasks found.")
            return

        lines = ["Recent tasks:\n"]
        for t in result.data:
            status = t["status"]
            label = {
                "complete": "done",
                "running": "run",
                "failed": "FAIL",
                "pending": "wait",
            }.get(status, status)
            lines.append(f"{t['id'][:8]} [{label}] {t['title'][:40]}")

        await update.message.reply_text("\n".join(lines))

    except Exception as e:
        log.exception("Error in /tasks")
        await update.message.reply_text(f"Error: {e}")


async def cmd_task(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    """/task <id> — Task detail + judgment verdict."""
    if not _authorized(update):
        return

    task_id = (update.message.text or "").removeprefix("/task").strip()
    if not task_id:
        await update.message.reply_text("Usage: /task <id>")
        return

    try:
        db = get_db()
        result = (
            db.table("tasks")
            .select("*")
            .like("id", f"{task_id}%")
            .limit(1)
            .execute()
        )

        if not result.data:
            await update.message.reply_text(f"Task not found: {task_id}")
            return

        t = result.data[0]
        tokens = f"{t.get('tokens_in', 0)} in / {t.get('tokens_out', 0)} out"

        msg = (
            f"{t['title']}\n"
            f"Status: {t['status']}\n"
            f"Agent: {t.get('agent_name', '-')}\n"
            f"Model: {t.get('model_used', '-')}\n"
            f"Tokens: {tokens}\n"
        )

        if isinstance(t.get("output"), dict) and t["output"].get("judgment"):
            j = t["output"]["judgment"]
            msg += f"Judgment: {j['verdict']} (attempt {j['attempt']})\n"

        if isinstance(t.get("output"), dict) and "response" in t["output"]:
            msg += f"\n{t['output']['response']}"

        await update.message.reply_text(_truncate(msg))

    except Exception as e:
        log.exception("Error in /task")
        await update.message.reply_text(f"Error: {e}")


async def cmd_costs(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    """/costs — Today / this week / total spend by model."""
    if not _authorized(update):
        return

    try:
        db = get_db()
        now = datetime.now(timezone.utc)
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
        week_start = (now - timedelta(days=7)).isoformat()

        all_costs = db.table("cost_log").select("model, cost_usd, created_at").execute()
        rows = all_costs.data or []

        total = 0.0
        today_total = 0.0
        week_total = 0.0
        by_model: dict[str, float] = {}

        for r in rows:
            cost = float(r.get("cost_usd", 0))
            model = r.get("model", "unknown")
            total += cost
            by_model[model] = by_model.get(model, 0) + cost

            created = r.get("created_at", "")
            if created >= today_start:
                today_total += cost
            if created >= week_start:
                week_total += cost

        lines = [
            f"Today: ${today_total:.4f}",
            f"This week: ${week_total:.4f}",
            f"Total: ${total:.4f}",
            "",
            "By model:",
        ]
        for model, cost in sorted(by_model.items(), key=lambda x: -x[1]):
            lines.append(f"  {model}: ${cost:.4f}")

        await update.message.reply_text("\n".join(lines))

    except Exception as e:
        log.exception("Error in /costs")
        await update.message.reply_text(f"Error: {e}")


async def cmd_health(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    """/health — Supabase connectivity, last task, today's spend."""
    if not _authorized(update):
        return

    try:
        db = get_db()

        last_task = (
            db.table("tasks")
            .select("id, title, status, created_at")
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        )

        now = datetime.now(timezone.utc)
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
        today_costs = (
            db.table("cost_log")
            .select("cost_usd")
            .gte("created_at", today_start)
            .execute()
        )
        today_spend = sum(float(r.get("cost_usd", 0)) for r in (today_costs.data or []))

        lines = ["Forge Health Check", "", "Supabase: connected"]

        if last_task.data:
            t = last_task.data[0]
            lines.append(f"Last task: {t['title'][:40]} [{t['status']}]")
            lines.append(f"  at {t['created_at'][:19]}")
        else:
            lines.append("Last task: none")

        lines.append(f"Today's spend: ${today_spend:.4f}")

        await update.message.reply_text("\n".join(lines))

    except Exception as e:
        log.exception("Error in /health")
        await update.message.reply_text(f"Forge Health Check\n\nSupabase: ERROR\n{e}")


def create_bot_app() -> Application:
    """Build the Telegram Application with all command handlers."""
    if not config.telegram_bot_token:
        msg = "TELEGRAM_BOT_TOKEN not set"
        raise RuntimeError(msg)

    application = Application.builder().token(config.telegram_bot_token).build()
    application.add_handler(CommandHandler("ask", cmd_ask))
    application.add_handler(CommandHandler("tasks", cmd_tasks))
    application.add_handler(CommandHandler("task", cmd_task))
    application.add_handler(CommandHandler("costs", cmd_costs))
    application.add_handler(CommandHandler("health", cmd_health))
    return application


async def start_bot() -> None:
    """Start the Telegram bot in polling mode (runs forever)."""
    application = create_bot_app()
    log.info("Telegram bot starting...")
    await application.initialize()
    await application.start()
    await application.updater.start_polling()

    # Keep running until cancelled
    try:
        while True:
            await asyncio.sleep(3600)
    except asyncio.CancelledError:
        log.info("Telegram bot shutting down")
    finally:
        await application.updater.stop()
        await application.stop()
        await application.shutdown()
