"""Llamado por terminal: python -m indexador --entrada <lote> --salida <carpeta>."""

from __future__ import annotations

import argparse
import sys

from indexador.corrida import indexar


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="indexador", description="Agente de indexación de Learning Catalog")
    parser.add_argument("--entrada", required=True, help="Carpeta del lote (con lote.json)")
    parser.add_argument("--salida", required=True, help="Carpeta donde se crea salida/<runId>/")
    parser.add_argument("--config", default=None, help="Archivo YAML de configuración (opcional)")
    args = parser.parse_args(argv)

    resultado = indexar(args.entrada, args.salida, args.config)
    t = resultado.reporte.totales
    print(f"Corrida {resultado.runId}")
    print(f"  {t.archivosRecibidos} archivos, {t.contenidosUnicos} contenidos únicos")
    print(f"  {t.archivosProcesados} procesados, {t.archivosIlegibles} ilegibles")
    print(f"  Salida: {resultado.carpeta}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
