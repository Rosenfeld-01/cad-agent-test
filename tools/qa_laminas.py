#!/usr/bin/env python3
"""qa_laminas.py — gate de QA de las láminas del juego de planos.

Revisa, para cada DXF de lámina (A2 = 0,594 x 0,420 m de papel):

1. solapes de texto  (TEXT y MTEXT, con su alineación y rotación)
2. entidades fuera de la hoja (bounds fuera de 0..ancho / 0..alto)
3. auditoría de ezdxf (errores de estructura)

Uso:
    python3 tools/qa_laminas.py out/L01.dxf out/L02.dxf
    python3 tools/qa_laminas.py --all out
    python3 tools/qa_laminas.py --all out --json out/_qa.json --verbose

Salida: una línea por lámina, el detalle de los hallazgos y exit code 1 si
alguna lámina no pasa. Es el mismo chequeo que se usó para cerrar la Vivienda 02.

Criterio
--------
- El solape se mide en metros de papel: cuenta si la intersección supera
  0,4 mm de ancho y 0,5 mm de alto (menos que eso es contacto tipográfico).
- Ancho medio de carácter: 0,62 x altura.
- Los INSERT no se evalúan fuera de hoja (su caja depende de la definición del
  bloque); los símbolos son chicos y van siempre junto a la planta.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import ezdxf
from ezdxf import bbox as ezbbox

ANCHO, ALTO = 0.594, 0.420           # A2 en metros de papel
MIN_IX, MIN_IY = 0.0004, 0.0005      # tolerancia de solape (m)
CRITERIO = 0.62                      # ancho medio de carácter / altura


def hoja_bbox(doc):
    """Caja del marco (capa X-FRAME) en unidades del dibujo.

    Las hojas a escala real (1 u = 1 m de obra) se dibujan ``escala`` veces más
    grandes que el A2 de papel; el marco da el tamaño real de la hoja, así el
    gate sigue midiendo "fuera de hoja" y las tolerancias en metros de papel.
    """
    ents = [e for e in doc.modelspace() if e.dxf.layer == "X-FRAME"]
    if ents:
        try:
            bb = ezbbox.extents(ents)
        except Exception:                            # noqa: BLE001
            bb = None
        if bb and bb.has_data and bb.extmax.x > bb.extmin.x:
            return bb.extmin.x, bb.extmin.y, bb.extmax.x, bb.extmax.y
    return 0.0, 0.0, ANCHO, ALTO


def caja_texto(e):
    """Caja (x0, y0, x1, y1) de un TEXT/MTEXT en metros de papel."""
    if e.dxftype() == "TEXT":
        t = e.dxf.text or ""
        h = float(e.dxf.height or 0.0)
        al, va = e.dxf.halign, e.dxf.valign
        p = e.dxf.align_point if (al or va) else e.dxf.insert
        x, y = float(p.x), float(p.y)
        w = len(t) * h * CRITERIO
        rot = float(e.dxf.rotation or 0.0) % 360.0
        if 89.0 < rot < 91.0:            # vertical ascendente
            return (x - h, y, x, y + w)
        if 269.0 < rot < 271.0:          # vertical descendente
            return (x, y - w, x + h, y)
        if 179.0 < rot < 181.0:          # cabeza abajo
            return (x - w, y - h, x, y)
        x0 = {0: x, 1: x - w / 2, 2: x - w}.get(al, x)
        y0 = {0: y - h * 0.26, 1: y, 2: y - h / 2, 3: y - h}.get(va, y - h * 0.26)
        return (x0, y0, x0 + w, y0 + h)

    # MTEXT
    filas = (e.plain_text() or "").splitlines() or [""]
    h = float(e.dxf.char_height or 0.0)
    p = e.dxf.insert
    x, y = float(p.x), float(p.y)
    w = max(len(f) for f in filas) * h * CRITERIO
    hh = h * (1.0 + 1.2 * (len(filas) - 1))
    ap = int(e.dxf.attachment_point or 1)
    fila, col = divmod(ap - 1, 3)          # 0 arriba, 1 medio, 2 abajo
    y0 = {0: y - hh, 1: y - hh / 2, 2: y}[fila]
    x0 = {0: x, 1: x - w / 2, 2: x - w}[col]
    return (x0, y0, x0 + w, y0 + hh)


def solapes(textos, k: float = 1.0):
    out = []
    for i in range(len(textos)):
        ta, ca = textos[i]
        for j in range(i + 1, len(textos)):
            tb, cb = textos[j]
            ix = min(ca[2], cb[2]) - max(ca[0], cb[0])
            iy = min(ca[3], cb[3]) - max(ca[1], cb[1])
            if ix > MIN_IX * k and iy > MIN_IY * k:
                out.append((ta[:30], [round(v, 3) for v in ca],
                            tb[:30], [round(v, 3) for v in cb],
                            round(ix, 4), round(iy, 4)))
    return out


def qa(ruta: Path) -> dict:
    doc = ezdxf.readfile(ruta)
    audit = doc.audit()
    msp = doc.modelspace()

    textos = []
    for e in msp:
        if e.dxftype() in ("TEXT", "MTEXT"):
            try:
                t = e.dxf.text if e.dxftype() == "TEXT" else e.plain_text()
                textos.append((t or "", caja_texto(e)))
            except Exception:                       # noqa: BLE001
                continue

    fx0, fy0, fx1, fy1 = hoja_bbox(doc)
    k = max(1.0, round((fx1 - fx0) / ANCHO, 6))
    tol = 1e-6 * k
    fuera = []
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
            fuera.append((e.dxftype(), e.dxf.layer,
                          round(x0, 3), round(y0, 3), round(x1, 3), round(y1, 3)))

    rep = {
        "lamina": ruta.name,
        "entidades": len(msp),
        "textos": len(textos),
        "fuera_de_hoja": fuera,
        "solapes_texto": solapes(textos, k),
        "audit_errores": len(audit.errors),
        "audit_correcciones": len(audit.fixes),
    }
    rep["ok"] = (not fuera and not rep["solapes_texto"]
                 and not rep["audit_errores"])
    return rep


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="QA de láminas DXF (A2, metros)")
    ap.add_argument("rutas", nargs="*", help="archivos DXF")
    ap.add_argument("--all", metavar="DIR", help="todas las L*.dxf de DIR")
    ap.add_argument("--json", metavar="SALIDA", help="escribir el resumen JSON")
    ap.add_argument("--verbose", "-v", action="store_true",
                    help="listar todos los hallazgos (por defecto 12)")
    args = ap.parse_args(argv)

    rutas = [Path(r) for r in args.rutas]
    if args.all:
        rutas += sorted(Path(args.all).glob("L*.dxf"))
    if not rutas:
        ap.error("indicá archivos o --all DIR")

    informes, fallas = [], 0
    for ruta in rutas:
        try:
            rep = qa(ruta)
        except Exception as exc:                    # noqa: BLE001
            print(f"{ruta.name}: ERROR {type(exc).__name__}: {exc}")
            fallas += 1
            continue
        informes.append(rep)
        print(f"{ruta.name:9s} ent={rep['entidades']:4d} txt={rep['textos']:4d} "
              f"fuera={len(rep['fuera_de_hoja']):2d} "
              f"solapes={len(rep['solapes_texto']):2d} "
              f"audit={rep['audit_errores']}/{rep['audit_correcciones']}  "
              f"{'OK' if rep['ok'] else 'FALLA'}")
        if not rep["ok"]:
            fallas += 1
            tope = None if args.verbose else 12
            for f in rep["fuera_de_hoja"][:tope]:
                print(f"    fuera  {f}")
            for s in rep["solapes_texto"][:tope]:
                print(f"    solape {s}")

    if args.json:
        Path(args.json).write_text(json.dumps(informes, ensure_ascii=False,
                                              indent=1), encoding="utf-8")
        print(f"\nresumen: {args.json}")

    print(f"\n{len(informes) - fallas}/{len(informes)} láminas OK")
    return 1 if fallas else 0


if __name__ == "__main__":
    sys.exit(main())
