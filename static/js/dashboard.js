document.addEventListener("DOMContentLoaded", () => {
  const root = document.getElementById("dashboard-stats");
  if (!root || typeof Chart === "undefined") return;
  const stats = JSON.parse(root.dataset.stats || "{}");
  const riskCanvas = document.getElementById("riskChart");
  if (riskCanvas) {
    new Chart(riskCanvas, {
      type: "doughnut",
      data: {
        labels: ["LOW", "MEDIUM", "HIGH"],
        datasets: [{ data: [stats.low || 0, stats.medium || 0, stats.high || 0], backgroundColor: ["#198754", "#e6a817", "#dc3545"] }],
      },
      options: { plugins: { legend: { labels: { color: "#d5e4f7" } } } },
    });
  }
  const predCanvas = document.getElementById("predChart");
  if (predCanvas) {
    new Chart(predCanvas, {
      type: "bar",
      data: {
        labels: ["Legitimate", "Suspicious", "Fraud"],
        datasets: [{ data: [stats.legitimate || 0, stats.suspicious || 0, stats.fraud || 0], backgroundColor: ["#3ee0c5", "#e6a817", "#dc3545"] }],
      },
      options: { plugins: { legend: { display: false } }, scales: { x: { ticks: { color: "#d5e4f7" } }, y: { ticks: { color: "#d5e4f7" } } } },
    });
  }
  const trend = document.getElementById("trendChart");
  if (trend) {
    const rows = JSON.parse(trend.dataset.trend || "[]");
    new Chart(trend, {
      type: "line",
      data: {
        labels: rows.map((r) => r.day),
        datasets: [{ label: "Fraud", data: rows.map((r) => r.c), borderColor: "#dc3545", tension: 0.3 }],
      },
      options: { plugins: { legend: { labels: { color: "#d5e4f7" } } }, scales: { x: { ticks: { color: "#d5e4f7" } }, y: { ticks: { color: "#d5e4f7" } } } },
    });
  }
});
