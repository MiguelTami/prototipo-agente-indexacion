"""El lote de ejemplo es válido y cubre los casos que el plan necesita."""

from __future__ import annotations

from actualizar_hashes import hash_esperado

from indexador.esquemas.entrada import ESTADOS_CON_MARKDOWN, cargar_entrada


def _por_id(entrada):
    return {a.sourceIdentifier: a for a in entrada.lote.archivos}


def test_el_lote_valida_contra_los_esquemas(carpeta_lote):
    entrada = cargar_entrada(carpeta_lote)
    assert len(entrada.lote.archivos) == 14
    assert entrada.lote.offeringId == entrada.contexto.cursoDictado.id


def test_doce_archivos_reales_y_dos_casos_sinteticos(carpeta_lote):
    archivos = cargar_entrada(carpeta_lote).lote.archivos
    reales = [a for a in archivos if not a.sourceIdentifier.startswith("sim-")]
    assert len(reales) == 12
    assert all(a.sintetico for a in archivos), "todo el contenido del lote es sintético"


def test_los_tres_ra_del_curso(carpeta_lote):
    ras = cargar_entrada(carpeta_lote).contexto.resultadosAprendizaje
    assert [(r.code, r.bloomLevel) for r in ras] == [
        ("RA-01", "Evaluate"),
        ("RA-02", "Analyze"),
        ("RA-03", "Create"),
    ]


def test_los_hashes_corresponden_al_contenido(carpeta_lote):
    for archivo in cargar_entrada(carpeta_lote).lote.archivos:
        esperado = hash_esperado(carpeta_lote, archivo.model_dump())
        assert archivo.core.contentHash == esperado, f"hash desactualizado: {archivo.sourceIdentifier}"


def test_caso_duplicado(carpeta_lote):
    archivos = _por_id(cargar_entrada(carpeta_lote))
    assert archivos["4542265"].core.contentHash == archivos["sim-0001"].core.contentHash
    assert archivos["4542265"].modulo != archivos["sim-0001"].modulo


def test_caso_elemento_ya_conocido(carpeta_lote):
    entrada = cargar_entrada(carpeta_lote)
    conocidos = {e.contentHash for e in entrada.catalogo.elementos}
    assert _por_id(entrada)["4542268"].core.contentHash in conocidos


def test_casos_ilegibles_y_truncado(carpeta_lote):
    archivos = _por_id(cargar_entrada(carpeta_lote))
    assert archivos["4542267"].core.markdownStatus == "unsupported"
    assert archivos["4542281"].core.markdownStatus == "failed"
    assert archivos["sim-0002"].core.markdownStatus in ESTADOS_CON_MARKDOWN
    assert (carpeta_lote / archivos["sim-0002"].markdownPath).read_text(encoding="utf-8").strip().startswith("## Página")
    assert archivos["4542275"].core.markdownTruncated is True
