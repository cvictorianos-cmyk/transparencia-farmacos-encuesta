"""Entrypoint de la API FastAPI."""
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api import router
from .database import init_db

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

app = FastAPI(
    title="API Benchmarking Fármacos Oncológicos",
    version="0.1.0",
    description=(
        "Automatiza el benchmarking de precios de fármacos oncológicos en clínicas "
        "privadas de Chile, partiendo del Registro Sanitario del ISP."
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


app.include_router(router)


@app.get("/")
async def root():
    return {
        "name": "API Benchmarking Fármacos Oncológicos",
        "version": "0.1.0",
        "docs": "/docs",
        "health": "/health",
    }
