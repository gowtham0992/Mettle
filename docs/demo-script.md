# Mettle demo script

Target length: **4:25**. Hard limit: **5:00**.

Record at 1440×900 or 1920×1080 with browser zoom at 100%. Hide bookmarks, notifications, AWS account identifiers, and every developer console. Use a fresh private window for the public demo. Keep the architecture PNG, one generated packet, and two sanitized AWS proof stills open in separate tabs before recording. Never wait for a live scheduler on camera; show the verified execution record and label the timeline compression.

## 0:00–0:28 — The person, problem, and stakes

**On screen:** Mettle welcome screen, then a close crop of the synthetic failed-inspection notice.

**Narration:**

> A small residential contractor fails an inspection. Now they have to translate a municipal notice into work for several trades, chase the right proof over text, watch the reinspection date, and rebuild the evidence trail by hand. One missed correction can mean another fee and another week of delay. Mettle turns that notice into a recovery campaign—and leaves every professional judgment with the contractor.

## 0:28–1:13 — Prove notice-first intake and the real Strands gate

**On screen:** Select **Start a recovery**. Paste `examples/notices/denver-remodel.txt`—not the notice used by the tour—continue through **People**, and choose the free local extraction button. Show the setup status changing to `LIVE · STRANDS`, the grounded correction candidates, and the zero-outreach review gate.

**Narration:**

> This notice has a different jurisdiction, header style, date format, and trade mix from the sample. Mettle starts from the document the contractor already has—there is no project template or manually authored punch list. Local intake preserves each correction as a grounded candidate; uncertainty becomes contractor review, not a fabricated code or proof requirement. Before a single outreach record is created, a native Strands interrupt pauses the graph so the contractor can confirm every route.

**On screen:** Point to `0 messages`, approve correction routing, then show the recorded outreach count change. Open **Run receipt** only long enough to show the model/policy/human legend.

**Narration:**

> The decision changes what the graph is allowed to do: only after approval does coordination begin. In the authenticated cloud path, Nova Micro handles unstructured notice language. Deterministic policy—not a model—owns dates, retries, gates, and permissible claims. The contractor owns professional authority.

## 1:13–2:43 — Show the complete product journey

**On screen:** Return home and select **Take the 90-second tour**. Keep the `GUIDED EVALUATOR PATH · SYNTHETIC DATA` label visible. Follow the recovery line through the staged campaign.

**Narration:**

> The public sample compresses a multi-day campaign into ninety seconds using disclosed synthetic data. It lets us show the complete product experience without spending a judge's AWS credit.

**On screen:** Pause on the accepted electrical evidence, then the rejected framing evidence and its specific re-request.

**Narration:**

> The evidence specialist accepts the panel set because the full work area and measured clearance are visible. The framing photo is not enough: its wider wall location is missing, so Mettle asks for that specific view instead of pretending the correction passed. In the live cloud path, a dedicated multimodal Strands agent on Nova Lite performs this visible-proof assessment. It never claims code compliance.

**On screen:** Advance to the T−2 deadline gate. Choose **Keep the date** and continue.

**Narration:**

> As the deadline approaches, the chase changes cadence and considers only unresolved citations. At T-minus-two, Mettle does not silently gamble with the schedule. A second native interrupt asks the contractor whether to keep the date or reschedule.

## 2:43–3:25 — Human authority and final artifact

**On screen:** Finish the background recovery, approve the packet at the final gate, select **Inspect the Strands agent run**, then open **Evidence & packet** to download it.

**Narration:**

> The ambiguous mechanical requirement was the tour’s first hard boundary: the contractor defined the visible proof before recovery began. After every citation has accepted evidence, Mettle assembles this traceable packet—but download stays blocked until final contractor approval. The result maps each notice citation to its trade, evidence, timeline, and consent record.

## 3:25–4:10 — Prove unattended cloud work, then explain the architecture

**On screen:** Show a short pre-recorded sequence with two visible wall-clock timestamps: an authenticated AgentCore recovery with a checkpoint armed, the browser closed, then the later EventBridge/CloudWatch acceptance record showing the private worker fired and the next checkpoint was armed. Show the waiting contractor judgment in Mettle. Then show `assets/architecture/mettle-product-architecture.png` with its three gates and `assets/architecture/mettle-aws-architecture.png` just long enough to connect EventBridge to AgentCore. Crop all account identifiers and keep only hashed workflow references visible.

**Narration:**

> Nobody touched the dashboard between these timestamps. EventBridge woke the private worker, AgentCore resumed the same typed Strands workflow, open-only policy advanced the chase, and Mettle stopped at a judgment it was not allowed to make. That is bounded authority: Nova models handle notice language and visible evidence; deterministic Python controls state, deadlines, retries, gates, and permissible claims; the licensed contractor decides interpretation, schedule tradeoffs, and release.

## 4:10–4:25 — Close

**On screen:** Return to the approved command center with the result visible.

**Narration:**

> Fifteen actions absorbed. Three decisions kept. Mettle ran the recovery while the contractor worked another job—and stopped, every time, at the line where a license matters. Notice in. Reinspection packet out. The contractor decides.

## Recording checklist

- [ ] Keep the finished cut at or below 4:45 to leave upload-transcode margin.
- [ ] Say the problem, target user, and why it matters in the first 28 seconds.
- [ ] Show `LIVE · STRANDS` before the synthetic sample.
- [ ] Keep the sample disclosure visible when describing compressed evidence and time.
- [ ] Show zero outreach before route approval, then the changed outreach count after approval.
- [ ] Show one native interrupt, one evidence re-request, the deadline gate, and final approval.
- [ ] Show the architecture diagram long enough to read `Strands` and `AgentCore Runtime`.
- [ ] Show sanitized `READY` and scheduler-execution proof; hide the account ID, ARNs, usernames, emails, session identifiers, and raw notice content.
- [ ] Show two readable wall-clock timestamps around the recorded scheduler run and state that the browser was closed.
- [ ] Describe the scheduler proof as a recorded deployed acceptance run, not as a live event occurring during the final narration.
- [ ] Upload publicly or unlisted to YouTube or Vimeo and test the URL while signed out.
