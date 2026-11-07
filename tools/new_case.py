#!/usr/bin/env python3
"""new_case.py — crea un caso nuevo a partir de un brief y una tipologia.

Copia el/los spec(s) semilla, escribe el brief y deja un `decisiones.md` inicial.
No inventa el diseno: el agente adapta el spec al brief y corre el validador.

Uso:
    python3 tools/new_case.py --brief briefs/<slug>.json
    python3 tools/new_case.py --brief briefs/<slug>.json \
        --typology typologies/casa_entre_medianeras_8.66x20.json \
        --slug <slug>
    python3 tools/new_case.py --brief briefs/x.json --from-case <seed>

Salida: crea `casos/<slug>/` y muestra los comandos siguientes.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CASES = ROOT / "casos"
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
    raise SystemExit(f"ERROR: no encuentro el brief '{value}'")


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
    raise SystemExit(f"ERROR: no encuentro la tipologia '{value}'")


def seed_specs(typology: dict, from_case: str | None) -> list[Path]:
    if from_case:
        case_json = CASES / from_case / "case.json"
        if not case_json.exists():
            raise SystemExit(f"ERROR: no existe {case_json}")
        case = load_json(case_json)
        specs = case.get("specs", [])
        if not specs:
            raise SystemExit(f"ERROR: {case_json} no declara specs")
        return [(ROOT / s).resolve() for s in specs]

    specs = (typology.get("semilla") or {}).get("specs", [])
    if not specs:
        raise SystemExit("ERROR: la tipologia no declara semilla.specs")
    return [(ROOT / s).resolve() for s in specs]


def spec_name(seed: dict, index: int, total: int) -> str:
    if total == 1:
        return "spec.json"
    planta = str(seed.get("planta", "")).upper()
    if "BAJA" in planta:
        return "spec_pb.json"
    if "ALTA" in planta:
        return "spec_pa.json"
    return f"spec_{index + 1}.json"


def decisiones_md(brief: dict, typology: dict, specs: list[str]) -> str:
    lote = brief.get("lote", {})
    prog = brief.get("programa", {})
    obj = brief.get("objetivo", {})
    programa = ", ".join(
        f"{k}={v}" for k, v in prog.items() if v not in (None, False)
    ) or "(completar)"
    return f"""# {brief.get('slug', '<slug>')} — decisiones

## Brief

- **Titulo:** {brief.get('titulo', '(sin titulo)')}
- **Tipologia:** `{brief.get('tipologia', typology.get('id', '?'))}`
- **Lote:** {lote.get('frente_m', '?')} x {lote.get('fondo_m', '?')} m
  ({lote.get('superficie_m2', '?')} m2), medianeras={lote.get('medianeras', '?')}
- **Plantas:** {brief.get('plantas', '?')}
- **Programa:** {programa}
- **Objetivo:** {obj.get('superficie_cubierta_m2', '?')} m2, altura libre
  {obj.get('altura_libre_m', '?')} m
- **Specs semilla:** {', '.join(f'`{s}`' for s in specs)}

## Partido

<completar: retiros, huella, orientacion, circulacion>

## Números que cerraron

| Concepto | Valor |
|---|---|
| Superficie de ambientes | <m2> |
| Ambientes | <n> |
| Puertas | <n> |
| Ventanas | <n> |
| Factor de iluminación | <%> |
| Reporte | <ok / errores> |

## Qué funcionó

- <decision de diseno que se puede reutilizar>

## Qué se corrigió

- <error del validador y como se arreglo>

## Qué reutilizar en el próximo caso

- Tipologia `{brief.get('tipologia', typology.get('id', '?'))}`.
- Specs semilla: {', '.join(f'`{s}`' for s in specs)}.
- Correr `validate_spec.py` y `run.sh` despues de cada cambio.

## Costo

<pendiente: `python3 tools/usage.py --project cad-agent`>

## Pendientes / límites

- <FOS/FOT, estructura, instalaciones, firma>
"""


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Crea un caso desde un brief + tipologia.")
    ap.add_argument("--brief", required=True, help="brief JSON")
    ap.add_argument("--typology", help="tipologia JSON o id (default: la del brief)")
    ap.add_argument("--slug", help="nombre de carpeta (default: brief.slug)")
    ap.add_argument("--from-case", help="usar los specs de un caso existente como semilla")
    ap.add_argument("--force", action="store_true", help="sobrescribir archivos del caso")
    args = ap.parse_args(argv)

    brief_path = resolve_brief(args.brief)
    brief = load_json(brief_path)
    slug = args.slug or brief.get("slug")
    if not slug:
        raise SystemExit("ERROR: falta --slug o brief.slug")
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]*", slug):
        raise SystemExit(f"ERROR: slug invalido '{slug}' (minusculas, numeros y guiones)")

    typology_id = args.typology or brief.get("tipologia")
    if not typology_id:
        raise SystemExit("ERROR: falta --typology o brief.tipologia")
    typology_path = resolve_typology(typology_id)
    typology = load_json(typology_path)

    seeds = seed_specs(typology, args.from_case)
    for s in seeds:
        if not s.exists():
            raise SystemExit(f"ERROR: no existe el spec semilla {s}")

    case_dir = CASES / slug
    if case_dir.exists() and any(case_dir.iterdir()) and not args.force:
        raise SystemExit(
            f"ERROR: {case_dir} ya existe y no esta vacio. Usá --force para sobrescribir.")
    case_dir.mkdir(parents=True, exist_ok=True)

    # Copiar specs semilla, actualizando el proyecto.
    spec_paths: list[str] = []
    for i, seed_path in enumerate(seeds):
        seed = load_json(seed_path)
        name = spec_name(seed, i, len(seeds))
        seed["proyecto"] = brief.get("titulo", slug)
        out = case_dir / name
        out.write_text(json.dumps(seed, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        spec_paths.append(str(out.relative_to(ROOT)))

    # Brief
    (case_dir / "brief.json").write_text(
        json.dumps(brief, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    # Decisiones
    (case_dir / "decisiones.md").write_text(
        decisiones_md(brief, typology, spec_paths), encoding="utf-8")

    # Metadata
    nivel = int((brief.get("entregable") or {}).get("nivel", 1))
    case = {
        "slug": slug,
        "version": 1,
        "titulo": brief.get("titulo", slug),
        "fecha": brief.get("fecha") or dt.date.today().isoformat(),
        "estado": "borrador",
        "nivel": nivel,
        "tipologia": brief.get("tipologia", typology.get("id")),
        "brief": f"casos/{slug}/brief.json",
        "specs": spec_paths,
        "salidas": {
            "dxf": [f"out/{slug}/{Path(p).stem}.dxf" for p in spec_paths],
            "reporte": [f"out/{slug}/{Path(p).stem}.report.json" for p in spec_paths],
        },
        "metricas": {
            "superficie_m2": None,
            "ambientes": None,
            "reporte_ok": False,
        },
        "lecciones": f"casos/{slug}/decisiones.md",
        "tags": [brief.get("tipologia", typology.get("id", "")), f"nivel-{nivel}"],
    }
    (case_dir / "case.json").write_text(
        json.dumps(case, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(f"caso creado: {case_dir}")
    for p in spec_paths:
        print(f"  spec: {p}")
    print()
    print("siguiente:")
    for p in spec_paths:
        print(f"  python3 tools/validate_spec.py {p}")
        print(f"  ./run.sh {p} out/{slug}")
    print()
    print("despues: editar el spec (no el DXF), correr de nuevo y actualizar case.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
