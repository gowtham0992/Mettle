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
  evidencePanel: document.querySelector("#evidence-panel"),
  evidenceResult: document.querySelector("#evidence-result"),
  evidenceButtons: [...document.querySelectorAll(".evidence-submit")],
  metrics: document.querySelector("#metrics-list"),
  packet: document.querySelector("#packet-status"),
  packetList: document.querySelector("#packet-list"),
  packetNote: document.querySelector("#packet-note"),
  packetAction: document.querySelector("#packet-action"),
  demoStep: document.querySelector("#demo-step"),
  advance: document.querySelector("#advance-button"),
  reset: document.querySelector("#reset-button"),
  loadNotice: document.querySelector("#load-notice-button"),
  noticeDialog: document.querySelector("#notice-dialog"),
  noticeForm: document.querySelector("#notice-form"),
  noticeText: document.querySelector("#notice-text"),
  workflowAsOf: document.querySelector("#workflow-as-of"),
  workflowError: document.querySelector("#workflow-form-error"),
  startWorkflow: document.querySelector("#start-workflow-button"),
  startBedrock: document.querySelector("#start-bedrock-button"),
  startAgentCore: document.querySelector("#start-agentcore-button"),
  closeNotice: document.querySelector("#close-notice-button"),
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
let activeWorkflowId = null;
let activeWorkflowTarget = "local";
let toastTimer = null;
let bedrockEnabled = false;
let agentCoreEnabled = false;
let workflowCreateKey = null;
let workflowCreateProvider = null;

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

function workflowCampaign(envelope, executionTarget = "local") {
  const snapshot = envelope.snapshot;
  const notice = snapshot.notice;
  const plan = snapshot.plan;
  if (!notice || !plan) throw new Error("The workflow did not produce a notice and recovery plan.");

  const deliveries = new Map(snapshot.deliveries.map((item) => [item.citation_id, item]));
  const evidenceByCitation = new Map();
  for (const assessment of envelope.evidence || []) evidenceByCitation.set(assessment.citation_id, assessment);
  const pendingInterrupt = snapshot.interrupts[0] || null;
  const pendingJudgments = pendingInterrupt?.reason?.judgments || [];
  const judgmentByCitation = new Map(pendingJudgments.map((item) => [item.citation_id, item]));
  const timestamp = (hour, minute = 0) => `${plan.as_of}T${String(hour).padStart(2, "0")}:${String(minute).padStart(2, "0")}:00Z`;

  const citations = notice.citations.map((citation) => {
    const delivery = deliveries.get(citation.citation_id);
    const assessment = evidenceByCitation.get(citation.citation_id);
    const needsJudgment = judgmentByCitation.has(citation.citation_id);
    const assessedStage = assessment?.status === "accepted"
      ? "ready"
      : assessment?.status === "rejected" ? "evidence_rejected" : null;
    return {
      ...citation,
      assignee: delivery ? `${delivery.recipient.name} · ${delivery.recipient.phone}` : null,
      evidence_note: assessment?.explanation || (needsJudgment
        ? "Mettle needs an evidence-spec decision before outreach"
        : delivery?.message_id.endsWith("-decision")
          ? "Contractor-directed request recorded locally"
          : delivery ? "Initial request recorded locally" : "No outreach until contractor review"),
      stage: assessedStage || (needsJudgment ? "needs_judgment" : "awaiting_evidence"),
    };
  });

  const events = [
    {
      happened_at: timestamp(8, 14), kind: "notice_parsed", actor: envelope.intake_provider === "bedrock" ? "Mettle · Nova Micro intake" : "Mettle · local intake",
      title: `Parsed ${notice.citations.length} notice-anchored citations`,
      detail: "The correction notice became the recovery docket without project setup.",
    },
    {
      happened_at: timestamp(8, 15), kind: "plan_created", actor: "Mettle · planner",
      title: `Built ${plan.actions.length} autonomous outreach actions`,
      detail: `Cadence is anchored to the ${formatDate(notice.reinspection_due_on)} reinspection deadline.`,
    },
    ...snapshot.deliveries.map((delivery, index) => ({
      happened_at: timestamp(8, 16 + index), kind: "message_recorded", actor: "Mettle · coordinator",
      title: `${delivery.message_id.endsWith("-decision") ? "Recorded contractor-directed" : "Recorded"} C${delivery.citation_id} request for ${delivery.recipient.name}`,
      detail: "Local delivery adapter used; no live SMS was sent.",
    })),
  ];
  if (pendingInterrupt) {
    events.push({
      happened_at: timestamp(8, 19), kind: "judgment_requested", actor: "Mettle · judgment gate",
      title: "Paused at contractor judgment",
      detail: "Code interpretation stays with the licensed contractor.",
    });
  }
  if (snapshot.contractor_decision) {
    events.push({
      happened_at: timestamp(8, 20), kind: "judgment_resolved", actor: "Contractor",
      title: "Contractor decision recorded; graph resumed",
      detail: snapshot.contractor_decision,
    });
  }
  for (const [index, assessment] of (envelope.evidence || []).entries()) {
    events.push({
      happened_at: timestamp(9, index),
      kind: `evidence_${assessment.status}`,
      actor: "Mettle · evidence assessor",
      title: `${assessment.status === "accepted" ? "Accepted" : assessment.status === "rejected" ? "Rejected" : "Held"} C${assessment.citation_id} photo evidence`,
      detail: assessment.explanation,
    });
  }
  if (envelope.packet) {
    events.push({
      happened_at: timestamp(10, envelope.packet.status === "approved" ? 5 : 0),
      kind: envelope.packet.status === "approved" ? "judgment_resolved" : "packet_prepared",
      actor: envelope.packet.status === "approved" ? "Contractor" : "Mettle · packet builder",
      title: envelope.packet.status === "approved" ? "Final packet approved" : "Reinspection packet assembled",
      detail: envelope.packet.status === "approved"
        ? envelope.packet.approval_decision
        : "Download remains blocked until contractor approval.",
    });
  }

  const judgments = pendingJudgments.length && pendingInterrupt ? [{
    ...pendingJudgments[0],
    judgment_id: pendingInterrupt.interrupt_id,
    status: "pending",
  }] : [];
  if (envelope.packet?.status === "awaiting_approval") {
    judgments.push({
      judgment_id: envelope.packet.approval_id,
      kind: "final_packet_approval",
      citation_id: null,
      question: "Approve this packet for reinspection scheduling?",
      reason: "All citations have accepted evidence. Download remains blocked until your final decision.",
      status: "pending",
      packet_approval: true,
    });
  }

  const citationsReady = [...evidenceByCitation.values()].filter((item) => item.status === "accepted").length;
  return {
    source_mode: "workflow",
    execution_target: executionTarget,
    intake_provider: envelope.intake_provider || "local",
    workflow_status: snapshot.status,
    notice_id: notice.notice_id,
    property_label: notice.property_label,
    as_of: plan.as_of,
    days_remaining: plan.days_remaining,
    priority: plan.priority,
    citations,
    evidence: envelope.evidence || [],
    packet: envelope.packet,
    events,
    judgments,
    packet_status: envelope.packet?.status === "approved"
      ? "approved"
      : envelope.packet?.status === "awaiting_approval" ? "awaiting_approval" : "blocked",
    metrics: {
      citations_ready: citationsReady,
      citations_total: citations.length,
      messages_handled: snapshot.deliveries.length,
      automated_actions: 2 + snapshot.deliveries.length + (envelope.evidence || []).length,
      contractor_decisions: (snapshot.contractor_decision ? 1 : 0)
        + (envelope.packet?.status === "approved" ? 1 : 0),
    },
    scenario_step: 0,
    scenario_complete: true,
  };
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
      if (activeWorkflowId && judgment.packet_approval) {
        const envelope = await request(`/api/workflows/${encodeURIComponent(activeWorkflowId)}/packet/approve`, {
          method: "POST",
          headers: { "Idempotency-Key": crypto.randomUUID().replaceAll("-", "_") },
          body: JSON.stringify({ approval_id: judgment.judgment_id, decision }),
        });
        campaign = workflowCampaign(envelope);
      } else if (activeWorkflowId) {
        const workflowRoot = activeWorkflowTarget === "agentcore"
          ? "/api/agentcore/workflows"
          : "/api/workflows";
        const envelope = await request(`${workflowRoot}/${encodeURIComponent(activeWorkflowId)}/resume`, {
          method: "POST",
          headers: { "Idempotency-Key": crypto.randomUUID().replaceAll("-", "_") },
          body: JSON.stringify({ interrupt_id: judgment.judgment_id, decision }),
        });
        campaign = workflowCampaign(envelope, activeWorkflowTarget);
      } else {
        campaign = await request(`/api/judgments/${encodeURIComponent(judgment.judgment_id)}/resolve`, {
          method: "POST",
          body: JSON.stringify({ decision }),
        });
      }
      render(campaign);
      showToast(judgment.packet_approval
        ? "Final approval recorded. The reinspection PDF is ready to download."
        : "Your decision is logged. Mettle resumed the recovery run.");
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
  const isWorkflow = data.source_mode === "workflow";
  const isAgentCore = isWorkflow && data.execution_target === "agentcore";
  elements.evidencePanel.hidden = !isWorkflow || isAgentCore;
  if (isWorkflow && !isAgentCore) {
    const latestEvidence = data.evidence.at(-1);
    elements.evidenceResult.hidden = !latestEvidence;
    if (latestEvidence) {
      elements.evidenceResult.className = `evidence-result evidence-result--${latestEvidence.status}`;
      elements.evidenceResult.replaceChildren(
        node("strong", "", latestEvidence.status.replaceAll("_", " ")),
        node("span", "", latestEvidence.explanation),
      );
    }
    const contractorDecisionRecorded = data.events.some(
      (event) => event.title === "Contractor decision recorded; graph resumed",
    );
    for (const button of elements.evidenceButtons) {
      button.disabled = button.dataset.requiresDecision === "true" && !contractorDecisionRecorded;
      button.title = button.disabled ? "Resolve the mechanical evidence specification first" : "";
    }
  }
  elements.packetAction.hidden = !isWorkflow || isAgentCore
    || (data.metrics.citations_ready < data.metrics.citations_total && data.packet_status !== "approved");
  elements.packetAction.textContent = data.packet_status === "approved"
    ? "Download approved PDF"
    : data.packet_status === "awaiting_approval" ? "Awaiting your approval" : "Prepare packet for approval";
  elements.packetAction.disabled = data.packet_status === "awaiting_approval";
  elements.packetNote.textContent = isAgentCore
    ? "AgentCore completed notice intake, outreach, and contractor judgment. Continue the full evidence-to-packet scenario in local demo mode."
    : "Assembles as evidence is accepted. Nothing reaches the inspector until you approve it.";
  elements.demoStep.textContent = isWorkflow
    ? `${isAgentCore ? "AGENTCORE + " : ""}${data.intake_provider === "bedrock" ? "BEDROCK + " : ""}STRANDS · ${data.workflow_status === "interrupted" ? "WAITING FOR YOU" : "GRAPH COMPLETE"}`
    : `${data.scenario_step} · ${stepLabels[data.scenario_step] || "RECOVERY RUN"}`;
  elements.advance.disabled = isWorkflow || data.scenario_complete;
  const advanceLabels = elements.advance.querySelectorAll("span");
  advanceLabels[0].textContent = isWorkflow ? "Real workflow active" : data.scenario_complete ? "Scenario complete" : "Run next agent event";
  advanceLabels[1].textContent = isWorkflow ? "LIVE" : data.scenario_complete ? "DONE ✓" : "NEXT ▸";
  elements.reset.querySelector("span").textContent = isWorkflow ? "RETURN TO DEMO" : "RESET";
}

async function loadCampaign() {
  elements.error.hidden = true;
  const workflowId = new URLSearchParams(window.location.search).get("workflow");
  const workflowTarget = new URLSearchParams(window.location.search).get("runtime") === "agentcore"
    ? "agentcore"
    : "local";
  try {
    if (workflowId) {
      activeWorkflowId = workflowId;
      activeWorkflowTarget = workflowTarget;
      const workflowRoot = workflowTarget === "agentcore"
        ? "/api/agentcore/workflows"
        : "/api/workflows";
      render(workflowCampaign(
        await request(`${workflowRoot}/${encodeURIComponent(workflowId)}`),
        workflowTarget,
      ));
    } else {
      activeWorkflowId = null;
      activeWorkflowTarget = "local";
      render(await request("/api/campaign"));
    }
  } catch (error) { showError(error); }
}

async function loadCapabilities() {
  try {
    const capabilities = await request("/api/capabilities");
    bedrockEnabled = capabilities.bedrock_intake === true;
    agentCoreEnabled = capabilities.agentcore_runtime === true;
  } catch (_error) {
    bedrockEnabled = false;
    agentCoreEnabled = false;
  }
  elements.startBedrock.disabled = !bedrockEnabled;
  elements.startBedrock.title = bedrockEnabled
    ? "Run notice intake on Amazon Nova Micro; this consumes AWS credit"
    : "Start the server with Bedrock enabled to use live intake";
  elements.startAgentCore.disabled = !agentCoreEnabled;
  elements.startAgentCore.title = agentCoreEnabled
    ? "Run the Strands graph on the deployed AgentCore runtime; this consumes AWS credit"
    : "Start the server with AgentCore enabled to use the deployed runtime";
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
    if (activeWorkflowId) {
      activeWorkflowId = null;
      activeWorkflowTarget = "local";
      window.history.replaceState({}, "", window.location.pathname);
    }
    render(await request("/api/demo/reset", { method: "POST", body: "{}" }));
    showToast("Recovery run reset to the opening campaign.");
  } catch (error) {
    showError(error);
  } finally {
    setBusy(elements.reset, false);
  }
});

elements.loadNotice.addEventListener("click", () => {
  elements.workflowError.hidden = true;
  elements.noticeDialog.showModal();
  elements.noticeText.focus();
});

elements.closeNotice.addEventListener("click", () => elements.noticeDialog.close());

elements.noticeForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const noticeText = elements.noticeText.value.trim();
  if (!noticeText) return;
  const executionTarget = event.submitter?.value === "agentcore" ? "agentcore" : "local";
  const provider = event.submitter?.value === "local" ? "local" : "bedrock";
  if (provider === "bedrock" && executionTarget === "local" && !bedrockEnabled) return;
  if (executionTarget === "agentcore" && !agentCoreEnabled) return;
  const createMode = `${executionTarget}:${provider}`;
  if (!workflowCreateKey || workflowCreateProvider !== createMode) {
    workflowCreateKey = crypto.randomUUID().replaceAll("-", "_");
    workflowCreateProvider = createMode;
  }
  const submittedKey = workflowCreateKey;
  setBusy(elements.startWorkflow, true);
  setBusy(elements.startBedrock, true);
  setBusy(elements.startAgentCore, true);
  elements.workflowError.hidden = true;
  try {
    const workflowRoot = executionTarget === "agentcore"
      ? "/api/agentcore/workflows"
      : "/api/workflows";
    const envelope = await request(workflowRoot, {
      method: "POST",
      headers: { "Idempotency-Key": submittedKey },
      body: JSON.stringify({
        notice_text: noticeText,
        intake_provider: provider,
        as_of: elements.workflowAsOf.value,
        roster: [
          { trade: "electrical", name: "Mike Alvarez", phone: "+13035550101" },
          { trade: "framing", name: "Jen Ortiz", phone: "+13035550102" },
          { trade: "mechanical", name: "Luis Vega", phone: "+13035550103" },
        ],
      }),
    });
    activeWorkflowId = envelope.workflow_id;
    activeWorkflowTarget = executionTarget;
    const targetQuery = executionTarget === "agentcore" ? "&runtime=agentcore" : "";
    window.history.replaceState({}, "", `${window.location.pathname}?workflow=${encodeURIComponent(activeWorkflowId)}${targetQuery}`);
    render(workflowCampaign(envelope, executionTarget));
    elements.noticeDialog.close();
    workflowCreateKey = null;
    workflowCreateProvider = null;
    showToast(executionTarget === "agentcore"
      ? "AgentCore ran the deployed Strands recovery graph and paused only for your judgment."
      : provider === "bedrock"
        ? "Nova Micro grounded the notice; Strands ran recovery and paused only for your judgment."
      : "Local intake and Strands ran recovery, then paused only for your judgment.");
  } catch (error) {
    elements.workflowError.textContent = error.message;
    elements.workflowError.hidden = false;
  } finally {
    setBusy(elements.startWorkflow, false);
    elements.startBedrock.disabled = !bedrockEnabled;
    elements.startBedrock.setAttribute("aria-busy", "false");
    elements.startAgentCore.disabled = !agentCoreEnabled;
    elements.startAgentCore.setAttribute("aria-busy", "false");
  }
});

elements.noticeForm.addEventListener("input", () => {
  workflowCreateKey = null;
  workflowCreateProvider = null;
});

for (const button of elements.evidenceButtons) {
  button.addEventListener("click", async () => {
    if (!activeWorkflowId) return;
    setBusy(button, true);
    try {
      const envelope = await request(`/api/workflows/${encodeURIComponent(activeWorkflowId)}/evidence`, {
        method: "POST",
        headers: { "Idempotency-Key": crypto.randomUUID().replaceAll("-", "_") },
        body: JSON.stringify({
          citation_id: button.dataset.citation || "1",
          sample_id: button.dataset.sample,
        }),
      });
      campaign = workflowCampaign(envelope);
      render(campaign);
      const result = envelope.evidence.at(-1);
      showToast(result.status === "accepted"
        ? "Evidence accepted for sufficiency. Mettle still does not certify compliance."
        : "Evidence rejected. Mettle produced a notice-specific re-request.");
    } catch (error) {
      showError(error);
    } finally {
      setBusy(button, false);
    }
  });
}

elements.packetAction.addEventListener("click", async () => {
  if (!activeWorkflowId) return;
  if (campaign?.packet_status === "approved") {
    window.location.assign(`/api/workflows/${encodeURIComponent(activeWorkflowId)}/packet.pdf`);
    return;
  }
  setBusy(elements.packetAction, true);
  try {
    const envelope = await request(`/api/workflows/${encodeURIComponent(activeWorkflowId)}/packet/prepare`, {
      method: "POST",
      headers: { "Idempotency-Key": crypto.randomUUID().replaceAll("-", "_") },
      body: "{}",
    });
    campaign = workflowCampaign(envelope);
    render(campaign);
    document.querySelector(".judgment input")?.focus();
    showToast("Packet assembled. Download remains blocked until your final approval.");
  } catch (error) {
    showError(error);
  } finally {
    if (campaign?.packet_status !== "awaiting_approval") {
      setBusy(elements.packetAction, false);
    }
  }
});

document.addEventListener("keydown", (event) => {
  if (event.target instanceof HTMLInputElement || event.target instanceof HTMLTextAreaElement || elements.noticeDialog.open) return;
  if (event.key === "ArrowRight" && !elements.advance.disabled) elements.advance.click();
  if (event.key.toLowerCase() === "r") elements.reset.click();
});

elements.retry.addEventListener("click", loadCampaign);
loadCapabilities();
loadCampaign();
