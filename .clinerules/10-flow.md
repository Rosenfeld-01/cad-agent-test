# 10 — Required flow

## Golden rule: never edit the DXF by hand

The source of truth is the JSON `spec`. The flow is always:

```
spec.json → validate_spec.py → plan.py → out/*.dxf → check.py → fix spec → repeat
```

Never edit `out/*.dxf` or `out/*.dwg` directly. If something is wrong, fix the
spec and regenerate.

## Two delivery levels

| Level | What it is | Command | Cost |
|---|---|---|---|
| **1** | One housing floor plan: DXF + report + PNG/DWG when CADCraft is available | `./run.sh <spec> out/<slug>` | Low |
| **2** | A2 sheet set (plans, roof, sections, facades, services, details) | `sheets.py` + gates | High |

**Level 1 first.** Do not produce the sheet set without explicit client
approval. Level 2 is a toolkit (`sheet_lib.py`, `CAD_Blocks/`, gates); each
project composes its own `sheets.py`.

## New project cycle (Level 1)

1. Read `briefs/*.json`, the typology in `typologies/`, `caba_rules.json`,
   `docs/CABA_RULES.md`, and the closest `cases/<seed>/decisions.md`.
2. Create the case:

   ```bash
   python3 tools/new_case.py --brief briefs/<x>.json --slug <slug>
   ```

3. Adapt `cases/<slug>/spec.json` to the brief.
4. Preflight:

   ```bash
   python3 tools/validate_spec.py cases/<slug>/spec.json
   ```

5. Generate and validate:

   ```bash
   ./run.sh cases/<slug>/spec.json out/<slug>
   ```

6. If `ok: false`, fix the spec and return to step 4. **Maximum 10
   iterations.** If it does not converge, stop and explain.
7. Only with `ok: true`, review the render and deliver.

## Level 2 cycle

1. Compose one sheet in the project's `sheets.py`.
2. Build only that sheet.
3. Run `tools/qa_sheets.py`, `tools/qa_geometry.py`, and, for plans,
   `tools/qa_walls.py`.
4. Fix the sheet and repeat. Close the set only when every gate is green.
