#!/usr/bin/env python3
"""validate_spec.py — cheap spec preflight before generating the DXF.

It does two things:

1. Validates the JSON against `schemas/spec.schema.json` (structure and types).
2. Checks the geometry that `plan.py` and `check.py` will need: walls with
   length, openings inside the wall and not overlapping, rooms with area and
   minimum side, rooms without overlaps, and clear height.

It does not replace `check.py`: `check.py` measures the generated DXF (lighting,
ventilation, real areas). This script is the entry gate, so a malformed spec does
not waste a generation.

Usage:
    python3 tools/validate_spec.py typologies/seeds/house_8.66x20.json
    python3 tools/validate_spec.py cases/<slug>/spec.json --json
    python3 tools/validate_spec.py spec.json --rules caba_rules.json

Output: exit 0 if there are no errors; exit 1 if there is at least one error.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_RULES = ROOT / "caba_rules.json"
DEFAULT_SCHEMA = ROOT / "schemas" / "spec.schema.json"
TOL = 1e-6


class Finding:
    def __init__(self, level: str, code: str, msg: str, where: str = ""):
        self.level = level
        self.code = code
        self.msg = msg
        self.where = where

    def as_dict(self) -> dict:
        d = {"level": self.level, "code": self.code, "msg": self.msg}
        if self.where:
            d["where"] = self.where
        return d


def load_json(path: Path) -> dict:
    with path.open(encoding="utf-8") as fh:
        return json.load(fh)


def check_schema(spec: dict, schema_path: Path) -> list[Finding]:
    """Validate against the JSON Schema. If jsonschema is missing, do the minimum."""
    findings: list[Finding] = []
    try:
        from jsonschema import Draft202012Validator
    except ImportError:
        return _check_schema_fallback(spec)

    try:
        schema = load_json(schema_path)
        Draft202012Validator.check_schema(schema)
        validator = Draft202012Validator(schema)
    except Exception as exc:  # broken schema or unreadable file
        return [Finding("ERROR", "SCHEMA_BROKEN", f"could not load schema: {exc}")]

    for err in sorted(validator.iter_errors(spec), key=lambda e: list(e.path)):
        where = "/".join(str(p) for p in err.path) or "(root)"
        findings.append(Finding("ERROR", "SCHEMA", err.message, where))
    return findings


def _check_schema_fallback(spec: dict) -> list[Finding]:
    """Minimum check without dependencies, in case jsonschema is missing."""
    findings: list[Finding] = []
    required = ["unit", "clear_height", "walls", "rooms"]
    for key in required:
        if key not in spec:
            findings.append(Finding("ERROR", "SCHEMA", f"missing '{key}'", "(root)"))
    if spec.get("unit") != "m":
        findings.append(Finding("ERROR", "SCHEMA", "unit must be 'm'", "unit"))
    if not isinstance(spec.get("walls"), list):
        findings.append(Finding("ERROR", "SCHEMA", "walls must be a list", "walls"))
    if not isinstance(spec.get("rooms"), list):
        findings.append(Finding("ERROR", "SCHEMA", "rooms must be a list", "rooms"))
    for i, w in enumerate(spec.get("walls", [])):
        for key in ("p1", "p2", "thickness", "openings"):
            if key not in w:
                findings.append(Finding("ERROR", "SCHEMA", f"wall {i}: missing '{key}'", f"walls/{i}"))
    for i, room in enumerate(spec.get("rooms", [])):
        for key in ("name", "type", "x", "y", "w", "h"):
            if key not in room:
                findings.append(Finding("ERROR", "SCHEMA", f"room {i}: missing '{key}'", f"rooms/{i}"))
    return findings


def _rect(room: dict) -> tuple[float, float, float, float]:
    x, y = float(room["x"]), float(room["y"])
    return x, y, x + float(room["w"]), y + float(room["h"])


def check_geometry(spec: dict, rules: dict) -> list[Finding]:
    findings: list[Finding] = []
    room_rules = rules.get("rooms", {})
    no_ventilation = set(rules.get("no_ventilation", []))

    # --- clear height ---
    alt = float(spec.get("clear_height", 0.0))
    if alt + 1e-9 < float(rules.get("min_clear_height", 0.0)):
        findings.append(Finding(
            "ERROR", "CEILING_LOW",
            f"clear height {alt:.2f} m < minimum {rules['min_clear_height']} m",
            "clear_height"))

    # --- walls ---
    for i, w in enumerate(spec.get("walls", [])):
        wid = w.get("id", f"wall {i}")
        where = f"walls/{i}"
        try:
            x1, y1 = float(w["p1"][0]), float(w["p1"][1])
            x2, y2 = float(w["p2"][0]), float(w["p2"][1])
        except (KeyError, IndexError, TypeError, ValueError):
            findings.append(Finding("ERROR", "WALL_BAD_POINT", f"{wid}: invalid p1/p2", where))
            continue
        length = math.hypot(x2 - x1, y2 - y1)
        if length <= TOL:
            findings.append(Finding("ERROR", "WALL_ZERO", f"{wid}: zero length", where))
            continue

        wall_type = w.get("type", "interior")
        key = "exterior_min" if wall_type == "exterior" else "interior_min"
        t = float(w.get("thickness", 0.0))
        if t + 1e-9 < float(rules["walls"][key]):
            findings.append(Finding(
                "ERROR", "WALL_THIN",
                f"{wid}: {t:.2f} m < minimum {rules['walls'][key]} m ({wall_type})",
                where))

        # openings: inside the wall and not overlapping
        prev_b = None
        for o in sorted(w.get("openings", []), key=lambda o: float(o.get("s", 0))):
            oid = o.get("id", "?")
            try:
                s = float(o["s"])
                width = float(o["width"])
            except (KeyError, TypeError, ValueError):
                findings.append(Finding("ERROR", "OPENING_BAD", f"{wid}: invalid opening {oid}", where))
                continue
            a, b = s - width / 2, s + width / 2
            if a < -1e-6 or b > length + 1e-6:
                findings.append(Finding(
                    "ERROR", "OPENING_OUT_OF_WALL",
                    f"{wid}: opening {oid} outside wall (a={a:.2f}, b={b:.2f}, L={length:.2f})",
                    where))
            if prev_b is not None and a < prev_b - 1e-6:
                findings.append(Finding(
                    "ERROR", "OPENING_OVERLAP",
                    f"{wid}: opening {oid} overlaps the previous one",
                    where))
            prev_b = max(prev_b or b, b)

            if o.get("type") == "door":
                use = o.get("use", "interior")
                need = float(rules.get("doors", {}).get(use, rules.get("doors", {}).get("interior", 0.8)))
                if width + 1e-9 < need:
                    findings.append(Finding(
                        "ERROR", "DOOR_NARROW",
                        f"{wid}: door {oid} {width:.2f} m < minimum {need} m ({use})",
                        where))

            height = o.get("height")
            if height is not None and float(height) > alt + 1e-6:
                findings.append(Finding(
                    "WARN", "OPENING_TALLER_THAN_WALL",
                    f"{wid}: opening {oid} height {float(height):.2f} m > clear height {alt:.2f} m",
                    where))
            sill = o.get("sill")
            if height is not None and sill is not None and float(sill) + float(height) > alt + 1e-6:
                findings.append(Finding(
                    "WARN", "OPENING_ABOVE_CEILING",
                    f"{wid}: opening {oid} sill+height > clear height",
                    where))

    # --- rooms ---
    names: dict[str, int] = {}
    for i, room in enumerate(spec.get("rooms", [])):
        name = room.get("name", f"room {i}")
        kind = room.get("type", "")
        where = f"rooms/{i}"
        if name in names:
            findings.append(Finding(
                "ERROR", "ROOM_DUPLICATE",
                f"duplicate room name: {name}",
                where))
        names[name] = i

        try:
            w, h = float(room["w"]), float(room["h"])
        except (KeyError, TypeError, ValueError):
            findings.append(Finding("ERROR", "ROOM_BAD_SIZE", f"{name}: invalid w/h", where))
            continue
        if w <= TOL or h <= TOL:
            findings.append(Finding("ERROR", "ROOM_ZERO", f"{name}: width or height is 0", where))
            continue

        r = room_rules.get(kind)
        if r is None:
            findings.append(Finding(
                "WARN", "ROOM_KIND_UNKNOWN",
                f"{name}: type '{kind}' has no rule in caba_rules.json",
                where))
        else:
            area = w * h
            if area + 1e-9 < float(r["min_area"]):
                findings.append(Finding(
                    "ERROR", "ROOM_TOO_SMALL",
                    f"{name}: {area:.2f} m2 < minimum {r['min_area']} m2",
                    where))
            side = min(w, h)
            if side + 1e-9 < float(r["min_side"]):
                findings.append(Finding(
                    "ERROR", "ROOM_SIDE_TOO_SMALL",
                    f"{name}: side {side:.2f} m < minimum {r['min_side']} m",
                    where))

        # If the spec declares a lot, the room must fit inside it.
        lot = spec.get("lot")
        if isinstance(lot, dict) and lot.get("front_m") and lot.get("depth_m"):
            x, y = float(room["x"]), float(room["y"])
            if x < -1e-6 or y < -1e-6:
                findings.append(Finding(
                    "ERROR", "ROOM_OUT_OF_LOT",
                    f"{name}: origin ({x:.2f}, {y:.2f}) outside the lot",
                    where))
            if x + w > float(lot["front_m"]) + 1e-6:
                findings.append(Finding(
                    "ERROR", "ROOM_OUT_OF_LOT",
                    f"{name}: x+w={x + w:.2f} > front {lot['front_m']}",
                    where))
            if y + h > float(lot["depth_m"]) + 1e-6:
                findings.append(Finding(
                    "ERROR", "ROOM_OUT_OF_LOT",
                    f"{name}: y+h={y + h:.2f} > depth {lot['depth_m']}",
                    where))

    # --- room overlap ---
    rooms = spec.get("rooms", [])
    for i, a in enumerate(rooms):
        try:
            ax0, ay0, ax1, ay1 = _rect(a)
        except (KeyError, TypeError, ValueError):
            continue
        for b in rooms[i + 1:]:
            try:
                bx0, by0, bx1, by1 = _rect(b)
            except (KeyError, TypeError, ValueError):
                continue
            ox = min(ax1, bx1) - max(ax0, bx0)
            oy = min(ay1, by1) - max(ay0, by0)
            if ox > 1e-4 and oy > 1e-4:
                findings.append(Finding(
                    "ERROR", "ROOM_OVERLAP",
                    f"{a.get('name', '?')} and {b.get('name', '?')} overlap {ox:.2f}x{oy:.2f} m",
                    f"rooms/{i}"))
    return findings


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Preflight a housing spec.")
    ap.add_argument("spec", type=Path, help="spec JSON to validate")
    ap.add_argument("--rules", type=Path, default=DEFAULT_RULES, help="CABA rules")
    ap.add_argument("--schema", type=Path, default=DEFAULT_SCHEMA, help="JSON Schema")
    ap.add_argument("--json", action="store_true", help="JSON output")
    args = ap.parse_args(argv)

    try:
        spec = load_json(args.spec)
    except Exception as exc:
        print(f"ERROR: could not read {args.spec}: {exc}", file=sys.stderr)
        return 1
    try:
        rules = load_json(args.rules)
    except Exception as exc:
        print(f"ERROR: could not read {args.rules}: {exc}", file=sys.stderr)
        return 1

    findings = check_schema(spec, args.schema) + check_geometry(spec, rules)
    errors = [f for f in findings if f.level == "ERROR"]
    warnings = [f for f in findings if f.level == "WARN"]

    if args.json:
        print(json.dumps({
            "spec": str(args.spec),
            "ok": not errors,
            "errors": [f.as_dict() for f in errors],
            "warnings": [f.as_dict() for f in warnings],
        }, ensure_ascii=False, indent=2))
    else:
        print(f"== validate_spec: {args.spec} ==")
        for f in errors + warnings:
            loc = f" [{f.where}]" if f.where else ""
            print(f"  {f.level:5s} {f.code}: {f.msg}{loc}")
        if not findings:
            print("  OK    schema and geometry have no findings")
        print()
        print(f"result: {'OK' if not errors else 'ERROR'} "
              f"({len(errors)} errors, {len(warnings)} warnings)")

    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
