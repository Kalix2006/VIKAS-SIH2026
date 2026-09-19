# VIKAS — Viksit India Kaushal Alignment System

## Architecture Context File

> **Check this file before making ANY technology or architecture decision.**
> This file is the single source of truth for locked decisions.

---

## Locked Technology Stack

| Layer | Technology | Version / Notes |
|-------|-----------|----------------|
| Backend | FastAPI (async) | Python 3.12 |
| Frontend | React (Vite) + TypeScript + Tailwind CSS v3 + shadcn/ui | Strict TS mode |
| Database | PostgreSQL | Via Supabase (hosted) |
| ORM | SQLAlchemy 2.0 (async) | asyncpg driver |
| Migrations | Alembic | Async-compatible |
| NLP | spaCy (`en_core_web_sm`) + sentence-transformers (`all-MiniLM-L6-v2`) | Local inference |
| LLM | Groq (Llama 3.3) | See LLM Policy below |
| Maps | Leaflet + OpenStreetMap | Never Google Maps |
| Charts | Recharts | — |
| Auth | JWT (python-jose) + argon2 (passlib/argon2-cffi) | Revocable refresh tokens in DB |
| Architecture | Modular monolith | NOT microservices |

### Deployment Targets

| Component | Platform |
|-----------|----------|
| Frontend | Vercel |
| Backend | Render or Railway |
| Database | Supabase |

---

## LLM Policy (CRITICAL)

Groq (Llama 3.3) is used ONLY for:
1. **Alert text generation** — formatting human-readable notifications
2. **Trainee chat** — conversational guidance for trainees
3. **Employer free-text parsing** — extracting structured data from unstructured job descriptions

**NEVER use the LLM for:**
- Skill gap scoring
- Supply-demand calculations
- Any deterministic/algorithmic decision
- Ranking, filtering, or prioritization logic

**Fallback requirement:** Every Groq API call MUST have a deterministic template fallback.
If the API is down, the system degrades gracefully with pre-built templates — it never breaks.

---

## RBAC Role Model

| Role | Description |
|------|-------------|
| `trainee` | Individual learner tracking their skills and career path |
| `institute_admin` | Training institute administrator managing courses and batches |
| `employer` | Employer posting skill requirements and job demands |
| `planner` | District/state-level planner viewing aggregate gap analysis |
| `panel_member` | Assessment panel member evaluating trainee competency |

All roles are enforced server-side. Frontend hides UI elements but never trusts client-side role checks.

---

## Phase 2: Schema & Security Architecture

### Core Database Tables (15 tables, all UUID PKs)
- `districts` (administrative units, centroids for maps)
- `trades` (vocational trades with NSQF codes; 5 locked starters)
- `institutes` (training institutes, ITIs, PMKVY centers)
- `users` (auth users, hashed argon2 password, role, district_id, institute_id)
- `panel_members` (1:1 extension of panel_member users)
- `courses` (institute courses with seats_available constraint)
- `job_postings` (ingested job board vacancies with NLP extracted skills)
- `skill_gaps` (algorithmic demand-supply gaps, confidence, breakdown)
- `panel_reviews` (panel evaluation reviews on skill gaps)
- `panel_votes` (individual panel member votes)
- `employer_validations` (employer demand validation submissions)
- `trainee_profiles` (1:1 extension of trainee users)
- `alerts` (notifications generated via template or Groq)
- `flag_annotations` (planner annotations and override flags)
- `refresh_tokens` (SHA-256 hashed refresh tokens for revocable rotation)

### Row-Level Security (RLS)
- Defense-in-depth at the PostgreSQL engine layer.
- Enforced via transaction-scoped `set_config('app.current_*', value, true)` helper (`set_rls_context`).
- Application-layer mirrors: `require_role(*roles)` and `require_own_scope(scope_field)`.
- Local dev seed script: `python scripts/seed_dev.py` (idempotent, populates Pune & Beed, 5 trades, test users for each role).

---

## Monorepo Structure

```
VIKAS/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI app, CORS, lifespan
│   │   ├── core/                # config.py, security.py, deps.py
│   │   ├── db/                  # session.py, base.py
│   │   ├── models/              # SQLAlchemy ORM models
│   │   ├── schemas/             # Pydantic request/response schemas
│   │   ├── routers/             # API route handlers
│   │   └── services/            # Business logic layer
│   ├── alembic/                 # Database migrations
│   ├── tests/                   # pytest test suite
│   ├── pyproject.toml           # Dependencies + tool config
│   └── .env.example             # Required environment variables
├── frontend/
│   ├── src/
│   │   ├── routes/              # Role-based page directories
│   │   │   ├── trainee/
│   │   │   ├── institute/
│   │   │   ├── employer/
│   │   │   ├── planner/
│   │   │   └── panel/
│   │   ├── components/
│   │   │   ├── ui/              # shadcn/ui components
│   │   │   ├── charts/          # Recharts wrappers
│   │   │   └── map/             # Leaflet components
│   │   └── lib/                 # api.ts, auth.ts
│   ├── .env.example
│   └── package.json
├── .github/workflows/ci.yml    # CI pipeline
├── CLAUDE.md                    # THIS FILE
└── README.md                    # Setup instructions
```

---

## Decision Checklist

Before adding a new dependency or changing architecture:

1. Is it in the locked stack above? If not, **stop and ask**.
2. Does it affect scoring or core decisions? If yes, **no LLM**.
3. Does it introduce a new service boundary? If yes, **no — modular monolith**.
4. Does it use Google Maps? **No — Leaflet + OSM only**.
5. Does the Groq call have a template fallback? If not, **add one**.
6. Is the role check server-side? If not, **move it**.
