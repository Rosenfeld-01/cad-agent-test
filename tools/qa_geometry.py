#!/usr/bin/env python3
"""Geometry gate: coincident lines and overlapping blocks.

    python3 tools/qa_geometry.py out/L01.dxf
    python3 tools/qa_geometry.py --all out
    python3 tools/qa_geometry.py --all out --verbose --json out/_geo.json

Detects three things that `qa_sheets.py` does not check:

1. **Coincident lines**: two LINE entities on the same layer, collinear and
   overlapping by more than `TOL` paper meters ("the same pipe/stroke was drawn
   twice").
2. **Overlapping blocks**: INSERT boxes that overlap by more than `FRAC` (5%) of
   the smaller area. On a plan, one fixture invades another.
3. **Circulation**: blocks that overlap a door swing (A-DOOR layer).

Exit code 1 if there is any finding (usable as a gate).
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import ezdxf
from ezdxf import bbox as ezbbox

TOL = 0.001          # 1 mm of paper: below this it is the same stroke
FRAC = 0.05          # 5% of the smaller block area


def _sheet_scale(doc) -> float:
    """Real sheet scale factor (1 = paper, 50 = 1:1 real).

    Real-scale plans are ``scale`` times larger than A2 paper, so tolerances stay
    in paper meters (1 mm stroke) without changing the criterion.
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


def _bbox(e):
    try:
        bb = ezbbox.extents([e])
    except Exception:                                   # noqa: BLE001
        return None
    if not bb.has_data:
        return None
    return (bb.extmin.x, bb.extmin.y, bb.extmax.x, bb.extmax.y)


def _segment(e):
    """Normalized segment (x0, y0, x1, y1)."""
    s, t = e.dxf.start, e.dxf.end
    p, q = (s.x, s.y), (t.x, t.y)
    return (p[0], p[1], q[0], q[1]) if (p[0], p[1]) <= (q[0], q[1]) else \
           (q[0], q[1], p[0], p[1])


def coincident(msp, tol: float = TOL):
    """Collinear lines on the same layer that overlap by more than ``tol``."""
    groups = {}
    for e in msp.query("LINE"):
        x0, y0, x1, y1 = _segment(e)
        dx, dy = x1 - x0, y1 - y0
        length = math.hypot(dx, dy)
        if length < tol:
            continue
        ang = round(math.degrees(math.atan2(dy, dx)) % 180.0, 2)
        d = abs(-dy * x0 + dx * y0) / length        # distance to origin
        groups.setdefault((e.dxf.layer, ang, round(d, 4)), []).append(
            (x0, y0, x1, y1, e))

    findings = []
    for (_layer, _ang, _d), items in groups.items():
        if len(items) < 2:
            continue
        x0, y0, x1, y1, _e = items[0]
        ux, uy = x1 - x0, y1 - y0
        n = math.hypot(ux, uy)
        ux, uy = ux / n, uy / n
        projections = []
        for it in items:
            a, b = it[0] * ux + it[1] * uy, it[2] * ux + it[3] * uy
            projections.append((min(a, b), max(a, b), it))
        projections.sort(key=lambda z: (z[0], z[1]))
        for i in range(len(projections) - 1):
            a0, a1, it0 = projections[i]
            b0, b1, it1 = projections[i + 1]
            overlap = min(a1, b1) - max(a0, b0)
            if overlap > tol:
                findings.append((
                    round(overlap, 4),
                    tuple(round(v, 3) for v in it0[:4]),
                    tuple(round(v, 3) for v in it1[:4]),
                    it0[4].dxf.layer))

    return findings


def _area(c):
    return max(0.0, c[2] - c[0]) * max(0.0, c[3] - c[1])


def _inter(a, b):
    return (max(a[0], b[0]), max(a[1], b[1]), min(a[2], b[2]), min(a[3], b[3]))


def _inside(a, b, tol=0.003):
    """True if box `a` is contained in `b` (a fixture on a countertop).

    3 mm of paper is tolerated: the real block bbox may slightly exceed the
    nominal box used to insert it (edge lines, shadows).
    """
    return (b[0] - tol <= a[0] and b[1] - tol <= a[1]
            and a[2] <= b[2] + tol and a[3] <= b[3] + tol)


def blocks(msp, contain_tol: float = 0.003):
    """Pairs of INSERTs whose boxes overlap by more than FRAC of the smaller area.

    Containment (a fixture inside a countertop, a meter inside a niche) is not
    reported: it is a valid design relationship.
    """
    items = []
    for e in msp.query("INSERT"):
        c = _bbox(e)
        if c is None:
            continue
        items.append((c, e.dxf.name,
                      (round(e.dxf.insert.x, 3), round(e.dxf.insert.y, 3))))
    items.sort(key=lambda z: z[0][0])
    findings = []
    for i, (ca, na, pa) in enumerate(items):
        for cb, nb, pb in items[i + 1:]:
            if cb[0] >= ca[2]:
                break
            ai = _area(_inter(ca, cb))
            if ai <= 0:
                continue
            frac = ai / max(1e-12, min(_area(ca), _area(cb)))
            if frac <= FRAC:
                continue
            if _inside(ca, cb, contain_tol) or _inside(cb, ca, contain_tol):
                continue
            findings.append((round(frac, 3), na, pa, nb, pb))
    return findings


def circulation(msp):
    """Blocks that overlap a door swing (A-DOOR layer)."""
    doors = []
    for e in msp.query("ARC"):
        if e.dxf.layer != "A-DOOR":
            continue
        c = _bbox(e)
        if c:
            doors.append(c)
    findings = []
    for e in msp.query("INSERT"):
        c = _bbox(e)
        if c is None:
            continue
        for door in doors:
            ai = _area(_inter(c, door))
            if ai <= 0:
                continue
            frac = ai / max(1e-12, _area(door))
            if frac > 0.25:
                findings.append((round(frac, 3), e.dxf.name,
                                 (round(e.dxf.insert.x, 3),
                                  round(e.dxf.insert.y, 3))))
                break
    return findings


def analyze(path: Path) -> dict:
    doc = ezdxf.readfile(path)
    msp = doc.modelspace()
    k = _sheet_scale(doc)
    return {
        "sheet": path.name,
        "entities": len(msp),
        "coincident": sorted(coincident(msp, TOL * k), key=lambda z: -z[0]),
        "blocks": sorted(blocks(msp, 0.003 * k), key=lambda z: -z[0]),
        "circulation": sorted(circulation(msp), key=lambda z: -z[0]),
    }


def main(argv) -> int:
    verbose = "--verbose" in argv or "-v" in argv
    json_path = None
    if "--json" in argv:
        i = argv.index("--json")
        if i + 1 < len(argv):
            json_path = Path(argv[i + 1])
            argv = [a for j, a in enumerate(argv) if j != i + 1]

    if "--all" in argv:
        i = argv.index("--all")
        base = Path(argv[i + 1]) if i + 1 < len(argv) else Path("out")
        if not base.is_dir():
            base = Path("out")
        paths = sorted(base.glob("L*.dxf"))
    else:
        paths = [Path(a) for a in argv[1:] if a.lower().endswith(".dxf")]
    if not paths:
        print("usage: qa_geometry.py [--all DIR] [--verbose] [--json PATH] *.[dxf]")
        return 2

    reports, failures = [], 0
    for path in paths:
        try:
            r = analyze(path)
        except Exception as exc:                        # noqa: BLE001
            print(f"{path.name}: ERROR {type(exc).__name__}: {exc}")
            failures += 1
            continue
        reports.append(r)
        nc = len(r["coincident"])
        nb = len(r["blocks"])
        nci = len(r["circulation"])
        status = "OK" if nc + nb + nci == 0 else "REVIEW"
        print(f"{path.name:10s} ent={r['entities']:5d}  coincident={nc:3d}"
              f"  blocks={nb:3d}  circulation={nci:3d}  {status}")
        if verbose:
            for overlap, a, b, layer in r["coincident"][:40]:
                print(f"    coinc {layer:8s} {overlap:7.4f} m  {a} vs {b}")
            for frac, na, pa, nb_, pb in r["blocks"][:40]:
                print(f"    blk  {na}@{pa} overlaps {nb_}@{pb}  ({frac:.0%})")
            for frac, na, pa in r["circulation"][:40]:
                print(f"    circ {na}@{pa} invades door swing ({frac:.0%})")
        if nc + nb + nci:
            failures += 1

    if json_path:
        json_path.write_text(json.dumps(reports, indent=1, ensure_ascii=False),
                             encoding="utf-8")
        print(f"\nreport: {json_path}")
    print(f"\n{len(reports) - failures}/{len(reports)} clean sheets")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
