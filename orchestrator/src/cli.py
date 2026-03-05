"""Forge CLI — dispatch tasks, check status, view results."""

from __future__ import annotations

import asyncio
import uuid
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

from .db import get_db
from .agents import research_agent

app = typer.Typer(name="forge", help="Forge Agent Orchestrator CLI")
console = Console()


@app.command()
def research(
    prompt: str = typer.Argument(..., help="Research prompt"),
    project: Optional[str] = typer.Option(None, "--project", "-p", help="Project slug"),
):
    """Dispatch a research task."""
    db = get_db()
    task_id = str(uuid.uuid4())

    # Resolve project ID from slug
    project_id = None
    if project:
        result = db.table("projects").select("id").eq("slug", project).single().execute()
        if result.data:
            project_id = result.data["id"]
        else:
            console.print(f"[red]Project '{project}' not found[/red]")
            raise typer.Exit(1)

    # Create task record
    db.table("tasks").insert({
        "id": task_id,
        "project_id": project_id,
        "title": f"Research: {prompt[:80]}",
        "description": prompt,
        "status": "pending",
        "input": {"prompt": prompt},
    }).execute()

    console.print(f"[green]Task created:[/green] {task_id}")
    console.print("[yellow]Running research agent...[/yellow]")

    result = asyncio.run(research_agent.run_task(
        task_id=task_id,
        prompt=prompt,
        project_id=project_id,
    ))

    console.print("\n[green]Research complete![/green]\n")
    console.print(result["response"])


@app.command()
def tasks(
    status: Optional[str] = typer.Option(None, "--status", "-s", help="Filter by status"),
    limit: int = typer.Option(20, "--limit", "-n", help="Number of tasks to show"),
):
    """List tasks."""
    db = get_db()
    query = db.table("tasks").select("id, title, status, model_used, cost_usd, created_at").order("created_at", desc=True).limit(limit)

    if status:
        query = query.eq("status", status)

    result = query.execute()

    table = Table(title="Forge Tasks")
    table.add_column("ID", style="dim", max_width=8)
    table.add_column("Title")
    table.add_column("Status")
    table.add_column("Model")
    table.add_column("Cost")
    table.add_column("Created")

    for task in result.data:
        status_style = {
            "pending": "yellow",
            "running": "blue",
            "complete": "green",
            "failed": "red",
        }.get(task["status"], "white")

        cost = f"${task['cost_usd']:.4f}" if task.get("cost_usd") else "-"
        table.add_row(
            task["id"][:8],
            task["title"][:50],
            f"[{status_style}]{task['status']}[/{status_style}]",
            task.get("model_used") or "-",
            cost,
            task["created_at"][:10],
        )

    console.print(table)


@app.command()
def task(task_id: str = typer.Argument(..., help="Task ID (prefix match)")):
    """View a task's details and output."""
    db = get_db()

    # Support prefix matching
    result = db.table("tasks").select("*").like("id", f"{task_id}%").single().execute()

    if not result.data:
        console.print(f"[red]Task not found: {task_id}[/red]")
        raise typer.Exit(1)

    t = result.data
    console.print(f"[bold]{t['title']}[/bold]")
    console.print(f"Status: {t['status']}")
    console.print(f"Model: {t.get('model_used', '-')}")
    console.print(f"Tokens: {t.get('tokens_in', 0)} in / {t.get('tokens_out', 0)} out")
    console.print(f"Cost: ${t.get('cost_usd', 0):.4f}")
    console.print()

    if t.get("output"):
        if isinstance(t["output"], dict) and "response" in t["output"]:
            console.print(t["output"]["response"])
        elif isinstance(t["output"], dict) and "error" in t["output"]:
            console.print(f"[red]Error: {t['output']['error']}[/red]")


@app.command()
def projects():
    """List projects."""
    db = get_db()
    result = db.table("projects").select("id, name, slug, created_at").order("name").execute()

    table = Table(title="Forge Projects")
    table.add_column("Slug")
    table.add_column("Name")
    table.add_column("Created")

    for p in result.data:
        table.add_row(p["slug"], p["name"], p["created_at"][:10])

    console.print(table)


@app.command()
def costs(
    days: int = typer.Option(30, "--days", "-d", help="Days to look back"),
):
    """Show cost summary."""
    db = get_db()
    result = db.rpc("get_cost_summary", {"days_back": days}).execute()

    if not result.data:
        # Fallback: raw query
        result = db.table("cost_log").select("model, cost_usd").execute()

    totals: dict[str, float] = {}
    for row in result.data:
        model = row.get("model", "unknown")
        cost = float(row.get("cost_usd", 0))
        totals[model] = totals.get(model, 0) + cost

    table = Table(title=f"Cost Summary (last {days} days)")
    table.add_column("Model")
    table.add_column("Total Cost", justify="right")

    grand_total = 0.0
    for model, cost in sorted(totals.items()):
        table.add_row(model, f"${cost:.4f}")
        grand_total += cost

    table.add_row("[bold]Total[/bold]", f"[bold]${grand_total:.4f}[/bold]")
    console.print(table)


if __name__ == "__main__":
    app()
