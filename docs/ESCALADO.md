# ESCALADO — cómo producir viviendas nuevas sin empezar de cero

Este documento explica el paquete que hace repetible el trabajo: `briefs/`,
`typologies/`, `casos/`, `schemas/`, `tools/` y los workflows de `.clinerules/`.
La idea es simple: **no se depende de la memoria del modelo**. Se reutiliza un
caso que ya funcionó, se adapta con una tipología y se valida con reglas
determinísticas.

## 1. El flujo

```
brief.json
   +
typologies/<id>.json
   +
casos/<seed>/spec.json + decisiones.md
   +
rules_caba.json
        │
        ▼
  new_case.py  →  casos/<slug>/spec.json
        │
        ▼
  validate_spec.py  →  plan.py  →  check.py  →  reporte ok
        │
        ▼
  Nivel 1: DXF + PNG/DWG + reporte
        │
        ├── (aprobación del cliente)
        ▼
  Nivel 2: planos.py + qa_laminas.py + qa_geometria.py → 13 láminas
```

## 2. Las tres piezas

| Pieza | Qué es | Cambia por proyecto |
|---|---|---|
| **Brief** (`briefs/`) | Lo que pide el cliente: lote, programa, objetivo, restricciones. | Sí, siempre. |
| **Tipología** (`typologies/`) | Una solución que ya funcionó para ese tipo de lote: implantación, programa, medidas default y spec semilla. | No; se reutiliza o se agrega una nueva. |
| **Caso** (`casos/`) | El proyecto concreto: brief, spec, decisiones, métricas y salidas. | Sí; es el registro del proyecto. |

El **caso semilla** es la parte de "inspiración": el agente lee el spec que ya
pasó el validador y las decisiones de ese caso, y adapta. No es fine-tuning ni
memoria del modelo: es un archivo que se puede leer, comparar y versionar.

## 3. Dos niveles de entrega

### Nivel 1 — planta (barato)

- Un spec por planta.
- `validate_spec.py` + `plan.py` + `check.py`.
- Salida: DXF, reporte, PNG/DWG/PDF si `cadcraft-cli` está.
- Es el nivel que se usa para explorar, iterar con el cliente y aprobar el
  partido.

### Nivel 2 — juego de láminas (caro)

- 13 láminas A2: planta, techos, cortes, fachadas, contrafrente, laterales,
  instalaciones sanitaria/eléctrica/gas, detalles y planilla.
- `planos.py` + `planos_lib.py` + `CAD_Blocks/` + dos gates.
- **`planos.py` es específico del caso de referencia (Nivel 2).** Vive en
  `examples/nivel2/` como plantilla: para un proyecto nuevo hay que copiarlo y
  adaptarlo (o generalizarlo). No es un generador genérico todavía.
- Se produce **después** de aprobar la planta, no antes.

## 4. Costo real y modelo de costo

La sesión de referencia que produjo el ejemplo de Nivel 2 (juego de 13 láminas)
midió:

| Métrica | Valor |
|---|---|
| Llamadas (respuestas del asistente con métricas) | 1.192 |
| Tokens de entrada | 190.212.921 |
| Tokens de salida | 372.747 |
| Cache read | 187.367.040 |
| Cache hit | 98,5 % |
| Costo total | US$ 0,735 |
| Tokens de entrada por llamada | ~159.600 |

La mayor parte del costo no fue dibujar: fue **releer contexto** y **reintentar
comandos**. El protocolo de `PLAYBOOK.md` §8 y `.clinerules/40-estilo.md` ataca
eso.

### Estimación para un caso nuevo

| Escenario | Llamadas estimadas | Costo estimado |
|---|---|---|
| Nivel 1, semilla que ya pasa, pocas iteraciones | 30–80 | US$ 0,02–0,10 |
| Nivel 1, partido nuevo, varias iteraciones | 80–200 | US$ 0,05–0,20 |
| Nivel 2, adaptar el juego de 13 láminas | 300–800 | US$ 0,20–0,60 |

Son **órdenes de magnitud**, no promesas: dependen del contexto que se lea, de
los reintentos y de si se usa cache. Medí siempre con `usage.py`.

### Medir y poner techo

```bash
python3 tools/usage.py --project cad-agent
python3 tools/usage.py --project cad-agent --by-project
python3 tools/usage.py --project cad-agent --max-cost 1.00 --max-calls 1500
```

`usage.py` lee `~/.cline/data/sessions/*/*.json` y los `*.messages.json` (métricas
por respuesta). No lee credenciales. El estado `failed` de una sesión es del
proceso, no del entregable.

## 5. Cómo agregar un caso

1. Escribir el brief en `briefs/<slug>.json`.
2. Crear el caso:
   ```bash
   python3 tools/new_case.py --brief briefs/<slug>.json --slug <slug>
   ```
3. Adaptar el spec y correr:
   ```bash
   python3 tools/validate_spec.py casos/<slug>/spec.json
   ./run.sh casos/<slug>/spec.json out/<slug>
   ```
4. Con `ok: true`, actualizar `case.json` y `decisiones.md`.
5. Medir el costo y anotarlo.

## 6. Cómo agregar una tipología

1. Partir de un caso que ya pasó `check.py` con `ok: true`.
2. Copiar su spec a un archivo semilla (o usar el del caso).
3. Crear `typologies/<id>.json` con la estructura de las existentes:
   `lote`, `implantacion`, `plantas`, `programa`, `ambientes_semilla`,
   `defaults`, `semilla`, `reglas`, `salidas`, `notas`.
4. Verificar que `new_case.py --typology ...` genere un caso que corra.
5. Anotar en `notas` qué se reutiliza y qué hay que cambiar.

## 7. Cómo agregar una regla

1. Agregar el mínimo en `rules_caba.json` (con fuente y disclaimer).
2. Si la regla necesita geometría nueva, agregarla en `check.py` (pedir permiso:
   es archivo protegido).
3. Agregar el chequeo equivalente en `validate_spec.py` si es barato.
4. Probar con un spec que viole la regla y con uno que la cumpla.

## 8. Qué es escalable y qué no

### Sí

- Viviendas unifamiliares entre medianeras o en esquina.
- Una o dos plantas, con programa residencial.
- Reutilización de partidos, medidas, bloques y lecciones.
- Validación determinística de habitabilidad.
- Medición de costo por proyecto.

### Todavía no

- **Edificios de departamentos**: `plan.py` es de una planta; faltan núcleo,
  escaleras, evacuación, medianeras y unidades repetidas.
- **Estructura**: no hay plano ni memoria de cargas.
- **Instalaciones calculadas**: los isométricos son conceptuales; no hay
  caudales, diámetros, pendientes ni secciones.
- **FOS/FOT/retiros**: se declaran, no se verifican contra el Código Urbanístico.
- **Nivel 2 genérico**: `planos.py` (en `examples/nivel2/`) está hecho para un
  caso de referencia. Generalizarlo es el próximo salto de escala.
- **Firma profesional**: el sistema no firma ni presenta.

## 9. Checklist de un proyecto nuevo

- [ ] Brief completo (lote, programa, objetivo, restricciones).
- [ ] Tipología elegida (o creada a partir de un caso que pasa).
- [ ] Caso creado con `new_case.py`.
- [ ] `validate_spec.py` sin errores.
- [ ] `run.sh` con `ok: true` y 0 errores.
- [ ] `case.json` actualizado.
- [ ] `decisiones.md` escrito.
- [ ] Costo medido.
- [ ] Si hay Nivel 2: `qa_laminas` y `qa_geometria` en verde.
- [ ] Deudas conocidas declaradas al cliente.

## 10. Mapa del paquete

| Ruta | Para qué |
|---|---|
| `briefs/` | Entradas de proyecto. |
| `typologies/` | Soluciones reutilizables + spec semilla. |
| `casos/` | Proyectos concretos + decisiones. |
| `schemas/spec.schema.json` | Contrato del spec. |
| `tools/validate_spec.py` | Preflight barato del spec. |
| `tools/new_case.py` | Crea un caso desde brief + tipología. |
| `tools/usage.py` | Costo, llamadas y cache por proyecto. |
| `.clinerules/` | Reglas duras + workflows (`/nueva-vivienda`, etc.). |
| `docs/ESCALADO.md` | Este documento. |
| `PLAYBOOK.md` | Método de Nivel 2, gates y protocolo de bajo costo. |
| `AGENTS.md` | Cómo trabaja el agente. |

## 11. Preguntas frecuentes

**¿Se puede reutilizar lo anterior para inspirar un diseño nuevo?**
Sí: se elige un caso semilla, se lee su spec y sus decisiones, se adapta la
tipología y se valida. La reutilización es explícita y auditable; no depende de
que el modelo "se acuerde".

**¿Escala a muchos proyectos?**
Para viviendas unifamiliares, sí: el costo marginal baja porque el brief y la
tipología acotan el problema y el validador evita iteraciones caras. El límite
está en Nivel 2, que hoy es artesanal por proyecto.

**¿Se puede cambiar de municipio?**
Sí, pero `rules_caba.json` es de CABA. Para otro municipio hay que crear un
`rules_<municipio>.json` y verificar los mínimos. No copiar valores sin fuente.

**¿El agente puede tocar archivos fuera del proyecto?**
No. `.clinerules/00-alcance.md` es una regla de instrucción, no un sandbox. La
garantía real es no darle herramientas fuera del proyecto y revisar los diffs.
