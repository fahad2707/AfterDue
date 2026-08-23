# RECLAIM backend. Railway / any container host.
# The committed model artifact is copied in; do not train on the container
# filesystem and expect that file to survive a restart.

FROM python:3.12-slim

WORKDIR /app

COPY backend/pyproject.toml backend/uv.lock ./
RUN pip install --no-cache-dir uv \
    && uv sync --frozen --no-dev

COPY backend/app ./app

ENV PYTHONUNBUFFERED=1
ENV APP_ENV=production
ENV LLM_ENABLED=false

ENV PATH="/app/.venv/bin:$PATH"

EXPOSE 8000

CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
