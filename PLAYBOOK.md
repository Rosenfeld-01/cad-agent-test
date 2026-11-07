# PLAYBOOK — method for agent-assisted housing plans with CADCraft

Technical memory for the pipeline. It records what works, what broke, and how to
avoid paying for the same mistake twice. It is not a user README.

## 1. What this repository produces

- **Level 1:** one housing floor plan from a JSON spec → DXF + report, plus
  PNG/DWG/PDF when `cadcraft-cli` is available.
- **Level 2:** a set of A2 sheets built with the reusable toolkit
  (`sheet_lib.py`, `CAD_Blocks/`) and verified by the gates. Level 2 is not a
  generic generator yet: each project composes its own `sheets.py`.

The source of truth is always the spec. The DXF is generated.

## 2. Pipeline

```
brief.json
   +
typologies/<id>.json
   +
typologies/seeds/<seed>.json
   +
caba_rules.json
        │
        ▼
  new_case.py  →  cases/<slug>/spec.json
        │
        ▼
  validate_spec.py  →  plan.py  →  check.py  →  report ok
        │
        ▼
  Level 1: DXF + PNG/DWG + report
        │
        ├── client approval
        ▼
  Level 2: sheets.py + qa_sheets.py + qa_geometry.py + qa_walls.py
```

## 3. The three pieces

| Piece | What it is | Changes per project |
|---|---|---|
| **Brief** (`briefs/`) | What the client asks for: lot, program, target, constraints. | Yes, always. |
| **Typology** (`typologies/`) | A solution that already worked: layout, program, defaults, seed spec. | No; reuse or add a new one. |
| **Case** (`cases/`) | The concrete project: brief, spec, decisions, metrics, outputs. | Yes; it is the project record. |

The seed is explicit and auditable. The agent reads a spec that already passed
the validator and adapts it. This is not model fine-tuning or memory.

## 4. Commands

```bash
# Validate and generate the seed
python3 tools/validate_spec.py typologies/seeds/house_8.66x20.json
./run.sh typologies/seeds/house_8.66x20.json out/seed

# Create a case
cp briefs/_template.json briefs/<slug>.json
python3 tools/new_case.py \
  --brief briefs/<slug>.json \
  --typology typologies/house_between_party_walls_8.66x20.json \
  --slug <slug>
python3 tools/validate_spec.py cases/<slug>/spec.json
./run.sh cases/<slug>/spec.json out/<slug>

# Level 2 gates
python3 tools/qa_sheets.py out/L06.dxf
python3 tools/qa_sheets.py --all out --json out/_qa.json --verbose
python3 tools/qa_geometry.py --all out --verbose
python3 tools/qa_walls.py --all out

# Render (optional)
for f in out/L*.dxf; do cadcraft-cli convert "$f" "${f%.dxf}.png"; done

# Cost
python3 tools/usage.py --project cad-agent
python3 tools/usage.py --project cad-agent --max-cost 1.00 --max-calls 1500
```

`plan.py`, `check.py`, and the gates return exit code 1 on failure. A chained
`status=0` is the definition of "delivery closed".

## 5. Hard conventions

1. **Model space is the sheet.** No layouts or paper space. A2 = 0.594 × 0.420
   m of paper. If something leaves `0..0.594 / 0..0.420`, it is an error.
2. **Everything goes through `Tr`.** `Tr(x0, y0, scale)` converts project meters
   to paper meters. Do not hand-calculate paper coordinates except when
   composing the sheet.
3. **Use `CAPAS` layers** (`A-WALL`, `A-DOOR`, `A-WIN`, `A-AREA`, `A-ANNO`,
   `A-DIM`, `A-AXIS`, `A-MOB`, `A-HATCH`, `A-ESC`, `X-FRAME`, `I-ELE`, `I-SAN`,
   `I-GAS`). Add new layers to `CAPAS`, never invent them inside a sheet.
4. **Paper text heights:** 0.0046 title block · 0.0032 sheet title · 0.0022
   block titles / dimensions / levels · 0.0016–0.0019 notes and descriptions.
5. **Blocks are 1:1 in meters** (`CAD_Blocks/`). Insert with
   `poner(lam, name, tr, x, y, rot)`; `poner` resolves the scale. Use
   `caja_rotada` before placing text near a block.
6. **No eyeballed text on the drawing.** Every note/table/legend returns its
   final Y (`nota`, `tabla`) so the next element can be chained.
7. **No new dependencies:** `ezdxf` + stdlib. CADCraft only for PNG/DWG.

## 6. Quality gates

| Gate | Command | What it detects | Cost |
|---|---|---|---|
| **Spec** | `check.py <dxf> <spec.json>` | rooms, areas, openings, minimum sides | 1 s |
| **Build** | `plan.py` / `sheets.py` | Python exception, sheet not generated | seconds |
| **Sheet** | `tools/qa_sheets.py` | overlapping text, geometry outside sheet, invalid DXF | ~1.5 s / 13 sheets |
| **Geometry** | `tools/qa_geometry.py` | duplicate lines, overlapping blocks, furniture in door swing | ~2 s / 13 sheets |
| **Walls** | `tools/qa_walls.py` | overlapping `A-WALL` polygons | ~1 s / plan sheet |
| **Eye** | PNG + `render window=` | composition, density, what no script sees | 2–4k tokens / image |

`qa_sheets.py` details:

- TEXT/MTEXT bbox width = `0.62 × height × character count`, respecting
  0/90/180/270 rotations;
- overlap = intersection > **0.4 mm × 0.5 mm** (below that is normal contact
  between a dimension and its text);
- out of sheet: bbox of **any** entity against `0..0.594 / 0..0.420` using
  `ezdxf.bbox.extents`;
- audit: `doc.audit()` → errors and fixes must be `0/0`.

`qa_geometry.py` details:

- **coincident:** two LINEs on the same layer, collinear and overlapping more
  than **1 mm** of paper. Cure with `Lamina.ln_unica()`;
- **blocks:** INSERTs whose boxes overlap more than **5%** of the smaller area,
  except **containment** (a fixture inside a counter, a meter inside a niche);
- **circulation:** a block that invades more than **25%** of a door swing box
  (`A-DOOR` layer).

**Never** trust "0 overlaps / 0 outside / 0 coincident" without testing the gate
against a deliberately broken DXF:

```bash
python3 tests/make_broken_dxf.py
python3 tools/qa_sheets.py tests/_broken.dxf      # must report 1 overlap + 1 outside
python3 tools/qa_geometry.py tests/_broken.dxf    # must report 1 coincident + 1 block
```

The self-test is `bash tests/test_gates.sh`.

## 7. Low-cost protocol

Most of the cost is not drawing: it is **re-reading the same context** and
**retrying shell commands**.

| # | Rule | Why |
|---|---|---|
| 0 | **Index before file.** Before opening a large file: `grep -n '^def '`, `grep -n '^##'`. | ~20k tokens per full read vs. ~1.5k for an index. |
| 1 | **Batch edits.** All independent edits in one response. | Every round trip pays for the whole context. |
| 2 | **Partial build.** Build only the sheet being edited. | Full set = seconds, but the loop should be one sheet. |
| 3 | **Gate before eye.** Run `qa_sheets.py`/`check.py` first; render only if the gate passes and something looks odd. | A gate is ~60 output tokens; an image is 2–4k. |
| 4 | **Cropped render** (`window`) and width ≤ 1200 px. | A full A2 PNG is unreadable. |
| 5 | **Never `cat` a whole file.** Redirect to `/tmp/x.txt` and read a range, or use `grep`/`tail`. | Full dumps are the biggest token sink. |
| 6 | **Scripts in `tools/`, not `/tmp`.** | `/tmp` is lost and rewritten, paying twice. |
| 7 | **Boxes before lines.** Reserve the sheet grid first. | Prevents most overlaps. |
| 8 | **Close each round with 5 lines** in this playbook. | Avoids re-deriving the same lesson. |
| 9 | **Do not re-export all PNGs** when one sheet changed. | Convert only what changed. |
| 10 | **One `bash -c '...'` per command block.** | The user's shell may be fish; bash syntax breaks. |

If a sheet takes more than ~15 calls, you are probably composing by eye instead
of reserving boxes first. Stop and redesign the grid.

## 8. Known defects (generic lessons)

### 8.1 A gate that lies

- **Symptom:** 13/13 sheets "OK" while a scale bar is 5 mm outside the sheet.
- **Cause:** `BoundingBox2d([entity])` does not accept entities in ezdxf 1.4.5;
  it raises `TypeError`. A broad `try/except: continue` swallowed the error and
  left the "outside sheet" list empty for every entity.
- **Fix:** `from ezdxf import bbox` → `bbox.extents([e])` (returns `Vec3`; use
  `.extmin.x`, `.extmax.y`).
- **Lesson:** test every gate against a deliberately broken DXF.

### 8.2 Scale bar outside the sheet

- **Cause:** at 1:25, the default scale-bar segments `(0,1,2,5)` produce a
  0.20 m paper bar; starting at 0.380 ends at 0.580 and the label leaves the
  frame.
- **Fix:** at 1:25 use `segments=(0, 1, 2)` → 0.08 m bar. Rule: bar width in
  paper (`segments[-1]/scale`) + 0.02 must fit the free column.

### 8.3 Section mark over the dimension chain

- **Cause:** `section_mark` extended the cut line 0.60 m into the drawing, right
  where the dimension chain runs.
- **Fix:** asymmetric extension `ext=(0.05, 0.60)` in plan and `(0.05, 0.90)` in
  roof plans: short tail on the dimension side.

### 8.4 Facades without levels

- **Cause:** `facade()` does not draw level marks; they were added per sheet.
- **Fix:** `levels_view(lam, tr, 6.60)` — one call, four levels, aligned to the
  right edge of the view.

### 8.5 Rear facade hidden by the kitchen roof

- **Cause:** the ground-floor kitchen roof (+2.95) sits in front of the facade
  plane.
- **Fix:** `facade(..., hidden_z=LEVELS["KITCHEN_ROOF"] + 0.35)` so the elevation
  clips the hidden part and draws the roof as a dashed/see-through line.

### 8.6 Composition errors

- **Table over the note below:** use the Y returned by `tabla()`; never
  recalculate `row_height * len(rows)` by hand (the header has a different
  height).
- **90° rotated text:** width and height swap; manual boxes underestimate width
  and produce overlaps.
- **"Harmless" text:** 0.0016 vs 0.0022 touch and read badly. The gate tolerates
  0.4 × 0.5 mm of intersection; more is a real defect.
- **Density:** above ~560 entities per sheet, split the sheet or reduce detail.

### 8.7 Water networks drawn on the floor and all one color

- **Symptom:** in the plumbing sheet, cold and hot water run through the middle
  of rooms, cross each other and the sewer, all on `I-SAN`.
- **Fix:** four layers with their own color in `CAPAS`: `I-AF` (blue 5), `I-AC`
  (red 1), `I-CL` (green 3), `I-PL` (yellow 2), lineweight 30–35. Cold and hot
  water are embedded in walls at ±0.05 m from the wall axis; sewer runs below
  the slab; stormwater runs on facade wall axes. Fixtures use their network
  layer (`CAPA_SIM`).

### 8.8 Tank only in the roof plan

- **Symptom:** the roof plan shows the 1,000 L tank; sections and facades show
  an empty kitchen roof.
- **Fix:** two helpers in `sheet_lib`: `tank_support()` (platform, pedestals,
  body, lid, vent, downpipe) and `tank_plan()` (plan with platform, lid,
  downpipe), used in roof plan, section, and facades. One level, one definition:
  `LEVELS["KITCHEN_ROOF_TOP"]`.
- **Mirror warning:** in views with `mirror=True`, pass `s0, s1` already
  reflected (`s' = L − s`) because `tank_support` calls `tr()` directly.

### 8.9 Blocks blocking circulation and stacked symbols

- **Symptom:** washing machine blocks the laundry door (37% of swing), bedroom
  closet blocks the storage door (75%), and electrical symbols overlap up to
  100%.
- **Fix:** `qa_geometry.py` measures both; relocate furniture and separate
  symbols by ≥ 0.25–0.30 m (the real block bbox is larger than its nominal
  size).
- **Rule:** a fixture may be **inside** a counter (containment), never
  **invading** a door swing.

### 8.10 Incomplete roof plan

- **Symptom:** kitchen roof appears as a single line; no dimensions, access
  hatch, stormwater connection, or tank platform.
- **Fix:** define the sector with three synthetic walls (`T-WEST`, `T-EAST`,
  `T-BACK`) to close the slab perimeter; add dimensions, a 0.60 × 0.60 access
  hatch, an edge gutter with 3 downpipes on `I-PL`, and a 1:20 tank-platform
  detail.
- **Lesson:** when filtering geometry with `min()/max()` over wall lists, verify
  the entity count per layer; a filter returning 1 wall instead of 3 is easy to
  miss in a small PNG.

## 9. Adding a case, typology, or rule

### New case

1. Write the brief in `briefs/<slug>.json`.
2. `python3 tools/new_case.py --brief briefs/<slug>.json --slug <slug>`.
3. Adapt `cases/<slug>/spec.json`; run `validate_spec.py` and `run.sh`.
4. With `ok: true`, update `case.json` and `decisions.md`.
5. Record the cost.

### New typology

1. Start from a case that passed `check.py` with `ok: true`.
2. Copy its spec to a seed file.
3. Create `typologies/<id>.json` with `lot`, `layout`, `floors`, `program`,
   `seed_rooms`, `defaults`, `seed`, `rules`, `outputs`, `notes`.
4. Verify that `new_case.py --typology ...` creates a runnable case.
5. Note in `notes` what is reused and what must change.

### New rule

1. Add the minimum to `caba_rules.json` with source and disclaimer.
2. If the rule needs new geometry, add it to `check.py` (ask first: protected
   file).
3. Add the equivalent cheap check to `validate_spec.py` when possible.
4. Test with a spec that violates the rule and one that complies.

## 10. Delivery checklist

- [ ] `validate_spec.py` with no errors.
- [ ] `run.sh` with `ok: true` and 0 errors.
- [ ] Level 2: `qa_sheets.py` and `qa_geometry.py` green; `qa_walls.py` overlap
      0.00 m² on plan sheets.
- [ ] Gate self-test passes: `bash tests/test_gates.sh`.
- [ ] ezdxf audit `0/0` on every sheet.
- [ ] No text overlaps beyond 0.4 × 0.5 mm.
- [ ] Nothing outside `0..0.594 × 0..0.420`.
- [ ] Title block complete: client, project, scale, date, sheet number/total.
- [ ] Section references consistent between plans and sections.
- [ ] Levels equal in all views.
- [ ] `case.json` updated and `decisions.md` written.
- [ ] Cost measured or declared unavailable.

## 11. What is scalable and what is not

### Yes

- Single-family houses between party walls or on a corner.
- One or two floors with a residential program.
- Reusing layouts, dimensions, blocks, and lessons.
- Deterministic habitability validation.
- Cost measurement per project.

### Not yet

- **Apartment buildings:** `plan.py` handles one floor; cores, stairs,
  evacuation, party walls, and repeated units are missing.
- **Structure:** no structural plan or load report.
- **Calculated services:** isometrics are conceptual; no flow rates, diameters,
  slopes, or conductor sizing.
- **FOS/FOT/setbacks:** declared, not verified against the Urban Code.
- **Generic Level 2:** `sheet_lib.py` is a toolkit; each project still composes
  its own sheet generator.
- **Professional signature:** the system does not sign or submit.
