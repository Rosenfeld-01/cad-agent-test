# /new-case — create a case skeleton

## Input

- A brief in `briefs/*.json` (or the data to write it).
- A typology in `typologies/` or a seed case (`--from-case`).

## Steps

1. If there is no brief, create `briefs/<slug>.json` from
   `briefs/_template.json`. Complete lot, program, target, and constraints.

2. Create the case:

   ```bash
   python3 tools/new_case.py \
     --brief briefs/<slug>.json \
     --typology typologies/<id>.json \
     --slug <slug>
   ```

   Or start from an existing case:

   ```bash
   python3 tools/new_case.py --brief briefs/<slug>.json --from-case <seed> --slug <slug>
   ```

3. Verify that these exist:
   - `cases/<slug>/brief.json`
   - `cases/<slug>/spec.json` (or `spec_*.json`)
   - `cases/<slug>/case.json` in `draft` state
   - `cases/<slug>/decisions.md`

4. Show the next commands:

   ```bash
   python3 tools/validate_spec.py cases/<slug>/spec.json
   ./run.sh cases/<slug>/spec.json out/<slug>
   ```

5. Do not invent the design. Adapt the seed spec to the brief and let the
   validator decide whether it works.
