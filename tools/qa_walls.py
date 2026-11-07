#!/usr/bin/env python3
"""qa_walls.py — wall-overlap gate (A-WALL).

    python3 tools/qa_walls.py out/L01.dxf out/L02.dxf
    python3 tools/qa_walls.py --all out
    python3 tools/qa_walls.py --all out --verbose --json out/_walls.json

Measures the overlap area between closed A-WALL polygons:

- If all are axis-aligned rectangles (the "one rectangle per wall" drawing), it
  computes the EXACT overlap: sum of areas minus the union area (rectangle
  sweep).
- If they are polygonal outlines (the boundary of the wall union), it estimates
  the overlap with a fine winding-number sample: a cell with winding >= 2 is
  covered twice.

Exit code 1 if any sheet exceeds TOL square paper meters.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

import ezdxf
from ezdxf import bbox as ezbbox

LAYER = "A-WALL"
TOL = 1e-5          # m2 of paper
STEP = 0.0006       # sample cell side (paper meters)


def _sheet_scale(doc) -> float:
    """Real sheet scale factor (1 = paper, 50 = 1:1 real).

    Real-scale plans are ``scale`` times larger than A2 paper; the cell and
    tolerance are scaled to keep the same physical resolution (~0.6 mm of paper)
    without oversampling.
    """
    ents = [e for e in doc.modelspace() if e.dxf.layer == "X-FRAME"]
    if ents:
        try:
            bb = ezbbox.extents(ents)
        except Exception:                            # noqa: BLE001
            bb = None
        if bb and bb.has_data and bb.extmax.x > bb.extmin.x:
            return max(1.0, round((bb.extmax.x - bb.extmin.x) / 0.594, 6))
    return 1.0


def _shoelace(pts):
    n = len(pts)
    s = 0.0
    for i in range(n):
        x0, y0 = pts[i]
        x1, y1 = pts[(i + 1) % n]
        s += x0 * y1 - x1 * y0
    return s / 2.0


def _polygons(msp):
    polys = []
    for pl in msp.query("LWPOLYLINE"):
        if pl.dxf.layer != LAYER or not pl.closed:
            continue
        pts = [(float(x), float(y)) for x, y in pl.get_points("xy")]
        if len(pts) >= 3:
            polys.append(pts)
    return polys


def _is_rect(poly, tol=1e-9):
    if len(poly) != 4:
        return None
    xs = sorted(set(round(p[0], 9) for p in poly))
    ys = sorted(set(round(p[1], 9) for p in poly))
    if len(xs) == 2 and len(ys) == 2:
        for x, y in poly:
            if not (abs(x - xs[0]) < tol or abs(x - xs[1]) < tol):
                return None
            if not (abs(y - ys[0]) < tol or abs(y - ys[1]) < tol):
                return None
        return (xs[0], ys[0], xs[1], ys[1])
    return None


def _union_area_rects(rects):
    """Exact union area of axis-aligned rectangles."""
    xs = sorted(set([r[0] for r in rects] + [r[2] for r in rects]))
    area = 0.0
    for x0, x1 in zip(xs, xs[1:]):
        if x1 - x0 < 1e-15:
            continue
        xm = (x0 + x1) / 2.0
        spans = sorted((r[1], r[3]) for r in rects if r[0] <= xm <= r[2])
        covered = 0.0
        cur_a = cur_b = None
        for a, b in spans:
            if cur_a is None:
                cur_a, cur_b = a, b
            elif a <= cur_b:
                cur_b = max(cur_b, b)
            else:
                covered += cur_b - cur_a
                cur_a, cur_b = a, b
        if cur_a is not None:
            covered += cur_b - cur_a
        area += (x1 - x0) * covered
    return area


def _winding(px, py, poly):
    w = 0
    n = len(poly)
    for i in range(n):
        x0, y0 = poly[i]
        x1, y1 = poly[(i + 1) % n]
        if y0 <= py:
            if y1 > py:
                if (x1 - x0) * (py - y0) - (px - x0) * (y1 - y0) > 0:
                    w += 1
        else:
            if y1 <= py:
                if (x1 - x0) * (py - y0) - (px - x0) * (y1 - y0) < 0:
                    w -= 1
    return w


def overlap(polys, step: float = STEP):
    """Overlap area (m2) between A-WALL polygons."""
    if len(polys) < 2:
        return 0.0
    rects = [_is_rect(p) for p in polys]
    if all(r is not None for r in rects):
        total = sum(abs(_shoelace(p)) for p in polys)
        return max(0.0, total - _union_area_rects(rects))
    xs0 = min(min(p[0] for p in q) for q in polys)
    xs1 = max(max(p[0] for p in q) for q in polys)
    ys0 = min(min(p[1] for p in q) for q in polys)
    ys1 = max(max(p[1] for p in q) for q in polys)
    # Adaptive step: no more than ~3M cells (avoids hanging if the DXF is in
    # project meters instead of paper meters).
    while ((xs1 - xs0) / step) * ((ys1 - ys0) / step) > 3_000_000:
        step *= 1.5
    nx = int((xs1 - xs0) / step) + 1
    ny = int((ys1 - ys0) / step) + 1
    area = 0.0
    for iy in range(ny):
        py = ys0 + (iy + 0.5) * step
        for ix in range(nx):
            px = xs0 + (ix + 0.5) * step
            w = 0
            for q in polys:
                w += _winding(px, py, q)
            if w >= 2:
                area += step * step
    return area


def analyze(path: Path) -> dict:
    doc = ezdxf.readfile(path)
    k = _sheet_scale(doc)
    polys = _polygons(doc.modelspace())
    return {"sheet": path.name, "polygons": len(polys), "k": k,
            "overlap_m2": round(overlap(polys, STEP * k), 7)}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Wall-overlap gate (A-WALL)")
    ap.add_argument("paths", nargs="*")
    ap.add_argument("--all", metavar="DIR")
    ap.add_argument("--json", metavar="OUTPUT")
    ap.add_argument("--verbose", "-v", action="store_true")
    args = ap.parse_args(argv)
    paths = [Path(r) for r in args.paths]
    if args.all:
        paths += sorted(Path(args.all).glob("L*.dxf"))
    if not paths:
        ap.error("provide files or --all DIR")

    reports, failures = [], 0
    for path in paths:
        try:
            rep = analyze(path)
        except Exception as exc:                        # noqa: BLE001
            print(f"{path.name}: ERROR {type(exc).__name__}: {exc}")
            failures += 1
            continue
        reports.append(rep)
        ok = rep["overlap_m2"] <= TOL * rep["k"] ** 2
        print(f"{path.name:9s} A-WALL={rep['polygons']:3d}  "
              f"overlap={rep['overlap_m2']:.2e} m2  {'OK' if ok else 'OVERLAP'}")
        if not ok:
            failures += 1
    if args.json:
        Path(args.json).write_text(
            json.dumps(reports, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"\nsummary: {args.json}")
    print(f"\n{len(reports) - failures}/{len(reports)} sheets without wall overlap")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
