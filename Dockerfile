FROM ghcr.io/astral-sh/uv:0.12.17 AS uv

FROM python:3.14.8-slim-trixie AS builder

COPY --from=uv /uv /uvx /bin/

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/opt/venv \
    UV_PYTHON_DOWNLOADS=never \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

COPY pyproject.toml uv.lock ./
RUN uv sync --locked --no-install-project --no-dev

COPY manage.py ./
COPY config ./config
COPY core ./core
COPY accounts ./accounts
COPY surveys ./surveys
COPY answers ./answers
COPY analytics ./analytics

FROM python:3.14.8-slim-trixie

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    VIRTUAL_ENV=/opt/venv \
    PATH=/opt/venv/bin:$PATH \
    DJANGO_SETTINGS_MODULE=config.settings

WORKDIR /app

COPY --from=builder /opt/venv /opt/venv
COPY --from=builder /app /app

RUN useradd --create-home --uid 1000 django \
    && mkdir -p /app/data/db /app/data/logs /app/data/static /app/data/media \
    && chown -R django:django /app/data

USER django

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/admin/login/', timeout=3)"

CMD ["granian", "--interface", "asginl", "--host", "0.0.0.0", "--port", "8000", \
     "--http", "1", "--no-ws", "--no-access-log", "--no-metrics", "--no-reload", \
     "--workers", "2", "--backpressure", "16", "config.asgi:application"]
