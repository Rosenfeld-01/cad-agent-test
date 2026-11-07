#!/usr/bin/env python3
"""Fixture de los gates: un A2 con defectos a propósito.

    python3 tools/mk_dxf_roto.py
    python3 tools/qa_laminas.py   tools/_roto.dxf   # 1 solape + 1 fuera
    python3 tools/qa_geometria.py tools/_roto.dxf   # 1 coincidente + 1 bloque

Ambos tienen que salir con código 1.  Si devuelven 0, el gate está roto
(ver PLAYBOOK §6.1).
"""
import sys
from pathlib import Path

import ezdxf

DESTINO = Path(__file__).with_name("_roto.dxf")


def main() -> int:
    doc = ezdxf.new()
    doc.units = 6                                # metros
    msp = doc.modelspace()

    # 1) dos textos en el mismo punto → solape de texto
    msp.add_text("HOLA MUNDO", dxfattribs={"height": 0.003, "insert": (0.10, 0.10)})
    msp.add_text("CHOCA", dxfattribs={"height": 0.003, "insert": (0.10, 0.10)})

    # 2) línea que se sale de la hoja A2 (0,594 × 0,420) → fuera de hoja
    msp.add_line((0.0, 0.10), (0.80, 0.10))

    # 3) la misma línea dibujada dos veces → trazo coincidente
    msp.add_line((0.10, 0.30), (0.20, 0.30))
    msp.add_line((0.10, 0.30), (0.20, 0.30))

    # 4) dos bloques que se pisan (no contenidos) → bloque superpuesto
    for nombre in ("BLOQUE_A", "BLOQUE_B"):
        blk = doc.blocks.new(name=nombre)
        blk.add_lwpolyline([(0, 0), (0.05, 0), (0.05, 0.05), (0, 0.05)])
    msp.add_blockref("BLOQUE_A", (0.30, 0.30))
    msp.add_blockref("BLOQUE_B", (0.32, 0.32))

    doc.saveas(DESTINO)
    print(f"escrito {DESTINO}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
