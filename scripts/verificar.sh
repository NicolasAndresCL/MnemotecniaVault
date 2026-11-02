#!/usr/bin/env bash
# Clon local del CI: reproduce los jobs de .github/workflows/ci.yml sobre un CLON LIMPIO de HEAD
# (el runner solo ve lo versionado), con un venv nuevo de Python 3.14, en el mismo orden.
# Uso (Git Bash, desde la raíz): ./scripts/verificar.sh [--sin-docker]
set -euo pipefail
RAIZ="$(cd "$(dirname "$0")/.." && pwd)"
SIN_DOCKER="${1:-}"
PY_BASE="${PYTHON:-py -3.14}"; command -v py >/dev/null 2>&1 || PY_BASE="python3.14"
export PYTHONIOENCODING=utf-8
paso() { printf '\n\033[1;34m== %s\033[0m\n' "$1"; }

TMP="$(mktemp -d)"
limpiar() {
  docker stop mnemo-pgtest >/dev/null 2>&1 || true
  (cd "$TMP/repo" 2>/dev/null && docker compose down -v --remove-orphans >/dev/null 2>&1) || true
  rm -rf "$TMP"
}
trap limpiar EXIT

paso "clon limpio de HEAD ($(git -C "$RAIZ" rev-parse --short HEAD))"
if [[ -n "$(git -C "$RAIZ" status --porcelain)" ]]; then
  echo "AVISO: hay cambios sin commitear; el clon verifica solo lo commiteado (igual que el CI)."
fi
git clone --quiet "$RAIZ" "$TMP/repo"
cd "$TMP/repo"
$PY_BASE -m venv .venv-ci
PY="$(pwd)/.venv-ci/Scripts/python.exe"; [[ -x $PY ]] || PY="$(pwd)/.venv-ci/bin/python"
"$PY" -m pip install -q --upgrade pip
"$PY" -m pip install -q -r requirements-dev.txt
# Mismo entrypoint que el CI: `pytest`, no `python -m pytest` (este añade el cwd al sys.path).
PYTEST="$(dirname "$PY")/pytest"
"$PY" --version

paso "lint: ruff + formato + bit de ejecución de los .sh"
"$PY" -m ruff check .
"$PY" -m ruff format --check .
# En Windows un .sh nuevo entra como 100644 y en el runner Linux da "Permission denied".
if git ls-files -s -- '*.sh' | grep -v '^100755'; then
  echo "Scripts sin bit de ejecución: git update-index --chmod=+x <archivo>"; exit 1
fi

paso "test (SQLite, cobertura >= 90)"
"$PYTEST" -rs --cov --cov-fail-under=90

[[ "$SIN_DOCKER" == "--sin-docker" ]] && { printf '\n\033[1;33mSaltando jobs con Docker.\033[0m\n'; exit 0; }

paso "lint de contenedores y manifiestos: hadolint + compose config + kustomize/kubeconform"
docker run --rm -i hadolint/hadolint < Dockerfile
POSTGRES_PASSWORD=ci STORAGE_SECRET=ci docker compose config --quiet
kubectl kustomize k8s | docker run --rm -i ghcr.io/yannh/kubeconform:v0.7.0 -strict -summary

paso "test-postgres (Postgres 18 efímero en :5433)"
docker rm -f mnemo-pgtest >/dev/null 2>&1 || true
docker run -d --rm --name mnemo-pgtest -e POSTGRES_USER=app -e POSTGRES_PASSWORD=app \
  -e POSTGRES_DB=app_test -p 5433:5432 postgres:18-alpine >/dev/null
until docker exec mnemo-pgtest pg_isready -U app -d app_test >/dev/null 2>&1; do sleep 1; done
sleep 1
TEST_DATABASE_URL=postgresql+psycopg://app:app@localhost:5433/app_test "$PYTEST" -rs -p no:cacheprovider
docker stop mnemo-pgtest >/dev/null

paso "build: compose up --wait + smoke (proyecto y puerto aparte, se baja al terminar)"
export COMPOSE_PROJECT_NAME=mnemo-verificar APP_PORT=18095 IMPORT_ON_STARTUP=false
export POSTGRES_PASSWORD STORAGE_SECRET
POSTGRES_PASSWORD=$("$PY" -c "import secrets; print(secrets.token_hex(16))")
STORAGE_SECRET=$("$PY" -c "import secrets; print(secrets.token_hex(24))")
docker compose up -d --build --wait --wait-timeout 180
./scripts/smoke.sh "http://localhost:$APP_PORT"
docker compose down -v --remove-orphans
printf '\n\033[1;32mTodo el pipeline en verde sobre un clon limpio (stack de prueba bajado).\033[0m\n'
