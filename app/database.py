"""Capa de persistencia SQLite."""
import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from typing import Iterable

from .config import DB_PATH


SCHEMA = """
CREATE TABLE IF NOT EXISTS benchmarks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    principio_activo TEXT NOT NULL,
    fecha_ejecucion TEXT NOT NULL,
    total_productos_isp INTEGER DEFAULT 0,
    total_aranceles INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS productos_isp (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    benchmark_id INTEGER NOT NULL REFERENCES benchmarks(id),
    numero_registro TEXT,
    nombre_comercial TEXT,
    nombre_marca TEXT,
    fecha_registro TEXT,
    empresa_titular TEXT,
    principio_activo TEXT,
    control_legal TEXT,
    presentacion TEXT
);

CREATE TABLE IF NOT EXISTS aranceles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    benchmark_id INTEGER NOT NULL REFERENCES benchmarks(id),
    clinica TEXT NOT NULL,
    query_busqueda TEXT NOT NULL,
    nombre_prestacion TEXT,
    codigo_interno TEXT,
    codigo_fonasa TEXT,
    precio_particular_clp INTEGER,
    precio_isapre_clp INTEGER,
    precio_fonasa_clp INTEGER,
    moneda TEXT DEFAULT 'CLP',
    horario TEXT,
    url_origen TEXT,
    fecha_consulta TEXT,
    notas TEXT
);

CREATE INDEX IF NOT EXISTS idx_aranceles_benchmark ON aranceles(benchmark_id);
CREATE INDEX IF NOT EXISTS idx_aranceles_clinica ON aranceles(clinica);
CREATE INDEX IF NOT EXISTS idx_productos_benchmark ON productos_isp(benchmark_id);

CREATE TABLE IF NOT EXISTS encuestas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    fecha_envio TEXT NOT NULL,
    rol TEXT,
    rango_edad TEXT,
    region TEXT,
    comuna TEXT,
    prevision TEXT,
    isapre TEXT,
    nombre TEXT,
    apellido TEXT,
    farmaco_oncologico TEXT,
    precio_pagado_clp INTEGER,
    precio_pagado_rango TEXT,
    lugar_compra TEXT,
    comparo_precios TEXT,
    dificultad_encontrar_precios INTEGER,
    gasto_bolsillo_mensual_clp INTEGER,
    gasto_bolsillo_rango TEXT,
    disposicion_usar_comparador INTEGER,
    email TEXT,
    consentimiento INTEGER DEFAULT 0,
    comentario TEXT,
    user_agent TEXT,
    ip_hash TEXT
);

CREATE INDEX IF NOT EXISTS idx_encuestas_fecha ON encuestas(fecha_envio);

CREATE TABLE IF NOT EXISTS alertas_precio (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    fecha_creacion TEXT NOT NULL,
    email TEXT NOT NULL,
    principio_activo TEXT NOT NULL,
    dosis_mg REAL,
    veces INTEGER,
    cobertura_pct REAL,
    precio_referencia_clp INTEGER,
    activa INTEGER DEFAULT 1
);

CREATE TABLE IF NOT EXISTS cotizaciones_lead (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    fecha TEXT NOT NULL,
    nombre TEXT,
    apellido TEXT,
    email TEXT NOT NULL,
    principio_activo TEXT,
    dosis_mg REAL,
    veces INTEGER,
    cobertura_pct REAL,
    mejor_clinica TEXT,
    mejor_total_clp INTEGER,
    enviado_email INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS visitas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    fecha TEXT NOT NULL,
    ruta TEXT NOT NULL,
    status INTEGER,
    user_agent TEXT,
    referer TEXT,
    ip_hash TEXT
);
CREATE INDEX IF NOT EXISTS idx_visitas_fecha ON visitas(fecha);
CREATE INDEX IF NOT EXISTS idx_visitas_ruta ON visitas(ruta);
"""


@contextmanager
def get_conn():
    # OneDrive y otros sistemas de archivos sincronizados a veces fallan con el journal
    # por defecto de SQLite. Usamos journal MEMORY para evitar `disk I/O error`.
    # isolation_level=None → modo autocommit; cada execute hace su propio commit.
    conn = sqlite3.connect(str(DB_PATH), timeout=30, isolation_level=None)
    conn.row_factory = sqlite3.Row
    try:
        conn.execute("PRAGMA journal_mode=MEMORY")
        conn.execute("PRAGMA synchronous=NORMAL")
        conn.execute("PRAGMA temp_store=MEMORY")
        yield conn
    finally:
        conn.close()


def init_db() -> None:
    with get_conn() as conn:
        conn.executescript(SCHEMA)
        # migracion suave: columnas nuevas en BDs ya creadas
        for col in ("isapre TEXT", "nombre TEXT", "apellido TEXT",
                    "precio_pagado_rango TEXT", "gasto_bolsillo_rango TEXT"):
            try:
                conn.execute(f"ALTER TABLE encuestas ADD COLUMN {col}")
            except sqlite3.OperationalError:
                pass  # ya existe


def crear_benchmark(principio_activo: str) -> int:
    init_db()
    with get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO benchmarks (principio_activo, fecha_ejecucion) VALUES (?, ?)",
            (principio_activo, datetime.utcnow().isoformat()),
        )
        return cur.lastrowid


def guardar_productos_isp(benchmark_id: int, productos: Iterable[dict]) -> None:
    with get_conn() as conn:
        conn.executemany(
            """INSERT INTO productos_isp (
                benchmark_id, numero_registro, nombre_comercial, nombre_marca,
                fecha_registro, empresa_titular, principio_activo, control_legal, presentacion
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            [
                (
                    benchmark_id,
                    p.get("numero_registro"),
                    p.get("nombre_comercial"),
                    p.get("nombre_marca"),
                    p.get("fecha_registro"),
                    p.get("empresa_titular"),
                    p.get("principio_activo"),
                    p.get("control_legal"),
                    p.get("presentacion"),
                )
                for p in productos
            ],
        )


def guardar_aranceles(benchmark_id: int, aranceles: Iterable[dict]) -> None:
    with get_conn() as conn:
        conn.executemany(
            """INSERT INTO aranceles (
                benchmark_id, clinica, query_busqueda, nombre_prestacion, codigo_interno, codigo_fonasa,
                precio_particular_clp, precio_isapre_clp, precio_fonasa_clp, moneda, horario,
                url_origen, fecha_consulta, notas
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            [
                (
                    benchmark_id,
                    a.get("clinica"),
                    a.get("query_busqueda"),
                    a.get("nombre_prestacion"),
                    a.get("codigo_interno"),
                    a.get("codigo_fonasa"),
                    a.get("precio_particular_clp"),
                    a.get("precio_isapre_clp"),
                    a.get("precio_fonasa_clp"),
                    a.get("moneda", "CLP"),
                    a.get("horario"),
                    a.get("url_origen"),
                    (a.get("fecha_consulta") or datetime.utcnow()).isoformat()
                        if not isinstance(a.get("fecha_consulta"), str)
                        else a.get("fecha_consulta"),
                    a.get("notas"),
                )
                for a in aranceles
            ],
        )


def actualizar_totales(benchmark_id: int) -> None:
    with get_conn() as conn:
        prods = conn.execute(
            "SELECT COUNT(*) FROM productos_isp WHERE benchmark_id=?", (benchmark_id,)
        ).fetchone()[0]
        ars = conn.execute(
            "SELECT COUNT(*) FROM aranceles WHERE benchmark_id=?", (benchmark_id,)
        ).fetchone()[0]
        conn.execute(
            "UPDATE benchmarks SET total_productos_isp=?, total_aranceles=? WHERE id=?",
            (prods, ars, benchmark_id),
        )


def obtener_benchmark(benchmark_id: int) -> dict | None:
    with get_conn() as conn:
        bench = conn.execute(
            "SELECT * FROM benchmarks WHERE id=?", (benchmark_id,)
        ).fetchone()
        if not bench:
            return None
        productos = conn.execute(
            "SELECT * FROM productos_isp WHERE benchmark_id=?", (benchmark_id,)
        ).fetchall()
        aranceles = conn.execute(
            "SELECT * FROM aranceles WHERE benchmark_id=?", (benchmark_id,)
        ).fetchall()
        return {
            "benchmark": dict(bench),
            "productos_isp": [dict(p) for p in productos],
            "aranceles": [dict(a) for a in aranceles],
        }


def listar_benchmarks(limit: int = 50) -> list[dict]:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM benchmarks ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()
        return [dict(r) for r in rows]


# === Encuesta / censo de validacion ===

_ENCUESTA_COLS = (
    "rol", "rango_edad", "region", "comuna", "prevision", "isapre", "nombre", "apellido",
    "farmaco_oncologico", "precio_pagado_clp", "precio_pagado_rango", "lugar_compra", "comparo_precios",
    "dificultad_encontrar_precios", "gasto_bolsillo_mensual_clp", "gasto_bolsillo_rango",
    "disposicion_usar_comparador", "email", "consentimiento", "comentario",
    "user_agent", "ip_hash",
)


def guardar_encuesta(data: dict) -> int:
    """Inserta una respuesta de la encuesta y devuelve su id."""
    init_db()
    cols = ", ".join(("fecha_envio",) + _ENCUESTA_COLS)
    placeholders = ", ".join(["?"] * (len(_ENCUESTA_COLS) + 1))
    valores = [datetime.utcnow().isoformat()]
    for c in _ENCUESTA_COLS:
        v = data.get(c)
        if c == "consentimiento":
            v = 1 if v else 0
        valores.append(v)
    with get_conn() as conn:
        cur = conn.execute(
            f"INSERT INTO encuestas ({cols}) VALUES ({placeholders})", valores
        )
        return cur.lastrowid


def listar_encuestas(limit: int = 1000) -> list[dict]:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM encuestas ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()
        return [dict(r) for r in rows]


def contar_encuestas() -> int:
    with get_conn() as conn:
        return conn.execute("SELECT COUNT(*) FROM encuestas").fetchone()[0]


# === Alertas de baja de precio (version Premium) ===

def guardar_alerta(data: dict) -> int:
    init_db()
    with get_conn() as conn:
        cur = conn.execute(
            """INSERT INTO alertas_precio
               (fecha_creacion, email, principio_activo, dosis_mg, veces,
                cobertura_pct, precio_referencia_clp)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (datetime.utcnow().isoformat(), data.get("email"),
             data.get("principio_activo"), data.get("dosis_mg"),
             data.get("veces"), data.get("cobertura_pct"),
             data.get("precio_referencia_clp")),
        )
        return cur.lastrowid


def listar_alertas(limit: int = 1000) -> list[dict]:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM alertas_precio WHERE activa=1 ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()
        return [dict(r) for r in rows]


# === Leads de cotizacion (version gratuita: envio por email) ===

def guardar_cotizacion_lead(data: dict) -> int:
    init_db()
    with get_conn() as conn:
        cur = conn.execute(
            """INSERT INTO cotizaciones_lead
               (fecha, nombre, apellido, email, principio_activo, dosis_mg, veces,
                cobertura_pct, mejor_clinica, mejor_total_clp, enviado_email)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (datetime.utcnow().isoformat(), data.get("nombre"), data.get("apellido"),
             data.get("email"), data.get("principio_activo"), data.get("dosis_mg"),
             data.get("veces"), data.get("cobertura_pct"), data.get("mejor_clinica"),
             data.get("mejor_total_clp"), 1 if data.get("enviado_email") else 0),
        )
        return cur.lastrowid


def listar_cotizaciones_lead(limit: int = 1000) -> list[dict]:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM cotizaciones_lead ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()
        return [dict(r) for r in rows]


# === Metricas de visitas (registro de trafico de la API) ===

def registrar_visita(data: dict) -> None:
    """Guarda una visita. Nunca lanza: el registro no debe romper la request."""
    try:
        with get_conn() as conn:
            conn.execute(
                "INSERT INTO visitas (fecha, ruta, status, user_agent, referer, ip_hash) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (data.get("fecha"), data.get("ruta"), data.get("status"),
                 data.get("user_agent"), data.get("referer"), data.get("ip_hash")),
            )
    except Exception:
        pass


def metricas_visitas() -> dict:
    """Resumen de visitas: totales, por dia, por ruta y ultimas visitas."""
    with get_conn() as conn:
        total = conn.execute("SELECT COUNT(*) c FROM visitas").fetchone()["c"]
        unicos = conn.execute(
            "SELECT COUNT(DISTINCT ip_hash) c FROM visitas WHERE ip_hash IS NOT NULL"
        ).fetchone()["c"]
        por_dia = [dict(r) for r in conn.execute(
            "SELECT substr(fecha, 1, 10) dia, COUNT(*) visitas, "
            "COUNT(DISTINCT ip_hash) visitantes_unicos "
            "FROM visitas GROUP BY dia ORDER BY dia DESC LIMIT 60")]
        por_ruta = [dict(r) for r in conn.execute(
            "SELECT ruta, COUNT(*) visitas, COUNT(DISTINCT ip_hash) visitantes_unicos "
            "FROM visitas GROUP BY ruta ORDER BY visitas DESC LIMIT 30")]
        ultimas = [dict(r) for r in conn.execute(
            "SELECT fecha, ruta, status, user_agent FROM visitas "
            "ORDER BY id DESC LIMIT 20")]
    return {
        "total_visitas": total,
        "visitantes_unicos": unicos,
        "por_dia": por_dia,
        "por_ruta": por_ruta,
        "ultimas_visitas": ultimas,
        "nota": ("Registro desde el ultimo deploy: el disco del plan free de Render es "
                 "efimero y el contador se reinicia con cada deploy/reinicio."),
    }
