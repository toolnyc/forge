"""Context assembly — builds the full context for an agent from project + memories."""

from __future__ import annotations

from typing import Optional

from ..db import get_db


def assemble_context(project_id: Optional[str] = None) -> str:
    """Build context string from project data and memories."""
    if not project_id:
        return ""

    db = get_db()
    parts: list[str] = []

    # Project context (CLAUDE.md equivalent)
    project = db.table("projects").select("name, context, stack").eq("id", project_id).single().execute()
    if project.data:
        parts.append(f"# Project: {project.data['name']}")
        if project.data.get("stack"):
            parts.append(f"Stack: {project.data['stack']}")
        parts.append(project.data["context"])

    # Memories
    memories = (
        db.table("memories")
        .select("content, category")
        .eq("project_id", project_id)
        .order("created_at", desc=True)
        .limit(20)
        .execute()
    )
    if memories.data:
        parts.append("\n# Relevant Memories")
        for m in memories.data:
            parts.append(f"- [{m['category']}] {m['content']}")

    return "\n\n".join(parts)
