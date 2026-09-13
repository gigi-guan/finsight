# FinSight Backend

FastAPI service for the FinSight monorepo. Full product context: **[root README](../README.md)**.

## Setup

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
# Optional offline ML:
# pip install -e ".[ml,dev]"
cp .env.example .env
# Set DATABASE_URL to your local Postgres user/database
```

## Database

```bash
createdb finsight
alembic upgrade head
```

## Run

```bash
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

- Health: http://127.0.0.1:8000/health
- Docs: http://127.0.0.1:8000/docs

## Tests

```bash
pytest
```
