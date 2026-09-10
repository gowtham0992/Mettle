const test = require("node:test");
const assert = require("node:assert/strict");

const {
  evidenceOptionLabel,
  normalizedPhone,
  noticeDeadline,
  noticeInspectionDate,
  recoveryDateError,
  selectEvidenceCitation,
} = require("../src/mettle/web/static/evidence-flow.js");

const citations = [
  { citation_id: "1", code_reference: "NEC 110.26", trade: "general", stage: "ready" },
  { citation_id: "2", code_reference: "IRC R602.6", trade: "general", stage: "awaiting_evidence" },
  { citation_id: "3", code_reference: "IMC 304.10", trade: "general", stage: "awaiting_evidence" },
];

test("advances from an accepted citation to the next correction needing proof", () => {
  assert.equal(selectEvidenceCitation(citations, "1"), "2");
});

test("keeps the current citation selected when its proof was rejected", () => {
  const rejected = citations.map((citation) => (
    citation.citation_id === "1" ? { ...citation, stage: "evidence_rejected" } : citation
  ));
  assert.equal(selectEvidenceCitation(rejected, "1"), "1");
});

test("labels generic citations with their code and evidence status", () => {
  assert.equal(evidenceOptionLabel(citations[0]), "C1 · NEC 110.26 · accepted");
  assert.equal(evidenceOptionLabel(citations[1]), "C2 · IRC R602.6 · needs proof");
});

test("extracts common municipal deadline formats", () => {
  assert.equal(noticeDeadline("Reinspection deadline: 8/28/26"), "2026-08-28");
  assert.equal(noticeDeadline("Reinspection on 2026-09-14"), "2026-09-14");
  assert.equal(noticeInspectionDate("Inspection date: 09/03/2026"), "2026-09-03");
});

test("rejects a working date on or after the reinspection deadline", () => {
  const notice = "Inspection date: 09/03/2026\nCorrections must be completed before reinspection on 09/14/2026.";
  assert.match(recoveryDateError(notice, "2026-09-02"), /inspection date .* is after .*2026-09-02/);
  assert.equal(recoveryDateError(notice, "2026-09-13"), "");
  assert.match(recoveryDateError(notice, "2026-09-14"), /deadline .* has been reached/);
  assert.match(recoveryDateError(notice, "2026-09-15"), /deadline .* has been reached/);
});

test("normalizes the phone formats a US contractor is likely to type", () => {
  assert.equal(normalizedPhone("(303) 555-0100"), "+13035550100");
  assert.equal(normalizedPhone("303-555-0100"), "+13035550100");
  assert.equal(normalizedPhone("1 303 555 0100"), "+13035550100");
  assert.equal(normalizedPhone("+44 20 7946 0958"), "+442079460958");
});

test("relative deadlines use the issue date, never the first date on the reinspection line", () => {
  const notice = "Date 08/07/2026 … Reinspection required within 10 days";
  assert.equal(noticeInspectionDate(notice), "2026-08-07");
  assert.equal(noticeDeadline(notice), "2026-08-17");
  assert.equal(noticeDeadline("Date: 12/29/2026\nRe-inspection required within 10 calendar days"), "2027-01-08");
  assert.equal(noticeDeadline("Date: 08/07/2026\nReinspection within 10 business days"), "");
  assert.equal(noticeDeadline("Date: 08/07/2026 … Reinspection required by 08/20/2026"), "2026-08-20");
  assert.equal(noticeDeadline(`Reinspection deadline: 2026-09-20\nOriginal report\n${notice}`), "2026-09-20");
  assert.equal(noticeDeadline("Date: 02/31/2026\nReinspection required within 10 days"), "");
  assert.equal(noticeDeadline("Reinspection deadline: 2026-13-01"), "");
});
