# Mettle

![Mettle logo](assets/brand/mettle-devpost-logo.png)

**From failed inspection to reinspection-ready.**

Mettle turns a municipal failed-inspection notice into a deadline-driven recovery campaign for small residential contractors. It preserves the notice's language, organizes citation-specific work, follows the recovery clock, and asks the contractor only for decisions that require licensed judgment.

## The first working slice

The repository runs a complete notice-to-judgment slice locally and through the
official AgentCore development server, with an explicit opt-in for live Bedrock
intake. It can:

- load a realistic text-form correction notice from the command center;
- extract its citations without interpreting building code;
- record citation-specific trade outreach through a safe local adapter;
- increase urgency as the reinspection deadline approaches; and
- pause at ambiguous requirements, accept the contractor's decision, and resume with contractor-directed outreach;
- securely normalize a real JPEG/PNG photo, use Nova Lite to check only visible notice requirements, and accept, re-request, or reserve ambiguity for the contractor;
- retain synthetic fixtures as a deterministic, zero-cost demo fallback; and
- assemble a four-page evidence packet, block download until final contractor approval, and produce a polished PDF with citation-to-evidence traceability.

The product core now runs those steps as a real Strands graph. Deterministic
policy nodes parse and plan the campaign, an idempotent communication port
records trade outreach, and a Strands interrupt pauses the graph for contractor
judgment before it resumes. No cloud model is invoked in this local mode.

The command center exposes three execution choices under **Load notice**:
free local execution, local Strands with live Bedrock intake, and the deployed
AgentCore runtime. The deterministic **demo controls** remain the complete
six-event judge scenario: accepted evidence, rejected evidence with a precise
re-request, deadline escalation, human judgment, and a contractor-approved
final packet.

The deterministic core is intentional. Strands orchestrates the recovery graph, while Bedrock can replace only the intake node. Domain rules remain testable without a model.

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

To expose the separate, credit-metered **Run live Bedrock** action in the
dashboard, start the server explicitly with the least-privilege assumed-role
profile:

```bash
uv run mettle serve \
  --enable-bedrock \
  --aws-profile mettle-dev \
  --aws-region us-east-1
```

AWS profile, region, and the Nova Micro/Nova Lite allowlist remain server-side;
the browser cannot override them. The default **Start local · free** action
never calls Bedrock. Creation requests are idempotent, including across a
browser retry, so an identical retry does not make a second model call.

The Bedrock boundary uses a low-cost Nova Micro model, a 30,000-character
input ceiling, a 2,048-token output ceiling, short timeouts, and at most two
total attempts. The intake CLI refuses model IDs outside the approved Nova
Micro allowlist. Model output must validate as Mettle's bounded notice schema
before it can enter campaign state.

The same explicit Bedrock opt-in enables real-photo evidence assessment with
Nova Lite. Uploads are capped at 5 MB, decoded as JPEG/PNG, stripped of metadata,
bounded in pixel dimensions, and re-encoded before the model sees them. The
model must return one structured, pixel-grounded finding per notice requirement.
Mettle deterministically converts those findings to accepted, rejected, or
manual-review status; the model is never asked to certify code compliance.

## Run the AgentCore boundary locally

The official AgentCore app lives at `agentcore_app.py`. It accepts only the
bounded `start` and `resume` operations, preserves the Strands workflow in the
AgentCore session, and does not let callers select an AWS profile, region, or
model. Start the local runtime without deploying anything:

```bash
npx agentcore dev --runtime MettleRecovery --port 8081 --logs --skip-deploy
```

Package the direct-code artifact with:

```bash
npx agentcore validate --json
npx agentcore package --directory . --runtime MettleRecovery
scripts/prune_agentcore_zip.sh
```

The final command strips design sources, docs, tests, and build tooling from the
runtime zip, then fails if a forbidden path remains. The generated zip and
staging tree are ignored. The checked-in IAM policies
allow only Nova Micro and Nova Lite plus AgentCore telemetry and restrict deployment to
Project-tagged Mettle runtimes. See
[AgentCore deployment and rollback](docs/agentcore-deployment.md).

The cloud runtime currently deployed in `us-east-1` is `MettleRecovery` version 3.
Its tested path runs live Bedrock intake inside Strands, pauses for contractor
judgment, resumes the same AgentCore session, assesses all three synthetic
evidence submissions, gates packet approval, and returns the verified
four-page PDF.

To expose **Run on AgentCore** in the command center, start the loopback-only
server with the deployed runtime fixed in server configuration:

```bash
uv run mettle serve \
  --enable-agentcore \
  --agentcore-runtime-arn arn:aws:bedrock-agentcore:us-east-1:123456789012:runtime/MettleRecovery-example \
  --aws-profile mettle-agentcore \
  --aws-region us-east-1
```

The browser can neither select a runtime nor access AWS credentials. The local
gateway owns the AgentCore session ID, reuses it for safe retries and resume,
caps process state, and sends only validated workflow operations. Cloud
workflow state can be restored while this local server remains running. The
server gateway verifies the returned PDF type and digest before offering the
contractor-approved download.

`mettle-dev` assumes the one-hour, least-privilege
`MettleHackathonDeveloper` role. It can invoke only the approved Nova models but cannot administer
IAM or invoke more expensive models. See [AWS access and teardown](docs/aws-access.md).

Workflow state is intentionally session-local in this phase. Restarting the
local dashboard server clears its private mapping from Mettle workflow IDs to
AgentCore sessions; AgentCore itself keeps the graph only while the isolated
runtime session is alive. Durable storage and live communication remain later
slices.

## Product boundary

Mettle starts when an inspection has failed. It is not a permit-management suite, a punch-list replacement, or an authority on building code. It never claims that work is compliant, interprets an ambiguous citation autonomously, contacts an inspector without approval, or submits a final packet without the contractor's consent.

Read [the product scope](docs/product-scope.md) and [the architecture](docs/architecture.md) for the decisions behind the MVP.
