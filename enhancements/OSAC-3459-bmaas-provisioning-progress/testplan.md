# Testplan — OSAC-3459

## Overview

- **Feature:** OSAC-3459 — BMaaS Provisioning Progress and Step Visibility
- **Total test cases:** 11
- **Requirements covered:** 8 of 8 approved-design labels (FR-1–FR-5, NFR-1–NFR-3)
- **Interface changes covered:** 6 of 6 (IC-1–IC-6)
- **Planning status:** FLAG — behavioral coverage is complete, but the full
  CR-to-UI freshness path and persisted browser coverage are not execution-ready.

The published PRD does not define numbered FR/NFR identifiers. This plan retains
the labels and mappings used by the approved design; the requirement text below
is a concise mapping to the PRD's In Scope, User Stories, and Out of Scope
sections, not newly invented canonical requirement wording.

## Execution Evidence Matrix

Each row identifies the assertion tier and its boundary. A proposed test file
or extension is planned work, not evidence that the suite already exists. No
tests were run for this draft.

| Behavior and cases | Owning component / refs | Tier and boundary | Test location | Execution | Dependencies and coverage boundary | Readiness / gap |
|---|---|---|---|---|---|---|
| Deterministic stage selection, order independence, and explicit no-work advancement — TC-FR2-01 | `bare-metal-fulfillment-operator`; FR-2, IC-2 | Unit; pure condition-to-stage function | Proposed `bare-metal-fulfillment-operator/api/v1alpha1/baremetalinstance_progress_test.go` | Existing `make test` from `bare-metal-fulfillment-operator/`, defined by `bare-metal-fulfillment-operator/Makefile` | `metav1.Condition` fixtures only; no Kubernetes API, fulfillment service, database, provider, or AAP | Command exists; proposed test file is not present. Unit execution is ready after implementation. |
| Exhaustive classification of every exported operator condition — TC-NFR3-01 | `bare-metal-fulfillment-operator`; NFR-3, IC-6 | Unit; operator condition contract | Same proposed API-package test file | Existing `make test` from `bare-metal-fulfillment-operator/` | Enumerates `HostCondition*` constants; provider and external controllers are omitted | Planned but not execution-ready until the exhaustive test and mapping exist. |
| Fulfillment presentation of active, provisioned, and ready condition values — TC-FR1-01 | `fulfillment-service`; FR-1, IC-1, IC-2 | Unit; `syncStatus` observable proto projection | Extend `fulfillment-service/internal/controllers/baremetalinstance/baremetalinstance_reconciler_function_test.go` | Existing `ginkgo run -r internal` from `fulfillment-service/`, documented by `fulfillment-service/AGENTS.md` | Uses operator condition fixtures and the local module replacement; no PostgreSQL, REST server, feedback controller, provider, or UI | Existing suite and command are available; the new assertions are proposed. |
| Fixed failure vocabulary and suppression of raw internal errors — TC-FR5-01 | `fulfillment-service`; FR-5, IC-5 | Unit; reconciler presentation and message mapping | Extend the same fulfillment reconciler test file | Existing `ginkgo run -r internal` from `fulfillment-service/` | Tests all seven approved failure mappings; operator/AAP/Metal3 raw error strings are fixture inputs only and must not cross the presentation boundary | Existing command is available; coverage is missing and must be added. |
| Feedback predicate reacts to condition reason/message transitions — TC-NFR1-01 | `osac-operator`; NFR-1, IC-3 | Unit; status-change predicate and Signal invocation boundary | Extend `osac-operator/internal/controller/baremetalinstance_feedback_controller_test.go` | Existing `make test` from `osac-operator/`, defined by `osac-operator/Makefile` | Kubernetes client and fulfillment RPC are test doubles; this proves predicate/caller behavior, not DB persistence or deployed networking | Existing focused tests are available; reason/message-specific assertions are proposed. |
| API-visible terminal/failure conditions persist after CR deletion until archival — TC-FR4-01 | `tests/e2e/bmaas` plus fulfillment persistence | E2E; deployed CR → feedback/reconcile → DB → API boundary | Proposed extension to `tests/e2e/bmaas/sanity/test_baremetal_instance_lifecycle.py`, using `tests/e2e/core/helpers.py` | Proposed focused command: `uv run pytest tests/e2e/bmaas/sanity/test_baremetal_instance_lifecycle.py -k 'progress or persistence'` from the repository root | Requires deployed fulfillment-service, PostgreSQL, osac-operator feedback, bare-metal operator, API auth, and a BMaaS fixture; gRPC/Kubernetes are real; the browser is omitted | Existing lifecycle journey is available but has no persistence assertion. The fixture and deletion/archive observation need explicit implementation. |
| CR status change reaches the API within the source freshness bound without relying on fallback resync — TC-NFR1-02 | `tests/e2e/bmaas` and feedback boundary; NFR-1, IC-3 | E2E; CR status update → Signal → fulfillment DB → API | Proposed extension to the same BMaaS lifecycle test and helpers | Proposed focused pytest command as above | Requires the same deployed chain. The trigger timestamp must be recorded at the CR condition update, the API condition must be observed, and the pass bound is `<10 seconds` as the PRD's single-digit-seconds requirement; periodic full resync must be disabled or accounted for | Planned but blocked by missing deterministic fixture/control over the CR update and Signal-vs-resync measurement. No current suite proves this bound. |
| Four ordered UI steps render pending, in-progress, complete, and terminal-ready states — TC-FR1-02 | `osac-ui`; FR-1, IC-4 | Unit; React component behavior with mocked Connect response | Proposed `osac-ui/libs/ui-components/src/components/BareMetalInstance/BareMetalDetails.test.tsx` and/or page test | Existing `pnpm --filter @osac/app-frontend test` from `/tmp/osac-pilot-iteration-4/osac/osac-ui`; command is defined by the UI package scripts and Vitest config | React Testing Library/jsdom, `TestProviders`, and mocked Connect transport are real test harness components; fulfillment API, proxy, DB, controllers, and providers are mocked/omitted | Harness and command exist; no BMaaS detail-page test exists. The test is planned, not execution-ready until the renderer is implemented. |
| Fixed failure reason maps to the failed UI step and curated message; no retry action appears — TC-FR5-02 | `osac-ui`; FR-5, IC-4 | Unit; read-only UI state and message rendering | Same proposed BMaaS detail component/page test | Existing app-frontend Vitest command from the UI checkout | Uses condition fixtures for each approved failure; no real API or backend boundary | Harness exists; focused coverage is absent and requires implementation. |
| Active UI refresh uses the approved bounded approximately five-second interval and stops at READY/failure — TC-FR3-01 | `osac-ui`; FR-3, IC-4 | Unit; query scheduling and terminal polling policy | Proposed `osac-ui/libs/ui-components/src/pages/tenant/BareMetalDetailsPage.test.tsx` or a focused query-hook test | Existing `pnpm --filter @osac/app-frontend test` from the UI checkout, with fake timers and an explicitly configured QueryClient | Mocked Connect transport and fake timers isolate UI scheduling; current `TestProviders` disables refetch intervals, so the test must provide an override; no proxy, DB, feedback, or provider | Current UI has only global 10-second polling and no terminal stop. The command exists, but the approved behavior is not implemented or covered. |
| User-visible refresh reflects a backend stage change within the source bound across CR → feedback → persisted API → browser, then stops after terminal state — TC-NFR2-01 | `osac-ui` plus deployed OSAC stack; NFR-2, IC-4 | E2E; hub CR update → feedback Signal → persisted API response → browser DOM | Proposed persisted `osac-ui/apps/playwright/src/bmaas-progress.spec.ts` | Existing `pnpm playwright:setup` followed by `pnpm playwright:run` from the UI checkout | Requires `OSAC_UI_BASE_URL`, Keycloak credentials, deployed UI/proxy, fulfillment-service/PostgreSQL, feedback controller, bare-metal operator, deterministic BMaaS fixture, and timestamp/log correlation for the CR write, Signal, API response, and DOM update; no mocked fulfillment service | The checked-in Playwright suite only has an authenticated masthead smoke test. Scratch specs are manual/non-persistent; this case is blocked pending a persisted scenario, deployed fixture, and full-path measurement. |

## Test Cases

### FR-1: The detail view exposes the four ordered provisioning phases and their current state

#### TC-FR1-01: Fulfillment projects each active and terminal stage into existing conditions

| Interface Change | Priority | Automation |
|-----------------|----------|------------|
| IC-1, IC-2 | critical | automated |

##### Preconditions

- `syncStatus` receives operator conditions representing Host Allocation,
  Provisioning, Network Setup, full provisioning completion, and readiness.
- The existing `PROVISIONED` and `READY` proto condition slots are available.

##### Steps

1. Invoke the fulfillment reconciler status projection for each staged fixture.
2. Inspect the emitted `PROVISIONED` and `READY` condition type, status, reason,
   message, and transition values.

##### Expected Results

- Active fixtures emit `PROVISIONED=False` with reason `HostAllocation`,
  `Provisioning`, or `NetworkSetup` and a non-empty stage-specific curated
  message. The approved design does not specify the exact prose for these
  three active-stage messages, so the test must not invent an expected string.
- Full provisioning emits `PROVISIONED=True` with reason `Provisioned` and
  message `Infrastructure has been allocated and provisioned.`.
- Readiness emits `READY=True` with reason `Ready` and message `The instance is
  ready.`.
- The existing condition fields carry all progress information; no new proto or
  CRD field is required.

#### TC-FR1-02: UI renders the four phases with the current phase highlighted

| Interface Change | Priority | Automation |
|-----------------|----------|------------|
| IC-4 | critical | automated |

##### Preconditions

- A mocked `BareMetalInstances.Get` response contains each staged condition
  fixture in turn.
- The detail page is rendered through the UI test providers.

##### Steps

1. Render the detail page with Host Allocation, Provisioning, Network Setup,
   `PROVISIONED=True`/`READY=False`, and `READY=True` responses.
2. Query the four phase labels and their state text.

##### Expected Results

- The page renders exactly Host Allocation, Provisioning, Network Setup, and
  Ready in that order.
- Earlier phases are marked complete, the derived current phase is marked
  in-progress, later phases are pending, and the terminal response marks all
  four complete.
- When `PROVISIONED=True` and `READY=False`, Host Allocation, Provisioning, and
  Network Setup are complete and Ready is the only in-progress phase; the page
  does not mark all four complete at this intermediate state.
- Only when `READY=True` does the page mark all four phases complete.
- The current condition message is visible beside the active phase.
- No retry, re-provision, or other mutating control is rendered by the progress
  view.

### FR-2: Stage derivation is deterministic and handles skipped work

#### TC-FR2-01: Furthest-advanced condition wins regardless of condition order

| Interface Change | Priority | Automation |
|-----------------|----------|------------|
| IC-2, IC-6 | critical | automated |

##### Preconditions

- The operator condition fixture set includes every provisioning-related
  lifecycle condition and the explicitly unsurfaced deletion conditions.
- Equivalent condition sets are supplied in multiple orderings, including a
  no-network-attachment case.

##### Steps

1. Call `DeriveProvisioningProgress` for each ordering and lifecycle fixture.
2. Compare the returned stage, provisioning-complete, ready, and failure
   classifications.

##### Expected Results

- Equal condition sets produce the same result independent of slice order.
- The furthest true lifecycle signal selects Host Allocation, Provisioning,
  Network Setup, `Provisioned`, or `Ready` according to the approved mapping.
- A no-work Network Setup path advances to completion and does not remain in a
  pending Network Setup state.
- Retried work remains on the same stage until its driving condition changes.
- Deletion-only conditions are explicitly classified as not surfaced by the
  provisioning derivation.

### FR-3: Active provisioning refreshes without user reload and stops at terminal state

#### TC-FR3-01: UI polling follows the active interval and terminates at READY or failure

| Interface Change | Priority | Automation |
|-----------------|----------|------------|
| IC-4 | high | automated |

##### Preconditions

- A focused page/query test supplies a QueryClient with fake timers and a mock
  Connect transport that returns a non-terminal response, then READY or a
  failed condition.
- The test does not use the default test provider setting that disables
  refetch intervals.

##### Steps

1. Render the page with an active provisioning response and advance the fake
   clock through one approved approximately five-second interval.
2. Return a terminal response and advance the clock through additional polling
   intervals.

##### Expected Results

- The query requests the active instance again on the configured bounded
  approximately five-second interval without a browser reload.
- The updated stage/message is rendered after the response changes.
- After `READY=True` or a provisioning failure, no further interval requests
  occur.
- The test does not pass through the current global 10-second interval as a
  substitute for the approved per-page behavior.

### FR-4: Terminal and failure outcomes remain available from the instance record

#### TC-FR4-01: Persisted terminal or failure conditions remain readable after CR deletion

| Interface Change | Priority | Automation |
|-----------------|----------|------------|
| — | high | automated |

##### Preconditions

- A deployed BMaaS environment has a test instance and the full feedback path.
- The instance has reached either terminal success or a phase-specific failure,
  and the API has returned the corresponding conditions.

##### Steps

1. Record the terminal or failure condition payload from the API.
2. Remove the hub CR through the normal release/deletion path.
3. Query the instance API before the fulfillment record is archived, then query
   after archival.

##### Expected Results

- Before archival, the API returns the same terminal or failure reason/message
  and the failed or completed phase remains identifiable.
- The full ordered phase history and per-phase durations are not required in
  the response.
- After archival, the public GET returns the existing not-found response.

### FR-5: Failures identify the phase with curated human-readable text

#### TC-FR5-01: Every approved failure reason emits its exact curated message

| Interface Change | Priority | Automation |
|-----------------|----------|------------|
| IC-5 | critical | automated |

##### Preconditions

- The reconciler receives one fixture for each approved failure reason:
  `NoMatchingHosts`, `HostAllocationFailed`, `ProvisionJobFailed`,
  `NetworkAttachmentFailed`, `NetworkHandoffFailed`, `IPDiscoveryFailed`, and
  `ReadyTimeout`.

##### Steps

1. Project each failure fixture through the fulfillment presentation layer.
2. Inspect the condition carrier, failure reason, and message.

##### Expected Results

- `NoMatchingHosts` produces `No bare metal host matched the requested
  profile.` on `PROVISIONED`.
- `HostAllocationFailed` produces `Host allocation failed.` on `PROVISIONED`.
- `ProvisionJobFailed` produces `OS installation and configuration did not
  complete; the provisioning job failed.` on `PROVISIONED`.
- `NetworkAttachmentFailed` produces `Network attachment did not complete.`
  on `PROVISIONED`.
- `NetworkHandoffFailed` produces `Network handoff (reboot) did not complete.`
  on `PROVISIONED`.
- `IPDiscoveryFailed` produces `IP address discovery did not complete.` on
  `PROVISIONED`.
- `ReadyTimeout` produces `The instance did not reach its powered-on ready
  state.` on `READY`.
- No raw operator, AAP, Metal3, or Ironic error string appears in a public
  condition message.

#### TC-FR5-02: UI marks the failed phase and remains read-only

| Interface Change | Priority | Automation |
|-----------------|----------|------------|
| IC-4 | high | automated |

##### Preconditions

- The UI receives each approved failure payload through the mocked Connect
  transport.

##### Steps

1. Render the instance detail view for each failure carrier and reason.
2. Inspect the four phase states, failure message, and available controls.

##### Expected Results

- The phase named by the failure mapping is marked failed; earlier phases retain
  completed state and later phases remain pending.
- The exact curated message for the reason is visible on the failed phase.
- Raw backend error text is absent.
- The progress view exposes no retry or re-provision action.

### NFR-1: Backend status changes reach the persisted/API representation within the stated freshness bound

#### TC-NFR1-01: Condition reason/message changes trigger the existing feedback Signal path

| Interface Change | Priority | Automation |
|-----------------|----------|------------|
| IC-3 | high | automated |

##### Preconditions

- The feedback controller test has a hub `BareMetalInstance` with an existing
  status and a fulfillment RPC test double.

##### Steps

1. Change only a condition reason or message on the hub resource status.
2. Run the feedback predicate and reconcile path.
3. Inspect the fulfillment RPC calls.

##### Expected Results

- The semantic status predicate accepts the reason/message-only status change.
- Exactly one `BareMetalInstances.Signal(id)` call is issued for the changed
  instance.
- An unchanged status does not issue a new Signal call.
- The test does not claim that the RPC double persisted data in PostgreSQL.

#### TC-NFR1-02: CR-to-API freshness is below ten seconds on the deployed Signal path

| Interface Change | Priority | Automation |
|-----------------|----------|------------|
| IC-3 | critical | automated |

##### Preconditions

- A deployed environment contains the bare-metal operator, osac-operator
  feedback controller, fulfillment-service, PostgreSQL, and an API-authenticated
  BMaaS fixture.
- The test can timestamp the hub condition update and observe the API response;
  periodic full resync is disabled or its timing is recorded so it cannot mask
  the Signal path.

##### Steps

1. Advance a test instance's condition reason/message to the next approved
   stage and record the update time.
2. Poll the instance API using bounded polling until the new reason/message is
   returned.
3. Record the elapsed time and the feedback/reconcile evidence.

##### Expected Results

- The API returns the new stage and curated message less than 10 seconds after
  the CR status update.
- The observed path includes feedback `Signal` and DB synchronization; a
  periodic resync alone is not accepted as proof of this case.
- If the Signal path is unavailable, the case is reported blocked rather than
  passing on a fallback resync result.

### NFR-2: The UI presents fresh active progress within the source bound and stops polling at terminal state

#### TC-NFR2-01: Browser view reflects the full-path update within single-digit seconds and ceases requests at terminal state

| Interface Change | Priority | Automation |
|-----------------|----------|------------|
| IC-4 | high | automated |

##### Preconditions

- A persisted Playwright scenario is available in the UI repository.
- A live deployment is configured through `OSAC_UI_BASE_URL`,
  `OSAC_USERNAME`, and `OSAC_PASSWORD`, with a deterministic BMaaS fixture whose
  condition can advance from an active stage to READY or failure.
- The scenario can observe four measurement endpoints: `t0`, when the updated
  condition is persisted/observed on the hub `BareMetalInstance` CR; `t_signal`,
  when the feedback controller sends or records `Signal(id)`; `t_api`, when an
  API GET response first contains the updated persisted reason/message; and
  `t_browser`, when the browser DOM first displays the updated phase/message.

##### Steps

1. Authenticate and open the instance detail page.
2. Advance the backend condition while the page remains open and record `t0`
   at the hub CR status update, not when the browser receives a response.
3. Correlate the feedback-controller `Signal(id)` event as `t_signal`, record
   the first API response carrying the new persisted condition as `t_api`, and
   record `t_browser` when the updated phase/message is visible in the DOM.
4. Advance the instance to READY or failure and monitor subsequent requests.

##### Expected Results

- The complete user-visible freshness interval `t_browser - t0` is less than
  10 seconds, preserving the PRD's single-digit-seconds bound. The measured
  interval includes CR update, feedback Signal, persistence/API visibility,
  browser polling, and DOM rendering.
- `t_signal` and `t_api` are observed in the path before `t_browser`; measuring
  only `t_api - t0` is insufficient evidence for this browser requirement.
- The browser shows the new stage and message without a page reload during the
  active polling window.
- The browser stops issuing instance refresh requests after the terminal
  response.
- The checked-in scenario records the user-visible result and does not rely on
  a scratch spec or a mocked fulfillment endpoint.
- If any of `t0`, `t_signal`, `t_api`, or `t_browser` cannot be observed, or if
  the deployed fixture/browser scenario is unavailable, the case is reported
  blocked rather than passing.

### NFR-3: The projection contract remains deterministic and compatible with existing fields

#### TC-NFR3-01: Exhaustiveness guard rejects an unclassified lifecycle condition

| Interface Change | Priority | Automation |
|-----------------|----------|------------|
| IC-6 | high | automated |

##### Preconditions

- The operator package exposes the lifecycle condition constants used by the
  bare-metal status controller.
- The exhaustive test enumerates those constants and the derivation's explicit
  surfaced or intentionally-unsurfaced classifications.

##### Steps

1. Run the derivation contract test against the current condition constant set.
2. Add a synthetic unclassified constant in the test fixture or equivalent
   contract input.

##### Expected Results

- The current condition set passes only when every constant has a declared
  classification.
- The synthetic unclassified condition causes a test failure naming the missing
  mapping.
- The contract continues to use existing `reason`, `message`, and transition
  fields; no generated proto or CRD artifact is required for this behavior.

## Gaps

### Requirement Coverage Gaps

All eight approved-design requirement labels have at least one behavioral test
case. The published PRD has no numbered FR/NFR identifiers, so the mapping is
not mechanically verifiable against PRD labels until the requirement traceability
is normalized; this is a documentation/traceability gap, not an omitted case.

### Interface Change Coverage Gaps

All six interface changes in approved design §5 are exercised by at least one
test case. The UI visual/interaction layout remains a design open question, but
the behavioral contract in IC-4 has cases for rendering, failure, refresh, and
terminal stop.

### Execution Infrastructure Gaps

- The approved design's `Infrastructure Needed` section says `None`, but the
  updated architectural context identifies concrete missing infrastructure for
  browser freshness: a deployed UI/proxy, authentication, fulfillment-service
  with PostgreSQL, feedback controller, bare-metal operator, and a deterministic
  BMaaS fixture, plus a persisted browser scenario. The context evidence governs
  this execution assessment; the design copy remains unchanged.
- The current BMaaS pytest lifecycle suite validates coarse gRPC/Kubernetes
  lifecycle state, not staged reason/message progression or the CR-to-API timing
  bound. TC-FR4-01 and TC-NFR1-02 require proposed assertions and controlled
  fixtures.
- Envtest and RPC test doubles cover local controller behavior only. They do not
  establish fulfillment persistence, PostgreSQL, deployed feedback networking,
  provider behavior, or browser rendering.
- The current UI Vitest harness disables refetch intervals, while the checked-in
  UI has global 10-second polling and no terminal stop. TC-FR3-01 requires an
  explicit QueryClient/fake-timer setup after implementation.
- The approved design specifies exact terminal and failure messages but not the
  exact active-stage prose for Host Allocation, Provisioning, and Network Setup.
  The implementation owner must define those three curated strings before
  TC-FR1-01 can assert exact message values; this plan asserts non-empty,
  stage-specific, non-internal text until that contract is resolved.
- The current Playwright suite contains only an authenticated masthead smoke
  test; scratch specs are not persisted regression coverage. TC-NFR2-01 remains
  blocked until a committed BMaaS scenario, live fixture, and full-path timing
  instrumentation exist. A backend-only CR-to-API measurement does not satisfy
  the browser freshness requirement.
- Real Metal3/Ironic/BMC/hardware semantics remain outside the current static
  provider suites and require the qualifying OSAC-4843 boundary if claimed.

## Summary

| Metric | Count |
|--------|-------|
| Total test cases | 11 |
| Critical | 5 |
| High | 6 |
| Medium | 0 |
| Low | 0 |
| Automated | 11 |
| Manual | 0 |
| Requirements with test cases | 8 / 8 |
| Interface changes with test cases | 6 / 6 |

## Planning Check

**FLAG**

### Corrections made in this phase

- Added an execution-evidence matrix with the owning component, canonical tier,
  boundary, test location, command, prerequisites, simulated dependencies, and
  readiness state for every behavioral case.
- Preserved the approved design's negative, exhaustive, no-work, lifecycle,
  persistence, failure-vocabulary, timing, and terminal-polling assertions;
  they were not replaced by generic schema or compatibility checks.
- Corrected the approved design's broad `envtest`/`kind` planning language into
  selected tiers and explicit boundaries. Envtest/unit and RPC doubles are not
  presented as fulfillment DB, deployed feedback, provider, or UI coverage.
- Selected the existing UI Vitest command for component behavior and the
  existing Playwright commands for a proposed persisted browser case, while
  recording that neither currently contains BMaaS progress coverage.
- Corrected TC-FR1-02 to distinguish the intermediate
  `PROVISIONED=True`/`READY=False` state from terminal `READY=True`, and
  corrected TC-NFR2-01 to measure the full CR → Signal → persisted API → DOM
  interval rather than accepting backend-only timing.
- Carried the published PRD/design FR/NFR identifier mismatch as an explicit
  traceability gap instead of inventing canonical PRD IDs.

### Remaining findings

**Planning omissions or unresolved contracts:**

- The approved design does not define exact active-stage message strings for
  Host Allocation, Provisioning, or Network Setup. TC-FR1-01 therefore asserts
  non-empty, stage-specific, non-internal text and leaves exact-string coverage
  unresolved.
- The published PRD has no numbered FR/NFR identifiers. The plan preserves the
  approved design's labels, but the requirement mapping still needs source-level
  normalization before traceability can be mechanically verified.

**Execution prerequisites, not planning omissions:**

- The proposed operator, fulfillment, feedback, BMaaS E2E, UI Vitest, and
  persisted Playwright assertions do not yet exist; their repository commands
  and proposed locations are named in the evidence matrix.
- TC-FR4-01 and TC-NFR1-02 require a deployed fulfillment/feedback/database
  chain and a deterministic BMaaS fixture. TC-NFR2-01 additionally requires a
  committed browser scenario and instrumentation for `t0`, `t_signal`,
  `t_api`, and `t_browser`.
- No real provider boundary is required for the pure projection cases. Any
  claim about Metal3/Ironic/BMC/hardware behavior still requires the separate
  OSAC-4843 qualifying boundary.

### Result and readiness

Behavioral requirement and interface coverage is complete on paper, but the plan
is not fully execution-ready. Unit and component test commands exist; their
focused assertions are proposed. The API persistence/freshness cases require a
deployed cross-component environment and deterministic fixtures. The user-visible
freshness case additionally requires persisted browser coverage and a live UI
environment. No tests or collection commands were run during this phase.
