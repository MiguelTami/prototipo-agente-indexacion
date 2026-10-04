"""El único punto de entrada del agente: indexar(entrada, salida)."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from indexador.config import Config, cargar_config
from indexador.esquemas.entrada import cargar_entrada
from indexador.esquemas.reporte import Reporte
from indexador.grafo import GRAFO_LOTE


@dataclass(frozen=True)
class ResultadoCorrida:
    runId: str
    carpeta: Path
    reporte: Reporte


def _nuevo_run_id(ahora: datetime) -> str:
    return f"{ahora:%Y%m%dT%H%M%SZ}-{uuid.uuid4().hex[:6]}"


def indexar(
    entrada: str | Path,
    salida: str | Path,
    config: Config | str | Path | None = None,
    trazar: bool = False,
) -> ResultadoCorrida:
    """Procesa la carpeta de entrada y escribe salida/<runId>/.

    Cada corrida crea su propia carpeta y nunca sobrescribe una anterior. Con trazar=True escribe
    además traza.json y traza.md: lo que devolvió cada nodo, contenido por contenido.
    """
    if not isinstance(config, Config):
        config = cargar_config(config)
    lote = cargar_entrada(entrada)

    ahora = datetime.now(timezone.utc)
    run_id = _nuevo_run_id(ahora)
    carpeta = Path(salida) / run_id
    carpeta.mkdir(parents=True, exist_ok=False)

    final = GRAFO_LOTE.invoke(
        {
            "entrada": lote,
            "config": config,
            "runId": run_id,
            "inicio": ahora.isoformat(timespec="seconds"),
            "carpetaSalida": str(carpeta),
            "trazar": trazar,
        }
    )
    return ResultadoCorrida(runId=run_id, carpeta=carpeta, reporte=final["reporte"])
