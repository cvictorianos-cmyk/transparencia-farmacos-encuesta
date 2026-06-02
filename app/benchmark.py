"""Orquestador del flujo de benchmarking - persistencia incremental por clinica."""
from __future__ import annotations
import asyncio
import logging
from typing import Iterable

from . import database as db
from .config import DELAY_BETWEEN_CLINICS_S
from scrapers import CLINIC_SCRAPERS, ISPChileScraper

log = logging.getLogger("benchmark")


async def _scrape_clinic(clinic_key: str, queries: list[str]) -> list[dict]:
    ScraperCls = CLINIC_SCRAPERS[clinic_key]
    out: list[dict] = []
    log.info(f"[{clinic_key}] iniciando scraper para {len(queries)} marcas")
    try:
        async with ScraperCls() as scraper:
            for q in queries:
                try:
                    res = await asyncio.wait_for(scraper.search(q), timeout=60)
                    log.info(f"[{clinic_key}] '{q}' -> {len(res)} aranceles")
                    out.extend(res)
                except asyncio.TimeoutError:
                    log.warning(f"[{clinic_key}] timeout en '{q}'")
                except Exception as e:
                    log.exception(f"[{clinic_key}] error con '{q}': {e}")
    except Exception as e:
        log.exception(f"[{clinic_key}] error iniciando scraper: {e}")
    return out


async def ejecutar_benchmark(
    principio_activo: str,
    clinicas: Iterable[str] | None = None,
    marcas_extra: Iterable[str] | None = None,
) -> dict:
    benchmark_id = db.crear_benchmark(principio_activo)
    log.info(f"Benchmark id={benchmark_id} para '{principio_activo}'")

    log.info("Consultando ISP Chile...")
    isp = ISPChileScraper()
    productos = await isp.buscar_por_principio_activo(principio_activo)
    log.info(f"ISP devolvio {len(productos)} productos")
    if productos:
        db.guardar_productos_isp(benchmark_id, productos)

    marcas = ISPChileScraper.marcas_unicas(productos)
    if marcas_extra:
        for m in marcas_extra:
            mu = m.upper().strip()
            if mu and mu not in marcas:
                marcas.append(mu)
    log.info(f"Marcas a buscar en clinicas: {marcas}")

    selected = list(clinicas) if clinicas else list(CLINIC_SCRAPERS.keys())
    for ck in selected:
        if ck not in CLINIC_SCRAPERS:
            log.warning(f"Clinica desconocida: {ck}")
            continue
        ars = await _scrape_clinic(ck, marcas)
        if ars:
            db.guardar_aranceles(benchmark_id, ars)
            db.actualizar_totales(benchmark_id)
            log.info(f"[{ck}] persistidos {len(ars)} aranceles. Total acumulado actualizado.")
        await asyncio.sleep(DELAY_BETWEEN_CLINICS_S)

    db.actualizar_totales(benchmark_id)
    return db.obtener_benchmark(benchmark_id)
