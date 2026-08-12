from __future__ import annotations

import os
import sys
from pathlib import Path


SOURCE_ROOT = Path(__file__).resolve().parent / "src"
if SOURCE_ROOT.is_dir() and str(SOURCE_ROOT) not in sys.path:
    sys.path.insert(0, str(SOURCE_ROOT))

from bedrock_agentcore import BedrockAgentCoreApp, RequestContext

from mettle.agentcore_runtime import MettleAgentCoreRuntime
from mettle.agents.bedrock import BedrockIntakeSettings, extract_notice_with_bedrock
from mettle.agents.vision import BedrockVisionSettings, assess_photo_with_bedrock
from mettle.workflow_registry import WorkflowRegistry


bedrock_settings = BedrockIntakeSettings(
    region=os.getenv("AWS_REGION", "us-east-1"),
    model_id="amazon.nova-micro-v1:0",
)
vision_settings = BedrockVisionSettings(
    region=os.getenv("AWS_REGION", "us-east-1"),
    model_id="amazon.nova-lite-v1:0",
)


def bedrock_intake(text: str):
    return extract_notice_with_bedrock(text, settings=bedrock_settings)


def photo_assessor(**kwargs):
    return assess_photo_with_bedrock(**kwargs, settings=vision_settings)


runtime = MettleAgentCoreRuntime(
    workflows=WorkflowRegistry(
        bedrock_intake=bedrock_intake,
        photo_assessor=photo_assessor,
    )
)
app = BedrockAgentCoreApp()


@app.entrypoint
def mettle_recovery(payload: object, context: RequestContext):
    """Run one bounded Mettle operation inside the isolated AgentCore session."""
    return runtime.handle(payload, session_id=context.session_id)


if __name__ == "__main__":
    app.run()
