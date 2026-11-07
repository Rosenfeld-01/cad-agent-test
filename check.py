#!/usr/bin/env python3
"""
check.py — validador determinístico del plano.

Esto es la "conciencia de errores" del agente: NO es el LLM. Es código que
revisa el DXF contra el spec y contra las reglas de rules_caba.json.

Calcula la iluminación y ventilación de cada ambiente desde la GEOMETRÍA REAL
de las ventanas del spec (no confía en un número declarado a mano).

Salida: reporte legible + report.json. Exit code 1 si hay errores.

Uso:
    python3 check.py out/planta.dxf typologies/semillas/casa_8.66x20.json [rules_caba.json]
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


def _rect(amb):
    x, y = float(amb["x"]), float(amb["y"])
    return x, y, x + float(amb["w"]), y + float(amb["h"])


def _point_in(px, py, rect, margin):
    x0, y0, x1, y1 = rect
    return (x0 - margin) <= px <= (x1 + margin) and (y0 - margin) <= py <= (y1 + margin)


def _window_area_by_room(spec, warnings):
    """Suma la superficie de ventanas de cada ambiente, ubicando el punto medio
    de cada ventana en el rectángulo del ambiente más cercano."""
    ambs = spec.get("ambientes", [])
    areas = {a["nombre"]: 0.0 for a in ambs}
    for w in spec["muros"]:
        p1, p2 = w["p1"], w["p2"]
        dx, dy = p2[0] - p1[0], p2[1] - p1[1]
        length = math.hypot(dx, dy)
        if length < 1e-9:
            continue
        ux, uy = dx / length, dy / length
        for o in w.get("aberturas", []):
            if o.get("tipo") != "ventana":
                continue
            s = float(o["s"])
            px, py = p1[0] + ux * s, p1[1] + uy * s
            cand = [a for a in ambs if _point_in(px, py, _rect(a), 0.30)]
            if not cand:
                warnings.append({
                    "code": "WINDOW_ORPHAN",
                    "msg": f"ventana {o.get('id', '?')} no cae en ningún ambiente",
                })
                continue
            cand.sort(key=lambda a: float(a["w"]) * float(a["h"]))
            room = cand[0]
            areas[room["nombre"]] += float(o["ancho"]) * float(o.get("alto", 1.4))
    return areas


def check(dxf_path: Path, spec: dict, rules: dict) -> dict:
    doc = ezdxf.readfile(dxf_path)
    msp = doc.modelspace()
    errors, warnings = [], []

    def err(code, msg, **kw):
        errors.append({"code": code, "msg": msg, **kw})

    def warn(code, msg, **kw):
        warnings.append({"code": code, "msg": msg, **kw})

    # --- capas mínimas ---
    for name in ["A-WALL", "A-DOOR", "A-WIN", "A-AREA", "A-ANNO"]:
        if name not in doc.layers:
            err("LAYER_MISSING", f"falta la capa {name}", layer=name)

    # --- polilíneas cerradas ---
    polylines = list(msp.query("LWPOLYLINE"))
    if not polylines:
        err("NO_WALLS", "el plano no tiene polilíneas (¿muros?)")
    for pl in polylines:
        if not pl.closed:
            err("POLYLINE_OPEN", f"polilínea abierta en capa {pl.dxf.layer}",
                layer=pl.dxf.layer, handle=pl.dxf.handle)

    # --- ambientes: DXF vs spec ---
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
            warn("ROOM_UNNAMED", "polígono de ambiente sin nombre en XDATA")
            continue
        dxf_rooms[name] = _shoelace(pts)

    win_area = _window_area_by_room(spec, warnings)
    amb_rules = rules["ambientes"]
    sin_vent = set(rules.get("sin_ventilacion", []))

    for amb in spec.get("ambientes", []):
        name, kind = amb["nombre"], amb["tipo"]
        w, h = float(amb["w"]), float(amb["h"])
        area_spec = w * h
        side_min = min(w, h)

        if name not in dxf_rooms:
            err("ROOM_MISSING", f"ambiente {name} no está en el DXF", ambiente=name)
            continue
        if abs(dxf_rooms[name] - area_spec) > TOL:
            err("AREA_MISMATCH",
                f"{name}: DXF {dxf_rooms[name]:.2f} m2 vs spec {area_spec:.2f} m2",
                ambiente=name)

        r = amb_rules.get(kind)
        if r is None:
            warn("ROOM_KIND_UNKNOWN", f"{name}: tipo '{kind}' sin regla", ambiente=name)
            continue
        if area_spec + 1e-9 < r["area_min"]:
            err("ROOM_TOO_SMALL",
                f"{name}: {area_spec:.2f} m2 < mínimo {r['area_min']} m2",
                ambiente=name)
        if side_min + 1e-9 < r["lado_min"]:
            err("ROOM_SIDE_TOO_SMALL",
                f"{name}: lado {side_min:.2f} m < mínimo {r['lado_min']} m",
                ambiente=name)

        # iluminación y ventilación calculadas desde la geometría
        if kind not in sin_vent:
            wa = win_area.get(name, 0.0)
            need_i = area_spec * rules["iluminacion"]["factor"]
            need_v = area_spec * rules["ventilacion"]["factor"]
            if wa + 1e-9 < need_i:
                err("LIGHTING",
                    f"{name}: ventanas {wa:.2f} m2 < iluminación {need_i:.2f} m2 "
                    f"(20% de {area_spec:.2f})", ambiente=name)
            if wa + 1e-9 < need_v:
                err("VENTILATION",
                    f"{name}: ventanas {wa:.2f} m2 < ventilación {need_v:.2f} m2 "
                    f"(5% de {area_spec:.2f})", ambiente=name)
            declared = amb.get("ventilacion_m2")
            if declared is not None and abs(float(declared) - wa) > TOL:
                warn("VENT_DECLARED_MISMATCH",
                    f"{name}: declarado {float(declared):.2f} m2 vs geometría {wa:.2f} m2",
                    ambiente=name)

    # --- solapamiento entre ambientes ---
    ambs = spec.get("ambientes", [])
    for i, a in enumerate(ambs):
        ax0, ay0, ax1, ay1 = _rect(a)
        for b in ambs[i + 1:]:
            bx0, by0, bx1, by1 = _rect(b)
            ox = min(ax1, bx1) - max(ax0, bx0)
            oy = min(ay1, by1) - max(ay0, by0)
            if ox > TOL and oy > TOL:
                err("ROOM_OVERLAP",
                    f"{a['nombre']} y {b['nombre']} se solapan {ox:.2f}x{oy:.2f} m",
                    ambientes=[a["nombre"], b["nombre"]])

    # --- muros: espesores y aberturas ---
    for w in spec["muros"]:
        t = float(w.get("espesor", 0.0))
        tipo = w.get("tipo", "interior")
        key = "exterior_min" if tipo == "exterior" else "interior_min"
        if t + 1e-9 < rules["muros"][key]:
            err("WALL_THIN",
                f"muro {w.get('id', '?')}: {t:.2f} m < mínimo {rules['muros'][key]} m ({tipo})")
        L = math.hypot(w["p2"][0] - w["p1"][0], w["p2"][1] - w["p1"][1])
        for o in w.get("aberturas", []):
            a = float(o["s"]) - float(o["ancho"]) / 2
            b = float(o["s"]) + float(o["ancho"]) / 2
            if a < -1e-6 or b > L + 1e-6:
                err("OPENING_OUT_OF_WALL",
                    f"abertura {o.get('id', '?')} fuera del muro {w.get('id', '?')}")
            if o.get("tipo") == "puerta":
                kind = o.get("uso", "interior")
                need = rules["puertas"].get(kind, rules["puertas"]["interior"])
                if float(o["ancho"]) + 1e-9 < need:
                    err("DOOR_NARROW",
                        f"puerta {o.get('id', '?')}: {o['ancho']:.2f} m < mínimo {need} m ({kind})")

    # --- altura libre ---
    alt = float(spec.get("altura_libre", 0.0))
    if alt + 1e-9 < rules["altura_libre_min"]:
        err("CEILING_LOW",
            f"altura libre {alt:.2f} m < mínimo {rules['altura_libre_min']} m")

    # --- altura de textos ---
    hmin = rules["texto"]["altura_min"]
    for t in msp.query("TEXT MTEXT"):
        h = getattr(t.dxf, "height", None) or getattr(t.dxf, "char_height", None)
        if h is not None and h + 1e-9 < hmin:
            warn("TEXT_SMALL", f"texto de altura {h:.2f} m < {hmin} m",
                 handle=t.dxf.handle)

    stats = {
        "polilineas": len(polylines),
        "ambientes_dxf": len(dxf_rooms),
        "ambientes_spec": len(ambs),
        "puertas": sum(1 for w in spec["muros"] for o in w.get("aberturas", [])
                       if o.get("tipo") == "puerta"),
        "ventanas": sum(1 for w in spec["muros"] for o in w.get("aberturas", [])
                        if o.get("tipo") == "ventana"),
        "ventana_m2": round(sum(win_area.values()), 2),
        "superficie_total_m2": round(sum(
            float(a["w"]) * float(a["h"]) for a in ambs), 2),
    }

    return {
        "ok": not errors,
        "errors": errors,
        "warnings": warnings,
        "stats": stats,
        "rules_source": rules.get("fuente", ""),
    }


def main() -> int:
    if len(sys.argv) < 3:
        print("uso: python3 check.py OUT.dxf SPEC.json [RULES.json]", file=sys.stderr)
        return 2
    dxf = Path(sys.argv[1])
    spec = json.loads(Path(sys.argv[2]).read_text(encoding="utf-8"))
    rules_path = Path(sys.argv[3]) if len(sys.argv) > 3 else Path(__file__).with_name("rules_caba.json")
    rules = json.loads(rules_path.read_text(encoding="utf-8"))

    rep = check(dxf, spec, rules)
    out = dxf.with_suffix(".report.json")
    out.write_text(json.dumps(rep, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"\n{'='*64}\nVALIDACIÓN: {dxf.name}\n{'='*64}")
    for e in rep["errors"]:
        print(f"  ERROR  [{e['code']}] {e['msg']}")
    for w in rep["warnings"]:
        print(f"  aviso  [{w['code']}] {w['msg']}")
    s = rep["stats"]
    print(f"\n  ambientes: {s['ambientes_dxf']}/{s['ambientes_spec']}  "
          f"puertas: {s['puertas']}  ventanas: {s['ventanas']} ({s['ventana_m2']} m2)  "
          f"superficie: {s['superficie_total_m2']} m2")
    print(f"  reglas: {rep['rules_source']}")
    estado = "OK" if rep["ok"] else f"{len(rep['errors'])} ERROR(ES)"
    print(f"  resultado: {estado}")
    print(f"  reporte: {out}\n")
    return 0 if rep["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
