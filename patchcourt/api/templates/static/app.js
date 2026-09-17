const $ = (sel) => document.querySelector(sel);

const form = $("#review-form");
const urlInput = $("#pr-url");
const error = $("#error");
const status = $("#status");
const statusText = $("#status-text");
const report = $("#report");

form.addEventListener("submit", async (e) => {
  e.preventDefault();
  const prUrl = urlInput.value.trim();
  if (!prUrl) return;
  error.classList.add("hidden");
  report.classList.add("hidden");
  status.classList.remove("hidden");

  statusText.textContent = "Pipeline: ingest → RAG → parallel agents → conflict → debate → judge…";
  const t0 = performance.now();
  try {
    const res = await fetch("/api/review", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ pr_url: prUrl }),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || "Request failed");
    status.classList.add("hidden");
    render(data, ((performance.now() - t0) / 1000).toFixed(1));
  } catch (err) {
    status.classList.add("hidden");
    error.textContent = "Error: " + err.message;
    error.classList.remove("hidden");
  }
});

function render(r, seconds) {
  const v = $("#verdict");
  v.textContent = "Verdict: " + r.verdict;
  v.className = "v-" + r.verdict;
  $("#score").textContent = `score ${r.overall_score} · reviewed in ${seconds}s`;
  $("#pr-link").textContent = r.pr_url;

  $("#debates").innerHTML = "";
  const debates = r.debate_transcripts || [];
  if (debates.length === 0) {
    $("#debate-section").classList.add("hidden");
  } else {
    $("#debate-section").classList.remove("hidden");
    debates.forEach((d) => {
      const el = document.createElement("div");
      el.className = "debate";
      el.innerHTML =
        `<p><strong>${d.file}</strong> — ${d.issue}</p>` +
        `<p>PRO: ${d.supporting}</p>` +
        `<p>CON: ${d.opposing}</p>` +
        `<p>rounds: ${d.rounds}</p>`;
      $("#debates").appendChild(el);
    });
  }

  const tabs = $("#file-tabs");
  tabs.innerHTML = "";
  const claimsBox = $("#claims");
  claimsBox.innerHTML = "";

  Object.entries(groupByFile(r.claims || [])).forEach(([file, claims], i) => {
    const tab = document.createElement("button");
    tab.className = "tab" + (i === 0 ? " active" : "");
    tab.textContent = file;
    tab.dataset.file = file;
    tab.onclick = () => {
      document.querySelectorAll(".tab").forEach((t) => t.classList.remove("active"));
      tab.classList.add("active");
      renderClaims(claims);
    };
    tabs.appendChild(tab);
    if (i === 0) renderClaims(claims);
  });
}

function renderClaims(claims) {
  const box = $("#claims");
  box.innerHTML = "";
  claims.forEach((c) => {
    const el = document.createElement("div");
    el.className = "claim";
    const tiers = c.evidence
      .map((ev) => `<span class="badge tier-${ev.tier}">T${ev.tier}</span>`)
      .join(" ");
    el.innerHTML =
      `<div class="head">
        <span class="issue">${escapeHtml(c.issue)}</span>
        <span class="agent">${escapeHtml(c.agent)}</span>
        <span class="badge">sev ${c.severity}</span>
        <span class="badge">conf ${c.confidence}</span>
        <span class="badge">${c.file}:${c.line}</span>
        <ul class="evidence">${tiers ? `<li>${tiers}</li>` : ""}
          ${c.evidence.map((ev) => `<li>${escapeHtml(ev.text)}</li>`).join("")}
        </ul>
      </div>`;
    box.appendChild(el);
  });
}

function groupByFile(claims) {
  const out = {};
  claims.forEach((c) => {
    (out[c.file] = out[c.file] || []).push(c);
  });
  return out;
}

function escapeHtml(s) {
  return String(s).replace(/[&<>"']/g, (m) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
  }[m]));
}