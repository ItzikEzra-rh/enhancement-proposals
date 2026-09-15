# Testplan — OSAC-3459

## Overview

- **Feature:** OSAC-3459 — BMaaS Provisioning Progress and Step Visibility
- **Total test cases:** 17
- **Requirements covered:** 8 of 8 approved-design traceability IDs
  (`FR-1`…`FR-5`, `NFR-1`…`NFR-3`)
- **Interface changes covered:** 6 of 6 (`IC-1`…`IC-6`)

The published PRD describes the behavior but does not label individual
requirements as `FR-*` or `NFR-*`. This plan preserves the requirement IDs
already used by the approved design and its graduation criteria. The headings'
descriptions are derived from the PRD prose and the design's IC requirement
mapping; no new requirement IDs are introduced.

The expected results below describe the approved behavior, not the current
implementation. Current implementation gaps and contradictory source behavior
are recorded under [Gaps](#gaps) and [Source-behavior constraints](#source-behavior-constraints).

## Test Cases

### FR-1: Expose the four ordered provisioning phases and their states

#### TC-FR1-01: API status exposes the staged provisioning progression

| Interface Change | Priority | Automation |
|-----------------|----------|------------|
| IC-1, IC-2 | critical | automated |

##### Preconditions

- A `BareMetalInstance` CR fixture can be reconciled with lifecycle conditions
  representing allocation, opaque provisioning, network setup, and powered-on
  readiness.
- The fulfillment reconciler and API status projection are running against the
  fixture.

##### Steps

1. Reconcile with no lifecycle milestone true and query the instance status.
2. Mark `Allocated` true, reconcile, and query the status.
3. Mark `ProvisionTemplateComplete` true, reconcile, and query the status.
4. Mark all approved network completion conditions true, reconcile, and query
   the status before `PowerSynced` is true.
5. Mark the powered-on readiness signal true, reconcile, and query the status.

##### Expected Results

- The `PROVISIONED` condition is false with reason `HostAllocation` before
  allocation, false with reason `Provisioning` after allocation, and false with
  reason `NetworkSetup` after opaque provisioning.
- After provisioning and network completion, `PROVISIONED` is true with reason
  `Provisioned`; the first three user-facing steps are complete and Ready is
  the current step until readiness is reported.
- After powered-on readiness, `READY` is true with reason `Ready`, and the
  status contains the curated terminal message for Ready.

#### TC-FR1-02: Detail view derives ordered step states from existing conditions

| Interface Change | Priority | Automation |
|-----------------|----------|------------|
| IC-4 | high | automated |

##### Preconditions

- The UI detail component receives API fixtures for each stage reason and for
  the terminal `READY` condition.

##### Steps

1. Render the detail view with `PROVISIONED.reason=HostAllocation`.
2. Render it with `PROVISIONED.reason=Provisioning`.
3. Render it with `PROVISIONED.reason=NetworkSetup`.
4. Render it with `PROVISIONED=True` and `READY=False`.
5. Render it with `PROVISIONED=True` and `READY=True`.

##### Expected Results

- The view always shows exactly these ordered labels: Host Allocation,
  Provisioning, Network Setup, and Ready.
- For each in-progress fixture, steps before the named stage are shown as
  complete, the named stage is shown as in progress, and later steps are shown
  as not started.
- With `PROVISIONED=True` and `READY=False`, Ready is shown as in progress.
- With both conditions true, all four steps are shown as complete.

#### TC-FR1-03: A no-network-attachment instance completes Network Setup

| Interface Change | Priority | Automation |
|-----------------|----------|------------|
| IC-2, IC-4 | medium | automated |

##### Preconditions

- The instance has no network attachments.
- Allocation, opaque provisioning, and powered-on readiness can be advanced in
  the test fixture.

##### Steps

1. Reconcile the instance through allocation and opaque provisioning.
2. Reconcile the no-network path.
3. Query the API status and render the detail view.

##### Expected Results

- Network Setup is represented as complete, not pending or in progress.
- The API advances to the approved provisioning-complete state without waiting
  for a network attachment condition that cannot exist.
- The UI shows Network Setup complete and does not show a stalled pending phase.

### FR-2: Derive the furthest-advanced phase deterministically

#### TC-FR2-01: Stage derivation is independent of condition order

| Interface Change | Priority | Automation |
|-----------------|----------|------------|
| IC-2, IC-6 | medium | automated |

##### Preconditions

- A table of equivalent operator condition sets is available in multiple list
  orders, including allocation, provisioning, network, and readiness milestones.

##### Steps

1. Pass each ordered condition set to `DeriveProvisioningProgress`.
2. Repeat with the same conditions permuted into every relevant order.
3. Compare the derived stage, terminal flags, and failure classification.

##### Expected Results

- Every permutation produces the same stage, `provisioned`, `ready`, and
  `failed` values.
- The selected stage is the furthest-advanced true milestone in the approved
  ordered vocabulary, not the last condition encountered in the slice.

#### TC-FR2-02: Operator mapping is exhaustive and collapses opaque retries

| Interface Change | Priority | Automation |
|-----------------|----------|------------|
| IC-6 | medium | automated |

##### Preconditions

- The operator package exposes the `HostCondition*` constants used by the CR
  lifecycle.
- Fixtures cover the opaque provisioning job, network job, IP discovery job,
  power condition, retry, and deprovisioning/offboarding condition paths.

##### Steps

1. Run the co-located exhaustiveness test over every exported lifecycle
   condition constant.
2. Present a non-terminal retry within a stage and then a terminal success for
   the same stage.
3. Present the deprovisioning/offboarding conditions during deletion.

##### Expected Results

- Every condition is either mapped to an approved stage, terminal state, or an
  explicit not-surfaced classification; an unclassified condition fails the
  test.
- A retry within a stage leaves the derived stage unchanged until its driving
  condition reaches a terminal state.
- Deprovisioning/offboarding conditions do not create provisioning-progress
  stages.

#### TC-FR2-03: Fulfillment presentation changes terminal condition timing

| Interface Change | Priority | Automation |
|-----------------|----------|------------|
| IC-1, IC-2 | critical | automated |

##### Preconditions

- A fulfillment reconciler test fixture can supply the operator status at
  network-complete, pre-ready, and powered-on-ready points.

##### Steps

1. Call `syncStatus` with `ProvisionTemplateComplete=True` but at least one
   required network completion signal false.
2. Call `syncStatus` after all approved provisioning/network signals are true
   but before powered-on readiness.
3. Call `syncStatus` after powered-on readiness is true.

##### Expected Results

- `PROVISIONED` is not true merely because
  `ProvisionTemplateComplete=True` while required later signals are false.
- At full provisioning completion, `PROVISIONED=True` with reason `Provisioned`
  and its exact curated message; `READY` remains false until readiness.
- At powered-on readiness, `READY=True` with reason `Ready` and its exact
  curated message.

### FR-3: Refresh active progress and stop at terminal state

#### TC-FR3-01: Active detail view refreshes at the dedicated interval

| Interface Change | Priority | Automation |
|-----------------|----------|------------|
| IC-4 | high | automated |

##### Preconditions

- The detail view is mounted with a non-terminal instance.
- The API query client and clock can be controlled by the UI test.

##### Steps

1. Mount the detail view with `PROVISIONED.reason=Provisioning`.
2. Advance the test clock by the configured approximately five-second polling
   interval without user interaction.
3. Change the returned condition fixture to `NetworkSetup` and advance the
   clock through the next interval.

##### Expected Results

- The query issues a new single-instance GET on the dedicated approximately
  five-second interval while the instance is non-terminal.
- The displayed current step changes from Provisioning to Network Setup after
  the refreshed response, without a page reload or user action.
- The detail view does not use the global approximately ten-second interval as
  its active-provisioning interval.

#### TC-FR3-02: Terminal success and failure stop polling

| Interface Change | Priority | Automation |
|-----------------|----------|------------|
| IC-4 | high | automated |

##### Preconditions

- The detail view is mounted with active polling and a controllable query clock.

##### Steps

1. Return a terminal `READY=True` response and advance the clock through two
   polling intervals.
2. Remount or reset the fixture with a provisioning failure condition and
   advance the clock through two polling intervals.

##### Expected Results

- After terminal success, no additional instance GET is issued and all four
  steps remain complete.
- After terminal failure, no additional instance GET is issued and the failed
  step/message remain visible.

### FR-4: Preserve terminal and failure outcomes for the record lifetime

#### TC-FR4-01: Terminal success remains queryable after CR deletion

| Interface Change | Priority | Automation |
|-----------------|----------|------------|
| — | critical | automated |

##### Preconditions

- An instance record has persisted `PROVISIONED=True` and `READY=True` with the
  terminal reason/message.
- The hub CR can be deleted while the fulfillment record remains retained.

##### Steps

1. Delete the hub `BareMetalInstance` CR through the existing deletion/finalizer
   lifecycle.
2. Query the fulfillment API before the record is archived.

##### Expected Results

- The API returns the instance record with the persisted terminal conditions,
  including `Provisioned`/`Ready` reasons and curated messages.
- No per-phase historical array or duration is required in the response.

#### TC-FR4-02: Terminal failure remains queryable until archival

| Interface Change | Priority | Automation |
|-----------------|----------|------------|
| — | critical | automated |

##### Preconditions

- An instance record has persisted a failed phase, fixed failure reason, and
  curated message.
- The hub CR can be deleted and the record can be advanced through finalizer
  removal and archival.

##### Steps

1. Delete the hub CR and query the API while the fulfillment record is retained.
2. Archive the released fulfillment record using the existing lifecycle.
3. Query the public API again.

##### Expected Results

- Before archival, the API returns the failed phase, exact failure reason, and
  curated failure message.
- After archival, the public GET returns `404`; no archive-read path is
  introduced by this feature.

### FR-5: Show phase-specific human-readable failure information

#### TC-FR5-01: Failure reasons map to the complete fixed message vocabulary

| Interface Change | Priority | Automation |
|-----------------|----------|------------|
| IC-2, IC-5 | critical | automated |

##### Preconditions

- A table-driven fixture can provide each approved failure classification at its
  condition carrier.

##### Steps

1. Apply `NoMatchingHosts` to Host Allocation.
2. Apply `HostAllocationFailed` to Host Allocation.
3. Apply `ProvisionJobFailed` to Provisioning.
4. Apply `NetworkAttachmentFailed` to Network Setup.
5. Apply `NetworkHandoffFailed` to Network Setup.
6. Apply `IPDiscoveryFailed` to Network Setup.
7. Apply `ReadyTimeout` to Ready.
8. Run the fulfillment presentation for each fixture.

##### Expected Results

- Each reason maps to exactly its approved message:
  - `NoMatchingHosts` → `No bare metal host matched the requested profile.`
  - `HostAllocationFailed` → `Host allocation failed.`
  - `ProvisionJobFailed` → `OS installation and configuration did not complete; the provisioning job failed.`
  - `NetworkAttachmentFailed` → `Network attachment did not complete.`
  - `NetworkHandoffFailed` → `Network handoff (reboot) did not complete.`
  - `IPDiscoveryFailed` → `IP address discovery did not complete.`
  - `ReadyTimeout` → `The instance did not reach its powered-on ready state.`
- The failed condition carrier is `PROVISIONED` for Host Allocation,
  Provisioning, and Network Setup, and `READY` for Ready.
- No raw operator, AAP, Metal3, parser, or provider error text appears in the
  API message.

#### TC-FR5-02: UI identifies the failed step without a remediation action

| Interface Change | Priority | Automation |
|-----------------|----------|------------|
| IC-4, IC-5 | high | automated |

##### Preconditions

- The detail view receives each approved failed condition carrier and message.

##### Steps

1. Render the view with a Host Allocation failure.
2. Render it with Provisioning, Network Setup, and Ready failures.
3. Inspect the rendered controls and accessible text.

##### Expected Results

- The corresponding one of the four steps is marked failed and displays the
  exact curated message.
- Earlier steps remain complete and later steps remain not started.
- No retry, re-provision, remediation, log, or raw internal-error control/text
  is present.

### NFR-1: Reflect backend condition changes within single-digit seconds

#### TC-NFR1-01: Status reason/message changes traverse feedback Signal

| Interface Change | Priority | Automation |
|-----------------|----------|------------|
| IC-3 | critical | automated |

##### Preconditions

- A deployed or integration harness includes the hub Kubernetes API, the
  `osac-operator` feedback controller, fulfillment service, and its database.
- The instance has a known fulfillment identifier and a running detail query.

##### Steps

1. Record the time and current API `PROVISIONED.reason`/`message`.
2. Change only the corresponding CR status condition reason/message.
3. Wait for the existing feedback controller to signal fulfillment and for the
  next API read to return the new status.

##### Expected Results

- The feedback controller sends the existing `BareMetalInstances.Signal` RPC;
  no additional watch or update API is used.
- The API exposes the new reason/message in less than 10 seconds from the CR
  status change under the test environment's documented timing boundary.

#### TC-NFR1-02: Periodic full resync remains the freshness backstop

| Interface Change | Priority | Automation |
|-----------------|----------|------------|
| IC-3 | high | automated |

##### Preconditions

- The same integration harness can suppress or fail the feedback Signal call
  without changing the CR status.
- The fulfillment service periodic full-resync path is enabled.

##### Steps

1. Change a CR stage condition while the Signal path is unavailable.
2. Wait for the next existing full-resync cycle.
3. Query the API status.

##### Expected Results

- The API eventually exposes the CR-derived reason/message after the periodic
  full resync.
- No new watcher, informer, or schema field is required for the fallback.

### NFR-2: UI progress uses the approved coarse-condition contract

#### TC-NFR2-01: Read-only UI consumes existing status fields consistently

| Interface Change | Priority | Automation |
|-----------------|----------|------------|
| IC-4 | medium | manual |

##### Preconditions

- A deployed UI can display a BMaaS instance whose API response contains only
  the existing status condition fields.
- Reference progress displays for CaaS/VMaaS are available for comparison.

##### Steps

1. Open the BMaaS instance detail view for in-progress, terminal, and failed
   fixtures.
2. Compare the displayed progress semantics with the existing coarse-condition,
   staged-reason/message pattern.
3. Attempt to find a mutating progress action.

##### Expected Results

- The BMaaS view derives its four steps from existing `reason`, `message`, and
  condition status fields; no new API status field is required.
- The visible progress semantics use the same coarse current-stage pattern as
  the reference services while retaining the four BMaaS labels.
- The view provides no progress mutation, retry, or re-provision action.

### NFR-3: Keep the condition contract fixed, exhaustive, and non-leaking

#### TC-NFR3-01: New or changed operator conditions fail the exhaustiveness test

| Interface Change | Priority | Automation |
|-----------------|----------|------------|
| IC-6 | high | automated |

##### Preconditions

- The operator package contains the approved exhaustive mapping test adjacent to
  the `HostCondition*` definitions.

##### Steps

1. Run the mapping test against the current condition set.
2. Add a representative condition constant without adding a mapping, or use a
   fixture that simulates that change in the test harness.
3. Run the mapping test again, then add the explicit mapping or unsurfaced
   classification and rerun it.

##### Expected Results

- The current condition set passes because every condition has a mapped or
  explicit unsurfaced classification.
- The unclassified condition causes the test to fail and names that condition.
- Adding the classification makes the test pass without changing a CRD or
  generated type.

#### TC-NFR3-02: Stage presentation uses only the fixed condition vocabulary

| Interface Change | Priority | Automation |
|-----------------|----------|------------|
| IC-1 | high | automated |

##### Preconditions

- The fulfillment unit test can exercise every in-progress and terminal stage.
- The public proto descriptor is available to confirm the existing condition
  fields remain unchanged.

##### Steps

1. Reconcile fixtures for Host Allocation, Provisioning, Network Setup,
   Provisioned, and Ready.
2. Inspect every emitted `PROVISIONED` and `READY` reason/message.
3. Compare the public condition schema before and after the test build.

##### Expected Results

- `PROVISIONED.reason` is one of `HostAllocation`, `Provisioning`,
  `NetworkSetup`, or `Provisioned` while provisioning and at completion;
  `READY.reason` is `Ready` at terminal readiness.
- Every emitted message is non-empty where the approved design specifies one and
  belongs to the curated vocabulary; raw internal error text is absent.
- Existing condition fields and enum values remain the API surface; no new proto
  or CRD field is present.

## Gaps

### Requirement Coverage Gaps

All eight approved-design traceability IDs have test cases. The PRD itself does
not provide explicit `FR-*`/`NFR-*` headings, so the exact mapping from PRD
paragraphs to the design's IDs remains a source-document ambiguity. This plan
preserves the IDs already used by the approved design rather than silently
renumbering or inventing them.

`NFR-2` is referenced by `IC-4` in the approved design but is not separately
spelled out in the published PRD. `TC-NFR2-01` therefore tests only the explicit
IC-4 contract—existing condition fields, consistent coarse-stage presentation,
and read-only behavior—and does not assert an unapproved visual or accessibility
standard.

### Interface Change Coverage Gaps

All six interface changes are exercised:

- `IC-1`: `TC-FR1-01`, `TC-FR2-03`, `TC-NFR3-02`
- `IC-2`: `TC-FR1-01`, `TC-FR1-03`, `TC-FR2-01`, `TC-FR2-03`, `TC-FR5-01`
- `IC-3`: `TC-NFR1-01`, `TC-NFR1-02`
- `IC-4`: `TC-FR1-02`, `TC-FR1-03`, `TC-FR3-01`, `TC-FR3-02`, `TC-FR5-02`, `TC-NFR2-01`
- `IC-5`: `TC-FR5-01`, `TC-FR5-02`
- `IC-6`: `TC-FR2-01`, `TC-FR2-02`, `TC-NFR3-01`

### Source-Behavior Constraints

- The current operator uses generic `TemplateFailed`, `InvalidSelector`, and
  power-sync reasons and may carry provider/job/parser text. The approved IC-5
  table uses phase-specific reasons and exact messages. The tests above assert
  the approved classified boundary; they do not treat current raw reasons or
  messages as expected behavior. The implementation must resolve the mapping
  before the failure-path cases can run end-to-end.
- The current fulfillment projection can mark `READY` true for a stopped
  instance, while the approved design defines Ready as powered-on provisioning
  readiness. No test in this plan assigns an expected result to the stopped
  day-2 power path; the implementation audit called out by the design must
  settle that boundary without changing unrelated restart behavior.
- The design says the operator exhaustiveness test covers every `HostCondition*`
  constant, but the current source has both provisioning and deletion/offboarding
  conditions. `TC-FR2-02` and `TC-NFR3-01` require each to be explicitly mapped
  or intentionally unsurfaced; they do not assume that deletion conditions are
  provisioning stages.
- The design's persistence assertion requires fulfillment service, database, hub
  Kubernetes API, and finalizer/archive behavior together. The current unit and
  envtest boundaries do not prove this full path; `TC-FR4-01` and `TC-FR4-02`
  remain planned integration cases until that harness is identified and
  available.

### Execution Readiness Gaps

- Operator derivation, fulfillment projection, feedback predicate, and UI
  component cases have identifiable unit-test locations and commands from the
  component guidance.
- Signal freshness and persistence require a running fulfillment service,
  database, hub API, and feedback controller; envtest alone is insufficient.
- BMaaS E2E stage progression requires the deployed provider-backed environment
  described by `tests/e2e/` and is not runnable from this planning-only phase.
- The concrete UI layout and accessibility affordances remain an approved design
  open question. Automated UI state/polling cases are actionable; visual
  comparison remains manual until the UI-focused design resolves those details.

## Summary

| Metric | Count |
|--------|-------|
| Total test cases | 17 |
| Critical | 6 |
| High | 7 |
| Medium | 4 |
| Low | 0 |
| Automated | 16 |
| Manual | 1 |
| Requirements with test cases | 8 / 8 |
| Interface changes with test cases | 6 / 6 |
