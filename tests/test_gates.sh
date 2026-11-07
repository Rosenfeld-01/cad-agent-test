#!/usr/bin/env bash
# test_gates.sh — self-test for the QA gates.
#
# Builds a deliberately broken DXF (tests/_broken.dxf) and checks that
# qa_sheets.py and qa_geometry.py detect it. A gate that does NOT fail is
# broken (see PLAYBOOK §8.1). This script must exit 0.
set -uo pipefail
cd "$(dirname "$0")/.."

BROKEN="tests/_broken.dxf"

echo "== build broken fixture =="
python3 tests/make_broken_dxf.py || { echo "fixture was not created"; exit 1; }

echo "== qa_sheets (must detect: exit 1) =="
python3 tools/qa_sheets.py "$BROKEN"; S=$?

echo "== qa_geometry (must detect: exit 1) =="
python3 tools/qa_geometry.py "$BROKEN"; G=$?

if [ "$S" -eq 1 ] && [ "$G" -eq 1 ]; then
  echo "PASS: both gates detect the fixture defects."
  rm -f "$BROKEN"
  exit 0
fi
echo "FAIL: a gate returned 0 (broken gate). qa_sheets=$S qa_geometry=$G"
exit 1
