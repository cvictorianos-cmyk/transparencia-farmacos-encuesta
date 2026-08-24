"""Entrypoint minimalista de la API FastAPI."""
import subprocess
from datetime import datetime
from fastapi import FastAPI, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="API Benchmarking Fármacos Oncológicos",
    version="0.2.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
async def health():
    return {"status": "ok"}

@app.get("/info")
async def info():
    return {
        "name": "API Benchmarking Fármacos Oncológicos",
        "version": "0.2.0",
    }

@app.post("/api/recolectar-navegador")
async def recolectar_navegador(background_tasks: BackgroundTasks):
    """Dispara recolección con Playwright (UANDES + SPA) en background."""
    def run_recolector():
        try:
            print(f"[{datetime.now()}] Iniciando Playwright recolector", flush=True)

            result = subprocess.run(
                ["python3", "scripts/recolectar_navegador_full.py",
                 "--export-json", "/tmp/navegador_hoy.json"],
                capture_output=True,
                text=True,
                timeout=600
            )

            if result.returncode == 0:
                print("[OK] Playwright completó, integrando con CSV", flush=True)
                subprocess.run(
                    ["python3", "scripts/integrar_navegador.py",
                     "/tmp/navegador_hoy.json"],
                    capture_output=True,
                    text=True
                )
                print("[OK] Recolección completada", flush=True)
            else:
                print(f"[ERROR] {result.stderr}", flush=True)
        except Exception as e:
            print(f"[ERROR] {e}", flush=True)

    background_tasks.add_task(run_recolector)
    return {"status": "recolección iniciada"}
