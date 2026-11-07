# 30 — CAD

## Geometric truth vs. aesthetics

- **Geometry / dimensions / rules** → `inspect_drawing`, `query_entities`,
  `find_text` (exact data) and `check.py`. This is the truth.
- **Aesthetics / legibility / "looks right"** → `render` (PNG) + vision model.
- If the render and the data disagree, **the data wins**.

## Tools

- MCP `cadcraft`: `command_line`, `script`, `execute`, `inspect_drawing`,
  `query_entities`, `find_text`, `render`, `open`, `save`, `new_drawing`,
  `cancel`, `list_commands`.
- CLI: `cadcraft-cli info | convert | run | commands | mcp`.
- Python: `ezdxf` (DXF read/write), `matplotlib`.

## CADCraft limits

- It is early-stage software: **entities it does not model are lost on save**.
  Always keep a copy of the original before overwriting.
- When opening a DWG, check the MCP `open` `warnings` and `readNotes` from
  `cadcraft-cli info`.
- After every save, verify with `cadcraft-cli info` that the entity count did not
  drop.
- Do not promise full AutoCAD fidelity. Validate the round-trip.
- Do not use screenshots as the source of geometric truth.

## Units and layers

- 1 unit = 1 m. `$INSUNITS = 6`.
- Layers: `A-WALL`, `A-DOOR`, `A-WIN`, `A-AREA`, `A-ANNO`, `A-DIM`, `A-AXIS`.
- Level 2 adds `A-MOB`, `A-HATCH`, `A-ESC`, `X-FRAME`, `I-ELE`, `I-SAN`,
  `I-GAS`, `I-AF`, `I-AC`, `I-CL`, `I-PL`.
- Minimum text height: 0.15 m. Dimensions in meters with two decimals.
