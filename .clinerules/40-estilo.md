# 40 — Estilo, convenciones y costo

## Idioma y tono

- Respondé y escribí comentarios en **español**.
- Sé concreto: medidas, archivos, comandos. Sin relleno.
- Si algo no se puede verificar, decilo; no lo inventes.

## Convenciones del proyecto

- Unidades: **metros** (1 unidad = 1 m). `$INSUNITS = 6`.
- Capas: `A-WALL`, `A-DOOR`, `A-WIN`, `A-AREA`, `A-ANNO`, `A-DIM`, `A-AXIS`.
- Ambientes: el polígono `A-AREA` lleva el nombre en XDATA (appid `CADAGENT`).
- Altura de texto mínima: 0,15 m (ver `rules_caba.json`).
- Cotas en metros, con dos decimales.

## Protocolo de bajo costo (obligatorio)

La mayor parte del costo no es dibujar: es **volver a leer lo mismo** y
**reintentar comandos**. Reglas:

1. **Índice antes que archivo.** Antes de abrir un archivo grande:
   `grep -n '^def '`, `grep -n '^##'` o el índice del `PLAYBOOK.md`.
2. **Ediciones agrupadas.** Todas las ediciones independientes en una sola
   respuesta.
3. **Build parcial.** `python3 planos.py L06` mientras se trabaja esa hoja.
4. **Gate antes que ojo.** Primero `qa_laminas.py` / `check.py`; PNG sólo si el
   gate pasa y algo se ve raro.
5. **Render con recorte** (`window`) y ancho ≤ 1200 px; un A2 completo no se lee.
6. **Nunca `cat` de todo.** Redirigir a `/tmp/x.txt` y leer el rango, o usar
   `grep`/`tail`.
7. **Scripts en `tools/`**, no en `/tmp` que se pierde.
8. **No repetir un comando que falló** sin cambiar algo. Si falla dos veces, leer
   el error y cambiar el enfoque.
9. **No leer `.dxf` completos**: se consultan con los gates.

## Costo

- Medir con:
  ```bash
  python3 tools/usage.py --project cad-agent
  python3 tools/usage.py --project cad-agent --by-project
  ```
- Para poner un techo:
  ```bash
  python3 tools/usage.py --project cad-agent --max-cost 1.00 --max-calls 1500
  ```
- Al cerrar un caso, anotar el costo agregado en `decisiones.md`. Si no hay
  desglose por caso, decirlo.
- El estado `failed` de una sesión es del **proceso** (por ejemplo, se cerró el
  editor), no del entregable. Mirá el reporte `ok` y los gates.

## Al terminar, mostrar

1. Tabla de ambientes (nombre, tipo, m², lado mínimo).
2. Resultado del reporte (`ok`, errores, warnings, superficie, ventanas).
3. Rutas de los archivos generados.
4. Qué se reutilizó y qué se cambió respecto de la semilla.
5. Costo de la sesión (si está disponible).
6. Deudas conocidas (FOS/FOT, estructura, instalaciones, firma).

## Qué NO hacer

- No inventar cotas ni superficies.
- No usar capturas de pantalla como fuente de verdad geométrica.
- No entregar sin reporte `ok: true`.
- No firmar ni presentar: el plano lo revisa y firma un profesional matriculado.
