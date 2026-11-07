#!/usr/bin/env python3
"""
blocks_catalog.py — index sheet for the CAD_Blocks library.

Builds CAD_Blocks/catalog.dxf (A0, paper meters) with all blocks in a grid,
their name, dimensions, and the scale each one is drawn at. It is then exported
to PNG with cadcraft-cli.
"""
from __future__ import annotations

import subprocess
from pathlib import Path

import ezdxf
from ezdxf import bbox

import blocks_build as BB
import blocks_data_architecture as DA
import blocks_data_bathroom_exterior as DB
import blocks_data_services as DI

BASE = Path(__file__).resolve().parent
DESTINATION = BASE / "CAD_Blocks"

WIDTH, HEIGHT = 1.189, 0.841      # A0 in paper meters
COLUMNS = 7
MARGIN = 0.020
TITLE_H = 0.055


def main() -> int:
    items = sorted(DA.BLOCKS + DB.BLOCKS + DI.BLOCKS,
                   key=lambda x: (x["category"], x["name"]))
    doc = ezdxf.new("R2013", setup=True)
    doc.units = ezdxf.units.M
    doc.header["$INSUNITS"] = 6
    msp = doc.modelspace()
    for layer, color in (("0", 7), ("X-FRAME", 7), ("A-ANNO", 7), ("A-MOB", 30)):
        if layer != "0":
            doc.layers.add(layer, color=color)

    # block definitions
    for it in items:
        blk = doc.blocks.new(it["name"])
        BB.draw(blk, it)

    # frame and title
    msp.add_lwpolyline([(0, 0), (WIDTH, 0), (WIDTH, HEIGHT), (0, HEIGHT)], close=True,
                       dxfattribs={"layer": "X-FRAME"})
    msp.add_text("CAD_Blocks LIBRARY - HOUSING", height=0.010,
                 dxfattribs={"layer": "A-ANNO"}).set_placement((MARGIN, HEIGHT - 0.030))
    msp.add_text(f"{len(items)} blocks - 1:1 meters - insertion point (0,0) - "
                 "sheet scale = scale/1000", height=0.0045,
                 dxfattribs={"layer": "A-ANNO"}).set_placement((MARGIN, HEIGHT - 0.045))

    usable_height = HEIGHT - TITLE_H - MARGIN
    rows = -(-len(items) // COLUMNS)
    cw = (WIDTH - 2 * MARGIN) / COLUMNS
    ch = usable_height / rows

    for i, it in enumerate(items):
        row, col = divmod(i, COLUMNS)
        x0 = MARGIN + col * cw
        y0 = HEIGHT - TITLE_H - (row + 1) * ch
        # cell frame
        msp.add_lwpolyline([(x0, y0), (x0 + cw, y0), (x0 + cw, y0 + ch), (x0, y0 + ch)],
                           close=True, dxfattribs={"layer": "X-FRAME"})
        # fit to the real block box (not the declared dimensions)
        box = bbox.extents(list(doc.blocks.get(it["name"])))
        if box.has_data:
            bw, bh = box.size.x or 0.1, box.size.y or 0.1
            bx, by = (box.extmin.x + box.extmax.x) / 2, (box.extmin.y + box.extmax.y) / 2
        else:
            bw, bh, bx, by = it["w"], it["h"], it["w"] / 2, it["h"] / 2
        f = min((cw * 0.78) / bw, (ch * 0.66) / bh)
        msp.add_blockref(it["name"],
                         (x0 + cw / 2 - f * bx, y0 + ch * 0.52 - f * by),
                         dxfattribs={"xscale": f, "yscale": f})
        msp.add_text(it["name"], height=0.0036,
                     dxfattribs={"layer": "A-ANNO"}).set_placement(
            (x0 + cw / 2, y0 + 0.0135),
            align=ezdxf.enums.TextEntityAlignment.MIDDLE_CENTER)
        msp.add_text(f"{it['w']:.2f} x {it['h']:.2f} m   (1:{round(1 / f)})",
                     height=0.0024, dxfattribs={"layer": "A-ANNO"}).set_placement(
            (x0 + cw / 2, y0 + 0.0055),
            align=ezdxf.enums.TextEntityAlignment.MIDDLE_CENTER)

    dxf = DESTINATION / "catalog.dxf"
    doc.saveas(dxf)
    png = DESTINATION / "catalog.png"
    subprocess.run(["cadcraft-cli", "convert", str(dxf), str(png)],
                   capture_output=True, text=True)
    print(f"OK catalog: {dxf.name} / {png.name} ({png.stat().st_size if png.exists() else 0} B)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
