"use strict";

const number = new Intl.NumberFormat("es-ES", { maximumFractionDigits: 2 });
const percent = (value) => value == null ? "—" : `${(100 * value).toFixed(1)} %`;
const svgNS = "http://www.w3.org/2000/svg";
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
    const x = (longitude + 180) * (1200 / 360);
    const y = (90 - latitude) * (600 / 180);
    point.setAttribute("cx", x.toFixed(2));
    point.setAttribute("cy", y.toFixed(2));
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
  const iterations = run.scenarios[scenario].iterations;
  const iteration = iterations[iterationIndex];
  const exceptions = new Set(iteration.exceptions);
  const unmapped = study.population.languages.filter(
    (language) => language.latitude == null || language.longitude == null,
  );
  const svg = document.getElementById("simulation-map");
  addMapBackground(svg);
  addPoints(svg, (_index, language) => (
    exceptions.has(language.glottocode) ? "#a23e84" : "#c9c5b9"
  ), (_index, language) => showLanguageCard(
    language, exceptions.has(language.glottocode)
  ));
  setText("unmapped-heading", `Hojas sin coordenadas (${unmapped.length})`);
  const unmappedList = document.getElementById("unmapped-language-list");
  unmappedList.replaceChildren();
  unmapped.forEach((language) => {
    const item = document.createElement("li");
    const status = exceptions.has(language.glottocode) ? "excepción" : "sin excepción";
    item.textContent = `${language.name} (${language.glottocode}) · ${status} simulada`;
    unmappedList.appendChild(item);
  });
  setText("iteration-label", String(iterationIndex + 1));
  setText(
    "world-summary",
    `${number.format(iteration.n_exceptions)} excepciones · ${percent(iteration.population_prevalence)} del mundo`,
  );
  setText("prevalence-label", percent(run.prevalence));
  const card = document.getElementById("language-card");
  card.classList.add("empty");
  card.textContent = "Seleccioná un punto del mapa para ver su ficha y la etiqueta simulada.";
  drawFalseUniversalChart(run);
  drawPrevalenceDistribution(run);
}

function drawFalseUniversalChart(run) {
  const canvas = document.getElementById("false-universal-chart");
  const ctx = canvas.getContext("2d");
  const width = canvas.width, height = canvas.height;
  ctx.clearRect(0, 0, width, height);
  const margin = { left: 54, right: 16, top: 14, bottom: 40 };
  const plotW = width - margin.left - margin.right;
  const plotH = height - margin.top - margin.bottom;
  const sizes = study.simulation.settings.sample_sizes;
  const independent = run.scenarios.independent.false_universal_by_sample_size;
  const correlated = run.scenarios.phylogenetic.false_universal_by_sample_size;
  const series = [
    independent.map((item) => item.rate),
    correlated.map((item) => item.rate),
    independent.map((item) => item.exact_independent_reference),
  ];
  const maxRate = Math.max(0.1, ...series.flat().filter((value) => value != null));
  const yMax = Math.min(1, Math.ceil(maxRate * 10) / 10);
  ctx.font = "10px system-ui";
  ctx.fillStyle = "#5b6b66";
  ctx.strokeStyle = "#d7ddd7";
  for (let step = 0; step <= 4; step++) {
    const fraction = step / 4;
    const y = margin.top + plotH * (1 - fraction);
    ctx.beginPath(); ctx.moveTo(margin.left, y); ctx.lineTo(width - margin.right, y); ctx.stroke();
    ctx.fillText(`${Math.round(yMax * fraction * 100)}%`, 5, y + 4);
  }
  sizes.forEach((size, index) => {
    const x = margin.left + (sizes.length === 1 ? plotW / 2 : plotW * index / (sizes.length - 1));
    ctx.fillText(number.format(size), x - 12, height - 16);
  });
  ctx.fillText("lenguas observadas · puntos ordenados por tamaño", width / 2 - 135, height - 2);

  const colors = ["#62776e", "#a23e84", "#253b34"];
  series.forEach((values, seriesIndex) => {
    ctx.beginPath();
    ctx.strokeStyle = colors[seriesIndex];
    ctx.lineWidth = seriesIndex === 2 ? 2 : 3;
    ctx.setLineDash(seriesIndex === 2 ? [6, 5] : []);
    let started = false;
    values.forEach((value, index) => {
      if (value == null) return;
      const x = margin.left + (sizes.length === 1 ? plotW / 2 : plotW * index / (sizes.length - 1));
      const y = margin.top + plotH * (1 - value / yMax);
      if (!started) { ctx.moveTo(x, y); started = true; } else ctx.lineTo(x, y);
    });
    if (started) ctx.stroke();
    ctx.setLineDash([]);
    if (seriesIndex < 2) values.forEach((value, index) => {
      if (value == null) return;
      const x = margin.left + (sizes.length === 1 ? plotW / 2 : plotW * index / (sizes.length - 1));
      const y = margin.top + plotH * (1 - value / yMax);
      ctx.fillStyle = colors[seriesIndex];
      ctx.beginPath(); ctx.arc(x, y, 4, 0, 2 * Math.PI); ctx.fill();
    });
  });

  const table = document.getElementById("false-universal-table");
  const headers = `<span class="head">Muestra</span><span class="head rate">Indep.</span><span class="head rate">R</span><span class="head rate">Indep. exacto</span>`;
  const rows = sizes.map((size, index) => {
    const left = independent[index], right = correlated[index];
    return `<span>${number.format(size)}</span><span class="rate">${percent(left.rate)} (${left.false_universals})</span><span class="rate">${percent(right.rate)} (${right.false_universals})</span><span class="rate">${percent(left.exact_independent_reference)}</span>`;
  }).join("");
  table.innerHTML = headers + rows;
}

function quantile(values, probability) {
  const sorted = [...values].sort((a, b) => a - b);
  return sorted[Math.min(sorted.length - 1, Math.floor(probability * sorted.length))];
}

function drawPrevalenceDistribution(run) {
  const canvas = document.getElementById("prevalence-distribution-chart");
  const ctx = canvas.getContext("2d");
  const width = canvas.width, height = canvas.height;
  ctx.clearRect(0, 0, width, height);
  const margin = { left: 50, right: 14, top: 14, bottom: 37 };
  const plotW = width - margin.left - margin.right;
  const plotH = height - margin.top - margin.bottom;
  const bins = 40;
  const values = [
    run.scenarios.independent.population_prevalence_draws,
    run.scenarios.phylogenetic.population_prevalence_draws,
  ];
  const allDraws = values.flat();
  const maxX = Math.min(1, Math.max(run.prevalence * 1.25, quantile(allDraws, 0.995) * 1.1, 0.02));
  const histograms = values.map((draws) => {
    const counts = Array(bins).fill(0);
    draws.forEach((value) => {
      const bin = Math.min(bins - 1, Math.max(0, Math.floor(value / maxX * bins)));
      counts[bin] += 1 / draws.length;
    });
    return counts;
  });
  const maxCount = Math.max(...histograms.flat(), 0.1);
  const yMax = Math.min(1, Math.ceil(maxCount * 4) / 4);
  ctx.font = "10px system-ui";
  ctx.fillStyle = "#5b6b66";
  ctx.strokeStyle = "#e0e4df";
  for (let step = 0; step <= 4; step++) {
    const fraction = step / 4;
    const y = margin.top + plotH * (1 - fraction);
    ctx.beginPath(); ctx.moveTo(margin.left, y); ctx.lineTo(width - margin.right, y); ctx.stroke();
    ctx.fillText(`${Math.round(yMax * fraction * 100)}%`, 4, y + 3);
  }
  const colors = ["#62776e99", "#a23e8499"];
  const binWidth = plotW / bins;
  histograms.forEach((counts, seriesIndex) => {
    counts.forEach((value, index) => {
      const barWidth = binWidth * 0.46;
      const x = margin.left + index * binWidth + (seriesIndex === 0 ? 0 : barWidth);
      const barHeight = plotH * value / yMax;
      ctx.fillStyle = colors[seriesIndex];
      ctx.fillRect(x, margin.top + plotH - barHeight, Math.max(1, barWidth - 1), barHeight);
    });
  });
  const prevalenceX = margin.left + (run.prevalence / maxX) * plotW;
  if (prevalenceX <= width - margin.right) {
    ctx.strokeStyle = "#253b34";
    ctx.lineWidth = 2;
    ctx.setLineDash([6, 5]);
    ctx.beginPath(); ctx.moveTo(prevalenceX, margin.top); ctx.lineTo(prevalenceX, margin.top + plotH); ctx.stroke();
    ctx.setLineDash([]);
  }
  ctx.fillStyle = "#5b6b66";
  ctx.fillText("0 %", margin.left, height - 10);
  ctx.fillText(`${(maxX * 50).toFixed(1)} %`, margin.left + plotW / 2 - 12, height - 10);
  ctx.fillText(`${(maxX * 100).toFixed(1)} %`, width - margin.right - 36, height - 10);
}

function setupTabs() {
  document.querySelectorAll(".tab").forEach((button) => {
    button.addEventListener("click", () => {
      document.querySelectorAll(".tab").forEach((tab) => tab.classList.toggle("active", tab === button));
      document.querySelectorAll(".panel").forEach((panel) => {
        panel.classList.toggle("active-panel", panel.id === button.dataset.section);
      });
    });
  });
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
  setupTabs();
  try {
    let response;
    for (const path of ["results/study.json", "../results/study.json"]) {
      response = await fetch(path);
      if (response.ok) break;
    }
    if (!response.ok) throw new Error(`No se encontró results/study.json (HTTP ${response.status}). Ejecutá primero el flujo de Python.`);
    study = await response.json();
    setText("population-count", number.format(study.population.n_languages));
    setText("mapped-count", number.format(study.population.n_mapped_languages));
    setText("replicate-count", number.format(study.simulation.settings.replicates));
    setText("matrix-note", `R utilizada: ${study.population.correlation_label}.`);
    setText("matrix-explanation", study.population.correlation_structure === "all_correlated"
      ? "Esta R es una matriz de unos: todas las lenguas comparten el mismo efecto latente. Es un extremo matemático para observar qué pasa cuando la dependencia es máxima; no representa una reconstrucción realista de la historia lingüística."
      : "Esta R se obtiene de los tiempos de rama compartidos del árbol MCC y se normaliza para que cada lengua tenga varianza uno. El muestreo recorre el árbol directamente, conservando también las correlaciones entre familias.");
    setText("coordinate-coverage", `${number.format(study.population.n_without_coordinates)} hojas no tienen coordenadas publicadas y por eso no aparecen como puntos. Sí forman parte de todos los mundos y tamaños muestrales.`);
    setupPrevalenceControl();
    const slider = document.getElementById("iteration-slider");
    slider.max = study.simulation.prevalence_runs[0].scenarios.phylogenetic.iterations.length;
    slider.addEventListener("input", drawSimulationMap);
    document.getElementById("scenario-select").addEventListener("change", drawSimulationMap);
    drawSimulationMap();
  } catch (error) {
    const main = document.querySelector("main");
    const message = document.createElement("div");
    message.className = "error";
    message.textContent = error.message;
    main.prepend(message);
  }
}

initialize();
