from __future__ import annotations

import re
from datetime import date

from mettle.domain import Citation, InspectionNotice, Trade


class NoticeParseError(ValueError):
    """Raised when a notice cannot satisfy Mettle's intake contract."""


_HEADER_LABELS = {
    "NOTICE ID": "notice_id",
    "ISSUED": "issued_on",
    "REINSPECTION DEADLINE": "reinspection_due_on",
    "PROPERTY": "property_label",
}


def parse_notice(text: str) -> InspectionNotice:
    """Parse Mettle's synthetic notice format without interpreting code."""
    normalized = text.replace("\r\n", "\n").strip()
    if not normalized:
        raise NoticeParseError("notice is empty")

    header: dict[str, str] = {}
    for label, field_name in _HEADER_LABELS.items():
        match = re.search(rf"(?m)^{re.escape(label)}:\s*(.+?)\s*$", normalized)
        if match:
            header[field_name] = match.group(1).strip()

    missing_headers = [field for field in _HEADER_LABELS.values() if field not in header]
    if missing_headers:
        raise NoticeParseError(f"missing notice fields: {', '.join(missing_headers)}")

    blocks = re.findall(
        r"(?ms)^CITATION\s+([^\n]+)\n(.*?)^END CITATION\s*$",
        normalized,
    )
    if not blocks:
        raise NoticeParseError("notice contains no citation blocks")

    citations = [_parse_citation(citation_id.strip(), body) for citation_id, body in blocks]

    try:
        issued_on = date.fromisoformat(header["issued_on"])
        due_on = date.fromisoformat(header["reinspection_due_on"])
    except ValueError as exc:
        raise NoticeParseError("notice dates must use YYYY-MM-DD") from exc

    if due_on < issued_on:
        raise NoticeParseError("reinspection deadline cannot precede issue date")

    return InspectionNotice(
        notice_id=header["notice_id"],
        issued_on=issued_on,
        reinspection_due_on=due_on,
        property_label=header["property_label"],
        citations=citations,
    )


def _parse_citation(citation_id: str, body: str) -> Citation:
    fields: dict[str, str] = {}
    for label in ("CODE", "TRADE", "FINDING", "EVIDENCE"):
        match = re.search(rf"(?m)^{label}:\s*(.+?)\s*$", body)
        if match:
            fields[label] = match.group(1).strip()

    missing = [label for label in ("CODE", "FINDING") if label not in fields]
    if missing:
        raise NoticeParseError(
            f"citation {citation_id} is missing required fields: {', '.join(missing)}"
        )

    trade = _trade_from_text(fields.get("TRADE", ""))
    requirements = [
        item.strip()
        for item in fields.get("EVIDENCE", "").split(";")
        if item.strip()
    ]

    ambiguity_reasons: list[str] = []
    if trade is Trade.UNKNOWN:
        ambiguity_reasons.append("the notice does not identify a recognized trade")
    if not requirements:
        ambiguity_reasons.append("the notice does not state observable evidence requirements")

    return Citation(
        citation_id=citation_id,
        code_reference=fields["CODE"],
        notice_text=fields["FINDING"],
        trade=trade,
        evidence_requirements=requirements,
        ambiguity_reason="; ".join(ambiguity_reasons) or None,
    )


def _trade_from_text(value: str) -> Trade:
    normalized = value.strip().lower()
    aliases = {
        "electrical": Trade.ELECTRICAL,
        "electrician": Trade.ELECTRICAL,
        "framing": Trade.FRAMING,
        "carpentry": Trade.FRAMING,
        "mechanical": Trade.MECHANICAL,
        "hvac": Trade.MECHANICAL,
        "plumbing": Trade.PLUMBING,
        "plumber": Trade.PLUMBING,
        "general": Trade.GENERAL,
        "gc": Trade.GENERAL,
    }
    return aliases.get(normalized, Trade.UNKNOWN)
