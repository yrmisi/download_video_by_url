FROM python:3.14.3-slim-trixie AS builder

COPY --from=ghcr.io/astral-sh/uv:0.11.14 /uv /uvx /bin/

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_NO_DEV=1

WORKDIR /app

COPY pyproject.toml uv.lock ./

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-install-project

COPY app/ ./app/
COPY alembic/ ./alembic/
COPY alembic.ini ./

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen

FROM python:3.14.3-slim-trixie

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/app/.venv/bin:$PATH"

WORKDIR /app

RUN apt-get update && \
    apt-get install -y --no-install-recommends curl ffmpeg && \
    rm -rf /var/lib/apt/lists/*

COPY --link --from=denoland/deno:bin-2.7.14 /deno /usr/local/bin/deno

COPY --link --from=builder /app/ /app/

RUN groupadd --gid 1000 appuser && \
    useradd --uid 1000 --gid appuser -m appuser && \
    chown -R appuser:appuser /app

RUN mkdir -p /app/downloads && \
    chown -R appuser:appuser /app/downloads

USER appuser

EXPOSE 8000

CMD ["granian", "app.main:app", \
     "--interface", "asgi", \
     "--host", "0.0.0.0", \
     "--port", "8000", \
     # оставляем один workers, что б не было конфликта из-за фоновых task по удаления
     "--workers", "1", \
     "--runtime-threads", "1", \
     "--loop", "uvloop", \
     "--backlog", "1024", \
     "--backpressure", "128", \
     "--log-level", "warning", \
     "--access-log"]
