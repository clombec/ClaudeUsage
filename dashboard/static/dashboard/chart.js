// Renders the usage chart from the JSON embedded by the view.
(function () {
  "use strict";

  // Disable the refresh button while the request runs (a fetch takes a few seconds).
  const refreshForm = document.getElementById("refresh-form");
  if (refreshForm) {
    refreshForm.addEventListener("submit", function () {
      const button = document.getElementById("refresh-button");
      button.disabled = true;
      button.textContent = "Actualisation…";
    });
  }

  const canvas = document.getElementById("usage-chart");
  if (!canvas) {
    return;
  }

  const data = JSON.parse(document.getElementById("chart-data").textContent);
  const styles = getComputedStyle(document.documentElement);
  const color = (name) => styles.getPropertyValue(name).trim();

  const GRID = color("--border");
  const TEXT = color("--muted");

  function dataset(series, lineColor) {
    return {
      label: series.label,
      data: series.points,
      borderColor: lineColor,
      backgroundColor: lineColor,
      borderWidth: 2,
      pointRadius: 2,
      pointHoverRadius: 5,
      tension: 0.2,
    };
  }

  const datasets = [
    dataset(data.fiveHour, color("--blue")),
    dataset(data.sevenDay, color("--yellow")),
  ];
  if (data.extra) {
    datasets.push(dataset(data.extra, color("--red")));
  }

  new Chart(canvas, {
    type: "line",
    data: { datasets: datasets },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      interaction: { mode: "nearest", axis: "x", intersect: false },
      scales: {
        x: {
          type: "time",
          time: {
            tooltipFormat: "dd/MM/yyyy HH:mm",
            displayFormats: { hour: "HH:mm", day: "dd/MM" },
          },
          grid: { color: GRID },
          ticks: { color: TEXT },
        },
        y: {
          min: 0,
          max: 100,
          grid: { color: GRID },
          ticks: { color: TEXT, stepSize: 10, callback: (v) => v + " %" },
        },
      },
      plugins: {
        legend: { labels: { color: color("--text") } },
        tooltip: {
          callbacks: { label: (ctx) => ctx.dataset.label + " : " + ctx.parsed.y + " %" },
        },
      },
    },
  });
})();
