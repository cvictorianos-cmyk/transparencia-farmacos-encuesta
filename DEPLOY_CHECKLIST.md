# 🚀 Deploy Checklist: Playwright en Render

## Estado actual
- ✅ Run lunes 2026-08-24: **56 precios capturados** (INDISA + UC)
- ✅ Correo enviado por SMTP
- ⏳ UANDES + SPA: pendiente de Playwright en Render

## Archivos nuevos (ya creados)
```
scripts/recolectar_navegador_full.py     ← Captura UANDES + SPA con Playwright
scripts/integrar_navegador.py            ← Mergea JSON con CSV histórico
requirements_render.txt                   ← Dependencias (con playwright)
Dockerfile.render                         ← Imagen Docker con Playwright
INSTRUCCIONES_RENDER.md                   ← Guía detallada
SETUP_RENDER.sh                           ← Script de verificación local
```

## Paso 1: Local (tu máquina)

### 1a. Verifica archivos
```bash
cd api_benchmarking_oncologico
bash SETUP_RENDER.sh
```

Debe salir: ✓ todos los archivos presentes

### 1b. Git: Commit y push
```bash
git add scripts/recolectar_navegador_full.py scripts/integrar_navegador.py
git add requirements_render.txt Dockerfile.render SETUP_RENDER.sh
git add INSTRUCCIONES_RENDER.md DEPLOY_CHECKLIST.md
git commit -m "feat: recolector Playwright para UANDES + clínicas SPA (2026-08-24)"
git push origin main
```

## Paso 2: Render.com (tu servicio)

### 2a. Detener servicio actual (opcional, pero recomendado)
- Dashboard → tu servicio → "Suspend"
- Esto evita que se reinicie mientras deployas

### 2b. Actualizar Build Command
1. Ve a: Settings → Build & Deploy
2. Build Command: reemplaza actual con:
   ```
   pip install -r requirements_render.txt && \
   python3 -m playwright install chromium --with-deps
   ```
3. **Save** (auto-redeploy comienza)

### 2c. Espera a que redeploy termine
- Mira los logs en "Recent Deploys"
- Debe terminar con "Build successful"
- Si hay error "playwright": verifica que `requirements_render.txt` esté en el repo root

### 2d. Resume el servicio (si lo suspendiste)
- Dashboard → tu servicio → "Resume"

## Paso 3: Agregar endpoint de recolección (en tu app/main.py)

Copia esto al final de tu FastAPI app:

```python
from fastapi import BackgroundTasks
import subprocess
from datetime import datetime

@app.post("/api/recolectar-navegador")
async def recolectar_navegador(background_tasks: BackgroundTasks):
    """
    Dispara recolección con Playwright (UANDES + SPA).
    Ejecuta en background, devuelve inmediatamente.
    """
    def run_recolector():
        try:
            print(f"[{datetime.now()}] Iniciando recolección Playwright", flush=True)
            
            # 1. Ejecuta recolector con Playwright
            result = subprocess.run(
                ["python3", "scripts/recolectar_navegador_full.py",
                 "--export-json", "/tmp/navegador_hoy.json"],
                capture_output=True,
                text=True,
                timeout=600  # 10 min max
            )
            
            print(result.stderr, flush=True)
            
            if result.returncode == 0:
                # 2. Integra con CSV histórico
                result2 = subprocess.run(
                    ["python3", "scripts/integrar_navegador.py",
                     "/tmp/navegador_hoy.json"],
                    capture_output=True,
                    text=True
                )
                print(result2.stderr, flush=True)
                print("[OK] Recolección + integración completada", flush=True)
            else:
                print(f"[ERROR] Recolector falló: {result.stderr}", flush=True)
        except Exception as e:
            print(f"[ERROR] Excepción: {e}", flush=True)
    
    # Ejecuta en background
    background_tasks.add_task(run_recolector)
    return {
        "status": "recolección iniciada (background)",
        "endpoint": "/api/recolectar-navegador",
        "tiempo_estimado": "5-10 minutos"
    }
```

Luego:
```bash
git add app/main.py
git commit -m "feat: endpoint /api/recolectar-navegador para Playwright"
git push
# Redeploy automático
```

## Paso 4: Configurar cron externo

### Opción A: cron-job.org (recomendado, gratuito)

1. Regístrate en https://cron-job.org
2. Dashboard → "Create Cronjob"
3. Configuración:
   - **Title**: "Recolector precios oncológicos"
   - **URL**: `https://tu-api-render.onrender.com/api/recolectar-navegador`
   - **Schedule**: Lunes 09:00 UTC
     - Minute: `0`
     - Hour: `9`
     - Day of week: `1` (lunes)
   - **Method**: `POST`
4. **Save**

### Opción B: EasyCron (alternativa)

1. Regístrate en https://www.easycron.com
2. "Add a new cron job"
3. URL: `https://tu-api-render.onrender.com/api/recolectar-navegador`
4. Method: POST
5. Schedule: Lunes 09:00

## Paso 5: Verificar

### 5a. Test manual (opcional)
```bash
curl -X POST https://tu-api-render.onrender.com/api/recolectar-navegador
# Respuesta: {"status": "recolección iniciada (background)"}
```

Espera 5-10 min y verifica:
```bash
tail -f ~/tu-proyecto/data/historial_precios.csv | grep "2026-08-24"
# Debe haber más filas (UANDES + SPA)
```

### 5b. Verificar logs en Render
- Dashboard → tu servicio → "Logs"
- Busca: `Recolección + integración completada`

## Paso 6: Monitoreo

Cada lunes 09:00 UTC, cron-job.org hará POST a tu API, que:
1. Lanza Playwright en background
2. Captura UANDES + SPA
3. Mergea con CSV histórico
4. Logs disponibles en Render

## Rollback (si falla algo)

Si la recolección Playwright falla:
1. Pausa el cron en cron-job.org
2. Sigue usando `reporte_lunes.py --no-collect` (los 56 precios HTTP siguen funcionando)
3. Revisa logs en Render → Settings → "View Build Logs"

## Resultado esperado (próximo lunes)

| Clínica | Método | Precios | Estado |
|---------|--------|---------|--------|
| INDISA | httpx | 26 | ✅ Existente |
| UC Marcoleta | httpx | 15 | ✅ Existente |
| UC San Carlos | httpx | 15 | ✅ Existente |
| UANDES | Playwright | 15-20 | ⏳ Nuevo |
| Dávila | Playwright | 0-5 | ⏳ Nuevo |
| Santa María | Playwright | 0-5 | ⏳ Nuevo |
| Alemana | Playwright | 0-5 | ⏳ Nuevo |
| **TOTAL** | — | **80-100+** | **📈 Completo** |

---

## ¿Ayuda?

- **Playwright en Render falla**: revisa Render logs, busca "ERROR"
- **Cron no dispara**: verifica en cron-job.org que la tarea esté activa
- **Precios no se actualizan**: revisa `/data/historial_precios.csv` último timestamp
- **Timeout**: aumenta `timeout=10000` a `timeout=20000` en recolectar_navegador_full.py

**Contacto**: Si necesitas soporte, revisa INSTRUCCIONES_RENDER.md o logs.
