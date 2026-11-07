#!/usr/bin/env python3
"""
planos_lib.py — armado de láminas del juego de planos (herramientas de Nivel 2).

Todo se dibuja en **metros de papel**: el model space de cada lámina es la hoja
(A2 = 0,594 x 0,420 m). La planta se dibuja en coordenadas de proyecto (m) y se
transforma a papel con factor 1/escala (1:50 -> 0,02).

Las plantas de arquitectura (L01/L02/L03) se emiten a **escala real**: con
``Lamina(..., escala_real=True)`` todo el model space se multiplica por
``escala`` al guardar, de modo que **1 unidad = 1 m del proyecto** (un muro de
6,40 m mide 6,40 u). Equivale a plotear la hoja a 1:escala, así las escalas
internas (detalle 1:20 de L03, barras de escala) se conservan. Cortes, fachadas,
instalaciones y detalles (L04–L13) siguen en metros de papel (1 u = 1 m de
papel).

Reglas que respeta
------------------
- La geometría de muros y aberturas sale del mismo spec que usa `plan.py` (se
  reutiliza `plan._wall_solids`), así la lámina y el validador no divergen.
- Los símbolos salen de la biblioteca `CAD_Blocks/`: se declaran como definición
  de bloque en la lámina y se insertan con escala = 1/escala.
- Capas del juego de láminas: las de `AGENTS.md` (A-WALL, A-DOOR, A-WIN,
  A-AREA, A-ANNO, A-DIM, A-AXIS) más A-MOB (mobiliario), A-HATCH, X-FRAME
  (marco y rótulo) e I-ELE / I-SAN / I-GAS para instalaciones.
"""
from __future__ import annotations

import math
from pathlib import Path

import ezdxf
from ezdxf.enums import TextEntityAlignment
from ezdxf.math import Vec2, Matrix44

import plan as PL
import blocks_build as BB
import blocks_data_arquitectura as DA
import blocks_data_bano_exterior as DB
import blocks_data_instalaciones as DI

BASE = Path(__file__).resolve().parent
BIBLIOTECA = BASE / "CAD_Blocks"

FORMATOS = {
    "A4": (0.297, 0.210),
    "A3": (0.420, 0.297),
    "A2": (0.594, 0.420),
}

# capa -> (color ACI, espesor de pluma en 1/100 mm)
CAPAS = {
    "X-FRAME": (7, 50),
    "A-WALL": (7, 50),
    "A-DOOR": (3, 25),
    "A-WIN": (4, 25),
    "A-AREA": (8, 13),
    "A-ANNO": (2, 18),
    "A-DIM": (1, 13),
    "A-AXIS": (6, 18),
    "A-MOB": (9, 13),
    "A-HATCH": (8, 13),
    "A-ESC": (7, 18),
    "I-ELE": (2, 25),
    "I-SAN": (7, 25),
    "I-GAS": (6, 25),
    # redes de agua: una capa y un color por red (AF azul, AC rojo,
    # CL verde, PL amarillo).  Antes todo iba a I-SAN y no se distinguía.
    "I-AF": (5, 35),
    "I-AC": (1, 35),
    "I-CL": (3, 30),
    "I-PL": (2, 30),
}

ALINEACION = {
    "mc": TextEntityAlignment.MIDDLE_CENTER,
    "ml": TextEntityAlignment.MIDDLE_LEFT,
    "mr": TextEntityAlignment.MIDDLE_RIGHT,
    "bl": TextEntityAlignment.BOTTOM_LEFT,
    "bc": TextEntityAlignment.BOTTOM_CENTER,
    "br": TextEntityAlignment.BOTTOM_RIGHT,
    "tl": TextEntityAlignment.TOP_LEFT,
    "tc": TextEntityAlignment.TOP_CENTER,
    "tr": TextEntityAlignment.TOP_RIGHT,
}


class Tr:
    """Transformación lineal proyecto (m) -> papel (m de hoja)."""

    def __init__(self, ox: float, oy: float, escala: float):
        self.ox, self.oy = float(ox), float(oy)
        self.esc = 1.0 / float(escala)

    @classmethod
    def anclado(cls, ox: float, oy: float, escala: float, ancla=(0.0, 0.0)):
        """Transformación que lleva el punto `ancla` del proyecto a (ox, oy)."""
        e = 1.0 / float(escala)
        return cls(ox - ancla[0] * e, oy - ancla[1] * e, escala)

    def __call__(self, p):
        return (self.ox + p[0] * self.esc, self.oy + p[1] * self.esc)

    def s(self, d: float) -> float:
        return float(d) * self.esc

    def v(self, vec: Vec2):
        return (self.ox + vec.x * self.esc, self.oy + vec.y * self.esc)


def definir_bloques(doc) -> int:
    """Declara en el documento las 70 definiciones de bloque de CAD_Blocks."""
    items = DA.BLOQUES + DB.BLOQUES + DI.BLOQUES
    n = 0
    for it in items:
        if it["nombre"] in doc.blocks:
            continue
        blk = doc.blocks.new(it["nombre"])
        BB.dibujar(blk, it)
        n += 1
    return n



class Lamina:
    """Una hoja del juego de planos, en metros de papel."""

    def __init__(self, numero: int, total: int, titulo: str, escala: int,
                 formato: str = "A2", proyecto: str = "VIVIENDA",
                 comitente: str = "COMITENTE: A DEFINIR",
                 fecha: str = "2026-03-11", codigo: str = "L01",
                 etapa: str = "PROYECTO EJECUTIVO", escala_real: bool = False):
        self.numero, self.total = numero, total
        self.titulo = titulo
        self.escala = int(escala)
        self.esc = 1.0 / self.escala
        self.codigo = codigo
        self.ancho, self.alto = FORMATOS[formato]
        self.formato = formato
        self.escala_real = escala_real
        self._escalado_real = False

        self.doc = ezdxf.new("R2013", setup=True)
        self.doc.units = ezdxf.units.M
        self.doc.header["$INSUNITS"] = 6
        self.doc.header["$MEASUREMENT"] = 1
        for nombre, (color, lw) in CAPAS.items():
            capa = self.doc.layers.add(nombre, color=color)
            capa.dxf.lineweight = lw
        self.msp = self.doc.modelspace()
        definir_bloques(self.doc)
        self._marco(proyecto, comitente, fecha, etapa)

    # --- primitivas de papel ------------------------------------------------
    def ln(self, a, b, capa: str = "A-ANNO", lt: str | None = None):
        attrs = {"layer": capa}
        if lt:
            attrs["linetype"] = lt
        return self.msp.add_line(a, b, dxfattribs=attrs)

    def pl(self, pts, capa: str = "A-WALL", close: bool = True,
           lt: str | None = None):
        attrs = {"layer": capa}
        if lt:
            attrs["linetype"] = lt
        return self.msp.add_lwpolyline([tuple(p) for p in pts], close=close,
                                       dxfattribs=attrs)

    def ln_unica(self, a, b, capa: str = "A-ANNO", lt: str | None = None):
        """Como `ln`, pero no repite un segmento idéntico ya dibujado.

        Evita los duplicados que aparecen al encadenar cotas (marca de 45° y
        línea de referencia compartidas) y al cerrar contornos de escalera.
        """
        cache = getattr(self, "_segs", None)
        if cache is None:
            cache = self._segs = set()
        k1 = (capa, round(a[0], 6), round(a[1], 6),
              round(b[0], 6), round(b[1], 6))
        k2 = (capa, k1[3], k1[4], k1[1], k1[2])
        if k1 in cache or k2 in cache:
            return None
        cache.add(k1)
        return self.ln(a, b, capa, lt)

    def circ(self, c, r: float, capa: str = "A-ANNO"):
        return self.msp.add_circle(c, r, dxfattribs={"layer": capa})

    def arc(self, c, r: float, a0: float, a1: float, capa: str = "A-ANNO"):
        return self.msp.add_arc(c, r, a0, a1, dxfattribs={"layer": capa})

    def tx(self, texto: str, p, h: float = 0.0028, capa: str = "A-ANNO",
           align: str = "ml", rot: float = 0.0):
        ent = self.msp.add_text(texto, height=h,
                                dxfattribs={"layer": capa, "rotation": rot})
        ent.set_placement(p, align=ALINEACION[align])
        return ent

    def blk(self, nombre: str, p, escala: float | None = None, rot: float = 0.0,
            capa: str | None = None):
        if nombre not in self.doc.blocks:
            raise KeyError(f"bloque inexistente: {nombre}")
        e = self.esc if escala is None else escala
        attrs = {"xscale": e, "yscale": e, "rotation": rot}
        if capa:
            attrs["layer"] = capa
        return self.msp.add_blockref(nombre, p, dxfattribs=attrs)

    def sym(self, nombre: str, tr: Tr, x: float, y: float, rot: float = 0.0,
            capa: str | None = None):
        """Inserta un símbolo de la biblioteca en coordenadas de proyecto."""
        return self.blk(nombre, tr((x, y)), rot=rot, capa=capa)

    # --- marco y rótulo -----------------------------------------------------
    def _marco(self, proyecto: str, comitente: str, fecha: str, etapa: str):
        W, H = self.ancho, self.alto
        m_izq, m_der, m_sup, m_inf = 0.030, 0.012, 0.012, 0.012
        self.borde = (m_izq, m_inf, W - m_der, H - m_sup)
        self.pl([(0, 0), (W, 0), (W, H), (0, H)], "X-FRAME")
        self.pl([(m_izq, m_inf), (W - m_der, m_inf),
                 (W - m_der, H - m_sup), (m_izq, H - m_sup)], "X-FRAME")

        rx1, ry0 = W - m_der, m_inf
        rw, rh = 0.205, 0.070
        rx0, ry1 = rx1 - rw, ry0 + rh
        self.rrotulo = (rx0, ry0, rx1, ry1)
        self.pl([(rx0, ry0), (rx1, ry0), (rx1, ry1), (rx0, ry1)], "X-FRAME")
        for f in (0.22, 0.40, 0.60, 0.80):
            y = ry0 + rh * f
            self.ln((rx0, y), (rx1, y), "X-FRAME")
        self.ln((rx0 + 0.120, ry0), (rx0 + 0.120, ry0 + rh * 0.22), "X-FRAME")
        self.ln((rx0 + 0.162, ry0), (rx0 + 0.162, ry0 + rh * 0.22), "X-FRAME")
        self.ln((rx0 + 0.120, ry0 + rh * 0.22), (rx0 + 0.120, ry0 + rh * 0.40),
                "X-FRAME")

        self.tx(proyecto, (rx0 + 0.003, ry0 + rh * 0.905), 0.0046, "A-ANNO", "ml")
        self.tx("VIVIENDA UNIFAMILIAR ENTRE MEDIANERAS - CABA - JUEGO L01/L13",
                (rx0 + 0.003, ry0 + rh * 0.828), 0.0016, "A-ANNO", "ml")
        self.tx(self.titulo, (rx0 + 0.003, ry0 + rh * 0.69), 0.0046, "A-ANNO", "ml")
        self.tx(etapa, (rx1 - 0.003, ry0 + rh * 0.69), 0.0019, "A-ANNO", "mr")
        self.tx(f"ESCALA  1:{self.escala}", (rx0 + 0.003, ry0 + rh * 0.50),
                0.0032, "A-ANNO", "ml")
        self.tx("COTAS Y NIVELES EN METROS", (rx1 - 0.003, ry0 + rh * 0.50),
                0.0019, "A-ANNO", "mr")
        self.tx(f"FECHA  {fecha}", (rx0 + 0.003, ry0 + rh * 0.31), 0.0024,
                "A-ANNO", "ml")
        self.tx(self.codigo, (rx0 + 0.124, ry0 + rh * 0.31), 0.0026, "A-ANNO", "ml")
        self.tx("DIBUJO: agente CAD", (rx0 + 0.166, ry0 + rh * 0.31), 0.0020,
                "A-ANNO", "ml")
        self.tx(f"LAMINA  {self.numero:02d}/{self.total:02d}",
                (rx0 + 0.003, ry0 + rh * 0.11), 0.0024, "A-ANNO", "ml")
        self.tx(self.formato, (rx0 + 0.124, ry0 + rh * 0.11), 0.0026, "A-ANNO", "ml")
        self.tx(comitente, (rx0 + 0.166, ry0 + rh * 0.11), 0.0020, "A-ANNO", "ml")

    def _a_escala_real(self):
        """Lleva la hoja a escala real: 1 unidad de modelo = 1 m del proyecto.

        La hoja se construye en metros de papel; multiplicar todo el model
        space por ``escala`` equivale a plotear a 1:escala.  La planta queda a
        1:1 real (un muro de 6,40 m mide 6,40 u) y las escalas internas
        (detalle 1:20, barras de escala) se conservan porque cambian de factor
        junto con el resto de la hoja.
        """
        s = float(self.escala)
        M = Matrix44.scale(s)
        for e in list(self.msp):
            e.transform(M)
        self.doc.header["$LTSCALE"] = s
        self.doc.header["$DIMSCALE"] = s
        self._escalado_real = True

    def guardar(self, ruta: Path) -> Path:
        ruta = Path(ruta)
        ruta.parent.mkdir(parents=True, exist_ok=True)
        if self.escala_real and not self._escalado_real:
            self._a_escala_real()
        self.doc.saveas(ruta)
        return ruta

# ---------------------------------------------------------------------------
# anotaciones
# ---------------------------------------------------------------------------
def flecha(lam, a, b, largo: float = 0.0026, ancho: float = 0.0009,
           capa: str = "A-DIM"):
    """Punta de flecha con el vértice en b, orientada según a->b."""
    ang = math.atan2(b[1] - a[1], b[0] - a[0])
    p1 = (b[0] - largo * math.cos(ang) + ancho * math.sin(ang),
          b[1] - largo * math.sin(ang) - ancho * math.cos(ang))
    p2 = (b[0] - largo * math.cos(ang) - ancho * math.sin(ang),
          b[1] - largo * math.sin(ang) + ancho * math.cos(ang))
    lam.pl([b, p1, p2], capa)


def cota(lam, a, b, off: float = 0.010, texto: str | None = None,
         h: float = 0.0022, capa: str = "A-DIM"):
    """Cota lineal entre dos puntos de papel, corrida `off` (perpendicular)."""
    ax, ay = a
    bx, by = b
    dx, dy = bx - ax, by - ay
    L = math.hypot(dx, dy)
    if L < 1e-9:
        return
    u = (dx / L, dy / L)
    n = (-u[1], u[0])
    a2 = (ax + n[0] * off, ay + n[1] * off)
    b2 = (bx + n[0] * off, by + n[1] * off)
    sgn = 1.0 if off >= 0 else -1.0
    # líneas de referencia
    lam.ln_unica(a, (a2[0] + n[0] * 0.002 * sgn, a2[1] + n[1] * 0.002 * sgn), capa)
    lam.ln_unica(b, (b2[0] + n[0] * 0.002 * sgn, b2[1] + n[1] * 0.002 * sgn), capa)
    # línea de cota
    lam.ln(a2, b2, capa)
    # marcas a 45° (una sola vez cuando dos cotas encadenadas comparten punto)
    t = 0.0014
    for p in (a2, b2):
        lam.ln_unica((p[0] - (u[0] + n[0]) * t, p[1] - (u[1] + n[1]) * t),
                     (p[0] + (u[0] + n[0]) * t, p[1] + (u[1] + n[1]) * t), capa)
    txt = texto if texto is not None else f"{L * lam.escala:.2f}"
    ang = math.degrees(math.atan2(u[1], u[0]))
    if ang > 90.0:
        ang -= 180.0
    if ang < -90.0:
        ang += 180.0
    pm = ((a2[0] + b2[0]) / 2 + n[0] * 0.0012, (a2[1] + b2[1]) / 2 + n[1] * 0.0012)
    lam.tx(txt, pm, h, capa, "mc", ang)


def cota_h(lam, x0: float, x1: float, y: float, dy: float,
           texto: str | None = None, h: float = 0.0022, capa: str = "A-DIM",
           escala: float | None = None):
    """Cota horizontal en papel; el valor por defecto se escribe en metros."""
    if texto is None:
        texto = f"{abs(x1 - x0) * (escala if escala else lam.escala):.2f}"
    cota(lam, (x0, y), (x1, y), dy, texto, h, capa)


def cota_v(lam, y0: float, y1: float, x: float, dx: float,
           texto: str | None = None, h: float = 0.0022, capa: str = "A-DIM",
           escala: float | None = None):
    """Cota vertical en papel; el valor por defecto se escribe en metros."""
    if texto is None:
        texto = f"{abs(y1 - y0) * (escala if escala else lam.escala):.2f}"
    cota(lam, (x, y0), (x, y1), dx, texto, h, capa)


def nivel(lam, p, texto: str, r: float = 0.0018, h: float = 0.0022,
          capa: str = "A-DIM", lado: int = 1):
    """Marca de nivel: triángulo isósceles + texto."""
    x, y = p
    lam.pl([(x, y), (x - r, y + r * 1.7), (x + r, y + r * 1.7)], capa)
    lam.ln((x - r * 1.6, y + r * 1.7), (x + r * 1.6, y + r * 1.7), capa)
    lam.tx(texto, (x + (r * 2.2 if lado > 0 else -r * 2.2), y + r * 1.7), h,
           capa, "ml" if lado > 0 else "mr")


def norte(lam, p, r: float = 0.014):
    """Rosa de los vientos simplificada (flecha de norte)."""
    x, y = p
    lam.circ((x, y), r, "A-ANNO")
    lam.pl([(x, y + r * 0.92), (x - r * 0.34, y - r * 0.55),
            (x, y - r * 0.22), (x + r * 0.34, y - r * 0.55)], "A-ANNO")
    lam.tx("N", (x, y + r * 1.18), 0.0032, "A-ANNO", "mc")


def escala_grafica(lam, p, escala: int, tramos=(0, 1, 2, 5), h: float = 0.0022):
    """Barra de escala con tramos alternados de 1 m de proyecto."""
    x, y = p
    e = 1.0 / escala
    x0 = x
    for i in range(len(tramos) - 1):
        ancho = (tramos[i + 1] - tramos[i]) * e
        lam.pl([(x0, y), (x0 + ancho, y), (x0 + ancho, y + 0.0028),
                (x0, y + 0.0028)], "A-ANNO")
        if i % 2 == 0:
            lam.ln((x0 + ancho / 2, y), (x0 + ancho / 2, y + 0.0028), "A-ANNO")
        lam.tx(str(tramos[i]), (x0, y - 0.0012), h, "A-ANNO", "tc")
        x0 += ancho
    lam.tx(str(tramos[-1]), (x0, y - 0.0012), h, "A-ANNO", "tc")
    lam.tx(f"1:{escala}  (m)", (x0 + 0.006, y + 0.0006), h, "A-ANNO", "ml")


def baranda(lam, tr, pts, capa: str = "A-ESC", espesor: float = 0.0014,
            paso: float = 0.0045):
    """Baranda de escalera abierta o balcón: doble línea con montantes.

    `pts` son puntos de proyecto; el espesor y el paso se dan en metros de papel.
    """
    pp = [tr(p) for p in pts]
    for a, b in zip(pp, pp[1:]):
        dx, dy = b[0] - a[0], b[1] - a[1]
        largo = math.hypot(dx, dy)
        if largo < 1e-9:
            continue
        nx, ny = -dy / largo * espesor, dx / largo * espesor
        lam.ln(a, b, capa)
        lam.ln((a[0] + nx, a[1] + ny), (b[0] + nx, b[1] + ny), capa)
        for i in range(1, int(largo / paso) + 1):
            t = min(i * paso, largo - 0.001)
            p = (a[0] + dx * t / largo, a[1] + dy * t / largo)
            lam.ln(p, (p[0] + nx, p[1] + ny), capa)


def nota(lam, x: float, y: float, lineas, h: float = 0.0022,
         inter: float = 0.0052, titulo: str | None = None,
         ancho: float = 0.16, capa: str = "A-ANNO") -> float:
    """Bloque de notas; devuelve el y final (para encadenar)."""
    yy = y
    if titulo:
        lam.tx(titulo.upper(), (x, yy), h * 1.15, capa, "ml")
        lam.ln((x, yy - 0.0014), (x + ancho, yy - 0.0014), capa)
        yy -= inter * 1.15
    for linea in lineas:
        lam.tx(linea, (x, yy), h, capa, "ml")
        yy -= inter
    return yy




# ---------------------------------------------------------------------------
# planta
# ---------------------------------------------------------------------------
TAM_BLOQUES = {it["nombre"]: (it["w"], it["h"])
               for it in DA.BLOQUES + DB.BLOQUES + DI.BLOQUES}


def poner(lam, nombre: str, tr: Tr, x: float, y: float, rot: int = 0,
          capa: str | None = None, escala: float | None = None):
    """Inserta un bloque con su esquina SO (ya rotada) en (x, y) del proyecto."""
    w, h = TAM_BLOQUES[nombre]
    rot = int(rot) % 360
    bx, by = {0: (0.0, 0.0), 90: (-h, 0.0), 180: (-w, -h), 270: (0.0, -w)}[rot]
    p = tr((x - bx, y - by))
    return lam.blk(nombre, p, rot=rot, capa=capa, escala=escala)


def caja_rotada(nombre: str, x: float, y: float, rot: int = 0):
    """Caja ocupada (x0, y0, x1, y1) por un bloque apoyado en (x, y)."""
    w, h = TAM_BLOQUES[nombre]
    rot = int(rot) % 360
    if rot in (0, 180):
        return (x, y, x + w, y + h)
    return (x, y, x + h, y + w)


def _modena_f(ancho: float, alto: float) -> str:
    return "A-MODENA-%03dx%03d" % (round(ancho * 100), round(alto * 100))


def _modena_p(ancho: float) -> str:
    return "A-MODENA-P-%03d" % round(ancho * 100)


def abertura(lam, tr: Tr, p1: Vec2, u: Vec2, n: Vec2, t: float,
             a: float, b: float, o: dict):
    """Símbolo de la abertura en el hueco [a, b] del muro, en papel."""
    pa, pb = p1 + u * a, p1 + u * b
    tipo = o.get("tipo", "hueco")
    if tipo == "puerta":
        hinge = pa + n * (t / 2)
        leaf = hinge + n * (b - a)
        lam.ln(tr.v(hinge), tr.v(leaf), "A-DOOR")
        ang_u = math.degrees(math.atan2(u.y, u.x))
        ang_n = math.degrees(math.atan2(n.y, n.x))
        a0, a1 = min(ang_u, ang_n), max(ang_u, ang_n)
        if a1 - a0 > 180:
            a0, a1 = a1, a0 + 360
        lam.arc(tr.v(hinge), tr.s(b - a), a0, a1, "A-DOOR")
    elif tipo == "porton":
        lam.ln(tr.v(pa + n * (t / 2)), tr.v(pb + n * (t / 2)), "A-DOOR")
        lam.ln(tr.v(pa - n * (t / 2)), tr.v(pb - n * (t / 2)), "A-DOOR")
    elif tipo == "ventana":
        nombre = _modena_p(b - a)
        if (1.0 / tr.esc) <= 60 and nombre in lam.doc.blocks:
            centro = p1 + u * ((a + b) / 2.0)
            rot = math.degrees(math.atan2(u.y, u.x))
            lam.blk(nombre, tr.v(centro), rot=rot, capa="A-WIN")
        else:                                   # respaldo genérico
            off = t / 6.0
            for s in (off, -off):
                lam.ln(tr.v(pa + n * s), tr.v(pb + n * s), "A-WIN")
            for p in (pa, pb):
                lam.ln(tr.v(p + n * (t / 2)), tr.v(p - n * (t / 2)), "A-WIN")
    elif tipo == "hueco":
        pass
    else:
        raise ValueError(f"tipo de abertura desconocido: {tipo}")


def planta(lam, spec: dict, origen=(0.10, 0.05), escala: float | None = None,
           etiquetas: bool = True, areas: bool = True,
           con_ambientes: bool = True, mob=None, capa_muro: str = "A-WALL",
           capa_area: str = "A-AREA", capa_texto: str = "A-ANNO",
           t_muro: float | None = None, h_nombre: float = 0.0026,
           h_area: float = 0.0022, ancla=(0.0, 0.0)) -> Tr:
    """Dibuja una planta completa (ambientes + muros + aberturas + mobiliario)."""
    esc = escala or lam.escala
    tr = Tr.anclado(origen[0], origen[1], esc, ancla)

    if con_ambientes:
        for amb in spec.get("ambientes", []):
            x, y = float(amb["x"]), float(amb["y"])
            w, h = float(amb["w"]), float(amb["h"])
            lam.pl([tr((x, y)), tr((x + w, y)), tr((x + w, y + h)), tr((x, y + h))],
                   capa_area)
            if not etiquetas:
                continue
            cx, cy = x + w / 2.0, y + h / 2.0
            rot = 90.0 if (w < 1.7 and h > w) else 0.0
            lam.tx(amb["nombre"], tr((cx, cy + (0.34 if areas else 0.0))),
                   h_nombre, capa_texto, "mc", rot)
            if areas:
                lam.tx(f"{w * h:.2f} m2", tr((cx, cy - 0.34)), h_area,
                       capa_texto, "mc", rot)

    muros = spec["muros"]
    ext_t = t_muro if t_muro is not None else 0.2
    muros_union = ([dict(m, espesor=t_muro) for m in muros]
                   if t_muro is not None else muros)
    for loop in PL.wall_outline(muros_union, ext_t):
        lam.pl([tr((x, y)) for x, y in loop], capa_muro)
    for muro in muros:
        t = t_muro if t_muro is not None else float(muro.get("espesor", 0.2))
        p1, p2 = Vec2(muro["p1"]), Vec2(muro["p2"])
        _solids, u, n, _L, cuts = PL._wall_solids(p1, p2, t,
                                                  muro.get("aberturas", []))
        for a, b, o in cuts:
            abertura(lam, tr, p1, u, n, t, a, b, o)

    for item in (mob or []):
        nombre, x, y = item[0], item[1], item[2]
        rot = item[3] if len(item) > 3 else 0
        capa = item[4] if len(item) > 4 else "A-MOB"
        poner(lam, nombre, tr, x, y, rot, capa)
    return tr


def escalera(lam, tr: Tr, x0: float, y0: float, ancho: float = 2.0,
             huella: float = 0.28, alzadas: int = 16, nivel: str = "PB",
             capa: str = "A-ESC", capa_ejes: str = "A-DIM",
             nota=None):
    """Escalera en U de dos tramos con descanso (16 alzadas de 0,18).

    Tramo 1 sube por la mitad oeste (n1 - 1 huellas), descanso de 1,00 m al
    fondo y tramo 2 baja por la mitad este hasta el nivel de llegada.  `nota`
    es el punto de papel donde se rotula la escalera (opcional).
    """
    hueso = 0.10
    fw = (ancho - hueso) / 2.0
    n1 = alzadas // 2
    y_desc = y0 + (n1 - 1) * huella
    y_fin = y_desc + 1.0
    if nivel == "PA":
        # el tramo 1 queda debajo: se marca el vacío y se dibuja lo que llega
        lam.ln(tr((x0, y0)), tr((x0 + fw, y_desc)), capa)
        lam.ln(tr((x0 + fw, y0)), tr((x0, y_desc)), capa)
        lam.tx("VACIO", tr((x0 + fw / 2, y0 + 0.35)), 0.0018, "A-ANNO", "mc")
    else:
        for k in range(1, n1 - 1):      # el último peldaño es el borde del descanso
            yy = y0 + k * huella
            lam.ln(tr((x0, yy)), tr((x0 + fw, yy)), capa)
    lam.ln(tr((x0, y_desc)), tr((x0 + ancho, y_desc)), capa)
    lam.ln(tr((x0, y_fin)), tr((x0 + ancho, y_fin)), capa)
    x1 = x0 + fw + hueso
    lam.ln(tr((x1 - hueso, y_desc)), tr((x1 - hueso, y_fin)), capa)
    n2 = alzadas - n1
    for k in range(1, n2):
        yy = y_fin - k * huella
        lam.ln(tr((x1, yy)), tr((x1 + fw, yy)), capa)
    lam.ln(tr((x0, y0)), tr((x0 + ancho, y0)), capa)
    lam.ln(tr((x0, y0)), tr((x0, y_fin)), capa)
    lam.ln(tr((x0 + ancho, y0)), tr((x0 + ancho, y_fin)), capa)

    # recorrido: sube por el tramo 1, cruza el descanso y sigue por el tramo 2
    xa, xb = x0 + fw / 2, x1 + fw / 2
    lam.ln(tr((xa, y0 + 0.25)), tr((xa, y_desc + 0.50)), capa_ejes)
    lam.ln(tr((xa, y_desc + 0.50)), tr((xb, y_desc + 0.50)), capa_ejes)
    lam.ln(tr((xb, y_desc + 0.50)), tr((xb, y0 + 0.55)), capa_ejes)
    flecha(lam, tr((xb, y0 + 0.85)), tr((xb, y0 + 0.55)), capa=capa_ejes)
    lam.circ(tr((xa, y0 + 0.25)), 0.0034, capa_ejes)
    lam.tx("SUBE" if nivel == "PB" else "BAJA", tr((xa, y0 + 0.10)), 0.0019,
           "A-ANNO", "mc")
    if nota:
        hu = f"{huella:.2f}".replace(".", ",")
        an = f"{ancho:.2f}".replace(".", ",")
        lam.tx(f"ESCALERA {alzadas} ALZ. x 0,18 - HUELLA {hu} - ANCHO {an}",
               nota, 0.0021, "A-ANNO", "ml")




def tabla(lam, x: float, y: float, anchos, filas, alto_fila: float = 0.0055,
          h: float = 0.0021, cabecera: bool = True, alineacion=None,
          capa: str = "A-ANNO", capa_linea: str = "X-FRAME") -> float:
    """Tabla simple que crece hacia abajo; devuelve el y del borde inferior."""
    total = sum(anchos)
    yy = y
    alineacion = alineacion or ["ml"] * len(anchos)
    for i, fila in enumerate(filas):
        alto = alto_fila * (1.15 if (cabecera and i == 0) else 1.0)
        yy -= alto
        lam.ln((x, yy), (x + total, yy), capa_linea)
        xx = x
        for j, texto in enumerate(fila):
            al = alineacion[j] if j < len(alineacion) else "ml"
            if texto:
                if al in ("mr", "br", "tr"):
                    px = xx + anchos[j] - 0.0015
                elif al in ("mc", "bc", "tc"):
                    px = xx + anchos[j] / 2.0
                else:
                    px = xx + 0.0015
                lam.tx(str(texto), (px, yy + alto * 0.32), h, capa, al)
            xx += anchos[j]
    lam.ln((x, y), (x + total, y), capa_linea)
    xx = x
    for w in anchos:
        lam.ln((xx, y), (xx, yy), capa_linea)
        xx += w
    lam.ln((xx, y), (xx, yy), capa_linea)
    return yy


def leyenda(lam, x: float, y: float, items, h: float = 0.0021,
            paso: float = 0.0056, titulo: str | None = None) -> float:
    """Leyenda de símbolos; cada ítem es (tipo, texto).

    Tipos: "linea", "linea-corta", "circulo", "circulo-negro", "cuadrado",
    "linea:LT" (con LT = CONTINUOUS, DASHED, PHANTOM…) y "bloque:NOMBRE".
    """
    yy = y
    if titulo:
        lam.tx(titulo.upper(), (x, yy), h * 1.2, "A-ANNO", "ml")
        yy -= paso * 0.9
    for tipo, texto in items:
        gx, gy = x + 0.004, yy - 0.0015
        if tipo == "linea":
            lam.ln((gx - 0.0035, gy), (gx + 0.0035, gy), "A-ANNO")
        elif tipo.startswith("linea:"):
            # "linea:CAPA:LINETYPE" — la capa es opcional y define el color
            capa, lt = "A-ANNO", None
            for parte in tipo.split(":")[1:]:
                if parte in CAPAS:
                    capa = parte
                else:
                    lt = parte
            lam.ln((gx - 0.0035, gy), (gx + 0.0035, gy), capa, lt=lt)
        elif tipo == "linea-corta":
            lam.ln((gx - 0.0020, gy), (gx + 0.0020, gy), "A-ANNO")
        elif tipo == "circulo":
            lam.circ((gx, gy), 0.0018, "A-ANNO")
        elif tipo == "circulo-negro":
            lam.circ((gx, gy), 0.0018, "A-ANNO")
            lam.circ((gx, gy), 0.0008, "A-ANNO")
        elif tipo == "cuadrado":
            lam.pl([(gx - 0.0018, gy - 0.0018), (gx + 0.0018, gy - 0.0018),
                    (gx + 0.0018, gy + 0.0018), (gx - 0.0018, gy + 0.0018)],
                   "A-ANNO")
        elif tipo.startswith("bloque:"):
            lam.blk(tipo.split(":", 1)[1], (gx - 0.0025, gy - 0.0025),
                    escala=0.005, capa="A-ANNO")
        lam.tx(texto, (x + 0.0105, yy), h, "A-ANNO", "ml")
        yy -= paso


def rayado(lam, caja, paso: float = 0.0035, capa: str = "A-HATCH",
           ang: float = 45.0):
    """Rayado recortado a una caja (x0, y0, x1, y1) en metros de papel.

    Sirve para las secciones de detalle: materiales en corte con rayado de 45°
    o con líneas horizontales/verticales para estratos (contrapiso, aislación).
    """
    x0, y0 = min(caja[0], caja[2]), min(caja[1], caja[3])
    x1, y1 = max(caja[0], caja[2]), max(caja[1], caja[3])
    a = float(ang) % 180.0
    if a < 1e-6:
        y = y0 + paso
        while y < y1 - 1e-9:
            lam.ln((x0, y), (x1, y), capa)
            y += paso
        return
    if abs(a - 90.0) < 1e-6:
        x = x0 + paso
        while x < x1 - 1e-9:
            lam.ln((x, y0), (x, y1), capa)
            x += paso
        return
    s = math.tan(math.radians(a))
    cs = [y - s * x for x, y in ((x0, y0), (x1, y0), (x0, y1), (x1, y1))]
    c = min(cs) + paso * 0.5
    while c < max(cs) - 1e-9:
        if s > 0:
            lo, hi = max(y0, s * x0 + c), min(y1, s * x1 + c)
        else:
            lo, hi = max(y0, s * x1 + c), min(y1, s * x0 + c)
        if hi - lo > 1e-9:
            lam.ln(((lo - c) / s, lo), ((hi - c) / s, hi), capa)
        c += paso


def cano(lam, tr: Tr, pts, capa: str = "I-SAN", lt: str | None = None):
    """Trazado de cañería / conducto en coordenadas de proyecto."""
    pp = [tr(p) for p in pts]
    for a, b in zip(pp, pp[1:]):
        lam.ln(a, b, capa, lt=lt)
    return pp


# ---------------------------------------------------------------------------
# cortes y vistas
# ---------------------------------------------------------------------------
NIVELES = {
    "TERRENO": -0.30,
    "PLATEA": -0.15,
    "PISO_PB": 0.00,
    "CIELO_PB": 2.80,
    "PISO_PA": 2.90,
    "CIELO_PA": 5.60,
    "AZOTEA": 5.75,
    "PARAPETO": 6.55,
    "TECHO_COCINA": 2.95,          # cielorraso / cara inferior de la cubierta
    "TECHO_COCINA_TOPE": 3.30,     # cara superior: apoyo de la plataforma
}

ANTEPECHO = 0.90


def _muros_cortados(spec: dict, eje: str, valor: float):
    """Muros que el plano de corte atraviesa, con su posición y aberturas."""
    out = []
    for w in spec["muros"]:
        x1, y1 = float(w["p1"][0]), float(w["p1"][1])
        x2, y2 = float(w["p2"][0]), float(w["p2"][1])
        t = float(w.get("espesor", 0.2))
        ops = w.get("aberturas", [])
        if eje == "X":
            if abs(y2 - y1) > 1e-6:
                continue
            if valor < min(x1, x2) - t / 2 or valor > max(x1, x2) + t / 2:
                continue
            L = abs(x2 - x1)
            u = 1.0 if x2 >= x1 else -1.0
            along = (y1 + y2) / 2.0
            s_cut = (valor - x1) / u
        else:
            if abs(x2 - x1) > 1e-6:
                continue
            if valor < min(y1, y2) - t / 2 or valor > max(y1, y2) + t / 2:
                continue
            L = abs(y2 - y1)
            u = 1.0 if y2 >= y1 else -1.0
            along = (x1 + x2) / 2.0
            s_cut = (valor - y1) / u
        huecos = []
        for o in ops:
            if abs(s_cut - float(o["s"])) <= float(o["ancho"]) / 2.0:
                tipo = o.get("tipo", "hueco")
                if tipo == "hueco":
                    sill = 0.0
                elif tipo == "ventana":
                    sill = float(o.get("antepecho", ANTEPECHO))
                else:
                    sill = 0.0
                alto = float(o.get("alto", 2.10 if sill == 0.0 else 1.40))
                huecos.append((sill, sill + alto))
        out.append({"along": along, "t": t, "L": L, "huecos": huecos,
                    "id": w.get("id", ""), "tipo": w.get("tipo", "interior")})
    return out


def _rect(lam, tr, a0: float, a1: float, z0: float, z1: float,
          capa: str = "A-WALL"):
    if a1 - a0 < 1e-6 or z1 - z0 < 1e-6:
        return
    lam.pl([tr((a0, z0)), tr((a1, z0)), tr((a1, z1)), tr((a0, z1))], capa)


def terreno(lam, tr, a0: float, a1: float, capa: str = "A-WALL",
            h: float = 0.30, paso: float = 0.10):
    """Línea de terreno con rayado bajo el nivel 0."""
    lam.ln(tr((a0, 0)), tr((a1, 0)), capa)
    z = NIVELES["TERRENO"]
    lam.ln(tr((a0, z)), tr((a1, z)), "A-AREA")
    a = a0
    while a < a1:
        lam.ln(tr((a, 0)), tr((min(a + h, a1), z)), "A-HATCH")
        a += paso



def corte(lam, pb: dict, pa: dict, eje: str = "X", valor: float = 5.10,
          origen=(0.06, 0.05), escala: float | None = None,
          a0: float | None = None, a1: float | None = None,
          etiquetas: bool = True, cotas: bool = True,
          con_escalera: bool = False, ancla=(0.0, 0.0),
          parapeto: bool = True) -> Tr:
    """Corte vertical de la vivienda (PB + PA + azotea).

    `eje="X"` corta con un plano x = valor y el eje horizontal del dibujo es Y;
    `eje="Y"` corta con y = valor y el eje horizontal es X.  La sección se arma
    con los muros del spec que el plano atraviesa (con sus aberturas), las losas
    y el terreno: no hay geometría inventada.
    """
    tr = Tr.anclado(origen[0], origen[1], escala or lam.escala, ancla)
    N = NIVELES
    if a0 is None or a1 is None:
        lims = []
        for s in (pb, pa):
            for w in s["muros"]:
                lims.append(w["p1"][1 if eje == "X" else 0])
                lims.append(w["p2"][1 if eje == "X" else 0])
        a0 = min(lims) - 0.4 if a0 is None else a0
        a1 = max(lims) + 0.4 if a1 is None else a1

    # terreno y platea
    terreno(lam, tr, a0, a1)
    _rect(lam, tr, a0, a1, N["PLATEA"], N["PISO_PB"], "A-WALL")

    # muros cortados de PB y PA
    for spec, z0, z1, capa in ((pb, N["PISO_PB"], N["CIELO_PB"], "A-WALL"),
                               (pa, N["PISO_PA"], N["CIELO_PA"], "A-WALL")):
        for m in _muros_cortados(spec, eje, valor):
            b0, b1 = m["along"] - m["t"] / 2.0, m["along"] + m["t"] / 2.0
            huecos = sorted(m["huecos"])
            zc = z0
            for h0, h1 in huecos:
                _rect(lam, tr, b0, b1, zc, min(h0, z1), capa)
                zc = max(zc, h1)
            _rect(lam, tr, b0, b1, zc, z1, capa)
    # parapetos: los muros exteriores de PA suben hasta +6,55
    if parapeto:
        for m in _muros_cortados(pa, eje, valor):
            if m.get("tipo") == "exterior":
                b0 = m["along"] - m["t"] / 2.0
                b1 = m["along"] + m["t"] / 2.0
                _rect(lam, tr, b0, b1, N["AZOTEA"], N["PARAPETO"], "A-WALL")

    # losas: piso de PA y azotea sobre el cuerpo principal, techo de cocina
    pa_ini = min(w["p1"][1] for w in pa["muros"])
    pa_fin = max(w["p1"][1] for w in pa["muros"])
    for w in pa["muros"]:
        pa_fin = max(pa_fin, max(w["p1"][1], w["p2"][1]))
    pa_ini = min(pa_ini, min(min(w["p1"][1], w["p2"][1]) for w in pa["muros"]))
    pb_fin = max(max(w["p1"][1], w["p2"][1]) for w in pb["muros"])
    if eje == "X":
        _rect(lam, tr, pa_ini, pa_fin, N["CIELO_PB"], N["PISO_PA"], "A-WALL")
        _rect(lam, tr, pa_ini, pa_fin, N["CIELO_PA"], N["AZOTEA"], "A-WALL")
        if pb_fin > pa_fin + 0.01:
            _rect(lam, tr, pa_fin, pb_fin, N["CIELO_PB"],
                  N["TECHO_COCINA_TOPE"], "A-WALL")
        lam.ln(tr((a0, N["CIELO_PB"])), tr((a1, N["CIELO_PB"])), "A-AREA")
    else:
        xs = [c for s in (pb, pa) for w in s["muros"]
              for c in (w["p1"][0], w["p2"][0])]
        x0, x1 = min(xs), max(xs)
        _rect(lam, tr, x0, x1, N["CIELO_PB"], N["PISO_PA"], "A-WALL")
        _rect(lam, tr, x0, x1, N["CIELO_PA"], N["AZOTEA"], "A-WALL")
        lam.ln(tr((a0, N["CIELO_PB"])), tr((a1, N["CIELO_PB"])), "A-AREA")

    # escalera en elevación si el corte la atraviesa
    if con_escalera and eje == "X" and 1.6 <= valor <= 3.6:
        escalera_corte(lam, tr, x0=1.6, y0=9.35, ancho=2.0, huella=0.28,
                       alzadas=16, valor_x=valor)

    # nombres de los locales que corta el plano
    if etiquetas:
        for amb in pb.get("ambientes", []):
            c = float(amb["x"]) + float(amb["w"]) / 2.0
            y = float(amb["y"]) + float(amb["h"]) / 2.0
            en = (float(amb["x"]) <= valor <= float(amb["x"]) + float(amb["w"])
                  if eje == "X" else
                  float(amb["y"]) <= valor <= float(amb["y"]) + float(amb["h"]))
            if not en:
                continue
            pos = y if eje == "X" else c
            lam.tx(amb["nombre"], tr((pos, 1.30)), 0.0022, "A-ANNO", "mc")
            lam.tx(f"{amb['w'] * amb['h']:.2f} m2", tr((pos, 0.95)), 0.0019,
                   "A-ANNO", "mc")
        for amb in pa.get("ambientes", []):
            c = float(amb["x"]) + float(amb["w"]) / 2.0
            y = float(amb["y"]) + float(amb["h"]) / 2.0
            en = (float(amb["x"]) <= valor <= float(amb["x"]) + float(amb["w"])
                  if eje == "X" else
                  float(amb["y"]) <= valor <= float(amb["y"]) + float(amb["h"]))
            if not en:
                continue
            pos = y if eje == "X" else c
            lam.tx(amb["nombre"], tr((pos, N["PISO_PA"] + 1.30)), 0.0022,
                   "A-ANNO", "mc")

    if cotas:
        for z, txt in ((N["PISO_PB"], "+0,00"), (N["PISO_PA"], "+2,90"),
                       (N["CIELO_PA"], "+5,60"), (N["AZOTEA"], "+5,75"),
                       (N["PARAPETO"], "+6,55")):
            p = tr((a1 + 0.10, z))
            lam.ln(tr((a1 - 0.06, z)), p, "A-DIM")
            nivel(lam, p, txt, lado=1)
        xl = tr((a0 - 0.45, 0))[0]
        py = lambda z: tr((0, z))[1]
        cota_v(lam, py(N["PISO_PB"]), py(N["CIELO_PB"]), xl, -0.009, "2,80")
        cota_v(lam, py(N["PISO_PA"]), py(N["CIELO_PA"]), xl, -0.009, "2,70")
        cota_v(lam, py(N["PISO_PB"]), py(N["CIELO_PA"]), xl - 0.014, -0.009,
               "5,60")
        cota_v(lam, py(N["PISO_PB"]), py(N["PARAPETO"]), xl - 0.028, -0.009,
               "6,55")
    return tr



def buscar_muro(spec: dict, muro_id: str) -> dict:
    for w in spec["muros"]:
        if w.get("id") == muro_id:
            return w
    raise KeyError(f"muro inexistente en el spec: {muro_id}")


def longitud(muro: dict) -> float:
    return math.hypot(float(muro["p2"][0]) - float(muro["p1"][0]),
                      float(muro["p2"][1]) - float(muro["p1"][1]))


def alfeizar(lam, tr, s0: float, s1: float, z: float, vuelo: float = 0.06):
    """Alféizar / goterón bajo una ventana en vista."""
    lam.ln(tr((s0 - vuelo, z)), tr((s1 + vuelo, z)), "A-WIN")


def elevacion(lam, tr, muro: dict, z0: float = 0.0, z1: float | None = None,
              espejo: bool = False, capa: str = "A-WALL",
              marco: bool = True, L_ref: float | None = None,
              z_baja: float | None = None):
    """Fachada de un muro con sus aberturas, en vista (coordenada s, z).

    `L_ref` fija el eje de espejado (por defecto la longitud del propio muro);
    permite espejar todas las plantas de una vista respecto del mismo eje.
    `z_baja` recorta la base del muro (por ejemplo cuando el cuerpo de PA está
    retirado y la cubierta tapa los primeros centímetros) sin mover las
    aberturas, que siguen referidas al nivel `z0`.
    """
    L = longitud(muro)
    Lr = L if L_ref is None else L_ref
    z1 = z1 if z1 is not None else z0 + 2.80
    zb = z0 if z_baja is None else max(z0, z_baja)

    def S(s: float, z: float):
        return tr(((Lr - s) if espejo else s, z))

    lam.pl([S(0, zb), S(L, zb), S(L, z1), S(0, z1)], capa)
    for o in sorted(muro.get("aberturas", []), key=lambda o: o["s"]):
        tipo = o.get("tipo", "hueco")
        if tipo == "hueco":
            continue
        s, w = float(o["s"]), float(o["ancho"])
        sill = 0.0 if tipo in ("puerta", "porton") else float(
            o.get("antepecho", ANTEPECHO))
        hgt = float(o.get("alto", 2.10 if sill == 0.0 else 1.40))
        a, b = s - w / 2.0, s + w / 2.0
        capa_o = "A-WIN" if tipo == "ventana" else "A-DOOR"
        za, zb2 = z0 + sill, z0 + sill + hgt
        if zb2 <= zb + 1e-6:
            continue
        recortada = (z0 + sill) < zb - 1e-9
        za = max(za, zb)
        nombre = _modena_f(w, hgt)
        if tipo == "ventana" and not recortada and nombre in lam.doc.blocks:
            xref = b if espejo else a
            lam.blk(nombre, S(xref, z0 + sill), rot=0, capa="A-WIN")
        else:
            lam.pl([S(a, za), S(b, za), S(b, zb2), S(a, zb2)], capa_o)
            if marco:
                m = 0.05
                lam.pl([S(a + m, za + m), S(b - m, za + m), S(b - m, zb2 - m),
                        S(a + m, zb2 - m)], capa_o)
                if tipo == "ventana":
                    lam.ln(S(a + w / 2, za + m), S(a + w / 2, zb2 - m), capa_o)
                    lam.ln(S(a + m, za + hgt * 0.72), S(b - m, za + hgt * 0.72),
                           capa_o)
                elif tipo == "puerta":
                    lam.ln(S(a + w / 2, za + m), S(a + w / 2, zb2 - m), capa_o)
                    lam.circ(S(b - 0.10, zb2 - 0.08), 0.0016, capa_o)
        if tipo == "ventana":
            p0, p1 = S(a - 0.06, za), S(b + 0.06, za)
            lam.ln(p0, p1, "A-WIN")
    return L


def fachada(lam, pb: dict, pa: dict, muro_id: str, origen=(0.06, 0.05),
            escala: float | None = None, espejo: bool = False,
            con_texto: bool = True, ancla=(0.0, 0.0),
            z_oculto: float | None = None) -> Tr:
    """Vista de un muro de fachada: PB, banda de losa, PA y parapeto.

    `z_oculto` se usa cuando el cuerpo de PA está retirado del plano de la
    vista (contrafrente): la cubierta del sector de cocina tapa los primeros
    centímetros del muro de PA, que se dibuja recién por encima de esa cota.
    """
    tr = Tr.anclado(origen[0], origen[1], escala or lam.escala, ancla)
    N = NIVELES
    m_pb = buscar_muro(pb, muro_id)
    L_pb = longitud(m_pb)
    try:
        m_pa = buscar_muro(pa, muro_id)
        L_pa = longitud(m_pa)
    except KeyError:
        m_pa, L_pa = None, 0.0

    terreno(lam, tr, -0.6, L_pb + 0.6)
    elevacion(lam, tr, m_pb, N["PISO_PB"], N["CIELO_PB"], espejo, L_ref=L_pb)
    if m_pa is not None and L_pa > 0.0:
        a0 = 0.0 if not espejo else L_pb - L_pa
        a1 = a0 + L_pa
        zb = N["PISO_PA"] if z_oculto is None else max(N["PISO_PA"], z_oculto)
        if z_oculto is None:
            _rect(lam, tr, a0, a1, N["CIELO_PB"], N["PISO_PA"], "A-WALL")
        else:
            # el cuerpo de PA está retirado: se ve la banda de la cubierta
            _rect(lam, tr, a0, a1, N["CIELO_PB"], zb, "A-WALL")
            lam.ln(tr((a0, N["TECHO_COCINA"])), tr((a1, N["TECHO_COCINA"])),
                   "A-WALL")
        elevacion(lam, tr, m_pa, N["PISO_PA"], N["CIELO_PA"], espejo,
                  L_ref=L_pb, z_baja=zb)
        _rect(lam, tr, a0, a1, N["CIELO_PA"], N["AZOTEA"], "A-WALL")
        _rect(lam, tr, a0, a1, N["AZOTEA"], N["PARAPETO"], "A-WALL")
        if L_pb > L_pa + 0.01:
            # el tramo sin PA queda como techo bajo (sector cocina)
            c0 = 0.0 if espejo else L_pa
            _rect(lam, tr, c0, c0 + (L_pb - L_pa), N["CIELO_PB"],
                  N["TECHO_COCINA"], "A-WALL")
            _rect(lam, tr, c0, c0 + (L_pb - L_pa), N["TECHO_COCINA"],
                  N["TECHO_COCINA_TOPE"], "A-WALL")
    if con_texto:
        lam.tx(f"VISTA {muro_id}", tr((L_pb / 2.0, N["PARAPETO"] + 0.30)),
               0.0032, "A-ANNO", "mc")
    return tr


def escalera_corte(lam, tr, x0: float, y0: float, ancho: float = 2.0,
                   huella: float = 0.28, alzadas: int = 16,
                   valor_x: float = 2.1, capa: str = "A-WALL"):
    """Perfil de la escalera en corte (tramo que corta el plano vertical)."""
    hueso = 0.10
    fw = (ancho - hueso) / 2.0
    alzada = NIVELES["PISO_PA"] / alzadas
    n1 = alzadas // 2
    if valor_x <= x0 + fw:          # tramo 1: sube hacia el fondo
        for k in range(n1):
            y = y0 + k * huella
            z = (k + 1) * alzada
            lam.ln(tr((y, z)), tr((y + huella, z)), capa)
            lam.ln(tr((y, z)), tr((y, z - alzada)), capa)
        y_desc = y0 + (n1 - 1) * huella
        lam.ln(tr((y_desc, n1 * alzada)), tr((y_desc + 1.0, n1 * alzada)), capa)
    else:                            # tramo 2: llega al nivel de PA
        y_fin = y0 + (n1 - 1) * huella + 1.0
        for k in range(alzadas - n1):
            y = y_fin - k * huella
            z = n1 * alzada + (k + 1) * alzada
            lam.ln(tr((y, z)), tr((y - huella, z)), capa)
            lam.ln(tr((y, z)), tr((y, z - alzada)), capa)

    return tr


# ---------------------------------------------------------------------------
# tanque de reserva
# ---------------------------------------------------------------------------
def tanque_apoyo(lam, tr, s0: float, s1: float, z: float, alto: float = 1.15,
                 espesor: float = 0.12, capa: str = "A-WALL",
                 etiqueta: str | None = None, h_txt: float = 0.0019):
    """Tanque de reserva sobre plataforma, visto en fachada o en corte.

    `s0..s1` es el ancho en la vista y `z` la cota de apoyo de la plataforma
    (el techo del sector de cocina).  Dibuja plataforma, pedestales, cuerpo,
    tapa, caño de ventilación y bajada, para que el tanque exista fuera de la
    planta de techos.
    """
    # plataforma de H°A° sobre el techo
    lam.pl([tr((s0, z)), tr((s1, z)), tr((s1, z + espesor)),
            tr((s0, z + espesor))], capa)
    # pedestales de apoyo
    for s in (s0 + 0.06, s1 - 0.20):
        lam.pl([tr((s, z - 0.10)), tr((s + 0.14, z - 0.10)),
                tr((s + 0.14, z)), tr((s, z))], capa)
    # cuerpo del tanque
    a, b = s0 + 0.10, s1 - 0.10
    zb = z + espesor
    lam.pl([tr((a, zb)), tr((b, zb)), tr((b, zb + alto)),
            tr((a, zb + alto))], capa)
    lam.ln(tr((a, zb + alto - 0.10)), tr((b, zb + alto - 0.10)), capa)
    # ventilación / tapón de inspección
    c = a + (b - a) / 2.0
    lam.ln(tr((c, zb + alto)), tr((c, zb + alto + 0.16)), capa)
    lam.ln(tr((c - 0.05, zb + alto + 0.16)), tr((c + 0.05, zb + alto + 0.16)),
           capa)
    # bajada de agua fría (montante) hacia la vivienda
    lam.ln(tr((a + 0.05, zb)), tr((a + 0.05, z - 0.55)), capa)
    if etiqueta:
        lam.tx(etiqueta, tr(((s0 + s1) / 2.0, zb + alto + 0.24)), h_txt,
               "A-ANNO", "mc")
    return (a, b, zb, zb + alto)


def tanque_planta(lam, tr, x: float, y: float, w: float = 1.10,
                  h: float = 1.10, capa: str = "A-WALL",
                  etiqueta: str | None = None, h_txt: float = 0.0020):
    """Tanque de reserva en planta: plataforma, cuerpo, tapa y bajada."""
    m = 0.15                                    # vuelo de la plataforma
    lam.pl([tr((x - m, y - m)), tr((x + w + m, y - m)),
            tr((x + w + m, y + h + m)), tr((x - m, y + h + m))], "A-AREA")
    lam.pl([tr((x, y)), tr((x + w, y)), tr((x + w, y + h)), tr((x, y + h))], capa)
    lam.circ(tr((x + w / 2.0, y + h / 2.0)), 0.016, capa)       # tapa
    lam.ln(tr((x + w / 2.0, y + h)), tr((x + w / 2.0, y + h + m)), capa)
    lam.circ(tr((x + 0.16, y + 0.16)), 0.010, "I-AF")           # bajada AF
    if etiqueta:
        lam.tx(etiqueta, tr((x + w / 2.0, y - m - 0.26)), h_txt, "A-ANNO", "mc")
    return (x, y, x + w, y + h)
