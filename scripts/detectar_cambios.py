# -*- coding: utf-8 -*-
"""Detecta cambios de precio entre las dos capturas mas recientes del historial.

Compara la ultima fecha registrada en data/historial_precios.csv contra la
fecha inmediatamente anterior, por cada par (clinica, glosa). Reporta CUALQUIER
variacion de precio (umbral configurado por el usuario) y las ofertas nuevas.

Salida: imprime un reporte en Markdown a stdout (vacio si no hay cambios), apto
para usarse como cuerpo de un GitHub Issue. No modifica nada.

Uso:  python scripts/detectar_cambios.py > cambios.md
"""
from __future__ import annotations

import csv
import sys
from pathlib import Path

CSV_PATH = Path(__file__).resolve().parent.parent / "data" / "historial_precios.csv"


def clp(n: int) -> str:
    """Formatea entero como CLP con separador de miles chileno (punto)."""
    return f"{n:,}".replace(",", ".")


def main() -> int:
    if not CSV_PATH.exists():
        return 0
    rows = list(csv.DictReader(CSV_PATH.open(encoding="utf-8")))
    if not rows:
        return 0

    fechas = sorted({r["fecha"] for r in rows})
    if len(fechas) < 2:
        return 0  # no hay captura previa con que comparar
    prev, hoy = fechas[-2], fechas[-1]

    def indexar(f: str) -> dict:
        d = {}
        for r in rows:
            if r["fecha"] != f:
                continue
            try:
                precio = int(float(r["precio_clp"]))
            except (ValueError, TypeError):
                continue
            d[(r["clinica"], r["glosa"])] = (precio, r["principio_activo"])
        return d

    ant, act = indexar(prev), indexar(hoy)

    cambios = []   # (clinica, pa, glosa, antes, ahora, delta, pct)
    for k, (p_new, pa) in act.items():
        if k in ant:
            p_old = ant[k][0]
            if p_new != p_old and p_old > 0:
                delta = p_new - p_old
                pct = delta / p_old * 100
                cambios.append((k[0], pa, k[1], p_old, p_new, delta, pct))

    nuevos = [(k[0], v[1], k[1], v[0]) for k, v in act.items() if k not in ant]

    if not cambios and not nuevos:
        return 0  # sin novedades: stdout vacio -> no se abre issue

    out = sys.stdout
    out.write(f"## Cambios de precio detectados: {prev} -> {hoy}\n\n")
    out.write(
        f"Comparacion automatica de las dos capturas mas recientes del "
        f"historial de la API. Umbral: **cualquier variacion**.\n\n"
    )

    if cambios:
        out.write(f"### {len(cambios)} precios cambiaron\n\n")
        out.write("| Clinica | Farmaco | Glosa | Antes (CLP) | Ahora (CLP) | Variacion | Var % |\n")
        out.write("|---|---|---|---:|---:|---:|---:|\n")
        for cl, pa, g, po, pn, d, pc in sorted(cambios, key=lambda x: -abs(x[6])):
            flecha = "subio" if d > 0 else "bajo"
            out.write(
                f"| {cl} | {pa} | {g} | {clp(po)} | {clp(pn)} | "
                f"{flecha} {clp(abs(d))} | {pc:+.1f}% |\n"
            )
        out.write("\n")

    if nuevos:
        out.write(f"### {len(nuevos)} ofertas nuevas (no estaban en la captura anterior)\n\n")
        out.write("| Clinica | Farmaco | Glosa | Precio (CLP) |\n")
        out.write("|---|---|---|---:|\n")
        for cl, pa, g, p in nuevos[:60]:
            out.write(f"| {cl} | {pa} | {g} | {clp(p)} |\n")
        out.write("\n")

    out.write(
        f"\n_Generado automaticamente por el recolector semanal "
        f"(scripts/detectar_cambios.py)._\n"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
