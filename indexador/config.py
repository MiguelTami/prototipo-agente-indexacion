"""Configuración del agente, leída de un archivo YAML."""

from __future__ import annotations

from pathlib import Path
from typing import Literal, Optional

import yaml
from pydantic import BaseModel, ConfigDict, Field

RUTA_POR_DEFECTO = Path(__file__).with_name("config.yaml")


class _Base(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ConfigLlm(_Base):
    modo: Literal["simulado", "bedrock"] = "simulado"
    modelo: Optional[str] = None
    region: str = "sa-east-1"


class Umbrales(_Base):
    minCaracteresUtiles: int = Field(default=100, ge=0)


class Config(_Base):
    agentVersion: str
    configVersion: str
    llm: ConfigLlm = Field(default_factory=ConfigLlm)
    umbrales: Umbrales = Field(default_factory=Umbrales)


def cargar_config(ruta: str | Path | None = None) -> Config:
    """Lee la configuración; sin ruta, usa la que viene con el paquete."""
    ruta = Path(ruta) if ruta else RUTA_POR_DEFECTO
    datos = yaml.safe_load(ruta.read_text(encoding="utf-8")) or {}
    return Config.model_validate(datos)
