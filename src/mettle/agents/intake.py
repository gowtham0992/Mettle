from __future__ import annotations

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
    return agent.structured_output(
        InspectionNotice,
        f"Extract this failed-inspection notice without interpreting code:\n\n{text}",
    )
