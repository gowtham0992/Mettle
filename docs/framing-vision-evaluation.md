# Framing evidence regression

The framing check now distinguishes recognizing a protection plate from
establishing coverage of every location requested by a notice. It does not
certify construction, hidden work, dimensions, or building-code compliance.

## Failure and fix

The original live evaluation accepted a tight close-up three times despite
the requirement to show **each corrected location**. The older wide fixture
was also a poor positive control: the relationship between its plates and the
bored framing was unclear.

Requirements containing “each”, “every”, or “all” now require a separate typed
coverage finding. A model's `shown` verdict cannot become accepted evidence
when its coverage finding is partial or uncertain. Omitted coverage fails the
output contract and follows the existing contractor-review path.

The replacement asset, `framing-plates-visible-v2.png`, visibly shows three
cable crossings and their plates. It was generated with the built-in image
tool and explicitly marked “SYNTHETIC TEST IMAGE — NOT A REAL JOB”. It is a
test fixture, not independently validated construction evidence. The older
asset remains available for historical links, but current sample, walkthrough,
and packet references use the replacement.

## Observed live results — September 6, 2026

Two post-fix batches, each with three repetitions per image, passed all
18 safety-outcome checks through the deployed AgentCore/Nova Lite path:

| Input | Required outcome | Observed |
| --- | --- | --- |
| Replacement framing fixture | Accepted as visible evidence | 6/6 accepted |
| Tight framing close-up | Never accepted | 6/6 rejected or held for contractor review |
| Unrelated Mettle mark | Rejected | 6/6 rejected |

Each assessment restored the same pre-evidence checkpoint in a fresh runtime
session. No fixture-adapter result substituted for a model call. The second
batch used a separate single-correction notice. All outreach was recorded-only.

Four added contract tests were observed failing before the implementation and
passing afterward. The full automated verification suite passed 223 checks.

These are repeated checks of three synthetic images, not a broad accuracy
benchmark or a guarantee of performance on real job-site photos. Rejection vs.
manual-review wording can vary; neither may mark the proof ready. Real project
identity and full site coverage still require contractor judgment.

## Repeat the check

From the repository root, run `scripts/framing_vision_smoke.py` with the project
Python environment. Its required `--runtime-id` is supplied locally, never
committed. `--allow-model-spend` explicitly enables paid calls; `--repeat` is
bounded to 1–5 and defaults to 3. The runner refuses live-SMS configuration,
prints no runtime IDs or private payloads, and exits nonzero on any unexpected
outcome. It performs one live intake plus three photo assessments per repetition.

Generation brief: synthetic, sharply lit timber wall; three horizontal cable
crossings through studs, a flat protection plate at each crossing, visible
surrounding context, no boxes or occluding tools, and an explicit synthetic
footer. Do not use the generated image as evidence of work at an actual site.
