# AgentCore deployment and rollback

Mettle is prepared for a direct CodeZip deployment in `us-east-1`. Direct
deployment avoids the broad CloudFormation bootstrap roles created by the
default CDK workflow. Do not run these commands with the root-backed `mettle`
profile during normal development.

## Current deployment

- Runtime: `MettleRecovery-example`
- ARN: `arn:aws:bedrock-agentcore:us-east-1:123456789012:runtime/MettleRecovery-example`
- Version and status: `6`, `READY`
- Artifact: `runtime/MettleRecovery-example.zip`, S3 version
  `EXAMPLE_OBJECT_VERSION`
- Artifact SHA-256:
  `EXAMPLE_ARTIFACT_SHA256`
- Runtime lifecycle: 15-minute idle timeout, 8-hour maximum session
- Log group: `/aws/bedrock-agentcore/runtimes/MettleRecovery-example-DEFAULT`,
  14-day retention

The version 4 vision acceptance workflow `qrbNmKhlhEzAxqVP` ran Nova Micro
notice intake and one real AgentCore-to-Nova-Lite photo assessment. The photo
was accepted against its notice-grounded visible requirement, all three
citations reached ready, contractor approval gated the final packet, and the
5,616,749-byte four-page PDF passed SHA-256 verification. CloudWatch recorded
only request/session metadata and timings; it did not log the notice, image,
model findings, phone numbers, or packet.

The rollback drill then deployed the recorded version 3 artifact as runtime
version 5, reached `READY`, and completed acceptance workflow
`okBa3CpGLR9W7d-B`. The exact immutable vision artifact was restored as runtime
version 6 and reached `READY`. This exercised artifact rollback and restoration
on the actual demo runtime rather than relying on a paper rollback.

The original version 3 acceptance workflow `gC2tCVUproqzcjpu` ran the entire recovery
inside one AgentCore session: Nova Micro intake, two initial trade deliveries,
one contractor judgment, a third delivery after resume, three accepted
evidence records, packet preparation, final contractor approval, and a
four-page PDF. The 7,605,783-byte packet passed a SHA-256 integrity check.

The version 2 acceptance workflow `DW8bsBrz77Q4Noa9` established that runtime
logs contain completion metadata only, without the synthetic notice or
credentials. The deployer and bootstrap identities intentionally cannot read
CloudWatch logs, so version 3 post-deploy log inspection was not broadened at
the expense of least privilege.

The rollback canary `MettleRecoveryCanary-gNWaC24tLN` reached `READY`, was
deleted, and returned `ResourceNotFound` on verification. Its retained log
group expires after 14 days. The first artifact failed before Bedrock intake
because the deployed Python path omitted the repository's `src/` directory;
the regression-tested entrypoint fix is in version 2, and the broken S3 object
version was permanently removed.

## Proven locally

- The strict runtime contract completes `start -> Strands interrupt -> resume
  -> evidence -> packet preparation -> final approval -> PDF` in one runtime
  session.
- Replaying the same start idempotency key does not repeat the Bedrock intake.
- `npx agentcore validate --json` succeeds.
- `scripts/prune_agentcore_zip.sh` strips repository-only files after packaging
  and fails if the zip still contains `.env`, `.aws`, `.git`, design sources,
  docs, tests, scripts, AgentCore deployment state, or Node dependencies.
- The Python tests validate the runtime contract and cloud-response decoder.
- The packaged entrypoint regression test removes the local editable-install
  path and proves `agentcore_app.py` bootstraps the deployed `src/` layout.
- AWS Access Analyzer reports zero findings for all checked-in identity
  policies.
- IAM simulation allows Nova Micro and Nova Lite and implicitly denies Nova Pro.

## Intended AWS footprint

The one-time account setup creates only:

1. `mettle-agentcore-artifacts-123456789012-us-east-1`, a private, encrypted,
   versioned S3 bucket with public access blocked;
2. `MettleAgentCoreRuntime`, trusted by AgentCore only from account
   `123456789012` in `us-east-1`;
3. `MettleAgentCoreDeployer`, assumable by the existing bootstrap user for one
   hour; and
4. a separate `AssumeMettleAgentCoreDeployer` inline policy on the bootstrap
   user allowing only that one new role. The existing Bedrock developer policy
   is left unchanged.

The deployment then uploads `agentcore/MettleRecovery.zip` below `runtime/`
and creates one IAM-authorized public-network AgentCore Runtime tagged
`Project=Mettle`. Public network mode describes outbound runtime networking;
inbound invocation still requires AWS IAM authorization.

The checked-in policies are:

- `agentcore/iam/runtime-trust.json`
- `agentcore/iam/runtime-policy.json`
- `agentcore/iam/deployer-trust.json`
- `agentcore/iam/deployer-policy.json`
- `agentcore/iam/bootstrap-deployer-policy.json`

The execution policy grants model invocation only for
`amazon.nova-micro-v1:0` and `amazon.nova-lite-v1:0`. It also includes the exact CloudWatch Logs, X-Ray,
and namespaced metric permissions documented for AgentCore Runtime. It has no
IAM, S3, configuration-bundle, or wildcard Bedrock model permission.

AgentCore's `CreateAgentRuntime` operation also authorizes the dependent
`CreateAgentRuntimeEndpoint` action for the future `runtime/*` ARN. AWS does
not pass the runtime request-tag context to that dependent authorization, so
this single action must be account-scoped. Runtime creation remains
`Project=Mettle` request-tag-gated, and get/update/delete/invoke remain
resource-tag-gated.

Runtime deletion has the symmetric `DeleteAgentRuntimeEndpoint` dependency.
AWS does not pass resource-tag context to that dependent authorization, so the
endpoint action uses the account's `runtime/*` ARN. `DeleteAgentRuntime`
itself remains `Project=Mettle` resource-tag-gated, so the deployer cannot
initiate deletion of a non-Mettle runtime.

First-use runtime creation also creates an AgentCore-managed workload identity
under the account's `default` workload identity directory. The deployer can
create and tag only the exact default directory and identities under it, and
only with
`Project=Mettle`; it cannot read identities or obtain workload tokens.
Rollback can delete only managed identities under that directory carrying the
same `Project=Mettle` resource tag. AWS also evaluates deletion against the
untagged parent, so the policy allows the delete action on the one exact
`default` directory ARN; it does not allow deletion under any other directory.

## Direct runtime request

After packaging and uploading a versioned object, the control-plane request is
equivalent to:

```bash
aws bedrock-agentcore-control create-agent-runtime \
  --profile mettle-agentcore \
  --region us-east-1 \
  --agent-runtime-name MettleRecovery \
  --agent-runtime-artifact '{"codeConfiguration":{"code":{"s3":{"bucket":"mettle-agentcore-artifacts-123456789012-us-east-1","prefix":"runtime/MettleRecovery.zip","versionId":"<VERSION_ID>"}},"runtime":"PYTHON_3_12","entryPoint":["agentcore_app.py"]}}' \
  --role-arn arn:aws:iam::123456789012:role/MettleAgentCoreRuntime \
  --network-configuration '{"networkMode":"PUBLIC"}' \
  --protocol-configuration '{"serverProtocol":"HTTP"}' \
  --lifecycle-configuration '{"idleRuntimeSessionTimeout":900,"maxLifetime":28800}' \
  --tags Project=Mettle
```

The actual deployment must use a unique 33-or-more-character client token and
record the returned runtime ID, ARN, version, artifact version ID, and request
time in a local ignored file. No notice data belongs in deployment state.

## Cloud acceptance check

1. Wait until `GetAgentRuntime` returns `READY`.
2. Invoke `start` with a fresh runtime session ID and synthetic notice.
3. Confirm the response is interrupted with exactly one judgment request.
4. Invoke `resume` with the same runtime session ID and returned workflow and
   interrupt IDs.
5. Submit accepted synthetic evidence for all three citations.
6. Prepare the packet, approve it through the contractor judgment gate, and
   render the PDF.
7. Verify the PDF type, SHA-256 digest, and four-page structure.
8. Confirm the graph completes and that the first outreach was not replayed.
9. Check CloudWatch logs for the hashed session reference and absence of notice
   text when using an authorized observability identity.
10. Verify the execution role cannot invoke a model other than the approved Nova Micro and Nova Lite pair.

The paid end-to-end check is scripted and prints only workflow and packet
metadata, not the notice or model response:

```bash
uv run python scripts/agentcore_smoke.py \
  --profile mettle-agentcore \
  --runtime-arn <RUNTIME_ARN> \
  --vision
```

AgentCore runtime sessions are ephemeral. The default idle timeout here is 15
minutes and maximum lifetime is 8 hours. The first cloud demo must therefore
keep `start` and `resume` in the same session; durable campaign recovery across
session expiry is explicitly out of scope for this slice.

## Rollback drill

Before leaving the final runtime deployed, create a disposable canary runtime,
wait for `READY`, delete it, and verify `GetAgentRuntime` no longer returns an
active resource. This exercises the same rollback path without deleting the
demo runtime.

If the final deployment is unhealthy, delete the runtime by its recorded ID,
verify deletion, and delete the uploaded object version. Do not reuse a failed
runtime while its state is `CREATING`, `UPDATING`, or `DELETING`.

## Full teardown

After the hackathon:

1. delete the Mettle runtime and verify deletion;
2. delete every object version and delete marker under the artifact bucket;
3. delete the artifact bucket;
4. delete inline policies from `MettleAgentCoreRuntime` and
   `MettleAgentCoreDeployer`, then delete both roles; and
5. after every AgentCore Runtime in the account is gone, delete the AWS-owned
   `AWSServiceRoleForBedrockAgentCoreRuntimeIdentity` service-linked role; and
6. remove the AgentCore deployer role from the bootstrap user's assume-role
   policy and local AWS config.

CloudWatch log groups may outlive the runtime. List only
`/aws/bedrock-agentcore/runtimes/` groups associated with the recorded runtime
before deciding whether to delete them.

## Tooling caveat

The supported `@aws/agentcore` 0.26.0 CLI is pinned as a development-only
dependency. Its current transitive dependency tree reports upstream npm audit
findings, and npm's automated fix attempts to install an AIX-only esbuild
package on macOS. Node tooling is excluded from the Python runtime artifact;
do not force incompatible dependency overrides into the deployable product.
