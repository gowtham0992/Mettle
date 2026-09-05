import json
from pathlib import Path


def test_checkpoint_release_permission_does_not_grant_infrastructure_or_iam_writes():
    policy = json.loads(Path("infra/web/iam/checkpoint-release-deployer-policy.json").read_text())
    allowed = {
        "lambda:GetFunction", "lambda:GetFunctionConfiguration", "lambda:UpdateFunctionCode",
        "cloudformation:DescribeStacks", "cloudformation:DescribeStackResources", "cloudformation:GetTemplate",
    }
    for statement in policy["Statement"]:
        assert statement["Effect"] == "Allow"
        assert set(statement["Action"]) <= allowed
        assert statement["Resource"] in {
            "arn:aws:lambda:us-east-1:123456789012:function:mettle-scheduler",
            "arn:aws:cloudformation:us-east-1:123456789012:stack/MettleWeb/*",
        }


def test_scheduler_checkpoint_permission_is_object_only_and_single_bucket():
    policy = json.loads(Path("infra/web/iam/scheduler-checkpoint-storage-policy.json").read_text())
    assert len(policy["Statement"]) == 1
    statement = policy["Statement"][0]
    assert set(statement["Action"]) == {"s3:GetObject", "s3:PutObject"}
    assert statement["Resource"] == "arn:aws:s3:::mettleweb-packetbucket-example/*"
