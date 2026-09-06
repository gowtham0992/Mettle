const {
  evidenceOptionLabel,
  normalizedPhone,
  recoveryDateError,
  selectEvidenceCitation,
} = globalThis.MettleEvidenceFlow;

const elements = {
  main: document.querySelector("#main"),
  band: document.querySelector(".command-band"),
  campaignStrip: document.querySelector(".campaign-strip"),
  loading: document.querySelector("#loading-state"),
  dashboard: document.querySelector("#dashboard"),
  workspaceNav: document.querySelector("#workspace-nav"),
  workspaceTabs: [...document.querySelectorAll("[data-workspace-tab]")],
  workspacePanels: [...document.querySelectorAll("[data-workspace-panel]")],
  workspaceAgentState: document.querySelector("#workspace-agent-state"),
  workspaceAgentTitle: document.querySelector("#workspace-agent-title"),
  workspaceAgentCopy: document.querySelector("#workspace-agent-copy"),
  judgeTour: document.querySelector("#judge-tour"),
  tourStops: [...document.querySelectorAll("[data-tour-stop]")],
  tourProgressLabel: document.querySelector("#tour-progress-label"),
  tourEyebrow: document.querySelector("#tour-eyebrow"),
  tourTitle: document.querySelector("#tour-title"),
  tourCopy: document.querySelector("#tour-copy"),
  tourVisual: document.querySelector("#tour-visual"),
  tourControlTitle: document.querySelector("#tour-control-title"),
  tourControlCopy: document.querySelector("#tour-control-copy"),
  judgeLensImpact: document.querySelector("#judge-lens-impact"),
  judgeLensAgent: document.querySelector("#judge-lens-agent"),
  judgeLensHuman: document.querySelector("#judge-lens-human"),
  tourAction: document.querySelector("#tour-action"),
  tourSecondary: document.querySelector("#tour-secondary"),
  tourSkip: document.querySelector("#tour-skip"),
  tourActionNote: document.querySelector("#tour-action-note"),
  tourExit: document.querySelector("#tour-exit"),
  tourMetrics: document.querySelector("#tour-metrics"),
  tourOutcomeCopy: document.querySelector("#tour-outcome-copy"),
  demoDriver: document.querySelector(".demo-driver"),
  nextAction: document.querySelector("#next-action"),
  workflowJourney: document.querySelector("#workflow-journey"),
  journeyCurrent: document.querySelector("#journey-current"),
  journeyStages: [...document.querySelectorAll("[data-journey-stage]")],
  nextActionEyebrow: document.querySelector("#next-action-eyebrow"),
  nextActionTitle: document.querySelector("#next-action-title"),
  nextActionCopy: document.querySelector("#next-action-copy"),
  nextActionButton: document.querySelector("#next-action-button"),
  nextActionMeta: document.querySelector("#next-action-meta"),
  awayBriefing: document.querySelector("#away-briefing"),
  awayBriefingMode: document.querySelector("#away-briefing-mode"),
  awayBriefingTitle: document.querySelector("#away-briefing-title"),
  awayBriefingCopy: document.querySelector("#away-briefing-copy"),
  awayBriefingList: document.querySelector("#away-briefing-list"),
  awayBriefingActions: document.querySelector("#away-briefing-actions"),
  error: document.querySelector("#error-banner"),
  errorTitle: document.querySelector("#error-title"),
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
  correctionSummary: document.querySelector("#correction-summary"),
  citations: document.querySelector("#citation-list"),
  events: document.querySelector("#event-list"),
  agentRunMode: document.querySelector("#agent-run-mode"),
  agentRunSummary: document.querySelector("#agent-run-summary"),
  agentRunDetail: document.querySelector("#agent-run-detail"),
  agentRunTopology: document.querySelector("#agent-run-topology"),
  agentRunHooks: document.querySelector("#agent-run-hooks"),
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
  photoModeNote: document.querySelector("#photo-mode-note"),
  photoError: document.querySelector("#photo-error"),
  recordForm: document.querySelector("#record-evidence-form"),
  recordTitle: document.querySelector("#record-title"),
  recordGuidance: document.querySelector("#record-guidance"),
  recordRequirements: document.querySelector("#record-requirements"),
  recordReference: document.querySelector("#record-reference"),
  recordReviewer: document.querySelector("#record-reviewer"),
  recordDate: document.querySelector("#record-date"),
  recordDetails: document.querySelector("#record-details"),
  recordConfirmed: document.querySelector("#record-confirmed"),
  recordConfirmation: document.querySelector("#record-confirmation"),
  recordSubmit: document.querySelector("#record-submit"),
  recordError: document.querySelector("#record-error"),
  metrics: document.querySelector("#metrics-list"),
  packet: document.querySelector("#packet-status"),
  packetReadiness: document.querySelector("#packet-readiness"),
  packetList: document.querySelector("#packet-list"),
  packetPreview: document.querySelector("#packet-preview"),
  packetJudgment: document.querySelector("#packet-judgment"),
  packetNote: document.querySelector("#packet-note"),
  packetAction: document.querySelector("#packet-action"),
  agentFlow: document.querySelector("#agent-flow"),
  provenanceSteps: document.querySelector("#provenance-steps"),
  awsSchedulerProof: document.querySelector("#aws-scheduler-proof"),
  demoStep: document.querySelector("#demo-step"),
  driverTag: document.querySelector("#driver-tag"),
  advance: document.querySelector("#advance-button"),
  reset: document.querySelector("#reset-button"),
  loadNotice: document.querySelector("#load-notice-button"),
  noticeDialog: document.querySelector("#notice-dialog"),
  noticeForm: document.querySelector("#notice-form"),
  noticeText: document.querySelector("#notice-text"),
  noticeFile: document.querySelector("#notice-file"),
  noticeOcr: document.querySelector("#notice-ocr"),
  noticeOcrConfirm: document.querySelector("#notice-ocr-confirm"),
  noticeOcrReview: document.querySelector("#notice-ocr-review"),
  noticeFileStatus: document.querySelector("#notice-file-status"),
  workflowAsOf: document.querySelector("#workflow-as-of"),
  workflowDateError: document.querySelector("#workflow-date-error"),
  workflowError: document.querySelector("#workflow-form-error"),
  startWorkflow: document.querySelector("#start-workflow-button"),
  startBedrock: document.querySelector("#start-bedrock-button"),
  startAgentCore: document.querySelector("#start-agentcore-button"),
  closeNotice: document.querySelector("#close-notice-button"),
  retry: document.querySelector("#retry-button"),
  toast: document.querySelector("#toast"),
  themeToggle: document.querySelector("#theme-toggle"),
  themeToggles: [...document.querySelectorAll("#theme-toggle, [data-theme-toggle]")],
  auth: document.querySelector("#auth-button"),
  home: document.querySelector("#mettle-home"),
  welcomeDialog: document.querySelector("#welcome-dialog"),
  welcomeTitle: document.querySelector("#welcome-title"),
  startTourEntry: document.querySelector("#start-tour-entry"),
  startRecoveryEntry: document.querySelector("#start-recovery-entry"),
  recoveryEntryAction: document.querySelector("#recovery-entry-action"),
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
  outreachConsent: document.querySelector("#outreach-consent"),
  tradeContacts: document.querySelector("#trade-contacts"),
  agentReceiptButtons: [...document.querySelectorAll("[data-open-agent-receipt]")],
  navNewRecovery: document.querySelector("#nav-new-recovery"),
  navExitSample: document.querySelector("#nav-exit-sample"),
};

const themePreferenceKey = "mettle_theme";
const systemTheme = window.matchMedia("(prefers-color-scheme: light)");

function savedTheme() {
  const value = localStorage.getItem(themePreferenceKey);
  return value === "light" || value === "dark" ? value : null;
}

function resolveTheme() {
  return savedTheme() || (systemTheme.matches ? "light" : "dark");
}

function applyTheme(theme, { persist = false } = {}) {
  const nextTheme = theme === "light" ? "light" : "dark";
  document.documentElement.dataset.theme = nextTheme;
  document.querySelector('meta[name="theme-color"]')?.setAttribute(
    "content",
    nextTheme === "light" ? "#f1efe8" : "#191d20",
  );
  if (persist) localStorage.setItem(themePreferenceKey, nextTheme);
  const destination = nextTheme === "dark" ? "light" : "dark";
  for (const toggle of elements.themeToggles) {
    toggle.dataset.theme = nextTheme;
    toggle.setAttribute("aria-label", `Switch to ${destination} mode`);
    toggle.title = `Switch to ${destination} mode`;
    toggle.querySelector(".theme-toggle__icon").textContent = destination === "light" ? "☼" : "☾";
    toggle.querySelector(".theme-toggle__label").textContent = destination === "light" ? "Light" : "Dark";
  }
}

applyTheme(resolveTheme());

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
let noticeImportVersion = 0;
let activeWorkflowTarget = "local";
let toastTimer = null;
let bedrockEnabled = false;
let agentCoreEnabled = false;
let workflowCreateKey = null;
let workflowCreateProvider = null;
let demoRunning = false;
let authConfig = null;
let accessToken = sessionStorage.getItem("mettle_access_token");
const postAuthPathKey = "mettle_post_auth_path";
const recoveryDraftKey = "mettle_recovery_draft";
let setupStep = 1;
let setupReturnsToWelcome = false;
let recoveryDraftRestored = false;
let pendingCorrectionReview = null;
let correctionReviewKey = null;
let nextActionHandler = null;
const judgmentDrafts = new Map();
let tourActionHandler = null;
let tourSecondaryHandler = null;
let animationSkipRequested = false;
let finishTourDelay = null;
let tourClockOverride = null;
let retryHandler = () => loadCampaign();
const workspaceViews = new Set(["recovery", "correction", "evidence", "activity"]);
let activeWorkspaceView = workspaceViewFromUrl();
let judgeTourActive = new URLSearchParams(window.location.search).get("tour") === "1"
  || sessionStorage.getItem("mettle_entry_selected") === "tour";

function currentLocalDate() {
  const now = new Date();
  return new Date(now.getTime() - now.getTimezoneOffset() * 60_000).toISOString().slice(0, 10);
}

function recoveryWorkingDate() {
  return elements.workflowAsOf.value || currentLocalDate();
}

if (!elements.workflowAsOf.value) {
  const localToday = currentLocalDate();
  elements.workflowAsOf.value = localToday;
  const relativeDate = (offset) => {
    const value = new Date(`${localToday}T12:00:00`);
    value.setDate(value.getDate() + offset);
    return `${String(value.getMonth() + 1).padStart(2, "0")}/${String(value.getDate()).padStart(2, "0")}/${value.getFullYear()}`;
  };
  elements.noticeText.value = elements.noticeText.value
    .replace(/Inspection date: \d{1,2}\/\d{1,2}\/\d{4}/, `Inspection date: ${relativeDate(-3)}`)
    .replace(/reinspection on \d{1,2}\/\d{1,2}\/\d{4}/, `reinspection on ${relativeDate(7)}`);
}

function workspaceViewFromUrl() {
  const requested = new URLSearchParams(window.location.search).get("view");
  return ["recovery", "correction", "evidence", "activity"].includes(requested) ? requested : "recovery";
}

function setWorkspaceView(view, { updateUrl = false, focusTab = false } = {}) {
  const nextView = workspaceViews.has(view) ? view : "recovery";
  activeWorkspaceView = nextView;
  elements.main.dataset.workspaceView = nextView;
  elements.dashboard.classList.toggle("dashboard--focused", nextView !== "recovery");
  for (const panel of elements.workspacePanels) {
    panel.classList.toggle("workspace-panel--view-hidden", panel.dataset.workspacePanel !== nextView);
  }
  for (const tab of elements.workspaceTabs) {
    const active = tab.dataset.workspaceTab === nextView;
    if (active) tab.setAttribute("aria-current", "page");
    else tab.removeAttribute("aria-current");
    if (active && focusTab) tab.focus();
  }
  if (elements.nextAction.dataset.actionVisible) {
    elements.nextAction.hidden = elements.nextAction.dataset.actionVisible !== "true"
      || nextView !== "recovery";
  }
  if (updateUrl) {
    const url = new URL(window.location.href);
    if (nextView === "recovery") url.searchParams.delete("view");
    else url.searchParams.set("view", nextView);
    window.history.pushState({}, "", `${url.pathname}${url.search}${url.hash}`);
  }
  if (campaign && (updateUrl || focusTab)) renderWorkbench(campaign);
}

function openWorkspacePanel(view, targetSelector, focusSelector = null) {
  if (targetSelector === "#evidence-panel" || targetSelector === ".citation--needs-action") {
    const pending = targetSelector === ".citation--needs-action"
      ? campaign?.judgments.find(j => j.status === "pending" && j.citation_id) : null;
    openCorrection(pending?.citation_id || elements.photoCitation.value);
    window.setTimeout(() => document.querySelector(focusSelector?.replace(".citation--needs-action", "#correction-decision"))?.focus(), 0);
    return;
  }
  setWorkspaceView(view, { updateUrl: true });
  window.setTimeout(() => {
    const target = document.querySelector(targetSelector);
    target?.scrollIntoView({ behavior: "smooth", block: "start" });
    if (focusSelector) document.querySelector(focusSelector)?.focus();
  }, 0);
}

function openCorrection(citationId) {
  if (!campaign) return;
  const citation = globalThis.MettleWorkbench.selectedCitation(campaign, citationId);
  if (!citation) return;
  const changed = elements.photoCitation.value !== String(citation.citation_id);
  if (changed) {
    elements.photoFile.value = "";
    elements.photoError.hidden = true;
    elements.evidenceResult.hidden = true;
  }
  elements.photoCitation.value = String(citation.citation_id);
  const url = new URL(window.location.href);
  url.searchParams.set("view", "correction");
  url.searchParams.set("correction", citation.citation_id);
  window.history.pushState({}, "", `${url.pathname}${url.search}${url.hash}`);
  setWorkspaceView("correction");
  renderWorkbench(campaign);
  document.getElementById("correction-title").focus();
  window.scrollTo({top:0,behavior:"auto"});
}

function renderWorkbench(data) {
  globalThis.MettleWorkbench.render(data, {node, openCorrection, renderJudgment, renderEvidenceRoute, renderEvidencePhoto, setWorkspaceView, elements});
}

const evidencePhotoRequests = new Map();
function renderEvidencePhoto(host, assessment, decisionHost) {
  host.replaceChildren();
  host.hidden = !assessment || Boolean(assessment.contractor_record);
  if (host.hidden) return;
  const accept = [...decisionHost.querySelectorAll('button')].find(b => b.textContent === 'Accept proof');
  if (accept) accept.disabled = true;
  host.append(node('p', 'mono-label', 'Submitted photo · review against the notice'));
  const status = node('p', '', 'Loading your stored photo…');
  host.append(status);
  const workflowId = activeWorkflowId;
  const root = activeWorkflowTarget === 'agentcore' ? '/api/agentcore/workflows' : '/api/workflows';
  const key = `${root}/${encodeURIComponent(workflowId)}/evidence/${encodeURIComponent(assessment.assessment_id)}/photo`;
  async function load() {
    status.textContent = 'Loading your stored photo…';
    try {
      let src;
      if (!workflowId && /^\/static\/evidence\/[a-z0-9-]+\.png$/.test(assessment.image_url || '')) {
        src = assessment.image_url;
      } else {
        if (!evidencePhotoRequests.has(key)) {
          if (evidencePhotoRequests.size >= 4) evidencePhotoRequests.delete(evidencePhotoRequests.keys().next().value);
          evidencePhotoRequests.set(key, request(key).catch(error => { evidencePhotoRequests.delete(key); throw error; }));
        }
        const result = await evidencePhotoRequests.get(key);
        if (!/^\/9j\/[A-Za-z0-9+/=\r\n]+$/.test(result.image_base64 || '') || result.image_base64.length > 6700000) throw new Error('Stored photo could not be displayed.');
        src = `data:image/jpeg;base64,${result.image_base64}`;
      }
      if (!status.isConnected) return;
      const img = node('img', 'stored-evidence-photo');
      img.alt = `Submitted evidence for correction ${assessment.citation_id}`;
      img.onload = () => { status.textContent = 'Inspect the photo and every required item before accepting. Evidence is not code certification.'; if (accept?.isConnected) accept.disabled = false; };
      img.onerror = () => { status.textContent = 'Photo could not be displayed. Reload this page to try again; do not approve unseen proof.'; };
      img.src = src;
      host.append(img);
    } catch (error) {
      if (!status.isConnected) return;
      status.textContent = error.message || 'Photo could not be loaded.';
      const retry = node('button', 'button button--outline', 'Retry photo'); retry.type = 'button';
      retry.onclick = () => { retry.remove(); load(); }; host.append(retry);
    }
  }
  load();
}

function setTourIsolation(active) {
  elements.demoDriver.hidden = active;
  if (campaign) {
    elements.workspaceNav.hidden = false;
    elements.dashboard.hidden = false;
    renderBackgroundBrief(campaign);
  }
}

function setJudgeTourActive(active, { updateUrl = false, focus = true } = {}) {
  judgeTourActive = Boolean(active);
  document.body.classList.toggle("tour-mode", judgeTourActive);
  elements.judgeTour.hidden = !judgeTourActive;
  setTourIsolation(judgeTourActive);
  if (judgeTourActive) setWorkspaceView("recovery");
  if (updateUrl) {
    const url = new URL(window.location.href);
    if (judgeTourActive) {
      url.searchParams.set("tour", "1");
      url.searchParams.delete("view");
      url.searchParams.delete("workflow");
      url.searchParams.delete("runtime");
    } else {
      url.searchParams.delete("tour");
    }
    window.history.replaceState({}, "", `${url.pathname}${url.search}${url.hash}`);
  }
  if (judgeTourActive && campaign) renderJudgeTour(campaign);
  if (focus) {
    window.setTimeout(() => {
      if (judgeTourActive) elements.tourTitle.focus();
      else elements.workspaceTabs.find((tab) => tab.dataset.workspaceTab === activeWorkspaceView)?.focus();
    }, 0);
  }
}

function base64Url(bytes) {
  return btoa(String.fromCharCode(...new Uint8Array(bytes)))
    .replaceAll("+", "-").replaceAll("/", "_").replaceAll("=", "");
}

function base64Standard(bytes) {
  const view = new Uint8Array(bytes);
  const chunks = [];
  const chunkSize = 32_768;
  for (let offset = 0; offset < view.length; offset += chunkSize) {
    chunks.push(String.fromCharCode(...view.subarray(offset, offset + chunkSize)));
  }
  return btoa(chunks.join(""));
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
  evidencePhotoRequests.clear();
  accessToken = null;
  sessionStorage.removeItem("mettle_access_token");
  updateAuthControl();
}

function updateAuthControl() {
  if (!authConfig?.cognito_domain || !authConfig?.cognito_client_id) {
    elements.auth.hidden = true;
    document.body.classList.remove("is-authenticated");
    return;
  }
  if (accessToken && !tokenIsCurrent(accessToken)) {
    clearAuth();
    return;
  }
  elements.auth.hidden = false;
  document.body.classList.toggle("is-authenticated", Boolean(accessToken));
  elements.auth.textContent = accessToken ? "Sign out" : "Sign in";
  elements.auth.title = accessToken
    ? "Signed in · live AgentCore recoveries use this same workspace"
    : "Sign in to unlock the authenticated AgentCore recovery path";
  if (elements.recoveryEntryAction) {
    elements.recoveryEntryAction.textContent = accessToken ? "START →" : "START · SIGN IN LATER →";
  }
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
  sessionStorage.setItem("mettle_post_auth_path", `${window.location.pathname}${window.location.search}${window.location.hash}`);
  if (elements.noticeDialog.open) saveRecoveryDraft();
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

function saveRecoveryDraft() {
  const contacts = {};
  for (const nameInput of elements.contactNames) {
    const trade = nameInput.dataset.contactName;
    contacts[trade] = {
      name: nameInput.value,
      phone: elements.contactPhones.find((item) => item.dataset.contactPhone === trade)?.value || "",
    };
  }
  sessionStorage.setItem("mettle_recovery_draft", JSON.stringify({
    notice_text: elements.noticeText.value,
    as_of: recoveryWorkingDate(),
    primary_name: elements.primaryContactName.value,
    primary_phone: elements.primaryContactPhone.value,
    contacts,
    setup_step: setupStep,
  }));
}

function restoreRecoveryDraft() {
  const encoded = sessionStorage.getItem(recoveryDraftKey);
  if (!encoded) return false;
  sessionStorage.removeItem("mettle_recovery_draft");
  try {
    const draft = JSON.parse(encoded);
    if (!draft || typeof draft !== "object") return false;
    if (typeof draft.notice_text === "string") elements.noticeText.value = draft.notice_text.slice(0, 100000);
    if (typeof draft.as_of === "string") elements.workflowAsOf.value = draft.as_of;
    if (typeof draft.primary_name === "string") elements.primaryContactName.value = draft.primary_name.slice(0, 120);
    if (typeof draft.primary_phone === "string") elements.primaryContactPhone.value = draft.primary_phone.slice(0, 32);
    for (const nameInput of elements.contactNames) {
      const saved = draft.contacts?.[nameInput.dataset.contactName];
      if (!saved || typeof saved !== "object") continue;
      if (typeof saved.name === "string") nameInput.value = saved.name.slice(0, 120);
      const phoneInput = elements.contactPhones.find((item) => item.dataset.contactPhone === nameInput.dataset.contactName);
      if (phoneInput && typeof saved.phone === "string") phoneInput.value = saved.phone.slice(0, 32);
    }
    elements.tradeContacts.open = elements.contactNames.some((input) => input.value.trim());
    setSetupStep(Number.isInteger(draft.setup_step) ? draft.setup_step : 3);
    return true;
  } catch (_error) {
    return false;
  }
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
  const requestedPath = sessionStorage.getItem(postAuthPathKey);
  sessionStorage.removeItem("mettle_post_auth_path");
  let returnPath = window.location.pathname;
  if (requestedPath) {
    try {
      const target = new URL(requestedPath, window.location.origin);
      if (target.origin === window.location.origin && target.pathname.startsWith("/")) {
        returnPath = `${target.pathname}${target.search}${target.hash}`;
      }
    } catch (_error) {
      // Invalid saved destinations fail closed to the same-origin root callback.
    }
  }
  window.history.replaceState({}, "", returnPath);
  recoveryDraftRestored = restoreRecoveryDraft();
}

async function initializeAuth() {
  try {
    const response = await fetch("/api/config", { headers: { Accept: "application/json" } });
    authConfig = response.ok ? await response.json() : null;
    document.querySelector("#notice-ocr-option").hidden = !authConfig?.notice_ocr;
    if (authConfig?.notice_ocr) document.querySelector("#notice-photo-help").textContent = "For a photo or single-page scan, enable AWS OCR above, choose the file, then check the extracted text before continuing.";
    await finishLogin();
    document.querySelector("#notice-ocr-signin").hidden = !authConfig?.notice_ocr || tokenIsCurrent(accessToken);
    elements.noticeOcr.disabled = !tokenIsCurrent(accessToken);
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

function formatTimestamp(value) {
  return new Intl.DateTimeFormat("en-US", {
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
    timeZoneName: "short",
  }).format(new Date(value));
}

function maskedPhone(value) {
  const digits = String(value || "").replace(/\D/g, "");
  return digits.length >= 4 ? `••• ••• ${digits.slice(-4)}` : "private number";
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
  const automation = envelope.automation || null;
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
      : assessment?.status === "rejected"
        ? "evidence_rejected"
        : assessment?.status === "manual_review" ? "needs_judgment" : null;
    return {
      ...citation,
      code_reference: citation.code_reference?.toLowerCase() === "unknown" ? "No code reference supplied" : citation.code_reference,
      assignee: delivery ? `${delivery.recipient.name} · ${maskedPhone(delivery.recipient.phone)}` : null,
      evidence_note: assessment?.explanation || (needsJudgment
        ? "Mettle needs an evidence-spec decision before outreach"
        : delivery?.message_id.endsWith("-decision")
          ? "Contractor-directed request recorded"
          : delivery?.status === "sent" ? "One-way SMS accepted by Amazon SNS"
            : delivery ? "Request recorded without carrier delivery" : "No outreach until contractor review"),
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
      const sent = delivery.status === "sent";
      return {
        happened_at: `${delivery.scheduled_on}T08:${String(16 + index).padStart(2, "0")}:00Z`,
        kind: followUp ? "deadline_escalation" : sent ? "message_sent" : "message_recorded",
        actor: followUp ? "Mettle · chase graph" : "Mettle · coordinator",
        title: followUp
          ? `Autonomously followed up C${delivery.citation_id} with ${delivery.recipient.name}`
          : `${sent ? "Sent" : "Recorded"} ${contractorDirected ? "contractor-directed " : ""}C${delivery.citation_id} request for ${delivery.recipient.name}`,
        detail: sent
          ? "Amazon SNS accepted this transactional, one-way SMS. Replies are intentionally outside the demo scope."
          : followUp
            ? `${plan.priority.toUpperCase()} cadence at ${daysBetween(delivery.scheduled_on, notice.reinspection_due_on)} day(s) to reinspection; carrier delivery was not enabled for this destination.`
            : "The safe recording adapter preserved the action without contacting this destination.",
      };
    }),
  ];
  if (automation) {
    events.push({
      happened_at: automation.next_check_at || timestamp(8, 22),
      kind: `automation_${automation.status}`,
      actor: "Mettle · EventBridge Scheduler",
      title: automation.status === "scheduled"
        ? `Armed autonomous T−${daysBetween(automation.logical_check_on, notice.reinspection_due_on)} checkpoint`
        : automation.status === "awaiting_decision"
          ? "Automation paused at a contractor judgment gate"
          : "Autonomous campaign stood down",
      detail: automation.status === "scheduled"
        ? `${automation.accelerated_demo_clock ? "Accelerated demo clock" : "Production campaign clock"} · next execution ${formatTimestamp(automation.next_check_at)}.`
        : automation.status === "awaiting_decision"
          ? "No background outreach will continue until the contractor resolves the judgment."
          : "No future EventBridge checkpoint remains for this campaign.",
    });
  }
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
    const sourceRecord = assessment.contractor_record;
    const contractorResolved = Boolean(assessment.contractor_decision || sourceRecord);
    events.push({
      happened_at: timestamp(9, index),
      kind: contractorResolved ? "judgment_resolved" : `evidence_${assessment.status}`,
      actor: contractorResolved ? "Contractor" : "Mettle · evidence assessor",
      title: sourceRecord ? `Contractor recorded C${assessment.citation_id} ${sourceRecord.route === "physical_reinspection" ? "inspection outcome" : "document review"}` : contractorResolved
        ? `${assessment.status === "accepted" ? "Accepted" : "Returned"} ambiguous C${assessment.citation_id} photo after contractor review`
        : `${assessment.status === "accepted" ? "Accepted" : assessment.status === "rejected" ? "Rejected" : "Held"} C${assessment.citation_id} photo evidence`,
      detail: sourceRecord ? `Source: ${sourceRecord.reference}. ${assessment.explanation}` : contractorResolved ? assessment.contractor_decision : assessment.explanation,
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
  for (const assessment of evidenceByCitation.values()) {
    if (assessment.status !== "manual_review") continue;
    judgments.push({
      judgment_id: assessment.assessment_id,
      kind: "evidence_review",
      citation_id: assessment.citation_id,
      question: "Is this ambiguous photo sufficient for the correction record?",
      reason: `${assessment.explanation} Accept it as visible evidence or request a clearer replacement.`,
      status: "pending",
      evidence_review: true,
    });
  }
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
      actor: assessment.contractor_record || step.step === "Contractor resolution" ? "Contractor" : "Evidence agent",
      status: step.status,
      detail: `C${assessment.citation_id} · ${step.detail}`,
    })),
  );
  return {
    source_mode: "workflow",
    recovery_hold: envelope.recovery_hold === true,
    execution_target: executionTarget,
    intake_provider: envelope.intake_provider || "local",
    workflow_status: snapshot.status,
    automation_status: envelope.recovery_hold ? "held" : automation?.status || null,
    next_check_at: envelope.recovery_hold ? null : automation?.next_check_at || null,
    accelerated_demo_clock: automation?.accelerated_demo_clock === true,
    correction_review_required: correctionReviewRequired,
    correction_review_interrupt: correctionReviewRequired ? pendingInterrupt.interrupt_id : null,
    review_citations: correctionReviewRequired ? pendingInterrupt.reason.citations : [],
    review_recipients: correctionReviewRequired ? pendingInterrupt.reason.recipients || [] : [],
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
        + (envelope.packet?.status === "approved" ? 1 : 0)
        + (envelope.evidence || []).filter((item) => item.contractor_decision || item.contractor_record).length,
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
      const error = new Error("Sign in to resume your recovery.");
      error.code = "sign_in_required";
      throw error;
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
  if (response.status === 401 && path.startsWith("/api/agentcore")) {
    clearAuth();
    const error = new Error("Your session has expired. Sign in to resume your recovery.");
    error.code = "sign_in_required";
    throw error;
  }
  const contentType = response.headers.get("content-type") || "";
  if (!contentType.toLowerCase().includes("application/json")) {
    const requestError = new Error(
      response.ok
        ? "Mettle returned an unexpected response. Please retry."
        : `The request was blocked before it reached Mettle (HTTP ${response.status}). Please retry.`,
    );
    const code = "edge_request_failed";
    requestError.code = code;
    requestError.status = response.status;
    throw requestError;
  }
  const payload = await response.json();
  if (!response.ok) {
    const requestError = new Error(payload.error?.message || "The campaign request failed.");
    requestError.code = payload.error?.code || "campaign_request_failed";
    requestError.status = response.status;
    throw requestError;
  }
  return payload;
}

function startFreshRecoveryFromError() {
  activeWorkflowId = null;
  activeWorkflowTarget = "local";
  const url = new URL(window.location.href);
  url.searchParams.delete("workflow");
  url.searchParams.delete("runtime");
  url.searchParams.delete("view");
  window.history.replaceState({}, "", `${url.pathname}${url.search}${url.hash}`);
  elements.error.hidden = true;
  openRecoverySetup();
}

function showError(error) {
  elements.loading.hidden = true;
  elements.error.hidden = false;
  if (error.code === "sign_in_required") {
    elements.errorTitle.textContent = "Sign in to resume your recovery";
    elements.errorMessage.textContent = "Your session has ended. Sign in with the same account to reopen this recovery. This page has not started a replacement or sent any messages.";
    elements.property.textContent = "Recovery awaiting sign-in";
    elements.conditionLabel.textContent = "SIGN-IN REQUIRED";
    elements.progressLabel.textContent = "SIGN IN TO LOAD PROGRESS";
    elements.cadence.textContent = "SESSION ENDED · RECOVERY LINK PRESERVED";
    elements.demoDriver.hidden = true;
    elements.retry.textContent = "Sign in to resume";
    retryHandler = () => beginLogin().catch(showError);
    return;
  }
  if (error.code === "workflow_not_found" && activeWorkflowTarget === "agentcore") {
    elements.errorTitle.textContent = "Recovery unavailable";
    elements.errorMessage.textContent = "This recovery could not be loaded. Older runs may not have a restorable checkpoint. Keep your report and contact the operator before starting again, so outreach is not duplicated.";
    elements.retry.textContent = "Start a new recovery";
    retryHandler = startFreshRecoveryFromError;
    return;
  }
  elements.errorTitle.textContent = "Campaign connection interrupted";
  elements.errorMessage.textContent = error.message || "The local API did not respond.";
  elements.retry.textContent = "Retry";
  retryHandler = () => loadCampaign();
}

function showInlineWorkflowError(error, element) {
  if (error.code === "workflow_not_found" && activeWorkflowTarget === "agentcore") {
    if (elements.noticeDialog.open) elements.noticeDialog.close();
    showError(error);
    elements.error.scrollIntoView({ behavior: "smooth", block: "start" });
    return;
  }
  element.textContent = error.message;
  element.hidden = false;
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
  if (!button.busyStatus && busy) {
    button.busyStatus = node("p", "photo-evidence__mode", "Working on this step… Your request is in progress; please don’t submit again.");
    button.busyStatus.setAttribute("role", "status");
    button.after(button.busyStatus);
  }
  if (button.busyStatus) button.busyStatus.hidden = !busy;
}

function activePhotoEnabled() {
  return Boolean(activeWorkflowId)
    && (activeWorkflowTarget === "agentcore" ? agentCoreEnabled : bedrockEnabled);
}

function hasApprovedEvidenceBoundary(data, citationId) {
  const citation = data.citations.find(
    (item) => String(item.citation_id) === String(citationId),
  );
  return Boolean(
    citation
    && citation.stage !== "needs_judgment"
    && Array.isArray(citation.evidence_requirements)
    && citation.evidence_requirements.length,
  );
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
  elements.startWorkflow.hidden = setupStep !== 3 || agentCoreEnabled;
  elements.startBedrock.hidden = true;
  elements.startAgentCore.hidden = setupStep !== 3 || !agentCoreEnabled;
  elements.approveCorrections.hidden = setupStep !== 4;
  elements.setupFooterNote.textContent = setupStep === 1
    ? "REPORT FIRST · NO PROJECT SETUP"
    : setupStep === 2 ? "ADD ONLY THE PEOPLE NEEDED FOR THIS JOB"
      : setupStep === 3 ? "NOTHING SENDS BEFORE YOUR REVIEW" : "YOU APPROVE · METTLE FOLLOWS UP";
  elements.setupNext.textContent = setupStep === 1 ? "Next · add contacts" : "Next · check setup";
  const heading = setupStep === 1
    ? "Start with the failed-inspection report"
    : setupStep === 2 ? "Who should Mettle contact?"
      : setupStep === 3 ? "Ready to build the recovery" : "Review every correction before outreach";
  document.querySelector("#notice-dialog-title").textContent = heading;
}

function validateSetupStep() {
  elements.workflowError.hidden = true;
  elements.workflowDateError.hidden = true;
  if (setupStep === 1) {
    if (!elements.noticeOcrReview.hidden && !elements.noticeOcrConfirm.checked) {
      elements.workflowError.textContent = "Check the extracted text against your original report, then confirm it above.";
      elements.workflowError.hidden = false;
      elements.noticeOcrConfirm.focus();
      return false;
    }
    if (!elements.noticeText.value.trim()) {
      elements.noticeText.setCustomValidity("Paste the failed-inspection report or comments.");
      elements.noticeText.reportValidity();
      elements.noticeText.setCustomValidity("");
      return false;
    }
    const dateError = recoveryDateError(
      elements.noticeText.value,
      recoveryWorkingDate(),
    );
    if (dateError) {
      elements.workflowDateError.textContent = `${dateError} Check the inspection and reinspection dates in the pasted report.`;
      elements.workflowDateError.hidden = false;
      elements.noticeText.setAttribute("aria-invalid", "true");
      elements.noticeText.focus();
      return false;
    }
    elements.noticeText.removeAttribute("aria-invalid");
    if (!completeNoticeDetails()) return false;
  }
  if (setupStep === 2) {
    const name = elements.primaryContactName.value.trim();
    const phone = normalizedPhone(elements.primaryContactPhone.value);
    if (!name) {
      elements.primaryContactName.reportValidity();
      return false;
    }
    if (!/^\+[1-9]\d{7,14}$/.test(phone)) {
      elements.primaryContactPhone.setCustomValidity("Enter a US phone number such as (303) 555-0100, or include the country code.");
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
        phoneInput.setCustomValidity("Enter a US phone number such as (303) 555-0101, or include the country code.");
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
    if (!elements.outreachConsent.checked) {
      elements.outreachConsent.setCustomValidity("Confirm that you are authorized to contact the people shown above.");
      elements.outreachConsent.reportValidity();
      elements.outreachConsent.setCustomValidity("");
      return false;
    }
  }
  return true;
}

function completeNoticeDetails() {
  const host = document.getElementById("notice-missing-details");
  const text = elements.noticeText.value;
  const fields = [
    ["permit", "Permit or notice number", "Permit", /^(?:permit|notice id|record id|correction notice)\b/im, "text"],
    ["address", "Job address or redacted job label", "Property", /^(?:property|project address|job address|address|location|site)\b/im, "text"],
    ["inspection", "When was the inspection?", "Inspection date", /^(?:inspection date|issued on|issued|date of inspection)\b/im, "date"],
    ["deadline", "What is the reinspection target date?", "Reinspection deadline", /(?:reinspection|re-inspection|correction deadline|correct by)/i, "date"],
  ].filter(field => !field[3].test(text));
  if (!fields.length) {host.hidden=true;host.replaceChildren();return true;}
  const additions=[];
  for (const [key,label,header,,type] of fields) {
    let input = document.getElementById(`notice-detail-${key}`);
    if (!input) {
      const wrapper=node("label","field"); wrapper.append(node("span","",label));
      input=node("input","");input.id=`notice-detail-${key}`;input.type=type;input.maxLength=180;input.required=true;
      wrapper.append(input);host.append(wrapper);
    }
    if (input.value.trim()) additions.push(`${header}: ${input.value.trim()}`);
  }
  host.hidden=false;
  if (!host.querySelector("p")) host.prepend(node("p","notice-dialog__intro","A few job details weren’t found in the report. Add them here; they will be marked as supplied by you, not by the inspector."));
  if (additions.length !== fields.length) {
    [...host.querySelectorAll("input")].find(input=>!input.value.trim())?.focus();
    return false;
  }
  const enriched=`Contractor-supplied setup details\n${additions.join("\n")}\n\nOriginal report\n${text}`;
  const error=recoveryDateError(enriched,recoveryWorkingDate());
  if (error) {elements.workflowDateError.textContent=error;elements.workflowDateError.hidden=false;return false;}
  elements.noticeText.value=enriched;
  host.replaceChildren();host.hidden=true;
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
  const cards = data.review_citations.map((citation) => {
    const card = node("article", "correction-review__card");
    card.dataset.reviewCitation = citation.citation_id;
    card.append(node("span", "correction-review__id", `C${citation.citation_id}`));
    card.append(node("span", "correction-review__code", `${!citation.code_reference || citation.code_reference.toLowerCase() === "unknown" ? "No code reference supplied" : citation.code_reference} · authority language`));
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

    const recipient = node("div", "correction-review__recipient");
    const updateRecipient = () => {
      const match = data.review_recipients?.find((contact) => contact.trade === tradeSelect.value);
      recipient.replaceChildren(
        node("span", "", "MESSAGE GOES TO"),
        node("strong", "", match ? `${match.name} · ••• ••• ${match.phone_suffix}` : "Saved recipient unavailable — do not assume who will be contacted."),
      );
    };
    tradeSelect.addEventListener("change", updateRecipient);
    updateRecipient();

    const routeLabel = node("label", "correction-review__route", "PROOF METHOD");
    const routeSelect = node("select");
    routeSelect.dataset.reviewRoute = "";
    routeSelect.setAttribute("aria-label", `Proof method for citation ${citation.citation_id}`);
    for (const [value, label] of Object.entries({photo_evidence: "Job-site photo", document_evidence: "Document evidence", physical_reinspection: "Physical reinspection"})) {
      const option = node("option", "", label);
      option.value = value;
      routeSelect.append(option);
    }
    routeSelect.value = citation.closure_route || "photo_evidence";
    routeLabel.append(routeSelect);
    routeLabel.append(node("small", "", "Keep the notice’s required method. A photo does not replace documents, an inspector visit, or code certification."));

    const proofLabel = node("label", "", "WHAT MUST COME BACK · ONE REQUIREMENT PER LINE");
    const proof = node("textarea");
    proof.dataset.reviewProof = "";
    proof.required = true;
    proof.maxLength = 5000;
    proof.placeholder = "Example: Wide photo showing the completed correction and its location";
    proof.setAttribute("aria-label", `Required proof for citation ${citation.citation_id}`);
    proof.value = (citation.evidence_requirements || []).join("\n");
    proofLabel.append(proof);
    fields.append(tradeLabel, recipient, routeLabel, proofLabel);
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
  elements.reviewNoticeSummary.textContent = `${reportLines} report lines · ${formatDate(recoveryWorkingDate())}`;
  elements.reviewContactSummary.textContent = `${elements.primaryContactName.value.trim()} + ${namedTrades} trade contact${namedTrades === 1 ? "" : "s"}`;
}

function openRecoverySetup({ returnToWelcome = false } = {}) {
  setupReturnsToWelcome = returnToWelcome;
  elements.workflowError.hidden = true;
  setSetupStep(1);
  elements.noticeDialog.showModal();
  window.setTimeout(() => elements.noticeText.focus(), 0);
}

function resetRecoverySetup() {
  noticeImportVersion += 1;
  elements.noticeForm.reset();
  elements.noticeOcrReview.hidden = true;
  document.getElementById("notice-missing-details").replaceChildren();
  document.getElementById("notice-missing-details").hidden = true;
  elements.workflowAsOf.value = currentLocalDate();
  elements.noticeText.value = "";
  elements.noticeFileStatus.textContent = "No file selected";
  elements.tradeContacts.open = false;
  elements.outreachConsent.checked = false;
  pendingCorrectionReview = null;
  workflowCreateKey = null;
  workflowCreateProvider = null;
}

function openWelcomeChooser() {
  if (!elements.welcomeDialog.open) elements.welcomeDialog.showModal();
  window.requestAnimationFrame(() => {
    elements.welcomeDialog.scrollTop = 0;
    elements.welcomeTitle.focus({ preventScroll: true });
    elements.welcomeDialog.scrollTop = 0;
  });
}

function exitRecoverySetup() {
  const returnToWelcome = setupReturnsToWelcome;
  setupReturnsToWelcome = false;
  elements.noticeDialog.close();
  if (returnToWelcome) {
    sessionStorage.removeItem("mettle_entry_selected");
    window.setTimeout(openWelcomeChooser, 0);
  }
}

function configureNextAction(data) {
  const isWorkflow = data.source_mode === "workflow";
  const pending = data.judgments.filter((item) => item.status === "pending");
  const openCitation = data.citations.find((item) => item.stage !== "ready");
  const actionView = pending[0]?.kind === "final_packet_approval"
    || (!openCitation && ["blocked", "awaiting_approval", "approved"].includes(data.packet_status))
    ? "evidence"
    : "recovery";
  elements.nextAction.dataset.actionView = actionView;
  elements.nextAction.dataset.actionVisible = "true";
  elements.nextAction.hidden = activeWorkspaceView !== "recovery";
  elements.nextAction.classList.toggle("next-action--sample", !isWorkflow);
  elements.nextActionEyebrow.textContent = pending.length ? "ACTION REQUIRED" : "NEXT STEP";
  elements.nextActionMeta.textContent = isWorkflow ? "ONE ACTION · CONTRACTOR CONTROLLED" : "SYNTHETIC DATA · 90 SECONDS";

  if (data.recovery_hold) {
    elements.nextAction.hidden = false;
    elements.nextActionTitle.textContent = "Recovery held to prevent duplicate messages";
    elements.nextActionCopy.textContent = "The last operation’s outcome could not be confirmed. Your last saved record remains available. Ask the operator to reconcile it before retrying or starting a replacement recovery.";
    elements.nextActionButton.textContent = "View saved activity";
    elements.nextActionMeta.textContent = "OPERATOR REVIEW REQUIRED · NO AUTOMATIC RETRY";
    nextActionHandler = () => setWorkspaceView("activity", { updateUrl: true });
    return;
  }

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
      elements.nextActionButton.textContent = pending[0].citation_id ? "Go to correction" : "Review decision";
      nextActionHandler = pending[0].citation_id
        ? () => openWorkspacePanel("recovery", ".citation--needs-action", ".citation--needs-action .judgment input")
        : () => openWorkspacePanel("recovery", "#judgment-list", "#judgment-list .judgment input");
    } else {
      elements.nextAction.dataset.actionVisible = "true";
      elements.nextAction.hidden = activeWorkspaceView !== "recovery";
      elements.nextActionTitle.textContent = "Mettle is handling the open work";
      elements.nextActionCopy.textContent = "Continue this recorded sample to see proof arrive, follow-ups change, and the next contractor decision appear. No live messages or model calls.";
      elements.nextActionButton.textContent = "Continue sample recovery";
      nextActionHandler = () => elements.advance.click();
    }
    return;
  }

  if (pending.length) {
    elements.nextActionTitle.textContent = pending[0].kind === "final_packet_approval" ? "Approve the final packet" : "Resolve the blocked decision";
    elements.nextActionCopy.textContent = pending[0].question;
    elements.nextActionButton.textContent = "Review decision";
    nextActionHandler = pending[0].kind === "final_packet_approval"
      ? () => openWorkspacePanel("evidence", "#packet-judgment", "#packet-judgment .judgment input")
      : pending[0].citation_id
        ? () => openWorkspacePanel("recovery", ".citation--needs-action", ".citation--needs-action .judgment input")
        : () => openWorkspacePanel("recovery", "#judgment-list", "#judgment-list .judgment input");
  } else if (openCitation) {
    const recordRoute = openCitation.closure_route && openCitation.closure_route !== "photo_evidence";
    const physical = openCitation.closure_route === "physical_reinspection";
    elements.nextActionTitle.textContent = `Collect proof for C${openCitation.citation_id}`;
    elements.nextActionCopy.textContent = recordRoute
      ? physical ? "Arrange the required inspector visit outside Mettle. After it is completed, record the source reference and outcome. A booking is not proof of completion."
        : "Review the required document, then record its reference and the details that address this correction. Keep the original for the inspector."
      : openCitation.stage === "evidence_rejected"
      ? "The last photo did not visibly show everything requested. Review the feedback and replace it."
      : "Choose the correction and add the job-site photo you expect to use for closure.";
    elements.nextActionButton.textContent = recordRoute ? physical ? "Record inspection outcome" : "Record document review" : activePhotoEnabled() ? "Add a photo" : "Review evidence status";
    nextActionHandler = () => {
      elements.photoCitation.value = openCitation.citation_id;
      openWorkspacePanel("evidence", "#evidence-panel", recordRoute ? "#record-reference" : "#photo-file");
    };
  } else if (data.packet_status === "blocked") {
    elements.nextActionTitle.textContent = "Assemble the review packet";
    elements.nextActionCopy.textContent = "Every citation has accepted evidence. Prepare the packet before giving final approval.";
    elements.nextActionButton.textContent = "Prepare packet";
    nextActionHandler = () => {
      setWorkspaceView("evidence", { updateUrl: true });
      elements.packetAction.click();
    };
  } else if (data.packet_status === "approved") {
    elements.nextActionTitle.textContent = "Download the approved packet";
    elements.nextActionCopy.textContent = "The notice, evidence, recovery history, and your approval are ready in one artifact.";
    elements.nextActionButton.textContent = "Download PDF";
    nextActionHandler = () => {
      setWorkspaceView("evidence", { updateUrl: true });
      elements.packetAction.click();
    };
  } else {
    elements.nextActionTitle.textContent = "Recovery is running in the background";
    elements.nextActionCopy.textContent = "Mettle will follow up on open corrections and return when your decision is needed.";
    elements.nextActionButton.textContent = "View activity";
    nextActionHandler = () => setWorkspaceView("activity", { updateUrl: true });
  }
}

function renderJourney(data) {
  const allReady = data.metrics.citations_total > 0
    && data.metrics.citations_ready === data.metrics.citations_total;
  const openCount = data.metrics.citations_total - data.metrics.citations_ready;
  let activeIndex = 2;
  let current = `${openCount} ${openCount === 1 ? "correction still needs" : "corrections still need"} proof`;
  if (data.correction_review_required) {
    activeIndex = 1;
    current = "Confirm assignments and proof before outreach";
  } else if (data.packet_status === "approved") {
    activeIndex = 4;
    current = "Approved packet ready for reinspection";
  } else if (data.packet_status === "awaiting_approval" || allReady) {
    activeIndex = 3;
    current = "Proof is complete · contractor approval is next";
  }
  elements.workflowJourney.hidden = false;
  elements.journeyCurrent.textContent = current;
  elements.journeyStages.forEach((stage, index) => {
    stage.classList.toggle("is-complete", index < activeIndex);
    stage.classList.toggle("is-current", index === activeIndex);
    if (index === activeIndex) stage.setAttribute("aria-current", "step");
    else stage.removeAttribute("aria-current");
  });
}

function conditionFor(data) {
  if (data.packet_status === "approved") return ["REINSPECTION READY", "ready"];
  if (data.packet_status === "awaiting_approval") return ["AWAITING APPROVAL", "approval"];
  if (data.priority === "critical") return ["CRITICAL", "critical"];
  return ["ON TRACK", "normal"];
}

const citationEvidenceImages = {
  ready: {
    "1": "/static/evidence/panel-wide-measured.png",
    "2": "/static/evidence/framing-plates-complete.png",
    "3": "/static/evidence/mechanical-access-wide.png",
  },
  evidence_rejected: {
    "1": "/static/evidence/panel-closeup-insufficient.png",
    "2": "/static/evidence/framing-closeup-insufficient.png",
  },
};

function correctionStatus(citation) {
  return {
    ready: ["PROOF ACCEPTED", "Proof is ready for packet assembly."],
    awaiting_evidence: ["AWAITING PROOF", "Mettle is waiting for the requested proof."],
    evidence_rejected: ["REPLACEMENT REQUESTED", "Mettle requested the one missing visible element."],
    needs_judgment: ["YOUR DECISION", "Mettle stopped instead of inventing a requirement."],
  }[citation.stage] || ["OPEN", "This correction remains open."];
}

function renderCorrectionSummary(data) {
  const total = data.citations.length;
  const ready = data.citations.filter((citation) => citation.stage === "ready").length;
  const chasing = data.citations.filter((citation) => ["awaiting_evidence", "evidence_rejected"].includes(citation.stage)).length;
  const needsYou = data.judgments.filter((judgment) => judgment.status === "pending" && judgment.kind !== "final_packet_approval").length;
  const preOutreach = data.correction_review_required || (data.metrics.messages_handled === 0 && pendingJudgment(data, "route-review"));
  elements.correctionSummary.replaceChildren(
    node("span", "", `${total} corrections`),
    node("strong", "summary-ready", `${ready} proof accepted`),
    node("span", "", preOutreach ? `${total} routes held` : `${chasing} awaiting proof`),
    node("strong", needsYou ? "summary-action" : "", `${needsYou} need you`),
  );
}

function renderCitation(citation, data) {
  const judgment = data.judgments.find(j => j.status === "pending" && String(j.citation_id || "") === String(citation.citation_id));
  const row = node("article", `citation citation--compact${judgment ? " citation--needs-action" : ""}`);
  row.id = `correction-${citation.citation_id}`;
  const button = node("button", "correction-row"); button.type = "button";
  button.append(node("span", "citation__number", `C${citation.citation_id}`));
  const identity = node("span", "correction-row__identity");
  identity.append(node("strong", "", titleCase(citation.trade)), node("span", "", citation.notice_text));
  const status = node("span", `status status--${citation.stage}`, correctionStatus(citation)[0]);
  button.append(identity, status, node("span", "correction-row__arrow", "→"));
  button.setAttribute("aria-label", `Open correction ${citation.citation_id}: ${citation.trade}`);
  button.addEventListener("click", () => openCorrection(citation.citation_id));
  row.append(button);
  return row;
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

const graphNodeDetails = {
  intake: ["Notice intake boundary", "Ground correction notice"],
  plan: ["Deterministic planner", "Derive bounded campaign plan"],
  review_gate: ["Contractor gate", "BeforeNodeCall · correction-review"],
  coordinate: ["Coordination policy", "Route notice-anchored outreach"],
  judgment_gate: ["Contractor gate", "BeforeNodeCall · contractor-judgment"],
  coordinate_decision: ["Coordination policy", "Resume with approved boundary"],
  finish: ["Deterministic orchestrator", "Checkpoint recovery graph"],
  replan_open: ["Deterministic planner", "Replan open citations only"],
  follow_up: ["Coordination policy", "Escalate unresolved trades"],
  deadline_gate: ["Contractor gate", "BeforeNodeCall · deadline-tradeoff"],
  finish_chase: ["Deterministic orchestrator", "Checkpoint deadline chase"],
  ground_requirements: ["Evidence agent", "Bind notice requirements"],
  inspect_visible_evidence: ["Evidence agent", "Inspect pixels with Bedrock"],
  apply_safety_policy: ["Evidence safety policy", "Deterministically route ambiguity to contractor"],
};

const recordedEvidenceAssessments = {
  panel_closeup_insufficient: {
    citation_id: "1",
    status: "rejected",
    label: "Recorded sample · rejected",
    explanation: "The panel is visible, but the full working area and a measurable clearance scale are not. Re-request a wider photo with the service area and tape measure in one frame.",
  },
  panel_wide_measured: {
    citation_id: "1",
    status: "accepted",
    label: "Recorded sample · accepted",
    explanation: "The wide view visibly includes the full panel area and measurement scale requested by the notice. This records evidence sufficiency, not code compliance.",
  },
  framing_plates_complete: {
    citation_id: "2",
    status: "accepted",
    label: "Recorded sample · accepted",
    explanation: "The submission visibly includes both the installed protection plates and the corrected wall location requested by the notice.",
  },
  mechanical_access_wide: {
    citation_id: "3",
    status: "manual_review",
    label: "Recorded sample · contractor review",
    explanation: "The photo shows the equipment and service area, but Mettle will not invent the clearance standard. A contractor-defined evidence boundary is required before acceptance.",
  },
};

function renderEvidenceAssessment(assessment) {
  elements.evidenceResult.dataset.mode = assessment.label?.startsWith("Recorded sample") ? "recorded" : "live";
  elements.evidenceResult.hidden = false;
  elements.evidenceResult.className = `evidence-result evidence-result--${assessment.status}`;
  const resultLabel = assessment.contractor_record ? "Contractor-reviewed record"
    : assessment.contractor_decision
    ? `${assessment.status === "accepted" ? "Accepted" : "Returned"} by contractor`
    : assessment.label || assessment.status.replaceAll("_", " ");
  elements.evidenceResult.replaceChildren(
    node("strong", "", `${resultLabel} · C${assessment.citation_id}`),
    node("span", "", assessment.explanation),
    ...(assessment.contractor_record ? [
      node("span", "", `Source: ${assessment.contractor_record.reference}`),
      node("span", "", `Reviewed by ${assessment.contractor_record.reviewer} · ${assessment.contractor_record.reviewed_on}`),
      node("span", "", assessment.contractor_record.details),
    ] : []),
    ...(assessment.contractor_decision
      ? [node("span", "evidence-result__decision", `Decision record: ${assessment.contractor_decision}`)]
      : []),
  );
}

function graphNodeDetail(step) {
  const known = graphNodeDetails[step.node_id];
  return {
    ...step,
    actor: step.actor || known?.[0] || "Mettle agent",
    detail: step.graph === "evidence" && step.detail
      ? step.detail
      : known?.[1] || step.detail || step.node_id.replaceAll("_", " "),
  };
}

function sampleAgentRun(data) {
  const pending = data.judgments.find((item) => item.status === "pending");
  const complete = data.scenario_complete === true;
  const coreNodes = ["intake", "plan", "review_gate", "coordinate", "judgment_gate", "coordinate_decision", "finish"];
  const chaseNodes = ["replan_open", "follow_up", "deadline_gate", "finish_chase"];
  const visibleNodes = Number(data.scenario_step || 0) >= 3 || complete
    ? [...coreNodes, ...chaseNodes]
    : coreNodes;
  return visibleNodes.map((nodeId, index) => {
    const graph = chaseNodes.includes(nodeId) ? "deadline_chase" : "recovery";
    let status = "completed";
    if (pending?.judgment_id === "route-review" && nodeId === "judgment_gate") status = "interrupted";
    if (pending?.judgment_id === "deadline-choice" && nodeId === "deadline_gate") status = "interrupted";
    return graphNodeDetail({ sequence: index + 1, graph, node_id: nodeId, status });
  });
}

function renderAgentRun(data) {
  const isWorkflow = data.source_mode === "workflow";
  const steps = (isWorkflow ? (data.agent_run || []) : sampleAgentRun(data)).map(graphNodeDetail);
  elements.agentRunMode.textContent = isWorkflow
    ? data.execution_target === "agentcore" ? "LIVE · AGENTCORE" : "LIVE · STRANDS"
    : "RECORDED · SAMPLE";
  const graphs = [...new Set(steps.map((step) => step.graph).filter(Boolean))];
  elements.agentRunTopology.textContent = graphs.length ? graphs.join(" → ") : "recovery → deadline_chase";
  elements.agentRunHooks.textContent = "3 BEFORENODECALL GATES";
  const intakeLabel = data.intake_provider === "bedrock"
    ? "Amazon Nova Micro notice intake"
    : "deterministic local notice intake";
  elements.agentRunDetail.textContent = isWorkflow
    ? `${data.execution_target === "agentcore" ? "AgentCore" : "Local"} execution trace from Strands GraphBuilder with ${intakeLabel}; node payloads and prompts remain private.`
    : "Recorded synthetic playback of the Strands GraphBuilder topology deployed on AgentCore. The live path uses Amazon Nova Micro for notice intake; this playback makes no model invocation.";
  const interrupted = steps.filter((step) => step.status === "interrupted").length;
  const completed = steps.filter((step) => step.status === "completed").length;
  elements.agentRunSummary.textContent = interrupted
    ? `${completed} graph steps completed · ${interrupted} paused for contractor judgment`
    : Number(data.metrics?.contractor_decisions || 0) > 0
      ? `${completed} execution lanes completed · ${data.metrics.contractor_decisions} professional decisions recorded`
      : `${completed} graph steps completed · no unnecessary contractor interrupt`;
  elements.agentNodes.replaceChildren(...steps.map((step) => {
    const item = node("li", `agent-node agent-node--${step.status}`);
    item.append(node("span", "agent-node__sequence", String(step.sequence).padStart(2, "0")));
    const body = node("div", "agent-node__body");
    body.append(node("code", "agent-node__id", step.node_id));
    body.append(node("strong", "", step.actor));
    body.append(node("span", "", step.detail));
    item.append(body, node("span", "agent-node__status", step.status.toUpperCase()));
    return item;
  }));
}

function provenanceStep({ number, kind, title, role, status, artifacts, open = false }) {
  const item = node("details", `provenance-step provenance-step--${kind}`);
  item.open = open;
  const summary = node("summary", "");
  summary.append(
    node("span", "provenance-step__number", String(number).padStart(2, "0")),
    node("strong", "provenance-step__title", title),
    node("span", "provenance-step__role", role),
    node("span", `provenance-step__status provenance-step__status--${status.className}`, status.label),
  );
  const artifact = node("dl", "provenance-step__artifact");
  for (const [label, value] of artifacts) {
    const field = node("div", "");
    field.append(node("dt", "", label), node("dd", "", value));
    artifact.append(field);
  }
  item.append(summary, artifact);
  return item;
}

function agentFlowNode({ kind, label, title, detail, state }) {
  const item = node("article", `agent-flow__node agent-flow__node--${kind} agent-flow__node--${state}`);
  item.append(
    node("span", "agent-flow__kind", label),
    node("strong", "agent-flow__name", title),
    node("span", "agent-flow__detail", detail),
    node("span", "agent-flow__state", state === "done" ? "COMPLETED" : state === "paused" ? "PAUSED" : state === "standby" ? "STOOD DOWN" : "UP NEXT"),
  );
  return item;
}

function agentFlowStage({ number, title, cadence, kind, nodes }) {
  const stage = node("section", `agent-flow__stage agent-flow__stage--${kind}`);
  const heading = node("header", "agent-flow__stage-heading");
  heading.append(
    node("span", "agent-flow__stage-number", number),
    node("strong", "agent-flow__stage-title", title),
    node("span", "agent-flow__stage-cadence", cadence),
  );
  const rail = node("div", "agent-flow__rail");
  nodes.forEach((flowNode, index) => {
    rail.append(flowNode);
    if (index < nodes.length - 1) rail.append(node("span", "agent-flow__connector", "→"));
  });
  stage.append(heading, rail);
  return stage;
}

function renderAgentFlow(data) {
  const events = data.events || [];
  const evidenceRan = (data.evidence || []).length > 0
    || events.some((event) => String(event.kind || "").startsWith("evidence_"));
  const schedulerRan = data.automation_status === "scheduled"
    || Number(data.scenario_step || 0) >= 3
    || events.some((event) => event.kind === "deadline_escalation");
  const pending = (data.judgments || []).some((judgment) => judgment.status === "pending");
  const decisions = Number(data.metrics?.contractor_decisions || 0);
  const allReady = Number(data.metrics?.citations_total || 0) > 0
    && data.metrics.citations_ready === data.metrics.citations_total;
  const packetDone = ["awaiting_approval", "approved"].includes(data.packet_status) || allReady;
  const campaignComplete = data.packet_status === "approved";
  const intakeLabel = data.source_mode === "workflow" && data.intake_provider !== "bedrock"
    ? "BOUNDED INTAKE"
    : "STRANDS AGENT · NOVA MICRO";
  elements.agentFlow.replaceChildren(
    agentFlowStage({
      number: "01",
      title: "Understand the notice",
      cadence: "RUNS ONCE",
      kind: "intake",
      nodes: [
        agentFlowNode({ kind: "input", label: "INPUT", title: "Failed-inspection notice", detail: "One redacted authority document", state: "done" }),
        agentFlowNode({ kind: "agent", label: intakeLabel, title: "Notice intake", detail: "Exact language → typed citations", state: "done" }),
        agentFlowNode({ kind: "policy", label: "DETERMINISTIC GRAPH", title: "Recovery policy", detail: "Assign, chase, and replan open work", state: "done" }),
      ],
    }),
    agentFlowStage({
      number: "02",
      title: "Recover in the background",
      cadence: "REPEATS UNTIL READY",
      kind: "background",
      nodes: [
        agentFlowNode({ kind: "agent", label: "STRANDS AGENT · NOVA LITE", title: "Visible-evidence agent", detail: "Pixels → bounded findings", state: evidenceRan ? "done" : "waiting" }),
        agentFlowNode({
          kind: "scheduler",
          label: "AMAZON EVENTBRIDGE",
          title: "Deadline wake-up",
          detail: campaignComplete ? "No open work · checkpoint cancelled" : "Resume the checkpointed chase",
          state: campaignComplete ? "standby" : schedulerRan ? "done" : "waiting",
        }),
      ],
    }),
    agentFlowStage({
      number: "03",
      title: "Stop for authority",
      cadence: "JUDGMENT ONLY",
      kind: "authority",
      nodes: [
        agentFlowNode({ kind: "human", label: "BEFORENODECALL GATE", title: "Contractor judgment", detail: "Interpret, trade off, and approve", state: pending ? "paused" : decisions > 0 ? "done" : "waiting" }),
        agentFlowNode({ kind: "output", label: "OUTPUT", title: "Reinspection packet", detail: "Evidence + authority trail", state: packetDone ? "done" : "waiting" }),
      ],
    }),
  );
}

function renderProvenance(data) {
  const isWorkflow = data.source_mode === "workflow";
  const isAgentCore = isWorkflow && data.execution_target === "agentcore";
  const events = data.events || [];
  const evidence = data.evidence || [];
  const pending = data.judgments.find((judgment) => judgment.status === "pending");
  const hasEvidence = evidence.length > 0 || events.some((event) => event.kind.startsWith("evidence_"));
  const hasRerequest = data.citations.some((citation) => citation.stage === "evidence_rejected")
    || events.some((event) => event.kind === "evidence_rejected");
  const eventBridgeArmed = data.automation_status === "scheduled";
  const deadlineRan = Number(data.scenario_step || 0) >= 3 || events.some((event) => event.kind === "deadline_escalation");
  const decisions = Number(data.metrics?.contractor_decisions || 0);
  const allReady = data.metrics.citations_total > 0 && data.metrics.citations_ready === data.metrics.citations_total;
  const done = { className: "completed", label: "Completed" };
  const recorded = { className: "completed", label: "Recorded sample" };
  const waiting = { className: "pending", label: "Pending" };
  const paused = { className: "paused", label: "Paused for contractor" };
  const stoodDown = { className: "completed", label: "Stood down" };
  const modeDone = isWorkflow ? done : recorded;
  const humanStatus = pending ? paused : decisions > 0 ? done : waiting;
  const packetStatus = data.packet_status === "approved" ? done
    : data.packet_status === "awaiting_approval" ? paused
      : allReady ? waiting : waiting;
  const intakeCapability = isWorkflow && data.intake_provider === "bedrock"
    ? `${isAgentCore ? "AgentCore" : "Local runtime"} · Strands Agent · Amazon Nova Micro`
    : isWorkflow ? "Strands graph · deterministic local intake"
      : "Recorded sample of the Nova Micro-backed production path";
  const visionCapability = isWorkflow && hasEvidence
    ? `${isAgentCore ? "AgentCore" : "Local runtime"} · multimodal Strands Evidence Agent on Nova Lite`
    : "Recorded evidence result; no model or AWS service called in sample playback";

  const steps = [
    provenanceStep({ number: 1, kind: "policy", title: "Failed-inspection notice received", role: "Input boundary", status: modeDone, artifacts: [
      ["Input received", `${data.notice_id} · ${data.property_label}`],
      ["Structured output", `${data.metrics.citations_total} correction records preserving the authority's language`],
      ["Safety boundary", "Mettle never contacts the municipality or inspector from notice intake."],
      ["Next action", "Pass the bounded notice text to intake."],
    ] }),
    provenanceStep({ number: 2, kind: "agent", title: "Notice intake extracts bounded corrections", role: data.intake_provider === "bedrock" || !isWorkflow ? "Strands agent · Nova Micro" : "Bounded local intake", status: modeDone, artifacts: [
      ["Input received", "Redacted correction notice text supplied by the contractor"],
      ["Responsible", data.intake_provider === "bedrock" ? "Mettle Intake Agent on Amazon Nova Micro" : "Validated local notice parser inside the Strands graph"],
      ["Structured output", `${data.metrics.citations_total} typed citations with code reference, exact notice text, trade, and ambiguity`],
      ["AWS / Strands capability", intakeCapability],
      ["Safety boundary", "Extraction only—no code interpretation, severity ranking, or invented correction."],
      ["Next action", "Hand typed corrections to deterministic planning policy."],
    ] }),
    provenanceStep({ number: 3, kind: "policy", title: "Coordination policy prepares trade outreach", role: "Deterministic policy", status: modeDone, artifacts: [
      ["Input received", `${data.metrics.citations_total} bounded corrections plus the contractor's roster`],
      ["Responsible", "Deterministic planning and coordination nodes in Strands GraphBuilder"],
      ["Structured output", `${data.metrics.messages_handled} recorded outreach or follow-up actions`],
      ["Safety boundary", "Ambiguous work is held; outreach remains notice-anchored and recipient-bounded."],
      ["Next action", pending?.kind === "code_interpretation" ? "Hold the ambiguous correction and request contractor judgment." : "Wait for visible proof from open trades."],
    ] }),
    provenanceStep({ number: 4, kind: "agent", title: "Evidence agent assesses visible proof", role: "Strands agent · Nova Lite", status: hasEvidence ? modeDone : waiting, open: hasEvidence && !pending, artifacts: [
      ["Input received", hasEvidence ? "Normalized job-site image plus requirements quoted from its correction" : "No evidence assessment has run yet"],
      ["Responsible", "Dedicated multimodal Mettle Evidence Agent"],
      ["Structured output", hasEvidence ? "One validated visible finding per notice requirement" : "Pending trade evidence"],
      ["AWS / Strands capability", visionCapability],
      ["Safety boundary", "Reports only visible pixels; never interprets code, hidden work, or compliance."],
      ["Next action", hasRerequest ? "Return insufficiency to coordination policy for a precise re-request." : "Accept visible sufficiency or route uncertainty to the contractor."],
    ] }),
    provenanceStep({ number: 5, kind: "policy", title: "Coordination policy sends a precise re-request", role: "Deterministic policy", status: hasRerequest ? modeDone : waiting, artifacts: [
      ["Input received", hasRerequest ? "Evidence finding naming the missing visible requirement" : "No rejected proof currently requires a re-request"],
      ["Responsible", "Deterministic coordination policy"],
      ["Structured output", hasRerequest ? "A bounded replacement-photo request naming only the missing element" : "Pending"],
      ["Safety boundary", "No invented requirement and no repeated contact outside the configured campaign cadence."],
      ["Next action", "Wait for replacement proof; leave accepted corrections out of future follow-ups."],
    ] }),
    provenanceStep({ number: 6, kind: "policy", title: "EventBridge wakes the deadline-chase graph", role: "Background scheduler", status: data.packet_status === "approved" ? stoodDown : eventBridgeArmed || deadlineRan ? modeDone : waiting, artifacts: [
      ["Input received", "Versioned workflow reference, deadline checkpoint, and idempotency key"],
      ["Responsible", isAgentCore ? "Amazon EventBridge Scheduler → private AgentCore worker" : "Recorded deadline-chase checkpoint"],
      ["Structured output", data.packet_status === "approved" ? "Packet approved; no open work remains and no further checkpoint is armed" : eventBridgeArmed ? `Next bounded check armed${data.next_check_at ? ` for ${formatTimestamp(data.next_check_at)}` : ""}` : deadlineRan ? "Open-only chase replanned at the deadline checkpoint" : "No checkpoint has fired yet"],
      ["Safety boundary", "One-time schedule, stale-event rejection, bounded retries, and open corrections only."],
      ["Next action", data.packet_status === "approved" ? "None—the approved campaign is complete." : "Replan unresolved work and interrupt only if the deadline creates a contractor tradeoff."],
    ] }),
    provenanceStep({ number: 7, kind: "human", title: "Strands pauses for professional judgment", role: "BeforeNodeCall gate", status: humanStatus, open: Boolean(pending), artifacts: [
      ["Input received", pending ? pending.question : `${decisions} contractor decision${decisions === 1 ? "" : "s"} recorded`],
      ["Responsible", "Licensed contractor—not a model"],
      ["Structured output", pending ? "Execution is paused until an explicit bounded decision is submitted" : "Validated decision restored to the same graph session"],
      ["AWS / Strands capability", "Strands BeforeNodeCallEvent interrupt and resume"],
      ["Safety boundary", "Mettle cannot interpret ambiguous code, choose a schedule tradeoff, or release the packet."],
      ["Next action", pending ? "Await contractor decision." : "Resume the deterministic recovery graph."],
    ] }),
    provenanceStep({ number: 8, kind: "policy", title: "Packet assembly prepares the evidence handoff", role: "Deterministic policy", status: packetStatus, artifacts: [
      ["Input received", `${data.metrics.citations_ready} of ${data.metrics.citations_total} corrections currently have accepted visible proof`],
      ["Responsible", "Deterministic ReportLab packet renderer"],
      ["Structured output", data.packet_status === "approved" ? "Contractor-approved evidence PDF" : data.packet_status === "awaiting_approval" ? "Evidence packet awaiting contractor release" : "Packet remains incomplete and locked"],
      ["Safety boundary", "No automatic inspector contact, municipality approval claim, or code certification."],
      ["Next action", data.packet_status === "approved" ? "Download the contractor-approved artifact." : allReady ? "Require final contractor approval." : "Wait for the remaining accepted proof."],
    ] }),
  ];
  renderAgentFlow(data);
  elements.provenanceSteps.replaceChildren(...steps);
}

function decisionPrompt(judgment) {
  if (judgment.kind === "final_packet_approval") {
    return ["Type your approval decision", "Approve packet"];
  }
  if (judgment.kind === "deadline_tradeoff") {
    return ["Keep the date, or request a new one?", "Record deadline decision"];
  }
  if (judgment.kind === "evidence_review") {
    return ["Record why this proof is sufficient or what must be clearer", "Accept proof"];
  }
  return ["Describe the evidence the trade must provide", "Set evidence requirement"];
}

function renderJudgment(judgment, {photoReview = false} = {}) {
  const isPacketApproval = judgment.packet_approval || judgment.kind === "final_packet_approval";
  const isEvidenceReview = judgment.evidence_review || judgment.kind === "evidence_review";
  const card = node("article", "judgment");
  card.append(node("div", "judgment__kind", `${titleCase(judgment.kind)}${judgment.citation_id ? ` · C${judgment.citation_id}` : ""}`));
  card.append(node("h3", "", judgment.question));
  card.append(node("p", "", judgment.reason));
  if (isEvidenceReview && !photoReview) {
    const review = node("button", "button button--orange", "Review photo & decide →");
    review.type = "button";
    review.onclick = () => openCorrection(judgment.citation_id);
    card.append(review);
    return card;
  }

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
  const draftKey = `${activeWorkflowId || "sample"}:${judgment.judgment_id}`;
  input.value = judgmentDrafts.get(draftKey) || "";
  input.addEventListener("input", () => judgmentDrafts.set(draftKey, input.value));
  const button = node("button", "button", buttonLabel);
  button.type = "submit";
  button.dataset.disposition = isEvidenceReview ? "accept" : "";
  const rejectButton = isEvidenceReview
    ? node("button", "button button--outline", "Request clearer proof")
    : null;
  if (rejectButton) {
    rejectButton.type = "submit";
    rejectButton.dataset.disposition = "reject";
    form.classList.add("judgment__evidence-review");
  }
  form.append(label, input, button, ...(rejectButton ? [rejectButton] : []));
  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    const decision = input.value.trim();
    if (decision.length < 3) return;
    const submittedButton = event.submitter || button;
    setBusy(button, true);
    if (rejectButton) setBusy(rejectButton, true);
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
      } else if (activeWorkflowId && isEvidenceReview) {
        const workflowRoot = activeWorkflowTarget === "agentcore"
          ? "/api/agentcore/workflows"
          : "/api/workflows";
        const envelope = await request(`${workflowRoot}/${encodeURIComponent(activeWorkflowId)}/evidence/review`, {
          method: "POST",
          headers: { "Idempotency-Key": crypto.randomUUID().replaceAll("-", "_") },
          body: JSON.stringify({
            assessment_id: judgment.judgment_id,
            disposition: submittedButton.dataset.disposition,
            decision,
          }),
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
      judgmentDrafts.delete(draftKey);
      showToast(isPacketApproval
        ? "Final approval recorded. The reinspection PDF is ready to download."
        : isEvidenceReview
          ? submittedButton.dataset.disposition === "accept"
            ? "Contractor acceptance recorded. This correction is ready for the packet."
            : "Contractor requested clearer proof. This correction remains open."
          : "Your decision is logged. Mettle resumed the recovery run.");
    } catch (error) {
      if (error.code === "workflow_not_found" && activeWorkflowTarget === "agentcore") {
        showError(error);
        elements.error.scrollIntoView({ behavior: "smooth", block: "start" });
      } else {
        input.setCustomValidity(error.message);
        input.reportValidity();
        input.setCustomValidity("");
      }
    } finally {
      setBusy(button, false);
      if (rejectButton) setBusy(rejectButton, false);
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

function pendingJudgment(data, judgmentId) {
  return (data.judgments || []).find(
    (judgment) => judgment.judgment_id === judgmentId && judgment.status === "pending",
  );
}

function tourPhase(data) {
  if (data.packet_status === "approved") {
    return {
      key: "complete", scene: 5, stopIndex: 4, complete: true,
      eyebrow: "RECOVERY COMPLETE · CONTRACTOR APPROVED",
      title: "Five pages. All of it earned.",
      copy: "Each citation carries its authority language, accepted photograph, communication trail, and contractor decision. Nothing was written that the evidence did not support.",
      controlTitle: "The packet is real. So is the restraint behind it.",
      controlCopy: "Download the approved artifact, then inspect the Strands run that coordinated the work without taking the contractor’s authority.",
      actionLabel: "Download the approved packet",
      actionNote: "5-PAGE PDF · GENERATED FROM THIS RECOVERY",
      action: "download-packet",
    };
  }
  if (pendingJudgment(data, "final-approval")) {
    return {
      key: "approval", scene: 4, stopIndex: 3,
      eyebrow: "FINAL GATE · PROFESSIONAL CONTROL",
      title: "The packet is assembled. Mettle still cannot release it.",
      copy: "Every citation has accepted proof, but contacting the inspector remains a contractor-controlled action.",
      controlTitle: "Autonomy ends exactly where professional authority begins.",
      controlCopy: "The packet agent prepared the artifact and then stopped. Your approval is recorded alongside the evidence it releases.",
      actionLabel: "Approve the reinspection packet",
      actionNote: "EXPLICIT APPROVAL · DOWNLOAD UNLOCKS AFTERWARD",
      action: "approve-packet",
    };
  }
  if (pendingJudgment(data, "deadline-choice")) {
    return {
      key: "deadline", scene: 3, stopIndex: 2,
      eyebrow: "BACKGROUND RECOVERY · DEADLINE ADAPTED",
      title: "Two days left. Not Mettle’s call.",
      copy: "Accepted work left the campaign. The incomplete framing photo triggered a precise re-request; two days out, only unresolved trades were escalated.",
      controlTitle: "The agent handled the routine pressure. The deadline tradeoff stays yours.",
      controlCopy: "Mettle can escalate follow-up, but it will not decide whether a contractor should keep or move the reinspection date.",
      actionLabel: "Keep the date and escalate",
      actionNote: "CONTRACTOR DECISION · CRITICAL RECOVERY RESUMES",
      action: "resolve-deadline",
    };
  }
  if (pendingJudgment(data, "route-review")) {
    return {
      key: "boundary", scene: 1, stopIndex: 0,
      eyebrow: "FOR THE CONTRACTOR HANDED A DISAPPROVED ROUGH-IN",
      title: "The notice is the only input.",
      copy: "Mettle derives a proposed recovery from the authority’s exact language, then stops before a single trade is contacted.",
      controlTitle: "Zero outreach until the contractor approves every route.",
      controlCopy: "The graph prepared assignees and proof requests, held the ambiguous mechanical boundary, and paused with zero messages recorded.",
      actionLabel: "Approve routes & begin recovery",
      actionNote: "CONTRACTOR DECISION · OUTREACH STARTS AFTER APPROVAL",
      action: "resolve-code",
    };
  }
  if (Number(data.scenario_step || 0) >= 3) {
    return {
      key: "finish", scene: 3, stopIndex: 2,
      eyebrow: "OPEN-ONLY REPLANNING · RECOVERY CONTINUES",
      title: "Closed work stays closed. Mettle keeps chasing only what remains.",
      copy: "The contractor’s deadline decision is recorded. The recovery graph can now accept replacement proof, close the final citations, and assemble the packet.",
      controlTitle: "One click compresses the remaining multi-day campaign.",
      controlCopy: "Watch the evidence and packet agents finish the bounded work. Mettle will stop again before anything can reach the inspector.",
      actionLabel: "Finish the background recovery",
      actionNote: "SYNTHETIC TIME COMPRESSION · SAME OPEN-ONLY POLICY",
      action: "advance",
    };
  }
  return {
    key: "recovery", scene: 2, stopIndex: 1,
    eyebrow: "BOUNDARY SET · CAMPAIGN RESUMED",
    title: "The chase runs without you.",
    copy: "Five days of coordination cross three trades: requests out, photographs in, one rejection, and deadline-aware checkpoints while no browser needs to stay open.",
    controlTitle: "The next click represents days of background coordination.",
    controlCopy: "Mettle will accept sufficient proof, reject an incomplete submission with a specific re-request, and interrupt only when the deadline creates a real tradeoff.",
    actionLabel: "Run the background campaign",
    actionNote: "WATCH ACCEPTANCE · REJECTION · DEADLINE ESCALATION",
    action: "advance",
  };
}

function tourArtifact({ index, title, detail, status, tone = "" }) {
  const card = node("article", `tour-artifact${tone ? ` tour-artifact--${tone}` : ""}`);
  card.append(node("span", "tour-artifact__index", index));
  const body = node("div", "tour-artifact__body");
  body.append(node("strong", "", title), node("p", "", detail));
  card.append(body, node("span", "tour-artifact__status", status));
  return card;
}

function citationTourArtifact(citation) {
  const labels = {
    ready: ["ACCEPTED", "ready"],
    evidence_rejected: ["RE-REQUESTED", "blocked"],
    needs_judgment: ["NEEDS YOU", "blocked"],
    awaiting_evidence: ["IN RECOVERY", ""],
  };
  const [status, tone] = labels[citation.stage] || [citation.stage.toUpperCase(), ""];
  const detail = citation.evidence_note
    || citation.evidence_requirements?.[0]
    || citation.notice_text;
  return tourArtifact({
    index: `C${citation.citation_id}`,
    title: `${citation.code_reference} · ${titleCase(citation.trade)}`,
    detail,
    status,
    tone,
  });
}

function evidenceComparisonCard({ image, alt, status, title, detail, tone }) {
  const card = node("figure", `tour-evidence-compare__card tour-evidence-compare__card--${tone}`);
  const photo = document.createElement("img");
  photo.src = image;
  photo.alt = alt;
  const media = node("div", "tour-evidence-compare__media");
  media.append(photo);
  const caption = node("figcaption", "");
  caption.append(
    node("span", "tour-evidence-compare__status", status),
    node("strong", "", title),
    node("p", "", detail),
  );
  card.append(media, caption);
  return card;
}

function createEvidenceComparison() {
  const comparison = node("section", "tour-evidence-compare");
  comparison.setAttribute("aria-label", "Rejected evidence and accepted replacement comparison");
  comparison.append(
    evidenceComparisonCard({
      image: "/static/evidence/framing-closeup-insufficient.png",
      alt: "Synthetic close-up of one framing protection plate without enough surrounding context to identify the corrected wall location",
      status: "RE-REQUESTED",
      title: "Close-up omitted the corrected wall location",
      detail: "Send a wider shot that identifies the corrected wall location.",
      tone: "rejected",
    }),
    node("div", "tour-evidence-compare__handoff", "PRECISE RE-REQUEST → REPLACEMENT"),
    evidenceComparisonCard({
      image: "/static/evidence/framing-plates-complete.png",
      alt: "Synthetic wide view showing framing protection plates and their corrected wall location",
      status: "ACCEPTED",
      title: "Replacement connected the repair to its location",
      detail: "Protection plates and the wider wall location are visible. This is evidence sufficiency—not code certification.",
      tone: "accepted",
    }),
  );
  return comparison;
}

function timelineEvent(label, tone = "") {
  const event = node("span", `coordination-timeline__event${tone ? ` coordination-timeline__event--${tone}` : ""}`, label);
  event.title = label;
  return event;
}

function createCoordinationTimeline(data) {
  const step = Number(data.scenario_step || 0);
  const timeline = node("section", "coordination-timeline");
  timeline.setAttribute("aria-label", "Recorded five-day coordination timeline");
  const heading = node("div", "coordination-timeline__heading");
  heading.append(
    node("div", "", "Coordination, five days"),
    node("span", "", "TIME COMPRESSED · AUG 10 → AUG 15 · RECORDED SAMPLE"),
  );
  const grid = node("div", "coordination-timeline__grid");
  const days = ["TRADE / DAY", "10", "11", "12", "13", "14", "15"];
  for (const day of days) grid.append(node("span", "coordination-timeline__day", day));
  const rows = [
    ["C1 · ELECTRICAL", [timelineEvent("REQUEST", "request"), step >= 1 ? timelineEvent("ACCEPTED", "accepted") : "", "", "", "", step >= 1 ? timelineEvent("CLOSED", "closed") : ""]],
    ["C2 · FRAMING", [timelineEvent("REQUEST", "request"), "", step >= 2 ? timelineEvent("REJECTED", "rejected") : "", step >= 2 ? timelineEvent("RE-REQUEST", "request") : "", step >= 2 ? timelineEvent("AWAITING", "waiting") : "", ""]],
    ["C3 · MECHANICAL", [timelineEvent("HELD", "held"), timelineEvent("REQUEST", "request"), "", timelineEvent("AWAITING", "waiting"), "", ""]],
  ];
  for (const [label, cells] of rows) {
    grid.append(node("strong", "coordination-timeline__trade", label));
    for (const cell of cells) {
      const slot = node("span", "coordination-timeline__slot");
      if (cell) slot.append(cell);
      grid.append(slot);
    }
  }
  const legend = node("p", "coordination-timeline__legend", "▲ request  ·  ■ accepted  ·  × rejected  ·  ○ awaiting  ·  ◆ checkpoint");
  const ledger = node("ol", "coordination-ledger");
  ledger.setAttribute("aria-label", "Latest autonomous work records");
  for (const event of (data.events || []).slice(0, 3)) {
    const entry = node("li", "");
    entry.append(
      node("span", "coordination-ledger__marker", event.kind === "evidence_rejected" ? "×" : "◆"),
      node("strong", "", event.title),
      node("span", "", event.actor.toUpperCase()),
    );
    ledger.append(entry);
  }
  timeline.append(heading, grid, legend, ledger);
  return timeline;
}

function tourWorkspaceView(phase) {
  if (["deadline", "approval", "complete"].includes(phase.key)) return "evidence";
  return "recovery";
}

function createTourWorkspaceFrame(data, phase, artifacts) {
  const frame = node("section", "tour-workspace");
  const navigation = node("nav", "tour-workspace__tabs");
  navigation.setAttribute("aria-label", "Tour workspace views");
  const activeView = tourWorkspaceView(phase);
  for (const [view, label] of [["recovery", "01 Recovery"], ["evidence", "02 Evidence & packet"], ["activity", "03 Agent activity"]]) {
    const tab = node("span", "", label);
    tab.setAttribute("aria-current", activeView === view ? "page" : "false");
    tab.title = activeView === view ? "Current guided-tour view" : "Available in the full workspace after the tour";
    navigation.append(tab);
  }
  const status = node("div", "tour-workspace__status");
  const ready = Number(data.metrics?.citations_ready || 0);
  const total = Number(data.metrics?.citations_total || 0);
  const open = Math.max(0, total - ready);
  status.append(
    node("strong", "", phase.complete ? "RECOVERY COMPLETE" : open ? `${open} CORRECTION${open === 1 ? "" : "S"} OPEN` : "PACKET AWAITING APPROVAL"),
    node("span", "", phase.complete ? `${ready} OF ${total} ACCEPTED · RECORD CLOSED` : `${data.days_remaining} DAYS TO REINSPECTION · OPEN-ONLY CHASE`),
  );
  const content = node("div", "tour-workspace__content");
  content.append(...artifacts);
  frame.append(navigation, status, content);
  return frame;
}

function createTourAgentProof(data) {
  const steps = sampleAgentRun(data);
  const interrupted = steps.find((step) => step.status === "interrupted");
  const preferredIds = interrupted?.node_id === "deadline_gate"
    ? ["intake", "plan", "coordinate", "replan_open", "deadline_gate"]
    : interrupted?.node_id === "judgment_gate"
      ? ["intake", "plan", "coordinate", "judgment_gate", "finish"]
      : ["intake", "plan", "coordinate", "replan_open", "finish_chase"];
  const featured = preferredIds
    .map((nodeId) => steps.find((step) => step.node_id === nodeId))
    .filter(Boolean)
    .slice(0, 5);
  for (const step of steps) {
    if (featured.length >= 5) break;
    if (!featured.some((item) => item.node_id === step.node_id)) featured.push(step);
  }
  const proof = node("aside", "tour-agent-proof");
  const header = node("div", "tour-agent-proof__header");
  const heading = node("div", "");
  heading.append(
    node("span", "tour-agent-proof__mode", "SAMPLE · STRANDS"),
    node("strong", "", "Inspectable orchestration"),
  );
  const inspect = node("button", "tour-agent-proof__inspect", "Open full trace ↗");
  inspect.type = "button";
  inspect.addEventListener("click", inspectAgentRun);
  header.append(heading, inspect);
  const topology = node("div", "tour-agent-proof__topology");
  topology.append(
    node("span", "", "recovery → deadline_chase"),
    node("span", "", "3 BEFORENODECALL GATES"),
  );
  const nodes = node("ol", "tour-agent-proof__nodes");
  for (const step of featured) {
    const item = node("li", `tour-agent-proof__node tour-agent-proof__node--${step.status}`);
    item.append(
      node("code", "", step.node_id),
      node("strong", "", step.actor),
      node("span", "", step.status === "interrupted" ? "PAUSED FOR CONTRACTOR" : step.status.toUpperCase()),
    );
    nodes.append(item);
  }
  proof.append(header, topology, nodes);
  return proof;
}

const packetEvidenceImages = {
  "1": "/static/evidence/panel-wide-measured.png",
  "2": "/static/evidence/framing-plates-complete.png",
  "3": "/static/evidence/mechanical-access-wide.png",
};

function renderPacketFinalePage(preview, page, data) {
  preview.replaceChildren();
  preview.dataset.page = String(page);
  if (page === 1) {
    const cover = node("div", "packet-page packet-page--cover");
    cover.append(
      node("span", "packet-page__eyebrow", "FAILED INSPECTION RECOVERY"),
      node("strong", "packet-page__title", "Reinspection evidence packet"),
      node("p", "", "A notice-anchored record of corrections, evidence, communication, and contractor decisions."),
    );
    const facts = node("dl", "packet-page__facts");
    for (const [label, value] of [["Notice", data.notice_id], ["Citations", `${data.metrics.citations_ready} / ${data.metrics.citations_total} ready`], ["Authority", "Contractor approved"]]) {
      const item = node("div", "");
      item.append(node("dt", "", label), node("dd", "", value));
      facts.append(item);
    }
    cover.append(facts, node("span", "packet-page__stamp", "APPROVED BY CONTRACTOR"));
    preview.append(cover);
    return;
  }
  if (page >= 2 && page <= 4) {
    const citation = data.citations.find((item) => item.citation_id === String(page - 1));
    const evidence = node("div", "packet-page packet-page--evidence");
    const photo = document.createElement("img");
    photo.src = packetEvidenceImages[citation.citation_id];
    photo.alt = `Accepted synthetic evidence for citation ${citation.citation_id}`;
    const copy = node("div", "packet-page__evidence-copy");
    copy.append(
      node("span", "packet-page__eyebrow", `PAGE ${page} · CITATION ${citation.citation_id} · ${citation.code_reference}`),
      node("strong", "", `${titleCase(citation.trade)} evidence accepted`),
      node("blockquote", "", `“${citation.notice_text}”`),
      node("p", "", citation.evidence_note || citation.evidence_requirements[0]),
      node("span", "packet-page__accepted", "VISIBLE PROOF ACCEPTED · NOT CODE CERTIFICATION"),
    );
    evidence.append(photo, copy);
    preview.append(evidence);
    return;
  }
  const record = node("div", "packet-page packet-page--record");
  record.append(
    node("span", "packet-page__eyebrow", "PAGE 5 · RECOVERY COMMUNICATION RECORD"),
    node("strong", "packet-page__title", "An inspectable trail of the recovery"),
  );
  const rows = node("ol", "packet-page__record-list");
  for (const event of data.events.slice(-4)) {
    const row = node("li", "");
    row.append(node("time", "", formatTime(event.happened_at)), node("span", "", event.title));
    rows.append(row);
  }
  record.append(rows, node("span", "packet-page__stamp", "RELEASE AUTHORITY RECORDED"));
  preview.append(record);
}

function createPacketFinale(data) {
  const finale = node("article", "packet-finale");
  const bar = node("div", "packet-finale__bar");
  bar.append(node("span", "", `METTLE · ${data.notice_id} · APPROVED PACKET`), node("span", "", "READY FOR REINSPECTION"));
  const body = node("div", "packet-finale__body");
  const heading = node("div", "packet-finale__heading");
  heading.append(
    node("span", "packet-page__eyebrow", "EVIDENCE INSIDE THE APPROVED ARTIFACT"),
    node("strong", "", "Five pages. Every citation tied back to visible proof."),
  );
  const navigation = node("nav", "packet-finale__nav");
  navigation.setAttribute("aria-label", "Packet page preview");
  const preview = node("div", "packet-finale__preview");
  const labels = ["Cover", "C1 Electrical", "C2 Framing", "C3 Mechanical", "Recovery record"];
  const buttons = labels.map((label, index) => {
    const button = node("button", "", `${index + 1} · ${label}`);
    button.type = "button";
    button.setAttribute("aria-pressed", String(index === 1));
    button.addEventListener("click", () => {
      for (const candidate of buttons) candidate.setAttribute("aria-pressed", String(candidate === button));
      renderPacketFinalePage(preview, index + 1, data);
    });
    navigation.append(button);
    return button;
  });
  renderPacketFinalePage(preview, 2, data);
  const documentDetails = node("details", "packet-finale__document");
  documentDetails.append(node("summary", "", "Open the actual five-page PDF"));
  const viewer = document.createElement("iframe");
  viewer.title = "Actual approved five-page reinspection packet PDF";
  viewer.loading = "lazy";
  viewer.src = "/api/demo/packet/preview.pdf#page=2&toolbar=1&navpanes=0";
  const fallback = node("a", "packet-finale__fallback", "Open PDF in a new tab ↗");
  fallback.href = "/api/demo/packet/preview.pdf";
  fallback.target = "_blank";
  fallback.rel = "noopener";
  documentDetails.append(viewer, fallback);
  body.append(heading, navigation, preview, documentDetails);
  finale.append(bar, body);
  return finale;
}

function renderTourVisual(data, phase) {
  const artifacts = [];
  if (phase.key === "boundary") {
    artifacts.push(
      tourArtifact({
        index: "PDF",
        title: "Municipal correction notice received",
        detail: `“${data.citations[0].notice_text}” plus 2 additional numbered findings.`,
        status: "SOURCE",
        tone: "emphasis",
      }),
      node("div", "tour-transition", "Intake agent → deterministic route policy → contractor gate"),
      tourArtifact({
        index: "0×",
        title: "Outreach held before approval",
        detail: "Three proposed routes are ready for review; no trade has been contacted and no message has been recorded.",
        status: "HELD",
        tone: "blocked",
      }),
      citationTourArtifact(data.citations.find((citation) => citation.citation_id === "3")),
    );
  } else if (phase.key === "deadline") {
    artifacts.push(
      createEvidenceComparison(),
      tourArtifact({
        index: "T−2",
        title: "Recovery cadence moved to critical",
        detail: "Only unresolved trades were escalated; the contractor received the deadline tradeoff instead of more routine noise.",
        status: "NEEDS YOU",
        tone: "blocked",
      }),
    );
  } else if (phase.key === "approval" || phase.key === "complete") {
    if (phase.key === "complete") {
      artifacts.push(createPacketFinale(data));
    } else {
      artifacts.push(
        ...data.citations.map(citationTourArtifact),
        node("div", "tour-transition", "Packet agent assembled the trail"),
        tourArtifact({
          index: "PDF",
          title: "Reinspection evidence packet prepared",
          detail: "Notice language, accepted evidence, recovery history, and the human approval record in one artifact.",
          status: "LOCKED",
          tone: "blocked",
        }),
      );
    }
  } else {
    if (phase.key === "recovery") artifacts.push(createCoordinationTimeline(data));
    else artifacts.push(...data.citations.map(citationTourArtifact));
  }
  if (!phase.complete) artifacts.push(createTourAgentProof(data));
  elements.tourVisual.replaceChildren(createTourWorkspaceFrame(data, phase, artifacts));
}

async function resolveTourJudgment(judgmentId, decision, successMessage) {
  setBusy(elements.tourAction, true);
  try {
    campaign = await request(`/api/judgments/${encodeURIComponent(judgmentId)}/resolve`, {
      method: "POST",
      body: JSON.stringify({ decision }),
    });
    render(campaign);
    showToast(successMessage);
  } catch (error) {
    showError(error);
  } finally {
    setBusy(elements.tourAction, false);
    if (campaign) renderJudgeTour(campaign);
  }
}

const judgeLensByPhase = {
  boundary: {
    impact: "Zero-configuration intake: the failed-inspection notice becomes a reviewable recovery plan.",
    agent: "The Nova Micro intake agent extracts bounded citations; deterministic policy prepares routes but records zero outreach.",
    human: "The contractor approves every assignee and proof request, including the mechanical boundary Mettle refuses to invent.",
  },
  recovery: {
    impact: "This is background autonomy, not a chat response: the campaign continues while the contractor is away.",
    agent: "The Nova Lite evidence agent checks visible proof; the recovery graph accepts, rejects, re-requests, and follows up across trades.",
    human: "Routine evidence handling creates no interrupt. The contractor returns only when the deadline creates a real tradeoff.",
  },
  deadline: {
    impact: "The campaign replans against time and removes completed work instead of restarting a generic checklist.",
    agent: "EventBridge wakes the graph; open-only policy escalates the unresolved trade and preserves accepted evidence.",
    human: "Whether to keep or move the reinspection date remains a business and professional decision.",
  },
  finish: {
    impact: "One decision resumes the same checkpointed campaign—closed citations remain closed.",
    agent: "Evidence assessment finishes the remaining citations and deterministic packet assembly prepares the handoff.",
    human: "Mettle can prepare the artifact, but it cannot release or send it for reinspection.",
  },
  approval: {
    impact: "Complete proof is not permission. The final artifact is deliberately locked.",
    agent: "Packet assembly binds notice language, accepted proof, timestamps, and the recovery record into five pages.",
    human: "Only the contractor can approve the packet for reinspection scheduling.",
  },
  complete: {
    impact: "The full loop ends with a usable contractor artifact, not a dashboard or a generated summary.",
    agent: "Fifteen background actions and two model-agent lanes are visible in the execution receipts.",
    human: "Three explicit contractor decisions form the authority trail behind the approved packet.",
  },
};

function renderJudgeTour(data) {
  if (!judgeTourActive || data.source_mode === "workflow") return;
  const phase = tourPhase(data);
  const phaseChanged = elements.judgeTour.dataset.phase !== phase.key;
  const guideView = ["approval", "complete"].includes(phase.key) ? "evidence" : "recovery";
  if (activeWorkspaceView !== guideView) setWorkspaceView(guideView);
  elements.judgeTour.hidden = false;
  elements.judgeTour.dataset.phase = phase.key;
  document.body.classList.add("tour-mode");
  setTourIsolation(true);
  elements.tourProgressLabel.textContent = phase.complete ? "RECOVERY COMPLETE" : `SCENE ${phase.scene} OF 5`;
  elements.tourEyebrow.textContent = phase.eyebrow;
  elements.tourTitle.textContent = phase.title;
  elements.tourCopy.textContent = phase.copy;
  elements.tourControlTitle.textContent = phase.controlTitle;
  elements.tourControlCopy.textContent = phase.controlCopy;
  const lens = judgeLensByPhase[phase.key] || judgeLensByPhase.boundary;
  document.getElementById("tour-agent-receipt").textContent = `RECORDED AGENT WORK · ${lens.agent}`;
  elements.judgeLensImpact.textContent = lens.impact;
  elements.judgeLensAgent.textContent = lens.agent;
  elements.judgeLensHuman.textContent = lens.human;
  elements.tourAction.textContent = phase.actionLabel;
  elements.tourActionNote.textContent = phase.actionNote;
  elements.tourAction.disabled = demoRunning;
  elements.tourAction.setAttribute("aria-busy", String(demoRunning));
  elements.tourSecondary.hidden = !phase.complete;
  elements.tourSecondary.disabled = demoRunning;
  elements.tourOutcomeCopy.replaceChildren();
  if (phase.complete) {
    elements.tourOutcomeCopy.append(
      node("span", "", "◆"),
      node("strong", "", "15 agent actions absorbed. 3 contractor decisions preserved. "),
      document.createTextNode("That is the product: autonomous recovery with an inspectable authority trail."),
    );
  } else {
    elements.tourOutcomeCopy.append(
      node("span", "", "◆"),
      node("strong", "", "Same product, staged for evaluation. "),
      document.createTextNode("Every scene uses this browser session’s real sample endpoints and remains inspectable in the full workspace."),
    );
  }
  for (const [index, stop] of elements.tourStops.entries()) {
    const state = phase.complete || index < phase.stopIndex
      ? "complete"
      : index === phase.stopIndex ? "active" : "upcoming";
    stop.dataset.state = state;
  }
  renderTourVisual(data, phase);
  const sceneProof = document.querySelector("#tour-visible-proof");
  sceneProof.replaceChildren();
  if (phase.key === "boundary") {
    sceneProof.append(node("p", "mono-label", "REVIEW THE SAMPLE ROUTES · ZERO OUTREACH SO FAR"));
    for (const citation of data.citations) {
      const route = node("p", "tour-route-summary");
      route.append(node("strong", "", `C${citation.citation_id} · ${titleCase(citation.trade)} — `),
        document.createTextNode(citation.evidence_requirements?.join("; ") || "Contractor-defined: wide photo showing the equipment and measured service clearance"));
      sceneProof.append(route);
    }
    sceneProof.append(node("p", "", "This walkthrough uses a prepared contractor decision. A real recovery requires reviewing each recipient and proof request."));
  } else if (["deadline", "finish"].includes(phase.key) && data.citations.find(c => c.citation_id === "2")?.stage !== "ready") {
    sceneProof.append(node("p", "mono-label", "RECORDED EVIDENCE RESULT · REPLACEMENT STILL NEEDED"),
      evidenceComparisonCard({
        image: "/static/evidence/framing-closeup-insufficient.png",
        alt: "Synthetic close-up missing the corrected wall location",
        status: "RE-REQUESTED", title: "The photo did not identify the wall location",
        detail: "Mettle requested a wider photo. The incomplete proof did not close this correction.", tone: "rejected",
      }));
  } else if (["finish", "approval", "complete"].includes(phase.key)) {
    sceneProof.append(node("p", "mono-label", "RECORDED EVIDENCE HISTORY · REJECTION TO ACCEPTED REPLACEMENT"), createEvidenceComparison());
  }
  sceneProof.hidden = !sceneProof.children.length;
  if (phase.complete) {
    const previewLink = node("a", "button button--outline", "View approved PDF in browser");
    previewLink.href = "/api/demo/packet/preview.pdf";
    previewLink.target = "_blank";
    previewLink.rel = "noopener";
    sceneProof.append(previewLink);
  }
  for (const target of document.querySelectorAll(".is-guide-target")) target.classList.remove("is-guide-target");
  const guideTargetSelector = {
    boundary: ".citation--needs-action",
    recovery: ".workspace-agent-status",
    deadline: ".away-briefing",
    finish: ".citation-list",
    approval: ".packet-primary",
    complete: ".packet-preview",
  }[phase.key];
  document.querySelector(guideTargetSelector)?.classList.add("is-guide-target");
  const metricValues = phase.key === "boundary"
    ? [
      ["Notice input", "1 PDF"],
      ["Trades contacted", "0"],
      ["Agent actions", data.metrics.automated_actions],
      ["Waiting on you", "1"],
    ]
    : [
      ["Citations ready", `${data.metrics.citations_ready}/${data.metrics.citations_total}`],
      ["Messages handled", data.metrics.messages_handled],
      ["Agent actions", data.metrics.automated_actions],
      ["Your decisions", data.metrics.contractor_decisions],
    ];
  elements.tourMetrics.replaceChildren(...metricValues.map(([label, value]) => {
    const metric = node("div", "tour-metric");
    metric.append(node("dd", "", String(value)), node("dt", "", label));
    return metric;
  }));
  tourSecondaryHandler = phase.complete ? inspectAgentRun : null;
  tourActionHandler = phase.action === "resolve-code"
    ? () => resolveTourJudgment(
      "route-review",
      "Wide photo showing the equipment and measured service clearance",
      "Routes approved. Mettle released the notice-anchored outreach and resumed the recovery.",
    )
      : phase.action === "resolve-deadline"
      ? resolveDeadlineAndContinue
      : phase.action === "approve-packet"
        ? () => resolveTourJudgment(
          "final-approval",
          "Approve packet for reinspection scheduling",
          "Final approval recorded. The reinspection packet is ready.",
        )
        : phase.action === "download-packet"
          ? downloadDemoPacket
          : runSampleUntilPause;
  if (phaseChanged) {
    window.requestAnimationFrame(() => window.scrollTo({ top: 0, behavior: "auto" }));
  }
}

function inspectAgentRun() {
  setJudgeTourActive(false, { updateUrl: true, focus: false });
  sessionStorage.setItem("mettle_entry_selected", "sample");
  setWorkspaceView("activity", { updateUrl: true, focusTab: true });
  window.setTimeout(() => document.querySelector(".agent-run-panel")?.scrollIntoView({ behavior: "smooth", block: "start" }), 0);
}

async function downloadDemoPacket() {
  try {
    const response = await fetch("/api/demo/packet.pdf");
    if (!response.ok || !response.headers.get("content-type")?.includes("application/pdf")) {
      throw new Error("The packet could not be downloaded. Your approved recovery is still saved. Try again.");
    }
    const url = URL.createObjectURL(await response.blob());
    const link = document.createElement("a");
    link.href = url;
    link.download = "mettle-guided-reinspection-packet.pdf";
    document.body.append(link);
    link.click();
    link.remove();
    window.setTimeout(() => URL.revokeObjectURL(url), 60000);
    showToast("Packet download requested. If your browser blocks downloads, your recovery remains here.");
  } catch (error) {
    showError(error);
  }
}

async function resolveDeadlineAndContinue() {
  setBusy(elements.tourAction, true);
  try {
    campaign = await request("/api/judgments/deadline-choice/resolve", {
      method: "POST",
      body: JSON.stringify({ decision: "Keep the current reinspection target and continue critical recovery" }),
    });
    render(campaign);
    showToast("Deadline decision recorded. Mettle is closing only the remaining work.");
    await runSampleUntilPause();
  } catch (error) {
    showError(error);
  } finally {
    setBusy(elements.tourAction, false);
  }
}

function buildBackgroundBrief(data) {
  const isWorkflow = data.source_mode === "workflow";
  const isAgentCore = isWorkflow && data.execution_target === "agentcore";
  const sampleHasAdvanced = !isWorkflow && Number(data.scenario_step || 0) > 0;
  const events = data.events || [];
  const completedKinds = new Set([
    "deadline_escalation",
    "evidence_accepted",
    "evidence_rejected",
    "evidence_manual_review",
    "packet_prepared",
  ]);
  const completedBackgroundWork = events.some((event) => completedKinds.has(event.kind));
  const armed = isAgentCore && data.automation_status === "scheduled" && !completedBackgroundWork;
  if (!sampleHasAdvanced && !(isAgentCore && (completedBackgroundWork || armed))) return null;

  const items = [];
  const citations = data.citations || [];
  const ready = citations.filter((citation) => citation.stage === "ready");
  const rejected = citations.filter((citation) => citation.stage === "evidence_rejected");
  const allReady = ready.length > 0 && ready.length === citations.length;

  if (allReady) {
    items.push({
      label: `${ready.length}/${citations.length} closed`,
      copy: "Every accepted citation was removed from the chase; no trade will receive another follow-up.",
    });
  } else {
    for (const citation of ready.slice(0, 2)) {
      items.push({
        label: `C${citation.citation_id} out of chase`,
        copy: `${titleCase(citation.trade)} evidence was accepted. Mettle removed this correction from every later follow-up.`,
      });
    }
  }

  for (const citation of rejected.slice(0, 1)) {
    const rejectionEvent = events.find(
      (event) => event.kind === "evidence_rejected" && String(event.citation_id) === String(citation.citation_id),
    );
    items.push({
      label: `C${citation.citation_id} re-requested`,
      copy: rejectionEvent?.detail || citation.evidence_note || "The submitted proof was incomplete, so Mettle requested the missing visible context.",
    });
  }

  const deadlineEvent = events.find((event) => event.kind === "deadline_escalation");
  if (deadlineEvent) {
    items.push({ label: "Deadline adapted", copy: deadlineEvent.detail });
  }

  const pendingJudgment = (data.judgments || []).find((judgment) => judgment.status === "pending");
  if (pendingJudgment && items.length < 4) {
    items.push({
      label: "Needs you",
      copy: `Mettle stopped instead of guessing: ${pendingJudgment.question}`,
    });
  }

  if (data.packet_status === "awaiting_approval" && items.length < 4) {
    items.push({
      label: "Packet ready",
      copy: "Mettle assembled the citation-to-evidence record and stopped before contractor release.",
    });
  }

  if (armed && !items.length) {
    items.push({
      label: "EventBridge armed",
      copy: `The next recovery checkpoint is scheduled${data.next_check_at ? ` for ${formatTimestamp(data.next_check_at)}` : ""}; this page can close.`,
    });
  }

  return {
    armed,
    mode: armed ? "EventBridge armed" : sampleHasAdvanced ? "Synthetic time compression" : "Background recovery brief",
    title: armed ? "Mettle is ready to work while you are away" : sampleHasAdvanced ? "Mettle worked while the contractor was away" : "Mettle worked while you were away",
    copy: sampleHasAdvanced
      ? "This disclosed sample compresses the background campaign. The authenticated run uses EventBridge Scheduler to wake the same open-only recovery policy."
      : armed
        ? "The authenticated campaign has a one-time checkpoint and will wake without this page remaining open."
        : "These results come from the current AgentCore campaign; only unresolved work remains in the chase.",
    items: items.slice(0, 4),
    actions: Number(data.metrics?.automated_actions || 0),
  };
}

function renderBackgroundBrief(data) {
  const brief = buildBackgroundBrief(data);
  elements.awayBriefing.hidden = !brief;
  if (!brief) {
    elements.awayBriefingList.replaceChildren();
    return;
  }
  elements.awayBriefing.classList.toggle("away-briefing--armed", brief.armed);
  elements.awayBriefingMode.textContent = brief.mode;
  elements.awayBriefingTitle.textContent = brief.armed
    ? "Background recovery is armed"
    : `${brief.actions} background action${brief.actions === 1 ? "" : "s"} handled`;
  elements.awayBriefingCopy.textContent = brief.armed
    ? `Next automatic checkpoint${data.next_check_at ? ` · ${formatTimestamp(data.next_check_at)}` : ""}`
    : "Open the activity record";
  elements.awayBriefingActions.textContent = String(brief.actions);
  elements.awayBriefingList.replaceChildren(...brief.items.map((item) => {
    const row = node("li", "away-briefing__item");
    row.append(node("strong", "", item.label), node("p", "", item.copy));
    return row;
  }));
}

function renderPacket(data) {
  const rows = data.citations.map((citation) => {
    const row = node("div", "packet-row");
    row.append(node("span", "packet-row__tag", `C${citation.citation_id}`));
    const copy = node("span", "packet-row__code", `${titleCase(citation.trade)} · ${citation.code_reference}`);
    const ready = citation.stage === "ready";
    copy.append(node("span", "packet-row__detail", ready
      ? "Accepted evidence · open the record for review"
      : correctionStatus(citation)[1]));
    row.append(copy);
    row.append(node("span", `packet-row__state${ready ? " packet-row__state--ready" : ""}`, ready ? "ACCEPTED" : "PENDING"));
    return row;
  });
  elements.packetList.replaceChildren(...rows);
  elements.packetReadiness.textContent = `${data.metrics.citations_ready} OF ${data.metrics.citations_total} READY`;

  const packetJudgment = data.judgments.find(
    (judgment) => judgment.status === "pending" && judgment.kind === "final_packet_approval",
  );
  elements.packetJudgment.replaceChildren(...(packetJudgment ? [renderJudgment(packetJudgment)] : []));

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
  } else {
    elements.packetPreview.replaceChildren();
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
  const waiting = data.workflow_status === "interrupted"
    || data.judgments.some(
      (judgment) => judgment.status === "pending" && judgment.kind !== "final_packet_approval",
    );
  const next = checkpoints.find((checkpoint) => checkpoint.date > data.as_of);
  const closed = open === 0;
  const expired = !next;
  const autonomous = data.execution_target === "agentcore" && data.automation_status === "scheduled";
  if (closed) {
    elements.clockTitle.textContent = "All citations closed · campaign standing down";
    elements.clockCopy.textContent = "Accepted evidence removed every citation from the chase plan. Mettle will send no further follow-ups.";
  } else if (waiting) {
    elements.clockTitle.textContent = `${open} open citation${open === 1 ? "" : "s"} · waiting for your decision`;
    elements.clockCopy.textContent = "The campaign is paused at a Strands judgment gate. Resolve it above before the next scheduled check.";
  } else if (autonomous) {
    elements.clockTitle.textContent = `Next automatic check · ${formatTimestamp(data.next_check_at)}`;
    elements.clockCopy.textContent = `${open} open correction${open === 1 ? "" : "s"}. Mettle will continue working even when this page is closed.`;
  } else if (expired) {
    elements.clockTitle.textContent = `${open} open citation${open === 1 ? "" : "s"} · deadline reached`;
    elements.clockCopy.textContent = "No later campaign checkpoint exists. Mettle will not invent outreach beyond the configured reinspection deadline.";
  } else {
    const nextDays = daysBetween(next.date, data.deadline_on);
    const behavior = nextDays <= 2 ? "frequent follow-up and ask you before changing the plan" : "deadline-aware follow-up to each open trade";
    elements.clockTitle.textContent = `Next: ${next.label} · ${formatDate(next.date)}`;
    elements.clockCopy.textContent = `${open} open citation${open === 1 ? "" : "s"}. Mettle will replan only those citations, then run ${behavior}.`;
  }
  elements.clockAction.disabled = autonomous || closed || waiting || expired || data.packet_status !== "blocked";
  elements.clockAction.textContent = autonomous ? "EventBridge armed" : waiting ? "Resolve decision to continue" : closed ? "Campaign stood down" : expired ? "Deadline reached" : "Compress to next checkpoint";
  elements.clockAction.hidden = data.source_mode === "workflow";
}

function render(data) {
  campaign = data;
  const isWorkflow = data.source_mode === "workflow";
  const isAgentCore = isWorkflow && data.execution_target === "agentcore";
  document.body.dataset.sourceMode = data.source_mode;
  elements.loading.hidden = true;
  elements.error.hidden = true;
  elements.dashboard.hidden = false;
  elements.workspaceNav.hidden = false;
  setWorkspaceView(activeWorkspaceView);
  elements.noticeId.textContent = data.notice_id;
  elements.workspaceNav.dataset.noticeId = data.notice_id;
  elements.navExitSample.hidden = isWorkflow;
  elements.property.textContent = data.property_label;
  const displayedDays = tourClockOverride ?? data.days_remaining;
  elements.days.textContent = String(Math.max(displayedDays, 0));
  elements.asOf.textContent = `AS OF ${formatDate(data.as_of).toUpperCase()}`;
  elements.progressLabel.textContent = `${data.metrics.citations_ready} / ${data.metrics.citations_total} CITATIONS READY`;
  elements.progressBar.style.width = `${(data.metrics.citations_ready / data.metrics.citations_total) * 100}%`;
  configureNextAction(data);
  renderBackgroundBrief(data);

  const [conditionLabel, conditionTone] = conditionFor(data);
  elements.conditionLabel.textContent = conditionLabel;
  elements.condition.className = `condition condition--${conditionTone}`;
  const criticalRecovery = data.priority === "critical" && data.packet_status !== "approved";
  elements.band.classList.toggle("command-band--critical", criticalRecovery);
  elements.campaignStrip.classList.toggle("campaign-strip--critical", criticalRecovery);
  elements.cadence.textContent = data.packet_status === "approved"
    ? "STANDING DOWN · PACKET APPROVED"
    : criticalRecovery ? "CRITICAL RECOVERY · CHECK-INS EVERY 4H" : "NORMAL FOLLOW-UP · DAILY CHECK-INS";
  if (data.packet_status === "approved") {
    elements.workspaceAgentState.innerHTML = '<i aria-hidden="true"></i> METTLE STOOD DOWN';
    elements.workspaceAgentTitle.textContent = "Packet approved. Follow-up stopped.";
    elements.workspaceAgentCopy.textContent = "All citations are closed; no trade remains in the chase.";
    elements.awsSchedulerProof.textContent = "Stood down · packet approved";
  } else if (data.source_mode === "workflow" && data.execution_target === "agentcore" && data.automation_status === "scheduled") {
    elements.workspaceAgentState.innerHTML = '<i aria-hidden="true"></i> METTLE IS WORKING';
    elements.workspaceAgentTitle.textContent = "Open-only follow-up is armed.";
    elements.workspaceAgentCopy.textContent = "Closed corrections leave the chase automatically.";
    elements.awsSchedulerProof.textContent = data.next_check_at
      ? `Armed · ${formatTimestamp(data.next_check_at)}`
      : "Armed · versioned checkpoint";
  } else {
    elements.workspaceAgentState.innerHTML = '<i aria-hidden="true"></i> METTLE IS READY';
    elements.workspaceAgentTitle.textContent = "No background checkpoint is active.";
    elements.workspaceAgentCopy.textContent = "Mettle will arm recovery only after contractor review.";
    elements.awsSchedulerProof.textContent = "No active checkpoint";
  }

  renderCorrectionSummary(data);
  renderJourney(data);
  elements.citations.replaceChildren(...data.citations.map((citation) => renderCitation(citation, data)));
  elements.events.replaceChildren(...data.events.map(renderEvent));
  renderAgentRun(data);
  renderProvenance(data);

  const pending = data.judgments.filter((item) => item.status === "pending");
  elements.judgmentCount.textContent = String(pending.length);
  const workspaceJudgments = pending.filter(
    (judgment) => !judgment.citation_id && judgment.kind !== "final_packet_approval",
  );
  elements.judgments.replaceChildren(...workspaceJudgments.map(renderJudgment));
  elements.judgments.hidden = workspaceJudgments.length === 0;

  renderMetrics(data.metrics);
  renderPacket(data);
  renderJudgeTour(data);
  elements.evidencePanel.hidden = false;
  elements.demoEvidence.hidden = isWorkflow;
  if (isWorkflow) elements.demoEvidence.open = false;
  elements.recoveryClock.hidden = !isWorkflow;
  elements.driverTag.textContent = isWorkflow ? "RECOVERY" : "SAMPLE";
  if (isWorkflow) renderRecoveryClock(data);
  const requestedCorrection = new URLSearchParams(window.location.search).get("correction");
  const explicitlySelected = activeWorkspaceView === "correction" && data.citations.find(c => String(c.citation_id) === requestedCorrection);
  const selectedCitation = explicitlySelected ? String(explicitlySelected.citation_id) : selectEvidenceCitation(data.citations, elements.photoCitation.value);
  const openEvidenceCitations = data.citations.filter((citation) => citation.stage !== "ready");
  elements.photoCitation.replaceChildren(...data.citations.map((citation) => {
    const option = node("option", "", evidenceOptionLabel(citation));
    option.value = citation.citation_id;
    option.disabled = false;
    return option;
  }));
  if ([...elements.photoCitation.options].some((option) => option.value === selectedCitation)) {
    elements.photoCitation.value = selectedCitation;
  }
  const hasOpenEvidence = openEvidenceCitations.length > 0;
  const canAssessPhoto = activePhotoEnabled() && hasOpenEvidence;
  elements.photoCitation.disabled = !isWorkflow || !data.citations.length;
  elements.photoFile.disabled = !isWorkflow || !hasOpenEvidence;
  elements.photoSubmit.disabled = !canAssessPhoto || !elements.photoFile.files?.length;
  elements.photoSubmit.title = canAssessPhoto
    ? "This live vision check consumes a small amount of AWS credit"
    : isWorkflow && !hasOpenEvidence
      ? "Every correction already has locked, accepted proof"
    : isWorkflow
      ? "Start Mettle with Bedrock or AgentCore enabled to assess real photos"
      : "Start a recovery to enable live Bedrock Vision";
  elements.photoModeNote.textContent = canAssessPhoto
    ? "LIVE BEDROCK VISION AVAILABLE · AWS CREDIT IS CONSUMED ONLY WHEN YOU SUBMIT"
    : isWorkflow && !hasOpenEvidence
      ? "ALL ACCEPTED PROOF IS LOCKED · START AN EXPLICIT REPLACEMENT WORKFLOW TO CHANGE IT"
    : isWorkflow
      ? "PHOTO CHECKING IS UNAVAILABLE IN THIS LOCAL RUN · START A SECURE RECOVERY TO USE IT"
      : "SAMPLE MODE · FIXTURES REPLAY RECORDED SYNTHETIC OUTCOMES · NO MODEL CALL";
  renderEvidenceRoute(data);
  if (isWorkflow) {
    const latestEvidence = [...data.evidence].reverse().find((item) => String(item.citation_id) === elements.photoCitation.value);
    elements.evidenceResult.hidden = !latestEvidence;
    if (latestEvidence) {
      renderEvidenceAssessment(latestEvidence);
    }
    const contractorDecisionRecorded = data.events.some(
      (event) => event.title === "Contractor decision recorded; graph resumed",
    );
    for (const button of elements.evidenceButtons) {
      const citationId = button.dataset.citation || "1";
      const citationLocked = data.citations.some(
        (citation) => String(citation.citation_id) === citationId && citation.stage === "ready",
      );
      const boundaryMissing = button.dataset.requiresDecision === "true"
        && !contractorDecisionRecorded
        && !hasApprovedEvidenceBoundary(data, citationId);
      button.disabled = citationLocked || boundaryMissing;
      button.title = citationLocked
        ? "Accepted proof is locked for this correction"
        : boundaryMissing ? "Resolve the evidence specification first" : "";
      button.textContent = button.dataset.sample === "panel_closeup_insufficient"
        ? "Assess close-up"
        : button.dataset.sample === "panel_wide_measured"
          ? "Assess wide photo"
          : button.dataset.sample === "framing_plates_complete"
            ? "Assess framing photo"
            : "Assess mechanical photo";
    }
  } else {
    if (elements.evidenceResult.dataset.mode === "live") elements.evidenceResult.hidden = true;
    for (const button of elements.evidenceButtons) {
      button.disabled = false;
      button.title = "Replay a recorded synthetic assessment without calling a model";
      button.textContent = button.dataset.sample === "panel_closeup_insufficient"
        ? "Replay rejection"
        : button.dataset.sample === "mechanical_access_wide"
          ? "Replay judgment gate"
          : "Replay acceptance";
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
    ? `${isAgentCore ? "AGENTCORE + " : ""}${data.intake_provider === "bedrock" ? "BEDROCK + " : ""}STRANDS · ${data.automation_status === "scheduled" ? "AUTONOMOUS CHECK ARMED" : data.workflow_status === "interrupted" ? "WAITING FOR YOU" : "GRAPH COMPLETE"}`
    : `${data.scenario_step} · ${stepLabels[data.scenario_step] || "RECOVERY RUN"}`;
  elements.advance.disabled = isWorkflow || data.scenario_complete || demoRunning;
  elements.advance.hidden = isWorkflow;
  elements.reset.disabled = demoRunning;
  elements.loadNotice.disabled = demoRunning;
  const advanceLabels = elements.advance.querySelectorAll("span");
  advanceLabels[0].textContent = isWorkflow ? "Real workflow active" : data.scenario_complete ? "Scenario complete" : demoRunning ? "Background recovery running" : "Compress background recovery";
  advanceLabels[1].textContent = isWorkflow ? "LIVE" : data.scenario_complete ? "DONE ✓" : demoRunning ? "WORKING…" : "TIME ▶";
  elements.loadNotice.querySelector("span").textContent = "NEW RECOVERY";
  elements.reset.querySelector("span").textContent = isWorkflow ? "OPEN SAMPLE" : "RESET SAMPLE";
  renderWorkbench(data);
}

async function loadCampaign() {
  elements.error.hidden = true;
  const params = new URLSearchParams(window.location.search);
  const workflowId = params.get("workflow");
  const workflowTarget = params.get("runtime") === "agentcore"
    ? "agentcore"
    : "local";
  try {
    if (workflowId) {
      sessionStorage.setItem("mettle_entry_selected", "workflow");
      setJudgeTourActive(false, { focus: false });
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
      const entry = sessionStorage.getItem("mettle_entry_selected");
      const directTour = params.get("tour") === "1" && entry !== "tour";
      if (directTour) sessionStorage.setItem("mettle_entry_selected", "tour");
      render(await request(directTour ? "/api/demo/reset" : "/api/campaign", directTour ? { method: "POST", body: "{}" } : {}));
      if (!entry && !judgeTourActive) openWelcomeChooser();
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
  elements.startBedrock.disabled = false;
  elements.startBedrock.title = "Build the correction list";
  elements.startAgentCore.disabled = false;
  elements.startAgentCore.title = accessToken
    ? "Build the correction list and pause for your review"
    : "Your setup will be saved while you sign in";
  document.querySelector("#secure-start-label").textContent = accessToken
    ? "Build my correction list"
    : "Sign in & build my correction list";
  document.querySelector("#secure-start-note").textContent = accessToken
    ? "NOTHING SENDS BEFORE YOUR REVIEW"
    : "YOUR SETUP IS SAVED DURING SIGN-IN";
  setSetupStep(setupStep);
}

elements.photoFile.addEventListener("change", () => {
  elements.photoError.hidden = true;
  elements.photoSubmit.disabled = !activePhotoEnabled() || !elements.photoFile.files?.length;
});

elements.photoCitation.addEventListener("change", () => {
  elements.photoFile.value = "";
  elements.photoError.hidden = true;
  elements.photoSubmit.disabled = true;
  renderEvidenceRoute(campaign);
  openCorrection(elements.photoCitation.value);
});

const recordDrafts = new Map();
let activeRecordDraft = null;
function renderEvidenceRoute(data) {
  const citation = data.citations.find((item) => String(item.citation_id) === elements.photoCitation.value);
  const record = data.source_mode === "workflow" && citation && citation.closure_route !== "photo_evidence" && Boolean(citation.closure_route);
  const key = record ? `${activeWorkflowId}:${citation.citation_id}` : null;
  if (activeRecordDraft !== key) {
    if (activeRecordDraft) recordDrafts.set(activeRecordDraft, {
      reference: elements.recordReference.value, reviewer: elements.recordReviewer.value,
      date: elements.recordDate.value, details: elements.recordDetails.value,
      confirmed: elements.recordConfirmed.checked,
    });
    const draft = recordDrafts.get(key);
    elements.recordForm.reset();
    if (draft) {
      elements.recordReference.value = draft.reference;
      elements.recordReviewer.value = draft.reviewer;
      elements.recordDate.value = draft.date;
      elements.recordDetails.value = draft.details;
      elements.recordConfirmed.checked = draft.confirmed;
    }
    activeRecordDraft = key;
    elements.recordError.hidden = true;
  }
  elements.recordForm.hidden = !record || citation.stage === "ready";
  elements.photoForm.hidden = Boolean(record) || citation?.stage === "ready";
  if (data.source_mode === "workflow") {
    const assessment = [...(data.evidence || [])].reverse().find((item) => String(item.citation_id) === elements.photoCitation.value);
    elements.evidenceResult.hidden = !assessment;
    if (assessment) renderEvidenceAssessment(assessment);
  }
  if (!record) return;
  const physical = citation.closure_route === "physical_reinspection";
  elements.recordTitle.textContent = physical ? "Record a completed inspection" : "Record a document review";
  elements.recordGuidance.textContent = physical
    ? "Arrange the visit with the authority outside Mettle. Only record a completed verification here—not a booking or a planned visit. Mettle does not contact the inspector."
    : "Review the original document against the notice. Save its reference and relevant findings here; keep the original available for the inspector. This is not a document upload or an AI verification.";
  elements.recordConfirmation.textContent = physical
    ? "I reviewed the completed inspector verification and confirm it addresses every required item. This is not merely a scheduled visit. I retain the original record."
    : "I reviewed the original document and confirm it addresses every required item. I retain the original source.";
  elements.recordRequirements.textContent = `Required: ${(citation.evidence_requirements || []).join("; ")}`;
  elements.recordSubmit.disabled = citation.stage === "ready" || Boolean(data.recovery_hold);
  elements.recordDate.max = new Date().toLocaleDateString("en-CA");
}

let recordSubmission = null;
let recordSubmitting = false;
elements.recordForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  if (recordSubmitting || !activeWorkflowId || !elements.recordForm.reportValidity()) return;
  const citation = campaign.citations.find((item) => String(item.citation_id) === elements.photoCitation.value);
  if (!citation || citation.closure_route === "photo_evidence") return;
  const body = JSON.stringify({citation_id: citation.citation_id, contractor_record: {
    route: citation.closure_route, reference: elements.recordReference.value.trim(),
    reviewer: elements.recordReviewer.value.trim(), reviewed_on: elements.recordDate.value,
    details: elements.recordDetails.value.trim(), confirmed: elements.recordConfirmed.checked,
  }});
  if (!recordSubmission || recordSubmission.body !== body || recordSubmission.workflow !== activeWorkflowId) {
    recordSubmission = {body, workflow: activeWorkflowId, key: crypto.randomUUID().replaceAll("-", "_")};
  }
  elements.recordError.hidden = true;
  recordSubmitting = true;
  setBusy(elements.recordSubmit, true);
  try {
    const root = activeWorkflowTarget === "agentcore" ? "/api/agentcore/workflows" : "/api/workflows";
    const envelope = await request(`${root}/${encodeURIComponent(activeWorkflowId)}/evidence`, {
      method: "POST", headers: {"Idempotency-Key": recordSubmission.key}, body,
    });
    campaign = workflowCampaign(envelope, activeWorkflowTarget);
    recordDrafts.delete(activeRecordDraft);
    activeRecordDraft = null;
    elements.recordForm.reset();
    recordSubmission = null;
    render(campaign);
    showToast("Contractor-reviewed source record saved. Original remains with you.");
  } catch (error) {
    showInlineWorkflowError(error, elements.recordError);
  } finally {
    recordSubmitting = false;
    setBusy(elements.recordSubmit, false);
    renderEvidenceRoute(campaign);
  }
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
        "Content-Type": "application/json",
        "Idempotency-Key": crypto.randomUUID().replaceAll("-", "_"),
      },
      body: JSON.stringify({ image_base64: base64Standard(await file.arrayBuffer()) }),
    });
    campaign = workflowCampaign(envelope, activeWorkflowTarget);
    render(campaign);
    const result = envelope.evidence.at(-1);
    showToast(result.status === "accepted"
      ? "Photo visibly satisfies every notice evidence requirement."
      : result.status === "manual_review"
        ? "The image is ambiguous. Mettle reserved the decision for you."
        : "Photo rejected with a specific re-request for the trade.");
    elements.photoFile.value = "";
  } catch (error) {
    showInlineWorkflowError(error, elements.photoError);
  } finally {
    setBusy(elements.photoSubmit, false);
    elements.photoSubmit.disabled = !activePhotoEnabled() || !elements.photoFile.files?.length;
    elements.photoSubmit.setAttribute("aria-busy", "false");
  }
});

async function runSampleUntilPause() {
  if (demoRunning || activeWorkflowId || campaign?.scenario_complete) return;
  demoRunning = true;
  animationSkipRequested = false;
  elements.tourSkip.hidden = !judgeTourActive;
  render(campaign);
  try {
    while (!campaign.scenario_complete) {
      const previousStep = campaign.scenario_step;
      const updated = await request("/api/demo/advance", {
        method: "POST",
        body: JSON.stringify({ idempotency_key: crypto.randomUUID().replaceAll("-", "_") }),
      });
      if (judgeTourActive && updated.scenario_step >= 3) tourClockOverride = null;
      campaign = updated;
      render(updated);
      if (updated.scenario_step === previousStep) {
        showToast("Mettle paused the campaign for your judgment.");
        if (judgeTourActive) elements.tourAction.focus();
        else document.querySelector(".judgment input")?.focus();
        break;
      }
      if (!updated.scenario_complete) {
        if (judgeTourActive && updated.scenario_step === 1) {
          await tourBeat(1600);
          stageTourClock(5, "FOLLOW-UP CHECKPOINT · TWO TRADES STILL OPEN");
          await tourBeat(1100);
        } else if (judgeTourActive && updated.scenario_step === 2) {
          stageTourClock(3, "DEADLINE CLOSING · OPEN-ONLY CHASE INTENSIFIES");
          await tourBeat(2200);
        } else {
          await tourBeat(1100);
        }
      }
    }
  } catch (error) {
    showError(error);
  } finally {
    demoRunning = false;
    tourClockOverride = null;
    finishTourDelay = null;
    elements.tourSkip.hidden = true;
    elements.tourSkip.textContent = "Skip animation";
    elements.tourSkip.disabled = false;
    if (campaign) {
      render(campaign);
      if (judgeTourActive) elements.tourAction.focus();
    }
  }
}

function tourBeat(milliseconds) {
  if (animationSkipRequested || window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
    return Promise.resolve();
  }
  return new Promise((resolve) => {
    let settled = false;
    const finish = () => {
      if (settled) return;
      settled = true;
      finishTourDelay = null;
      resolve();
    };
    const timer = window.setTimeout(finish, milliseconds);
    finishTourDelay = () => {
      window.clearTimeout(timer);
      finish();
    };
  });
}

function stageTourClock(days, cadence) {
  if (!judgeTourActive || animationSkipRequested) return;
  tourClockOverride = days;
  elements.days.textContent = String(days);
  elements.cadence.textContent = cadence;
  elements.days.classList.remove("tour-clock-transition");
  void elements.days.offsetWidth;
  elements.days.classList.add("tour-clock-transition");
}

elements.advance.addEventListener("click", runSampleUntilPause);

elements.reset.addEventListener("click", async () => {
  setBusy(elements.reset, true);
  try {
    if (activeWorkflowId) {
      activeWorkflowId = null;
      activeWorkflowTarget = "local";
    }
    window.history.replaceState({}, "", window.location.pathname);
    setWorkspaceView("recovery");
    render(await request("/api/demo/reset", { method: "POST", body: "{}" }));
    showToast("Recovery run reset to the opening campaign.");
  } catch (error) {
    showError(error);
  } finally {
    setBusy(elements.reset, false);
  }
});

for (const tab of elements.workspaceTabs) {
  tab.addEventListener("click", () => setWorkspaceView(tab.dataset.workspaceTab, { updateUrl: true }));
}

for (const button of elements.agentReceiptButtons) {
  button.addEventListener("click", () => setWorkspaceView("activity", { updateUrl: true, focusTab: true }));
}

elements.navNewRecovery?.addEventListener("click", () => {
  resetRecoverySetup();
  openRecoverySetup();
});
elements.navExitSample?.addEventListener("click", () => {
  setupReturnsToWelcome = false;
  openWelcomeChooser();
});

window.addEventListener("popstate", () => {
  const params = new URLSearchParams(window.location.search);
  if ((params.get("workflow") || null) !== activeWorkflowId
      || (activeWorkflowId && (params.get("runtime") || "local") !== activeWorkflowTarget)) {
    window.location.reload();
    return;
  }
  const tourFromUrl = new URLSearchParams(window.location.search).get("tour") === "1";
  setJudgeTourActive(tourFromUrl, { focus: false });
  if (!tourFromUrl) setWorkspaceView(workspaceViewFromUrl());
  if (campaign) {
    const selected = globalThis.MettleWorkbench.selectedCitation(campaign, params.get("correction"));
    if (selected) elements.photoCitation.value = String(selected.citation_id);
    renderWorkbench(campaign);
  }
});

elements.nextActionButton.addEventListener("click", () => nextActionHandler?.());
elements.tourAction.addEventListener("click", () => tourActionHandler?.());
elements.tourSecondary.addEventListener("click", () => tourSecondaryHandler?.());
elements.tourSkip.addEventListener("click", () => {
  animationSkipRequested = true;
  elements.tourSkip.textContent = "Finishing…";
  elements.tourSkip.disabled = true;
  finishTourDelay?.();
});
elements.tourExit.addEventListener("click", () => {
  sessionStorage.setItem("mettle_entry_selected", "sample");
  setJudgeTourActive(false, { updateUrl: true });
});

elements.home.addEventListener("click", (event) => {
  event.preventDefault();
  setupReturnsToWelcome = false;
  if (elements.noticeDialog.open) elements.noticeDialog.close();
  elements.resumeCurrentEntry.hidden = !(activeWorkflowId || judgeTourActive);
  elements.resumeCurrentEntry.querySelector("strong").textContent = judgeTourActive ? "Return to Judge mode" : "Return to current recovery";
  elements.resumeCurrentEntry.querySelector("span:last-child").textContent = judgeTourActive
    ? "Close this chooser without leaving the guided evaluator path."
    : "Close this chooser without changing the recovery already in progress.";
  openWelcomeChooser();
});

elements.startRecoveryEntry.addEventListener("click", () => {
  setJudgeTourActive(false, { updateUrl: true, focus: false });
  elements.welcomeDialog.close();
  resetRecoverySetup();
  openRecoverySetup({ returnToWelcome: true });
});

elements.startTourEntry.addEventListener("click", async () => {
  sessionStorage.setItem("mettle_entry_selected", "tour");
  setBusy(elements.startTourEntry, true);
  elements.welcomeDialog.close();
  window.history.replaceState({}, "", window.location.pathname);
  setWorkspaceView("recovery");
  activeWorkflowId = null;
  activeWorkflowTarget = "local";
  try {
    campaign = await request("/api/demo/reset", { method: "POST", body: "{}" });
    setJudgeTourActive(true, { updateUrl: true, focus: false });
    render(campaign);
  } catch (error) {
    showError(error);
  } finally {
    setBusy(elements.startTourEntry, false);
  }
  elements.tourTitle.focus();
});

elements.trySampleEntry.addEventListener("click", async () => {
  sessionStorage.setItem("mettle_entry_selected", "sample");
  setBusy(elements.trySampleEntry, true);
  elements.welcomeDialog.close();
  setJudgeTourActive(false, { focus: false });
  window.history.replaceState({}, "", window.location.pathname);
  setWorkspaceView("recovery");
  activeWorkflowId = null;
  activeWorkflowTarget = "local";
  try {
    render(await request("/api/demo/reset", { method: "POST", body: "{}" }));
  } catch (error) {
    showError(error);
  } finally {
    setBusy(elements.trySampleEntry, false);
  }
  elements.nextActionButton.focus();
});

elements.resumeCurrentEntry.addEventListener("click", () => {
  elements.welcomeDialog.close();
  if (judgeTourActive) elements.tourAction.focus();
  else elements.nextActionButton.focus();
});

elements.setupNext.addEventListener("click", () => {
  if (!validateSetupStep()) return;
  if (setupStep === 2) updateLaunchReview();
  setSetupStep(setupStep + 1);
  const pane = elements.setupPanes.find((item) => Number(item.dataset.setupPane) === setupStep);
  pane?.querySelector("input, textarea, button")?.focus();
});

elements.workflowAsOf.addEventListener("input", () => {
  elements.workflowDateError.hidden = true;
  elements.noticeText.removeAttribute("aria-invalid");
});

elements.noticeText.addEventListener("input", () => {
  noticeImportVersion += 1;
  elements.workflowDateError.hidden = true;
  elements.noticeText.removeAttribute("aria-invalid");
});

elements.noticeFile.addEventListener("change", async () => {
  const importVersion = ++noticeImportVersion;
  const file = elements.noticeFile.files?.[0];
  if (!file) {
    elements.noticeFileStatus.textContent = "No file selected";
    return;
  }
  const fileLimit = elements.noticeOcr?.checked ? 3_500_000 : 5_000_000;
  if (file.size > fileLimit) {
    elements.noticeFile.value = "";
    elements.noticeFileStatus.textContent = `File is larger than ${fileLimit / 1_000_000} MB`;
    return;
  }
  elements.workflowError.hidden = true;
  elements.noticeFile.disabled = true;
  elements.noticeFileStatus.textContent = `Reading ${file.name}…`;
  try {
    const useOcr = Boolean(elements.noticeOcr?.checked);
    const payload = await request(useOcr ? "/api/agentcore/notices/ocr" : "/api/notices/text", {
      method: "POST",
      body: JSON.stringify({
        filename: file.name,
        file_base64: base64Standard(await file.arrayBuffer()),
      }),
    });
    if (importVersion !== noticeImportVersion || !elements.noticeDialog.open || setupStep !== 1) {
      elements.noticeFileStatus.textContent = "Import discarded because you edited or left the report. Select the file again if needed.";
      return;
    }
    workflowCreateKey = null;
    elements.noticeText.value = payload.text;
    if (elements.noticeOcrReview) {
      elements.noticeOcrReview.hidden = !useOcr;
      elements.noticeOcrConfirm.checked = false;
    }
    elements.noticeFileStatus.textContent = `${file.name} · ${payload.text.split(/\r?\n/).filter(Boolean).length} lines ready`;
    elements.noticeText.focus();
  } catch (error) {
    showInlineWorkflowError(error, elements.workflowError);
    elements.noticeFileStatus.textContent = "Could not read this report";
  } finally {
    elements.noticeFile.disabled = false;
    elements.noticeFile.value = "";
  }
});

elements.noticeOcr.addEventListener("change", () => {
  elements.noticeFile.accept = elements.noticeOcr.checked
    ? "image/jpeg,image/png,application/pdf,.jpg,.jpeg,.png,.pdf" : "application/pdf,text/plain,.pdf,.txt";
  elements.noticeFile.value = "";
  elements.noticeFileStatus.textContent = elements.noticeOcr.checked ? "Choose one photo or scanned page · sign-in required" : "No file selected";
});
document.querySelector("#notice-ocr-signin").addEventListener("click", () => beginLogin().catch(error => showInlineWorkflowError(error, elements.workflowError)));

elements.setupBack.addEventListener("click", () => {
  setSetupStep(setupStep - 1);
  const pane = elements.setupPanes.find((item) => Number(item.dataset.setupPane) === setupStep);
  pane?.querySelector("input, textarea, button")?.focus();
});

document.querySelector("#revise-source-button").addEventListener("click", () => {
  // Never mutate authority text inside an existing recovery or release its gate.
  // A corrected source starts a distinct run; retain the user's report/contacts.
  workflowCreateKey = null;
  workflowCreateProvider = null;
  correctionReviewKey = null;
  elements.outreachConsent.checked = false;
  elements.workflowError.hidden = true;
  setSetupStep(1);
  elements.noticeText.focus();
  showToast("Recheck the source report. Building again creates a replacement; the previous plan stays paused.");
});

elements.loadNotice.addEventListener("click", () => {
  resetRecoverySetup();
  openRecoverySetup();
});

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
  const executionTarget = event.submitter === elements.startAgentCore ? "agentcore" : "local";
  const provider = executionTarget === "agentcore" || bedrockEnabled ? "bedrock" : "local";
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
        as_of: recoveryWorkingDate(),
        roster: buildRoster(),
      }),
    });
    activeWorkflowId = envelope.workflow_id;
    activeWorkflowTarget = executionTarget;
    const targetQuery = executionTarget === "agentcore" ? "&runtime=agentcore" : "";
    window.history.replaceState({}, "", `${window.location.pathname}?workflow=${encodeURIComponent(activeWorkflowId)}${targetQuery}`);
    setWorkspaceView("recovery");
    const workflowView = workflowCampaign(envelope, executionTarget);
    render(workflowView);
    sessionStorage.setItem("mettle_entry_selected", "recovery");
    sessionStorage.removeItem("mettle_recovery_draft");
    workflowCreateKey = null;
    workflowCreateProvider = null;
    if (workflowView.correction_review_required) {
      openPendingCorrectionReview(workflowView);
      showToast("Correction list ready. Nothing has been sent; review each assignment and proof request next.");
    } else {
      setupReturnsToWelcome = false;
      elements.noticeDialog.close();
    }
  } catch (error) {
    showInlineWorkflowError(error, elements.workflowError);
  } finally {
    setBusy(elements.startWorkflow, false);
    setBusy(elements.startBedrock, false);
    elements.startBedrock.disabled = !bedrockEnabled;
    elements.startBedrock.setAttribute("aria-busy", "false");
    setBusy(elements.startAgentCore, false);
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
    const sent = envelope.snapshot.deliveries.filter((delivery) => delivery.status === "sent").length;
    showToast(sent
      ? `Recovery started. Mettle sent ${sent} job update${sent === 1 ? "" : "s"}.${campaign.automation_status === "scheduled" ? " The next check is scheduled." : " No background checkpoint is active."}`
      : `Recovery started. Mettle prepared ${envelope.snapshot.deliveries.length} outreach action${envelope.snapshot.deliveries.length === 1 ? "" : "s"}.${campaign.automation_status === "scheduled" ? " The next check is scheduled." : " No background checkpoint is active."}`);
  } catch (error) {
    showInlineWorkflowError(error, elements.workflowError);
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
    if (!activeWorkflowId) {
      const assessment = recordedEvidenceAssessments[button.dataset.sample];
      if (!assessment) return;
      renderEvidenceAssessment(assessment);
      elements.evidenceResult.scrollIntoView({ behavior: "smooth", block: "nearest" });
      showToast("Recorded synthetic assessment replayed. No model or AWS service was called.");
      return;
    }
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
    setBusy(elements.clockAction, false);
    elements.clockAction.disabled = campaign?.workflow_status === "interrupted";
  }
});

elements.packetAction.addEventListener("click", async () => {
  if (!activeWorkflowId) {
    if (campaign?.packet_status === "approved") {
      await downloadDemoPacket();
    }
    return;
  }
  const workflowRoot = activeWorkflowTarget === "agentcore"
    ? "/api/agentcore/workflows"
    : "/api/workflows";
  if (campaign?.packet_status === "approved") {
    try {
      if (activeWorkflowTarget === "agentcore") {
      const link = await request(`${workflowRoot}/${encodeURIComponent(activeWorkflowId)}/packet-url`);
      window.location.assign(link.download_url);
      } else {
      window.location.assign(`${workflowRoot}/${encodeURIComponent(activeWorkflowId)}/packet.pdf`);
      }
    } catch (error) {
      showError(error);
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
    setBusy(elements.packetAction, false);
    elements.packetAction.disabled = campaign?.packet_status === "awaiting_approval";
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

elements.retry.addEventListener("click", () => retryHandler());
for (const toggle of elements.themeToggles) {
  toggle.addEventListener("click", () => {
    const nextTheme = document.documentElement.dataset.theme === "light" ? "dark" : "light";
    applyTheme(nextTheme, { persist: true });
  });
}
systemTheme.addEventListener("change", () => {
  if (!savedTheme()) applyTheme(resolveTheme());
});
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
  if (recoveryDraftRestored) {
    setupReturnsToWelcome = false;
    if (elements.welcomeDialog.open) elements.welcomeDialog.close();
    if (!elements.noticeDialog.open) elements.noticeDialog.showModal();
    window.setTimeout(() => {
      const pane = elements.setupPanes.find((item) => Number(item.dataset.setupPane) === setupStep);
      pane?.querySelector("input, textarea, button")?.focus();
    }, 0);
  }
});

window.setInterval(async () => {
  if (
    document.visibilityState !== "visible"
    || document.activeElement?.matches("input, textarea, select")
    || !activeWorkflowId
    || activeWorkflowTarget !== "agentcore"
    || campaign?.automation_status !== "scheduled"
  ) return;
  try {
    await loadCampaign();
  } catch (_error) {
    // The normal error banner and manual retry remain the user-facing recovery.
  }
}, 10_000);
