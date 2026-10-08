async function loadInvestigations() {
  const status = document.getElementById("statusFilter").value;
  const qs = status ? ("?status=" + encodeURIComponent(status)) : "";
  const res = await fetch("/api/investigations" + qs);
  const json = await res.json();
  const rows = json.data || [];
  const counts = { OPEN: 0, UNDER_REVIEW: 0, ESCALATED: 0, RESOLVED: 0, FALSE_POSITIVE: 0 };
  rows.forEach(r => { counts[r.case_status] = (counts[r.case_status] || 0) + 1; });
  document.getElementById("invStats").innerHTML = Object.entries(counts).map(([k, v]) =>
    `<div class="stat"><div class="muted">${k.replace("_", " ")}</div><div class="n">${v}</div></div>`
  ).join("");
  document.getElementById("invBody").innerHTML = rows.map(r => `
    <tr>
      <td>${r.investigation_id}</td>
      <td>${r.customer_id}</td>
      <td>${r.transaction_id}</td>
      <td>${r.risk_score ?? "-"}</td>
      <td><span class="badge-risk ${r.severity || ""}">${r.severity || "-"}</span></td>
      <td>${r.case_status}</td>
      <td>${r.created_at}</td>
      <td><a class="btn btn-sm btn-primary" href="/investigations/${r.investigation_id}">View Investigation</a></td>
    </tr>`).join("");
}
document.getElementById("statusFilter").onchange = loadInvestigations;
loadInvestigations();
