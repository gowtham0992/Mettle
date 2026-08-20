# Agents for Humans: Making Mettle wake itself up safely on AWS

> **Excerpt:** An agent that only works while its dashboard is open is still asking a human to supervise it. Mettle uses AgentCore and EventBridge Scheduler to advance inspection recovery without keeping a browser alive.

The central promise of **Mettle** is simple: after a failed inspection, the contractor should not spend the next week remembering whom to chase. The agent should watch the recovery clock, follow only unresolved corrections, and surface the decisions that actually require professional judgment.

That promise fails if the workflow exists only inside a browser session. A dashboard can display a deadline, but it cannot claim background autonomy unless something trusted wakes the campaign after the contractor closes the tab.

For my Agents for Humans project, I deployed Mettle's typed Strands operations to **Amazon Bedrock AgentCore Runtime** and used **Amazon EventBridge Scheduler** for one-time recovery checkpoints. This post covers the engineering boundaries that made that path safe enough to demonstrate publicly: authenticated sessions, versioned events, idempotency, least privilege, rollback, and explicit limits.

## One typed runtime surface

Mettle's AgentCore entrypoint does not accept arbitrary prompts. It accepts a discriminated set of operations: start a recovery, review extracted corrections, resume a judgment, submit evidence, run the next checkpoint, prepare a packet, approve it, and render the approved PDF.

Each request is validated by Pydantic with unknown fields forbidden. Mutation operations carry bounded idempotency keys. The browser cannot choose a model ID, region, runtime ARN, or AWS tool.

The public deployment puts another boundary in front of AgentCore:

- CloudFront serves a private S3 origin through Origin Access Control.
- AWS WAF applies managed protections and rate limits API traffic.
- Cognito uses authorization code flow with PKCE and disables self-registration.
- API Gateway requires a Cognito JWT for every paid AgentCore route.
- Lambda maps a hash of the verified Cognito subject to an AgentCore session in DynamoDB.
- approved packets go to a private encrypted S3 bucket and use short-lived download URLs.

The unauthenticated sample never calls Bedrock. Judges can explore the product without spending project credit, while the authenticated path remains available for controlled proof.

![Mettle AWS architecture](https://raw.githubusercontent.com/gowtham0992/Mettle/main/assets/architecture/mettle-aws-architecture.png)

*The browser reaches one authenticated gateway; runtime credentials, model access, workflow state, and private evidence remain server-side.*

## Scheduling the next bounded action

Mettle does not create a permanent polling process. When the campaign advances, deterministic policy calculates the next logical checkpoint. The scheduler creates one exact `at(...)` event targeting a private Lambda worker:

```python
request = {
    "Name": schedule_name,
    "GroupName": self._schedule_group,
    "ScheduleExpression": f"at({execution_at:%Y-%m-%dT%H:%M:%S})",
    "ScheduleExpressionTimezone": "UTC",
    "FlexibleTimeWindow": {"Mode": "OFF"},
    "ActionAfterCompletion": "DELETE",
    "Target": {
        "Arn": self._target_arn,
        "RoleArn": self._execution_role_arn,
        "Input": serialized_event,
        "DeadLetterConfig": {"Arn": self._dlq_arn},
        "RetryPolicy": {
            "MaximumEventAgeInSeconds": 3600,
            "MaximumRetryAttempts": 2,
        },
    },
}
```

The schedule name is derived from a SHA-256 digest of the owner and workflow, not a customer name, phone number, address, or notice identifier. Its payload contains the owner hash, workflow ID, logical date, and schedule version.

When the private worker fires, it validates that payload and asks the durable gateway to run the scheduled check. The campaign advances only if the incoming version still matches the active automation record. A stale event cannot move a newer plan backward.

## Replay safety is part of autonomy

AWS services retry, users double-click, and networks time out after a server has already committed work. An autonomous workflow must treat duplication as normal rather than exceptional.

Mettle derives a deterministic idempotency key from the schedule version, logical checkpoint date, and hashed workflow reference. The gateway conditionally records mutation results in DynamoDB. Replaying the same delivery returns the existing receipt instead of repeating outreach or model spend.

The same principle applies to human resumes. A correction review that fails predictable roster validation does not consume the Strands interrupt. Retrying the same invalid request returns a stable validation error instead of turning into a server failure, and the valid correction can resume the original checkpoint.

## Proving the browser can be closed

The repository includes a paid deployment acceptance script for the complete scheduling boundary. The controlled run:

1. creates a synthetic authenticated workflow;
2. approves correction routing and confirms schedule version 1 exists;
3. waits for EventBridge Scheduler to invoke the private worker;
4. verifies the workflow advanced and armed schedule version 2;
5. confirms six safe outreach records were produced;
6. cancels the follow-on smoke schedule;
7. verifies the scheduler group is clean and the dead-letter queue is empty.

This acceptance passed on the deployed Mettle stack. No SMS permission was granted to the AgentCore, web, or scheduler roles, and no message was sent.

The final hackathon video will not wait ninety seconds for that event. It will show the contractor experience first, then a sanitized record of the completed AgentCore and EventBridge execution. Time compression is useful; pretending a pre-recorded event is live is not.

## Least privilege, including the deployment path

Runtime security is only half the problem. A deployment identity with broad IAM or S3 access can undermine an otherwise narrow application.

Mettle uses scoped bootstrap and deployer roles. The web deployer can update one Lambda, synchronize one static bucket, read only versioned artifacts beneath one private prefix, and invalidate one CloudFront distribution. The AgentCore deployer uploads one private versioned CodeZip artifact and creates or updates only the tagged Mettle runtime.

The runtime role can invoke only Amazon Nova Micro and Nova Lite. The web gateway can invoke only the exact AgentCore runtime and its `DEFAULT` endpoint. The scheduler worker has the same narrow runtime boundary plus the exact scheduler resources required to advance a campaign. None of these roles can publish to SNS.

The exact endpoint permission was a real deployment lesson. A direct AgentCore smoke test succeeded while the Lambda gateway received `AccessDenied`. AgentCore's hierarchical authorization required both the runtime ARN and its `runtime-endpoint/DEFAULT` resource. Adding that exact endpoint fixed the gateway without falling back to a wildcard.

## Rollback and failure visibility

Every runtime and web artifact is versioned in private S3. I exercised rollback rather than merely documenting it: restored a recorded prior Lambda artifact, verified the public health route, and then restored the intended artifact.

That drill also exposed an overly narrow deployer policy. The deployment role could update the function but could not read the private rollback object. I added `GetObject` only beneath the Mettle web-artifact prefix and repeated the drill successfully.

Scheduled failures have an encrypted SQS dead-letter queue and CloudWatch alarms. Scheduler logs contain a short hashed workflow reference, version, execution result, and status—not the notice, contractor identity, or session ID. The alarm path was manually placed into `ALARM` and returned to `OK` after verification.

## The limit I will not hide

AgentCore sessions are not durable multi-week campaign memory. Mettle configures a 15-minute idle timeout and an eight-hour maximum lifetime. DynamoDB maps an authenticated user to the active session and safely supports the accelerated judge run, but production operation across many days would require durable workflow rehydration beyond this hackathon slice.

The messaging boundary is similarly explicit. A guarded one-way Amazon SNS adapter exists for one hashed, pre-approved demo destination, but it remains disabled until enrollment. Inbound SMS interpretation is not implemented; trades submit evidence through the portal.

Those constraints do not weaken the demonstrated architecture. They define exactly what it proves: a real Strands campaign can run on AgentCore, pause for human judgment, wake itself through EventBridge, reject stale events, and fail visibly without leaving an open browser or a broad AWS credential behind.

## Try Mettle

- **Public guided demo:** [d1ytth8asjpes8.cloudfront.net](https://d1ytth8asjpes8.cloudfront.net)
- **MIT-licensed source:** [github.com/gowtham0992/Mettle](https://github.com/gowtham0992/Mettle)
- **Deployment acceptance:** [`scripts/web_scheduler_smoke.py`](https://github.com/gowtham0992/Mettle/blob/main/scripts/web_scheduler_smoke.py)
- **Verification:** all 119 tests run without AWS credentials or model spend

**The contractor closes the browser. Mettle keeps the recovery clock.**

<!-- Builder Center publishing metadata:
Cover image: assets/architecture/mettle-aws-architecture.png
Tags: Amazon Bedrock AgentCore, Amazon EventBridge Scheduler, AWS Lambda, Amazon DynamoDB, Strands Agents, serverless, generative AI
Recommended inline images: mettle-aws-architecture.png, 01-command-center.png, 04-deadline-judgment.png
-->
