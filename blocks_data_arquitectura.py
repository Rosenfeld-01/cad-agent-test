"""
blocks_data_arquitectura.py — aberturas y mobiliario de la biblioteca CAD_Blocks.

Bloques de arquitectura, en metros 1:1, con el punto de inserción (0,0) en el
gozne de la puerta o en la esquina inferior izquierda del mueble, y el bloque
"mirando hacia arriba" (+Y).
"""
from __future__ import annotations


def R(x0, y0, x1, y1):
    """Rectángulo cerrado."""
    return ("pl", [(x0, y0), (x1, y0), (x1, y1), (x0, y1)], True)


def L(x1, y1, x2, y2):
    return ("ln", (x1, y1), (x2, y2))


def C(x, y, r):
    return ("ci", (x, y), r)


def A(x, y, r, a1, a2):
    return ("ar", (x, y), r, a1, a2)


def T(txt, x, y, h, al="mc"):
    return ("tx", txt, (x, y), h, al)


def puerta(ancho: float, hojas: int = 1) -> list:
    """Hoja(s) abierta(s) a 90° + arco de giro. Gozne en (0,0)."""
    ops = []
    w = ancho / hojas
    for i in range(hojas):
        x0 = i * w
        # hoja abierta (perpendicular al muro), espesor 0,04
        ops.append(R(x0, 0.0, x0 + 0.04, w))
        ops.append(A(x0, 0.0, w, 0, 90))
    # topes del marco
    ops.append(L(0, -0.02, 0, 0.02))
    ops.append(L(ancho, -0.02, ancho, 0.02))
    return ops


def ventana(ancho: float, espesor: float = 0.15) -> list:
    """Ventana de abrir: 3 líneas de vidrio + cabeceros."""
    m = espesor / 2
    return [
        L(0, m, ancho, m),
        L(0, 0, ancho, 0),
        L(0, -m, ancho, -m),
        L(0, -m, 0, m),
        L(ancho, -m, ancho, m),
    ]


def modena(ancho: float, alto: float) -> list:
    """Modena de fachada (aluminio A30, DVH): marco + montante + travesaño.

    Bloque mirando hacia arriba, con la esquina inferior izquierda en (0,0).
    """
    m = 0.05
    return [
        R(0, 0, ancho, alto),                       # marco exterior
        R(m, m, ancho - m, alto - m),               # marco interior (hoja)
        L(ancho / 2.0, m, ancho / 2.0, alto - m),    # montante central
        L(m, alto * 0.72, ancho - m, alto * 0.72),   # travesaño superior
    ]


def modena_planta(ancho: float, espesor: float = 0.20) -> list:
    """Modena en planta: 3 líneas de vidrio + topes, centrada en (0,0)."""
    h = ancho / 2.0
    m = espesor / 2.0
    g = espesor / 6.0
    return [
        L(-h, g, h, g),
        L(-h, 0, h, 0),
        L(-h, -g, h, -g),
        L(-h, -m, -h, m),
        L(h, -m, h, m),
    ]


BLOQUES = [
    # ------------------------------------------------------------- aberturas
    {"nombre": "A-PUERTA-070", "cat": "Aberturas",
     "desc": "Puerta 0,70 m (placard / baño tipo IV)", "w": 0.70, "h": 0.70,
     "ops": puerta(0.70)},
    {"nombre": "A-PUERTA-080", "cat": "Aberturas",
     "desc": "Puerta interior 0,80 m (paso libre mínimo de baño tipo II)",
     "w": 0.80, "h": 0.80, "ops": puerta(0.80)},
    {"nombre": "A-PUERTA-090", "cat": "Aberturas",
     "desc": "Puerta de entrada 0,90 m", "w": 0.90, "h": 0.90, "ops": puerta(0.90)},
    {"nombre": "A-PUERTA-DOBLE-160", "cat": "Aberturas",
     "desc": "Puerta de dos hojas 2 x 0,80 m", "w": 1.60, "h": 1.60,
     "ops": puerta(1.60, hojas=2)},
    {"nombre": "A-PANEL-050", "cat": "Aberturas",
     "desc": "Panel / hoja de placard 0,50 m", "w": 0.50, "h": 0.50,
     "ops": puerta(0.50)},
    {"nombre": "A-VENTANA-090", "cat": "Aberturas",
     "desc": "Ventana 0,90 m (baño / toilette)", "w": 0.90, "h": 0.15,
     "ops": ventana(0.90)},
    {"nombre": "A-VENTANA-120", "cat": "Aberturas",
     "desc": "Ventana 1,20 m", "w": 1.20, "h": 0.15, "ops": ventana(1.20)},
    {"nombre": "A-VENTANA-150", "cat": "Aberturas",
     "desc": "Ventana 1,50 m", "w": 1.50, "h": 0.15, "ops": ventana(1.50)},
    {"nombre": "A-VENTANA-180", "cat": "Aberturas",
     "desc": "Ventana 1,80 m", "w": 1.80, "h": 0.15, "ops": ventana(1.80)},
    {"nombre": "A-VENTANA-240", "cat": "Aberturas",
     "desc": "Ventana 2,40 m (living / suite)", "w": 2.40, "h": 0.15,
     "ops": ventana(2.40)},
    {"nombre": "A-PUERTA-BALCON-160", "cat": "Aberturas",
     "desc": "Puerta balcón 2 hojas 1,60 m (a terraza)", "w": 1.60, "h": 1.60,
     "ops": puerta(1.60, hojas=2)},
    {"nombre": "A-PORTON-300", "cat": "Aberturas",
     "desc": "Portón corredizo 3,00 m (acceso vehicular)", "w": 3.00, "h": 0.20,
     "ops": [R(0, -0.05, 1.50, 0.05), R(1.50, -0.05, 3.00, 0.05),
             L(0.20, 0.10, 2.80, 0.10),
             T("CORREDIZO", 1.50, 0.22, 0.12)]},

    # ------------------------------------------------------------ mobiliario
    {"nombre": "A-CAMA-1PL", "cat": "Mobiliario",
     "desc": "Cama 1 plaza 0,90 x 1,90 m (MEDIDAS_CABA bloque B)",
     "w": 0.90, "h": 1.90,
     "ops": [R(0, 0, 0.90, 1.90), R(0.08, 1.50, 0.82, 1.82),
             L(0, 1.45, 0.90, 1.45)]},
    {"nombre": "A-CAMA-2PL", "cat": "Mobiliario",
     "desc": "Cama 2 plazas 1,40 x 1,90 m", "w": 1.40, "h": 1.90,
     "ops": [R(0, 0, 1.40, 1.90), R(0.08, 1.50, 0.68, 1.82),
             R(0.72, 1.50, 1.32, 1.82), L(0, 1.45, 1.40, 1.45)]},
    {"nombre": "A-PLACARD-210", "cat": "Mobiliario",
     "desc": "Placard 2,10 x 0,60 m (profundidad 0,60 de práctica)",
     "w": 2.10, "h": 0.60,
     "ops": [R(0, 0, 2.10, 0.60), L(0, 0.55, 2.10, 0.55),
             L(0.70, 0, 0.70, 0.55), L(1.40, 0, 1.40, 0.55)]},
    {"nombre": "A-MESA-6", "cat": "Mobiliario",
     "desc": "Mesa comedor 6 personas 1,60 x 0,90 m", "w": 1.60, "h": 0.90,
     "ops": [R(0, 0, 1.60, 0.90), R(0.06, 0.06, 0.34, 0.84),
             R(1.26, 0.06, 1.54, 0.84)]},
    {"nombre": "A-SILLA", "cat": "Mobiliario",
     "desc": "Silla 0,45 x 0,45 m", "w": 0.45, "h": 0.45,
     "ops": [R(0, 0, 0.45, 0.45), L(0, 0.10, 0.45, 0.10)]},
    {"nombre": "A-SILLON", "cat": "Mobiliario",
     "desc": "Sillón 0,80 x 0,80 m", "w": 0.80, "h": 0.80,
     "ops": [R(0, 0, 0.80, 0.80), R(0.08, 0.08, 0.72, 0.62),
             L(0, 0.62, 0.80, 0.62)]},
    {"nombre": "A-SOFA-3", "cat": "Mobiliario",
     "desc": "Sofá 3 cuerpos 2,10 x 0,90 m", "w": 2.10, "h": 0.90,
     "ops": [R(0, 0, 2.10, 0.90), R(0, 0.62, 2.10, 0.90),
             R(0.10, 0.08, 0.72, 0.60), R(0.74, 0.08, 1.36, 0.60),
             R(1.38, 0.08, 2.00, 0.60)]},
    {"nombre": "A-MESA-RATONA", "cat": "Mobiliario",
     "desc": "Mesa ratona 0,90 x 0,90 m", "w": 0.90, "h": 0.90,
     "ops": [R(0, 0, 0.90, 0.90), R(0.10, 0.10, 0.80, 0.80)]},
    {"nombre": "A-ESCRITORIO", "cat": "Mobiliario",
     "desc": "Escritorio 1,40 x 0,70 m con silla", "w": 1.40, "h": 1.20,
     "ops": [R(0, 0, 1.40, 0.70), R(0.45, 0.75, 0.95, 1.20)]},
    {"nombre": "A-MODULO-TV", "cat": "Mobiliario",
     "desc": "Módulo de TV 1,80 x 0,45 m", "w": 1.80, "h": 0.45,
     "ops": [R(0, 0, 1.80, 0.45), L(0.60, 0, 0.60, 0.45),
             L(1.20, 0, 1.20, 0.45)]},
    {"nombre": "A-MESADA-300", "cat": "Mobiliario",
     "desc": "Mesada de cocina 3,00 x 0,60 m con pileta", "w": 3.00, "h": 0.60,
     "ops": [R(0, 0, 3.00, 0.60), R(1.10, 0.08, 1.90, 0.52),
             C(1.50, 0.30, 0.03)]},
    {"nombre": "A-COCINA-4H", "cat": "Mobiliario",
     "desc": "Anafe / cocina 4 hornallas 0,60 x 0,60 m", "w": 0.60, "h": 0.60,
     "ops": [R(0, 0, 0.60, 0.60), C(0.18, 0.42, 0.08), C(0.42, 0.42, 0.08),
             C(0.18, 0.18, 0.08), C(0.42, 0.18, 0.08)]},
    {"nombre": "A-HELADERA", "cat": "Mobiliario",
     "desc": "Heladera 0,70 x 0,70 m", "w": 0.70, "h": 0.70,
     "ops": [R(0, 0, 0.70, 0.70), L(0, 0, 0.70, 0.70), L(0, 0.70, 0.70, 0)]},
    {"nombre": "A-LAVARROPAS", "cat": "Mobiliario",
     "desc": "Lavarropas 0,60 x 0,60 m", "w": 0.60, "h": 0.60,
     "ops": [R(0, 0, 0.60, 0.60), C(0.30, 0.30, 0.20)]},
    {"nombre": "A-CAMPANA", "cat": "Mobiliario",
     "desc": "Campana de cocina 0,60 x 0,50 m", "w": 0.60, "h": 0.50,
     "ops": [R(0, 0, 0.60, 0.50), L(0.10, 0.10, 0.50, 0.40),
             L(0.10, 0.40, 0.50, 0.10)]},
]

# ------------------------------------------------ familia MODENA (por medida)
# Pares (ancho, alto) que usan los specs de Vivienda 02 + las 5 medidas
# adicionales de la carpinteria de catalogo.  Se generan dos bloques por ancho
# de fachada y uno por ancho de planta.
_MODENA_FACHADA = [
    (0.60, 1.20), (0.90, 1.40), (1.00, 1.40), (1.20, 1.40), (1.40, 1.40),
    (1.50, 1.40), (1.60, 1.40), (1.80, 1.50), (2.40, 1.60), (2.40, 1.70),
    (2.40, 2.10),
    (0.40, 0.60), (1.20, 0.60), (1.20, 1.20), (1.80, 2.00), (2.00, 2.00),
]

for _a, _h in dict.fromkeys(_MODENA_FACHADA):
    BLOQUES.append({
        "nombre": "A-MODENA-%03dx%03d" % (round(_a * 100), round(_h * 100)),
        "cat": "Aberturas",
        "desc": "Modena %.2f x %.2f m - aluminio A30 / DVH" % (_a, _h),
        "w": _a, "h": _h, "ops": modena(_a, _h)})

for _a in sorted({round(a, 2) for a, _ in _MODENA_FACHADA}):
    BLOQUES.append({
        "nombre": "A-MODENA-P-%03d" % round(_a * 100),
        "cat": "Aberturas",
        "desc": "Modena %.2f m - planta" % _a,
        "w": _a, "h": 0.20, "ops": modena_planta(_a)})

