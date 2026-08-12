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
    assert "dynamodb:Scan" not in actions
    assert "s3:ListBucket" not in actions
    assert not any(action.startswith("iam:") for action in actions)
    assert not any("CreateAgentRuntime" in action for action in actions)
    assert "*" not in actions


def test_storage_is_private_encrypted_and_ephemeral_packets_expire() -> None:
    for logical_id in ("StaticBucket", "PacketBucket"):
        properties = RESOURCES[logical_id]["Properties"]
        assert all(properties["PublicAccessBlockConfiguration"].values())
        algorithm = properties["BucketEncryption"]["ServerSideEncryptionConfiguration"][0]
        assert algorithm["ServerSideEncryptionByDefault"]["SSEAlgorithm"] == "AES256"

    packet_rule = RESOURCES["PacketBucket"]["Properties"]["LifecycleConfiguration"]["Rules"][0]
    assert packet_rule["ExpirationInDays"] == 1


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
