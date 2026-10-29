"""Une las hojas completas del MCC con nombres y coordenadas disponibles."""

import hashlib
import json
from dataclasses import dataclass

import pandas as pd

from .paths import DATA_DIR
from .phylogeny import load_mcc_tree


@dataclass(frozen=True)
class Population:
    """Población ordenada como las hojas del árbol para simular el campo."""

    languages: pd.DataFrame
    tree: object
    manifest: dict


def _valid_coordinates(row: dict, latitude_key: str, longitude_key: str):
    """Devuelve un par de coordenadas válido o None si la fuente no lo da."""
    try:
        latitude = float(row[latitude_key])
        longitude = float(row[longitude_key])
    except (KeyError, TypeError, ValueError):
        return None
    if not (-90 <= latitude <= 90 and -180 <= longitude <= 180):
        return None
    return latitude, longitude


def _check_source_hashes(manifest: dict) -> None:
    """Detecta cambios en los archivos de entrada registrados."""
    for filename, expected_hash in manifest["source_sha256"].items():
        source_path = DATA_DIR / filename
        if not source_path.is_file():
            if filename.startswith("global-language-summary-tree-"):
                raise FileNotFoundError(
                    "No se encontró el árbol MCC. Ejecuta "
                    "`uv run universals-study download-data`."
                )
            raise FileNotFoundError(f"Falta el archivo de datos requerido: {source_path}")
        observed_hash = hashlib.sha256(source_path.read_bytes()).hexdigest()
        if observed_hash != expected_hash:
            raise ValueError(f"Cambió el archivo de entrada {filename}; revisa el manifiesto")


def _assemble_languages(codes: list[str], labels: dict[str, str]) -> pd.DataFrame:
    """Crea una fila por hoja MCC y añade los metadatos de Glottolog."""
    geo = pd.read_csv(
        DATA_DIR / "glottolog_5_3_languages_and_dialects_geo.csv",
        keep_default_na=False,
    )
    geo_by_code = {}
    for row in geo.to_dict(orient="records"):
        code = row.get("glottocode", "")
        if code and (code not in geo_by_code or _valid_coordinates(
            row, "latitude", "longitude"
        )):
            geo_by_code[code] = row

    rows = []
    for tip_index, code in enumerate(codes):
        geo_row = geo_by_code.get(code, {})
        geo_coordinates = _valid_coordinates(geo_row, "latitude", "longitude")
        coordinate_source = "Glottolog" if geo_coordinates else "Sin coordenadas"
        source_label = labels[code]
        fallback_name = source_label.split("_", 1)[1].split("_", 1)[0]
        rows.append(
            {
                "tip_index": tip_index,
                "glottocode": code,
                "name": geo_row.get("name") or fallback_name,
                "macroarea": geo_row.get("macroarea", ""),
                "latitude": geo_coordinates[0] if geo_coordinates else None,
                "longitude": geo_coordinates[1] if geo_coordinates else None,
                "coordinate_source": coordinate_source,
            }
        )
    languages = pd.DataFrame(rows)
    if languages["glottocode"].duplicated().any():
        raise ValueError("El MCC debe contener glottocódigos únicos")
    return languages


def load_population() -> Population:
    """Lee fuentes locales y conserva las 6.636 hojas en orden MCC."""
    manifest = json.loads((DATA_DIR / "manifest.json").read_text(encoding="utf-8"))
    _check_source_hashes(manifest)
    tree, codes, labels = load_mcc_tree()
    if len(codes) != manifest["n_tree_tips"]:
        raise ValueError("La cantidad de hojas MCC no coincide con el manifiesto")
    languages = _assemble_languages(codes, labels)
    expected = manifest["expected_matches"]
    mapped = int(languages["latitude"].notna().sum())
    if mapped != expected["tree_languages_with_coordinates"]:
        raise ValueError("La cobertura de coordenadas no coincide con el manifiesto")
    if len(languages) - mapped != expected["tree_languages_without_coordinates"]:
        raise ValueError("La cantidad de hojas sin coordenadas no coincide con el manifiesto")
    return Population(languages, tree, manifest)
