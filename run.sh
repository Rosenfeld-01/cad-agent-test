#!/usr/bin/env bash
# run.sh — full pipeline: spec -> validation -> DXF -> validation -> PNG/DWG
# Usage: ./run.sh [spec.json] [out_dir]
#   ./run.sh typologies/seeds/house_8.66x20.json
#   ./run.sh cases/<slug>/spec.json out/<slug>
set -uo pipefail
cd "$(dirname "$0")"

SPEC=${1:-typologies/seeds/house_8.66x20.json}
OUT=${2:-out}
NAME=$(basename "$SPEC" .json)
mkdir -p "$OUT"

echo "== 0/4 spec preflight =="
python3 tools/validate_spec.py "$SPEC" || exit 1

echo "== 1/4 generate =="
python3 plan.py "$SPEC" "$OUT/$NAME.dxf" || exit 1

echo "== 2/4 validate =="
CHECK=0
python3 check.py "$OUT/$NAME.dxf" "$SPEC" || CHECK=1

echo "== 3/4 render PNG =="
if command -v cadcraft-cli >/dev/null 2>&1; then
  cadcraft-cli convert "$OUT/$NAME.dxf" "$OUT/$NAME.png" && echo "  $OUT/$NAME.png"
  echo "== 4/4 DWG + PDF =="
  cadcraft-cli convert "$OUT/$NAME.dxf" "$OUT/$NAME.dwg" && echo "  $OUT/$NAME.dwg"
  cadcraft-cli convert "$OUT/$NAME.dxf" "$OUT/$NAME.pdf" && echo "  $OUT/$NAME.pdf"
else
  echo "  cadcraft-cli is not in PATH (see README)"
fi

if [[ $CHECK -ne 0 ]]; then
  echo
  echo "BLOCKED: the plan has errors. Fix the spec and run again."
  exit 1
fi
echo
echo "DONE: $OUT/$NAME.dxf (and derived files when cadcraft-cli is available)"
