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

  const api = { evidenceOptionLabel, selectEvidenceCitation };
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  root.MettleEvidenceFlow = api;
}(typeof globalThis === "undefined" ? this : globalThis));
