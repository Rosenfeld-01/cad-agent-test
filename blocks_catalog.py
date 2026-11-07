#!/usr/bin/env python3
"""
blocks_catalog.py — lámina índice de la biblioteca CAD_Blocks (Fase 1).

Genera CAD_Blocks/catalogo.dxf (A0, metros de papel) con todos los bloques en
grilla, su nombre, medidas y la escala a la que está dibujado cada uno.
Después se exporta a PNG con cadcraft-cli.
"""
from __future__ import annotations

import subprocess
from pathlib import Path

import ezdxf
from ezdxf import bbox

import blocks_build as BB
import blocks_data_arquitectura as DA
import blocks_data_bano_exterior as DB
import blocks_data_instalaciones as DI

BASE = Path(__file__).resolve().parent
DESTINO = BASE / "CAD_Blocks"

ANCHO, ALTO = 1.189, 0.841      # A0 en metros de papel
COLUMNAS = 7
MARGEN = 0.020
TITULO_H = 0.055


def main() -> int:
    items = sorted(DA.BLOQUES + DB.BLOQUES + DI.BLOQUES,
                   key=lambda x: (x["cat"], x["nombre"]))
    doc = ezdxf.new("R2013", setup=True)
    doc.units = ezdxf.units.M
    doc.header["$INSUNITS"] = 6
    msp = doc.modelspace()
    for capa, color in (("0", 7), ("X-FRAME", 7), ("A-ANNO", 7), ("A-MOB", 30)):
        if capa != "0":
            doc.layers.add(capa, color=color)

    # definiciones de bloque
    for it in items:
        blk = doc.blocks.new(it["nombre"])
        BB.dibujar(blk, it)

    # marco y título
    msp.add_lwpolyline([(0, 0), (ANCHO, 0), (ANCHO, ALTO), (0, ALTO)], close=True,
                       dxfattribs={"layer": "X-FRAME"})
    msp.add_text("BIBLIOTECA DE BLOQUES - VIVIENDA 02", height=0.010,
                 dxfattribs={"layer": "A-ANNO"}).set_placement((MARGEN, ALTO - 0.030))
    msp.add_text(f"{len(items)} bloques - metros 1:1 - punto de inserción (0,0) - "
                 "escala de lámina = escala/1000", height=0.0045,
                 dxfattribs={"layer": "A-ANNO"}).set_placement((MARGEN, ALTO - 0.045))

    util_alto = ALTO - TITULO_H - MARGEN
    filas = -(-len(items) // COLUMNAS)
    cw = (ANCHO - 2 * MARGEN) / COLUMNAS
    ch = util_alto / filas

    for i, it in enumerate(items):
        fil, col = divmod(i, COLUMNAS)
        x0 = MARGEN + col * cw
        y0 = ALTO - TITULO_H - (fil + 1) * ch
        # recuadro de la celda
        msp.add_lwpolyline([(x0, y0), (x0 + cw, y0), (x0 + cw, y0 + ch), (x0, y0 + ch)],
                           close=True, dxfattribs={"layer": "X-FRAME"})
        # encuadre por la caja real del bloque (no por las medidas declaradas)
        caja = bbox.extents(list(doc.blocks.get(it["nombre"])))
        if caja.has_data:
            bw, bh = caja.size.x or 0.1, caja.size.y or 0.1
            bx, by = (caja.extmin.x + caja.extmax.x) / 2, (caja.extmin.y + caja.extmax.y) / 2
        else:
            bw, bh, bx, by = it["w"], it["h"], it["w"] / 2, it["h"] / 2
        f = min((cw * 0.78) / bw, (ch * 0.66) / bh)
        msp.add_blockref(it["nombre"],
                         (x0 + cw / 2 - f * bx, y0 + ch * 0.52 - f * by),
                         dxfattribs={"xscale": f, "yscale": f})
        msp.add_text(it["nombre"], height=0.0036,
                     dxfattribs={"layer": "A-ANNO"}).set_placement(
            (x0 + cw / 2, y0 + 0.0135),
            align=ezdxf.enums.TextEntityAlignment.MIDDLE_CENTER)
        msp.add_text(f"{it['w']:.2f} x {it['h']:.2f} m   (1:{round(1 / f)})",
                     height=0.0024, dxfattribs={"layer": "A-ANNO"}).set_placement(
            (x0 + cw / 2, y0 + 0.0055),
            align=ezdxf.enums.TextEntityAlignment.MIDDLE_CENTER)

    dxf = DESTINO / "catalogo.dxf"
    doc.saveas(dxf)
    png = DESTINO / "catalogo.png"
    subprocess.run(["cadcraft-cli", "convert", str(dxf), str(png)],
                   capture_output=True, text=True)
    print(f"OK catalogo: {dxf.name} / {png.name} ({png.stat().st_size if png.exists() else 0} B)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
