from __future__ import annotations

from collections.abc import Callable, Mapping
from datetime import date
from enum import StrEnum
from hashlib import blake2s
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator
from strands.agent.agent_result import AgentResult
from strands.hooks import BeforeNodeCallEvent, HookProvider, HookRegistry
from strands.multiagent import GraphBuilder
from strands.multiagent.base import MultiAgentBase, MultiAgentResult, NodeResult, Status
from strands.telemetry.metrics import EventLoopMetrics

from mettle.campaign import build_campaign_plan
from mettle.communication import Messenger, OutboundMessage, Recipient, RecordedDelivery
from mettle.domain import CampaignPlan, InspectionNotice, Trade
from mettle.notice_parser import parse_notice


class WorkflowConfigurationError(RuntimeError):
    """Raised when a run cannot safely execute with the supplied configuration."""


class WorkflowStateError(RuntimeError):
    """Raised when a workflow operation is not valid in the current state."""


class WorkflowStatus(StrEnum):
    INTERRUPTED = "interrupted"
    COMPLETED = "completed"
    FAILED = "failed"


class WorkflowInterrupt(BaseModel):
    model_config = ConfigDict(extra="forbid")

    interrupt_id: str
    name: str
    reason: dict[str, Any]


class WorkflowSnapshot(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: WorkflowStatus
    notice: InspectionNotice | None = None
    plan: CampaignPlan | None = None
    deliveries: list[RecordedDelivery] = Field(default_factory=list)
    interrupts: list[WorkflowInterrupt] = Field(default_factory=list)
    contractor_decision: str | None = None


class ResumeDecision(BaseModel):
    model_config = ConfigDict(extra="forbid")

    interrupt_id: str = Field(min_length=1, max_length=240)
    decision: str = Field(min_length=3, max_length=500)

    @field_validator("decision")
    @classmethod
    def normalize_decision(cls, value: str) -> str:
        normalized = " ".join(value.split())
        if len(normalized) < 3:
            raise ValueError("decision must contain at least 3 visible characters")
        return normalized


NodeFunction = Callable[[str | list[dict[str, Any]], dict[str, Any]], str]
NoticeExtractor = Callable[[str], InspectionNotice]


class DeterministicNode(MultiAgentBase):
    """Run enforceable Python policy as a first-class Strands graph node."""

    def __init__(self, *, name: str, function: NodeFunction) -> None:
        super().__init__()
        self.name = name
        self.function = function

    async def invoke_async(
        self,
        task: str | list[dict[str, Any]],
        invocation_state: dict[str, Any] | None = None,
        **_kwargs: Any,
    ) -> MultiAgentResult:
        state = invocation_state if invocation_state is not None else {}
        summary = self.function(task, state)
        agent_result = AgentResult(
            stop_reason="end_turn",
            message={"role": "assistant", "content": [{"text": summary}]},
            metrics=EventLoopMetrics(),
            state=state,
        )
        return MultiAgentResult(
            status=Status.COMPLETED,
            results={
                self.name: NodeResult(
                    result=agent_result,
                    status=Status.COMPLETED,
                    execution_count=1,
                )
            },
            execution_count=1,
        )


class ContractorJudgmentHook(HookProvider):
    """Pause the graph only when the validated campaign plan needs judgment."""

    def register_hooks(self, registry: HookRegistry) -> None:
        registry.add_callback(BeforeNodeCallEvent, self.require_judgment)

    def require_judgment(self, event: BeforeNodeCallEvent) -> None:
        if event.node_id != "judgment_gate" or event.invocation_state is None:
            return
        plan = event.invocation_state.get("plan")
        if not isinstance(plan, CampaignPlan) or not plan.judgments:
            return

        response = event.interrupt(
            "contractor-judgment",
            reason={
                "notice_id": plan.notice_id,
                "judgments": [
                    judgment.model_dump(mode="json") for judgment in plan.judgments
                ],
            },
        )
        decision = ResumeDecision(
            interrupt_id="resolved-by-strands",
            decision=str(response),
        )
        event.invocation_state["contractor_decision"] = decision.decision


class RecoveryWorkflowSession:
    """One stateful Strands recovery run with explicit start/resume boundaries."""

    def __init__(
        self,
        *,
        notice_text: str,
        as_of: date,
        roster: Mapping[Trade, Recipient],
        messenger: Messenger,
        notice_extractor: NoticeExtractor = parse_notice,
    ) -> None:
        if not notice_text.strip():
            raise ValueError("notice_text must contain visible characters")
        if len(notice_text) > 100_000:
            raise ValueError("notice_text exceeds the 100,000 character limit")

        self._notice_text = notice_text
        self._notice_extractor = notice_extractor
        self._state: dict[str, Any] = {
            "as_of": as_of,
            "roster": dict(roster),
            "messenger": messenger,
            "deliveries": [],
        }
        self._started = False
        self._last_result: MultiAgentResult | None = None
        self._graph = self._build_graph()

    def start(self) -> WorkflowSnapshot:
        if self._started:
            raise WorkflowStateError("workflow has already started")
        self._started = True
        self._last_result = self._graph(
            self._notice_text,
            invocation_state=self._state,
        )
        return self._snapshot()

    def resume(self, *, interrupt_id: str, decision: str) -> WorkflowSnapshot:
        if not self._started or self._last_result is None:
            raise WorkflowStateError("workflow has not started")
        if self._last_result.status is not Status.INTERRUPTED:
            raise WorkflowStateError("workflow is not waiting for a decision")

        payload = ResumeDecision(interrupt_id=interrupt_id, decision=decision)
        active_ids = {item.id for item in self._last_result.interrupts}
        if payload.interrupt_id not in active_ids:
            raise WorkflowStateError("interrupt does not belong to this workflow")

        self._last_result = self._graph(
            [
                {
                    "interruptResponse": {
                        "interruptId": payload.interrupt_id,
                        "response": payload.decision,
                    }
                }
            ],
            invocation_state=self._state,
        )
        return self._snapshot()

    def _build_graph(self) -> MultiAgentBase:
        builder = GraphBuilder()
        builder.add_node(
            DeterministicNode(name="intake", function=self._intake),
            "intake",
        )
        builder.add_node(
            DeterministicNode(name="plan", function=self._plan),
            "plan",
        )
        builder.add_node(
            DeterministicNode(name="coordinate", function=self._coordinate),
            "coordinate",
        )
        builder.add_node(
            DeterministicNode(name="judgment_gate", function=self._judgment_gate),
            "judgment_gate",
        )
        builder.add_node(
            DeterministicNode(
                name="coordinate_decision",
                function=self._coordinate_decision,
            ),
            "coordinate_decision",
        )
        builder.add_node(
            DeterministicNode(name="finish", function=self._finish),
            "finish",
        )
        builder.add_edge("intake", "plan")
        builder.add_edge("plan", "coordinate")
        builder.add_edge("coordinate", "judgment_gate")
        builder.add_edge("judgment_gate", "coordinate_decision")
        builder.add_edge("coordinate_decision", "finish")
        builder.set_entry_point("intake")
        builder.set_max_node_executions(6)
        builder.set_execution_timeout(15)
        builder.set_hook_providers([ContractorJudgmentHook()])
        return builder.build()

    def _intake(self, task: str | list[dict[str, Any]], state: dict[str, Any]) -> str:
        if isinstance(task, str):
            notice_text = task
        elif isinstance(task, list) and all(
            isinstance(block, dict) and isinstance(block.get("text"), str)
            for block in task
        ):
            notice_text = "\n".join(block["text"] for block in task)
        else:
            raise ValueError("notice intake requires text-only content blocks")
        notice = self._notice_extractor(notice_text)
        state["notice"] = notice
        return f"Parsed {len(notice.citations)} notice-anchored citations."

    @staticmethod
    def _plan(_task: str | list[dict[str, Any]], state: dict[str, Any]) -> str:
        notice = state.get("notice")
        as_of = state.get("as_of")
        if not isinstance(notice, InspectionNotice) or not isinstance(as_of, date):
            raise WorkflowConfigurationError("intake state is incomplete")
        plan = build_campaign_plan(notice, as_of=as_of)
        state["plan"] = plan
        return f"Planned {len(plan.actions)} autonomous outreach actions."

    @staticmethod
    def _coordinate(_task: str | list[dict[str, Any]], state: dict[str, Any]) -> str:
        plan = state.get("plan")
        roster = state.get("roster")
        messenger = state.get("messenger")
        if not isinstance(plan, CampaignPlan) or not isinstance(roster, dict):
            raise WorkflowConfigurationError("campaign coordination state is incomplete")
        if messenger is None:
            raise WorkflowConfigurationError("messenger is not configured")

        missing = sorted(
            {action.trade.value for action in plan.actions if action.trade not in roster}
        )
        if missing:
            raise WorkflowConfigurationError(
                f"missing recipient for trade(s): {', '.join(missing)}"
            )

        deliveries: list[RecordedDelivery] = []
        for action in plan.actions:
            recipient = roster[action.trade]
            delivery_token = blake2s(
                f"{plan.notice_id}\0{action.citation_id}".encode("utf-8"),
                digest_size=10,
            ).hexdigest()
            delivery = messenger.send(
                OutboundMessage(
                    message_id=f"msg-{delivery_token}-initial",
                    notice_id=plan.notice_id,
                    citation_id=action.citation_id,
                    recipient=recipient,
                    body=action.message,
                    idempotency_key=f"delivery:{delivery_token}:initial",
                    scheduled_on=action.due_on,
                )
            )
            deliveries.append(delivery)
        state["deliveries"] = deliveries
        return f"Recorded {len(deliveries)} idempotent trade messages."

    @staticmethod
    def _judgment_gate(
        _task: str | list[dict[str, Any]], state: dict[str, Any]
    ) -> str:
        return "Contractor judgment recorded." if state.get("contractor_decision") else "No judgment required."

    @staticmethod
    def _coordinate_decision(
        _task: str | list[dict[str, Any]], state: dict[str, Any]
    ) -> str:
        decision = state.get("contractor_decision")
        plan = state.get("plan")
        notice = state.get("notice")
        roster = state.get("roster")
        messenger = state.get("messenger")
        if not decision:
            return "No contractor-directed outreach required."
        if (
            not isinstance(plan, CampaignPlan)
            or not isinstance(notice, InspectionNotice)
            or not isinstance(roster, dict)
            or messenger is None
        ):
            raise WorkflowConfigurationError("decision coordination state is incomplete")

        citations = {citation.citation_id: citation for citation in notice.citations}
        deliveries = list(state.get("deliveries", []))
        recorded = 0
        for judgment in plan.judgments:
            if judgment.citation_id is None:
                continue
            citation = citations.get(judgment.citation_id)
            if citation is None:
                raise WorkflowConfigurationError("judgment citation is missing from notice")
            recipient = roster.get(citation.trade)
            if recipient is None:
                raise WorkflowConfigurationError(
                    f"missing recipient for trade(s): {citation.trade.value}"
                )
            delivery_token = blake2s(
                f"{plan.notice_id}\0{citation.citation_id}\0decision".encode("utf-8"),
                digest_size=10,
            ).hexdigest()
            delivery = messenger.send(
                OutboundMessage(
                    message_id=f"msg-{delivery_token}-decision",
                    notice_id=plan.notice_id,
                    citation_id=citation.citation_id,
                    recipient=recipient,
                    body=(
                        f'Notice: "{citation.notice_text}" '
                        f'Contractor direction: "{decision}" '
                        f"Reinspection target: {notice.reinspection_due_on.isoformat()}. "
                        "Reply with the requested photos; Mettle does not certify compliance."
                    ),
                    idempotency_key=f"delivery:{delivery_token}:decision",
                    scheduled_on=plan.as_of,
                )
            )
            deliveries.append(delivery)
            recorded += 1
        state["deliveries"] = deliveries
        return f"Recorded {recorded} contractor-directed trade messages."

    @staticmethod
    def _finish(_task: str | list[dict[str, Any]], state: dict[str, Any]) -> str:
        state["workflow_complete"] = True
        return "Recovery workflow completed."

    def _snapshot(self) -> WorkflowSnapshot:
        if self._last_result is None:
            raise WorkflowStateError("workflow has no result")
        status = {
            Status.INTERRUPTED: WorkflowStatus.INTERRUPTED,
            Status.COMPLETED: WorkflowStatus.COMPLETED,
            Status.FAILED: WorkflowStatus.FAILED,
        }.get(self._last_result.status, WorkflowStatus.FAILED)
        return WorkflowSnapshot(
            status=status,
            notice=self._state.get("notice"),
            plan=self._state.get("plan"),
            deliveries=list(self._state.get("deliveries", [])),
            interrupts=[
                WorkflowInterrupt(
                    interrupt_id=item.id,
                    name=item.name,
                    reason=item.reason if isinstance(item.reason, dict) else {},
                )
                for item in self._last_result.interrupts
            ],
            contractor_decision=self._state.get("contractor_decision"),
        )
