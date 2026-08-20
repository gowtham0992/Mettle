# Mettle AWS access

Use the `mettle-dev` profile for everyday development. It assumes one-hour
credentials for `MettleHackathonDeveloper`; do not use the root-backed
`mettle` profile for model calls or application development.

## Verify the active identity

```bash
aws sts get-caller-identity --profile mettle-dev --region us-east-1
```

The ARN must contain `assumed-role/MettleHackathonDeveloper/`. If it contains
`:root`, stop and correct the profile before continuing.

## Run the bounded Bedrock intake

```bash
uv run mettle ingest examples/notices/failed-rough-in.txt \
  --provider bedrock \
  --aws-profile mettle-dev \
  --aws-region us-east-1 \
  --model-id amazon.nova-micro-v1:0 \
  --as-of 2026-08-10
```

The local trust chain is intentionally narrow:

- `mettle-bootstrap` stores the only long-lived access key. Its IAM user can
  only call `sts:AssumeRole` for `MettleHackathonDeveloper`.
- `mettle-dev` assumes that role for at most one hour.
- The role can call `bedrock:InvokeModel` and
  `bedrock:InvokeModelWithResponseStream` only for Amazon Nova Micro and Nova Lite in
  `us-east-1`.
- The root account has MFA enabled and no root access keys.

AWS profile files are local machine configuration. They are not part of this
repository and must never be copied into `.env` files, issue descriptions, or
commits.

## Refresh the public web application

The `mettle-web` profile assumes the exact-resource `MettleWebDeployer` role.
It can update only the deployed `mettle-web` Lambda, synchronize only Mettle's
static bucket, read deployment artifacts only beneath the private `web/`
prefix, and invalidate only Mettle's CloudFront distribution. The direct
release script verifies that assumed-role ARN and refuses root or any other
identity before building or changing AWS resources:

```bash
./scripts/deploy_web_direct.sh mettle-web
```

This path intentionally avoids CloudFormation for ordinary code and static
asset refreshes. Infrastructure changes still require a separately reviewed
CloudFormation deployment.

## Remove access after the hackathon

First list the bootstrap access-key ID:

```bash
aws iam list-access-keys \
  --user-name mettle-cli-bootstrap \
  --profile mettle
```

Then replace `<ACCESS_KEY_ID>` below with that ID and run the teardown in this
order:

```bash
aws iam delete-access-key \
  --user-name mettle-cli-bootstrap \
  --access-key-id <ACCESS_KEY_ID> \
  --profile mettle

aws iam delete-user-policy \
  --user-name mettle-cli-bootstrap \
  --policy-name AssumeMettleHackathonDeveloper \
  --profile mettle

aws iam delete-user-policy \
  --user-name mettle-cli-bootstrap \
  --policy-name AssumeMettleWebDeployer \
  --profile mettle

aws iam delete-role-policy \
  --role-name MettleWebDeployer \
  --policy-name DeployMettleWebExactResources \
  --profile mettle

aws iam delete-role-policy \
  --role-name MettleHackathonDeveloper \
  --policy-name InvokeMettleNovaMicro \
  --profile mettle

aws iam delete-user --user-name mettle-cli-bootstrap --profile mettle
aws iam delete-role --role-name MettleHackathonDeveloper --profile mettle
aws iam delete-role --role-name MettleWebDeployer --profile mettle
```

Finally remove the `mettle-bootstrap` entries from the local AWS credentials
and config files, and remove the `mettle-dev` and `mettle-web` role profiles
from the config file. Confirm removal with `aws configure list-profiles`.
