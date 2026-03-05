"""FastAPI routes for projects, tasks, and costs."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from ..db import get_db

router = APIRouter()


# --- Pydantic schemas ---


class ProjectCreate(BaseModel):
    name: str
    slug: str
    context: str | None = None
    stack: str | None = None


class ProjectResponse(BaseModel):
    id: str
    name: str
    slug: str
    context: str | None
    stack: str | None
    created_at: str


class TaskCreate(BaseModel):
    title: str
    description: str | None = None
    project_id: str | None = None
    input: dict[str, Any] | None = None


class TaskResponse(BaseModel):
    id: str
    project_id: str | None
    title: str
    description: str | None
    status: str
    input: dict[str, Any] | None
    output: dict[str, Any] | None
    tokens_in: int | None
    tokens_out: int | None
    cost_usd: float | None
    model_used: str | None
    created_at: str
    started_at: str | None
    completed_at: str | None


class CostSummaryItem(BaseModel):
    model: str
    total_cost: float
    call_count: int


# --- Project endpoints ---


@router.get("/projects", response_model=list[ProjectResponse])
def list_projects() -> list[ProjectResponse]:
    db = get_db()
    result = db.table("projects").select("*").order("name").execute()
    return [ProjectResponse(**row) for row in result.data]


@router.get("/projects/{project_id}", response_model=ProjectResponse)
def get_project(project_id: str) -> ProjectResponse:
    db = get_db()
    result = db.table("projects").select("*").eq("id", project_id).single().execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="Project not found")
    return ProjectResponse(**result.data)


@router.post("/projects", response_model=ProjectResponse, status_code=201)
def create_project(body: ProjectCreate) -> ProjectResponse:
    db = get_db()
    result = db.table("projects").insert(body.model_dump()).execute()
    if not result.data:
        raise HTTPException(status_code=500, detail="Failed to create project")
    return ProjectResponse(**result.data[0])


# --- Task endpoints ---


@router.get("/tasks", response_model=list[TaskResponse])
def list_tasks(
    status: str | None = Query(None),
    project_id: str | None = Query(None),
    limit: int = Query(50, le=500),
) -> list[TaskResponse]:
    db = get_db()
    query = (
        db.table("tasks")
        .select("*")
        .order("created_at", desc=True)
        .limit(limit)
    )
    if status:
        query = query.eq("status", status)
    if project_id:
        query = query.eq("project_id", project_id)
    result = query.execute()
    return [TaskResponse(**row) for row in result.data]


@router.get("/tasks/{task_id}", response_model=TaskResponse)
def get_task(task_id: str) -> TaskResponse:
    db = get_db()
    result = db.table("tasks").select("*").eq("id", task_id).single().execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="Task not found")
    return TaskResponse(**result.data)


@router.post("/tasks", response_model=TaskResponse, status_code=201)
def create_task(body: TaskCreate) -> TaskResponse:
    db = get_db()
    payload = {**body.model_dump(), "status": "pending"}
    result = db.table("tasks").insert(payload).execute()
    if not result.data:
        raise HTTPException(status_code=500, detail="Failed to create task")
    return TaskResponse(**result.data[0])


# --- Cost endpoints ---


@router.get("/costs", response_model=list[CostSummaryItem])
def get_costs(days: int = Query(30, ge=1, le=365)) -> list[CostSummaryItem]:
    db = get_db()
    since = (datetime.now(tz=timezone.utc) - timedelta(days=days)).isoformat()
    result = (
        db.table("cost_log")
        .select("model, cost_usd")
        .gte("created_at", since)
        .execute()
    )

    totals: dict[str, dict[str, Any]] = {}
    for row in result.data:
        model = row.get("model") or "unknown"
        if model not in totals:
            totals[model] = {"model": model, "total_cost": 0.0, "call_count": 0}
        totals[model]["total_cost"] += float(row.get("cost_usd") or 0)
        totals[model]["call_count"] += 1

    return [CostSummaryItem(**v) for v in sorted(totals.values(), key=lambda x: x["model"])]
