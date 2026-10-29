"""Rutas del proyecto, definidas desde la ubicación del paquete."""

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "data"
CONFIG_PATH = PROJECT_ROOT / "config" / "study.json"
RESULTS_DIR = PROJECT_ROOT / "results"
SITE_DIR = PROJECT_ROOT / "site"
