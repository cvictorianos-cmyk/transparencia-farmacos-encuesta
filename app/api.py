"""Endpoints REST de la API de benchmarking."""
from __future__ import annotations
import csv
import hashlib
import io
import os
import secrets
from collections import Counter
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse, Response, StreamingResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials

from .benchmark import ejecutar_benchmark
from .config import BASE_DIR
from .models import BenchmarkRequest, BenchmarkSummary, EncuestaRespuesta
from . import database as db
from . import export as exporter
from . import catalogo as cat
from scrapers import CLINIC_SCRAPERS, ISPChileScraper

router = APIRouter()

# === Autenticacion Basic para descargas y reportes ===
# Credenciales configurables via variables de entorno (Render), con valores por defecto.
_security = HTTPBasic()
_EXPORT_USER = os.environ.get("EXPORT_USER", "cvictoriano")
_EXPORT_PASS = os.environ.get("EXPORT_PASS", "transparencia2026")


def requiere_credenciales(credentials: HTTPBasicCredentials = Depends(_security)) -> str:
    """Protege endpoints de descarga/reporte con usuario y contrasena (HTTP Basic).

    Usa secrets.compare_digest para evitar ataques de timing.
    El navegador muestra el dialogo nativo de login al acceder al enlace.
    """
    user_ok = secrets.compare_digest(credentials.username.encode(), _EXPORT_USER.encode())
    pass_ok = secrets.compare_digest(credentials.password.encode(), _EXPORT_PASS.encode())
    if not (user_ok and pass_ok):
        raise HTTPException(
            status_code=401,
            detail="Usuario o contrasena incorrectos",
            headers={"WWW-Authenticate": 'Basic realm="Descargas Transparencia Oncologica"'},
        )
    return credentials.username


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
    "/categorias",
    summary="Lista las categorias oncologicas con sus farmacos",
    tags=["comparador"],
)
async def get_categorias():
    cats = cat.listar_categorias()
    return {"total": len(cats), "categorias": cats}


@router.get(
    "/catalogo",
    summary="Lista los farmacos oncologicos (opcionalmente filtrados por categoria)",
    tags=["comparador"],
)
async def get_catalogo(categoria: str | None = None):
    casos = cat.listar_catalogo(categoria=categoria)
    return {"total": len(casos), "clinicas": cat.CLINICAS, "categoria": categoria, "casos": casos}


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
    "/dashboard",
    summary="Metricas agregadas para el panel Premium",
    tags=["comparador"],
)
async def get_dashboard(email: str | None = None,
                        clinicas: str | None = None, farmacos: str | None = None):
    cl = [x for x in clinicas.split(",") if x] if clinicas else None
    fa = [x for x in farmacos.split(",") if x] if farmacos else None
    data = cat.dashboard(clinicas_sel=cl, farmacos_sel=fa)
    alertas = db.listar_alertas(limit=1000)
    if email:
        alertas = [a for a in alertas if (a.get("email") or "").lower() == email.lower()]
    data["alertas_activas"] = alertas
    return data


@router.get(
    "/dashboard/historico",
    summary="Series historicas combinadas (filtros y rango de fechas) para el panel",
    tags=["comparador"],
)
async def get_dashboard_historico(clinicas: str | None = None, farmacos: str | None = None,
                                  desde: str | None = None, hasta: str | None = None):
    from . import historial as hist
    cl = [x for x in clinicas.split(",") if x] if clinicas else None
    fa = [x for x in farmacos.split(",") if x] if farmacos else None
    return hist.series_dashboard(farmacos=fa, clinicas=cl, desde=desde, hasta=hasta)


@router.get(
    "/dashboard/bajas",
    summary="Bajas de precio entre dos fechas configurables (Premium)",
    tags=["comparador"],
)
async def get_dashboard_bajas(desde: str | None = None, hasta: str | None = None,
                              clinicas: str | None = None, farmacos: str | None = None):
    from . import historial as hist
    cl = [x for x in clinicas.split(",") if x] if clinicas else None
    fa = [x for x in farmacos.split(",") if x] if farmacos else None
    return hist.bajas_precio(desde=desde, hasta=hasta, farmacos=fa, clinicas=cl)


@router.get(
    "/dashboard/export.csv",
    summary="Descarga el historico/snapshot de precios para analisis (ERP)",
    tags=["comparador"],
)
async def dashboard_export_csv(usuario: str = Depends(requiere_credenciales)):
    from . import historial as hist
    filas = hist.filas_export()  # serie historica completa (todas las fechas)
    buf = io.StringIO()
    cols = ["fecha", "categoria", "principio_activo", "marca", "presentacion",
            "clinica", "nombre_en_clinica", "empresa_isp", "tipo",
            "precio_particular_clp", "moneda", "origen", "fuente"]
    w = csv.DictWriter(buf, fieldnames=cols)
    w.writeheader()
    for f in filas:
        w.writerow(f)
    # BOM utf-8 para que Excel muestre bien los acentos (Pulmón, Riñón, etc.)
    contenido = "﻿" + buf.getvalue()
    return StreamingResponse(
        iter([contenido]), media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": "attachment; filename=transparencia_precios.csv"},
    )


@router.get(
    "/dashboard/reporte.pdf",
    summary="Reporte ejecutivo del panel en PDF (Premium)",
    tags=["comparador"],
)
async def dashboard_reporte_pdf(usuario: str = Depends(requiere_credenciales)):
    from . import reporte
    pdf_bytes = reporte.generar_reporte_pdf(cat.dashboard())
    return Response(
        content=pdf_bytes, media_type="application/pdf",
        headers={"Content-Disposition": "attachment; filename=reporte_transparencia_oncologica.pdf"},
    )


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
    "/cotizar/{principio_activo}",
    summary="Cotiza el costo total de un tratamiento por clinica",
    tags=["cotizador"],
)
async def get_cotizar(principio_activo: str, dosis_mg: float, veces: int,
                      cobertura_pct: float = 0.0):
    data = cat.cotizar(principio_activo, dosis_mg, veces, cobertura_pct)
    if not data:
        raise HTTPException(404, f"No se pudo cotizar '{principio_activo}'")
    return data


@router.post(
    "/cotizacion/enviar",
    summary="Cotiza y envia la cotizacion por email (version gratuita)",
    tags=["cotizador"],
)
async def post_cotizacion_enviar(request: Request):
    from . import mailer
    body = await request.json()
    email = (body.get("email") or "").strip()
    nombre = (body.get("nombre") or "").strip()
    apellido = (body.get("apellido") or "").strip()
    pa = (body.get("principio_activo") or "").strip()
    if not email or "@" not in email:
        raise HTTPException(400, "Email valido requerido")
    if not nombre or not apellido:
        raise HTTPException(400, "Nombre y apellido requeridos")
    try:
        dosis = float(body.get("dosis_mg"))
        veces = int(body.get("veces"))
        cobertura = float(body.get("cobertura_pct") or 0)
    except (TypeError, ValueError):
        raise HTTPException(400, "Dosis y numero de administraciones requeridos")

    cot = cat.cotizar(pa, dosis, veces, cobertura)
    if not cot:
        raise HTTPException(404, f"No se pudo cotizar '{pa}'")

    enviado = mailer.enviar_cotizacion(email, nombre, cot)
    mejor = cot["opcion_mas_barata"]
    db.guardar_cotizacion_lead({
        "nombre": nombre, "apellido": apellido, "email": email,
        "principio_activo": pa, "dosis_mg": dosis, "veces": veces,
        "cobertura_pct": cobertura, "mejor_clinica": mejor["clinica"],
        "mejor_total_clp": mejor["costo_total_clp"], "enviado_email": enviado,
    })
    return {"ok": True, "enviado_email": enviado, "cotizacion": cot}


@router.get(
    "/cotizaciones",
    summary="Lista los leads de cotizacion (gratuita)",
    tags=["cotizador"],
)
async def get_cotizaciones(limit: int = 1000):
    return {"cotizaciones": db.listar_cotizaciones_lead(limit=limit)}


@router.post(
    "/alertas",
    summary="Registra una alerta de baja de precio (Premium)",
    tags=["cotizador"],
)
async def post_alerta(request: Request):
    body = await request.json()
    email = (body.get("email") or "").strip()
    pa = (body.get("principio_activo") or "").strip()
    if not email or "@" not in email or not pa:
        raise HTTPException(400, "Se requiere email valido y principio activo")
    alerta_id = db.guardar_alerta(body)
    return {"ok": True, "id": alerta_id,
            "mensaje": "Alerta registrada: te avisaremos por email si baja el precio."}


@router.get(
    "/alertas",
    summary="Lista las alertas de precio activas",
    tags=["cotizador"],
)
async def get_alertas(limit: int = 1000):
    return {"alertas": db.listar_alertas(limit=limit)}


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
async def export_resultado(benchmark_id: int, fmt: str,
                           usuario: str = Depends(requiere_credenciales)):
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
async def encuestas_export_csv(usuario: str = Depends(requiere_credenciales)):
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
