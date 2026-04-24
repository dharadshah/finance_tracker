# Finance Tracker

A locally hosted personal finance tracker covering bank accounts, credit cards,
mutual funds, and stock portfolios. Built with Python, SQLAlchemy, and Gradio.

## Tech stack

- Python 3.11+
- SQLAlchemy 2.0 (ORM + migrations via Alembic)
- Gradio 4.x (dashboard UI)
- Pandas (data processing)
- Plotly (charts)
- pdfplumber (bank statement parsing)
- SQLite (local database)

## Project structure

```
finance_tracker/
    models/         ORM models — one file per domain
    parsers/        Statement parsers — one class per bank/source
    repositories/   Data access layer — queries and writes
    services/       Business logic — calculations, XIRR, net worth
    ui/             Gradio dashboard — one file per tab
    utils/          Shared helpers
config.py           Settings loaded from .env
database.py         Engine, session factory, init_db()

scripts/
    seed_categories.py    Populate default expense categories

tests/
    test_models/
    test_parsers/
    test_services/

main.py             Entry point
```

## Setup

```powershell
# 1. Clone the repo
git clone <your-repo-url>
cd finance_tracker

# 2. Install Poetry if not already installed
(Invoke-WebRequest -Uri https://install.python-poetry.org -UseBasicParsing).Content | python -

# 3. Install dependencies
poetry install

# 4. Copy and configure environment
copy .env.example .env

# 5. Seed the categories table
poetry run python scripts/seed_categories.py

# 6. Run the app
poetry run python main.py
```

Open http://127.0.0.1:7860 in your browser.

## Development

```powershell
# Run tests
poetry run pytest

# Lint
poetry run ruff check .

# Type check
poetry run mypy finance_tracker
```

## Versioning

| Version | Phase     | Description                        |
|---------|-----------|------------------------------------|
| 0.1.0   | Phase 1   | Database schema and project setup  |
| 0.2.0   | Phase 2   | Bank statement parser              |
| 0.3.0   | Phase 3   | CC, MF, and stock importers        |
| 0.4.0   | Phase 4   | Gradio dashboard                   |
| 0.5.0   | Phase 5   | Monthly workflow and polish        |

## Git commit conventions

```
feat: add HDFC bank statement parser
fix: handle missing date in ICICI CSV
refactor: extract base parser interface
chore: bump sqlalchemy to 2.0.30
docs: update setup instructions
```
