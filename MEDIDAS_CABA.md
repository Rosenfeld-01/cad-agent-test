# Medidas de referencia — vivienda en CABA

Dos bloques: **mínimos normativos** (Código de Edificación de CABA) y **medidas
de práctica profesional** (no normativas, para que el plano funcione).

> Verificar siempre contra el texto vigente. Esto es una ayuda de proyecto, no
> asesoramiento legal.

## A. Mínimos normativos (CE CABA, Ley 6100 / texto ordenado Ley 6438)

| Concepto | Lado mín. | Superficie mín. | Artículo |
|---|---|---|---|
| Altura libre de local | — | 2,40 m | 3.3.1.2.1 |
| Local único de 1ra clase | 2,80 m | 18,00 m² | 3.8.9.1 |
| Local de 1ra clase (estar) | 2,80 m | 9,00 m² | 3.8.9.1 |
| Estar-comedor-dormitorio | 2,80 m | 15,00 m² | 3.8.1.1.1 |
| Estar-comedor-dormitorio-cocina | 2,80 m | 18,00 m² | 3.8.1.1.1 |
| Dormitorio (3ra clase) | 2,50 m | 7,50 m² | 3.8.9.1 |
| Baño tipo I (In-Lo-Du c/Ba) | 1,50 m | 3,00 m² | 3.8.1.1.1 |
| Baño tipo II (In-Lo-Du s/Ba) | 1,50 m | 2,50 m² | 3.8.1.1.1 |
| Baño tipo III (In-Lo-Du) | 0,90 m | 1,40 m² | 3.8.1.1.1 |
| Baño tipo IV (In-Du) | 0,90 m | 1,20 m² | 3.8.1.1.1 |
| Balcón, terraza o patio | 1,20 m | 1,50 m² | 3.8.9.1 |
| Espacio de guardado | 0,60 m | 1,00 m² | 3.8.9.1 |
| Circulación interna | 1,00 m | — | 3.8.9.1 |
| Circulación en parcela ≤ 8,66 m | 0,95 m | — | 3.8.9.1 |
| Vano de acceso en parcela angosta | 0,85 m | — | 3.8.9.1 |
| Puerta de baño tipo II (paso libre) | 0,80 m | — | 3.8.9.1 |
| Luz de paso de cocina | 0,90 m | — | 3.8.9.1 |
| Espacio para cocinar integrado | 0,80 m paso | +3,00 m² | 3.8.9.1 |
| Iluminación natural | — | 20 % de la sup. del local | 3.8.1.1.3 |
| Ventilación | — | 5 % de la sup. del local | 3.8.1.1.3 |

Notas:

- En viviendas con **2 o más dormitorios**, el **50 %** puede iluminar y
  ventilar a **patio vertical** (3.8.1.1.3).
- La **Unidad de Vivienda Mínima** (18 a 25,50 m² de locales de permanencia) es
  un régimen especial; no es el objetivo de este proyecto.
- **FOS, FOT y retiros no están acá**: dependen del Código Urbanístico y de la
  parcela concreta. No los inventes.

## B. Práctica profesional (no normativo)

| Concepto | Valor usual |
|---|---|
| Muro exterior | 0,20 m |
| Muro interior / tabique | 0,10 m |
| Puerta de entrada | 0,90 m |
| Puerta interior | 0,80 m |
| Ventana: antepecho | 0,90 m |
| Ventana: altura | 1,40 m |
| Dintel / altura de paso | 2,10 m |
| Mesada de cocina | 0,60 m prof. × 0,90 m alto |
| Placard | 0,60 m de profundidad |
| Cama 2 plazas | 1,40 × 1,90 m |
| Cama 1 plaza | 0,90 × 1,90 m |
| Inodoro | 0,40 × 0,70 m |
| Lavatorio | 0,50 × 0,40 m |
| Ducha | 0,90 × 0,90 m |
| Bañera | 1,70 × 0,70 m |
| Cochera | 2,50 × 5,00 m |
| Escalera (si hubiera) | huella 0,28 m, contrahuella 0,18 m, ancho 0,90–1,00 m |
| Módulo de diseño | 0,10 m |

## C. Cómo se valida

`check.py` aplica el bloque A desde `rules_caba.json` y calcula iluminación y
ventilación **desde la geometría real de las ventanas** del spec. El bloque B es
criterio de diseño: el agente lo usa para que el plano sea habitable, pero el
validador no lo exige.
