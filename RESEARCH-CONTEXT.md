# Pete Wallace — Comprehensive Context for Forge

Compiled March 4, 2026 from all CLAUDE.md files, .claude/ configs, Dropbox, and project codebases.

---

## WHO IS PETE

**Pete Wallace** — Solo creative technical consultant, Brooklyn, NY.
- **Entity:** Late Bloomer Studio LLC (legally changing to Huge Tool LLC)
- **Brand:** tool.nyc — "I make websites" energy
- **EIN:** Registered, single-member LLC

### Identity
- Senior solo practitioner (not freelancer, not agency)
- Brand + web together — unusual in market (most separate these roles)
- NYC underground music scene participant: DJ, producer, promoter
- Anti-vendor-lock-in, open-source philosophy
- Values: ownership, clarity, taste, independence, craft
- Voice: direct, understated confidence, plain language, dry wit
- Anti-patterns: marketing buzzwords, hedging, superlatives, filler enthusiasm, "we" when it's one person

### Life Context
- Rents in Brooklyn (home office setup)
- Health insurance (paying monthly premiums)
- Investment account (dividends + capital gains/losses)
- Graduate student: Georgia Tech (CSE-6040 computing, ISYE-6501 analytics modeling)
- Active music producer (Ableton Live) and DJ (Rekordbox, Engine DJ)
- Employment history: W-2 job Feb-July 2025, otherwise freelance/consulting

---

## FINANCIALS

### 2024 Baseline
- **Gross revenue:** Mid-five-figure consultancy revenue
- **Net business income (Schedule C):** Roughly 40% of gross after expenses
- **W-2 wages:** Additional part-time income
- **Dividends:** Low-five-figure investment income
- **Tax situation:** Under-tracked expenses, simplified home office method (leaving significant deductions on the table)

### 2025 Transition
- W-2 employment (Feb-July), minimal freelance July-Dec
- Investment withdrawals
- Zero estimated quarterly payments made (relying on W-2 withholding)

### 2026 Targets
- **Revenue goal:** $10-15K/month ($120-180K annual)
- **Revenue mix:** 40% retainers/recurring, 40% projects, 20% Club Stack SaaS
- **Quarterly estimates due:** Standard federal + state + city obligations

### Revenue Streams
1. **Consulting packages:** Launch Kit, Growth, Full Build (tiered pricing from low-five to mid-five figures)
2. **Retainers:** Maintenance, On-Call, Embedded (tiered monthly pricing)
3. **Club Stack SaaS:** Monthly per-venue subscription (pre-launch)
4. **Event ticketing (VERBS):** Active but smaller revenue

### Deductions Being Missed
- Self-employed health insurance premiums (HUGE — above-the-line)
- Home office actual method (significantly more than simplified)
- Internet business percentage
- All SaaS subscriptions (Figma, Supabase, Cloudflare, domains, etc.)
- Stripe fees, phone, professional development, client meals, transportation
- SEP-IRA contributions (meaningful tax savings potential)

---

## ACTIVE PROJECTS (Priority Order)

### 1. Tool.NYC (toolweb) — Primary Business Site
- **Stack:** Astro 5 SSR → Cloudflare Pages, Supabase, Stripe, Resend, R2
- **Features:** Portfolio mood board, AI inquiry chatbot (OpenAI Whisper + GPT-4o-mini), client portal (magic links), merch shop, admin dashboard, analytics
- **Domain:** tool.nyc (prod), pre.tool.nyc (staging)
- **Status:** Core infrastructure complete, polishing animations + Cal.com integration
- **Sessions:** 137 Claude Code sessions (most active project)

### 2. Club Stack — SaaS for Nightlife Venues
- **Purpose:** Displace RA's 10% commission with flat subscription
- **Target:** Underground/music-first venues, 200-600 capacity
- **Pricing:** Flat monthly per venue, DJs free
- **Philosophy:** Ghost business model applied to nightlife — flat fee, 0% creator cut, open source ethos
- **Status:** Post-research, pre-MVP
- **Stack (planned):** Next.js + Supabase + Stripe Connect

### 3. RA-Killer (ClubStack Dancefloor Services)
- **Purpose:** NYC event aggregator + recommendation engine
- **Stack:** Python 3.12, httpx, BeautifulSoup4, Claude API (batch scoring), Supabase, Telegram bot, Twilio IVR
- **Scrapes:** RA, DICE, Partiful, Basement, Light & Sound, NYC Noise
- **Server:** Hetzner VPS, scheduled scrapes 6AM/6PM
- **Taste profile:** 319 artists, 57 venues (weighted)
- **Top artists:** Sleep D, Mia Koden, Autumns, Skee Mask, KiNK, Cinthie, DJ Hell
- **Top venues:** Nowadays, BASEMENT, Signal, H0L0, Good Room, Paragon
- **Current issues:** Weekly recs overwritten daily, script generates with no content, voice is wrong

### 4. VERBS — Event Ticketing Platform
- **Stack:** Astro 5 SSR → Vercel, Supabase, Stripe, Resend
- **Features:** Event ticketing, DJ mixes, newsletter campaigns, admin dashboard
- **Complexity:** Cursor-following flyer preview system (Lenis + GSAP + ViewTransitions)
- **Sessions:** 105 Claude Code sessions

### 5. Forge — Agent Orchestrator (THIS PROJECT)
- **Purpose:** Self-hosted multi-agent system, reduce vendor dependence
- **Stack:** Python 3.12, Pydantic AI, LiteLLM, LangGraph, Supabase, FastAPI
- **Infrastructure:** Hetzner VPS for agents, Vercel for dashboard (planned)
- **Status:** Research agent working, CLI functional, builder loop being built
- **Timeline:** 1-2 months to functional system

### 6. Z Hub — Business Operations Dashboard
- **Purpose:** Centralized admin hub for finances, taxes, invoices
- **Location:** Inside toolweb at /admin/hub/*
- **Schema:** zh_* prefix tables
- **Status:** Planning phase, Phase 1 foundation starting
- **Features:** Expense tracking (17 Schedule C categories), invoice management, quarterly tax tracker, retainer management, CSV import

### 7. Gallery 1882 (g1882) — Art Gallery CMS
- **Stack:** Next.js 15 + Payload CMS 3, MongoDB, Vercel Blob
- **Location:** Chesterton, IN art gallery
- **Status:** Active, fixing bulk image upload reliability
- **Sessions:** 27 Claude Code sessions

### 8. Experiment Lacrosse — Training Session Platform
- **Stack:** Next.js 15, Supabase, Stripe, Resend
- **Status:** Active, finishing brand migration (Lacrosse Lab → Experiment Lacrosse)
- **Sessions:** 38 Claude Code sessions

### 9. 1134-web — Minimal Landing Page
- **Stack:** Astro 5, vanilla CSS, Supabase, Resend
- **Philosophy:** Zero framework bloat, pure utility

### 10. Blow — DIY Party Series
- **Aesthetic:** Windows 98-themed website with draggable windows, taskbar, boot screen
- **Stack:** Astro static site, email capture, SoundCloud embeds
- **Vibe:** Playful, irreverent, deliberately retro

---

## MUSIC & CULTURAL CONTEXT

### Production
- **DAW:** Ableton Live
- **Controller:** Akai APC40 MK II
- **Plugins:** Valhalla suite, iZotope, fabfilter, RaveGenerator2
- **DJ Software:** Rekordbox, Engine DJ
- **Genres:** Minimal techno, IDM, deep house, industrial, leftfield electronics, acid, jungle/breakbeat, dub, rave
- **Recent productions:** killing-youth, immaterial, massive-saturation (Feb-March 2026)

### DJ Library
- **Curated:** ~482 AIFF tracks, ~212 artists in Library/Selects/
- **Incoming:** ~2,389 tracks from Bandcamp (~235 artists)
- **Active sets:** Rock-A-Rave series, Honey Trap Dinner, B2B sets

### Music Knowledge
- Comprehensive synthesis reference docs (Roland fundamentals, signal flow)
- Music theory guide (scales, chords, progressions, harmony, counterpoint)
- Ableton workflow optimization (templates, APC40 mapping, sample organization)

### Venue Culture
- Underground, artist-first, music-centric spaces
- Serious about sound quality, intimate vibes, integrity
- Key reference: Nowadays (Ridgewood) — multi-day 24hr parties, tight operations
- Anti-RA sentiment: 10% commission model is extractive

---

## TECH STACK & CONVENTIONS (Universal Across Projects)

### Git Workflow (NON-NEGOTIABLE)
- ALWAYS use git worktrees for feature/fix branches
- NEVER commit directly to master
- Pattern: `git worktree add -b feature/<name> ../project-<name>` → `pnpm install` → work → push → remove worktree

### Package Manager
- **pnpm** for all JS/TS projects (never npm or yarn)
- **uv** for Python projects
- **Hatchling** for Python build system

### Frontend Patterns
- Astro 5 SSR (primary) or Next.js 15 App Router
- Tailwind CSS for styling
- GSAP + ScrollTrigger + Lenis for animation
- `prefers-reduced-motion` bailout on all animations

### Backend Patterns
- Supabase PostgreSQL with Row Level Security everywhere
- Dual-client pattern: `getSupabase()` (anon, RLS) + `getSupabaseAdmin()` (service key, bypasses RLS)
- Lazy singleton env initialization (`src/lib/env.ts` pattern)
- Feature flags in database, checked in middleware

### Auth Patterns
- Supabase Auth: magic links for clients, password for admin
- Cookie-based sessions (sb-access-token, sb-refresh-token)
- Middleware protection on /admin/* and /portal/* routes

### Stripe Patterns (CRITICAL)
- Always include `checkout_type` in session metadata
- Webhook is most dangerous code — extract logic to `src/lib/`, test independently
- Idempotent upserts on `stripe_session_id`
- Money in cents (integers), divide by 100 at webhook boundary only
- Stock: `Math.max(0, stock_count - quantity)` (clamp to 0)
- Stripe ↔ Resend coupling: stale webhook endpoints poison idempotency
- Test with real prices ($13.99, $41.97), not round numbers

### Supabase Gotcha
- Multiple FKs between tables → must use explicit FK names in `.select()`:
  `ticket_tiers!ticket_tiers_event_id_fkey(*)` not just `ticket_tiers(*)`
  Otherwise: PGRST201 error

### Cloudflare Pages Gotcha
- Non-inheritable keys (vars, r2_buckets, kv_namespaces) are all-or-nothing
- Override ONE in `[env.preview]` → must repeat ALL or they silently disappear

### Email
- Resend for all transactional email
- Template pattern: HTML email tables for compatibility
- Brand constants: FROM_ADDRESS, REPLY_TO, LOGO_URL

### Testing
- Vitest (unit/integration) + Playwright (E2E) for JS/TS
- pytest for Python
- CRITICAL USER FLOWS > quantity: purchasing, checkout, auth, payments
- Extract pure logic into `src/lib/`, import in tests (never duplicate)

### Code Quality
- `from __future__ import annotations` in all Python files
- `X | None` not `Optional[X]`
- Ruff linting: E, F, I, N, UP, B, SIM
- Be direct with feedback (honest critique > encouragement)
- Stay tightly scoped — don't refactor adjacent code
- Clean up old/unused code while making changes
- Default to plan mode before implementing

---

## DEPLOYMENT INFRASTRUCTURE

### Hosting
- **Cloudflare Pages:** toolweb (tool.nyc), verbs
- **Vercel:** experiment-lacrosse, g1882, 1134-web, forge dashboard (planned)
- **Hetzner VPS:** ra-killer, forge orchestrator, forge builder

### Services
- **Supabase:** Multiple projects (all DB + auth + storage)
- **Stripe:** Payments (live + test keys per project)
- **Resend:** Transactional email (multiple domains)
- **Cloudflare R2:** Media storage (tool-media bucket)
- **Cloudflare Stream:** Video hosting
- **Cal.com:** Scheduling (embedded on tool.nyc)
- **Telegram Bot API:** Notifications
- **Twilio:** IVR voicemail (ra-killer)
- **OpenAI:** Whisper (transcription) + GPT-4o-mini (intent extraction)

### Aliases & Shortcuts
```bash
yolo          # claude --dangerously-skip-permissions
remote-claude # SSH to VPS
env-switch    # multi-account Vercel/Stripe switcher
spotenv       # spotify downloader venv
stable        # Stable Diffusion WebUI
```

---

## CONTENT & MARKETING STRATEGY

### LinkedIn (Primary Funnel)
- 3 posts/week (Mon/Wed/Fri), 150-300 words
- Pillars: Own Your Stack, Design That Works, Building in Public, Small Business Real Talk
- Text-only, no hashtags, hook → context → insight → takeaway → soft CTA
- Never: motivational content, "I woke up at 5am" format, AI takes unless novel

### Instagram (Trust Building)
- 2 posts/week (Tue/Thu), 1 Reel + 1 carousel
- Reels: 30-90 sec face-to-camera, teaching something specific
- Carousels: 4-7 slides, bold text, CMYK palette
- Slightly more casual than LinkedIn

### Production Workflow
- Sunday: Write 3 LinkedIn posts (45 min)
- Saturday/Sunday: Record + create Instagram content
- Never produce day-of
- Total: 2.5 hours/week

### Voice Guide
- Short sentences, no filler, opinionated
- TTS-friendly, 200-400 words max
- Direct tone, dry wit, no hedging
- "I make websites" energy — not an agency, a person

---

## DESIGN SYSTEM

### CMYK Accents (tool.nyc)
- Cyan: `#00FFFF`
- Magenta: `#FF00FF`
- Yellow: `#FFEB00`

### Typography
- Space Grotesk (variable weight) for toolweb
- System fonts stack for body

### Grid
- 24-column responsive grid with 1px gaps
- Breakpoints: md (800px), lg (1000px)
- Generous whitespace

### Design References
- hardsun.com — editorial scroll, full-bleed imagery, 1px grid gaps, sticky CTA
- bottlingfruit.co.uk — endless scroll, bold text, horizontal layout
- body-without-organs.netlify.app — hover effects, elegant interactions
- jonway.studio — aesthetic inspiration for 1134-web

---

## WHAT FORGE NEEDS TO KNOW

### Pete's Priorities (What the agent should optimize for)
1. **Revenue growth** — every tool should serve the path to $10-15K/month
2. **Time efficiency** — automate what can be automated, Pete's time is the bottleneck
3. **Cost awareness** — track every dollar (both business expenses and AI costs)
4. **Quality over speed** — Pete's brand is taste and craft, not volume
5. **Independence** — own the tools, own the data, no vendor lock-in

### Pete's Work Style
- Plans before implements (default to plan mode)
- Juggles 5-8 projects daily
- Heavy morning focus (8-11 AM), afternoon work blocks (2-4 PM)
- Prefers honest critique over encouragement
- Wants to know WHY, not just HOW
- Values scope discipline — don't expand beyond what was asked

### What Pete Cares About
- Underground music culture and artist protection
- Building sustainable solo business infrastructure
- Open-source tools and data ownership
- Financial independence through diversified revenue
- Interesting work over scale
- Brooklyn community and NYC creative scene

### What Pete Doesn't Want
- Agency cosplay ("we" language)
- Marketing buzzwords or filler enthusiasm
- Over-engineering or premature abstraction
- VC-funded growth-at-all-costs thinking
- Vendor lock-in or data extraction
- Generic AI aesthetics or boilerplate solutions
