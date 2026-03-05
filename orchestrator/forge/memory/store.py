"""Memory store — CRUD for persistent agent memories in Supabase."""

from __future__ import annotations

import uuid
from typing import Optional

from ..db import get_db


def save_memory(
    content: str,
    category: str = "general",
    project_id: Optional[str] = None,
) -> str:
    """Save a memory and return its ID."""
    db = get_db()
    memory_id = str(uuid.uuid4())
    db.table("memories").insert({
        "id": memory_id,
        "project_id": project_id,
        "content": content,
        "category": category,
    }).execute()
    return memory_id


def get_memories(
    project_id: Optional[str] = None,
    category: Optional[str] = None,
    limit: int = 50,
) -> list[dict]:
    """Retrieve memories, optionally filtered by project and category."""
    db = get_db()
    query = db.table("memories").select("*").order("created_at", desc=True).limit(limit)

    if project_id:
        query = query.eq("project_id", project_id)
    if category:
        query = query.eq("category", category)

    result = query.execute()
    return result.data


def delete_memory(memory_id: str) -> None:
    """Delete a memory by ID."""
    db = get_db()
    db.table("memories").delete().eq("id", memory_id).execute()
