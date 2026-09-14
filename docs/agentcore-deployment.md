# AgentCore deployment and rollback

Mettle uses direct CodeZip deployment in `us-east-1`. The public repository
documents the reproducible process while keeping account IDs, runtime IDs,
bucket names, object-version IDs, session IDs, and workflow IDs out of source.

## Verification and remaining limits

The deployed checkpoint path passed fresh-runtime restoration and signed-in
browser acceptance through intake, photo assessment, contractor approval,
reload restoration, and PDF download. See [recovery checkpoints](recovery-checkpoints.md)
for the recorded acceptance scope. An overnight real-date scheduling test and
a self-service interface for uncertain-outcome reconciliation remain outstanding.

The configured runtime lifecycle is a 15-minute idle timeout and an eight-hour
maximum session. Durable recovery comes from private checkpoints, not from
keeping that process alive. Keep runtime versions, artifact digests, and private
deployment identifiers in your own release records.

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

## Runtime prerequisites

Before the direct runtime update below, an administrator must provision:

1. a private, encrypted, versioned S3 artifact bucket with public access
   blocked;
2. a runtime execution role scoped to Nova Micro, Nova Lite, logs, traces, and
   namespaced metrics;
3. a deployment role scoped to the Mettle runtime and artifact prefix; and
4. temporary deployment access through a reviewed role.

The update command does not create a runtime. For a first deployment, use the
[AWS runtime creation guide](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/getting-started-custom.html)
with the packaged entrypoint and reviewed execution role. The separate web stack
adds Cognito, API Gateway, Lambda, CloudFront, WAF, DynamoDB, private recovery
storage, and scheduling resources; follow [AWS setup](aws-access.md) for the order.

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
7. Render the packet and verify content type, base64, SHA-256, all expected
   corrections and photographs, and the recovery communication record. Page
   count depends on the input; inspect the rendered PDF rather than relying on
   a fixed number of pages.
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

AgentCore sessions remain ephemeral (15-minute idle timeout, eight-hour maximum lifetime). New checkpoint-bearing recoveries restore in a fresh runtime per operation. Legacy runs without checkpoints remain session-bound. Do not downgrade checkpoint-bearing runs to a runtime without restore support.

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
