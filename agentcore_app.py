from __future__ import annotations

import os

from bedrock_agentcore import BedrockAgentCoreApp, RequestContext

from mettle.agentcore_runtime import MettleAgentCoreRuntime
from mettle.agents.bedrock import BedrockIntakeSettings, extract_notice_with_bedrock
from mettle.workflow_registry import WorkflowRegistry


bedrock_settings = BedrockIntakeSettings(
    region=os.getenv("AWS_REGION", "us-east-1"),
    model_id="amazon.nova-micro-v1:0",
)


def bedrock_intake(text: str):
    return extract_notice_with_bedrock(text, settings=bedrock_settings)


runtime = MettleAgentCoreRuntime(
    workflows=WorkflowRegistry(bedrock_intake=bedrock_intake)
)
app = BedrockAgentCoreApp()


@app.entrypoint
def mettle_recovery(payload: object, context: RequestContext):
    """Run one bounded Mettle operation inside the isolated AgentCore session."""
    return runtime.handle(payload, session_id=context.session_id)


if __name__ == "__main__":
    app.run()
