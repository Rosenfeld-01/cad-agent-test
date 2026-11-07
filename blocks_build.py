#!/usr/bin/env python3
"""
blocks_build.py — build the CAD_Blocks/ library.

Blocks are declared as data (an "ops" list) in the blocks_data_*.py modules, and
this file turns them into DXF.

Library convention
------------------
- One file per block: CAD_Blocks/<NAME>.dxf
- Geometry in 1:1 METERS (same as the rest of the project, $INSUNITS = 6).
- Insertion point = (0,0) = $INSBASE, with the block "facing up".
- Entities on layer 0: they inherit color and lineweight from the insertion
  layer.
- Geometry is written to MODEL SPACE (so CADCraft's INSERT command can read it
  from the file) and mirrored into a block definition with the same name (so it
  can also be inserted from ezdxf/AutoCAD).

Insertion scale on a sheet: sheet scale / 1000 (1:50 -> 0.02).

Usage:
    python3 blocks_build.py            # writes CAD_Blocks/ + index.json
"""
from __future__ import annotations

import json
import math
from pathlib import Path

import ezdxf
from ezdxf.enums import TextEntityAlignment

import blocks_data_architecture as DA
import blocks_data_bathroom_exterior as DB
import blocks_data_services as DI

BASE = Path(__file__).resolve().parent
DESTINATION = BASE / "CAD_Blocks"

ALIGNMENT = {
    "mc": TextEntityAlignment.MIDDLE_CENTER,
    "ml": TextEntityAlignment.MIDDLE_LEFT,
    "mr": TextEntityAlignment.MIDDLE_RIGHT,
    "bc": TextEntityAlignment.BOTTOM_CENTER,
    "tl": TextEntityAlignment.TOP_LEFT,
    "tr": TextEntityAlignment.TOP_RIGHT,
}


def draw(container, item: dict) -> None:
    """Draw a block's ops into a layout (model space or definition)."""
    for op in item["ops"]:
        kind = op[0]
        if kind == "ln":
            container.add_line(op[1], op[2])
        elif kind == "pl":
            container.add_lwpolyline(op[1], close=bool(op[2]) if len(op) > 2 else False)
        elif kind == "ci":
            container.add_circle(op[1], op[2])
        elif kind == "ar":
            container.add_arc(op[1], op[2], op[3], op[4])
        elif kind == "tx":
            text, point, height = op[1], op[2], op[3]
            align = ALIGNMENT[op[4] if len(op) > 4 else "mc"]
            ent = container.add_text(text, height=height)
            ent.set_placement(point, align=align)
        else:
            raise ValueError(f"unknown op {kind!r} in {item['name']}")
    for a in item.get("attrs", []):
        ad = container.add_attdef(
            a["tag"], a["at"], dxfattribs={"height": a["h"], "prompt": a.get("prompt", a["tag"])})
        if a.get("default"):
            ad.dxf.text = a["default"]
        if a.get("invisible", True):
            ad.dxf.flags = 1


def create_document(item: dict) -> ezdxf.document.Drawing:
    doc = ezdxf.new("R2013", setup=True)
    doc.units = ezdxf.units.M
    doc.header["$INSUNITS"] = 6
    doc.header["$MEASUREMENT"] = 1
    doc.header["$INSBASE"] = (0.0, 0.0, 0.0)
    msp = doc.modelspace()
    draw(msp, item)
    blk = doc.blocks.new(item["name"])
    draw(blk, item)
    return doc


def validate(items: list[dict]) -> None:
    seen = set()
    for it in items:
        name = it["name"]
        if name in seen:
            raise ValueError(f"duplicate block: {name}")
        seen.add(name)
        if len(name) > 32:
            raise ValueError(f"name too long: {name}")
        for ch in name:
            if not (ch.isalnum() or ch in "-_"):
                raise ValueError(f"invalid character in name: {name}")
        if not it.get("ops"):
            raise ValueError(f"block without geometry: {name}")
        for key in ("category", "description", "w", "h"):
            if key not in it:
                raise ValueError(f"{name}: missing key {key}")


def main() -> int:
    items = DA.BLOCKS + DB.BLOCKS + DI.BLOCKS
    validate(items)
    DESTINATION.mkdir(parents=True, exist_ok=True)
    index = []
    for it in sorted(items, key=lambda x: x["name"]):
        doc = create_document(it)
        path = DESTINATION / f"{it['name']}.dxf"
        doc.saveas(path)
        index.append({
            "block": it["name"],
            "file": path.name,
            "category": it["category"],
            "description": it["description"],
            "width_m": it["w"],
            "height_m": it["h"],
            "attributes": [a["tag"] for a in it.get("attrs", [])],
            "bytes": path.stat().st_size,
        })
    (DESTINATION / "index.json").write_text(
        json.dumps({"unit": "m", "insert_base": [0, 0],
                    "insert_scale": "sheet_scale/1000 (1:50 -> 0.02)",
                    "total": len(index), "blocks": index},
                   ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"OK  {len(index)} blocks in {DESTINATION}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
