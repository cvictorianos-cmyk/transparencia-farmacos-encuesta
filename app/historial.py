"""Series temporales de precios para la linea de tiempo (version Premium).

Combina dos fuentes:
  1. LINEA BASE SINTETICA: se asume que cada oferta mantuvo su precio actual
     desde el 1 de enero de 2026 (puntos quincenales). Marcada fuente="base".
  2. REGISTRO REAL DIARIO: filas de data/historial_precios.csv generadas por
     scripts/recolectar_diario.py (GitHub Actions, diario). A medida que se
     acumulan dias, la serie real reemplaza/extiende la base. fuente="real".

El match entre el CSV y las ofertas del catalogo se hace por codigo interno
UC (FOxxxx/FXxxxx) cuando existe, o por glosa normalizada en caso contrario.
"""
from __future__ import annotations

import csv
import re
from datetime import date, timedelta
from pathlib import Path

from .catalogo import CATALOGO, _slug

BASE_DIR = Path(__file__).resolve().parent.parent
CSV_PATH = BASE_DIR / "data" / "historial_precios.csv"

INICIO_BASE = date(2026, 1, 1)
PASO_BASE_DIAS = 15  # puntos quincenales para la linea base


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").strip().upper())


def _codigo(glosa: str) -> str | None:
    m = re.search(r"\((F[OX]\d+)\)", glosa or "", re.I)
    return m.group(1).upper() if m else None


def _leer_csv() -> list[dict]:
    if not CSV_PATH.exists():
        return []
    with CSV_PATH.open(encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def _match(fila_csv: dict, oferta: dict, pa: str) -> bool:
    if _slug(fila_csv.get("principio_activo", "")) != pa:
        return False
    if _norm(fila_csv.get("clinica", "")) != _norm(oferta["clinica"]):
        return False
    cod_csv = _codigo(fila_csv.get("glosa", ""))
    cod_cat = _codigo(oferta["glosa"])
    if cod_cat and cod_csv:
        return cod_cat == cod_csv
    return _norm(fila_csv.get("glosa", "")) == _norm(oferta["glosa"])


def serie_historica(principio_activo: str) -> dict | None:
    """Series de precio por oferta (clinica+glosa) para un principio activo."""
    pa = _slug(principio_activo)
    casos = [c for c in CATALOGO if _slug(c["principio_activo"]) == pa]
    if not casos:
        return None

    filas_csv = _leer_csv()
    hoy = date.today()
    presentaciones = []

    for c in casos:
        series = []
        for o in c["ofertas"]:
            reales = sorted(
                (
                    (r["fecha"], int(r["precio_clp"]))
                    for r in filas_csv
                    if _match(r, o, pa) and r.get("fecha") and r.get("precio_clp")
                ),
                key=lambda t: t[0],
            )
            primera_real = (
                date.fromisoformat(reales[0][0]) if reales else hoy + timedelta(days=1)
            )
            # base sintetica: precio actual plano desde el 1-ene-2026 hasta
            # el dia anterior al primer dato real
            puntos = []
            d = INICIO_BASE
            while d < primera_real and d <= hoy:
                puntos.append({"fecha": d.isoformat(), "precio_clp": o["precio"], "fuente": "base"})
                d += timedelta(days=PASO_BASE_DIAS)
            ultimo_base = min(primera_real - timedelta(days=1), hoy)
            if puntos and puntos[-1]["fecha"] != ultimo_base.isoformat() and ultimo_base >= INICIO_BASE:
                puntos.append({"fecha": ultimo_base.isoformat(), "precio_clp": o["precio"], "fuente": "base"})
            for f, p in reales:
                puntos.append({"fecha": f, "precio_clp": p, "fuente": "real"})

            precios = [pt["precio_clp"] for pt in puntos]
            actual = precios[-1] if precios else o["precio"]
            corte_30 = (hoy - timedelta(days=30)).isoformat()
            previos_30 = [pt["precio_clp"] for pt in puntos if pt["fecha"] <= corte_30]
            base_30 = previos_30[-1] if previos_30 else (precios[0] if precios else actual)
            series.append({
                "clinica": o["clinica"],
                "glosa": o["glosa"],
                "bioequivalente": o["bioequivalente"],
                "precio_actual_clp": actual,
                "min_historico_clp": min(precios) if precios else actual,
                "max_historico_clp": max(precios) if precios else actual,
                "var_30d_pct": round((actual - base_30) / base_30 * 100, 1) if base_30 else 0.0,
                "en_minimo_historico": bool(precios) and actual == min(precios),
                "n_dias_reales": len(reales),
                "puntos": puntos,
            })
        presentaciones.append({
            "marca": c["marca"],
            "presentacion": c["presentacion"],
            "series": series,
        })

    total_reales = sum(s["n_dias_reales"] for p in presentaciones for s in p["series"])
    return {
        "principio_activo": pa,
        "desde": INICIO_BASE.isoformat(),
        "hasta": hoy.isoformat(),
        "presentaciones": presentaciones,
        "nota": (
            "Linea base referencial: se asume precio constante desde enero 2026 "
            "(igual al ultimo precio publicado). Los puntos fuente='real' provienen "
            "del registro diario automatico de los aranceles publicos de cada clinica."
            + (" Aun sin dias reales registrados." if total_reales == 0 else "")
        ),
    }


def series_dashboard(farmacos: list[str] | None = None,
                     clinicas: list[str] | None = None,
                     desde: str | None = None, hasta: str | None = None) -> dict:
    """Series historicas combinadas (1 linea por farmaco+clinica) para el panel.

    Filtra por farmacos, clinicas y rango de fechas [desde, hasta] (YYYY-MM-DD).
    """
    fa = {f.strip().lower() for f in farmacos} if farmacos else None
    cl = {c.strip().lower() for c in clinicas} if clinicas else None
    d0 = desde or INICIO_BASE.isoformat()
    d1 = hasta or date.today().isoformat()

    pas = sorted({c["principio_activo"] for c in CATALOGO})
    if fa:
        pas = [p for p in pas if p.lower() in fa]

    lineas = []
    for pa in pas:
        s = serie_historica(pa)
        if not s:
            continue
        for pres in s["presentaciones"]:
            for serie in pres["series"]:
                if cl and serie["clinica"].lower() not in cl:
                    continue
                puntos = [pt for pt in serie["puntos"] if d0 <= pt["fecha"] <= d1]
                if not puntos:
                    continue
                lineas.append({
                    "label": pa.capitalize() + " · " + serie["clinica"]
                             + (" (bioeq.)" if serie["bioequivalente"] else ""),
                    "principio_activo": pa,
                    "clinica": serie["clinica"],
                    "bioequivalente": serie["bioequivalente"],
                    "puntos": puntos,
                })
    return {
        "desde": d0, "hasta": d1,
        "n_lineas": len(lineas),
        "lineas": lineas,
    }
