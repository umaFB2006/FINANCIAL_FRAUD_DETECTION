function makeChart(id, type, labels, data) {
  const el = document.getElementById(id);
  if (!el) return null;
  if (el._chart) el._chart.destroy();
  el._chart = new Chart(el, {
    type,
    data: {
      labels,
      datasets: [{
        label: "Count",
        data,
        borderColor: "#3d8bfd",
        backgroundColor: type === "line" ? "rgba(61,139,253,.2)" : ["#22c55e", "#eab308", "#f97316", "#ef4444", "#3d8bfd", "#a855f7", "#14b8a6", "#64748b"],
        tension: 0.3
      }]
    },
    options: {
      plugins: { legend: { labels: { color: "#d5def0" } } },
      scales: type === "doughnut" || type === "pie" ? {} : {
        x: { ticks: { color: "#93a0bb" }, grid: { color: "#243049" } },
        y: { ticks: { color: "#93a0bb" }, grid: { color: "#243049" } }
      }
    }
  });
  return el._chart;
}

function labelsAndCounts(rows, labelKey = "label", countKey = "n") {
  return {
    labels: (rows || []).map(r => r[labelKey]),
    data: (rows || []).map(r => r[countKey])
  };
}
