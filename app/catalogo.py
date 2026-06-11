"""Catalogo de farmacos oncologicos con PRECIOS REALES de clinicas chilenas.

Todos los precios provienen de los buscadores publicos de aranceles de cada
clinica (valor particular, horario habil), extraidos en junio de 2026:

    - Clinica INDISA ............... indisa.cl/aranceles-buscador (GraphQL)
    - Clinica Davila ............... davila.cl/aranceles (categoria Farmacos)
    - Clinica U. de los Andes ...... clinicauandes.cl/aranceles/resultado
    - UC Marcoleta (Hospital Clinico UC) . aranceles.ucchristus.cl/api/public (centroId=1)
    - UC San Carlos (Apoquindo) ......... aranceles.ucchristus.cl/api/public (centroId=3)

Clinica Santa Maria y Clinica Alemana NO publican el valor particular de estos
farmacos oncologicos en su arancel web, por lo que no se incluyen.

Cada caso corresponde a una presentacion (vial/dosis) y contiene una lista de
"ofertas": una fila por cada version publicada por una clinica, con:
    clinica         : nombre de la clinica
    glosa           : nombre EXACTO con que aparece el farmaco en esa clinica
    precio          : valor particular en CLP
    bioequivalente  : True si es biosimilar/bioequivalente; False si es la marca
                      original (innovador de referencia)

Precios con fines academicos (Proyecto de Titulo MSIIN); no constituyen una
cotizacion formal.
"""
from __future__ import annotations

import re
from statistics import mean

CLINICAS = [
    "Clinica INDISA",
    "Clinica Davila",
    "Clinica Universidad de los Andes",
    "UC Marcoleta",
    "UC San Carlos",
]

FECHA_DATOS = "2026-06 (arancel particular, horario habil)"

# Categorias clinicas (tipo de cancer / area) a las que se asocia cada principio
# activo, segun sus indicaciones. Un farmaco puede pertenecer a varias.
CATEGORIAS_POR_PA = {
    "pembrolizumab": ["Mama"],
    "daratumumab": ["Mieloma múltiple"],
    "nivolumab": ["Pulmón", "Melanoma", "Renal", "Estómago"],
    "bevacizumab": ["Colon", "Pulmón", "Renal", "Ovario"],
    "rituximab": ["Linfoma", "Leucemia"],
    "cetuximab": ["Colon", "Cabeza y cuello"],
    "ipilimumab": ["Melanoma", "Renal"],
}

# Emoji por categoria (para las tarjetas de la primera pagina).
# Solo se usan emojis ampliamente compatibles (se evitan los de organos 2020:
# pulmones/riñon/corazon que no renderizan en Windows 10).
_CAT_ICON = {
    "Mama": "🎀", "Pulmón": "🌬️", "Colon": "🧬", "Estómago": "🍽️", "Próstata": "🧔",
    "Melanoma": "🧴", "Renal": "🧫", "Vejiga": "💧", "Ovario": "🌸",
    "Linfoma": "🩸", "Leucemia": "🩸", "Mieloma múltiple": "🦴",
    "Cabeza y cuello": "👤",
}


def categorias_de(pa: str) -> list[str]:
    return CATEGORIAS_POR_PA.get(_slug(pa), ["Otros"])


def listar_categorias() -> list[dict]:
    """Lista de categorias oncologicas con la cantidad de farmacos en cada una."""
    agrupado: dict[str, set] = {}
    for c in CATALOGO:
        pa = c["principio_activo"]
        for cat in categorias_de(pa):
            agrupado.setdefault(cat, set()).add(pa)
    out = [
        {"categoria": cat, "icono": _CAT_ICON.get(cat, "💊"),
         "n_farmacos": len(pas), "farmacos": sorted(pas)}
        for cat, pas in agrupado.items()
    ]
    out.sort(key=lambda x: (-x["n_farmacos"], x["categoria"]))
    return out


def _o(clinica, glosa, precio, bioeq=False):
    return {"clinica": clinica, "glosa": glosa, "precio": precio, "bioequivalente": bioeq}


# Empresa titular segun el Registro Sanitario del ISP (registrosanitario.ispch.gob.cl).
# Se resuelve por palabra clave de la glosa, evaluando primero las marcas de
# biosimilares y luego las marcas innovadoras. Datos extraidos en jun-2026.
_EMPRESAS_ISP = [
    ("ABXEDA", "Laboratorios Recalcine S.A."),
    ("RIXATHON", "Sandoz Chile S.p.A."),
    ("TRUXIMA", "Celltrion Healthcare Chile S.p.A."),
    ("BIOSIMILAR", "Biosimilar (Sandoz / Celltrion)"),
    ("KEYTRUDA", "Merck Sharp & Dohme (I.A.) LLC"),
    ("PEMBROLIZUMAB", "Merck Sharp & Dohme (I.A.) LLC"),
    ("DARZALEX", "Johnson & Johnson de Chile S.A."),
    ("DARATUMUMAB", "Johnson & Johnson de Chile S.A."),
    ("OPDIVO", "Bristol-Myers Squibb de Chile"),
    ("NIVOLUMAB", "Bristol-Myers Squibb de Chile"),
    ("AVASTIN", "Roche Chile Ltda."),
    ("MABTHERA", "Roche Chile Ltda."),
    ("ERBITUX", "Merck S.A."),
    ("CETUXIMAB", "Merck S.A."),
    ("YERVOY", "Bristol-Myers Squibb de Chile"),
    ("IPILIMUMAB", "Bristol-Myers Squibb de Chile"),
    ("ELAPRASE", "Takeda Chile S.p.A."),
    ("IDURSULFASA", "Takeda Chile S.p.A."),
    ("TIMOGLOBULINA", "Sanofi (Genzyme)"),
    ("BEVACIZUMAB", "Roche Chile Ltda."),   # glosas sin marca (Avastin de referencia)
    ("RITUXIMAB", "Roche Chile Ltda."),     # glosas sin marca (Mabthera de referencia)
]


def _empresa(glosa: str) -> str:
    g = glosa.upper()
    for clave, empresa in _EMPRESAS_ISP:
        if clave in g:
            return empresa
    return "No especificada"


CATALOGO: list[dict] = [
    {
        "principio_activo": "pembrolizumab",
        "marca": "Keytruda 100 mg/4 mL",
        "indicacion": "Inmunoterapia (melanoma, pulmon, otros tumores PD-L1+)",
        "titular": "MSD (Merck Sharp & Dohme)",
        "registro_isp": "B-2456/15",
        "presentacion": "Vial 100 mg/4 mL concentrado para perfusion",
        "ofertas": [
            _o("Clinica INDISA", "PEMBROLIZUMAB 100 MG/4ML (KEYTRUDA)", 6_030_118),
            _o("Clinica Davila", "PEMBROLIZUMAB 100 MG/4 ML (KEYTRUDA) FA", 4_048_980),
            _o("Clinica Universidad de los Andes", "PEMBROLIZUMAB 100 MG FAM", 4_380_828),
            _o("UC Marcoleta", "PEMBROLIZUMAB 100MG 4ML (FX0045)", 4_063_300),
            _o("UC San Carlos", "PEMBROLIZUMAB 100MG 4ML (FX0045)", 4_469_630),
        ],
    },
    {
        "principio_activo": "daratumumab",
        "marca": "Darzalex IV 400 mg",
        "indicacion": "Mieloma multiple (formulacion intravenosa)",
        "titular": "Janssen Cilag (Johnson & Johnson)",
        "registro_isp": "B-2711/17",
        "presentacion": "Vial 400 mg/20 mL concentrado para perfusion",
        "ofertas": [
            _o("Clinica INDISA", "DARATUMUMAB 400 MG/20 ML (DARZALEX)", 2_431_941),
            _o("Clinica Universidad de los Andes", "DARATUMUMAB 400 MG FAM", 2_796_600),
            _o("UC Marcoleta", "DARATUMUMAB 400 MG 20 ML X 1 FA (FO0573)", 2_319_665),
            _o("UC San Carlos", "DARATUMUMAB 400 MG 20 ML X 1 FA (FO0573)", 2_530_511),
        ],
    },
    {
        "principio_activo": "daratumumab",
        "marca": "Darzalex Faspro SC 1800 mg",
        "indicacion": "Mieloma multiple (formulacion subcutanea)",
        "titular": "Janssen Cilag (Johnson & Johnson)",
        "registro_isp": "B-3110/20",
        "presentacion": "Vial 1800 mg/15 mL solucion subcutanea",
        "ofertas": [
            _o("Clinica Universidad de los Andes", "DARATUMUMAB 1800 MG/15 ML SC", 5_616_940),
            _o("UC Marcoleta", "DARATUMUMAB SC 1800 MG (FO0641)", 5_473_958),
            _o("UC San Carlos", "DARATUMUMAB SC 1800 MG (FO0641)", 6_021_353),
        ],
    },
    {
        "principio_activo": "nivolumab",
        "marca": "Opdivo 100 mg/10 mL",
        "indicacion": "Inmunoterapia (melanoma, pulmon, renal)",
        "titular": "Bristol Myers Squibb",
        "registro_isp": "B-2502/16",
        "presentacion": "Vial 100 mg/10 mL concentrado para perfusion",
        "ofertas": [
            _o("Clinica INDISA", "NIVOLUMAB 100 MG/10 ML (OPDIVO)", 2_654_551),
            _o("Clinica Davila", "NIVOLUMAB 100 MG/10 ML (OPDIVO)", 1_916_720),
            _o("Clinica Universidad de los Andes", "NIVOLUMAB 100 MG FAM", 2_460_840),
            _o("UC Marcoleta", "NIVOLUMAB 100 MG REFRIGERADO (FO0152)", 2_129_885),
            _o("UC San Carlos", "NIVOLUMAB 100 MG REFRIGERADO (FO0152)", 2_321_652),
        ],
    },
    {
        "principio_activo": "bevacizumab",
        "marca": "Avastin 100 mg/4 mL",
        "indicacion": "Antiangiogenico (colon, pulmon, renal, glioblastoma)",
        "titular": "Roche",
        "registro_isp": "B-1820/12",
        "presentacion": "Vial 100 mg/4 mL concentrado para perfusion",
        "ofertas": [
            _o("Clinica INDISA", "BEVACIZUMAB (AVASTIN) 100 MG/4ML", 1_054_823),
            _o("Clinica INDISA", "BEVACIZUMAB 100 MG/4 ML (ABXEDA)", 433_160, bioeq=True),
            _o("Clinica Davila", "BEVACIZUMAB 100 MG/4 ML (AVASTIN)", 541_362),
            _o("Clinica Universidad de los Andes", "BEVACIZUMAB FAM 100 MG/4 ML", 660_180),
            _o("UC Marcoleta", "BEVACIZUMAB 100 MG /4 ML *REFRIGERADO* (FO0026)", 586_265),
            _o("UC San Carlos", "BEVACIZUMAB 100 MG/4ML (FO0026)", 644_891),
        ],
    },
    {
        "principio_activo": "rituximab",
        "marca": "Mabthera 500 mg",
        "indicacion": "Linfoma no Hodgkin, leucemia linfocitica cronica, artritis",
        "titular": "Roche",
        "registro_isp": "B-1455/09",
        "presentacion": "Vial 500 mg/50 mL concentrado para perfusion",
        "ofertas": [
            _o("Clinica INDISA", "RITUXIMAB 500 MG (MABTHERA)", 3_139_895),
            _o("Clinica INDISA", "RITUXIMAB 500MG/50ML (RIXATHON)", 1_365_214, bioeq=True),
            _o("Clinica Davila", "RITUXIMAB 500 MG/50 ML (MABTHERA)", 1_301_000),
            _o("Clinica Davila", "RITUXIMAB (TRUXIMA) 500 MG", 728_730, bioeq=True),
            _o("Clinica Universidad de los Andes", "RITUXIMAB FAM 500 MG/50 ML", 1_926_360),
            _o("UC Marcoleta", "RITUXIMAB 500 MG *REFRIGERADO* (FO0092)", 1_750_563),
            _o("UC Marcoleta", "RITUXIMAB 500MG REFRIGERADO BIOSIMILAR (FX9037)", 394_485, bioeq=True),
            _o("UC San Carlos", "RITUXIMAB 500 MG (FO0092)", 1_925_619),
            _o("UC San Carlos", "RITUXIMAB 500MG BIOSIMILAR (FX9037)", 433_933, bioeq=True),
        ],
    },
    {
        "principio_activo": "cetuximab",
        "marca": "Erbitux 100 mg/20 mL",
        "indicacion": "Cancer colorrectal metastasico y de cabeza y cuello",
        "titular": "Merck",
        "registro_isp": "B-1602/10",
        "presentacion": "Vial 100 mg/20 mL solucion para perfusion",
        "ofertas": [
            _o("Clinica INDISA", "CETUXIMAB 100 MG/20 ML (ERBITUX)", 425_051),
            _o("Clinica Davila", "CETUXIMAB 100 MG/20 ML (ERBITUX)", 502_244),
            _o("Clinica Universidad de los Andes", "CETUXIMAB 100 MG/20 ML FAM", 523_020),
            _o("UC Marcoleta", "CETUXIMAB 100 MG REFRIGERADO (FO0123)", 472_356),
            _o("UC San Carlos", "CETUXIMAB 100 MG REFRIGERADO (FO0123)", 519_591),
        ],
    },
    {
        "principio_activo": "ipilimumab",
        "marca": "Yervoy 50 mg/10 mL",
        "indicacion": "Inmunoterapia (melanoma avanzado, combinaciones)",
        "titular": "Bristol Myers Squibb",
        "registro_isp": "B-2380/15",
        "presentacion": "Vial 50 mg/10 mL concentrado para perfusion",
        "ofertas": [
            _o("Clinica INDISA", "IPILIMUMAB 50 MG (YERVOY)", 4_758_742),
            _o("Clinica Universidad de los Andes", "IPILIMUMAB FAM 50 MG / 10 ML", 3_917_688),
            _o("UC Marcoleta", "IPILIMUMAB 50MG EV AMP (FO0160)", 3_588_387),
            _o("UC San Carlos", "IPILIMUMAB 50MG EV AMP (FO0160)", 3_947_225),
        ],
    },
]


def _slug(s: str) -> str:
    return s.strip().lower()


def _vial_mg(presentacion: str) -> float | None:
    """Extrae los mg por vial desde la presentacion (ej: 'Vial 400 mg/20 mL')."""
    m = re.search(r"([\d.]+)\s*mg", presentacion or "", re.I)
    return float(m.group(1)) if m else None


def cotizar(principio_activo: str, dosis_mg: float, veces: int,
            cobertura_pct: float = 0.0) -> dict | None:
    """Costo total de un tratamiento por clinica.

    dosis_mg      : dosis indicada por el medico para cada administracion
    veces         : numero de administraciones (ciclos) del tratamiento
    cobertura_pct : % de cobertura de la isapre/seguro (0 si no se conoce)
    """
    pa = _slug(principio_activo)
    casos = [c for c in CATALOGO if _slug(c["principio_activo"]) == pa]
    if not casos or dosis_mg <= 0 or veces <= 0:
        return None
    cobertura_pct = max(0.0, min(100.0, cobertura_pct or 0.0))

    import math
    opciones = []
    for c in casos:
        mg = _vial_mg(c["presentacion"])
        if not mg:
            continue
        viales = math.ceil(dosis_mg / mg)
        for o in c["ofertas"]:
            costo_dosis = viales * o["precio"]
            costo_total = costo_dosis * veces
            copago = round(costo_total * (1 - cobertura_pct / 100))
            opciones.append({
                "clinica": o["clinica"],
                "glosa": o["glosa"],
                "presentacion": c["presentacion"],
                "marca": c["marca"],
                "bioequivalente": o["bioequivalente"],
                "mg_por_vial": mg,
                "viales_por_dosis": viales,
                "precio_vial_clp": o["precio"],
                "costo_por_dosis_clp": costo_dosis,
                "costo_total_clp": costo_total,
                "copago_estimado_clp": copago,
            })
    if not opciones:
        return None
    opciones.sort(key=lambda x: x["costo_total_clp"])
    mas_barata, mas_cara = opciones[0], opciones[-1]
    return {
        "principio_activo": pa,
        "dosis_mg": dosis_mg,
        "veces": veces,
        "cobertura_pct": cobertura_pct,
        "opciones": opciones,
        "ahorro_total_clp": mas_cara["costo_total_clp"] - mas_barata["costo_total_clp"],
        "opcion_mas_barata": {"clinica": mas_barata["clinica"], "costo_total_clp": mas_barata["costo_total_clp"]},
        "disclaimer": (
            "Calculo referencial: viales completos necesarios por dosis x numero de "
            "administraciones, segun el arancel particular publicado por cada clinica "
            "(Ley de Transparencia - Ley 20.285). No incluye honorarios de administracion, "
            "insumos ni dia cama. No constituye una cotizacion formal."
        ),
    }


def _tiene_biosimilar(caso: dict) -> bool:
    return any(o["bioequivalente"] for o in caso["ofertas"])


def listar_catalogo(categoria: str | None = None) -> list[dict]:
    """Devuelve una vista resumida de los casos. Si se da `categoria`, filtra."""
    cat_f = categoria.strip().lower() if categoria else None
    out = []
    for c in CATALOGO:
        cats = categorias_de(c["principio_activo"])
        if cat_f and cat_f not in [x.lower() for x in cats]:
            continue
        precios = [o["precio"] for o in c["ofertas"]]
        clinicas = {o["clinica"] for o in c["ofertas"]}
        out.append({
            "principio_activo": c["principio_activo"],
            "marca": c["marca"],
            "indicacion": c["indicacion"],
            "presentacion": c["presentacion"],
            "categorias": cats,
            "bioequivalente": _tiene_biosimilar(c),
            "n_clinicas": len(clinicas),
            "n_ofertas": len(c["ofertas"]),
            "precio_min_clp": min(precios),
            "precio_max_clp": max(precios),
            "ahorro_max_clp": max(precios) - min(precios),
            "ahorro_max_pct": round((max(precios) - min(precios)) / max(precios) * 100, 1),
        })
    return out


def exportar_filas() -> list[dict]:
    """Filas planas del snapshot actual de precios (para descarga CSV / ERP)."""
    from datetime import date
    hoy = date.today().isoformat()
    filas = []
    for c in CATALOGO:
        cats = "; ".join(categorias_de(c["principio_activo"]))
        for o in c["ofertas"]:
            filas.append({
                "fecha": hoy,
                "categoria": cats,
                "principio_activo": c["principio_activo"],
                "marca": c["marca"],
                "presentacion": c["presentacion"],
                "clinica": o["clinica"],
                "nombre_en_clinica": o["glosa"],
                "empresa_isp": _empresa(o["glosa"]),
                "tipo": "Bioequivalente" if o["bioequivalente"] else "Original",
                "precio_particular_clp": o["precio"],
                "moneda": "CLP",
                "fuente": "Arancel publico (Ley 20.285)",
            })
    return filas


def dashboard() -> dict:
    """Metricas agregadas del catalogo para el panel Premium."""
    clinicas = set()
    brechas = []          # ahorro_pct por caso (marca vs marca + biosimilares)
    ahorros_clp = []      # ahorro absoluto por caso
    por_farmaco = []      # ranking de brecha por farmaco
    biosimilares = []     # ahorro del biosimilar vs marca
    suma_min = suma_max = 0
    n_ofertas = 0

    for c in CATALOGO:
        ofertas = c["ofertas"]
        n_ofertas += len(ofertas)
        for o in ofertas:
            clinicas.add(o["clinica"])
        precios = [o["precio"] for o in ofertas]
        pmin, pmax = min(precios), max(precios)
        suma_min += pmin
        suma_max += pmax
        ahorro = pmax - pmin
        ahorro_pct = round(ahorro / pmax * 100, 1) if pmax else 0
        brechas.append(ahorro_pct)
        ahorros_clp.append(ahorro)
        barata = min(ofertas, key=lambda o: o["precio"])
        # nombre unico por presentacion (evita confundir las 2 de daratumumab)
        otras_pres = sum(1 for x in CATALOGO if x["principio_activo"] == c["principio_activo"])
        nombre = c["principio_activo"].capitalize()
        if otras_pres > 1:
            nombre += " " + c["marca"].replace("Darzalex", "").strip().split()[0]
        por_farmaco.append({
            "principio_activo": c["principio_activo"],
            "nombre": nombre,
            "marca": c["marca"],
            "ahorro_pct": ahorro_pct,
            "ahorro_clp": ahorro,
            "precio_min_clp": pmin,
            "precio_max_clp": pmax,
            "clinica_mas_barata": barata["clinica"],
        })
        marcas = [o["precio"] for o in ofertas if not o["bioequivalente"]]
        bios = [o["precio"] for o in ofertas if o["bioequivalente"]]
        if marcas and bios:
            mmin, bmin = min(marcas), min(bios)
            biosimilares.append({
                "principio_activo": c["principio_activo"],
                "precio_marca_min_clp": mmin,
                "precio_biosimilar_min_clp": bmin,
                "ahorro_pct": round((mmin - bmin) / mmin * 100, 1),
            })

    por_farmaco.sort(key=lambda x: x["ahorro_pct"], reverse=True)
    biosimilares.sort(key=lambda x: x["ahorro_pct"], reverse=True)
    return {
        "n_farmacos": len({c["principio_activo"] for c in CATALOGO}),
        "n_presentaciones": len(CATALOGO),
        "n_clinicas": len(clinicas),
        "n_ofertas": n_ofertas,
        "clinicas": sorted(clinicas),
        "brecha_promedio_pct": round(sum(brechas) / len(brechas), 1) if brechas else 0,
        "brecha_max_pct": max(brechas) if brechas else 0,
        "ahorro_potencial_total_clp": sum(ahorros_clp),
        "suma_precio_min_clp": suma_min,
        "suma_precio_max_clp": suma_max,
        "ranking_brecha": por_farmaco,
        "biosimilares": biosimilares,
        "fecha_datos": FECHA_DATOS,
    }


def comparar(principio_activo: str, marca: str | None = None) -> dict | None:
    """Comparacion de precios reales de un caso entre las clinicas que lo publican.

    Cada fila incluye la glosa (nombre exacto en la clinica) y si es bioequivalente.
    """
    pa = _slug(principio_activo)
    casos = [c for c in CATALOGO if _slug(c["principio_activo"]) == pa]
    if marca:
        m = _slug(marca)
        casos = [c for c in casos if m in _slug(c["marca"])]
    if not casos:
        return None

    presentaciones = []
    for c in casos:
        ofertas = sorted(c["ofertas"], key=lambda o: o["precio"])
        precios = [o["precio"] for o in ofertas]
        precio_min, precio_max = precios[0], precios[-1]
        # precio minimo solo entre marcas originales (para medir el ahorro del biosimilar)
        precios_marca = [o["precio"] for o in ofertas if not o["bioequivalente"]]
        min_marca = min(precios_marca) if precios_marca else precio_min
        filas = []
        for o in ofertas:
            filas.append({
                "clinica": o["clinica"],
                "principio_activo": c["principio_activo"],
                "glosa": o["glosa"],
                "empresa": _empresa(o["glosa"]),
                "bioequivalente": o["bioequivalente"],
                "tipo": "Bioequivalente" if o["bioequivalente"] else "Original",
                "precio_particular_clp": o["precio"],
                "es_menor": o["precio"] == precio_min,
                "sobreprecio_vs_min_clp": o["precio"] - precio_min,
                "sobreprecio_vs_min_pct": round((o["precio"] - precio_min) / precio_min * 100, 1),
                "fuente": "real",
            })
        n_clin = len({o["clinica"] for o in ofertas})
        ahorro_biosim = None
        if any(o["bioequivalente"] for o in ofertas):
            min_bio = min(o["precio"] for o in ofertas if o["bioequivalente"])
            ahorro_biosim = {
                "precio_min_biosimilar_clp": min_bio,
                "precio_min_marca_clp": min_marca,
                "ahorro_pct": round((min_marca - min_bio) / min_marca * 100, 1),
            }
        presentaciones.append({
            "marca": c["marca"],
            "titular": c["titular"],
            "registro_isp": c["registro_isp"],
            "presentacion": c["presentacion"],
            "indicacion": c["indicacion"],
            "bioequivalente": _tiene_biosimilar(c),
            "n_clinicas": n_clin,
            "n_ofertas": len(ofertas),
            "precio_min_clp": precio_min,
            "precio_max_clp": precio_max,
            "precio_promedio_clp": round(mean(precios)),
            "ahorro_clp": precio_max - precio_min,
            "ahorro_pct": round((precio_max - precio_min) / precio_max * 100, 1),
            "clinica_mas_barata": ofertas[0]["clinica"],
            "clinica_mas_cara": ofertas[-1]["clinica"],
            "ahorro_biosimilar": ahorro_biosim,
            "precios": filas,
        })

    return {
        "principio_activo": pa,
        "n_presentaciones": len(presentaciones),
        "presentaciones": presentaciones,
        "disclaimer": (
            "Precios REALES del arancel particular publicado por cada clinica, soportado por la "
            "Ley de Transparencia (Ley 20.285) en Chile. 'Nombre en la clinica' es la glosa exacta "
            "del arancel. Solo en Premium: 'Empresa (ISP)', titular del registro sanitario segun "
            "registrosanitario.ispch.gob.cl, y 'Tipo', que indica si es el medicamento original "
            "(marca innovadora) o un bioequivalente/biosimilar. No constituye una cotizacion "
            "formal; confirme siempre el valor con la clinica."
        ),
    }
