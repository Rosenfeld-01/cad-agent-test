#!/usr/bin/env python3
"""
blocks_build.py — genera la biblioteca CAD_Blocks/ (Fase 1, Vivienda 02).

Los bloques se declaran como datos (lista de "ops") en los módulos
blocks_data_*.py y este archivo los convierte en DXF.

Convención de la biblioteca
---------------------------
- Un archivo por bloque: CAD_Blocks/<NOMBRE>.dxf
- Geometría en METROS 1:1 (igual que el resto del proyecto, $INSUNITS = 6).
- Punto de inserción = (0,0) = $INSBASE, con el bloque "mirando hacia arriba".
- Entidades en la capa 0: heredan color y espesor de la capa de inserción.
- La geometría se escribe en el MODEL SPACE (así la levanta el comando INSERT
  de CADCraft desde el archivo) y se replica en una definición de bloque con el
  mismo nombre (así también se puede insertar desde ezdxf/AutoCAD).

Escala de inserción en lámina: escala de la lámina / 1000 (1:50 -> 0,02).

Uso:
    python3 blocks_build.py            # escribe CAD_Blocks/ + index.json
"""
from __future__ import annotations

import json
import math
from pathlib import Path

import ezdxf
from ezdxf.enums import TextEntityAlignment

import blocks_data_arquitectura as DA
import blocks_data_bano_exterior as DB
import blocks_data_instalaciones as DI

BASE = Path(__file__).resolve().parent
DESTINO = BASE / "CAD_Blocks"

ALINEACION = {
    "mc": TextEntityAlignment.MIDDLE_CENTER,
    "ml": TextEntityAlignment.MIDDLE_LEFT,
    "mr": TextEntityAlignment.MIDDLE_RIGHT,
    "bc": TextEntityAlignment.BOTTOM_CENTER,
    "tl": TextEntityAlignment.TOP_LEFT,
    "tr": TextEntityAlignment.TOP_RIGHT,
}


def dibujar(contenedor, item: dict) -> None:
    """Dibuja las ops de un bloque en un layout (model space o definición)."""
    for op in item["ops"]:
        tipo = op[0]
        if tipo == "ln":
            contenedor.add_line(op[1], op[2])
        elif tipo == "pl":
            contenedor.add_lwpolyline(op[1], close=bool(op[2]) if len(op) > 2 else False)
        elif tipo == "ci":
            contenedor.add_circle(op[1], op[2])
        elif tipo == "ar":
            contenedor.add_arc(op[1], op[2], op[3], op[4])
        elif tipo == "tx":
            texto, punto, alto = op[1], op[2], op[3]
            alin = ALINEACION[op[4] if len(op) > 4 else "mc"]
            ent = contenedor.add_text(texto, height=alto)
            ent.set_placement(punto, align=alin)
        else:
            raise ValueError(f"op desconocida {tipo!r} en {item['nombre']}")
    for a in item.get("attrs", []):
        ad = contenedor.add_attdef(
            a["tag"], a["at"], dxfattribs={"height": a["h"], "prompt": a.get("prompt", a["tag"])})
        if a.get("default"):
            ad.dxf.text = a["default"]
        if a.get("invisible", True):
            ad.dxf.flags = 1


def crear_documento(item: dict) -> ezdxf.document.Drawing:
    doc = ezdxf.new("R2013", setup=True)
    doc.units = ezdxf.units.M
    doc.header["$INSUNITS"] = 6
    doc.header["$MEASUREMENT"] = 1
    doc.header["$INSBASE"] = (0.0, 0.0, 0.0)
    msp = doc.modelspace()
    dibujar(msp, item)
    blk = doc.blocks.new(item["nombre"])
    dibujar(blk, item)
    return doc


def validar(items: list[dict]) -> None:
    vistos = set()
    for it in items:
        n = it["nombre"]
        if n in vistos:
            raise ValueError(f"bloque repetido: {n}")
        vistos.add(n)
        if len(n) > 32:
            raise ValueError(f"nombre demasiado largo: {n}")
        for ch in n:
            if not (ch.isalnum() or ch in "-_"):
                raise ValueError(f"nombre con carácter inválido: {n}")
        if not it.get("ops"):
            raise ValueError(f"bloque sin geometría: {n}")
        for k in ("cat", "desc", "w", "h"):
            if k not in it:
                raise ValueError(f"{n}: falta la clave {k}")


def main() -> int:
    items = DA.BLOQUES + DB.BLOQUES + DI.BLOQUES
    validar(items)
    DESTINO.mkdir(parents=True, exist_ok=True)
    indice = []
    for it in sorted(items, key=lambda x: x["nombre"]):
        doc = crear_documento(it)
        ruta = DESTINO / f"{it['nombre']}.dxf"
        doc.saveas(ruta)
        indice.append({
            "bloque": it["nombre"],
            "archivo": ruta.name,
            "categoria": it["cat"],
            "descripcion": it["desc"],
            "ancho_m": it["w"],
            "alto_m": it["h"],
            "atributos": [a["tag"] for a in it.get("attrs", [])],
            "bytes": ruta.stat().st_size,
        })
    (DESTINO / "index.json").write_text(
        json.dumps({"unidad": "m", "insbase": [0, 0],
                    "escala_insercion": "escala_lámina/1000 (1:50 -> 0,02)",
                    "total": len(indice), "bloques": indice},
                   ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"OK  {len(indice)} bloques en {DESTINO}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
