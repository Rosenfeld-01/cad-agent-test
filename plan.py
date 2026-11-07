#!/usr/bin/env python3
"""
plan.py — parametric housing floor-plan generator (DXF) for CADCraft.

Reads a JSON spec (design intent) and emits a DXF with:
  - walls as closed polylines (A-WALL), with real openings (gaps)
  - doors with leaf + swing arc (A-DOOR)
  - windows with double lines (A-WIN)
  - rooms as closed polygons + name and area (A-AREA / A-ANNO)
  - overall dimensions (A-DIM)

Nothing is drawn by hand: everything comes from the spec. The agent edits the
spec, not the DXF.

Usage:
    python3 plan.py typologies/seeds/house_8.66x20.json out/plan.dxf
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import ezdxf
from ezdxf.enums import TextEntityAlignment

APPID = "CADAGENT"

LAYERS = {
    "A-WALL": 7,      # walls
    "A-DOOR": 3,      # doors
    "A-WIN": 4,       # windows
    "A-AREA": 8,      # room polygons
    "A-ANNO": 2,      # text / names
    "A-DIM": 1,       # dimensions
    "A-AXIS": 6,      # axes
}


def _vec(x):
    return ezdxf.math.Vec2(x[0], x[1])


def _wall_solids(p1, p2, t, openings):
    """Return the solid wall spans (rectangles) and support data."""
    p1, p2 = _vec(p1), _vec(p2)
    delta = p2 - p1
    length = delta.magnitude
    if length < 1e-9:
        raise ValueError("zero-length wall")
    u = delta.normalize()
    n = ezdxf.math.Vec2((-u.y, u.x))

    ops = sorted(openings, key=lambda o: o["s"])
    cuts = []
    for o in ops:
        a = o["s"] - o["width"] / 2.0
        b = o["s"] + o["width"] / 2.0
        if a < -1e-6 or b > length + 1e-6:
            raise ValueError(
                f"opening outside wall (s={o['s']}, width={o['width']}, L={length:.2f})"
            )
        cuts.append((max(a, 0.0), min(b, length), o))

    intervals, cur = [], 0.0
    for a, b, _o in cuts:
        if a > cur + 1e-6:
            intervals.append((cur, a))
        cur = max(cur, b)
    if cur < length - 1e-6:
        intervals.append((cur, length))

    solids = []
    for a, b in intervals:
        pa, pb = p1 + u * a, p1 + u * b
        solids.append([pa + n * (t / 2), pb + n * (t / 2),
                       pb - n * (t / 2), pa - n * (t / 2)])
    return solids, u, n, length, cuts


def _point_in_convex(px, py, poly, eps=1e-9):
    """True if (px,py) is inside a convex polygon (or on its edge)."""
    n = len(poly)
    sign = 0
    for i in range(n):
        ax, ay = poly[i]
        bx, by = poly[(i + 1) % n]
        cr = (bx - ax) * (py - ay) - (by - ay) * (px - ax)
        if cr > eps:
            s = 1
        elif cr < -eps:
            s = -1
        else:
            continue
        if sign == 0:
            sign = s
        elif s != sign:
            return False
    return True


def _union_segments(solids, eps=1e-3):
    """Atomic edges on the boundary of the union of solids (convex polygons).

    Returns directed segments (interior on the left): CCW outline of the bodies
    and CW outline of the holes. Each edge is split at crossings and vertex
    projections; interior pieces are discarded and orientation is decided by
    sampling both sides.
    """
    edges = []
    pts = []
    for poly in solids:
        n = len(poly)
        for i in range(n):
            a = (poly[i][0], poly[i][1])
            b = (poly[(i + 1) % n][0], poly[(i + 1) % n][1])
            edges.append((a, b))
            pts.append(a)

    # 1) cut parameters per edge (ends + intersections + vertices)
    cuts = [[0.0, 1.0] for _ in edges]
    for i, (a, b) in enumerate(edges):
        dx, dy = b[0] - a[0], b[1] - a[1]
        L2 = dx * dx + dy * dy
        if L2 < 1e-18:
            continue
        for (px, py) in pts:                       # vertex projections
            t = ((px - a[0]) * dx + (py - a[1]) * dy) / L2
            if 1e-9 < t < 1 - 1e-9:
                qx, qy = a[0] + dx * t, a[1] + dy * t
                if abs(qx - px) < 1e-7 and abs(qy - py) < 1e-7:
                    cuts[i].append(t)
        for j, (c, d) in enumerate(edges):         # crossings with other edges
            if j == i:
                continue
            ex, ey = d[0] - c[0], d[1] - c[1]
            den = dx * ey - dy * ex
            if abs(den) < 1e-15:
                continue
            t = ((c[0] - a[0]) * ey - (c[1] - a[1]) * ex) / den
            u = ((c[0] - a[0]) * dy - (c[1] - a[1]) * dx) / den
            if 1e-9 < t < 1 - 1e-9 and -1e-9 < u < 1 + 1e-9:
                cuts[i].append(t)

    # 2) unique subsegments (without duplicating coincident edges)
    uniq = {}
    for i, (a, b) in enumerate(edges):
        dx, dy = b[0] - a[0], b[1] - a[1]
        ts = sorted(set(round(t, 9) for t in cuts[i]))
        for t0, t1 in zip(ts, ts[1:]):
            if t1 - t0 < 1e-9:
                continue
            p0 = (round(a[0] + dx * t0, 6), round(a[1] + dy * t0, 6))
            p1 = (round(a[0] + dx * t1, 6), round(a[1] + dy * t1, 6))
            k = tuple(sorted((p0, p1)))
            if p0 != p1:
                uniq[k] = (p0, p1)

    # 3) oriented boundary (interior on the left)
    directed = []
    for p0, p1 in uniq.values():
        mx, my = (p0[0] + p1[0]) / 2.0, (p0[1] + p1[1]) / 2.0
        dx, dy = p1[0] - p0[0], p1[1] - p0[1]
        L = math.hypot(dx, dy)
        if L < 1e-12:
            continue
        nx, ny = -dy / L, dx / L
        left = any(_point_in_convex(mx + nx * eps, my + ny * eps, s) for s in solids)
        right = any(_point_in_convex(mx - nx * eps, my - ny * eps, s) for s in solids)
        if left and not right:
            directed.append((p0, p1))
        elif right and not left:
            directed.append((p1, p0))
    return directed


def _chain_loops(directed):
    """Join directed segments (interior on the left) into closed loops."""
    if not directed:
        return []
    outgoing = {}
    for a, b in directed:
        outgoing.setdefault(a, []).append(b)

    def angle(a, b):
        return math.degrees(math.atan2(b[1] - a[1], b[0] - a[0])) % 360.0

    used = set()
    loops = []
    for start in list(outgoing):
        for nxt in outgoing[start]:
            if (start, nxt) in used:
                continue
            loop = [start]
            prev, cur = start, nxt
            used.add((prev, cur))
            while cur != start:
                loop.append(cur)
                candidates = [b for b in outgoing.get(cur, []) if (cur, b) not in used]
                if not candidates:
                    break
                incoming_angle = angle(prev, cur)
                # tightest left turn = smallest clockwise rotation of the reverse
                def key(b):
                    return (incoming_angle + 180.0 - angle(cur, b)) % 360.0
                nxt2 = min(candidates, key=key)
                used.add((cur, nxt2))
                prev, cur = cur, nxt2
            if len(loop) >= 3 and cur == start:
                loops.append(loop)
    return loops


def wall_outline(walls, ext=0.20):
    """Union outline of a set of walls as closed loops in project coordinates.

    Replaces one rectangle per wall (which overlapped at corners and crossings)
    with the real boundary of the union. Returns a list of loops [(x,y)...].
    """
    solids = []
    for w in walls:
        p1, p2 = _vec(w["p1"]), _vec(w["p2"])
        t = float(w.get("thickness", ext))
        s, _u, _n, _L, _cuts = _wall_solids(p1, p2, t, w.get("openings", []))
        for pts in s:
            solids.append([(p.x, p.y) for p in pts])
    return _chain_loops(_union_segments(solids))


def _draw_opening(msp, p1, u, n, t, a, b, kind):
    """Opening symbol in the gap [a, b]."""
    pa, pb = p1 + u * a, p1 + u * b
    if kind == "door":
        hinge = pa + n * (t / 2)
        leaf_end = hinge + n * (b - a)
        msp.add_line(hinge, leaf_end, dxfattribs={"layer": "A-DOOR"})
        ang_u = math.degrees(math.atan2(u.y, u.x))
        ang_n = math.degrees(math.atan2(n.y, n.x))
        # 90-degree arc from the leaf to the wall
        msp.add_arc(
            center=hinge, radius=(b - a),
            start_angle=min(ang_u, ang_n), end_angle=max(ang_u, ang_n),
            dxfattribs={"layer": "A-DOOR"},
        )
    elif kind == "window":
        off = t / 6.0
        for s in (off, -off):
            msp.add_line(pa + n * s, pb + n * s, dxfattribs={"layer": "A-WIN"})
    elif kind == "opening":
        pass
    else:
        raise ValueError(f"unknown opening type: {kind}")


def build(spec: dict, out: Path) -> Path:
    doc = ezdxf.new("R2010", setup=True)
    doc.units = ezdxf.units.M
    doc.header["$INSUNITS"] = 6
    doc.appids.add(APPID)

    for name, color in LAYERS.items():
        if name not in doc.layers:
            doc.layers.add(name, color=color)

    msp = doc.modelspace()
    walls_data = spec["walls"]
    if isinstance(walls_data, dict):
        ext = walls_data.get("exterior", 0.20)
        walls = walls_data["segments"]
    else:
        ext = 0.20
        walls = walls_data

    # One union outline per region: avoids overlapping walls at corners/crossings.
    for loop in wall_outline(walls, ext):
        msp.add_lwpolyline([(x, y) for x, y in loop], close=True,
                           dxfattribs={"layer": "A-WALL"})
    for w in walls:
        p1, p2 = _vec(w["p1"]), _vec(w["p2"])
        t = float(w.get("thickness", ext))
        _solids, u, n, _length, cuts = _wall_solids(p1, p2, t, w.get("openings", []))
        for a, b, o in cuts:
            _draw_opening(msp, p1, u, n, t, a, b, o.get("type", "opening"))

    # Rooms: polygon + label
    for room in spec.get("rooms", []):
        x, y = float(room["x"]), float(room["y"])
        w, h = float(room["w"]), float(room["h"])
        pts = [(x, y), (x + w, y), (x + w, y + h), (x, y + h)]
        pl = msp.add_lwpolyline(pts, close=True, dxfattribs={"layer": "A-AREA"})
        pl.set_xdata(APPID, [(1000, room["name"])])
        area = w * h
        cx, cy = x + w / 2, y + h / 2
        name = msp.add_text(room["name"], height=0.20,
                            dxfattribs={"layer": "A-ANNO"})
        name.set_placement((cx, cy + 0.20), align=TextEntityAlignment.MIDDLE_CENTER)
        val = msp.add_text(f"{area:.1f} m2", height=0.16,
                           dxfattribs={"layer": "A-ANNO"})
        val.set_placement((cx, cy - 0.15), align=TextEntityAlignment.MIDDLE_CENTER)

    # Overall dimensions
    xs = [p[0] for w in walls for p in (w["p1"], w["p2"])]
    ys = [p[1] for w in walls for p in (w["p1"], w["p2"])]
    x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)
    msp.add_linear_dim(base=((x0 + x1) / 2, y0 - 1.0), p1=(x0, y0), p2=(x1, y0),
                       angle=0, dimstyle="EZDXF",
                       override={"dimtxt": 0.18}).render()
    msp.add_linear_dim(base=(x1 + 1.0, (y0 + y1) / 2), p1=(x1, y0), p2=(x1, y1),
                       angle=90, dimstyle="EZDXF",
                       override={"dimtxt": 0.18}).render()

    out.parent.mkdir(parents=True, exist_ok=True)
    doc.saveas(out)
    return out


def main() -> int:
    if len(sys.argv) != 3:
        print("usage: python3 plan.py SPEC.json OUT.dxf", file=sys.stderr)
        return 2
    spec = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    out = build(spec, Path(sys.argv[2]))
    print(f"OK  {out}  ({out.stat().st_size} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
