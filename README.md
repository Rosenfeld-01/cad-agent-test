# cad-agent — deterministic housing-plan pipeline for CADCraft

A deterministic pipeline that turns a **brief** into a **validated housing plan**.
The source of truth is a JSON `spec`; the DXF is **generated**, never edited by
hand.

```
brief.json ─▶ new_case.py ─▶ spec.json ─▶ validate_spec.py ─▶ plan.py ─▶ check.py ─▶ out/*.dxf
```

If something is wrong, fix the `spec` and regenerate. Editing the DXF by hand
breaks traceability and makes the validator meaningless.

- **Level 1 (cheap):** one housing floor plan → DXF + report + PNG/DWG/PDF when
  `cadcraft-cli` is available.
- **Level 2 (expensive):** a set of A2 sheets. The reusable toolkit is
  `sheet_lib.py` plus `CAD_Blocks/`; the original case-specific generator is not
  shipped here. Build a project-specific `sheets.py` from the toolkit when
  Level 2 is approved.

## Requirements

- Python 3.10+ with `ezdxf` and `matplotlib`.
- Optional: `cadcraft-cli` in `PATH` to export PNG/DWG/PDF (see
  `mcp-cline.json` / `mcp-opencode.json`).

## Quick start (Level 1)

```bash
# Validate and generate the included seed plan
python3 tools/validate_spec.py typologies/seeds/house_8.66x20.json
./run.sh typologies/seeds/house_8.66x20.json out/seed
```

The report is written to `out/seed/*.report.json`. With `"ok": true` the plan is
clean; if there are errors, fix the spec and run again (**maximum 10
iterations**; if it does not converge, stop and explain).

## Create a new case

```bash
cp briefs/_template.json briefs/<slug>.json      # complete the brief
python3 tools/new_case.py --brief briefs/<slug>.json \
  --typology typologies/house_between_party_walls_8.66x20.json --slug <slug>
python3 tools/validate_spec.py cases/<slug>/spec.json
./run.sh cases/<slug>/spec.json out/<slug>
```

`new_case.py` copies the typology seed spec and creates `brief.json`,
`case.json` (status `draft`), and `decisions.md`.

## Layout

| Path | Purpose |
|---|---|
| `plan.py` | Generate the DXF from the spec (parametric, units in meters). |
| `check.py` | Validate the DXF against the spec and `caba_rules.json`; write the report. |
| `run.sh` | Full pipeline: validate → generate → validate → PNG/DWG/PDF. |
| `caba_rules.json` | Starting values (not legal advice). |
| `docs/CABA_RULES.md` | Practice dimensions and CABA minimums. |
| `schemas/spec.schema.json` | Spec contract. |
| `tools/validate_spec.py` | Cheap spec preflight. |
| `tools/new_case.py` | Create a case from a brief + typology. |
| `tools/usage.py` | Cost, calls, and cache per project. |
| `tools/qa_sheets.py` | Level 2 gate: text overlaps, out-of-sheet geometry, DXF audit. |
| `tools/qa_geometry.py` | Level 2 gate: duplicate lines, overlapping blocks, door clearance. |
| `tools/qa_walls.py` | Wall-thickness/overlap gate for `A-WALL`. |
| `typologies/` | Reusable solutions + seed specs (`seeds/`). |
| `briefs/` | Project inputs (`_template.json`). |
| `cases/` | Concrete projects: spec, decisions, and metrics. |
| `sheet_lib.py` | Sheet primitives (frame, title block, scales, blocks) for Level 2. |
| `blocks_*.py` | Data and builder for the `CAD_Blocks/` library (used by `sheet_lib`). |
| `CAD_Blocks/` | Registered block library (furniture, fixtures, services). |
| `tests/` | Gate self-test (`make_broken_dxf.py` + `test_gates.sh`). |
| `PLAYBOOK.md` | Technical method: gates, conventions, low-cost protocol. |
| `AGENTS.md` | How the agent works. |

## Conventions

- Units: **meters** (1 unit = 1 m). `$INSUNITS = 6`.
- Layers: `A-WALL`, `A-DOOR`, `A-WIN`, `A-AREA`, `A-ANNO`, `A-DIM`, `A-AXIS`
  (Level 2 adds `A-MOB`, `A-HATCH`, `X-FRAME`, `I-ELE`, `I-SAN`, `I-GAS`).
- Minimum text height: 0.15 m. Dimensions in meters with two decimals.
- JSON spec keys and CAD layer/block codes are stable API identifiers. Documents,
  comments, messages, and folder names are in English.

## Level 2 toolkit

Level 2 is a library, not a generic generator. Use `sheet_lib.py` to compose
sheets and the gates to verify them:

```bash
python3 tools/qa_sheets.py --all out
python3 tools/qa_geometry.py --all out
python3 tools/qa_walls.py --all out        # plan sheets only
```

The original case-specific sheet generator is preserved in the larger
`cad-agent` archive, outside this clean repository. Generalizing it is the next
scale-up step (see `PLAYBOOK.md`).

## Normative rules

`caba_rules.json` contains **starting values**, not legal advice. Before
delivery, verify each value against the CABA Building Code (Law 6100) and the
Urban Code (Law 6099), or the local municipality. FOS/FOT and setbacks depend on
the parcel: declare and verify them, never invent them. A licensed professional
reviews and signs the plan.

## Cost

```bash
python3 tools/usage.py --project cad-agent
python3 tools/usage.py --project cad-agent --max-cost 1.00 --max-calls 1500
```

## Tests

```bash
bash tests/test_gates.sh
```

The self-test creates a deliberately broken DXF and verifies that both Level 2
gates reject it. A gate that does not fail is broken.
