#!/usr/bin/env bash
# run.sh — pipeline completo: spec -> validación -> DXF -> validación -> PNG/DWG
# Uso: ./run.sh [spec.json] [out_dir]
#   ./run.sh typologies/semillas/casa_8.66x20.json
#   ./run.sh casos/<slug>/spec.json out/<slug>
set -uo pipefail
cd "$(dirname "$0")"

SPEC=${1:-typologies/semillas/casa_8.66x20.json}
OUT=${2:-out}
NAME=$(basename "$SPEC" .json)
mkdir -p "$OUT"

echo "== 0/4 preflight del spec =="
python3 tools/validate_spec.py "$SPEC" || exit 1

echo "== 1/4 generar =="
python3 plan.py "$SPEC" "$OUT/$NAME.dxf" || exit 1

echo "== 2/4 validar =="
CHECK=0
python3 check.py "$OUT/$NAME.dxf" "$SPEC" || CHECK=1

echo "== 3/4 render PNG =="
if command -v cadcraft-cli >/dev/null 2>&1; then
  cadcraft-cli convert "$OUT/$NAME.dxf" "$OUT/$NAME.png" && echo "  $OUT/$NAME.png"
  echo "== 4/4 DWG + PDF =="
  cadcraft-cli convert "$OUT/$NAME.dxf" "$OUT/$NAME.dwg" && echo "  $OUT/$NAME.dwg"
  cadcraft-cli convert "$OUT/$NAME.dxf" "$OUT/$NAME.pdf" && echo "  $OUT/$NAME.pdf"
else
  echo "  cadcraft-cli no está en PATH (ver README)"
fi

if [[ $CHECK -ne 0 ]]; then
  echo
  echo "BLOQUEADO: el plano tiene errores. Corregí el spec y volvé a correr."
  exit 1
fi
echo
echo "LISTO: $OUT/$NAME.dxf (y derivados si cadcraft-cli está disponible)"
