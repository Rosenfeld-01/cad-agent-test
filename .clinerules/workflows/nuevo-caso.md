# /nuevo-caso — crear el esqueleto de un caso

## Entrada

- Un brief en `briefs/*.json` (o los datos para escribirlo).
- Una tipología de `typologies/` o un caso semilla (`--from-case`).

## Pasos

1. Si no hay brief, crearlo en `briefs/<slug>.json` copiando la estructura de
   `briefs/_plantilla/brief.json`. Completar lote, programa, objetivo y restricciones.

2. Crear el caso:
   ```bash
   python3 tools/new_case.py \
     --brief briefs/<slug>.json \
     --typology typologies/<id>.json \
     --slug <slug>
   ```
   O, para partir de un caso existente:
   ```bash
   python3 tools/new_case.py --brief briefs/<slug>.json --from-case <seed> --slug <slug>
   ```

3. Verificar que se creó:
   - `casos/<slug>/brief.json`
   - `casos/<slug>/spec.json` (o `spec_pb.json` / `spec_pa.json`)
   - `casos/<slug>/case.json` en estado `borrador`
   - `casos/<slug>/decisiones.md`

4. Mostrar los comandos siguientes:
   ```bash
   python3 tools/validate_spec.py casos/<slug>/spec.json
   ./run.sh casos/<slug>/spec.json out/<slug>
   ```

## Qué NO hace este workflow

- No diseña ni adapta el spec: eso es `/nueva-vivienda`.
- No corre el pipeline: eso es `/nueva-vivienda` o `/revisar-plano`.
- No entrega: eso es `/entregar`.

## Prohibido

- Crear un caso sin brief.
- Copiar un spec y declararlo listo sin validar.
- Duplicar specs canónicos: usá `--from-case` o la semilla de la tipología.
