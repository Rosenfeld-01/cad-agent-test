# typologies/ — memoria de diseño reutilizable

Una **tipología** no es un plano: es un paquete de decisiones que ya funcionó
(lote, implantación, programa, medidas default y un spec semilla que pasa el
validador). El agente la usa como punto de partida para un caso nuevo y la
adapta al brief. Esto es lo que hace escalable al sistema: no se "inventa" cada
vivienda desde cero ni se depende de la memoria del modelo.

```
brief  +  tipología  +  rules_caba.json  +  caso semilla
                         ↓
                 spec nuevo (JSON)
                         ↓
        validate_spec.py → plan.py → check.py
```

## Qué contiene una tipología

| Campo | Para qué |
|---|---|
| `id` | Identificador estable. Es el que usa `new_case.py --typology`. |
| `lote` | Frente, fondo, superficie, si es entre medianeras o esquina. |
| `implantacion` | Retiros, huella, FOS/FOT estimados. **Verificar siempre.** |
| `plantas` | 1 o 2. |
| `programa` | Cantidad de dormitorios, baños, oficina, cochera, etc. |
| `ambientes_semilla` | Ambientes del caso que sirvió de base, con m² y lado mínimo. |
| `defaults` | Alturas, espesores, puertas, ventanas, niveles. |
| `semilla.specs` | Spec(s) JSON que se copian al crear un caso. |
| `semilla.caso_referencia` | Caso documentado en `casos/` para leer decisiones. |
| `reglas` | Archivo de reglas que aplica el validador. |
| `salidas` | `planta` (Nivel 1) o `juego_laminas` (Nivel 2). |
| `notas` | Lecciones y advertencias. |

## Tipologías disponibles

| ID | Lote | Plantas | Semilla | Nivel |
|---|---|---|---|---|
| `casa_entre_medianeras_8.66x20` | 8,66 × 20,00 m (173,2 m²) | 1 | `typologies/semillas/casa_8.66x20.json` | 1 |

## Cómo crear un caso desde una tipología

```bash
cd ~/proyectos/cad-agent-test
python3 tools/new_case.py \
  --brief briefs/<slug>.json \
  --typology typologies/casa_entre_medianeras_8.66x20.json \
  --slug <slug>
```

El comando copia el spec semilla a `casos/<slug>/`, escribe el `brief.json`
y un `decisiones.md` inicial, y deja el `case.json` en estado `borrador`.
Después se edita el spec (nunca el DXF) y se corre:

```bash
python3 tools/validate_spec.py casos/<slug>/spec.json
./run.sh casos/<slug>/spec.json out/<slug>
```

## Cómo agregar una tipología nueva

1. Partí de un caso que ya pasó `check.py` con `ok: true`.
2. Copiá su spec a `spec_<algo>.json` (o dejalo en `casos/<slug>/`).
3. Creá `typologies/<id>.json` copiando la estructura de una existente.
4. Completá `lote`, `implantacion`, `programa`, `defaults`, `semilla` y `notas`.
5. Verificá que `new_case.py --typology ...` genere un caso que corra.
6. Anotá en `notas` qué se reutiliza y qué hay que cambiar.

## Reglas de oro

- **Una tipología no es normativa.** FOS/FOT/retiros son estimaciones: se
  verifican contra el Código Urbanístico de CABA y la parcela real.
- **La semilla debe pasar el validador.** Si la semilla no pasa, no sirve como
  base: primero se arregla.
- **No dupliques el spec canónico.** Las tipologías referencian specs; los casos
  nuevos copian la semilla y quedan autocontenidos.
- **Nivel 1 antes que Nivel 2.** Primero la planta (barata); el juego de láminas
  se produce sólo después de la aprobación del cliente.
