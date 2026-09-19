# VIKAS — Production Deployment Runbook

This document details the step-by-step procedures for deploying, maintaining, migrating, and rolling back the VIKAS platform (Viksit India Kaushal Alignment System) in production environments.

---

## 1. System Architecture Overview

```
                          ┌───────────────────────────┐
                          │   Client Browser / Mobile │
                          └─────────────┬─────────────┘
                                        │ HTTPS
                     ┌──────────────────┴──────────────────┐
                     │                                     │
                     ▼                                     ▼
        ┌─────────────────────────┐           ┌─────────────────────────┐
        │      Frontend SPA       │           │       Backend API       │
        │      (Vercel / CDN)     │           │    (Render / Railway)   │
        │   React 18 + Vite + TS  │           │   FastAPI + Uvicorn     │
        └─────────────────────────┘           └────────────┬────────────┘
                                                           │ AsyncPG (Pool 5-15)
                                                           ▼
                                              ┌─────────────────────────┐
                                              │   Managed PostgreSQL    │
                                              │  (Supabase / AWS RDS)   │
                                              │  RLS + Audit Logs + BKP │
                                              └─────────────────────────┘
```

---

## 2. Required Production Environment Variables

### Backend Configuration

| Variable | Description | Required | Example / Recommendation |
|---|---|:---:|---|
| `DATABASE_URL` | Async PostgreSQL connection string | Yes | `postgresql+asyncpg://user:pass@aws-0-ap-south-1.pooler.supabase.com:6543/postgres` |
| `JWT_SECRET` | Primary 256-bit cryptographically secure secret | Yes | Generate via: `openssl rand -hex 32` |
| `JWT_SECRET_FALLBACK` | Secondary secret during key rotation window | No | Set when rotating keys (see `docs/JWT_ROTATION_RUNBOOK.md`) |
| `JWT_ALGORITHM` | JWT signing algorithm | No | Default: `HS256` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Access token lifespan | No | Default: `30` |
| `REFRESH_TOKEN_EXPIRE_DAYS` | Refresh token lifespan | No | Default: `7` |
| `CORS_ORIGINS` | Comma-delimited list of allowed origin URLs | Yes | `https://vikas.gov.in,https://app.vikas.gov.in` (Never `*` in prod) |
| `ENVIRONMENT` | Runtime mode (`development`, `staging`, `production`) | Yes | `production` (enables exception masking & security headers) |
| `GROQ_API_KEY` | Groq LLM API Key (alert copy, career chat, text parsing) | Yes | `gsk_...` |
| `ADZUNA_APP_ID` | Adzuna Job Scraper App ID | Optional | External ingestion feed |
| `ADZUNA_APP_KEY` | Adzuna Job Scraper API Key | Optional | External ingestion feed |
| `JOOBLE_API_KEY` | Jooble Job Feed API Key | Optional | External ingestion feed |

### Frontend Configuration

| Variable | Description | Required | Example |
|---|---|:---:|---|
| `VITE_API_BASE_URL` | Fully qualified backend URL | Yes | `https://api.vikas.gov.in` |

---

## 3. Database Migration Strategy (Zero-Downtime)

Alembic migrations must be executed automatically before application containers serve traffic.

### Migration Principles
1. **Additive Schema Changes First**: Adding tables, nullable columns, and non-blocking indexes can run while the previous container version is active.
2. **Backwards Compatibility**: Code changes must never assume new or dropped columns exist simultaneously without migration phasing.
3. **Execution Point**: The container startup script executes `alembic upgrade head` before spawning the `uvicorn` master worker:
   ```bash
   alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port $PORT --workers 2
   ```

### Verifying Pending Migrations Locally or in CI
```bash
# Check current database revision vs head
alembic current
alembic heads

# Apply migrations
alembic upgrade head

# Roll back exactly 1 revision if needed
alembic downgrade -1
```

---

## 4. Platform-Specific Deployment Guides

### Option A: Render Deployment (Recommended Backend)

The project includes a declarative `render.yaml` specification.

1. **Connect GitHub Repository**: Link `VIKAS` repo to Render.
2. **Create Blueprint**: Render will automatically detect `render.yaml` defining the `vikas-backend` Docker web service.
3. **Configure Environment Secrets**: In the Render Dashboard under **Environment**, populate:
   - `DATABASE_URL`
   - `JWT_SECRET`
   - `GROQ_API_KEY`
   - `CORS_ORIGINS`
4. **Health Check**: Render monitors `GET /health`. If the database check (`SELECT 1`) fails, the deployment aborts with HTTP 503 without terminating the previous healthy instance.

### Option B: Railway Deployment (Alternative Backend)

The project includes `railway.json`.

1. Install Railway CLI: `npm install -g @railway/cli`
2. Initialize project: `railway init`
3. Add PostgreSQL plugin or provide external Supabase connection string under `DATABASE_URL`.
4. Deploy: `railway up`

### Option C: Vercel Deployment (Frontend SPA)

The project includes `frontend/vercel.json` with client-side SPA rewrites and hardened HTTP headers.

1. Install Vercel CLI: `npm install -g vercel`
2. Link project from `frontend/`:
   ```bash
   cd frontend
   vercel
   ```
3. Set environment variable:
   ```bash
   vercel env add VITE_API_BASE_URL production https://api.vikas.gov.in
   ```
4. Deploy to production:
   ```bash
   vercel --prod
   ```

---

## 5. Health Check & Observability Monitoring

### Automated Probes
- **Endpoint**: `GET /health`
- **Response HTTP 200 (Healthy)**:
  ```json
  {
    "status": "healthy",
    "database": "connected",
    "timestamp": "2026-09-19T18:45:10.123456Z"
  }
  ```
- **Response HTTP 503 (Unhealthy)**:
  ```json
  {
    "status": "unhealthy",
    "database": "disconnected",
    "timestamp": "2026-09-19T18:45:10.123456Z"
  }
  ```

### Request Correlation & Structured Logs
All requests emit structured JSON logs with correlation IDs:
- Inbound headers checked: `X-Request-ID`
- Outbound headers returned: `X-Request-ID`
- When triaging 500 error reports or performance anomalies, grep by `request_id`:
  ```bash
  grep "req_abc123xyz" /var/log/vikas/service.log
  ```

---

## 6. Rollback Procedures

### Application Rollback
1. **Container / Web Service Rollback**:
   - In Render: Go to Service -> **Deploys** -> Select previous stable deployment -> **Rollback**.
   - In Railway: Re-deploy previous commit SHA.
   - In Vercel: Promote previous deployment instantaneously in Dashboard.

### Database Rollback
If a migration introduced breaking constraints or faulty schema:
1. SSH / CLI into running container or local maintenance machine with access to `DATABASE_URL`:
   ```bash
   alembic downgrade -1
   ```
2. Verify schema status:
   ```bash
   alembic current
   ```
3. Check audit log integrity:
   ```sql
   SELECT count(*) FROM audit_logs WHERE recorded_at >= NOW() - INTERVAL '1 hour';
   ```

