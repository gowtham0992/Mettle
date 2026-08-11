# Mettle

![Mettle logo](assets/brand/mettle-devpost-logo.png)

**From failed inspection to reinspection-ready.**

Mettle turns a municipal failed-inspection notice into a deadline-driven recovery campaign for small residential contractors. It preserves the notice's language, organizes citation-specific work, follows the recovery clock, and asks the contractor only for decisions that require licensed judgment.

## The first working slice

The repository currently runs without AWS credentials or paid model calls. It can:

- ingest a realistic text-form correction notice;
- extract its citations without interpreting building code;
- produce citation-specific follow-up actions;
- increase urgency as the reinspection deadline approaches; and
- route missing or ambiguous requirements to a judgment queue.

The deterministic core is intentional. Strands and Bedrock will provide agentic extraction, communication, evidence review, and orchestration, while the domain rules remain testable without a model.

## Run it locally

Use Python 3.12 and [`uv`](https://docs.astral.sh/uv/):

```bash
uv sync --extra dev
uv run mettle ingest examples/notices/failed-rough-in.txt --as-of 2026-08-10
uv run pytest
```

AWS integration is optional until credits arrive:

```bash
uv sync --extra aws --extra dev
```

No AWS credentials are needed for the example or tests.

## Product boundary

Mettle starts when an inspection has failed. It is not a permit-management suite, a punch-list replacement, or an authority on building code. It never claims that work is compliant, interprets an ambiguous citation autonomously, contacts an inspector without approval, or submits a final packet without the contractor's consent.

Read [the product scope](docs/product-scope.md) and [the architecture](docs/architecture.md) for the decisions behind the MVP.
