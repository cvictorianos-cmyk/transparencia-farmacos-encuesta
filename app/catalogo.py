"""Catalogo de farmacos oncologicos con PRECIOS REALES de clinicas chilenas.

Todos los precios provienen de los buscadores publicos de aranceles de cada
clinica (valor particular, horario habil), extraidos en junio de 2026:

    - Clinica INDISA ............... indisa.cl/aranceles-buscador (GraphQL)
    - Clinica Davila ............... davila.cl/aranceles (categoria Farmacos)
    - Clinica U. de los Andes ...... clinicauandes.cl/aranceles/resultado
    - UC Marcoleta (Hospital Clinico UC) . aranceles.ucchristus.cl/api/public (centroId=1)
    - UC San Carlos (Apoquindo) ......... aranceles.ucchristus.cl/api/public (centroId=3)

Clinica Santa Maria y Clinica Alemana publican solo algunos de estos farmacos
en su arancel web; se incluyen los casos con valor particular verificado
(ej. Phesgo, jul-2026).

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
    "Clinica Santa Maria",
    "Clinica Alemana",
    "FALP",
]

FECHA_DATOS = "2026-07 (arancel particular, horario habil)"

# Pagina/arancel publico de cada clinica (para la columna "fuente" del export).
CLINICA_URL = {
    "Clinica INDISA": "https://www.indisa.cl/aranceles-buscador?param=medicamentos",
    "Clinica Davila": "https://www.davila.cl/aranceles",
    "Clinica Universidad de los Andes": "https://www.clinicauandes.cl/aranceles",
    "UC Marcoleta": "https://aranceles.ucchristus.cl/",
    "UC San Carlos": "https://aranceles.ucchristus.cl/",
    "Clinica Santa Maria": "https://www.clinicasantamaria.cl/aranceles",
    "Clinica Alemana": "https://www.clinicaalemana.cl/aranceles/list/insumos-y-medicamentos",
    "FALP": "https://www.falp.org/aranceles/",
}

# Categorias clinicas (tipo de cancer / area) a las que se asocia cada principio
# activo, segun sus indicaciones. Un farmaco puede pertenecer a varias.
CATEGORIAS_POR_PA = {
    "pembrolizumab": ["Mama"],
    "daratumumab": ["Mieloma múltiple"],
    "nivolumab": ["Pulmón", "Riñón", "Estómago"],
    "bevacizumab": ["Colon", "Pulmón", "Riñón", "Ovario"],
    "rituximab": ["Linfoma", "Leucemia"],
    "cetuximab": ["Colon", "Cabeza y cuello"],
    "ipilimumab": ["Riñón"],
    "tamoxifeno": ["Mama"],
    "letrozol": ["Mama"],
    "trastuzumab": ["Mama"],
    "trastuzumab emtansina": ["Mama"],
    "trastuzumab deruxtecan": ["Mama"],
    "pertuzumab/trastuzumab": ["Mama"],
    "imatinib": ["Leucemia"],
}

# Emoji por categoria (para las tarjetas de la primera pagina).
# Solo se usan emojis ampliamente compatibles (se evitan los de organos 2020:
# pulmones/riñon/corazon que no renderizan en Windows 10).
_CAT_ICON = {
    "Mama": "🎀", "Pulmón": "🌬️", "Colon": "🧬", "Estómago": "🍽️", "Próstata": "🧔",
    "Riñón": "🧫", "Vejiga": "💧", "Ovario": "🌸",
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
    ("ABBOTT", "Abbott Laboratories de Chile Ltda."),
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
    ("HERZUMA", "Celltrion Healthcare Chile S.p.A."),   # biosimilar trastuzumab
    ("KADCYLA", "Roche Chile Ltda."),
    ("PHESGO", "Roche Chile Ltda."),
    ("PERTU", "Roche Chile Ltda."),
    ("HERCEPTIN", "Roche Chile Ltda."),
    ("BISINTEX", "Bio-Sintex (titular por verificar)"),  # biosimilar trastuzumab
    ("DERUXTECAN", "Daiichi Sankyo (titular por verificar)"),  # Enhertu
    ("TRASTUZUMAB", "Roche Chile Ltda."),   # glosas sin marca (Herceptin de referencia)
    ("FEMARA", "Novartis Chile S.A."),
    ("NOLVADEX", "AstraZeneca Chile S.A."),
    ("GLIVEC", "Novartis Chile S.A."),
    ("TIADIS", "Tiadis Pharma S.A."),       # laboratorio del generico Letrozol
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
            _o("Clinica Santa Maria", "KEYTRUDA 100 MG (PEMBROLIZUMAB) FRASCO (65380006)", 3_832_456),
            _o("Clinica Alemana", "KEYTRUDA 100 MG/4 ML INYECTABLE (500000092)", 3_112_932),
            _o("FALP", "PEMBROLIZUMAB 100MG FA (10400277)", 3_382_751),
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
            _o("Clinica Santa Maria", "DARZALEX (DARATUMUMAB) 400 MG/20 ML (65380014)", 2_585_548),
            _o("Clinica Alemana", "DARZALEX 400 MG/20 ML INYECTABLE (500820021)", 2_228_454),
            _o("FALP", "DARATUMUMAB 400 MG/20ML (10400399)", 1_696_735),
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
            _o("Clinica Alemana", "DARZALEX 1800 MG/15 ML S/C (500820238)", 5_898_174),
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
            _o("Clinica Santa Maria", "OPDIVO 100 MG (NIVOLUMAB) FRASCO (65380004)", 2_125_511),
            _o("Clinica Alemana", "OPDIVO (NIVOLUMAB) 100 MG/10 ML X VIAL (500820011)", 1_922_512),
            _o("FALP", "NIVOLUMAB 100 MG FA (10400290)", 1_559_212),
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
            _o("Clinica Santa Maria", "AVASTIN 100 MG/4 ML (BEVACIZUMAB) (65100042)", 536_954),
            _o("Clinica Alemana", "AVASTIN 100 MG/4 ML INYECTABLE (500820920)", 524_957),
            _o("FALP", "BEVACIZUMAB 100 MG (AVASTIN) (10400102)", 475_507),
            _o("FALP", "BEVACIZUMAB 100 MG (ABBOTT) (10400674)", 397_338, bioeq=True),
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
            _o("Clinica Santa Maria", "MABTHERA 500 MG/50 ML (RITUXIMAB) (65100035)", 1_677_788),
            _o("Clinica Santa Maria", "TRUXIMA 500MG/50ML (RITUXIMAB) (65380022)", 1_513_422, bioeq=True),
            _o("Clinica Alemana", "MABTHERA 500 MG/50 ML INYECTABLE (500825547)", 1_607_024),
            _o("FALP", "RITUXIMAB 500 MG (RM ROCHE) (10400083)", 1_105_099),
            _o("FALP", "RITUXIMAB 500 MG (RIXATHON) (10400503)", 331_810, bioeq=True),
            _o("FALP", "RITUXIMAB 500 MG (TRUXIMA) (10400444)", 191_445, bioeq=True),
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
            _o("Clinica Santa Maria", "ERBITUX 100 MG/20 ML (CETUXIMAB) (65100039)", 776_974),
            _o("Clinica Alemana", "ERBITUX 100 MG/20 ML INYECTABLE (500823555)", 456_484),
            _o("FALP", "CETUXIMAB 100 MG/20ML (ERBITUX) (10400107)", 495_736),
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
            _o("Clinica Santa Maria", "YERVOY 50 MG (IPILIMUMAB) (65380003)", 3_994_979),
            _o("Clinica Alemana", "YERVOY 50 MG/10 ML INYECTABLE (500829600)", 4_181_041),
            _o("FALP", "IPILIMUMAB 50 MG/10 ML FA (10400215)", 3_085_503),
        ],
    },
    # ------------------------------------------------------------------
    # Incorporados jun-2026: Tamoxifeno, Letrozol, Trastuzumab e Imatinib.
    # Precios REALES obtenidos en vivo via los scrapers de INDISA (API
    # GraphQL), Clinica Davila y Clinica U. de los Andes (Playwright).
    # Clinica Santa Maria no publica estos farmacos en su buscador; Clinica
    # Alemana no respondio durante la extraccion (sitio con timeout). UC
    # Marcoleta/San Carlos y FALP quedan pendientes (no tienen scraper
    # propio, se cargan manualmente como el resto del catalogo).
    #
    # NOTA DE UNIDADES: Tamoxifeno, Letrozol e Imatinib son orales y cada
    # clinica publica una unidad de venta distinta (comprimido individual
    # vs. caja). Para no mezclar unidades en una misma comparacion, cada
    # unidad de venta se modela como una "presentacion" propia (igual
    # criterio que las 2 presentaciones de daratumumab). La glosa de cada
    # oferta indica la unidad exacta reportada por la clinica.
    # ------------------------------------------------------------------
    {
        "principio_activo": "tamoxifeno",
        "marca": "Tamoxifeno 20 mg (Nolvadex / generico)",
        "indicacion": "Cancer de mama hormonosensible (terapia endocrina adyuvante)",
        "titular": "AstraZeneca / multiples titulares genericos",
        "registro_isp": "Por verificar (registrosanitario.ispch.gob.cl)",
        "presentacion": "Comprimido 20 mg (precio normalizado por comprimido)",
        "ofertas": [
            _o("Clinica INDISA", "TAMOXIFENO 20 MG COMP (por comprimido)", 1_282),
            _o("Clinica Davila", "TAMOXIFENO 20 MG CAJA 30 -> por comprimido", 5_299),
            _o("Clinica Universidad de los Andes", "NOLVADEX TAMOXIFENO 20 MG CAJA 30 -> por comprimido", 1_627),
            _o("Clinica Universidad de los Andes", "TAMOXIFENO 20 MG / 30 CMP -> por comprimido", 1_444, bioeq=True),
        ],
    },
    {
        "principio_activo": "letrozol",
        "marca": "Letrozol 2,5 mg (Femara / generico)",
        "indicacion": "Cancer de mama hormonosensible, postmenopausia (inhibidor de aromatasa)",
        "titular": "Novartis / multiples titulares genericos",
        "registro_isp": "Por verificar (registrosanitario.ispch.gob.cl)",
        "presentacion": "Comprimido 2,5 mg (precio normalizado por comprimido)",
        "ofertas": [
            _o("Clinica INDISA", "FEMARA 2,5 MG (INDISA HOGAR) (por comprimido)", 17_211),
            _o("Clinica Davila", "LETROZOL 2,5 MG (TIADIS) CAJA 30 -> por comprimido", 2_327, bioeq=True),
            _o("Clinica Universidad de los Andes", "LETROZOL 2,5 MG / 30 CMP -> por comprimido", 9_275, bioeq=True),
        ],
    },
    {
        "principio_activo": "trastuzumab",
        "marca": "Herceptin IV 440 mg",
        "indicacion": "Cancer de mama y gastrico HER2-positivo (formulacion intravenosa)",
        "titular": "Roche",
        "registro_isp": "Por verificar (registrosanitario.ispch.gob.cl)",
        "presentacion": "Vial 440 mg liofilizado para perfusion",
        "ofertas": [
            _o("Clinica INDISA", "HERCEPTIN 440 MG FCO INY", 3_748_431),
            _o("Clinica INDISA", "TRASTUZUMAB 440MG/50 ML (HERCEPTIN)", 3_150_990),
            _o("Clinica INDISA", "TRASTUZUMAB 440 MG (HERZUMA) INY FRASCO", 1_147_224, bioeq=True),
            _o("Clinica Davila", "TRASTUZUMAB 440 MG EV FCO AMP 1 UNI", 1_801_250),
            _o("Clinica Universidad de los Andes", "TRASTUZUMAB FAM 440 MG LIOF", 2_519_244),
            _o("Clinica Universidad de los Andes", "TRASTUZUMAB 440MG EV (BISINTEX)", 1_611_295, bioeq=True),
            _o("Clinica Alemana", "HERCEPTIN 440 MG INYECTABLE (500824007)", 2_552_535),
            _o("Clinica Santa Maria", "HERCEPTIN 440 MG (TRASTUZUMAB) LIOF. FRA (65060003)", 1_403_737),
            _o("Clinica Santa Maria", "BISINTEX 440 MG (TRASTUZUMAB) LIOF FRASC (65390005)", 1_668_707, bioeq=True),
            _o("UC Marcoleta", "TRASTUZUMAB 440MG (F00125)", 2_718_829),
            _o("UC San Carlos", "TRASTUZUMAB 440MG (F00125)", 2_990_711),
        ],
    },
    {
        "principio_activo": "trastuzumab",
        "marca": "Herceptin SC 600 mg",
        "indicacion": "Cancer de mama HER2-positivo (formulacion subcutanea)",
        "titular": "Roche",
        "registro_isp": "Por verificar (registrosanitario.ispch.gob.cl)",
        "presentacion": "Vial 600 mg/5 mL solucion subcutanea",
        "ofertas": [
            _o("Clinica INDISA", "TRASTUZUMAB 600 MG/5ML SC (HERCEPTIN)", 2_898_491),
            _o("Clinica Davila", "TRASTUZUMAB 600 MG SC (HERCEPTIN) JERING", 2_532_250),
            _o("Clinica Universidad de los Andes", "TRASTUZUMAB JER 600 MG SC", 2_772_900),
            _o("Clinica Santa Maria", "HERCEPTIN 600 MG/5 ML (TRASTUZUMAB) SC F (65390003)", 2_420_878),
            _o("UC Marcoleta", "TRASTUZUMAB 600 MG 5 ML SUBCUTANEO RE (F00147)", 2_904_597),
            _o("UC San Carlos", "TRASTUZUMAB 600 MG 5 ML SUBCUTANEO RE (F00147)", 3_195_056),
        ],
    },
    {
        "principio_activo": "trastuzumab emtansina",
        "marca": "Kadcyla 100 mg",
        "indicacion": "Cancer de mama HER2-positivo, post-tratamiento (conjugado anticuerpo-farmaco)",
        "titular": "Roche",
        "registro_isp": "Por verificar (registrosanitario.ispch.gob.cl)",
        "presentacion": "Vial 100 mg liofilizado para perfusion",
        "ofertas": [
            _o("Clinica Davila", "TRASTUZUMAB EMTANSINE 100 MG.(KADCYLA) A", 1_925_560),
            _o("Clinica Universidad de los Andes", "TRASTUZUMAB EMTANSINE 100 MG", 2_443_500),
            _o("Clinica Santa Maria", "TRASTUZUMAB EMTANSINA 100 ML LIOF IV FRA (77010027)", 1_968_348),
            _o("UC Marcoleta", "TRASTUZUMAB EMTANSINA 100 MG (F01043)", 2_152_019),
            _o("UC San Carlos", "TRASTUZUMAB EMTANSINA 100 MG (F01043)", 2_278_566),
        ],
    },
    {
        "principio_activo": "trastuzumab emtansina",
        "marca": "Kadcyla 160 mg",
        "indicacion": "Cancer de mama HER2-positivo, post-tratamiento (conjugado anticuerpo-farmaco)",
        "titular": "Roche",
        "registro_isp": "Por verificar (registrosanitario.ispch.gob.cl)",
        "presentacion": "Vial 160 mg liofilizado para perfusion",
        "ofertas": [
            _o("Clinica INDISA", "TRASTUZUMAB EMTANSINA (KADCYLA) 160 MG", 3_677_718),
            _o("Clinica Davila", "TRASTUZUMAB EMTANSINE 160 MG.(KADCYLA) A", 3_103_550),
            _o("Clinica Universidad de los Andes", "TRASTUZUMAB EMTANSINE 160 MG FAM", 3_779_820),
            _o("UC San Carlos", "TRASTUZUMAB EMTANSINA 160 MG (F01044)", 3_645_709),
        ],
    },
    {
        "principio_activo": "trastuzumab deruxtecan",
        "marca": "Enhertu 100 mg",
        "indicacion": "Cancer de mama HER2-positivo/HER2-low avanzado (conjugado anticuerpo-farmaco)",
        "titular": "Daiichi Sankyo / AstraZeneca",
        "registro_isp": "Por verificar (registrosanitario.ispch.gob.cl)",
        "presentacion": "Vial 100 mg liofilizado para perfusion",
        "ofertas": [
            _o("UC Marcoleta", "TRASTUZUMAB DERUXTECAN 100 MG (F01051)", 3_747_127),
            _o("UC San Carlos", "TRASTUZUMAB DERUXTECAN 100 MG (F01051)", 4_121_839),
        ],
    },
    {
        "principio_activo": "pertuzumab/trastuzumab",
        "marca": "Phesgo 600/600 mg",
        "indicacion": "Cancer de mama HER2-positivo (combinacion fija pertuzumab + trastuzumab, subcutanea, dosis de mantencion)",
        "titular": "Roche",
        "registro_isp": "Por verificar (registrosanitario.ispch.gob.cl)",
        "presentacion": "Vial combo 600 mg/600 mg solucion subcutanea",
        "ofertas": [
            _o("Clinica INDISA", "PHESGO 600/600 (PERTU/TRASTUZUMAB)", 3_848_317),
            _o("Clinica Davila", "PERTUZUMAB/TRASTUZUMAB 600/600MG (PHESGO)", 3_962_790),
            _o("Clinica Santa Maria", "PHESGO(PERTUZ 600MG+TRASTUZ 600MG)/10ML (77010001)", 4_650_544),
            _o("UC Marcoleta", "PERTUZUMAB 600MG TRASTUZUMAB 600MG (F00141)", 4_177_233),
            _o("UC San Carlos", "PERTUZUMAB 600MG TRASTUZUMAB 600MG (F00141)", 4_594_956),
        ],
    },
    {
        "principio_activo": "pertuzumab/trastuzumab",
        "marca": "Phesgo 1200/600 mg",
        "indicacion": "Cancer de mama HER2-positivo (combinacion fija pertuzumab + trastuzumab, subcutanea, dosis de carga)",
        "titular": "Roche",
        "registro_isp": "Por verificar (registrosanitario.ispch.gob.cl)",
        "presentacion": "Vial combo 1200 mg/600 mg solucion subcutanea (dosis de carga)",
        "ofertas": [
            _o("Clinica Alemana", "PHESGO 1200/600 MG INYECTABLE (500820236)", 3_809_834),
            _o("Clinica INDISA", "PHESGO 1200/600 MG (PERTU/TRASTU) FRASCO (13030129)", 3_848_317),
            _o("Clinica Davila", "PERTUZUMAB/TRASTUZUMAB 1200/600MG (PHESGO)", 3_962_790),
            _o("UC Marcoleta", "PERTUZUMAB 1200MG TRASTUZUMAB 600MG (F00146)", 4_344_322),
            _o("UC San Carlos", "PERTUZUMAB 1200MG TRASTUZUMAB 600MG (F00146)", 4_778_754),
        ],
    },
    {
        "principio_activo": "imatinib",
        "marca": "Imatinib 100 mg (Glivec / generico)",
        "indicacion": "Leucemia mieloide cronica y tumores GIST (inhibidor BCR-ABL/c-KIT)",
        "titular": "Novartis / multiples titulares genericos",
        "registro_isp": "Por verificar (registrosanitario.ispch.gob.cl)",
        "presentacion": "Caja x 60 comprimidos 100 mg (venta por caja)",
        "ofertas": [
            _o("Clinica Universidad de los Andes", "IMATINIB 100 MG 60 CMP (5000002062)", 1_207_978, bioeq=True),
        ],
    },
    {
        "principio_activo": "imatinib",
        "marca": "Imatinib 400 mg (Glivec / generico)",
        "indicacion": "Leucemia mieloide cronica y tumores GIST (inhibidor BCR-ABL/c-KIT)",
        "titular": "Novartis / multiples titulares genericos",
        "registro_isp": "Por verificar (registrosanitario.ispch.gob.cl)",
        "presentacion": "Comprimido recubierto 400 mg (precio normalizado por comprimido)",
        "ofertas": [
            _o("Clinica Universidad de los Andes", "IMATINIB MESILATO CMP REC 400 MG (5000001139) (por comprimido)", 175_855, bioeq=True),
            _o("Clinica Universidad de los Andes", "IMATINIB 400 MG X 30 CMP (5000002436) -> por comprimido", 77_025),
            _o("UC Marcoleta", "IMATINIB 400 MG X 30 UND (F01014) -> por comprimido", 77_055),
            _o("UC San Carlos", "IMATINIB 400 MG X 30 UND (F01014) -> por comprimido", 77_055),
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


def dashboard(clinicas_sel: list[str] | None = None,
              farmacos_sel: list[str] | None = None) -> dict:
    """Metricas agregadas del catalogo para el panel Premium.

    clinicas_sel : si se entrega, solo considera esas clinicas.
    farmacos_sel : si se entrega, solo considera esos principios activos.
    """
    cl_f = {c.strip().lower() for c in clinicas_sel} if clinicas_sel else None
    fa_f = {f.strip().lower() for f in farmacos_sel} if farmacos_sel else None

    clinicas = set()
    brechas = []          # ahorro_pct por caso (marca vs marca + biosimilares)
    ahorros_clp = []      # ahorro absoluto por caso
    por_farmaco = []      # ranking de brecha por farmaco
    biosimilares = []     # ahorro del biosimilar vs marca
    suma_min = suma_max = 0
    n_ofertas = 0

    for c in CATALOGO:
        if fa_f and _slug(c["principio_activo"]) not in fa_f:
            continue
        ofertas = [o for o in c["ofertas"]
                   if not cl_f or o["clinica"].lower() in cl_f]
        if not ofertas:
            continue
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
        cara = max(ofertas, key=lambda o: o["precio"])
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
            "clinica_mas_cara": cara["clinica"],
            "glosa_mas_barata": barata["glosa"],
            "glosa_mas_cara": cara["glosa"],
            "tipo_mas_barata": "Bioequivalente" if barata["bioequivalente"] else "Original",
            "tipo_mas_cara": "Bioequivalente" if cara["bioequivalente"] else "Original",
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
        "todas_clinicas": list(CLINICAS),
        "todos_farmacos": sorted({c["principio_activo"] for c in CATALOGO}),
        "filtros": {"clinicas": clinicas_sel or [], "farmacos": farmacos_sel or []},
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
