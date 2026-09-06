import json
from pathlib import Path

import yaml


class CloudFormationLoader(yaml.SafeLoader):
    pass


def _construct_tag(loader, tag_suffix, node):
    if isinstance(node, yaml.ScalarNode):
        return {tag_suffix: loader.construct_scalar(node)}
    if isinstance(node, yaml.SequenceNode):
        return {tag_suffix: loader.construct_sequence(node)}
    return {tag_suffix: loader.construct_mapping(node)}


CloudFormationLoader.add_multi_constructor("!", _construct_tag)
TEMPLATE = yaml.load(
    Path("infra/web/template.yaml").read_text(encoding="utf-8"),
    Loader=CloudFormationLoader,
)
RESOURCES = TEMPLATE["Resources"]


def test_ocr_is_opt_in_and_only_grants_synchronous_text_detection():
    assert TEMPLATE["Parameters"]["NoticeOcrEnabled"]["Default"] == "0"
    statements = RESOURCES["WebFunctionRole"]["Properties"]["Policies"][0]["PolicyDocument"]["Statement"]
    ocr = next(s for s in statements if s["Sid"] == "ReadOneNoticePage")
    assert ocr["Action"] == "textract:DetectDocumentText"
    assert ocr["Condition"]["StringEquals"]["aws:RequestedRegion"] == {"Ref":"AWS::Region"}
    assert not any("textract" in str(s) for s in RESOURCES["SchedulerFunctionRole"]["Properties"]["Policies"])


def test_scoped_web_deployer_can_rollback_only_from_web_artifacts() -> None:
    policy = json.loads(
        Path("infra/web/iam/deployer-policy.json").read_text(encoding="utf-8")
    )
    artifact_statement = next(
        statement
        for statement in policy["Statement"]
        if statement["Sid"] == "ReadOnlyImmutableWebArtifacts"
    )

    assert artifact_statement["Action"] == "s3:GetObject"
    assert artifact_statement["Resource"].endswith("/web/*")
    assert "/runtime/" not in artifact_statement["Resource"]


def test_live_agentcore_routes_require_jwt_but_demo_routes_remain_public() -> None:
    protected = RESOURCES["ProtectedAgentCoreRoute"]["Properties"]
    fallback = RESOURCES["PublicDefaultRoute"]["Properties"]

    assert protected["RouteKey"] == "ANY /api/agentcore/{proxy+}"
    assert protected["AuthorizationType"] == "JWT"
    assert fallback["RouteKey"] == "$default"
    assert fallback["AuthorizationType"] == "NONE"


def test_lambda_role_is_least_privilege_and_cannot_manage_infrastructure() -> None:
    policies = RESOURCES["WebFunctionRole"]["Properties"]["Policies"]
    statements = policies[0]["PolicyDocument"]["Statement"]
    actions = {
        action
        for statement in statements
        for action in (
            statement["Action"] if isinstance(statement["Action"], list) else [statement["Action"]]
        )
    }

    assert "bedrock-agentcore:InvokeAgentRuntime" in actions
    assert "scheduler:CreateSchedule" in actions
    assert "iam:PassRole" in actions
    assert "dynamodb:Scan" not in actions
    assert "s3:ListBucket" not in actions
    assert {action for action in actions if action.startswith("iam:")} == {"iam:PassRole"}
    assert not any("CreateAgentRuntime" in action for action in actions)
    assert "*" not in actions

    invoke_statement = next(
        statement
        for statement in statements
        if statement["Sid"] == "InvokeOnlyMettleRuntime"
    )
    assert invoke_statement["Resource"] == [
        {"Ref": "AgentCoreRuntimeArn"},
        {"Sub": "${AgentCoreRuntimeArn}/runtime-endpoint/DEFAULT"},
    ]


def test_scheduler_is_one_time_bounded_and_has_a_dead_letter_path() -> None:
    worker = RESOURCES["SchedulerFunction"]["Properties"]
    invoke_role = RESOURCES["SchedulerInvokeRole"]["Properties"]
    queue = RESOURCES["SchedulerDeadLetterQueue"]["Properties"]
    web_env = RESOURCES["WebFunction"]["Properties"]["Environment"]["Variables"]

    assert "ReservedConcurrentExecutions" not in worker
    assert worker["Handler"] == "scheduler_handler.handler"
    assert web_env["METTLE_SCHEDULER_ENABLED"] == "1"
    assert web_env["METTLE_SCHEDULER_DEMO_DELAY_SECONDS"] == "90"
    assert queue["SqsManagedSseEnabled"] is True
    assert queue["MessageRetentionPeriod"] == 1209600
    trust = invoke_role["AssumeRolePolicyDocument"]["Statement"][0]
    assert trust["Principal"]["Service"] == "scheduler.amazonaws.com"
    assert trust["Condition"]["StringEquals"]["aws:SourceAccount"] == {"Ref": "AWS::AccountId"}


def test_scheduler_worker_has_no_public_route_or_sms_permission() -> None:
    route_targets = [
        properties["Target"]
        for name, resource in RESOURCES.items()
        if resource.get("Type") == "AWS::ApiGatewayV2::Route"
        for properties in [resource["Properties"]]
    ]
    assert all("Scheduler" not in str(target) for target in route_targets)

    statements = RESOURCES["SchedulerFunctionRole"]["Properties"]["Policies"][0][
        "PolicyDocument"
    ]["Statement"]
    actions = {
        action
        for statement in statements
        for action in (
            statement["Action"]
            if isinstance(statement["Action"], list)
            else [statement["Action"]]
        )
    }
    assert "sns:Publish" not in actions
    assert not any(action.startswith("sms-voice:") for action in actions)
    invoke_statement = next(
        statement
        for statement in statements
        if statement["Sid"] == "InvokeOnlyMettleRuntime"
    )
    assert invoke_statement["Resource"] == [
        {"Ref": "AgentCoreRuntimeArn"},
        {"Sub": "${AgentCoreRuntimeArn}/runtime-endpoint/DEFAULT"},
    ]


def test_storage_is_private_encrypted_and_ephemeral_packets_expire() -> None:
    for logical_id in ("StaticBucket", "PacketBucket"):
        properties = RESOURCES[logical_id]["Properties"]
        assert all(properties["PublicAccessBlockConfiguration"].values())
        algorithm = properties["BucketEncryption"]["ServerSideEncryptionConfiguration"][0]
        assert algorithm["ServerSideEncryptionByDefault"]["SSEAlgorithm"] == "AES256"

    packet_rule = RESOURCES["PacketBucket"]["Properties"]["LifecycleConfiguration"]["Rules"][0]
    # Must outlive the 30-day workflow record; one day destroys cold recovery.
    assert packet_rule["ExpirationInDays"] == 31


def test_cost_and_abuse_boundaries_are_explicit() -> None:
    function = RESOURCES["WebFunction"]["Properties"]
    route_settings = RESOURCES["HttpApiStage"]["Properties"]["DefaultRouteSettings"]
    waf_rules = RESOURCES["WebAcl"]["Properties"]["Rules"]

    assert "ReservedConcurrentExecutions" not in function
    assert function["Environment"]["Variables"]["METTLE_MAX_UPLOAD_BYTES"] == "3500000"
    assert route_settings["ThrottlingRateLimit"] == 5
    protected_throttle = RESOURCES["HttpApiStage"]["Properties"]["RouteSettings"]
    assert protected_throttle["ANY /api/agentcore/{proxy+}"]["ThrottlingRateLimit"] == 1
    assert waf_rules[0]["Statement"]["RateBasedStatement"]["Limit"] == 300


def test_cognito_disallows_public_signup_and_uses_code_flow() -> None:
    pool = RESOURCES["UserPool"]["Properties"]
    client = RESOURCES["UserPoolClient"]["Properties"]

    assert pool["AdminCreateUserConfig"]["AllowAdminCreateUserOnly"] is True
    assert client["GenerateSecret"] is False
    assert client["AllowedOAuthFlows"] == ["code"]
    assert client["EnableTokenRevocation"] is True
