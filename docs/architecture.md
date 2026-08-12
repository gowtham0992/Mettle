# Mettle separates agent judgment from enforceable recovery rules

Mettle is a modular Python application with one durable domain model. Strands agents may extract, communicate, and assess evidence, but deterministic policy controls deadlines, approvals, and what the system is allowed to claim.

## Constraints

- Development must work before AWS credits arrive.
- The demo uses synthetic contractor, property, trade, and inspection data.
- No model output may certify code compliance.
- Ambiguous code interpretation and final packet submission require a human decision.
- A failed or unavailable model must not corrupt campaign state.
- The first demo handles one project, one notice format, and three trades.

## Recommended boundaries

### Domain core

Pydantic models represent notices, citations, recovery actions, and judgment requests. Pure functions calculate urgency and escalation from an injected date. This layer has no network or model dependency.

### Agent adapters

Strands agents translate unstructured input into the domain contracts. Their structured output is validated before it enters campaign state. The first adapter is the notice-intake agent; communication and evidence agents follow as separate nodes.

The opt-in Bedrock intake adapter configures Nova Micro with explicit region,
token, timeout, retry, and input limits. AWS errors are reduced to a service
code and request ID; upstream messages and notice contents are never copied
into caller-facing failures. The deterministic parser remains the default.

### Orchestration

The working Strands graph runs `intake -> plan -> coordinate -> judgment gate -> contractor-directed coordination -> finish`. A graph interrupt pauses before code interpretation, returns a judgment card to the contractor, and resumes without replaying the initial outreach. The application then binds notice-anchored evidence assessment and contractor-approved packet assembly to that workflow state.

### External ports

SMS, object storage, model providers, and packet rendering live behind small interfaces. The demo begins with recording fakes. Twilio, Amazon S3, Amazon Bedrock, and AgentCore can replace those fakes independently.

The evidence lab uses a trusted catalog of synthetic photo fixtures. A deterministic adapter maps observable requirements in the notice to server-controlled capabilities, rejects missing views or scale, and routes unknown requirement language to manual review. This is a safe contract test for the future Bedrock vision adapter; it does not infer code compliance.

Packet generation begins only when the latest evidence for every citation is accepted. A separate final approval record blocks PDF download until the contractor approves the assembled packet. ReportLab renders the notice, evidence requirements, synthetic images, safety boundary, and communication record from validated server state; client-provided paths or filenames never reach the renderer.

### Local application boundary

FastAPI exposes bounded workflow creation, retrieval, and resume endpoints to the command center. A thread-safe in-memory registry owns each stateful Strands session, caps the number of runs, and protects create and resume operations with idempotency keys. It is a development boundary, not durable production storage.

## Why this structure

Putting all behavior inside agent prompts would produce an impressive but untestable demo. Keeping all behavior deterministic would miss the hackathon's agentic thesis. The boundary is deliberate: models handle language and evidence; code enforces state transitions, deadlines, idempotency, and human-approval policy.

## Failure behavior

- Invalid structured output is rejected and leaves the campaign unchanged.
- Duplicate inbound messages are ignored by an idempotency key.
- SMS failure records an event and schedules a retry; it never marks a citation complete.
- Unclear evidence creates a re-request or judgment item; it never certifies completion.
- A missed deadline moves the campaign to critical review instead of silently rescheduling.

## Risk-ordered build slices

1. **Notice to campaign plan:** prove traceable extraction, deadline behavior, and judgment routing without a model.
2. **Local Strands orchestration:** run deterministic contract nodes, recorded outreach, and a resumable human interrupt. **Complete.**
3. **Recorded communication loop:** receive simulated SMS events with retry and idempotency behavior.
4. **Evidence assessment:** compare synthetic photos to notice-anchored requirements and produce a specific re-request. **Local adapter complete.**
5. **Human interrupts:** pause and resume the graph for ambiguous language and final packet approval. **Complete.**
6. **Demo interface and packet:** show the recovery timeline and generate a citation-to-evidence PDF. **Complete.**
7. **AWS deployment:** move the graph to AgentCore and add Bedrock, storage, memory, and observability. **Bedrock intake adapter complete; live verification and AgentCore remain.**

## Decisions we can reverse later

The database, SMS provider, and production frontend hosting remain intentionally undecided. FastAPI and the dependency-free browser interface are established for the local demo, but neither constrains the external ports.
