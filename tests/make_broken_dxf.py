#!/usr/bin/env python3
"""Gate fixture: an A2 sheet with deliberate defects.

    python3 tests/make_broken_dxf.py
    python3 tools/qa_sheets.py   tests/_broken.dxf   # 1 overlap + 1 outside
    python3 tools/qa_geometry.py tests/_broken.dxf   # 1 coincident + 1 block

Both must exit with code 1. If they return 0, the gate is broken
(see PLAYBOOK §8.1).
"""
import sys
from pathlib import Path

import ezdxf

DESTINATION = Path(__file__).with_name("_broken.dxf")


def main() -> int:
    doc = ezdxf.new()
    doc.units = 6                                # meters
    msp = doc.modelspace()

    # 1) two texts at the same point -> text overlap
    msp.add_text("HELLO WORLD", dxfattribs={"height": 0.003, "insert": (0.10, 0.10)})
    msp.add_text("OVERLAP", dxfattribs={"height": 0.003, "insert": (0.10, 0.10)})

    # 2) line outside the A2 sheet (0.594 x 0.420) -> out of sheet
    msp.add_line((0.0, 0.10), (0.80, 0.10))

    # 3) the same line drawn twice -> coincident stroke
    msp.add_line((0.10, 0.30), (0.20, 0.30))
    msp.add_line((0.10, 0.30), (0.20, 0.30))

    # 4) two overlapping blocks (not contained) -> overlapping blocks
    for name in ("BLOCK_A", "BLOCK_B"):
        blk = doc.blocks.new(name=name)
        blk.add_lwpolyline([(0, 0), (0.05, 0), (0.05, 0.05), (0, 0.05)])
    msp.add_blockref("BLOCK_A", (0.30, 0.30))
    msp.add_blockref("BLOCK_B", (0.32, 0.32))

    doc.saveas(DESTINATION)
    print(f"wrote {DESTINATION}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
