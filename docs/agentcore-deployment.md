# AgentCore deployment and rollback

Mettle uses direct CodeZip deployment in `us-east-1`. The public repository
documents the reproducible process while keeping account IDs, runtime IDs,
bucket names, object-version IDs, session IDs, and workflow IDs out of source.

## Current acceptance status

- Runtime: `MettleRecovery` (resource identifier recorded privately)
- Version and status: `13`, `READY`
- Artifact: immutable, private, versioned S3 object
- Artifact SHA-256:
  `8a83f7ce876e92565e56ac958ed3cc5877d276fb2192fe383c62122d7e63ab16`
- Runtime lifecycle: 15-minute idle timeout, 8-hour maximum session
- Log retention: 14 days

The version 13 acceptance run used synthetic data. It ran Nova Micro notice
intake, stopped with zero deliveries for contractor review, resumed the same
Strands graph, accepted three bounded evidence fixtures, required final
contractor approval, and rendered a five-page packet. The PDF passed
content-type, page-count, recovery-record, base64, and SHA-256 integrity checks
with digest
`2e251570d2f42482aedca4958b801c614c8117dff8c39edfe63426de8c2b4973`.

Earlier acceptance runs exercised live Nova Lite vision, deadline replanning,
idempotent replay, stale-event rejection, final approval, packet integrity,
rollback, and restoration. Their infrastructure and workflow identifiers are
recorded privately rather than committed.

## Proven locally

- The strict runtime contract completes `start -> Strands interrupt -> resume
  -> evidence -> packet preparation -> final approval -> PDF` in one session.
- Replaying the same start idempotency key does not repeat Bedrock intake.
- `npm ci && npx agentcore validate --json` succeeds from a clean clone.
- `scripts/prune_agentcore_zip.sh` strips repository-only files and rejects
  `.env`, `.aws`, `.git`, design sources, docs, tests, scripts, deployment
  state, build output, and Node dependencies.
- The packaged entrypoint regression removes the editable-install path and
  proves `agentcore_app.py` bootstraps the deployed `src/` layout.
- AWS Access Analyzer reports zero findings for the checked-in policy shapes.
- IAM simulation allows Nova Micro and Nova Lite and denies Nova Pro.

## Intended AWS footprint

The one-time private account setup creates only:

1. a private, encrypted, versioned S3 artifact bucket with public access
   blocked;
2. a runtime execution role scoped to Nova Micro, Nova Lite, logs, traces, and
   namespaced metrics;
3. a deployment role scoped to the Mettle runtime and artifact prefix; and
4. a narrow assume-role policy for the local bootstrap identity.

Public example policies use sample account identifiers. Replace them through a
private deployment configuration; never commit real account or resource IDs.

The runtime uses IAM-authorized inbound invocation. `PUBLIC` network mode
describes outbound runtime networking and does not make the invocation endpoint
anonymous.

## Package validation

Package from the repository root:

```bash
npx agentcore package -d . -r MettleRecovery
bash scripts/prune_agentcore_zip.sh agentcore/MettleRecovery.zip
```

Before upload, verify:

```bash
unzip -Z1 agentcore/MettleRecovery.zip | rg \
  '(^|/)(\.env|\.aws|\.git|node_modules)(/|$)|^(build|docs|tests|scripts|assets)/'
shasum -a 256 agentcore/MettleRecovery.zip
```

The first command must print no matches. Native extensions must target ARM64
Linux for the managed Python 3.12 runtime.

## Direct runtime update

Upload the pruned artifact to a new immutable key in the private versioned
bucket. Then update the existing runtime with private values supplied outside
source control:

```bash
aws bedrock-agentcore-control update-agent-runtime \
  --agent-runtime-id '<RUNTIME_ID>' \
  --agent-runtime-artifact '{"codeConfiguration":{"code":{"s3":{"bucket":"<PRIVATE_BUCKET>","prefix":"runtime/<IMMUTABLE_ARTIFACT>.zip","versionId":"<VERSION_ID>"}},"runtime":"PYTHON_3_12","entryPoint":["agentcore_app.py"]}}' \
  --role-arn 'arn:aws:iam::<AWS_ACCOUNT_ID>:role/MettleAgentCoreRuntime' \
  --network-configuration '{"networkMode":"PUBLIC"}' \
  --protocol-configuration '{"serverProtocol":"HTTP"}' \
  --lifecycle-configuration '{"idleRuntimeSessionTimeout":900,"maxLifetime":28800}' \
  --client-token '<UNIQUE_IDEMPOTENCY_TOKEN>' \
  --region us-east-1
```

Use a scoped deployment profile. Do not use root-backed credentials for normal
updates. Record the returned version, artifact version, digest, and request time
in a private deployment log.

## Cloud acceptance check

1. Wait until `GetAgentRuntime` reports `READY`.
2. Invoke `start` with a new session ID and synthetic notice.
3. Confirm one structured contractor-review interrupt and zero deliveries.
4. Submit the review through the same session and verify bounded outreach.
5. Submit accepted synthetic evidence for all three citations.
6. Prepare the packet and approve it through the contractor gate.
7. Render the packet and verify content type, base64, SHA-256, five pages, and
   the recovery communication record.
8. Confirm an idempotent replay does not repeat outreach.
9. Confirm logs contain only safe metadata, not notice text, images, model
   findings, phone numbers, credentials, or packet content.

The bounded paid smoke test prints workflow and packet metadata only:

```bash
uv run python scripts/agentcore_smoke.py \
  --profile '<SCOPED_PROFILE>' \
  --runtime-arn '<PRIVATE_RUNTIME_ARN>'
```

Add `--vision` to exercise live Nova Lite and `--chase` to exercise the T-3
follow-up, replay safety, and T-2 deadline interrupt.

AgentCore sessions are ephemeral. This slice uses a 15-minute idle timeout and
an 8-hour maximum lifetime; start and resume must remain in the same session.
Durable campaign recovery across runtime-session expiry is intentionally out of
scope and the UI directs the contractor to start a fresh recovery.

## Rollback

Keep the last known-good immutable artifact version. If a new runtime version
fails acceptance:

1. update the same runtime to the last known-good private object version;
2. wait for `READY`;
3. rerun the bounded acceptance check; and
4. remove the failed object version only after rollback succeeds.

## Full teardown

After the hackathon:

1. delete the Mettle runtime and verify deletion;
2. delete all versions and delete markers in the private artifact bucket;
3. delete the bucket;
4. remove the scoped policies and deployment/runtime roles; and
5. remove the local assume-role profile.

CloudWatch log groups may outlive the runtime. Resolve the exact private log
group before deciding whether to delete it.
