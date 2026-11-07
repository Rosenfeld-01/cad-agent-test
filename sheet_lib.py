#!/usr/bin/env python3
"""
sheet_lib.py — drawing-sheet toolkit for the Level 2 set.

Everything is drawn in **paper meters**: each sheet's model space is the sheet
(A2 = 0.594 x 0.420 m). The plan is drawn in project coordinates (m) and
transformed to paper with factor 1/scale (1:50 -> 0.02).

Architectural plans (L01/L02/L03) are emitted at **real scale**: with
``Lamina(..., escala_real=True)`` the whole model space is multiplied by
``escala`` on save, so **1 unit = 1 m of the project** (a 6.40 m wall measures
6.40 u). This is equivalent to plotting the sheet at 1:scale, so internal scales
(the 1:20 detail on L03, scale bars) are preserved. Sections, facades, services,
and details (L04-L13) remain in paper meters (1 u = 1 m of paper).

Rules it follows
----------------
- Wall and opening geometry comes from the same spec used by `plan.py` (it
  reuses `plan._wall_solids`), so the sheet and the validator cannot diverge.
- Symbols come from the `CAD_Blocks/` library: they are declared as block
  definitions on the sheet and inserted at scale = 1/scale.
- Sheet layers: those in `AGENTS.md` (A-WALL, A-DOOR, A-WIN, A-AREA, A-ANNO,
  A-DIM, A-AXIS) plus A-MOB (furniture), A-HATCH, X-FRAME (frame and title
  block), and I-ELE / I-SAN / I-GAS for services.

Public helper names are kept in Spanish for compatibility with existing sheet
scripts; new code should call them as-is.
"""
from __future__ import annotations

import math
from pathlib import Path

import ezdxf
from ezdxf.enums import TextEntityAlignment
from ezdxf.math import Vec2, Matrix44

import plan as PL
import blocks_build as BB
import blocks_data_architecture as DA
import blocks_data_bathroom_exterior as DB
import blocks_data_services as DI

FORMATOS = {
    "A4": (0.297, 0.210),
    "A3": (0.420, 0.297),
    "A2": (0.594, 0.420),
}

# layer -> (ACI color, plot lineweight in 1/100 mm)
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
    # water networks: one layer and one color per network (AF blue, AC red,
    # CL green, PL yellow). Previously everything went to I-SAN and was indistinguishable.
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
    """Linear transform project (m) -> paper (sheet meters)."""

    def __init__(self, ox: float, oy: float, escala: float):
        self.ox, self.oy = float(ox), float(oy)
        self.esc = 1.0 / float(escala)

    @classmethod
    def anclado(cls, ox: float, oy: float, escala: float, ancla=(0.0, 0.0)):
        """Transform that maps the project `ancla` point to (ox, oy)."""
        e = 1.0 / float(escala)
        return cls(ox - ancla[0] * e, oy - ancla[1] * e, escala)

    def __call__(self, p):
        return (self.ox + p[0] * self.esc, self.oy + p[1] * self.esc)

    def s(self, d: float) -> float:
        return float(d) * self.esc

    def v(self, vec: Vec2):
        return (self.ox + vec.x * self.esc, self.oy + vec.y * self.esc)


def definir_bloques(doc) -> int:
    """Declare the 97 CAD_Blocks block definitions in the document."""
    items = DA.BLOCKS + DB.BLOCKS + DI.BLOCKS
    n = 0
    for it in items:
        if it["name"] in doc.blocks:
            continue
        blk = doc.blocks.new(it["name"])
        BB.draw(blk, it)
        n += 1
    return n



class Lamina:
    """One drawing-set sheet, in paper meters."""

    def __init__(self, numero: int, total: int, titulo: str, escala: int,
                 formato: str = "A2", proyecto: str = "HOUSING",
                 comitente: str = "CLIENT: TO BE DEFINED",
                 fecha: str = "2026-03-11", codigo: str = "L01",
                 etapa: str = "CONSTRUCTION DOCUMENT", escala_real: bool = False):
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

    # --- paper primitives ------------------------------------------------
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
        """Like `ln`, but does not repeat an identical segment already drawn.

        Avoids duplicates that appear when chaining dimensions (shared 45-degree
        tick and extension line) and when closing stair outlines.
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
            raise KeyError(f"unknown block: {nombre}")
        e = self.esc if escala is None else escala
        attrs = {"xscale": e, "yscale": e, "rotation": rot}
        if capa:
            attrs["layer"] = capa
        return self.msp.add_blockref(nombre, p, dxfattribs=attrs)

    def sym(self, nombre: str, tr: Tr, x: float, y: float, rot: float = 0.0,
            capa: str | None = None):
        """Insert a library symbol in project coordinates."""
        return self.blk(nombre, tr((x, y)), rot=rot, capa=capa)

    # --- frame and title block -----------------------------------------------------
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
        self.tx("SINGLE-FAMILY HOUSE BETWEEN PARTY WALLS - CABA - SHEET SET L01/L13",
                (rx0 + 0.003, ry0 + rh * 0.828), 0.0016, "A-ANNO", "ml")
        self.tx(self.titulo, (rx0 + 0.003, ry0 + rh * 0.69), 0.0046, "A-ANNO", "ml")
        self.tx(etapa, (rx1 - 0.003, ry0 + rh * 0.69), 0.0019, "A-ANNO", "mr")
        self.tx(f"SCALE  1:{self.escala}", (rx0 + 0.003, ry0 + rh * 0.50),
                0.0032, "A-ANNO", "ml")
        self.tx("DIMENSIONS AND LEVELS IN METERS", (rx1 - 0.003, ry0 + rh * 0.50),
                0.0019, "A-ANNO", "mr")
        self.tx(f"DATE  {fecha}", (rx0 + 0.003, ry0 + rh * 0.31), 0.0024,
                "A-ANNO", "ml")
        self.tx(self.codigo, (rx0 + 0.124, ry0 + rh * 0.31), 0.0026, "A-ANNO", "ml")
        self.tx("DRAWN BY: CAD agent", (rx0 + 0.166, ry0 + rh * 0.31), 0.0020,
                "A-ANNO", "ml")
        self.tx(f"SHEET  {self.numero:02d}/{self.total:02d}",
                (rx0 + 0.003, ry0 + rh * 0.11), 0.0024, "A-ANNO", "ml")
        self.tx(self.formato, (rx0 + 0.124, ry0 + rh * 0.11), 0.0026, "A-ANNO", "ml")
        self.tx(comitente, (rx0 + 0.166, ry0 + rh * 0.11), 0.0020, "A-ANNO", "ml")

    def _a_escala_real(self):
        """Bring the sheet to real scale: 1 model unit = 1 m of the project.

        The sheet is built in paper meters; multiplying the whole model space by
        ``escala`` is equivalent to plotting at 1:scale. The plan becomes 1:1
        real (a 6.40 m wall measures 6.40 u) and internal scales (1:20 detail,
        scale bars) are preserved because they scale with the rest of the sheet.
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
# annotations
# ---------------------------------------------------------------------------
def flecha(lam, a, b, largo: float = 0.0026, ancho: float = 0.0009,
           capa: str = "A-DIM"):
    """Arrowhead with its tip at b, oriented along a->b."""
    ang = math.atan2(b[1] - a[1], b[0] - a[0])
    p1 = (b[0] - largo * math.cos(ang) + ancho * math.sin(ang),
          b[1] - largo * math.sin(ang) - ancho * math.cos(ang))
    p2 = (b[0] - largo * math.cos(ang) - ancho * math.sin(ang),
          b[1] - largo * math.sin(ang) + ancho * math.cos(ang))
    lam.pl([b, p1, p2], capa)


def cota(lam, a, b, off: float = 0.010, texto: str | None = None,
         h: float = 0.0022, capa: str = "A-DIM"):
    """Linear dimension between two paper points, offset `off` (perpendicular)."""
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
    # extension lines
    lam.ln_unica(a, (a2[0] + n[0] * 0.002 * sgn, a2[1] + n[1] * 0.002 * sgn), capa)
    lam.ln_unica(b, (b2[0] + n[0] * 0.002 * sgn, b2[1] + n[1] * 0.002 * sgn), capa)
    # dimension line
    lam.ln(a2, b2, capa)
    # 45-degree ticks (only once when two chained dimensions share a point)
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
    """Horizontal dimension on paper; the default value is written in meters."""
    if texto is None:
        texto = f"{abs(x1 - x0) * (escala if escala else lam.escala):.2f}"
    cota(lam, (x0, y), (x1, y), dy, texto, h, capa)


def cota_v(lam, y0: float, y1: float, x: float, dx: float,
           texto: str | None = None, h: float = 0.0022, capa: str = "A-DIM",
           escala: float | None = None):
    """Vertical dimension on paper; the default value is written in meters."""
    if texto is None:
        texto = f"{abs(y1 - y0) * (escala if escala else lam.escala):.2f}"
    cota(lam, (x, y0), (x, y1), dx, texto, h, capa)


def nivel(lam, p, texto: str, r: float = 0.0018, h: float = 0.0022,
          capa: str = "A-DIM", lado: int = 1):
    """Level mark: isosceles triangle + text."""
    x, y = p
    lam.pl([(x, y), (x - r, y + r * 1.7), (x + r, y + r * 1.7)], capa)
    lam.ln((x - r * 1.6, y + r * 1.7), (x + r * 1.6, y + r * 1.7), capa)
    lam.tx(texto, (x + (r * 2.2 if lado > 0 else -r * 2.2), y + r * 1.7), h,
           capa, "ml" if lado > 0 else "mr")


def norte(lam, p, r: float = 0.014):
    """Simplified compass rose (north arrow)."""
    x, y = p
    lam.circ((x, y), r, "A-ANNO")
    lam.pl([(x, y + r * 0.92), (x - r * 0.34, y - r * 0.55),
            (x, y - r * 0.22), (x + r * 0.34, y - r * 0.55)], "A-ANNO")
    lam.tx("N", (x, y + r * 1.18), 0.0032, "A-ANNO", "mc")


def escala_grafica(lam, p, escala: int, tramos=(0, 1, 2, 5), h: float = 0.0022):
    """Scale bar with alternating 1 m project segments."""
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
    """Open-stair or balcony railing: double line with posts.

    `pts` are project points; thickness and spacing are given in paper meters.
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
    """Note block; returns the final y (for chaining)."""
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
# plan
# ---------------------------------------------------------------------------
BLOCK_SIZES = {it["name"]: (it["w"], it["h"])
               for it in DA.BLOCKS + DB.BLOCKS + DI.BLOCKS}


def poner(lam, nombre: str, tr: Tr, x: float, y: float, rot: int = 0,
          capa: str | None = None, escala: float | None = None):
    """Insert a block with its rotated lower-left corner at project (x, y)."""
    w, h = BLOCK_SIZES[nombre]
    rot = int(rot) % 360
    bx, by = {0: (0.0, 0.0), 90: (-h, 0.0), 180: (-w, -h), 270: (0.0, -w)}[rot]
    p = tr((x - bx, y - by))
    return lam.blk(nombre, p, rot=rot, capa=capa, escala=escala)


def caja_rotada(nombre: str, x: float, y: float, rot: int = 0):
    """Occupied box (x0, y0, x1, y1) of a block placed at (x, y)."""
    w, h = BLOCK_SIZES[nombre]
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
    """Opening symbol in the wall gap [a, b], in paper coordinates."""
    pa, pb = p1 + u * a, p1 + u * b
    tipo = o.get("type", "opening")
    if tipo == "door":
        hinge = pa + n * (t / 2)
        leaf = hinge + n * (b - a)
        lam.ln(tr.v(hinge), tr.v(leaf), "A-DOOR")
        ang_u = math.degrees(math.atan2(u.y, u.x))
        ang_n = math.degrees(math.atan2(n.y, n.x))
        a0, a1 = min(ang_u, ang_n), max(ang_u, ang_n)
        if a1 - a0 > 180:
            a0, a1 = a1, a0 + 360
        lam.arc(tr.v(hinge), tr.s(b - a), a0, a1, "A-DOOR")
    elif tipo == "gate":
        lam.ln(tr.v(pa + n * (t / 2)), tr.v(pb + n * (t / 2)), "A-DOOR")
        lam.ln(tr.v(pa - n * (t / 2)), tr.v(pb - n * (t / 2)), "A-DOOR")
    elif tipo == "window":
        nombre = _modena_p(b - a)
        if (1.0 / tr.esc) <= 60 and nombre in lam.doc.blocks:
            centro = p1 + u * ((a + b) / 2.0)
            rot = math.degrees(math.atan2(u.y, u.x))
            lam.blk(nombre, tr.v(centro), rot=rot, capa="A-WIN")
        else:                                   # generic fallback
            off = t / 6.0
            for s in (off, -off):
                lam.ln(tr.v(pa + n * s), tr.v(pb + n * s), "A-WIN")
            for p in (pa, pb):
                lam.ln(tr.v(p + n * (t / 2)), tr.v(p - n * (t / 2)), "A-WIN")
    elif tipo == "opening":
        pass
    else:
        raise ValueError(f"unknown opening type: {tipo}")


def planta(lam, spec: dict, origen=(0.10, 0.05), escala: float | None = None,
           etiquetas: bool = True, areas: bool = True,
           con_ambientes: bool = True, mob=None, capa_muro: str = "A-WALL",
           capa_area: str = "A-AREA", capa_texto: str = "A-ANNO",
           t_muro: float | None = None, h_nombre: float = 0.0026,
           h_area: float = 0.0022, ancla=(0.0, 0.0)) -> Tr:
    """Draw a complete plan (rooms + walls + openings + furniture)."""
    esc = escala or lam.escala
    tr = Tr.anclado(origen[0], origen[1], esc, ancla)

    if con_ambientes:
        for amb in spec.get("rooms", []):
            x, y = float(amb["x"]), float(amb["y"])
            w, h = float(amb["w"]), float(amb["h"])
            lam.pl([tr((x, y)), tr((x + w, y)), tr((x + w, y + h)), tr((x, y + h))],
                   capa_area)
            if not etiquetas:
                continue
            cx, cy = x + w / 2.0, y + h / 2.0
            rot = 90.0 if (w < 1.7 and h > w) else 0.0
            lam.tx(amb["name"], tr((cx, cy + (0.34 if areas else 0.0))),
                   h_nombre, capa_texto, "mc", rot)
            if areas:
                lam.tx(f"{w * h:.2f} m2", tr((cx, cy - 0.34)), h_area,
                       capa_texto, "mc", rot)

    muros = spec["walls"]
    ext_t = t_muro if t_muro is not None else 0.2
    muros_union = ([dict(m, thickness=t_muro) for m in muros]
                   if t_muro is not None else muros)
    for loop in PL.wall_outline(muros_union, ext_t):
        lam.pl([tr((x, y)) for x, y in loop], capa_muro)
    for muro in muros:
        t = t_muro if t_muro is not None else float(muro.get("thickness", 0.2))
        p1, p2 = Vec2(muro["p1"]), Vec2(muro["p2"])
        _solids, u, n, _L, cuts = PL._wall_solids(p1, p2, t,
                                                  muro.get("openings", []))
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
    """U-shaped two-flight stair with landing (16 risers of 0.18).

    Flight 1 rises along the west half (n1 - 1 treads), a 1.00 m landing at the
    rear, and flight 2 returns along the east half to the arrival level. `nota`
    is the paper point where the stair is labeled (optional).
    """
    hueso = 0.10
    fw = (ancho - hueso) / 2.0
    n1 = alzadas // 2
    y_desc = y0 + (n1 - 1) * huella
    y_fin = y_desc + 1.0
    if nivel == "PA":
        # flight 1 is below: mark the void and draw what arrives
        lam.ln(tr((x0, y0)), tr((x0 + fw, y_desc)), capa)
        lam.ln(tr((x0 + fw, y0)), tr((x0, y_desc)), capa)
        lam.tx("VOID", tr((x0 + fw / 2, y0 + 0.35)), 0.0018, "A-ANNO", "mc")
    else:
        for k in range(1, n1 - 1):      # the last tread is the landing edge
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

    # path: up flight 1, across the landing, then flight 2
    xa, xb = x0 + fw / 2, x1 + fw / 2
    lam.ln(tr((xa, y0 + 0.25)), tr((xa, y_desc + 0.50)), capa_ejes)
    lam.ln(tr((xa, y_desc + 0.50)), tr((xb, y_desc + 0.50)), capa_ejes)
    lam.ln(tr((xb, y_desc + 0.50)), tr((xb, y0 + 0.55)), capa_ejes)
    flecha(lam, tr((xb, y0 + 0.85)), tr((xb, y0 + 0.55)), capa=capa_ejes)
    lam.circ(tr((xa, y0 + 0.25)), 0.0034, capa_ejes)
    lam.tx("UP" if nivel == "PB" else "DOWN", tr((xa, y0 + 0.10)), 0.0019,
           "A-ANNO", "mc")
    if nota:
        hu = f"{huella:.2f}".replace(".", ",")
        an = f"{ancho:.2f}".replace(".", ",")
        lam.tx(f"STAIR {alzadas} RISERS x 0.18 - TREAD {hu} - WIDTH {an}",
               nota, 0.0021, "A-ANNO", "ml")




def tabla(lam, x: float, y: float, anchos, filas, alto_fila: float = 0.0055,
          h: float = 0.0021, cabecera: bool = True, alineacion=None,
          capa: str = "A-ANNO", capa_linea: str = "X-FRAME") -> float:
    """Simple table growing downward; returns the bottom-edge y."""
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
    """Symbol legend; each item is (type, text).

    Types: "linea", "linea-corta", "circulo", "circulo-negro", "cuadrado",
    "linea:LT" (LT = CONTINUOUS, DASHED, PHANTOM, ...), and "bloque:NAME".
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
            # "linea:LAYER:LINETYPE" - the layer is optional and defines the color
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
    """Hatch clipped to a box (x0, y0, x1, y1) in paper meters.

    Used for detail sections: cut materials with 45-degree hatching or
    horizontal/vertical lines for strata (subfloor, insulation).
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
    """Pipe/duct route in project coordinates."""
    pp = [tr(p) for p in pts]
    for a, b in zip(pp, pp[1:]):
        lam.ln(a, b, capa, lt=lt)
    return pp


# ---------------------------------------------------------------------------
# sections and views
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
    "TECHO_COCINA": 2.95,          # ceiling / underside of the roof
    "TECHO_COCINA_TOPE": 3.30,     # top face: platform support
}

ANTEPECHO = 0.90


def _muros_cortados(spec: dict, eje: str, valor: float):
    """Walls crossed by the section plane, with position and openings."""
    out = []
    for w in spec["walls"]:
        x1, y1 = float(w["p1"][0]), float(w["p1"][1])
        x2, y2 = float(w["p2"][0]), float(w["p2"][1])
        t = float(w.get("thickness", 0.2))
        ops = w.get("openings", [])
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
            if abs(s_cut - float(o["s"])) <= float(o["width"]) / 2.0:
                tipo = o.get("type", "opening")
                if tipo == "opening":
                    sill = 0.0
                elif tipo == "window":
                    sill = float(o.get("sill", ANTEPECHO))
                else:
                    sill = 0.0
                alto = float(o.get("height", 2.10 if sill == 0.0 else 1.40))
                huecos.append((sill, sill + alto))
        out.append({"along": along, "t": t, "L": L, "huecos": huecos,
                    "id": w.get("id", ""), "type": w.get("type", "interior")})
    return out


def _rect(lam, tr, a0: float, a1: float, z0: float, z1: float,
          capa: str = "A-WALL"):
    if a1 - a0 < 1e-6 or z1 - z0 < 1e-6:
        return
    lam.pl([tr((a0, z0)), tr((a1, z0)), tr((a1, z1)), tr((a0, z1))], capa)


def terreno(lam, tr, a0: float, a1: float, capa: str = "A-WALL",
            h: float = 0.30, paso: float = 0.10):
    """Ground line with hatching below level 0."""
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
    """Vertical section of the house (ground floor + upper floor + roof).

    `eje="X"` cuts with a plane x = value and the drawing's horizontal axis is Y;
    `eje="Y"` cuts with y = value and the horizontal axis is X. The section is
    built from the spec walls crossed by the plane (with their openings), the
    slabs, and the ground: no invented geometry.
    """
    tr = Tr.anclado(origen[0], origen[1], escala or lam.escala, ancla)
    N = NIVELES
    if a0 is None or a1 is None:
        lims = []
        for s in (pb, pa):
            for w in s["walls"]:
                lims.append(w["p1"][1 if eje == "X" else 0])
                lims.append(w["p2"][1 if eje == "X" else 0])
        a0 = min(lims) - 0.4 if a0 is None else a0
        a1 = max(lims) + 0.4 if a1 is None else a1

    # ground and slab
    terreno(lam, tr, a0, a1)
    _rect(lam, tr, a0, a1, N["PLATEA"], N["PISO_PB"], "A-WALL")

    # cut walls of the ground and upper floors
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
    # parapets: upper-floor exterior walls rise to +6.55
    if parapeto:
        for m in _muros_cortados(pa, eje, valor):
            if m.get("type") == "exterior":
                b0 = m["along"] - m["t"] / 2.0
                b1 = m["along"] + m["t"] / 2.0
                _rect(lam, tr, b0, b1, N["AZOTEA"], N["PARAPETO"], "A-WALL")

    # slabs: upper-floor slab and roof over the main body, kitchen roof
    pa_ini = min(w["p1"][1] for w in pa["walls"])
    pa_fin = max(w["p1"][1] for w in pa["walls"])
    for w in pa["walls"]:
        pa_fin = max(pa_fin, max(w["p1"][1], w["p2"][1]))
    pa_ini = min(pa_ini, min(min(w["p1"][1], w["p2"][1]) for w in pa["walls"]))
    pb_fin = max(max(w["p1"][1], w["p2"][1]) for w in pb["walls"])
    if eje == "X":
        _rect(lam, tr, pa_ini, pa_fin, N["CIELO_PB"], N["PISO_PA"], "A-WALL")
        _rect(lam, tr, pa_ini, pa_fin, N["CIELO_PA"], N["AZOTEA"], "A-WALL")
        if pb_fin > pa_fin + 0.01:
            _rect(lam, tr, pa_fin, pb_fin, N["CIELO_PB"],
                  N["TECHO_COCINA_TOPE"], "A-WALL")
        lam.ln(tr((a0, N["CIELO_PB"])), tr((a1, N["CIELO_PB"])), "A-AREA")
    else:
        xs = [c for s in (pb, pa) for w in s["walls"]
              for c in (w["p1"][0], w["p2"][0])]
        x0, x1 = min(xs), max(xs)
        _rect(lam, tr, x0, x1, N["CIELO_PB"], N["PISO_PA"], "A-WALL")
        _rect(lam, tr, x0, x1, N["CIELO_PA"], N["AZOTEA"], "A-WALL")
        lam.ln(tr((a0, N["CIELO_PB"])), tr((a1, N["CIELO_PB"])), "A-AREA")

    # stair in elevation if the section crosses it
    if con_escalera and eje == "X" and 1.6 <= valor <= 3.6:
        escalera_corte(lam, tr, x0=1.6, y0=9.35, ancho=2.0, huella=0.28,
                       alzadas=16, valor_x=valor)

    # names of the rooms crossed by the plane
    if etiquetas:
        for amb in pb.get("rooms", []):
            c = float(amb["x"]) + float(amb["w"]) / 2.0
            y = float(amb["y"]) + float(amb["h"]) / 2.0
            en = (float(amb["x"]) <= valor <= float(amb["x"]) + float(amb["w"])
                  if eje == "X" else
                  float(amb["y"]) <= valor <= float(amb["y"]) + float(amb["h"]))
            if not en:
                continue
            pos = y if eje == "X" else c
            lam.tx(amb["name"], tr((pos, 1.30)), 0.0022, "A-ANNO", "mc")
            lam.tx(f"{amb['w'] * amb['h']:.2f} m2", tr((pos, 0.95)), 0.0019,
                   "A-ANNO", "mc")
        for amb in pa.get("rooms", []):
            c = float(amb["x"]) + float(amb["w"]) / 2.0
            y = float(amb["y"]) + float(amb["h"]) / 2.0
            en = (float(amb["x"]) <= valor <= float(amb["x"]) + float(amb["w"])
                  if eje == "X" else
                  float(amb["y"]) <= valor <= float(amb["y"]) + float(amb["h"]))
            if not en:
                continue
            pos = y if eje == "X" else c
            lam.tx(amb["name"], tr((pos, N["PISO_PA"] + 1.30)), 0.0022,
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
    for w in spec["walls"]:
        if w.get("id") == muro_id:
            return w
    raise KeyError(f"unknown wall in spec: {muro_id}")


def longitud(muro: dict) -> float:
    return math.hypot(float(muro["p2"][0]) - float(muro["p1"][0]),
                      float(muro["p2"][1]) - float(muro["p1"][1]))


def alfeizar(lam, tr, s0: float, s1: float, z: float, vuelo: float = 0.06):
    """Sill / drip edge below a window in elevation."""
    lam.ln(tr((s0 - vuelo, z)), tr((s1 + vuelo, z)), "A-WIN")


def elevacion(lam, tr, muro: dict, z0: float = 0.0, z1: float | None = None,
              espejo: bool = False, capa: str = "A-WALL",
              marco: bool = True, L_ref: float | None = None,
              z_baja: float | None = None):
    """Facade of a wall with its openings, in elevation (s, z coordinates).

    `L_ref` sets the mirror axis (defaults to the wall's own length); it lets all
    floors of a view mirror about the same axis. `z_baja` clips the wall base
    (for example when the upper-floor body is set back and the roof covers the
    first centimeters) without moving the openings, which remain referenced to
    level `z0`.
    """
    L = longitud(muro)
    Lr = L if L_ref is None else L_ref
    z1 = z1 if z1 is not None else z0 + 2.80
    zb = z0 if z_baja is None else max(z0, z_baja)

    def S(s: float, z: float):
        return tr(((Lr - s) if espejo else s, z))

    lam.pl([S(0, zb), S(L, zb), S(L, z1), S(0, z1)], capa)
    for o in sorted(muro.get("openings", []), key=lambda o: o["s"]):
        tipo = o.get("type", "opening")
        if tipo == "opening":
            continue
        s, w = float(o["s"]), float(o["width"])
        sill = 0.0 if tipo in ("door", "gate") else float(
            o.get("sill", ANTEPECHO))
        hgt = float(o.get("height", 2.10 if sill == 0.0 else 1.40))
        a, b = s - w / 2.0, s + w / 2.0
        capa_o = "A-WIN" if tipo == "window" else "A-DOOR"
        za, zb2 = z0 + sill, z0 + sill + hgt
        if zb2 <= zb + 1e-6:
            continue
        recortada = (z0 + sill) < zb - 1e-9
        za = max(za, zb)
        nombre = _modena_f(w, hgt)
        if tipo == "window" and not recortada and nombre in lam.doc.blocks:
            xref = b if espejo else a
            lam.blk(nombre, S(xref, z0 + sill), rot=0, capa="A-WIN")
        else:
            lam.pl([S(a, za), S(b, za), S(b, zb2), S(a, zb2)], capa_o)
            if marco:
                m = 0.05
                lam.pl([S(a + m, za + m), S(b - m, za + m), S(b - m, zb2 - m),
                        S(a + m, zb2 - m)], capa_o)
                if tipo == "window":
                    lam.ln(S(a + w / 2, za + m), S(a + w / 2, zb2 - m), capa_o)
                    lam.ln(S(a + m, za + hgt * 0.72), S(b - m, za + hgt * 0.72),
                           capa_o)
                elif tipo == "door":
                    lam.ln(S(a + w / 2, za + m), S(a + w / 2, zb2 - m), capa_o)
                    lam.circ(S(b - 0.10, zb2 - 0.08), 0.0016, capa_o)
        if tipo == "window":
            p0, p1 = S(a - 0.06, za), S(b + 0.06, za)
            lam.ln(p0, p1, "A-WIN")
    return L


def fachada(lam, pb: dict, pa: dict, muro_id: str, origen=(0.06, 0.05),
            escala: float | None = None, espejo: bool = False,
            con_texto: bool = True, ancla=(0.0, 0.0),
            z_oculto: float | None = None) -> Tr:
    """View of a facade wall: ground floor, slab band, upper floor, and parapet.

    `z_oculto` is used when the upper-floor body is set back from the view plane
    (rear facade): the kitchen roof covers the first centimeters of the upper
    wall, which is drawn only above that level.
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
            # the upper-floor body is set back: the roof band is visible
            _rect(lam, tr, a0, a1, N["CIELO_PB"], zb, "A-WALL")
            lam.ln(tr((a0, N["TECHO_COCINA"])), tr((a1, N["TECHO_COCINA"])),
                   "A-WALL")
        elevacion(lam, tr, m_pa, N["PISO_PA"], N["CIELO_PA"], espejo,
                  L_ref=L_pb, z_baja=zb)
        _rect(lam, tr, a0, a1, N["CIELO_PA"], N["AZOTEA"], "A-WALL")
        _rect(lam, tr, a0, a1, N["AZOTEA"], N["PARAPETO"], "A-WALL")
        if L_pb > L_pa + 0.01:
            # the segment without an upper floor remains as a low roof (kitchen area)
            c0 = 0.0 if espejo else L_pa
            _rect(lam, tr, c0, c0 + (L_pb - L_pa), N["CIELO_PB"],
                  N["TECHO_COCINA"], "A-WALL")
            _rect(lam, tr, c0, c0 + (L_pb - L_pa), N["TECHO_COCINA"],
                  N["TECHO_COCINA_TOPE"], "A-WALL")
    if con_texto:
        lam.tx(f"VIEW {muro_id}", tr((L_pb / 2.0, N["PARAPETO"] + 0.30)),
               0.0032, "A-ANNO", "mc")
    return tr


def escalera_corte(lam, tr, x0: float, y0: float, ancho: float = 2.0,
                   huella: float = 0.28, alzadas: int = 16,
                   valor_x: float = 2.1, capa: str = "A-WALL"):
    """Stair profile in section (flight crossed by the vertical plane)."""
    hueso = 0.10
    fw = (ancho - hueso) / 2.0
    alzada = NIVELES["PISO_PA"] / alzadas
    n1 = alzadas // 2
    if valor_x <= x0 + fw:          # flight 1: rises toward the rear
        for k in range(n1):
            y = y0 + k * huella
            z = (k + 1) * alzada
            lam.ln(tr((y, z)), tr((y + huella, z)), capa)
            lam.ln(tr((y, z)), tr((y, z - alzada)), capa)
        y_desc = y0 + (n1 - 1) * huella
        lam.ln(tr((y_desc, n1 * alzada)), tr((y_desc + 1.0, n1 * alzada)), capa)
    else:                            # flight 2: arrives at the upper-floor level
        y_fin = y0 + (n1 - 1) * huella + 1.0
        for k in range(alzadas - n1):
            y = y_fin - k * huella
            z = n1 * alzada + (k + 1) * alzada
            lam.ln(tr((y, z)), tr((y - huella, z)), capa)
            lam.ln(tr((y, z)), tr((y, z - alzada)), capa)

    return tr


# ---------------------------------------------------------------------------
# reserve tank
# ---------------------------------------------------------------------------
def tanque_apoyo(lam, tr, s0: float, s1: float, z: float, alto: float = 1.15,
                 espesor: float = 0.12, capa: str = "A-WALL",
                 etiqueta: str | None = None, h_txt: float = 0.0019):
    """Reserve tank on a platform, seen in facade or section.

    `s0..s1` is the width in the view and `z` the platform support level
    (the kitchen roof). Draws platform, pedestals, body, lid, vent pipe, and
    downpipe, so the tank exists outside the roof plan.
    """
    # reinforced-concrete platform on the roof
    lam.pl([tr((s0, z)), tr((s1, z)), tr((s1, z + espesor)),
            tr((s0, z + espesor))], capa)
    # support pedestals
    for s in (s0 + 0.06, s1 - 0.20):
        lam.pl([tr((s, z - 0.10)), tr((s + 0.14, z - 0.10)),
                tr((s + 0.14, z)), tr((s, z))], capa)
    # tank body
    a, b = s0 + 0.10, s1 - 0.10
    zb = z + espesor
    lam.pl([tr((a, zb)), tr((b, zb)), tr((b, zb + alto)),
            tr((a, zb + alto))], capa)
    lam.ln(tr((a, zb + alto - 0.10)), tr((b, zb + alto - 0.10)), capa)
    # vent / inspection cap
    c = a + (b - a) / 2.0
    lam.ln(tr((c, zb + alto)), tr((c, zb + alto + 0.16)), capa)
    lam.ln(tr((c - 0.05, zb + alto + 0.16)), tr((c + 0.05, zb + alto + 0.16)),
           capa)
    # cold-water downpipe (riser) to the house
    lam.ln(tr((a + 0.05, zb)), tr((a + 0.05, z - 0.55)), capa)
    if etiqueta:
        lam.tx(etiqueta, tr(((s0 + s1) / 2.0, zb + alto + 0.24)), h_txt,
               "A-ANNO", "mc")
    return (a, b, zb, zb + alto)


def tanque_planta(lam, tr, x: float, y: float, w: float = 1.10,
                  h: float = 1.10, capa: str = "A-WALL",
                  etiqueta: str | None = None, h_txt: float = 0.0020):
    """Reserve tank in plan: platform, body, lid, and downpipe."""
    m = 0.15                                    # platform overhang
    lam.pl([tr((x - m, y - m)), tr((x + w + m, y - m)),
            tr((x + w + m, y + h + m)), tr((x - m, y + h + m))], "A-AREA")
    lam.pl([tr((x, y)), tr((x + w, y)), tr((x + w, y + h)), tr((x, y + h))], capa)
    lam.circ(tr((x + w / 2.0, y + h / 2.0)), 0.016, capa)       # lid
    lam.ln(tr((x + w / 2.0, y + h)), tr((x + w / 2.0, y + h + m)), capa)
    lam.circ(tr((x + 0.16, y + 0.16)), 0.010, "I-AF")           # cold-water downpipe
    if etiqueta:
        lam.tx(etiqueta, tr((x + w / 2.0, y - m - 0.26)), h_txt, "A-ANNO", "mc")
    return (x, y, x + w, y + h)
