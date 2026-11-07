# 10 — Flujo obligatorio

## Regla de oro: el DXF no se edita a mano

La fuente de verdad es el `spec` JSON. El flujo es siempre:

```
spec.json → validate_spec.py → plan.py → out/*.dxf → check.py → corregir spec → repetir
```

Nunca edites `out/*.dxf` ni `out/*.dwg` directamente. Si algo está mal, se
corrige el spec y se regenera.

## Dos niveles de entrega

| Nivel | Qué es | Comando | Costo |
|---|---|---|---|
| **1** | Planta de una vivienda: DXF + reporte + PNG/DWG si hay CADCraft | `./run.sh <spec> out/<slug>` | Bajo |
| **2** | Juego de láminas A2 (planta, techos, cortes, fachadas, instalaciones, detalles) | `python3 planos.py` + gates | Alto |

**Nivel 1 primero.** No se produce el juego de láminas sin aprobación explícita
del cliente. El Nivel 2 se apoya en un `planos.py` por proyecto y en el catálogo
`CAD_Blocks/`.

## Ciclo de un proyecto nuevo (Nivel 1)

1. Leer el `briefs/*.json`, la tipología de `typologies/`, `rules_caba.json`,
   `MEDIDAS_CABA.md` y el `casos/<seed>/decisiones.md` más parecido.
2. Crear el caso:
   ```bash
   python3 tools/new_case.py --brief briefs/<x>.json --slug <slug>
   ```
3. Editar `casos/<slug>/spec.json` (o `spec_pb.json` / `spec_pa.json`). Se
   adapta el spec semilla al brief; no se dibuja a mano.
4. Preflight:
   ```bash
   python3 tools/validate_spec.py casos/<slug>/spec.json
   ```
5. Generar y validar:
   ```bash
   ./run.sh casos/<slug>/spec.json out/<slug>
   ```
6. Leer `out/<slug>/*.report.json`. Si `ok: false`, corregir el spec y repetir.
   **Máximo 10 iteraciones.** Si no converge, parar y explicar.
7. Con `ok: true`, actualizar `casos/<slug>/case.json` (estado, métricas,
   salidas) y escribir 5–10 líneas en `casos/<slug>/decisiones.md`.
8. Entregar Nivel 1. Preguntar antes de pasar a Nivel 2.

## Nivel 2 (sólo con aprobación)

1. Leer `PLAYBOOK.md` §2 (mapa del código) y §3 (comandos).
2. Usar el `planos.py` del proyecto o copiar el de Vivienda 02 como base.
3. Construir por hoja: `python3 planos.py L07`.
4. Gate por hoja: `qa_laminas.py` y `qa_geometria.py`.
5. Cierre: `python3 planos.py && python3 tools/qa_laminas.py --all out &&
   python3 tools/qa_geometria.py --all out`. Si los dos gates están en verde,
   la entrega está cerrada.

## Nunca

- Declarar terminado un plano con el reporte en `ok: false`.
- Entregar sin `validate_spec.py` y `check.py`.
- Editar el DXF o el DWG para "arreglar" algo.
- Inventar medidas, cotas o normas.
- Promover a Nivel 2 sin aprobación.
