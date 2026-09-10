const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");
const source = fs.readFileSync("src/mettle/web/static/app.js", "utf8");

test("oversized photo gives actionable feedback before a paid request", () => {
  let change;
  const elements = {photoFile: {files: [{size: 3_500_001}], addEventListener: (_, fn) => {change=fn;}}, photoError: {}, photoSubmit: {}};
  const context = vm.createContext({elements, maxPhotoBytes:3_500_000, activePhotoEnabled:()=>true});
  vm.runInContext(source.slice(source.indexOf('elements.photoFile.addEventListener("change"'), source.indexOf('elements.photoCitation.addEventListener("change"')), context);
  change();
  assert.equal(elements.photoSubmit.disabled, true);
  assert.equal(elements.photoError.hidden, false);
  assert.match(elements.photoError.textContent, /3.5 MB/);
  elements.photoFile.files[0].size = 3_500_000;
  change();
  assert.equal(elements.photoSubmit.disabled, false);
  assert.equal(elements.photoError.hidden, true);
});

test("cadence label follows actual scheduling state without invented frequency", () => {
  const elements = {cadence:{}};
  const context = vm.createContext({elements, criticalRecovery:false, data:{packet_status:"blocked", automation_status:"scheduled", judgments:[]}});
  const start = source.indexOf('  elements.cadence.textContent = data.packet_status');
  vm.runInContext(source.slice(start, source.indexOf('  if (data.packet_status', start)), context);
  assert.match(elements.cadence.textContent, /FOLLOW-UP SCHEDULED/);
  context.data.automation_status = "paused";
  vm.runInContext(source.slice(start, source.indexOf('  if (data.packet_status', start)), context);
  assert.match(elements.cadence.textContent, /FOLLOW-UP PAUSED/);
  context.criticalRecovery = true;
  context.data.judgments = [{status:"pending"}];
  vm.runInContext(source.slice(start, source.indexOf('  if (data.packet_status', start)), context);
  assert.match(elements.cadence.textContent, /CRITICAL .* DECISION PENDING/);
});

test("sample packet failure remains in the recovery and shows a retryable error", async () => {
  let reported;
  const context = vm.createContext({
    fetch: async () => ({ok:false}),
    showError: error => {reported = error.message;},
  });
  vm.runInContext(source.slice(source.indexOf("async function downloadDemoPacket("), source.indexOf("async function resolveDeadlineAndContinue(")), context);
  await context.downloadDemoPacket();
  assert.match(reported, /approved recovery is still saved/);
});

function element(tag, className, text) {
  return {
    tag, className, text, children: [], dataset: {}, value: "",
    append(...items) {
      this.children.push(...items);
      if (this.tag === "select") {
        const selected = items.find((item) => item.selected);
        if (selected) this.value = selected.value;
      }
    },
    replaceChildren(...items) { this.children = items; },
    setAttribute() {}, addEventListener() {},
  };
}

test("correction review preserves document and inspection routes and uses saved recipients", () => {
  const list = element("div");
  const context = vm.createContext({node: element, elements: {correctionReviewList: list}, buildRoster: () => [], maskedPhone: () => "private number"});
  vm.runInContext(source.slice(source.indexOf("function renderCorrectionReview("), source.indexOf("function buildCorrectionReviewPayload(")), context);
  for (const route of ["photo_evidence", "document_evidence", "physical_reinspection"]) {
    context.renderCorrectionReview({
      review_citations: [{citation_id: "1", trade: "general", closure_route: route, evidence_requirements: ["Required record"]}],
      review_recipients: [{trade: "general", name: "Saved Contractor", phone_suffix: "0123"}],
    });
    const flat = (item) => [item, ...item.children.flatMap(flat)];
    const nodes = flat(list);
    assert.equal(nodes.find((item) => "reviewRoute" in item.dataset).value, route);
    assert.ok(nodes.some((item) => item.text === "Saved Contractor · ••• ••• 0123"));
  }
});

test("an in-flight report import cannot overwrite an edited draft", async () => {
  let handler;
  let resolve;
  const response = new Promise((done) => { resolve = done; });
  const elements = {
    noticeOcr: {checked:false, addEventListener() {}},
    noticeFile: {files: [{name: "notice.txt", size: 20, arrayBuffer: async () => new ArrayBuffer(0)}], addEventListener: (_, fn) => {handler = fn;}},
    noticeText: {value: "Original", focus() {}}, noticeFileStatus: {}, workflowError: {}, noticeDialog: {open: true},
  };
  const context = vm.createContext({elements, document:{querySelector:()=>({addEventListener(){}})}, noticeImportVersion: 0, setupStep: 1, request: () => response, base64Standard: () => "", showInlineWorkflowError() {}});
  vm.runInContext(source.slice(source.indexOf('elements.noticeFile.addEventListener("change"'), source.indexOf('elements.setupBack.addEventListener')), context);
  const pending = handler();
  context.noticeImportVersion++;
  elements.noticeText.value = "Contractor edited this";
  resolve({text: "Imported report"});
  await pending;
  assert.equal(elements.noticeText.value, "Contractor edited this");
  assert.match(elements.noticeFileStatus.textContent, /discarded/);
  assert.equal(elements.noticeFile.disabled, false);
});

test("uncertain recovery visibly takes priority over the normal approval action", () => {
  const elements = Object.fromEntries(["nextAction", "nextActionEyebrow", "nextActionMeta", "nextActionTitle", "nextActionCopy", "nextActionButton"].map((key) => [key, {dataset: {}, classList: {toggle() {}}}]));
  const context = vm.createContext({elements, activeWorkspaceView: "evidence", setWorkspaceView() {}});
  vm.runInContext(source.slice(source.indexOf("function configureNextAction("), source.indexOf("function renderJourney(")), context);
  context.configureNextAction({source_mode: "workflow", recovery_hold: true, correction_review_required: true, judgments: [], citations: [], packet_status: "blocked"});
  assert.equal(elements.nextAction.hidden, false);
  assert.match(elements.nextActionTitle.textContent, /held/);
  assert.equal(elements.nextActionButton.textContent, "View saved activity");
  assert.match(elements.nextActionCopy.textContent, /operator/);
});

test("each non-photo route guides the contractor to a source record, never a photo", () => {
  for (const route of ["document_evidence", "physical_reinspection"]) {
    const elements = Object.fromEntries(["nextAction", "nextActionEyebrow", "nextActionMeta", "nextActionTitle", "nextActionCopy", "nextActionButton"].map((key) => [key, {dataset: {}, classList: {toggle() {}}}]));
    const context = vm.createContext({elements, activeWorkspaceView: "recovery", activePhotoEnabled: () => true});
    vm.runInContext(source.slice(source.indexOf("function configureNextAction("), source.indexOf("function renderJourney(")), context);
    context.configureNextAction({source_mode: "workflow", judgments: [], citations: [{citation_id: "2", stage: "awaiting_evidence", closure_route: route}], packet_status: "blocked"});
    assert.match(elements.nextActionButton.textContent, /Record (document review|inspection outcome)/);
    assert.doesNotMatch(elements.nextActionButton.textContent, /photo/i);
  }
});

test("record drafts do not bleed across corrections and accepted records are read-only", () => {
  const keys = ["photoCitation", "recordForm", "photoForm", "recordTitle", "recordGuidance", "recordRequirements", "recordReference", "recordReviewer", "recordDate", "recordDetails", "recordConfirmed", "recordConfirmation", "recordSubmit", "recordError", "evidenceResult"];
  const elements = Object.fromEntries(keys.map((key) => [key, {value: "", checked: false}]));
  elements.recordForm.reset = () => {
    for (const key of ["recordReference", "recordReviewer", "recordDate", "recordDetails"]) elements[key].value = "";
    elements.recordConfirmed.checked = false;
  };
  let shown;
  elements.photoSubmit = {};
  elements.photoFile = {};
  const context = vm.createContext({elements, activePhotoEnabled:()=>true, activeWorkflowId: "test", renderEvidenceAssessment: (a) => {shown = a;}});
  vm.runInContext(source.slice(source.indexOf("const recordDrafts ="), source.indexOf("let recordSubmission =")), context);
  const data = {source_mode: "workflow", citations: [
    {citation_id: "1", closure_route: "document_evidence", stage: "awaiting_evidence"},
    {citation_id: "2", closure_route: "physical_reinspection", stage: "awaiting_evidence"},
  ], evidence: []};
  elements.photoCitation.value = "1";
  context.renderEvidenceRoute(data);
  elements.recordReference.value = "Document one";
  elements.photoCitation.value = "2";
  context.renderEvidenceRoute(data);
  assert.equal(elements.recordReference.value, "");
  assert.match(elements.recordGuidance.textContent, /not a booking/);
  elements.photoCitation.value = "1";
  context.renderEvidenceRoute(data);
  assert.equal(elements.recordReference.value, "Document one");
  data.citations[0].stage = "ready";
  data.evidence = [{citation_id: "1", status: "accepted"}];
  context.renderEvidenceRoute(data);
  assert.equal(elements.recordForm.hidden, true);
  assert.equal(shown.citation_id, "1");
});
