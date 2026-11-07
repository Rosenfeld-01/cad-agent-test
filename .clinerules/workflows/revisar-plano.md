# /revisar-plano — diagnosticar y corregir un plano

## Entrada

- Un caso (`casos/<slug>/`) o un spec (`spec_*.json`).
- Si no se indica, usar el caso más reciente en `casos/`.

## Pasos

1. **Preflight del spec**:
   ```bash
   python3 tools/validate_spec.py <spec>
   ```
   Si falla, corregir primero la estructura o la geometría del spec.

2. **Generar y validar**:
   ```bash
   ./run.sh <spec> out/<slug>
   ```
   Leer `out/<slug>/*.report.json`.

3. **Explicar cada error** con su código (`ROOM_TOO_SMALL`, `LIGHTING`,
   `OPENING_OUT_OF_WALL`, etc.), el ambiente o muro afectado y la medida que
   falta. No decir "hay errores": decir cuáles y por qué.

4. **Corregir el spec**, no el DXF:
   - área o lado mínimo → mover el muro o ampliar el ambiente;
   - iluminación → agrandar la ventana o reasignarla al ambiente correcto;
   - abertura fuera del muro → ajustar `s` o `ancho`;
   - solapamiento → corregir el partido.
   Volver al paso 1. **Máximo 10 iteraciones.**

5. Si el error es una **regla faltante** (FOS/FOT, retiros, estructura), parar y
   preguntar. No inventar el número.

6. Si hay juego de láminas, correr los gates:
   ```bash
   python3 tools/qa_laminas.py --all out
   python3 tools/qa_geometria.py --all out
   ```
   Un hallazgo de gate es un defecto real: corregir la hoja y volver a pasar.

## Criterio de terminado

- `ok: true`, 0 errores.
- Si hay láminas: `qa_laminas` y `qa_geometria` en verde.
- El reporte final se guarda y se menciona en la respuesta.

## Prohibido

- Editar el DXF para "taparlo".
- Bajar el estándar para que pase el validador.
- Declarar terminado sin reporte.
