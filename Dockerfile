# syntax=docker/dockerfile:1
# ---------------------------------------------------------------- build
FROM python:3.14-slim AS builder
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
WORKDIR /build
COPY requirements.txt .
RUN python -m venv /opt/venv \
    && /opt/venv/bin/pip install --upgrade pip \
    && /opt/venv/bin/pip install -r requirements.txt

# ---------------------------------------------------------------- runtime
FROM python:3.14-slim AS runtime
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PATH="/opt/venv/bin:$PATH"
# Sin apt-get: el healthcheck usa Python, no curl.
RUN useradd --create-home --shell /bin/bash --uid 1000 app
WORKDIR /app
COPY --from=builder /opt/venv /opt/venv
COPY --chown=app:app app/ app/
# Storage de NiceGUI (tema elegido por navegador): debe existir con dueño 'app' para que el volumen lo herede.
RUN mkdir -p /app/.nicegui && chown app:app /app/.nicegui
USER 1000:1000
EXPOSE 8080
# /api/health responde 503 si la BD no contesta: sano = app + Postgres.
HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
    CMD ["python", "-c", "import urllib.request,sys; sys.exit(urllib.request.urlopen('http://localhost:8080/api/health', timeout=4).status != 200)"]
CMD ["python", "-m", "app.main"]
