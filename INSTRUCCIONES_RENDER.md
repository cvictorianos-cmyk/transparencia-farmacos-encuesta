# Despliegue de Recolector Completo (UANDES + SPA) en Render

## Problema
El sandbox local no puede ejecutar Playwright (requiere librerías del sistema). Solución: migrar recolector a **Render**, donde ya vive tu API y tiene Playwright disponible.

## Paso 1: Copiar scripts a tu repo (API en Render)

En tu carpeta local del proyecto, copia:
```
scripts/recolectar_navegador_full.py    (nuevo, usa Playwright)
scripts/integrar_navegador.py           (nuevo, merge JSON → CSV)
```

Commitea y push a GitHub/GitLab.

## Paso 2: Actualizar Dockerfile en Render

Tu Dockerfile actual probablemente no instala Playwright. Actualiza:

```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .

# Instala deps de Playwright
RUN apt-get update && apt-get install -y \
    libnss3 libnspr4 libgconf-2-4 libappindicator1 libpangcairo-1 \
    libgbm1 libasound2 libxss1 libxrender1 fonts-noto-color-emoji \
    xfonts-75dpi xfonts-100dpi xfonts-scalable xfonts-encodings \
    && rm -rf /var/lib/apt/lists/*

# Instala dependencias Python (incluir playwright)
RUN pip install -r requirements.txt

# Instala Chromium de Playwright
RUN python3 -m playwright install chromium --with-deps

COPY . .
EXPOSE 8000
CMD ["python", "app/main.py"]
```

**requirements.txt debe incluir:**
```
playwright>=1.40.0
```

## Paso 3: Crear tarea cron en Render

Render no tiene cron nativo, pero puedes usar un servicio externo (ej. EasyCron) o agregar un endpoint Flask/FastAPI que dispare la recolección:

### Opción A: Endpoint en tu API (recomendado)

Agrega a tu `app/main.py`:

```python
from fastapi import FastAPI, BackgroundTasks
import subprocess
import json
from datetime import date
from pathlib import Path

app = FastAPI()

@app.post("/api/recolectar-navegador")
async def recolectar_navegador(background_tasks: BackgroundTasks):
    """Dispara recolección con Playwright (UANDES + SPA)."""
    def run_recolector():
        try:
            # Ejecuta recolector con Playwright
            result = subprocess.run(
                ["python3", "scripts/recolectar_navegador_full.py", 
                 "--export-json", "/tmp/navegador_hoy.json"],
                capture_output=True, text=True, timeout=600
            )
            
            if result.returncode == 0:
                # Integra con CSV histórico
                subprocess.run(
                    ["python3", "scripts/integrar_navegador.py", 
                     "/tmp/navegador_hoy.json"],
                    capture_output=True, text=True
                )
                print("OK: Recolección navegador + integración completada")
            else:
                print(f"ERROR recolector: {result.stderr}")
        except Exception as e:
            print(f"ERROR: {e}")
    
    background_tasks.add_task(run_recolector)
    return {"status": "recolección iniciada (fondo)"}
```

Luego configura un cron externo (EasyCron, cron-job.org) que POST a:
```
https://tu-app-render.onrender.com/api/recolectar-navegador
```

### Opción B: Script directo (sin endpoint)

Crea `scripts/recolectar_semanal_completo.py`:

```python
#!/usr/bin/env python3
"""Ejecuta recolección HTTP + navegador completa."""
import subprocess
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

# 1. Ejecuta recolector original (INDISA + UC via httpx)
print("Paso 1: Recolección HTTP (INDISA + UC)...", flush=True)
result1 = subprocess.run(
    ["python3", "scripts/recolectar_diario.py"],
    capture_output=True, text=True
)
print(result1.stdout)
if result1.returncode != 0:
    print(f"Advertencia: {result1.stderr}", file=sys.stderr)

# 2. Ejecuta recolector Playwright (UANDES + SPA)
print("Paso 2: Recolección Navegador (UANDES + SPA)...", flush=True)
result2 = subprocess.run(
    ["python3", "scripts/recolectar_navegador_full.py",
     "--export-json", "/tmp/navegador_hoy.json"],
    capture_output=True, text=True, timeout=600
)
print(result2.stderr)

# 3. Integra resultado
if result2.returncode == 0:
    print("Paso 3: Integrando datos de navegador...", flush=True)
    result3 = subprocess.run(
        ["python3", "scripts/integrar_navegador.py", "/tmp/navegador_hoy.json"],
        capture_output=True, text=True
    )
    print(result3.stderr)

print("OK: Recolección semanal completa", flush=True)
```

Dale permisos y usa cron en Render (si tu plan lo permite):
```bash
chmod +x scripts/recolectar_semanal_completo.py
```

## Paso 4: Configurar cron con servicio externo

Usa **cron-job.org** o **EasyCron** (gratuito):

1. Regístrate en https://cron-job.org
2. Nueva tarea:
   - **URL**: https://tu-app-render.onrender.com/api/recolectar-navegador
   - **Frecuencia**: Lunes 09:00 UTC (o tu horario)
   - **Método**: POST

Verifica que la tarea corra exitosamente en el dashboard.

## Paso 5: Verificar salida

Después de que la tarea corra, verifica:
```bash
# En Render Shell o local
python3 -c "
import csv
from pathlib import Path
csv_path = Path('data/historial_precios.csv')
with csv_path.open() as f:
    rows = list(csv.DictReader(f))
    hoy = rows[-1]['fecha']
    hoy_rows = [r for r in rows if r['fecha'] == hoy]
    print(f'Filas de hoy ({hoy}): {len(hoy_rows)}')
    from collections import Counter
    print(Counter(r['clinica'] for r in hoy_rows))
"
```

## Rollback: Si algo falla

Si necesitas volver a solo HTTP (INDISA + UC):
- Comenta/desactiva la tarea cron
- Sigue usando `scripts/reporte_lunes.py --no-collect` con los 56 precios existentes

## Notas

- **Timeout Playwright**: el script recolectar_navegador_full.py tiene timeout de 10s/página. Si una clínica es muy lenta, aumenta el `timeout=10000` a `timeout=20000` en el código.
- **Headless mode**: Chrome se ejecuta sin interfaz gráfica (`headless=True`). Si hay problemas, agrega `--no-sandbox` a la launch.
- **Costos Render**: Playwright consume más CPU. Si estás en plan Free, monitorea el uso.

## Resumen

| Paso | Qué | Dónde |
|------|-----|-------|
| 1 | Copiar scripts | Tu repo GitHub |
| 2 | Actualizar Dockerfile | Render (auto-redeploy) |
| 3 | Agregar endpoint/cron script | `app/main.py` o nuevo script |
| 4 | Configurar cron externo | cron-job.org |
| 5 | Verificar| Render logs + CSV |

**Resultado final**: Captura completa de 7 clínicas (INDISA + UC x2 + UANDES + Dávila + Santa María + Alemana) cada lunes a las 09:00 UTC.
