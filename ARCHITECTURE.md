# Forge — What It Is and How It Works

## The one-sentence version

Forge is a personal AI assistant that runs tasks for you — research, writing, code — judges whether the output is good enough, and retries if it isn't.

## Why it exists

Pete runs 8+ codebases, a consultancy, a SaaS product in development, and a music recommendation engine. His time is the bottleneck. Forge automates the stuff that doesn't need his hands on the keyboard: research, first drafts, routine code, overnight builds.

## What Forge is NOT

- Not a chatbot. It's a task runner with quality control.
- Not a hosted service. It runs on your own machine (laptop, VPS, wherever).
- Not tied to one AI provider. Claude, GPT, DeepSeek, local models — all swappable.

---

## The two parts

Forge has two independent pieces today. They share a philosophy but don't depend on each other.

### 1. The Orchestrator (`orchestrator/`)

**This is the main system.** A Python CLI you run from your terminal.

What it does:
- You give it a prompt: `forge ask "research Pydantic AI vs LangChain"`
- A **router** classifies the task (trivial/standard/complex) and picks the right agent and model
- An **agent** runs (right now just research; code and content agents coming)
- A **judge panel** evaluates the output — did it answer the question? Is it complete? Does it cite sources?
- If judges fail, the agent **retries** with feedback (up to 2 retries)
- Everything gets logged to Supabase: the task, the cost, the judge scores

Why this design:
- **Cheap judges catch expensive mistakes.** A $0.004 Haiku call can prevent you from shipping a bad $0.10 Sonnet output.
- **Judges are independent.** Each one checks one thing. Non-applicable judges skip themselves (a voice-style judge auto-passes on code tasks).
- **Budget-aware.** Running low on money? The router auto-downgrades to Haiku.
- **Everything persisted.** You can inspect any task, see what judges said, track spend over time.

Where it runs: **Your laptop.** Just `forge ask "..."` from the terminal. Could also run on the Hetzner VPS, a cron job, or behind an API — it's just a Python package.

Stack: Python 3.12+, Pydantic AI (agent framework), Supabase (persistence), Typer (CLI).

### 2. The Builder (`infra/builder/`)

**A narrow automation tool.** Runs on a Hetzner VPS as a background service.

What it does:
- Watches GitHub for issues labeled `forge-build`
- Picks one up, creates a branch, runs aider (Claude Code) to implement it
- Judges the result using heuristics (did the code lint? did it change the right files?)
- If it passes, opens a PR. If not, retries or gives up.
- You review the PR in the morning.

Why it exists: Pete wanted overnight builds — label an issue before bed, wake up to a PR. It was built first, before the orchestrator, as a standalone script.

Where it runs: **Hetzner VPS only.** It's a systemd service that polls continuously.

Stack: Python, aider (subprocess), GitHub CLI, ollama (optional local judge).

### How they relate

They don't talk to each other today. The builder is standalone — it has its own budget tracking (a JSON file), its own judge (heuristic decision tree), its own retry logic.

**Long-term plan:** The builder becomes unnecessary. Once the orchestrator has a proper code agent, you'd just run `forge ask "implement feature X"` and it would do what the builder does — but better, with the full judge panel, Supabase persistence, and cost tracking. The builder is scaffolding; the orchestrator is the building.

**For now:** Keep both. The builder works and does its job. The orchestrator is where new development happens.

---

## How to test it right now

### Prerequisites

1. **Supabase project** with these tables: `projects`, `tasks`, `memories`, `cost_log`, `judgments`
2. **Environment variables** in `orchestrator/.env`:
   ```
   SUPABASE_URL=https://your-project.supabase.co
   SUPABASE_SERVICE_KEY=your-service-key
   ANTHROPIC_API_KEY=your-key  # for the agents and LLM judge
   ```
3. **Run the migration** to add the judgments table:
   ```
   # Apply via Supabase dashboard SQL editor, or:
   # psql $DATABASE_URL < migrations/002_judgments.sql
   ```

### Install and run

```bash
cd orchestrator
uv pip install -e ".[dev]"

# Simplest test — research task with judges
forge research "What is Pydantic AI and how does it compare to LangChain?"

# Routed task — let the system pick the agent
forge ask "research the best Python testing frameworks in 2026"

# Inspect the judgment
forge judgments <task-id>

# See all tasks
forge tasks
```

### What you should see

1. Router prints its decision (complexity, agent, model)
2. Agent runs and produces output
3. Judges evaluate (task alignment via Haiku, completeness check, grounding check)
4. If judges fail, agent retries with feedback
5. Final output printed with verdict (pass/fail)
6. Everything logged to Supabase

---

## Key design decisions

**Why Pydantic AI instead of LangChain?**
Simpler, less magic, better typing. LangChain has too many abstractions. Pydantic AI is just "define an agent with a system prompt and tools, call `.run()`."

**Why Supabase instead of SQLite?**
Pete's entire ecosystem already runs on Supabase. Shared database means the future dashboard, API, and agents all read from the same place. Also: row-level security, realtime subscriptions, and hosted Postgres without managing a server.

**Why separate judges instead of one big evaluation prompt?**
IQIDIS research (Devansh/Chocolate Milk Cult): specialized cheap judges outperform one expensive generalist judge. Each judge is independently testable, independently weightable, and independently skippable. Adding a new judge is one class — no changes to existing code.

**Why heuristic judges when you could use LLM for everything?**
Cost. Four heuristic judges cost $0.00. One Haiku judge costs ~$0.004. A Sonnet judge would cost ~$0.05. For most checks (truncation, TODOs, buzzwords, lint), regex is better and free.

**Why not just run everything on the VPS?**
You can. But for development and testing, running locally is faster. The orchestrator doesn't care where it runs — it just needs Supabase credentials and an API key.

**Why keep the builder separate?**
It works. It's deployed. It does one thing well. Merging it into the orchestrator is future work — when there's a code agent that can replace aider, the builder retires naturally.

---

## What's built vs. what's planned

### Built (works today)
- [x] Judge module: 5 judges, 2 aggregation strategies, concurrent panel
- [x] ForgeAgent with judge retry loop
- [x] Research agent with judge panel wired up
- [x] Router (complexity classification, agent/model selection, budget pressure)
- [x] CLI: `forge ask`, `forge research`, `forge judgments`, `forge tasks`, `forge task`
- [x] Builder (standalone, Hetzner)
- [x] 23 unit tests for judge system

### Next up
- [ ] Run the migration + test end-to-end against live Supabase
- [ ] Content agent (drafts, LinkedIn posts, emails — with voice judge)
- [ ] Code agent (replaces builder long-term)
- [ ] FastAPI endpoints (so other tools can call Forge)

### Later
- [ ] Web dashboard (Next.js on Vercel, reads from Supabase)
- [ ] Telegram bot for orchestrator (not just builder)
- [ ] LangGraph workflows for multi-step tasks
- [ ] Langfuse observability
- [ ] Retire the builder once code agent is solid
