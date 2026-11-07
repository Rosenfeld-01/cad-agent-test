# 20 — Normative rules

`caba_rules.json` contains **starting values**, not legal advice. The validator
applies only the rules written there.

## Before delivery

- Verify each value against the current CABA Building Code (Law 6100) and Urban
  Code (Law 6099), or the project's municipality.
- **FOS/FOT/setbacks are not in `caba_rules.json`**: they depend on the parcel
  and the Urban Code. If the project needs them, verify and write them in
  `case.json`; never invent them.
- If a rule is missing: **ask**. Do not "approximate" a code requirement or copy
  a number from another municipality.
- A licensed professional reviews and signs the plan. Do not sign or submit.

## Minimums already applied by `check.py`

- Clear height, minimum areas, and minimum sides by room type.
- Entrance, interior, and bathroom door widths.
- Minimum wall thickness.
- Lighting (20%) and ventilation (5%) calculated from window geometry, not from
  a declared number.
- Circulation: 1.00 m (0.95 m on lots with frontage ≤ 8.66 m).
- Minimum entrance opening on narrow lots (0.85 m).
- No lighting/ventilation required for corridor and storage.
