#!/usr/bin/env bash
# Smoke test del stack levantado: salud, API y que cada pantalla responda 200.
# Uso: ./scripts/smoke.sh [URL_BASE]   (por defecto http://localhost:8095)
set -euo pipefail
BASE="${1:-http://localhost:8095}"
fallos=0
check() {
  local ruta="$1" esperado="${2:-200}" codigo
  codigo=$(curl -s -o /dev/null -w '%{http_code}' "$BASE$ruta")
  if [[ "$codigo" == "$esperado" ]]; then printf '  ok   %s %s\n' "$codigo" "$ruta"
  else printf '  FALLA %s %s (esperado %s)\n' "$codigo" "$ruta" "$esperado"; fallos=$((fallos + 1)); fi
}
echo "Smoke contra $BASE"
check /api/live
check /api/health
check /api/stats
check /docs
for ruta in / /repaso /mazos /tarjetas /ganchos /palacio /gimnasio /estadisticas /importar /metodo; do
  check "$ruta"
done
curl -sf "$BASE/api/health" | grep -q '"status":"ok"' || { echo "  FALLA /api/health sin status ok"; fallos=$((fallos + 1)); }
[[ $fallos -eq 0 ]] && echo "Smoke en verde" || { echo "$fallos fallos"; exit 1; }
