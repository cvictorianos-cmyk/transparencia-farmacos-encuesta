#!/bin/bash
# Script de setup: prepara el proyecto para deploy en Render con Playwright
set -e

echo "=== Setup Render con Playwright ==="

# 1. Verificar archivos nuevos
echo "✓ Verificando scripts nuevos..."
test -f scripts/recolectar_navegador_full.py || echo "ERROR: falta recolectar_navegador_full.py"
test -f scripts/integrar_navegador.py || echo "ERROR: falta integrar_navegador.py"

# 2. Verificar Dockerfile.render
echo "✓ Verificando Dockerfile.render..."
test -f Dockerfile.render || echo "ERROR: falta Dockerfile.render"

# 3. Verificar requirements_render.txt
echo "✓ Verificando requirements_render.txt..."
test -f requirements_render.txt || echo "ERROR: falta requirements_render.txt"

# 4. Verificar guía
echo "✓ Verificando INSTRUCCIONES_RENDER.md..."
test -f INSTRUCCIONES_RENDER.md || echo "ERROR: falta INSTRUCCIONES_RENDER.md"

echo ""
echo "=== Próximos pasos ==="
echo ""
echo "1. Git: commit y push"
echo "   git add scripts/recolectar_navegador_full.py scripts/integrar_navegador.py"
echo "   git add requirements_render.txt Dockerfile.render SETUP_RENDER.sh INSTRUCCIONES_RENDER.md"
echo "   git commit -m 'feat: recolector Playwright para UANDES + clínicas SPA'"
echo "   git push"
echo ""
echo "2. Render: actualizar configuración"
echo "   - En Render.com, ve a tu servicio"
echo "   - Environment: agrega PLAYWRIGHT_INSTALL=1"
echo "   - Build command: pip install -r requirements_render.txt && python3 -m playwright install chromium --with-deps"
echo "   - Redeploy"
echo ""
echo "3. Cron externo: configura en cron-job.org o EasyCron"
echo "   - URL: https://tu-api-render.onrender.com/api/recolectar-navegador"
echo "   - Lunes 09:00 UTC"
echo ""
echo "=== Documentación ==="
echo "Lee INSTRUCCIONES_RENDER.md para instrucciones detalladas"
echo ""
