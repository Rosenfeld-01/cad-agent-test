# Catálogo de defectos ya resueltos

Lecciones que ya se pagaron una vez. Revisar antes de tocar el juego de
láminas o el pipeline: muchos "errores nuevos" son viejos conocidos.

---

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

