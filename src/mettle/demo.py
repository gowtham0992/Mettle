from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from enum import StrEnum
from threading import Lock

from pydantic import BaseModel, ConfigDict, Field

from mettle.domain import Priority, Trade
from mettle.notice_parser import parse_notice


class CitationStage(StrEnum):
    AWAITING_EVIDENCE = "awaiting_evidence"
    EVIDENCE_REJECTED = "evidence_rejected"
    NEEDS_JUDGMENT = "needs_judgment"
    READY = "ready"


class GateStatus(StrEnum):
    PENDING = "pending"
    RESOLVED = "resolved"


class DemoCitation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    citation_id: str
    code_reference: str
    notice_text: str
    trade: Trade
    assignee: str | None
    evidence_requirements: list[str]
    stage: CitationStage
    evidence_note: str | None = None


class DemoEvent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    event_id: str
    happened_at: datetime
    kind: str
    title: str
    detail: str
    citation_id: str | None = None
    actor: str


class DemoJudgment(BaseModel):
    model_config = ConfigDict(extra="forbid")

    judgment_id: str
    kind: str
    citation_id: str | None = None
    question: str
    reason: str
    status: GateStatus = GateStatus.PENDING
    decision: str | None = None


class DemoMetrics(BaseModel):
    model_config = ConfigDict(extra="forbid")

    citations_ready: int
    citations_total: int
    messages_handled: int
    automated_actions: int
    contractor_decisions: int


class DemoCampaign(BaseModel):
    model_config = ConfigDict(extra="forbid")

    notice_id: str
    property_label: str
    issued_on: date
    reinspection_due_on: date
    as_of: date
    days_remaining: int
    priority: Priority
    scenario_step: int
    scenario_complete: bool
    packet_status: str
    citations: list[DemoCitation]
    events: list[DemoEvent]
    judgments: list[DemoJudgment]
    metrics: DemoMetrics


class DemoNotFound(LookupError):
    pass


class DemoConflict(RuntimeError):
    pass


class DemoStore:
    """Thread-safe, in-memory scenario store for the local judge demo."""

    def __init__(self) -> None:
        self._lock = Lock()
        self._seen_keys: set[str] = set()
        self._resolved_decisions: dict[str, str] = {}
        self._reset_unlocked()

    def snapshot(self) -> DemoCampaign:
        with self._lock:
            return self._snapshot_unlocked()

    def reset(self) -> DemoCampaign:
        with self._lock:
            self._reset_unlocked()
            return self._snapshot_unlocked()

    def advance(self, *, idempotency_key: str) -> DemoCampaign:
        with self._lock:
            if idempotency_key in self._seen_keys:
                return self._snapshot_unlocked()
            self._seen_keys.add(idempotency_key)

            handlers = (
                self._accept_electrical_evidence,
                self._reject_framing_evidence,
                self._escalate_deadline,
                self._accept_framing_replacement,
                self._accept_mechanical_evidence,
                self._prepare_final_packet,
            )
            if self._step == 4 and self._citation("3").stage is CitationStage.NEEDS_JUDGMENT:
                return self._snapshot_unlocked()
            if self._step == 5 and any(
                item.stage is not CitationStage.READY for item in self._citations
            ):
                return self._snapshot_unlocked()
            if self._step < len(handlers):
                handlers[self._step]()
                self._step += 1
            return self._snapshot_unlocked()

    def resolve_judgment(self, judgment_id: str, *, decision: str) -> DemoCampaign:
        with self._lock:
            judgment = next(
                (item for item in self._judgments if item.judgment_id == judgment_id),
                None,
            )
            if judgment is None:
                raise DemoNotFound(f"judgment {judgment_id!r} does not exist")
            if judgment.status is GateStatus.RESOLVED:
                if self._resolved_decisions[judgment_id] != decision:
                    raise DemoConflict("this judgment was already resolved differently")
                return self._snapshot_unlocked()

            judgment.status = GateStatus.RESOLVED
            judgment.decision = decision
            self._resolved_decisions[judgment_id] = decision
            self._contractor_decisions += 1
            self._events.append(
                self._event(
                    event_id=f"decision-{judgment_id}",
                    kind="judgment_resolved",
                    title="Contractor judgment recorded",
                    detail=decision,
                    citation_id=judgment.citation_id,
                    actor="Contractor",
                )
            )

            if judgment_id == "code-c3":
                citation = self._citation("3")
                citation.stage = CitationStage.AWAITING_EVIDENCE
                citation.trade = Trade.MECHANICAL
                citation.assignee = "Alex Kim · Alpine Mechanical"
                citation.evidence_requirements = [decision]
            elif judgment_id == "final-approval":
                self._packet_status = "approved"
            return self._snapshot_unlocked()

    def _reset_unlocked(self) -> None:
        fixture = """
NOTICE ID: CR-2026-0417
ISSUED: 2026-08-07
REINSPECTION DEADLINE: 2026-08-17
PROPERTY: 100 Demo Way, Castle Pines, CO

CITATION 1
CODE: NEC 110.26
TRADE: Electrical
FINDING: Maintain the required working clearance in front of the service panel.
EVIDENCE: Wide photo showing the complete service panel area; photo with a tape measure showing the clearance
END CITATION

CITATION 2
CODE: IRC R602.6
TRADE: Framing
FINDING: Protect bored framing members where the edge distance is less than required.
EVIDENCE: Close photo of each installed protection plate; wide photo identifying each corrected wall location
END CITATION

CITATION 3
CODE: IMC 304.10
TRADE: Mechanical
FINDING: Provide clearance and service access at the installed mechanical equipment.
END CITATION
"""
        notice = parse_notice(fixture)
        assignees = {
            "1": "Mike Alvarez · Brightline Electric",
            "2": "Jen Ortiz · Front Range Framing",
            "3": None,
        }
        self._notice = notice
        self._as_of = date(2026, 8, 10)
        self._step = 0
        self._messages_handled = 2
        self._automated_actions = 4
        self._contractor_decisions = 0
        self._packet_status = "blocked"
        self._seen_keys = set()
        self._resolved_decisions = {}
        self._citations = [
            DemoCitation(
                citation_id=item.citation_id,
                code_reference=item.code_reference,
                notice_text=item.notice_text,
                trade=item.trade,
                assignee=assignees[item.citation_id],
                evidence_requirements=item.evidence_requirements,
                stage=(
                    CitationStage.NEEDS_JUDGMENT
                    if item.ambiguity_reason
                    else CitationStage.AWAITING_EVIDENCE
                ),
            )
            for item in notice.citations
        ]
        self._events = []
        self._events.append(
            self._event(
                event_id="notice-ingested",
                kind="notice_ingested",
                title="Correction notice converted into a recovery run",
                detail="3 citations extracted and anchored to the source notice.",
                actor="Intake agent",
            )
        )
        self._events.append(
            self._event(
                event_id="assignments-sent",
                kind="message_sent",
                title="Trade requests sent without project setup",
                detail="Electrical and framing requests delivered over simulated SMS.",
                actor="Coordination agent",
            )
        )
        self._judgments = [
            DemoJudgment(
                judgment_id="code-c3",
                kind="code_interpretation",
                citation_id="3",
                question="What evidence should the mechanical trade provide for citation 3?",
                reason=(
                    "The notice requires service access but does not state an observable "
                    "evidence requirement. Mettle will not invent one."
                ),
            )
        ]

    def _accept_electrical_evidence(self) -> None:
        citation = self._citation("1")
        citation.stage = CitationStage.READY
        citation.evidence_note = "Wide panel view and measured clearance accepted."
        self._messages_handled += 1
        self._automated_actions += 2
        self._events.append(
            self._event(
                event_id="c1-evidence-accepted",
                kind="evidence_accepted",
                title="Citation 1 evidence accepted",
                detail="The panel and measured clearance are both visible in the submitted set.",
                citation_id="1",
                actor="Evidence agent",
            )
        )

    def _reject_framing_evidence(self) -> None:
        citation = self._citation("2")
        citation.stage = CitationStage.EVIDENCE_REJECTED
        citation.evidence_note = (
            "Close plate photo received; the wider location view required by the notice is missing."
        )
        self._messages_handled += 2
        self._automated_actions += 2
        self._events.append(
            self._event(
                event_id="c2-evidence-rejected",
                kind="evidence_rejected",
                title="Insufficient framing photo rejected",
                detail=(
                    "Mettle asked Jen for a wider shot that identifies the corrected wall location."
                ),
                citation_id="2",
                actor="Evidence agent",
            )
        )

    def _escalate_deadline(self) -> None:
        self._as_of = date(2026, 8, 15)
        self._messages_handled += 3
        self._automated_actions += 3
        self._events.append(
            self._event(
                event_id="deadline-escalated",
                kind="deadline_escalation",
                title="Recovery cadence moved to critical",
                detail="Two days remain. Silent trades were escalated and the contractor was alerted.",
                actor="Recovery orchestrator",
            )
        )
        self._judgments.append(
            DemoJudgment(
                judgment_id="deadline-choice",
                kind="deadline_tradeoff",
                question="Keep the current reinspection target or request a new date?",
                reason="Two days remain and open corrections still depend on field evidence.",
            )
        )

    def _accept_framing_replacement(self) -> None:
        citation = self._citation("2")
        citation.stage = CitationStage.READY
        citation.evidence_note = "Replacement set includes close and location-wide views."
        self._messages_handled += 1
        self._automated_actions += 1
        self._events.append(
            self._event(
                event_id="c2-replacement-accepted",
                kind="evidence_accepted",
                title="Citation 2 replacement evidence accepted",
                detail="Both notice-anchored photo requirements are now represented.",
                citation_id="2",
                actor="Evidence agent",
            )
        )

    def _accept_mechanical_evidence(self) -> None:
        citation = self._citation("3")
        citation.stage = CitationStage.READY
        citation.evidence_note = "Contractor-defined service-clearance view accepted."
        self._messages_handled += 1
        self._automated_actions += 1
        self._events.append(
            self._event(
                event_id="c3-evidence-accepted",
                kind="evidence_accepted",
                title="Citation 3 evidence accepted",
                detail="The submitted view matches the contractor-approved evidence request.",
                citation_id="3",
                actor="Evidence agent",
            )
        )

    def _prepare_final_packet(self) -> None:
        unresolved = [item for item in self._judgments if item.status is GateStatus.PENDING]
        self._packet_status = "awaiting_approval" if not unresolved else "blocked"
        self._automated_actions += 2
        self._events.append(
            self._event(
                event_id="packet-prepared",
                kind="packet_prepared",
                title="Reinspection packet assembled",
                detail=(
                    "The packet is assembled, but submission remains blocked by human gates."
                    if unresolved
                    else "The citation-to-evidence packet is ready for final approval."
                ),
                actor="Packet agent",
            )
        )
        self._judgments.append(
            DemoJudgment(
                judgment_id="final-approval",
                kind="final_packet_approval",
                question="Approve the correction packet for reinspection scheduling?",
                reason="Mettle never submits or contacts the inspector without contractor approval.",
            )
        )

    def _snapshot_unlocked(self) -> DemoCampaign:
        days_remaining = (self._notice.reinspection_due_on - self._as_of).days
        ready = sum(item.stage is CitationStage.READY for item in self._citations)
        priority = (
            Priority.CRITICAL
            if days_remaining <= 2
            else Priority.URGENT
            if days_remaining <= 4
            else Priority.ATTENTION
            if days_remaining <= 7
            else Priority.ROUTINE
        )
        return DemoCampaign(
            notice_id=self._notice.notice_id,
            property_label=self._notice.property_label,
            issued_on=self._notice.issued_on,
            reinspection_due_on=self._notice.reinspection_due_on,
            as_of=self._as_of,
            days_remaining=days_remaining,
            priority=priority,
            scenario_step=self._step,
            scenario_complete=self._step >= 6,
            packet_status=self._packet_status,
            citations=[item.model_copy(deep=True) for item in self._citations],
            events=[item.model_copy(deep=True) for item in reversed(self._events)],
            judgments=[item.model_copy(deep=True) for item in self._judgments],
            metrics=DemoMetrics(
                citations_ready=ready,
                citations_total=len(self._citations),
                messages_handled=self._messages_handled,
                automated_actions=self._automated_actions,
                contractor_decisions=self._contractor_decisions,
            ),
        )

    def _citation(self, citation_id: str) -> DemoCitation:
        return next(item for item in self._citations if item.citation_id == citation_id)

    def _event(
        self,
        *,
        event_id: str,
        kind: str,
        title: str,
        detail: str,
        actor: str,
        citation_id: str | None = None,
    ) -> DemoEvent:
        base = datetime(2026, 8, 10, 15, 30, tzinfo=timezone.utc)
        offset_minutes = len(getattr(self, "_events", [])) * 17
        return DemoEvent(
            event_id=event_id,
            happened_at=base + timedelta(minutes=offset_minutes),
            kind=kind,
            title=title,
            detail=detail,
            citation_id=citation_id,
            actor=actor,
        )
