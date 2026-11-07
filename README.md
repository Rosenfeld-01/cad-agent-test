# cad-agent — framework para generar planos de vivienda con CADCraft

Pipeline determinístico que convierte un **brief** en un **plano de vivienda
validado**. La fuente de verdad es un `spec` JSON; el DXF se **genera**, nunca
se edita a mano.

```
brief.json ─▶ new_case.py ─▶ spec.json ─▶ validate_spec.py ─▶ plan.py ─▶ check.py ─▶ out/*.dxf
```

Si algo está mal, se corrige el `spec` y se regenera. Editar el DXF a mano rompe
la trazabilidad y el validador deja de tener sentido.

- **Nivel 1 (barato):** planta de una vivienda → DXF + reporte + PNG/DWG/PDF si
  está `cadcraft-cli`.
- **Nivel 2 (caro):** juego de láminas A2. El código de referencia vive en
  `examples/nivel2/`; se produce **sólo** tras aprobar la planta.

## Requisitos

- Python 3.10+ con `ezdxf` y `matplotlib`.
- Opcional: `cadcraft-cli` en `PATH` para exportar PNG/DWG/PDF (ver
  `mcp-cline.json` / `mcp-opencode.json`).

## Arranque rápido (Nivel 1)

```bash
# Validar y generar la planta de la semilla incluida
python3 tools/validate_spec.py typologies/semillas/casa_8.66x20.json
./run.sh typologies/semillas/casa_8.66x20.json out/semilla
```

El reporte queda en `out/semilla/*.report.json`. Con `"ok": true` el plano está
limpio; si hay errores, se corrige el spec y se vuelve a correr (**máximo 10
iteraciones**; si no converge, parar y explicar).

## Crear un caso nuevo

```bash
cp briefs/_plantilla/brief.json briefs/<slug>.json      # completar el brief
python3 tools/new_case.py --brief briefs/<slug>.json \
  --typology typologies/casa_entre_medianeras_8.66x20.json --slug <slug>
python3 tools/validate_spec.py casos/<slug>/spec.json
./run.sh casos/<slug>/spec.json out/<slug>
```

`new_case.py` copia el spec semilla de la tipología y deja `brief.json`,
`case.json` (estado `borrador`) y `decisiones.md`.

## Estructura

| Ruta | Para qué |
|---|---|
| `plan.py` | Genera el DXF desde el spec (paramétrico, unidades en metros). |
| `check.py` | Valida el DXF contra el spec y `rules_caba.json`; emite el reporte. |
| `run.sh` | Pipeline completo: validar → generar → validar → PNG/DWG/PDF. |
| `rules_caba.json` | Valores de partida (no asesoramiento legal). |
| `MEDIDAS_CABA.md` | Medidas de práctica y mínimos. |
| `schemas/spec.schema.json` | Contrato del spec. |
| `tools/validate_spec.py` | Preflight barato del spec. |
| `tools/new_case.py` | Crea un caso desde brief + tipología. |
| `tools/usage.py` | Costo, llamadas y cache por proyecto. |
| `tools/qa_laminas.py`, `tools/qa_geometria.py` | Gates del juego de láminas (Nivel 2). |
| `tools/qa_muros.py` | Chequeo de espesores/continuidad de muros. |
| `typologies/` | Soluciones reutilizables + spec semilla (`semillas/`). |
| `briefs/` | Entradas de proyecto (`_plantilla/brief.json`). |
| `casos/` | Proyectos concretos: spec, decisiones y métricas. |
| `planos_lib.py` | Primitivas de lámina (marco, escalas, bloques) para Nivel 2. |
| `examples/nivel2/` | Ejemplo autocontenido del juego de láminas. |
| `CAD_Blocks/` | Biblioteca de bloques cadastrados (mobiliario, artefactos, instalaciones). |
| `tests/` | Autotest de gates (`mk_dxf_roto.py` + `test_gates.sh`). |
| `docs/` | `ESCALADO.md` (método y costos) y `DEFECTOS_CONOCIDOS.md`. |
| `PLAYBOOK.md` | Memoria técnica del Nivel 2 (gates, convenciones, protocolo de bajo costo). |
| `AGENTS.md` | Cómo trabaja el agente. |

## Convenciones

- Unidades: **metros** (1 unidad = 1 m). `$INSUNITS = 6`.
- Capas: `A-WALL`, `A-DOOR`, `A-WIN`, `A-AREA`, `A-ANNO`, `A-DIM`, `A-AXIS`
  (Nivel 2 agrega `A-MOB`, `A-HATCH`, `X-FRAME`, `I-ELE`, `I-SAN`, `I-GAS`).
- Altura de texto mínima: 0,15 m. Cotas en metros con dos decimales.

## Nivel 2 (ejemplo de referencia)

```bash
cd examples/nivel2
python3 planos.py L07                       # construir sólo una hoja
python3 ../../tools/qa_laminas.py out/L07.dxf
python3 ../../tools/qa_geometria.py out/L07.dxf
```

`planos.py` está hecho para un caso concreto: es una **plantilla** para copiar y
adaptar a un proyecto nuevo, no un generador genérico. Generalizarlo es el
próximo salto de escala (ver `docs/ESCALADO.md` §8).

## Normativa

`rules_caba.json` son **valores de partida**, no asesoramiento legal. Antes de
entregar, verificar cada valor contra el Código de Edificación (Ley 6100) y el
Código Urbanístico (Ley 6099) de CABA, o la normativa del municipio. FOS/FOT y
retiros dependen de la parcela: se declaran y se verifican, no se inventan. El
plano lo revisa y firma un profesional matriculado.

## Costo

```bash
python3 tools/usage.py --project cad-agent
python3 tools/usage.py --project cad-agent --max-cost 1.00 --max-calls 1500
```
