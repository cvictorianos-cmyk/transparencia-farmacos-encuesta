"""Envio de correos (cotizaciones).

Usa SMTP si esta configurado por variables de entorno; si no, no envia y deja
el lead guardado en la base de datos para envio/seguimiento posterior.

Variables de entorno (configurar en Render):
    SMTP_HOST   ej: smtp.gmail.com
    SMTP_PORT   ej: 587 (TLS) o 465 (SSL)
    SMTP_USER   usuario / correo emisor
    SMTP_PASS   contrasena o app-password
    SMTP_FROM   remitente visible (por defecto = SMTP_USER)
    SMTP_SSL    "1" para usar SSL directo (puerto 465); por defecto STARTTLS
"""
from __future__ import annotations

import os
import smtplib
import ssl
from email.mime.text import MIMEText
from email.utils import formataddr


def smtp_configurado() -> bool:
    return bool(os.environ.get("SMTP_HOST") and os.environ.get("SMTP_USER")
               and os.environ.get("SMTP_PASS"))


def _fmt(n) -> str:
    try:
        return "$" + f"{int(n):,}".replace(",", ".")
    except Exception:
        return str(n)


def cuerpo_cotizacion(nombre: str, cot: dict) -> tuple[str, str]:
    """Devuelve (asunto, cuerpo_html) de la cotizacion."""
    pa = cot.get("principio_activo", "").capitalize()
    asunto = f"Tu cotizacion de tratamiento - {pa}"
    filas = ""
    for o in cot.get("opciones", []):
        filas += (
            f"<tr><td style='padding:6px 10px;border-bottom:1px solid #eee'>{o['clinica']}</td>"
            f"<td style='padding:6px 10px;border-bottom:1px solid #eee;font-size:12px;color:#555'>{o['glosa']}</td>"
            f"<td style='padding:6px 10px;border-bottom:1px solid #eee;text-align:right'>{_fmt(o['costo_total_clp'])}</td>"
            f"<td style='padding:6px 10px;border-bottom:1px solid #eee;text-align:right'>{_fmt(o['copago_estimado_clp'])}</td></tr>"
        )
    mejor = cot.get("opcion_mas_barata", {})
    html = f"""\
<div style="font-family:Arial,sans-serif;max-width:640px;margin:auto;color:#1c2430">
  <h2 style="color:#1F3A5F">Transparencia Oncologica Clinica</h2>
  <p>Hola {nombre or ''}, aqui esta tu cotizacion referencial para <b>{pa}</b>
  (dosis {cot.get('dosis_mg')} mg, {cot.get('veces')} administraciones,
  cobertura {cot.get('cobertura_pct', 0)}%).</p>
  <p style="background:#e6f4ec;border-radius:8px;padding:10px 14px;color:#14613f">
    Opcion mas conveniente: <b>{_fmt(mejor.get('costo_total_clp'))}</b> en {mejor.get('clinica','')}.
    Ahorro frente a la mas cara: <b>{_fmt(cot.get('ahorro_total_clp'))}</b>.</p>
  <table style="border-collapse:collapse;width:100%;font-size:14px">
    <thead><tr style="background:#f4f6f9">
      <th style="padding:8px 10px;text-align:left">Clinica</th>
      <th style="padding:8px 10px;text-align:left">Producto</th>
      <th style="padding:8px 10px;text-align:right">Costo total</th>
      <th style="padding:8px 10px;text-align:right">Copago estimado</th>
    </tr></thead>
    <tbody>{filas}</tbody>
  </table>
  <p style="font-size:12px;color:#777;margin-top:16px">{cot.get('disclaimer','')}</p>
  <p style="font-size:12px;color:#777">Precios reales del arancel particular publicado por cada
  clinica, soportado por la Ley de Transparencia (Ley 20.285) en Chile.</p>
</div>"""
    return asunto, html


def enviar_cotizacion(email: str, nombre: str, cot: dict) -> bool:
    """Envia la cotizacion por correo. Devuelve True si se envio."""
    if not smtp_configurado():
        return False
    host = os.environ["SMTP_HOST"]
    port = int(os.environ.get("SMTP_PORT", "587"))
    user = os.environ["SMTP_USER"]
    pwd = os.environ["SMTP_PASS"]
    sender = os.environ.get("SMTP_FROM", user)
    asunto, html = cuerpo_cotizacion(nombre, cot)
    msg = MIMEText(html, "html", "utf-8")
    msg["Subject"] = asunto
    msg["From"] = formataddr(("Transparencia Oncologica Clinica", sender))
    msg["To"] = email
    try:
        if os.environ.get("SMTP_SSL") == "1" or port == 465:
            ctx = ssl.create_default_context()
            with smtplib.SMTP_SSL(host, port, context=ctx, timeout=20) as s:
                s.login(user, pwd)
                s.sendmail(sender, [email], msg.as_string())
        else:
            with smtplib.SMTP(host, port, timeout=20) as s:
                s.starttls(context=ssl.create_default_context())
                s.login(user, pwd)
                s.sendmail(sender, [email], msg.as_string())
        return True
    except Exception:
        return False
