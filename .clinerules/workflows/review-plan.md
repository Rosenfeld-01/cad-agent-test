# /review-plan — diagnose and fix a plan

## Input

- A case (`cases/<slug>/`) or a spec (`spec_*.json`).
- If not specified, use the most recent case in `cases/`.

## Steps

1. **Spec preflight:**

   ```bash
   python3 tools/validate_spec.py <spec>
   ```

   If it fails, fix the spec structure or geometry first.

2. **Generate and validate:**

   ```bash
   ./run.sh <spec> out/<slug>
   ```

   Read `out/<slug>/*.report.json`.

3. **Explain every error** with its code (`ROOM_TOO_SMALL`, `LIGHTING`,
   `OPENING_OUT_OF_WALL`, etc.), the affected room or wall, and the missing
   dimension. Do not say "there are errors": say which and why.

4. **Fix the spec**, not the DXF:
   - minimum area or side → move the wall or enlarge the room;
   - lighting → enlarge the window or reassign it to the correct room;
   - opening outside wall → adjust `s` or `width`;
   - overlap → correct the layout.
   Return to step 1. **Maximum 10 iterations.**

5. If the error is a **missing rule** (FOS/FOT/setbacks), stop and ask. Do not
   invent a value.

6. With `ok: true`, review the render and close.
