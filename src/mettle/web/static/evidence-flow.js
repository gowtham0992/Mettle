(function exposeEvidenceFlow(root) {
  function evidenceOptionLabel(citation) {
    const subject = citation.code_reference || citation.trade || "correction";
    const status = citation.stage === "ready"
      ? "accepted"
      : citation.stage === "evidence_rejected"
        ? "replace proof"
        : citation.stage === "needs_judgment" ? "needs decision" : "needs proof";
    return `C${citation.citation_id} · ${subject} · ${status}`;
  }

  function selectEvidenceCitation(citations, currentCitationId) {
    const open = citations.filter((citation) => citation.stage !== "ready");
    const current = citations.find(
      (citation) => String(citation.citation_id) === String(currentCitationId || ""),
    );
    const currentIsOpen = open.find(
      (citation) => String(citation.citation_id) === String(currentCitationId || ""),
    );
    return String(currentIsOpen?.citation_id || open[0]?.citation_id || current?.citation_id || citations[0]?.citation_id || "");
  }

  function dateFromLine(line) {
    if (!line) return "";
    const match = line.match(/\b(\d{4})-(\d{1,2})-(\d{1,2})\b|\b(\d{1,2})\/(\d{1,2})\/(\d{2,4})\b/);
    if (!match) return "";
    if (match[1]) {
      return `${match[1]}-${String(match[2]).padStart(2, "0")}-${String(match[3]).padStart(2, "0")}`;
    }
    const year = Number(match[6]) < 100 ? 2000 + Number(match[6]) : Number(match[6]);
    return `${year}-${String(match[4]).padStart(2, "0")}-${String(match[5]).padStart(2, "0")}`;
  }

  function noticeDeadline(noticeText) {
    const line = String(noticeText || "").split(/\r?\n/).find(
      (value) => /reinspection|correction deadline/i.test(value),
    );
    return dateFromLine(line);
  }

  function noticeInspectionDate(noticeText) {
    const line = String(noticeText || "").split(/\r?\n/).find(
      (value) => /inspection date|issued(?: on)?/i.test(value) && !/reinspection/i.test(value),
    );
    return dateFromLine(line);
  }

  function recoveryDateError(noticeText, workingDate) {
    const issued = noticeInspectionDate(noticeText);
    const deadline = noticeDeadline(noticeText);
    if (!workingDate) return "";
    if (issued && workingDate < issued) {
      return `The working date cannot be before the ${issued} inspection date.`;
    }
    if (!deadline) return "";
    return workingDate >= deadline
      ? `The working date must be before the ${deadline} reinspection deadline.`
      : "";
  }

  function normalizedPhone(value) {
    const raw = String(value || "").trim();
    const digits = raw.replace(/\D/g, "");
    if (digits.length === 10) return `+1${digits}`;
    if (digits.length === 11 && digits.startsWith("1")) return `+${digits}`;
    if (raw.startsWith("+") && digits.length >= 8 && digits.length <= 15) return `+${digits}`;
    return raw.replace(/[\s().-]/g, "");
  }

  const api = { evidenceOptionLabel, normalizedPhone, noticeDeadline, noticeInspectionDate, recoveryDateError, selectEvidenceCitation };
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  root.MettleEvidenceFlow = api;
}(typeof globalThis === "undefined" ? this : globalThis));
