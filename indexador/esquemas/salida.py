"""Objetos de salida, espejo de mods/learning-catalog/objects/*.json.

Nombres de campo, valores permitidos y obligatoriedad copiados de los objetos reales del mod
(rama fix/catalog-gaps). Cada objeto lleva además un `id` local: el prototipo no tiene base de
datos, así que los ids son estables pero no son los que asignaría Object Manager.

Sin diferencias de obligatoriedad con el mod. Hasta LAB-40, CatalogFile.learningElementId e
identificationMethod eran opcionales aquí porque un archivo ilegible salía sin elemento; ahora el
agente lo identifica por hash antes de marcarlo ilegible y le asocia un elemento, así que son
obligatorios, como en el mod.
"""

from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

from indexador.esquemas.entrada import BloomLevel, FileType, SourceSystem

# Valores permitidos del mod.
IdentificationMethod = Literal["ExactHash", "ContentSimilarity"]
DetectionExtractionStatus = Literal["Detected", "Extracted", "Unreadable"]
ElementType = Literal["Document", "Video", "Audio", "Exam", "Other"]
KnowledgeType = Literal["Factual", "Conceptual", "Procedural", "Metacognitive"]
ValidityStatus = Literal["Valid", "Outdated"]
Rights = Literal["Institution", "Section"]
IngestionStatus = Literal["Detected", "Extracted", "Published"]
EvaluationStatus = Literal["NotEvaluated", "Evaluated", "Expired"]
Character = Literal["Develops", "Evaluates", "Both"]
BackingStatus = Literal["Proposed", "Validated"]
UsageCharacter = Literal["Mandatory", "Complementary"]
EntityType = Literal["LearningElement", "Usage", "Backing", "CatalogFile"]
Origin = Literal["Lms", "AiAgent", "Person", "SeedPropagation"]
ActorRole = Literal["Authority", "Curator", "Professor"]


class _Objeto(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(description="Id local del prototipo.")


class CatalogFile(_Objeto):
    sourceSystem: SourceSystem
    sourceIdentifier: str
    fileType: FileType
    sourceUrl: Optional[str] = None
    offeringId: Optional[str] = None
    learningElementId: str
    contentHash: Optional[str] = None
    identificationMethod: IdentificationMethod
    identificationConfidence: Optional[float] = Field(default=None, ge=0, le=1)
    identificationPending: bool = False
    detectionExtractionStatus: DetectionExtractionStatus
    sourceVersion: Optional[str] = None
    detectedAt: str
    lastSyncedAt: Optional[str] = None


class LearningElement(_Objeto):
    descriptiveTitle: str
    description: Optional[str] = None
    identifiedAuthors: list[str] = Field(default_factory=list)
    keywords: list[str] = Field(default_factory=list)
    type: ElementType
    knowledgeType: Optional[KnowledgeType] = None
    language: str
    estimatedTime: float = Field(ge=0)
    validityStatus: ValidityStatus = "Valid"
    cognitiveLevel: Optional[BloomLevel] = None
    rights: Rights = "Institution"
    extractedTextUrl: Optional[str] = None
    semanticRepresentationUrl: Optional[str] = None
    ingestionStatus: IngestionStatus = "Extracted"
    metadataStatus: bool
    evaluationStatus: EvaluationStatus = "NotEvaluated"
    professorReviewed: bool = False
    publishedById: Optional[str] = None
    publishedAt: Optional[str] = None


class Backing(_Objeto):
    learningElementId: str
    courseId: str
    learningOutcomeId: str
    character: Character
    offeredCognitiveLevel: Optional[BloomLevel] = None
    modelConfidence: Optional[float] = Field(default=None, ge=0, le=1)
    status: BackingStatus = "Proposed"
    proposedWithoutUsage: bool = False
    validatedAt: Optional[str] = None
    validatedById: Optional[str] = None


class Usage(_Objeto):
    learningElementId: str
    offeringId: str
    weekOrUnit: Optional[str] = None
    order: Optional[int] = None
    usageCharacter: UsageCharacter = "Complementary"
    notes: Optional[str] = None
    sequencingReviewed: bool = False


class Provenance(_Objeto):
    entityType: EntityType
    entityId: str
    fieldName: str
    origin: Origin
    actorId: Optional[str] = None
    agentIdentifier: Optional[str] = None
    actorRole: Optional[ActorRole] = None
    actorSegmentId: Optional[str] = None
    recordedAt: str
    configVersion: Optional[str] = None


class ObjetosCorrida(BaseModel):
    """Todos los objetos que produce una corrida, uno por archivo de objetos/."""

    model_config = ConfigDict(extra="forbid")

    catalogFiles: list[CatalogFile] = Field(default_factory=list)
    learningElements: list[LearningElement] = Field(default_factory=list)
    backings: list[Backing] = Field(default_factory=list)
    usages: list[Usage] = Field(default_factory=list)
    provenance: list[Provenance] = Field(default_factory=list)
