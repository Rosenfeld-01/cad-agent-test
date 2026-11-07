#!/usr/bin/env bash
# test_gates.sh — autotest de los gates de QA.
#
# Genera un DXF con defectos a propósito (tests/_roto.dxf) y comprueba que
# qa_laminas.py y qa_geometria.py lo detecten. Un gate que NO falla está roto
# (ver docs/DEFECTOS_CONOCIDOS.md §6.1). Este script tiene que salir con 0.
set -uo pipefail
cd "$(dirname "$0")/.."

ROTO="tests/_roto.dxf"

echo "== generar fixture roto =="
python3 tests/mk_dxf_roto.py || { echo "no se generó el fixture"; exit 1; }

echo "== qa_laminas (debe detectar: exit 1) =="
python3 tools/qa_laminas.py "$ROTO"; L=$?

echo "== qa_geometria (debe detectar: exit 1) =="
python3 tools/qa_geometria.py "$ROTO"; G=$?

if [ "$L" -eq 1 ] && [ "$G" -eq 1 ]; then
  echo "PASS: los dos gates detectan los defectos del fixture."
  rm -f "$ROTO"
  exit 0
fi
echo "FAIL: algún gate devolvió 0 (gate roto). qa_laminas=$L qa_geometria=$G"
exit 1
