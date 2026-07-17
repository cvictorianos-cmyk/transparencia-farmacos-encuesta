"""Entrypoint de la API FastAPI."""
import hashlib
import logging
import os
import secrets
from datetime import datetime, timezone

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response

from .api import router
from .database import init_db

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

app = FastAPI(
    title="API Benchmarking Fármacos Oncológicos",
    version="0.2.0",
    description=(
        "Automatiza el benchmarking de precios de fármacos oncológicos en clínicas "
        "privadas de Chile, partiendo del Registro Sanitario del ISP. Incluye un "
        "comparador web responsivo con 10 casos precargados."
    ),
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def _startup():
    init_db()


# === Registro de visitas (metricas de trafico para el AFE) ===
# Guarda cada GET relevante en SQLite (tabla visitas). Consultar en /metricas
# (protegido con las credenciales de descargas). IP anonimizada via hash.
_RUTAS_SIN_REGISTRO = ("/health", "/metricas", "/favicon", "/docs", "/openapi", "/redoc")


@app.middleware("http")
async def registrar_visitas(request: Request, call_next):
    response = await call_next(request)
    try:
        ruta = request.url.path
        if request.method == "GET" and not ruta.startswith(_RUTAS_SIN_REGISTRO):
            from . import database as db
            ip = request.client.host if request.client else None
            db.registrar_visita({
                "fecha": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                "ruta": ruta,
                "status": response.status_code,
                "user_agent": (request.headers.get("user-agent") or "")[:200],
                "referer": (request.headers.get("referer") or "")[:200],
                "ip_hash": hashlib.sha256(ip.encode()).hexdigest()[:16] if ip else None,
            })
    except Exception:
        pass  # el registro jamas debe romper una request
    return response


# === Autenticacion ===
# El acceso inicial al sitio es publico (el HTTP Basic global fue retirado
# de forma definitiva para la presentacion del 13-jul-2026).
#
# MODO_DEMO controla el login de la version Premium:
#   - "1" (por defecto): Premium se activa SIN usuario ni contraseña (demo).
#   - "0": /premium/login vuelve a exigir credenciales (AUTH_USER / AUTH_PASS).
# Para reactivar el login Premium despues de la defensa: cambiar el valor por
# defecto a "0" aqui, o definir MODO_DEMO=0 como variable de entorno en Render.
MODO_DEMO = os.environ.get("MODO_DEMO", "1") != "0"

# Credenciales del login Premium, configurables via variables de entorno en Render.
AUTH_USER = os.environ.get("AUTH_USER", "carlos")
AUTH_PASS = os.environ.get("AUTH_PASS", "Transparencia2026")


# Login de la version Premium del comparador.
@app.post("/premium/login")
async def premium_login(request: Request):
    if MODO_DEMO:
        return {"ok": True, "plan": "premium", "demo": True}
    try:
        body = await request.json()
    except Exception:
        body = {}
    user = str(body.get("usuario", ""))
    pwd = str(body.get("contrasena", ""))
    if secrets.compare_digest(user, AUTH_USER) and secrets.compare_digest(pwd, AUTH_PASS):
        return {"ok": True, "plan": "premium"}
    return Response(status_code=401, content='{"ok": false}', media_type="application/json")


app.include_router(router)


@app.get("/")
async def root():
    return {
        "name": "API Benchmarking Fármacos Oncológicos",
        "version": "0.2.0",
        "comparador": "/comparador",
        "catalogo": "/catalogo",
        "encuesta": "/encuesta",
        "docs": "/docs",
        "health": "/health",
    }
