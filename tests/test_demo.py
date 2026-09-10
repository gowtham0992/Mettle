import pytest

from mettle.demo import CitationStage, DemoConflict, DemoStore, GateStatus, Priority


def approve_routes(store: DemoStore) -> None:
    store.resolve_judgment(
        "route-review",
        decision="Wide photo showing equipment and measured service clearance",
    )


def test_resolution_keys_survive_checkpoint_and_reset_with_the_session():
    store = DemoStore()
    decision = "Approve the prepared routes"
    first = store.resolve_judgment("route-review", decision=decision, idempotency_key="resolution-1")
    assert "resolution_keys" not in store.dump_state().model_dump()
    assert all(isinstance(value, str) for value in store.dump_state().resolved_decisions.values())
    restored = DemoStore.from_state(store.dump_state())
    assert restored.resolve_judgment("route-review", decision=decision, idempotency_key="resolution-1") == first
    with pytest.raises(DemoConflict, match="different decision"):
        restored.resolve_judgment("deadline-choice", decision=decision, idempotency_key="resolution-1")
    restored.reset()
    assert restored.resolve_judgment("route-review", decision="New route approval", idempotency_key="resolution-1").metrics.contractor_decisions == 1


def test_demo_opening_state_has_zero_outreach_before_contractor_approval() -> None:
    campaign = DemoStore().snapshot()

    assert campaign.metrics.messages_handled == 0
    assert all(citation.assignee is None for citation in campaign.citations)
    assert not any(event.kind == "message_sent" for event in campaign.events)


def test_demo_full_journey_preserves_distinct_event_timestamps() -> None:
    store = DemoStore()
    approve_routes(store)
    for step in range(3):
        store.advance(idempotency_key=f"timestamp-before-deadline-{step}")
    store.resolve_judgment(
        "deadline-choice",
        decision="Keep the current reinspection target and continue critical recovery",
    )
    for step in range(3, 6):
        campaign = store.advance(idempotency_key=f"timestamp-after-deadline-{step}")
    store.resolve_judgment("final-approval", decision="Approved for download")
    campaign = store.snapshot()

    timestamps = [event.happened_at for event in campaign.events]
    assert len(timestamps) == len(set(timestamps))
    assert timestamps == sorted(timestamps, reverse=True)
    assert campaign.metrics.automated_actions == 15
    assert campaign.metrics.contractor_decisions == 3


def test_demo_rejects_insufficient_evidence_then_accepts_replacement() -> None:
    store = DemoStore()
    approve_routes(store)

    store.advance(idempotency_key="step-one")
    rejected = store.advance(idempotency_key="step-two")
    framing = next(item for item in rejected.citations if item.citation_id == "2")

    assert framing.stage is CitationStage.EVIDENCE_REJECTED
    assert "wider location view" in framing.evidence_note
    assert rejected.events[0].kind == "evidence_rejected"

    store.advance(idempotency_key="step-three")
    store.resolve_judgment(
        "deadline-choice",
        decision="Keep the current reinspection target and continue critical recovery",
    )
    accepted = store.advance(idempotency_key="step-four")
    framing = next(item for item in accepted.citations if item.citation_id == "2")
    assert framing.stage is CitationStage.READY


def test_demo_replay_has_a_single_effect() -> None:
    store = DemoStore()
    approve_routes(store)

    first = store.advance(idempotency_key="same-event")
    replay = store.advance(idempotency_key="same-event")

    assert replay.scenario_step == first.scenario_step == 1
    assert replay.metrics == first.metrics
    assert [event.event_id for event in replay.events] == [
        event.event_id for event in first.events
    ]


def test_demo_escalates_and_interrupts_near_deadline() -> None:
    store = DemoStore()
    approve_routes(store)
    store.advance(idempotency_key="one")
    store.advance(idempotency_key="two")
    campaign = store.advance(idempotency_key="three")

    assert campaign.priority is Priority.CRITICAL
    assert campaign.days_remaining == 2
    assert any(item.judgment_id == "deadline-choice" for item in campaign.judgments)

    with pytest.raises(DemoConflict, match="blocked"):
        store.advance(idempotency_key="four")
    assert store.snapshot().scenario_step == campaign.scenario_step

    resumed = store.resolve_judgment(
        "deadline-choice",
        decision="Keep the current reinspection target and continue critical recovery",
    )
    assert resumed.metrics.contractor_decisions == 2


def test_resolving_code_gate_resumes_only_the_affected_citation() -> None:
    store = DemoStore()

    campaign = store.resolve_judgment(
        "route-review",
        decision="Wide photo showing the equipment and measured service clearance",
    )
    mechanical = next(item for item in campaign.citations if item.citation_id == "3")
    gate = next(item for item in campaign.judgments if item.judgment_id == "route-review")

    assert mechanical.stage is CitationStage.AWAITING_EVIDENCE
    assert mechanical.assignee == "Alex Kim · Alpine Mechanical"
    assert campaign.metrics.messages_handled == 3
    assert any(item.kind == "message_sent" for item in campaign.events)
    assert gate.status is GateStatus.RESOLVED
    assert campaign.metrics.contractor_decisions == 1

    with pytest.raises(DemoConflict, match="already resolved differently"):
        store.resolve_judgment("route-review", decision="A conflicting second decision")


def test_final_packet_gate_appears_only_after_all_citations_are_ready() -> None:
    store = DemoStore()
    approve_routes(store)

    for step in range(3):
        store.advance(idempotency_key=f"event-{step}")
    store.resolve_judgment(
        "deadline-choice",
        decision="Keep the current reinspection target and continue critical recovery",
    )
    before_packet = None
    for step in range(3, 5):
        before_packet = store.advance(idempotency_key=f"event-{step}")

    assert before_packet is not None
    assert before_packet.metrics.citations_ready == 3
    assert not any(
        item.judgment_id == "final-approval" for item in before_packet.judgments
    )

    packet = store.advance(idempotency_key="event-5")
    assert packet.scenario_complete is True
    assert any(item.judgment_id == "final-approval" for item in packet.judgments)


def test_demo_cannot_advance_before_route_approval() -> None:
    store = DemoStore()

    with pytest.raises(DemoConflict, match="blocked"):
        store.advance(idempotency_key="blocked-before-route-approval")
    campaign = store.snapshot()

    assert campaign.scenario_step == 0
    assert campaign.metrics.messages_handled == 0
