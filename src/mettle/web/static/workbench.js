(function exposeWorkbench(root) {
  // Presentation is derived from the server campaign; no parallel recovery state.
  function selectedCitation(data, requested) {
    return data.citations.find(c => String(c.citation_id) === String(requested))
      || data.citations.find(c => c.stage !== "ready") || data.citations[0] || null;
  }
  function recoverySummary(data) {
    const ready = data.citations.filter(c => c.stage === "ready").length;
    const pending = data.judgments.filter(j => j.status === "pending");
    const approved = data.packet_status === "approved";
    return {
      ready, total: data.citations.length, pending: pending.length,
      title: data.recovery_hold ? "Your recovery needs an operator’s review."
        : data.correction_review_required ? "Your notice is read. Let’s check the plan."
        : approved ? "The handoff is ready."
        : pending.length ? "A little needs you. The rest is moving."
        : ready === data.citations.length && ready > 0 ? "One last look. Then you’re ready."
        : "Your recovery, moving forward.",
      background: approved ? "Follow-up stopped."
        : data.recovery_hold ? "Recovery safely held."
        : data.automation_status === "scheduled" ? "Your next check is scheduled."
        : pending.length ? "Waiting for your decision."
        : data.source_mode !== "workflow" ? "Recorded sample activity."
        : "No background check is active.",
    };
  }
  function render(data, api) {
    const {node, openCorrection, renderJudgment, renderEvidenceRoute, renderEvidencePhoto, setWorkspaceView, elements} = api;
    const $ = id => document.getElementById(id);
    const summary = recoverySummary(data);
    const selected = selectedCitation(data, elements.photoCitation.value);
    $("docket-title").textContent = summary.title;
    $("workbench-count").textContent = `${summary.ready} of ${summary.total} ready`;
    // Today always owns the next step; Packet already has its own real actions.
    $("today-action-slot").append(elements.nextAction);
    if (data.automation_status !== "scheduled" && data.packet_status !== "approved") {
      elements.workspaceAgentTitle.textContent=summary.background;
      elements.workspaceAgentCopy.textContent=data.source_mode !== "workflow"
        ? "This sample uses recorded outcomes, not background cloud execution."
        : data.correction_review_required ? "Review the plan before outreach can begin."
        : data.execution_target === "agentcore" ? "Mettle is not scheduling further outreach in this state."
        : "This local run records operations; it does not schedule cloud wake-ups.";
    }
    // The long activity receipt remains available; Today gets only recent outputs.
    const activity = $("workbench-activity");
    const heading = node("div", "workbench-agent-heading");
    heading.append(node("span", "workbench-agent-symbol", "✳"), node("h2", "", data.packet_status === "approved" ? "The work, handled" : "Mettle is on it"));
    const mode = node("p", "workbench-mode", data.source_mode === "workflow" ? "This recovery · recorded actions and outcomes" : "Recorded sample · no live model calls");
    const entries = node("ol", "workbench-events");
    for (const event of data.events.slice(-3).reverse()) {
      const item = node("li", "");
      item.append(node("span", "mono-label", event.actor || "Recovery policy"), node("h3", "", event.title), node("p", "", event.detail));
      entries.append(item);
    }
    if (!entries.children.length) entries.append(node("li", "", "Once the notice is reviewed, the recorded recovery actions appear here."));
    const foot = node("div", "workbench-agent-foot");
    foot.append(node("strong", "", summary.background));
    if (data.next_check_at && data.automation_status === "scheduled") foot.append(node("p", "", `Next check: ${new Date(data.next_check_at).toLocaleString()}. You can close this page.`));
    const inspect = node("button", "button button--outline", "See the agent work →"); inspect.type = "button";
    inspect.onclick = () => setWorkspaceView("activity", {updateUrl:true, focusTab:true});
    activity.replaceChildren(heading, mode, entries, foot, inspect);
    // Packet rows are real links to each correction, including accepted records.
    for (const [index,row] of [...elements.packetList.children].entries()) {
      row.querySelector(".packet-row__open")?.remove();
      const button = node("button", "button button--outline packet-row__open", "Review →"); button.type="button";
      button.setAttribute("aria-label", `Review correction ${data.citations[index].citation_id}`);
      button.onclick = () => openCorrection(data.citations[index].citation_id);
      row.append(button);
    }
    let cover = $("workbench-packet-cover");
    if (!cover) {cover=node("aside","packet-cover");cover.id="workbench-packet-cover";document.querySelector(".packet-layout").append(cover);}
    cover.replaceChildren(node("p","mono-label","Your handoff, assembled"), node("h2","",data.property_label), node("p","", "Reinspection evidence packet"), node("div","packet-cover__line", `${summary.ready} / ${summary.total} evidence sets ready`), node("p","", "01 · Notice and exact requirements"), node("p","", "02 · Evidence and source records"), node("p","", "03 · Contractor decisions"), node("small","", "Mettle assembles the record. The contractor approves release. Code compliance is not certified."));
    if (!selected) {
      $("correction-title").textContent="No corrections yet";
      $("correction-subtitle").textContent="Start with a correction notice to build your recovery.";
      document.querySelector(".correction-layout").hidden=true;
      return;
    }
    document.querySelector(".correction-layout").hidden=false;
    const id=String(selected.citation_id);
    $("correction-tabs").replaceChildren(...data.citations.map(c=>{
      const button=node("button", "button button--outline", `C${c.citation_id} · ${c.trade}`);button.type="button";
      button.setAttribute("aria-pressed",String(String(c.citation_id)===id));button.onclick=()=>openCorrection(c.citation_id);return button;
    }));
    $("correction-context").textContent=`Correction ${id} · ${selected.stage.replaceAll("_"," ")}`;
    $("correction-title").textContent=`${selected.trade.charAt(0).toUpperCase()+selected.trade.slice(1)} correction`;
    $("correction-subtitle").textContent=selected.assignee || "Awaiting contractor review before outreach";
    $("correction-source-title").textContent=selected.code_reference && selected.code_reference !== "Not stated in notice" ? selected.code_reference : "Original correction · no code cited";
    $("correction-source-text").textContent=selected.notice_text;
    $("correction-requirements").replaceChildren(...(selected.evidence_requirements.length ? selected.evidence_requirements : ["The notice does not define observable proof. Contractor direction is required."]).map(r=>node("li","",r)));
    $("correction-authority-note").textContent="The original notice stays unchanged. Evidence acceptance is not a code-compliance certificate.";
    const pending=data.judgments.filter(j=>j.status==="pending" && String(j.citation_id||"")===id);
    $("correction-decision").replaceChildren(...pending.map(j=>renderJudgment(j, {photoReview:true})));
    $("correction-decision").hidden=!pending.length;
    const beforeReview = data.correction_review_required || data.judgments.some(j=>j.judgment_id==="route-review" && j.status==="pending");
    if (beforeReview && !pending.length) {
      const held=node("article","judgment");
      held.append(node("p","mono-label","Nothing sends yet"),node("h3","","Review the recovery plan first."),node("p","","Confirm assignments and proof requests before starting outreach or adding evidence."));
      const review=node("button","button button--orange","Review the plan →");review.type="button";
      review.onclick=()=>{setWorkspaceView("recovery",{updateUrl:true});elements.nextActionButton.click();};
      held.append(review);$("correction-decision").replaceChildren(held);$("correction-decision").hidden=false;
    }
    const history=$("correction-history");
    history.replaceChildren();
    const assessment=[...(data.evidence||[])].reverse().find(a=>String(a.citation_id)===id);
    let photo=$("stored-evidence");
    if (!photo) { photo=node("section","stored-evidence");photo.id="stored-evidence";$("correction-decision").before(photo); }
    renderEvidencePhoto(photo, assessment, $("correction-decision"));
    if (selected.evidence_note || assessment) {
      history.append(node("p","mono-label","Evidence record"),node("h2","",selected.stage==="ready" ? "Proof is ready for your packet." : "What Mettle needs next"),node("p","",assessment?.explanation || selected.evidence_note));
    }
    const next=data.citations.find(c=>c.stage!=="ready" && String(c.citation_id)!==id);
    if (selected.stage==="ready") {
      const button=node("button","button button--orange",next ? `Continue to C${next.citation_id} →` : "Review the packet →");button.type="button";
      button.onclick=()=>next ? openCorrection(next.citation_id) : setWorkspaceView("evidence",{updateUrl:true,focusTab:true});
      history.append(button);
    }
    history.hidden=!history.children.length;
    $("correction-back").onclick=()=>setWorkspaceView("recovery",{updateUrl:true,focusTab:true});
    // Reuse the existing route controls and all their server-side enforcement.
    renderEvidenceRoute(data);
    $("evidence-title").textContent=selected.stage === "ready" ? "Your accepted evidence" : "Add the required proof";
    elements.evidencePanel.hidden=Boolean(beforeReview);
    if (data.source_mode !== "workflow") {
      elements.photoForm.hidden=true;
      elements.demoEvidence.open=true;
      for (const fixture of elements.demoEvidence.querySelectorAll(".evidence-fixture")) {
        const button=fixture.querySelector("button");
        fixture.hidden=String(button.dataset.citation || "1")!==id;
      }
    }
  }
  const api={selectedCitation,recoverySummary,render};
  if(typeof module!=="undefined" && module.exports)module.exports=api;
  root.MettleWorkbench=api;
}(globalThis));
