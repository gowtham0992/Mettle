from __future__ import annotations

import re
from datetime import date, datetime, timedelta

from mettle.domain import Citation, InspectionNotice, Trade


class NoticeParseError(ValueError):
    """Raised when a notice cannot satisfy Mettle's intake contract."""


_HEADER_PATTERNS = {
    "notice_id": (
        r"(?im)^(?:NOTICE ID|RECORD ID|PERMIT\s+(?:NO\.?|NUMBER)|PERMIT)(?:\s*(?:#\s*:?|:)\s*|\s+)(.+?)\s*$",
        r"(?im)^CORRECTION NOTICE\s*#\s*(.+?)\s*$",
    ),
    "issued_on": (
        r"(?im)^(?:DATE OF INSPECTION|INSPECTION PERFORMED|INSPECTION DATE|DATE ISSUED|ISSUED|DATE)(?:\s*(?:#\s*:?|:)\s*|\s+)(.+?)\s*$",
    ),
    "reinspection_due_on": (
        r"(?im)^(?:RE[- ]?INSPECTION (?:REQUIRED BY|DEADLINE|TARGET|DATE|DUE)|CORRECTION DEADLINE|CORRECT BY)(?:\s*(?:#\s*:?|:)\s*|\s+)(.+?)\s*$",
        r"(?i)corrections must be completed before reinspection on\s+([^\n.]+)",
    ),
    "property_label": (
        r"(?im)^(?:PROJECT ADDRESS|PROPERTY ADDRESS|JOB ADDRESS|PROPERTY|LOCATION|ADDRESS|SITE)(?:\s*(?:#\s*:?|:)\s*|\s+)(.+?)\s*$",
    ),
}

_CODE_PATTERN = re.compile(
    r"\b(NEC|IRC|IMC|IPC|IBC|IFC|UPC|IECC)\s+([A-Z]?\d+(?:\.\d+)*(?:\([A-Za-z0-9.]+\))*)\b",
    re.IGNORECASE,
)

_TRADE_BY_CODE = {
    "NEC 110.26": Trade.ELECTRICAL,
    "IRC R602.6": Trade.FRAMING,
    "IMC 304.10": Trade.MECHANICAL,
}

_EVIDENCE_POLICY = {
    "NEC 110.26": [
        "Wide photo showing the complete service panel area",
        "Photo with a tape measure showing the working clearance",
    ],
    "IRC R602.6": [
        "Close photo of each installed protection plate",
        "Wide photo identifying each corrected wall location",
    ],
}


def parse_notice(text: str) -> InspectionNotice:
    """Parse supported correction-notice text without interpreting building code."""
    normalized = text.replace("\r\n", "\n").strip()
    if not normalized:
        raise NoticeParseError("notice is empty")

    if re.search(r"(?m)^CITATION\s+[^\n]+$", normalized):
        return _parse_labeled_notice(normalized)
    return _parse_numbered_notice(normalized)


def _parse_labeled_notice(normalized: str) -> InspectionNotice:
    header = _extract_header(normalized)
    blocks = re.findall(
        r"(?ms)^CITATION\s+([^\n]+)\n(.*?)^END CITATION\s*$",
        normalized,
    )
    if not blocks:
        raise NoticeParseError("notice contains no citation blocks")
    citations = [_parse_labeled_citation(item_id.strip(), body) for item_id, body in blocks]
    return _build_notice(header, citations)


def _parse_numbered_notice(normalized: str) -> InspectionNotice:
    header = _extract_header(normalized)
    blocks = re.findall(
        r"(?ms)^\s*(?:ITEM\s+|#|\()?([0-9]{1,2})\)?[.):\-]\s+(.+?)(?=^\s*(?:ITEM\s+|#|\()?[0-9]{1,2}\)?[.):\-]\s+|\Z)",
        normalized,
        flags=re.IGNORECASE,
    )
    if not blocks:
        section = re.search(
            r"(?ims)^(?:CORRECTIONS(?: REQUIRED)?|INSPECTION COMMENTS|VIOLATIONS|DEFICIENCIES|ITEMS REQUIRING CORRECTION|OUTSTANDING CORRECTIONS)\s*:?[ \t]*\n(.+)$",
            normalized,
        )
        if section:
            bullet_items = re.findall(r"(?m)^\s*[-*•]\s+(.+?)\s*$", section.group(1))
            blocks = [(str(index), item) for index, item in enumerate(bullet_items, start=1)]
    if not blocks:
        raise NoticeParseError("notice contains no numbered correction items")

    citations: list[Citation] = []
    for citation_id, raw_item in blocks:
        item = " ".join(raw_item.split())
        code_match = _CODE_PATTERN.search(item)
        if code_match is None:
            if len(item) < 12:
                raise NoticeParseError(f"correction {citation_id} has no usable finding text")
            citations.append(
                _citation(
                    citation_id=citation_id,
                    code_reference="Not stated in notice",
                    notice_text=item.strip(" []:;—–-\t"),
                    trade=_trade_from_code_and_text("", item),
                    evidence_requirements=[],
                    additional_ambiguity="the notice does not state a code reference",
                )
            )
            continue
        code_reference = f"{code_match.group(1).upper()} {code_match.group(2).upper()}"
        notice_text = (
            item[: code_match.start()] + item[code_match.end() :]
        ).strip(" []:;—–-\t")
        if not notice_text:
            raise NoticeParseError(f"correction {citation_id} has no finding text")
        citations.append(
            _derived_citation(
                citation_id=citation_id,
                code_reference=code_reference,
                notice_text=notice_text,
            )
        )
    return _build_notice(header, citations)


def _extract_header(normalized: str) -> dict[str, str]:
    header: dict[str, str] = {}
    for field_name, patterns in _HEADER_PATTERNS.items():
        for pattern in patterns:
            match = re.search(pattern, normalized)
            if match:
                header[field_name] = match.group(1).strip()
                break
    # Some municipal notices put a calendar-day deadline after the issue date.
    # Extract only that date, not the remaining prose on the same line.
    if "issued_on" in header:
        numeric_date = re.match(r"(\d{4}-\d{1,2}-\d{1,2}|\d{1,2}/\d{1,2}/\d{2,4})\b", header["issued_on"])
        if numeric_date:
            header["issued_on"] = numeric_date.group(1)
    if "reinspection_due_on" not in header:
        relative = re.search(r"re[- ]?inspection\s+(?:required\s+)?within\s+(\d{1,3})\s+(?:calendar\s+)?days\b", normalized, re.I)
        if relative and "issued_on" in header and 1 <= int(relative.group(1)) <= 365:
            header["reinspection_due_on"] = (_parse_date(header["issued_on"]) + timedelta(days=int(relative.group(1)))).isoformat()
    missing = [field for field in _HEADER_PATTERNS if field not in header]
    if missing:
        raise NoticeParseError(f"missing notice fields: {', '.join(missing)}")
    return header


def _build_notice(header: dict[str, str], citations: list[Citation]) -> InspectionNotice:
    issued_on = _parse_date(header["issued_on"])
    due_on = _parse_date(header["reinspection_due_on"])
    if due_on < issued_on:
        raise NoticeParseError("reinspection deadline cannot precede issue date")
    return InspectionNotice(
        notice_id=header["notice_id"],
        issued_on=issued_on,
        reinspection_due_on=due_on,
        property_label=header["property_label"],
        citations=citations,
    )


def _parse_date(value: str) -> date:
    cleaned = re.sub(r"\s+", " ", value.strip().rstrip("."))
    for format_string in (
        "%Y-%m-%d",
        "%m/%d/%Y",
        "%m/%d/%y",
        "%B %d, %Y",
        "%b %d, %Y",
        "%B %d %Y",
        "%b %d %Y",
    ):
        try:
            return datetime.strptime(cleaned, format_string).date()
        except ValueError:
            continue
    raise NoticeParseError("notice contains a date Mettle could not read")


def _parse_labeled_citation(citation_id: str, body: str) -> Citation:
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
        item.strip() for item in fields.get("EVIDENCE", "").split(";") if item.strip()
    ]
    return _citation(
        citation_id=citation_id,
        code_reference=fields["CODE"],
        notice_text=fields["FINDING"],
        trade=trade,
        evidence_requirements=requirements,
    )


def _derived_citation(
    *, citation_id: str, code_reference: str, notice_text: str
) -> Citation:
    trade = _TRADE_BY_CODE.get(code_reference) or _trade_from_code_and_text(
        code_reference, notice_text
    )
    requirements = list(_EVIDENCE_POLICY.get(code_reference, ()))
    return _citation(
        citation_id=citation_id,
        code_reference=code_reference,
        notice_text=notice_text,
        trade=trade,
        evidence_requirements=requirements,
    )


def _citation(
    *,
    citation_id: str,
    code_reference: str,
    notice_text: str,
    trade: Trade,
    evidence_requirements: list[str],
    additional_ambiguity: str | None = None,
) -> Citation:
    ambiguity_reasons: list[str] = [additional_ambiguity] if additional_ambiguity else []
    if trade is Trade.UNKNOWN:
        ambiguity_reasons.append("the notice does not identify a recognized trade")
    if not evidence_requirements:
        ambiguity_reasons.append("the notice does not state observable evidence requirements")
    return Citation(
        citation_id=citation_id,
        code_reference=code_reference,
        notice_text=notice_text,
        trade=trade,
        evidence_requirements=evidence_requirements,
        ambiguity_reason="; ".join(ambiguity_reasons) or None,
    )


def _trade_from_code_and_text(code_reference: str, notice_text: str) -> Trade:
    family = code_reference.split(maxsplit=1)[0] if code_reference.strip() else ""
    if family == "NEC":
        return Trade.ELECTRICAL
    if family == "IMC":
        return Trade.MECHANICAL
    if family in {"IPC", "UPC"}:
        return Trade.PLUMBING
    lowered = notice_text.lower()
    keyword_trades = (
        (("water heater", "piping", "plumbing", "drain"), Trade.PLUMBING),
        (("framing", "fireblock", "stud", "plate"), Trade.FRAMING),
        (("duct", "exhaust", "mechanical", "hvac"), Trade.MECHANICAL),
        (("electrical", "outlet", "panel", "receptacle"), Trade.ELECTRICAL),
    )
    for keywords, trade in keyword_trades:
        if any(keyword in lowered for keyword in keywords):
            return trade
    return Trade.GENERAL if family in {"IRC", "IBC", "IFC", "IECC"} else Trade.UNKNOWN


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
