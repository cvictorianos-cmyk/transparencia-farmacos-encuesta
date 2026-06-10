"""Endpoints REST de la API de benchmarking."""
from __future__ import annotations
import csv
import hashlib
import io
from collections import Counter
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse, StreamingResponse

from .benchmark import ejecutar_benchmark
from .config import BASE_DIR
from .models import BenchmarkRequest, BenchmarkSummary, EncuestaRespuesta
from . import database as db
from . import export as exporter
from . import catalogo as cat
from scrapers import CLINIC_SCRAPERS, ISPChileScraper

router = APIRouter()

_ENCUESTA_HTML = BASE_DIR / "app" / "static" / "encuesta.html"
_COMPARADOR_HTML = BASE_DIR / "app" / "static" / "comparador.html"


@router.get("/health")
async def health():
    return {"status": "ok"}


@router.get("/clinicas", summary="Lista las clínicas soportadas")
async def list_clinicas():
    return {"clinicas": list(CLINIC_SCRAPERS.keys())}


# === Comparador / catalogo precargado (10 casos oncologicos) ===

@router.get(
    "/comparador",
    response_class=HTMLResponse,
    summary="Comparador web responsivo de precios (movil y escritorio)",
    tags=["comparador"],
)
async def comparador_ui():
    if not _COMPARADOR_HTML.exists():
        raise HTTPException(500, "Comparador no encontrado")
    return HTMLResponse(_COMPARADOR_HTML.read_text(encoding="utf-8"))


@router.get(
    "/catalogo",
    summary="Lista los 10 casos de farmacos oncologicos disponibles",
    tags=["comparador"],
)
async def get_catalogo():
    casos = cat.listar_catalogo()
    return {"total": len(casos), "clinicas": cat.CLINICAS, "casos": casos}


@router.get(
    "/comparar/{principio_activo}",
    summary="Compara los precios de un farmaco entre las 5 clinicas",
    tags=["comparador"],
)
async def get_comparar(principio_activo: str, marca: str | None = None):
    data = cat.comparar(principio_activo, marca=marca)
    if not data:
        raise HTTPException(404, f"No hay datos para '{principio_activo}'")
    return data


@router.get(
    "/historial/{principio_activo}",
    summary="Serie temporal de precios por clinica (linea de tiempo Premium)",
    tags=["comparador"],
)
async def get_historial(principio_activo: str):
    from . import historial as hist
    data = hist.serie_historica(principio_activo)
    if not data:
        raise HTTPException(404, f"No hay historial para '{principio_activo}'")
    return data


@router.get(
    "/bioequivalentes/{principio_activo}",
    summary="Lista productos del ISP para un principio activo (sin guardar)",
)
async def get_bioequivalentes(principio_activo: str):
    isp = ISPChileScraper()
    productos = await isp.buscar_por_principio_activo(principio_activo)
    return {
        "principio_activo": principio_activo,
        "total": len(productos),
        "marcas_unicas": ISPChileScraper.marcas_unicas(productos),
        "productos": productos,
    }


@router.post(
    "/benchmark/{principio_activo}",
    summary="Ejecuta el benchmark completo (ISP + 5 clínicas) y guarda en SQLite",
)
async def post_benchmark(principio_activo: str, body: BenchmarkRequest | None = None):
    body = body or BenchmarkRequest(principio_activo=principio_activo)
    res = await ejecutar_benchmark(
        principio_activo=principio_activo,
        clinicas=body.clinicas,
        marcas_extra=body.incluir_marcas_extra,
    )
    return _resumen(res)


@router.get(
    "/benchmarks",
    summary="Lista los benchmarks ejecutados",
)
async def list_benchmarks(limit: int = 50):
    return {"benchmarks": db.listar_benchmarks(limit=limit)}


@router.get(
    "/resultados/{benchmark_id}",
    summary="Obtiene los datos completos de un benchmark",
)
async def get_resultados(benchmark_id: int):
    data = db.obtener_benchmark(benchmark_id)
    if not data:
        raise HTTPException(404, f"Benchmark {benchmark_id} no encontrado")
    return data


@router.get(
    "/resultados/{benchmark_id}/resumen",
    summary="Resumen ejecutivo del benchmark",
)
async def get_resumen(benchmark_id: int):
    data = db.obtener_benchmark(benchmark_id)
    if not data:
        raise HTTPException(404, f"Benchmark {benchmark_id} no encontrado")
    return _resumen(data)


@router.get(
    "/resultados/{benchmark_id}/export.{fmt}",
    summary="Exporta el benchmark a json | csv | xlsx",
)
async def export_resultado(benchmark_id: int, fmt: str):
    try:
        path = exporter.export_benchmark(benchmark_id, fmt=fmt)
    except ValueError as e:
        raise HTTPException(400, str(e))
    return FileResponse(path, filename=path.name)


# === Encuesta / censo de validacion (QR del AFE) ===

@router.get(
    "/encuesta",
    response_class=HTMLResponse,
    summary="Formulario de la encuesta (destino del QR del AFE)",
    tags=["encuesta"],
)
async def encuesta_form():
    if not _ENCUESTA_HTML.exists():
        raise HTTPException(500, "Formulario de encuesta no encontrado")
    return HTMLResponse(_ENCUESTA_HTML.read_text(encoding="utf-8"))


@router.post(
    "/encuesta",
    summary="Guarda una respuesta de la encuesta",
    tags=["encuesta"],
)
async def encuesta_submit(respuesta: EncuestaRespuesta, request: Request):
    data = respuesta.model_dump()
    data["user_agent"] = request.headers.get("user-agent")
    ip = request.client.host if request.client else None
    data["ip_hash"] = hashlib.sha256(ip.encode()).hexdigest()[:16] if ip else None
    encuesta_id = db.guardar_encuesta(data)
    return {"status": "ok", "id": encuesta_id}


@router.get(
    "/encuestas",
    summary="Lista las respuestas de la encuesta (censo)",
    tags=["encuesta"],
)
async def encuestas_list(limit: int = 1000):
    return {"total": db.contar_encuestas(), "encuestas": db.listar_encuestas(limit=limit)}


@router.get(
    "/encuestas/export.csv",
    summary="Exporta todas las respuestas de la encuesta a CSV",
    tags=["encuesta"],
)
async def encuestas_export_csv():
    filas = db.listar_encuestas(limit=100000)
    buf = io.StringIO()
    if filas:
        writer = csv.DictWriter(buf, fieldnames=list(filas[0].keys()))
        writer.writeheader()
        writer.writerows(filas)
    else:
        buf.write("sin_respuestas\n")
    buf.seek(0)
    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=encuestas_censo.csv"},
    )


def _resumen(data: dict) -> dict:
    aranceles = data.get("aranceles", [])
    productos = data.get("productos_isp", [])
    counts = Counter(a["clinica"] for a in aranceles)
    return {
        "benchmark_id": data["benchmark"]["id"],
        "principio_activo": data["benchmark"]["principio_activo"],
        "fecha_ejecucion": data["benchmark"]["fecha_ejecucion"],
        "total_productos_isp": len(productos),
        "marcas_unicas": sorted({(p.get("nombre_marca") or "").upper() for p in productos if p.get("nombre_marca")}),
        "total_aranceles": len(aranceles),
        "aranceles_por_clinica": dict(counts),
        "precio_min_por_marca_clinica": _matriz_min(aranceles),
    }


def _matriz_min(aranceles: list[dict]) -> dict:
    """Construye matriz {marca: {clinica: precio_min_particular}}."""
    out: dict[str, dict[str, int]] = {}
    for a in aranceles:
        marca = (a.get("query_busqueda") or "").upper()
        clinica = a.get("clinica")
        precio = a.get("precio_particular_clp")
        if not marca or not clinica or precio is None:
            continue
        d = out.setdefault(marca, {})
        if clinica not in d or precio < d[clinica]:
            d[clinica] = precio
    return out
