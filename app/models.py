"""Modelos Pydantic para entradas/salidas de la API."""
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field


# === Modelos de dominio ===

class ProductoISP(BaseModel):
    """Producto registrado en el Registro Sanitario del ISP de Chile."""
    numero_registro: str
    nombre_comercial: str
    nombre_marca: str = Field(..., description="Marca extraída del nombre comercial (ej: AVASTIN)")
    fecha_registro: Optional[str] = None
    empresa_titular: Optional[str] = None
    principio_activo: str
    control_legal: Optional[str] = None
    presentacion: Optional[str] = Field(None, description="Ej: 100 mg/4 mL")


class ArancelClinica(BaseModel):
    """Arancel encontrado en una clínica."""
    clinica: str
    query_busqueda: str = Field(..., description="Texto buscado en la clínica (ej: AVASTIN)")
    nombre_prestacion: str
    codigo_interno: Optional[str] = None
    codigo_fonasa: Optional[str] = None
    precio_particular_clp: Optional[int] = None
    precio_isapre_clp: Optional[int] = None
    precio_fonasa_clp: Optional[int] = None
    moneda: str = "CLP"
    horario: Optional[str] = None
    url_origen: Optional[str] = None
    fecha_consulta: datetime = Field(default_factory=datetime.utcnow)
    notas: Optional[str] = None


class BenchmarkResultado(BaseModel):
    """Resultado consolidado de un benchmark por principio activo."""
    benchmark_id: int
    principio_activo: str
    fecha_ejecucion: datetime
    productos_isp: List[ProductoISP]
    aranceles: List[ArancelClinica]


# === Modelos de respuesta de la API ===

class BenchmarkRequest(BaseModel):
    principio_activo: str = Field(..., examples=["bevacizumab"])
    clinicas: Optional[List[str]] = Field(
        None,
        description="Lista de clínicas a consultar. Por defecto: todas.",
        examples=[["santa_maria", "alemana"]],
    )
    incluir_marcas_extra: Optional[List[str]] = Field(
        None,
        description="Marcas comerciales adicionales a buscar más allá de las del ISP.",
    )


class BenchmarkSummary(BaseModel):
    benchmark_id: int
    principio_activo: str
    fecha_ejecucion: datetime
    total_productos_isp: int
    total_aranceles: int
    aranceles_por_clinica: dict[str, int]


# === Encuesta / censo de validacion (QR del AFE) ===

class EncuestaRespuesta(BaseModel):
    """Respuesta del cuestionario de validacion enlazado por el QR del AFE.

    Captura cuatro bloques: perfil, experiencia de precios, dolor/disposicion
    y contacto opcional. Todos los campos sensibles son opcionales para no
    frenar la tasa de respuesta.
    """
    # Bloque 1 - Perfil del paciente/cuidador
    rol: Optional[str] = Field(None, description="paciente | cuidador | profesional_salud | otro")
    rango_edad: Optional[str] = Field(None, description="Ej: 18-29, 30-44, 45-59, 60+")
    region: Optional[str] = None
    comuna: Optional[str] = None
    prevision: Optional[str] = Field(None, description="fonasa | isapre | particular | otro")
    isapre: Optional[str] = Field(None, description="Nombre de la isapre si prevision=isapre")

    # Bloque 2 - Experiencia de precios
    farmaco_oncologico: Optional[str] = Field(None, description="Principio activo o marca usada")
    precio_pagado_clp: Optional[int] = None
    precio_pagado_rango: Optional[str] = Field(None, description="Rango de precio por dosis")
    lugar_compra: Optional[str] = Field(None, description="clinica | farmacia | hospital_publico | otro")
    comparo_precios: Optional[str] = Field(None, description="si | no | no_pude")

    # Bloque 3 - Dolor y disposicion (escalas 1-5)
    dificultad_encontrar_precios: Optional[int] = Field(None, ge=1, le=5)
    gasto_bolsillo_mensual_clp: Optional[int] = None
    gasto_bolsillo_rango: Optional[str] = Field(None, description="Rango de gasto mensual")
    disposicion_usar_comparador: Optional[int] = Field(None, ge=1, le=5)

    # Bloque 4 - Contacto opcional
    nombre: Optional[str] = None
    apellido: Optional[str] = None
    email: Optional[str] = None
    consentimiento: Optional[bool] = Field(False, description="Acepta ser contactado para validacion o noticias")

    # Comentario libre
    comentario: Optional[str] = None
