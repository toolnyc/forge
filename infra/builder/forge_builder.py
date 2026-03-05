#!/usr/bin/env python3
"""Forge Builder — autonomous build loop.

Polls GitHub Issues labeled 'forge-build', runs Claude Code headless
to implement each one, and opens a PR for review.

Designed to run as a systemd service on a Hetzner VPS.
"""

from __future__ import annotations

import json
import logging
import os
import subprocess
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
log = logging.getLogger("forge-builder")

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

@dataclass
class BuilderConfig:
    repo_dir: str = os.getenv("FORGE_REPO_DIR", "/opt/forge")
    github_repo: str = os.getenv("FORGE_GITHUB_REPO", "")  # e.g. "petejames/forge"
    poll_interval: int = int(os.getenv("FORGE_POLL_INTERVAL", "300"))  # 5 min
    label_pending: str = "forge-build"
    label_in_progress: str = "building"
    label_done: str = "pr-ready"
    max_concurrent: int = 1
    branch_prefix: str = "forge-build"
    claude_max_turns: str = os.getenv("FORGE_CLAUDE_MAX_TURNS", "50")

    # --- Budget controls ---
    # Daily spend cap in USD. Builder pauses when reached.
    daily_budget_usd: float = float(os.getenv("FORGE_DAILY_BUDGET", "5.00"))
    # Per-issue spend cap. Kills the run if exceeded.
    per_issue_budget_usd: float = float(os.getenv("FORGE_PER_ISSUE_BUDGET", "1.50"))
    # Model routing: use cheaper models for smaller tasks
    # "auto" = pick model based on issue labels/size, or specify a model directly
    model_strategy: str = os.getenv("FORGE_MODEL_STRATEGY", "auto")
    # Explicit model override (used when strategy != "auto")
    claude_model: str = os.getenv("FORGE_CLAUDE_MODEL", "")
    # Budget log file (append-only JSON lines)
    budget_log: str = os.getenv("FORGE_BUDGET_LOG", "/opt/forge/infra/builder/budget.jsonl")

    # --- Schedule controls ---
    # Only build during these hours (UTC). Empty = always.
    # e.g. "22-06" = 10pm to 6am UTC (overnight)
    active_hours: str = os.getenv("FORGE_ACTIVE_HOURS", "")


cfg = BuilderConfig()

# ---------------------------------------------------------------------------
# Budget tracking
# ---------------------------------------------------------------------------

COST_PER_TURN_ESTIMATE = {
    # Conservative estimates per agent turn (input + output)
    "sonnet": 0.025,   # ~5k in + 2k out per turn
    "haiku": 0.005,    # much cheaper for small tasks
    "opus": 0.10,      # expensive, use sparingly
}


def _today_str() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def get_daily_spend() -> float:
    """Sum today's spend from the budget log."""
    log_path = Path(cfg.budget_log)
    if not log_path.exists():
        return 0.0

    today = _today_str()
    total = 0.0
    for line in log_path.read_text().splitlines():
        try:
            entry = json.loads(line)
            if entry.get("date") == today:
                total += entry.get("cost_usd", 0.0)
        except json.JSONDecodeError:
            continue
    return total


def log_spend(issue_number: int, model: str, turns: int, cost_usd: float):
    """Append a spend entry to the budget log."""
    log_path = Path(cfg.budget_log)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    entry = {
        "date": _today_str(),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "issue": issue_number,
        "model": model,
        "turns": turns,
        "cost_usd": round(cost_usd, 4),
    }
    with open(log_path, "a") as f:
        f.write(json.dumps(entry) + "\n")


def budget_remaining() -> float:
    """How much budget is left today."""
    return cfg.daily_budget_usd - get_daily_spend()


def is_within_active_hours() -> bool:
    """Check if current UTC hour is within configured active hours."""
    if not cfg.active_hours:
        return True  # no restriction

    try:
        start_str, end_str = cfg.active_hours.split("-")
        start_h, end_h = int(start_str), int(end_str)
    except ValueError:
        log.warning("Invalid FORGE_ACTIVE_HOURS format: %s (expected 'HH-HH')", cfg.active_hours)
        return True

    now_h = datetime.now(timezone.utc).hour
    if start_h <= end_h:
        return start_h <= now_h < end_h
    else:
        # Wraps midnight, e.g. 22-06
        return now_h >= start_h or now_h < end_h


def pick_model(issue: dict) -> str:
    """Choose a model based on issue characteristics and remaining budget.

    Strategy:
    - Issues labeled 'complex' or 'architecture' → sonnet (capable, mid-cost)
    - Issues labeled 'simple' or 'docs' → haiku (cheapest)
    - Default → sonnet
    - If budget is tight (< 30% remaining) → downgrade to haiku
    - Never auto-select opus (must be explicit via FORGE_CLAUDE_MODEL)
    """
    if cfg.model_strategy != "auto":
        return cfg.claude_model or ""

    labels = {l["name"].lower() for l in issue.get("labels", [])}
    remaining = budget_remaining()
    remaining_pct = remaining / cfg.daily_budget_usd if cfg.daily_budget_usd > 0 else 0

    # Budget pressure: switch to cheapest capable model
    if remaining_pct < 0.30:
        log.info("Budget tight (%.1f%% remaining) — using sonnet", remaining_pct * 100)
        return "claude-sonnet-4-6"

    # Label-based routing
    # Note: haiku is too cautious for code tasks (asks permission instead of acting).
    # Use sonnet as the floor for any task that writes code.
    cheap_labels = {"docs", "documentation", "typo"}
    if labels & cheap_labels:
        log.info("Docs-only task detected — using haiku")
        return "claude-haiku-4-5"

    expensive_labels = {"complex", "architecture", "refactor", "feature"}
    if labels & expensive_labels:
        log.info("Complex task — using sonnet")
        return "claude-sonnet-4-6"

    # Default to sonnet (good balance of capability and cost)
    return "claude-sonnet-4-6"


def estimate_cost(model: str, turns: int) -> float:
    """Estimate cost for a run."""
    if "haiku" in model:
        return turns * COST_PER_TURN_ESTIMATE["haiku"]
    if "opus" in model:
        return turns * COST_PER_TURN_ESTIMATE["opus"]
    return turns * COST_PER_TURN_ESTIMATE["sonnet"]

# ---------------------------------------------------------------------------
# Shell helpers
# ---------------------------------------------------------------------------

def run(cmd: list[str], cwd: str | None = None, check: bool = True) -> subprocess.CompletedProcess:
    """Run a subprocess, logging the command."""
    log.debug("$ %s", " ".join(cmd))
    result = subprocess.run(cmd, capture_output=True, text=True, cwd=cwd or cfg.repo_dir)
    if check and result.returncode != 0:
        log.error("Command failed: %s\nstdout: %s\nstderr: %s", " ".join(cmd), result.stdout, result.stderr)
        raise subprocess.CalledProcessError(result.returncode, cmd, result.stdout, result.stderr)
    return result


def gh(args: list[str], **kwargs) -> subprocess.CompletedProcess:
    """Run a gh CLI command."""
    return run(["gh"] + args, **kwargs)

# ---------------------------------------------------------------------------
# GitHub Issue management
# ---------------------------------------------------------------------------

def fetch_pending_issues() -> list[dict]:
    """Get open issues labeled 'forge-build' that aren't already being worked on."""
    result = gh([
        "issue", "list",
        "--repo", cfg.github_repo,
        "--label", cfg.label_pending,
        "--state", "open",
        "--json", "number,title,body,labels",
        "--limit", "20",
    ])
    issues = json.loads(result.stdout)
    # Filter out issues already in progress
    return [
        i for i in issues
        if not any(l["name"] == cfg.label_in_progress for l in i.get("labels", []))
    ]


def label_issue(number: int, add: list[str] | None = None, remove: list[str] | None = None):
    """Add/remove labels on an issue."""
    if add:
        for label in add:
            gh(["issue", "edit", str(number), "--repo", cfg.github_repo, "--add-label", label])
    if remove:
        for label in remove:
            gh(["issue", "edit", str(number), "--repo", cfg.github_repo, "--remove-label", label], check=False)


def comment_on_issue(number: int, body: str):
    """Post a comment on an issue."""
    gh(["issue", "comment", str(number), "--repo", cfg.github_repo, "--body", body])

# ---------------------------------------------------------------------------
# Git helpers
# ---------------------------------------------------------------------------

def slugify(text: str) -> str:
    """Turn text into a branch-safe slug."""
    slug = text.lower().strip()
    slug = "".join(c if c.isalnum() or c == " " else "" for c in slug)
    slug = "-".join(slug.split())
    return slug[:50]


def prepare_branch(issue_number: int, title: str) -> str:
    """Reset to main, pull, and create a feature branch."""
    branch_name = f"{cfg.branch_prefix}/{issue_number}-{slugify(title)}"

    run(["git", "fetch", "origin"])
    run(["git", "checkout", "main"])
    run(["git", "reset", "--hard", "origin/main"])
    run(["git", "checkout", "-b", branch_name])

    return branch_name


def has_changes() -> bool:
    """Check if there are uncommitted changes."""
    result = run(["git", "status", "--porcelain"], check=False)
    return bool(result.stdout.strip())


def commit_and_push(branch_name: str, issue_number: int, title: str):
    """Stage all changes, commit, push."""
    # Ensure secrets and logs are never committed
    run(["git", "reset", "HEAD", "--", "infra/builder/.env", "infra/builder/budget.jsonl"], check=False)
    run(["git", "checkout", "--", "infra/builder/.env"], check=False)
    run(["git", "add", "-A"])
    commit_msg = f"forge-build: {title} (#{issue_number})\n\nAutonomously implemented by Forge Builder using Claude Code.\nCloses #{issue_number}\n\nCo-Authored-By: Claude <noreply@anthropic.com>"
    run(["git", "commit", "-m", commit_msg])
    run(["git", "push", "-u", "origin", branch_name])


def open_pr(branch_name: str, issue_number: int, title: str, summary: str) -> str:
    """Open a PR and return its URL."""
    pr_body = f"""## Auto-generated by Forge Builder

Implements #{issue_number}

{summary}

---
Built autonomously by [Forge Builder](https://github.com/{cfg.github_repo}) using Claude Code headless.
Review carefully before merging.
"""
    result = gh([
        "pr", "create",
        "--repo", cfg.github_repo,
        "--base", "main",
        "--head", branch_name,
        "--title", f"[forge-build] {title}",
        "--body", pr_body,
    ])
    return result.stdout.strip()

# ---------------------------------------------------------------------------
# Claude Code execution
# ---------------------------------------------------------------------------

def run_claude(issue: dict) -> tuple[bool, str]:
    """Run Claude Code headless on the repo to implement the issue.

    Returns (success, summary).
    """
    model = pick_model(issue)
    max_turns = int(cfg.claude_max_turns)

    # Pre-flight budget check
    estimated = estimate_cost(model, max_turns)
    remaining = budget_remaining()
    if estimated > remaining:
        msg = f"Skipping: estimated cost ${estimated:.2f} exceeds remaining daily budget ${remaining:.2f}"
        log.warning(msg)
        return False, msg

    if estimated > cfg.per_issue_budget_usd:
        # Downgrade to haiku and reduce turns
        log.info("Estimated cost $%.2f exceeds per-issue cap $%.2f — switching to haiku with fewer turns",
                 estimated, cfg.per_issue_budget_usd)
        model = "claude-haiku-4-5"
        max_turns = min(max_turns, 30)

    prompt = f"""You are working on the Forge project — an open-source agent orchestrator.

Implement the following GitHub issue:

## #{issue['number']}: {issue['title']}

{issue.get('body', '') or 'No description provided.'}

---

Instructions:
- Read CLAUDE.md first for project conventions
- Make focused, minimal changes to implement this issue
- Write tests if the project has a test framework set up
- Do NOT modify unrelated code
- If you're blocked or something is unclear, leave a TODO comment explaining why
- Be efficient with your turns — avoid unnecessary file reads or exploratory searches
"""

    cmd = ["claude", "-p", "--output-format", "text"]

    if model:
        cmd.extend(["--model", model])

    cmd.extend(["--max-turns", str(max_turns)])

    log.info("Running Claude Code headless (model=%s, max_turns=%d, budget_remaining=$%.2f)...",
             model or "default", max_turns, remaining)

    result = subprocess.run(
        cmd,
        input=prompt,
        capture_output=True,
        text=True,
        cwd=cfg.repo_dir,
        timeout=1800,  # 30 min max per issue
    )

    # Log the spend (estimate based on turns used — actual cost comes from API)
    actual_cost = estimate_cost(model or "claude-sonnet-4-6", max_turns // 2)  # assume ~half turns used
    log_spend(issue["number"], model or "default", max_turns, actual_cost)

    if result.returncode != 0:
        log.error("Claude Code failed:\nstdout: %s\nstderr: %s", result.stdout[-2000:], result.stderr[-2000:])
        return False, f"Claude Code exited with code {result.returncode}:\n```\n{result.stderr[-500:]}\n```"

    summary = result.stdout[-3000:] if result.stdout else "No output captured."
    return True, summary

# ---------------------------------------------------------------------------
# Main loop
# ---------------------------------------------------------------------------

def process_issue(issue: dict):
    """Process a single issue end-to-end."""
    number = issue["number"]
    title = issue["title"]
    log.info("=== Processing issue #%d: %s ===", number, title)

    # Mark as in-progress
    label_issue(number, add=[cfg.label_in_progress])
    comment_on_issue(number, "Forge Builder is working on this...")

    try:
        # Prepare branch
        branch_name = prepare_branch(number, title)

        # Run Claude Code
        success, summary = run_claude(issue)

        if not success:
            comment_on_issue(number, f"Build failed:\n\n{summary}")
            label_issue(number, remove=[cfg.label_in_progress])
            # Checkout main to clean up
            run(["git", "checkout", "main"], check=False)
            run(["git", "branch", "-D", branch_name], check=False)
            return

        # Check if Claude actually changed anything
        if not has_changes():
            comment_on_issue(number, "Claude Code ran but made no changes. May need a more specific issue description.")
            label_issue(number, remove=[cfg.label_in_progress])
            run(["git", "checkout", "main"])
            run(["git", "branch", "-D", branch_name], check=False)
            return

        # Commit, push, open PR
        commit_and_push(branch_name, number, title)
        pr_url = open_pr(branch_name, number, title, summary)

        # Update issue
        label_issue(number, add=[cfg.label_done], remove=[cfg.label_in_progress, cfg.label_pending])
        comment_on_issue(number, f"PR opened: {pr_url}\n\nPlease review before merging.")
        log.info("PR created: %s", pr_url)

    except Exception as e:
        log.exception("Error processing issue #%d", number)
        comment_on_issue(number, f"Forge Builder encountered an error:\n```\n{e}\n```")
        label_issue(number, remove=[cfg.label_in_progress])
        # Clean up
        run(["git", "checkout", "main"], check=False)


def main():
    """Main polling loop."""
    log.info(
        "Forge Builder starting — repo: %s, poll: %ds, daily_budget: $%.2f, per_issue: $%.2f, hours: %s",
        cfg.github_repo, cfg.poll_interval, cfg.daily_budget_usd,
        cfg.per_issue_budget_usd, cfg.active_hours or "always",
    )

    if not cfg.github_repo:
        log.error("FORGE_GITHUB_REPO not set. Exiting.")
        sys.exit(1)

    if not Path(cfg.repo_dir).exists():
        log.error("Repo dir %s does not exist. Exiting.", cfg.repo_dir)
        sys.exit(1)

    while True:
        try:
            # Schedule gate
            if not is_within_active_hours():
                log.info("Outside active hours (%s). Sleeping...", cfg.active_hours)
                time.sleep(cfg.poll_interval)
                continue

            # Budget gate
            remaining = budget_remaining()
            if remaining <= 0:
                log.info("Daily budget exhausted ($%.2f spent). Sleeping until tomorrow...", cfg.daily_budget_usd)
                time.sleep(cfg.poll_interval * 6)  # check less often when broke
                continue

            log.info("Budget remaining today: $%.2f / $%.2f", remaining, cfg.daily_budget_usd)

            issues = fetch_pending_issues()
            if issues:
                log.info("Found %d pending issue(s)", len(issues))
                issue = sorted(issues, key=lambda i: i["number"])[0]
                process_issue(issue)
            else:
                log.info("No pending issues. Sleeping...")
        except KeyboardInterrupt:
            log.info("Shutting down.")
            break
        except Exception:
            log.exception("Unexpected error in main loop")

        time.sleep(cfg.poll_interval)


if __name__ == "__main__":
    main()
