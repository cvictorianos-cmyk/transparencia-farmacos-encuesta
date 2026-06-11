"""Generacion del reporte ejecutivo en PDF (panel Premium).

Usa fpdf2 (pip install fpdf2). Si la libreria no esta instalada, devuelve un
PDF minimo valido con un aviso, para no romper el endpoint.
"""
from __future__ import annotations

from datetime import date


def _clp(n) -> str:
    try:
        return "$" + f"{int(n):,}".replace(",", ".")
    except Exception:
        return str(n)


def generar_reporte_pdf(dash: dict) -> bytes:
    try:
        from fpdf import FPDF
    except Exception:
        # PDF minimo valido si no hay fpdf2 (no deberia ocurrir en produccion)
        return (b"%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n"
                b"2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj\n"
                b"3 0 obj<</Type/Page/Parent 2 0 R/MediaBox[0 0 595 842]>>endobj\n"
                b"trailer<</Root 1 0 R>>\n%%EOF")

    AZUL = (31, 58, 95)
    GRIS = (90, 100, 112)
    VERDE = (27, 138, 90)

    pdf = FPDF(orientation="L", unit="mm", format="A4")  # horizontal (landscape)
    pdf.set_auto_page_break(auto=True, margin=14)
    pdf.add_page()

    def t(s: str) -> str:
        # fpdf core fonts: latin-1; reemplazar caracteres fuera de rango
        return (s.replace("—", "-").replace("–", "-").replace("•", "-")
                 .encode("latin-1", "replace").decode("latin-1"))

    def short(c: str) -> str:
        return (c.replace("Clinica ", "").replace("Universidad de los Andes", "U. Andes"))

    def clip(s: str, n: int) -> str:
        s = s or ""
        return s if len(s) <= n else s[:n - 1] + "."

    # Encabezado
    pdf.set_fill_color(*AZUL)
    pdf.rect(0, 0, 297, 26, "F")
    pdf.set_xy(12, 7)
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(0, 8, t("Transparencia Oncologica Clinica"), ln=1)
    pdf.set_x(12)
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(0, 6, t("Reporte ejecutivo de precios - " + date.today().isoformat()), ln=1)

    pdf.set_text_color(*GRIS)
    pdf.set_xy(12, 30)
    pdf.set_font("Helvetica", "", 9)
    pdf.multi_cell(273, 5, t("Datos: " + dash.get("fecha_datos", "") +
                  ". Precios reales del arancel particular publicado por cada clinica, "
                  "soportado por la Ley de Transparencia (Ley 20.285) en Chile."))

    # KPIs
    y = 42
    kpis = [
        (str(dash["n_farmacos"]), "Farmacos"),
        (str(dash["n_clinicas"]), "Clinicas"),
        (str(dash["brecha_promedio_pct"]) + "%", "Brecha promedio"),
        (_clp(dash["ahorro_potencial_total_clp"]), "Ahorro potencial"),
    ]
    w = 64
    for i, (v, l) in enumerate(kpis):
        x = 12 + i * (w + 3)
        pdf.set_fill_color(244, 246, 249)
        pdf.rect(x, y, w, 18, "F")
        pdf.set_xy(x, y + 3)
        pdf.set_text_color(*AZUL)
        pdf.set_font("Helvetica", "B", 13)
        pdf.cell(w, 7, t(v), align="C")
        pdf.set_xy(x, y + 11)
        pdf.set_text_color(*GRIS)
        pdf.set_font("Helvetica", "", 7)
        pdf.cell(w, 4, t(l), align="C")

    # Ranking de brecha (con glosa, tipo y precio de la mas economica y la mas cara)
    y = 66
    pdf.set_xy(12, y)
    pdf.set_text_color(*AZUL)
    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(0, 7, t("Comparacion por farmaco: opcion mas economica vs mas cara"), ln=1)
    # cabecera tabla
    cols = [("Farmaco", 26), ("Nombre mas economica", 55), ("Tipo", 18),
            ("Precio min", 24), ("Nombre mas cara", 55), ("Tipo", 18),
            ("Precio max", 24), ("Brecha", 15), ("Ahorro", 22)]
    pdf.set_x(12)
    pdf.set_font("Helvetica", "B", 6.5)
    pdf.set_fill_color(31, 58, 95)
    pdf.set_text_color(255, 255, 255)
    for label, cw in cols:
        align = "R" if label in ("Precio min", "Precio max", "Brecha", "Ahorro") else "L"
        pdf.cell(cw, 7, t(label), border=0, fill=True, align=align,
                 ln=1 if label == "Ahorro" else 0)
    pdf.set_text_color(40, 40, 48)
    pdf.set_font("Helvetica", "", 6.5)
    fill = False
    for x in dash["ranking_brecha"]:
        nombre = x.get("nombre") or x["principio_activo"].capitalize()
        pdf.set_x(12)
        pdf.set_fill_color(244, 246, 249)
        pdf.cell(26, 6, t(clip(nombre, 22)), fill=fill)
        pdf.cell(55, 6, t(short(x.get("clinica_mas_barata", "")) + " - " + clip(x.get("glosa_mas_barata", ""), 34)), fill=fill)
        pdf.cell(18, 6, t(x.get("tipo_mas_barata", "")[:12]), fill=fill)
        pdf.cell(24, 6, t(_clp(x["precio_min_clp"])), align="R", fill=fill)
        pdf.cell(55, 6, t(short(x.get("clinica_mas_cara", "")) + " - " + clip(x.get("glosa_mas_cara", ""), 34)), fill=fill)
        pdf.cell(18, 6, t(x.get("tipo_mas_cara", "")[:12]), fill=fill)
        pdf.cell(24, 6, t(_clp(x["precio_max_clp"])), align="R", fill=fill)
        pdf.cell(15, 6, t(str(x["ahorro_pct"]) + "%"), align="R", fill=fill)
        pdf.cell(22, 6, t(_clp(x["ahorro_clp"])), align="R", fill=fill, ln=1)
        fill = not fill

    # Biosimilares
    if dash.get("biosimilares"):
        pdf.ln(4)
        pdf.set_x(12)
        pdf.set_text_color(*AZUL)
        pdf.set_font("Helvetica", "B", 11)
        pdf.cell(0, 7, t("Ahorro con bioequivalentes"), ln=1)
        pdf.set_font("Helvetica", "", 8)
        pdf.set_text_color(40, 40, 48)
        for b in dash["biosimilares"]:
            pdf.set_x(12)
            pdf.cell(70, 6, t(b["principio_activo"].capitalize()))
            pdf.cell(45, 6, t(_clp(b["precio_biosimilar_min_clp"]) + " vs " + _clp(b["precio_marca_min_clp"])))
            pdf.set_text_color(*VERDE)
            pdf.cell(0, 6, t("-" + str(b["ahorro_pct"]) + "%"), ln=1)
            pdf.set_text_color(40, 40, 48)

    pdf.ln(6)
    pdf.set_x(12)
    pdf.set_text_color(*GRIS)
    pdf.set_font("Helvetica", "I", 7)
    pdf.multi_cell(273, 4, t("Reporte generado automaticamente. No constituye una cotizacion "
                  "formal. Contacto: transparenciaoncologica@gmail.com"))

    out = pdf.output()
    return bytes(out)
