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
- pause at ambiguous requirements, accept the contractor's decision, and resume with contractor-directed outreach;
- reject an insufficient synthetic photo, explain what is missing, and accept a replacement only when it satisfies the notice's observable requirements; and
- assemble a four-page evidence packet, block download until final contractor approval, and produce a polished PDF with citation-to-evidence traceability.

The product core now runs those steps as a real Strands graph. Deterministic
policy nodes parse and plan the campaign, an idempotent communication port
records trade outreach, and a Strands interrupt pauses the graph for contractor
judgment before it resumes. No cloud model is invoked in this local mode.

The command center has two modes. **Load notice** runs the real local Strands graph, preserves the workflow ID in the URL, and exposes a synthetic evidence lab for all three trades. The **demo controls** drive a deterministic six-event judge scenario: accepted evidence, rejected evidence with a precise re-request, deadline escalation, human judgment, and a contractor-approved final packet.

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

Select **Load notice** to use the included synthetic notice and roster. The local communication adapter records every proposed message but never sends SMS. In **Evidence lab**, resolve the mechanical evidence specification, assess the electrical, framing, and mechanical fixtures, then prepare and approve the downloadable packet.

Strands is installed as a core dependency, but no AWS credentials are needed
for the example or tests. Amazon Bedrock intake is deliberately opt-in, so
normal development and the dashboard never consume credits:

```bash
uv run mettle ingest examples/notices/failed-rough-in.txt \
  --provider bedrock \
  --aws-profile mettle-dev \
  --aws-region us-east-1 \
  --model-id amazon.nova-micro-v1:0 \
  --as-of 2026-08-10
```

The Bedrock boundary uses a low-cost Nova Micro model, a 30,000-character
input ceiling, a 2,048-token output ceiling, short timeouts, and at most two
total attempts. The intake CLI refuses model IDs outside the approved Nova
Micro allowlist. Model output must validate as Mettle's bounded notice schema
before it can enter campaign state. AgentCore deployment will follow after
this live intake path is verified.

`mettle-dev` assumes the one-hour, least-privilege
`MettleHackathonDeveloper` role. It can invoke Nova Micro but cannot administer
IAM or invoke more expensive models. See [AWS access and teardown](docs/aws-access.md).

Workflow state is intentionally process-local in this phase. Restarting the server clears created runs; durable storage, authentication, and live communication belong to the deployment slice.

## Product boundary

Mettle starts when an inspection has failed. It is not a permit-management suite, a punch-list replacement, or an authority on building code. It never claims that work is compliant, interprets an ambiguous citation autonomously, contacts an inspector without approval, or submits a final packet without the contractor's consent.

Read [the product scope](docs/product-scope.md) and [the architecture](docs/architecture.md) for the decisions behind the MVP.
