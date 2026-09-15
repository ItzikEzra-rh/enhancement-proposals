# Testplan — OSAC-3459

## Overview

- **Feature:** OSAC-3459 — BMaaS Provisioning Progress and Step Visibility
- **Mode:** Approved-design test-plan-only regeneration
- **Total test cases:** 18
- **Requirements covered:** 8 of 8 approved-design traceability labels
- **Interface changes covered:** 6 of 6 (`IC-1` through `IC-6`)
- **Execution status:** Planned; no tests were executed in this phase.

### Traceability note

The published PRD does not define `FR-*` or `NFR-*` identifiers. The approved
design uses `FR-1` through `FR-5` and `NFR-1` through `NFR-3` in its Interface
Changes matrix, so this plan preserves those labels as **design-only
traceability labels**. They are not presented as canonical PRD identifiers.
The authoritative source anchors are the PRD's In Scope, Out of Scope,
Assumptions, User Stories, and Dependencies sections, together with the
approved design's Interface Changes, Workflow Description, UI, Persistence,
Failure Handling, and Test Plan sections.

## Source-Derived Assertion Checklist

These local assertion IDs were extracted from the approved design before the
cases were written. They supplement, and do not replace, the design-only
requirement and interface labels.

| ID | Source | Observable assertion | Expected-result coverage |
|---|---|---|---|
| A-01 | `design.md` §Proposal, §Workflow Description | The user-facing sequence is Host Allocation → Provisioning → Network Setup → Ready. | TC-FR1-01, TC-FR1-02, TC-FR1-03 |
| A-02 | `design.md` §UI | Steps before the current step are complete, the current step is in progress, and later steps are not started. | TC-FR1-01, TC-FR1-02, TC-FR1-03 |
| A-03 | `design.md` §Proposal, §Reconciler stage derivation | While `PROVISIONED` is false, its reason carries `HostAllocation`, `Provisioning`, or `NetworkSetup` and its message is non-empty and curated. | TC-FR1-01, TC-FR1-02, TC-FR1-03 |
| A-04 | `design.md` §Reconciler stage derivation | The furthest-advanced true condition wins independent of CR condition order. | TC-FR2-01 |
| A-05 | `design.md` §Phase-to-backend-signal mapping | Allocation, provisioning, network, and power conditions map to the specified stage, completion, and ready transitions. | TC-FR2-02 |
| A-06 | `design.md` IC-6 | Every exported `HostCondition*` constant is mapped or explicitly listed as not surfaced. | TC-FR2-04, TC-NFR3-01 |
| A-07 | `design.md` §Workflow Description | A stage with no work, such as no network attachment, is already satisfied and does not leave the UI stuck in Network Setup. | TC-FR2-03 |
| A-08 | `design.md` §Workflow Description | Retrying within a stage leaves the derived stage unchanged until its driving condition reaches a terminal state. | TC-FR2-03 |
| A-09 | `design.md` §Workflow Description | OS installation and configuration inside one AAP job remain one Provisioning stage. | TC-FR2-03 |
| A-10 | `design.md` UX Alignment, §UI | The existing condition transition time remains the current stage's transition marker; no per-phase history or duration is exposed. | TC-FR4-01, TC-FR5-02 |
| A-11 | `design.md` §UI | `PROVISIONED=true` with `READY=false` makes Ready the current step; both true makes all steps complete. | TC-FR1-03 |
| A-12 | `design.md` IC-5 | Each of the seven specified failure classifications maps to its exact fixed message and condition carrier. | TC-FR5-01 |
| A-13 | `design.md` IC-5, §Failure Handling | Raw operator, AAP, Metal3, and provider error text is never emitted in the public message. | TC-FR5-01, TC-FR5-02 |
| A-14 | `design.md` §UI, §Failure Handling | A failed step is marked failed, carries its curated message, and later steps remain not started. | TC-FR5-02 |
| A-15 | `design.md` Non-Goals, §UI | The progress view is read-only and has no retry, re-provision, log, duration, or per-phase history control. | TC-FR5-02, TC-NFR2-01 |
| A-16 | `design.md` IC-3, §Reconciler and freshness | A CR condition reason/message transition uses the existing feedback→`Signal` path and updates the public record within the source's seconds-level promise. | TC-NFR1-01 |
| A-17 | `design.md` §Persistence and retention | Terminal/failure conditions remain served after CR deletion while the active record exists; archived records return 404. | TC-FR4-01, TC-FR4-02 |
| A-18 | `design.md` IC-4, §UI | The detail view refreshes at approximately five seconds while non-terminal. | TC-FR3-01 |
| A-19 | `design.md` IC-4, §UI | Refresh stops at `READY=true` or a provisioning failure condition. | TC-FR3-01 |
| A-20 | `design.md` §API Extensions, §No schema change | No proto, CRD, public status field, or new endpoint is added. | TC-NFR3-02 |
| A-21 | `design.md` §RBAC / Tenancy | Existing authorization, tenant scoping, and owner-reference metadata remain the access boundary; no new RBAC permission is required. | TC-NFR2-01 |
| A-22 | `design.md` §Failure Handling and Recovery | Operator/reconciler interruption preserves last-known status and resumes or falls back to existing full resync without data loss. | TC-NFR1-02 |

## Test Cases

### FR-1 (design-only): Four-step current-state visibility

#### TC-FR1-01: Show Host Allocation and Provisioning intermediate states

| Interface Change | Priority | Automation |
|-----------------|----------|------------|
| IC-1, IC-2, IC-4 | critical | automated |

##### Preconditions

- A bare-metal instance has no true lifecycle milestone condition.
- A second fixture has `Allocated=True` while provisioning remains incomplete.
- The API returns the existing `PROVISIONED` condition and the UI detail page is open.

##### Steps

1. Read the first fixture through the existing bare-metal instance API and render the detail view.
2. Read the second fixture and render the detail view.

##### Expected Results

- For the first fixture, `PROVISIONED.status` is false, `PROVISIONED.reason` is `HostAllocation`, the message is non-empty, Host Allocation is in progress, and Provisioning, Network Setup, and Ready are not started.
- For the second fixture, `PROVISIONED.status` is false, `PROVISIONED.reason` is `Provisioning`, Host Allocation is complete, Provisioning is in progress, and Network Setup and Ready are not started.

#### TC-FR1-02: Show Network Setup while dependent network work remains

| Interface Change | Priority | Automation |
|-----------------|----------|------------|
| IC-1, IC-2, IC-4 | critical | automated |

##### Preconditions

- `Allocated=True` and `ProvisionTemplateComplete=True`.
- At least one of `NetworkAttachmentsReady`, `NetworkHandoffComplete`, or `IPDiscoveryComplete` is not complete.

##### Steps

1. Reconcile the fixture and read the public instance status.
2. Render the detail view from that status.

##### Expected Results

- `PROVISIONED.status` is false, its reason is `NetworkSetup`, and its message is non-empty.
- Host Allocation and Provisioning are complete, Network Setup is in progress, and Ready is not started.
- The public condition exposes the current stage rather than a raw provider or job message.

#### TC-FR1-03: Show Ready as the final in-progress step and then complete all steps

| Interface Change | Priority | Automation |
|-----------------|----------|------------|
| IC-1, IC-2, IC-4 | critical | automated |

##### Preconditions

- Fixture A has all provisioning/network conditions true, but the powered-on ready condition is not yet true.
- Fixture B has the same conditions plus the ready condition true.

##### Steps

1. Render Fixture A through the existing instance detail view.
2. Render Fixture B through the same view.

##### Expected Results

- Fixture A has `PROVISIONED=True` with reason `Provisioned` and message `Infrastructure has been allocated and provisioned.`; the first three steps are complete and Ready is the current in-progress step.
- Fixture B has `PROVISIONED=True` and `READY=True` with reason `Ready` and message `The instance is ready.`; all four steps are complete.

#### TC-FR1-04: Preserve current transition time without adding a phase history

| Interface Change | Priority | Automation |
|-----------------|----------|------------|
| IC-1 | high | automated |

##### Preconditions

- A fixture contains a current-stage condition with a known `lastTransitionTime`.

##### Steps

1. Read the instance status after the stage transition.
2. Inspect the detail view and serialized public condition data.

##### Expected Results

- The current condition exposes the stage transition time from the existing `last_transition_time` field.
- No ordered per-phase history, per-phase duration, or timeline field is returned or rendered.

### FR-2 (design-only): Condition-to-stage derivation

#### TC-FR2-01: Select the furthest stage independent of condition order

| Interface Change | Priority | Automation |
|-----------------|----------|------------|
| IC-2, IC-6 | critical | automated |

##### Preconditions

- Two equivalent condition sets contain the same true lifecycle milestones in different array orders.

##### Steps

1. Call `DeriveProvisioningProgress` with the first condition ordering.
2. Call it with the permuted ordering.

##### Expected Results

- Both calls return the same stage, `provisioned`, `ready`, and failure result.
- The result is the furthest-advanced applicable stage, not the last condition encountered.

#### TC-FR2-02: Map each lifecycle signal to its approved stage or terminal result

| Interface Change | Priority | Automation |
|-----------------|----------|------------|
| IC-2, IC-6 | critical | automated |

##### Preconditions

- Parameterized fixtures cover no milestone, `Allocated`, `ProvisionTemplateComplete`, each network milestone, and `PowerSynced`/available.

##### Steps

1. Pass each fixture to `DeriveProvisioningProgress`.
2. Pass the derived result through `syncStatus`.

##### Expected Results

- No milestone maps to Host Allocation; `Allocated` maps to Provisioning; completed provisioning with incomplete network maps to Network Setup.
- `NetworkAttachmentsReady`, `NetworkHandoffComplete`, and `IPDiscoveryComplete` advance Network Setup in the approved order; all required network conditions make `PROVISIONED=True` with reason `Provisioned`.
- The powered-on ready signal makes `READY=True` with reason `Ready`.

#### TC-FR2-03: Advance no-work stages and preserve collapsed/retried behavior

| Interface Change | Priority | Automation |
|-----------------|----------|------------|
| IC-2, IC-6 | high | automated |

##### Preconditions

- A no-network-work fixture, an in-stage retry fixture, and a fixture representing the single opaque OS/configuration job are available.

##### Steps

1. Derive progress for the no-network-work fixture.
2. Derive progress during a retry before its driving condition is terminal.
3. Derive progress for the combined OS installation/configuration job.

##### Expected Results

- No-network work is treated as already satisfied; the result advances beyond Network Setup and the UI does not remain stuck on that step.
- A retry leaves the current stage unchanged until the driving condition reaches its terminal state; retry detail is not surfaced.
- OS installation and configuration are represented as one Provisioning stage, not separate user-visible phases.

#### TC-FR2-04: Reject an unclassified exported operator condition

| Interface Change | Priority | Automation |
|-----------------|----------|------------|
| IC-6 | high | automated |

##### Preconditions

- The operator package exposes its complete `HostCondition*` constant set.
- The proposed co-located exhaustiveness test is present.

##### Steps

1. Run the exhaustiveness test against the exported condition constants.
2. Add a temporary unclassified constant in the test fixture or equivalent test-only enumeration.

##### Expected Results

- Every existing condition is mapped to a stage, terminal, failure, or explicit not-surfaced classification.
- The test fails when a condition is unclassified, identifying the missing mapping instead of allowing an empty or incorrect public reason.

### FR-3 (design-only): Active refresh

#### TC-FR3-01: Refresh while active and stop at terminal state

| Interface Change | Priority | Automation |
|-----------------|----------|------------|
| IC-4 | high | automated |

##### Preconditions

- The detail view uses a controllable API transport and fake timers.
- One fixture is non-terminal; another becomes `READY=True`; a third becomes a provisioning failure.

##### Steps

1. Mount the detail view with the non-terminal fixture and advance the clock across one approximately five-second refresh interval.
2. Change the transport response to the terminal success fixture and advance the clock again.
3. Repeat with the failure fixture.

##### Expected Results

- The non-terminal view issues a single-instance refresh at the page-scoped approximately five-second interval and displays the new stage.
- After `READY=True`, no further periodic refresh is scheduled.
- After a provisioning failure condition, no further periodic refresh is scheduled.

### FR-4 (design-only): Terminal persistence and retention

#### TC-FR4-01: Serve terminal success after CR deletion while the record is active

| Interface Change | Priority | Automation |
|-----------------|----------|------------|
| — | critical | automated |

##### Preconditions

- An instance has persisted `PROVISIONED=True` and `READY=True` status.
- The active fulfillment record exists and the Kubernetes CR is deleted.

##### Steps

1. Read the instance through the public API after CR deletion.
2. Inspect the returned conditions and transition time.

##### Expected Results

- The API continues to return the active instance with all four steps complete, `PROVISIONED.reason=Provisioned`, and `READY.reason=Ready`.
- The terminal condition messages and current transition time remain available; no new archive-read endpoint is used.

#### TC-FR4-02: Preserve failure until archive, then return not-found

| Interface Change | Priority | Automation |
|-----------------|----------|------------|
| — | critical | automated |

##### Preconditions

- An instance has a persisted failure condition and an active fulfillment record.

##### Steps

1. Delete the CR and read the active instance.
2. Archive/release the fulfillment record through the existing lifecycle.
3. Read the same public instance URL again.

##### Expected Results

- Before archive, the API returns the failed step and its curated message.
- After archive, the public GET returns HTTP 404; no public archive-read path exposes the record.

### FR-5 (design-only): Failure identification and curated messages

#### TC-FR5-01: Map every approved failure reason to its fixed public message

| Interface Change | Priority | Automation |
|-----------------|----------|------------|
| IC-2, IC-5 | critical | automated |

##### Preconditions

- Parameterized fixtures represent all seven approved failure classifications.

##### Steps

1. Reconcile each failure fixture.
2. Read the public condition carrier and message.

##### Expected Results

- `NoMatchingHosts` on `PROVISIONED` maps to Host Allocation and `No bare metal host matched the requested profile.`
- `HostAllocationFailed` on `PROVISIONED` maps to Host Allocation and `Host allocation failed.`
- `ProvisionJobFailed` on `PROVISIONED` maps to Provisioning and `OS installation and configuration did not complete; the provisioning job failed.`
- `NetworkAttachmentFailed` on `PROVISIONED` maps to Network Setup and `Network attachment did not complete.`
- `NetworkHandoffFailed` on `PROVISIONED` maps to Network Setup and `Network handoff (reboot) did not complete.`
- `IPDiscoveryFailed` on `PROVISIONED` maps to Network Setup and `IP address discovery did not complete.`
- `ReadyTimeout` on `READY` maps to Ready and `The instance did not reach its powered-on ready state.`
- Every mapped public message equals the fixed string above; no raw provider, operator, AAP, Metal3, or internal error text appears.

#### TC-FR5-02: Render a failed step without exposing recovery controls or history

| Interface Change | Priority | Automation |
|-----------------|----------|------------|
| IC-4, IC-5 | high | automated |

##### Preconditions

- The API returns a failed provisioning condition with a fixed reason/message.

##### Steps

1. Render the instance detail view.
2. Inspect the failed step and available controls.

##### Expected Results

- The failing step is marked failed and displays the fixed human-readable message.
- Later steps are not started.
- The view contains no retry, re-provision, log, duration, or per-phase history control.

### NFR-1 (design-only): Freshness and degraded-path behavior

#### TC-NFR1-01: Propagate a reason/message transition through Signal within the published bound

| Interface Change | Priority | Automation |
|-----------------|----------|------------|
| IC-3 | critical | automated |

##### Preconditions

- A deployed Kind/component-integration environment runs the osac-operator feedback controller, fulfillment service, database, and the existing private Signal endpoint.
- The test can record the CR status-update timestamp and poll the public API without relying on the UI refresh loop or periodic full resync.

##### Steps

1. Change only a `BareMetalInstance` condition reason/message so the CR status changes.
2. Record the Signal receipt or equivalent feedback-controller event.
3. Poll the public instance API from the recorded CR transition until the new reason/message is visible.

##### Expected Results

- The condition reason/message transition triggers the existing feedback→`Signal` path.
- The public API exposes the new reason/message in less than ten seconds, matching the PRD’s single-digit-seconds freshness promise; the measurement is isolated from the fallback full resync and UI polling.

#### TC-NFR1-02: Preserve last-known status across component interruption

| Interface Change | Priority | Automation |
|-----------------|----------|------------|
| IC-3 | high | manual |

##### Preconditions

- A deployed environment has a persisted in-progress or terminal status.

##### Steps

1. Interrupt the operator, fulfillment reconciler, or feedback path at the point described by the selected failure scenario.
2. Read the public API while the component is unavailable.
3. Restore the component and observe the next reconciliation/resync.

##### Expected Results

- While the producer is unavailable, the API serves the last persisted conditions and does not lose the status.
- After restoration, the existing full-resync or feedback path converges the API to the current CR conditions; the test records the observed freshness degradation if Signal was interrupted.

### NFR-2 (design-only): Read-only, tenant-scoped presentation

#### TC-NFR2-01: Preserve existing authorization and expose an accessible read-only view

| Interface Change | Priority | Automation |
|-----------------|----------|------------|
| IC-4 | high | automated |

##### Preconditions

- Authorized Tenant User, Tenant Admin, and Cloud Provider Admin fixtures can access the same instance through the existing authorization path.
- An unrelated tenant lacks access to that instance.

##### Steps

1. Render the detail view for each authorized persona using the same returned condition data.
2. Query the view by accessible roles/names and inspect available actions.
3. Attempt the unrelated tenant’s existing read path.

##### Expected Results

- Each authorized persona sees the same four-step read-only status and curated message; the exact visual layout remains a UI-design question.
- The progress controls expose status information but no mutation action.
- The unrelated tenant cannot read the instance, and existing tenant/owner-reference authorization remains the boundary.

### NFR-3 (design-only): Stable existing contract and exhaustive source mapping

#### TC-NFR3-01: Keep the condition contract exhaustive as constants evolve

| Interface Change | Priority | Automation |
|-----------------|----------|------------|
| IC-1, IC-6 | high | automated |

##### Preconditions

- The operator exhaustiveness test and the existing proto condition model are available.

##### Steps

1. Run the operator exhaustiveness test.
2. Compare the mapped condition set with the exported `HostCondition*` constants.

##### Expected Results

- All condition constants are classified or explicitly excluded from the surfaced progress model.
- The test fails with the missing constant when the set and mapping diverge.

#### TC-NFR3-02: Verify that the design adds no schema or endpoint surface

| Interface Change | Priority | Automation |
|-----------------|----------|------------|
| IC-1 | high | manual |

##### Preconditions

- The implementation change is available for review.

##### Steps

1. Inspect proto sources/generated descriptors, CRD definitions, public API service definitions, and RBAC manifests.
2. Compare the changed files with the approved design’s existing-condition contract.

##### Expected Results

- No new proto message, enum, field, CRD field, endpoint, webhook, or RBAC permission is present.
- Only the existing condition reason/message/transition-time fields and the approved internal Go projection surface are changed.

## Execution Evidence

The following matrix separates planned behavioral coverage from a verified
execution path. Commands marked **existing** are documented in the checked-out
component instructions or Makefiles. Proposed locations and harness changes
remain planned work and are not represented as runnable coverage.

| Evidence row | Behavior and cases | Tier and boundary | Test location | Execution | Dependencies | Readiness / gap |
|---|---|---|---|---|---|---|
| E-1 | Pure stage, failure, retry, no-work, order, and exhaustiveness behavior; TC-FR2-01 through TC-FR2-04, TC-FR5-01, TC-NFR3-01 | Unit; operator condition-to-stage boundary | Proposed `bare-metal-fulfillment-operator/api/v1alpha1/baremetalinstance_progress_test.go` | **Existing:** `make test` from `bare-metal-fulfillment-operator/`. **Proposed focused:** `go test ./api/v1alpha1 -run 'TestDeriveProvisioningProgress'` | `metav1.Condition` fixtures only; no API server, provider, Metal3, hardware, or AAP | Planned but not execution-ready until the function and test file exist. `make test` also runs generated/manifests and envtest setup. |
| E-2 | Public condition presentation, exact curated messages, transition time, and `PROVISIONED`/`READY` terminal semantics; TC-FR1-01 through TC-FR1-04, TC-FR5-01 | Unit; fulfillment reconciler projection boundary | Proposed additions to `fulfillment-service/internal/controllers/baremetalinstance/baremetalinstance_reconciler_function_test.go` | **Existing:** `ginkgo run -r internal` from `fulfillment-service/` | Reconciler fixtures and fakes; no deployed PostgreSQL, operator, or provider | Planned but not execution-ready until the projection implementation and focused cases exist. |
| E-3 | Existing feedback predicate and Signal trigger for CR reason/message changes; part of TC-NFR1-01 | Unit for trigger; not sufficient for full cross-component persistence | Existing `osac-operator/internal/controller/baremetalinstance_feedback_controller_test.go` plus proposed boundary test | **Existing:** `make test` from `osac-operator/` for controller tests | Envtest supplies Kubernetes API/etcd; fulfillment service and database are not provided by osac-operator envtest | The caller-side trigger is testable; no checked-out qualifying suite was identified for the full CR→Signal→fulfillment DB boundary. Full coverage is a gap, not claimed from envtest. |
| E-4 | UI step states, failure rendering, read-only controls, and approximately five-second terminal refresh; TC-FR1-01 through TC-FR1-03, TC-FR3-01, TC-FR5-02, TC-NFR2-01 | Unit; UI component/query boundary | Proposed co-located `osac-ui/libs/ui-components/src/components/BareMetalInstance/BareMetalDetails.test.tsx` and API hook test | **Existing:** `pnpm test`, `pnpm run typecheck`, and `pnpm lint` from `osac-ui/` | Vitest/jsdom and `createMockConnectTransport`; no browser, cluster, or real API | Planned but not execution-ready until tests are added. No persisted browser E2E suite exists; visual/accessibility layout remains an open design item. |
| E-5 | Terminal/failure persistence after CR deletion and archive retention; TC-FR4-01 and TC-FR4-02 | E2E; deployed fulfillment/operator/database/CR boundary | Proposed extension to `tests/e2e/bmaas/sanity/test_baremetal_instance_lifecycle.py` | **Existing collection:** `uv run pytest --collect-only tests/e2e/bmaas/`. **Proposed narrow run:** `uv run pytest tests/e2e/bmaas/sanity/test_baremetal_instance_lifecycle.py -k 'provisioning_progress or archive'` from repository root | Deployed OSAC stack, fulfillment API/database, Kubernetes CRs, and configured BMaaS backend; provider/hardware availability remains environment-dependent | Planned but not execution-ready: no existing case for this exact retention contract was identified, and a deployed environment is required. |
| E-6 | Cross-component freshness bound and interruption fallback; TC-NFR1-01 and TC-NFR1-02 | Component integration/contract; CR status→feedback→DB/API boundary | Proposed harness; no dedicated existing location identified | **Proposed:** use the installer-owned Kind fulfillment environment, then run a targeted test harness that records CR transition, Signal, and API visibility. No runnable command is claimed until that harness is defined. | Real deployed osac-operator feedback, fulfillment service, database, Kubernetes API, and API client; no real hardware required for status propagation | Blocked by missing qualifying harness and unresolved ownership/follow-up. A fake Signal endpoint would test only the caller, not persistence/reconciliation. |
| E-7 | No schema/endpoint/RBAC expansion and tenant scoping; TC-NFR2-01 and TC-NFR3-02 | Manual/static review; API and authorization boundary | Existing proto, CRD, RBAC, and public-server sources | **Existing static checks:** `make -C proto lint` and component lint/typecheck commands where applicable; source review remains required | No deployed provider; authorization review must use existing tenant fixtures or a deployed API | Partially ready as a review activity. It does not replace behavioral tenant authorization or deployed wiring coverage. |

## Gaps

### Requirement Coverage Gaps

All eight approved-design traceability labels have test cases. The published
PRD does not provide a canonical FR/NFR-to-section mapping, so the requirement
labels and their descriptions remain a traceability gap for downstream review.
This plan does not invent a PRD mapping.

### Interface Change Coverage Gaps

All six interface changes (`IC-1` through `IC-6`) are exercised by at least one
case. Interface coverage does not mean execution readiness: IC-3's full
cross-component boundary lacks a verified harness, and IC-4's visual and
accessibility details remain unresolved in the approved design.

### Execution and Contract Gaps

- The approved design requires no-work network stages to advance, but the
  current operator orchestration path can return before writing the helper's
  skipped conditions. TC-FR2-03 preserves the approved assertion; the
  implementation path must be resolved before execution can be considered
  ready.
- The approved design names `READY` as powered-on readiness, while current
  fulfillment behavior derives it from coarse `RUNNING`/`STOPPED` state. The
  stopped-state contract is unresolved and affects TC-FR1-03 and TC-FR4-01.
- The approved design expects the public transition time to represent the
  current stage, but the existing fulfillment projection does not visibly copy
  the CR transition time. TC-FR1-04 remains blocked until that contract is
  confirmed.
- No test execution was performed; every case is planned evidence, not a
  result.

## Summary

| Metric | Count |
|--------|-------|
| Total test cases | 18 |
| Critical | 9 |
| High | 9 |
| Medium | 0 |
| Low | 0 |
| Automated | 16 |
| Manual | 2 |
| Requirements with test cases | 8 / 8 design-only labels |
| Interface changes with test cases | 6 / 6 |

## Planning Check

- **Result:** FLAG after one correction round and a full recheck.
- **Prepare:** Added the source-derived assertion checklist before cases,
  mapped each behavior to an owning component/boundary, and recorded commands,
  dependencies, and readiness separately.
- **Correction:** Split the intermediate stage cases so Host Allocation,
  Provisioning, Network Setup, `PROVISIONED=true`/`READY=false`, and terminal
  Ready assertions are explicit; added the seven exact failure mappings,
  exhaustive condition assertions, archive boundary, and no-work/retry/
  collapsed-job behaviors. Corrected the freshness case to measure CR status
  change → Signal → public API rather than UI polling or fallback resync.
- **Recheck:** All 18 case IDs are unique and grouped under matching labels;
  all six ICs are referenced; all assertion checklist IDs have case mappings;
  expected results use concrete values/messages/states; timing, proposed
  harnesses, and unavailable boundaries are explicitly marked.
- **Remaining gate:** The plan is behaviorally complete but not execution-ready
  for the full Signal/DB boundary, UI visual/accessibility verification, or the
  unresolved no-work, stopped-READY, and transition-time contracts.

---

## Provenance

Authored: draft @ design 0.11.1 - f1d6a4b, workspace pilot/OSAC-5320-iteration-5 @ 554e5a07a (dirty)

<!-- ai-workflow-provenance:{"schema_version":1,"provenance_kind":"session","workflow":"design","workflow_version":"0.11.1","ai_workflows":"f1d6a4b","source_repo":"554e5a07a (dirty)","source_repo_branch":"pilot/OSAC-5320-iteration-5","commits_behind_main":0,"commits_ahead_main":0,"main_ref":"main","phases":["draft"],"authoring_modes":["skill"],"context_changed":false,"origin_untracked":false} -->
