# /nueva-vivienda — vivienda nueva (Nivel 1: planta)

## Entrada

- Un brief en `briefs/*.json` o los datos del cliente en el mensaje.
- Si falta el brief, pedilo antes de empezar: lote, programa, objetivo,
  restricciones y si el entregable es Nivel 1 o Nivel 2.

## Pasos

1. **Leer el contexto mínimo** (no leer archivos grandes completos):
   - el brief,
   - la tipología de `typologies/`,
   - `rules_caba.json` y `MEDIDAS_CABA.md`,
   - el `casos/<seed>/decisiones.md` más parecido.

2. **Crear el caso** (no a mano):
   ```bash
   python3 tools/new_case.py --brief briefs/<x>.json --slug <slug>
   ```
   Si el brief ya trae `tipologia`, no hace falta `--typology`. Si querés partir
   de otro caso: `--from-case <slug>`.

3. **Adaptar el spec** `casos/<slug>/spec.json` (o `spec_pb.json` /
   `spec_pa.json`):
   - ajustar ambientes, muros y aberturas al programa,
   - mantener los mínimos de `rules_caba.json`,
   - no tocar el DXF.

4. **Preflight**:
   ```bash
   python3 tools/validate_spec.py casos/<slug>/spec.json
   ```
   Si hay errores, corregir el spec antes de generar.

5. **Generar y validar**:
   ```bash
   ./run.sh casos/<slug>/spec.json out/<slug>
   ```
   Leer `out/<slug>/*.report.json`. Si `ok: false`, corregir el spec y repetir.
   **Máximo 10 iteraciones.** Si no converge, parar y explicar qué falta.

6. **Cerrar el caso**:
   - actualizar `casos/<slug>/case.json`: `estado: "ok"`, `metricas`, `salidas`;
   - escribir 5–10 líneas en `casos/<slug>/decisiones.md` (partido, qué funcionó,
     qué se corrigió, qué reutilizar);
   - medir el costo:
     ```bash
     python3 tools/usage.py --project cad-agent
     ```

7. **Entregar Nivel 1**: DXF + reporte + PNG/DWG/PDF si `cadcraft-cli` está.
   Mostrar tabla de ambientes, resultado del reporte y rutas.

8. **Preguntar** si el cliente quiere el juego de láminas (Nivel 2). No lo
   produzcas sin aprobación: es la parte cara.

## Criterio de terminado

- `validate_spec.py` sin errores.
- `run.sh` con `ok: true` y 0 errores.
- `case.json` actualizado.
- `decisiones.md` escrito.
- Costo medido o declarado como no disponible.

## Prohibido

- Editar el DXF/DWG.
- Entregar con `ok: false`.
- Inventar normas o medidas.
- Saltar el preflight.
