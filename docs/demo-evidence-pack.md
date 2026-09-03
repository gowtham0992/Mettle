# Mettle demo evidence pack

Prepare these assets before recording so the five-minute video proves the real agent system without depending on live AWS timing.

## Product captures

1. **Previously unseen notice to review gate:** `examples/notices/denver-remodel.txt` entering the `LIVE · STRANDS` path, with extracted citations, `0 messages`, and the correction-review interrupt visible.
2. **Inspectable orchestration:** the Run receipt showing intake, plan, review gate, coordination, and the contractor handoff.
3. **Peak evidence moment:** the framing photo rejected with the specific wide-location-photo re-request while the synthetic-data badge remains visible.
4. **Deadline judgment:** the T−2 keep-date-or-reschedule interrupt.
5. **Final artifact:** the approved command center and citation-to-evidence pages from the generated reinspection packet.

## AWS proof captures

Capture these after a successful controlled acceptance run. Use still images or a short pre-recorded clip; do not leave the final video waiting for a scheduled event.

1. **AgentCore is real:** Bedrock AgentCore Runtime shows Mettle in `READY` state.
2. **The workflow wakes itself up:** a continuous or clearly timestamped capture shows the browser closed, then CloudWatch logs show the private scheduler worker executing a hashed workflow reference and advancing the campaign.
3. **The next checkpoint is autonomous:** the acceptance record shows schedule version 1 replaced by version 2 after the worker run.
4. **Failures are bounded:** the scheduler DLQ is empty and the scheduler alarm is `OK` after the acceptance run.

The final cut needs only the first two proof stills. Keep the others available for the README, Devpost gallery, or judge questions.

## Redaction checklist

- Hide the 12-digit AWS account ID everywhere, including the console header.
- Hide ARNs, session identifiers, Cognito subjects, emails, usernames, phone numbers, and S3 object keys.
- Show only hashed workflow references in logs.
- Do not show AWS credentials, terminal environment variables, browser developer tools, or private notice payloads.
- Do not crop away the AWS service name, runtime state, timestamp, or scheduler action that makes the proof understandable.

## Truthful narration boundaries

- `LIVE · STRANDS` proves the real local Strands graph and native interrupts.
- `SAMPLE CAMPAIGN · SYNTHETIC DATA` proves the complete product journey without model spend.
- The authenticated cloud path proves the same typed workflow running on AgentCore with Nova-backed intake and evidence assessment.
- The scheduler stills prove a completed deployed acceptance run; they are not presented as a live event firing during the recording.
- Mettle verifies visible evidence sufficiency, never building-code compliance.
- Models never decide deadlines, gates, or what Mettle may claim; those boundaries remain deterministic and contractor-controlled.
- One-way SNS delivery remains disabled until an approved demo destination is enrolled; inbound SMS is not part of the product.

## Final quality gate

- [ ] Every screenshot is readable at normal YouTube playback size.
- [ ] No capture reveals an account identifier or personal information.
- [ ] The peak evidence re-request occurs before the architecture explanation.
- [ ] The video demonstrates a model specialist, deterministic policy, autonomous scheduling, and a meaningful human interrupt.
- [ ] The final cut is 4:45 or shorter and plays while signed out.
