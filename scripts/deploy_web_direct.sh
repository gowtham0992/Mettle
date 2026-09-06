#!/usr/bin/env bash
set -euo pipefail

if [[ "$#" -lt 3 || "$#" -gt 4 ]]; then
  echo "Usage: $0 <aws-profile> <static-bucket> <distribution-id> [site-url]" >&2
  exit 2
fi

profile="$1"
region="us-east-1"
function_name="mettle-web"
static_bucket="$2"
distribution_id="$3"
site_url="${4:-the configured CloudFront distribution}"
repo_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
artifact="${repo_dir}/build/mettle-web.zip"

caller_arn="$(aws sts get-caller-identity \
  --profile "${profile}" \
  --query Arn \
  --output text)"

if [[ "${caller_arn}" != arn:aws:sts::*:assumed-role/MettleWebDeployer/* ]]; then
  echo "Refusing deployment from unexpected identity: ${caller_arn}" >&2
  echo "Use the scoped mettle-web profile." >&2
  exit 1
fi

"${repo_dir}/scripts/build_web_lambda.sh"

rm -f "${artifact}"
(
  cd "${repo_dir}/build/web-lambda"
  zip -9qr "${artifact}" .
)

artifact_bytes="$(wc -c < "${artifact}" | tr -d ' ')"
if (( artifact_bytes >= 52428800 )); then
  echo "Refusing direct upload: Lambda ZIP is ${artifact_bytes} bytes; limit is 52428800."
  exit 1
fi

aws lambda update-function-code \
  --profile "${profile}" \
  --region "${region}" \
  --function-name "${function_name}" \
  --zip-file "fileb://${artifact}" >/dev/null

aws lambda wait function-updated-v2 \
  --profile "${profile}" \
  --region "${region}" \
  --function-name "${function_name}"

aws s3 sync \
  --profile "${profile}" \
  --region "${region}" \
  "${repo_dir}/src/mettle/web/static/" \
  "s3://${static_bucket}/static/" \
  --exclude index.html \
  --exclude '.DS_Store' \
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

invalidation_id="$(aws cloudfront create-invalidation \
  --profile "${profile}" \
  --distribution-id "${distribution_id}" \
  --paths '/*' \
  --query 'Invalidation.Id' \
  --output text)"

aws cloudfront wait invalidation-completed \
  --profile "${profile}" \
  --distribution-id "${distribution_id}" \
  --id "${invalidation_id}"

echo "Mettle web deployment is live at ${site_url}"
