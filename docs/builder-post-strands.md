# Agents for Humans: Designing Strands agents that stop for professional judgment

> **Excerpt:** Mettle uses Strands graphs to run inspection-recovery work across specialists, but its most important behavior is knowing exactly when autonomy must stop.

A failed building inspection creates two very different kinds of work. Some of it is repetitive: separate citations, assign follow-ups, check which evidence is still missing, and prepare a packet. Some of it is consequential: interpret ambiguous notice language, decide whether to keep a reinspection date, and release evidence to an authority.

I built **Mettle** for the first category without letting a model quietly claim the second. It is my Professional Agents entry for the Agents for Humans Hackathon. A contractor gives Mettle a failed-inspection notice; a Strands workflow turns it into a recovery campaign, runs the repeatable coordination, and interrupts only when licensed judgment is required.

That sounds like a prompt-design problem. It was actually a control-flow problem.

## Why one agent was the wrong abstraction

One large prompt could extract a notice, suggest assignments, describe a photo, and draft a packet. It would also blur four responsibilities that need different failure behavior:

- notice intake works with unstructured municipal language;
- campaign policy owns dates, status transitions, retries, and permissions;
- visual evidence assessment works with pixels and bounded requirements;
- the contractor owns interpretation and release.

Mettle therefore runs two Strands `GraphBuilder` graphs. The recovery graph handles notice intake, planning, correction review, coordination, ambiguity, and completion. The chase graph replans only unresolved work and applies deadline-aware follow-ups.

Deterministic Python policy is represented as a first-class graph node rather than hidden inside an agent prompt:

```python
builder = GraphBuilder()
builder.add_node(DeterministicNode(name="intake", function=self._intake), "intake")
builder.add_node(DeterministicNode(name="plan", function=self._plan), "plan")
builder.add_node(
    DeterministicNode(name="review_gate", function=self._review_gate),
    "review_gate",
)
builder.add_edge("intake", "plan")
builder.add_edge("plan", "review_gate")
```

This separation matters during failure. A model can return invalid structure or uncertain evidence. It cannot silently change a deadline, replay outreach, or grant itself permission to release a packet.

## Interrupts are authority boundaries

Many agent demonstrations add an approval button after the model has already made the important decision. Mettle uses native Strands interrupts before the protected action.

The first gate runs before outreach. Notice extraction may suggest a trade and visible-proof requirement, but the contractor must confirm every correction route:

```python
response = event.interrupt(
    "correction-review",
    reason={
        "notice_id": notice.notice_id,
        "citations": [
            citation.model_dump(mode="json")
            for citation in notice.citations
        ],
    },
)
review = CorrectionReview.model_validate_json(str(response))
```

Validation requires the review to include every citation exactly once, assign a known trade, and supply bounded evidence requirements. Only then does the graph rebuild the campaign plan and continue.

Two other gates protect different decisions:

1. `contractor-judgment` pauses when a citation needs code interpretation or a visible-proof requirement cannot be derived safely.
2. `deadline-tradeoff` pauses at T−2 when unresolved work remains and the contractor must keep or move the reinspection date.

The final packet has a separate approval boundary. Assembly can be autonomous; release cannot.

These are not generic “are you sure?” dialogs. Each interrupt has a named reason, validated response, allowed state transition, and observable position in the graph.

## A specialist that can describe evidence but cannot certify it

The visual boundary was the hardest one to make honest. A construction photo can show a panel label, a nail plate, or the surrounding wall location. It cannot prove hidden work, and a language model is not a building official.

Mettle gives a dedicated Strands Evidence Agent on Amazon Nova Lite only the image and requirements grounded in the failed-inspection notice. Its system prompt prohibits code interpretation, hidden-work inference, compliance certification, and unreadable measurements.

The output contract permits three verdicts per requirement: `shown`, `not_shown`, or `uncertain`. The model adapter exposes exactly one Pydantic tool and forces that tool selection:

```python
tool_spec = convert_pydantic_to_tool_spec(output_model)
response = self.stream(
    messages=prompt,
    tool_specs=[tool_spec],
    tool_choice={"tool": {"name": tool_spec["name"]}},
)

if stop_reason != "tool_use":
    raise ValueError("Evidence model did not return the required tool output")
```

Deterministic policy then checks that every requirement was returned exactly once. A missing item becomes a specific re-request. An uncertain item becomes contractor review. Only a complete set of `shown` findings records evidence as sufficient—and even that result explicitly says it is not a code-compliance decision.

This fail-closed path came from a real deployment failure. Earlier AgentCore runtime versions sometimes received conversational prose instead of the expected structured result. Making the output contract smaller and forcing one tool produced the reliable version 12 path used by Mettle today.

## Making multi-agent work inspectable

An architecture diagram can claim anything, so Mettle exposes a bounded **Run receipt** inside the product. Safe hooks emit the graph name, node, specialist, sequence, and status. A judge can see intake hand off to planning, the graph pause for correction review, coordination resume, and the evidence specialist run.

The trace deliberately excludes prompts, model reasoning, credentials, runtime identifiers, and notice payloads. Inspectability should not become a data leak.

The public product labels execution modes instead of blending them:

- `LIVE · STRANDS` runs the real graph and native interruptions with deterministic local notice extraction.
- `SAMPLE CAMPAIGN · SYNTHETIC DATA` compresses the complete multi-day journey without model spend.
- the authenticated cloud path runs the typed workflow on Amazon Bedrock AgentCore Runtime with Nova-backed intake and evidence assessment.

![Mettle Run receipt](https://raw.githubusercontent.com/gowtham0992/Mettle/main/assets/submission/03-agent-run.png)

*The Run receipt exposes specialist handoffs and the exact point where professional judgment interrupted execution.*

## What I learned

The strongest human-in-the-loop design is not “a human can edit the answer.” It is a precise statement of authority:

- the model may structure unstructured input;
- deterministic policy may execute previously approved rules;
- the workflow must stop before interpretation, schedule tradeoffs, or release;
- every resume must be validated and replay-safe.

Strands made those boundaries executable. Its graphs gave each responsibility a visible place, and native interrupts let the contractor resume the same workflow instead of starting a new chat.

Mettle is intentionally narrow: several common pasted-notice shapes, a bounded trade roster, visible-evidence sufficiency rather than compliance, and no inbound SMS interpretation. Unfamiliar numbered findings become grounded contractor-review candidates instead of fabricated code or proof requirements. That narrowness is what lets the complete workflow be real.

## Try Mettle

- **Public guided demo:** [d1ytth8asjpes8.cloudfront.net](https://d1ytth8asjpes8.cloudfront.net)
- **MIT-licensed source:** [github.com/gowtham0992/Mettle](https://github.com/gowtham0992/Mettle)
- **Architecture:** [Mettle product architecture](https://raw.githubusercontent.com/gowtham0992/Mettle/main/assets/architecture/mettle-product-architecture.png)
- **Verification:** all 137 tests run without AWS credentials or model spend

**Mettle handles the chase. The contractor decides.**

<!-- Builder Center publishing metadata:
Cover image: assets/architecture/mettle-product-architecture.png
Tags: Strands Agents, Amazon Bedrock, Amazon Nova, agents, human in the loop, generative AI
Recommended inline images: 03-agent-run.png, 02-evidence-rerequest.png, mettle-product-architecture.png
-->
