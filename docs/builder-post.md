# Agents for Humans: Building Mettle, an inspection-recovery agent that knows when to stop

A failed residential inspection rarely ends with one clean task. A small contractor has to read a municipal notice, separate corrections by trade, explain them to subcontractors, chase photographs, watch a reinspection deadline, and assemble proof for the next visit. The work lives across a PDF, text threads, job-site photos, and memory.

I built **Mettle** for that recovery window. It starts with the failed-inspection notice itself and runs a citation-by-citation campaign toward reinspection. It handles the repetitive chase while reserving code interpretation, schedule tradeoffs, and final packet approval for the licensed contractor.

The central product decision was not to build an AI building inspector. A model should not decide that work complies with code, and a polished answer does not become authority merely because it sounds certain. Mettle instead uses three explicit authority lanes:

1. Amazon Nova models handle unstructured notice language and visible photo evidence.
2. Deterministic Python controls dates, state transitions, retries, permissions, and permitted claims.
3. The contractor decides interpretation, deadline tradeoffs, correction routing, and final release.

That separation shaped both the Strands workflow and the interface.

## One workflow, end to end

The hackathon guidance encouraged one complete workflow instead of several partial ones. Mettle therefore focuses on a single incident: a failed rough-in inspection with several corrections and a reinspection clock.

The flow is:

`notice → typed correction docket → contractor routing review → trade coordination → evidence assessment → deadline decision → packet approval`

A Strands intake agent on Amazon Nova Micro extracts the docket from unstructured notice text while preserving the authority's source language. A Strands `GraphBuilder` workflow then moves the campaign through planning, review, coordination, and follow-up. A second graph handles deadline checks at progressively more urgent checkpoints.

Three native Strands interrupts are load-bearing product controls, not decorative approval buttons:

- correction routing pauses before any outreach is recorded;
- ambiguous notice language pauses before Mettle invents an evidence requirement;
- the T−2 checkpoint pauses before Mettle chooses whether to keep or move the reinspection date.

The workflow resumes from the same interruption after the contractor decides. Safe graph hooks feed an Agent Run panel with node, specialist, sequence, and status, while excluding prompts, model reasoning, credentials, runtime identifiers, and private payloads.

## Evidence without pretending to inspect

Photo evidence was the hardest boundary to express honestly. A dedicated multimodal Strands Evidence Agent on Amazon Nova Lite sees a normalized JPEG or PNG plus a notice-grounded visible requirement. Its structured response can say that the required label, location, clearance, or component is visible; it cannot say that the work complies with code.

Deterministic policy converts that result into one of three outcomes:

- accept the evidence;
- request a more specific photo;
- return the question to the contractor.

That design produces a useful autonomous moment without manufacturing professional authority. When a framing photo fails to show the correction location and full clearance, Mettle asks for a wider location photo. When the notice itself is ambiguous, it stops.

## Deploying the agent on AWS

The same typed operations run on Amazon Bedrock AgentCore Runtime: start, review, resume, add evidence, run a deadline check, prepare a packet, and approve release. The browser never receives AWS credentials or the runtime ARN.

The public product boundary uses:

- Amazon CloudFront and AWS WAF at the edge;
- private Amazon S3 for static assets and approved packets;
- Amazon Cognito with PKCE for the paid runtime path;
- Amazon API Gateway and AWS Lambda for the web and gateway APIs;
- Amazon DynamoDB for authenticated user-to-session mappings;
- Amazon Bedrock AgentCore Runtime for managed agent execution.

The public guided sample uses synthetic data and deterministic playback so anyone can evaluate the complete product without credentials or model spend. The interface labels that path explicitly. A separate `LIVE · STRANDS` flow demonstrates the real graph and native interruption behavior, and the authenticated path invokes AgentCore.

## What failed on the way

The most useful engineering lesson came from a failed deployment. An early AgentCore version asked Nova Lite to select a generic operation tool. The model sometimes returned prose instead of the required tool call. Rather than hiding that behind retries, I narrowed the model's job: the runtime contract stayed typed and deterministic, and multimodal reasoning moved into a dedicated evidence agent with one bounded task. The next version failed closed and passed the end-to-end acceptance workflow.

Another failure appeared during review. A correction-routing request with missing trade contacts correctly returned a validation error, but retrying the same idempotency key could reuse a consumed Strands interrupt and crash. The fix was to validate predictable roster errors before resuming the graph, preserving the checkpoint for a safe retry. A regression test now proves the same bad retry remains a stable validation error rather than becoming a 500.

These failures reinforced the same principle: let models work on ambiguity, but keep protocol, authority, and recovery behavior explicit.

## The result

Mettle now demonstrates one complete recovery campaign with a real Strands graph, native human interrupts, a dedicated evidence agent, deadline-aware replanning, idempotent operations, approval-gated PDF generation, and a deployed AgentCore runtime. The repository includes 108 behavior-focused tests, a clean-clone setup path, a public live demo, and the full architecture.

The product is deliberately narrow. It supports one representative residential notice shape and three trade categories; messaging is recorded rather than delivered; the public sample compresses days into seconds; and Mettle never contacts an inspector or claims code compliance autonomously.

That narrowness is the point. Small contractors do not need another chatbot that can discuss an inspection. They need the repetitive recovery work handled, the important decisions surfaced, and a trustworthy record at the end.

**Mettle handles the chase. The contractor decides.**

## Project links

- Live demo: https://d1ytth8asjpes8.cloudfront.net
- Source and setup: https://github.com/gowtham0992/Mettle
- Architecture: https://github.com/gowtham0992/Mettle/blob/main/assets/architecture/mettle-architecture.png
