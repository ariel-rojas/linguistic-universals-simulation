"use strict";

const number = new Intl.NumberFormat("es-ES", { maximumFractionDigits: 2 });
const percent = (value) => `${(100 * value).toFixed(1)} %`;
const svgNS = "http://www.w3.org/2000/svg";
const scenarioDescriptions = {
  independent: "Cada lengua recibe una probabilidad p y se sortea por separado.",
  phylogenetic: "La propensión latente sigue la correlación Browniana de las ramas compartidas del árbol MCC.",
  all_correlated: "Todas las lenguas comparten el mismo efecto latente en cada mundo; sus etiquetas se sortean con esa probabilidad común.",
};
let study;

function setText(id, value) {
  document.getElementById(id).textContent = value;
}

function currentRun() {
  const prevalence = Number(document.getElementById("prevalence-select").value);
  return study.simulation.prevalence_runs.find(
    (run) => Math.abs(run.prevalence - prevalence) < 1e-12,
  );
}

function addMapBackground(svg) {
  svg.replaceChildren();
  const image = document.createElementNS(svgNS, "image");
  image.setAttribute("href", "assets/world-land.svg");
  image.setAttribute("width", "1200");
  image.setAttribute("height", "600");
  svg.appendChild(image);
}

function addPoints(svg, fillFor, onChoose) {
  const group = document.createElementNS(svgNS, "g");
  group.setAttribute("class", "map-points");
  const fragment = document.createDocumentFragment();
  study.population.languages.forEach((language, index) => {
    if (language.latitude == null || language.longitude == null) return;
    const latitude = Number(language.latitude);
    const longitude = Number(language.longitude);
    if (!Number.isFinite(latitude) || !Number.isFinite(longitude)) return;
    const point = document.createElementNS(svgNS, "circle");
    point.setAttribute("cx", ((longitude + 180) * (1200 / 360)).toFixed(2));
    point.setAttribute("cy", ((90 - latitude) * (600 / 180)).toFixed(2));
    point.setAttribute("r", "2.05");
    point.setAttribute("class", "map-point");
    point.setAttribute("fill", fillFor(index, language));
    point.setAttribute("stroke", "#fffdf7");
    point.setAttribute("stroke-width", "0.55");
    point.addEventListener("click", () => onChoose(index, language));
    const title = document.createElementNS(svgNS, "title");
    title.textContent = `${language.name} · ${language.glottocode} · ${language.coordinate_source}`;
    point.appendChild(title);
    fragment.appendChild(point);
  });
  group.appendChild(fragment);
  svg.appendChild(group);
}

function escapeHtml(value) {
  return String(value).replace(/[&<>"']/g, (character) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"
  })[character]);
}

function showLanguageCard(language, exception) {
  const card = document.getElementById("language-card");
  card.classList.remove("empty");
  const coordinateText = language.latitude == null
    ? "Sin coordenadas publicadas."
    : `${number.format(language.latitude)}, ${number.format(language.longitude)} (${escapeHtml(language.coordinate_source)}).`;
  card.innerHTML = `<h3>${escapeHtml(language.name)} <span class="muted">(${escapeHtml(language.glottocode)})</span></h3>
    <p><strong>Macroárea:</strong> ${escapeHtml(language.macroarea || "Sin dato")}</p>
    <p><strong>Ubicación:</strong> ${coordinateText}</p>
    <p><strong>Resultado simulado:</strong> ${exception ? "excepción" : "sin excepción"}.</p>`;
}

function drawSimulationMap() {
  const run = currentRun();
  const scenario = document.getElementById("scenario-select").value;
  const iterationIndex = Number(document.getElementById("iteration-slider").value) - 1;
  const scenarioRun = run.scenarios[scenario];
  const iteration = scenarioRun.iterations[iterationIndex];
  const exceptions = new Set(iteration.exceptions);
  const unmapped = study.population.languages.filter(
    (language) => language.latitude == null || language.longitude == null,
  );

  const svg = document.getElementById("simulation-map");
  addMapBackground(svg);
  addPoints(
    svg,
    (_index, language) => (
      exceptions.has(language.glottocode) ? "#a23e84" : "#c9c5b9"
    ),
    (_index, language) => showLanguageCard(
      language, exceptions.has(language.glottocode)
    ),
  );

  setText("unmapped-heading", `Hojas sin coordenadas (${unmapped.length})`);
  const unmappedList = document.getElementById("unmapped-language-list");
  unmappedList.replaceChildren();
  unmapped.forEach((language) => {
    const result = exceptions.has(language.glottocode) ? "excepción" : "sin excepción";
    const item = document.createElement("li");
    item.textContent = `${language.name} (${language.glottocode}) · ${result} simulada`;
    unmappedList.appendChild(item);
  });

  setText("iteration-label", String(iterationIndex + 1));
  setText(
    "world-summary",
    `${number.format(iteration.n_exceptions)} excepciones · ${percent(iteration.population_prevalence)} del mundo`,
  );
  setText("prevalence-label", percent(run.prevalence));
  setText("matrix-note", scenarioDescriptions[scenario]);

  const card = document.getElementById("language-card");
  card.classList.add("empty");
  card.textContent = "Seleccioná un punto del mapa para ver su ficha y la etiqueta simulada.";
  drawPrevalenceDistribution(run, scenario, iteration);
}

function quantile(values, probability) {
  const sorted = [...values].sort((a, b) => a - b);
  return sorted[Math.min(sorted.length - 1, Math.floor(probability * sorted.length))];
}

function drawPrevalenceDistribution(run, selectedScenario, selectedIteration) {
  const canvas = document.getElementById("prevalence-distribution-chart");
  const ctx = canvas.getContext("2d");
  const width = canvas.width;
  const height = canvas.height;
  ctx.clearRect(0, 0, width, height);

  const margin = { left: 52, right: 18, top: 20, bottom: 42 };
  const plotW = width - margin.left - margin.right;
  const plotH = height - margin.top - margin.bottom;
  const bins = 36;
  const scenarios = Object.keys(run.scenarios);
  const draws = scenarios.map(
    (scenario) => run.scenarios[scenario].population_prevalence_draws,
  );
  const allDraws = draws.flat();
  const maxX = Math.min(
    1,
    Math.max(
      run.prevalence * 1.25,
      quantile(allDraws, 0.995) * 1.1,
      selectedIteration.population_prevalence * 1.1,
      0.02,
    ),
  );

  const histograms = draws.map((values) => {
    const counts = Array(bins).fill(0);
    values.forEach((value) => {
      const bin = Math.min(bins - 1, Math.max(0, Math.floor(value / maxX * bins)));
      counts[bin] += 1 / values.length;
    });
    return counts;
  });
  const maxBin = Math.max(...histograms.flat(), 0.01);
  const yMax = Math.min(1, Math.ceil(maxBin * 4) / 4);

  ctx.font = "10px system-ui";
  ctx.fillStyle = "#5b6b66";
  ctx.strokeStyle = "#e0e4df";
  for (let step = 0; step <= 4; step++) {
    const fraction = step / 4;
    const y = margin.top + plotH * (1 - fraction);
    ctx.beginPath();
    ctx.moveTo(margin.left, y);
    ctx.lineTo(width - margin.right, y);
    ctx.stroke();
    ctx.fillText(`${Math.round(yMax * fraction * 100)} %`, 4, y + 3);
  }

  const colors = ["#62776e99", "#a23e8499", "#4385b899"];
  const binWidth = plotW / bins;
  const barWidth = (binWidth * 0.9) / scenarios.length;
  histograms.forEach((counts, scenarioIndex) => {
    counts.forEach((value, binIndex) => {
      const x = margin.left + binIndex * binWidth + scenarioIndex * barWidth;
      const barHeight = plotH * value / yMax;
      ctx.fillStyle = colors[scenarioIndex];
      ctx.fillRect(x, margin.top + plotH - barHeight, Math.max(1, barWidth - 1), barHeight);
    });
  });

  const drawReference = (value, color, dash) => {
    const x = margin.left + (value / maxX) * plotW;
    if (x < margin.left || x > width - margin.right) return;
    ctx.strokeStyle = color;
    ctx.lineWidth = 2;
    ctx.setLineDash(dash);
    ctx.beginPath();
    ctx.moveTo(x, margin.top);
    ctx.lineTo(x, margin.top + plotH);
    ctx.stroke();
    ctx.setLineDash([]);
  };

  drawReference(run.prevalence, "#263b34", [5, 5]);
  drawReference(selectedIteration.population_prevalence, "#d24d57", []);
  ctx.fillStyle = "#5b6b66";
  ctx.fillText("0 %", margin.left, height - 12);
  ctx.fillText(`${(maxX * 50).toFixed(1)} %`, margin.left + plotW / 2 - 12, height - 12);
  ctx.fillText(`${(maxX * 100).toFixed(1)} %`, width - margin.right - 36, height - 12);

  const label = study.population.scenario_labels[selectedScenario];
  setText(
    "selected-world-label",
    `Iteración ${selectedIteration.iteration} · ${label}: ${percent(selectedIteration.population_prevalence)} de excepciones`,
  );
}

function setupPrevalenceControl() {
  const select = document.getElementById("prevalence-select");
  study.simulation.prevalence_runs.forEach((run) => {
    const option = document.createElement("option");
    option.value = String(run.prevalence);
    option.textContent = percent(run.prevalence);
    select.appendChild(option);
  });
  select.value = String(study.settings.default_prevalence);
  select.addEventListener("change", drawSimulationMap);
}

async function initialize() {
  try {
    let response;
    for (const path of ["results/study.json", "../results/study.json"]) {
      response = await fetch(path);
      if (response.ok) break;
    }
    if (!response.ok) {
      throw new Error(
        `No se encontró results/study.json (HTTP ${response.status}). Ejecutá primero el flujo de Python.`,
      );
    }
    study = await response.json();
    setText("population-count", number.format(study.population.n_languages));
    setText("mapped-count", number.format(study.population.n_mapped_languages));
    setText("replicate-count", number.format(study.simulation.settings.replicates));
    setText("matrix-note", "");
    setText(
      "coordinate-coverage",
      `${number.format(study.population.n_without_coordinates)} hojas no tienen coordenadas publicadas y por eso no aparecen como puntos. Sí forman parte de todos los mundos.`,
    );

    setupPrevalenceControl();
    const slider = document.getElementById("iteration-slider");
    slider.max = study.simulation.prevalence_runs[0].scenarios.phylogenetic.iterations.length;
    slider.addEventListener("input", drawSimulationMap);
    document.getElementById("scenario-select").addEventListener("change", drawSimulationMap);
    drawSimulationMap();
  } catch (error) {
    const message = document.createElement("div");
    message.className = "error";
    message.textContent = error.message;
    document.querySelector("main").prepend(message);
  }
}

initialize();
