"""Async task worker — polls pending tasks and dispatches to agents."""

from __future__ import annotations

import asyncio
import logging

from .agents import research_agent
from .agents.base import ForgeAgent
from .db import get_db

logger = logging.getLogger(__name__)

POLL_INTERVAL = 10  # seconds


def _get_agent(task: dict) -> ForgeAgent:
    """Dispatch logic: pick an agent based on task metadata."""
    title: str = task.get("title") or ""
    agent_type: str = (task.get("input") or {}).get("agent_type", "")

    if agent_type == "research" or title.startswith("Research:"):
        return research_agent

    # Default: research agent (only one exists right now)
    return research_agent


async def _process_task(task: dict) -> None:
    """Run a single pending task through the appropriate agent."""
    task_id: str = task["id"]
    project_id: str | None = task.get("project_id")
    prompt: str = (task.get("input") or {}).get("prompt") or task.get("description") or ""

    agent = _get_agent(task)
    logger.info("Dispatching task %s to agent '%s'", task_id[:8], agent.name)

    try:
        await agent.run_task(task_id=task_id, prompt=prompt, project_id=project_id)
        logger.info("Task %s complete", task_id[:8])
    except Exception as exc:
        # base.py already marks the task failed; just log and continue
        logger.error("Task %s failed: %s", task_id[:8], exc)


async def worker_loop() -> None:
    """Poll the tasks table for pending work and dispatch one at a time."""
    db = get_db()
    logger.info("Worker started — polling every %ds", POLL_INTERVAL)

    while True:
        try:
            result = (
                db.table("tasks")
                .select("id, project_id, title, description, input")
                .eq("status", "pending")
                .order("created_at")
                .limit(1)
                .execute()
            )
            if result.data:
                await _process_task(result.data[0])
            else:
                logger.debug("No pending tasks")
        except Exception as exc:
            logger.error("Worker poll error: %s", exc)

        await asyncio.sleep(POLL_INTERVAL)
