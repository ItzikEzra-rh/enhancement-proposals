# Testplan — OSAC-3459

## Overview

- Feature: BMaaS provisioning progress and terminal outcome visibility.
- Source inputs: the published PRD, the approved design copied to `03-design.md`, and the fresh `01-context.md`.
- Scope: behavioral verification of the approved architecture and its existing condition/status interfaces. This plan does not add API or CRD fields.
- Total test cases: 12.
- Requirements covered: 8 of 8 referenced IDs (`FR-1` through `FR-5`, `NFR-1` through `NFR-3`).
- Interface changes covered: 6 of 6 (`IC-1` through `IC-6`).

### Traceability note

The published PRD does not declare formal `FR-*` or `NFR-*` requirement headings. The IDs below are retained exactly from the approved design's interface-change requirement references. The descriptions are working traceability labels derived from those references and the PRD scope; they are not new requirements. The canonical wording and any missing numeric bounds must be confirmed during review.

| Requirement ID | Working traceability label used by this plan | Source of the mapping |
|---|---|---|
| FR-1 | Staged provisioning progress is visible through the existing status/detail surfaces | Approved design IC-1, IC-2, IC-4; PRD progress-view scope |
| FR-2 | The approved four-stage model is derived from the existing condition contract | Approved design IC-2, IC-6 |
| FR-3 | The active detail view refreshes progress automatically | Approved design IC-4; PRD progress-view scope |
| FR-4 | Terminal success and failure remain viewable for the record lifetime | Approved design terminal-state behavior; PRD terminal-outcome scope |
| FR-5 | Failures use curated phase-specific human-readable messages | Approved design IC-5; PRD failure-message scope |
| NFR-1 | Feedback keeps API-visible status fresh through the existing Signal path | Approved design IC-3 |
| NFR-2 | The progress surface is consistent, readable, and read-only while updating | Approved design IC-4; exact canonical wording is not declared in the PRD |
| NFR-3 | The cross-service condition contract remains stable and exhaustively interpreted without a new schema | Approved design IC-1, IC-6 |

### Approved behavior boundaries

- The approved stages are `Host Allocation`, `Provisioning`, `Network Setup`, and `Ready`. Failure is terminal and is associated with the phase in which it occurs.
- The approved design uses the existing `reason` and `message` fields on the existing status condition. Expected results below must not require a new field, CRD property, or proto field.
- The approved failure vocabulary is normative for the user-visible failure message. Exact strings are asserted in `TC-FR5-01`.
- Visual choices that the approved design leaves open—layout, colors, icons, and animation—are not behavioral assertions. Tests assert semantic state, text, read-only behavior, and update timing only.
- The current implementation observations in `01-context.md` are baseline context, not expected results. In particular, the current coarse status projection, global UI polling interval, absent operator derivation helper, and existing `READY` comment do not override the approved design.

### Test execution conventions

- Existing unit and envtest cases run with the component's documented `make test` or focused Go test command from that component directory.
- Existing UI tests run from `osac-ui/` with the documented Vitest command; React Testing Library and fake timers may be used for deterministic polling assertions.
- Proposed cross-component cases must use bounded observable waits, not fixed sleeps. External Metal3/Ironic/BMC provisioning is mocked or isolated unless a real-provider environment is explicitly supplied.
- Proposed E2E cases belong under `tests/e2e/bmaas/` and must use the existing BMaaS fixtures and wait helpers. They are not claimed to exist in the current suite.

## Test Cases

### FR-1: Staged provisioning progress is visible

#### TC-FR1-01: Project the current stage through the existing status condition

| Interface Change | Priority | Automation |
|---|---|---|
| IC-1, IC-2 | Critical | Automated unit and envtest |

##### Preconditions

- A BMaaS instance fixture uses the existing condition fields and can be advanced through the four approved stages.
- The operator, feedback path, and fulfillment status projection are exercised with the same condition type/status/reason/message contract used in production.

##### Execution

- Owner/tier: bare-metal-fulfillment-operator and fulfillment-service; unit plus envtest.
- Location/command: proposed co-located operator and fulfillment controller tests; run the affected component's focused Go tests, then `make test` in each affected component.
- Dependencies: Kubernetes API and database are mocked or envtest-backed; no Metal3, Ironic, BMC, or real provisioning job is required.

##### Steps

1. Set the fixture to each approved non-terminal stage, including a transition where more than one prerequisite condition is already true.
2. Reconcile the operator and process the status through the existing feedback path.
3. Read the existing user-facing status condition and its `reason` and `message` fields.

##### Expected Results

- The projected condition identifies the approved current stage and contains the stage-specific user-facing status described by the approved design.
- The projection uses the existing condition fields and preserves tenant-scoped status ownership; no new schema field is required.
- A later stage is not replaced by an earlier condition merely because condition update order differs.

#### TC-FR1-02: Render staged progress from the existing API response

| Interface Change | Priority | Automation |
|---|---|---|
| IC-4 | High | Automated UI unit/component test |

##### Preconditions

- React Testing Library fixtures provide an API response for each approved stage and for a terminal failure.
- The detail view is rendered as a read-only view with no mutation handlers.

##### Execution

- Owner/tier: osac-ui; Vitest and React Testing Library.
- Location/command: proposed tests co-located with `BareMetalDetails`; run `pnpm test` from `osac-ui/`.
- Dependencies: API responses are mocked; no browser cluster or provisioning backend is required.

##### Steps

1. Render the detail view with each staged API response.
2. Query the accessible stage/status text and the condition detail exposed to the user.
3. Attempt the available view interactions and record all network calls made by the component.

##### Expected Results

- The current approved stage and its user-facing condition detail are exposed for every response.
- The view remains read-only and makes no create, update, retry, or delete request.
- Assertions do not depend on an unapproved visual choice such as exact layout, color, icon, or animation.

### FR-2: The approved four-stage model is derived from conditions

#### TC-FR2-01: Derive the furthest advanced stage independently of condition order

| Interface Change | Priority | Automation |
|---|---|---|
| IC-2, IC-6 | Critical | Automated operator unit test |

##### Preconditions

- The approved stage order and condition-to-stage mapping are encoded as test fixtures from the design.
- The fixture can present the same set of conditions in every permutation, including a failure condition and incomplete prerequisites.

##### Execution

- Owner/tier: bare-metal-fulfillment-operator; unit test in the controller/API package.
- Location/command: proposed co-located derivation tests; run `make test` from `bare-metal-fulfillment-operator/`.
- Dependencies: pure in-memory condition fixtures; no Kubernetes or provider dependency.

##### Steps

1. For every mapped condition combination in the approved contract, derive the stage.
2. Repeat each combination with condition order permuted.
3. Exercise incomplete, simultaneous, and terminal-failure combinations.

##### Expected Results

- Each combination has one explicit approved outcome; no input is silently treated as `Ready` by a default branch.
- The result is the furthest advanced approved stage represented by the conditions, independent of list order.
- A terminal failure remains associated with its approved phase and is not hidden by a later success condition.

#### TC-FR2-02: Handle no-work networking and terminal transitions

| Interface Change | Priority | Automation |
|---|---|---|
| IC-2, IC-6 | Medium | Automated unit and envtest |

##### Preconditions

- Fixtures represent both an instance with network setup work and an instance for which network setup is not requested.
- The approved Ready semantics and terminal transition rules are loaded from the design, rather than from the current implementation.

##### Execution

- Owner/tier: bare-metal-fulfillment-operator and fulfillment-service; unit plus envtest.
- Location/command: proposed controller/status tests; run focused Go tests and `make test` in the affected components.
- Dependencies: Kubernetes API and persistence are mocked or envtest-backed; provider operations are not required.

##### Steps

1. Advance a no-network instance through allocation and provisioning to the approved terminal state.
2. Advance a networked instance through network setup to the same terminal state.
3. Repeat with a failure at each applicable stage.

##### Expected Results

- Absence of optional network conditions does not create a false failure or require an inapplicable stage.
- The two valid paths converge on the same approved terminal semantics when their required work succeeds.
- Failures stop at the phase where they occur and retain the approved phase-specific message.

### FR-3: The active detail view refreshes automatically

#### TC-FR3-01: Poll while active and stop after a terminal outcome

| Interface Change | Priority | Automation |
|---|---|---|
| IC-4 | Critical | Automated UI unit/component test |

##### Preconditions

- The API query is controllable and returns a non-terminal response followed by a terminal success or failure response.
- Fake timers are enabled so elapsed polling time is deterministic.

##### Execution

- Owner/tier: osac-ui; Vitest and React Testing Library.
- Location/command: proposed tests co-located with the detail query/view; run `pnpm test` from `osac-ui/`.
- Dependencies: query function is mocked; no live API or browser cluster is required.

##### Steps

1. Render the view with a non-terminal response and advance fake time through successive approved polling intervals.
2. Change the mocked response to terminal success and advance time again.
3. Repeat with terminal failure and unmount/remount the view around the transition.

##### Expected Results

- While the instance is non-terminal, the query refreshes at the approved bounded interval.
- The view reflects the next API result without a user-initiated reload.
- Polling stops after either terminal success or terminal failure, and unmounting leaves no active timer or subscription.
- The test asserts the approved timing bound; it does not preserve the current global 10-second interval as a requirement.

### FR-4: Terminal outcomes remain viewable for the record lifetime

#### TC-FR4-01: Preserve terminal success after the source CR disappears

| Interface Change | Priority | Automation |
|---|---|---|
| — | High | Proposed automated component integration test |

##### Preconditions

- A tenant-scoped BMaaS record and its source CR exist in an isolated environment.
- The record has reached the approved terminal Ready state and its status has been persisted.

##### Execution

- Owner/tier: fulfillment-service with feedback integration; proposed component integration test.
- Location/command: proposed test under the fulfillment controller integration-test area; run the component's focused integration command after the implementation supplies the harness.
- Dependencies: real persistence and Kubernetes API; provider provisioning is mocked. The test must use bounded status waits.

##### Steps

1. Drive the record to terminal success and wait for the persisted API status.
2. Delete the source CR while retaining the fulfillment record.
3. Read the record through the existing API and refresh the detail view.

##### Expected Results

- The persisted record remains readable for the record's approved lifetime.
- The terminal Ready outcome, stage, and associated condition detail do not regress merely because the source CR is gone.
- No new source CR is created by the read-only status view.

#### TC-FR4-02: Preserve terminal failure and its message after the source CR disappears

| Interface Change | Priority | Automation |
|---|---|---|
| — | High | Proposed automated component integration test |

##### Preconditions

- A tenant-scoped BMaaS record has reached each representative approved terminal failure through the existing status path.
- Persistence and API reads are available after source-CR deletion.

##### Execution

- Owner/tier: fulfillment-service with feedback integration; proposed component integration test.
- Location/command: proposed companion to `TC-FR4-01`; run the focused component integration command with mocked provider operations.
- Dependencies: real persistence and Kubernetes API; no real hardware provider.

##### Steps

1. Drive the record to terminal failure at each applicable phase.
2. Record the API-visible stage, reason, and curated message.
3. Delete the source CR and read the record again through the API and detail view.

##### Expected Results

- The failure remains terminal and associated with the same phase.
- The exact curated message remains stable after source-CR deletion and refresh.
- The view does not offer a retry or expose the deleted CR's raw provider error.

### FR-5: Failures use curated phase-specific messages

#### TC-FR5-01: Map every approved failure reason to its exact user message

| Interface Change | Priority | Automation |
|---|---|---|
| IC-2, IC-5 | Critical | Automated unit test |

##### Preconditions

- The failure fixture can set each approved phase/reason pair on the existing condition.
- The expected messages are taken verbatim from the approved design.

##### Execution

- Owner/tier: fulfillment-service and operator status projection; proposed co-located unit tests.
- Location/command: affected controller/status packages; run the focused Go tests and the component's `make test`.
- Dependencies: in-memory conditions and status projection; no provider or database dependency.

##### Steps

1. Apply each phase/reason pair in the table below.
2. Project the condition through the approved operator-to-fulfillment path.
3. Compare the user-visible message and terminal phase with the expected values.

##### Expected Results

| Phase | Reason | Exact user-visible message |
|---|---|---|
| Host Allocation | `NoMatchingHosts` | `No bare metal host matched the requested profile.` |
| Host Allocation | `HostAllocationFailed` | `Host allocation failed.` |
| Provisioning | `ProvisionJobFailed` | `OS installation and configuration did not complete; the provisioning job failed.` |
| Network Setup | `NetworkAttachmentFailed` | `Network attachment did not complete.` |
| Network Setup | `NetworkHandoffFailed` | `Network handoff (reboot) did not complete.` |
| Network Setup | `IPDiscoveryFailed` | `IP address discovery did not complete.` |
| Ready | `ReadyTimeout` | `The instance did not reach its powered-on ready state.` |

- Each reason maps to exactly the message in the table and to its approved phase.
- No raw provider exception, internal object name, credential, or unapproved retry instruction appears in the user-visible message.
- The fallback mapping for an unrecognized provider failure is not specified in the published sources and remains an implementation-review gap; no test assertion is introduced for it until the approved mapping is confirmed.

#### TC-FR5-02: Present a terminal failure without a retry action or raw error

| Interface Change | Priority | Automation |
|---|---|---|
| IC-4, IC-5 | High | Automated UI unit/component test |

##### Preconditions

- The UI receives each curated failure response from `TC-FR5-01`, including the phase, reason, and message.
- A raw provider-error field is included in the fixture only to verify that it is not rendered.

##### Execution

- Owner/tier: osac-ui; Vitest and React Testing Library.
- Location/command: proposed failure-state tests co-located with `BareMetalDetails`; run `pnpm test` from `osac-ui/`.
- Dependencies: mocked API response; no live provider or browser cluster.

##### Steps

1. Render the detail view for each curated failure response.
2. Inspect the accessible failed-stage text and displayed message.
3. Inspect rendered controls and captured network calls.

##### Expected Results

- The failed phase and exact curated message are displayed.
- The raw provider error is not displayed.
- No retry or mutation action is offered by the approved read-only view, and rendering causes no mutation request.

### NFR-1: Feedback keeps API-visible status fresh

#### TC-NFR1-01: Propagate a status transition through Signal within the approved freshness bound

| Interface Change | Priority | Automation |
|---|---|---|
| IC-3 | Critical | Proposed automated contract/integration test |

##### Preconditions

- The feedback controller watches the status transition and uses the existing Signal RPC path.
- The test has a monotonic clock and bounded polling observer for the persisted fulfillment record.

##### Execution

- Owner/tier: osac-operator feedback controller and fulfillment-service; proposed cross-component contract test, with an isolated fake fulfillment endpoint or Kind deployment.
- Location/command: proposed test under the affected controller/integration area; run the focused feedback tests and the component integration command.
- Dependencies: real controller event handling and persistence; external provisioning is mocked. If the shared environment cannot provide deterministic timing, isolate the Signal RPC and test event-to-persistence propagation separately.

##### Steps

1. Change a source CR condition from one approved stage to the next.
2. Wait for the feedback controller to issue Signal and for the fulfillment record to change.
3. Measure monotonic time from the source status transition to the API-visible update.

##### Expected Results

- The API-visible stage and condition update is observed within the approved freshness bound.
- The existing Signal path is used; no polling-only fallback is required for normal propagation.
- Duplicate status events do not create conflicting or stale terminal projections.

The published sources describe this as a single-digit-seconds freshness target but do not state a numeric threshold. The implementation/test owner must confirm the numeric bound before this case can be scored; no arbitrary threshold is introduced here.

### NFR-2: The progress surface is consistent, readable, and read-only

#### TC-NFR2-01: Keep semantic state and controls consistent across updates

| Interface Change | Priority | Automation |
|---|---|---|
| IC-4 | Medium | Automated UI unit/component test |

##### Preconditions

- The same detail view instance receives sequential API responses for all approved stages and then a terminal outcome.
- Fixtures include condition detail and any raw/internal fields that must remain hidden.

##### Execution

- Owner/tier: osac-ui; Vitest and React Testing Library.
- Location/command: proposed co-located semantic-state tests; run `pnpm test` from `osac-ui/`.
- Dependencies: mocked API responses and deterministic query timers; no live cluster.

##### Steps

1. Render the initial stage and record the accessible state and available controls.
2. Apply each subsequent stage response without remounting the view.
3. Apply terminal success and terminal failure responses.

##### Expected Results

- The accessible current-stage state and condition text change to match each response without stale text from the preceding stage.
- The view remains read-only throughout and has no mutation or retry control.
- The semantic assertions remain valid regardless of deferred layout, color, icon, or animation choices.

The exact canonical wording for `NFR-2` is not declared in the PRD; this case covers only the observable read-only/consistency behavior supported by the approved design and records the wording gap for review.

### NFR-3: The condition contract remains stable and exhaustive

#### TC-NFR3-01: Verify compatibility with the existing schema and exhaustive interpretation

| Interface Change | Priority | Automation |
|---|---|---|
| IC-1, IC-6 | Low | Proposed automated compatibility check plus unit test |

##### Preconditions

- A baseline revision of the published API/proto/CRD descriptors is available for comparison.
- The approved condition mapping fixture enumerates every condition/status combination accepted by the design.

##### Execution

- Owner/tier: proto/API owners and bare-metal-fulfillment-operator; proposed repository compatibility check and co-located derivation test.
- Location/command: proposed check in the affected component validation; run the existing proto/CRD validation and `make test` from `bare-metal-fulfillment-operator/`. The exact baseline comparison command must be selected with the implementation owner.
- Dependencies: generated artifacts are compared to the approved baseline; no external provider is required.

##### Steps

1. Compare the generated proto/API and CRD field sets with the approved baseline.
2. Compile and run the condition derivation tests against every enumerated input.
3. Verify that existing clients can deserialize the status condition containing stage `reason` and `message` values.

##### Expected Results

- No new proto field, CRD field, or API schema property is required for provisioning progress.
- Every approved condition combination has an explicit derivation result, and unsupported combinations fail according to the approved contract rather than silently becoming Ready.
- Existing clients continue to read the condition type, status, reason, and message without a compatibility change.

The repository has no dedicated current test for this exact no-schema-change assertion; the compatibility command and baseline source must be finalized before execution.

## Gaps

### Requirement Coverage Gaps

- All eight preserved requirement IDs have at least one behavioral case, but the PRD does not provide canonical FR/NFR wording. `FR-1`–`FR-5` and `NFR-1`–`NFR-3` descriptions must be confirmed against the approved design during review.
- `NFR-1` has no numeric freshness threshold in the published sources. The plan deliberately does not invent one; the test cannot be scored until the bound is fixed.
- `NFR-2` has no independently stated canonical wording. The plan covers only the approved design's observable read-only, semantic consistency, and update behavior.
- `FR-4` says “record lifetime,” but the published sources do not define the retention/archive boundary. The test covers persistence while the record remains within that approved lifetime; retention policy itself remains out of scope.

### Interface Change Coverage Gaps

- All six interface changes have test coverage. `IC-3` freshness and `IC-6` exhaustive interpretation require proposed cross-component or compatibility harnesses because the current repository does not expose dedicated tests for those contracts.
- The current implementation does not yet provide the approved operator derivation helper, fixed failure vocabulary, or staged UI behavior. Those are implementation gaps recorded in `01-context.md`, not alternate expected results for this plan.
- The current proto `READY` comment describes a coarser availability meaning than the approved powered-on Ready semantics. The plan follows the approved design and requires the implementation owner to reconcile the source comment/contract before execution; it does not treat the current comment as a second valid behavior.
- Existing BMaaS E2E coverage waits for CR lifecycle states but does not assert staged API conditions. New staged assertions should be added under `tests/e2e/bmaas/` only if the component integration cases cannot provide the required cross-service evidence.

## Summary

| Metric | Count |
|---|---:|
| Total test cases | 12 |
| Critical | 5 |
| High | 4 |
| Medium | 2 |
| Low | 1 |
| Automated | 12 |
| Manual | 0 |
| Requirements covered | 8 / 8 |
| Interface changes covered | 6 / 6 |
| Cases requiring proposed component-integration or compatibility harnesses | 4 |
