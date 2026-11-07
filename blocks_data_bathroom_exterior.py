"""
blocks_data_bathroom_exterior.py — bathroom fixtures and exterior equipment.

Same criteria as blocks_data_architecture: 1:1 meters, base (0,0) lower-left,
block facing up (+Y).
"""
from __future__ import annotations

from blocks_data_architecture import A, C, L, R, T

BLOCKS = [
    # --------------------------------------------------------------- bathroom
    {"name": "A-INODORO", "category": "Bathroom",
     "description": "Toilet 0.40 x 0.70 m (low tank)", "w": 0.40, "h": 0.70,
     "ops": [R(0.02, 0, 0.38, 0.18),                     # tank
             C(0.20, 0.44, 0.20),                        # bowl
             C(0.20, 0.44, 0.15)]},
    {"name": "A-LAVATORIO", "category": "Bathroom",
     "description": "Washbasin 0.60 x 0.45 m on counter", "w": 0.60, "h": 0.45,
     "ops": [R(0, 0, 0.60, 0.45), C(0.30, 0.24, 0.16), C(0.30, 0.05, 0.02)]},
    {"name": "A-BIDET", "category": "Bathroom",
     "description": "Bidet 0.40 x 0.60 m", "w": 0.40, "h": 0.60,
     "ops": [R(0.04, 0.08, 0.36, 0.52), C(0.20, 0.42, 0.13),
             R(0.04, 0, 0.36, 0.08)]},
    {"name": "A-DUCHA-090", "category": "Bathroom",
     "description": "Shower 0.90 x 0.90 m with drain and curb",
     "w": 0.90, "h": 0.90,
     "ops": [R(0, 0, 0.90, 0.90), C(0.45, 0.45, 0.30),
             C(0.45, 0.45, 0.06), L(0, 0.90, 0.08, 0.82),
             L(0.90, 0.90, 0.82, 0.82)]},
    {"name": "A-BANERA-170", "category": "Bathroom",
     "description": "Bathtub 1.70 x 0.70 m", "w": 1.70, "h": 0.70,
     "ops": [R(0, 0, 1.70, 0.70), R(0.06, 0.06, 1.64, 0.64),
             C(1.58, 0.35, 0.04)]},
    {"name": "A-PILETA-LAVAR", "category": "Bathroom",
     "description": "Laundry sink 0.60 x 0.60 m with counter", "w": 0.60, "h": 0.60,
     "ops": [R(0, 0, 0.60, 0.60), R(0.08, 0.08, 0.52, 0.52), C(0.30, 0.30, 0.03)]},

    # --------------------------------------------------------------- exterior
    {"name": "A-ESCALERA-16", "category": "Stairs",
     "description": "16-riser stair: 2 flights of 8 + 1.10 landing",
     "w": 2.20, "h": 4.20,
     "ops": [R(0, 0, 1.10, 2.24), L(0, 0.28, 1.10, 0.28), L(0, 0.56, 1.10, 0.56),
             L(0, 0.84, 1.10, 0.84), L(0, 1.12, 1.10, 1.12),
             L(0, 1.40, 1.10, 1.40), L(0, 1.68, 1.10, 1.68),
             L(0, 1.96, 1.10, 1.96),
             R(1.10, 2.24, 2.20, 2.90),                  # landing
             R(1.10, 0, 2.20, 2.24), L(1.10, 0.28, 2.20, 0.28),
             L(1.10, 0.56, 2.20, 0.56), L(1.10, 0.84, 2.20, 0.84),
             L(1.10, 1.12, 2.20, 1.12), L(1.10, 1.40, 2.20, 1.40),
             L(1.10, 1.68, 2.20, 1.68), L(1.10, 1.96, 2.20, 1.96),
             L(0.55, 2.95, 0.55, 3.45), L(0.55, 3.45, 0.55, 3.90),
             ("tx", "16 RISERS 0.181 - TREAD 0.28", (0.55, 4.10), 0.13, "mc")]},
    {"name": "A-ARBOL-A", "category": "Exterior",
     "description": "Tree, 2.00 m crown (evergreen)", "w": 2.00, "h": 2.00,
     "ops": [C(0, 0, 1.00), C(0, 0, 0.72), C(0, 0, 0.06)]},
    {"name": "A-ARBOL-B", "category": "Exterior",
     "description": "Tree, 1.20 m crown (deciduous)", "w": 1.20, "h": 1.20,
     "ops": [C(0, 0, 0.60), C(0, 0, 0.42), C(0, 0, 0.05)]},
    {"name": "A-AUTO", "category": "Exterior",
     "description": "Car 1.80 x 4.40 m (space check)",
     "w": 1.80, "h": 4.40,
     "ops": [R(0, 0, 1.80, 4.40), R(0.10, 0.30, 1.70, 1.10),
             R(0.10, 1.30, 1.70, 3.10), R(0.10, 3.30, 1.70, 4.20)]},
    {"name": "A-GRILL", "category": "Exterior",
     "description": "Grill 0.90 x 0.60 m", "w": 0.90, "h": 0.60,
     "ops": [R(0, 0, 0.90, 0.60), L(0.10, 0.10, 0.80, 0.50),
             L(0.10, 0.50, 0.80, 0.10)]},
    {"name": "A-TANQUE-1000", "category": "Exterior",
     "description": "1,000 L water tank on structure (1.10 x 1.10 m)",
     "w": 1.10, "h": 1.10,
     "ops": [R(0, 0, 1.10, 1.10), C(0.55, 0.55, 0.45),
             L(0, 0, 1.10, 1.10), L(0, 1.10, 1.10, 0)]},
    {"name": "A-PLANTIN", "category": "Exterior",
     "description": "Entrance planter 1.20 x 0.30 m", "w": 1.20, "h": 0.30,
     "ops": [R(0, 0, 1.20, 0.30), L(0, 0.15, 1.20, 0.15)]},
]
