#!/usr/bin/env python3
"""Gate de geometría: líneas superpuestas y bloques que se pisan.

    python3 tools/qa_geometria.py out/L01.dxf
    python3 tools/qa_geometria.py --all out
    python3 tools/qa_geometria.py --all out --verbose --json out/_geo.json

Detecta tres cosas que `qa_laminas.py` no mira:

1. **Coincidentes**: dos LINE del mismo layer colineales que se solapan más de
   `TOL` metros de papel ("dibujé el mismo caño/trazo dos veces").
2. **Bloques superpuestos**: INSERT cuyas cajas se pisan más de `FRAC` (5%) del
   área del menor. En planta, un artefacto que invade otro.
3. **Circulación**: bloques que pisan el barrido de una puerta (capa A-DOOR).

Código de salida 1 si hay cualquier hallazgo (sirve como gate).
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import ezdxf
from ezdxf import bbox as ezbbox

TOL = 0.001          # 1 mm de papel: por debajo se considera el mismo trazo
FRAC = 0.05          # 5% del área del bloque menor


def _escala_hoja(doc) -> float:
    """Factor de escala real de la hoja (1 = papel, 50 = 1:1 real).

    Sale del ancho del marco X-FRAME: las hojas a escala real son ``escala``
    veces más grandes que el A2 de papel, así las tolerancias se mantienen en
    metros de papel (1 mm de trazo) sin cambiar el criterio.
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


def _seg(e):
    """Segmento normalizado (x0, y0, x1, y1)."""
    s, t = e.dxf.start, e.dxf.end
    p, q = (s.x, s.y), (t.x, t.y)
    return (p[0], p[1], q[0], q[1]) if (p[0], p[1]) <= (q[0], q[1]) else \
           (q[0], q[1], p[0], p[1])



def coincidentes(msp, tol: float = TOL):
    """Líneas colineales del mismo layer que se solapan más de ``tol``."""
    grupos = {}
    for e in msp.query("LINE"):
        x0, y0, x1, y1 = _seg(e)
        dx, dy = x1 - x0, y1 - y0
        largo = math.hypot(dx, dy)
        if largo < tol:
            continue
        ang = round(math.degrees(math.atan2(dy, dx)) % 180.0, 2)
        d = abs(-dy * x0 + dx * y0) / largo        # distancia al origen
        grupos.setdefault((e.dxf.layer, ang, round(d, 4)), []).append(
            (x0, y0, x1, y1, e))

    hallazgos = []
    for (_capa, _ang, _d), items in grupos.items():
        if len(items) < 2:
            continue
        x0, y0, x1, y1, _e = items[0]
        ux, uy = x1 - x0, y1 - y0
        n = math.hypot(ux, uy)
        ux, uy = ux / n, uy / n
        proy = []
        for it in items:
            a, b = it[0] * ux + it[1] * uy, it[2] * ux + it[3] * uy
            proy.append((min(a, b), max(a, b), it))
        proy.sort(key=lambda z: (z[0], z[1]))
        for i in range(len(proy) - 1):
            a0, a1, it0 = proy[i]
            b0, b1, it1 = proy[i + 1]
            solape = min(a1, b1) - max(a0, b0)
            if solape > tol:
                hallazgos.append((
                    round(solape, 4),
                    tuple(round(v, 3) for v in it0[:4]),
                    tuple(round(v, 3) for v in it1[:4]),
                    it0[4].dxf.layer))

    return hallazgos


def _area(c):
    return max(0.0, c[2] - c[0]) * max(0.0, c[3] - c[1])


def _inter(a, b):
    return (max(a[0], b[0]), max(a[1], b[1]), min(a[2], b[2]), min(a[3], b[3]))


def _dentro(a, b, tol=0.003):
    """True si la caja `a` está contenida en `b` (un artefacto en la mesada).

    Se toleran 3 mm de papel: el bbox real del bloque puede exceder levemente
    la caja nominal usada para insertarlo (líneas de canto, sombras).
    """
    return (b[0] - tol <= a[0] and b[1] - tol <= a[1]
            and a[2] <= b[2] + tol and a[3] <= b[3] + tol)


def bloques(msp, tol_cont: float = 0.003):
    """Pares de INSERT cuyas cajas se pisan más de FRAC del área menor.

    La contención (un artefacto dentro de la mesada, el medidor dentro del
    nicho) no se informa: es una relación de diseño válida.
    """
    items = []
    for e in msp.query("INSERT"):
        c = _bbox(e)
        if c is None:
            continue
        items.append((c, e.dxf.name,
                      (round(e.dxf.insert.x, 3), round(e.dxf.insert.y, 3))))
    items.sort(key=lambda z: z[0][0])
    hallazgos = []
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
            if _dentro(ca, cb, tol_cont) or _dentro(cb, ca, tol_cont):
                continue
            hallazgos.append((round(frac, 3), na, pa, nb, pb))
    return hallazgos


def circulacion(msp):
    """Bloques que pisan el barrido de una puerta (capa A-DOOR)."""
    puertas = []
    for e in msp.query("ARC"):
        if e.dxf.layer != "A-DOOR":
            continue
        c = _bbox(e)
        if c:
            puertas.append(c)
    hallazgos = []
    for e in msp.query("INSERT"):
        c = _bbox(e)
        if c is None:
            continue
        for pd in puertas:
            ai = _area(_inter(c, pd))
            if ai <= 0:
                continue
            frac = ai / max(1e-12, _area(pd))
            if frac > 0.25:
                hallazgos.append((round(frac, 3), e.dxf.name,
                                  (round(e.dxf.insert.x, 3),
                                   round(e.dxf.insert.y, 3))))
                break
    return hallazgos


def analizar(ruta: Path) -> dict:
    doc = ezdxf.readfile(ruta)
    msp = doc.modelspace()
    k = _escala_hoja(doc)
    return {
        "lamina": ruta.name,
        "entidades": len(msp),
        "coincidentes": sorted(coincidentes(msp, TOL * k), key=lambda z: -z[0]),
        "bloques": sorted(bloques(msp, 0.003 * k), key=lambda z: -z[0]),
        "circulacion": sorted(circulacion(msp), key=lambda z: -z[0]),
    }


def main(argv) -> int:
    verbose = "--verbose" in argv or "-v" in argv
    ruta_json = None
    if "--json" in argv:
        i = argv.index("--json")
        if i + 1 < len(argv):
            ruta_json = Path(argv[i + 1])
            argv = [a for j, a in enumerate(argv) if j != i + 1]

    if "--all" in argv:
        i = argv.index("--all")
        base = Path(argv[i + 1]) if i + 1 < len(argv) else Path("out")
        if not base.is_dir():
            base = Path("out")
        rutas = sorted(base.glob("L*.dxf"))
    else:
        rutas = [Path(a) for a in argv[1:] if a.lower().endswith(".dxf")]
    if not rutas:
        print("uso: qa_geometria.py [--all DIR] [--verbose] [--json ruta] *.[dxf]")
        return 2

    reportes, fallas = [], 0
    for ruta in rutas:
        try:
            r = analizar(ruta)
        except Exception as exc:                        # noqa: BLE001
            print(f"{ruta.name}: ERROR {type(exc).__name__}: {exc}")
            fallas += 1
            continue
        reportes.append(r)
        nc = len(r["coincidentes"])
        nb = len(r["bloques"])
        nci = len(r["circulacion"])
        estado = "OK" if nc + nb + nci == 0 else "REVISAR"
        print(f"{ruta.name:10s} ent={r['entidades']:5d}  coincidentes={nc:3d}"
              f"  bloques={nb:3d}  circulacion={nci:3d}  {estado}")
        if verbose:
            for solape, a, b, capa in r["coincidentes"][:40]:
                print(f"    coinc {capa:8s} {solape:7.4f} m  {a} vs {b}")
            for frac, na, pa, nb_, pb in r["bloques"][:40]:
                print(f"    blq  {na}@{pa} pisa {nb_}@{pb}  ({frac:.0%})")
            for frac, na, pa in r["circulacion"][:40]:
                print(f"    circ {na}@{pa} invade barrido de puerta ({frac:.0%})")
        if nc + nb + nci:
            fallas += 1

    if ruta_json:
        ruta_json.write_text(json.dumps(reportes, indent=1, ensure_ascii=False),
                             encoding="utf-8")
        print(f"\nreporte: {ruta_json}")
    print(f"\n{len(reportes) - fallas}/{len(reportes)} láminas limpias")
    return 1 if fallas else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))

