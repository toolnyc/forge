# Forge — Agent Orchestrator

Open-source multiagent framework backed by Supabase PostgreSQL. Built by Pete Wallace (tool.nyc / Huge Tool LLC, Brooklyn). Forge exists to automate development, research, and business operations across Pete's projects — and eventually as a standalone open-source tool others can use.

## Why Forge exists

Pete runs a solo creative consultancy with 8+ active codebases, a music recommendation engine, a SaaS product in development (Club Stack), and a business operations dashboard being built. His time is the bottleneck. Forge automates what can be automated — research, content, ops — so daytime hours go to client work and creative output.

**Core principles:** Open source, self-hosted (Hetzner), cost-aware, model-agnostic, no vendor lock-in.

## Project structure

```
forge/
├── orchestrator/          # Python package (forge-orchestrator)
│   ├── forge/
│   │   ├── agents/        # Agent implementations
│   │   │   ├── base.py    # ForgeAgent base class (task lifecycle, cost tracking)
│   │   │   └── research.py # Research agent (Pydantic AI + DuckDuckGo)
│   │   ├── memory/        # Memory system (store.py, retrieval.py)
│   │   ├── judges/        # Judge/evaluation logic
│   │   ├── graph/         # LangGraph workflows (planned)
│   │   ├── tools/         # Custom agent tools (planned)
│   │   ├── api/           # FastAPI endpoints (planned)
│   │   ├── telegram.py    # Telegram bot commands (/ask, /tasks, /task, /costs, /health)
│   │   ├── router.py      # Task routing logic
│   │   ├── cli.py         # Typer CLI (forge command)
│   │   ├── db.py          # Supabase client singleton
│   │   └── config.py      # Env-based config
│   └── pyproject.toml
├── migrations/            # DB migrations
├── CLAUDE.md              # This file
└── RESEARCH-CONTEXT.md    # Full context on Pete's life, projects, and preferences
```

## Related repos

- **forge-builder** (`~/Code/forge-builder/`): Autonomous CI agent that polls GitHub Issues and opens PRs. Runs on Hetzner VPS. Separate repo — works on any repo, not just forge.
- **toolweb** (`~/Code/toolweb/`): Has forge dashboard pages at `src/pages/admin/forge/*` — reads from forge's Supabase, no code dependency on this repo.

## Tech stack

- Python 3.12+, Hatchling build, pnpm for any JS
- Pydantic AI for agent framework
- LiteLLM for model routing (Claude, GPT, DeepSeek swappable)
- Supabase PostgreSQL (projects, tasks, memories, cost_log tables)
- FastAPI + Uvicorn (planned API layer)
- LangGraph + Postgres checkpointer (planned workflows)
- Typer + Rich for CLI
- Langfuse for observability (planned, self-hosted)

## Database tables

- `projects` — id, name, slug, context, stack, created_at
- `tasks` — id, project_id, title, description, status, input, output, tokens_in, tokens_out, cost_usd, model_used, created_at, started_at, completed_at
- `memories` — id, project_id, content, category, created_at
- `cost_log` — id, task_id, project_id, model, input_tokens, output_tokens, cost_usd

## Conventions

- `from __future__ import annotations` in all Python files
- Type hints everywhere: `X | None` not `Optional[X]`
- Ruff linting: E, F, I, N, UP, B, SIM rules
- Line length: 100
- snake_case for everything except class names
- All DB interaction through `get_db()` singleton
- Agents extend `ForgeAgent` base class
- New agents go in `orchestrator/forge/agents/`
- Keep imports sorted (ruff handles this)
- Stay tightly scoped — don't refactor adjacent code or expand beyond what was asked
- Plan before implementing (default to plan mode)

## Task lifecycle

pending → running → complete | failed

All tasks persisted in Supabase `tasks` table with token/cost tracking.

## Adding a new agent

1. Create `orchestrator/forge/agents/your_agent.py`
2. Define raw Pydantic AI `Agent` with system prompt and tools
3. Wrap in `ForgeAgent(name="your_agent", agent=_your_agent)`
4. Export from `orchestrator/forge/agents/__init__.py`
5. Add CLI command in `cli.py` if user-facing

## Cost awareness

Budget is real — don't burn tokens carelessly.

- Default: claude-sonnet-4-6 (most tasks)
- Simple/routine: claude-haiku-4-5
- Critical architecture only: claude-opus-4-6
- Always log costs to cost_log table

## Telegram bot

Forge has its own Telegram commands for interacting with the orchestrator, defined in `orchestrator/forge/telegram.py`:

- `/ask <prompt>` — Route + run agent, return result
- `/tasks` — List 10 recent tasks
- `/task <id>` — Task detail + judgment verdict
- `/costs` — Today / this week / total spend by model
- `/health` — Supabase connectivity check

Currently standalone handlers — wiring up as a running bot is a future task.

## Dashboard

The web dashboard lives in **toolweb** at `src/pages/admin/forge/*`. It reads from forge's Supabase project — no code dependency on this repo. Pages: overview, tasks list, task detail, costs, judgments.

## Pete's ecosystem (what agents may interact with)

- **tool.nyc (toolweb):** Astro 5 + Cloudflare Pages + Supabase + Stripe + Resend + R2
- **Club Stack:** SaaS for nightlife venues (Next.js + Supabase + Stripe Connect, pre-MVP)
- **ra-killer:** Python event scraper + recommendation engine (Hetzner, Telegram, Twilio)
- **VERBS:** Event ticketing (Astro 5 + Vercel + Supabase + Stripe)
- **Z Hub:** Business ops dashboard inside toolweb (expense tracking, invoices, taxes)
- **g1882:** Art gallery CMS (Next.js + Payload CMS + MongoDB)
- **experiment-lacrosse:** Training platform (Next.js + Supabase + Stripe)

All projects use Supabase, most use Stripe, all JS projects use pnpm, all use git worktrees.

## Voice and style

When generating content, reports, or communications on Pete's behalf:
- Direct, understated confidence — "I make websites" energy
- Short declarative sentences, no filler
- No hedging, superlatives, or marketing buzzwords
- No "we" (it's one person)
- Dry wit when natural, never forced
- Opinionated — take a stance
- Plain language over jargon

## What NOT to do

- Don't over-engineer or add premature abstractions
- Don't create docs/README unless explicitly asked
- Don't use Optional[X] — use X | None
- Don't vendor-lock to any single AI provider
- Don't burn budget on exploratory searches when cheaper approaches exist
- Don't expand scope beyond what was asked
- Don't add features nobody requested
