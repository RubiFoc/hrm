FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_LINK_MODE=copy

WORKDIR /app

RUN pip install --no-cache-dir uv

COPY apps/backend/pyproject.toml apps/backend/README.md ./
COPY apps/backend/src ./src

RUN uv sync --no-dev

EXPOSE 8000

CMD ["uv", "run", "--no-dev", "uvicorn", "--app-dir", "src", "hrm_backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
