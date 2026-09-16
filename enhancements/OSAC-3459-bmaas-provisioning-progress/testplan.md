# Testplan — OSAC-3459

## Overview

- **Feature:** OSAC-3459 — BMaaS Provisioning Progress and Step Visibility
- **Mode:** Test-plan-only regeneration from the approved design
- **Authoritative sources:** approved PRD and approved design recorded in `01-context.md`; the standalone `testplan.md` is not an input to this run.
- **Total test cases:** 19
- **Requirements covered:** 8 of 8 design-defined requirement labels
- **Interface changes covered:** 6 of 6
- **Execution status:** planned and source-checked; no tests, lint, type checks, collection, generation, or implementation commands were run.

The approved PRD expresses six in-scope behaviors and does not assign `FR-*` or
`NFR-*` labels. The approved design supplies `FR-1` through `FR-5` and
`NFR-1` through `NFR-3`; those labels are retained below as design-defined
labels with explicit PRD mapping. No new requirement wording is introduced.

## Requirement and interface mapping

| Design label | Approved PRD source mapping | Approved design/interface mapping |
|---|---|---|
| FR-1 | In Scope bullet 1 and the current-phase user story | IC-1, IC-2, IC-4 |
| FR-2 | In Scope bullet 2 and Assumptions bullet 1 | IC-2, IC-6 |
| FR-3 | In Scope bullet 3 and the auto-refresh user story | IC-4 |
| FR-4 | In Scope bullet 4 and the terminal-outcome user story | IC-1, IC-4 |
| FR-5 | In Scope bullets 5–6 | IC-2, IC-4, IC-5 |
| NFR-1 | In Scope bullet 3’s single-digit-second freshness promise | IC-3 |
| NFR-2 | Design IC-4’s UI consistency/read-only behavior; the PRD’s current-phase and consistency bullets | IC-4 |
| NFR-3 | Design constraints for the existing condition contract and exhaustive derivation | IC-1, IC-6 |

## Assertion checklist

This checklist was extracted independently from the PRD and approved design
before reviewing the generated cases. The audit later in this document links
each assertion to a concrete Expected Results bullet.

| ID | Source | Assertion to preserve | Case / Expected Results reference |
|---|---|---|---|
| PRD-01 | PRD In Scope 1 | Show current phase, state, and human-readable message; earlier phases are complete and later phases pending. | TC-FR1-01 ER1–ER5; TC-FR1-02 ER1–ER4 |
| PRD-02 | PRD In Scope 1, Clarify R2.Q3 | A no-work phase is complete, not stuck pending. | TC-FR1-03 ER1 |
| PRD-03 | PRD In Scope 2, Clarify R3.Q3 | User-visible phases are exactly Host Allocation, Provisioning, Network Setup, and Ready; internal hardware/OS/configuration/verification work is folded into Provisioning. | TC-FR2-01 ER1–ER3 |
| PRD-04 | PRD In Scope 3, Clarify R1.Q2 | Active detail view refreshes without user action on a bounded approximately five-second interval. | TC-FR3-01 ER1–ER3 |
| PRD-05 | PRD In Scope 3 | Polling stops after successful readiness or provisioning failure. | TC-FR3-02 ER1–ER2 |
| PRD-06 | PRD In Scope 3 | Backend progress is visible without page reload within single-digit seconds. | TC-FR3-01 ER4 |
| PRD-07 | PRD In Scope 4 | Success shows all phases succeeded; failure identifies the failed phase and message. | TC-FR4-01 ER1; TC-FR4-02 ER1; TC-FR5-01 ER1–ER7 |
| PRD-08 | PRD In Scope 4, Assumptions 2 | Terminal/failure state remains viewable for the instance-record lifetime until archival. | TC-FR4-01 ER2–ER3; TC-FR4-02 ER2–ER3 |
| PRD-09 | PRD In Scope 4, Out of Scope | No durable ordered phase history or per-phase durations is exposed. | TC-FR4-01 ER4 |
| PRD-10 | PRD In Scope 5 | Progress follows the existing coarse-condition reason/message pattern. | TC-FR5-02 ER1–ER2 |
| PRD-11 | PRD In Scope 6 | Failure text identifies phase and condition in human-readable terms. | TC-FR5-01 ER1–ER7 |
| PRD-12 | PRD In Scope 6 | Raw internal errors and implementation details are not surfaced. | TC-FR5-02 ER3 |
| PRD-13 | PRD Out of Scope / In Scope 6 | The progress view is read-only: no retry, re-provision, remediation, logs, or cross-tenant progress list. | TC-FR5-03 ER1–ER3 |
| PRD-14 | PRD Out of Scope | Deprovisioning progress and day-two configuration progress are not added. | TC-FR5-03 ER4–ER5 |
| DES-01 | Design §4.1, §4.3 | No proto/CRD schema or generated type change is required; existing condition fields carry the projection. | TC-NFR3-01 ER1–ER3 |
| DES-02 | Design Proposal / IC-2 | `DeriveProvisioningProgress` is a pure operator-owned condition-to-stage contract used by `syncStatus`. | TC-FR1-01 ER1–ER5; TC-NFR3-02 ER1, ER3 |
| DES-03 | Design IC-2 / IC-6 | The furthest-advanced stage wins independently of condition order. | TC-FR2-02 ER1–ER2 |
| DES-04 | Design phase mapping table | Host Allocation precedes Allocated; Provisioning follows Allocated; Network Setup follows provisioning; network completion makes PROVISIONED true; powered-on readiness makes READY true. | TC-FR1-01 ER1–ER5 |
| DES-05 | Design workflow/UI rules | PROVISIONED true with READY not true makes Ready current; both true makes all four complete. | TC-FR2-03 ER1–ER2 |
| DES-06 | Design IC-5 | Seven failure reasons map to the seven exact curated messages and their specified carriers/steps. | TC-FR5-01 ER1–ER7 |
| DES-07 | Design IC-6 | Every exported `HostCondition*` constant is mapped or explicitly listed as not surfaced. | TC-NFR3-02 ER1–ER2 |
| DES-08 | Design behavior notes | No-work advances; retries remain on the same stage; opaque OS/configuration work remains Provisioning. | TC-FR1-03 ER1–ER3 |
| DES-09 | Design IC-3 / freshness section | CR status reason/message changes use the existing feedback→Signal path to resync fulfillment. | TC-NFR1-01 ER1–ER4 |
| DES-10 | Design persistence section | Last terminal/failure conditions remain served after CR deletion until archival; archived records return 404. | TC-FR4-01 ER2–ER3; TC-FR4-02 ER2–ER3 |
| DES-11 | Design UI section | UI derives four step states from PROVISIONED reason/message and READY, including failure message and terminal transitions. | TC-FR1-02 ER1–ER4; TC-FR2-03 ER1–ER2 |
| DES-12 | Design UI section | UI polls only while non-terminal and stops at READY true or provisioning failure. | TC-FR3-01 ER1–ER4; TC-FR3-02 ER1–ER2 |
| DES-13 | Design Failure Handling | Operator, reconciler, and feedback-path outages preserve last-known data and define restart/fallback behavior. | TC-NFR1-02 ER1–ER3 |
| DES-14 | Design Security / RBAC | Existing tenant authorization and tenant/owner metadata remain the visibility boundary; no new cross-tenant path is introduced. | TC-FR5-03 ER3 |

## Test cases

### FR-1: Current phase, state, and message are projected and rendered

#### TC-FR1-01: Derive and project each active and terminal provisioning stage

| Interface Change | Priority | Automation |
|---|---|---|
| IC-1, IC-2 | critical | automated |

##### Preconditions

- Use operator condition fixtures for no milestone, `Allocated=True`, `ProvisionTemplateComplete=True`, all network milestones true, and powered-on readiness.
- Run the operator derivation and fulfillment `syncStatus` projection in their owning package tests with external providers replaced by fixtures.

##### Steps

1. Apply each fixture to `DeriveProvisioningProgress` and pass the result through the status projection.
2. Inspect the API `PROVISIONED` and `READY` conditions after each milestone.

##### Expected Results

- **ER1:** Before `Allocated=True`, `PROVISIONED` is not true and its reason is exactly `HostAllocation`; its message is non-empty and describes the current stage.
- **ER2:** After `Allocated=True` and before `ProvisionTemplateComplete=True`, `PROVISIONED` is not true and its reason is exactly `Provisioning`; its message is non-empty and describes the current stage.
- **ER3:** After `ProvisionTemplateComplete=True` and before all network milestones are true, `PROVISIONED` is not true and its reason is exactly `NetworkSetup`; its message is non-empty and describes the current stage.
- **ER4:** After the required network milestones are true, `PROVISIONED` is true with reason exactly `Provisioned` and message exactly `Infrastructure has been allocated and provisioned.`.
- **ER5:** When the instance reaches the powered-on ready state, `READY` is true with reason exactly `Ready` and message exactly `The instance is ready.`.

#### TC-FR1-02: Render pending, running, succeeded, and failed step states

| Interface Change | Priority | Automation |
|---|---|---|
| IC-4 | critical | automated |

##### Preconditions

- Render the proposed detail progress component with API fixtures for an active stage, a completed stage sequence, and each IC-5 failure carrier.

##### Steps

1. Load the detail view for each fixture without invoking a mutating action.
2. Inspect the four named steps and the driving condition message.

##### Expected Results

- **ER1:** The view names exactly `Host Allocation`, `Provisioning`, `Network Setup`, and `Ready`.
- **ER2:** For an active stage, earlier steps are shown as complete, the current step is shown as in progress, later steps are shown as not yet started, and the current condition message is visible.
- **ER3:** For a failed fixture, the step named by the failure carrier is shown as failed and its curated message is visible.
- **ER4:** For a completed fixture, all four named steps are shown as succeeded.

#### TC-FR1-03: Advance no-work, retry, and opaque-job fixtures

| Interface Change | Priority | Automation |
|---|---|---|
| IC-2 | high | automated |

##### Preconditions

- Prepare fixtures for an instance with no network attachment, a retrying provisioning job, and the combined OS/configuration job.

##### Steps

1. Derive status for each fixture.
2. Render the resulting API conditions in the UI fixture.

##### Expected Results

- **ER1:** A network stage with no work is represented as complete and the view does not leave `Network Setup` pending.
- **ER2:** A retry within one stage leaves the same `PROVISIONED.reason` stage value in place and does not expose retry internals.
- **ER3:** Hardware preparation, OS deployment, and configuration work inside the opaque provisioning job produce the single `Provisioning` step rather than additional user-visible steps.

### FR-2: Fixed four-phase vocabulary and ordered derivation

#### TC-FR2-01: Expose only the approved four phases

| Interface Change | Priority | Automation |
|---|---|---|
| IC-4 | high | automated |

##### Preconditions

- Render an active and a terminal instance detail view using the existing `BareMetalInstanceStatus.conditions` fields.

##### Steps

1. Inspect the progress view and the condition data used to derive it.
2. Search the progress view output for phase labels and per-phase duration/history fields.

##### Expected Results

- **ER1:** The only progress labels are `Host Allocation`, `Provisioning`, `Network Setup`, and `Ready`.
- **ER2:** The UI does not show separate Hardware Preparation, OS Deployment, Configuration, or Verification steps.
- **ER3:** The progress view has no ordered history or per-phase duration fields.

#### TC-FR2-02: Select the furthest stage independently of condition order

| Interface Change | Priority | Automation |
|---|---|---|
| IC-2, IC-6 | critical | automated |

##### Preconditions

- Build two condition arrays with the same true milestones in different orders, including an array with an earlier and later milestone both true.

##### Steps

1. Pass both arrays to `DeriveProvisioningProgress`.
2. Compare the returned stage and terminal flags.

##### Expected Results

- **ER1:** Both arrays return the same stage, completion, readiness, and failure classification.
- **ER2:** When multiple milestones are true, the returned stage is the furthest stage in the approved order rather than the last condition in the input array.

#### TC-FR2-03: Handle the provisioning-complete/ready boundary

| Interface Change | Priority | Automation |
|---|---|---|
| IC-1, IC-4 | critical | automated |

##### Preconditions

- Prepare one API fixture with `PROVISIONED=True` and `READY` not true, and one with both conditions true.

##### Steps

1. Render each fixture in the detail view.
2. Inspect step states and the polling terminal predicate.

##### Expected Results

- **ER1:** With `PROVISIONED=True` and `READY` not true, Host Allocation, Provisioning, and Network Setup are complete and Ready is the current in-progress step.
- **ER2:** With both `PROVISIONED=True` and `READY=True`, all four steps are complete and the instance is terminal.

### FR-3: Bounded refresh and terminal polling behavior

#### TC-FR3-01: Refresh active progress without a page reload

| Interface Change | Priority | Automation |
|---|---|---|
| IC-4 | critical | automated |

##### Preconditions

- Render the detail view with a non-terminal API response and a controllable query timer.
- For the cross-component measurement, use a deployed CR/API path where the CR transition timestamp and user-visible API response can be recorded separately.

##### Steps

1. Leave the detail page open without invoking browser reload.
2. Advance the backend condition and record the CR status transition time.
3. Observe query requests and the time when the new stage is visible in the detail view.

##### Expected Results

- **ER1:** The detail view issues refreshes on its dedicated approximately five-second interval while the instance is non-terminal.
- **ER2:** The new stage becomes visible without a user-triggered page reload.
- **ER3:** The UI request path observes the existing `GET /api/fulfillment/v1/baremetal_instances/{id}` response rather than a new progress endpoint.
- **ER4:** From the CR status transition to the user-visible detail view update, the measured interval is less than 10 seconds; the measurement excludes a page reload and isolates the existing periodic-resync fallback.

#### TC-FR3-02: Stop refreshes at terminal success and failure

| Interface Change | Priority | Automation |
|---|---|---|
| IC-4 | high | automated |

##### Preconditions

- Render the detail view with a non-terminal response, then change the response to `READY=True` in one run and to a provisioning failure in another.

##### Steps

1. Allow one refresh to observe the terminal success or failure response.
2. Advance the query timer beyond the next nominal interval and count additional requests.

##### Expected Results

- **ER1:** After `READY=True`, the detail view makes no further automatic progress refresh requests.
- **ER2:** After a provisioning failure, the detail view makes no further automatic progress refresh requests.

### FR-4: Terminal and failure persistence

#### TC-FR4-01: Preserve successful terminal state through CR deletion and archive boundary

| Interface Change | Priority | Automation |
|---|---|---|
| IC-1, IC-4 | critical | automated |

##### Preconditions

- Use the fulfillment persistence path and a deployed hub CR with an instance record; the exact archival fixture is an execution gap recorded below.

##### Steps

1. Drive the instance to `PROVISIONED=True` and `READY=True`.
2. Delete the hub CR while retaining the fulfillment record.
3. Read the public instance detail, then release/archive the fulfillment record and read it again.

##### Expected Results

- **ER1:** Before CR deletion, the detail view shows all four phases succeeded and the API returns the terminal `PROVISIONED` and `READY` conditions.
- **ER2:** After CR deletion and before archival, the public GET returns the same terminal conditions and all four succeeded steps.
- **ER3:** After archival, the public GET returns HTTP 404 for the released instance.
- **ER4:** The response contains the current terminal projection only; it does not expose an ordered phase history or per-phase duration values.

#### TC-FR4-02: Preserve failure state through CR deletion and archive boundary

| Interface Change | Priority | Automation |
|---|---|---|
| IC-1, IC-4, IC-5 | critical | automated |

##### Preconditions

- Use a deployed fulfillment instance whose hub CR reaches one IC-5 failure, with the archive operation available in the test environment.

##### Steps

1. Drive the instance to the selected failure condition.
2. Delete the hub CR while retaining the fulfillment record.
3. Read the public detail before and after record archival.

##### Expected Results

- **ER1:** Before CR deletion, the failed step and its exact IC-5 message are visible.
- **ER2:** After CR deletion and before archival, the public GET returns the same failed condition, phase, and curated message.
- **ER3:** After archival, the public GET returns HTTP 404 and no archived progress view is served.

### FR-5: Consistent curated failure and read-only presentation

#### TC-FR5-01: Map every approved failure reason to its exact message

| Interface Change | Priority | Automation |
|---|---|---|
| IC-5 | critical | automated |

##### Preconditions

- Feed each approved failure reason to the operator derivation/presentation fixture and render the resulting condition in the UI.

##### Steps

1. Evaluate each failure reason independently.
2. Inspect the condition carrier, failed step, failure reason, and message.

##### Expected Results

- **ER0:** For every fixture, the specified condition carrier has status `False` while the failed step is displayed.
- **ER1:** `NoMatchingHosts` on `PROVISIONED` marks Host Allocation failed and emits exactly `No bare metal host matched the requested profile.`.
- **ER2:** `HostAllocationFailed` on `PROVISIONED` marks Host Allocation failed and emits exactly `Host allocation failed.`.
- **ER3:** `ProvisionJobFailed` on `PROVISIONED` marks Provisioning failed and emits exactly `OS installation and configuration did not complete; the provisioning job failed.`.
- **ER4:** `NetworkAttachmentFailed` on `PROVISIONED` marks Network Setup failed and emits exactly `Network attachment did not complete.`.
- **ER5:** `NetworkHandoffFailed` on `PROVISIONED` marks Network Setup failed and emits exactly `Network handoff (reboot) did not complete.`.
- **ER6:** `IPDiscoveryFailed` on `PROVISIONED` marks Network Setup failed and emits exactly `IP address discovery did not complete.`.
- **ER7:** `ReadyTimeout` on `READY` marks Ready failed and emits exactly `The instance did not reach its powered-on ready state.`.

#### TC-FR5-02: Preserve the coarse reason/message contract without raw errors

| Interface Change | Priority | Automation |
|---|---|---|
| IC-1, IC-2, IC-4 | high | automated |

##### Preconditions

- Prepare a status fixture containing an internal provider/AAP error alongside each stage and failure classification.

##### Steps

1. Run the projection and render the API response.
2. Compare the condition fields with the input internal error.

##### Expected Results

- **ER1:** Progress is carried by the existing `PROVISIONED` and `READY` condition `reason` and `message` fields; no new progress field is required by the API response.
- **ER2:** Repeated projection of the same failure reason emits the same curated message string.
- **ER3:** The API and UI message contain none of the raw provider, AAP, Metal3, or implementation-level error text.

#### TC-FR5-03: Keep the progress surface read-only and scoped

| Interface Change | Priority | Automation |
|---|---|---|
| IC-4 | high | automated |

##### Preconditions

- Render active, failed, and deprovisioning detail fixtures for a tenant-scoped instance.

##### Steps

1. Inspect controls, links, and network requests exposed by the progress view.
2. Inspect the API shape and visible scope for the tenant.

##### Expected Results

- **ER1:** The progress view contains no retry, re-provision, remediation, or log-access control.
- **ER2:** The progress view issues no mutating request while rendering or refreshing status.
- **ER3:** The view uses the existing tenant-authorized instance detail path and exposes no cross-tenant progress list.
- **ER4:** Deprovisioning does not add step-level progress; deletion continues to use the existing coarse lifecycle behavior.
- **ER5:** `CONFIGURATION_APPLIED` is not used as a day-two progress phase.

### NFR-1: Feedback freshness and fallback behavior

#### TC-NFR1-01: Propagate condition reason/message changes through Signal

| Interface Change | Priority | Automation |
|---|---|---|
| IC-3 | critical | automated |

##### Preconditions

- Run the osac-operator feedback controller, fulfillment Signal endpoint, reconciler, persistence backend, and hub API in a deployed Kind setup; provider actions remain simulated.
- Disable or bypass the periodic resync for the measurement interval so it cannot mask the feedback path.

##### Steps

1. Change only a hub `BareMetalInstance` status condition’s reason/message and record the CR update time.
2. Observe the feedback controller call to `Signal(id)`.
3. Observe the fulfillment DB/API condition update and record its completion time.

##### Expected Results

- **ER1:** A status-only condition reason/message change passes the feedback predicate and causes one `Signal(id)` call for the instance.
- **ER2:** The fulfillment reconciler reads the changed CR and persists the new condition reason/message without requiring a new RPC or schema field.
- **ER3:** The CR-update-to-DB/API update interval is less than 10 seconds when the Signal path is healthy, measured without periodic resync or UI polling.
- **ER4:** No new hub watch, informer, or feedback RPC is required; the existing status-change predicate carries reason/message transitions.

#### TC-NFR1-02: Preserve last-known state when a feedback dependency is unavailable

| Interface Change | Priority | Automation |
|---|---|---|
| IC-3 | high | automated |

##### Preconditions

- Start with a persisted stage condition, then make the feedback Signal call unavailable and separately restart the fulfillment reconciler.

##### Steps

1. Advance the hub condition while Signal is unavailable and read the API.
2. Restore the dependency or restart the reconciler and allow its existing full-resync path to run.

##### Expected Results

- **ER1:** While the feedback path is unavailable, the API continues serving the last persisted condition rather than returning raw provider data.
- **ER2:** After the existing fallback resync is restored, the API converges to the current hub-derived stage without a new status schema.
- **ER3:** A fulfillment reconciler restart re-syncs the current CR and does not remove the persisted terminal or failure condition.

### NFR-2: User-visible UI consistency and read-only behavior

#### TC-NFR2-01: Render the existing condition contract through the UI progress view

| Interface Change | Priority | Automation |
|---|---|---|
| IC-4 | high | automated |

##### Preconditions

- Use the existing osac-ui Connect test transport pattern with a typed `BareMetalInstance` response containing only existing condition fields.

##### Steps

1. Render the detail component with active, failed, and terminal responses.
2. Inspect the user-visible progress labels, state text, and messages.

##### Expected Results

- **ER1:** The view derives all progress state from existing `status.conditions[].type`, `status`, `reason`, and `message` values.
- **ER2:** The four fixed phase names and the curated current/failure message are visible for the corresponding fixture.
- **ER3:** The component renders without a generated progress field or a new API endpoint.

#### TC-NFR2-02: Verify visual and accessibility details after the UI-focused design is resolved

| Interface Change | Priority | Automation |
|---|---|---|
| IC-4 | medium | manual |

##### Preconditions

- Use a deployed osac-ui detail page and the UI-focused design decision for layout, component choice, translations, and accessibility affordances.

##### Steps

1. Open an active, failed, and terminal instance in a supported browser.
2. Use keyboard navigation and a screen reader or accessibility inspection tool.

##### Expected Results

- **ER1:** The rendered presentation follows the UI-focused design’s specified layout and accessibility affordances while preserving the four fixed phase names and read-only behavior.

### NFR-3: Contract stability and exhaustive source mapping

#### TC-NFR3-01: Reuse existing condition fields without schema generation

| Interface Change | Priority | Automation |
|---|---|---|
| IC-1 | critical | manual |

##### Preconditions

- Compare the implementation change against the approved proto, CRD, and generated UI type sources.

##### Steps

1. Inspect the API condition projection and UI inputs.
2. Inspect the changed-file set after implementation, without regenerating artifacts.

##### Expected Results

- **ER1:** `BareMetalInstanceCondition.type`, `status`, `last_transition_time`, `reason`, and `message` remain the data contract used for progress.
- **ER2:** No new proto message, enum, field, CRD field, RPC, or progress endpoint is required.
- **ER3:** No generated proto, CRD, or UI type file is changed for this design.

#### TC-NFR3-02: Enforce exhaustive `HostCondition*` classification

| Interface Change | Priority | Automation |
|---|---|---|
| IC-6 | critical | automated |

##### Preconditions

- Enumerate the exported `HostCondition*` constants from the operator package and run the proposed co-located derivation contract test.

##### Steps

1. Compare the constant inventory with the derivation mapping and explicit unsurfaced classification.
2. Add a temporary unclassified constant in the test fixture or equivalent source-controlled test seam.

##### Expected Results

- **ER1:** Every existing exported `HostCondition*` constant appears exactly once in either the stage/failure mapping or the explicit not-surfaced classification.
- **ER2:** The contract test fails when a condition is present in the inventory but absent from both classifications.
- **ER3:** `DeriveProvisioningProgress` accepts `[]metav1.Condition`, reads only those inputs, and produces no external API call or state mutation.

## Execution evidence

The rows below separate a documented command from a proposed test extension and
from actual execution. No row was executed in this phase.

| Evidence row | Behavior and cases | Tier / boundary | Test location | Execution | Dependencies | Readiness / gap |
|---|---|---|---|---|---|---|
| E-1 | Operator derivation and exhaustive mapping: TC-FR1-01, TC-FR1-03, TC-FR2-02, TC-NFR3-02; bare-metal operator owns IC-2/IC-6. | Unit; pure condition-to-result function, no deployed boundary. | Proposed co-located test beside `bare-metal-fulfillment-operator/api/v1alpha1/baremetalinstance_types.go`; existing co-located `*_test.go` pattern. | Existing command: `make test` from `bare-metal-fulfillment-operator/`, defined by its `Makefile` and `AGENTS.md`. Proposed test extension; not run. | Go package and apimachinery real; provider/Kubernetes APIs omitted. | Command path verified; test implementation is proposed and therefore not execution-ready. |
| E-2 | CR status transition fixtures: TC-FR1-01, TC-FR2-02; operator status boundary. | Envtest; in-process operator/controller against Kubernetes API and etcd. | Existing `bare-metal-fulfillment-operator/internal/controller/*_envtest_test.go` suites. | Existing command: `make test` from `bare-metal-fulfillment-operator/`. Proposed fixture extension; not run. | API server, etcd, OSAC CRDs, and static Metal3 CRDs real; Metal3/Ironic/BMC/hardware/provider transitions simulated. | Existing harness path verified; it cannot prove real provider semantics and no test was executed. |
| E-3 | Fulfillment presentation and curated messages: TC-FR1-01, TC-FR5-01, TC-FR5-02. | Unit; `syncStatus` and message projection in the fulfillment package. | Existing `fulfillment-service/internal/controllers/baremetalinstance/baremetalinstance_reconciler_function_test.go`. | Existing command: `ginkgo run -r internal` from `fulfillment-service/`, defined by `fulfillment-service/AGENTS.md`. Proposed expectation updates; not run. | Go code and mocks real; database, hub, operator, and provider are mocked or omitted. | Existing test path verified; current tests encode the old PROVISIONED timing and need implementation-aligned updates. |
| E-4 | Feedback→Signal freshness: TC-NFR1-01, TC-NFR1-02. | Contract/component integration; hub status predicate through Signal to fulfillment persistence/API. | Proposed focused test in the deployed fulfillment/installer integration harness; no existing dedicated BMI feedback-to-DB suite was found. | Existing installer command: `make -C ../osac-installer test PLATFORM=kind PROFILE=dev NS=osac SUITE=fulfillment` from repository root; the focused harness/test case is proposed and no command was run. | Deployed hub/operator, fulfillment service, API, and persistence backend real; provider transitions simulated; periodic resync must be disabled or isolated for the timing assertion. | Missing dedicated harness and exact resync-isolation setup; execution not ready. |
| E-5 | Persistence after CR deletion and archival: TC-FR4-01, TC-FR4-02. | Component integration; fulfillment persistence and public GET/archive boundary. | Proposed extension to the installer-owned fulfillment integration suite; current fulfillment unit tests do not establish the deployed archive boundary. | Same documented installer command as E-4; proposed case, not run. | Fulfillment service/API and configured persistence backend real; hub CR lifecycle real; archive trigger/fixture not identified in the checked-out suite. | Missing archive fixture and dedicated case; execution not ready. |
| E-6 | Deployed BMaaS user journey: TC-FR3-01, TC-FR4-01, TC-FR4-02, and the API portion of TC-FR5-01. | E2E; deployed fulfillment→hub/operator→API journey. | Proposed extension to `tests/e2e/bmaas/sanity/test_baremetal_instance_lifecycle.py`. | Existing collection command: `uv run pytest --collect-only tests/e2e/bmaas/sanity/`; proposed narrow test command must be selected after the case is added. No collection or test run. | Deployed OSAC API/CRs and configured provider environment real; hardware/AAP/provider availability environment-dependent. | Suite and collection command verified; staged reason/message assertions do not yet exist and no provider environment was exercised. |
| E-7 | UI state derivation, failure rendering, and polling: TC-FR1-02, TC-FR2-01, TC-FR2-03, TC-FR3-01, TC-FR3-02, TC-FR5-03, TC-NFR2-01. | Unit; React component/query behavior with a Connect test transport. | Proposed `osac-ui/libs/ui-components/src/components/BareMetalInstance/BareMetalProgress.test.tsx` or the component test location selected by implementation; current `BareMetalDetails` has no progress test. | Existing command: `pnpm test` from `osac-ui/`; proposed test extension, not run. | React/query/test transport real; fulfillment service and browser are simulated/omitted. | Existing Vitest path verified; test file and polling injection seam are proposed, so execution is not ready. |
| E-8 | UI static compatibility: compile portion of TC-NFR2-01. | Static/build validation, not an integration tier. | `osac-ui` package sources and generated type tree. | Existing commands: `pnpm run typecheck` and `pnpm lint` from `osac-ui/`; not run. | TypeScript compiler, ESLint, Prettier, and i18n checks real; API/runtime omitted. | Commands verified; no checks executed; no generated type change is expected. |
| E-9 | UI-focused visual/accessibility contract: TC-NFR2-02. | Manual; live deployed browser boundary. | Existing `osac-ui/apps/playwright` harness is manual/live-cluster only; no persisted BM detail browser suite exists. | Manual environment/actions are specified in the case; the harness requires `OSAC_UI_BASE_URL`, credentials, and a deployed fulfillment endpoint. No browser run. | Browser and deployed UI/API real; no hermetic mock server; screen reader/accessibility tooling required. | UI visual/accessibility decisions are an approved design open question; execution is blocked until resolved and a live environment is available. |
| E-10 | Schema and generated-artifact stability: TC-NFR3-01. | Static source review, not an integration tier. | Top-level proto sources, operator CRD/type sources, and `osac-ui/libs/types`; no new test file is required by the approved design. | No repository test command is defined for this no-schema assertion; perform a manual changed-file review after implementation. No generation run. | Source tree and approved design real; generators and runtime services intentionally omitted. | Planned but not execution-ready as an automated check; the user’s no-generation constraint is preserved. |

## Gaps

### Requirement coverage gaps

All 8 design-defined requirement labels have at least one test case. The PRD-to-
label mapping is a traceability gap because the approved PRD has no canonical
`FR-*`/`NFR-*` identifiers; the mapping above records the design labels without
rewriting the PRD.

### Interface change coverage gaps

All six approved interface changes are exercised by at least one case:

- IC-1: TC-FR1-01, TC-FR4-01, TC-FR4-02, TC-FR5-02, TC-NFR3-01.
- IC-2: TC-FR1-01, TC-FR1-03, TC-FR2-02, TC-FR5-02.
- IC-3: TC-NFR1-01, TC-NFR1-02.
- IC-4: TC-FR1-02, TC-FR2-01, TC-FR2-03, TC-FR3-01, TC-FR3-02, TC-FR4-01, TC-FR4-02, TC-FR5-02, TC-FR5-03, TC-NFR2-01, TC-NFR2-02.
- IC-5: TC-FR4-02, TC-FR5-01.
- IC-6: TC-FR2-02, TC-NFR3-02.

### Remaining gaps by classification

| Classification | Remaining gap | Affected cases / decision needed |
|---|---|---|
| Conflicting approved requirements | None found between the approved PRD and approved design. Older Jira scope is stale input, not an approved-source contradiction. | None. |
| Unspecified behavior | Exact fixed strings for non-failure in-progress stage messages are not enumerated in the approved design; cases assert the fixed stage reason and non-empty curated message, while exact failure strings are asserted. | TC-FR1-01, TC-FR5-02; decide the non-failure message vocabulary before implementation if exact-string assertions are required. |
| Unspecified behavior | The approved design fixes powered-on readiness for the provisioning view but does not define the post-provision stopped-instance interaction with the existing coarse READY state. | TC-FR2-03; implementation must preserve the provisioning terminal boundary or obtain a design decision. |
| Unspecified behavior | Concrete UI layout, component choice, translations, and accessibility affordances are explicitly delegated to a UI-focused design. | TC-NFR2-02; resolve that approved design question before treating manual UI execution as ready. |
| Implementation drift | The operator has no `DeriveProvisioningProgress`; fulfillment currently ratchets `PROVISIONED` at the old milestone; current tests encode that old timing; osac-ui has no progress view or per-page polling seam. | E-1, E-3, E-7; implementation work is required, with no source contract reduction. |
| Missing execution infrastructure | No dedicated deployed Signal→DB freshness harness isolates periodic resync, and no checked-out fulfillment integration case identifies the archive fixture. | E-4, E-5; define the harness/setup owner before execution. |
| Missing execution infrastructure | No persisted BM detail UI test exists, and UI browser coverage is manual/live-cluster only. | E-7, E-9; add the unit seam and resolve the UI-focused design. |
| Boundary limitation | Existing operator envtest/Kind and BMaaS E2E suites simulate or depend on provider transitions; they do not prove real Metal3/Ironic/BMC/hardware semantics. | E-2, E-6; real-provider coverage remains outside this phase and follows the component guide’s OSAC-4843 boundary. |
| Traceability | The approved PRD’s six unnumbered in-scope behaviors and the design’s eight labels are not a one-to-one source taxonomy. | Requirement mapping above is explicit; downstream work should preserve the mapping rather than invent PRD IDs. |

## Assertion-preservation audit

The audit was performed against the PRD and approved design independently. Each
row names a concrete case and quotes the decisive Expected Results wording;
execution readiness is reported separately from preservation.

| Source assertion | TC / exact Expected Results evidence | Verdict |
|---|---|---|
| PRD-01 current phase/state/message and pending/completed ordering | TC-FR1-01 ER1: “`PROVISIONED` is not true and its reason is exactly `HostAllocation`”; TC-FR1-02 ER2: “earlier steps are shown as complete, the current step is shown as in progress, later steps are shown as not yet started” | preserved |
| PRD-02 no-work phase | TC-FR1-03 ER1: “A network stage with no work is represented as complete and the view does not leave `Network Setup` pending.” | preserved |
| PRD-03 four phases and folded work | TC-FR2-01 ER1: “The only progress labels are `Host Allocation`, `Provisioning`, `Network Setup`, and `Ready`”; ER2 excludes the four folded labels | preserved |
| PRD-04 bounded refresh | TC-FR3-01 ER1: “refreshes on its dedicated approximately five-second interval while the instance is non-terminal.” | preserved |
| PRD-05 stop at success/failure | TC-FR3-02 ER1–ER2: “makes no further automatic progress refresh requests” after each terminal outcome | preserved |
| PRD-06 single-digit-second user visibility | TC-FR3-01 ER4: “the measured interval is less than 10 seconds” from CR transition to detail update | preserved |
| PRD-07 terminal success/failure presentation | TC-FR4-01 ER1: “all four phases succeeded”; TC-FR4-02 ER1: “the failed step and its exact IC-5 message are visible.” | preserved |
| PRD-08 lifetime persistence until archive | TC-FR4-01 ER2–ER3 and TC-FR4-02 ER2–ER3 specify same conditions before archive and HTTP 404 after archive | preserved |
| PRD-09 no timeline/durations | TC-FR4-01 ER4: “does not expose an ordered phase history or per-phase duration values.” | preserved |
| PRD-10 coarse reason/message pattern | TC-FR5-02 ER1: “Progress is carried by the existing `PROVISIONED` and `READY` condition `reason` and `message` fields” | preserved |
| PRD-11 human-readable phase/condition failure | TC-FR5-01 ER1–ER7 name each failed step and exact message | preserved |
| PRD-12 no raw internal errors | TC-FR5-02 ER3: “contain none of the raw provider, AAP, Metal3, or implementation-level error text.” | preserved |
| PRD-13 read-only scope | TC-FR5-03 ER1–ER3 enumerate absent controls, no mutating request, and no cross-tenant list | preserved |
| PRD-14 deprovisioning/day-two exclusions | TC-FR5-03 ER4–ER5 explicitly exclude both surfaces | preserved |
| DES-01 existing schema/no generated type change | TC-NFR3-01 ER1–ER3 name the existing fields and explicitly exclude new schema/generated changes | preserved |
| DES-02 pure derivation and syncStatus | TC-FR1-01 ER1–ER5 gives the derivation inputs and projection outputs; TC-NFR3-02 ER1 and ER3 name the exhaustive input-only contract | preserved |
| DES-03 order-independent furthest stage | TC-FR2-02 ER1–ER2 specify equal results and furthest-stage selection | preserved |
| DES-04 milestone mapping | TC-FR1-01 ER1–ER5 enumerate Host Allocation, Provisioning, Network Setup, Provisioned, and Ready outputs | preserved |
| DES-05 PROVISIONED/READY boundary | TC-FR2-03 ER1–ER2 explicitly names both condition combinations and UI outcomes | preserved |
| DES-06 exact failure vocabulary | TC-FR5-01 ER0–ER7 quote the false carrier plus all seven exact messages and carriers/steps | preserved |
| DES-07 exhaustive condition classification | TC-NFR3-02 ER1–ER2 require one mapping/classification per constant and a failing unclassified test | preserved |
| DES-08 no-work/retry/opaque-job behavior | TC-FR1-03 ER1–ER3 gives each concrete outcome | preserved |
| DES-09 Signal freshness path | TC-NFR1-01 ER1–ER4 names status-only trigger, Signal call, persistence, less-than-10-second interval, and reuse of the existing watch path | preserved |
| DES-10 persistence/archive boundary | TC-FR4-01 ER2–ER3 and TC-FR4-02 ER2–ER3 specify retained conditions and 404 after archive | preserved |
| DES-11 UI derivation rules | TC-FR1-02 ER1–ER4 and TC-FR2-03 ER1–ER2 name all four steps, active/failure/terminal states, and messages | preserved |
| DES-12 UI polling terminal predicate | TC-FR3-01 ER1–ER4 and TC-FR3-02 ER1–ER2 specify interval, visible update, and both stop conditions | preserved |
| DES-13 outage/restart/fallback behavior | TC-NFR1-02 ER1–ER3 specifies last-known serving and convergence after fallback/restart | preserved |
| DES-14 tenant boundary | TC-FR5-03 ER3: “uses the existing tenant-authorized instance detail path and exposes no cross-tenant progress list.” | preserved |
| Exact non-failure stage message strings | No approved source gives the exact prose for active `HostAllocation`, `Provisioning`, or `NetworkSetup` messages; TC-FR1-01 ER1–ER3 preserve non-empty curated output only. | unresolved source contract; flagged |
| Post-provision stopped-instance READY semantics | Approved design specifies powered-on readiness but does not state the later stopped-instance interaction; TC-FR2-03 covers only the specified provisioning boundary. | unresolved source contract; flagged |
| Concrete UI visual/accessibility contract | Approved design explicitly delegates layout and accessibility affordances; TC-NFR2-02 is manual and conditional on that decision. | unresolved source contract; flagged |

### Audit result

- **Source assertions audited:** 31, including the three unresolved source-contract rows.
- **Preserved:** 28.
- **Missing/weakened:** 0.
- **Unresolved source contracts:** 3; none was silently narrowed or replaced with an invented requirement.
- **Case-link coverage:** 19/19 test cases link to at least one execution-evidence row; case links do not substitute for the Expected Results audit.
- **Planning result:** FLAG because unresolved source contracts remain. The behavioral assertions are retained, and infrastructure gaps are reported separately from the contract gaps.

## Corrections made within this phase

### Correction round 1 — assertion-to-result audit

The first internal pass identified that the active-stage UI case did not
separately state the terminal `PROVISIONED=True`/`READY=True` boundary, and the
freshness case did not state the exact `<10 seconds` comparison operator. The
written cases were corrected to add TC-FR2-03 ER1–ER2 and TC-FR3-01 ER4, then
the audit was regenerated against those bullets.

### Correction round 2 — execution-evidence recheck

The recheck separated existing commands from proposed test extensions and
classified the Signal→DB and archive checks as not execution-ready because no
dedicated harness/fixture was found. It also preserved the provider-boundary
limitation rather than treating envtest or static Metal3 fixtures as real
provider coverage. No source assertion was removed or weakened.

## Summary

| Metric | Count |
|---|---:|
| Total test cases | 19 |
| Critical | 11 |
| High | 7 |
| Medium | 1 |
| Low | 0 |
| Automated | 17 |
| Manual | 2 |
| Requirements with test cases | 8 / 8 |
| Interface changes with test cases | 6 / 6 |
| Assertions preserved | 28 / 31 |
| Missing or weakened assertions | 0 |
| Unresolved source contracts | 3 |

No test execution result is claimed. The phase stops here for review; no
decomposition or publication follows this artifact.
