# Mettle architecture diagrams

The root README uses these current views:

- [Product architecture](mettle-product-architecture.png): refreshed notice-to-packet product flow, including contractor authority boundaries.
- [AWS architecture](mettle-aws-architecture.svg): authenticated operations, two model-driven Strands agents, durable S3/DynamoDB checkpoints, and background scheduling. The SVG is its editable source; a matching [PNG export](mettle-aws-architecture.png) is also included.

The other PNG, HTML, and CSS files in this directory are earlier architecture snapshots, not the source of these current views. The repository-root Pencil file is not the editable source of this refreshed pair.

For implementation details and limitations, see [checkpoint documentation](../../docs/recovery-checkpoints.md) and [architecture reference](../../docs/architecture.md).
