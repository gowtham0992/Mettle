from __future__ import annotations

from datetime import date, timedelta

from mettle.domain import (
    CampaignPlan,
    FollowUpAction,
    InspectionNotice,
    JudgmentKind,
    JudgmentRequest,
    Priority,
)


def build_campaign_plan(notice: InspectionNotice, *, as_of: date) -> CampaignPlan:
    days_remaining = (notice.reinspection_due_on - as_of).days
    priority = _priority_for(days_remaining)
    actions: list[FollowUpAction] = []
    judgments: list[JudgmentRequest] = []

    for citation in notice.citations:
        if citation.ambiguity_reason:
            judgments.append(
                JudgmentRequest(
                    kind=JudgmentKind.CODE_INTERPRETATION,
                    citation_id=citation.citation_id,
                    question=(
                        f"What correction and evidence should Mettle request for "
                        f"citation {citation.citation_id}?"
                    ),
                    reason=citation.ambiguity_reason,
                )
            )
            continue

        evidence = "; ".join(citation.evidence_requirements)
        actions.append(
            FollowUpAction(
                citation_id=citation.citation_id,
                trade=citation.trade,
                priority=priority,
                due_on=_action_due_on(as_of, notice.reinspection_due_on, priority),
                message=_message_for(
                    priority=priority,
                    citation_id=citation.citation_id,
                    notice_text=citation.notice_text,
                    evidence=evidence,
                    due_on=notice.reinspection_due_on,
                ),
            )
        )

    if days_remaining <= 2 and actions:
        judgments.append(
            JudgmentRequest(
                kind=JudgmentKind.DEADLINE_TRADEOFF,
                question="Should Mettle keep the current reinspection target or request a new date?",
                reason=f"Only {max(days_remaining, 0)} day(s) remain with open corrections.",
            )
        )

    return CampaignPlan(
        notice_id=notice.notice_id,
        as_of=as_of,
        days_remaining=days_remaining,
        priority=priority,
        actions=actions,
        judgments=judgments,
    )


def _priority_for(days_remaining: int) -> Priority:
    if days_remaining <= 2:
        return Priority.CRITICAL
    if days_remaining <= 4:
        return Priority.URGENT
    if days_remaining <= 7:
        return Priority.ATTENTION
    return Priority.ROUTINE


def _action_due_on(as_of: date, deadline: date, priority: Priority) -> date:
    offsets = {
        Priority.ROUTINE: 2,
        Priority.ATTENTION: 1,
        Priority.URGENT: 0,
        Priority.CRITICAL: 0,
    }
    return min(as_of + timedelta(days=offsets[priority]), deadline)


def _message_for(
    *,
    priority: Priority,
    citation_id: str,
    notice_text: str,
    evidence: str,
    due_on: date,
) -> str:
    opening = {
        Priority.ROUTINE: "Please review this correction",
        Priority.ATTENTION: "This correction needs attention",
        Priority.URGENT: "Urgent correction follow-up",
        Priority.CRITICAL: "Deadline-critical correction",
    }[priority]
    return (
        f"{opening} for citation {citation_id}. Notice: \"{notice_text}\" "
        f"Reply with: {evidence}. Reinspection target: {due_on.isoformat()}."
    )
