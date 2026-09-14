FROM python:3.13.7-slim-bookworm AS builder

ENV PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /build
COPY requirements.txt .
RUN python -m venv /opt/venv \
    && /opt/venv/bin/pip install --upgrade pip \
    && /opt/venv/bin/pip install --requirement requirements.txt

FROM builder AS test

ENV PATH=/opt/venv/bin:$PATH \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/srv/app \
    APP_OTEL_ENABLED=false

WORKDIR /srv/app
COPY requirements-dev.txt /tmp/requirements-dev.txt
COPY requirements.txt /tmp/requirements.txt
RUN pip install --requirement /tmp/requirements-dev.txt
COPY app ./app
COPY tests ./tests

CMD ["pytest", "-q", "tests"]

FROM python:3.13.7-slim-bookworm AS runtime

ENV PATH=/opt/venv/bin:$PATH \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/srv/app

RUN groupadd --gid 10001 appgroup \
    && useradd --uid 10001 --gid appgroup --no-create-home --shell /usr/sbin/nologin appuser

WORKDIR /srv/app
COPY --from=builder /opt/venv /opt/venv
COPY app ./app

USER 10001:10001
EXPOSE 8000

HEALTHCHECK --interval=10s --timeout=3s --start-period=20s --retries=5 \
  CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health/live', timeout=2)"]

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--no-access-log", "--proxy-headers", "--forwarded-allow-ips=127.0.0.1"]
