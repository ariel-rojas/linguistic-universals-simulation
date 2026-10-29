# Universales lingüísticos bajo dependencia

> Experimento reproducible para estudiar cómo el parentesco entre lenguas afecta lo que una muestra puede hacer parecer universal.

## Qué hace

El programa simula mundos de lenguas con una prevalencia configurada de excepciones y compara dos escenarios:

- **Independiente:** cada lengua desarrolla una excepción mediante un sorteo separado.
- **Filogenético:** las propensiones a la excepción se correlacionan según las ramas compartidas del árbol MCC.

En cada mundo se toman muestras aleatorias y se calcula cuántas no encuentran excepciones. La página interactiva permite recorrer mundos, comparar escenarios y ver la proporción de excepciones de cada simulación.

Las excepciones y sus colores son simulados. El proyecto no estima la prevalencia de un rasgo real ni representa observaciones de OV/VO.

## Visualizador

La [página interactiva](https://ariel-rojas.github.io/linguistic-universals-simulation/) permite explorar los resultados guardados en este repositorio.

## Datos

- **Población y parentesco:** 6.636 hojas del árbol MCC de *Global Language Tree Pipeline*, versión 2.0.0. El archivo se descarga desde la release original con el comando de preparación y se verifica mediante su huella digital. No se incluye una copia del árbol en este repositorio.
- **Nombres y mapa:** Glottolog 5.3, archivo `languages_and_dialects_geo.csv`. Se usan sus nombres, macroáreas y coordenadas; 6.626 hojas tienen coordenadas publicadas. Diez participan en la simulación pero no aparecen en el mapa.
- **WALS:** no es una entrada del modelo ni del mapa. Se había usado para completar coordenadas y nombres, pero no añadía información necesaria para la simulación. La población y la matriz de parentesco vienen del MCC; Glottolog alcanza la cobertura geográfica indicada.

El árbol y sus datos pertenecen a sus respectivas fuentes. El repositorio upstream indica que su licencia de código no cubre automáticamente los archivos de las releases; por eso el árbol se descarga de allí. Glottolog se distribuye bajo **CC BY 4.0**. Consulta las fuentes originales antes de reutilizar los datos.

## Preparar y ejecutar

Requisitos: Python 3.12 o posterior y [uv](https://docs.astral.sh/uv/).

Desde la carpeta del proyecto, en PowerShell:

```powershell
uv sync --locked
uv run universals-study download-data
uv run universals-study run
uv run universals-study serve
```

La última orden inicia el servidor local. Abre `http://127.0.0.1:8000/site/` y detenlo con `Ctrl+C`.

`download-data` guarda el árbol MCC en `data/` tras comprobar que corresponde a la versión esperada. Hace falta conexión a Internet solo para descargarlo. La simulación produce `results/study.json` (usado por la web) y `results/report.md`.

## Ajustes principales

Edita `config/study.json` y vuelve a ejecutar `uv run universals-study run`.

| Parámetro | Para qué sirve |
|---|---|
| `simulation_prevalences` | Valores de prevalencia marginal `p` que se comparan. |
| `default_prevalence` | Valor seleccionado inicialmente en la página. |
| `sample_sizes` | Cantidades de lenguas sorteadas en cada muestra; máximo actual: 6.636. |
| `population_simulations` | Mundos simulados por escenario y por valor de `p`. |
| `map_iterations` | Mundos guardados para recorrer en el mapa. |
| `simulation_phylogenetic_scale` | Amplitud del efecto correlacionado. |
| `correlation_structure` | `tree_global` usa el MCC; `all_correlated` es el extremo donde todas las hojas comparten el mismo efecto. |
| `seed` | Semilla para reproducir los sorteos. |

El costo de ejecución aumenta con el número de valores de `p`, mundos simulados y tamaños muestrales.

## Cómo interpretar los resultados

El campo filogenético `f` se genera a partir de los incrementos aleatorios de las ramas compartidas. Para cada lengua `i`, el modelo transforma `α + fᵢ` en una probabilidad `qᵢ` mediante la distribución normal estándar y luego sortea si hay excepción. La constante `α` se calibra para que `p` sea la prevalencia marginal esperada al promediar mundos; no obliga a que cada mundo tenga exactamente esa proporción.

La matriz filogenética es una correlación Browniana derivada del árbol: lenguas que comparten más historia tienen efectos latentes más parecidos. No se incluyen geografía ni contacto. La muestra aleatoria simple aísla el efecto del tamaño, pero no imita los diseños tipológicos que controlan parentesco o región.

La población corresponde a las hojas de este árbol y no es un censo de todas las lenguas vivas. Un tamaño muestral igual a 6.636 representa el censo de la población simulada.

## Estructura

```text
config/study.json       parámetros del experimento
data/                   coordenadas Glottolog y árbol MCC descargado
src/universals_study/   carga, simulación y comandos
site/                   visualizador interactivo
results/                resultados de la última ejecución
```

## Fuentes

- Bouckaert et al. (2026), [Global Language Tree Pipeline, release v2.0.0](https://github.com/rbouckaert/global-language-tree-pipeline/releases/tag/v2.0.0). Cita también el preprint asociado al reutilizar el árbol: [doi:10.31235/osf.io/f8tr6_v2](https://doi.org/10.31235/osf.io/f8tr6_v2).
- Miestamo, Bakker y Arppe (2016), [Sampling for variety](https://doi.org/10.1515/lingty-2016-0006).
- Piantadosi y Gibson (2014), [Quantitative Standards for Absolute Linguistic Universals](https://doi.org/10.1111/cogs.12088).
- [Glottolog 5.3, datos y descargas](https://glottolog.org/download); licencia [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/).

