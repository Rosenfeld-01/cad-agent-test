# 40 — Style, conventions, and cost

## Language and tone

- Respond and write comments in **English**.
- Be concrete: dimensions, files, commands. No filler.
- If something cannot be verified, say so; do not invent it.

## Project conventions

- Units: **meters** (1 unit = 1 m). `$INSUNITS = 6`.
- Layers: `A-WALL`, `A-DOOR`, `A-WIN`, `A-AREA`, `A-ANNO`, `A-DIM`, `A-AXIS`.
- Rooms: the `A-AREA` polygon carries the name in XDATA (appid `CADAGENT`).
- Minimum text height: 0.15 m (see `caba_rules.json`).
- Dimensions in meters, with two decimals.
- Keep CAD layer names, block codes, and JSON keys stable.

## Low-cost protocol (required)

Most of the cost is not drawing: it is **re-reading the same context** and
**retrying commands**. Rules:

1. **Index before file.** Before opening a large file: `grep -n '^def '`,
   `grep -n '^##'`, or the `PLAYBOOK.md` index.
2. **Batch edits.** All independent edits in one response.
3. **Partial build.** Build only the sheet being edited.
4. **Gate before eye.** Run `qa_sheets.py` / `check.py` first; render only when
   needed and crop with `window=`.
5. **Do not `cat` whole files.** Use `grep`, `tail`, or a range read.
6. **Reusable scripts in `tools/`, not `/tmp`.**
7. **Close each round with 5 lines** in `PLAYBOOK.md` when a lesson is learned.
8. **One `bash -c '...'` per command block.** The user's shell may be fish.

## Output discipline

- No `ok: true` report → no delivery.
- No invented dimensions, areas, or code values.
- No signature or submission by the agent.
