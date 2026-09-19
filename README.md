# VIKAS — Viksit India Kaushal Alignment System

District-level skill demand-supply gap analysis platform for India's workforce development ecosystem.

## Prerequisites

- **Python 3.12+** — [python.org/downloads](https://www.python.org/downloads/)
- **Node.js 20+** — [nodejs.org](https://nodejs.org/)
- **PostgreSQL 15+** — via [Supabase](https://supabase.com/) (recommended) or local install
- **Git** — [git-scm.com](https://git-scm.com/)

## Repository Structure

```
VIKAS/
├── backend/          # FastAPI (Python 3.12)
├── frontend/         # React + Vite + TypeScript
├── .github/workflows # CI pipeline
├── CLAUDE.md         # Architecture decisions (READ FIRST)
└── README.md         # This file
```

## Quick Start

### 1. Clone and configure environment

```bash
git clone <repo-url> VIKAS
cd VIKAS
```

### 2. Backend Setup

```bash
cd backend

# Create and activate virtual environment
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS/Linux:
# source .venv/bin/activate

# Install dependencies (core + dev)
pip install -e ".[dev]"

# Copy environment template and fill in values
cp .env.example .env
# Edit .env with your Supabase, Groq, and API credentials

# Run database migrations
alembic upgrade head

# Start the development server
uvicorn app.main:app --reload --port 8000
```

The API will be available at `http://localhost:8000`. API docs at `http://localhost:8000/docs`.

### 3. Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Copy environment template and fill in values
cp .env.example .env
# Edit .env with your API URL and Supabase credentials

# Start the development server
npm run dev
```

The app will be available at `http://localhost:5173`.

### 4. Running Both Servers

Open two terminal windows:
- Terminal 1: `cd backend && uvicorn app.main:app --reload --port 8000`
- Terminal 2: `cd frontend && npm run dev`

## Running Tests

### Backend

```bash
cd backend
pytest tests/ -v              # Run all tests
pytest tests/ -v -x           # Stop on first failure
pytest tests/ -v --tb=short   # Short tracebacks
```

### Frontend

```bash
cd frontend
npm run test                  # Run all tests (watch mode)
npx vitest run                # Run all tests (CI mode, no watch)
```

## Linting & Type Checking

### Backend

```bash
cd backend
ruff check app/ tests/        # Lint
ruff format app/ tests/        # Auto-format
mypy app/                      # Type check
```

### Frontend

```bash
cd frontend
npx eslint src/ --ext .ts,.tsx  # Lint
npx prettier --write src/       # Auto-format
npx tsc --noEmit                # Type check
```

## Database Migrations

```bash
cd backend

# Create a new migration after model changes
alembic revision --autogenerate -m "description of change"

# Apply pending migrations
alembic upgrade head

# Rollback one migration
alembic downgrade -1
```

## Pre-commit Hooks

```bash
cd backend
pre-commit install             # Install hooks (one-time)
pre-commit run --all-files     # Run all hooks manually
```

## CI Pipeline

GitHub Actions runs on every push to `main` and every PR:
- **Backend**: ruff lint → ruff format check → mypy → pytest
- **Frontend**: eslint → tsc → vitest

All checks must pass for a PR to merge.

## Architecture

See [CLAUDE.md](./CLAUDE.md) for the complete architecture reference, including:
- Locked technology stack
- RBAC role model
- LLM usage policy
- Folder structure guide
