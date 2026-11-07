# PLAYBOOK — método del juego de planos de vivienda con agente + CADCraft

Cuaderno de obra del juego de láminas (Nivel 2) escrito para **reusar el método
sin repetir el trabajo** y **gastando una fracción de los tokens**. No es un
README de usuario: es lo que funcionó, lo que rompió y cómo se arregló.

> El código de referencia del Nivel 2 vive en `examples/nivel2/` (sus specs son
> `spec_pb.json` / `spec_pa.json`). Los números de §1 corresponden a esa corrida
> de referencia. El catálogo de defectos de §6 también está en
> `docs/DEFECTOS_CONOCIDOS.md` (documento independiente y versionable).

---

## 1. Qué se construyó

Vivienda entre medianeras, lote 10,00 × 28,00 m, ancho útil 6,60 m,
planta baja + planta alta + azotea. Todo el juego en **A2 (594 × 420 mm)**.
Las plantas de arquitectura **L01/L02/L03** se emiten a **escala real** (1 unidad
= 1 m del proyecto; marco = A2 × 50 = 29,70 × 21,00 u; se plotéa a 1:50). El
resto de las láminas queda en **metros de papel** (1 unidad = 1 m de papel). Los
gates derivan el factor de escala del ancho del marco X-FRAME, así miden igual
en ambos casos.

| Hoja | Título | Escala | Entidades |
|---|---|---|---|
| L01 | PLANTA BAJA | 1:50 | 429 |
| L02 | PLANTA ALTA | 1:50 | 526 |
| L03 | PLANTA DE TECHO | 1:50 | 242 |
| L04 | CORTE A-A | 1:50 | 388 |
| L05 | CORTES B-B Y C-C | 1:50 | 376 |
| L06 | FACHADA PRINCIPAL | 1:25 | 241 |
| L07 | CONTRAFRENTE | 1:25 | 243 |
| L08 | LATERAL ESTE | 1:50 | 395 |
| L09 | LATERAL OESTE | 1:50 | 539 |
| L10 | INSTALACION SANITARIA | 1:50 | 576 |
| L11 | INSTALACION ELECTRICA Y GAS | 1:50 | 587 |
| L12 | DETALLES Y SUPERFICIES | 1:10 | 502 |
| L13 | PLANTA DE CONJUNTO | 1:100 | 333 |

Las 13 láminas son de la **REV. 1** (ver §11): `TOTAL = 13` y el rótulo dice
"JUEGO L01/L13".


Datos de la vivienda (los consume `planos_lib`):

- Niveles: PB +0,00 · PA +2,90 · azotea +5,75 · parapeto +6,55 (constante en las
  cuatro fachadas) · módulo del tanque +7,30. Altura libre 2,80 PB / 2,70 PA.
  Antepecho 0,90. **La REV. 1 eliminó el techo de cocina +2,95/+3,30.**
- **REV. 1 (partido vigente)**: PB 8 ambientes / 101,90 m² · PA 12 ambientes /
  94,39 m² · 6 y 9 puertas · 7 y 8 ventanas. FOS 0,396 · FOT ≈ 0,71.
  Detalle del rediseño en §11.
- `check.py` (sobre el DXF de `plan.py`, no sobre las láminas): PB 7/7
  ambientes, 5 puertas, 7 ventanas (20,16 m²), 95,55 m²; PA 10/10, 7 puertas,
  5 ventanas (13,98 m²), 76,93 m². Reglas: Código de Edificación de CABA,
  arts. 3.3.1.2.1 (altura), 3.8.9.1 y 3.8.1.1.1 (áreas y lados), 3.8.1.1.3
  (iluminación y ventilación).
- Huella PB 6,60 × 16,80 m = 110,88 m² → FOS 0,396 (declarado, no verificado
  contra el código urbanístico; ver §7).

## 2. Mapa del código (leer esto antes que los archivos)

Un agente que abre `planos.py` (63 KB, 1471 líneas) gasta ~20 000 tokens por
lectura y lo va a leer muchas veces. Este índice alcanza para casi todo:
`grep -n '^def ' planos.py` y `grep -n '^def \|^class ' planos_lib.py`.

**`planos.py`** — una función por lámina, todas con la misma firma `def lXX() -> Lamina`:

| Línea | Función | Qué hace |
|---|---|---|
| 1-60 | cabecera | imports, `OUT`, `FECHA`, `TOTAL = 13` |
| 227 | `l01` | planta baja: muros, aberturas, mobiliario, cotas, rótulo |
| 290 | `l02` | planta alta (misma receta, otro spec) |
| 331 | `l03` | planta de techo: cubiertas, tanque, pendientes |
| 431 | `l04` | corte A-A (usa `planos_lib.corte`) |
| 463 | `l05` | cortes B-B y C-C en la misma hoja |
| 557 | `l06` | fachada principal (usa `planos_lib.fachada`) |
| 585 | `l07` | contrafrente (ídem, con `z_oculto`) |
| 662 | `l08` | lateral este (helper compartido con L09) |
| 694 | `l09` | lateral oeste |
| 840 | `l10` | instalación sanitaria (planta + isométrico esquemático) |
| 1039 | `l11` | instalación eléctrica y gas |
| 1192 | `l12` | detalles constructivos + planilla de superficies |
| 1428 | `SHEETS` | dict `{"L01": l01, ...}` |
| 1444 | `main` | `python3 planos.py [L01 L04 ...]` → `out/Lxx.dxf` |

**`planos_lib.py`** — todo lo reutilizable (no se toca al agregar una hoja):

| Línea | Objeto | Para qué |
|---|---|---|
| 37 | `FORMATOS` | A4/A3/A2/A1/A0 en metros |
| 44 | `CAPAS` | capa → (color, lineweight). **Fuente de verdad de capas** |
| 61 | `ALINEACION` | códigos de justificación de texto (`ml`, `tc`, …) |
| 74 | `Tr` | transformación proyecto→papel (`Tr(x0, y0, escala)`) |
| 97 | `definir_bloques` | carga los 71 `.dxf` de `CAD_Blocks/` |
| 111 | `Lamina` | marco, rótulo, `.ln .pl .tx .cir .arc .ins .solido .guardar` |
| 231-330 | `flecha cota cota_h cota_v nivel norte escala_grafica` | anotación en papel |
| 331 | `nota` | bloque de texto; **devuelve la Y final** para encadenar |
| 355 | `poner` | inserta bloque de `CAD_Blocks` con rotación 0/90/180/270 |
| 365 | `caja_rotada` | bbox de un bloque insertado (para no pisar texto) |
| 374 | `abertura` | vano: marco, hoja, sentido de giro, alféizar |
| 404 | `planta` | planta completa desde `spec` (muros + aberturas + ambientes) |
| 448 | `escalera` | escalera en U de 2 tramos (16 alzadas) |
| 503 | `tabla` | planilla; **devuelve la Y del borde inferior** |
| 535 | `leyenda` | leyenda de símbolos con muestra |
| 571 | `rayado` | hatch de líneas paralelas en una caja |
| 606 | `cano` | cañería / conducto polilínea |
| 617 | `NIVELES` | dict de niveles de la vivienda |
| 695 | `corte` | corte vertical completo desde dos specs |
| 823 | `elevacion` | fachada de un muro desde `spec` |
| 876 | `fachada` | fachada compuesta (PB + PA + cubierta) |
| 926 | `escalera_corte` | escalera vista en corte |

**Otros**: `plan.py` (una sola planta desde spec, pipeline viejo), `check.py`
(validador del spec), `rules_caba.json`, `spec_vivienda02_pb.json` /
`spec_vivienda02_pa.json` (los dos specs que alimentan L01/L02), `CAD_Blocks/`
(97 bloques 1:1 en metros, incluye la familia Modena), `tools/qa_laminas.py`
(gate de láminas) y `tools/qa_muros.py` (gate de solape de muros A-WALL).

**Muros**: `plan.wall_outline()` dibuja la unión de los sólidos de muro (una
frontera, sin rectángulos interiores); lo usan `plan.build()` y
`planos_lib.planta()`.


## 3. Comandos (los únicos que hacen falta)

```bash
cd ~/proyectos/cad-agent

# construir todo (o sólo algunas hojas: mucho más rápido para iterar)
python3 planos.py
python3 planos.py L06 L07

# validar el spec de una planta: plan.py dibuja en metros reales y check.py
# mide sobre ESE dxf (no sirve sobre las láminas, que están en metros de papel)
python3 plan.py spec_vivienda02_pb.json /tmp/pb02.dxf
python3 check.py /tmp/pb02.dxf spec_vivienda02_pb.json
python3 plan.py spec_vivienda02_pa.json /tmp/pa02.dxf
python3 check.py /tmp/pa02.dxf spec_vivienda02_pa.json

# GATE de láminas: solapes de texto, fuera de hoja, auditoría DXF
python3 tools/qa_laminas.py out/L06.dxf
python3 tools/qa_laminas.py --all out --json out/_qa.json
python3 tools/qa_laminas.py --all out --verbose

# GATE de muros (solape de muros A-WALL): sólo plantas L01/L02/L03
python3 tools/qa_muros.py out/L01.dxf out/L02.dxf out/L03.dxf

# PNG para revisar a ojo (13 hojas ~ 27 s)
for f in out/L*.dxf; do cadcraft-cli convert "$f" "${f%.dxf}.png"; done
```

**Regla**: `planos.py` y `check.py` devuelven exit 1 si algo falló. Un `status=0`
encadenado (`python3 planos.py && python3 tools/qa_laminas.py --all out`) es la
definición de "entrega cerrada".

## 4. Convenciones duras (no negociar)

1. **El model space ES la hoja.** No hay layouts ni paper space: se dibuja en
   metros de papel, A2 = 0,594 × 0,420. El margen útil del marco es 0,012.
   Si algo se sale de `0..0.594 / 0..0.420`, es un error, no una licencia.
2. **Todo pasa por `Tr`.** `Tr(x0, y0, escala)` convierte proyecto (m) a papel
   (m). Nunca se escribe una coordenada de papel calculada a mano salvo en la
   composición de la hoja (dónde va cada vista).
3. **Capas de `CAPAS`** (A-WALL, A-DOOR, A-WIN, A-AREA, A-ANNO, A-DIM, A-AXIS,
   A-MOB, A-HATCH, A-ESC, X-FRAME, I-ELE, I-SAN, I-GAS). Una capa nueva
   se agrega a `CAPAS`, no se inventa en la hoja.
4. **Alturas de texto en papel**: 0,0046 rótulo · 0,0032 título de lámina ·
   0,0022 títulos de bloque / cotas / niveles · 0,0016-0,0019 notas y
   descripciones. Un texto a 0,0022 y otro a 0,0016 pueden tocarse sin verse
   mal: por eso el gate de solapes usa tolerancia.
5. **Bloques a 1:1 en metros** (`CAD_Blocks/`, 71 bloques). Se insertan con
   `poner(lam, nombre, tr, x, y, rot)`; la escala la resuelve `poner`
   (1/escala). Antes de poner texto cerca de un bloque, `caja_rotada` da su bbox.
6. **Nada de texto "a ojo" sobre el dibujo**: cada nota/tabla/leyenda devuelve
   la Y final (`nota`, `tabla`) para encadenar la siguiente sin adivinar.
7. **Sin dependencias nuevas**: `ezdxf` + stdlib. CADCraft sólo para PNG/DWG.

## 5. Los cinco gates de calidad

| Gate | Comando | Qué detecta | Costo |
|---|---|---|---|
| **Spec** | `check.py <dxf> <spec.json>` | ambientes, superficies, aberturas, lados mínimos | 1 s |
| **Build** | `planos.py` | excepción de Python, hoja que no se genera | 3 s / 13 hojas |
| **Lámina** | `tools/qa_laminas.py` | textos superpuestos, geometría fuera de hoja, DXF inválido | 1,5 s / 13 hojas |
| **Geometría** | `tools/qa_geometria.py` | trazos duplicados, bloques que se pisan, muebles en el barrido de una puerta | 2 s / 13 hojas |
| **Ojo** | PNG + `render window=` | composición, densidad, lo que ningún script ve | 2-4 k tokens por imagen |

`tools/qa_laminas.py` en detalle:

- bbox de cada TEXT/MTEXT con ancho = `0,62 × altura × nº de caracteres`
  (factor medido sobre la fuente del rótulo), respetando rotación 0/90/180/270;
- solape = intersección > **0,4 mm × 0,5 mm** (por debajo es contacto normal
  entre cota y texto);
- fuera de hoja: bbox de **cualquier** entidad contra `0..0,594 / 0..0,420`
  con `ezdxf.bbox.extents`;
- auditoría: `doc.audit()` → errores y fixes (tiene que dar `0/0`).

`tools/qa_geometria.py` en detalle:

- **coincidentes**: dos LINE del mismo layer colineales (mismo ángulo y misma
  distancia al origen) que se solapan más de **1 mm** de papel. Es el "dibujé el
  mismo caño o la misma cota dos veces"; se cura con `Lamina.ln_unica()`, que no
  repite un segmento idéntico;
- **bloques**: INSERT cuyas cajas se pisan más del **5%** del área del menor,
  salvo **contención** (un artefacto dentro de la mesada, el medidor dentro del
  nicho): anidar no es colisionar;
- **circulación**: bloque que invade más del **25%** de la caja del barrido de
  una puerta (capa A-DOOR): el mueble que tapa la puerta.

**Nunca** confiar en un "0 solapes / 0 fuera / 0 coincidentes" sin haber probado
los gates contra un DXF roto a propósito:

```bash
python3 tools/mk_dxf_roto.py                   # escribe tools/_roto.dxf
python3 tools/qa_laminas.py tools/_roto.dxf    # debe dar 1 solape + 1 fuera
python3 tools/qa_geometria.py tools/_roto.dxf  # debe dar 1 coincidente + 1 bloque
```


## 6. Catálogo de defectos ya resueltos

Ordenados por lo que cuesta redescubrirlos. Cada uno es "síntoma → causa → arreglo".

### 6.1 Un gate que miente (el peor de todos)

- **Síntoma**: 13/13 láminas "OK" y una barra de escala 5 mm afuera de la hoja.
- **Causa**: `BoundingBox2d([entidad])` **no acepta entidades** en ezdxf 1.4.5 —
  lanza `TypeError: cannot unpack non-iterable Line object`. El `try/except:
  continue` del chequeo de "fuera de hoja" se comía el error y dejaba la lista
  vacía para *todas* las entidades: el chequeo nunca corrió.
- **Arreglo**: `from ezdxf import bbox` → `bbox.extents([e])` (devuelve
  `Vec3`; usar `.extmin.x`, `.extmax.y`, no desempaquetar).
- **Lección**: todo gate se prueba contra un DXF roto a propósito
  (`tools/mk_dxf_roto.py`); si no acusa exactamente 1 solape + 1 fuera, el gate
  está roto.

### 6.2 Barra de escala que se sale de la hoja (L06/L07)

- **Síntoma**: TEXT en x 0,586-0,599 (hoja 0,594; marco 0,582).
- **Causa**: `escala_grafica(..., 25)` con los tramos por defecto `(0,1,2,5)`
  mide `(1+1+3)/25 = 0,20 m` de papel; arrancando en 0,380 termina en 0,580 y el
  rótulo "1:25 (m)" se va afuera del marco.
- **Arreglo**: a 1:25 usar `tramos=(0, 1, 2)` → 0,08 m de barra. Regla: el ancho
  de la barra en papel (`tramos[-1]/escala`) + 0,02 tiene que entrar en la
  columna libre de la hoja.

### 6.3 Burbuja de marca de corte sobre la cota (L01/L03)

- **Síntoma**: solape entre el texto de la marca de corte y la cota `2,10`.
- **Causa**: `marca_corte` extendía la línea de corte `0,60 m` hacia el interior
  del dibujo, justo donde corre la cadena de cotas.
- **Arreglo**: extensión asimétrica `ext=(0,05, 0,60)` en la planta y
  `ext=(0,05, 0,90)` en L03: la cola corta del lado de las cotas.

### 6.4 Fachadas sin niveles (L06/L07)

- **Síntoma**: la fachada no acotaba +0,00 / +2,90 / +5,75 / +6,55.
- **Causa**: `fachada()` no dibuja marcas de nivel; se agregan en la hoja.
- **Arreglo**: `niveles_vista(lam, tr, 6.60)` — una llamada, cuatro niveles,
  alineados al borde derecho de la vista.

### 6.5 Contrafrente tapada por la cubierta de cocina (L07)

- **Causa**: el techo de cocina de PB (+2,95) está delante del plano de fachada.
- **Arreglo**: `fachada(..., z_oculto=NIVELES["TECHO_COCINA"] + 0.35)` para que
  la elevación recorte la parte oculta y dibuje el techo como línea de veo.

### 6.6 Errores de composición (los de siempre)

- **Planilla que pisa la nota de abajo**: usar la Y que devuelve `tabla()`;
  nunca recalcular `alto_fila * len(filas)` a mano (el encabezado mide distinto).
- **Texto girado 90°**: al estimar su caja, ancho ↔ alto se intercambian; si se
  calcula a mano, se subestima el ancho y aparece el solape.
- **Texto que "no molesta"**: 0,0016 vs 0,0022 se tocan y se lee mal. El gate
  tolera 0,4 × 0,5 mm de intersección; más que eso es un defecto real.
- **Densidad**: si una hoja pasa de ~560 entidades, conviene partirla o bajar
  detalle; L11 (558) es el techo práctico de este formato.

### 6.7 Entorno (esto cuesta más tokens que el CAD)

- El shell es **fish**: no hay heredocs, `$?` es `$status`, y `{ cmd; }` falla.
  Todo lo multi-línea va a un archivo (`/tmp/x.py`, `/tmp/x.sh`) y se corre con
  `bash -c`. Los reintentos por sintaxis son carísimos.
- `cat` de un archivo largo = tokens tirados. Redirigir a `/tmp/*.txt` y leer
  con `head`, `tail`, `grep -c`, o pedir sólo el rango con `read_files`.
- Los `.dxf` superan el límite de lectura: nunca se leen, se consultan con
  `qa_laminas.py`, `find_text` o `query_entities`.

### 6.8 Redes de agua dibujadas en el piso y todas del mismo color

- **Síntoma**: en L10 las cañerías de AF y AC corrían por el medio de los
  locales (x = 6,35 con el muro en 6,60 / 6,80), se cruzaban entre sí y con la
  cloacal, y todo salía en la misma capa `I-SAN`: imposible distinguir AF, AC,
  cloaca y pluvial.
- **Causa**: las redes se escribieron como "líneas por el local" y con una sola
  capa heredada.
- **Solución**:
  1. cuatro capas con color propio en `CAPAS`: `I-AF` (azul 5), `I-AC` (rojo 1),
     `I-CL` (verde 3), `I-PL` (amarillo 2), con espesor 30-35;
  2. AF y AC **empotradas en los muros**: cada red corre por el eje del muro con
     offset ±0,05 m (AF +0,05 / AC −0,05). Con muros de 0,20 m entran las dos
     dentro del espesor y no se pisan; la cloacal va bajo el contrapiso y la
     pluvial por el eje de los muros de fachada;
  3. `leyenda()` acepta `linea:CAPA:LINETYPE`, así la muestra de la leyenda sale
     del color real de la red;
  4. los artefactos se dibujan en la capa de su red (`CAPA_SIM`).

### 6.9 El tanque existía sólo en la planta de techos

- **Síntoma**: L03 mostraba el tanque de 1.000 l y ninguna otra lámina lo tenía:
  cortes y fachadas mostraban el techo de cocina vacío.
- **Solución**: dos helpers en `planos_lib` — `tanque_apoyo()` (plataforma,
  pedestales, cuerpo, tapa, ventilación y bajada) y `tanque_planta()` (planta con
  plataforma, tapa y bajada)— usados en L03, L04 (corte A-A), L07, L08 y L09.
  La cota de apoyo es `NIVELES["TECHO_COCINA_TOPE"]` = +3,30, que ahora también
  usan el corte y las fachadas: **un solo nivel, una sola definición**.
- **Ojo con el espejo**: en las vistas con `espejo=True` hay que pasar `s0, s1`
  ya reflejados (`s' = L − s`), porque `tanque_apoyo` llama a `tr()` directo.

### 6.10 Bloques que tapan la circulación y símbolos apilados

- **Síntoma**: el lavarropas bloqueaba la puerta del lavadero (37% del barrido),
  el placard del dormitorio 3 tapaba la puerta del guardado (75%) y en L11 había
  tomas y llaves dibujadas en el mismo punto (hasta 100% de solape).
- **Causa**: posiciones de mobiliario/electrónica puestas "a ojo", sin contrastar
  con el barrido de las puertas ni con el tamaño real de los símbolos.
- **Solución**: el gate `qa_geometria.py` mide las dos cosas; el mobiliario se
  reubicó `(0,25 / 18,60)` y `(2,65 / 13,70)` y los símbolos eléctricos se
  separaron ≥ 0,25-0,30 m (el bbox real del bloque es mayor que su tamaño
  nominal, por eso 0,20 m no alcanza).
- **Regla**: un aparato puede estar **dentro** de la mesada (contención), nunca
  **invadiendo** el cuarto de círculo de una puerta.

### 6.11 Planta de techos incompleta

- **Síntoma**: el techo del sector de cocina aparecía como una sola línea (el
  filtro `min(y) >= 16,8` sobre los muros de PB dejaba únicamente el muro de
  fondo), no había cotas, ni boca de acceso, ni conexión pluvial, ni plataforma
  del tanque con pedestales.
- **Solución**: el sector se define con tres muros sintéticos (`T-OESTE`,
  `T-ESTE`, `T-FONDO`) para cerrar el perímetro de losa a +2,95; se agregaron
  cotas (6,60 / 13,80 / 3,00 / 16,80), boca de acceso 0,60 × 0,60, canaleta de
  borde con 3 bajadas sobre `I-PL`, y un detalle 1:20 de la plataforma del
  tanque con su cota de altura (1,27 m).
- **Lección**: cuando se filtra geometría con `min()/max()` sobre listas de
  muros, verificar el resultado con un conteo de entidades por capa: un filtro
  que devuelve 1 muro cuando deberían ser 3 no se nota mirando el PNG chico.

## 7. Deudas conocidas (lo que este juego NO es)

Decirlo antes de que lo diga el comitente:

1. **L12 son detalles esquemáticos**, no ejecutivos: falta armado, especificación
   de materiales, juntas, aislaciones e hidrófugo.
2. **Instalaciones sin cálculo**: no hay verificación de caudales, diámetros,
   pendientes, secciones de conductores, protecciones ni puesta a tierra. Los
   isométricos son conceptuales.
3. **No hay plano estructural** (platea, encadenados, columnas) ni memoria de
   cargas: el juego es arquitectura + instalaciones.
4. **No hay planilla de carpintería** con códigos (`P-01`, `V-01`) cruzados al
   plano, ni cómputo y presupuesto.
5. **FOS/FOT/retiros**: declarados en el rótulo, no verificados contra el
   Código Urbanístico. `rules_caba.json` son valores de partida.
6. **Escalera**: 16 alzadas de 0,18 = 2,88 m contra un PA de +2,90. La alzada
   real es 0,1813. Parametrizar `alzadas`/alzada desde `NIVELES`.
7. **Sin verificación de interferencias** entre cañerías, conductos y muros
   (no hay pases dibujados).
8. **Rótulo**: `COMITENTE: A DEFINIR`, sin profesional ni matrícula. Se completa
   en la entrega final, no antes.


## 8. Procedimiento de bajo costo (el protocolo)

La mayor parte del costo de la Vivienda 02 no fue dibujar: fue **volver a leer
lo mismo** y **reintentar comandos de shell**. Este protocolo apunta a eso.

### 8.1 Reglas de oro

| # | Regla | Por qué |
|---|---|---|
| 0 | **Índice antes que archivo.** Antes de abrir `planos.py`, `grep -n '^def '` | ~20 k tokens por lectura completa vs. ~1,5 k del índice |
| 1 | **Ediciones agrupadas.** Todas las ediciones independientes en una sola respuesta | cada ida y vuelta paga todo el contexto |
| 2 | **Build parcial.** `python3 planos.py L06` mientras se trabaja esa hoja | 13 hojas = 3 s, pero el bucle se hace sobre 1 |
| 3 | **Gate antes que ojo.** `qa_laminas.py` primero; PNG sólo si el gate pasa y algo "se ve raro" | 1 gate ≈ 60 tokens de salida; 1 imagen ≈ 2-4 k |
| 4 | **Render con `window`** y `width <= 1200` | un A2 completo en PNG no se lee; el recorte sí |
| 5 | **Nunca `cat` de todo.** Redirigir a `/tmp/x.txt` y leer el rango, o `grep`/`tail` | el volcado completo es el 80% de los tokens tirados |
| 6 | **Scripts en `tools/`, no en `/tmp`** | `/tmp` se pierde y se reescribe (pagando dos veces) |
| 7 | **Cajas antes que líneas** | reservar la retícula de la hoja evita el 80% de los solapes |
| 8 | **Cerrar cada ronda escribiendo 5 líneas** en este playbook | evita re-deducir lo mismo en la ronda siguiente |
| 9 | **No re-exportar PNG de las 13 hojas** si cambió una | `cadcraft-cli convert` sólo de lo tocado |
| 10 | **Un solo `bash -c '...'`** por bloque de comandos | el shell fish rompe con sintaxis de bash |

### 8.2 Presupuesto sugerido por hoja

| Etapa | Llamadas | Qué se hace |
|---|---|---|
| Composición | 2-4 | elegir vista, escala, columnas (dibujo / notas / planilla / rótulo) |
| Cuerpo | 4-8 | muros/aberturas o corte/fachada, cotas, niveles |
| Anotación | 2-4 | notas, leyenda, planilla, referencias de corte |
| Cierre | 2-3 | build + gate + (si hace falta) render recortado |

Si una hoja pasa de ~15 llamadas, casi siempre es porque se está componiendo a
ojo en vez de reservar cajas primero. Parar y replantear la retícula.

### 8.3 Reservar cajas (siguiente mejora concreta)

El patrón que faltó y que explica buena parte de los solapes: **cada zona de la
hoja se reserva antes de dibujar** y el generador avisa si dos zonas se pisan.
No está implementado; el boceto es este (iría en `planos_lib.Lamina`):

```python
class Lamina:
    def reservar(self, nombre, caja):          # caja = (x0, y0, x1, y1)
        for otro, c in self._zonas:
            if _interseca(caja, c):
                print(f"[zonas] {self.codigo}: '{nombre}' pisa '{otro}'")
        self._zonas.append((nombre, caja))
        return caja                            # se usa como p = (x0, y0)
```

Con eso, la composición de una hoja nueva arranca así:

```python
z_vista  = lam.reservar("vista",    (0.070, 0.115, 0.360, 0.380))
z_notas  = lam.reservar("notas",    (0.380, 0.240, 0.560, 0.380))
z_datos  = lam.reservar("planilla", (0.380, 0.150, 0.560, 0.230))
z_escala = lam.reservar("escala",   (0.380, 0.120, 0.560, 0.145))
```

y el gate de texto queda para lo fino (texto que se sale de su caja), no para lo
grueso (zonas mal repartidas).

## 9. Runbook: vivienda nueva de punta a punta

1. **Spec primero.** Escribir `spec_viviendaNN_pb.json` / `_pa.json` (muros como
   segmentos con `id`, `x0,y0,x1,y1`, `espesor`, y `aberturas` con tipo, ancho,
   posición y altura de antepecho). Sin spec no se dibuja.
2. **`check.py` verde** en los dos specs (`plan.py` → `/tmp/*.dxf` →
   `check.py dxf spec`). Si el validador se queja, se corrige el spec, no el plano.
3. **Copiar las 13 firmas.** Duplicar `planos.py` cambiando sólo los números
   (lote, ancho, niveles) y dejando la receta. Las hojas nuevas se agregan a
   `SHEETS` y a `TOTAL`.
4. **Hojas de a una, en este orden**: L01 → L02 → L03 → L04 → L05 → L06 → L07 →
   L08/L09 → L10 → L11 → L12 → L13. Cada una: `planos.py LNN` + `qa_laminas.py
   out/LNN.dxf` antes de pasar a la siguiente.
5. **Cierre**: `planos.py` completo + `qa_laminas.py --all out --json` +
   `check.py` de los dos specs + `for f in out/L*.dxf` a PNG.
6. **Revisión visual** sólo de las hojas que cambiaron de composición, con
   `render window` en la zona dudosa.
7. **Documentar**: actualizar este playbook (§6 con los defectos nuevos, §7 con
   las deudas) y `README.md` si cambió un comando.

## 10. Checklist de entrega

- [ ] `python3 planos.py` → exit 0, 13 líneas de salida, ningún `ERROR`.
- [ ] `python3 tools/qa_laminas.py --all out` → `13/13 láminas OK`.
- [ ] `python3 tools/qa_geometria.py --all out` → `13/13 láminas limpias`.
- [ ] `python3 tools/qa_muros.py out/L01.dxf out/L02.dxf out/L03.dxf` → solape `0,00 m²` (3/3).
- [ ] `python3 plan.py spec_*_pb.json /tmp/pb.dxf` + `check.py /tmp/pb.dxf spec_*_pb.json` → OK (ídem PA).
- [ ] Autotest: `tools/mk_dxf_roto.py` + ambos gates → 1+1 y 1+1, exit 1 en cada uno.
- [ ] Auditoría ezdxf `0/0` en las 13 hojas (la imprime el mismo gate).
- [ ] Sin textos superpuestos en tolerancia 0,4 × 0,5 mm.
- [ ] Nada fuera de `0..0,594 × 0..0,420`.
- [ ] Rótulo completo: comitente, proyecto, escala, fecha, número y total de hojas.
- [ ] Referencias de corte coherentes entre L01/L02 y L04/L05.
- [ ] Niveles iguales en todas las vistas (+0,00 / +2,90 / +5,75 / +6,55).
- [ ] `out/L01..L13.dxf` + `.png` regenerados en la última corrida.

---

