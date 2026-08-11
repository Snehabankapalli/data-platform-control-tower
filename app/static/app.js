"use strict";

const state = Object.freeze({ dashboard: null, selectedIncidentId: null });
let currentState = state;

const elements = {
  dashboard: document.querySelector("#dashboard"), loading: document.querySelector("#loading-state"),
  errorBanner: document.querySelector("#error-banner"), errorMessage: document.querySelector("#error-message"),
  metrics: document.querySelector("#metrics-grid"), pipelineRows: document.querySelector("#pipeline-rows"),
  pipelineEmpty: document.querySelector("#pipeline-empty"), pipelineSearch: document.querySelector("#pipeline-search"),
  statusFilter: document.querySelector("#status-filter"), incidents: document.querySelector("#incident-list"),
  navIncidentCount: document.querySelector("#nav-incident-count"), monthCost: document.querySelector("#month-cost"),
  savingsTotal: document.querySelector("#savings-total"), recommendations: document.querySelector("#cost-recommendations"),
  chart: document.querySelector("#cost-chart"), lineage: document.querySelector("#lineage-graph"),
  dialog: document.querySelector("#incident-dialog"), dialogContent: document.querySelector("#dialog-content"),
  dialogTitle: document.querySelector("#dialog-title"), approveButton: document.querySelector("#approve-button"),
  refreshButton: document.querySelector("#refresh-button"), lastUpdated: document.querySelector("#last-updated"), toast: document.querySelector("#toast")
};

const formatCurrency = value => new Intl.NumberFormat("en-US", { style: "currency", currency: "USD", maximumFractionDigits: 0 }).format(value);
const formatCompact = value => new Intl.NumberFormat("en-US", { notation: "compact", maximumFractionDigits: 1 }).format(value);
const titleCase = value => value.replaceAll("_", " ").replace(/\b\w/g, character => character.toUpperCase());
const escapeHtml = value => String(value).replace(/[&<>'"]/g, character => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", "'": "&#39;", '"': "&quot;" })[character]);

async function request(path, options = {}) {
  const response = await fetch(path, { headers: { "Content-Type": "application/json" }, ...options });
  const payload = await response.json();
  if (!response.ok || !payload.success) throw new Error(payload.error || `Request failed (${response.status})`);
  return payload.data;
}

function renderMetrics(overview) {
  const metrics = [
    { label: "Healthy pipelines", value: `${overview.healthy_pipelines}/${overview.total_pipelines}`, detail: "Two workloads require attention", score: overview.healthy_pipelines / overview.total_pipelines * 100, main: true },
    { label: "SLA compliance", value: `${overview.sla_compliance_percent}%`, detail: "+1.2 pts vs. last week", score: overview.sla_compliance_percent },
    { label: "Records today", value: formatCompact(overview.records_processed_today), detail: "Across streaming and batch", score: 84 },
    { label: "Savings identified", value: formatCurrency(overview.monthly_savings_opportunity_usd), detail: "3 reviewed recommendations", score: 68 }
  ];
  elements.metrics.innerHTML = metrics.map(metric => `
    <article class="metric ${metric.main ? "metric-main" : ""}">
      <div class="metric-label"><span>${escapeHtml(metric.label)}</span><span>${metric.main ? "● LIVE" : "30D"}</span></div>
      <strong class="metric-value">${escapeHtml(metric.value)}</strong>
      <div><div class="metric-detail">${escapeHtml(metric.detail)}</div><div class="mini-bar" aria-hidden="true"><i style="width:${metric.score}%"></i></div></div>
    </article>`).join("");
}

function renderPipelines() {
  const dashboard = currentState.dashboard;
  if (!dashboard) return;
  const query = elements.pipelineSearch.value.trim().toLowerCase();
  const status = elements.statusFilter.value;
  const filtered = dashboard.pipelines.filter(item => (!status || item.status === status) && (!query || `${item.name} ${item.domain} ${item.platform}`.toLowerCase().includes(query)));
  elements.pipelineRows.innerHTML = filtered.map(item => `
    <tr><td><span class="pipeline-name">${escapeHtml(item.name)}<small>${escapeHtml(item.domain)} · ${escapeHtml(item.platform)}</small></span></td>
    <td><span class="status status-${escapeHtml(item.status)}">${escapeHtml(item.status)}</span></td>
    <td class="mono">${item.freshness_minutes}m / ${item.sla_minutes}m</td><td class="mono">${item.success_rate_percent}%</td><td class="mono">${formatCompact(item.records_processed)}</td></tr>`).join("");
  elements.pipelineEmpty.hidden = filtered.length > 0;
}

function renderIncidents(incidents) {
  const active = incidents.filter(item => item.status !== "resolved");
  elements.navIncidentCount.textContent = active.length;
  elements.incidents.innerHTML = active.map(item => `
    <article class="incident"><div class="incident-top"><span class="severity severity-${escapeHtml(item.severity)}">${escapeHtml(item.severity)}</span><time>${new Date(item.detected_at).toLocaleTimeString([], {hour: "2-digit", minute: "2-digit"})}</time></div>
    <h3>${escapeHtml(item.title)}</h3><p>${escapeHtml(item.summary)}</p><button class="text-button incident-detail" data-incident-id="${escapeHtml(item.id)}" type="button">Review incident →</button></article>`).join("");
  document.querySelectorAll(".incident-detail").forEach(button => button.addEventListener("click", () => openIncident(button.dataset.incidentId)));
}

function makeLinePath(values, width, height, maxValue) {
  return values.map((value, index) => `${index === 0 ? "M" : "L"} ${index * width / (values.length - 1)} ${height - value / maxValue * height}`).join(" ");
}

function renderCostChart(trend) {
  const width = 520, height = 125, maxValue = Math.max(...trend.flatMap(item => [item.snowflake_usd, item.aws_usd])) * 1.12;
  const snowflake = makeLinePath(trend.map(item => item.snowflake_usd), width, height, maxValue);
  const aws = makeLinePath(trend.map(item => item.aws_usd), width, height, maxValue);
  elements.chart.innerHTML = `<svg viewBox="-5 -8 ${width + 10} ${height + 35}" preserveAspectRatio="none" aria-hidden="true">
    <g stroke="#dfe3dc" stroke-width="1">${[0,1,2,3].map(i => `<line x1="0" y1="${i * height / 3}" x2="${width}" y2="${i * height / 3}"/>`).join("")}</g>
    <path d="${snowflake}" fill="none" stroke="#0d7757" stroke-width="3" vector-effect="non-scaling-stroke"/><path d="${aws}" fill="none" stroke="#b66a13" stroke-width="2" vector-effect="non-scaling-stroke"/>
    ${trend.map((item, index) => `<text x="${index * width / (trend.length - 1)}" y="${height + 20}" text-anchor="middle" fill="#687c76" font-size="10">${escapeHtml(item.date.replace("Aug ", ""))}</text>`).join("")}
  </svg>`;
}

function renderRecommendations(recommendations) {
  elements.recommendations.innerHTML = recommendations.map(item => `<div class="recommendation"><strong>${escapeHtml(item.title)}</strong><p>${escapeHtml(item.service)} · ${escapeHtml(item.confidence_percent)}% confidence · ${escapeHtml(item.effort)} effort</p><span class="saving">${formatCurrency(item.monthly_savings_usd)}/mo</span></div>`).join("");
}

function renderLineage(graph) {
  const orderedLayers = ["Source", "Ingest", "Storage", "Transform", "Warehouse", "Consumer"];
  const populatedLayers = orderedLayers.filter(layer => graph.nodes.some(node => node.layer === layer));
  elements.lineage.style.gridTemplateColumns = `repeat(${populatedLayers.length}, minmax(72px, 1fr))`;
  elements.lineage.innerHTML = populatedLayers.map(layer => `<div class="lineage-column"><span class="lineage-layer">${layer}</span>${graph.nodes.filter(node => node.layer === layer).map(node => `<div class="lineage-node ${node.has_incident ? "affected" : ""}">${escapeHtml(node.label)}</div>`).join("")}</div>`).join("");
}

function openIncident(incidentId) {
  const incident = currentState.dashboard.incidents.find(item => item.id === incidentId);
  if (!incident) return;
  currentState = Object.freeze({ ...currentState, selectedIncidentId: incidentId });
  elements.dialogTitle.textContent = incident.title;
  elements.dialogContent.innerHTML = `<div class="dialog-grid">
    <div class="dialog-block"><small>Severity / status</small><p>${escapeHtml(titleCase(incident.severity))} · ${escapeHtml(titleCase(incident.status))}</p></div>
    <div class="dialog-block"><small>Blast radius</small><p>${escapeHtml(incident.blast_radius)}</p></div>
    <div class="dialog-block full"><small>Root-cause hypothesis</small><p>${escapeHtml(incident.root_cause)}</p></div>
    <div class="dialog-block full"><small>Recommended action</small><p>${escapeHtml(incident.recommended_action)}</p></div></div>`;
  const approvable = incident.status === "awaiting_approval";
  elements.approveButton.hidden = !approvable;
  elements.approveButton.disabled = false;
  elements.dialog.showModal();
}

async function approveSelectedIncident() {
  if (!currentState.selectedIncidentId) return;
  elements.approveButton.disabled = true;
  elements.approveButton.textContent = "Recording approval…";
  try {
    const updated = await request(`/api/incidents/${encodeURIComponent(currentState.selectedIncidentId)}/approve`, { method: "POST", body: JSON.stringify({ actor: "demo-operator" }) });
    const incidents = currentState.dashboard.incidents.map(item => item.id === updated.id ? updated : item);
    currentState = Object.freeze({ ...currentState, dashboard: Object.freeze({ ...currentState.dashboard, incidents }) });
    renderIncidents(incidents); elements.dialog.close(); showToast("Remediation approved and audit event recorded.");
  } catch (error) { showToast(error.message, true); elements.approveButton.disabled = false; }
  finally { elements.approveButton.textContent = "Approve remediation"; }
}

function showToast(message, isError = false) {
  elements.toast.textContent = message; elements.toast.style.borderLeftColor = isError ? "#b43b35" : "#58c58c"; elements.toast.hidden = false;
  window.setTimeout(() => { elements.toast.hidden = true; }, 3500);
}

function renderDashboard(data) {
  currentState = Object.freeze({ dashboard: Object.freeze(data), selectedIncidentId: null });
  renderMetrics(data.overview); renderPipelines(); renderIncidents(data.incidents); renderCostChart(data.cost_trend);
  renderRecommendations(data.cost_recommendations); renderLineage(data.lineage);
  elements.monthCost.textContent = formatCurrency(data.overview.monthly_cost_usd);
  elements.savingsTotal.textContent = `${formatCurrency(data.overview.monthly_savings_opportunity_usd)} / month`;
  elements.lastUpdated.textContent = new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
}

async function loadDashboard() {
  elements.errorBanner.hidden = true; elements.refreshButton.disabled = true;
  try {
    renderDashboard(await request("/api/dashboard")); elements.loading.hidden = true; elements.dashboard.hidden = false;
  } catch (error) {
    elements.loading.hidden = true; elements.errorMessage.textContent = error.message; elements.errorBanner.hidden = false;
  } finally { elements.refreshButton.disabled = false; }
}

elements.pipelineSearch.addEventListener("input", renderPipelines);
elements.statusFilter.addEventListener("change", renderPipelines);
elements.refreshButton.addEventListener("click", loadDashboard);
elements.approveButton.addEventListener("click", approveSelectedIncident);
document.querySelectorAll(".nav-item").forEach(link => link.addEventListener("click", () => {
  document.querySelectorAll(".nav-item").forEach(item => { item.classList.remove("active"); item.removeAttribute("aria-current"); });
  link.classList.add("active"); link.setAttribute("aria-current", "page");
}));

loadDashboard();
