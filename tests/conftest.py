from __future__ import annotations

import sys
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "scripts"))

LOTE_EJEMPLO = RAIZ / "ejemplos" / "curso-412711"


@pytest.fixture
def carpeta_lote() -> Path:
    return LOTE_EJEMPLO
