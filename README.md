# FinSight

FinSight is a **local, single-user portfolio** personal-finance app: track accounts and transactions, import CSVs, review categories, view monthly analytics, and detect likely recurring payments/income.

It is **not** a multi-tenant product. There is **no authentication**, no Plaid, and no production deployment story. The goal is a clear, interview-ready codebase that demonstrates careful money handling, data provenance, and honest ML experimentation.

## Architecture

```
financeproject/
├── backend/          FastAPI + SQLAlchemy + Alembic + PostgreSQL
└── frontend/         Next.js (App Router) TypeScript UI
```

- **Backend** owns persistence, validation, analytics, CSV import, and recurring detection.
- **Frontend** is a thin client over the HTTP API (Server Components for reads; Client Components for forms).
- **ML categorization** lives under `backend/app/ml/categorization/` as an **offline experiment only** — it is **not** wired into the live API.

## Tech stack

| Layer | Stack |
|-------|--------|
| API | FastAPI, Pydantic Settings, Uvicorn |
| DB | PostgreSQL, SQLAlchemy 2.x, Alembic |
| Money | `Decimal` / SQL `Numeric` (never float for balances/amounts) |
| UI | Next.js App Router, TypeScript |
| Offline ML (optional) | scikit-learn, joblib (`pip install -e ".[ml]"`) |

## Setup / run

### Prerequisites

- Python 3.11+
- Node.js 20+
- PostgreSQL with a local database (default name: `finsight`)

### Backend

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"          # API + tests
# Optional offline ML extras:
# pip install -e ".[ml,dev]"
cp .env.example .env             # set DATABASE_URL for your Postgres user
createdb finsight                # or create the DB another way
alembic upgrade head
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

- Health: http://127.0.0.1:8000/health
- OpenAPI: http://127.0.0.1:8000/docs

### Frontend

```bash
cd frontend
cp .env.example .env.local       # NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8000
npm install
npm run dev
```

Open http://127.0.0.1:3000

## Major features

1. **Accounts** — create/list accounts with a manually reported snapshot balance.
2. **Transactions** — create/list; signed amounts; optional account filter; category review (`PATCH`).
3. **CSV import** — multipart upload with **partial success** (good rows commit; bad rows reported).
4. **Analytics** — month summary: income, spending magnitude, net, MoM spending %, category/merchant breakdowns.
5. **Recurring detection** — deterministic/statistical series from history (`GET /analytics/recurring`).
6. **Offline ML categorization** — train/eval scripts only; not used by the API.

## Decimal / money design

- API and ORM store money as **`Decimal` / `Numeric(…, 2)`**.
- Parsing and aggregates avoid unnecessary `float` casts.
- Display formats strings from the API; calculations stay decimal-safe on the backend.

## CSV import (partial success)

`POST /transactions/import` accepts `account_id` + file.

- Validates headers, UTF-8, size limit.
- Imports valid rows in one commit; rejects invalid/duplicate rows with per-row errors.
- Error `row` uses the CSV parser’s **physical line number** (`reader.line_num`) so blank lines and multiline quirks report correctly.
- Dedupe is heuristic on `(account, date, merchant, amount, description)`.
- Imported categories get `category_source=csv`.

## Category provenance

Each transaction tracks:

- `category` — canonical taxonomy (unsupported → `other`; blank → `uncategorized`)
- `category_source` — `user` | `csv` | `rules` | `model` | `unknown`
- `category_confidence` — only meaningful for model predictions; **null** in the live app today

User corrections via `PATCH /transactions/{id}/category` set `category_source=user` and clear confidence.

## Recurring detection

`GET /analytics/recurring` computes series on read (no `is_recurring` DB column).

- Groups by `(account_id, normalize_merchant(merchant))`
- Requires ≥3 observations and regular weekly / biweekly / monthly cadence
- Monthly uses **calendar-month** arithmetic (± day tolerance), not “always 30 days”
- Distinguishes fixed vs variable amounts; confidence is an **explainable heuristic**, not a calibrated probability

## ML experiment (offline, not integrated)

Location: `backend/app/ml/categorization/`

```bash
cd backend && source .venv/bin/activate
pip install -e ".[ml,dev]"
python -m app.ml.categorization.train
```

Committed evidence: `backend/app/ml/categorization/RESULTS.md` and `results_metrics.json`.
Heavy `.joblib` model files stay gitignored.

### Methodology and limitations

- Trusted labels for training would be `user`/`csv` only; real DB labels are currently **insufficient**.
- Experiments use a **synthetic fixture** so the pipeline can run end-to-end.
- **Synthetic description text carries much of the signal** and may not resemble real bank-feed descriptors.
- The **rule baseline is not an independent benchmark**: rule vocabulary overlaps the synthetic fixture.
- Evaluation compares **random stratified** vs **merchant-grouped** splits. Grouped splits are harder and more realistic (no merchant leakage). Random splits can look optimistic when the same merchant appears in train and test.
- Merchant-grouped metrics are reported as **mean ± std over multiple seeds** (see `backend/app/ml/categorization/RESULTS.md`).
- Artifacts (`.joblib`) are gitignored; reproducible summary metrics are committed in `RESULTS.md`.

**The production API does not load or serve ML category predictions.**

## Auth / deployment posture

This is a **local portfolio system**: no login, no multi-user isolation, `DEBUG` defaults to **false** (enable only in `.env` for local work). Do not expose it on the public internet as-is.

## Known limitations

- Snapshot `current_balance` is **not** a live ledger balance (not updated by transactions).
- Merchant identity is light normalization only (`NETFLIX.COM` ≠ `Netflix`).
- Recurring detection defers quarterly/yearly patterns; mixed recurring + one-off spend at one merchant can confuse cadence.
- Real labeled data is too thin to retrain/integrate categorization.
- No auth, bank sync, anomaly detection, forecasting, or mobile apps.

## License

Portfolio / personal use.
