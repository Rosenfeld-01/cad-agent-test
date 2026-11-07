# /new-home — new housing project (Level 1: floor plan)

## Input

- A brief in `briefs/*.json` or the client data in the message.
- If the brief is missing, ask for it first: lot, program, target, constraints,
  and whether the deliverable is Level 1 or Level 2.

## Steps

1. **Read the minimum context** (do not read large files in full):
   - the brief,
   - the typology in `typologies/`,
   - `caba_rules.json` and `docs/CABA_RULES.md`,
   - the closest `cases/<seed>/decisions.md`.

2. **Create the case** (not by hand):

   ```bash
   python3 tools/new_case.py --brief briefs/<x>.json --slug <slug>
   ```

   If the brief already has `typology`, `--typology` is not needed. To start
   from another case: `--from-case <slug>`.

3. **Adapt the spec** `cases/<slug>/spec.json`:
   - adjust rooms, walls, and openings to the program,
   - keep the minimums from `caba_rules.json`,
   - do not touch the DXF.

4. **Preflight:**

   ```bash
   python3 tools/validate_spec.py cases/<slug>/spec.json
   ```

5. **Generate and validate:**

   ```bash
   ./run.sh cases/<slug>/spec.json out/<slug>
   ```

6. **Read the report** `out/<slug>/*.report.json`. If `ok: false`, fix the spec
   and return to step 4. Maximum 10 iterations.

7. **With `ok: true`**, review the render and deliver DXF + DWG + PNG/PDF +
   report. Update `case.json` and `decisions.md`.
