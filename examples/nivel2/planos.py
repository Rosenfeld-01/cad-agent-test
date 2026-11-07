#!/usr/bin/env python3
"""
planos.py — juego de láminas de referencia Nivel 2 (A2, cotas en metros).

Ejemplo autocontenido: cada lámina se arma desde los specs `spec_pb.json` y
`spec_pa.json` con las primitivas de `planos_lib.py` (que vive en la raíz del
repo); los símbolos son los bloques verificados de `CAD_Blocks/`.

Uso:
    python3 planos.py            # las 12 láminas en out/
    python3 planos.py L01 L04    # solo algunas
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

# planos_lib.py vive en la raíz del repo: se agrega al path para importarlo.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import planos_lib as L
from planos_lib import Lamina, Tr, planta, escalera, corte, fachada

BASE = Path(__file__).resolve().parent
OUT = BASE / "out"
FECHA = "2026-11-04"
TOTAL = 13

PB = json.loads((BASE / "spec_pb.json").read_text())
PA = json.loads((BASE / "spec_pa.json").read_text())

# ---------------------------------------------------------------------------
# mobiliario (bloque, x, y, rot) con la esquina SO ya rotada
# ---------------------------------------------------------------------------
MOB_PB = [
    # living-comedor
    ("A-PLANTIN", 5.30, 3.30, 0),
    ("A-MESA-6", 3.20, 3.80, 0),
    ("A-SILLA", 3.30, 3.30, 0),
    ("A-SILLA", 4.20, 3.30, 0),
    ("A-SILLA", 3.30, 4.75, 180),
    ("A-SILLA", 4.20, 4.75, 180),
    ("A-SOFA-3", 0.30, 6.20, 90),
    ("A-MESA-RATONA", 1.50, 6.80, 0),
    ("A-SILLON", 2.60, 6.20, 0),
    ("A-MODULO-TV", 2.60, 8.55, 180),
    # toilette amplio
    ("A-INODORO", 5.00, 12.55, 0),
    ("A-LAVATORIO", 6.05, 12.55, 270),
    ("A-DUCHA-090", 5.60, 13.65, 0),
    # despensa
    ("A-PLACARD-210", 0.20, 14.85, 0),
    # lavadero
    ("A-PILETA-LAVAR", 0.25, 17.05, 0),
    ("A-LAVARROPAS", 0.25, 17.75, 0),
    # cocina abierta: mesada al muro este + comedor diario junto a la ventana balcón
    ("A-MESADA-300", 5.95, 14.90, 270),
    ("A-COCINA-4H", 5.95, 15.60, 0),
    ("A-PILETA-LAVAR", 5.95, 16.90, 0),
    ("A-HELADERA", 5.85, 18.50, 0),
    ("A-MESA-RATONA", 3.05, 18.20, 0),
    ("A-SILLA", 2.55, 18.35, 270),
    ("A-SILLA", 4.00, 18.35, 90),
]

MOB_PA = [
    # dormitorio 2 (frente oeste)
    ("A-CAMA-1PL", 0.30, 3.60, 0),
    ("A-PLACARD-210", 2.05, 3.40, 270),
    # bano compartido entre los dos dormitorios
    ("A-DUCHA-090", 2.85, 3.25, 0),
    ("A-LAVATORIO", 3.45, 4.40, 270),
    ("A-INODORO", 2.85, 5.40, 180),
    # dormitorio 3 (frente este)
    ("A-CAMA-1PL", 4.20, 3.40, 0),
    ("A-PLACARD-210", 6.00, 3.40, 270),
    ("A-ESCRITORIO", 5.30, 5.50, 90),
    # oficina privada
    ("A-ESCRITORIO", 3.70, 10.00, 0),
    ("A-SILLA", 4.15, 9.40, 0),
    ("A-PLACARD-210", 3.70, 11.70, 0),
    # toilette de la oficina
    ("A-INODORO", 6.20, 12.55, 180),
    ("A-LAVATORIO", 5.75, 12.55, 270),
    # dormitorio principal (fondo, con balcón)
    ("A-CAMA-2PL", 1.20, 14.60, 0),
    ("A-SILLON", 0.30, 18.60, 0),
    # vestidor
    ("A-PLACARD-210", 3.65, 14.90, 0),
    # bano en suite: inodoro, lavatorio y banera (sin ducha adicional)
    ("A-INODORO", 3.70, 15.75, 0),
    ("A-LAVATORIO", 3.65, 16.70, 270),
    ("A-BANERA-170", 5.60, 15.75, 90),
    # guardado de ropa blanca
    ("A-PLACARD-210", 3.65, 19.10, 0),
]

SIN_VENT = {"pasillo", "guardado"}


def fmt(v: float) -> str:
    return f"{v:.2f}".replace(".", ",")


def cadena(lam, tr: Tr, valores, fijo: float, eje: str, at: float,
           dy: float = 0.0, capa: str = "A-DIM"):
    """Cadena de cotas parciales entre valores consecutivos del modelo."""
    for a, b in zip(valores, valores[1:]):
        txt = fmt(abs(b - a))
        if eje == "X":
            p, q = tr((a, fijo)), tr((b, fijo))
            L.cota_h(lam, p[0], q[0], at, dy, txt, capa=capa)
        else:
            p, q = tr((fijo, a)), tr((fijo, b))
            L.cota_v(lam, p[1], q[1], at, dy, txt, capa=capa)


def ventanas_por_ambiente(spec: dict) -> dict:
    """Superficie de ventanas por ambiente (mismo criterio que check.py)."""
    out = {a["nombre"]: 0.0 for a in spec.get("ambientes", [])}
    for w in spec["muros"]:
        x1, y1 = w["p1"]
        x2, y2 = w["p2"]
        dx, dy = x2 - x1, y2 - y1
        Lm = (dx * dx + dy * dy) ** 0.5
        if Lm < 1e-9:
            continue
        ux, uy = dx / Lm, dy / Lm
        for o in w.get("aberturas", []):
            if o.get("tipo") != "ventana":
                continue
            s = float(o["s"])
            px, py = x1 + ux * s, y1 + uy * s
            cand = [a for a in spec["ambientes"]
                    if a["x"] - 0.30 <= px <= a["x"] + a["w"] + 0.30
                    and a["y"] - 0.30 <= py <= a["y"] + a["h"] + 0.30]
            if not cand:
                continue
            cand.sort(key=lambda a: float(a["w"]) * float(a["h"]))
            out[cand[0]["nombre"]] += float(o["ancho"]) * float(o.get("alto", 1.4))
    return out


def planilla_locales(lam, spec: dict, x: float, y: float, capa: str = "A-ANNO"):
    """Planilla de locales: superficie, ventanas, iluminación y ventilación."""
    vent = ventanas_por_ambiente(spec)
    filas = [["AMBIENTE", "SUP. m2", "VENT. m2", "ILUM.", "VENT."]]
    total = 0.0
    for amb in spec["ambientes"]:
        sup = float(amb["w"]) * float(amb["h"])
        total += sup
        v = vent.get(amb["nombre"], 0.0)
        if amb["tipo"] in SIN_VENT:
            il = "s/req."
            ve = "s/req."
        else:
            il = f"{v / (sup * 0.20) * 100:.0f}%" if sup else "-"
            ve = f"{v / (sup * 0.05) * 100:.0f}%" if sup else "-"
        filas.append([amb["nombre"][:18], fmt(sup), fmt(v), il, ve])
    filas.append(["TOTAL", fmt(total), "", "", ""])
    ancho = [0.078, 0.026, 0.026, 0.022, 0.022]
    alto = 0.0052
    yf = L.tabla(lam, x, y, ancho, filas, alto, 0.0019,
                 alineacion=["ml", "mr", "mr", "mr", "mr"])
    lam.tx("ILUM.: % del 20% exigido - VENT.: % del 5% - s/req.: local sin requisito",
           (x, yf - 0.0034), 0.0017, capa, "ml")
    return yf


def superficie(spec: dict) -> float:
    return sum(float(a["w"]) * float(a["h"]) for a in spec["ambientes"])


def marca_corte(lam, tr: Tr, eje: str, valor: float, a0: float, a1: float,
                letra: str, ext=(0.30, 0.60), capa: str = "A-DIM"):
    """Línea de corte en planta con la letra del corte en ambos extremos."""
    e0, e1 = ext
    if eje == "X":
        p1, p2 = tr((valor, a0 - e0)), tr((valor, a1 + e1))
    else:
        p1, p2 = tr((a0 - e0, valor)), tr((a1 + e1, valor))
    lam.ln(p1, p2, capa)
    for p, d in ((p1, -1.0), (p2, 1.0)):
        if eje == "X":
            lam.ln((p[0] - 0.005, p[1]), (p[0] + 0.005, p[1]), capa)
            c = (p[0], p[1] + d * 0.006)
        else:
            lam.ln((p[0], p[1] - 0.005), (p[0], p[1] + 0.005), capa)
            c = (p[0] + d * 0.006, p[1])
        lam.circ(c, 0.0034, capa)
        lam.tx(letra, c, 0.0024, capa, "mc")


def planilla_aberturas(lam, spec: dict, x: float, y: float,
                       capa: str = "A-ANNO") -> float:
    """Cómputo de aberturas agrupadas por tipo y medida."""
    grupos = {}
    for w in spec["muros"]:
        for o in w.get("aberturas", []):
            tipo = {"ventana": "V", "puerta": "P", "porton": "G",
                    "hueco": "H"}.get(o.get("tipo", "hueco"), "?")
            ancho = float(o["ancho"])
            alto = float(o["alto"]) if o.get("alto") else 2.10
            k = (tipo, round(ancho, 2), round(alto, 2))
            grupos[k] = grupos.get(k, 0) + 1
    filas = [["TIPO", "ANCHO", "ALTO", "CANT"]]
    for k in sorted(grupos, key=lambda k: (-grupos[k], k)):
        tipo, ancho, alto = k
        filas.append([{"V": "Ventana", "P": "Puerta", "G": "Porton",
                       "H": "Hueco"}[tipo], fmt(ancho), fmt(alto),
                      str(grupos[k])])
    return L.tabla(lam, x, y, [0.074, 0.028, 0.028, 0.020], filas, 0.0048,
                   0.0019, alineacion=["ml", "mr", "mr", "mr"])


NOTAS_GENERALES = [
    "1. Cotas y niveles en metros. Escala grafica en cada lamina.",
    "2. Muros: ladrillo hueco 0,18 revocado 0,02 c/u (e=0,20);",
    "   interiores 0,15 y 0,10 terminados.",
    "3. Losas: platea de H21 e=0,15; entrepiso y azotea H21 e=0,15.",
    "4. Altura libre PB 2,80 m; PA 2,70 m; azotea +5,75 y",
    "   parapeto +6,55 con cubierta a un agua (1,8% al fondo).",
    "5. Verificar en obra cotas y niveles antes de iniciar tareas.",
    "6. Cabida 1/8 de la superficie del terreno libre de edificacion.",
]

LEYES = [
    ("cuadrado", "Ambiente / superficie"),
    ("linea", "Muro cortado"),
    ("linea-corta", "Abertura / pasaje"),
    ("circulo", "Boca de luz"),
    ("bloque:S-LLAVE-PASO", "Llave de paso"),
]
# ---------------------------------------------------------------------------
# L01 / L02 — plantas de arquitectura
# ---------------------------------------------------------------------------
def _hoja_planta(numero: int, titulo: str, codigo: str, spec: dict, mob,
                 nivel_txt: str, ancho_total: str, largo_total: str,
                 xs, ys, cortes, escala: int = 50,
                 nota_local=(), ext_a=(0.05, 0.60),
                 escala_real: bool = True) -> Lamina:
    lam = Lamina(numero, TOTAL, titulo, escala, codigo=codigo, fecha=FECHA,
                 escala_real=escala_real)
    tr = planta(lam, spec, origen=(0.078, 0.040), ancla=(0.1, 3.1), mob=mob)

    # cotas generales y parciales
    cadena(lam, tr, xs, 3.1, "X", 0.026)
    p0, p1 = tr((xs[0], 3.1)), tr((xs[-1], 3.1))
    L.cota_h(lam, p0[0], p1[0], 0.014, 0.0, ancho_total)
    cadena(lam, tr, ys, 0.1, "Y", 0.068)
    q0, q1 = tr((0.1, ys[0])), tr((0.1, ys[-1]))
    L.cota_v(lam, q0[1], q1[1], 0.052, 0.0, largo_total)

    for eje, valor, a0, a1, letra, _txt in cortes:
        marca_corte(lam, tr, eje, valor, a0, a1, letra,
                    ext=ext_a if eje == "X" else (0.75, 0.75))

    # columna A: planillas y notas particulares
    lam.tx(titulo, (0.215, 0.401), 0.0046, "A-ANNO", "ml")
    lam.tx(f"{nivel_txt} - SUPERFICIE CUBIERTA {fmt(superficie(spec))} m2",
           (0.215, 0.393), 0.0020, "A-ANNO", "ml")
    yf = planilla_locales(lam, spec, 0.215, 0.384)
    L.nota(lam, 0.215, yf - 0.012, [
        "La planilla verifica el art. 3.8.1.1.3 del CE CABA:",
        "iluminacion 20% y ventilacion 5% de la superficie.",
    ], h=0.0017, inter=0.0040, titulo=None, ancho=0.155)
    y = planilla_aberturas(lam, spec, 0.215, yf - 0.030)
    lam.tx("ABERTURAS - medidas en metros", (0.215, yf - 0.023), 0.0019,
           "A-ANNO", "ml")
    if nota_local:
        y = L.nota(lam, 0.215, y - 0.014, list(nota_local), h=0.0018,
                   inter=0.0044, titulo="Escalera", ancho=0.155)

    # columna B: notas generales, referencias y cortes
    L.nota(lam, 0.400, 0.384, NOTAS_GENERALES, h=0.0019, inter=0.0048,
           titulo="Notas generales", ancho=0.178)
    L.leyenda(lam, 0.400, 0.335, LEYES, h=0.0019, paso=0.0048,
              titulo="Referencias")
    L.nota(lam, 0.400, 0.300, [c[5] for c in cortes], h=0.0019, inter=0.0048,
           titulo="Cortes", ancho=0.178)
    L.norte(lam, (0.556, 0.238), 0.0125)
    L.escala_grafica(lam, (0.400, 0.232), escala)
    return lam


def l01() -> Lamina:
    lam = _hoja_planta(
        1, "PLANTA BAJA", "L01", PB, MOB_PB,
        "NIVEL +0,00 - ALTURA LIBRE 2,80 m", "6,60", "16,80",
        [0.1, 1.525, 2.4, 4.425, 6.7],
        [3.1, 9.275, 12.425, 14.725, 16.9, 19.9],
        [("X", 2.60, 3.1, 19.9, "A", "CORTE A-A longitudinal (L04)"),
         ("Y", 5.30, 0.1, 6.7, "B", "CORTE B-B transversal (L05)"),
         ("Y", 13.00, 0.1, 6.7, "C", "CORTE C-C transversal (L05)")],
        nota_local=["Escalera abierta: 16 alzadas de 0,18 m, huella 0,28 m",
                    "y 1,95 m de ancho; H°A° empotrada en el muro oeste,",
                    "baranda de 1,00 m sobre el borde libre este.",
                    "Aberturas de fluidez: 5,10 m living-hall y 1,88 m",
                    "pasillo-cocina, sin puertas."])
    tr = Tr.anclado(0.078, 0.040, 50, ancla=(0.1, 3.1))
    escalera(lam, tr, 1.6, 9.35, ancho=1.95, nivel="PB")
    # escalera abierta: baranda sobre el borde libre (este y frente), 2 cm
    # fuera del canto de la losa para no duplicar el trazo
    L.baranda(lam, tr, [(3.57, 9.35), (3.57, 12.15), (1.58, 12.15)])
    lam.tx("ESCALERA ABIERTA", tr((2.55, 11.75)), 0.0016, "A-ANNO", "mc")
    return lam


def l02() -> Lamina:
    lam = _hoja_planta(
        2, "PLANTA ALTA", "L02", PA, MOB_PA,
        "NIVEL +2,90 - ALTURA LIBRE 2,70 m", "6,60", "16,80",
        [0.1, 1.45, 3.6, 6.7],
        [3.1, 7.0, 9.275, 12.425, 13.6, 15.65, 17.85, 19.9],
        [("X", 2.60, 3.1, 19.9, "A", "CORTE A-A longitudinal (L04)"),
         ("Y", 5.30, 0.1, 6.7, "B", "CORTE B-B transversal (L05)"),
         ("Y", 13.00, 0.1, 6.7, "C", "CORTE C-C transversal (L05)")],
        nota_local=["Llega a +2,90 en el hall; el tramo 1 queda como vacio",
                    "sobre PB con baranda perimetral de 1,00 m.",
                    "El balcón del dormitorio principal (1,00 x 3,28)",
                    "vuela sobre el jardín de fondo."],
        ext_a=(0.05, 0.90))
    tr = Tr.anclado(0.078, 0.040, 50, ancla=(0.1, 3.1))
    escalera(lam, tr, 1.6, 9.35, ancho=1.95, nivel="PA")
    # barandas del vacio de la escalera abierta (oeste, este y sur), 2 cm
    # fuera del canto para no duplicar el trazo de la losa
    L.baranda(lam, tr, [(1.58, 9.35), (1.58, 12.35)])
    L.baranda(lam, tr, [(3.57, 9.35), (3.57, 12.35)])
    L.baranda(lam, tr, [(1.58, 12.37), (3.57, 12.37)])
    # balcón del dormitorio principal al fondo (vuela 1,00 m sobre el jardin)
    lam.pl([tr((0.2, 19.9)), tr((3.475, 19.9)), tr((3.475, 20.9)),
            tr((0.2, 20.9))], "A-AREA")
    L.baranda(lam, tr, [(0.24, 20.86), (3.435, 20.86), (3.435, 19.94)])
    L.baranda(lam, tr, [(0.24, 19.94), (0.24, 20.86)])
    lam.tx("BALCON 1,00 x 3,28", tr((1.84, 20.42)), 0.0016, "A-ANNO", "mc")
    lam.tx("AL JARDIN DE FONDO", tr((1.84, 20.12)), 0.0013, "A-ANNO", "mc")
    # Escala de gato a la azotea: boca de 0,70 x 0,70 sobre el hall
    # (x 0,4..1,1 - y 8,0..8,7), alineada con la pasarela de servicio.
    lam.pl([tr((0.4, 8.0)), tr((1.1, 8.0)), tr((1.1, 8.7)),
            tr((0.4, 8.7))], "A-DOOR")
    for xx in (0.5, 1.0):
        lam.ln(tr((xx, 8.05)), tr((xx, 8.65)), "A-ESC")
    for yy in (8.2, 8.35, 8.5):
        lam.ln(tr((0.5, yy)), tr((1.0, yy)), "A-ESC")
    lam.tx("ESCALA DE GATO", tr((0.75, 7.62)), 0.0014, "A-ANNO", "mc")
    return lam
# ---------------------------------------------------------------------------
# L03 — planta de techo
# ---------------------------------------------------------------------------
def cabecera(lam, titulo: str, subtitulo: str, x: float = 0.215,
             y: float = 0.401):
    lam.tx(titulo, (x, y), 0.0046, "A-ANNO", "ml")
    lam.tx(subtitulo, (x, y - 0.008), 0.0020, "A-ANNO", "ml")


def l03() -> Lamina:
    lam = Lamina(3, TOTAL, "PLANTA DE TECHO", 50, codigo="L03", fecha=FECHA,
                 escala_real=True)
    tr = Tr.anclado(0.078, 0.040, 50, ancla=(0.1, 3.1))

    # Azotea única sobre la huella completa: los muros de PA son el parapeto
    # perimetral de +6,55, constante en las cuatro fachadas.  El parapeto es
    # ciego: se pasan los muros SIN aberturas (las ventanas de PA no se ven en
    # planta de techo).
    paramentos = {"muros": [dict(w, aberturas=[]) for w in PA["muros"]
                            if w.get("tipo") == "exterior"],
                  "ambientes": []}
    planta(lam, paramentos, origen=(0.078, 0.040), ancla=(0.1, 3.1),
           con_ambientes=False, mob=[])

    # Cubierta a un agua escondida: 1,8% de +6,15 (frente) a +5,85 (fondo).
    for x, y in ((4.9, 6.2), (4.9, 11.0), (4.9, 15.6), (2.0, 8.5),
                 (2.0, 13.0)):
        lam.sym("X-PENDIENTE", tr, x, y, 0)

    # Canaleta y desagües al fondo (punto más bajo de la pendiente).
    lam.ln(tr((0.3, 19.55)), tr((6.5, 19.55)), "I-PL")
    for x in (0.65, 6.15):
        lam.sym("X-REGISTRO", tr, x, 19.55, 0, "I-PL")
        lam.circ(tr((x, 19.78)), 0.0020, "I-PL")
        L.cano(lam, tr, [(x, 19.55), (x, 19.78)], "I-PL", "DASHDOT")
    lam.tx("CANALETA +5,85", tr((3.4, 19.25)), 0.0015, "A-ANNO", "mc")

    # Módulo del tanque: 2,40 x 2,00 (4,80 m2) sobre el fondo oeste, con
    # puerta de 0,70 m en el lado sur (acceso desde la pasarela de servicio).
    lam.pl([tr((1.95, 17.4)), tr((2.7, 17.4)), tr((2.7, 19.4)),
            tr((0.3, 19.4)), tr((0.3, 17.4)), tr((1.25, 17.4))], "A-WALL",
           close=False)
    lam.ln(tr((1.25, 17.4)), tr((1.25, 18.1)), "A-DOOR")
    lam.arc(tr((1.25, 17.4)), 0.014, 0, 90, "A-DOOR")
    lam.tx("MODULO TANQUE +7,30", tr((1.5, 16.95)), 0.0015, "A-ANNO", "mc")
    L.tanque_planta(lam, tr, 0.95, 17.85, 1.10, 1.10, capa="A-AREA")
    lam.tx("TANQUE 1.000 l", tr((1.50, 18.55)), 0.0014, "A-ANNO", "mc")

    # Pasarela de servicio de 0,90 m por el borde oeste, de la boca de acceso
    # a la puerta del módulo, con baranda de 1,00 m sobre el borde libre.
    lam.pl([tr((0.3, 8.7)), tr((1.2, 8.7)), tr((1.2, 17.4)),
            tr((0.3, 17.4))], "A-AREA")
    L.baranda(lam, tr, [(1.2, 8.7), (1.2, 17.4)])
    lam.tx("PASARELA DE SERVICIO 0,90", tr((0.75, 12.6)), 0.0014,
           "A-ANNO", "mc", 90)

    # Boca de acceso a la azotea (0,70 x 0,70) sobre el hall de PA.
    lam.pl([tr((0.4, 8.0)), tr((1.1, 8.0)), tr((1.1, 8.7)),
            tr((0.4, 8.7))], "A-WALL")
    lam.ln(tr((0.4, 8.0)), tr((1.1, 8.7)), "A-WALL")
    lam.ln(tr((0.4, 8.7)), tr((1.1, 8.0)), "A-WALL")
    lam.tx("BOCA DE ACCESO 0,70 x 0,70", tr((0.75, 7.55)), 0.0015,
           "A-ANNO", "mc")

    # Ventilaciones cloacales sobre la azotea.
    for x, y in ((3.4, 6.0), (5.9, 13.0), (5.0, 16.7)):
        lam.sym("S-VENTILACION", tr, x, y, 0, "I-CL")

    # Bajada de AF desde el módulo hasta el lavadero (muro oeste).
    L.cano(lam, tr, [(1.00, 18.20), (0.10, 18.20), (0.10, 17.0)], "I-AF")

    lam.tx("AZOTEA INTRANSITABLE +5,75", tr((3.30, 9.40)), 0.0024, "A-ANNO", "mc")
    lam.tx("CUBIERTA 1,8% HACIA EL FONDO", tr((3.30, 8.95)), 0.0019,
           "A-ANNO", "mc")
    lam.tx("PARAPETO +6,55", tr((3.30, 4.20)), 0.0020, "A-ANNO", "mc")
    lam.tx("+6,15", tr((3.30, 3.55)), 0.0016, "A-ANNO", "mc")
    lam.tx("+5,85", tr((3.30, 18.60)), 0.0016, "A-ANNO", "mc")

    # Cotas generales de la cubierta.
    L.cota_h(lam, 0.078, 0.210, 0.027, 0.0, "6,60", 0.0019)
    L.cota_v(lam, 0.040, 0.376, 0.068, 0.0, "16,80", 0.0019)
    L.cota_h(lam, tr((0.3, 17.4))[0], tr((2.7, 17.4))[0], 0.320, 0.0,
             "2,40", 0.0016)
    L.cota_v(lam, tr((0, 17.4))[1], tr((0, 19.4))[1], 0.072, 0.0,
             "2,00", 0.0016)

    # referencias de corte (las mismas de L01/L02)
    marca_corte(lam, tr, "X", 2.60, 3.1, 19.9, "A", ext=(0.05, 0.90))
    marca_corte(lam, tr, "Y", 5.30, 0.1, 6.7, "B", ext=(0.75, 0.75))

    # rótulos de la lámina
    cabecera(lam, "PLANTA DE TECHO",
             "CUBIERTA A UN AGUA +6,15/+5,85 - PARAPETO +6,55", 0.215)
    L.nota(lam, 0.215, 0.374, [
        "1. Cubierta a un agua escondida: carpeta de",
        "   pendiente 1,8% de +6,15 (frente) a +5,85",
        "   (fondo), membrana y proteccion pesada.",
        "2. Parapeto de +6,55 constante en las cuatro",
        "   fachadas: la pendiente no se ve desde la calle.",
        "3. Canaleta al fondo con 2 bocas de desague de",
        "   0,10 m y 2 bajadas por los ejes de los muros.",
        "4. Ventilaciones cloacales de 0,10 m sobre azotea.",
        "5. Modulo de tanque de 2,40 x 2,00 con paredes",
        "   hasta +7,30 sobre el fondo oeste: aloja el",
        "   tanque de 1.000 l sobre plataforma de H21,",
        "   con puerta de 0,70 m y bajada de AF al lavadero.",
        "6. Acceso por boca de 0,70 x 0,70 sobre el hall",
        "   de PA, con escala de gato; pasarela de servicio",
        "   de 0,90 m y baranda de 1,00 m hasta la puerta",
    ], h=0.0018, inter=0.0045, titulo="Notas de cubierta", ancho=0.178)
    filas = [["PANO", "SUP. m2", "PEND.", "DESAGUES"],
             ["Azotea unica", "110,88", "1,8%", "2"],
             ["Modulo tanque", "4,80", "-", "-"],
             ["TOTAL CUBIERTA", "110,88", "", "2"]]
    L.tabla(lam, 0.215, 0.248, [0.070, 0.030, 0.026, 0.032], filas, 0.0052,
            0.0019, alineacion=["ml", "mr", "mr", "mr"])
    L.leyenda(lam, 0.400, 0.374, [
        ("bloque:X-PENDIENTE", "Pendiente de cubierta (1,8%)"),
        ("bloque:S-VENTILACION", "Ventilacion cloacal"),
        ("bloque:X-REGISTRO", "Boca de desague en canaleta"),
        ("linea", "Parapeto +6,55 / muro"),
        ("linea:I-PL", "Canaleta al fondo"),
        ("linea:I-PL:DASHDOT", "Bajada pluvial"),
        ("linea:I-AF", "Bajada de agua fria del tanque"),
        ("linea-corta", "Modulo del tanque (+7,30)"),
    ], h=0.0018, paso=0.0048, titulo="Referencias")
    detalle_cubierta(lam, 0.232, 0.052)
    L.norte(lam, (0.556, 0.262), 0.0125)
    L.escala_grafica(lam, (0.215, 0.140), 50)
    return lam


def detalle_cubierta(lam, x0: float, y0: float, escala: int = 20):
    """Encuentro cubierta / parapeto / módulo de tanque (1:20).

    Se dibuja un corte por el fondo: losa, carpeta con pendiente, membrana,
    canaleta, parapeto de +6,55 y pared del módulo hasta +7,30 con el tanque.
    """
    e = 1.0 / escala
    tr = Tr.anclado(x0, y0, escala, ancla=(18.6, 5.45))
    lam.tx("DETALLE CUBIERTA Y MODULO - 1:20", (x0, y0 + 2.10 * e), 0.0019,
           "A-ANNO", "ml")
    # losa + carpeta de pendiente (paquete 5,60 a 5,85) y membrana
    lam.pl([tr((18.6, 5.60)), tr((20.0, 5.60)), tr((20.0, 5.85)),
            tr((18.6, 5.83))], "A-HATCH")
    lam.ln(tr((18.6, 5.83)), tr((20.0, 5.85)), "A-WALL")     # membrana
    # canaleta al fondo (rebaje de 0,10) y bajada pluvial
    lam.pl([tr((19.50, 5.85)), tr((19.50, 5.70)), tr((19.72, 5.70)),
            tr((19.72, 5.85))], "A-WALL")
    lam.ln(tr((19.61, 5.70)), tr((19.61, 5.30)), "I-PL")
    # parapeto +6,55 con babeta
    lam.pl([tr((19.80, 5.85)), tr((20.00, 5.85)), tr((20.00, 6.55)),
            tr((19.80, 6.55))], "A-WALL")
    lam.ln(tr((19.76, 6.55)), tr((20.02, 6.55)), "A-WALL")
    # pared y losa del módulo del tanque hasta +7,30
    lam.pl([tr((19.28, 5.85)), tr((19.48, 5.85)), tr((19.48, 7.30)),
            tr((19.28, 7.30))], "A-WALL")
    lam.ln(tr((18.60, 7.30)), tr((19.48, 7.30)), "A-WALL")
    L.tanque_apoyo(lam, tr, 18.70, 19.20, 5.85, alto=1.15, espesor=0.12,
                   capa="A-WALL")
    lam.tx("TANQUE 1.000 l", tr((18.95, 6.75)), 0.0015, "A-ANNO", "mc")
    lam.tx("PARAPETO +6,55", tr((19.90, 6.25)), 0.0014, "A-ANNO", "mr")
    lam.tx("MEMBRANA +5,85", tr((18.75, 5.92)), 0.0013, "A-ANNO", "ml")
    lam.tx("LOSA +5,75", tr((18.75, 5.66)), 0.0013, "A-ANNO", "ml")
    lam.tx("CANALETA", tr((19.35, 5.55)), 0.0013, "A-ANNO", "mc")
    L.cota_v(lam, tr((0, 5.60))[1], tr((0, 7.30))[1], x0 - 0.010, 0.0,
             "1,70", 0.0016)
    return tr


# ---------------------------------------------------------------------------
# L04 / L05 — cortes
# ---------------------------------------------------------------------------
NOTAS_CORTE = [
    "1. Altura libre PB 2,80 m y PA 2,70 m (art. 4.1.1.1 CE CABA).",
    "2. Losa de entrepiso y de azotea de H21 e=0,15 m,",
    "   contrapiso de H8 e=0,06 m y piso terminado.",
    "3. Platea de fundacion H21 e=0,15 m sobre terreno",
    "   compactado; capa aisladora horizontal y vertical.",
    "4. Muros exteriores de 0,20 m (HLA 20x20x40), junta 0,015,",
    "   revoque exterior e=0,02 e interior e=0,015.",
    "5. Escalera: 16 alzadas de 0,18 m, huellas de 0,28 m,",
    "   ancho 1,95 m y descanso de 1,00 m.",
    "6. Carpeta de pendiente 1% sobre azotea y membrana.",
    "7. Dinteles y encadenados verticales indicados en L06.",
]


def planilla_niveles(lam, x: float, y: float) -> float:
    filas = [["NIVEL", "COTA", "LOSA", "LIBRE"],
             [" Terreno natural", "-0,30", "", ""],
             [" Platea de fundacion", "-0,15", "0,15", ""],
             [" Piso terminado PB", "+0,00", "", "2,80"],
             [" Piso terminado PA", "+2,90", "0,15", "2,70"],
             [" Azotea", "+5,75", "0,15", ""],
             [" Parapeto", "+6,55", "", ""]]
    return L.tabla(lam, x, y, [0.062, 0.026, 0.020, 0.022], filas, 0.0054,
                   0.0019, alineacion=["ml", "mr", "mr", "mr"])


def l04() -> Lamina:
    lam = Lamina(4, TOTAL, "CORTE A-A", 50, codigo="L04", fecha=FECHA)
    tr = corte(lam, PB, PA, eje="X", valor=2.60, origen=(0.078, 0.250),
               a0=2.70, a1=21.20, con_escalera=True, ancla=(2.70, 0.0))
    lam.tx("CORTE A-A", (0.078, 0.394), 0.0032, "A-ANNO", "ml")
    lam.tx("Corte longitudinal por x = 2,60 m - mira hacia el oeste - 1:50",
           (0.078, 0.388), 0.0019, "A-ANNO", "ml")
    # cubierta a un agua escondida: 1,8% de +6,15 (frente) a +5,85 (fondo)
    lam.ln(tr((3.1, 6.15)), tr((19.9, 5.85)), "A-WALL")
    lam.tx("CUBIERTA 1,8%", tr((8.4, 6.10)), 0.0014, "A-ANNO", "mc")
    # módulo del tanque en el fondo (x = 2,60 corta el módulo)
    lam.pl([tr((17.4, 5.85)), tr((19.4, 5.85)), tr((19.4, 7.30)),
            tr((17.4, 7.30))], "A-WALL")
    lam.pl([tr((17.75, 5.97)), tr((18.85, 5.97)), tr((18.85, 6.90)),
            tr((17.75, 6.90))], "A-AREA")
    lam.tx("MODULO TANQUE +7,30", tr((18.35, 7.45)), 0.0015, "A-ANNO", "mc")
    lam.tx("TANQUE 1.000 l", tr((18.30, 6.35)), 0.0013, "A-ANNO", "mc")
    # balcón del dormitorio principal: vuela 1,00 m sobre el jardin de fondo
    lam.pl([tr((19.9, 2.72)), tr((20.9, 2.72)), tr((20.9, 2.90)),
            tr((19.9, 2.90))], "A-WALL")
    L.baranda(lam, tr, [(20.88, 2.90), (20.88, 3.90)])
    lam.tx("BALCON +2,90", tr((20.40, 4.15)), 0.0014, "A-ANNO", "mc")
    yf = planilla_niveles(lam, 0.078, 0.232)
    L.nota(lam, 0.078, yf - 0.018, NOTAS_CORTE[:4], h=0.0018, inter=0.0044,
           titulo="Notas de corte", ancho=0.128)
    L.nota(lam, 0.212, yf - 0.018, NOTAS_CORTE[4:], h=0.0018, inter=0.0044,
           titulo=None, ancho=0.128)
    L.escala_grafica(lam, (0.212, yf - 0.062), 50)
    L.nota(lam, 0.470, 0.232, [
        "El corte A-A pasa por el living, la",
        "escalera abierta, el pasillo, la cocina",
        "y el modulo del tanque.",
        "",
        "La planta alta cubre la huella completa:",
        "no hay techo de cocina independiente.",
        "",
        "Cubierta a un agua escondida (1,8% al",
        "fondo) detras del parapeto de +6,55.",
        "",
        "El balcon del dormitorio principal vuela",
        "1,00 m sobre el jardin de fondo.",
    ], h=0.0019, inter=0.0046, titulo="Descripcion", ancho=0.110)
    L.leyenda(lam, 0.470, 0.150, [
        ("linea", "Muro cortado / losa"),
        ("linea-corta", "Cielo raso PB"),
        ("bloque:X-CORTE", "Nivel y cota"),
    ], h=0.0019, paso=0.0050, titulo="Referencias")
    return lam


def l05() -> Lamina:
    lam = Lamina(5, TOTAL, "CORTES B-B Y C-C", 50, codigo="L05", fecha=FECHA)
    corte(lam, PB, PA, eje="Y", valor=5.30, origen=(0.078, 0.250),
          ancla=(-0.30, 0.0))
    lam.tx("CORTE B-B", (0.078, 0.394), 0.0032, "A-ANNO", "ml")
    lam.tx("Corte transversal por y = 5,30 m - 1:50", (0.078, 0.388),
           0.0019, "A-ANNO", "ml")
    corte(lam, PB, PA, eje="Y", valor=13.00, origen=(0.298, 0.250),
          ancla=(-0.30, 0.0))
    lam.tx("CORTE C-C", (0.298, 0.394), 0.0032, "A-ANNO", "ml")
    lam.tx("Corte transversal por y = 13,00 m - 1:50", (0.298, 0.388),
           0.0019, "A-ANNO", "ml")
    yf = planilla_niveles(lam, 0.078, 0.232)
    L.nota(lam, 0.078, yf - 0.018, NOTAS_CORTE[:4], h=0.0018, inter=0.0044,
           titulo="Notas de corte", ancho=0.128)
    L.nota(lam, 0.212, yf - 0.018, NOTAS_CORTE[4:], h=0.0018, inter=0.0044,
           titulo=None, ancho=0.128)
    L.escala_grafica(lam, (0.078, yf - 0.062), 50)
    L.nota(lam, 0.400, 0.230, [
        "B-B corta el living comedor en PB y la suite",
        "con su bano en PA: el ancho util es de 6,20 m",
        "entre paramentos interiores.",
        "",
        "C-C corta el sector de guardado y escritorio",
        "en PB y el pasillo con el bano de PA.",
        "Ambos cortes verifican la continuidad de la",
        "losa de entrepiso y de los encadenados.",
    ], h=0.0019, inter=0.0046, titulo="Descripcion", ancho=0.178)
    return lam

# ---------------------------------------------------------------------------
# L06 a L09 — vistas
# ---------------------------------------------------------------------------
ANTEPECHO = L.ANTEPECHO


def alzado_abertura(o: dict):
    """(alto, antepecho) de una abertura, con los mismos defaults de elevacion."""
    tipo = o.get("tipo", "hueco")
    sill = 0.0 if tipo in ("puerta", "porton") else float(
        o.get("antepecho", ANTEPECHO))
    alto = float(o.get("alto", 2.10 if sill == 0.0 else 1.40))
    return alto, sill


def planilla_aberturas_muro(lam, x: float, y: float, muros, niveles=None
                            ) -> float:
    """Planilla de aberturas de uno o varios muros (PB y PA), con bloque."""
    filas = [["CODIGO", "BLOQUE", "TIPO", "NIV.", "ANCHO", "ALTO", "ANTEP."]]
    niveles = niveles or [""] * len(muros)
    for muro, niv in zip(muros, niveles):
        for o in sorted(muro.get("aberturas", []),
                        key=lambda o: float(o["s"])):
            if o.get("tipo") == "hueco":
                continue
            alto, sill = alzado_abertura(o)
            bloque = (L._modena_f(float(o["ancho"]), alto)
                      if o.get("tipo") == "ventana" else "-")
            filas.append([o.get("id", ""), bloque, o.get("tipo", "")[:7], niv,
                          fmt(float(o["ancho"])), fmt(alto),
                          fmt(sill) if sill else "-"])
    return L.tabla(lam, x, y,
                   [0.028, 0.054, 0.015, 0.009, 0.015, 0.013, 0.015],
                   filas, 0.0050, 0.0018,
                   alineacion=["ml", "ml", "ml", "mc", "mr", "mr", "mr"])


def cotas_vista(lam, tr: Tr, largo: float, y_cota: float = 0.246):
    p0, p1 = tr((0.0, 0.0)), tr((largo, 0.0))
    xa, xb = min(p0[0], p1[0]), max(p0[0], p1[0])
    L.cota_h(lam, xa, xb, y_cota, 0.0, fmt(largo))
    q0, q1 = tr((0.0, 0.0)), tr((0.0, L.NIVELES["PARAPETO"]))
    L.cota_v(lam, q0[1], q1[1], xa - 0.018, 0.0, "6,55")


NOTAS_VISTA = [
    "1. Muros exteriores de 0,20 m revocados y pintados;",
    "   junta de dilatacion cada 6,00 m.",
    "2. Zocalo de cemento alisado de 0,20 m.",
    "3. Carpinteria de aluminio linea A30 con DVH 4-9-4.",
    "4. Antepechos de mamposteria revocados; alfeizares",
    "   de marmol de 0,03 m con goteron.",
    "5. Parapeto de azotea de 0,80 m con remate de chapa.",
]

TEXTURAS = [
    "Muros: revoque fratasado + latex acrilico",
    "  blanco hueso (N-10) en PB y gris claro (N7)",
    "  en PA segun plano de color.",
    "Carpinteria: aluminio blanco; vidrio DVH.",
    "Rejas y barandas: hierro pintado negro mate.",
    "Antepecho de frente: piedra reconstituida.",
]


def l06() -> Lamina:
    lam = Lamina(6, TOTAL, "FACHADA PRINCIPAL", 25, codigo="L06", fecha=FECHA)
    muro = L.buscar_muro(PB, "M-E-FRENTE")
    tr = fachada(lam, PB, PA, "M-E-FRENTE", origen=(0.085, 0.100),
                 con_texto=False)
    cotas_vista(lam, tr, 6.60, 0.064)
    niveles_vista(lam, tr, 6.60)
    lam.tx("FACHADA PRINCIPAL", (0.085, 0.394), 0.0032, "A-ANNO", "ml")
    lam.tx("Vista del frente sobre la linea municipal - 1:25", (0.085, 0.388),
           0.0019, "A-ANNO", "ml")
    yf = planilla_aberturas_muro(lam, 0.380, 0.380,
                                 [muro, L.buscar_muro(PA, "M-E-FRENTE")],
                                 ["PB", "PA"])
    L.nota(lam, 0.380, yf - 0.014, NOTAS_VISTA, h=0.0018, inter=0.0044,
           titulo="Notas de fachada", ancho=0.150)
    L.nota(lam, 0.380, yf - 0.062, TEXTURAS, h=0.0018, inter=0.0044,
           titulo="Texturas y colores", ancho=0.170)
    L.nota(lam, 0.380, yf - 0.096, [
        "Niveles: +0,00 vereda / +2,90 piso PA /",
        "+5,75 azotea / +6,55 parapeto.",
        "La puerta de entrada (P-ENTRADA 0,90) se ubica",
        "a 0,90 m del eje oeste y la ventana del living",
        "(V-LIV-F 2,40 x 1,60) sobre el pano este.",
    ], h=0.0018, inter=0.0044, titulo="Descripcion", ancho=0.170)
    L.escala_grafica(lam, (0.380, 0.150), 25, tramos=(0, 1, 2))
    return lam


def l07() -> Lamina:
    lam = Lamina(7, TOTAL, "CONTRAFRENTE", 25, codigo="L07", fecha=FECHA)
    muro = L.buscar_muro(PB, "M-E-FONDO")
    # PA cubre la huella completa: la vista muestra las dos plantas completas,
    # el balcón del dormitorio principal, la ventana balcón de la cocina y el
    # módulo del tanque asomando sobre el parapeto.
    tr = fachada(lam, PB, PA, "M-E-FONDO", origen=(0.085, 0.100), espejo=True,
                 con_texto=False)
    # balcón +2,90 con baranda: x 0,20..3,475 del proyecto, espejado en 6,60
    L.baranda(lam, tr, [(3.12, 2.90), (3.12, 3.90)])
    lam.pl([tr((3.12, 2.90)), tr((6.40, 2.90)), tr((6.40, 2.72)),
            tr((3.12, 2.72))], "A-WALL")
    lam.tx("BALCON +2,90", tr((4.76, 4.15)), 0.0015, "A-ANNO", "mc")
    # módulo del tanque: x 0,30..2,70 -> espejado 3,90..6,30, de +5,85 a +7,30
    lam.pl([tr((3.90, 5.85)), tr((6.30, 5.85)), tr((6.30, 7.30)),
            tr((3.90, 7.30))], "A-WALL")
    lam.tx("MODULO TANQUE +7,30", tr((5.10, 7.45)), 0.0015, "A-ANNO", "mc")
    cotas_vista(lam, tr, 6.60, 0.064)
    niveles_vista(lam, tr, 6.60)
    lam.tx("CONTRAFRENTE", (0.085, 0.394), 0.0032, "A-ANNO", "ml")
    lam.tx("Vista desde el fondo del lote - muro M-E-FONDO - 1:25",
           (0.085, 0.388), 0.0019, "A-ANNO", "ml")
    yf = planilla_aberturas_muro(lam, 0.380, 0.380,
                                 [muro, L.buscar_muro(PA, "M-E-FONDO")],
                                 ["PB", "PA"])
    L.nota(lam, 0.380, yf - 0.014, [
        "1. El contrafrente cierra el lavadero y la",
        "   cocina en PB y el dormitorio principal en PA.",
        "2. La ventana balcón de 2,40 x 2,10 (VB-COC)",
        "   ventila e ilumina la cocina hacia el jardin",
        "   de fondo; lleva baranda de 1,00 m.",
        "3. Sobre ella, el balcón del dormitorio",
        "   principal (1,00 x 3,28) con baranda metálica.",
        "4. El módulo del tanque asoma sobre el parapeto",
        "   de +6,55 con paredes hasta +7,30.",
        "5. Acceso: escala de gato y boca de 0,70 (hall PA).",
    ], h=0.0018, inter=0.0044, titulo="Notas de fachada", ancho=0.150)
    L.nota(lam, 0.380, yf - 0.062, TEXTURAS, h=0.0018, inter=0.0044,
           titulo="Texturas y colores", ancho=0.170)
    L.nota(lam, 0.380, yf - 0.096, [
        "Vista espejada respecto del plano: el oeste de",
        "la planta aparece a la derecha.",
        "Niveles: +0,00 terreno / +2,90 piso PA /",
        "+5,75 azotea / +6,55 parapeto / +7,30 módulo.",
    ], h=0.0018, inter=0.0044, titulo="Descripcion", ancho=0.170)
    L.escala_grafica(lam, (0.380, 0.150), 25, tramos=(0, 1, 2))
    return lam


def niveles_vista(lam, tr: Tr, largo: float, off: float = 0.30):
    """Marcas de nivel a la derecha de una vista larga."""
    for z, txt in ((0.0, "+0,00"), (L.NIVELES["PISO_PA"], "+2,90"),
                   (L.NIVELES["AZOTEA"], "+5,75"),
                   (L.NIVELES["PARAPETO"], "+6,55")):
        L.nivel(lam, tr((largo + off, z)), txt, lado=1)


def _hoja_lateral(numero: int, codigo: str, titulo: str, muro_id: str,
                  espejo: bool, subtitulo: str, notas,
                  modulo=None, balcon=None) -> Lamina:
    lam = Lamina(numero, TOTAL, titulo, 50, codigo=codigo, fecha=FECHA)
    muro = L.buscar_muro(PB, muro_id)
    largo = L.longitud(muro)
    tr = fachada(lam, PB, PA, muro_id, origen=(0.078, 0.215), espejo=espejo,
                 con_texto=False)
    if modulo:                   # (s0, s1) ya espejados por el llamador
        lam.pl([tr((modulo[0], 5.85)), tr((modulo[1], 5.85)),
                tr((modulo[1], 7.30)), tr((modulo[0], 7.30))], "A-WALL")
        lam.tx("MODULO TANQUE +7,30",
               tr(((modulo[0] + modulo[1]) / 2.0, 7.45)), 0.0014,
               "A-ANNO", "mc")
    if balcon:                   # balcón visto de perfil: losa + baranda
        b0, b1 = min(balcon), max(balcon)
        lam.pl([tr((b0, 2.72)), tr((b1, 2.72)), tr((b1, 2.90)),
                tr((b0, 2.90))], "A-WALL")
        borde = max(balcon, key=abs)
        L.baranda(lam, tr, [(borde, 2.90), (borde, 3.90)])
    cotas_vista(lam, tr, largo, 0.196)
    niveles_vista(lam, tr, largo)
    lam.tx(titulo, (0.078, 0.398), 0.0032, "A-ANNO", "ml")
    lam.tx(subtitulo, (0.078, 0.393), 0.0017, "A-ANNO", "ml")
    yf = planilla_aberturas_muro(lam, 0.078, 0.170,
                                 [muro, L.buscar_muro(PA, muro_id)],
                                 ["PB", "PA"])
    L.nota(lam, 0.240, 0.170, notas, h=0.0018, inter=0.0044,
           titulo="Notas de fachada", ancho=0.150)
    y1 = L.nota(lam, 0.400, 0.170, TEXTURAS, h=0.0018, inter=0.0044,
                titulo="Texturas y colores", ancho=0.170)
    L.nota(lam, 0.400, y1 - 0.012, [
        "La longitud total del lateral es de",
        "16,80 m y la altura hasta el parapeto",
        "de 6,55 m; la planta alta cubre la",
        "huella completa, de modo que la fachada",
        "es continua en toda su longitud.",
    ], h=0.0018, inter=0.0044, titulo="Descripcion", ancho=0.170)
    L.escala_grafica(lam, (0.078, min(yf - 0.020, 0.118)), 50)
    return lam


def l08() -> Lamina:
    return _hoja_lateral(
        8, "L08", "LATERAL ESTE", "M-E-ESTE", False,
        "Vista desde el lindero este - muro M-E-ESTE - 1:50",
        ["1. El lateral este reune las aberturas de living,",
         "   hall, toilette y cocina en PB, y las de los dos",
         "   dormitorios, oficina, toilette, vestidor y bano",
         "   en suite en PA.",
         "2. Las ventanas de 2,40 x 1,50 tienen alfeizar a",
         "   0,90 m y dintel a 2,40 m.",
         "3. La cubierta a un agua (1,8% al fondo) queda",
         "   escondida detrás del parapeto de +6,55: el",
         "   perfil superior de la fachada es horizontal.",
         "4. Al fondo asoma el modulo del tanque (+7,30) y",
         "   el balcón del dormitorio principal (+2,90)."],
        modulo=(14.30, 16.20), balcon=(16.80, 17.80))


def planilla_general_aberturas(lam, x: float, y: float) -> float:
    """Planilla general de aberturas de toda la vivienda (PB + PA)."""
    filas = [["CODIGO", "MURO", "NIV.", "TIPO", "ANCHO", "ALTO", "ANTEP."]]
    for spec, niv in ((PB, "PB"), (PA, "PA")):
        for muro in spec["muros"]:
            for o in sorted(muro.get("aberturas", []),
                            key=lambda o: float(o["s"])):
                if o.get("tipo") == "hueco":
                    continue
                alto, sill = alzado_abertura(o)
                filas.append([o.get("id", ""), muro.get("id", ""), niv,
                              o.get("tipo", "")[:7], fmt(float(o["ancho"])),
                              fmt(alto), fmt(sill) if sill else "-"])
    return L.tabla(lam, x, y, [0.024, 0.021, 0.010, 0.017, 0.015, 0.014, 0.015],
                   filas, 0.0044, 0.0016,
                   alineacion=["ml", "ml", "mc", "ml", "mr", "mr", "mr"])


def l09() -> Lamina:
    lam = Lamina(9, TOTAL, "LATERAL OESTE", 50, codigo="L09", fecha=FECHA)
    muro = L.buscar_muro(PB, "M-E-OESTE")
    largo = L.longitud(muro)
    tr = fachada(lam, PB, PA, "M-E-OESTE", origen=(0.078, 0.215), espejo=True,
                 con_texto=False)
    # módulo del tanque: y 17,40..19,40 -> espejado 0,50..2,50
    lam.pl([tr((0.50, 5.85)), tr((2.50, 5.85)), tr((2.50, 7.30)),
            tr((0.50, 7.30))], "A-WALL")
    lam.tx("MODULO TANQUE +7,30", tr((1.55, 7.45)), 0.0014, "A-ANNO", "mc")
    # balcón de perfil: y 19,90..20,90 -> espejado -1,00..0,00
    lam.pl([tr((-1.00, 2.72)), tr((0.00, 2.72)), tr((0.00, 2.90)),
            tr((-1.00, 2.90))], "A-WALL")
    L.baranda(lam, tr, [(-1.00, 2.90), (-1.00, 3.90)])
    cotas_vista(lam, tr, largo, 0.196)
    niveles_vista(lam, tr, largo)
    lam.tx("LATERAL OESTE", (0.078, 0.398), 0.0032, "A-ANNO", "ml")
    lam.tx("Vista desde el lindero oeste - muro M-E-OESTE (medianera) - 1:50",
           (0.078, 0.393), 0.0017, "A-ANNO", "ml")
    L.nota(lam, 0.240, 0.170, [
        "1. El lateral oeste es medianera: no lleva",
        "   aberturas en ningun nivel.",
        "2. Muro de 0,20 m revocado y pintado en toda su",
        "   altura, con junta de dilatacion cada 6,00 m.",
        "3. La cubierta a un agua (1,8% al fondo) queda",
        "   escondida detrás del parapeto de +6,55.",
        "4. Al fondo asoman el módulo del tanque (+7,30) y",
        "   el balcón del dormitorio principal (+2,90).",
        "5. Los locales se ventilan por el lateral este y",
        "   por la cubierta de azotea.",
    ], h=0.0018, inter=0.0044, titulo="Notas de fachada", ancho=0.150)
    y1 = L.nota(lam, 0.400, 0.170, TEXTURAS, h=0.0018, inter=0.0044,
                titulo="Texturas y colores", ancho=0.170)
    L.nota(lam, 0.400, y1 - 0.012, [
        "Al no tener vanos, la vista se resuelve como",
        "plano ciego con despiece de revoque cada",
        "1,50 m y junta horizontal a la altura de la",
        "losa de +2,80. El nivel +5,75 marca el",
        "arranque del parapeto de 0,80 m.",
    ], h=0.0018, inter=0.0044, titulo="Descripcion", ancho=0.170)
    planilla_general_aberturas(lam, 0.432, 0.384)
    L.escala_grafica(lam, (0.078, 0.176), 50)
    return lam





# ---------------------------------------------------------------------------
# L10 / L11 — instalaciones
# ---------------------------------------------------------------------------
# artefactos de L10 (bloque, x, y, rot, capa) — los mismos del mobiliario de L01
FIX_PB = [
    # toilette amplio (muro este)
    ("A-INODORO", 5.00, 12.55, 0, "A-MOB"),
    ("A-LAVATORIO", 6.05, 12.55, 270, "A-MOB"),
    ("A-DUCHA-090", 5.60, 13.65, 0, "A-MOB"),
    # lavadero al fondo
    ("A-PILETA-LAVAR", 0.25, 17.05, 0, "A-MOB"),
    ("A-LAVARROPAS", 0.25, 17.75, 0, "A-MOB"),
    # cocina abierta
    ("A-MESADA-300", 5.95, 14.90, 270, "A-MOB"),
    ("A-COCINA-4H", 5.95, 15.60, 0, "A-MOB"),
    ("A-PILETA-LAVAR", 5.95, 16.90, 0, "A-MOB"),
]

FIX_PA = [
    # bano compartido entre los dos dormitorios
    ("A-DUCHA-090", 2.85, 3.25, 0, "A-MOB"),
    ("A-LAVATORIO", 2.85, 4.40, 270, "A-MOB"),
    ("A-INODORO", 2.85, 5.40, 180, "A-MOB"),
    # toilette de la oficina
    ("A-INODORO", 6.20, 12.55, 180, "A-MOB"),
    ("A-LAVATORIO", 5.75, 12.55, 270, "A-MOB"),
    # bano en suite
    ("A-INODORO", 3.70, 15.75, 0, "A-MOB"),
    ("A-LAVATORIO", 3.65, 16.70, 270, "A-MOB"),
    ("A-BANERA-170", 5.60, 15.75, 90, "A-MOB"),
]

# Redes de agua en coordenadas de proyecto.
# AF y AC van EMPOTRADAS EN LOS MUROS: cada red corre por el eje del muro con
# un offset de +0,05 (AF) y -0,05 (AC), de modo que las dos caben dentro del
# espesor y no se pisan entre sí.  Las cloacales van bajo el contrapiso y las
# pluviales bajan por los ejes de los muros de fachada.
# Ejemplos de eje: este x=6,70 (AF 6,75 / AC 6,65) · oeste x=0,10 (0,05/0,15)
# · frente y=3,10 (3,15/3,05) · fondo PB y=19,90 (19,95/19,85).
AF_PB = [
    [(1.75, 2.45), (1.75, 3.15)],                       # acometida al nicho
    [(1.75, 3.15), (6.75, 3.15)],                       # muro de frente
    [(6.75, 3.15), (6.75, 19.95)],                      # montante muro este
    [(6.75, 19.95), (1.55, 19.95)],                     # muro de fondo (hasta lavadero)
    [(1.55, 19.95), (1.55, 19.65)],                     # conexion al calefon
    [(1.55, 19.95), (0.05, 19.95)],                     # muro de fondo (oeste)
    [(0.05, 19.95), (0.05, 17.35)],                     # bajada muro oeste
    [(0.05, 17.35), (0.25, 17.35)],                     # pileta de lavar
    [(0.05, 18.05), (0.25, 18.05)],                     # lavarropas
    [(6.75, 12.475), (5.20, 12.475)],                   # ramal muro M-I-06
    [(5.20, 12.475), (5.20, 12.55)],                    # conexion al inodoro
    [(6.75, 12.85), (6.50, 12.85)],                     # lavatorio
    [(6.75, 14.10), (6.50, 14.10)],                     # ducha
    [(6.75, 17.20), (6.55, 17.20)],                     # pileta de cocina
]

AC_PB = [
    [(1.55, 19.65), (1.55, 19.85)],                     # salida del calefon
    [(1.55, 19.85), (6.65, 19.85)],                     # muro de fondo (este)
    [(6.65, 19.85), (6.65, 12.375)],                    # montante muro este
    [(1.55, 19.85), (0.15, 19.85)],                     # muro de fondo (oeste)
    [(0.15, 19.85), (0.15, 17.45)],                     # bajada muro oeste
    [(0.15, 17.45), (0.25, 17.45)],                     # pileta de lavar
    [(6.65, 12.95), (6.50, 12.95)],                     # lavatorio
    [(6.65, 13.95), (6.50, 13.95)],                     # ducha
    [(6.65, 17.05), (6.55, 17.05)],                     # pileta de cocina
]

CL_PB = [
    [(5.10, 13.30), (5.10, 13.90), (6.55, 13.90)],      # inodoro toilette
    [(6.20, 12.80), (6.55, 12.80)],                     # lavatorio toilette
    [(5.90, 14.10), (5.90, 13.90)],                     # ducha toilette
    [(6.55, 19.10), (6.55, 3.60), (2.40, 3.60)],        # colector este + frente
    [(5.80, 17.70), (6.55, 17.70)],                     # pileta de cocina
    [(0.60, 17.60), (1.52, 17.60), (1.52, 3.60), (2.40, 3.60)],   # ramal oeste
    [(0.60, 18.10), (1.52, 18.10)],                     # lavarropas
    [(2.40, 3.60), (2.40, 2.60)],                       # entrada a la camara
    [(6.55, 19.10), (6.55, 19.50)],                     # ventilacion al fondo
]

PL_PB = [
    [(0.65, 19.90), (0.65, 20.20)],                     # bajada pluvial oeste
    [(6.15, 19.90), (6.15, 20.20)],                     # bajada pluvial este
]

AF_PA = [
    [(6.75, 3.15), (6.75, 19.95)],                      # montante muro este
    [(6.75, 3.15), (2.80, 3.15)],                       # ramal muro de frente
    [(2.80, 3.15), (2.80, 5.85)],                       # muro del bano compartido
    [(2.80, 3.70), (2.85, 3.70)],                       # ducha
    [(2.80, 4.70), (2.85, 4.70)],                       # lavatorio
    [(2.80, 5.75), (2.85, 5.75)],                       # inodoro
    [(6.75, 12.475), (5.95, 12.475)],                   # toilette oficina (M-I-07)
    [(6.40, 12.475), (6.40, 12.55)],                    # inodoro oficina
    [(5.95, 12.475), (5.95, 12.55)],                    # lavatorio oficina
    [(6.75, 15.675), (3.55, 15.675)],                   # bano suite (M-I-11)
    [(3.90, 15.675), (3.90, 15.75)],                    # inodoro suite
    [(3.60, 15.675), (3.60, 17.00), (3.65, 17.00)],     # lavatorio suite
    [(6.75, 15.85), (6.30, 15.85)],                     # banera
]

AC_PA = [
    [(6.65, 3.05), (6.65, 16.05)],                      # montante muro este
    [(6.65, 3.05), (2.70, 3.05)],                       # ramal muro de frente
    [(2.70, 3.05), (2.70, 5.00)],                       # muro del bano compartido
    [(2.70, 3.85), (2.85, 3.85)],                       # ducha
    [(2.70, 4.85), (2.85, 4.85)],                       # lavatorio
    [(6.65, 12.375), (5.95, 12.375), (5.95, 12.55)],    # lavatorio oficina
    [(3.50, 15.575), (3.50, 17.10), (3.65, 17.10)],     # lavatorio suite
    [(6.65, 16.05), (6.30, 16.05)],                     # banera
]

CL_PA = [
    [(3.05, 5.90), (3.05, 6.60), (6.60, 6.60)],         # inodoro bano compartido
    [(3.05, 3.70), (3.05, 5.90)],                       # ducha + lavatorio
    [(6.40, 13.10), (6.40, 12.70), (6.60, 12.70)],      # toilette oficina
    [(3.90, 16.10), (3.90, 17.50), (6.60, 17.50)],      # inodoro + lavatorio suite
    [(5.95, 16.60), (5.95, 17.50)],                     # banera
    [(6.60, 17.50), (6.60, 18.90)],                     # colector al fondo
]


SIM_SAN_PB = [
    ("S-MEDIDOR-AGUA", 1.75, 2.52, 0),
    ("S-CAMARA-INS", 2.40, 2.60, 0),
    ("S-LLAVE-PASO", 2.02, 3.45, 0),
    ("S-BOCA-ACCESO", 1.52, 9.75, 0),
    ("S-VENTILACION", 1.92, 19.20, 0),
    ("S-REJILLA-PISO", 5.75, 14.30, 0),
    ("S-REJILLA-PISO", 1.35, 18.35, 0),
]

SIM_SAN_PA = [
    ("S-REJILLA-PISO", 3.20, 3.60, 0),
    ("S-VENTILACION", 3.60, 6.70, 0),
    ("S-REJILLA-PISO", 4.30, 17.40, 0),
    ("S-VENTILACION", 5.90, 17.55, 0),
]


def marca(lam, tr: Tr, x: float, y: float, texto: str, capa: str = "A-ANNO",
          dx: float = 0.0036, dy: float = 0.0036):
    """Marca de montante / pilar: círculo en el punto y rótulo con leader."""
    p = tr((x, y))
    q = (p[0] + dx, p[1] + dy)
    lam.circ(p, 0.0012, capa)
    lam.ln(p, q, capa)
    lam.ln(q, (q[0] + 0.004, q[1]), capa)
    lam.tx(texto, (q[0] + 0.0048, q[1]), 0.0017, capa, "ml")


def l10() -> Lamina:
    lam = Lamina(10, TOTAL, "INSTALACION SANITARIA", 50, codigo="L10",
                 fecha=FECHA)
    cabecera(lam, "INSTALACION SANITARIA",
             "AGUA FRIA, AGUA CALIENTE, CLOACAS Y PLUVIAL - PLANTAS 1:50",
             0.362, 0.401)
    tr_pb = planta(lam, PB, origen=(0.068, 0.048), ancla=(0.1, 3.1),
                   areas=False, mob=FIX_PB, h_nombre=0.0021)
    lam.tx("PLANTA BAJA +0,00", (0.068, 0.036), 0.0023, "A-ANNO", "ml")
    lam.tx("1:50", (0.200, 0.036), 0.0023, "A-ANNO", "mr")
    tr_pa = planta(lam, PA, origen=(0.216, 0.048), ancla=(0.1, 3.1),
                   areas=False, mob=FIX_PA, h_nombre=0.0021)
    lam.tx("PLANTA ALTA +2,90", (0.216, 0.036), 0.0023, "A-ANNO", "ml")
    lam.tx("1:50", (0.348, 0.036), 0.0023, "A-ANNO", "mr")

    # Una capa y un color por red: AF azul continuo, AC rojo de trazos,
    # CL verde trazo y punto, PL amarillo raya-punto.
    REDES = ((tr_pb, ((AF_PB, "I-AF", None), (AC_PB, "I-AC", "DASHED"),
                      (CL_PB, "I-CL", "PHANTOM"), (PL_PB, "I-PL", "DASHDOT"))),
             (tr_pa, ((AF_PA, "I-AF", None), (AC_PA, "I-AC", "DASHED"),
                      (CL_PA, "I-CL", "PHANTOM"))))
    for tr, redes in REDES:
        for tramos, capa, lt in redes:
            for pts in tramos:
                L.cano(lam, tr, pts, capa, lt)

    # artefactos y accesorios, cada uno en la capa de su red
    CAPA_SIM = {"S-MEDIDOR-AGUA": "I-AF", "S-LLAVE-PASO": "I-AF",
                "S-CAMARA-INS": "I-CL", "S-BOCA-ACCESO": "I-CL",
                "S-VENTILACION": "I-CL", "S-REJILLA-PISO": "I-CL"}
    for bloque, x, y, rot in SIM_SAN_PB:
        L.poner(lam, bloque, tr_pb, x, y, rot, CAPA_SIM.get(bloque, "I-SAN"))
    for bloque, x, y, rot in SIM_SAN_PA:
        L.poner(lam, bloque, tr_pa, x, y, rot, CAPA_SIM.get(bloque, "I-SAN"))

    # montantes: AF y AC en el muro este (6,75 / 6,65); cloacales bajando por
    # el mismo muro para apilar con el colector de PB
    for tr in (tr_pb, tr_pa):
        marca(lam, tr, 6.75, 14.30, "M1")
        marca(lam, tr, 6.75, 12.475, "M2")
        marca(lam, tr, 6.55, 6.60, "M5")
        marca(lam, tr, 6.55, 13.60, "M6")
        marca(lam, tr, 6.55, 17.50, "M7")

    # --- columna derecha: planillas, memoria y leyenda ----------------------
    lam.tx("PLANILLA DE ARTEFACTOS Y CONEXIONES", (0.362, 0.389), 0.0019,
           "A-ANNO", "ml")
    filas = [
        ["LOCAL", "ARTEFACTO", "C", "AGUA", "DN", "DESAGUE"],
        ["TOILETTE", "INODORO", "1", "AF", "0,013", "0,110"],
        ["TOILETTE", "LAVATORIO", "1", "AF/AC", "0,013", "0,040"],
        ["TOILETTE", "DUCHA", "1", "AF/AC", "0,013", "0,040"],
        ["LAVADERO", "PILETA", "1", "AF/AC", "0,013", "0,040"],
        ["LAVADERO", "LAVARROPAS", "1", "AF", "0,013", "0,040"],
        ["LAVADERO", "CALEFON", "1", "AF/AC", "0,019", "-"],
        ["COCINA", "PILETA", "1", "AF/AC", "0,013", "0,040"],
        ["BANO COMPARTIDO", "INODORO", "1", "AF", "0,013", "0,110"],
        ["BANO COMPARTIDO", "LAVATORIO", "1", "AF/AC", "0,013", "0,040"],
        ["BANO COMPARTIDO", "DUCHA", "1", "AF/AC", "0,013", "0,040"],
        ["TOILETTE OFICINA", "INODORO", "1", "AF", "0,013", "0,110"],
        ["TOILETTE OFICINA", "LAVATORIO", "1", "AF/AC", "0,013", "0,040"],
        ["BANO SUITE", "INODORO", "1", "AF", "0,013", "0,110"],
        ["BANO SUITE", "LAVATORIO", "1", "AF/AC", "0,013", "0,040"],
        ["BANO SUITE", "BANERA", "1", "AF/AC", "0,013", "0,040"],
    ]
    y1 = L.tabla(lam, 0.362, 0.386,
                 [0.050, 0.052, 0.008, 0.016, 0.014, 0.016], filas, 0.0050,
                 0.0016, alineacion=["ml", "ml", "mc", "mc", "mr", "mr"])
    y1 = L.nota(lam, 0.362, y1 - 0.010, [
        "1. Presion minima en la conexion: 12 m.c.a.;",
        "   caudal de calculo 0,55 l/s.",
        "2. Acometida DN 0,019 con medidor y llave de paso",
        "   en el nicho de la vereda, sobre el eje municipal.",
        "3. AF: 0,019 principal y 0,013 ramales; AC: 0,013",
        "   con aislacion elastomerica.",
        "4. Cloacas: colector DN 110 y desagues 0,040, bajo",
        "   el contrapiso con 2% hacia la camara de 0,60 x 0,60.",
        "5. Ventilacion: 2 montantes hasta +6,55 sobre la",
        "   azotea, con sombrerete.",
        "6. Calefon de 14 l/min a gas en el lavadero, con",
        "   conducto de evacuacion al techo.",
        "7. AF y AC van empotradas en los muros (offset +0,05",
        "   / -0,05 por eje) y los montantes M1, M2, M5-M7",
        "   apilan PB y PA sobre el muro este.",
        "8. Pluvial: 2 desagues en canaleta y 2 bajadas de",
        "   0,10 al jardin de fondo.",
    ], h=0.0017, inter=0.0041, titulo="Memoria de calculo", ancho=0.216)
    filas = [
        ["TRAMO", "DN", "PEND.", "LONG.", "MONTANTE"],
        ["Acometida AF", "0,019", "-", "6,10", "M1"],
        ["Colector cloacal", "0,110", "2%", "16,40", "M5-M7"],
        ["Ramal cocina", "0,040", "2%", "2,90", "M7"],
        ["Ramal lavadero", "0,040", "2%", "3,40", "M7"],
        ["Ramal toilette PB", "0,040", "2%", "2,20", "M6"],
        ["Ramales banos PA", "0,040", "2%", "4,60", "M5-M7"],
    ]
    y2 = L.tabla(lam, 0.362, 0.214, [0.056, 0.026, 0.022, 0.024, 0.030],
                 filas, 0.0046, 0.0016,
                 alineacion=["ml", "mr", "mr", "mr", "mc"])
    L.leyenda(lam, 0.362, y2 - 0.010, [
        ("linea:I-AF", "Agua fria DN 0,019 / 0,013 - azul"),
        ("linea:I-AC:DASHED", "Agua caliente DN 0,013 - rojo"),
        ("linea:I-CL:PHANTOM", "Cloaca DN 0,110 / desague 0,040 - verde"),
        ("linea:I-PL:DASHDOT", "Pluvial DN 0,100 - amarillo"),
        ("bloque:S-MEDIDOR-AGUA", "Medidor de agua - nicho en vereda"),
        ("bloque:S-CAMARA-INS", "Camara de inspeccion 0,60 x 0,60"),
        ("bloque:S-BOCA-ACCESO", "Boca de acceso / registro"),
        ("bloque:S-VENTILACION", "Ventilacion cloacal - sombrerete"),
        ("bloque:S-REJILLA-PISO", "Rejilla de piso"),
        ("bloque:S-LLAVE-PASO", "Llave de paso"),
    ], h=0.0018, paso=0.0050, titulo="Referencias")
    L.escala_grafica(lam, (0.362, 0.098), 50)
    lam.tx("REPLANTEO DE CAÑERIAS: cotas parciales al eje de cada tramo,",
           (0.362, 0.084), 0.0017, "A-ANNO", "ml")
    lam.tx("ver planillas de montantes y desagues.", (0.362, 0.079), 0.0017,
           "A-ANNO", "ml")
    return lam

# --- L11: bocas eléctricas (bloque, x, y) ----------------------------------
ELE_PB = [
    # living-comedor
    ("E-BOCA-TECHO", 1.90, 5.40), ("E-BOCA-TECHO", 4.70, 5.40),
    ("E-BOCA-TECHO", 3.30, 8.40),
    ("E-TOM", 0.28, 4.40), ("E-TOM", 0.28, 7.60),
    ("E-TOM", 6.34, 4.40), ("E-TOM", 6.34, 8.20),
    ("E-TIMBRE", 1.15, 3.30), ("E-INT-1", 1.60, 3.30),
    ("E-PT", 6.20, 8.90),
    # hall y escalera abierta
    ("E-BOCA-TECHO", 4.60, 10.80),
    ("E-TOM", 6.34, 10.60),
    ("E-INT-2", 4.60, 9.60), ("E-INT-2", 4.60, 12.10),
    ("E-TABLERO", 5.85, 11.85), ("E-TERMICA", 5.85, 11.10),
    # pasillo y toilette
    ("E-BOCA-TECHO", 3.00, 13.50), ("E-BOCA-TECHO", 5.70, 13.60),
    ("E-TOM", 3.90, 13.95), ("E-TOM", 6.34, 12.90),
    ("E-INT-1", 4.35, 12.60),
    # despensa y lavadero
    ("E-BOCA-TECHO", 1.30, 15.80), ("E-BOCA-TECHO", 1.30, 18.40),
    ("E-TOM", 2.20, 15.10), ("E-TOM", 2.20, 17.30), ("E-TOM", 2.20, 19.50),
    ("E-INT-1", 2.20, 16.40),
    # cocina
    ("E-BOCA-TECHO", 3.60, 16.60), ("E-BOCA-TECHO", 5.20, 18.90),
    ("E-TOM", 2.60, 14.95), ("E-TOM", 6.34, 15.10), ("E-TOM", 6.34, 17.80),
    ("E-TOME", 6.34, 16.60),
    ("E-BOCA-EXT", 6.55, 12.20),
    ("E-INT-2", 2.60, 14.50),
]

RED_PB = [
    [(5.85, 11.85), (5.85, 10.80), (4.60, 10.80)],          # tablero - hall
    [(5.85, 10.80), (5.85, 5.40), (4.70, 5.40)],            # living este
    [(4.70, 5.40), (1.90, 5.40)],                           # living
    [(1.90, 5.40), (1.90, 8.40), (3.30, 8.40)],             # living fondo
    [(5.85, 11.85), (5.85, 16.60), (3.60, 16.60)],          # cocina
    [(5.85, 16.60), (5.85, 18.90), (5.20, 18.90)],          # cocina fondo
    [(3.60, 16.60), (3.60, 15.80), (1.30, 15.80)],          # despensa
    [(1.30, 15.80), (1.30, 18.40)],                         # lavadero
    [(1.30, 15.80), (1.30, 13.50), (2.40, 13.50)],          # pasillo
    [(1.30, 13.50), (1.30, 10.60)],                         # guardado
    [(2.40, 13.50), (3.00, 13.50)],                         # boca pasillo
    [(5.85, 13.60), (5.70, 13.60)],                         # toilette
]

ELE_PA = [
    # dormitorio 2
    ("E-BOCA-TECHO", 1.45, 5.20), ("E-TOM", 0.28, 3.60),
    ("E-TOM", 2.40, 6.75), ("E-INT-1", 1.70, 6.60),
    # bano compartido
    ("E-BOCA-TECHO", 3.40, 4.80), ("E-INT-1", 3.30, 6.60),
    # dormitorio 3
    ("E-BOCA-TECHO", 5.30, 5.20), ("E-TOM", 6.34, 3.60),
    ("E-TOM", 4.40, 6.75), ("E-INT-1", 5.70, 6.60),
    # hall
    ("E-BOCA-TECHO", 2.40, 8.20), ("E-BOCA-TECHO", 5.10, 8.20),
    ("E-TOM", 6.34, 8.60), ("E-INT-2", 2.40, 7.35),
    # pasillo
    ("E-BOCA-TECHO", 0.80, 10.80), ("E-TOM", 1.20, 11.70),
    ("E-INT-2", 1.20, 12.35),
    # oficina
    ("E-BOCA-TECHO", 5.10, 10.80), ("E-TOM", 6.34, 10.05),
    ("E-TOM", 3.90, 12.20), ("E-INT-1", 4.95, 9.30),
    # pasillo norte y toilette de la oficina
    ("E-BOCA-TECHO", 2.40, 13.00), ("E-BOCA-TECHO", 5.95, 13.00),
    ("E-TOM", 1.20, 13.35), ("E-INT-1", 5.40, 13.40),
    # dormitorio principal
    ("E-BOCA-TECHO", 1.80, 15.20), ("E-BOCA-TECHO", 1.80, 18.40),
    ("E-TOM", 0.28, 14.00), ("E-TOM", 0.28, 17.60),
    ("E-TOM", 3.30, 19.40), ("E-INT-2", 1.65, 13.85),
    # vestidor, bano en suite y guardado
    ("E-BOCA-TECHO", 5.00, 14.60), ("E-BOCA-TECHO", 5.00, 16.70),
    ("E-BOCA-TECHO", 5.00, 18.80), ("E-TOM", 6.34, 14.40),
    ("E-INT-1", 5.10, 13.85), ("E-INT-1", 5.10, 15.95),
]

RED_PA = [
    [(5.10, 8.20), (2.40, 8.20)],                           # hall
    [(2.40, 8.20), (1.45, 8.20), (1.45, 5.20)],             # dormitorio 2
    [(1.45, 5.20), (3.40, 5.20), (3.40, 4.80)],             # bano compartido
    [(3.40, 5.20), (5.30, 5.20), (5.30, 8.20)],             # dormitorio 3
    [(1.45, 8.20), (0.80, 8.20), (0.80, 10.80), (0.80, 13.00),
     (2.40, 13.00)],                                        # pasillo
    [(1.80, 13.00), (1.80, 15.20), (1.80, 18.40)],          # suite
    [(5.10, 8.20), (5.10, 10.80), (5.10, 13.00), (5.95, 13.00)],    # oficina
    [(5.10, 13.00), (5.00, 14.60), (5.00, 16.70), (5.00, 18.80)],   # vestidor
]

# gas: acometida, nicho, medidor, calefon (lavadero) y cocina
GAS_PB = [
    [(2.55, 2.80), (2.55, 3.35), (6.40, 3.35), (6.40, 19.35), (1.95, 19.35)],
    [(6.40, 15.90), (6.10, 15.90)],
]

GAS_SIM_PB = [
    ("G-NICHO", 2.20, 2.58),
    ("G-MEDIDOR", 2.35, 2.62),
    ("G-LLAVE", 3.12, 2.62),
    ("G-PUNTO", 6.10, 15.95),
    ("G-CALEFON", 1.50, 19.40),
    ("G-REJILLA", 1.50, 19.15),
    ("G-LLAVE", 6.28, 19.30),
]


def l11() -> Lamina:
    lam = Lamina(11, TOTAL, "INSTALACION ELECTRICA Y GAS", 50, codigo="L11",
                 fecha=FECHA)
    cabecera(lam, "INSTALACION ELECTRICA Y GAS",
             "BOCAS, CIRCUITOS Y CAÑERIA DE GAS - PLANTAS 1:50 Y 1:100",
             0.352, 0.401)
    tr_pb = planta(lam, PB, origen=(0.066, 0.048), ancla=(0.1, 3.1),
                   areas=False, mob=[], h_nombre=0.0021)
    lam.tx("PLANTA BAJA +0,00", (0.066, 0.036), 0.0023, "A-ANNO", "ml")
    lam.tx("1:50", (0.198, 0.036), 0.0023, "A-ANNO", "mr")
    tr_pa = planta(lam, PA, origen=(0.208, 0.048), ancla=(0.1, 3.1),
                   areas=False, mob=[], h_nombre=0.0021)
    lam.tx("PLANTA ALTA +2,90", (0.208, 0.036), 0.0023, "A-ANNO", "ml")
    lam.tx("1:50", (0.340, 0.036), 0.0023, "A-ANNO", "mr")

    for tr, red in ((tr_pb, RED_PB), (tr_pa, RED_PA)):
        for pts in red:
            L.cano(lam, tr, pts, "I-ELE")
    for bloque, x, y in ELE_PB:
        L.poner(lam, bloque, tr_pb, x, y, 0, "I-ELE")
    for bloque, x, y in ELE_PA:
        L.poner(lam, bloque, tr_pa, x, y, 0, "I-ELE")
    marca(lam, tr_pb, 5.85, 11.85, "T")
    marca(lam, tr_pa, 5.10, 8.20, "M")

    # --- cuadro de cargas ---------------------------------------------------
    lam.tx("CUADRO DE CARGAS - 220 V MONOFASICO", (0.352, 0.389), 0.0019,
           "A-ANNO", "ml")
    filas = [
        ["CIRC.", "DESCRIPCION", "BOCAS", "W", "A", "T.A.", "mm2"],
        ["C1", "ILUMINACION PB", "11", "780", "3,5", "2x16", "1,5"],
        ["C2", "TOMAS LIVING / ESC.", "5", "1000", "4,5", "2x16", "2,5"],
        ["C3", "TOMAS COCINA", "4", "800", "3,6", "2x16", "2,5"],
        ["C4", "TOMAS LAVADERO", "2", "600", "2,7", "2x16", "2,5"],
        ["C5", "TOME COCINA 4 H", "1", "2000", "9,1", "2x20", "4,0"],
        ["C6", "ILUMINACION PA", "12", "840", "3,8", "2x16", "1,5"],
        ["C7", "TOMAS PA", "10", "1600", "7,3", "2x16", "2,5"],
        ["", "TOTAL INSTALADO", "45", "7620", "34,5", "", ""],
    ]
    y1 = L.tabla(lam, 0.352, 0.386,
                 [0.016, 0.054, 0.014, 0.014, 0.010, 0.014, 0.010], filas,
                 0.0047, 0.0016,
                 alineacion=["mc", "ml", "mr", "mr", "mr", "mc", "mr"])
    L.leyenda(lam, 0.352, y1 - 0.011, [
        ("linea:CONTINUOUS", "Circuito de iluminacion (C1 / C6)"),
        ("bloque:E-BOCA-TECHO", "Boca de techo - artefacto de iluminacion"),
        ("bloque:E-BOCA-PARED", "Boca de pared - aplique / brazo"),
        ("bloque:E-BOCA-EXT", "Boca exterior estanca IP44"),
        ("bloque:E-TOM", "Tomacorriente 2P+T 10 A"),
        ("bloque:E-TOME", "Tomacorriente especial 20 A"),
        ("bloque:E-INT-1", "Interruptor simple"),
        ("bloque:E-INT-2", "Interruptor de 2 puntos"),
        ("bloque:E-TABLERO", "Tablero seccional con termica y disyuntor"),
        ("bloque:E-PT", "Toma de TV / datos"),
        ("bloque:E-TIMBRE", "Timbre con pulsador en puerta"),
    ], h=0.0018, paso=0.0053, titulo="Referencias electricas")
    y2 = L.nota(lam, 0.352, y1 - 0.011 - 0.0053 * 12 - 0.010, [
        "1. Alimentacion monofasica 220 V 50 Hz, acometida",
        "   subterranea 2x6 mm2 hasta el medidor en el nicho",
        "   de la vereda y de alli al tablero seccional.",
        "2. Tablero en el pasillo, a 1,60 m del piso, con",
        "   disyuntor diferencial 2x40 A 30 mA y una termica",
        "   por circuito; puesta a tierra con jabalina de 5/8.",
        "3. Iluminacion: 11 bocas en PB y 12 en PA, con",
        "   conductores de 1,5 mm2 en cañeria de PVC 3/4.",
        "4. Tomacorrientes: 16 A / 10 A segun circuito, a",
        "   0,30 m del piso y a 1,10 m sobre mesadas;",
        "   los de exterior son estancos IP44.",
        "5. Los tomas se vinculan a C2 a C5 y C7 con cañeria",
        "   independiente por cielorraso y muro: en planta se",
        "   indica solo la ubicacion de las bocas.",
    ], h=0.0017, inter=0.0040, titulo="Memoria de calculo", ancho=0.136)
    L.escala_grafica(lam, (0.352, 0.112), 50, tramos=(0, 1, 2))

    # --- gas ----------------------------------------------------------------
    tr_gas = Tr.anclado(0.500, 0.222, 100, ancla=(0.1, 3.1))
    planta(lam, PB, origen=(0.500, 0.222), escala=100, ancla=(0.1, 3.1),
           etiquetas=False, areas=False, mob=[], capa_muro="A-WALL")
    for pts in GAS_PB:
        L.cano(lam, tr_gas, pts, "I-GAS")
    for bloque, x, y in GAS_SIM_PB:
        L.poner(lam, bloque, tr_gas, x, y, 0, "I-GAS", escala=1.0 / 100)
    lam.tx("INSTALACION DE GAS - PLANTA BAJA", (0.500, 0.204), 0.0022,
           "A-ANNO", "ml")
    lam.tx("1:100", (0.566, 0.204), 0.0020, "A-ANNO", "mr")
    y3 = L.tabla(lam, 0.500, 0.195,
                 [0.036, 0.010, 0.012, 0.010],
                 [["ARTEFACTO", "C", "kcal/h", "DN"],
                  ["COCINA 4 H", "1", "4000", "0,013"],
                  ["CALEFON 14 l", "1", "8000", "0,013"],
                  ["TOTAL", "2", "12000", "0,019"]],
                 0.0046, 0.0016, alineacion=["ml", "mc", "mr", "mr"])
    L.nota(lam, 0.500, y3 - 0.008, [
        "1. Gas natural, presion 20 mbar;",
        "   acometida DN 0,019 desde la red",
        "   de la vereda.",
        "2. Nicho y medidor sobre el eje",
        "   municipal; llave de paso de",
        "   abonado a 0,20 m del piso.",
        "3. Cañeria de acero galvanizado a",
        "   la vista y PE-AL-PE enterrada.",
        "4. Calefon de tiro balanceado con",
        "   conducto y rejilla de ventilacion",
        "   al exterior segun detalle D-04.",
        "5. Llave de paso junto a cada",
        "   artefacto, a 1,50 m del piso.",
    ], h=0.0017, inter=0.0040, titulo="Referencias de gas", ancho=0.078)
    return lam

class Det:
    """Dibujo de detalle: coordenadas locales (m reales) -> papel."""

    def __init__(self, lam, cx: float, cy: float, escala: int):
        self.lam, self.cx, self.cy = lam, cx, cy
        self.k = 1.0 / float(escala)

    def p(self, u: float, v: float):
        return (self.cx + u * self.k, self.cy + v * self.k)

    def ln(self, a, b, capa: str = "A-WALL"):
        self.lam.ln(self.p(*a), self.p(*b), capa)

    def pl(self, pts, capa: str = "A-WALL"):
        self.lam.pl([self.p(*q) for q in pts], capa)

    def box(self, u0, v0, u1, v1, capa: str = "A-WALL", ray: bool = True,
            paso: float = 0.05, ang: float = 45.0):
        self.pl([(u0, v0), (u1, v0), (u1, v1), (u0, v1)], capa)
        if ray:
            a, b = self.p(u0, v0), self.p(u1, v1)
            L.rayado(self.lam, (*a, *b), paso * self.k, "A-HATCH", ang)

    def num(self, n, u: float, v: float):
        self.lam.tx(str(n), self.p(u, v), 0.0014, "A-ANNO", "mc")

    def tx(self, t, u: float, v: float, h: float = 0.0016, align="mc",
           capa: str = "A-ANNO"):
        self.lam.tx(t, self.p(u, v), h, capa, align)


def celda(lam, cx: float, y_top: float, w: float, h: float, codigo: str,
          titulo: str, escala: int) -> Det:
    """Marco de celda de detalle con su rótulo; devuelve el dibujo."""
    x0, x1 = cx - w / 2.0, cx + w / 2.0
    lam.pl([(x0, y_top - h), (x1, y_top - h), (x1, y_top), (x0, y_top)],
           "A-AREA")
    lam.tx(f"{codigo}  {titulo}", (x0 + 0.001, y_top - h - 0.006), 0.0019,
           "A-ANNO", "ml")
    lam.tx(f"1:{escala}", (x1 - 0.001, y_top - h - 0.006), 0.0018, "A-ANNO",
           "mr")
    return Det(lam, cx, y_top - h / 2.0 - 0.004, escala)


def l13() -> Lamina:
    """Planta de conjunto 1:100: lote, accesos y jardin."""
    lam = Lamina(13, TOTAL, "PLANTA DE CONJUNTO", 100, codigo="L13",
                 fecha=FECHA)
    cabecera(lam, "PLANTA DE CONJUNTO",
             "LOTE 10,00 x 28,00 - ACCESOS Y JARDIN", 0.215)
    tr = Tr.anclado(0.070, 0.055, 100, ancla=(0.0, 0.0))

    # --- limites del lote y calle -------------------------------------------
    lam.pl([tr((0, 0)), tr((10, 0)), tr((10, 28)), tr((0, 28))], "A-WALL")
    lam.ln(tr((-0.8, 0)), tr((10.8, 0)), "A-AREA")
    lam.tx("CALLE", tr((5.0, -0.9)), 0.0018, "A-ANNO", "mc")
    lam.tx("LOTE 10,00 x 28,00 = 280,00 m2", tr((5.0, 27.2)), 0.0018,
           "A-ANNO", "mc")

    # --- terreno: hatch en los jardines (no se confunde con el piso interior)
    for caja in ((0.0, 0.0, 10.0, 3.0), (6.8, 3.0, 10.0, 20.0),
                 (0.0, 20.0, 10.0, 28.0)):
        a, b = tr((caja[0], caja[1])), tr((caja[2], caja[3]))
        L.rayado(lam, (a[0], a[1], b[0], b[1]), 0.0042, "A-HATCH", 45)

    # --- vivienda: solo los muros exteriores de PB --------------------------
    planta(lam, {"muros": [w for w in PB["muros"] if w.get("tipo") == "exterior"],
                 "ambientes": []},
           origen=(0.070, 0.055), escala=100, ancla=(0.0, 0.0),
           con_ambientes=False, mob=[])
    lam.tx("VIVIENDA 2 PLANTAS", tr((3.4, 11.5)), 0.0020, "A-ANNO", "mc")
    lam.tx("HUELLA 6,80 x 17,00 - FOS 0,396 - FOT 0,70", tr((3.4, 10.9)),
           0.0014, "A-ANNO", "mc")

    # --- acceso peatonal ----------------------------------------------------
    a, b = tr((0.20, 0.0)), tr((1.40, 3.0))
    L.rayado(lam, (a[0], a[1], b[0], b[1]), 0.0030, "A-HATCH", 0)
    lam.tx("ACCESO PEATONAL", tr((0.8, 1.5)), 0.0013, "A-ANNO", "mc", 90)

    # --- vegetacion ---------------------------------------------------------
    for nombre, x, y in (("A-ARBOL-A", 8.30, 7.00),
                         ("A-ARBOL-B", 8.40, 12.20),
                         ("A-ARBOL-A", 8.30, 17.40),
                         ("A-ARBOL-A", 6.20, 25.20),
                         ("A-ARBOL-B", 2.30, 26.20),
                         ("A-ARBOL-B", 8.40, 25.60)):
        lam.blk(nombre, tr((x, y)), escala=1.0 / 100, rot=0, capa="A-MOB")
    for x, y, rot in ((2.30, 1.10, 0), (3.90, 1.10, 0), (2.30, 2.30, 0),
                      (4.60, 2.20, 90)):
        lam.blk("A-PLANTIN", tr((x, y)), escala=1.0 / 100, rot=rot,
                capa="A-MOB")
    lam.tx("JARDIN LATERAL ESTE 3,20 m", tr((8.4, 14.6)), 0.0014,
           "A-ANNO", "mc", 90)
    lam.tx("FONDO 8,00 m", tr((6.0, 22.0)), 0.0014, "A-ANNO", "mc")

    # --- cotas del lote y de los retiros ------------------------------------
    L.cota_h(lam, tr((0, 0))[0], tr((10, 0))[0], 0.043, 0.0, "10,00", 0.0019)
    L.cota_v(lam, tr((0, 0))[1], tr((0, 28))[1], 0.060, 0.0, "28,00", 0.0019)
    L.cota_v(lam, tr((0, 0))[1], tr((0, 3))[1], 0.052, 0.0, "3,00", 0.0016)
    L.cota_v(lam, tr((0, 20))[1], tr((0, 28))[1], 0.052, 0.0, "8,00", 0.0016)
    L.cota_h(lam, tr((6.8, 0))[0], tr((10, 0))[0], 0.037, 0.0, "3,20", 0.0016)

    # --- memoria, planilla, leyenda ----------------------------------------
    L.nota(lam, 0.215, 0.376, [
        "1. Lote entre medianeras de 10,00 x 28,00 m (280 m2). Huella",
        "   de la vivienda 6,80 x 17,00 m (paredes exteriores); deja",
        "   jardin lateral este de 3,20 m, retiro frontal de 3,00 m y",
        "   fondo libre de 8,00 m, medidos en claro desde el paramento.",
        "2. Huella de ejes 6,60 x 16,80 = 110,88 m2; FOS 0,396 y FOT",
        "   0,70 declarados (verificar con el Codigo Urbanistico).",
        "   Altura maxima +6,55 de parapeto y +7,30 el modulo del tanque.",
        "3. Acceso peatonal de 1,20 m por el oeste hasta la",
        "   puerta de entrada.",
        "4. Vegetacion: 3 arboles en el jardin este, 3 al fondo y",
        "   plantines sobre el acceso peatonal.",
        "5. El hatch indica terreno natural: el interior de la",
        "   vivienda queda sin hatch para distinguir el piso.",
    ], h=0.0018, inter=0.0044, titulo="Memoria de conjunto", ancho=0.178)
    filas = [["CONCEPTO", "m2", "MEDIDAS"],
             ["Lote", "280,00", "10,00 x 28,00"],
             ["Vivienda PB", "101,90", "6,80 x 17,00"],
             ["Vivienda PA", "94,39", ""],
             ["Jardin + fondo", "178,10", ""]]
    L.tabla(lam, 0.215, 0.196, [0.070, 0.030, 0.048], filas, 0.0050, 0.0017,
            alineacion=["ml", "mr", "ml"])
    L.leyenda(lam, 0.400, 0.376, [
        ("linea", "Linea municipal y ejes medianeros"),
        ("linea-corta", "Limite de jardin"),
        ("circulo", "Arbol de 1ra magnitud"),
        ("circulo-negro", "Arbol / arbusto"),
        ("bloque:A-PLANTIN", "Plantin sobre el acceso"),
    ], h=0.0018, paso=0.0050, titulo="Referencias")
    L.norte(lam, (0.520, 0.180), 0.0125)
    L.escala_grafica(lam, (0.215, 0.070), 100, tramos=(0, 1, 2))
    return lam


def l12() -> Lamina:
    lam = Lamina(12, TOTAL, "DETALLES Y SUPERFICIES", 10, codigo="L12",
                 fecha=FECHA)
    cabecera(lam, "DETALLES CONSTRUCTIVOS Y SUPERFICIES",
             "CORTES DE OBRA FINA - ESCALAS 1:5 Y 1:10 - COTAS EN METROS",
             0.045, 0.401)

    # --- D-01 platea, contrapiso y piso -------------------------------------
    d = celda(lam, 0.115, 0.390, 0.158, 0.094, "D-01",
              "PLATEA, CONTRAPISO Y PISO", 10)
    d.box(-0.62, -0.46, 0.62, -0.30, paso=0.06)
    d.box(-0.62, -0.30, 0.62, -0.15, paso=0.05, ang=135)
    d.ln((-0.62, -0.153), (0.62, -0.153))
    d.ln((-0.62, -0.145), (0.62, -0.145))
    d.box(-0.62, -0.145, 0.62, -0.05, paso=0.05, ang=0)
    d.box(-0.62, -0.05, 0.62, 0.00, paso=0.03, ang=90)
    d.box(-0.62, 0.00, -0.42, 0.42, paso=0.05)
    d.box(-0.42, 0.00, -0.40, 0.10, ray=False)
    d.num(1, 0.30, -0.38)
    d.num(2, 0.30, -0.22)
    d.num(3, 0.30, -0.152)
    d.num(4, 0.30, -0.10)
    d.num(5, 0.45, -0.028)
    d.num(6, -0.52, 0.30)
    d.num(7, -0.32, 0.05)
    d.tx("NIVEL +0,00", 0.52, 0.05, 0.0015, "mc")

    # --- D-02 azotea, parapeto y desague pluvial ----------------------------
    d = celda(lam, 0.275, 0.390, 0.158, 0.094, "D-02",
              "AZOTEA, PARAPETO Y DESAGUE", 10)
    d.box(-0.10, -0.40, 0.10, 0.42, paso=0.05)
    d.box(0.10, -0.15, 0.56, 0.00, paso=0.05, ang=135)
    d.ln((0.10, 0.003), (0.56, 0.003))
    d.ln((0.104, 0.00), (0.104, 0.20))
    d.box(0.10, 0.02, 0.56, 0.05, paso=0.04, ang=0)
    d.ln((0.11, 0.20), (0.26, 0.05))
    d.box(-0.14, 0.42, 0.14, 0.46, ray=False)
    d.ln((0.56, 0.02), (0.58, 0.02))
    d.ln((0.58, 0.02), (0.58, -0.38))
    d.ln((0.62, 0.02), (0.62, -0.38))
    d.ln((0.58, 0.02), (0.62, 0.02))
    d.ln((0.40, 0.14), (0.40, 0.005))
    d.ln((0.50, 0.085), (0.50, 0.055))
    d.ln((0.21, 0.23), (0.17, 0.15))
    d.ln((0.16, 0.44), (0.22, 0.44))
    d.num(1, 0.00, 0.32)
    d.num(3, 0.40, 0.17)
    d.num(4, 0.50, 0.10)
    d.num(5, 0.22, 0.25)
    d.num(6, 0.25, 0.44)
    d.num(7, 0.60, -0.40)
    d.num(2, 0.35, -0.07)
    d.tx("+5,75", 0.65, 0.09, 0.0015, "mc")

    # --- D-03 antepecho y alfeizar -----------------------------------------
    d = celda(lam, 0.115, 0.278, 0.158, 0.094, "D-03",
              "ANTEPECHO Y ALFEIZAR DE VENTANA", 10)
    d.box(-0.10, -0.45, 0.10, -0.02, paso=0.05)
    d.box(-0.16, -0.02, 0.14, 0.02, paso=0.03, ang=0)
    d.box(-0.02, 0.02, 0.00, 0.40, ray=False)
    d.box(0.04, 0.02, 0.06, 0.40, ray=False)
    d.ln((0.015, 0.04), (0.015, 0.38))
    d.ln((0.028, 0.04), (0.028, 0.38))
    d.box(-0.12, -0.45, -0.10, -0.02, paso=0.03, ang=90)
    d.ln((-0.16, -0.005), (-0.13, -0.005))
    d.ln((-0.13, -0.005), (-0.13, -0.02))
    d.num(1, -0.05, -0.30)
    d.num(2, -0.05, 0.00)
    d.ln((0.06, 0.32), (0.10, 0.32))
    d.num(3, 0.13, 0.32)
    d.ln((0.01, 0.24), (-0.03, 0.24))
    d.num(4, -0.06, 0.24)
    d.num(5, -0.11, -0.34)
    d.num(6, -0.20, -0.02)
    d.tx("+0,90", 0.12, 0.02, 0.0015, "mc")

    # --- D-04 canaleta y bajada pluvial -------------------------------------
    d = celda(lam, 0.275, 0.278, 0.158, 0.094, "D-04",
              "CANALETA Y BAJADA PLUVIAL", 10)
    d.box(-0.10, -0.30, 0.10, 0.36, paso=0.05)
    d.ln((0.10, 0.100), (0.68, 0.060))
    d.ln((0.10, 0.086), (0.68, 0.046))
    d.box(0.30, 0.02, 0.36, 0.072, ray=False)
    d.box(0.10, -0.03, 0.64, 0.02, paso=0.05, ang=135)
    d.ln((0.660, 0.055), (0.660, 0.005))
    d.ln((0.660, 0.005), (0.716, 0.005))
    d.ln((0.716, 0.005), (0.716, 0.045))
    d.ln((0.662, 0.005), (0.662, -0.40))
    d.ln((0.714, 0.005), (0.714, -0.40))
    d.ln((0.24, 0.115), (0.24, 0.095))
    d.ln((0.69, 0.065), (0.70, 0.050))
    d.num(1, -0.02, 0.28)
    d.num(2, 0.24, 0.135)
    d.num(3, 0.33, 0.045)
    d.num(4, 0.45, -0.005)
    d.num(5, 0.68, 0.080)
    d.num(6, 0.688, -0.35)

    # --- D-05 camara de inspeccion -----------------------------------------
    d = celda(lam, 0.115, 0.166, 0.158, 0.094, "D-05",
              "CAMARA DE INSPECCION", 10)
    d.box(-0.45, -0.44, -0.30, 0.10, paso=0.05)
    d.box(0.30, -0.44, 0.45, 0.10, paso=0.05)
    d.box(-0.30, -0.44, 0.30, -0.30, paso=0.05, ang=135)
    d.box(-0.62, -0.27, -0.30, -0.16, ray=False)
    d.box(0.30, -0.27, 0.62, -0.16, ray=False)
    d.ln((-0.30, -0.30), (0.00, -0.34))
    d.ln((0.30, -0.30), (0.00, -0.34))
    d.box(-0.34, 0.10, 0.34, 0.15, paso=0.04, ang=0)
    d.num(1, -0.375, -0.05)
    d.num(2, 0.00, -0.37)
    d.num(3, 0.00, 0.125)
    d.num(4, -0.46, -0.215)
    d.num(5, 0.375, -0.34)

    # --- D-06 peldaño y nariz ----------------------------------------------
    d = celda(lam, 0.275, 0.166, 0.158, 0.094, "D-06",
              "PELDAÑO, NARIZ Y ZOCALO", 5)
    d.box(-0.30, -0.22, 0.36, 0.00, paso=0.04)
    d.box(-0.32, 0.02, 0.36, 0.04, paso=0.02, ang=0)
    d.box(-0.34, -0.20, -0.32, 0.02, ray=False)
    d.box(-0.30, 0.040, -0.26, 0.046, ray=False)
    d.ln((0.20, 0.04), (0.20, 0.12))
    d.num(1, 0.05, -0.12)
    d.num(2, 0.20, 0.15)
    d.ln((-0.33, 0.035), (-0.26, 0.13))
    d.num(3, -0.24, 0.16)
    d.ln((-0.27, 0.05), (-0.14, 0.14))
    d.num(4, -0.12, 0.17)
    d.ln((-0.34, -0.10), (-0.355, -0.145))
    d.num(5, -0.365, -0.175)

    # --- planilla de superficies -------------------------------------------
    spb, spa = superficie(PB), superficie(PA)
    ter = 10.00 * 28.00          # lote 10,00 x 28,00 m
    libre = ter - spb
    huella = 6.60 * 16.80        # huella entre ejes 6,60 x 16,80 m
    lam.tx("PLANILLA DE SUPERFICIES", (0.368, 0.390), 0.0021, "A-ANNO",
           "ml")
    y = L.tabla(lam, 0.368, 0.386, [0.098, 0.042, 0.024],
                [["CONCEPTO", "m2", "%"],
                 ["TERRENO 10,00 x 28,00", fmt(ter), "100"],
                 ["SUPERFICIE DE AMBIENTES PB", fmt(spb),
                  fmt(round(spb / ter * 100))],
                 ["SUPERFICIE DE AMBIENTES PA", fmt(spa),
                  fmt(round(spa / ter * 100))],
                 ["TOTAL DE AMBIENTES (FOT)", fmt(spb + spa),
                  fmt(round((spb + spa) / ter * 100))],
                 ["HUELLA CUBIERTA 6,60x16,80", fmt(huella),
                  fmt(round(huella / ter * 100))],
                 ["BALCON +2,90", "3,28", "1"],
                 ["MODULO TANQUE +7,30", "4,80", "-"],
                 ["SUPERFICIE LIBRE (JARDIN)", fmt(libre),
                  fmt(round(libre / ter * 100))],
                 ["FOS = HUELLA / TERRENO", "0,396", "-"],
                 ["ALTURA MAXIMA +7,30 (modulo)", "-", "-"]],
                0.0042, 0.0016, alineacion=["ml", "mr", "mr"])

    # --- referencias de los detalles ---------------------------------------
    def refs(x0: float, y0: float, bloques) -> float:
        yy = y0
        for tit, lineas in bloques:
            lam.tx(tit, (x0, yy), 0.0017, "A-ANNO", "ml")
            yy -= 0.0044
            for t in lineas:
                lam.tx(t, (x0, yy), 0.0015, "A-ANNO", "ml")
                yy -= 0.0037
            yy -= 0.0030
        return yy

    lam.tx("REFERENCIAS DE DETALLES", (0.368, 0.334), 0.0019, "A-ANNO", "ml")
    refs(0.368, 0.328, [
        ("D-01  PLATEA Y PISO", [
            "1 terreno compactado 95% Proctor",
            "2 platea H21 e=0,15 con malla Q92",
            "3 capa aisladora horizontal 1:3",
            "4 contrapiso H8 e=0,10",
            "5 carpeta 1:3 y piso de porcelanato",
            "6 muro de HLA 18x18x33 e=0,18",
            "7 zocalo de 0,10 con adhesivo"]),
        ("D-02  AZOTEA Y PARAPETO", [
            "1 parapeto HLA e=0,20 h=1,00",
            "2 losa H21 e=0,15",
            "3 membrana asfaltica 4 mm",
            "4 proteccion pesada e=0,03",
            "5 babetta 0,10 con refuerzo",
            "6 remate metalico del parapeto",
            "7 bajada pluvial PVC 0,10"]),
        ("D-03  ANTEPECHO", [
            "1 muro de HLA bajo alfeizar",
            "2 alfeizar de marmol e=0,03",
            "3 marco de aluminio linea A30",
            "4 DVH 4-9-4",
            "5 revoque exterior hidrofugo",
            "6 goteron y babeta de escurrido"]),
    ])
    refs(0.478, 0.328, [
        ("D-04  CANALETA Y BAJADA PLUVIAL", [
            "1 parapeto de HLA e=0,20 h=0,80",
            "2 canaleta de chapa galvanizada",
            "3 collarín y refuerzo de membrana",
            "4 membrana asfaltica 4 mm y losa H21",
            "5 embudo de desague",
            "6 bajada pluvial PVC DN 110"]),
        ("D-05  CAMARA DE INSPECCION", [
            "1 mamposteria de H15 e=0,15",
            "2 fondo con pendiente 2%",
            "3 tapa de H21 0,60 x 0,60",
            "4 caño PVC DN 110",
            "5 revoque hidrofugo interior"]),
        ("D-06  PELDAÑO 1:5", [
            "1 hormigon H21 de la escalera",
            "2 carpeta y piso de granito",
            "3 nariz de 0,02",
            "4 cinta antideslizante",
            "5 guardacantos de 0,15"]),
    ])

    # --- notas generales ----------------------------------------------------
    L.nota(lam, 0.368, 0.222, [
        "1. Hormigones: H21 en platea, losa y escalera; H8 en",
        "   contrapisos; H15 en mamposteria de la camara.",
        "2. Mamposteria de HLA 18x18x33 con juntas de 0,01 y",
        "   encadenado de H21 cada 3,00 m.",
        "3. Revoque grueso 1:4 y fino 1:3; pintura latex",
        "   interior lavable y exterior acrilico.",
        "4. Aislacion: capa aisladora horizontal y vertical,",
        "   hidrofugo de masa en locales humedos.",
        "5. Carpinteria de aluminio linea A30 con DVH 4-9-4;",
        "   puertas de placa de 0,80 y 0,70.",
        "6. Instalaciones segun L10 (sanitaria) y L11",
        "   (electrica y gas); cotas en metros.",
        "7. Las medidas de detalle priman sobre las de planta;",
        "   verificar niveles en obra antes de replantear.",
    ], h=0.0017, inter=0.0040, titulo="Notas y especificaciones",
        ancho=0.210)
    L.escala_grafica(lam, (0.368, 0.146), 100, tramos=(0, 1, 2))
    lam.tx("Detalles D-01 a D-05 a escala 1:10 y D-06 a 1:5.",
           (0.368, 0.132), 0.0018, "A-ANNO", "ml")
    return lam


SHEETS = {
    "L01": l01,
    "L02": l02,
    "L03": l03,
    "L04": l04,
    "L05": l05,
    "L06": l06,
    "L07": l07,
    "L08": l08,
    "L09": l09,
    "L10": l10,
    "L11": l11,
    "L12": l12,
    "L13": l13,
}


def main(argv) -> int:
    pedidos = [a.upper() for a in argv[1:] if a.upper().startswith("L")]
    codigos = pedidos or list(SHEETS)
    OUT.mkdir(parents=True, exist_ok=True)
    fallas = 0

    for cod in codigos:
        fn = SHEETS.get(cod)
        if fn is None:
            print(f"lamina desconocida: {cod}")
            fallas += 1
            continue
        try:
            lam = fn()
        except Exception as exc:                      # noqa: BLE001
            print(f"{cod}: ERROR {type(exc).__name__}: {exc}")
            fallas += 1
            continue
        ruta = lam.guardar(OUT / f"{cod}.dxf")
        print(f"{cod}  {ruta.name}  {len(lam.msp)} entidades  "
              f"({lam.titulo}, 1:{lam.escala}, {lam.formato})")
    return 1 if fallas else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))


