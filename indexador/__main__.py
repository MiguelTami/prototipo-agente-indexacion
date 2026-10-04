"""Llamado por terminal: python -m indexador --entrada <lote> --salida <carpeta>."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from indexador.corrida import indexar
from indexador.evaluacion import escribir_evaluacion, evaluar
from indexador.traza import traza_terminal


def main(argv: list[str] | None = None) -> int:
    # En Windows, una salida redirigida usa cp1252 y no imprime tildes ni símbolos.
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(prog="indexador", description="Agente de indexación de Learning Catalog")
    parser.add_argument("--entrada", required=True, help="Carpeta del lote (con lote.json)")
    parser.add_argument("--salida", required=True, help="Carpeta donde se crea salida/<runId>/")
    parser.add_argument("--config", default=None, help="Archivo YAML de configuración (opcional)")
    parser.add_argument(
        "--trazar",
        action="store_true",
        help="Muestra lo que devolvió cada nodo y escribe traza.json y traza.md en la salida",
    )
    parser.add_argument(
        "--evaluar",
        action="store_true",
        help="Compara la corrida con las respuestas esperadas y escribe evaluacion.json y evaluacion.md",
    )
    parser.add_argument(
        "--esperado",
        default=None,
        help="Archivo de respuestas esperadas (por defecto, esperado.json dentro de la carpeta de entrada)",
    )
    args = parser.parse_args(argv)

    ruta_esperado = Path(args.esperado) if args.esperado else Path(args.entrada) / "esperado.json"
    if args.evaluar and not ruta_esperado.is_file():
        parser.error(f"no existe el archivo de respuestas esperadas: {ruta_esperado}")

    resultado = indexar(args.entrada, args.salida, args.config, trazar=args.trazar)
    if args.trazar:
        entradas = json.loads((resultado.carpeta / "traza.json").read_text(encoding="utf-8"))
        print(traza_terminal(entradas))
        print()
    t = resultado.reporte.totales
    print(f"Corrida {resultado.runId}")
    print(f"  {t.archivosRecibidos} archivos, {t.contenidosUnicos} contenidos únicos")
    print(f"  {t.archivosProcesados} procesados, {t.archivosVinculados} vinculados, {t.archivosIlegibles} ilegibles")
    print(f"  Salida: {resultado.carpeta}")
    if args.trazar:
        print(f"  Traza completa: {resultado.carpeta / 'traza.md'}")

    if args.evaluar:
        evaluacion = evaluar(resultado.carpeta, ruta_esperado)
        escribir_evaluacion(evaluacion, resultado.carpeta)
        print(f"\nAcuerdo con las respuestas esperadas ({evaluacion.estadoEsperado}):")
        for campo, acuerdo in evaluacion.campos.items():
            if acuerdo.total:
                print(f"  {campo:20} {acuerdo.aciertos:>3}/{acuerdo.total:<3} {acuerdo.porcentaje:>5} %")
        print(f"  Desacuerdos: {len(evaluacion.desacuerdos)} · detalle en {resultado.carpeta / 'evaluacion.md'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
