from __future__ import annotations

import re
from typing import Any

from mettle.domain import Citation, ClosureRoute, InspectionNotice, Trade
from mettle.notice_parser import parse_notice


SYSTEM_PROMPT = """
You are Mettle's notice-intake specialist. Extract only information grounded in
the failed-inspection notice. Preserve each finding's operative language in
notice_text. Never decide that work is code-compliant and never invent a code
interpretation. If the responsible trade or observable evidence requirement is
not explicit, set ambiguity_reason so a licensed contractor can decide.
""".strip()


def create_intake_agent(*, model: Any | None = None) -> Any:
    """Create the Strands intake agent when the optional AWS extra is installed."""
    try:
        from strands import Agent
    except ImportError as exc:
        raise RuntimeError(
            "Strands is not installed. Run `uv sync --extra dev`."
        ) from exc

    return Agent(model=model, system_prompt=SYSTEM_PROMPT, callback_handler=None)


def extract_notice_with_agent(text: str, *, model: Any | None = None) -> InspectionNotice:
    """Extract and validate a notice through Strands structured output."""
    # Establish a complete source inventory before invoking a probabilistic model.
    # Unsupported formats must not silently become a partial recovery.
    source = reconcile_explicit_citation_ids(text, parse_notice(text))
    agent = create_intake_agent(model=model)
    extracted = agent.structured_output(
        InspectionNotice,
        "Extract this failed-inspection notice without interpreting code. "
        "For a heading such as 'CITATION 3', citation_id must be exactly '3'. "
        "Evidence instructions need not have an EVIDENCE heading: extract explicit "
        "requests such as 'provide a clear wide photo showing the panel and cleared floor', "
        "'provide the manufacturer document', or 'on-site inspector verification'. "
        "Preserve these requests in evidence_requirements without adding measurements "
        "or conditions absent from the notice. Select the matching closure_route. "
        "When no explicit proof instructions exist for a citation, return an empty "
        "evidence_requirements list and set ambiguity_reason.\n\n"
        f"{text}",
    )
    return ground_notice_in_source(source, extracted, text)


def ground_notice_in_source(
    source: InspectionNotice, proposed: InspectionNotice, source_text: str,
) -> InspectionNotice:
    """Models propose; source blocks own identity, completeness and authority.

    Never zip source items to model items: omitted/reordered model output could
    otherwise attach an unrelated requirement to the wrong correction.
    """
    citations = []
    for original in source.citations:
        candidates = [c for c in proposed.citations
                      if c.notice_text.strip() == original.notice_text.strip()]
        candidate = candidates[0] if len(candidates) == 1 else None
        requirements = explicit_proof(original, source_text)
        route = ClosureRoute.PHOTO_EVIDENCE
        proof_text = " ".join(requirements).lower()
        if re.search(r"\b(?:on[- ]site|physical)\s+(?:inspector\s+)?(?:verification|reinspection|inspection)\b", proof_text):
            route = ClosureRoute.PHYSICAL_REINSPECTION
        elif re.search(r"\b(?:documents?|certificates?|certification|reports?)\b", proof_text):
            route = ClosureRoute.DOCUMENT_EVIDENCE
        # A model may propose an otherwise unknown trade for contractor review,
        # but cannot replace source authority or downgrade its proof method.
        trade = original.trade
        ambiguity = None
        if trade == Trade.UNKNOWN and candidate:
            trade = candidate.trade
            ambiguity = "Confirm the model-proposed trade; the notice does not explicitly identify one"
        citations.append(Citation(
            citation_id=original.citation_id,
            code_reference=original.code_reference,
            notice_text=original.notice_text,
            trade=trade,
            closure_route=route,
            evidence_requirements=requirements,
            ambiguity_reason=ambiguity,
        ))
    return InspectionNotice(
        notice_id=source.notice_id, property_label=source.property_label,
        issued_on=source.issued_on, reinspection_due_on=source.reinspection_due_on,
        citations=citations,
    )


def explicit_proof(citation: Citation, source_text: str) -> list[str]:
    """Keep quoted proof instructions; do not inherit code-based demo defaults."""
    block = re.search(
        rf"(?ms)^CITATION\s+{re.escape(citation.citation_id)}[ \t]*\n(.*?)^END CITATION[ \t]*$",
        source_text,
    )
    if block:
        evidence = re.search(r"(?m)^EVIDENCE:[ \t]*(.+)$", block.group(1))
        if evidence:
            return [item.strip() for item in evidence.group(1).split(";") if item.strip()]
    instructions = [sentence.strip() for sentence in re.split(
        r"(?<=[.!?])\s+|\n+", citation.notice_text,
    ) if re.search(
        r"\b(?:provide|submit|attach|show|document|upload|send|verify|verification|reinspection)\b",
        sentence, re.I,
    ) and re.search(
        r"\b(?:photo(?:graph)?s?|images?|documents?|certificates?|reports?|on[- ]site|inspector|reinspection)\b",
        sentence, re.I,
    )]
    return instructions


def reconcile_explicit_citation_ids(
    source_text: str,
    notice: InspectionNotice,
) -> InspectionNotice:
    """Ground IDs in explicit source headings when the source provides them."""
    source_ids = [
        match.group(1).strip()
        for match in re.finditer(r"(?m)^CITATION\s+([^\n]+?)\s*$", source_text)
    ]
    if not source_ids:
        return notice
    if len(source_ids) != len(notice.citations):
        raise ValueError("model citation count does not match explicit source headings")
    if len(source_ids) != len(set(source_ids)):
        raise ValueError("explicit source citation identifiers must be unique")

    citations = [
        citation.model_copy(update={"citation_id": source_id})
        for source_id, citation in zip(source_ids, notice.citations, strict=True)
    ]
    return notice.model_copy(update={"citations": citations})
