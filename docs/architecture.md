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

Strands agents translate unstructured input into the domain contracts. Their structured output is validated before it enters campaign state. The notice-intake agent and multimodal evidence agent are separate specialists; communication remains an enforceable graph node behind a provider interface.

The opt-in Bedrock intake adapter configures Nova Micro with explicit region,
token, timeout, retry, and input limits. AWS errors are reduced to a service
code and request ID; upstream messages and notice contents are never copied
into caller-facing failures. The deterministic parser remains the default.

### Orchestration

The intake graph runs `intake -> plan -> correction review -> coordinate -> judgment gate -> contractor-directed coordination -> finish`. The first interrupt returns every extracted citation before outreach; the contractor must confirm its assigned trade, closure route, and proof requirements, and the server rejects evidence while that review remains open. The same graph session then records notice-anchored requests without replaying intake. A second chase graph runs `replan open -> follow up -> deadline gate -> finish check`: deterministic policy chooses the next T−7/T−3/T−2/T−1/deadline checkpoint, removes citations with accepted evidence, records idempotent follow-ups for only the remainder, and interrupts at T−2 for the contractor's keep-date-or-reschedule judgment. The browser can compress time for a judge, but cannot choose campaign dates.

### External ports

Outbound messaging, object storage, model providers, scheduling, and packet rendering live behind small interfaces. The demo begins with recording fakes. Amazon SNS, Amazon S3, Amazon Bedrock, AgentCore, and EventBridge Scheduler can replace those fakes independently. Messaging is intentionally one-way: Mettle sends a bounded request but does not ingest SMS replies or pretend a carrier thread is workflow state.

The evidence lab keeps a trusted catalog of synthetic photo fixtures as a reliable fallback and also accepts real JPEG/PNG uploads. The server caps the raw body, decodes and bounds pixels, removes metadata, and re-encodes to JPEG before invoking a dedicated multimodal Strands Evidence Agent on Nova Lite. The model adapter deliberately uses non-streaming Converse so the runtime does not need a broader streaming permission for this bounded assessment. The agent returns one validated finding per notice requirement; deterministic policy derives accepted, rejected, or manual-review status and never asks the model to infer code compliance. Idempotency fingerprints include the normalized image bytes so retries cannot repeat model spend.

Strands `BeforeNodeCallEvent` and `AfterNodeCallEvent` hooks record a safe execution trace containing only graph name, node, specialist, sequence, and status. Evidence assessments add the same high-level trace around requirement grounding, multimodal inspection, and policy application. The command center renders this as the Run receipt; prompts, notice contents, model reasoning, credentials, and private runtime identifiers are intentionally excluded.

Packet generation begins only when the latest evidence for every citation is accepted. A separate final approval record blocks PDF download until the contractor approves the assembled packet. ReportLab renders the notice, evidence requirements, trusted fixture or normalized uploaded images, safety boundary, and communication record from validated server state; client-provided paths or filenames never reach the renderer.

### Local application boundary

FastAPI exposes bounded workflow creation, retrieval, correction-review, resume, evidence, packet, and next-check endpoints to the command center. A thread-safe in-memory registry owns each stateful Strands session, caps the number of runs, and protects every mutation with idempotency keys. It is a development boundary, not durable production storage.

### AgentCore runtime boundary

`agentcore_app.py` hosts the same registry behind the official AgentCore Python
runtime. A discriminated JSON contract permits only the named workflow operations,
forbids extra fields, bounds idempotency keys, and converts internal failures
to quiet error codes. Logs contain only a one-way session reference; notice
text and credentials are never logged.

AgentCore routes a runtime session to isolated compute, so a `start` and
`resume` using the same runtime session ID reach the same in-memory Strands
graph. This is not durable persistence: the state disappears when the session
expires or the runtime stops. Mettle exposes that limitation instead of
pretending AgentCore Memory has already been integrated.

### Dashboard-to-AgentCore boundary

The FastAPI server exposes a separate, opt-in AgentCore workflow surface. The
browser submits the same bounded Mettle request but cannot provide a runtime
ARN, AWS profile, region, or AgentCore session ID. A process-local gateway
generates and owns each session ID, caches the latest validated workflow
envelope, and maps only the public Mettle workflow ID back to the cloud
session.

The gateway serializes cloud operations for this single-operator demo, caps
both successful and retryable creation attempts, rejects changed idempotency
replays before invocation, and reuses the original session after an uncertain
transport failure. This limits duplicate model spend and prevents concurrent
resume calls from racing one stateful runtime session. It is not an internet-
facing authorization design: the server binds to loopback and AgentCore is
disabled unless the operator explicitly enables it at startup.

### Public serverless boundary

The public dashboard keeps static assets in a private S3 bucket readable only
through CloudFront Origin Access Control. CloudFront terminates TLS, applies
security headers and AWS WAF, and forwards `/api/*` to an HTTP API backed by
Lambda. Deterministic demo routes remain public; API
Gateway requires a Cognito access-token JWT for every `/api/agentcore/*` route.
Self-registration is disabled, the browser uses authorization code with PKCE,
and no browser receives AWS credentials.

The Lambda never uses deployment credentials. Its execution role can invoke
only the exact Mettle AgentCore runtime ARN and its `DEFAULT` endpoint, read and conditionally update one
DynamoDB table, and write contractor-approved packets beneath one private S3
bucket. It cannot create or update runtimes, list either bucket, scan the table,
or call IAM. DynamoDB keys contain only a hash of the verified Cognito subject;
each workflow and idempotency attempt is therefore caller-scoped without
persisting an email address or access token. Records expire with the AgentCore
session after eight hours.

After a successful authenticated mutation, deterministic campaign policy
selects the next logical checkpoint. The gateway creates a versioned, one-time
EventBridge schedule targeting a private Lambda worker. Its payload contains no
phone number, notice text, property address, or AgentCore session identifier.
It carries only an owner hash, workflow identifier, logical date, schedule
name, and version. The worker reloads the caller-scoped mapping from DynamoDB
and rejects stale versions before invoking the same AgentCore session.
Schedules delete after completion, retry twice, and send exhausted events to
an encrypted dead-letter queue. The 90-second demo cadence proves autonomous
wake-up inside the eight-hour runtime-session boundary; durable multi-day
campaigns require a future persistence layer.

Generated PDFs are integrity-checked, stored encrypted for at most one day,
and returned through a 60-second presigned download. Internet photo bodies are
capped at 3.5 MB before the existing decode, pixel-bound, metadata-strip, and
JPEG re-encode boundary. Tight route-level API Gateway throttling and WAF rate
limiting cap both abuse and accidental model spend. Reserved concurrency is
intentionally omitted because this account's regional concurrency quota is too
small to reserve safely without impairing other functions.

The deployment boundary uses direct CodeZip deployment rather than the CLI's
default CDK bootstrap. A private, versioned S3 object holds the artifact. The
runtime role can invoke only Nova Micro for text, Nova Lite for vision, and publish AgentCore telemetry. A
separate deployer role can pass only that execution role and manage only
Project-tagged Mettle runtimes.

## Why this structure

Putting all behavior inside agent prompts would produce an impressive but untestable demo. Keeping all behavior deterministic would miss the hackathon's agentic thesis. The boundary is deliberate: models handle language and evidence; code enforces state transitions, deadlines, idempotency, and human-approval policy.

## Failure behavior

- Invalid structured output is rejected and leaves the campaign unchanged.
- Duplicate outbound delivery attempts are ignored by an idempotency key.
- Amazon SNS failure fails closed and never records a message as sent or marks a citation complete; a successful provider receipt is cached for replay-safe retries within the session.
- Unclear evidence creates a re-request or judgment item; it never certifies completion.
- A missed deadline moves the campaign to critical review instead of silently rescheduling.

## Risk-ordered build slices

1. **Notice to campaign plan:** prove traceable extraction, deadline behavior, and judgment routing without a model.
2. **Local Strands orchestration:** run deterministic contract nodes, recorded outreach, and a resumable human interrupt. **Complete.**
3. **Deadline chase loop:** replan open citations, record scheduled follow-ups with replay safety, stop on accepted evidence, and interrupt at the T−2 tradeoff. **Complete locally and through the deployed AgentCore-compatible contract.**
4. **Evidence assessment:** compare trusted fixtures or normalized real photos to notice-anchored requirements and produce a specific re-request or judgment interrupt. **Local fixture adapter and dedicated Strands Evidence Agent on Bedrock complete; its model adapter forces one validated evidence-decision tool rather than accepting free-form output.**
5. **Human interrupts:** pause and resume the graph for ambiguous language and final packet approval. **Complete.**
6. **Demo interface and packet:** show the recovery timeline, inspectable Run receipt, and citation-to-evidence PDF. **Complete.**
7. **AWS runtime:** host the graph behind AgentCore's strict session boundary,
   package it as CodeZip, and define least-privilege deployment and rollback.
   **Complete: runtime version 12 is deployed, immutable-artifact rollback was
   exercised on the real demo runtime, and live acceptance covers start,
   contractor review with zero pre-approval outreach, resume, vision, T−3/T−2
   chase behavior, replay safety, approval, and PDF integrity in one AgentCore
   session.**
8. **Public durability:** user-scoped AgentCore session mapping, idempotency,
   private packet storage, Cognito authentication, and a CloudFront/Lambda edge.
   **Deployed behind CloudFront with private origins, WAF, Cognito-protected
   paid routes, and a public deterministic judge journey.**
9. **Autonomous wake-up:** create one-time EventBridge schedules, invoke a
   private worker, reject stale events, and surface failures through a DLQ.
   **Deployed and verified end to end: a live synthetic workflow advanced from
   schedule version 1 to version 2, then the follow-on smoke schedule was cancelled.**
10. **One-way messaging:** keep recording as the safe default and allow Amazon
    SNS delivery only to a hashed, pre-approved personal demo destination.
    **Complete in code; AWS messaging enrollment and live-send verification are pending.**

## Decisions we can reverse later

The public demo uses DynamoDB, private S3, CloudFront, API Gateway, Lambda,
Cognito, and WAF; the local FastAPI path remains independent for offline
rehearsals. Amazon SNS is the only delivery adapter. It is disabled unless the
runtime receives a SHA-256 allowlist for one demo destination, and every other
phone number falls back to a recorded delivery without contacting a carrier.
