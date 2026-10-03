# AI Health Agent — Backend

FastAPI + SQLAlchemy + Alembic, backed by **Supabase Postgres**. Phase 0: foundations
(data model, migrations, health checks, minimal Users CRUD).

## Prerequisites

- Python 3.12+ (developed on 3.14)
- A Supabase project (free tier is fine)
- No Docker and no local Postgres required — the database is Supabase (cloud).

## Setup

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate          # Windows (PowerShell/Git Bash)
# source .venv/bin/activate     # macOS/Linux
pip install -r requirements-dev.txt

cp .env.example .env            # then edit .env with your Supabase URLs
```

### Filling in `.env`

Both URLs come from the Supabase dashboard → **Project Settings → Database**:

| Var | Which connection | Port | Used by |
|-----|------------------|------|---------|
| `DATABASE_URL` | Direct connection (URI) | 5432 | Alembic migrations |
| `DATABASE_POOL_URL` | Connection pooling → Transaction mode | 6543 | the app at runtime |

> **IPv6 note:** Supabase serves the direct host (`db.<ref>.supabase.co`) over IPv6 only.
> If your network has no IPv6 and `DATABASE_URL` won't connect, use the **session-mode
> pooler** string instead (pooler host, port **5432**) — it works over IPv4 and behaves
> like a direct connection for migrations.

## Run the migrations

```bash
cd backend
alembic upgrade head
```

To (re)generate a migration after changing models:

```bash
alembic revision --autogenerate -m "describe change"
alembic upgrade head
```

## Run the API

```bash
cd backend
uvicorn app.main:app --reload
```

- Liveness:  http://localhost:8000/health
- DB check:  http://localhost:8000/health/db
- Docs:      http://localhost:8000/docs

## Tests & lint

```bash
cd backend
pytest -q
ruff check .
```

## Data model (Phase 0)

10 tables: `users`, `sessions`, `conversation_messages`, `food_logs`, `food_items`,
`exercise_logs`, `daily_summaries`, `user_memory`, `reports`, `llm_monitoring_logs`.
Traceability columns (`langfuse_trace_id`, `prompt_version`) are on `food_logs`,
`conversation_messages`, and `reports`.

---

## Phase 0 — remaining manual setup (needs your accounts)

These require your own accounts and are left for you to do (or to approve me walking
you through):

- [x] **Supabase**: project created, connection strings in `backend/.env`, schema migrated.
- [x] **GitHub**: repo connected — https://github.com/Deep-Arande/Hygeia-ai (CI runs on push).
- [ ] **Railway**: create a project from the repo; it builds `backend/Dockerfile`.
      Set `DATABASE_URL` / `DATABASE_POOL_URL` as Railway variables. (Redis + worker
      services are added in Phase 5.)
