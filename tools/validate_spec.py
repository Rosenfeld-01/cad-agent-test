#!/usr/bin/env python3
"""validate_spec.py — preflight barato del spec antes de generar el DXF.

Hace dos cosas:

1. Valida el JSON contra `schemas/spec.schema.json` (estructura y tipos).
2. Revisa la geometria que `plan.py` y `check.py` van a necesitar: muros con
   longitud, aberturas dentro del muro y sin solaparse, ambientes con area y
   lado minimo, ambientes sin solaparse y altura libre.

No reemplaza a `check.py`: `check.py` mide el DXF generado (iluminacion,
ventilacion, superficies reales). Este script es el portero de entrada, para no
gastar una generacion en un spec mal formado.

Uso:
    python3 tools/validate_spec.py spec_vivienda01.json
    python3 tools/validate_spec.py casos/vivienda-03/spec.json --json
    python3 tools/validate_spec.py spec.json --rules rules_caba.json

Salida: exit 0 si no hay errores; exit 1 si hay al menos un error.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_RULES = ROOT / "rules_caba.json"
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
    """Valida contra el JSON Schema. Si jsonschema no esta, hace lo minimo."""
    findings: list[Finding] = []
    try:
        from jsonschema import Draft202012Validator
    except ImportError:
        return _check_schema_fallback(spec)

    try:
        schema = load_json(schema_path)
        Draft202012Validator.check_schema(schema)
        validator = Draft202012Validator(schema)
    except Exception as exc:  # schema roto o archivo ilegible
        return [Finding("ERROR", "SCHEMA_BROKEN", f"no se pudo cargar el schema: {exc}")]

    for err in sorted(validator.iter_errors(spec), key=lambda e: list(e.path)):
        where = "/".join(str(p) for p in err.path) or "(raiz)"
        findings.append(Finding("ERROR", "SCHEMA", err.message, where))
    return findings


def _check_schema_fallback(spec: dict) -> list[Finding]:
    """Chequeo minimo sin dependencias, por si falta jsonschema."""
    findings: list[Finding] = []
    required = ["unidad", "altura_libre", "muros", "ambientes"]
    for key in required:
        if key not in spec:
            findings.append(Finding("ERROR", "SCHEMA", f"falta '{key}'", "(raiz)"))
    if spec.get("unidad") != "m":
        findings.append(Finding("ERROR", "SCHEMA", "unidad debe ser 'm'", "unidad"))
    if not isinstance(spec.get("muros"), list):
        findings.append(Finding("ERROR", "SCHEMA", "muros debe ser una lista", "muros"))
    if not isinstance(spec.get("ambientes"), list):
        findings.append(Finding("ERROR", "SCHEMA", "ambientes debe ser una lista", "ambientes"))
    for i, w in enumerate(spec.get("muros", [])):
        for key in ("p1", "p2", "espesor", "aberturas"):
            if key not in w:
                findings.append(Finding("ERROR", "SCHEMA", f"muro {i}: falta '{key}'", f"muros/{i}"))
    for i, a in enumerate(spec.get("ambientes", [])):
        for key in ("nombre", "tipo", "x", "y", "w", "h"):
            if key not in a:
                findings.append(Finding("ERROR", "SCHEMA", f"ambiente {i}: falta '{key}'", f"ambientes/{i}"))
    return findings


def _rect(a: dict) -> tuple[float, float, float, float]:
    x, y = float(a["x"]), float(a["y"])
    return x, y, x + float(a["w"]), y + float(a["h"])


def check_geometry(spec: dict, rules: dict) -> list[Finding]:
    findings: list[Finding] = []
    amb_rules = rules.get("ambientes", {})
    sin_vent = set(rules.get("sin_ventilacion", []))

    # --- altura libre ---
    alt = float(spec.get("altura_libre", 0.0))
    if alt + 1e-9 < float(rules.get("altura_libre_min", 0.0)):
        findings.append(Finding(
            "ERROR", "CEILING_LOW",
            f"altura libre {alt:.2f} m < minimo {rules['altura_libre_min']} m",
            "altura_libre"))

    # --- muros ---
    for i, w in enumerate(spec.get("muros", [])):
        wid = w.get("id", f"muro {i}")
        where = f"muros/{i}"
        try:
            x1, y1 = float(w["p1"][0]), float(w["p1"][1])
            x2, y2 = float(w["p2"][0]), float(w["p2"][1])
        except (KeyError, IndexError, TypeError, ValueError):
            findings.append(Finding("ERROR", "WALL_BAD_POINT", f"{wid}: p1/p2 invalidos", where))
            continue
        length = math.hypot(x2 - x1, y2 - y1)
        if length <= TOL:
            findings.append(Finding("ERROR", "WALL_ZERO", f"{wid}: longitud 0", where))
            continue

        tipo = w.get("tipo", "interior")
        key = "exterior_min" if tipo == "exterior" else "interior_min"
        t = float(w.get("espesor", 0.0))
        if t + 1e-9 < float(rules["muros"][key]):
            findings.append(Finding(
                "ERROR", "WALL_THIN",
                f"{wid}: {t:.2f} m < minimo {rules['muros'][key]} m ({tipo})",
                where))

        # aberturas: dentro del muro y sin solaparse
        prev_b = None
        for o in sorted(w.get("aberturas", []), key=lambda o: float(o.get("s", 0))):
            oid = o.get("id", "?")
            try:
                s = float(o["s"])
                ancho = float(o["ancho"])
            except (KeyError, TypeError, ValueError):
                findings.append(Finding("ERROR", "OPENING_BAD", f"{wid}: abertura {oid} invalida", where))
                continue
            a, b = s - ancho / 2, s + ancho / 2
            if a < -1e-6 or b > length + 1e-6:
                findings.append(Finding(
                    "ERROR", "OPENING_OUT_OF_WALL",
                    f"{wid}: abertura {oid} fuera del muro (a={a:.2f}, b={b:.2f}, L={length:.2f})",
                    where))
            if prev_b is not None and a < prev_b - 1e-6:
                findings.append(Finding(
                    "ERROR", "OPENING_OVERLAP",
                    f"{wid}: abertura {oid} se solapa con la anterior",
                    where))
            prev_b = max(prev_b or b, b)

            if o.get("tipo") == "puerta":
                uso = o.get("uso", "interior")
                need = float(rules.get("puertas", {}).get(uso, rules.get("puertas", {}).get("interior", 0.8)))
                if ancho + 1e-9 < need:
                    findings.append(Finding(
                        "ERROR", "DOOR_NARROW",
                        f"{wid}: puerta {oid} {ancho:.2f} m < minimo {need} m ({uso})",
                        where))

            alto = o.get("alto")
            if alto is not None and float(alto) > alt + 1e-6:
                findings.append(Finding(
                    "WARN", "OPENING_TALLER_THAN_WALL",
                    f"{wid}: abertura {oid} alto {float(alto):.2f} m > altura libre {alt:.2f} m",
                    where))
            ante = o.get("antepecho")
            if alto is not None and ante is not None and float(ante) + float(alto) > alt + 1e-6:
                findings.append(Finding(
                    "WARN", "OPENING_ABOVE_CEILING",
                    f"{wid}: abertura {oid} antepecho+alto > altura libre",
                    where))

    # --- ambientes ---
    names: dict[str, int] = {}
    for i, amb in enumerate(spec.get("ambientes", [])):
        name = amb.get("nombre", f"ambiente {i}")
        kind = amb.get("tipo", "")
        where = f"ambientes/{i}"
        if name in names:
            findings.append(Finding(
                "ERROR", "ROOM_DUPLICATE",
                f"nombre de ambiente repetido: {name}",
                where))
        names[name] = i

        try:
            w, h = float(amb["w"]), float(amb["h"])
        except (KeyError, TypeError, ValueError):
            findings.append(Finding("ERROR", "ROOM_BAD_SIZE", f"{name}: w/h invalidos", where))
            continue
        if w <= TOL or h <= TOL:
            findings.append(Finding("ERROR", "ROOM_ZERO", f"{name}: ancho o alto 0", where))
            continue

        r = amb_rules.get(kind)
        if r is None:
            findings.append(Finding(
                "WARN", "ROOM_KIND_UNKNOWN",
                f"{name}: tipo '{kind}' sin regla en rules_caba.json",
                where))
        else:
            area = w * h
            if area + 1e-9 < float(r["area_min"]):
                findings.append(Finding(
                    "ERROR", "ROOM_TOO_SMALL",
                    f"{name}: {area:.2f} m2 < minimo {r['area_min']} m2",
                    where))
            side = min(w, h)
            if side + 1e-9 < float(r["lado_min"]):
                findings.append(Finding(
                    "ERROR", "ROOM_SIDE_TOO_SMALL",
                    f"{name}: lado {side:.2f} m < minimo {r['lado_min']} m",
                    where))

        # Si el spec declara lote, el ambiente tiene que entrar.
        lote = spec.get("lote")
        if isinstance(lote, dict) and lote.get("frente_m") and lote.get("fondo_m"):
            x, y = float(amb["x"]), float(amb["y"])
            if x < -1e-6 or y < -1e-6:
                findings.append(Finding(
                    "ERROR", "ROOM_OUT_OF_LOT",
                    f"{name}: origen ({x:.2f}, {y:.2f}) fuera del lote",
                    where))
            if x + w > float(lote["frente_m"]) + 1e-6:
                findings.append(Finding(
                    "ERROR", "ROOM_OUT_OF_LOT",
                    f"{name}: x+w={x + w:.2f} > frente {lote['frente_m']}",
                    where))
            if y + h > float(lote["fondo_m"]) + 1e-6:
                findings.append(Finding(
                    "ERROR", "ROOM_OUT_OF_LOT",
                    f"{name}: y+h={y + h:.2f} > fondo {lote['fondo_m']}",
                    where))

    # --- solapamiento entre ambientes ---
    ambs = spec.get("ambientes", [])
    for i, a in enumerate(ambs):
        try:
            ax0, ay0, ax1, ay1 = _rect(a)
        except (KeyError, TypeError, ValueError):
            continue
        for b in ambs[i + 1:]:
            try:
                bx0, by0, bx1, by1 = _rect(b)
            except (KeyError, TypeError, ValueError):
                continue
            ox = min(ax1, bx1) - max(ax0, bx0)
            oy = min(ay1, by1) - max(ay0, by0)
            if ox > 1e-4 and oy > 1e-4:
                findings.append(Finding(
                    "ERROR", "ROOM_OVERLAP",
                    f"{a.get('nombre', '?')} y {b.get('nombre', '?')} se solapan {ox:.2f}x{oy:.2f} m",
                    f"ambientes/{i}"))
    return findings


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Preflight de un spec de vivienda.")
    ap.add_argument("spec", type=Path, help="spec JSON a validar")
    ap.add_argument("--rules", type=Path, default=DEFAULT_RULES, help="reglas CABA")
    ap.add_argument("--schema", type=Path, default=DEFAULT_SCHEMA, help="JSON Schema")
    ap.add_argument("--json", action="store_true", help="salida JSON")
    args = ap.parse_args(argv)

    try:
        spec = load_json(args.spec)
    except Exception as exc:
        print(f"ERROR: no se pudo leer {args.spec}: {exc}", file=sys.stderr)
        return 1
    try:
        rules = load_json(args.rules)
    except Exception as exc:
        print(f"ERROR: no se pudo leer {args.rules}: {exc}", file=sys.stderr)
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
            print("  OK    schema y geometria sin hallazgos")
        print()
        print(f"resultado: {'OK' if not errors else 'ERROR'} "
              f"({len(errors)} errores, {len(warnings)} warnings)")

    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
