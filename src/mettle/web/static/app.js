const elements = {
  band: document.querySelector(".command-band"),
  campaignStrip: document.querySelector(".campaign-strip"),
  loading: document.querySelector("#loading-state"),
  dashboard: document.querySelector("#dashboard"),
  nextAction: document.querySelector("#next-action"),
  nextActionEyebrow: document.querySelector("#next-action-eyebrow"),
  nextActionTitle: document.querySelector("#next-action-title"),
  nextActionCopy: document.querySelector("#next-action-copy"),
  nextActionButton: document.querySelector("#next-action-button"),
  nextActionMeta: document.querySelector("#next-action-meta"),
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
  agentRunMode: document.querySelector("#agent-run-mode"),
  agentRunSummary: document.querySelector("#agent-run-summary"),
  agentNodes: document.querySelector("#agent-node-list"),
  judgments: document.querySelector("#judgment-list"),
  judgmentCount: document.querySelector("#judgment-count"),
  recoveryClock: document.querySelector("#recovery-clock"),
  clockTrack: document.querySelector("#clock-track"),
  clockTitle: document.querySelector("#clock-title"),
  clockCopy: document.querySelector("#clock-copy"),
  clockAction: document.querySelector("#clock-action"),
  evidencePanel: document.querySelector("#evidence-panel"),
  evidenceResult: document.querySelector("#evidence-result"),
  evidenceButtons: [...document.querySelectorAll(".evidence-submit")],
  demoEvidence: document.querySelector("#demo-evidence"),
  photoForm: document.querySelector("#photo-evidence-form"),
  photoCitation: document.querySelector("#photo-citation"),
  photoFile: document.querySelector("#photo-file"),
  photoSubmit: document.querySelector("#photo-submit"),
  photoError: document.querySelector("#photo-error"),
  metrics: document.querySelector("#metrics-list"),
  packet: document.querySelector("#packet-status"),
  packetList: document.querySelector("#packet-list"),
  packetPreview: document.querySelector("#packet-preview"),
  packetNote: document.querySelector("#packet-note"),
  packetAction: document.querySelector("#packet-action"),
  demoStep: document.querySelector("#demo-step"),
  driverTag: document.querySelector("#driver-tag"),
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
  auth: document.querySelector("#auth-button"),
  home: document.querySelector("#mettle-home"),
  welcomeDialog: document.querySelector("#welcome-dialog"),
  startRecoveryEntry: document.querySelector("#start-recovery-entry"),
  trySampleEntry: document.querySelector("#try-sample-entry"),
  resumeCurrentEntry: document.querySelector("#resume-current-entry"),
  setupStepLabel: document.querySelector("#setup-step-label"),
  setupPanes: [...document.querySelectorAll("[data-setup-pane]")],
  setupProgress: [...document.querySelectorAll("[data-setup-progress]")],
  setupBack: document.querySelector("#setup-back-button"),
  setupNext: document.querySelector("#setup-next-button"),
  setupFooterNote: document.querySelector("#setup-footer-note"),
  primaryContactName: document.querySelector("#primary-contact-name"),
  primaryContactPhone: document.querySelector("#primary-contact-phone"),
  contactNames: [...document.querySelectorAll("[data-contact-name]")],
  contactPhones: [...document.querySelectorAll("[data-contact-phone]")],
  reviewNoticeSummary: document.querySelector("#review-notice-summary"),
  reviewContactSummary: document.querySelector("#review-contact-summary"),
  correctionReviewList: document.querySelector("#correction-review-list"),
  approveCorrections: document.querySelector("#approve-corrections-button"),
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
let demoRunning = false;
let authConfig = null;
let accessToken = sessionStorage.getItem("mettle_access_token");
let setupStep = 1;
let setupReturnsToWelcome = false;
let pendingCorrectionReview = null;
let correctionReviewKey = null;
let nextActionHandler = null;

function base64Url(bytes) {
  return btoa(String.fromCharCode(...new Uint8Array(bytes)))
    .replaceAll("+", "-").replaceAll("/", "_").replaceAll("=", "");
}

function tokenIsCurrent(token) {
  if (!token) return false;
  try {
    const encoded = token.split(".")[1].replaceAll("-", "+").replaceAll("_", "/");
    const padded = encoded.padEnd(Math.ceil(encoded.length / 4) * 4, "=");
    const payload = JSON.parse(atob(padded));
    return Number(payload.exp || 0) > Math.floor(Date.now() / 1000) + 30;
  } catch (_error) {
    return false;
  }
}

function clearAuth() {
  accessToken = null;
  sessionStorage.removeItem("mettle_access_token");
  updateAuthControl();
}

function updateAuthControl() {
  if (!authConfig?.cognito_domain || !authConfig?.cognito_client_id) {
    elements.auth.hidden = true;
    return;
  }
  if (accessToken && !tokenIsCurrent(accessToken)) {
    clearAuth();
    return;
  }
  elements.auth.hidden = false;
  elements.auth.textContent = accessToken ? "Sign out" : "Sign in for live run";
}

async function beginLogin() {
  if (!authConfig?.cognito_domain || !authConfig?.cognito_client_id) {
    throw new Error("Live sign-in is not configured on this deployment.");
  }
  const verifier = base64Url(crypto.getRandomValues(new Uint8Array(48)));
  const challenge = base64Url(await crypto.subtle.digest("SHA-256", new TextEncoder().encode(verifier)));
  const state = base64Url(crypto.getRandomValues(new Uint8Array(24)));
  sessionStorage.setItem("mettle_pkce_verifier", verifier);
  sessionStorage.setItem("mettle_oauth_state", state);
  const params = new URLSearchParams({
    response_type: "code",
    client_id: authConfig.cognito_client_id,
    redirect_uri: `${window.location.origin}/`,
    scope: "openid email",
    state,
    code_challenge_method: "S256",
    code_challenge: challenge,
  });
  window.location.assign(`${authConfig.cognito_domain}/oauth2/authorize?${params}`);
}

async function finishLogin() {
  const params = new URLSearchParams(window.location.search);
  const code = params.get("code");
  if (!code) return;
  const expectedState = sessionStorage.getItem("mettle_oauth_state");
  const verifier = sessionStorage.getItem("mettle_pkce_verifier");
  if (!expectedState || params.get("state") !== expectedState || !verifier) {
    throw new Error("The sign-in response could not be verified. Please try again.");
  }
  const response = await fetch(`${authConfig.cognito_domain}/oauth2/token`, {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body: new URLSearchParams({
      grant_type: "authorization_code",
      client_id: authConfig.cognito_client_id,
      code,
      redirect_uri: `${window.location.origin}/`,
      code_verifier: verifier,
    }),
  });
  const payload = await response.json();
  if (!response.ok || !tokenIsCurrent(payload.access_token)) {
    throw new Error("Sign-in did not return a usable access token.");
  }
  accessToken = payload.access_token;
  sessionStorage.setItem("mettle_access_token", accessToken);
  sessionStorage.removeItem("mettle_oauth_state");
  sessionStorage.removeItem("mettle_pkce_verifier");
  window.history.replaceState({}, "", window.location.pathname);
}

async function initializeAuth() {
  try {
    const response = await fetch("/api/config", { headers: { Accept: "application/json" } });
    authConfig = response.ok ? await response.json() : null;
    await finishLogin();
  } catch (error) {
    showError(error);
  }
  updateAuthControl();
}

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

function daysBetween(from, to) {
  return Math.round((Date.parse(`${to}T12:00:00Z`) - Date.parse(`${from}T12:00:00Z`)) / 86_400_000);
}

function campaignCheckpoints(deadline) {
  const deadlineAtNoon = Date.parse(`${deadline}T12:00:00Z`);
  return [7, 3, 2, 1, 0].map((daysBefore) => ({
    label: daysBefore ? `T−${daysBefore}` : "DUE",
    date: new Date(deadlineAtNoon - daysBefore * 86_400_000).toISOString().slice(0, 10),
  }));
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
  const correctionReviewRequired = pendingInterrupt?.name === "correction-review";
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
    ...snapshot.deliveries.map((delivery, index) => {
      const followUp = delivery.message_id.endsWith("-followup");
      const contractorDirected = delivery.message_id.endsWith("-decision");
      return {
        happened_at: `${delivery.scheduled_on}T08:${String(16 + index).padStart(2, "0")}:00Z`,
        kind: followUp ? "deadline_escalation" : "message_recorded",
        actor: followUp ? "Mettle · chase graph" : "Mettle · coordinator",
        title: followUp
          ? `Autonomously followed up C${delivery.citation_id} with ${delivery.recipient.name}`
          : `${contractorDirected ? "Recorded contractor-directed" : "Recorded"} C${delivery.citation_id} request for ${delivery.recipient.name}`,
        detail: followUp
          ? `${plan.priority.toUpperCase()} cadence at ${daysBetween(delivery.scheduled_on, notice.reinspection_due_on)} day(s) to reinspection; no live SMS was sent.`
          : "Local delivery adapter used; no live SMS was sent.",
      };
    }),
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
  if (snapshot.deadline_decision) {
    events.push({
      happened_at: timestamp(8, 21), kind: "judgment_resolved", actor: "Contractor",
      title: "Deadline tradeoff resolved; chase graph resumed",
      detail: snapshot.deadline_decision,
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
  const graphRun = (snapshot.agent_run || []).map((step) => ({
    sequence: step.sequence,
    graph: step.graph,
    node_id: step.node_id,
    actor: step.actor,
    status: step.status,
    detail: `${step.graph.replaceAll("_", " ")} graph · ${step.node_id.replaceAll("_", " ")}`,
  }));
  let evidenceSequence = graphRun.length;
  const evidenceRun = (envelope.evidence || []).flatMap((assessment) =>
    (assessment.agent_run || []).map((step) => ({
      sequence: ++evidenceSequence,
      graph: "evidence",
      node_id: step.step.toLowerCase().replaceAll(" ", "_"),
      actor: "Evidence agent",
      status: step.status,
      detail: `C${assessment.citation_id} · ${step.detail}`,
    })),
  );
  return {
    source_mode: "workflow",
    execution_target: executionTarget,
    intake_provider: envelope.intake_provider || "local",
    workflow_status: snapshot.status,
    correction_review_required: correctionReviewRequired,
    correction_review_interrupt: correctionReviewRequired ? pendingInterrupt.interrupt_id : null,
    review_citations: correctionReviewRequired ? pendingInterrupt.reason.citations : [],
    notice_id: notice.notice_id,
    property_label: notice.property_label,
    as_of: plan.as_of,
    deadline_on: notice.reinspection_due_on,
    days_remaining: plan.days_remaining,
    priority: plan.priority,
    citations,
    evidence: envelope.evidence || [],
    packet: envelope.packet,
    events,
    agent_run: [...graphRun, ...evidenceRun],
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
        + (snapshot.deadline_decision ? 1 : 0)
        + (envelope.packet?.status === "approved" ? 1 : 0),
    },
    scenario_step: 0,
    scenario_complete: true,
  };
}

async function request(path, options = {}) {
  const headers = { ...(options.headers || {}) };
  if (path.startsWith("/api/agentcore")) {
    if (!tokenIsCurrent(accessToken)) {
      clearAuth();
      throw new Error("Sign in before using the live AgentCore runtime.");
    }
    headers.Authorization = `Bearer ${accessToken}`;
  }
  if (!Object.keys(headers).some((key) => key.toLowerCase() === "content-type")) {
    headers["Content-Type"] = "application/json";
  }
  const response = await fetch(path, {
    ...options,
    headers,
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

function normalizedPhone(value) {
  return value.trim().replace(/[\s().-]/g, "");
}

function activePhotoEnabled() {
  return activeWorkflowTarget === "agentcore" ? agentCoreEnabled : bedrockEnabled;
}

function setSetupStep(step) {
  setupStep = Math.max(1, Math.min(4, step));
  elements.setupStepLabel.textContent = `STEP ${setupStep} OF 4`;
  for (const pane of elements.setupPanes) pane.hidden = Number(pane.dataset.setupPane) !== setupStep;
  for (const marker of elements.setupProgress) {
    const markerStep = Number(marker.dataset.setupProgress);
    marker.classList.toggle("setup-progress__step--active", markerStep === setupStep);
    marker.classList.toggle("setup-progress__step--complete", markerStep < setupStep);
  }
  elements.setupBack.hidden = setupStep === 1 || setupStep === 4;
  elements.setupNext.hidden = setupStep >= 3;
  elements.startWorkflow.hidden = setupStep !== 3;
  elements.startBedrock.hidden = setupStep !== 3;
  elements.startAgentCore.hidden = setupStep !== 3;
  elements.approveCorrections.hidden = setupStep !== 4;
  elements.setupFooterNote.textContent = setupStep === 1
    ? "REPORT FIRST · NO PROJECT SETUP"
    : setupStep === 2 ? "SUBS USE THEIR PHONE · NO NEW ACCOUNT"
      : setupStep === 3 ? "EXTRACT ONLY · ZERO OUTREACH BEFORE REVIEW" : "YOU APPROVE · METTLE COORDINATES";
  elements.setupNext.textContent = setupStep === 1 ? "Next · add people" : "Next · review launch";
  const heading = setupStep === 1
    ? "Start with the failed-inspection report"
    : setupStep === 2 ? "Who owns the corrections?"
      : setupStep === 3 ? "Extract the correction docket" : "Review every correction before outreach";
  document.querySelector("#notice-dialog-title").textContent = heading;
}

function validateSetupStep() {
  elements.workflowError.hidden = true;
  if (setupStep === 1) {
    if (!elements.noticeText.value.trim()) {
      elements.noticeText.setCustomValidity("Paste the failed-inspection report or comments.");
      elements.noticeText.reportValidity();
      elements.noticeText.setCustomValidity("");
      return false;
    }
    if (!elements.workflowAsOf.value) {
      elements.workflowAsOf.reportValidity();
      return false;
    }
  }
  if (setupStep === 2) {
    const name = elements.primaryContactName.value.trim();
    const phone = normalizedPhone(elements.primaryContactPhone.value);
    if (!name) {
      elements.primaryContactName.reportValidity();
      return false;
    }
    if (!/^\+[1-9]\d{7,14}$/.test(phone)) {
      elements.primaryContactPhone.setCustomValidity("Use an international phone number such as +13035550100.");
      elements.primaryContactPhone.reportValidity();
      elements.primaryContactPhone.setCustomValidity("");
      return false;
    }
    for (const nameInput of elements.contactNames) {
      const trade = nameInput.dataset.contactName;
      const phoneInput = elements.contactPhones.find((item) => item.dataset.contactPhone === trade);
      const hasName = Boolean(nameInput.value.trim());
      const tradePhone = normalizedPhone(phoneInput.value);
      if (hasName !== Boolean(tradePhone)) {
        const incomplete = hasName ? phoneInput : nameInput;
        incomplete.setCustomValidity("Add both a contact name and phone number, or leave both blank.");
        incomplete.reportValidity();
        incomplete.setCustomValidity("");
        return false;
      }
      if (tradePhone && !/^\+[1-9]\d{7,14}$/.test(tradePhone)) {
        phoneInput.setCustomValidity("Use an international phone number such as +13035550101.");
        phoneInput.reportValidity();
        phoneInput.setCustomValidity("");
        return false;
      }
    }
  }
  if (setupStep === 4) {
    for (const card of elements.correctionReviewList.querySelectorAll("[data-review-citation]")) {
      const proof = card.querySelector("textarea");
      const requirements = proof.value.split("\n").map((item) => item.trim()).filter(Boolean);
      if (!requirements.length || requirements.some((item) => item.length > 500)) {
        proof.setCustomValidity("Add at least one proof request; keep each line under 500 characters.");
        proof.reportValidity();
        proof.setCustomValidity("");
        return false;
      }
    }
  }
  return true;
}

function renderCorrectionReview(data) {
  pendingCorrectionReview = data;
  correctionReviewKey = null;
  const tradeLabels = {
    electrical: "Electrical",
    framing: "Framing",
    mechanical: "Mechanical",
    plumbing: "Plumbing",
    general: "General contractor",
  };
  const routeLabels = {
    photo_evidence: "Photo evidence",
    document_evidence: "Document or letter",
    physical_reinspection: "Physical reinspection",
  };
  const cards = data.review_citations.map((citation) => {
    const card = node("article", "correction-review__card");
    card.dataset.reviewCitation = citation.citation_id;
    card.append(node("span", "correction-review__id", `C${citation.citation_id}`));
    card.append(node("span", "correction-review__code", `${citation.code_reference} · authority language`));
    card.append(node("p", "correction-review__authority", `“${citation.notice_text}”`));
    if (citation.ambiguity_reason) card.append(node("span", "correction-review__needs-you", `Needs your judgment: ${citation.ambiguity_reason}`));

    const fields = node("div", "correction-review__fields");
    const tradeLabel = node("label", "", "ASSIGN TO");
    const tradeSelect = node("select");
    tradeSelect.dataset.reviewTrade = "";
    tradeSelect.setAttribute("aria-label", `Trade for citation ${citation.citation_id}`);
    for (const [value, label] of Object.entries(tradeLabels)) {
      const option = node("option", "", label);
      option.value = value;
      option.selected = value === citation.trade || (citation.trade === "unknown" && value === "general");
      tradeSelect.append(option);
    }
    tradeLabel.append(tradeSelect);

    const routeLabel = node("label", "", "CLOSURE ROUTE");
    const routeSelect = node("select");
    routeSelect.dataset.reviewRoute = "";
    routeSelect.setAttribute("aria-label", `Closure route for citation ${citation.citation_id}`);
    for (const [value, label] of Object.entries(routeLabels)) {
      const option = node("option", "", label);
      option.value = value;
      option.selected = value === (citation.closure_route || "photo_evidence");
      routeSelect.append(option);
    }
    routeLabel.append(routeSelect);

    const proofLabel = node("label", "", "WHAT MUST COME BACK · ONE REQUIREMENT PER LINE");
    const proof = node("textarea");
    proof.dataset.reviewProof = "";
    proof.required = true;
    proof.maxLength = 5000;
    proof.placeholder = "Example: Wide photo showing the completed correction and its location";
    proof.setAttribute("aria-label", `Required proof for citation ${citation.citation_id}`);
    proof.value = (citation.evidence_requirements || []).join("\n");
    proofLabel.append(proof);
    fields.append(tradeLabel, routeLabel, proofLabel);
    card.append(fields);
    return card;
  });
  elements.correctionReviewList.replaceChildren(...cards);
}

function buildCorrectionReviewPayload() {
  return {
    interrupt_id: pendingCorrectionReview.correction_review_interrupt,
    citations: [...elements.correctionReviewList.querySelectorAll("[data-review-citation]")].map((card) => ({
      citation_id: card.dataset.reviewCitation,
      trade: card.querySelector("[data-review-trade]").value,
      closure_route: card.querySelector("[data-review-route]").value,
      evidence_requirements: card.querySelector("[data-review-proof]").value
        .split("\n").map((item) => item.trim()).filter(Boolean),
    })),
  };
}

function openPendingCorrectionReview(data) {
  renderCorrectionReview(data);
  elements.workflowError.hidden = true;
  setSetupStep(4);
  if (!elements.noticeDialog.open) elements.noticeDialog.showModal();
  window.setTimeout(() => elements.correctionReviewList.querySelector("select, textarea")?.focus(), 0);
}

function buildRoster() {
  const fallback = {
    name: elements.primaryContactName.value.trim(),
    phone: normalizedPhone(elements.primaryContactPhone.value),
  };
  return ["electrical", "framing", "mechanical", "plumbing", "general"].map((trade) => {
    const name = elements.contactNames.find((item) => item.dataset.contactName === trade)?.value.trim();
    const phone = normalizedPhone(elements.contactPhones.find((item) => item.dataset.contactPhone === trade)?.value || "");
    return { trade, name: name || fallback.name, phone: phone || fallback.phone };
  });
}

function updateLaunchReview() {
  const reportLines = elements.noticeText.value.split("\n").filter((line) => line.trim()).length;
  const namedTrades = elements.contactNames.filter((item) => item.value.trim()).length;
  elements.reviewNoticeSummary.textContent = `${reportLines} report lines · ${formatDate(elements.workflowAsOf.value)}`;
  elements.reviewContactSummary.textContent = `${elements.primaryContactName.value.trim()} + ${namedTrades} trade contact${namedTrades === 1 ? "" : "s"}`;
}

function openRecoverySetup({ returnToWelcome = false } = {}) {
  setupReturnsToWelcome = returnToWelcome;
  elements.workflowError.hidden = true;
  setSetupStep(1);
  elements.noticeDialog.showModal();
  window.setTimeout(() => elements.noticeText.focus(), 0);
}

function exitRecoverySetup() {
  const returnToWelcome = setupReturnsToWelcome;
  setupReturnsToWelcome = false;
  elements.noticeDialog.close();
  if (returnToWelcome) {
    sessionStorage.removeItem("mettle_entry_selected");
    window.setTimeout(() => {
      if (!elements.welcomeDialog.open) elements.welcomeDialog.showModal();
    }, 0);
  }
}

function configureNextAction(data) {
  const isWorkflow = data.source_mode === "workflow";
  const pending = data.judgments.filter((item) => item.status === "pending");
  const openCitation = data.citations.find((item) => item.stage !== "ready");
  elements.nextAction.hidden = false;
  elements.nextAction.classList.toggle("next-action--sample", !isWorkflow);
  elements.nextActionEyebrow.textContent = isWorkflow ? "YOUR NEXT MOVE" : "SAMPLE CAMPAIGN";
  elements.nextActionMeta.textContent = isWorkflow ? "ONE ACTION · CONTRACTOR CONTROLLED" : "SYNTHETIC DATA · 90 SECONDS";

  if (isWorkflow && data.correction_review_required) {
    elements.nextActionTitle.textContent = "Review the extracted corrections";
    elements.nextActionCopy.textContent = "No outreach has started. Confirm each assignee, closure route, and proof request first.";
    elements.nextActionButton.textContent = "Continue review";
    nextActionHandler = () => openPendingCorrectionReview(data);
    return;
  }

  if (!isWorkflow) {
    if (data.scenario_complete) {
      elements.nextActionTitle.textContent = "The sample recovery is complete";
      elements.nextActionCopy.textContent = "Start a redacted recovery to see Mettle derive a new docket from report text.";
      elements.nextActionButton.textContent = "Start a recovery";
      nextActionHandler = openRecoverySetup;
    } else if (pending.length) {
      elements.nextActionTitle.textContent = "Make the one decision Mettle cannot";
      elements.nextActionCopy.textContent = pending[0].question;
      elements.nextActionButton.textContent = "Review decision";
      nextActionHandler = () => document.querySelector(".judgment input")?.focus();
    } else {
      elements.nextActionTitle.textContent = "Watch Mettle run the recovery";
      elements.nextActionCopy.textContent = "The sample compresses days of evidence chasing, escalation, and packet assembly into one guided run.";
      elements.nextActionButton.textContent = "Run sample recovery";
      nextActionHandler = () => elements.advance.click();
    }
    return;
  }

  if (pending.length) {
    elements.nextActionTitle.textContent = pending[0].kind === "final_packet_approval" ? "Approve the final packet" : "Resolve the blocked decision";
    elements.nextActionCopy.textContent = pending[0].question;
    elements.nextActionButton.textContent = "Review decision";
    nextActionHandler = () => {
      document.querySelector(".judgment-panel")?.scrollIntoView({ behavior: "smooth", block: "center" });
      window.setTimeout(() => document.querySelector(".judgment input")?.focus(), 300);
    };
  } else if (openCitation) {
    elements.nextActionTitle.textContent = `Collect proof for C${openCitation.citation_id}`;
    elements.nextActionCopy.textContent = openCitation.stage === "evidence_rejected"
      ? "The last photo did not visibly show everything requested. Review the feedback and replace it."
      : "Choose the citation and add the photo or document the contractor expects to use for closure.";
    elements.nextActionButton.textContent = activePhotoEnabled() ? "Add evidence" : "Open evidence options";
    nextActionHandler = () => {
      elements.photoCitation.value = openCitation.citation_id;
      elements.evidencePanel.scrollIntoView({ behavior: "smooth", block: "start" });
      if (!activePhotoEnabled()) elements.demoEvidence.open = true;
      window.setTimeout(() => elements.photoFile.focus(), 300);
    };
  } else if (data.packet_status === "blocked") {
    elements.nextActionTitle.textContent = "Assemble the review packet";
    elements.nextActionCopy.textContent = "Every citation has accepted evidence. Prepare the packet before giving final approval.";
    elements.nextActionButton.textContent = "Prepare packet";
    nextActionHandler = () => elements.packetAction.click();
  } else if (data.packet_status === "approved") {
    elements.nextActionTitle.textContent = "Download the approved packet";
    elements.nextActionCopy.textContent = "The notice, evidence, recovery history, and your approval are ready in one artifact.";
    elements.nextActionButton.textContent = "Download PDF";
    nextActionHandler = () => elements.packetAction.click();
  } else {
    elements.nextActionTitle.textContent = "Run the next scheduled check";
    elements.nextActionCopy.textContent = "Mettle will replan only open citations and adjust follow-up intensity against the deadline.";
    elements.nextActionButton.textContent = "Run scheduled check";
    nextActionHandler = () => elements.clockAction.click();
  }
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

function sampleAgentRun(data) {
  const actorStatus = new Map();
  for (const event of [...data.events].reverse()) {
    const actor = event.actor.replace(/^Mettle · /, "");
    const interrupted = event.kind === "judgment_requested";
    actorStatus.set(actor, {
      actor,
      status: interrupted ? "interrupted" : "completed",
      detail: event.title,
    });
  }
  return [...actorStatus.values()].map((item, index) => ({ ...item, sequence: index + 1 }));
}

function renderAgentRun(data) {
  const isWorkflow = data.source_mode === "workflow";
  const steps = isWorkflow ? (data.agent_run || []) : sampleAgentRun(data);
  elements.agentRunMode.textContent = isWorkflow
    ? data.execution_target === "agentcore" ? "LIVE · AGENTCORE" : "LIVE · STRANDS"
    : "SAMPLE TRACE";
  const interrupted = steps.filter((step) => step.status === "interrupted").length;
  const completed = steps.filter((step) => step.status === "completed").length;
  elements.agentRunSummary.textContent = interrupted
    ? `${completed} agent steps completed · ${interrupted} paused for contractor judgment`
    : `${completed} agent steps completed · no unnecessary contractor interrupt`;
  elements.agentNodes.replaceChildren(...steps.map((step) => {
    const item = node("li", `agent-node agent-node--${step.status}`);
    item.append(node("span", "agent-node__sequence", String(step.sequence).padStart(2, "0")));
    const body = node("div", "agent-node__body");
    body.append(node("strong", "", step.actor));
    body.append(node("span", "", step.detail));
    item.append(body, node("span", "agent-node__status", step.status.toUpperCase()));
    return item;
  }));
}

function decisionPrompt(judgment) {
  if (judgment.kind === "final_packet_approval") {
    return ["Type your approval decision", "Approve packet"];
  }
  if (judgment.kind === "deadline_tradeoff") {
    return ["Keep the date, or request a new one?", "Record deadline decision"];
  }
  return ["Describe the evidence the trade must provide", "Set evidence requirement"];
}

function renderJudgment(judgment) {
  const isPacketApproval = judgment.packet_approval || judgment.kind === "final_packet_approval";
  const card = node("article", "judgment");
  card.append(node("div", "judgment__kind", `${titleCase(judgment.kind)}${judgment.citation_id ? ` · C${judgment.citation_id}` : ""}`));
  card.append(node("h3", "", judgment.question));
  card.append(node("p", "", judgment.reason));

  const [placeholder, buttonLabel] = decisionPrompt(judgment);
  const form = document.createElement("form");
  const label = node("label", "sr-only", "Contractor decision");
  const input = document.createElement("input");
  input.id = `decision-${judgment.judgment_id}`;
  label.htmlFor = input.id;
  input.name = "decision";
  input.required = true;
  input.minLength = 3;
  input.maxLength = 500;
  input.placeholder = placeholder;
  const button = node("button", "button", buttonLabel);
  button.type = "submit";
  form.append(label, input, button);
  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    const decision = input.value.trim();
    if (decision.length < 3) return;
    setBusy(button, true);
    try {
      if (activeWorkflowId && isPacketApproval) {
        const workflowRoot = activeWorkflowTarget === "agentcore"
          ? "/api/agentcore/workflows"
          : "/api/workflows";
        const envelope = await request(`${workflowRoot}/${encodeURIComponent(activeWorkflowId)}/packet/approve`, {
          method: "POST",
          headers: { "Idempotency-Key": crypto.randomUUID().replaceAll("-", "_") },
          body: JSON.stringify({ approval_id: judgment.judgment_id, decision }),
        });
        campaign = workflowCampaign(envelope, activeWorkflowTarget);
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
      showToast(isPacketApproval
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

  elements.packetPreview.hidden = data.packet_status !== "approved";
  if (data.packet_status === "approved") {
    const header = node("div", "packet-preview__header");
    header.append(
      node("span", "", "METTLE / REINSPECTION EVIDENCE PACKET"),
      node("strong", "", data.notice_id),
    );
    const summary = node("div", "packet-preview__summary");
    summary.append(
      node("span", "", `${data.metrics.citations_total} CITATIONS`),
      node("span", "", `${data.metrics.citations_ready} EVIDENCE SETS`),
      node("span", "", "CONTRACTOR APPROVED"),
    );
    elements.packetPreview.replaceChildren(
      header,
      node("p", "", "Notice language, accepted evidence, recovery history, and the human approval record—assembled into one reviewable artifact."),
      summary,
    );
  }
}

function renderRecoveryClock(data) {
  const checkpoints = campaignCheckpoints(data.deadline_on);
  elements.clockTrack.replaceChildren(...checkpoints.map((checkpoint) => {
    const stop = node("span", "clock-stop", checkpoint.label);
    if (checkpoint.date < data.as_of) stop.classList.add("clock-stop--passed");
    if (checkpoint.date === data.as_of) stop.classList.add("clock-stop--current");
    if (checkpoint.label === "DUE") stop.classList.add("clock-stop--due");
    stop.title = formatDate(checkpoint.date);
    return stop;
  }));

  const open = data.metrics.citations_total - data.metrics.citations_ready;
  const waiting = data.workflow_status === "interrupted";
  const next = checkpoints.find((checkpoint) => checkpoint.date > data.as_of);
  const closed = open === 0;
  const expired = !next;
  if (closed) {
    elements.clockTitle.textContent = "All citations closed · campaign standing down";
    elements.clockCopy.textContent = "Accepted evidence removed every citation from the chase plan. Mettle will send no further follow-ups.";
  } else if (waiting) {
    elements.clockTitle.textContent = `${open} open citation${open === 1 ? "" : "s"} · waiting for your decision`;
    elements.clockCopy.textContent = "The campaign is paused at a Strands judgment gate. Resolve it above before the next scheduled check.";
  } else if (expired) {
    elements.clockTitle.textContent = `${open} open citation${open === 1 ? "" : "s"} · deadline reached`;
    elements.clockCopy.textContent = "No later campaign checkpoint exists. Mettle will not invent outreach beyond the configured reinspection deadline.";
  } else {
    const nextDays = daysBetween(next.date, data.deadline_on);
    const behavior = nextDays <= 2 ? "critical four-hour follow-up and a contractor tradeoff gate" : "deadline-aware follow-up to each open trade";
    elements.clockTitle.textContent = `Next: ${next.label} · ${formatDate(next.date)}`;
    elements.clockCopy.textContent = `${open} open citation${open === 1 ? "" : "s"}. Mettle will replan only those citations, then run ${behavior}.`;
  }
  elements.clockAction.disabled = closed || waiting || expired || data.packet_status !== "blocked";
  elements.clockAction.textContent = waiting ? "Resolve decision to continue" : closed ? "Campaign stood down" : expired ? "Deadline reached" : "Simulate scheduled check";
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
  configureNextAction(data);

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
  renderAgentRun(data);

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
  elements.evidencePanel.hidden = !isWorkflow;
  elements.recoveryClock.hidden = !isWorkflow;
  elements.driverTag.textContent = isWorkflow ? "RECOVERY" : "SAMPLE";
  if (isWorkflow) renderRecoveryClock(data);
  if (isWorkflow) {
    const selectedCitation = elements.photoCitation.value;
    elements.photoCitation.replaceChildren(...data.citations.map((citation) => {
      const option = node("option", "", `C${citation.citation_id} · ${citation.trade}`);
      option.value = citation.citation_id;
      return option;
    }));
    if ([...elements.photoCitation.options].some((option) => option.value === selectedCitation)) {
      elements.photoCitation.value = selectedCitation;
    }
    const canAssessPhoto = activePhotoEnabled();
    elements.photoSubmit.disabled = !canAssessPhoto || !elements.photoFile.files?.length;
    elements.photoSubmit.title = canAssessPhoto
      ? "This live vision check consumes a small amount of AWS credit"
      : "Start Mettle with Bedrock or AgentCore enabled to assess real photos";
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
  elements.packetAction.hidden = isWorkflow
    ? data.metrics.citations_ready < data.metrics.citations_total && data.packet_status !== "approved"
    : data.packet_status !== "approved";
  elements.packetAction.textContent = data.packet_status === "approved"
    ? "Download approved PDF"
    : data.packet_status === "awaiting_approval" ? "Awaiting your approval" : "Prepare packet for approval";
  elements.packetAction.disabled = data.packet_status === "awaiting_approval";
  elements.packetNote.textContent = data.packet_status === "approved"
    ? "The approved artifact is ready. Download the same packet the contractor reviewed."
    : "Assembles as evidence is accepted. Nothing reaches the inspector until you approve it.";
  elements.demoStep.textContent = isWorkflow
    ? `${isAgentCore ? "AGENTCORE + " : ""}${data.intake_provider === "bedrock" ? "BEDROCK + " : ""}STRANDS · ${data.workflow_status === "interrupted" ? "WAITING FOR YOU" : "GRAPH COMPLETE"}`
    : `${data.scenario_step} · ${stepLabels[data.scenario_step] || "RECOVERY RUN"}`;
  elements.advance.disabled = isWorkflow || data.scenario_complete || demoRunning;
  elements.advance.hidden = isWorkflow;
  elements.reset.disabled = demoRunning;
  elements.loadNotice.disabled = demoRunning;
  const advanceLabels = elements.advance.querySelectorAll("span");
  advanceLabels[0].textContent = isWorkflow ? "Real workflow active" : data.scenario_complete ? "Scenario complete" : demoRunning ? "Recovery running" : "Run compressed recovery";
  advanceLabels[1].textContent = isWorkflow ? "LIVE" : data.scenario_complete ? "DONE ✓" : demoRunning ? "WORKING…" : "AUTO ▶";
  elements.loadNotice.querySelector("span").textContent = isWorkflow ? "NEW" : "LOAD";
  elements.reset.querySelector("span").textContent = isWorkflow ? "SAMPLE" : "RESET";
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
      if (!sessionStorage.getItem("mettle_entry_selected") && !elements.welcomeDialog.open) {
        elements.welcomeDialog.showModal();
      }
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

elements.photoFile.addEventListener("change", () => {
  elements.photoError.hidden = true;
  elements.photoSubmit.disabled = !activePhotoEnabled() || !elements.photoFile.files?.length;
});

elements.photoForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  if (!activeWorkflowId || !elements.photoFile.files?.length || !activePhotoEnabled()) return;
  const file = elements.photoFile.files[0];
  elements.photoError.hidden = true;
  setBusy(elements.photoSubmit, true);
  try {
    const workflowRoot = activeWorkflowTarget === "agentcore"
      ? "/api/agentcore/workflows"
      : "/api/workflows";
    const citation = encodeURIComponent(elements.photoCitation.value);
    const envelope = await request(`${workflowRoot}/${encodeURIComponent(activeWorkflowId)}/evidence/photo?citation_id=${citation}`, {
      method: "POST",
      headers: {
        "Content-Type": file.type,
        "Idempotency-Key": crypto.randomUUID().replaceAll("-", "_"),
      },
      body: file,
    });
    campaign = workflowCampaign(envelope, activeWorkflowTarget);
    render(campaign);
    const result = envelope.evidence.at(-1);
    showToast(result.status === "accepted"
      ? "Photo visibly satisfies every notice evidence requirement."
      : result.status === "manual_review"
        ? "The image is ambiguous. Mettle reserved the decision for you."
        : "Photo rejected with a specific re-request for the trade.");
    elements.photoForm.reset();
  } catch (error) {
    elements.photoError.textContent = error.message;
    elements.photoError.hidden = false;
  } finally {
    elements.photoSubmit.disabled = !activePhotoEnabled() || !elements.photoFile.files?.length;
    elements.photoSubmit.setAttribute("aria-busy", "false");
  }
});

elements.advance.addEventListener("click", async () => {
  if (demoRunning || activeWorkflowId || campaign?.scenario_complete) return;
  demoRunning = true;
  render(campaign);
  try {
    while (!campaign.scenario_complete) {
      const previousStep = campaign.scenario_step;
      const updated = await request("/api/demo/advance", {
        method: "POST",
        body: JSON.stringify({ idempotency_key: crypto.randomUUID().replaceAll("-", "_") }),
      });
      campaign = updated;
      render(updated);
      if (updated.scenario_step === previousStep) {
        showToast("Mettle paused the campaign for your judgment.");
        document.querySelector(".judgment input")?.focus();
        break;
      }
      if (!updated.scenario_complete) {
        await new Promise((resolve) => window.setTimeout(resolve, 1400));
      }
    }
  } catch (error) {
    showError(error);
  } finally {
    demoRunning = false;
    if (campaign) render(campaign);
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

elements.nextActionButton.addEventListener("click", () => nextActionHandler?.());

elements.home.addEventListener("click", (event) => {
  event.preventDefault();
  setupReturnsToWelcome = false;
  if (elements.noticeDialog.open) elements.noticeDialog.close();
  elements.resumeCurrentEntry.hidden = !activeWorkflowId;
  if (!elements.welcomeDialog.open) elements.welcomeDialog.showModal();
});

elements.startRecoveryEntry.addEventListener("click", () => {
  elements.welcomeDialog.close();
  openRecoverySetup({ returnToWelcome: true });
});

elements.trySampleEntry.addEventListener("click", async () => {
  sessionStorage.setItem("mettle_entry_selected", "sample");
  elements.welcomeDialog.close();
  if (activeWorkflowId) {
    activeWorkflowId = null;
    activeWorkflowTarget = "local";
    window.history.replaceState({}, "", window.location.pathname);
    try {
      render(await request("/api/campaign"));
    } catch (error) {
      showError(error);
    }
  }
  elements.nextActionButton.focus();
});

elements.resumeCurrentEntry.addEventListener("click", () => {
  elements.welcomeDialog.close();
  elements.nextActionButton.focus();
});

elements.setupNext.addEventListener("click", () => {
  if (!validateSetupStep()) return;
  if (setupStep === 2) updateLaunchReview();
  setSetupStep(setupStep + 1);
  const pane = elements.setupPanes.find((item) => Number(item.dataset.setupPane) === setupStep);
  pane?.querySelector("input, textarea, button")?.focus();
});

elements.setupBack.addEventListener("click", () => {
  setSetupStep(setupStep - 1);
  const pane = elements.setupPanes.find((item) => Number(item.dataset.setupPane) === setupStep);
  pane?.querySelector("input, textarea, button")?.focus();
});

elements.loadNotice.addEventListener("click", () => openRecoverySetup());

elements.closeNotice.addEventListener("click", exitRecoverySetup);

elements.noticeDialog.addEventListener("cancel", (event) => {
  event.preventDefault();
  exitRecoverySetup();
});

elements.noticeForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  if (setupStep !== 3) return;
  const noticeText = elements.noticeText.value.trim();
  if (!noticeText) return;
  const executionTarget = event.submitter?.value === "agentcore" ? "agentcore" : "local";
  const provider = event.submitter?.value === "local" ? "local" : "bedrock";
  if (provider === "bedrock" && executionTarget === "local" && !bedrockEnabled) return;
  if (executionTarget === "agentcore" && !agentCoreEnabled) return;
  if (executionTarget === "agentcore" && !tokenIsCurrent(accessToken)) {
    await beginLogin();
    return;
  }
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
        roster: buildRoster(),
      }),
    });
    activeWorkflowId = envelope.workflow_id;
    activeWorkflowTarget = executionTarget;
    const targetQuery = executionTarget === "agentcore" ? "&runtime=agentcore" : "";
    window.history.replaceState({}, "", `${window.location.pathname}?workflow=${encodeURIComponent(activeWorkflowId)}${targetQuery}`);
    const workflowView = workflowCampaign(envelope, executionTarget);
    render(workflowView);
    sessionStorage.setItem("mettle_entry_selected", "recovery");
    workflowCreateKey = null;
    workflowCreateProvider = null;
    if (workflowView.correction_review_required) {
      openPendingCorrectionReview(workflowView);
      showToast(executionTarget === "agentcore"
        ? "AgentCore extracted the docket and paused before outreach for your review."
        : provider === "bedrock"
          ? "Nova Micro grounded the notice; Strands paused before outreach for your review."
          : "Local intake extracted the docket; Strands paused before outreach for your review.");
    } else {
      setupReturnsToWelcome = false;
      elements.noticeDialog.close();
    }
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

elements.approveCorrections.addEventListener("click", async () => {
  if (!pendingCorrectionReview || !activeWorkflowId || !validateSetupStep()) return;
  if (!correctionReviewKey) correctionReviewKey = crypto.randomUUID().replaceAll("-", "_");
  const workflowRoot = activeWorkflowTarget === "agentcore"
    ? "/api/agentcore/workflows"
    : "/api/workflows";
  setBusy(elements.approveCorrections, true);
  elements.workflowError.hidden = true;
  try {
    const envelope = await request(`${workflowRoot}/${encodeURIComponent(activeWorkflowId)}/review`, {
      method: "POST",
      headers: { "Idempotency-Key": correctionReviewKey },
      body: JSON.stringify(buildCorrectionReviewPayload()),
    });
    const workflowView = workflowCampaign(envelope, activeWorkflowTarget);
    render(workflowView);
    pendingCorrectionReview = null;
    correctionReviewKey = null;
    setupReturnsToWelcome = false;
    elements.noticeDialog.close();
    showToast(`Review approved. Mettle recorded ${envelope.snapshot.deliveries.length} notice-anchored request${envelope.snapshot.deliveries.length === 1 ? "" : "s"}.`);
  } catch (error) {
    elements.workflowError.textContent = error.message;
    elements.workflowError.hidden = false;
  } finally {
    setBusy(elements.approveCorrections, false);
  }
});

elements.noticeForm.addEventListener("input", () => {
  workflowCreateKey = null;
  workflowCreateProvider = null;
  correctionReviewKey = null;
});

for (const button of elements.evidenceButtons) {
  button.addEventListener("click", async () => {
    if (!activeWorkflowId) return;
    setBusy(button, true);
    try {
      const workflowRoot = activeWorkflowTarget === "agentcore"
        ? "/api/agentcore/workflows"
        : "/api/workflows";
      const envelope = await request(`${workflowRoot}/${encodeURIComponent(activeWorkflowId)}/evidence`, {
        method: "POST",
        headers: { "Idempotency-Key": crypto.randomUUID().replaceAll("-", "_") },
        body: JSON.stringify({
          citation_id: button.dataset.citation || "1",
          sample_id: button.dataset.sample,
        }),
      });
      campaign = workflowCampaign(envelope, activeWorkflowTarget);
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

elements.clockAction.addEventListener("click", async () => {
  if (!activeWorkflowId || elements.clockAction.disabled) return;
  const workflowRoot = activeWorkflowTarget === "agentcore"
    ? "/api/agentcore/workflows"
    : "/api/workflows";
  setBusy(elements.clockAction, true);
  try {
    const envelope = await request(`${workflowRoot}/${encodeURIComponent(activeWorkflowId)}/checks/next`, {
      method: "POST",
      headers: { "Idempotency-Key": crypto.randomUUID().replaceAll("-", "_") },
      body: "{}",
    });
    campaign = workflowCampaign(envelope, activeWorkflowTarget);
    render(campaign);
    if (campaign.workflow_status === "interrupted") {
      document.querySelector(".judgment input")?.focus();
      showToast("Mettle reached T−2 and needs one deadline tradeoff decision.");
    } else {
      showToast(`Scheduled check complete. ${campaign.metrics.citations_ready}/${campaign.metrics.citations_total} citations are closed.`);
    }
  } catch (error) {
    showError(error);
  } finally {
    if (campaign?.workflow_status !== "interrupted") setBusy(elements.clockAction, false);
  }
});

elements.packetAction.addEventListener("click", async () => {
  if (!activeWorkflowId) {
    if (campaign?.packet_status === "approved") {
      window.location.assign("/api/demo/packet.pdf");
    }
    return;
  }
  const workflowRoot = activeWorkflowTarget === "agentcore"
    ? "/api/agentcore/workflows"
    : "/api/workflows";
  if (campaign?.packet_status === "approved") {
    if (activeWorkflowTarget === "agentcore") {
      const link = await request(`${workflowRoot}/${encodeURIComponent(activeWorkflowId)}/packet-url`);
      window.location.assign(link.download_url);
    } else {
      window.location.assign(`${workflowRoot}/${encodeURIComponent(activeWorkflowId)}/packet.pdf`);
    }
    return;
  }
  setBusy(elements.packetAction, true);
  try {
    const envelope = await request(`${workflowRoot}/${encodeURIComponent(activeWorkflowId)}/packet/prepare`, {
      method: "POST",
      headers: { "Idempotency-Key": crypto.randomUUID().replaceAll("-", "_") },
      body: "{}",
    });
    campaign = workflowCampaign(envelope, activeWorkflowTarget);
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
  if (elements.noticeDialog.open && event.key === "Escape") {
    event.preventDefault();
    exitRecoverySetup();
    return;
  }
  if (event.target instanceof HTMLInputElement || event.target instanceof HTMLTextAreaElement || elements.noticeDialog.open) return;
  if (event.key === "ArrowRight" && !elements.advance.disabled) elements.advance.click();
  if (event.key.toLowerCase() === "r") elements.reset.click();
});

elements.retry.addEventListener("click", loadCampaign);
elements.auth.addEventListener("click", async () => {
  if (accessToken) {
    clearAuth();
    showToast("Signed out. The deterministic demo remains available.");
  } else {
    await beginLogin();
  }
});
initializeAuth().then(async () => {
  await loadCapabilities();
  await loadCampaign();
});
