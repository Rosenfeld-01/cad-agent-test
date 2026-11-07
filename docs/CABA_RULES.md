# Reference dimensions — housing in CABA

Two blocks: **normative minimums** (CABA Building Code) and **professional
practice dimensions** (not normative, but needed for a plan that works).

> Always verify against the current text. This is a project aid, not legal
> advice.

## A. Normative minimums (CABA Building Code, Law 6100 / consolidated text Law 6438)

| Concept | Min. side | Min. area | Article |
|---|---|---|---|
| Room clear height | — | 2.40 m | 3.3.1.2.1 |
| Single first-class room | 2.80 m | 18.00 m² | 3.8.9.1 |
| First-class room (living) | 2.80 m | 9.00 m² | 3.8.9.1 |
| Living-dining-bedroom | 2.80 m | 15.00 m² | 3.8.1.1.1 |
| Living-dining-bedroom-kitchen | 2.80 m | 18.00 m² | 3.8.1.1.1 |
| Bedroom (third class) | 2.50 m | 7.50 m² | 3.8.9.1 |
| Bathroom type I (WC-bidet-shower with tub) | 1.50 m | 3.00 m² | 3.8.1.1.1 |
| Bathroom type II (WC-bidet-shower without tub) | 1.50 m | 2.50 m² | 3.8.1.1.1 |
| Bathroom type III (WC-bidet-shower) | 0.90 m | 1.40 m² | 3.8.1.1.1 |
| Bathroom type IV (WC-shower) | 0.90 m | 1.20 m² | 3.8.1.1.1 |
| Balcony, terrace, or patio | 1.20 m | 1.50 m² | 3.8.9.1 |
| Storage space | 0.60 m | 1.00 m² | 3.8.9.1 |
| Internal circulation | 1.00 m | — | 3.8.9.1 |
| Circulation on lots ≤ 8.66 m | 0.95 m | — | 3.8.9.1 |
| Entrance opening on a narrow lot | 0.85 m | — | 3.8.9.1 |
| Type II bathroom door (clear passage) | 0.80 m | — | 3.8.9.1 |
| Kitchen passage | 0.90 m | — | 3.8.9.1 |
| Integrated cooking space | 0.80 m passage | +3.00 m² | 3.8.9.1 |
| Natural lighting | — | 20% of room area | 3.8.1.1.3 |
| Ventilation | — | 5% of room area | 3.8.1.1.3 |

Notes:

- In homes with **2 or more bedrooms**, **50%** of them may light and ventilate
  to a vertical patio (3.8.1.1.3).
- The **Minimum Housing Unit** (18 to 25.50 m² of habitable rooms) is a special
  regime; it is not the goal of this project.
- **FOS, FOT, and setbacks are not here**: they depend on the Urban Code and the
  specific parcel. Do not invent them.

## B. Professional practice (not normative)

| Concept | Usual value |
|---|---|
| Exterior wall | 0.20 m |
| Interior wall / partition | 0.10 m |
| Entrance door | 0.90 m |
| Interior door | 0.80 m |
| Window: sill height | 0.90 m |
| Window: height | 1.40 m |
| Lintel / passage height | 2.10 m |
| Kitchen counter | 0.60 m deep × 0.90 m high |
| Closet | 0.60 m deep |
| Double bed | 1.40 × 1.90 m |
| Single bed | 0.90 × 1.90 m |
| Toilet | 0.40 × 0.70 m |
| Washbasin | 0.50 × 0.40 m |
| Shower | 0.90 × 0.90 m |
| Bathtub | 1.70 × 0.70 m |
| Garage | 2.50 × 5.00 m |
| Stair (if any) | 0.28 m tread, 0.18 m riser, 0.90–1.00 m wide |
| Design module | 0.10 m |

## C. How it is validated

`check.py` applies block A from `caba_rules.json` and calculates lighting and
ventilation **from the actual window geometry** in the spec. Block B is design
judgment: the agent uses it to make the plan habitable, but the validator does
not enforce it.
