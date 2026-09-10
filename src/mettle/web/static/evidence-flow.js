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
    const year = match[1] || (Number(match[6]) < 100 ? 2000 + Number(match[6]) : Number(match[6]));
    const iso = `${year}-${String(match[2] || match[4]).padStart(2, "0")}-${String(match[3] || match[5]).padStart(2, "0")}`;
    const parsed = new Date(`${iso}T00:00:00Z`);
    return Number.isFinite(parsed.getTime()) && parsed.toISOString().slice(0, 10) === iso ? iso : "";
  }

  function noticeDeadline(noticeText) {
    const text = String(noticeText || "");
    // Match after the deadline label, never an unrelated date earlier on its line.
    const explicit = text.match(/(?:re[- ]?inspection\s+(?:required by|deadline|target|date|due|on)|correction deadline|correct by)\s*:?\s*([^\n]+)/i);
    if (explicit) return dateFromLine(explicit[1]);
    const relative = text.match(/re[- ]?inspection\s+(?:required\s+)?within\s+(\d{1,3})\s+(?:calendar\s+)?days\b/i);
    const issued = noticeInspectionDate(text);
    if (!relative || !issued || Number(relative[1]) < 1 || Number(relative[1]) > 365) return "";
    const result = new Date(`${issued}T00:00:00Z`);
    result.setUTCDate(result.getUTCDate() + Number(relative[1]));
    return result.toISOString().slice(0, 10);
  }

  function noticeInspectionDate(noticeText) {
    const match = String(noticeText || "").match(/^(?:inspection date|date of inspection|inspection performed|date issued|issued(?: on)?|date)\s*:?\s*([^\n]+)/im);
    return dateFromLine(match?.[1]);
  }

  function recoveryDateError(noticeText, workingDate) {
    const issued = noticeInspectionDate(noticeText);
    const deadline = noticeDeadline(noticeText);
    if (!workingDate) return "";
    if (issued && workingDate < issued) {
      return `The inspection date (${issued}) is after the recovery start date (${workingDate}). Check the date in your report.`;
    }
    if (!deadline) return "";
    return workingDate >= deadline
      ? `The reinspection deadline (${deadline}) has been reached for this recovery start date (${workingDate}). Check the deadline in your report.`
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
