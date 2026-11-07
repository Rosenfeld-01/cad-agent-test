#!/usr/bin/env python3
"""qa_muros.py — gate de solapes de muros (A-WALL).

    python3 tools/qa_muros.py out/L01.dxf out/L02.dxf
    python3 tools/qa_muros.py --all out
    python3 tools/qa_muros.py --all out --verbose --json out/_muros.json

Mide el área de solape entre los polígonos cerrados de la capa A-WALL:

- Si todos son rectángulos alineados a los ejes (el dibujo "un rectángulo por
  muro"), calcula el solape EXACTO: suma de áreas menos el área de la unión
  (barrido de rectángulos).
- Si son contornos poligonales (la frontera de la unión de muros), estima el
  solape con un muestreo fino del número de vueltas: una celda con número de
  vueltas >= 2 está cubierta dos veces.

Código de salida 1 si alguna lámina supera TOL metros cuadrados de papel.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

import ezdxf
from ezdxf import bbox as ezbbox

CAPA = "A-WALL"
TOL = 1e-5          # m² de papel
PASO = 0.0006       # lado de celda del muestreo (m de papel)


def _escala_hoja(doc) -> float:
    """Factor de escala real de la hoja (1 = papel, 50 = 1:1 real).

    Las plantas a escala real son ``escala`` veces más grandes que el A2 de
    papel; se escalan la celda y la tolerancia para medir con la misma
    resolución física (≈0,6 mm de papel) sin muestrear de más.
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


def _poligonos(msp):
    polys = []
    for pl in msp.query("LWPOLYLINE"):
        if pl.dxf.layer != CAPA or not pl.closed:
            continue
        pts = [(float(x), float(y)) for x, y in pl.get_points("xy")]
        if len(pts) >= 3:
            polys.append(pts)
    return polys


def _es_rect(poly, tol=1e-9):
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
    """Área exacta de la unión de rectángulos alineados a los ejes."""
    xs = sorted(set([r[0] for r in rects] + [r[2] for r in rects]))
    area = 0.0
    for x0, x1 in zip(xs, xs[1:]):
        if x1 - x0 < 1e-15:
            continue
        xm = (x0 + x1) / 2.0
        tramos = sorted((r[1], r[3]) for r in rects if r[0] <= xm <= r[2])
        cub = 0.0
        cua = cuf = None
        for a, b in tramos:
            if cua is None:
                cua, cuf = a, b
            elif a <= cuf:
                cuf = max(cuf, b)
            else:
                cub += cuf - cua
                cua, cuf = a, b
        if cua is not None:
            cub += cuf - cua
        area += (x1 - x0) * cub
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


def solape(polys, paso: float = PASO):
    """Área de solape (m²) entre los polígonos de A-WALL."""
    if len(polys) < 2:
        return 0.0
    rects = [_es_rect(p) for p in polys]
    if all(r is not None for r in rects):
        suma = sum(abs(_shoelace(p)) for p in polys)
        return max(0.0, suma - _union_area_rects(rects))
    xs0 = min(min(p[0] for p in q) for q in polys)
    xs1 = max(max(p[0] for p in q) for q in polys)
    ys0 = min(min(p[1] for p in q) for q in polys)
    ys1 = max(max(p[1] for p in q) for q in polys)
    # paso adaptativo: no más de ~3M de celdas (evita colgarse si el DXF está en
    # metros de proyecto en lugar de metros de papel)
    while ((xs1 - xs0) / paso) * ((ys1 - ys0) / paso) > 3_000_000:
        paso *= 1.5
    nx = int((xs1 - xs0) / paso) + 1
    ny = int((ys1 - ys0) / paso) + 1
    area = 0.0
    for iy in range(ny):
        py = ys0 + (iy + 0.5) * paso
        for ix in range(nx):
            px = xs0 + (ix + 0.5) * paso
            w = 0
            for q in polys:
                w += _winding(px, py, q)
            if w >= 2:
                area += paso * paso
    return area


def analizar(ruta: Path) -> dict:
    doc = ezdxf.readfile(ruta)
    k = _escala_hoja(doc)
    polys = _poligonos(doc.modelspace())
    return {"lamina": ruta.name, "poligonos": len(polys), "k": k,
            "solape_m2": round(solape(polys, PASO * k), 7)}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Gate de solapes de muros (A-WALL)")
    ap.add_argument("rutas", nargs="*")
    ap.add_argument("--all", metavar="DIR")
    ap.add_argument("--json", metavar="SALIDA")
    ap.add_argument("--verbose", "-v", action="store_true")
    args = ap.parse_args(argv)
    rutas = [Path(r) for r in args.rutas]
    if args.all:
        rutas += sorted(Path(args.all).glob("L*.dxf"))
    if not rutas:
        ap.error("indicá archivos o --all DIR")

    informes, fallas = [], 0
    for ruta in rutas:
        try:
            rep = analizar(ruta)
        except Exception as exc:                        # noqa: BLE001
            print(f"{ruta.name}: ERROR {type(exc).__name__}: {exc}")
            fallas += 1
            continue
        informes.append(rep)
        ok = rep["solape_m2"] <= TOL * rep["k"] ** 2
        print(f"{ruta.name:9s} A-WALL={rep['poligonos']:3d}  "
              f"solape={rep['solape_m2']:.2e} m2  {'OK' if ok else 'SOLAPE'}")
        if not ok:
            fallas += 1
    if args.json:
        Path(args.json).write_text(
            json.dumps(informes, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"\nresumen: {args.json}")
    print(f"\n{len(informes) - fallas}/{len(informes)} láminas sin solape de muro")
    return 1 if fallas else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
