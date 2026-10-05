"""El modelo que usa el agente: Amazon Bedrock, Gemini o un simulado determinista.

Los nodos no conocen el proveedor: piden metadata o juicios de respaldo a un ModeloAgente y
reciben objetos ya validados por Pydantic. El modo simulado no usa red ni credenciales; sirve
para las pruebas y para revisar el flujo, no para juzgar la calidad de la metadata.
"""

from __future__ import annotations

import math
import os
import re
import threading
from collections import Counter
from dataclasses import dataclass
from importlib import resources
from typing import Generic, Optional, Protocol, TypeVar

from pydantic import BaseModel, ConfigDict, Field

from indexador.config import Config
from indexador.esquemas.entrada import ArchivoEntrada, BloomLevel, ContextoCurso
from indexador.esquemas.salida import Character, KnowledgeType

T = TypeVar("T")


class ErrorModelo(Exception):
    """El modelo no respondió o no devolvió una salida válida."""


# --- Lo que el modelo debe devolver ---------------------------------------------------------


class _Salida(BaseModel):
    model_config = ConfigDict(extra="forbid")


class MetadataPropuesta(_Salida):
    """Metadata del elemento que propone el modelo."""

    descriptiveTitle: str = Field(description="Título descriptivo del contenido, no el nombre del archivo.")
    description: str = Field(description="Descripción de 1 a 3 oraciones de qué trata y para qué sirve.")
    identifiedAuthors: list[str] = Field(description="Autores que aparecen en el contenido. Vacío si no hay.")
    keywords: list[str] = Field(description="Entre 3 y 8 palabras clave en el idioma del contenido.")
    knowledgeType: KnowledgeType = Field(description="Dimensión de conocimiento de Bloom revisada.")
    language: str = Field(description="Idioma del contenido, código ISO 639-1 (por ejemplo 'es').")
    estimatedTime: float = Field(ge=0, description="Tiempo estimado de estudio, en horas.")
    cognitiveLevel: BloomLevel = Field(description="Nivel cognitivo que el contenido exige, Bloom revisada.")


class JuicioRespaldo(_Salida):
    """Juicio del modelo sobre si el elemento respalda un RA del curso."""

    codigoRA: str = Field(description="El code del RA, tal como viene en la lista.")
    aporta: bool = Field(description="True si el contenido desarrolla o evalúa este RA.")
    caracter: Optional[Character] = Field(
        default=None, description="Develops, Evaluates o Both. Vacío si no aporta."
    )
    nivelOfrecido: Optional[BloomLevel] = Field(
        default=None, description="Nivel cognitivo que el contenido ofrece para este RA."
    )
    confianza: float = Field(ge=0, le=1, description="Confianza del juicio, de 0 a 1.")
    razon: str = Field(description="Por qué, en una o dos oraciones, citando el contenido.")


class JuiciosRespaldo(_Salida):
    juicios: list[JuicioRespaldo]


@dataclass(frozen=True)
class Respuesta(Generic[T]):
    valor: T
    tokensEntrada: int = 0
    tokensSalida: int = 0


class ModeloAgente(Protocol):
    identificador: str

    def generar_metadata(
        self, markdown: str, archivo: ArchivoEntrada, contexto: ContextoCurso
    ) -> Respuesta[MetadataPropuesta]: ...

    def juzgar_respaldos(
        self, markdown: str, metadata: MetadataPropuesta, contexto: ContextoCurso
    ) -> Respuesta[JuiciosRespaldo]: ...


# --- Modelo simulado ------------------------------------------------------------------------

_STOPWORDS_ES = set(
    "de la que el en y a los del se las por un para con no una su al lo como más pero sus le ya o "
    "este esta estos estas entre cuando muy sin sobre también me hasta hay donde quien desde todo "
    "nos durante todos uno les ni contra otros ese eso ante ellos e esto mí antes algunos qué unos "
    "yo otro otras otra él tanto esa estos mucho quienes nada muchos cual poco ella estar estas "
    "algunas algo nosotros cada cómo debe deben puede pueden será según tiene tienen través cuál "
    "estudiante curso reto semana semanas".split()
)
_STOPWORDS_EN = set("the and of to in is that for it with as was on are be this by".split())

# Raíces verbales por nivel de Bloom, de mayor a menor exigencia.
_VERBOS_BLOOM: list[tuple[BloomLevel, tuple[str, ...]]] = [
    ("Create", ("diseñ", "elabor", "constru")),
    ("Evaluate", ("evalú", "valor", "juzg", "argument")),
    ("Analyze", ("analiz", "clasific", "compar", "asoci", "examin")),
    ("Apply", ("aplic", "resuelv", "implement")),
    ("Remember", ("record", "identific", "enumer")),
]


def _palabras(texto: str) -> list[str]:
    return re.findall(r"[a-záéíóúñü]+", texto.lower())


def _terminos(texto: str) -> list[str]:
    return [p for p in _palabras(texto) if len(p) >= 5 and p not in _STOPWORDS_ES]


def _sin_paginas(markdown: str) -> str:
    return re.sub(r"(?m)^\s*#{1,6}\s*Página\s+\d+\s*$", "", markdown)


class ModeloSimulado:
    """Heurísticas deterministas con la misma forma de salida que el modelo real."""

    identificador = "simulado@1"

    def generar_metadata(self, markdown, archivo, contexto):
        texto = _sin_paginas(markdown)
        lineas = [l.strip() for l in texto.splitlines()]

        titulo = next((l.lstrip("#").strip() for l in lineas if l.startswith("# ")), archivo.tituloLms)
        parrafo = next(
            (l for l in lineas if l and not l.startswith(("#", "-", "|", "1.", "2.", "3.", "4."))),
            titulo,
        )
        descripcion = parrafo if len(parrafo) <= 300 else parrafo[:300].rsplit(" ", 1)[0] + "…"

        autores = [
            m.group(1).strip()
            for l in lineas
            if (m := re.match(r"^-\s+([^,]+),\s+(autor|autora|diseñador|diseñadora)\b", l, re.IGNORECASE))
        ]

        conteo = Counter(_terminos(texto))
        keywords = [p for p, _ in sorted(conteo.items(), key=lambda kv: (-kv[1], kv[0]))[:6]]

        palabras = _palabras(texto)
        es = sum(p in _STOPWORDS_ES for p in palabras)
        en = sum(p in _STOPWORDS_EN for p in palabras)
        idioma = "en" if en > es else "es"

        horas = max(0.25, math.ceil(len(palabras) / 180 / 60 / 0.25) * 0.25)

        bajo = texto.lower()
        nivel: BloomLevel = "Understand"
        mejor = 0
        for candidato, raices in _VERBOS_BLOOM:
            n = sum(bajo.count(r) for r in raices)
            if n > mejor:
                nivel, mejor = candidato, n

        pasos = sum(bool(re.match(r"^\d+\.\s", l)) for l in lineas)
        referencias = sum(bool(re.search(r"\(\d{4}\)", l)) for l in lineas)
        tipo_conocimiento: KnowledgeType = (
            "Procedural" if pasos >= 3 else "Factual" if referencias >= 2 else "Conceptual"
        )

        return Respuesta(
            MetadataPropuesta(
                descriptiveTitle=titulo,
                description=descripcion,
                identifiedAuthors=autores,
                keywords=keywords,
                knowledgeType=tipo_conocimiento,
                language=idioma,
                estimatedTime=horas,
                cognitiveLevel=nivel,
            )
        )

    def juzgar_respaldos(self, markdown, metadata, contexto):
        terminos_contenido = set(_terminos(markdown))
        evalua = bool(re.search(r"(?im)^#+\s*(producto del reto|evaluaci[oó]n)", markdown))
        juicios = []
        for ra in contexto.resultadosAprendizaje:
            terminos_ra = set(_terminos(ra.name))
            comunes = sorted(terminos_ra & terminos_contenido)
            puntaje = len(comunes) / len(terminos_ra) if terminos_ra else 0.0
            aporta = puntaje >= 0.35
            juicios.append(
                JuicioRespaldo(
                    codigoRA=ra.code,
                    aporta=aporta,
                    caracter=("Both" if evalua else "Develops") if aporta else None,
                    nivelOfrecido=metadata.cognitiveLevel if aporta else None,
                    confianza=round(min(0.95, 0.3 + 0.7 * puntaje), 2) if aporta else round(puntaje, 2),
                    razon=(
                        f"[simulado] Comparte {len(comunes)} de {len(terminos_ra)} términos del RA"
                        + (f": {', '.join(comunes[:5])}." if comunes else ".")
                    ),
                )
            )
        return Respuesta(JuiciosRespaldo(juicios=juicios))


# --- Modelos reales (LangChain) -------------------------------------------------------------


def _prompt(nombre: str) -> str:
    return resources.files("indexador.prompts").joinpath(nombre).read_text(encoding="utf-8")


def _rellenar(plantilla: str, valores: dict[str, str]) -> str:
    for clave, valor in valores.items():
        plantilla = plantilla.replace("{{" + clave + "}}", valor)
    return plantilla


class _ModeloLangChain:
    """Lo común a los proveedores reales: mismos prompts, salida estructurada validada por Pydantic.

    Cada proveedor solo construye su chat de LangChain; todo lo demás es igual.
    """

    identificador: str

    def __init__(self, chat, identificador: str, config: Config):
        self.identificador = identificador
        self._max_caracteres = config.llm.maxCaracteresEntrada
        self._metadata = chat.with_structured_output(MetadataPropuesta, include_raw=True)
        self._respaldos = chat.with_structured_output(JuiciosRespaldo, include_raw=True)

    def _invocar(self, cadena, sistema: str, usuario: str) -> Respuesta:
        try:
            salida = cadena.invoke([("system", sistema), ("human", usuario)])
        except Exception as error:  # el proveedor puede fallar de muchas formas
            raise ErrorModelo(f"{type(error).__name__}: {error}") from error
        if salida.get("parsed") is None:
            raise ErrorModelo(f"Salida no válida: {salida.get('parsing_error')}")
        uso = getattr(salida.get("raw"), "usage_metadata", None) or {}
        return Respuesta(salida["parsed"], uso.get("input_tokens", 0), uso.get("output_tokens", 0))

    def _recortar(self, markdown: str) -> str:
        return markdown[: self._max_caracteres]

    def generar_metadata(self, markdown, archivo, contexto):
        usuario = _rellenar(
            _prompt("metadata_usuario.md"),
            {
                "curso": contexto.curso.name,
                "titulo_lms": archivo.tituloLms,
                "modulo": archivo.modulo,
                "markdown": self._recortar(markdown),
            },
        )
        return self._invocar(self._metadata, _prompt("metadata_sistema.md"), usuario)

    def juzgar_respaldos(self, markdown, metadata, contexto):
        ras = "\n".join(
            f"- {ra.code} (nivel requerido: {ra.bloomLevel}): {ra.name}" for ra in contexto.resultadosAprendizaje
        )
        usuario = _rellenar(
            _prompt("respaldos_usuario.md"),
            {
                "curso": contexto.curso.name,
                "titulo": metadata.descriptiveTitle,
                "resultados": ras,
                "markdown": self._recortar(markdown),
            },
        )
        return self._invocar(self._respaldos, _prompt("respaldos_sistema.md"), usuario)


def _exigir_modelo(config: Config) -> str:
    if not config.llm.modelo:
        raise ErrorModelo(f"llm.modelo está vacío: indica el id del modelo para el modo {config.llm.modo}")
    return config.llm.modelo


class ModeloBedrock(_ModeloLangChain):
    """Amazon Bedrock vía langchain-aws. Credenciales: las de AWS del entorno (perfil o SSO)."""

    def __init__(self, config: Config):
        try:
            from langchain_aws import ChatBedrockConverse
        except ImportError as error:  # pragma: no cover - depende de la instalación
            raise ErrorModelo('Falta langchain-aws: pip install -e ".[bedrock]"') from error
        modelo = _exigir_modelo(config)
        chat = ChatBedrockConverse(model=modelo, region_name=config.llm.region, temperature=config.llm.temperatura)
        super().__init__(chat, f"bedrock/{modelo}", config)


class ModeloGemini(_ModeloLangChain):
    """Gemini en Google AI Studio vía langchain-google-genai. Llave: GOOGLE_API_KEY o GEMINI_API_KEY."""

    def __init__(self, config: Config):
        try:
            from langchain_google_genai import ChatGoogleGenerativeAI
        except ImportError as error:  # pragma: no cover - depende de la instalación
            raise ErrorModelo('Falta langchain-google-genai: pip install -e ".[gemini]"') from error
        modelo = _exigir_modelo(config)
        llave = os.environ.get("GOOGLE_API_KEY") or os.environ.get("GEMINI_API_KEY")
        if not llave:
            raise ErrorModelo("Falta la llave de Gemini: define GOOGLE_API_KEY en el archivo .env (ver .env.example)")
        chat = ChatGoogleGenerativeAI(model=modelo, google_api_key=llave, temperature=config.llm.temperatura)
        super().__init__(chat, f"gemini/{modelo}", config)


# --- Fábrica --------------------------------------------------------------------------------

_cache: dict[str, ModeloAgente] = {}
_lock = threading.Lock()


def obtener_modelo(config: Config) -> ModeloAgente:
    """Un modelo por configuración, reutilizado entre contenidos y corridas."""
    clave = config.llm.model_dump_json()
    with _lock:
        if clave not in _cache:
            proveedores = {"simulado": lambda c: ModeloSimulado(), "bedrock": ModeloBedrock, "gemini": ModeloGemini}
            _cache[clave] = proveedores[config.llm.modo](config)
        return _cache[clave]
