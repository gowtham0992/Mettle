# Agents for Humans: Building Mettle, an inspection-recovery agent that knows when to stop

> **Excerpt:** A failed inspection leaves a small contractor chasing trades, photos, and a reinspection deadline. Mettle runs that recovery with Strands and Amazon Bedrock AgentCore—and stops whenever professional judgment is required.

A failed residential inspection rarely ends with one clean task. A small contractor has to read a municipal notice, separate corrections by trade, chase replies and photographs over text, watch a reinspection date, and rebuild a proof packet for the next visit. The work lives across a PDF, message threads, job-site photos, and memory. One missed follow-up can mean another fee and another week of delay.

I built **Mettle** for that recovery window. It is my **Professional Agents** project for the Agents for Humans Hackathon: give it a failed-inspection notice, and it runs a citation-by-citation campaign toward reinspection while the licensed contractor keeps every consequential decision.

I did not arrive there immediately. My first concept was a community donation-drive coordinator. It sounded compassionate, but its supposed autonomy depended on volunteers manually updating inventory over a multi-week drive. I wanted a workflow with a real initiating event, work that unfolded against a clock, and clear moments when an agent should stop. A failed-inspection notice supplied all three.

The most important product decision was what I did **not** build: an AI building inspector. A model should not decide that work complies with code, and a polished answer does not become authority merely because it sounds certain. Mettle therefore separates authority three ways:

1. **Amazon Nova models** handle unstructured notice language and visible photo evidence on the Bedrock-backed paths.
2. **Deterministic Python** controls dates, state transitions, retries, permissions, and what Mettle is allowed to claim.
3. **The licensed contractor** decides interpretation, correction routing, deadline tradeoffs, and final release.

That division shaped the Strands graphs, the AWS deployment, and the interface.

## One workflow, end to end

The hackathon guidance favored one complete workflow over several partial ones. I focused on one operational incident: a failed rough-in inspection with several corrections and a reinspection clock.

1. The contractor pastes the failed-inspection notice—no project template or manually authored punch list first.
2. Mettle creates a typed correction docket while preserving the authority's source wording. The public `LIVE · STRANDS` path uses deterministic local extraction; the opt-in Bedrock and AgentCore paths use a Strands intake agent on Amazon Nova Micro.
3. Before any outreach is recorded, the contractor confirms who owns each correction and what proof to request.
4. Mettle coordinates only the open corrections and changes its follow-up cadence at server-selected T−7, T−3, T−2, T−1, and due-date checkpoints.
5. Evidence arrives through a bounded API operation. Visible sufficiency feeds the next chase decision; accepted citations stop receiving follow-ups.
6. At T−2, the contractor decides whether to keep or move the reinspection date.
7. Once every citation is ready, Mettle assembles the packet but blocks its release until final contractor approval.

The [public guided demo](https://d1ytth8asjpes8.cloudfront.net) compresses that multi-day campaign into ninety seconds using disclosed synthetic data. It consumes no model credit. A separate `LIVE · STRANDS` option proves the real graph and native interruption behavior, while authenticated users can invoke the deployed AgentCore path.

![Mettle product architecture](https://raw.githubusercontent.com/gowtham0992/Mettle/main/assets/architecture/mettle-product-architecture.png)

*The product view makes the campaign loop and its three professional-judgment gates explicit.*

![Mettle recovery command center](https://raw.githubusercontent.com/gowtham0992/Mettle/main/assets/submission/01-command-center.png)

*The guided sample keeps its synthetic-data label visible while showing the complete contractor journey.*

## The Strands graph, concretely

Mettle is not one prompt wrapped in a dashboard. It runs two `GraphBuilder` graphs. The recovery graph handles intake, planning, contractor review, coordination, ambiguity, and completion. A second graph replans open work and applies deadline-aware follow-ups.

The graph definition makes the control flow reviewable:

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
builder.set_hook_providers([
    AgentRunTraceHook(graph="recovery"),
    CorrectionReviewHook(),
    ContractorJudgmentHook(),
])
```

Three native Strands interrupts are product controls rather than decorative approval buttons:

- `correction-review` pauses before the first outreach record;
- `contractor-judgment` pauses when notice language needs professional interpretation;
- `deadline-tradeoff` pauses at T−2 while unresolved work remains.

Each hook listens for `BeforeNodeCallEvent`, calls `event.interrupt(...)`, and stores the validated response back in invocation state. The contractor's decision resumes the same graph session instead of starting a new prompt exchange.

I also wanted the autonomy to be inspectable without exposing private internals. Safe hooks emit only the graph name, node, specialist, sequence, status, and a bounded description. The Run receipt deliberately excludes prompts, chain-of-thought, credentials, runtime identifiers, and notice payloads.

![Mettle Run receipt](https://raw.githubusercontent.com/gowtham0992/Mettle/main/assets/submission/03-agent-run.png)

*The Run receipt shows specialist handoffs and the exact points where Mettle stopped for the contractor.*

## Evidence without pretending to inspect

Photo evidence was the hardest boundary to express honestly. A dedicated multimodal Strands Evidence Agent on Amazon Nova Lite receives a normalized JPEG plus requirements grounded in the notice. Its validated result can say that a requested label, location, clearance, or component is visible. It cannot say that the work complies with code.

Deterministic policy turns the findings into three outcomes: accept the evidence, request a more specific photo, or return the question to the contractor. A framing photo that omits the correction location and full clearance receives a request for a wider shot. Ambiguous pixels or ambiguous notice language do not become an optimistic pass.

The implementation became more reliable only after two failed AgentCore versions. Nova Lite sometimes answered in prose instead of selecting a generic structured-output tool. I replaced that path with a model adapter that exposes one Pydantic output contract and forces that exact tool through `tool_choice`:

```python
tool_spec = convert_pydantic_to_tool_spec(VisibleEvidenceFindings)
response = self.stream(
    messages=prompt,
    tool_specs=[tool_spec],
    tool_choice={"tool": {"name": tool_spec["name"]}},
)

if stop_reason != "tool_use":
    raise ValueError("Evidence model did not return the required tool output")
```

The output model permits only `shown`, `not_shown`, or `uncertain`, with extra fields forbidden. If the model does not return the contract, the citation cannot advance. That is what “fail closed” means here.

![Specific evidence re-request](https://raw.githubusercontent.com/gowtham0992/Mettle/main/assets/submission/02-evidence-rerequest.png)

*The sample rejects an insufficient framing photo and requests the missing visible context; it never labels the work code-compliant.*

## Deploying the workflow on AWS

The same operations run behind **Amazon Bedrock AgentCore Runtime**: start, review, resume, submit evidence, run the next deadline check, prepare the packet, approve it, and render the PDF. The runtime entrypoint validates a discriminated Pydantic union with `extra="forbid"`; mutation requests carry bounded idempotency keys. One paid acceptance run completed Nova Micro intake, a native interrupt and resume, Nova Lite evidence assessment, open-only replanning, the deadline gate, final approval, and PDF verification in one AgentCore session.

![Mettle AWS architecture](https://raw.githubusercontent.com/gowtham0992/Mettle/main/assets/architecture/mettle-aws-architecture.png)

*The public browser reaches one authenticated, throttled server boundary; credentials, model access, workflow state, and evidence stay behind it.*

The public application adds a deliberately narrow AWS boundary around that runtime:

- **Amazon CloudFront** serves the site from a private S3 origin through Origin Access Control and forwards `/api/*` without caching.
- **AWS WAF** applies managed common protections and an IP rate limit to API traffic.
- **Amazon Cognito** uses authorization code flow with PKCE. Self-registration is disabled, so paid model execution requires an admin-created account.
- **Amazon API Gateway** and **AWS Lambda** expose the product API. Every `/api/agentcore/*` route requires a Cognito JWT and is throttled to 1 request per second with a burst of 2.
- **Amazon DynamoDB** maps the hash of a verified Cognito subject to an AgentCore session and stores replay records with an eight-hour TTL. It does not persist email addresses or tokens.
- A second private **Amazon S3** bucket holds approved packets. Each PDF is checked against the runtime's SHA-256, encrypted with SSE-S3, retained for at most one day, and delivered through a 60-second presigned URL.

The browser never receives AWS credentials, the AgentCore runtime ARN, or its session identifier. The Lambda gateway owns the session and can invoke one exact Mettle runtime resource. The runtime role can invoke only Amazon Nova Micro and Nova Lite; Nova Pro is not granted. I ran AWS Access Analyzer against the checked-in identity policies and received zero findings.

I chose the models for their jobs rather than their size. Nova Micro handles bounded text extraction at lower cost. Nova Lite adds the multimodal capability needed for visible evidence. Deterministic policy handles everything that does not benefit from model uncertainty.

For AgentCore deployment, I used direct **CodeZip** rather than accepting the CLI's broader default CDK bootstrap. The deployer uploads one private, versioned S3 object and creates or updates only the tagged Mettle runtime. Immutable object versions make rollback concrete: I deployed a recorded older artifact, verified the runtime reached `READY`, restored the intended artifact, and verified it returned to `READY`.

Cost control is part of the design. The synthetic public journey makes zero Bedrock calls. Credit-metered routes sit behind Cognito, and the browser cannot choose model IDs or regions. Internet photo bodies are capped at 3.5 MB at the deployed edge, decoded, pixel-bounded, stripped of metadata, and re-encoded before the vision agent sees them. The adapter uses non-streaming Converse, avoiding a broader streaming permission for this operation.

One limitation matters: AgentCore runtime sessions are ephemeral. Mettle configures a 15-minute idle timeout and an eight-hour maximum lifetime. DynamoDB durably maps an authenticated user to the active session, and EventBridge Scheduler can wake the next checkpoint during the accelerated judge run, but this is not durable multi-day campaign memory. I would rather state that boundary than imply persistence that is not present.

> **Demo boundary:** `SAMPLE TRACE` is deterministic playback over synthetic data. `LIVE · STRANDS` runs the real graph with deterministic local notice extraction. The authenticated AgentCore path runs the graph with Nova-backed intake and evidence assessment. The interface and repository label these paths separately.

## Four failures that changed the build

The project reached AgentCore runtime version 12. The version count is less interesting than what failed along the way.

**Versions 10 and 11: the model did not select the output tool.** Generic structured output was unreliable for the vision path. I narrowed the model's responsibility to one evidence task and forced one validated output contract. Version 12 failed closed and completed the paid end-to-end acceptance workflow.

**Version 8: the artifact contained the wrong architecture.** The runtime zip accidentally included an x86_64 web-Lambda staging tree alongside ARM64 runtime dependencies and never became ready. The packaging pruner now removes and rejects repository-only build directories, and a regression test boots the packaged `src/` layout without relying on the local editable install.

**Version 7: the smoke test was wrong.** My acceptance check assumed every packet would have four pages. Seven communication records correctly pushed the packet onto a fifth page. I reproduced the structure locally and changed the smoke check to verify the expected page count, text, content type, and hash instead of a stale assumption.

**The correction-review retry consumed an interrupt.** A request with missing trade contacts correctly returned a validation error, but retrying the same idempotency key could reuse a consumed Strands interrupt and crash. The fix validates predictable roster errors before resuming the graph, preserving the checkpoint. A regression test now proves the repeated invalid request remains a stable `422` instead of becoming a `500`.

These failures pushed the implementation in the same direction: models work on bounded ambiguity; protocols and recovery behavior remain explicit and testable.

## What I deliberately left out

Mettle accepts several common pasted-notice shapes—alternate municipal headers, common date formats, numbered findings, and correction-section bullets—and preserves unfamiliar but clearly listed findings as review candidates instead of inventing a code reference or proof requirement. It still uses a small, bounded trade roster rather than pretending to understand every jurisdiction or specialty. Messaging is one-way and recorded by default. An opt-in Amazon SNS adapter can send only to one hashed, pre-approved personal demo number; it is not an inbound trade channel and is not a substitute for contractor consent or opt-out operations. The public sample compresses days into ninety seconds. EventBridge Scheduler advances that accelerated run, but there is no durable AgentCore Memory integration for a real multi-day campaign. Mettle never contacts an inspector and never claims code compliance autonomously.

Those are product boundaries, not footnotes. A small contractor does not need another chatbot that can discuss an inspection. They need the repetitive recovery work handled, the consequential decisions surfaced, and a trustworthy record at the end.

## Try Mettle

- **Live guided demo:** [d1ytth8asjpes8.cloudfront.net](https://d1ytth8asjpes8.cloudfront.net)—synthetic data, no AWS account required
- **Source and setup:** [github.com/gowtham0992/Mettle](https://github.com/gowtham0992/Mettle)—MIT licensed, public, and verified from an anonymous clone
- **Verification:** the offline Python and infrastructure suites run without AWS credentials or model spend; `npx agentcore validate --json` succeeds from a clean install
- **Hackathon track:** Professional Agents

**Notice in. Reinspection ready. Mettle handles the chase. The contractor decides.**

<!-- Builder Center publishing metadata:
Cover image: assets/architecture/mettle-product-architecture.png
Tags: Amazon Bedrock, Amazon Nova, Amazon Bedrock AgentCore, Strands Agents, AWS Lambda, Amazon DynamoDB, serverless, generative AI
Recommended inline images: mettle-product-architecture.png, 01-command-center.png, 03-agent-run.png, 02-evidence-rerequest.png, mettle-aws-architecture.png
-->
