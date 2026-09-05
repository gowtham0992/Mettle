import io
import json
from hashlib import sha256

import pytest

from mettle.agentcore_runtime import MettleAgentCoreRuntime
from mettle.durable_agentcore_gateway import DurableAgentCoreWorkflowGateway
from mettle.communication import RecordingMessenger
from mettle.request_identity import set_principal, reset_principal
from mettle.workflow_registry import WorkflowRegistry, ResumeWorkflowRequest, WorkflowConflict, WorkflowNotFound
from mettle.agentcore_gateway import AgentCoreGatewayError
from test_durable_agentcore_gateway import MemoryTable, payload, review_request, RUNTIME_ARN, FakeCampaignScheduler
from mettle.automation import ScheduledCheckEvent


class PrivateBucket:
    def __init__(self):
        self.objects = {}

    def put_object(self, *, Key, Body, **kwargs):
        assert kwargs["ServerSideEncryption"] == "AES256"
        self.objects[Key] = bytes(Body)

    def Object(self, key):
        class Object:
            def get(_self):
                return {"Body": io.BytesIO(self.objects[key])}
        return Object()


class RuntimeClient:
    def __init__(self):
        self.sessions = {}
        self.messengers = []
        self.lose_response = False

    def messenger(self):
        result = RecordingMessenger()
        self.messengers.append(result)
        return result

    def invoke_agent_runtime(self, **kwargs):
        session_id = kwargs["runtimeSessionId"]
        if session_id not in self.sessions:
            self.sessions[session_id] = MettleAgentCoreRuntime(workflows=WorkflowRegistry(messenger_factory=self.messenger))
        request = json.loads(kwargs["payload"])
        response = self.sessions[session_id].handle(request, session_id=session_id)
        if self.lose_response and request["operation"] == "review":
            raise RuntimeError("connection lost after execution")
        return {"statusCode": 200, "response": io.BytesIO(json.dumps(response).encode())}


def test_cold_recovery_after_two_days_preserves_gate_and_does_not_repeat_messages():
    table, bucket, client = MemoryTable(), PrivateBucket(), RuntimeClient()
    now = [1_000_000]
    gateway = DurableAgentCoreWorkflowGateway(client=client, runtime_arn=RUNTIME_ARN, table=table, packet_bucket=bucket, clock=lambda: now[0])
    token = set_principal("contractor-one")
    try:
        first, _ = gateway.create(payload(), idempotency_key="cold_create_123")
        assert "checkpoint" not in first.model_dump()
        client.sessions.clear()
        now[0] += 2 * 86400
        reviewed = gateway.review(first.workflow_id, review_request(first), idempotency_key="cold_review_123")
        sent = sum(len(m.deliveries) for m in client.messengers)
        assert sent > 0
        client.sessions.clear()
        assert gateway.get(first.workflow_id).recovery_hold is False
        replay = gateway.review(first.workflow_id, review_request(first), idempotency_key="cold_review_123")
        assert replay == reviewed
        assert sum(len(m.deliveries) for m in client.messengers) == sent
        if reviewed.snapshot.interrupts:
            result = gateway.resume(first.workflow_id, ResumeWorkflowRequest(interrupt_id=reviewed.snapshot.interrupts[0].interrupt_id, decision="Show the entire equipment service access area"), idempotency_key="cold_resume_123")
            assert result.snapshot.deliveries[:sent] == reviewed.snapshot.deliveries
        other = set_principal("different-contractor")
        try:
            with pytest.raises(WorkflowNotFound):
                gateway.get(first.workflow_id)
        finally:
            reset_principal(other)
    finally:
        reset_principal(token)


def test_uncertain_outreach_is_held_even_with_a_new_idempotency_key():
    client = RuntimeClient()
    gateway = DurableAgentCoreWorkflowGateway(client=client, runtime_arn=RUNTIME_ARN, table=MemoryTable(), packet_bucket=PrivateBucket())
    token = set_principal("contractor-one")
    try:
        first, _ = gateway.create(payload(), idempotency_key="uncertain_create")
        client.lose_response = True
        with pytest.raises(AgentCoreGatewayError):
            gateway.review(first.workflow_id, review_request(first), idempotency_key="uncertain_review")
        assert gateway.get(first.workflow_id).recovery_hold is True
        sent = sum(len(m.deliveries) for m in client.messengers)
        assert sent > 0
        client.sessions.clear()
        with pytest.raises(WorkflowConflict, match="uncertain"):
            gateway.review(first.workflow_id, review_request(first), idempotency_key="different_review")
        assert sum(len(m.deliveries) for m in client.messengers) == sent
    finally:
        reset_principal(token)


def test_background_check_restores_without_browser_or_warm_session():
    client = RuntimeClient()
    gateway = DurableAgentCoreWorkflowGateway(client=client, runtime_arn=RUNTIME_ARN, table=MemoryTable(), packet_bucket=PrivateBucket(), campaign_scheduler=FakeCampaignScheduler())
    token = set_principal("contractor-one")
    try:
        first, _ = gateway.create(payload(), idempotency_key="scheduled_create")
        reviewed = gateway.review(first.workflow_id, review_request(first), idempotency_key="scheduled_review")
    finally:
        reset_principal(token)
    client.sessions.clear()
    automation = reviewed.automation
    event = ScheduledCheckEvent(owner_hash=sha256(b"contractor-one").hexdigest(), workflow_id=first.workflow_id, schedule_name=automation.schedule_name, schedule_version=automation.schedule_version, logical_check_on=automation.logical_check_on)
    advanced, executed = gateway.run_scheduled_check(event)
    assert executed
    assert advanced.snapshot.plan.as_of == event.logical_check_on
    sent = sum(len(m.deliveries) for m in client.messengers)
    _, repeated = gateway.run_scheduled_check(event)
    assert not repeated
    assert sum(len(m.deliveries) for m in client.messengers) == sent
