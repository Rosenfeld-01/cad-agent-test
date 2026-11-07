# briefs/ — entradas de proyecto

Un **brief** es lo que pide el cliente, en lenguaje de proyecto: lote, programa,
objetivo, restricciones y preferencias. No es un spec: todavía no tiene muros ni
ambientes. El agente lo convierte en spec usando una tipología y un caso semilla.

```
brief.json  +  typologies/<id>.json  +  casos/<seed>/  →  spec.json
```

## Campos

| Campo | Obligatorio | Para qué |
|---|---|---|
| `slug` | sí | Nombre del caso. Debe coincidir con la carpeta. |
| `titulo` | sí | Nombre legible. |
| `fecha` | sí | ISO `YYYY-MM-DD`. |
| `tipologia` | sí | ID de `typologies/`. |
| `lote` | sí | Frente, fondo, superficie, medianeras/esquina. |
| `plantas` | sí | 1 o 2. |
| `programa` | sí | Dormitorios, baños, toilette, cocina, lavadero, cochera, oficina. |
| `objetivo` | sí | Superficie objetivo y altura libre. |
| `restricciones` | sí | Retiros, espesores, pasillo mínimo, factor de ventana. |
| `preferencias` | no | Orientación, patio, materialidad, terminaciones. |
| `entregable` | no | Nivel 1 (planta) o Nivel 2 (láminas). |
| `notas` | no | Contexto, pedidos especiales, cosas a verificar. |

## Cómo crear un caso desde un brief

```bash
python3 tools/new_case.py \
  --brief briefs/<slug>.json \
  --typology typologies/casa_entre_medianeras_8.66x20.json \
  --slug <slug>
```

## Brief vs. tipología vs. caso

- **Brief:** qué pide el cliente. Cambia en cada proyecto.
- **Tipología:** qué solución ya funcionó para ese tipo de lote. Se reutiliza.
- **Caso:** el proyecto concreto con su spec, sus decisiones y sus resultados.

## Checklist antes de arrancar

- [ ] El lote está identificado (frente, fondo, esquina/medianeras).
- [ ] El programa está claro (dormitorios, baños, cocina, lavadero).
- [ ] La superficie objetivo es realista para el lote.
- [ ] Está claro si el entregable es Nivel 1 (planta) o Nivel 2 (láminas).
- [ ] Las normas locales están identificadas (CABA u otro municipio).
- [ ] Hay un caso semilla razonable en `casos/`.

## Ejemplo

`_plantilla/brief.json` es el esqueleto vacío: copialo a `briefs/<slug>.json` y
completá lote, programa, objetivo y restricciones. La tipología
`casa_entre_medianeras_8.66x20` trae un spec semilla que ya pasa el validador y
sirve de punto de partida para adaptar el programa al brief.
