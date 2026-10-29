"""Orquesta la simulación y escribe resultados legibles para la página."""

import json

import pandas as pd

from .covariance import create_field_sampler
from .paths import CONFIG_PATH, RESULTS_DIR
from .population import load_population
from .simulation import SCENARIO_LABELS, simulate_worlds

EXPECTED_SETTINGS = {
    "seed",
    "population_simulations",
    "map_iterations",
    "simulation_prevalences",
    "default_prevalence",
    "simulation_phylogenetic_scale",
}


def load_settings(path=CONFIG_PATH) -> dict:
    """Lee y valida la configuración antes de iniciar una ejecución."""
    settings = json.loads(path.read_text(encoding="utf-8"))
    if set(settings) != EXPECTED_SETTINGS:
        raise ValueError(f"Claves requeridas: {sorted(EXPECTED_SETTINGS)}")

    for key in ("seed", "population_simulations", "map_iterations"):
        if type(settings[key]) is not int or settings[key] <= 0:
            raise ValueError(f"{key} debe ser un entero positivo")

    scale = settings["simulation_phylogenetic_scale"]
    if isinstance(scale, bool) or not isinstance(scale, (int, float)) or scale < 0:
        raise ValueError("simulation_phylogenetic_scale no puede ser negativa")

    prevalences = settings["simulation_prevalences"]
    if not isinstance(prevalences, list) or not prevalences:
        raise ValueError("simulation_prevalences debe ser una lista no vacía")
    if any(
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not 0 < value < 1
        for value in prevalences
    ):
        raise ValueError("Cada prevalencia debe estar entre 0 y 1")
    if sorted(set(prevalences)) != prevalences:
        raise ValueError("simulation_prevalences debe estar ordenada y sin repeticiones")
    if settings["default_prevalence"] not in prevalences:
        raise ValueError("default_prevalence debe estar incluido en simulation_prevalences")

    largest_seed_offset = 10_000 * (len(prevalences) - 1) + 300
    if settings["seed"] + largest_seed_offset >= 2**32:
        raise ValueError("La semilla y sus desplazamientos deben ser menores que 2**32")
    if settings["map_iterations"] > settings["population_simulations"]:
        raise ValueError("map_iterations no puede superar population_simulations")
    return settings


def _json_records(frame: pd.DataFrame) -> list[dict]:
    """Convierte los valores faltantes de pandas en null válido para JSON."""
    safe = frame.astype(object).where(pd.notna(frame), None)
    return safe.to_dict(orient="records")


def run_study(config_path=CONFIG_PATH) -> dict:
    """Genera la población y compara tres escenarios para cada valor de p."""
    settings = load_settings(config_path)
    population = load_population()
    languages = population.languages
    field_samplers = {
        "phylogenetic": create_field_sampler(
            "tree_global", population.tree, len(languages)
        ),
        "all_correlated": create_field_sampler(
            "all_correlated", population.tree, len(languages)
        ),
    }

    print(
        f"Generando {len(languages):,} lenguas, "
        f"{len(settings['simulation_prevalences'])} valores de p "
        "y tres escenarios de dependencia",
        flush=True,
    )
    simulation = simulate_worlds(population, settings, field_samplers)
    n_mapped = int(languages["latitude"].notna().sum())
    result = {
        "schema_version": 4,
        "project": "Universales lingüísticos bajo dependencia filogenética",
        "status": "complete",
        "created_with_seed": settings["seed"],
        "population": {
            "n_languages": len(languages),
            "n_mapped_languages": n_mapped,
            "n_without_coordinates": len(languages) - n_mapped,
            "unit": "hoja única del árbol MCC, identificada por glottocódigo",
            "tree_release": population.manifest["tree_release"],
            "scenario_labels": SCENARIO_LABELS,
            "coverage_note": (
                "Todas las hojas del MCC forman la población. Los nombres y las "
                "coordenadas disponibles proceden de Glottolog 5.3. Diez hojas no "
                "tienen coordenadas publicadas y no se dibujan."
            ),
            "languages": _json_records(languages),
        },
        "simulation": simulation,
        "settings": settings,
        "interpretation_limits": [
            "Las excepciones se simulan; no son valores observados de una característica lingüística.",
            "p es una prevalencia marginal configurada, no una estimación a partir de datos reales.",
            "La población corresponde a las hojas del árbol MCC y no a un censo de todas las lenguas vivas.",
            "No se incluyen geografía, contacto ni transmisión explícita de estados por ramas.",
            "El árbol y las longitudes de sus ramas se tratan como conocidos.",
        ],
    }

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    (RESULTS_DIR / "study.json").write_text(
        json.dumps(result, ensure_ascii=False, separators=(",", ":")),
        encoding="utf-8",
    )
    _write_report(result)
    return result


def _write_report(result: dict) -> None:
    """Resume la variación simulada de la proporción de excepciones."""
    settings = result["simulation"]["settings"]
    lines = [
        "# Reporte de simulación de universales lingüísticos",
        "",
        f"Semilla: **{result['created_with_seed']}**.",
        f"Población: **{result['population']['n_languages']:,} hojas MCC**; "
        f"{result['population']['n_mapped_languages']:,} ubicadas en el mapa.",
        f"Mundos por escenario y valor de p: **{settings['replicates']:,}**.",
        "",
        "La tabla muestra la media y el intervalo central del 95 % de la proporción "
        "realizada de excepciones entre los mundos simulados.",
        "",
    ]
    for run in result["simulation"]["prevalence_runs"]:
        lines += [
            f"## Prevalencia marginal p = {run['prevalence']:.1%}",
            "",
            "| Escenario | Media | Intervalo central del 95 % |",
            "|---|---:|---:|",
        ]
        for scenario, summary in run["scenarios"].items():
            low, high = summary["population_prevalence_interval_95"]
            lines.append(
                f"| {summary['label']} | "
                f"{summary['population_prevalence_mean']:.2%} | {low:.2%}–{high:.2%} |"
            )
        lines.append("")

    lines += [
        "## Interpretación",
        "",
        "La prevalencia marginal p es la media esperada a través de muchos mundos. "
        "La proporción observada cambia de mundo a mundo; las estructuras de "
        "correlación determinan cuánto varía.",
        "",
        "El mapa usa coordenadas de lenguas reales y colores simulados. La línea del "
        "histograma indica la proporción del mundo que está visible en el mapa.",
        "",
        "## Archivos",
        "",
        "- study.json: datos que consume la página interactiva.",
        "- report.md: este resumen.",
    ]
    (RESULTS_DIR / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
