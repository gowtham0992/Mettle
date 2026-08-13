# Contractor operator research

Updated: 2026-08-13

## Decision

Mettle should be a short-lived failed-inspection recovery workspace, not a general construction management system. A small general contractor should be able to open a recovery from an inspection report, confirm how each correction can be closed, identify the responsible trade, and then work from one next-action queue until a contractor-approved packet is ready.

The core outcome is: **a GC can turn a failed-inspection report into a controlled recovery run in five minutes, without requiring subcontractors to install another app.**

## What the local process establishes

Douglas County schedules inspections for the next business day when requested before 3:30 p.m. and publishes real-time inspection results online. Inspection requests require a permit number and inspection type. This makes the permit/report—not a manually configured project—the correct starting object for Mettle.

- [Douglas County building inspections](https://www.douglasco.gov/building-division/building-inspections/)
- [Douglas County building records and permit search](https://apps.douglasco.gov/building/services/Default.aspx?PosseObjectId=16634210&PossePresentation=Help)

Public Douglas County records show that a single disapproval can mix several trades and several kinds of closure. A residential rough-frame report can contain eight numbered corrections spanning plans, framing, HVAC, plumbing, and electrical. Other reports show failures caused by missing access/contact information or inspections requested before prerequisite work was ready.

- [Eight-item residential rough-frame disapproval](https://apps.douglas.co.us/building/services/Report.aspx?PosseObjectId=93806135&PosseReport=BuildingInspectionPreview)
- [Disapproval caused by missing site contact](https://apps.douglas.co.us/building/services/Report.aspx?PosseObjectId=102385511&PosseReport=BuildingInspectionPreview)
- [Disapproval caused by incomplete prerequisites](https://apps.douglas.co.us/building/services/Report.aspx?PosseObjectId=94797290&PosseReport=BuildingInspectionPreview)

The closure path is not uniform. One Douglas County permit history records a rough-electrical approval after photos were sent, while other corrections were recalled for an in-person inspection and some required engineering letters or documents. Mettle therefore must not equate “photo accepted by AI” with “inspection closed.” The contractor chooses the authority-approved closure path for each item: photo/document review, engineer or manufacturer documentation, or physical reinspection.

- [Douglas County permit history with photo acceptance, recalls, and engineering-letter dependencies](https://apps.douglas.co.us/building/services/Default.aspx?PosseObjectId=74734884&PossePresentation=PermitDetails)

Reinspection fees are real but not the primary value proposition. Douglas County may assess them for missing plans, missing access, or deviations from approved plans; an older published schedule lists a $47 electrical reinspection fee. Avoided delay, return trips, withheld completion payments, and reduced chasing are likely more valuable than the fee alone.

- [Douglas County common code amendments on reinspection fees](https://www.douglasco.gov/documents/building-codes-exhibit-a-amendments-to-common-to-all-adopted-codes.pdf/)
- [Douglas County building fee schedule](https://www.douglasco.gov/documents/building-fees.pdf/)

## What contractors already tolerate

The reviewed product field points to three established behaviors:

1. Photos and checklists are useful when the requested proof is explicit. CompanyCam emphasizes that unstructured photo capture creates gaps and that inspection/closeout checklists reduce guesswork.
2. Assignment, schedule confirmation, and document sharing already exist in broad systems such as Buildertrend. Rebuilding those as a generic project manager would make Mettle weaker and harder to adopt.
3. Crews continue to use chat and text. Banamind explicitly builds around WhatsApp so field workers do not change behavior, and contractor discussions repeatedly describe field adoption failing when updates require office-style software.

- [CompanyCam on construction photo documentation and checklists](https://companycam.com/resources/blog/construction-photo-documentation-a-contractors-guide-to-protecting-your-work)
- [Buildertrend subcontractor management](https://buildertrend.com/communication/subcontractor-software/)
- [Buildertrend schedule confirmations](https://buildertrend.com/help-article/advanced-schedule-overview/)
- [Banamind’s chat-first construction workflow](https://banamind.ai/)
- [Practitioner discussion: projects still managed in texts and spreadsheets](https://www.reddit.com/r/ConstructionManagers/comments/1jldzkc/we_tried_5_tools_still_managing_projects_in_texts/)

The competitive wedge is narrow. PermitFlow covers permitting, AHJ coordination, inspection tracking, and closeout at a broader operational layer. Banamind captures and structures ongoing jobsite communications and can inspect photos. Mettle should claim neither generic photo intelligence nor general construction coordination. Its specific job is a notice-anchored, deadline-aware recovery run with contractor-owned decisions.

- [PermitFlow](https://www.permitflow.com/)
- [Banamind](https://banamind.ai/)

## Product requirements derived from the evidence

### Build now

- Two honest entry points: **Start a recovery** and **Try the sample campaign**.
- A setup path that asks for the failed-inspection text/report, the working date, and editable trade contacts.
- A review step that makes clear that Mettle drafts and records outreach; it does not contact an inspector or certify compliance.
- One dominant **Next action** after setup. Priority order: contractor judgment, collect/assess evidence, run the next scheduled check, prepare packet, approve packet, download packet.
- Real-run UI should hide synthetic evidence fixtures. They remain available only in the sample campaign.
- A visible public-demo warning: use sample or redacted information unless signed into a protected deployment.
- Restore an active recovery from its URL/session where the backend supports it.

### Build next if validated

- Import a public permit/report URL or permit number instead of requiring pasted text.
- Per-citation closure path: photo/document review, engineer letter, or physical reinspection.
- Preview/edit derived citations and evidence requests before outreach is released.
- SMS/MMS delivery with explicit contractor approval, recipient consent, opt-out handling, and a delivery audit trail.
- Inspector scheduling handoff that opens the authority’s official portal; do not automate inspector contact without approval.

### Skip

- Estimating, invoicing, job costing, CRM, broad project scheduling, plan management, and daily logs.
- Autonomous code interpretation or claims that a photo proves code compliance.
- An inspector-facing submission without contractor approval.
- Requiring each subcontractor to create a Mettle account or install an app.

## Assumptions and kill criteria

The strongest evidence here is the official workflow and public report shape. The adoption conclusions are supported by vendor behavior and practitioner discussion but still need direct interviews.

Pause or reposition the product if contractor interviews show any of the following:

- Most failed residential inspections are corrected and recalled by one person within the same day.
- The GC does not need to chase evidence across trades.
- Inspectors in the target jurisdiction will not accept any remote evidence or documentation.
- Subcontractors will not reply to a dedicated project number with photos.

The cheapest validation is five conversations using a real disapproved report: ask how corrections were divided, which items required a call to the inspector, which proof was accepted remotely, how many follow-ups were needed, and what work or payment remained blocked until approval.
