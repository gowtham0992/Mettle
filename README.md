# Mettle

![Mettle logo](assets/brand/mettle-devpost-logo.png)

**From failed inspection to reinspection-ready.**

Mettle turns a municipal failed-inspection notice into a deadline-driven recovery campaign for small residential contractors. It preserves the notice's language, organizes citation-specific work, follows the recovery clock, and asks the contractor only for decisions that require licensed judgment.

## The first working slice

The repository runs a complete notice-to-judgment slice without AWS credentials or paid model calls. It can:

- load a realistic text-form correction notice from the command center;
- extract its citations without interpreting building code;
- record citation-specific trade outreach through a safe local adapter;
- increase urgency as the reinspection deadline approaches; and
- pause at ambiguous requirements, accept the contractor's decision, and resume with contractor-directed outreach.

The product core now runs those steps as a real Strands graph. Deterministic
policy nodes parse and plan the campaign, an idempotent communication port
records trade outreach, and a Strands interrupt pauses the graph for contractor
judgment before it resumes. No cloud model is invoked in this local mode.

The command center has two modes. **Load notice** runs the real local Strands graph and preserves the workflow ID in the URL so the run survives a refresh. The **demo controls** drive a deterministic six-event judge scenario: accepted evidence, rejected evidence with a precise re-request, deadline escalation, human judgment, and a contractor-approved final packet.

The deterministic core is intentional. Strands and Bedrock will provide agentic extraction, communication, evidence review, and orchestration, while the domain rules remain testable without a model.

## Run it locally

Use Python 3.12 and [`uv`](https://docs.astral.sh/uv/):

```bash
uv sync --extra dev
uv run mettle ingest examples/notices/failed-rough-in.txt --as-of 2026-08-10
uv run mettle serve
uv run pytest
```

Open [http://127.0.0.1:4310](http://127.0.0.1:4310) after starting the server. The demo binds only to the local machine.

Select **Load notice** to use the included synthetic notice and roster. The local communication adapter records every proposed message but never sends SMS.

Strands is installed as a core dependency, but no AWS credentials are needed
for the example or tests. Bedrock and AgentCore adapters will be added behind
the same workflow contracts once credits are available.

Workflow state is intentionally process-local in this phase. Restarting the server clears created runs; durable storage, authentication, and live communication belong to the deployment slice.

## Product boundary

Mettle starts when an inspection has failed. It is not a permit-management suite, a punch-list replacement, or an authority on building code. It never claims that work is compliant, interprets an ambiguous citation autonomously, contacts an inspector without approval, or submits a final packet without the contractor's consent.

Read [the product scope](docs/product-scope.md) and [the architecture](docs/architecture.md) for the decisions behind the MVP.
