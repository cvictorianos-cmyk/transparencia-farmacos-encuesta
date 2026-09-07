# -*- coding: utf-8 -*-
"""Reporte semanal (lunes) de la actualizacion de precios oncologicos.

Orquesta el pipeline de actualizacion de precios y produce un correo de estado
para transparenciaoncologica@gmail.com respondiendo tres preguntas:

  1. Salio bien la actualizacion?  (exit code + total de precios capturados)
  2. Falto algun dato?            (clinicas esperadas sin filas hoy + errores)
  3. Cambio alguna descripcion o precio? (variaciones vs. la captura anterior)

Flujo:
  a) Ejecuta scripts/recolectar_diario.py (salvo --no-collect).
  b) Ejecuta scripts/detectar_cambios.py y captura su reporte Markdown.
  c) Lee data/historial_precios.csv y arma el resumen por clinica.
  d) Envia el correo por SMTP si hay credenciales; si no, escribe el cuerpo a
     un archivo para que se envie como borrador de Gmail.

Envio SMTP: usa variables de entorno (SMTP_HOST, SMTP_USER, SMTP_PASS,
SMTP_PORT, SMTP_FROM, SMTP_SSL). Tambien las lee de un archivo local opcional
'.smtp_env' en la raiz del proyecto (formato KEY=VALOR, una por linea), que NO
se versiona. Asi el envio automatico funciona sin exponer la contrasena.

Uso:
  python scripts/reporte_lunes.py                # recolecta + detecta + envia
  python scripts/reporte_lunes.py --no-collect   # NO recolecta (solo analiza)
  python scripts/reporte_lunes.py --no-send      # no envia; solo escribe cuerpo

Codigos de salida: 0 = OK (con o sin cambios); 1 = la recoleccion fallo.
"""
from __future__ import annotations

import csv
import os
import smtplib
import ssl
import subprocess
import sys
from datetime import date
from email.mime.text import MIMEText
from email.utils import formataddr
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = BASE_DIR / "scripts"
CSV_PATH = BASE_DIR / "data" / "historial_precios.csv"
SMTP_ENV_FILE = BASE_DIR / ".smtp_env"
OUT_BODY = BASE_DIR / "exports" / "reporte_lunes_ultimo.md"

DESTINATARIO = "transparenciaoncologica@gmail.com"

# Fuentes que el recolector deberia devolver (para detectar "falto un dato").
CLINICAS_ESPERADAS = [
    "Clinica INDISA",
    "Clinica Universidad de los Andes",
    "UC Marcoleta",
    "UC San Carlos",
    # Clinicas SPA via navegador (pueden faltar si Playwright no esta instalado):
    "Clinica Davila",
    "Clinica Santa Maria",
    "Clinica Alemana",
]
# httpx desatendido SOLO funciona en estas 3 (INDISA GraphQL + UC API).
# UANDES (DataDome 403), Davila/Santa Maria (Azure WAF) y Alemana (DataDome)
# requieren navegador; ver [[project_uandes_403_navegador]]. Opcion 2 (hibrido):
# el cron captura las HTTP y las 4 por-navegador se refrescan asistido.
CLINICAS_HTTP = ["Clinica INDISA", "UC Marcoleta", "UC San Carlos"]
CLINICAS_NAVEGADOR = ["Clinica Universidad de los Andes", "Clinica Davila",
                      "Clinica Santa Maria", "Clinica Alemana"]


CLINICA_DISPLAY = {
    "Clinica INDISA": "Clínica INDISA",
    "Clinica Universidad de los Andes": "Clínica Universidad de los Andes",
    "Clinica Davila": "Clínica Dávila",
    "Clinica Santa Maria": "Clínica Santa María",
    "Clinica Alemana": "Clínica Alemana",
}


def _disp(c: str) -> str:
    """Etiqueta con acentos para mostrar; NO cambia la clave usada para cruzar datos."""
    return CLINICA_DISPLAY.get(c, c)


def _clp(n) -> str:
    try:
        return "$" + f"{int(n):,}".replace(",", ".")
    except Exception:
        return str(n)


def _cargar_smtp_env() -> None:
    """Carga variables SMTP desde .smtp_env si existen y no estan ya en el env."""
    if not SMTP_ENV_FILE.exists():
        return
    try:
        for linea in SMTP_ENV_FILE.read_text(encoding="utf-8").splitlines():
            linea = linea.strip()
            if not linea or linea.startswith("#") or "=" not in linea:
                continue
            k, v = linea.split("=", 1)
            k, v = k.strip(), v.strip().strip('"').strip("'")
            if k and k not in os.environ:
                os.environ[k] = v
    except Exception as e:
        print(f"AVISO: no se pudo leer .smtp_env ({e})", file=sys.stderr)


def _smtp_configurado() -> bool:
    return bool(os.environ.get("SMTP_HOST") and os.environ.get("SMTP_USER")
                and os.environ.get("SMTP_PASS"))


def _run(script: str) -> tuple[int, str, str]:
    """Ejecuta un script del proyecto y devuelve (returncode, stdout, stderr)."""
    proc = subprocess.run(
        [sys.executable, str(SCRIPTS_DIR / script)],
        capture_output=True, text=True, encoding="utf-8", cwd=str(BASE_DIR),
    )
    return proc.returncode, proc.stdout, proc.stderr


def _leer_csv() -> list[dict]:
    if not CSV_PATH.exists():
        return []
    with CSV_PATH.open(encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def _resumen_captura(rows: list[dict], fecha: str) -> dict:
    """Cuenta filas por clinica para una fecha dada."""
    porc: dict[str, int] = {}
    for r in rows:
        if r.get("fecha") == fecha:
            porc[r.get("clinica", "?")] = porc.get(r.get("clinica", "?"), 0) + 1
    return porc


def construir_reporte(no_collect: bool) -> tuple[str, str, str, bool]:
    """Devuelve (asunto, cuerpo_texto, cuerpo_html, ok)."""
    hoy = date.today().isoformat()
    errores_recoleccion = ""
    rc_recolecta = 0
    salida_recolecta = ""

    if no_collect:
        salida_recolecta = "(modo --no-collect: no se ejecuto la recoleccion)"
    else:
        rc_recolecta, salida_recolecta, errores_recoleccion = _run("recolectar_diario.py")

    # Detectar cambios (read-only, no modifica nada)
    rc_cambios, reporte_cambios, err_cambios = _run("detectar_cambios.py")
    reporte_cambios = (reporte_cambios or "").strip()

    rows = _leer_csv()
    fechas = sorted({r["fecha"] for r in rows if r.get("fecha")})
    fecha_ref = fechas[-1] if fechas else hoy
    fecha_prev = fechas[-2] if len(fechas) >= 2 else None

    resumen_hoy = _resumen_captura(rows, fecha_ref)
    total_hoy = sum(resumen_hoy.values())

    # Faltantes: clinicas HTTP esperadas sin filas (dato faltante "duro").
    faltan_http = [c for c in CLINICAS_HTTP if resumen_hoy.get(c, 0) == 0]
    faltan_spa = [c for c in CLINICAS_NAVEGADOR if resumen_hoy.get(c, 0) == 0]

    # Veredicto
    if not no_collect and rc_recolecta != 0:
        veredicto = "FALLO"
        emoji = "[FALLO]"
    elif faltan_http:
        veredicto = "OK CON ADVERTENCIAS"
        emoji = "[ADVERTENCIA]"
    else:
        veredicto = "OK"
        emoji = "[OK]"

    hay_cambios = bool(reporte_cambios)

    # ---- Cuerpo en texto plano ----
    L = []
    L.append(f"ACTUALIZACIÓN DE PRECIOS ONCOLÓGICOS - {hoy}")
    L.append(f"Estado general: {veredicto}")
    L.append("")
    L.append("1) La actualización salió bien?")
    if no_collect:
        L.append("   - Modo prueba (--no-collect): no se ejecutó la recolección.")
    else:
        L.append(f"   - Código de salida del recolector: {rc_recolecta} "
                 f"({'éxito' if rc_recolecta == 0 else 'error'}).")
    L.append(f"   - Captura de referencia: {fecha_ref}. Precios capturados: {total_hoy}.")
    L.append("   - Detalle por clínica:")
    for c in CLINICAS_ESPERADAS:
        n = resumen_hoy.get(c, 0)
        marca = "  OK" if n > 0 else "  SIN DATOS"
        L.append(f"       {_disp(c)}: {n}{marca}")
    otras = [c for c in resumen_hoy if c not in CLINICAS_ESPERADAS]
    for c in otras:
        L.append(f"       {_disp(c)}: {resumen_hoy[c]}  (fuente extra)")
    L.append("")
    L.append("2) Faltó algún dato?")
    if faltan_http:
        L.append(f"   - SÍ. Clínicas HTTP sin datos hoy: {', '.join(faltan_http)}.")
        L.append("     Revisar si el sitio cambió de endpoint o estuvo caído.")
    else:
        L.append("   - No: todas las fuentes HTTP principales devolvieron datos.")
    if faltan_spa:
        L.append(f"   - Nota: clínicas por navegador pendientes de refresco: {', '.join(faltan_spa)} "
                 f"(esperado en el run automático; se completan vía Claude in Chrome).")
    if errores_recoleccion.strip():
        L.append("   - Mensajes de error del recolector (stderr):")
        for ln in errores_recoleccion.strip().splitlines()[:25]:
            L.append(f"       {ln}")
    L.append("")
    L.append("3) Cambió alguna descripción o precio?")
    if fecha_prev:
        L.append(f"   - Comparación: {fecha_prev} -> {fecha_ref}.")
    if hay_cambios:
        L.append("   - SÍ. Detalle:")
        L.append("")
        L.append(reporte_cambios)
    else:
        L.append("   - No se detectaron variaciones de precio ni glosas nuevas "
                 "respecto de la captura anterior.")
    if err_cambios.strip():
        L.append("")
        L.append(f"   (aviso detectar_cambios: {err_cambios.strip()[:200]})")
    L.append("")
    L.append("--")
    L.append("Correo automático del recolector semanal "
             "(scripts/reporte_lunes.py). Proyecto Transparencia Oncologica.")
    cuerpo_txt = "\n".join(L)

    # ---- Cuerpo HTML ----
    color = {"OK": "#14613f", "OK CON ADVERTENCIAS": "#8a6d00", "FALLO": "#a11"}[veredicto]
    filas_clin = ""
    for c in CLINICAS_ESPERADAS:
        n = resumen_hoy.get(c, 0)
        est = "OK" if n > 0 else "SIN DATOS"
        col = "#14613f" if n > 0 else "#a11"
        filas_clin += (f"<tr><td style='padding:4px 10px;border-bottom:1px solid #eee'>{_disp(c)}</td>"
                       f"<td style='padding:4px 10px;border-bottom:1px solid #eee;text-align:right'>{n}</td>"
                       f"<td style='padding:4px 10px;border-bottom:1px solid #eee;color:{col}'>{est}</td></tr>")
    cambios_html = ("<p style='color:#14613f'>Sin variaciones de precio ni glosas nuevas.</p>"
                    if not hay_cambios else
                    "<pre style='white-space:pre-wrap;font-size:13px;background:#f7f7f7;"
                    "padding:10px;border-radius:6px'>" + reporte_cambios
                    .replace("&", "&amp;").replace("<", "&lt;") + "</pre>")
    faltan_html = ("<p style='color:#14613f'>Todas las fuentes HTTP principales devolvieron datos.</p>"
                   if not faltan_http else
                   f"<p style='color:#a11'>Sin datos hoy: {', '.join(faltan_http)}.</p>")
    html = f"""\
<div style="font-family:Arial,sans-serif;max-width:660px;margin:auto;color:#1c2430">
  <h2 style="color:#1F3A5F;margin-bottom:2px">Actualización de precios oncológicos</h2>
  <p style="color:#777;margin-top:0">{hoy}</p>
  <p style="font-size:16px">Estado general:
     <b style="color:{color}">{veredicto}</b></p>
  <h3 style="color:#1F3A5F">1) La actualización salió bien?</h3>
  <p>Precios capturados en {fecha_ref}: <b>{total_hoy}</b>
     {'' if no_collect else f'(código recolector: {rc_recolecta})'}.</p>
  <table style="border-collapse:collapse;width:100%;font-size:14px">
    <thead><tr style="background:#f4f6f9">
      <th style="padding:6px 10px;text-align:left">Clínica</th>
      <th style="padding:6px 10px;text-align:right">Filas</th>
      <th style="padding:6px 10px;text-align:left">Estado</th>
    </tr></thead><tbody>{filas_clin}</tbody>
  </table>
  <h3 style="color:#1F3A5F">2) Faltó algún dato?</h3>
  {faltan_html}
  <h3 style="color:#1F3A5F">3) Cambió alguna descripción o precio?</h3>
  {('<p>Comparación ' + fecha_prev + ' &rarr; ' + fecha_ref + '.</p>') if fecha_prev else ''}
  {cambios_html}
  <hr style="border:none;border-top:1px solid #eee">
  <p style="font-size:12px;color:#777">Correo automático del recolector semanal
  (scripts/reporte_lunes.py). Proyecto Transparencia Oncologica.</p>
</div>"""

    asunto = f"{emoji} Actualización precios oncológicos {hoy} - {veredicto}"
    if hay_cambios:
        asunto += " (con cambios)"
    ok = no_collect or rc_recolecta == 0
    return asunto, cuerpo_txt, html, ok


def enviar_smtp(asunto: str, cuerpo_txt: str, html: str) -> bool:
    if not _smtp_configurado():
        return False
    host = os.environ["SMTP_HOST"]
    port = int(os.environ.get("SMTP_PORT", "587"))
    user = os.environ["SMTP_USER"]
    pwd = os.environ["SMTP_PASS"]
    sender = os.environ.get("SMTP_FROM", user)
    msg = MIMEText(html, "html", "utf-8")
    msg["Subject"] = asunto
    msg["From"] = formataddr(("Transparencia Oncologica", sender))
    msg["To"] = DESTINATARIO
    try:
        if os.environ.get("SMTP_SSL") == "1" or port == 465:
            ctx = ssl.create_default_context()
            with smtplib.SMTP_SSL(host, port, context=ctx, timeout=25) as s:
                s.login(user, pwd)
                s.sendmail(sender, [DESTINATARIO], msg.as_string())
        else:
            with smtplib.SMTP(host, port, timeout=25) as s:
                s.starttls(context=ssl.create_default_context())
                s.login(user, pwd)
                s.sendmail(sender, [DESTINATARIO], msg.as_string())
        return True
    except Exception as e:
        print(f"ERROR SMTP: {e}", file=sys.stderr)
        return False


def main() -> int:
    no_collect = "--no-collect" in sys.argv
    no_send = "--no-send" in sys.argv
    _cargar_smtp_env()

    asunto, cuerpo_txt, html, ok = construir_reporte(no_collect)

    # Siempre deja el cuerpo en disco para trazabilidad / fallback a borrador.
    OUT_BODY.parent.mkdir(parents=True, exist_ok=True)
    OUT_BODY.write_text(
        f"SUBJECT: {asunto}\nTO: {DESTINATARIO}\n\n{cuerpo_txt}\n",
        encoding="utf-8",
    )

    print(asunto)
    print("-" * 60)
    print(cuerpo_txt)
    print("-" * 60)

    if no_send:
        print("Modo --no-send: no se envio correo. Cuerpo en:", OUT_BODY)
    elif enviar_smtp(asunto, cuerpo_txt, html):
        print(f"Correo ENVIADO por SMTP a {DESTINATARIO}.")
    else:
        print("SMTP no configurado o fallo el envio. "
              f"Cuerpo listo para enviar como borrador en: {OUT_BODY}")

    # El codigo de salida refleja el exito de la recoleccion (no del envio).
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
