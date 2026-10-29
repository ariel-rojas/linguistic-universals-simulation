"""Alternativas de correlación para el campo latente simulado."""

from dataclasses import dataclass

import numpy as np

from .phylogeny import BrownianTreeSampler

MATRIX_LABELS = {
    "tree_global": "Árbol MCC completo, sin bloquear familias",
    "all_correlated": "Correlación global perfecta (extremo didáctico)",
}


@dataclass(frozen=True)
class GlobalCorrelationSampler:
    """Representa R = 11ᵀ sin construir ni factorizar la matriz de unos."""

    size: int

    def draw(self, rng: np.random.Generator) -> np.ndarray:
        """Todas las lenguas reciben el mismo efecto normal en una iteración."""
        return np.full(self.size, rng.standard_normal(), dtype=np.float64)


def create_field_sampler(structure: str, tree, size: int):
    """Crea el generador del campo latente para la estructura seleccionada."""
    if structure == "tree_global":
        return BrownianTreeSampler.from_tree(tree)
    if structure == "all_correlated":
        return GlobalCorrelationSampler(size)
    raise ValueError(
        f"Estructura desconocida: {structure!r}. Opciones: {sorted(MATRIX_LABELS)}"
    )
