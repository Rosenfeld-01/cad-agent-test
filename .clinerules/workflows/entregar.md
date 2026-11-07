# /entregar — cerrar y entregar un caso

## Entrada

- Un caso (`casos/<slug>/`) con su spec y reporte.
- Si el caso no está en estado `ok`, no entregar: volver a `/revisar-plano`.

## Checklist

1. **Reporte de planta**:
   ```bash
   python3 tools/validate_spec.py <spec>
   ./run.sh <spec> out/<slug>
   ```
   `ok: true`, 0 errores.

2. **Si hay juego de láminas (Nivel 2)**:
   ```bash
   python3 planos.py
   python3 tools/qa_laminas.py --all out
   python3 tools/qa_geometria.py --all out
   ```
   Los dos gates tienen que estar en verde (13/13 en Vivienda 02).

3. **Archivos**: listar DXF, DWG, PNG, PDF y reportes generados. Verificar que
   existan y que el DXF no haya bajado el conteo de entidades.

4. **Actualizar el caso**:
   - `case.json`: `estado`, `metricas`, `salidas`;
   - `decisiones.md`: 5–10 líneas con lo que sirve para el próximo caso;
   - costo: `python3 tools/usage.py --project cad-agent`.

5. **Resumen al cliente**:
   - tabla de ambientes (nombre, tipo, m², lado mínimo);
   - superficies, ventanas y factor de iluminación;
   - resultado de los gates;
   - rutas de los archivos;
   - deudas conocidas (FOS/FOT, estructura, instalaciones, firma).

6. **Firma**: el plano lo revisa y firma un profesional matriculado. No firmes
   ni presentes en nombre de nadie.

## Prohibido

- Entregar con errores o warnings sin explicar.
- Ocultar que un cálculo no está hecho (estructura, instalaciones, FOS/FOT).
- Prometer fidelidad total contra AutoCAD sin validar el round-trip.
