"""Mundos binarios simulados y detección de excepciones en muestras."""

from collections.abc import Iterable

import numpy as np
from scipy.special import ndtr, ndtri

from .covariance import MATRIX_LABELS


def probit_intercept(prevalence: float, field_scale: float) -> float:
    """Calibra el intercepto para que la prevalencia marginal sea p.

    Si f_i ~ Normal(0, field_scale**2), entonces
    E[Phi(intercepto + f_i)] = Phi(intercepto / sqrt(1 + field_scale**2)).
    Por eso este intercepto conserva p al cambiar la dependencia.
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
    """Genera un mundo de lenguas y las probabilidades condicionales.

    Sin generador latente, las etiquetas son Bernoulli independientes. Con un
    generador, se obtiene un campo normal correlacionado y se aplica el enlace
    probit. La marginal de cada lengua es prevalence en ambos casos.
    """
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


def _scenario_iterations(
    *,
    scenario: str,
    n_replicates: int,
    map_iterations: int,
    sample_sizes: Iterable[int],
    population_size: int,
    prevalence: float,
    field_scale: float,
    field_sampler,
    tip_ids: list[str],
    seed: int,
) -> dict:
    rng = np.random.default_rng(seed)
    sizes = [int(value) for value in sample_sizes]
    counts = {size: {"eligible_worlds": 0, "false_universals": 0} for size in sizes}
    population_rates = []
    examples = []
    stored = min(map_iterations, n_replicates)
    for replicate in range(n_replicates):
        labels, _ = draw_world(
            size=population_size,
            rng=rng,
            prevalence=prevalence,
            field_scale=field_scale,
            field_sampler=field_sampler,
        )
        has_exception = bool(labels.any())
        population_rates.append(float(labels.mean()))
        permutation = rng.permutation(population_size)
        for size in sizes:
            if has_exception:
                counts[size]["eligible_worlds"] += 1
                if labels[permutation[:size]].sum() == 0:
                    counts[size]["false_universals"] += 1
        if replicate < stored:
            examples.append(
                {
                    "iteration": replicate + 1,
                    "exceptions": [tip_ids[i] for i in np.flatnonzero(labels)],
                    "n_exceptions": int(labels.sum()),
                    "population_prevalence": float(labels.mean()),
                }
            )
    summary = []
    for size in sizes:
        eligible = counts[size]["eligible_worlds"]
        events = counts[size]["false_universals"]
        rate = events / eligible if eligible else None
        summary.append(
            {
                "sample_size": size,
                "eligible_worlds": eligible,
                "false_universals": events,
                "rate": rate,
                "exact_independent_reference": (
                    float(
                        ((1 - prevalence) ** size - (1 - prevalence) ** population_size)
                        / (1 - (1 - prevalence) ** population_size)
                    )
                    if scenario == "independent"
                    else None
                ),
            }
        )
    return {
        "label": "Independiente" if scenario == "independent" else "R seleccionada",
        "scenario": scenario,
        "population_prevalence_mean": float(np.mean(population_rates)),
        "population_prevalence_interval_95": [
            float(np.quantile(population_rates, 0.025)),
            float(np.quantile(population_rates, 0.975)),
        ],
        "population_prevalence_draws": population_rates,
        "false_universal_by_sample_size": summary,
        "iterations": examples,
    }


def simulate_worlds(population, settings: dict, field_sampler) -> dict:
    """Compara mundos por prevalencia y conserva iteraciones para el mapa."""
    tip_ids = population.languages["glottocode"].tolist()
    population_size = len(tip_ids)
    prevalence_runs = []
    for prevalence_index, prevalence in enumerate(settings["simulation_prevalences"]):
        common = {
            "n_replicates": settings["population_simulations"],
            "map_iterations": settings["map_iterations"],
            "sample_sizes": settings["sample_sizes"],
            "population_size": population_size,
            "prevalence": prevalence,
            "field_scale": settings["simulation_phylogenetic_scale"],
            "tip_ids": tip_ids,
        }
        seed_offset = prevalence_index * 10_000
        prevalence_runs.append(
            {
                "prevalence": prevalence,
                "scenarios": {
                    "independent": _scenario_iterations(
                        scenario="independent",
                        field_sampler=None,
                        seed=settings["seed"] + seed_offset + 10,
                        **common,
                    ),
                    "phylogenetic": _scenario_iterations(
                        scenario="phylogenetic",
                        field_sampler=field_sampler,
                        seed=settings["seed"] + seed_offset + 20,
                        **common,
                    ),
                },
            }
        )
    return {
        "settings": {
            "replicates": settings["population_simulations"],
            "sample_sizes": settings["sample_sizes"],
            "prevalences": settings["simulation_prevalences"],
            "phylogenetic_field_scale": settings["simulation_phylogenetic_scale"],
            "correlation_structure": settings["correlation_structure"],
            "correlation_label": MATRIX_LABELS[settings["correlation_structure"]],
            "sampling": "muestra aleatoria simple sin reemplazo",
            "event": "la muestra no ve excepciones aunque el mundo sí contiene alguna",
        },
        "prevalence_runs": prevalence_runs,
    }
