"""
blocks_data_architecture.py — openings and furniture for the CAD_Blocks library.

Architecture blocks, in 1:1 meters, with the insertion point (0,0) at the door
hinge or the lower-left corner of the furniture, and the block "facing up" (+Y).
"""
from __future__ import annotations


def R(x0, y0, x1, y1):
    """Closed rectangle."""
    return ("pl", [(x0, y0), (x1, y0), (x1, y1), (x0, y1)], True)


def L(x1, y1, x2, y2):
    return ("ln", (x1, y1), (x2, y2))


def C(x, y, r):
    return ("ci", (x, y), r)


def A(x, y, r, a1, a2):
    return ("ar", (x, y), r, a1, a2)


def T(txt, x, y, h, al="mc"):
    return ("tx", txt, (x, y), h, al)


def door(width: float, leaves: int = 1) -> list:
    """Open leaf/leaves at 90 degrees + swing arc. Hinge at (0,0)."""
    ops = []
    w = width / leaves
    for i in range(leaves):
        x0 = i * w
        # open leaf (perpendicular to the wall), 0.04 thick
        ops.append(R(x0, 0.0, x0 + 0.04, w))
        ops.append(A(x0, 0.0, w, 0, 90))
    # frame stops
    ops.append(L(0, -0.02, 0, 0.02))
    ops.append(L(width, -0.02, width, 0.02))
    return ops


def window(width: float, thickness: float = 0.15) -> list:
    """Casement window: 3 glass lines + jambs."""
    m = thickness / 2
    return [
        L(0, m, width, m),
        L(0, 0, width, 0),
        L(0, -m, width, -m),
        L(0, -m, 0, m),
        L(width, -m, width, m),
    ]


def modena(width: float, height: float) -> list:
    """Facade Modena (A30 aluminum, DVH): frame + mullion + transom.

    Block facing up, lower-left corner at (0,0).
    """
    m = 0.05
    return [
        R(0, 0, width, height),                       # outer frame
        R(m, m, width - m, height - m),               # inner frame (leaf)
        L(width / 2.0, m, width / 2.0, height - m),   # center mullion
        L(m, height * 0.72, width - m, height * 0.72),  # upper transom
    ]


def modena_plan(width: float, thickness: float = 0.20) -> list:
    """Modena in plan: 3 glass lines + stops, centered at (0,0)."""
    h = width / 2.0
    m = thickness / 2.0
    g = thickness / 6.0
    return [
        L(-h, g, h, g),
        L(-h, 0, h, 0),
        L(-h, -g, h, -g),
        L(-h, -m, -h, m),
        L(h, -m, h, m),
    ]


BLOCKS = [
    # --------------------------------------------------------------- openings
    {"name": "A-PUERTA-070", "category": "Openings",
     "description": "0.70 m door (closet / type IV bathroom)", "w": 0.70, "h": 0.70,
     "ops": door(0.70)},
    {"name": "A-PUERTA-080", "category": "Openings",
     "description": "0.80 m interior door (type II bathroom minimum clear passage)",
     "w": 0.80, "h": 0.80, "ops": door(0.80)},
    {"name": "A-PUERTA-090", "category": "Openings",
     "description": "0.90 m entrance door", "w": 0.90, "h": 0.90, "ops": door(0.90)},
    {"name": "A-PUERTA-DOBLE-160", "category": "Openings",
     "description": "Double door, 2 x 0.80 m", "w": 1.60, "h": 1.60,
     "ops": door(1.60, leaves=2)},
    {"name": "A-PANEL-050", "category": "Openings",
     "description": "0.50 m closet panel / leaf", "w": 0.50, "h": 0.50,
     "ops": door(0.50)},
    {"name": "A-VENTANA-090", "category": "Openings",
     "description": "0.90 m window (bathroom / powder room)", "w": 0.90, "h": 0.15,
     "ops": window(0.90)},
    {"name": "A-VENTANA-120", "category": "Openings",
     "description": "1.20 m window", "w": 1.20, "h": 0.15, "ops": window(1.20)},
    {"name": "A-VENTANA-150", "category": "Openings",
     "description": "1.50 m window", "w": 1.50, "h": 0.15, "ops": window(1.50)},
    {"name": "A-VENTANA-180", "category": "Openings",
     "description": "1.80 m window", "w": 1.80, "h": 0.15, "ops": window(1.80)},
    {"name": "A-VENTANA-240", "category": "Openings",
     "description": "2.40 m window (living / suite)", "w": 2.40, "h": 0.15,
     "ops": window(2.40)},
    {"name": "A-PUERTA-BALCON-160", "category": "Openings",
     "description": "Balcony door, 2 leaves, 1.60 m (to terrace)", "w": 1.60, "h": 1.60,
     "ops": door(1.60, leaves=2)},
    {"name": "A-PORTON-300", "category": "Openings",
     "description": "3.00 m sliding gate (vehicle access)", "w": 3.00, "h": 0.20,
     "ops": [R(0, -0.05, 1.50, 0.05), R(1.50, -0.05, 3.00, 0.05),
             L(0.20, 0.10, 2.80, 0.10),
             T("SLIDING", 1.50, 0.22, 0.12)]},

    # -------------------------------------------------------------- furniture
    {"name": "A-CAMA-1PL", "category": "Furniture",
     "description": "Single bed 0.90 x 1.90 m (CABA dimensions, block B)",
     "w": 0.90, "h": 1.90,
     "ops": [R(0, 0, 0.90, 1.90), R(0.08, 1.50, 0.82, 1.82),
             L(0, 1.45, 0.90, 1.45)]},
    {"name": "A-CAMA-2PL", "category": "Furniture",
     "description": "Double bed 1.40 x 1.90 m", "w": 1.40, "h": 1.90,
     "ops": [R(0, 0, 1.40, 1.90), R(0.08, 1.50, 0.68, 1.82),
             R(0.72, 1.50, 1.32, 1.82), L(0, 1.45, 1.40, 1.45)]},
    {"name": "A-PLACARD-210", "category": "Furniture",
     "description": "Wardrobe 2.10 x 0.60 m (0.60 m practice depth)",
     "w": 2.10, "h": 0.60,
     "ops": [R(0, 0, 2.10, 0.60), L(0, 0.55, 2.10, 0.55),
             L(0.70, 0, 0.70, 0.55), L(1.40, 0, 1.40, 0.55)]},
    {"name": "A-MESA-6", "category": "Furniture",
     "description": "Dining table for 6, 1.60 x 0.90 m", "w": 1.60, "h": 0.90,
     "ops": [R(0, 0, 1.60, 0.90), R(0.06, 0.06, 0.34, 0.84),
             R(1.26, 0.06, 1.54, 0.84)]},
    {"name": "A-SILLA", "category": "Furniture",
     "description": "Chair 0.45 x 0.45 m", "w": 0.45, "h": 0.45,
     "ops": [R(0, 0, 0.45, 0.45), L(0, 0.10, 0.45, 0.10)]},
    {"name": "A-SILLON", "category": "Furniture",
     "description": "Armchair 0.80 x 0.80 m", "w": 0.80, "h": 0.80,
     "ops": [R(0, 0, 0.80, 0.80), R(0.08, 0.08, 0.72, 0.62),
             L(0, 0.62, 0.80, 0.62)]},
    {"name": "A-SOFA-3", "category": "Furniture",
     "description": "3-seat sofa 2.10 x 0.90 m", "w": 2.10, "h": 0.90,
     "ops": [R(0, 0, 2.10, 0.90), R(0, 0.62, 2.10, 0.90),
             R(0.10, 0.08, 0.72, 0.60), R(0.74, 0.08, 1.36, 0.60),
             R(1.38, 0.08, 2.00, 0.60)]},
    {"name": "A-MESA-RATONA", "category": "Furniture",
     "description": "Coffee table 0.90 x 0.90 m", "w": 0.90, "h": 0.90,
     "ops": [R(0, 0, 0.90, 0.90), R(0.10, 0.10, 0.80, 0.80)]},
    {"name": "A-ESCRITORIO", "category": "Furniture",
     "description": "Desk 1.40 x 0.70 m with chair", "w": 1.40, "h": 1.20,
     "ops": [R(0, 0, 1.40, 0.70), R(0.45, 0.75, 0.95, 1.20)]},
    {"name": "A-MODULO-TV", "category": "Furniture",
     "description": "TV unit 1.80 x 0.45 m", "w": 1.80, "h": 0.45,
     "ops": [R(0, 0, 1.80, 0.45), L(0.60, 0, 0.60, 0.45),
             L(1.20, 0, 1.20, 0.45)]},
    {"name": "A-MESADA-300", "category": "Furniture",
     "description": "Kitchen counter 3.00 x 0.60 m with sink", "w": 3.00, "h": 0.60,
     "ops": [R(0, 0, 3.00, 0.60), R(1.10, 0.08, 1.90, 0.52),
             C(1.50, 0.30, 0.03)]},
    {"name": "A-COCINA-4H", "category": "Furniture",
     "description": "4-burner cooktop 0.60 x 0.60 m", "w": 0.60, "h": 0.60,
     "ops": [R(0, 0, 0.60, 0.60), C(0.18, 0.42, 0.08), C(0.42, 0.42, 0.08),
             C(0.18, 0.18, 0.08), C(0.42, 0.18, 0.08)]},
    {"name": "A-HELADERA", "category": "Furniture",
     "description": "Refrigerator 0.70 x 0.70 m", "w": 0.70, "h": 0.70,
     "ops": [R(0, 0, 0.70, 0.70), L(0, 0, 0.70, 0.70), L(0, 0.70, 0.70, 0)]},
    {"name": "A-LAVARROPAS", "category": "Furniture",
     "description": "Washing machine 0.60 x 0.60 m", "w": 0.60, "h": 0.60,
     "ops": [R(0, 0, 0.60, 0.60), C(0.30, 0.30, 0.20)]},
    {"name": "A-CAMPANA", "category": "Furniture",
     "description": "Kitchen hood 0.60 x 0.50 m", "w": 0.60, "h": 0.50,
     "ops": [R(0, 0, 0.60, 0.50), L(0.10, 0.10, 0.50, 0.40),
             L(0.10, 0.40, 0.50, 0.10)]},
]

# --------------------------------------------------- MODENA family (by size)
# (width, height) pairs used by the seed specs + the 5 extra catalog
# carpentry sizes. Two blocks are generated per facade width and one per plan
# width.
_MODENA_FACADE = [
    (0.60, 1.20), (0.90, 1.40), (1.00, 1.40), (1.20, 1.40), (1.40, 1.40),
    (1.50, 1.40), (1.60, 1.40), (1.80, 1.50), (2.40, 1.60), (2.40, 1.70),
    (2.40, 2.10),
    (0.40, 0.60), (1.20, 0.60), (1.20, 1.20), (1.80, 2.00), (2.00, 2.00),
]

for _a, _h in dict.fromkeys(_MODENA_FACADE):
    BLOCKS.append({
        "name": "A-MODENA-%03dx%03d" % (round(_a * 100), round(_h * 100)),
        "category": "Openings",
        "description": "Modena %.2f x %.2f m - A30 aluminum / DVH" % (_a, _h),
        "w": _a, "h": _h, "ops": modena(_a, _h)})

for _a in sorted({round(a, 2) for a, _ in _MODENA_FACADE}):
    BLOCKS.append({
        "name": "A-MODENA-P-%03d" % round(_a * 100),
        "category": "Openings",
        "description": "Modena %.2f m - plan" % _a,
        "w": _a, "h": 0.20, "ops": modena_plan(_a)})
