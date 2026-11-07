# CAD_Blocks — biblioteca de bloques de Vivienda 02

Biblioteca paramétrica generada por `blocks_build.py`. **70 bloques** en DXF,
pensados para las 12 láminas del juego de planos y para reutilizar en cualquier
otra vivienda.

## Convención (importante)

| Ítem | Valor |
|---|---|
| Unidades | **metros** ($INSUNITS = 6), igual que el resto del proyecto |
| Escala de dibujo | 1:1 real (un inodoro mide 0,40 × 0,70 m en el bloque) |
| Punto de inserción | **(0,0) = $INSBASE**, esquina inferior izquierda / gozne |
| Orientación | el bloque "mira" hacia **+Y** (arriba) |
| Capa | **0** — hereda color y espesor de la capa donde se inserta |
| Escala de inserción en lámina | `escala_lámina / 1000` → **1:50 ⇒ 0,02** |

Ejemplo: en una lámina 1:50, un inodoro se inserta con `xscale = yscale = 0.02`
y mide 0,40 × 0,70 m = 8 × 14 mm de papel.

## Insertar desde CADCraft / AutoCAD

```
INSERT
  nombre: A-INODORO
  archivo: CAD_Blocks/A-INODORO.dxf      (CADCraft lo define desde su model space)
  punto: 3.20,1.45
  escala: 0.02
  rotación: 0/90/180/270
```

Desde Python (ezdxf) los bloques se dibujan con `blocks_build.dibujar()` sobre
la definición de bloque del dibujo destino, sin pasar por el DXF.

## Atributos

Los atributos son invisibles por defecto y se completan al insertar:

| Bloque | Atributo | Uso |
|---|---|---|
| `X-CORTE` | `LETRA` | letra del corte (A, B…) |
| `X-NIVEL` | `NIVEL` | cota de nivel (+2,82) |
| `X-PENDIENTE` | `PEND` | valor de pendiente (1 %) |
| `X-BURBUJA-DETALLE` | `DETALLE`, `PLACA` | número de detalle y lámina |

## Contenido

| Categoría | Bloques | Ejemplos |
|---|---|---|
| Aberturas | 12 | `A-PUERTA-080`, `A-VENTANA-150`, `A-PORTON-300` |
| Mobiliario | 15 | `A-CAMA-2PL`, `A-SOFA-3`, `A-MESADA-300` |
| Baño | 6 | `A-INODORO`, `A-DUCHA-090`, `A-BANERA-170` |
| Escalera | 1 | `A-ESCALERA-16` (16 alzadas, 2 tramos) |
| Exterior | 6 | `A-ARBOL-A`, `A-AUTO`, `A-TANQUE-1000` |
| Eléctrica | 11 | `E-BOCA-TECHO`, `E-TOM`, `E-TABLERO` |
| Gas | 6 | `G-MEDIDOR`, `G-CALEFON`, `G-REJILLA` |
| Sanitaria | 7 | `S-CAMARA-INS`, `S-CANILLA`, `S-VENTILACION` |
| Símbolos | 6 | `X-NORTE`, `X-CORTE`, `X-NIVEL` |

El detalle de medidas de mobiliario sigue `MEDIDAS_CABA.md` (cama 2 plazas
1,40 × 1,90; placard 0,60 de profundidad; paso libre de puerta de baño 0,80).

## Archivos

- `<NOMBRE>.dxf` — un archivo por bloque, con la geometría en el model space y
  la definición homónima (insertable desde CADCraft y desde ezdxf).
- `index.json` — nombre, categoría, descripción, medidas y atributos de cada bloque.
- `catalogo.dxf` / `catalogo.png` — lámina índice A0 con todos los bloques.

## Regenerar

```
python3 blocks_build.py     # reescribe los 70 DXF + index.json
python3 blocks_catalog.py   # rehace catalogo.dxf y catalogo.png
```

## Alcance

Son símbolos de **dibujo** simplificados (líneas, polilíneas, arcos y textos),
no familias paramétricas ni bloques dinámicos. Los símbolos de instalaciones son
la representación de práctica local del IRAM 2031; no reemplazan la
documentación técnica de cada especialidad.
