#!/usr/bin/env python3
"""
plan.py — generador paramétrico de planos de vivienda (DXF) para CADCraft.

Lee un spec JSON (intención del diseño) y emite un DXF con:
  - muros como polilíneas cerradas (A-WALL), con aberturas reales (huecos)
  - puertas con hoja + arco de giro (A-DOOR)
  - ventanas con doble línea (A-WIN)
  - ambientes con polígono cerrado + nombre y superficie (A-AREA / A-ANNO)
  - cotas generales (A-DIM)

No dibuja a mano: todo sale del spec. El agente edita el spec, no el DXF.

Uso:
    python3 plan.py typologies/semillas/casa_8.66x20.json out/planta.dxf
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
    "A-WALL": 7,      # muros
    "A-DOOR": 3,      # puertas
    "A-WIN": 4,       # ventanas
    "A-AREA": 8,      # polígonos de ambiente
    "A-ANNO": 2,      # textos / nombres
    "A-DIM": 1,       # cotas
    "A-AXIS": 6,      # ejes
}


def _v(x):
    return ezdxf.math.Vec2(x[0], x[1])


def _wall_solids(p1, p2, t, openings):
    """Devuelve los tramos sólidos del muro (rectángulos) y los datos de apoyo."""
    p1, p2 = _v(p1), _v(p2)
    delta = p2 - p1
    length = delta.magnitude
    if length < 1e-9:
        raise ValueError("muro de longitud cero")
    u = delta.normalize()
    n = ezdxf.math.Vec2((-u.y, u.x))

    ops = sorted(openings, key=lambda o: o["s"])
    cuts = []
    for o in ops:
        a = o["s"] - o["ancho"] / 2.0
        b = o["s"] + o["ancho"] / 2.0
        if a < -1e-6 or b > length + 1e-6:
            raise ValueError(
                f"abertura fuera del muro (s={o['s']}, ancho={o['ancho']}, L={length:.2f})"
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


def _pip_convex(px, py, poly, eps=1e-9):
    """True si (px,py) está dentro de un polígono convexo (o en borde)."""
    n = len(poly)
    signo = 0
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
        if signo == 0:
            signo = s
        elif s != signo:
            return False
    return True


def _segmentos_union(solids, eps=1e-3):
    """Aristas atómicas en la frontera de la unión de sólidos (polígonos convexos).

    Devuelve segmentos dirigidos (interior a la izquierda): contorno CCW de los
    cuerpos y CW de los huecos.  Se parte cada arista en cruces y proyecciones
    de vértices, se descartan las interiores y se orienta por muestreo lateral.
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

    # 1) parámetros de corte por arista (extremos + intersecciones + vértices)
    cortes = [[0.0, 1.0] for _ in edges]
    for i, (a, b) in enumerate(edges):
        dx, dy = b[0] - a[0], b[1] - a[1]
        L2 = dx * dx + dy * dy
        if L2 < 1e-18:
            continue
        for (px, py) in pts:                       # proyecciones de vértices
            t = ((px - a[0]) * dx + (py - a[1]) * dy) / L2
            if 1e-9 < t < 1 - 1e-9:
                qx, qy = a[0] + dx * t, a[1] + dy * t
                if abs(qx - px) < 1e-7 and abs(qy - py) < 1e-7:
                    cortes[i].append(t)
        for j, (c, d) in enumerate(edges):         # cruces con otras aristas
            if j == i:
                continue
            ex, ey = d[0] - c[0], d[1] - c[1]
            den = dx * ey - dy * ex
            if abs(den) < 1e-15:
                continue
            t = ((c[0] - a[0]) * ey - (c[1] - a[1]) * ex) / den
            u = ((c[0] - a[0]) * dy - (c[1] - a[1]) * dx) / den
            if 1e-9 < t < 1 - 1e-9 and -1e-9 < u < 1 + 1e-9:
                cortes[i].append(t)

    # 2) subsegmentos únicos (sin duplicar aristas coincidentes)
    uniq = {}
    for i, (a, b) in enumerate(edges):
        dx, dy = b[0] - a[0], b[1] - a[1]
        ts = sorted(set(round(t, 9) for t in cortes[i]))
        for t0, t1 in zip(ts, ts[1:]):
            if t1 - t0 < 1e-9:
                continue
            p0 = (round(a[0] + dx * t0, 6), round(a[1] + dy * t0, 6))
            p1 = (round(a[0] + dx * t1, 6), round(a[1] + dy * t1, 6))
            k = tuple(sorted((p0, p1)))
            if p0 != p1:
                uniq[k] = (p0, p1)

    # 3) frontera orientada (interior a la izquierda)
    dirig = []
    for p0, p1 in uniq.values():
        mx, my = (p0[0] + p1[0]) / 2.0, (p0[1] + p1[1]) / 2.0
        dx, dy = p1[0] - p0[0], p1[1] - p0[1]
        L = math.hypot(dx, dy)
        if L < 1e-12:
            continue
        nx, ny = -dy / L, dx / L
        izq = any(_pip_convex(mx + nx * eps, my + ny * eps, s) for s in solids)
        der = any(_pip_convex(mx - nx * eps, my - ny * eps, s) for s in solids)
        if izq and not der:
            dirig.append((p0, p1))
        elif der and not izq:
            dirig.append((p1, p0))
    return dirig


def _encadenar(dirig):
    """Une segmentos dirigidos (interior a la izquierda) en lazos cerrados."""
    if not dirig:
        return []
    salidas = {}
    for a, b in dirig:
        salidas.setdefault(a, []).append(b)

    def ang(a, b):
        return math.degrees(math.atan2(b[1] - a[1], b[0] - a[0])) % 360.0

    usados = set()
    lazos = []
    for ini in list(salidas):
        for nxt in salidas[ini]:
            if (ini, nxt) in usados:
                continue
            lazo = [ini]
            prev, cur = ini, nxt
            usados.add((prev, cur))
            while cur != ini:
                lazo.append(cur)
                cands = [b for b in salidas.get(cur, []) if (cur, b) not in usados]
                if not cands:
                    break
                a_in = ang(prev, cur)
                # giro más cerrado a la izquierda = menor rotación horaria de la inversa
                def clave(b):
                    return (a_in + 180.0 - ang(cur, b)) % 360.0
                nxt2 = min(cands, key=clave)
                usados.add((cur, nxt2))
                prev, cur = cur, nxt2
            if len(lazo) >= 3 and cur == ini:
                lazos.append(lazo)
    return lazos


def wall_outline(walls, ext=0.20):
    """Contorno (unión) de un conjunto de muros como lazos cerrados en proyecto.

    Reemplaza el dibujo de un rectángulo por muro (que se solapaba en esquinas y
    cruces) por la frontera real de la unión.  Devuelve lista de lazos [(x,y)...].
    """
    solids = []
    for w in walls:
        p1, p2 = _v(w["p1"]), _v(w["p2"])
        t = float(w.get("espesor", ext))
        s, _u, _n, _L, _cuts = _wall_solids(p1, p2, t, w.get("aberturas", []))
        for pts in s:
            solids.append([(p.x, p.y) for p in pts])
    return _encadenar(_segmentos_union(solids))


def _draw_opening(msp, p1, u, n, t, a, b, kind):
    """Símbolo de la abertura en el hueco [a, b]."""
    pa, pb = p1 + u * a, p1 + u * b
    if kind == "puerta":
        hinge = pa + n * (t / 2)
        leaf_end = hinge + n * (b - a)
        msp.add_line(hinge, leaf_end, dxfattribs={"layer": "A-DOOR"})
        ang_u = math.degrees(math.atan2(u.y, u.x))
        ang_n = math.degrees(math.atan2(n.y, n.x))
        # arco de 90° desde la hoja hasta el muro
        msp.add_arc(
            center=hinge, radius=(b - a),
            start_angle=min(ang_u, ang_n), end_angle=max(ang_u, ang_n),
            dxfattribs={"layer": "A-DOOR"},
        )
    elif kind == "ventana":
        off = t / 6.0
        for s in (off, -off):
            msp.add_line(pa + n * s, pb + n * s, dxfattribs={"layer": "A-WIN"})
    elif kind == "hueco":
        pass
    else:
        raise ValueError(f"tipo de abertura desconocido: {kind}")


def build(spec: dict, out: Path) -> Path:
    doc = ezdxf.new("R2010", setup=True)
    doc.units = ezdxf.units.M
    doc.header["$INSUNITS"] = 6
    doc.appids.add(APPID)

    for name, color in LAYERS.items():
        if name not in doc.layers:
            doc.layers.add(name, color=color)

    msp = doc.modelspace()
    ext = spec["muros"].get("exterior", 0.20) if isinstance(spec.get("muros"), dict) else 0.20

    walls = spec["muros"] if isinstance(spec["muros"], list) else spec["muros"]["segmentos"]
    # un solo contorno (unión) por región: evita muros solapados en esquinas/cruces
    for loop in wall_outline(walls, ext):
        msp.add_lwpolyline([(x, y) for x, y in loop], close=True,
                           dxfattribs={"layer": "A-WALL"})
    for w in walls:
        p1, p2 = _v(w["p1"]), _v(w["p2"])
        t = float(w.get("espesor", ext))
        _solids, u, n, _length, cuts = _wall_solids(p1, p2, t, w.get("aberturas", []))
        for a, b, o in cuts:
            _draw_opening(msp, p1, u, n, t, a, b, o.get("tipo", "hueco"))

    # Ambientes: polígono + etiqueta
    for amb in spec.get("ambientes", []):
        x, y = float(amb["x"]), float(amb["y"])
        w, h = float(amb["w"]), float(amb["h"])
        pts = [(x, y), (x + w, y), (x + w, y + h), (x, y + h)]
        pl = msp.add_lwpolyline(pts, close=True, dxfattribs={"layer": "A-AREA"})
        pl.set_xdata(APPID, [(1000, amb["nombre"])])
        area = w * h
        cx, cy = x + w / 2, y + h / 2
        name = msp.add_text(amb["nombre"], height=0.20,
                            dxfattribs={"layer": "A-ANNO"})
        name.set_placement((cx, cy + 0.20), align=TextEntityAlignment.MIDDLE_CENTER)
        val = msp.add_text(f"{area:.1f} m2", height=0.16,
                           dxfattribs={"layer": "A-ANNO"})
        val.set_placement((cx, cy - 0.15), align=TextEntityAlignment.MIDDLE_CENTER)

    # Cotas generales
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
        print("uso: python3 plan.py SPEC.json OUT.dxf", file=sys.stderr)
        return 2
    spec = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    out = build(spec, Path(sys.argv[2]))
    print(f"OK  {out}  ({out.stat().st_size} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
