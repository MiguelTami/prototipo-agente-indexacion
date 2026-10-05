"""Configuración del agente, leída de un archivo YAML."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Literal, Optional

import yaml
from pydantic import BaseModel, ConfigDict, Field

RUTA_POR_DEFECTO = Path(__file__).with_name("config.yaml")


class _Base(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ConfigLlm(_Base):
    modo: Literal["simulado", "bedrock", "gemini"] = "simulado"
    modelo: Optional[str] = None
    region: str = "sa-east-1"
    temperatura: float = Field(default=0.0, ge=0, le=1)
    reintentos: int = Field(default=2, ge=0, description="Reintentos además del primer intento.")
    esperaReintentoSegundos: float = Field(
        default=0.0, ge=0, description="Espera antes del primer reintento; se duplica en cada uno."
    )
    maxConcurrencia: int = Field(default=4, ge=1, description="Contenidos procesados a la vez.")
    maxCaracteresEntrada: int = Field(default=60_000, gt=0)


class Umbrales(_Base):
    minCaracteresUtiles: int = Field(default=100, ge=0)


class Config(_Base):
    agentVersion: str
    configVersion: str
    llm: ConfigLlm = Field(default_factory=ConfigLlm)
    umbrales: Umbrales = Field(default_factory=Umbrales)


def cargar_env(ruta: str | Path = ".env") -> None:
    """Carga variables KEY=VALUE de un archivo .env sin pisar las que ya existen.

    Así la llave de un proveedor vive fuera del código y fuera de git (.env está en .gitignore).
    """
    ruta = Path(ruta)
    if not ruta.is_file():
        return
    for linea in ruta.read_text(encoding="utf-8").splitlines():
        linea = linea.strip()
        if not linea or linea.startswith("#") or "=" not in linea:
            continue
        clave, valor = linea.split("=", 1)
        os.environ.setdefault(clave.strip(), valor.strip().strip('"').strip("'"))


def cargar_config(ruta: str | Path | None = None) -> Config:
    """Lee la configuración; sin ruta, usa la que viene con el paquete."""
    ruta = Path(ruta) if ruta else RUTA_POR_DEFECTO
    datos = yaml.safe_load(ruta.read_text(encoding="utf-8")) or {}
    return Config.model_validate(datos)
