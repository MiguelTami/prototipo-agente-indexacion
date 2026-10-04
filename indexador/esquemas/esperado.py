"""Respuestas esperadas de un lote: lo que una persona espera que el agente produzca.

Sirven para medir el acuerdo humano-IA por campo (riesgo R5 del producto). Cada campo admite
varias respuestas aceptables cuando el juicio es legítimamente discutible, y un respaldo puede
marcarse como ambiguo (aporta = null) para que no cuente.
"""

from __future__ import annotations

from pathlib import Path
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator

from indexador.esquemas.entrada import BloomLevel
from indexador.esquemas.reporte import EstadoArchivo
from indexador.esquemas.salida import Character, KnowledgeType


class _Base(BaseModel):
    model_config = ConfigDict(extra="forbid")


class RespaldoEsperado(_Base):
    aporta: Optional[bool] = Field(description="null: ambiguo, no se evalúa.")
    caracteres: list[Character] = Field(default_factory=list, description="Aceptados cuando aporta.")
    nota: Optional[str] = None

    @model_validator(mode="after")
    def _caracter_si_aporta(self) -> "RespaldoEsperado":
        if self.aporta and not self.caracteres:
            raise ValueError("un respaldo que aporta necesita al menos un carácter aceptado")
        return self


class ElementoEsperado(_Base):
    cognitiveLevel: list[BloomLevel] = Field(min_length=1, description="Niveles aceptados.")
    knowledgeType: list[KnowledgeType] = Field(min_length=1, description="Tipos aceptados.")
    language: str
    identifiedAuthors: list[str] = Field(default_factory=list)
    terminosClave: list[str] = Field(
        min_length=1, description="Al menos uno debe aparecer en las palabras clave o en el título."
    )
    estimatedTimeHoras: tuple[float, float] = Field(description="Rango aceptado, en horas.")
    respaldos: dict[str, RespaldoEsperado] = Field(description="Por code del RA.")
    nota: Optional[str] = None


class ArchivoEsperado(_Base):
    estado: EstadoArchivo
    elemento: Optional[ElementoEsperado] = None
    mismoElementoQue: Optional[str] = Field(
        default=None, description="sourceIdentifier de otro archivo que debe dar el mismo elemento."
    )

    @model_validator(mode="after")
    def _elemento_solo_si_procesado(self) -> "ArchivoEsperado":
        if self.elemento and self.estado != "procesado":
            raise ValueError("solo un archivo procesado tiene elemento esperado")
        return self


class RespuestasEsperadas(_Base):
    version: Literal[1] = 1
    estado: Literal["borrador", "revisado"]
    autor: str
    criterio: str
    archivos: dict[str, ArchivoEsperado]


def cargar_esperado(ruta: str | Path) -> RespuestasEsperadas:
    return RespuestasEsperadas.model_validate_json(Path(ruta).read_text(encoding="utf-8"))
