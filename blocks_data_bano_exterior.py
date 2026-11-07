"""
blocks_data_bano_exterior.py — artefactos de baño y equipamiento exterior.

Mismos criterios que blocks_data_arquitectura: metros 1:1, base (0,0) abajo a
la izquierda, bloque mirando hacia arriba (+Y).
"""
from __future__ import annotations

from blocks_data_arquitectura import A, C, L, R, T

BLOQUES = [
    # ------------------------------------------------------------------ baño
    {"nombre": "A-INODORO", "cat": "Baño",
     "desc": "Inodoro 0,40 x 0,70 m (tanque bajo)", "w": 0.40, "h": 0.70,
     "ops": [R(0.02, 0, 0.38, 0.18),                     # tanque
             C(0.20, 0.44, 0.20),                        # cubeta
             C(0.20, 0.44, 0.15)]},
    {"nombre": "A-LAVATORIO", "cat": "Baño",
     "desc": "Lavatorio 0,60 x 0,45 m sobre mesada", "w": 0.60, "h": 0.45,
     "ops": [R(0, 0, 0.60, 0.45), C(0.30, 0.24, 0.16), C(0.30, 0.05, 0.02)]},
    {"nombre": "A-BIDET", "cat": "Baño",
     "desc": "Bidet 0,40 x 0,60 m", "w": 0.40, "h": 0.60,
     "ops": [R(0.04, 0.08, 0.36, 0.52), C(0.20, 0.42, 0.13),
             R(0.04, 0, 0.36, 0.08)]},
    {"nombre": "A-DUCHA-090", "cat": "Baño",
     "desc": "Ducha 0,90 x 0,90 m con desagüe y zócalo",
     "w": 0.90, "h": 0.90,
     "ops": [R(0, 0, 0.90, 0.90), C(0.45, 0.45, 0.30),
             C(0.45, 0.45, 0.06), L(0, 0.90, 0.08, 0.82),
             L(0.90, 0.90, 0.82, 0.82)]},
    {"nombre": "A-BANERA-170", "cat": "Baño",
     "desc": "Bañera 1,70 x 0,70 m", "w": 1.70, "h": 0.70,
     "ops": [R(0, 0, 1.70, 0.70), R(0.06, 0.06, 1.64, 0.64),
             C(1.58, 0.35, 0.04)]},
    {"nombre": "A-PILETA-LAVAR", "cat": "Baño",
     "desc": "Pileta de lavar 0,60 x 0,60 m con mesada", "w": 0.60, "h": 0.60,
     "ops": [R(0, 0, 0.60, 0.60), R(0.08, 0.08, 0.52, 0.52), C(0.30, 0.30, 0.03)]},

    # -------------------------------------------------------------- exterior
    {"nombre": "A-ESCALERA-16", "cat": "Escalera",
     "desc": "Escalera de 16 alzadas: 2 tramos de 8 + descanso 1,10",
     "w": 2.20, "h": 4.20,
     "ops": [R(0, 0, 1.10, 2.24), L(0, 0.28, 1.10, 0.28), L(0, 0.56, 1.10, 0.56),
             L(0, 0.84, 1.10, 0.84), L(0, 1.12, 1.10, 1.12),
             L(0, 1.40, 1.10, 1.40), L(0, 1.68, 1.10, 1.68),
             L(0, 1.96, 1.10, 1.96),
             R(1.10, 2.24, 2.20, 2.90),                  # descanso
             R(1.10, 0, 2.20, 2.24), L(1.10, 0.28, 2.20, 0.28),
             L(1.10, 0.56, 2.20, 0.56), L(1.10, 0.84, 2.20, 0.84),
             L(1.10, 1.12, 2.20, 1.12), L(1.10, 1.40, 2.20, 1.40),
             L(1.10, 1.68, 2.20, 1.68), L(1.10, 1.96, 2.20, 1.96),
             L(0.55, 2.95, 0.55, 3.45), L(0.55, 3.45, 0.55, 3.90),
             ("tx", "16 ALZ. 0,181 - PIE 0,28", (0.55, 4.10), 0.13, "mc")]},
    {"nombre": "A-ARBOL-A", "cat": "Exterior",
     "desc": "Árbol copa 2,00 m (follaje perenne)", "w": 2.00, "h": 2.00,
     "ops": [C(0, 0, 1.00), C(0, 0, 0.72), C(0, 0, 0.06)]},
    {"nombre": "A-ARBOL-B", "cat": "Exterior",
     "desc": "Árbol copa 1,20 m (follaje caduco)", "w": 1.20, "h": 1.20,
     "ops": [C(0, 0, 0.60), C(0, 0, 0.42), C(0, 0, 0.05)]},
    {"nombre": "A-AUTO", "cat": "Exterior",
     "desc": "Automóvil 1,80 x 4,40 m (verificación de espacio)",
     "w": 1.80, "h": 4.40,
     "ops": [R(0, 0, 1.80, 4.40), R(0.10, 0.30, 1.70, 1.10),
             R(0.10, 1.30, 1.70, 3.10), R(0.10, 3.30, 1.70, 4.20)]},
    {"nombre": "A-GRILL", "cat": "Exterior",
     "desc": "Parrilla / grill 0,90 x 0,60 m", "w": 0.90, "h": 0.60,
     "ops": [R(0, 0, 0.90, 0.60), L(0.10, 0.10, 0.80, 0.50),
             L(0.10, 0.50, 0.80, 0.10)]},
    {"nombre": "A-TANQUE-1000", "cat": "Exterior",
     "desc": "Tanque de agua 1.000 l sobre estructura (1,10 x 1,10 m)",
     "w": 1.10, "h": 1.10,
     "ops": [R(0, 0, 1.10, 1.10), C(0.55, 0.55, 0.45),
             L(0, 0, 1.10, 1.10), L(0, 1.10, 1.10, 0)]},
    {"nombre": "A-PLANTIN", "cat": "Exterior",
     "desc": "Plantín de acceso 1,20 x 0,30 m", "w": 1.20, "h": 0.30,
     "ops": [R(0, 0, 1.20, 0.30), L(0, 0.15, 1.20, 0.15)]},
]
