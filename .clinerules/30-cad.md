# 30 — CAD

## Verdad geométrica vs. estética

- **Geometría / medidas / reglas** → `inspect_drawing`, `query_entities`,
  `find_text` (datos exactos) y `check.py`. Es la verdad.
- **Estética / legibilidad / "se ve bien"** → `render` (PNG) + modelo de visión.
- Si el render y los datos no coinciden, **mandan los datos**.

## Herramientas

- MCP `cadcraft`: `command_line`, `script`, `execute`, `inspect_drawing`,
  `query_entities`, `find_text`, `render`, `open`, `save`, `new_drawing`,
  `cancel`, `list_commands`.
- CLI: `cadcraft-cli info | convert | run | commands | mcp`.
- Python: `ezdxf` (lectura/escritura DXF), `matplotlib`.

## Límites de CADCraft

- Está en desarrollo temprano: **las entidades que no modela se pierden al
  guardar**. Guardá siempre una copia del original antes de sobrescribir.
- Al abrir un DWG, revisar `warnings` del MCP `open` y `readNotes` de
  `cadcraft-cli info`.
- Después de cada guardado, verificar con `cadcraft-cli info` que el conteo de
  entidades no bajó.
- No prometas fidelidad total contra AutoCAD. Validá el round-trip.

## Catálogo de bloques

`CAD_Blocks/` tiene 71 bloques (mobiliario, artefactos, instalaciones). Usalos;
no dibujes símbolos a mano. El índice está en `CAD_Blocks/index.json`.

## Juego de láminas

Antes de abrir `planos.py` o `planos_lib.py`: leer **`PLAYBOOK.md` §2** (índice de
funciones por línea) y §3 (comandos). No leer los archivos completos.

- Build parcial por hoja: `python3 planos.py L07`.
- Gate de láminas: `python3 tools/qa_laminas.py out/L07.dxf`.
- Gate de geometría: `python3 tools/qa_geometria.py out/L07.dxf`.
- Nunca leer un `.dxf` completo: se consulta con los gates, `find_text` o
  `query_entities`.

## Errores que ya se pagaron (no repetir)

- Un gate que miente es peor que no tener gate: probalo contra
  `tools/mk_dxf_roto.py`.
- La barra de escala a 1:25 se sale de la hoja si no se ajustan los tramos.
- Las marcas de corte no deben invadir la cadena de cotas.
- Las fachadas necesitan niveles (+0,00 / +2,90 / +5,75 / +6,55).
- Las redes de agua van en capas separadas y empotradas en el muro.
- Un bloque puede estar dentro de una mesada, nunca invadir el barrido de una
  puerta.
