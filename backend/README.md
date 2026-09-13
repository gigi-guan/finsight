# FinSight Backend

Minimal FastAPI service for the FinSight monorepo.

## Setup

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
cp .env.example .env
# Edit DATABASE_URL if your Postgres user/db differ
```

## Database

```bash
createdb finsight
alembic upgrade head
```

## Run

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

- Health: http://localhost:8000/health
- Docs: http://localhost:8000/docs
