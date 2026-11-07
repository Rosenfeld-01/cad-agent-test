# 20 — Normativa

`rules_caba.json` contiene **valores de partida**, no asesoramiento legal. El
validador sólo aplica las reglas escritas ahí.

## Antes de entregar

- Verificar cada valor contra el Código de Edificación de CABA (Ley 6100) y el
  Código Urbanístico (Ley 6099) vigentes, o la normativa del municipio del
  proyecto.
- **FOS/FOT/retiros no están en `rules_caba.json`**: dependen de la parcela y del
  Código Urbanístico. Si el proyecto los necesita, verificar y dejarlos escritos
  en el `case.json`; no inventarlos.
- Si falta una regla: **preguntar**. No "aproximar" una norma ni copiar un número
  de otro municipio.
- El plano lo revisa y firma un profesional matriculado. No firmes ni presentes.

## Mínimos que ya aplica `check.py`

- Altura libre, áreas y lados mínimos por tipo de ambiente.
- Ancho de puertas de entrada, interiores y baños.
- Espesores mínimos de muro.
- Iluminación (20 %) y ventilación (5 %) calculadas desde la geometría de las
  ventanas, no desde un número declarado.
- Circulación: 1,00 m (0,95 m en parcelas de frente ≤ 8,66 m).

## Fuente de práctica

`MEDIDAS_CABA.md` tiene las medidas de práctica y los mínimos. Si hay conflicto
entre la práctica y la norma, manda la norma vigente; si no está clara, preguntá.
