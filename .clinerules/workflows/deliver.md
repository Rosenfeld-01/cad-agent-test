# /deliver — close and deliver a case

## Input

- A case (`cases/<slug>/`) with its spec and report.
- If the case is not in `ok` state, do not deliver: return to `/review-plan`.

## Checklist

1. **Floor-plan report:**

   ```bash
   python3 tools/validate_spec.py <spec>
   ./run.sh <spec> out/<slug>
   ```

   `ok: true`, 0 errors.

2. **If there is a sheet set (Level 2):**

   ```bash
   python3 tools/qa_sheets.py --all out
   python3 tools/qa_geometry.py --all out
   python3 tools/qa_walls.py --all out
   ```

   Both Level 2 gates must be green; wall overlap must be 0.00 m² on plan
   sheets.

3. **Files:** list DXF, DWG, PNG, PDF, and reports generated. Verify they exist
   and that the DXF entity count did not drop.

4. **Update the case:**
   - `case.json`: `status`, `metrics`, `outputs`;
   - `decisions.md`: 5–10 lines useful for the next case;
   - cost: `python3 tools/usage.py --project cad-agent`.

5. **Client summary:**
   - room table (name, type, m², minimum side);
   - areas;
   - lighting and ventilation per room;
   - what was verified and what is pending (FOS/FOT, structure, services,
     signature).

6. **Do not sign or submit.** A licensed professional reviews and signs.
