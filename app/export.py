"""Exportación de resultados a JSON / CSV / Excel."""
from __future__ import annotations
import json
from pathlib import Path

import pandas as pd

from . import database as db
from .config import EXPORTS_DIR


def export_benchmark(benchmark_id: int, fmt: str = "json") -> Path:
    """Exporta un benchmark a formato {json, csv, xlsx}. Devuelve path al archivo."""
    fmt = fmt.lower()
    data = db.obtener_benchmark(benchmark_id)
    if not data:
        raise ValueError(f"Benchmark {benchmark_id} no existe")

    base = EXPORTS_DIR / f"benchmark_{benchmark_id}_{data['benchmark']['principio_activo']}"

    if fmt == "json":
        path = base.with_suffix(".json")
        path.write_text(
            json.dumps(data, indent=2, ensure_ascii=False, default=str),
            encoding="utf-8",
        )
        return path

    df_aranceles = pd.DataFrame(data["aranceles"])
    df_productos = pd.DataFrame(data["productos_isp"])

    if fmt == "csv":
        path = base.with_suffix(".csv")
        df_aranceles.to_csv(path, index=False, encoding="utf-8-sig")
        return path

    if fmt in ("xlsx", "excel"):
        path = base.with_suffix(".xlsx")
        with pd.ExcelWriter(path, engine="openpyxl") as writer:
            df_meta = pd.DataFrame([data["benchmark"]])
            df_meta.to_excel(writer, sheet_name="benchmark", index=False)
            if not df_productos.empty:
                df_productos.to_excel(writer, sheet_name="productos_isp", index=False)
            if not df_aranceles.empty:
                df_aranceles.to_excel(writer, sheet_name="aranceles", index=False)
                # Tabla pivote de comparación clínica × marca
                if "query_busqueda" in df_aranceles.columns and "precio_particular_clp" in df_aranceles.columns:
                    pivot = df_aranceles.pivot_table(
                        index="query_busqueda",
                        columns="clinica",
                        values="precio_particular_clp",
                        aggfunc="min",
                    )
                    pivot.to_excel(writer, sheet_name="comparativa_min")
        return path

    raise ValueError(f"Formato no soportado: {fmt}. Usa json|csv|xlsx.")
