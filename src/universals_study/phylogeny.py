"""Lectura del MCC y muestreo eficiente de su correlación Browniana."""

import gzip
import hashlib
import io
import re
import urllib.request
from dataclasses import dataclass

import numpy as np
from Bio import Phylo

from .paths import DATA_DIR

TREE_FILE = DATA_DIR / "global-language-summary-tree-relabelled_cartoonised.tree.gz"
TREE_SHA256 = "35578af18d987e58172c88793b33e8ba60626404bdad246610cd94e73146cb46"
TREE_RELEASE = "v2.0.0"
TREE_URL = (
    "https://github.com/rbouckaert/global-language-tree-pipeline/releases/"
    f"download/{TREE_RELEASE}/global-language-summary-tree-relabelled_cartoonised.tree.gz"
)
EXPECTED_TIPS = 6636


def load_mcc_tree():
    """Carga STATE_1 sin alterar sus ramas y devuelve códigos en orden de hoja.

    El NEXUS usa una tabla Translate con identificadores numéricos. Se resuelve
    explícitamente antes de asociar cada punta a su glottocódigo.
    """
    if not TREE_FILE.exists():
        raise FileNotFoundError(
            "No se encontró el árbol MCC. Ejecuta primero "
            "`uv run universals-study download-data`."
        )
    content = TREE_FILE.read_bytes()
    if hashlib.sha256(content).hexdigest() != TREE_SHA256:
        raise ValueError("El MCC local no coincide con la release fijada")
    with gzip.open(TREE_FILE, "rt", encoding="utf-8") as handle:
        source = handle.read()

    # Las anotaciones NEXUS no son longitudes de rama; Bio.Phylo recibe solo
    # el Newick estructural, conservando los números de rama publicados.
    clean = re.sub(r"\[[^\[\]]*\]", "", source)
    translation = re.search(r"(?is)\btranslate\s+(.*?);", clean)
    if translation is None:
        raise ValueError("El archivo MCC no contiene la tabla Translate esperada")
    labels = dict(re.findall(r"(\d+)\s+([^,\s]+)", translation.group(1)))
    trees = dict(re.findall(r"(?i)\btree\s+(\w+)\s*=\s*([^;]+);", clean))
    if set(trees) != {"STATE_1", "STATE_0"} or trees["STATE_1"] != trees["STATE_0"]:
        raise ValueError("El archivo ya no contiene las dos copias MCC esperadas")

    tree = Phylo.read(io.StringIO(trees["STATE_1"] + ";"), "newick")
    codes = []
    source_labels = {}
    for tip in tree.get_terminals():
        source_label = labels.get(tip.name, "")
        match = re.match(r"^([a-z]{4}[0-9]{4})_", source_label)
        if match is None:
            raise ValueError(f"Punta MCC sin glottocódigo reconocible: {source_label!r}")
        code = match.group(1)
        if code in source_labels:
            raise ValueError(f"Glottocódigo repetido en el MCC: {code}")
        tip.name = code
        codes.append(code)
        source_labels[code] = source_label

    if len(codes) != EXPECTED_TIPS:
        raise ValueError(f"Se esperaban {EXPECTED_TIPS} hojas y se leyeron {len(codes)}")
    tree.rooted = True
    return tree, codes, source_labels


def download_mcc_tree() -> None:
    """Descarga el MCC oficial y comprueba su huella antes de guardarlo."""
    TREE_FILE.parent.mkdir(parents=True, exist_ok=True)
    temporary_file = TREE_FILE.with_suffix(TREE_FILE.suffix + ".download")
    try:
        urllib.request.urlretrieve(TREE_URL, temporary_file)
        content = temporary_file.read_bytes()
        if hashlib.sha256(content).hexdigest() != TREE_SHA256:
            raise ValueError("La huella del árbol descargado no coincide con la release")
        temporary_file.replace(TREE_FILE)
    finally:
        temporary_file.unlink(missing_ok=True)


@dataclass
class BrownianTreeSampler:
    """Muestrea N(0, R) recorriendo las ramas, sin construir una matriz densa.

    Cada rama aporta un incremento normal independiente con varianza igual a
    su longitud. Luego cada punta se divide por su profundidad raíz-punta. Esto
    genera exactamente R_ij = C_ij / sqrt(C_ii C_jj), donde C es el tiempo de
    rama compartido del MCC.
    """

    parent_indices: np.ndarray
    branch_standard_deviations: np.ndarray
    tip_indices: np.ndarray
    tip_standard_deviations: np.ndarray

    @classmethod
    def from_tree(cls, tree):
        """Prepara índices topológicos en un único recorrido del árbol."""
        nodes = list(tree.find_clades(order="preorder"))
        node_indices = {node: index for index, node in enumerate(nodes)}
        parents = np.full(len(nodes), -1, dtype=np.int32)
        branch_sd = np.zeros(len(nodes), dtype=np.float64)
        depths = np.zeros(len(nodes), dtype=np.float64)
        for parent_index, parent in enumerate(nodes):
            for child in parent.clades:
                parents[node_indices[child]] = parent_index

        for index, node in enumerate(nodes[1:], start=1):
            parent = int(parents[index])
            if parent < 0:
                raise ValueError("No se pudo recuperar la relación padre-hijo del MCC")
            length = node.branch_length
            if length is None or not np.isfinite(length) or length < 0:
                raise ValueError("El MCC tiene una longitud de rama inválida")
            parents[index] = parent
            branch_sd[index] = np.sqrt(length)
            depths[index] = depths[parent] + length

        tips = list(tree.get_terminals())
        tip_indices = np.asarray([node_indices[tip] for tip in tips], dtype=np.int32)
        tip_depths = depths[tip_indices]
        if np.any(tip_depths <= 0):
            raise ValueError("Una punta del MCC tiene profundidad nula")
        return cls(parents, branch_sd, tip_indices, np.sqrt(tip_depths))

    @property
    def size(self) -> int:
        """Cantidad de lenguas (hojas) del árbol."""
        return len(self.tip_indices)

    def draw(self, rng: np.random.Generator) -> np.ndarray:
        """Genera una realización estandarizada del campo filogenético."""
        increments = rng.standard_normal(len(self.parent_indices)) * self.branch_standard_deviations
        values = np.zeros(len(self.parent_indices), dtype=np.float64)
        for index in range(1, len(values)):
            values[index] = values[self.parent_indices[index]] + increments[index]
        return values[self.tip_indices] / self.tip_standard_deviations
