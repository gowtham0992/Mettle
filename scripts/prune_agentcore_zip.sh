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

zip -q -d "${artifact_path}" \
  "Logo file and HTML usage.zip" \
  "assets/*" \
  "docs/*" \
  "tests/*" \
  "scripts/*" \
  "package.json" \
  "package-lock.json" \
  "README.md"

if unzip -Z1 "${artifact_path}" | rg -q \
  '(^|/)(\.env|\.aws|\.git|node_modules|docs|tests|scripts|assets)(/|$)|Logo file and HTML usage\.zip|(^|/)package(-lock)?\.json$'; then
  echo "Repository-only or sensitive paths remain in ${artifact_path}." >&2
  exit 1
fi

echo "Pruned and verified ${artifact_path}."
