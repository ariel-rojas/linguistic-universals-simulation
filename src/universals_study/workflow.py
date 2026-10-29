"""Orquesta las simulaciones y escribe los archivos de resultados."""

import json

import pandas as pd

from .covariance import MATRIX_LABELS, create_field_sampler
from .paths import CONFIG_PATH, RESULTS_DIR
from .population import load_population
from .simulation import simulate_worlds

EXPECTED_SETTINGS = {
    "seed",
    "population_simulations",
    "map_iterations",
    "sample_sizes",
    "simulation_prevalences",
    "default_prevalence",
    "simulation_phylogenetic_scale",
    "correlation_structure",
}


def load_settings(path=CONFIG_PATH) -> dict:
    """Lee y valida la configuración de una ejecución."""
    settings = json.loads(path.read_text(encoding="utf-8"))
    if set(settings) != EXPECTED_SETTINGS:
        raise ValueError(f"Claves requeridas: {sorted(EXPECTED_SETTINGS)}")
    for key in ("seed", "population_simulations", "map_iterations"):
        if type(settings[key]) is not int or settings[key] <= 0:
            raise ValueError(f"{key} debe ser un entero positivo")

    scale = settings["simulation_phylogenetic_scale"]
    if isinstance(scale, bool) or not isinstance(scale, (int, float)) or scale < 0:
        raise ValueError("simulation_phylogenetic_scale no puede ser negativa")
    if settings["correlation_structure"] not in MATRIX_LABELS:
        raise ValueError(
            "correlation_structure debe ser una de: "
            + ", ".join(sorted(MATRIX_LABELS))
        )

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
    if settings["seed"] + 10_000 * (len(prevalences) - 1) + 20 >= 2**32:
        raise ValueError("La semilla y sus desplazamientos deben ser menores que 2**32")

    sizes = settings["sample_sizes"]
    if not isinstance(sizes, list) or not sizes:
        raise ValueError("sample_sizes debe ser una lista no vacía")
    if any(type(size) is not int or size <= 0 for size in sizes):
        raise ValueError("Cada tamaño muestral debe ser un entero positivo")
    if sorted(set(sizes)) != sizes:
        raise ValueError("sample_sizes debe estar ordenada y no repetir tamaños")
    if settings["map_iterations"] > settings["population_simulations"]:
        raise ValueError("map_iterations no puede superar population_simulations")
    return settings


def _format_rate(value) -> str:
    """Formatea una tasa; deja un guion si ningún mundo fue elegible."""
    return "—" if value is None else f"{value:.2%}"


def _json_records(frame: pd.DataFrame) -> list[dict]:
    """Convierte los faltantes de pandas en null válido para JSON y JavaScript."""
    safe = frame.astype(object).where(pd.notna(frame), None)
    return safe.to_dict(orient="records")


def run_study(config_path=CONFIG_PATH) -> dict:
    """Simula ambos escenarios para cada p y actualiza mapa e informe."""
    settings = load_settings(config_path)
    population = load_population()
    languages = population.languages
    if max(settings["sample_sizes"]) > len(languages):
        raise ValueError(
            f"Un tamaño muestral supera las {len(languages)} hojas del MCC"
        )

    field_sampler = create_field_sampler(
        settings["correlation_structure"], population.tree, len(languages)
    )
    print(
        f"Generando {len(languages):,} lenguas para "
        f"{len(settings['simulation_prevalences'])} valores de p",
        flush=True,
    )
    simulation = simulate_worlds(population, settings, field_sampler)
    n_mapped = int(languages["latitude"].notna().sum())
    result = {
        "schema_version": 3,
        "project": "Universales lingüísticos bajo dependencia filogenética",
        "status": "complete",
        "created_with_seed": settings["seed"],
        "population": {
            "n_languages": len(languages),
            "n_mapped_languages": n_mapped,
            "n_without_coordinates": len(languages) - n_mapped,
            "unit": "hoja única del árbol MCC, identificada por glottocódigo",
            "tree_release": population.manifest["tree_release"],
            "correlation_structure": settings["correlation_structure"],
            "correlation_label": MATRIX_LABELS[settings["correlation_structure"]],
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
            "Las excepciones se simulan; no son valores observados de una feature.",
            "p es prevalencia marginal configurada, no estimada a partir de datos reales.",
            "El muestreo aleatorio simple no imita el diseño genealógico de una muestra tipológica.",
            "No se incluye geografía, contacto ni transmisión explícita de estados por ramas.",
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
    """Resume cobertura, variación de prevalencia y no detección por p."""
    settings = result["simulation"]["settings"]
    lines = [
        "# Reporte de simulación de universales lingüísticos",
        "",
        f"Semilla: **{result['created_with_seed']}**.",
        f"Población: **{result['population']['n_languages']:,} hojas MCC**; "
        f"{result['population']['n_mapped_languages']:,} ubicadas en el mapa.",
        f"Mundos por escenario y valor de p: **{settings['replicates']:,}**.",
        f"Matriz: **{settings['correlation_label']}**.",
        "",
        "El intervalo central del 95 % muestra la variación entre mundos; "
        "la tasa de no detección se calcula solo en mundos con al menos una excepción.",
        "",
    ]
    for run in result["simulation"]["prevalence_runs"]:
        independent = run["scenarios"]["independent"]
        correlated = run["scenarios"]["phylogenetic"]
        lines += [
            f"## Prevalencia marginal p = {run['prevalence']:.1%}",
            "",
            "### Proporción de excepciones en el mundo completo",
            "",
            "| Escenario | Media | Intervalo central del 95 % |",
            "|---|---:|---:|",
            f"| Independiente | {independent['population_prevalence_mean']:.2%} | "
            f"{independent['population_prevalence_interval_95'][0]:.2%}–"
            f"{independent['population_prevalence_interval_95'][1]:.2%} |",
            f"| R seleccionada | {correlated['population_prevalence_mean']:.2%} | "
            f"{correlated['population_prevalence_interval_95'][0]:.2%}–"
            f"{correlated['population_prevalence_interval_95'][1]:.2%} |",
            "",
            "### Muestras sin excepciones",
            "",
            "| Lenguas observadas | Independiente | R seleccionada | Referencia independiente exacta |",
            "|---:|---:|---:|---:|",
        ]
        for left, right in zip(
            independent["false_universal_by_sample_size"],
            correlated["false_universal_by_sample_size"],
        ):
            lines.append(
                f"| {left['sample_size']:,} | {_format_rate(left['rate'])} "
                f"({left['false_universals']}/{left['eligible_worlds']}) | "
                f"{_format_rate(right['rate'])} ({right['false_universals']}/{right['eligible_worlds']}) | "
                f"{left['exact_independent_reference']:.2%} |"
            )
        lines.append("")
    lines += [
        "## Alcance",
        "",
        "El histograma del visualizador resume la proporción realizada de excepciones "
        "en cada mundo simulado. El mapa usa coordenadas reales; sus etiquetas de "
        "excepción son simuladas.",
        "",
        "Una muestra del tamaño de toda la población equivale a observar el censo "
        "del árbol y, por definición, no puede omitir una excepción que esté en él.",
        "",
        "## Archivos",
        "",
        "- `study.json`: datos de la página interactiva.",
        "- `report.md`: este resumen.",
    ]
    (RESULTS_DIR / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
