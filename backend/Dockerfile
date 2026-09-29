# syntax=docker/dockerfile:1.7
FROM ghcr.io/astral-sh/uv:0.5.24 AS uv

FROM python:3.12.8-slim-bookworm AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

RUN groupadd --gid 10001 app \
    && useradd --uid 10001 --gid app --create-home app

WORKDIR /app
COPY --from=uv /uv /uvx /bin/
COPY pyproject.toml uv.lock ./
RUN uv sync --locked --no-install-project --no-dev

COPY alembic.ini ./
COPY migrations ./migrations
COPY src ./src
RUN uv sync --locked --no-dev

USER 10001:10001
EXPOSE 8000
CMD ["uv", "run", "--no-sync", "uvicorn", "vbe_hub.api.app:app", "--host", "0.0.0.0", "--port", "8000"]

FROM runtime AS development
USER root
COPY tests ./tests
RUN uv sync --locked
USER 10001:10001
