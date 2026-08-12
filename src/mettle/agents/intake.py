from __future__ import annotations

import re
from typing import Any

from mettle.domain import InspectionNotice


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
    agent = create_intake_agent(model=model)
    extracted = agent.structured_output(
        InspectionNotice,
        "Extract this failed-inspection notice without interpreting code. "
        "For a heading such as 'CITATION 3', citation_id must be exactly '3'. "
        "When no EVIDENCE language exists for a citation, return an empty "
        "evidence_requirements list and set ambiguity_reason.\n\n"
        f"{text}",
    )
    return reconcile_explicit_citation_ids(text, extracted)


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
