# Backend (uv)

## Setup
- Install dependencies: `uv sync --project .`
- Run app: `uv run --project . uvicorn hrm_backend.main:app --reload`
- Run tests: `uv run --project . pytest -q`
- Run lint: `uv run --project . ruff check .`
