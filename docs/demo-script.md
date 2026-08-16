# Mettle demo script

Target length: **4:35**. Hard limit: **5:00**.

Record at 1440×900 or 1920×1080 with browser zoom at 100%. Hide bookmarks, notifications, AWS account identifiers, and every developer console. Use a fresh private window for the public demo. Keep the architecture PNG and one generated packet open in separate tabs before recording.

## 0:00–0:28 — The person, problem, and stakes

**On screen:** Mettle welcome screen, then a close crop of the synthetic failed-inspection notice.

**Narration:**

> A small residential contractor fails an inspection. Now they have to translate a municipal notice into work for several trades, chase the right proof over text, watch the reinspection date, and rebuild the evidence trail by hand. One missed correction can mean another fee and another week of delay. Mettle turns that notice into a recovery campaign—and leaves every professional judgment with the contractor.

## 0:28–1:42 — Prove the real Strands workflow first

**On screen:** Select **Start a recovery**. Paste the included synthetic notice, continue through **People**, and choose the free local extraction button. Show the setup status changing to `LIVE · STRANDS`.

**Narration:**

> This is the real Strands workflow, not the guided playback. Mettle starts from the document the contractor already has—there is no project template or manually authored punch list. The intake graph converts the notice into typed citations while preserving its wording. Before a single outreach record is created, a native Strands interrupt pauses the graph so the contractor can confirm who owns each correction.

**On screen:** Approve correction routing. Open **Agent Run** and point to intake, plan, review gate, coordination, and the completed handoff. Briefly show the recovery clock and correction cards.

**Narration:**

> Once approved, deterministic policy coordinates only the open corrections. The Agent Run makes that boundary inspectable: a model-backed intake specialist handles unstructured language; policy nodes own dates, retries, and permissions; the contractor owns authority. Idempotency keys prevent a retry from repeating outreach or model spend.

## 1:42–3:12 — Show the complete product journey

**On screen:** Return home and select **Try the sample campaign**. Keep the `SAMPLE CAMPAIGN · SYNTHETIC DATA` label visible. Run the compressed recovery.

**Narration:**

> The public sample compresses a multi-day campaign into ninety seconds using disclosed synthetic data. It lets us show the complete product experience without spending a judge's AWS credit.

**On screen:** Pause on the accepted electrical evidence, then the rejected framing evidence and its specific re-request.

**Narration:**

> The evidence specialist accepts the panel photo because the required label and breaker position are visible. This framing photo is not enough: the location and full clearance are missing, so Mettle asks for a wider shot instead of pretending the correction passed. In the live cloud path, a dedicated multimodal Strands agent on Nova Lite performs this visible-proof assessment. It never claims code compliance.

**On screen:** Advance to the T−2 deadline gate. Choose **Keep the date** and continue.

**Narration:**

> As the deadline approaches, the chase changes cadence and considers only unresolved citations. At T-minus-two, Mettle does not silently gamble with the schedule. A second native interrupt asks the contractor whether to keep the date or reschedule.

## 3:12–3:55 — Human authority and final artifact

**On screen:** Resolve the ambiguous mechanical evidence requirement. Approve the packet, download it, and scroll the citation-to-evidence table.

**Narration:**

> Ambiguous notice language is another hard boundary: the contractor defines what visible proof is needed. After every citation has accepted evidence, Mettle assembles this traceable packet—but download stays blocked until final contractor approval. The result maps each notice citation to its trade, evidence, timeline, and consent record.

## 3:55–4:28 — Architecture and technical credibility

**On screen:** Show `assets/architecture/mettle-product-architecture.png` first. Trace the campaign loop and its three human judgment gates. Then switch to `assets/architecture/mettle-aws-architecture.png` and trace the authenticated request path into AgentCore.

**Narration:**

> Mettle separates authority three ways. Amazon Nova models handle notice language and visible evidence. Deterministic Python controls state, deadlines, retries, and permissions. The licensed contractor decides interpretation, schedule tradeoffs, and release. In AWS, the public browser reaches one authenticated Lambda gateway before the same typed operations run on Amazon Bedrock AgentCore Runtime; credentials, model access, state, and private evidence stay server-side.

## 4:28–4:35 — Close

**On screen:** Return to the approved command center with the result visible.

**Narration:**

> Notice in. Reinspection ready. Mettle handles the chase; the contractor decides.

## Recording checklist

- [ ] Keep the finished cut at or below 4:45 to leave upload-transcode margin.
- [ ] Say the problem, target user, and why it matters in the first 28 seconds.
- [ ] Show `LIVE · STRANDS` before the synthetic sample.
- [ ] Keep the sample disclosure visible when describing compressed evidence and time.
- [ ] Show one native interrupt, one evidence re-request, the deadline gate, and final approval.
- [ ] Show the architecture diagram long enough to read `Strands` and `AgentCore Runtime`.
- [ ] Upload publicly or unlisted to YouTube or Vimeo and test the URL while signed out.
