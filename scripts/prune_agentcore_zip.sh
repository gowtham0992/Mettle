#!/usr/bin/env bash
set -euo pipefail

artifact_path="${1:-agentcore/MettleRecovery.zip}"
case "${artifact_path}" in
  agentcore/*.zip) ;;
  *)
    echo "Refusing to modify an artifact outside agentcore/." >&2
    exit 2
    ;;
esac

if [[ ! -f "${artifact_path}" ]]; then
  echo "Artifact not found: ${artifact_path}" >&2
  exit 2
fi

set +e
zip_output="$(zip -q -d "${artifact_path}" \
  "Logo file and HTML usage.zip" \
  "assets/*" \
  "docs/*" \
  "tests/*" \
  "scripts/*" \
  "package.json" \
  "package-lock.json" \
  "README.md" 2>&1)"
zip_status=$?
set -e
if [[ ${zip_status} -ne 0 && ${zip_status} -ne 12 ]]; then
  printf '%s\n' "${zip_output}" >&2
  echo "Unable to prune ${artifact_path} (zip exit ${zip_status})." >&2
  exit "${zip_status}"
fi

zip_listing="$(unzip -Z1 "${artifact_path}")"
if rg -q \
  '(^|/)(\.env|\.aws|\.git|node_modules)(/|$)|^(docs|tests|scripts|assets)/|^Logo file and HTML usage\.zip$|^package(-lock)?\.json$' \
  <<< "${zip_listing}"; then
  echo "Repository-only or sensitive paths remain in ${artifact_path}." >&2
  exit 1
fi

echo "Pruned and verified ${artifact_path}."
