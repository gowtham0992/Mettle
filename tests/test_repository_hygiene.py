from __future__ import annotations

import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SAMPLE_ACCOUNT_ID = "123456789012"
DEPLOYMENT_FILES = (
    ROOT / "agentcore" / "aws-targets.json",
    *(ROOT / "agentcore" / "iam").glob("*.json"),
    *(ROOT / "infra" / "web" / "iam").glob("*.json"),
)


def test_deployment_examples_do_not_embed_a_real_aws_account_id() -> None:
    for path in DEPLOYMENT_FILES:
        account_ids = set(re.findall(r"(?<!\d)\d{12}(?!\d)", path.read_text()))
        assert account_ids <= {SAMPLE_ACCOUNT_ID}, path


def test_direct_deploy_requires_private_resource_arguments() -> None:
    script = (ROOT / "scripts" / "deploy_web_direct.sh").read_text()
    assert 'static_bucket="$2"' in script
    assert 'distribution_id="$3"' in script
    assert "staticbucket-" not in script
    assert not re.search(r'distribution_id="[A-Z0-9]{10,}"', script)


def test_cloud_smokes_derive_the_calling_account() -> None:
    agentcore_smoke = (ROOT / "scripts" / "agentcore_smoke.py").read_text()
    scheduler_smoke = (ROOT / "scripts" / "web_scheduler_smoke.py").read_text()
    assert 'get_caller_identity()["Account"]' in agentcore_smoke
    assert 'get_caller_identity()["Account"]' in scheduler_smoke
    assert "EXPECTED_ACCOUNT" not in agentcore_smoke
    assert "EXPECTED_ACCOUNT" not in scheduler_smoke
