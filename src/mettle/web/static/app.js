const elements = {
  band: document.querySelector(".command-band"),
  campaignStrip: document.querySelector(".campaign-strip"),
  loading: document.querySelector("#loading-state"),
  dashboard: document.querySelector("#dashboard"),
  error: document.querySelector("#error-banner"),
  errorMessage: document.querySelector("#error-message"),
  noticeId: document.querySelector("#notice-id"),
  property: document.querySelector("#property-label"),
  days: document.querySelector("#days-remaining"),
  condition: document.querySelector(".condition"),
  conditionLabel: document.querySelector("#condition-label"),
  cadence: document.querySelector("#cadence-label"),
  progressLabel: document.querySelector("#progress-label"),
  progressBar: document.querySelector("#progress-bar"),
  asOf: document.querySelector("#as-of-date"),
  citations: document.querySelector("#citation-list"),
  events: document.querySelector("#event-list"),
  judgments: document.querySelector("#judgment-list"),
  judgmentCount: document.querySelector("#judgment-count"),
  metrics: document.querySelector("#metrics-list"),
  packet: document.querySelector("#packet-status"),
  packetList: document.querySelector("#packet-list"),
  demoStep: document.querySelector("#demo-step"),
  advance: document.querySelector("#advance-button"),
  reset: document.querySelector("#reset-button"),
  retry: document.querySelector("#retry-button"),
  toast: document.querySelector("#toast"),
};

const stepLabels = [
  "OPENING CAMPAIGN",
  "ELECTRICAL EVIDENCE ACCEPTED",
  "FRAMING EVIDENCE REJECTED",
  "CRITICAL CADENCE",
  "FRAMING REPLACEMENT ACCEPTED",
  "MECHANICAL EVIDENCE ACCEPTED",
  "PACKET ASSEMBLED",
];

let campaign = null;
let toastTimer = null;

function node(tag, className, text) {
  const item = document.createElement(tag);
  if (className) item.className = className;
  if (text !== undefined) item.textContent = text;
  return item;
}

function titleCase(value) {
  return value.replaceAll("_", " ").replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function formatDate(value) {
  return new Intl.DateTimeFormat("en-US", { month: "short", day: "numeric", year: "numeric" })
    .format(new Date(`${value}T12:00:00`));
}

function formatTime(value) {
  return new Intl.DateTimeFormat("en-US", { hour: "numeric", minute: "2-digit", timeZone: "UTC" })
    .format(new Date(value));
}

async function request(path, options = {}) {
  const response = await fetch(path, {
    ...options,
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
  });
  const payload = await response.json();
  if (!response.ok) throw new Error(payload.error?.message || "The campaign request failed.");
  return payload;
}

function showError(error) {
  elements.loading.hidden = true;
  elements.error.hidden = false;
  elements.errorMessage.textContent = error.message || "The local API did not respond.";
}

function showToast(message) {
  window.clearTimeout(toastTimer);
  elements.toast.textContent = message;
  elements.toast.hidden = false;
  toastTimer = window.setTimeout(() => { elements.toast.hidden = true; }, 2800);
}

function setBusy(button, busy) {
  button.disabled = busy;
  button.setAttribute("aria-busy", String(busy));
}

function conditionFor(data) {
  if (data.packet_status === "approved") return ["REINSPECTION READY", "ready"];
  if (data.packet_status === "awaiting_approval") return ["AWAITING APPROVAL", "approval"];
  if (data.priority === "critical") return ["CRITICAL", "critical"];
  return ["ON TRACK", "normal"];
}

function renderCitation(citation) {
  const card = node("article", "citation");
  card.append(node("div", "citation__number", `C${citation.citation_id}`));

  const body = node("div", "citation__body");
  body.append(node("p", "citation__code", `${citation.code_reference} · ${titleCase(citation.trade)}`));
  body.append(node("p", "citation__finding", `“${citation.notice_text}”`));

  const requirements = node("ul", "citation__requirements");
  for (const requirement of citation.evidence_requirements) requirements.append(node("li", "", requirement));
  if (requirements.children.length) body.append(requirements);

  const ownership = citation.assignee || "Waiting for contractor judgment";
  const note = citation.evidence_note ? ` · ${citation.evidence_note}` : "";
  body.append(node("p", "citation__meta", `${ownership}${note}`));
  card.append(body);

  const labels = {
    ready: "ACCEPTED",
    awaiting_evidence: "AWAITING EVIDENCE",
    evidence_rejected: "REJECTED",
    needs_judgment: "NEEDS YOU",
  };
  card.append(node("span", `status status--${citation.stage}`, labels[citation.stage]));
  return card;
}

function renderEvent(event) {
  const item = node("li", "event");
  item.append(node("time", "event__time", formatTime(event.happened_at)));
  item.append(node("span", `event__tag event__tag--${event.kind}`, event.kind.replaceAll("_", " ").toUpperCase()));
  const body = node("div", "event__body");
  body.append(node("strong", "", event.title));
  body.append(node("p", "", event.detail));
  body.append(node("span", "event__actor", event.actor.toUpperCase()));
  item.append(body);
  return item;
}

function decisionDefaults(judgment) {
  if (judgment.kind === "final_packet_approval") {
    return ["Approve packet for reinspection scheduling", "Approve packet"];
  }
  if (judgment.kind === "deadline_tradeoff") {
    return ["Keep the current reinspection date and continue four-hour follow-ups", "Keep the date"];
  }
  return ["Wide photo showing equipment clearance with the access panel open", "Use this evidence spec"];
}

function renderJudgment(judgment) {
  const card = node("article", "judgment");
  card.append(node("div", "judgment__kind", `${titleCase(judgment.kind)}${judgment.citation_id ? ` · C${judgment.citation_id}` : ""}`));
  card.append(node("h3", "", judgment.question));
  card.append(node("p", "", judgment.reason));

  const [defaultDecision, buttonLabel] = decisionDefaults(judgment);
  const form = document.createElement("form");
  const label = node("label", "sr-only", "Contractor decision");
  const input = document.createElement("input");
  input.id = `decision-${judgment.judgment_id}`;
  label.htmlFor = input.id;
  input.name = "decision";
  input.required = true;
  input.minLength = 3;
  input.maxLength = 500;
  input.value = defaultDecision;
  const button = node("button", "button", buttonLabel);
  button.type = "submit";
  form.append(label, input, button);
  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    const decision = input.value.trim();
    if (decision.length < 3) return;
    setBusy(button, true);
    try {
      campaign = await request(`/api/judgments/${encodeURIComponent(judgment.judgment_id)}/resolve`, {
        method: "POST",
        body: JSON.stringify({ decision }),
      });
      render(campaign);
      showToast("Your decision is logged. Mettle resumed the recovery run.");
    } catch (error) {
      input.setCustomValidity(error.message);
      input.reportValidity();
      input.setCustomValidity("");
    } finally {
      setBusy(button, false);
    }
  });
  card.append(form);
  return card;
}

function renderMetrics(metrics) {
  const values = [
    ["Citations ready", `${metrics.citations_ready}/${metrics.citations_total}`],
    ["Messages handled", metrics.messages_handled],
    ["Automated actions", metrics.automated_actions],
    ["Decisions — yours", metrics.contractor_decisions],
  ];
  elements.metrics.replaceChildren(...values.map(([label, value]) => {
    const row = node("div", "metric");
    row.append(node("dd", "", String(value)), node("dt", "", label));
    return row;
  }));
}

function renderPacket(data) {
  const rows = data.citations.map((citation) => {
    const row = node("div", "packet-row");
    row.append(node("span", "packet-row__tag", `C${citation.citation_id}`));
    row.append(node("span", "packet-row__code", citation.code_reference));
    const ready = citation.stage === "ready";
    row.append(node("span", `packet-row__state${ready ? " packet-row__state--ready" : ""}`, ready ? "ACCEPTED" : "PENDING"));
    return row;
  });
  elements.packetList.replaceChildren(...rows);

  elements.packet.textContent = data.packet_status === "approved"
    ? "APPROVED"
    : data.packet_status === "awaiting_approval" ? "AWAITING APPROVAL" : "LOCKED";
  elements.packet.className = "packet-stamp";
  if (data.packet_status === "approved") elements.packet.classList.add("packet-stamp--approved");
  if (data.packet_status === "awaiting_approval") elements.packet.classList.add("packet-stamp--awaiting");
}

function render(data) {
  campaign = data;
  elements.loading.hidden = true;
  elements.error.hidden = true;
  elements.dashboard.hidden = false;
  elements.noticeId.textContent = data.notice_id;
  elements.property.textContent = data.property_label;
  elements.days.textContent = String(Math.max(data.days_remaining, 0));
  elements.asOf.textContent = `AS OF ${formatDate(data.as_of).toUpperCase()}`;
  elements.progressLabel.textContent = `${data.metrics.citations_ready} / ${data.metrics.citations_total} CITATIONS READY`;
  elements.progressBar.style.width = `${(data.metrics.citations_ready / data.metrics.citations_total) * 100}%`;

  const [conditionLabel, conditionTone] = conditionFor(data);
  elements.conditionLabel.textContent = conditionLabel;
  elements.condition.className = `condition condition--${conditionTone}`;
  const criticalRecovery = data.priority === "critical" && data.packet_status !== "approved";
  elements.band.classList.toggle("command-band--critical", criticalRecovery);
  elements.campaignStrip.classList.toggle("campaign-strip--critical", criticalRecovery);
  elements.cadence.textContent = data.packet_status === "approved"
    ? "STANDING DOWN · PACKET APPROVED"
    : criticalRecovery ? "CRITICAL RECOVERY · CHECK-INS EVERY 4H" : "NORMAL FOLLOW-UP · DAILY CHECK-INS";

  elements.citations.replaceChildren(...data.citations.map(renderCitation));
  elements.events.replaceChildren(...data.events.map(renderEvent));

  const pending = data.judgments.filter((item) => item.status === "pending");
  elements.judgmentCount.textContent = String(pending.length);
  if (pending.length) {
    elements.judgments.replaceChildren(...pending.map(renderJudgment));
  } else {
    const empty = node("div", "empty-state");
    empty.append(node("strong", "", "No decisions needed"));
    empty.append(node("p", "", "METTLE KEEPS WORKING — YOU’LL GET AN SMS WHEN SOMETHING DOES"));
    elements.judgments.replaceChildren(empty);
  }

  renderMetrics(data.metrics);
  renderPacket(data);
  elements.demoStep.textContent = `${data.scenario_step} · ${stepLabels[data.scenario_step] || "RECOVERY RUN"}`;
  elements.advance.disabled = data.scenario_complete;
  const advanceLabels = elements.advance.querySelectorAll("span");
  advanceLabels[0].textContent = data.scenario_complete ? "Scenario complete" : "Run next agent event";
  advanceLabels[1].textContent = data.scenario_complete ? "DONE ✓" : "NEXT ▸";
}

async function loadCampaign() {
  elements.error.hidden = true;
  try { render(await request("/api/campaign")); } catch (error) { showError(error); }
}

elements.advance.addEventListener("click", async () => {
  const previousStep = campaign?.scenario_step;
  setBusy(elements.advance, true);
  try {
    const updated = await request("/api/demo/advance", {
      method: "POST",
      body: JSON.stringify({ idempotency_key: crypto.randomUUID().replaceAll("-", "_") }),
    });
    render(updated);
    if (updated.scenario_step === previousStep) {
      showToast("Mettle is waiting for your judgment before it can continue.");
      document.querySelector(".judgment input")?.focus();
    } else {
      showToast("Agent event processed. The recovery record is updated.");
    }
  } catch (error) {
    showError(error);
  } finally {
    if (campaign && !campaign.scenario_complete) setBusy(elements.advance, false);
  }
});

elements.reset.addEventListener("click", async () => {
  setBusy(elements.reset, true);
  try {
    render(await request("/api/demo/reset", { method: "POST", body: "{}" }));
    showToast("Recovery run reset to the opening campaign.");
  } catch (error) {
    showError(error);
  } finally {
    setBusy(elements.reset, false);
  }
});

document.addEventListener("keydown", (event) => {
  if (event.target instanceof HTMLInputElement) return;
  if (event.key === "ArrowRight" && !elements.advance.disabled) elements.advance.click();
  if (event.key.toLowerCase() === "r") elements.reset.click();
});

elements.retry.addEventListener("click", loadCampaign);
loadCampaign();
