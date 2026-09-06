#!/usr/bin/env bash
set -euo pipefail

repo_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
build_dir="${repo_dir}/build/web-lambda"

if [[ "${build_dir}" != "${repo_dir}/build/web-lambda" ]]; then
  echo "Refusing to clean an unexpected build directory" >&2
  exit 1
fi

rm -rf "${build_dir}"
mkdir -p "${build_dir}"

uv export \
  --frozen \
  --no-dev \
  --no-emit-project \
  --no-hashes \
  --output-file "${repo_dir}/build/web-requirements.txt"

docker run --rm --platform linux/amd64 \
  --entrypoint /bin/bash \
  --volume "${repo_dir}:/asset" \
  --workdir /asset \
  public.ecr.aws/lambda/python:3.12 \
  -lc 'python -m pip install --no-cache-dir --target build/web-lambda -r build/web-requirements.txt && python -m pip install --no-cache-dir --no-deps --target build/web-lambda .'

cp "${repo_dir}/lambda_handler.py" "${build_dir}/lambda_handler.py"
cp "${repo_dir}/scheduler_handler.py" "${build_dir}/scheduler_handler.py"

# Retired/unreferenced visuals remain in the static origin for old links, but
# no packet or current page uses them. Keep them out of the limited Lambda ZIP.
rm -f "${build_dir}/mettle/web/static/evidence/framing-plates-complete.png" \
  "${build_dir}/mettle/web/static/mettle-lockup.png"

find "${build_dir}" -type d -name '__pycache__' -prune -exec rm -rf '{}' +
find "${build_dir}" -type f \( -name '*.pyc' -o -name '*.pyo' \) -delete
# Immutable Lambda bundles are not pip install/uninstall environments. Preserve
# package metadata and licenses; omit only the installer file inventories.
find "${build_dir}" -type f -path '*.dist-info/RECORD' -delete

if find "${build_dir}" -type f \( -name '.env' -o -name 'credentials' \) | grep -q .; then
  echo "Refusing to package a credential-shaped file" >&2
  exit 1
fi

python_files="$(find "${build_dir}" -type f | wc -l | tr -d ' ')"
echo "Built Lambda artifact at ${build_dir} (${python_files} files)"
