#!/usr/bin/env bash
set -euo pipefail

if [[ "$#" -lt 2 || "$#" -gt 3 ]]; then
  echo "Usage: $0 <aws-profile> <artifact-bucket> [stack-name]" >&2
  exit 2
fi

profile="$1"
artifact_bucket="$2"
stack_name="${3:-MettleWeb}"
region="us-east-1"
repo_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
template="${repo_dir}/infra/web/template.yaml"
packaged_template="${repo_dir}/build/web-packaged.yaml"
runtime_arn="arn:aws:bedrock-agentcore:${region}:123456789012:runtime/MettleRecovery-example"

if [[ "${METTLE_SKIP_WEB_BUILD:-0}" != "1" ]]; then
  "${repo_dir}/scripts/build_web_lambda.sh"
fi

aws cloudformation package \
  --profile "${profile}" \
  --region "${region}" \
  --template-file "${template}" \
  --s3-bucket "${artifact_bucket}" \
  --s3-prefix web \
  --output-template-file "${packaged_template}"

account_id="$(aws sts get-caller-identity --profile "${profile}" --query Account --output text)"
domain_prefix="mettle-${account_id}"

aws cloudformation deploy \
  --profile "${profile}" \
  --region "${region}" \
  --stack-name "${stack_name}" \
  --template-file "${packaged_template}" \
  --capabilities CAPABILITY_NAMED_IAM \
  --parameter-overrides \
    AgentCoreRuntimeArn="${runtime_arn}" \
    CognitoDomainPrefix="${domain_prefix}" \
  --tags Project=Mettle

output() {
  aws cloudformation describe-stacks \
    --profile "${profile}" \
    --region "${region}" \
    --stack-name "${stack_name}" \
    --query "Stacks[0].Outputs[?OutputKey=='$1'].OutputValue | [0]" \
    --output text
}

site_url="$(output SiteUrl)"
distribution_id="$(output DistributionId)"
static_bucket="$(output StaticBucketName)"
user_pool_id="$(output UserPoolId)"
user_pool_client_id="$(output UserPoolClientId)"

aws cognito-idp update-user-pool-client \
  --profile "${profile}" \
  --region "${region}" \
  --user-pool-id "${user_pool_id}" \
  --client-id "${user_pool_client_id}" \
  --client-name MettleWebPublicClient \
  --enable-token-revocation \
  --prevent-user-existence-errors ENABLED \
  --allowed-o-auth-flows-user-pool-client \
  --allowed-o-auth-flows code \
  --allowed-o-auth-scopes openid email \
  --callback-urls "${site_url}/" \
  --logout-urls "${site_url}/" \
  --supported-identity-providers COGNITO \
  --explicit-auth-flows ALLOW_REFRESH_TOKEN_AUTH ALLOW_USER_SRP_AUTH \
  --access-token-validity 1 \
  --id-token-validity 1 \
  --refresh-token-validity 1 \
  --token-validity-units AccessToken=hours,IdToken=hours,RefreshToken=days >/dev/null

aws s3 sync \
  --profile "${profile}" \
  --region "${region}" \
  "${repo_dir}/src/mettle/web/static/" \
  "s3://${static_bucket}/static/" \
  --exclude index.html \
  --delete \
  --sse AES256 \
  --cache-control 'public,max-age=300,must-revalidate'

aws s3 cp \
  --profile "${profile}" \
  --region "${region}" \
  "${repo_dir}/src/mettle/web/static/index.html" \
  "s3://${static_bucket}/index.html" \
  --sse AES256 \
  --content-type text/html \
  --cache-control 'no-cache,no-store,must-revalidate'

aws cloudfront create-invalidation \
  --profile "${profile}" \
  --distribution-id "${distribution_id}" \
  --paths '/*' >/dev/null

echo "Mettle web deployment is updating at ${site_url}"
echo "Cognito self-registration is disabled; create the owner account separately."
