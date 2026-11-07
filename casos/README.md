# casos/ — biblioteca de proyectos

Cada carpeta es un **caso**: un proyecto concreto con su brief, sus specs, sus
decisiones y sus resultados. La idea es que el próximo trabajo no arranque de
cero: se busca el caso más parecido, se lee qué funcionó y qué se corrigió, y se
adapta la tipología.

```
casos/<slug>/
├── case.json        # metadata: tipología, specs, salidas, estado, métricas
├── brief.json       # qué pidió el cliente (entrada)
├── spec.json        # fuente de verdad del diseño (o spec_pb/pa)
├── decisiones.md    # qué se hizo, qué funcionó, qué no repetir
└── (salidas generadas en out/<slug>/)
```

## Regla de oro

**El `case.json` y el `decisiones.md` son memoria; el `spec` es la verdad.**
Nunca se edita el DXF. Si algo está mal, se corrige el spec y se regenera.

## Campos de `case.json`

| Campo | Para qué |
|---|---|
| `slug` | Nombre de la carpeta. |
| `titulo` | Nombre legible del proyecto. |
| `fecha` | Fecha de cierre (ISO). |
| `estado` | `borrador`, `en-curso`, `ok`, `bloqueado`, `archivado`. |
| `nivel` | `1` = planta; `2` = juego de láminas. |
| `tipologia` | ID en `typologies/`. |
| `brief` | Ruta al brief (relativa a la raíz del proyecto). |
| `specs` | Rutas a los specs (relativas a la raíz). |
| `salidas` | Rutas a DXF/PNG/PDF/reportes. |
| `metricas` | Superficies, ambientes, láminas, gates. |
| `lecciones` | Ruta al `decisiones.md`. |
| `tags` | Búsqueda: `2-dormitorios`, `dos-plantas`, etc. |

Las rutas son **relativas a la raíz** (`/home/joaquin/proyectos/cad-agent-test`), no
a la carpeta del caso. Así los casos viejos pueden apuntar a los specs
canónicos sin duplicarlos.

## Casos existentes

Todavía no hay casos: este repositorio es el framework. El primero se crea con
el comando de abajo a partir de `briefs/_plantilla/brief.json` y la tipología
`casa_entre_medianeras_8.66x20`.

## Crear un caso nuevo

```bash
python3 tools/new_case.py \
  --brief briefs/<slug>.json \
  --typology typologies/casa_entre_medianeras_8.66x20.json \
  --slug <slug>
```

Luego:

```bash
python3 tools/validate_spec.py casos/<slug>/spec.json
./run.sh casos/<slug>/spec.json out/<slug>
```

## Cerrar un caso

1. `validate_spec.py` sin errores.
2. `run.sh` con `ok: true`.
3. Si hay láminas: `qa_laminas.py --all` y `qa_geometria.py --all` en verde.
4. Actualizar `case.json` (`estado`, `metricas`, `salidas`).
5. Escribir 5–10 líneas en `decisiones.md` con lo que sirve para el próximo caso.
6. Registrar el costo con `python3 tools/usage.py --project cad-agent`.

## Qué NO hacer

- No crear un caso sin brief: el brief es la entrada y la trazabilidad.
- No copiar un spec y decir que está listo sin correr el validador.
- No borrar `decisiones.md`: es lo que hace que el sistema aprenda.
- No promover a Nivel 2 (láminas) sin aprobación explícita: es la parte cara.
