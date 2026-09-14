# Run Mettle in your AWS account

You do not need AWS access to try Mettle. Start with the public judge walkthrough
or the [offline local setup](../README.md#run-locally). The hosted contractor
experience uses an invited Mettle account, not AWS credentials.

Deploying your own environment requires your own account, permissions, and
budget. This is a deployment guide, not a one-command account bootstrap.
Never request or reuse the submitter's credentials or private resource IDs.

## Prerequisites

- Complete the Python and Node dependency installation in the root README.
- Install AWS CLI v2 and configure a named profile with temporary credentials.
  If your organization uses IAM Identity Center, follow the
  [AWS profile setup guide](https://docs.aws.amazon.com/cli/latest/userguide/cli-configure-sso.html).
  Your administrator must first grant access to the relevant account and role.
- Use `us-east-1` for the checked-in model ARNs and infrastructure examples.
  Confirm Nova Micro and Nova Lite availability and invocation permissions in
  your account before attempting live assessments.
- Have an administrator review infrastructure creation separately from routine
  code releases. Do not use root credentials for application execution or
  routine deployment.

Replace `YOUR_PROFILE` below with a profile you configured. Profile names do
not confer permissions. Verify the account and ARN before changing resources:

```bash
aws sts get-caller-identity --profile YOUR_PROFILE --region us-east-1
```

Stop if the identity is unexpected or is account root. Keep credentials and
identity output outside the repository.

## Test bounded live intake first

With permission to invoke Nova Micro, this runs intake without deploying the
web application. It consumes model usage but does not send messages:

```bash
uv run mettle ingest examples/notices/failed-rough-in.txt \
  --provider bedrock \
  --aws-profile YOUR_PROFILE \
  --aws-region us-east-1 \
  --model-id amazon.nova-micro-v1:0 \
  --as-of 2026-08-10
```

## Deploy the runtime, then the web stack

1. Prepare a private, encrypted, versioned artifact bucket and runtime execution
   role. Review the example policies in [agentcore/iam](../agentcore/iam/).
   The account number `123456789012` is a placeholder. Adapt policy copies
   privately to your account and exact resources.
2. Follow [AgentCore packaging and deployment](agentcore-deployment.md).
   The direct-update example requires an existing runtime; initial creation is
   an administrator prerequisite. The CLI/CDK project is an alternative
   infrastructure path, not the process used for the hosted release.
3. Set `METTLE_AGENTCORE_RUNTIME_ARN` in your local deployment environment to
   your runtime ARN. [scripts/deploy_web.sh](../scripts/deploy_web.sh) accepts a
   profile, artifact bucket, and optional stack name. It packages and deploys
   [infra/web/template.yaml](../infra/web/template.yaml), configures Cognito
   callback URLs, and publishes static assets. It creates paid resources and
   requires infrastructure permissions, not merely model access.
4. Check the stack outputs for your site URL and Cognito pool. Create a test
   application user in your own pool; self-registration is disabled. Never
   commit that user's password.
5. Run the deployment guide's acceptance checks with synthetic inputs and
   recorded communication. Keep SMS disabled unless separately authorized
   and configured for one approved destination.

The web template includes gateway, scheduler, checkpoint storage, and retention
policies. Deploy compatible runtime and gateway versions together. For an older
installation, follow the [checkpoint migration guide](checkpoint-release-permissions.md).

This sequence has not been exercised as a fresh-account bootstrap. The hosted
environment's verified behavior and remaining limitations are documented in
[recovery checkpoints](recovery-checkpoints.md).

## Routine code releases

The direct release script requires the `MettleWebDeployer` assumed role and
scoped resource permissions. A generic profile will not satisfy that guard.
Configure the reviewed role in your account before using this path:

```bash
./scripts/deploy_web_direct.sh \
  YOUR_DEPLOYER_PROFILE \
  '<PRIVATE_STATIC_BUCKET>' \
  '<PRIVATE_DISTRIBUTION_ID>' \
  '<PUBLIC_SITE_URL>'
```

This script updates web code and static assets, not runtime, scheduler code,
or infrastructure. Use the coordinated migration order when those components
change. Keep deployment values in local configuration, not committed examples.

## Cleanup

Keep the submitted environment accessible for judging. For your own test
deployment, inventory the exact stack, runtime, bucket versions, logs,
schedules, and roles before teardown. Confirm ownership and retention needs;
never apply another developer's resource names or broad deletion commands.
Remove unused local profiles and revoke temporary test access afterward.
