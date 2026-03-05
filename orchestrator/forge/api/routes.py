"""Forge API route handlers."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel

from ..config import config
from ..db import get_db
from ..models import get_available_models, invalidate_cache
from ..router import route

router = APIRouter()


# ---------- Auth ----------

def _check_auth(authorization: str = Header(default="")) -> None:
    """Verify bearer token matches FORGE_API_KEY."""
    if not config.api_key:
        return  # no key configured = open (dev mode)
    token = authorization.removeprefix("Bearer ").strip()
    if token != config.api_key:
        raise HTTPException(status_code=401, detail="Unauthorized")


# ---------- Request / response models ----------

class TaskSubmit(BaseModel):
    prompt: str
    project_slug: str | None = None
    source: str = "api"


class ModelUpdate(BaseModel):
    enabled: bool | None = None
    priority: int | None = None


# ---------- Endpoints ----------

@router.post("/tasks", dependencies=[Depends(_check_auth)])
async def create_task(body: TaskSubmit) -> dict[str, Any]:
    """Create a pending task. The background worker picks it up."""
    db = get_db()
    decision = route(body.prompt)

    # Resolve project ID from slug
    project_id = None
    if body.project_slug:
        result = (
            db.table("projects").select("id").eq("slug", body.project_slug).limit(1).execute()
        )
        if result.data:
            project_id = result.data[0]["id"]

    task_id = str(uuid.uuid4())
    db.table("tasks").insert({
        "id": task_id,
        "project_id": project_id,
        "title": f"{decision.agent_name}: {body.prompt[:80]}",
        "description": body.prompt,
        "status": "pending",
        "input": {
            "prompt": body.prompt,
            "source": body.source,
            "routed_agent": decision.agent_name,
            "routed_model": decision.model,
            "routed_task_type": decision.task_type,
        },
        "task_type": decision.task_type,
        "agent_name": decision.agent_name,
    }).execute()

    return {"task_id": task_id, "status": "pending", "agent": decision.agent_name}


@router.get("/tasks", dependencies=[Depends(_check_auth)])
async def list_tasks(
    status: str | None = None,
    limit: int = 20,
) -> list[dict[str, Any]]:
    """List tasks, optionally filtered by status."""
    db = get_db()
    query = (
        db.table("tasks")
        .select("id, title, status, model_used, task_type, agent_name, tokens_in, tokens_out, created_at, completed_at")
        .order("created_at", desc=True)
        .limit(limit)
    )
    if status:
        query = query.eq("status", status)
    result = query.execute()
    return result.data or []


@router.get("/tasks/{task_id}", dependencies=[Depends(_check_auth)])
async def get_task(task_id: str) -> dict[str, Any]:
    """Get a single task with full output."""
    db = get_db()
    result = db.table("tasks").select("*").like("id", f"{task_id}%").limit(1).execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="Task not found")
    return result.data[0]


@router.get("/costs", dependencies=[Depends(_check_auth)])
async def get_costs() -> dict[str, Any]:
    """Cost summary: today, this week, total, by model."""
    db = get_db()
    now = datetime.now(timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
    week_start = (now - timedelta(days=7)).isoformat()

    rows = (db.table("cost_log").select("model, cost_usd, created_at").execute()).data or []

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

    return {
        "today": round(today_total, 6),
        "this_week": round(week_total, 6),
        "total": round(total, 6),
        "by_model": {k: round(v, 6) for k, v in sorted(by_model.items(), key=lambda x: -x[1])},
    }


@router.get("/health")
async def health() -> dict[str, Any]:
    """Health check — DB connectivity, last task, today's spend."""
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
            db.table("cost_log").select("cost_usd").gte("created_at", today_start).execute()
        )
        today_spend = sum(float(r.get("cost_usd", 0)) for r in (today_costs.data or []))

        return {
            "status": "ok",
            "supabase": "connected",
            "last_task": last_task.data[0] if last_task.data else None,
            "today_spend": round(today_spend, 6),
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}


@router.get("/projects", dependencies=[Depends(_check_auth)])
async def list_projects() -> list[dict[str, Any]]:
    """List all projects."""
    db = get_db()
    result = db.table("projects").select("id, name, slug, created_at").order("name").execute()
    return result.data or []


@router.get("/models", dependencies=[Depends(_check_auth)])
async def list_models() -> list[dict[str, Any]]:
    """List models from registry."""
    db = get_db()
    result = db.table("model_registry").select("*").order("priority").execute()
    return result.data or []


@router.patch("/models/{model_id}", dependencies=[Depends(_check_auth)])
async def update_model(model_id: str, body: ModelUpdate) -> dict[str, Any]:
    """Toggle enabled or update priority for a model."""
    db = get_db()
    updates: dict[str, Any] = {}
    if body.enabled is not None:
        updates["enabled"] = body.enabled
    if body.priority is not None:
        updates["priority"] = body.priority

    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")

    result = db.table("model_registry").update(updates).eq("id", model_id).execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="Model not found")

    invalidate_cache()
    return result.data[0]
