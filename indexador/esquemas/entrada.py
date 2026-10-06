"""Modelos de la carpeta de entrada de una corrida.

La entrada imita lo que el core de uP1 entrega hoy al convertir un archivo a Markdown
(object-manager/docs/features/markdown-conversion.md, UPONE-1628) y lo que el mod sabe del
archivo en el LMS (mods/learning-catalog/objects/CatalogFile.json). Así, conectar el agente más
adelante solo cambia de dónde se leen los mismos datos.

Estructura de la carpeta:

    <lote>/
      lote.json               manifiesto: el curso dictado y la lista de archivos
      contexto/curso.json     curso, curso dictado y sus RA
      contexto/catalogo.json  elementos ya conocidos, para no duplicar (opcional)
      archivos/<nombre>.md    el markdown tal como lo deja el core
"""

from __future__ import annotations

from pathlib import Path
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator

# Valores permitidos copiados de los objetos reales del mod y del core.
FileType = Literal["Pdf", "Video", "Audio", "Word", "Exam", "Other"]  # CatalogFile.fileType
SourceSystem = Literal["Lms", "Repository"]  # CatalogFile.sourceSystem
BloomLevel = Literal["Remember", "Understand", "Apply", "Analyze", "Evaluate", "Create"]
MarkdownStatus = Literal["ok", "native", "unsupported", "failed", "too_large", "skipped_limit"]

# Estados del core en los que existe un markdown legible.
ESTADOS_CON_MARKDOWN: frozenset[str] = frozenset({"ok", "native"})


class _Base(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ConversionCore(_Base):
    """Lo que devuelve el core por archivo al pedirlo con markdownFields."""

    filename: str
    contentHash: str = Field(description="sha256 del contenido. En lotes sintéticos, del .md.")
    markdownStatus: MarkdownStatus
    markdownWarning: Optional[str] = None
    markdownTruncated: bool = False


class ArchivoEntrada(_Base):
    """Un archivo del LMS detectado en el curso dictado del lote."""

    sourceIdentifier: str = Field(description="Identificador del archivo en el LMS (TopicId en Brightspace).")
    tituloLms: str = Field(description="Título con el que aparece en el LMS. No es el descriptiveTitle.")
    fileType: FileType
    sourceUrl: Optional[str] = None
    sourceVersion: Optional[str] = Field(default=None, description="Última modificación en el LMS.")
    modulo: str = Field(description="Módulo o unidad del curso donde aparece. Precarga Usage.weekOrUnit.")
    orden: int = Field(ge=1, description="Posición dentro del módulo. Precarga Usage.order.")
    markdownPath: Optional[str] = Field(
        default=None, description="Ruta relativa al lote del .md. Vacía cuando el core no generó markdown."
    )
    core: ConversionCore
    sintetico: bool = Field(
        default=False, description="True cuando el contenido o el caso no vienen del LMS real."
    )
    notaSimulacion: Optional[str] = None

    @model_validator(mode="after")
    def _markdown_segun_estado(self) -> "ArchivoEntrada":
        tiene_md = self.core.markdownStatus in ESTADOS_CON_MARKDOWN
        if tiene_md and not self.markdownPath:
            raise ValueError(f"{self.sourceIdentifier}: estado '{self.core.markdownStatus}' exige markdownPath")
        if not tiene_md and self.markdownPath:
            raise ValueError(f"{self.sourceIdentifier}: estado '{self.core.markdownStatus}' no trae markdown")
        if not tiene_md and not self.core.markdownWarning:
            raise ValueError(f"{self.sourceIdentifier}: el core siempre advierte cuando no hay markdown")
        return self


class Lote(_Base):
    """El manifiesto lote.json."""

    version: Literal[1] = 1
    descripcion: str
    tenant: str = Field(description="Tenant ficticio del lote. El prototipo no se conecta a ninguno.")
    sourceSystem: SourceSystem = "Lms"
    lms: str
    offeringId: str = Field(description="Curso dictado del lote. Debe coincidir con contexto/curso.json.")
    archivos: list[ArchivoEntrada] = Field(min_length=1)

    @model_validator(mode="after")
    def _identificadores_unicos(self) -> "Lote":
        vistos: set[str] = set()
        for archivo in self.archivos:
            if archivo.sourceIdentifier in vistos:
                raise ValueError(f"sourceIdentifier repetido: {archivo.sourceIdentifier}")
            vistos.add(archivo.sourceIdentifier)
        return self


class Curso(_Base):
    """Activity con recordType Course (curriculum-design)."""

    id: str
    code: Optional[str] = None
    name: str
    language: Optional[str] = None
    description: Optional[str] = None


class CursoDictado(_Base):
    """Offering con recordType Syllabus: el curso que existe en el LMS."""

    id: str
    lmsId: str
    name: str
    term: Optional[str] = None


class ResultadoAprendizaje(_Base):
    """CurricularSection con recordType LearningOutcome y su satélite rt__LearningOutcome."""

    id: str
    code: str
    name: str = Field(description="Enunciado del RA.")
    bloomLevel: BloomLevel


class ContextoCurso(_Base):
    """El archivo contexto/curso.json."""

    curso: Curso
    cursoDictado: CursoDictado
    resultadosAprendizaje: list[ResultadoAprendizaje] = Field(
        default_factory=list, description="Vacío si el curso no tiene RA: no se proponen respaldos."
    )


class ElementoConocido(_Base):
    """Un elemento que ya existe en el catálogo, para resolver identidad por hash."""

    learningElementId: str
    contentHash: str
    descriptiveTitle: str


class CatalogoExistente(_Base):
    """El archivo contexto/catalogo.json (opcional)."""

    elementos: list[ElementoConocido] = Field(default_factory=list)


class EntradaLote(_Base):
    """Todo lo que el agente lee de una carpeta de entrada, ya validado."""

    carpeta: Path
    lote: Lote
    contexto: ContextoCurso
    catalogo: CatalogoExistente

    @model_validator(mode="after")
    def _coherencia(self) -> "EntradaLote":
        if self.lote.offeringId != self.contexto.cursoDictado.id:
            raise ValueError("lote.offeringId no coincide con contexto.cursoDictado.id")
        for archivo in self.lote.archivos:
            if archivo.markdownPath and not (self.carpeta / archivo.markdownPath).is_file():
                raise ValueError(f"{archivo.sourceIdentifier}: no existe {archivo.markdownPath}")
        return self


def cargar_entrada(carpeta: str | Path) -> EntradaLote:
    """Lee y valida la carpeta de entrada de una corrida."""
    carpeta = Path(carpeta)
    lote = Lote.model_validate_json((carpeta / "lote.json").read_text(encoding="utf-8"))
    contexto = ContextoCurso.model_validate_json(
        (carpeta / "contexto" / "curso.json").read_text(encoding="utf-8")
    )
    ruta_catalogo = carpeta / "contexto" / "catalogo.json"
    catalogo = (
        CatalogoExistente.model_validate_json(ruta_catalogo.read_text(encoding="utf-8"))
        if ruta_catalogo.is_file()
        else CatalogoExistente()
    )
    return EntradaLote(carpeta=carpeta, lote=lote, contexto=contexto, catalogo=catalogo)
