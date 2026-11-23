# School Fee & Payment Tracker

Multi-tenant school fee and payment tracking with automatic M-Pesa reconciliation.
Built with Django 5, Django REST Framework, PostgreSQL, Redis/Celery, and React + Vite.

## Repository layout

```
schoolpay/
  backend/          # Django project (config/ + apps/)
  frontend/         # React + Vite + TypeScript app (Phase 6)
  docker-compose.yml   # Postgres + Redis
  README.md         # this file
```

## Prerequisites (Windows / PowerShell)

- Python 3.11+ (3.14 tested)
- Docker Desktop (provides Postgres 15 and Redis 7)
- `git`

## 1. Backend setup

```powershell
# Open a PowerShell terminal in the schoolpay folder
cd C:\Users\linzs\Projects\FeePayment\schoolpay\backend

# Create and activate a virtual environment
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# Install the package in editable mode with dev tools (pytest, ruff, ...)
pip install -e ".[dev]"

# Copy the environment template and fill in real values before first run
copy .env.example .env
# NOTEPAD .env   # edit SECRET_KEY and any other values
```

> If you get an execution-policy error activating the venv, run:
> `Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser`

## 2. Start infrastructure (Postgres + Redis) — optional for initial dev

`dev.py` uses **SQLite by default**, so you can run and test immediately without
Docker. When you are ready for the production stack (PostgreSQL + Redis), start
the containers from the `schoolpay` folder and switch `dev.py` back to the
PostgreSQL configuration in `base.py`.

```powershell
cd C:\Users\linzs\Projects\FeePayment\schoolpay
docker compose up -d
docker compose ps
```

## 3. Database migrations

```powershell
cd backend
.\.venv\Scripts\python.exe manage.py makemigrations tenants accounts
.\.venv\Scripts\python.exe manage.py migrate
```

With SQLite (the dev default) this works without Docker. With PostgreSQL, make
sure `docker compose up -d` has run first.

Create a superuser (used to access Django admin and create the first school):

```powershell
.\.venv\Scripts\python.exe manage.py createsuperuser
```

## 4. Run the development server

```powershell
.\.venv\Scripts\python.exe manage.py runserver
```

API docs: http://localhost:8000/api/docs/
Admin UI: http://localhost:8000/admin/

## 5. Run the test suite

```powershell
.\.venv\Scripts\python.exe -m pytest
```

Run a single app's tests:

```powershell
.\.venv\Scripts\python.exe -m pytest apps/accounts tests -v
```

## 6. Linting / formatting

```powershell
.\.venv\Scripts\python.exe -m ruff check .
.\.venv\Scripts\python.exe -m ruff format --check .
# Auto-fix lint issues and format:
.\.venv\Scripts\python.exe -m ruff check --fix .
.\.venv\Scripts\python.exe -m ruff format .
```

## 7. Celery background jobs

In development, `dev.py` sets `CELERY_TASK_ALWAYS_EAGER = True`, so tasks run
inline and you do **not** need a Celery worker. When you are ready for async
processing:

```powershell
# Start a Celery worker (requires Redis running via docker compose)
.\.venv\Scripts\python.exe -m celery -A config worker -l info
```

## 8. Environment variables

All secrets come from `.env` (never committed). See `backend/.env.example` for
the full list: Django secret, database, Redis, JWT lifetimes, CORS, M-Pesa
Daraja sandbox credentials, and Africa's Talking SMS settings.

## Phases

- Phase 0 (done): scaffolding — this README, Docker Compose, settings split,
  custom User model, JWT auth, tenant base model, pre-commit, CI.
- Phase 1: core data (School, academic structure, students, guardians, import).
- Phase 2: fees, invoices, append-only ledger.
- Phase 3: M-Pesa C2B (Daraja) + simulator.
- Phase 4: reconciliation engine.
- Phase 5: receipts, statements, SMS.
- Phase 6: React bursar frontend.
- Phase 7: STK Push + parent portal.
- Phase 8: hardening, load tests, deployment guide.