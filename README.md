# Universales lingüísticos bajo dependencia

[Explorar los resultados en la página interactiva](https://ariel-rojas.github.io/linguistic-universals-simulation/)

Este proyecto compara cómo cambia la proporción de excepciones entre mundos simulados cuando las lenguas son independientes, comparten historia en un árbol o están perfectamente correlacionadas.

Las excepciones son simuladas. No son datos observados de OV/VO ni de otra característica lingüística, y el modelo no estima parámetros a partir de una característica real.

## Qué compara

Para cada valor de prevalencia marginal p se generan mundos completos con las mismas 6.636 lenguas. En cada mundo, cada lengua puede tener o no la excepción simulada. Se repite el proceso y se observa cómo varía la proporción de excepciones entre mundos.

En esta versión no se toman submuestras ni se calcula la probabilidad de que una muestra no encuentre excepciones. La comparación se concentra en la distribución de prevalencias realizadas de los mundos completos.

Se comparan tres escenarios:

1. **Lenguas independientes.** Cada lengua recibe una probabilidad p y se sortea por separado.
2. **Árbol MCC.** Las propensiones a la excepción tienen correlación según el tiempo de ramas compartidas por las lenguas.
3. **R perfectamente correlacionada.** Todas las lenguas comparten la misma propensión latente dentro de cada mundo.

La página muestra las tres distribuciones y permite elegir un escenario, un valor de p y una iteración. El mapa y el gráfico por iteración se actualizan juntos: un punto rojo marca el mundo elegido y una línea horizontal señala su proporción de excepciones. En el histograma general, esa misma proporción aparece con una línea vertical porque allí la proporción está en el eje horizontal. Otra línea indica la prevalencia marginal p.

## Cómo se genera un mundo

### 1. Se fija la prevalencia marginal

p es la proporción esperada de excepciones al promediar muchos mundos. Los valores iniciales son 1 %, 5 %, 10 % y 20 %. No se estima p usando datos observados.

### 2. Se define la dependencia

En los escenarios dependientes se genera un vector latente f con distribución normal multivariada:

`f ~ Normal(0, σ² R)`

R determina qué lenguas tienden a tener propensiones parecidas. σ controla la amplitud de esas diferencias. En el escenario independiente no se genera f: cada lengua conserva directamente la probabilidad p.

- **R del árbol:** si Cᵢⱼ es el tiempo de rama que comparten las lenguas i y j, la correlación es `Rᵢⱼ = Cᵢⱼ / √(Cᵢᵢ Cⱼⱼ)`. El programa la genera recorriendo los incrementos de las ramas, sin almacenar la matriz completa de 6.636 × 6.636 valores.
- **R perfectamente correlacionada:** todos los elementos de R valen uno. Todas las lenguas reciben el mismo valor latente f en ese mundo.

La segunda alternativa es un extremo matemático de comparación, no una hipótesis histórica realista.

### 3. Se convierten las propensiones en probabilidades

Para cada lengua i:

`qᵢ = Φ(α + fᵢ)`

Φ es la función de distribución de la normal estándar. Convierte cualquier valor real en una probabilidad entre cero y uno. El intercepto se fija así:

`α = √(1 + σ²) · Φ⁻¹(p)`

Esta calibración hace que la probabilidad marginal de cada lengua, promediada entre mundos, sea p. No obliga a que cada mundo tenga exactamente una proporción p. La proporción realizada cambia de una iteración a otra y esa variación es precisamente lo que se compara.

En el escenario independiente, qᵢ = p para todas las lenguas.

### 4. Se sortean las excepciones

`Yᵢ ~ Bernoulli(qᵢ)`

Yᵢ vale 1 si la lengua i tiene una excepción simulada y 0 si no la tiene. En el caso perfectamente correlacionado, las probabilidades qᵢ son iguales dentro de un mundo, aunque cada etiqueta binaria todavía se sortea por separado una vez fijada esa probabilidad común.

## Qué muestra el visualizador

- **Mapa:** las ubicaciones corresponden a lenguas reales. El color de cada punto es una etiqueta simulada del mundo seleccionado.
- **Distribución:** cada histograma resume la proporción de excepciones en todos los mundos de un escenario para el p elegido.
- **Gráfico por iteración:** muestra la proporción de excepciones de cada mundo simulado en el orden en que se generó. El punto rojo y la línea horizontal corresponden al mundo que aparece en el mapa; la línea vertical del mismo color marca su número de iteración.
- **Línea de p:** señala la prevalencia marginal configurada.
- **Marca del mundo mostrado en el histograma:** señala en qué proporción cae la iteración visible en el mapa. Al cambiar el escenario o mover el control de iteración, las marcas y el mapa se actualizan juntos.
- **Ficha de lengua:** al seleccionar un punto, muestra su nombre, glottocódigo, macroárea, coordenadas y etiqueta simulada.
- **Lenguas sin coordenadas:** siguen participando en la generación y en los porcentajes, pero no se colocan artificialmente en el mapa.

La distribución no es una distribución posterior bayesiana. Es una distribución empírica de resultados producidos por simulación bajo los valores definidos en la configuración.

## Población y fuentes

La población de la simulación son las **6.636 hojas** del árbol MCC de *Global Language Tree Pipeline*, release v2.0.0. No equivale a un censo de todas las lenguas vivas. El árbol y sus longitudes de rama se tratan como conocidos.

Los nombres, macroáreas y coordenadas se toman de **Glottolog 5.3**. Hay coordenadas publicadas para 6.626 hojas; las diez restantes participan en el modelo y aparecen en la lista de lenguas sin coordenadas.

**WALS no se utiliza como entrada**. Se había empleado para añadir metadatos de mapa, pero no era necesario para definir la población, construir la correlación ni mejorar la cobertura frente a Glottolog en este flujo.

El archivo del árbol se descarga desde la release original y se comprueba con su huella SHA-256 antes de usarse. No se redistribuye una copia de ese archivo en este repositorio. El archivo geográfico de Glottolog está incluido; Glottolog publica estos datos bajo CC BY 4.0 y se atribuye a su fuente.

## Preparar y ejecutar

Requisitos: Python 3.12 o posterior y [uv](https://docs.astral.sh/uv/).

En PowerShell, desde la carpeta del proyecto:

```powershell
uv sync --locked
uv run universals-study download-data
uv run universals-study run
uv run universals-study serve
```

La última orden inicia el servidor local. Abre `http://127.0.0.1:8000/site/` y detenlo con `Ctrl+C`.

`download-data` descarga el árbol MCC de la release oficial y verifica la huella. Se necesita conexión a Internet para esta preparación. Si Python no puede validar el certificado TLS del sistema, el comando intenta usar curl, sin desactivar la validación TLS.

`run` vuelve a generar las simulaciones y actualiza `results/study.json` y `results/report.md`. La página usa el archivo JSON.

## Cambiar valores

Edita `config/study.json` y vuelve a ejecutar `uv run universals-study run`.

| Campo | Función |
|---|---|
| `seed` | Semilla para repetir los mismos sorteos. |
| `population_simulations` | Mundos generados por escenario y por cada valor de p. |
| `map_iterations` | Primeros mundos guardados para navegar con el control del mapa. |
| `simulation_prevalences` | Valores de p que se comparan; cada uno ejecuta los tres escenarios. |
| `default_prevalence` | Valor de p seleccionado al abrir la página. |
| `simulation_phylogenetic_scale` | Amplitud σ del efecto latente en los escenarios correlacionados. |

El costo aumenta con el número de valores de p y de mundos simulados. El número de iteraciones guardadas para el mapa afecta el tamaño del archivo de resultados, no la cantidad total de mundos simulados.

## Estructura del proyecto

```text
config/study.json       valores que controla el usuario
data/                   datos geográficos y manifiesto de fuentes
src/universals_study/   lectura del árbol, generadores y simulación
site/                   mapa e histogramas interactivos
results/                datos de la página y resumen de la última ejecución
.github/workflows/      publicación automática de la página
```

### Qué hace cada módulo

| Archivo | Función principal |
|---|---|
| cli.py | main() define los comandos download-data, run y serve. |
| population.py | load_population() carga el árbol y une sus hojas con nombres y coordenadas de Glottolog mediante el glottocódigo. |
| phylogeny.py | load_mcc_tree() lee y verifica el árbol; BrownianTreeSampler genera campos correlacionados recorriendo sus ramas. |
| covariance.py | create_field_sampler() selecciona el generador del árbol o el de correlación perfecta. |
| simulation.py | probit_intercept() calibra p; draw_world() genera etiquetas; simulate_worlds() compara los tres escenarios. |
| workflow.py | load_settings() valida la configuración; run_study() organiza la simulación y escribe los resultados. |
| site/app.js | Lee el JSON y sincroniza los controles, el mapa, la ficha de lengua y la distribución. |

## Fuentes y cita

- Bouckaert et al. (2026). [Global Language Tree Pipeline, release v2.0.0](https://github.com/rbouckaert/global-language-tree-pipeline/releases/tag/v2.0.0). Al reutilizar el árbol, cita el [preprint asociado](https://doi.org/10.31235/osf.io/f8tr6_v2).
- [Glottolog 5.3: descarga de datos](https://glottolog.org/download) y [licencia CC BY 4.0](https://creativecommons.org/licenses/by/4.0/).
- Miestamo, Bakker y Arppe (2016). [Sampling for variety](https://doi.org/10.1515/lingty-2016-0006).
- Piantadosi y Gibson (2014). [Quantitative Standards for Absolute Linguistic Universals](https://doi.org/10.1111/cogs.12088).

