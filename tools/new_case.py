#!/usr/bin/env python3
"""new_case.py — create a new case from a brief and a typology.

Copies the seed spec(s), writes the brief, and creates an initial `decisions.md`.
It does not invent the design: the agent adapts the spec to the brief and runs
the validator.

Usage:
    python3 tools/new_case.py --brief briefs/<slug>.json
    python3 tools/new_case.py --brief briefs/<slug>.json \
        --typology typologies/house_between_party_walls_8.66x20.json \
        --slug <slug>
    python3 tools/new_case.py --brief briefs/x.json --from-case <seed>

Output: creates `cases/<slug>/` and prints the next commands.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CASES = ROOT / "cases"
TYPO = ROOT / "typologies"


def load_json(path: Path) -> dict:
    with path.open(encoding="utf-8") as fh:
        return json.load(fh)


def resolve_brief(value: str) -> Path:
    p = Path(value)
    if p.exists():
        return p.resolve()
    if (ROOT / value).exists():
        return (ROOT / value).resolve()
    if (ROOT / "briefs" / value).exists():
        return (ROOT / "briefs" / value).resolve()
    if (ROOT / "briefs" / f"{value}.json").exists():
        return (ROOT / "briefs" / f"{value}.json").resolve()
    raise SystemExit(f"ERROR: cannot find brief '{value}'")


def resolve_typology(value: str) -> Path:
    p = Path(value)
    if p.exists():
        return p.resolve()
    if (ROOT / value).exists():
        return (ROOT / value).resolve()
    if (TYPO / value).exists():
        return (TYPO / value).resolve()
    if (TYPO / f"{value}.json").exists():
        return (TYPO / f"{value}.json").resolve()
    raise SystemExit(f"ERROR: cannot find typology '{value}'")


def seed_specs(typology: dict, from_case: str | None) -> list[Path]:
    if from_case:
        case_json = CASES / from_case / "case.json"
        if not case_json.exists():
            raise SystemExit(f"ERROR: {case_json} does not exist")
        case = load_json(case_json)
        specs = case.get("specs", [])
        if not specs:
            raise SystemExit(f"ERROR: {case_json} does not declare specs")
        return [(ROOT / s).resolve() for s in specs]

    specs = (typology.get("seed") or {}).get("specs", [])
    if not specs:
        raise SystemExit("ERROR: the typology does not declare seed.specs")
    return [(ROOT / s).resolve() for s in specs]


def spec_name(seed: dict, index: int, total: int) -> str:
    if total == 1:
        return "spec.json"
    floor = str(seed.get("floor", "")).upper()
    if "GROUND" in floor:
        return "spec_gf.json"
    if "UPPER" in floor:
        return "spec_uf.json"
    return f"spec_{index + 1}.json"


def decisions_md(brief: dict, typology: dict, specs: list[str]) -> str:
    lot = brief.get("lot", {})
    program = brief.get("program", {})
    target = brief.get("target", {})
    program_text = ", ".join(
        f"{k}={v}" for k, v in program.items() if v not in (None, False)
    ) or "(complete)"
    return f"""# {brief.get('slug', '<slug>')} — decisions

## Brief

- **Title:** {brief.get('title', '(untitled)')}
- **Typology:** `{brief.get('typology', typology.get('id', '?'))}`
- **Lot:** {lot.get('front_m', '?')} x {lot.get('depth_m', '?')} m
  ({lot.get('area_m2', '?')} m2), party_walls={lot.get('party_walls', '?')}
- **Floors:** {brief.get('floors', '?')}
- **Program:** {program_text}
- **Target:** {target.get('covered_area_m2', '?')} m2, clear height
  {target.get('clear_height_m', '?')} m
- **Seed specs:** {', '.join(f'`{s}`' for s in specs)}

## Layout

<complete: setbacks, footprint, orientation, circulation>

## Numbers that worked

| Concept | Value |
|---|---|
| Room area | <m2> |
| Rooms | <n> |
| Doors | <n> |
| Windows | <n> |
| Lighting factor | <%> |
| Report | <ok / errors> |

## What worked

- <design decision that can be reused>

## What was fixed

- <validator error and how it was fixed>

## What to reuse in the next case

- Typology `{brief.get('typology', typology.get('id', '?'))}`.
- Seed specs: {', '.join(f'`{s}`' for s in specs)}.
- Run `validate_spec.py` and `run.sh` after every change.

## Cost

<pending: `python3 tools/usage.py --project cad-agent`>

## Pending / limits

- <FOS/FOT, structure, services, signature>
"""


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Create a case from a brief + typology.")
    ap.add_argument("--brief", required=True, help="brief JSON")
    ap.add_argument("--typology", help="typology JSON or id (default: the brief's)")
    ap.add_argument("--slug", help="folder name (default: brief.slug)")
    ap.add_argument("--from-case", help="use an existing case's specs as the seed")
    ap.add_argument("--force", action="store_true", help="overwrite case files")
    args = ap.parse_args(argv)

    brief_path = resolve_brief(args.brief)
    brief = load_json(brief_path)
    slug = args.slug or brief.get("slug")
    if not slug:
        raise SystemExit("ERROR: missing --slug or brief.slug")
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]*", slug):
        raise SystemExit(f"ERROR: invalid slug '{slug}' (lowercase, digits, hyphens)")

    typology_id = args.typology or brief.get("typology")
    if not typology_id:
        raise SystemExit("ERROR: missing --typology or brief.typology")
    typology_path = resolve_typology(typology_id)
    typology = load_json(typology_path)

    seeds = seed_specs(typology, args.from_case)
    for s in seeds:
        if not s.exists():
            raise SystemExit(f"ERROR: seed spec {s} does not exist")

    case_dir = CASES / slug
    if case_dir.exists() and any(case_dir.iterdir()) and not args.force:
        raise SystemExit(
            f"ERROR: {case_dir} already exists and is not empty. Use --force to overwrite.")
    case_dir.mkdir(parents=True, exist_ok=True)

    # Copy seed specs, updating the project name.
    spec_paths: list[str] = []
    for i, seed_path in enumerate(seeds):
        seed = load_json(seed_path)
        name = spec_name(seed, i, len(seeds))
        seed["project"] = brief.get("title", slug)
        out = case_dir / name
        out.write_text(json.dumps(seed, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        spec_paths.append(str(out.relative_to(ROOT)))

    # Brief
    (case_dir / "brief.json").write_text(
        json.dumps(brief, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    # Decisions
    (case_dir / "decisions.md").write_text(
        decisions_md(brief, typology, spec_paths), encoding="utf-8")

    # Metadata
    level = int((brief.get("deliverable") or {}).get("level", 1))
    case = {
        "slug": slug,
        "version": 1,
        "title": brief.get("title", slug),
        "date": brief.get("date") or dt.date.today().isoformat(),
        "status": "draft",
        "level": level,
        "typology": brief.get("typology", typology.get("id")),
        "brief": f"cases/{slug}/brief.json",
        "specs": spec_paths,
        "outputs": {
            "dxf": [f"out/{slug}/{Path(p).stem}.dxf" for p in spec_paths],
            "report": [f"out/{slug}/{Path(p).stem}.report.json" for p in spec_paths],
        },
        "metrics": {
            "area_m2": None,
            "rooms": None,
            "report_ok": False,
        },
        "lessons": f"cases/{slug}/decisions.md",
        "tags": [brief.get("typology", typology.get("id", "")), f"level-{level}"],
    }
    (case_dir / "case.json").write_text(
        json.dumps(case, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(f"case created: {case_dir}")
    for p in spec_paths:
        print(f"  spec: {p}")
    print()
    print("next:")
    for p in spec_paths:
        print(f"  python3 tools/validate_spec.py {p}")
        print(f"  ./run.sh {p} out/{slug}")
    print()
    print("then: edit the spec (not the DXF), run again, and update case.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
