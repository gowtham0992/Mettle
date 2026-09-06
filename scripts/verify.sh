#!/usr/bin/env bash
set -euo pipefail

uv run --frozen pytest
uv run --frozen pytest infra/web/test_template.py
npm run test:ui
node --check src/mettle/web/static/evidence-flow.js
node --check src/mettle/web/static/app.js
node --check src/mettle/web/static/workbench.js
npm --prefix agentcore/cdk run build
npm --prefix agentcore/cdk test -- --runInBand
