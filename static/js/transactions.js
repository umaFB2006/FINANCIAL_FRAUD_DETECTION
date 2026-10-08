let page = 1;

function badge(v) {
  return `<span class="badge-risk ${v || ""}">${v || "-"}</span>`;
}

async function loadTxns() {
  const q = document.getElementById("searchBox").value;
  const prediction = document.getElementById("predFilter").value;
  const params = new URLSearchParams({ page, per_page: 15, q, prediction });
  const res = await fetch("/api/transactions?" + params.toString());
  const json = await res.json();
  const items = json.data.items || [];
  document.getElementById("txnBody").innerHTML = items.map(t => `
    <tr>
      <td>${t.transaction_id}</td>
      <td>${t.customer_id}</td>
      <td>₹ ${t.transaction_amount}</td>
      <td>${t.transaction_type}</td>
      <td>${t.location || ""}</td>
      <td>${t.payment_method || ""}</td>
      <td>${t.risk_score ?? "-"}</td>
      <td>${badge(t.prediction)}</td>
      <td>${badge(t.severity)}</td>
      <td>${t.transaction_time}</td>
      <td>
        <a class="btn btn-sm btn-outline-light" href="/transactions/${t.transaction_id}">View</a>
        ${t.investigation_id ? `<a class="btn btn-sm btn-primary" href="/investigations/${t.investigation_id}">Investigate</a>` : ""}
      </td>
    </tr>`).join("");
  const total = json.data.total || 0;
  document.getElementById("pageInfo").textContent = `Page ${page} · ${total} rows`;
}

document.getElementById("searchBox").addEventListener("input", () => { page = 1; loadTxns(); });
document.getElementById("predFilter").addEventListener("change", () => { page = 1; loadTxns(); });
document.getElementById("prevPage").onclick = () => { page = Math.max(1, page - 1); loadTxns(); };
document.getElementById("nextPage").onclick = () => { page += 1; loadTxns(); };
loadTxns();
