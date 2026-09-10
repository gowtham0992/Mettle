# Cold recovery checkpoints

Implementation status: runtime, web gateway, scheduler, and storage prerequisites deployed. The live runtime passed a fresh-session restore and recorded-only outreach check. September 9 authenticated browser acceptance completed intake, two photo assessments, final approval, reload restoration, and a downloaded four-page PDF with both photos intact. An overnight real-date cloud soak remains pending.

New authenticated recoveries can resume without keeping an AgentCore process alive. After each successful operation, the runtime exports a versioned JSON checkpoint. The gateway writes it to encrypted private S3 and commits its content-addressed key with the public workflow envelope in DynamoDB. Checkpoints never enter HTTP responses or presigned download links.

The checkpoint includes the Strands graph interrupt state, reviewed notice and plan, contact roster, recorded deliveries, evidence assessments, uploaded photo bytes, and packet approval. A new operation restores a fresh runtime from the committed checkpoint. It does not rerun intake or replay completed outreach. The Strands SDK version must match; upgrades require an explicit compatibility or migration decision.

## Failure rules

- Resource ownership is checked before checkpoint access. Only the existing IAM-authorized gateway can call the runtime restoration operation; there is no public restoration endpoint.
- S3 content hashes and workflow identities are checked before restore. JSON is used, never pickle or executable object deserialization.
- A persistent pending-operation marker prevents another mutation if a response is lost after execution may have begun. This is intentionally fail-closed: an operator must reconcile the outcome. It is not an exactly-once SMS claim and not an automatic retry of an uncertain send.
- Validated evidence/packet rejections clear that marker so the contractor can correct their request. Unknown execution failures retain it.
- Completed gateway retry records return the previous result without re-executing. Stale scheduled events remain no-ops.
- Previously created runs without checkpoints retain the legacy session-bound behavior. This change cannot recover state already lost from those processes.

## Retention and rollout

DynamoDB records expire 30 days after their last update. Private recovery artifacts, including PDFs and checkpoints, have a 31-day lifecycle policy. This replaces the old one-day artifact cleanup and must be deployed with the gateway. The scheduling worker also needs access to the private artifact bucket.

Deploy the compatible runtime, storage/worker policy, and gateway together; do not advertise multi-day operation until a deployed cold-runtime test passes. An old runtime response without a checkpoint remains readable, but does not acquire durable restoration. Do not roll back the runtime to a version that cannot restore already-created checkpoints.

Local tests discard runtime instances between operations, advance the clock by two days, resume contractor review, preserve photo evidence through approved PDF generation, execute a background check without a signed-in browser, reject cross-owner reads, and hold uncertain sends. The completed signed-in browser test exercises deployed S3/DynamoDB/AgentCore integration. An overnight scheduled run is still unverified. Administrative resolution of uncertain outcomes is not yet exposed as a self-service UI.
