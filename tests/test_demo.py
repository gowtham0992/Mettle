import pytest

from mettle.demo import CitationStage, DemoConflict, DemoStore, GateStatus, Priority


def test_demo_opening_events_have_distinct_chronology() -> None:
    campaign = DemoStore().snapshot()

    assert campaign.events[0].happened_at > campaign.events[1].happened_at


def test_demo_full_journey_preserves_distinct_event_timestamps() -> None:
    store = DemoStore()
    store.resolve_judgment(
        "code-c3",
        decision="Wide photo showing equipment and measured service clearance",
    )
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


def test_demo_rejects_insufficient_evidence_then_accepts_replacement() -> None:
    store = DemoStore()

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

    first = store.advance(idempotency_key="same-event")
    replay = store.advance(idempotency_key="same-event")

    assert replay.scenario_step == first.scenario_step == 1
    assert replay.metrics == first.metrics
    assert [event.event_id for event in replay.events] == [
        event.event_id for event in first.events
    ]


def test_demo_escalates_and_interrupts_near_deadline() -> None:
    store = DemoStore()
    store.advance(idempotency_key="one")
    store.advance(idempotency_key="two")
    campaign = store.advance(idempotency_key="three")

    assert campaign.priority is Priority.CRITICAL
    assert campaign.days_remaining == 2
    assert any(item.judgment_id == "deadline-choice" for item in campaign.judgments)

    blocked = store.advance(idempotency_key="four")
    assert blocked.scenario_step == campaign.scenario_step

    resumed = store.resolve_judgment(
        "deadline-choice",
        decision="Keep the current reinspection target and continue critical recovery",
    )
    assert resumed.metrics.contractor_decisions == 1


def test_resolving_code_gate_resumes_only_the_affected_citation() -> None:
    store = DemoStore()

    campaign = store.resolve_judgment(
        "code-c3",
        decision="Wide photo showing the equipment and measured service clearance",
    )
    mechanical = next(item for item in campaign.citations if item.citation_id == "3")
    gate = next(item for item in campaign.judgments if item.judgment_id == "code-c3")

    assert mechanical.stage is CitationStage.AWAITING_EVIDENCE
    assert mechanical.assignee == "Alex Kim · Alpine Mechanical"
    assert gate.status is GateStatus.RESOLVED
    assert campaign.metrics.contractor_decisions == 1

    with pytest.raises(DemoConflict, match="already resolved differently"):
        store.resolve_judgment("code-c3", decision="A conflicting second decision")


def test_final_packet_gate_appears_only_after_all_citations_are_ready() -> None:
    store = DemoStore()
    store.resolve_judgment(
        "code-c3",
        decision="Wide photo showing equipment and measured service clearance",
    )

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


def test_mechanical_evidence_event_waits_for_contractor_judgment() -> None:
    store = DemoStore()

    for step in range(4):
        campaign = store.advance(idempotency_key=f"blocked-{step}")

    assert campaign.scenario_step == 3
    store.resolve_judgment(
        "deadline-choice",
        decision="Keep the current reinspection target and continue critical recovery",
    )
    store.advance(idempotency_key="framing-after-deadline")
    campaign = store.advance(idempotency_key="blocked-on-code")
    assert campaign.scenario_step == 4
    mechanical = next(item for item in campaign.citations if item.citation_id == "3")
    assert mechanical.stage is CitationStage.NEEDS_JUDGMENT
    assert not any(item.judgment_id == "final-approval" for item in campaign.judgments)
