#!/usr/bin/env python3
"""
check.py — deterministic plan validator.

This is the agent's "error conscience": it is NOT the LLM. It is code that
checks the DXF against the spec and against the rules in `caba_rules.json`.

It calculates lighting and ventilation for each room from the REAL GEOMETRY of
the windows in the spec (it does not trust a hand-declared number).

Output: readable report + report.json. Exit code 1 if there are errors.

Usage:
    python3 check.py out/plan.dxf typologies/seeds/house_8.66x20.json [caba_rules.json]
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import ezdxf

APPID = "CADAGENT"
TOL = 0.02


def _shoelace(pts):
    s = 0.0
    for (x1, y1), (x2, y2) in zip(pts, pts[1:] + pts[:1]):
        s += x1 * y2 - x2 * y1
    return abs(s) / 2.0


def _rect(room):
    x, y = float(room["x"]), float(room["y"])
    return x, y, x + float(room["w"]), y + float(room["h"])


def _point_in(px, py, rect, margin):
    x0, y0, x1, y1 = rect
    return (x0 - margin) <= px <= (x1 + margin) and (y0 - margin) <= py <= (y1 + margin)


def _window_area_by_room(spec, warnings):
    """Sum window area per room by placing each window midpoint in the nearest
    room rectangle."""
    rooms = spec.get("rooms", [])
    areas = {room["name"]: 0.0 for room in rooms}
    for w in spec["walls"]:
        p1, p2 = w["p1"], w["p2"]
        dx, dy = p2[0] - p1[0], p2[1] - p1[1]
        length = math.hypot(dx, dy)
        if length < 1e-9:
            continue
        ux, uy = dx / length, dy / length
        for o in w.get("openings", []):
            if o.get("type") != "window":
                continue
            s = float(o["s"])
            px, py = p1[0] + ux * s, p1[1] + uy * s
            candidates = [r for r in rooms if _point_in(px, py, _rect(r), 0.30)]
            if not candidates:
                warnings.append({
                    "code": "WINDOW_ORPHAN",
                    "msg": f"window {o.get('id', '?')} does not fall in any room",
                })
                continue
            candidates.sort(key=lambda r: float(r["w"]) * float(r["h"]))
            room = candidates[0]
            areas[room["name"]] += float(o["width"]) * float(o.get("height", 1.4))
    return areas


def check(dxf_path: Path, spec: dict, rules: dict) -> dict:
    doc = ezdxf.readfile(dxf_path)
    msp = doc.modelspace()
    errors, warnings = [], []

    def err(code, msg, **kw):
        errors.append({"code": code, "msg": msg, **kw})

    def warn(code, msg, **kw):
        warnings.append({"code": code, "msg": msg, **kw})

    # --- required layers ---
    for name in ["A-WALL", "A-DOOR", "A-WIN", "A-AREA", "A-ANNO"]:
        if name not in doc.layers:
            err("LAYER_MISSING", f"missing layer {name}", layer=name)

    # --- closed polylines ---
    polylines = list(msp.query("LWPOLYLINE"))
    if not polylines:
        err("NO_WALLS", "the plan has no polylines (walls?)")
    for pl in polylines:
        if not pl.closed:
            err("POLYLINE_OPEN", f"open polyline on layer {pl.dxf.layer}",
                layer=pl.dxf.layer, handle=pl.dxf.handle)

    # --- rooms: DXF vs spec ---
    dxf_rooms = {}
    for pl in polylines:
        if pl.dxf.layer != "A-AREA":
            continue
        name = None
        try:
            for tag in pl.get_xdata(APPID):
                if tag.code == 1000:
                    name = str(tag.value)
        except Exception:
            pass
        pts = [(p[0], p[1]) for p in pl.get_points("xy")]
        if name is None:
            warn("ROOM_UNNAMED", "room polygon without a name in XDATA")
            continue
        dxf_rooms[name] = _shoelace(pts)

    win_area = _window_area_by_room(spec, warnings)
    room_rules = rules["rooms"]
    no_ventilation = set(rules.get("no_ventilation", []))

    for room in spec.get("rooms", []):
        name, kind = room["name"], room["type"]
        w, h = float(room["w"]), float(room["h"])
        area_spec = w * h
        side_min = min(w, h)

        if name not in dxf_rooms:
            err("ROOM_MISSING", f"room {name} is not in the DXF", room=name)
            continue
        if abs(dxf_rooms[name] - area_spec) > TOL:
            err("AREA_MISMATCH",
                f"{name}: DXF {dxf_rooms[name]:.2f} m2 vs spec {area_spec:.2f} m2",
                room=name)

        r = room_rules.get(kind)
        if r is None:
            warn("ROOM_KIND_UNKNOWN", f"{name}: type '{kind}' has no rule", room=name)
            continue
        if area_spec + 1e-9 < r["min_area"]:
            err("ROOM_TOO_SMALL",
                f"{name}: {area_spec:.2f} m2 < minimum {r['min_area']} m2",
                room=name)
        if side_min + 1e-9 < r["min_side"]:
            err("ROOM_SIDE_TOO_SMALL",
                f"{name}: side {side_min:.2f} m < minimum {r['min_side']} m",
                room=name)

        # lighting and ventilation calculated from geometry
        if kind not in no_ventilation:
            wa = win_area.get(name, 0.0)
            need_i = area_spec * rules["lighting"]["factor"]
            need_v = area_spec * rules["ventilation"]["factor"]
            if wa + 1e-9 < need_i:
                err("LIGHTING",
                    f"{name}: windows {wa:.2f} m2 < lighting {need_i:.2f} m2 "
                    f"(20% of {area_spec:.2f})", room=name)
            if wa + 1e-9 < need_v:
                err("VENTILATION",
                    f"{name}: windows {wa:.2f} m2 < ventilation {need_v:.2f} m2 "
                    f"(5% of {area_spec:.2f})", room=name)
            declared = room.get("ventilation_m2")
            if declared is not None and abs(float(declared) - wa) > TOL:
                warn("VENT_DECLARED_MISMATCH",
                    f"{name}: declared {float(declared):.2f} m2 vs geometry {wa:.2f} m2",
                    room=name)

    # --- room overlap ---
    rooms = spec.get("rooms", [])
    for i, a in enumerate(rooms):
        ax0, ay0, ax1, ay1 = _rect(a)
        for b in rooms[i + 1:]:
            bx0, by0, bx1, by1 = _rect(b)
            ox = min(ax1, bx1) - max(ax0, bx0)
            oy = min(ay1, by1) - max(ay0, by0)
            if ox > TOL and oy > TOL:
                err("ROOM_OVERLAP",
                    f"{a['name']} and {b['name']} overlap {ox:.2f}x{oy:.2f} m",
                    rooms=[a["name"], b["name"]])

    # --- walls: thickness and openings ---
    for w in spec["walls"]:
        t = float(w.get("thickness", 0.0))
        wall_type = w.get("type", "interior")
        key = "exterior_min" if wall_type == "exterior" else "interior_min"
        if t + 1e-9 < rules["walls"][key]:
            err("WALL_THIN",
                f"wall {w.get('id', '?')}: {t:.2f} m < minimum {rules['walls'][key]} m ({wall_type})")
        L = math.hypot(w["p2"][0] - w["p1"][0], w["p2"][1] - w["p1"][1])
        for o in w.get("openings", []):
            a = float(o["s"]) - float(o["width"]) / 2
            b = float(o["s"]) + float(o["width"]) / 2
            if a < -1e-6 or b > L + 1e-6:
                err("OPENING_OUT_OF_WALL",
                    f"opening {o.get('id', '?')} outside wall {w.get('id', '?')}")
            if o.get("type") == "door":
                kind = o.get("use", "interior")
                need = rules["doors"].get(kind, rules["doors"]["interior"])
                if float(o["width"]) + 1e-9 < need:
                    err("DOOR_NARROW",
                        f"door {o.get('id', '?')}: {o['width']:.2f} m < minimum {need} m ({kind})")

    # --- clear height ---
    alt = float(spec.get("clear_height", 0.0))
    if alt + 1e-9 < rules["min_clear_height"]:
        err("CEILING_LOW",
            f"clear height {alt:.2f} m < minimum {rules['min_clear_height']} m")

    # --- text height ---
    hmin = rules["text"]["min_height"]
    for t in msp.query("TEXT MTEXT"):
        h = getattr(t.dxf, "height", None) or getattr(t.dxf, "char_height", None)
        if h is not None and h + 1e-9 < hmin:
            warn("TEXT_SMALL", f"text height {h:.2f} m < {hmin} m",
                 handle=t.dxf.handle)

    stats = {
        "polylines": len(polylines),
        "rooms_dxf": len(dxf_rooms),
        "rooms_spec": len(rooms),
        "doors": sum(1 for w in spec["walls"] for o in w.get("openings", [])
                     if o.get("type") == "door"),
        "windows": sum(1 for w in spec["walls"] for o in w.get("openings", [])
                       if o.get("type") == "window"),
        "window_m2": round(sum(win_area.values()), 2),
        "total_area_m2": round(sum(
            float(a["w"]) * float(a["h"]) for a in rooms), 2),
    }

    return {
        "ok": not errors,
        "errors": errors,
        "warnings": warnings,
        "stats": stats,
        "rules_source": rules.get("source", ""),
    }


def main() -> int:
    if len(sys.argv) < 3:
        print("usage: python3 check.py OUT.dxf SPEC.json [RULES.json]", file=sys.stderr)
        return 2
    dxf = Path(sys.argv[1])
    spec = json.loads(Path(sys.argv[2]).read_text(encoding="utf-8"))
    rules_path = Path(sys.argv[3]) if len(sys.argv) > 3 else Path(__file__).with_name("caba_rules.json")
    rules = json.loads(rules_path.read_text(encoding="utf-8"))

    rep = check(dxf, spec, rules)
    out = dxf.with_suffix(".report.json")
    out.write_text(json.dumps(rep, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"\n{'='*64}\nVALIDATION: {dxf.name}\n{'='*64}")
    for e in rep["errors"]:
        print(f"  ERROR  [{e['code']}] {e['msg']}")
    for w in rep["warnings"]:
        print(f"  warning [{w['code']}] {w['msg']}")
    s = rep["stats"]
    print(f"\n  rooms: {s['rooms_dxf']}/{s['rooms_spec']}  "
          f"doors: {s['doors']}  windows: {s['windows']} ({s['window_m2']} m2)  "
          f"area: {s['total_area_m2']} m2")
    print(f"  rules: {rep['rules_source']}")
    status = "OK" if rep["ok"] else f"{len(rep['errors'])} ERROR(S)"
    print(f"  result: {status}")
    print(f"  report: {out}\n")
    return 0 if rep["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
