"""Genera mundos simulados para comparar tres estructuras de dependencia."""

import numpy as np
from scipy.special import ndtr, ndtri

SCENARIO_LABELS = {
    "independent": "Lenguas independientes",
    "phylogenetic": "Árbol MCC",
    "all_correlated": "R perfectamente correlacionada",
}


def probit_intercept(prevalence: float, field_scale: float) -> float:
    """Calibra el intercepto para conservar la prevalencia marginal p.

    Si f_i ~ Normal(0, field_scale²), entonces E[Phi(alpha + f_i)] es igual a
    Phi(alpha / sqrt(1 + field_scale²)). Se elige alpha para que esa esperanza
    sea p; cada mundo todavía puede tener una proporción distinta de excepciones.
    """
    if not 0 < prevalence < 1 or field_scale < 0:
        raise ValueError("La prevalencia debe estar en (0, 1) y la escala >= 0")
    return float(np.sqrt(1 + field_scale**2) * ndtri(prevalence))


def draw_world(
    *,
    size: int,
    rng: np.random.Generator,
    prevalence: float,
    field_scale: float = 0.0,
    field_sampler=None,
) -> tuple[np.ndarray, np.ndarray]:
    """Genera las etiquetas binarias y sus probabilidades condicionales."""
    if field_sampler is None:
        probabilities = np.full(size, prevalence, dtype=np.float64)
    else:
        latent_field = field_scale * field_sampler.draw(rng)
        if latent_field.shape != (size,):
            raise ValueError("El campo latente no coincide con el tamaño de la población")
        intercept = probit_intercept(prevalence, field_scale)
        probabilities = ndtr(intercept + latent_field)
    labels = rng.binomial(1, probabilities).astype(np.int8)
    return labels, probabilities


def _simulate_scenario(
    *,
    scenario: str,
    n_replicates: int,
    map_iterations: int,
    population_size: int,
    prevalence: float,
    field_scale: float,
    field_sampler,
    tip_ids: list[str],
    seed: int,
) -> dict:
    """Simula los mundos de un escenario y conserva los primeros para el mapa."""
    rng = np.random.default_rng(seed)
    prevalence_draws = np.empty(n_replicates, dtype=np.float64)
    map_worlds = []

    for replicate in range(n_replicates):
        labels, _ = draw_world(
            size=population_size,
            rng=rng,
            prevalence=prevalence,
            field_scale=field_scale,
            field_sampler=field_sampler,
        )
        world_prevalence = float(labels.mean())
        prevalence_draws[replicate] = world_prevalence

        if replicate < map_iterations:
            map_worlds.append(
                {
                    "iteration": replicate + 1,
                    "exceptions": [tip_ids[i] for i in np.flatnonzero(labels)],
                    "n_exceptions": int(labels.sum()),
                    "population_prevalence": world_prevalence,
                }
            )

    return {
        "label": SCENARIO_LABELS[scenario],
        "scenario": scenario,
        "population_prevalence_mean": float(prevalence_draws.mean()),
        "population_prevalence_interval_95": [
            float(np.quantile(prevalence_draws, 0.025)),
            float(np.quantile(prevalence_draws, 0.975)),
        ],
        "population_prevalence_draws": prevalence_draws.tolist(),
        "iterations": map_worlds,
    }


def simulate_worlds(population, settings: dict, field_samplers: dict) -> dict:
    """Compara independencia, la R del MCC y la R perfectamente correlacionada."""
    tip_ids = population.languages["glottocode"].tolist()
    population_size = len(tip_ids)
    scenario_samplers = {
        "independent": None,
        "phylogenetic": field_samplers["phylogenetic"],
        "all_correlated": field_samplers["all_correlated"],
    }
    prevalence_runs = []

    for prevalence_index, prevalence in enumerate(settings["simulation_prevalences"]):
        scenarios = {}
        seed_offset = settings["seed"] + prevalence_index * 10_000
        for scenario_index, (scenario, sampler) in enumerate(scenario_samplers.items()):
            scenarios[scenario] = _simulate_scenario(
                scenario=scenario,
                n_replicates=settings["population_simulations"],
                map_iterations=settings["map_iterations"],
                population_size=population_size,
                prevalence=prevalence,
                field_scale=settings["simulation_phylogenetic_scale"],
                field_sampler=sampler,
                tip_ids=tip_ids,
                seed=seed_offset + (scenario_index + 1) * 100,
            )
        prevalence_runs.append({"prevalence": prevalence, "scenarios": scenarios})

    return {
        "settings": {
            "replicates": settings["population_simulations"],
            "prevalences": settings["simulation_prevalences"],
            "phylogenetic_field_scale": settings["simulation_phylogenetic_scale"],
            "scenario_labels": SCENARIO_LABELS,
        },
        "prevalence_runs": prevalence_runs,
    }
