"""Background worker — polls pending tasks and runs them through agents."""

from __future__ import annotations

import asyncio
import logging

from .agents import research_agent
from .db import get_db

log = logging.getLogger("forge.worker")

# Agent registry — add new agents here
_AGENTS = {
    "research": research_agent,
}


def _get_agent(name: str):
    return _AGENTS.get(name, research_agent)


async def process_task(task_data: dict) -> None:
    """Route and execute a single task."""
    task_id = task_data["id"]
    input_data = task_data.get("input") or {}
    prompt = input_data.get("prompt") or task_data.get("description", "")
    agent_name = input_data.get("routed_agent") or task_data.get("agent_name", "research")
    model = input_data.get("routed_model")
    task_type = input_data.get("routed_task_type") or task_data.get("task_type", "general")
    project_id = task_data.get("project_id")

    if not prompt:
        db = get_db()
        db.table("tasks").update({
            "status": "failed",
            "output": {"error": "No prompt found in task"},
        }).eq("id", task_id).execute()
        return

    agent = _get_agent(agent_name)
    log.info("Processing task %s with agent=%s model=%s", task_id[:8], agent_name, model)

    try:
        await agent.run_task(
            task_id=task_id,
            prompt=prompt,
            project_id=project_id,
            model=model,
            task_type=task_type,
        )
        log.info("Task %s completed", task_id[:8])
    except Exception:
        log.exception("Task %s failed", task_id[:8])


async def run_worker(poll_interval: float = 3.0) -> None:
    """Poll for pending tasks and process them one at a time."""
    log.info("Worker started, polling every %.1fs", poll_interval)

    while True:
        try:
            db = get_db()
            result = (
                db.table("tasks")
                .select("*")
                .eq("status", "pending")
                .order("created_at")
                .limit(1)
                .execute()
            )

            if result.data:
                await process_task(result.data[0])
            else:
                await asyncio.sleep(poll_interval)

        except asyncio.CancelledError:
            log.info("Worker shutting down")
            break
        except Exception:
            log.exception("Worker error, retrying in %ss", poll_interval)
            await asyncio.sleep(poll_interval)
