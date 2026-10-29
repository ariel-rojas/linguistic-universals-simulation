"""Comandos para ejecutar la simulación y servir la página local."""

import argparse
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

from .paths import PROJECT_ROOT
from .phylogeny import download_mcc_tree
from .workflow import run_study


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Simulación de universales bajo dependencia filogenética"
    )
    commands = parser.add_subparsers(dest="command", required=True)
    run = commands.add_parser("run", help="Ejecutar las simulaciones")
    run.add_argument("--config", default="config/study.json")
    commands.add_parser("download-data", help="Descargar el árbol MCC de la release oficial")
    serve = commands.add_parser("serve", help="Servir la página interactiva en local")
    serve.add_argument("--host", default="127.0.0.1")
    serve.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()

    if args.command == "run":
        path = PROJECT_ROOT / args.config
        result = run_study(path)
        print(f"Resultados guardados en {PROJECT_ROOT / 'results'}")
        print(f"Lenguas simuladas: {result['population']['n_languages']}")
        return

    if args.command == "download-data":
        download_mcc_tree()
        print(f"Árbol descargado y verificado: {PROJECT_ROOT / 'data' / 'global-language-summary-tree-relabelled_cartoonised.tree.gz'}")
        return

    handler = partial(SimpleHTTPRequestHandler, directory=str(PROJECT_ROOT))
    server = ThreadingHTTPServer((args.host, args.port), handler)
    print(f"Abrí http://{args.host}:{args.port}/site/ en el navegador")
    print("Detené el servidor con Ctrl+C")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nServidor detenido")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
