#!/usr/bin/env python3
"""qa_sheets.py — QA gate for the drawing-set sheets.

For each sheet DXF (A2 = 0.594 x 0.420 m of paper) it checks:

1. text overlaps (TEXT and MTEXT, with alignment and rotation)
2. entities outside the sheet (bounds outside 0..width / 0..height)
3. ezdxf audit (structural errors)

Usage:
    python3 tools/qa_sheets.py out/L01.dxf out/L02.dxf
    python3 tools/qa_sheets.py --all out
    python3 tools/qa_sheets.py --all out --json out/_qa.json --verbose

Output: one line per sheet, details for findings, and exit code 1 if any sheet
fails.

Criterion
---------
- Overlap is measured in paper meters: it counts when the intersection is wider
  than 0.4 mm and taller than 0.5 mm (less than that is typographic contact).
- Average character width: 0.62 x height.
- INSERTs are not checked for out-of-sheet bounds (their box depends on the
  block definition); symbols are small and always next to the plan.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import ezdxf
from ezdxf import bbox as ezbbox

WIDTH, HEIGHT = 0.594, 0.420           # A2 in paper meters
MIN_OVERLAP_X, MIN_OVERLAP_Y = 0.0004, 0.0005
CHAR_WIDTH = 0.62                      # average character width / height


def sheet_bbox(doc):
    """Frame box (X-FRAME layer) in drawing units.

    Real-scale sheets (1 unit = 1 m of the building) are drawn ``scale`` times
    larger than the A2 paper. The frame gives the real sheet size, so the gate
    still measures "outside the sheet" and tolerances in paper meters.
    """
    ents = [e for e in doc.modelspace() if e.dxf.layer == "X-FRAME"]
    if ents:
        try:
            bb = ezbbox.extents(ents)
        except Exception:                            # noqa: BLE001
            bb = None
        if bb and bb.has_data and bb.extmax.x > bb.extmin.x:
            return bb.extmin.x, bb.extmin.y, bb.extmax.x, bb.extmax.y
    return 0.0, 0.0, WIDTH, HEIGHT


def text_box(e):
    """Box (x0, y0, x1, y1) of a TEXT/MTEXT in paper meters."""
    if e.dxftype() == "TEXT":
        t = e.dxf.text or ""
        h = float(e.dxf.height or 0.0)
        al, va = e.dxf.halign, e.dxf.valign
        p = e.dxf.align_point if (al or va) else e.dxf.insert
        x, y = float(p.x), float(p.y)
        w = len(t) * h * CHAR_WIDTH
        rot = float(e.dxf.rotation or 0.0) % 360.0
        if 89.0 < rot < 91.0:            # vertical, upward
            return (x - h, y, x, y + w)
        if 269.0 < rot < 271.0:          # vertical, downward
            return (x, y - w, x + h, y)
        if 179.0 < rot < 181.0:          # upside down
            return (x - w, y - h, x, y)
        x0 = {0: x, 1: x - w / 2, 2: x - w}.get(al, x)
        y0 = {0: y - h * 0.26, 1: y, 2: y - h / 2, 3: y - h}.get(va, y - h * 0.26)
        return (x0, y0, x0 + w, y0 + h)

    # MTEXT
    rows = (e.plain_text() or "").splitlines() or [""]
    h = float(e.dxf.char_height or 0.0)
    p = e.dxf.insert
    x, y = float(p.x), float(p.y)
    w = max(len(row) for row in rows) * h * CHAR_WIDTH
    hh = h * (1.0 + 1.2 * (len(rows) - 1))
    ap = int(e.dxf.attachment_point or 1)
    row, col = divmod(ap - 1, 3)          # 0 top, 1 middle, 2 bottom
    y0 = {0: y - hh, 1: y - hh / 2, 2: y}[row]
    x0 = {0: x, 1: x - w / 2, 2: x - w}[col]
    return (x0, y0, x0 + w, y0 + hh)


def overlaps(texts, k: float = 1.0):
    out = []
    for i in range(len(texts)):
        ta, ca = texts[i]
        for j in range(i + 1, len(texts)):
            tb, cb = texts[j]
            ix = min(ca[2], cb[2]) - max(ca[0], cb[0])
            iy = min(ca[3], cb[3]) - max(ca[1], cb[1])
            if ix > MIN_OVERLAP_X * k and iy > MIN_OVERLAP_Y * k:
                out.append((ta[:30], [round(v, 3) for v in ca],
                            tb[:30], [round(v, 3) for v in cb],
                            round(ix, 4), round(iy, 4)))
    return out


def qa(path: Path) -> dict:
    doc = ezdxf.readfile(path)
    audit = doc.audit()
    msp = doc.modelspace()

    texts = []
    for e in msp:
        if e.dxftype() in ("TEXT", "MTEXT"):
            try:
                t = e.dxf.text if e.dxftype() == "TEXT" else e.plain_text()
                texts.append((t or "", text_box(e)))
            except Exception:                       # noqa: BLE001
                continue

    fx0, fy0, fx1, fy1 = sheet_bbox(doc)
    k = max(1.0, round((fx1 - fx0) / WIDTH, 6))
    tol = 1e-6 * k
    outside = []
    for e in msp:
        try:
            bb = ezbbox.extents([e])
        except Exception:                           # noqa: BLE001
            continue
        if not bb.has_data:
            continue
        x0, y0 = bb.extmin.x, bb.extmin.y
        x1, y1 = bb.extmax.x, bb.extmax.y
        if (x0 < fx0 - tol or y0 < fy0 - tol
                or x1 > fx1 + tol or y1 > fy1 + tol):
            outside.append((e.dxftype(), e.dxf.layer,
                            round(x0, 3), round(y0, 3), round(x1, 3), round(y1, 3)))

    rep = {
        "sheet": path.name,
        "entities": len(msp),
        "texts": len(texts),
        "out_of_sheet": outside,
        "text_overlaps": overlaps(texts, k),
        "audit_errors": len(audit.errors),
        "audit_fixes": len(audit.fixes),
    }
    rep["ok"] = (not outside and not rep["text_overlaps"]
                 and not rep["audit_errors"])
    return rep


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="QA DXF sheets (A2, meters)")
    ap.add_argument("paths", nargs="*", help="DXF files")
    ap.add_argument("--all", metavar="DIR", help="all L*.dxf in DIR")
    ap.add_argument("--json", metavar="OUTPUT", help="write the JSON summary")
    ap.add_argument("--verbose", "-v", action="store_true",
                    help="list all findings (default: 12)")
    args = ap.parse_args(argv)

    paths = [Path(r) for r in args.paths]
    if args.all:
        paths += sorted(Path(args.all).glob("L*.dxf"))
    if not paths:
        ap.error("provide files or --all DIR")

    reports, failures = [], 0
    for path in paths:
        try:
            rep = qa(path)
        except Exception as exc:                    # noqa: BLE001
            print(f"{path.name}: ERROR {type(exc).__name__}: {exc}")
            failures += 1
            continue
        reports.append(rep)
        print(f"{path.name:9s} ent={rep['entities']:4d} txt={rep['texts']:4d} "
              f"out={len(rep['out_of_sheet']):2d} "
              f"overlaps={len(rep['text_overlaps']):2d} "
              f"audit={rep['audit_errors']}/{rep['audit_fixes']}  "
              f"{'OK' if rep['ok'] else 'FAIL'}")
        if not rep["ok"]:
            failures += 1
            limit = None if args.verbose else 12
            for f in rep["out_of_sheet"][:limit]:
                print(f"    outside  {f}")
            for s in rep["text_overlaps"][:limit]:
                print(f"    overlap  {s}")

    if args.json:
        Path(args.json).write_text(json.dumps(reports, ensure_ascii=False,
                                              indent=1), encoding="utf-8")
        print(f"\nsummary: {args.json}")

    print(f"\n{len(reports) - failures}/{len(reports)} sheets OK")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
