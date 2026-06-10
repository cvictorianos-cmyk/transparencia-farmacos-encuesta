"""Entrypoint de la API FastAPI."""
import base64
import logging
import os
import secrets

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


# === Proteccion con usuario y contraseña (HTTP Basic) durante el desarrollo ===
# Credenciales configurables via variables de entorno en Render (AUTH_USER / AUTH_PASS).
AUTH_USER = os.environ.get("AUTH_USER", "carlos")
AUTH_PASS = os.environ.get("AUTH_PASS", "Transparencia2026")

# Rutas publicas: /health (healthcheck de Render) y /encuesta (QR del censo del AFE).
_RUTAS_PUBLICAS = ("/health", "/encuesta")


@app.middleware("http")
async def basic_auth_middleware(request: Request, call_next):
    path = request.url.path
    if any(path == r or path.startswith(r + "/") for r in _RUTAS_PUBLICAS):
        return await call_next(request)
    auth = request.headers.get("authorization", "")
    if auth.lower().startswith("basic "):
        try:
            decoded = base64.b64decode(auth.split(" ", 1)[1]).decode("utf-8")
            user, _, pwd = decoded.partition(":")
            if secrets.compare_digest(user, AUTH_USER) and secrets.compare_digest(pwd, AUTH_PASS):
                return await call_next(request)
        except Exception:
            pass
    return Response(
        status_code=401,
        headers={"WWW-Authenticate": 'Basic realm="TransparenciaRx (acceso restringido)"'},
        content="Acceso restringido: ingresa usuario y contrasena.",
    )


# Login de la version Premium del comparador (mismas credenciales por ahora).
@app.post("/premium/login")
async def premium_login(request: Request):
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
