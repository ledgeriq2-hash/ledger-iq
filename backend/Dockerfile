FROM python:3.11-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=off \
    PIP_DISABLE_PIP_VERSION_CHECK=on \
    PIP_DEFAULT_TIMEOUT=100

WORKDIR /app

FROM base AS builder
RUN apt-get update && apt-get install -y --no-install-recommends build-essential libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt /app/requirements.txt
RUN pip install --upgrade pip && pip install --prefix=/install -r /app/requirements.txt

FROM base AS runtime
RUN apt-get update && apt-get install -y --no-install-recommends libpq-dev curl \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder /install /usr/local
COPY backend /app

ENV PYTHONPATH=/app
EXPOSE 8000

CMD ["sh", "-c", "alembic upgrade head && exec gunicorn -k uvicorn.workers.UvicornWorker app.main:app --bind 0.0.0.0:8000 --workers ${WORKERS:-3} --timeout 60"]
