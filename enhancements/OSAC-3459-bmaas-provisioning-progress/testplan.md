# OSAC-3459 Test Plan

## Scope and provenance

This is the test-plan-only regeneration for `/design:draft`.

Authoritative inputs inspected:

- `.artifacts/design/OSAC-3459/01-context.md`
- `enhancement-proposals/enhancements/OSAC-3459-bmaas-provisioning-progress/prd.md`
- `enhancement-proposals/enhancements/OSAC-3459-bmaas-provisioning-progress/design.md`
- `AGENTS.md` and the applicable instructions for `bare-metal-fulfillment-operator/`, `fulfillment-service/`, `osac-operator/`, `osac-ui/`, `enhancement-proposals/`, and `proto/`
- `docs/ARCHITECTURE.md`, `docs/CONVENTIONS.md`, and the BMaaS/component sections of `docs/INTEGRATION-TESTING.md`
- Read-only Jira context for OSAC-3459, used only to identify stale or superseded expectations

The approved PRD does not define canonical `FR-*` or `NFR-*` identifiers. The `PRD-*` identifiers below are local traceability IDs, not additions to the approved requirements. The approved design's `IC-1` through `IC-6` identifiers are retained. Design references to `FR-1` through `FR-5` and `NFR-1` through `NFR-3` are recorded as unresolved source-label gaps where their definitions are absent from the approved PRD.

No test, build, generation, implementation, Jira write, commit, push, or publication was performed.

## Requirement and interface assertion inventory

The assertions were extracted separately from the approved PRD and design, then reconciled below. Every assertion has a test case or an explicit gap.

### Approved PRD assertions

| ID | Source | Observable contract | Coverage |
|---|---|---|---|
| PRD-1 | PRD scope and user stories | The detail view exposes the current phase, state, and human-readable message; states include pending, running, succeeded, and failed. | TC-PRD-1, TC-PRD-2 |
| PRD-2 | PRD scope, assumptions | The user-facing sequence is Host Allocation, Provisioning, Network Setup, Ready; internal hardware, OS, configuration, and verification work is folded into Provisioning. Earlier phases remain done and later phases remain pending while progress advances. | TC-PRD-1, TC-PRD-3 |
| PRD-3 | PRD scope and success criteria | Nonterminal detail data refreshes automatically at approximately five seconds, stops at Ready or Failed, and exposes backend progress to the user within the stated single-digit-second bound. | TC-PRD-4, GAP-EXEC-1 |
| PRD-4 | PRD scope and success criteria | The terminal outcome remains visible for the life of the instance record until archival; success identifies all phases as complete, and failure identifies the failed phase and message. No ordered history or per-phase duration is required. | TC-PRD-5, GAP-EXEC-2 |
| PRD-5 | PRD scope, consistency requirement | The reason/message shape follows the existing coarse condition pattern used by CaaS and VMaaS without changing the resource schema. | TC-PRD-6, GAP-REQ-1 |
| PRD-6 | PRD scope and failure behavior | Failure text is curated for users and does not expose raw provider, job, or internal error values. | TC-PRD-7 |
| PRD-7 | Out-of-scope and user-story boundaries | The view is read-only for this feature: no retry, remediation, per-phase logs, deprovisioning progress, or aggregate cross-tenant progress is introduced. | TC-PRD-8, TC-PRD-9 |

### Approved design assertions and interfaces

| ID | Source | Observable contract | Coverage |
|---|---|---|---|
| IC-1 | Design §5 | Existing `PROVISIONED` and terminal `READY` conditions carry staged `reason`/`message`; no proto, CRD, or status-schema fields are added. | TC-PRD-6, TC-PRD-9 |
| IC-2 | Design §5 | Operator-owned `DeriveProvisioningProgress` and fulfillment `syncStatus` derive a deterministic phase from existing conditions, use curated messages, set `PROVISIONED` at provisioning completion, set `READY` at readiness, and apply the message sanitizer. | TC-PRD-1, TC-PRD-2, TC-PRD-3, TC-PRD-7 |
| IC-3 | Design §5 | Existing feedback `Signal` behavior observes status changes, including reason/message changes, so the fulfillment record receives fresh progress. | TC-PRD-4, GAP-EXEC-1 |
| IC-4 | Design §5 | The UI reads the existing condition values, presents the progress view, refreshes while nonterminal, and stops refreshing at a terminal result. | TC-PRD-1, TC-PRD-4, TC-PRD-8 |
| IC-5 | Design §5 | The failure vocabulary is deterministic and maps the seven named failure cases to the exact approved user-facing messages. | TC-PRD-7 |
| IC-6 | Design §5 | The mapping test is exhaustive over all `HostCondition` constants. | TC-PRD-3, GAP-REQ-2 |

### Design-only assertions without a separate PRD counterpart

| ID | Source | Observable contract | Coverage |
|---|---|---|---|
| DA-1 | Design §4–§5 | Stage derivation is independent of condition arrival order and reports the furthest applicable stage without exposing internal substeps. | TC-PRD-2, TC-PRD-3 |
| DA-2 | Design §4–§5 | No-network work marked `Skipped` is treated as complete for the relevant stage. | TC-PRD-2 |
| DA-3 | Design §4–§5 | Provisioning and network completion are distinct: `PROVISIONED=True` is not asserted before the design's provisioning completion point, and `READY=True` follows powered-on readiness. | TC-PRD-1, TC-PRD-3 |
| DA-4 | Design §4–§5 | Retries and overlapping internal work do not create additional user-visible phases. | TC-PRD-2, GAP-REQ-3 |
| DA-5 | Design §5 | The seven approved failure mappings are exact, and unknown/raw values are not passed through to the user. | TC-PRD-7 |
| DA-6 | Design §5 | A reason/message-only status change satisfies the existing feedback update predicate. | TC-PRD-4, GAP-EXEC-1 |
| DA-7 | Design §5 | Terminal condition values remain available through fulfillment persistence until the instance record is archived. | TC-PRD-5, GAP-EXEC-2 |
| DA-8 | Design §5 and embedded test plan | Existing consumers remain compatible because the implementation uses existing condition fields and preserves unrelated condition behavior. | TC-PRD-6, TC-PRD-9, GAP-REQ-4 |

## Test cases

### TC-PRD-1 — Happy-path phase derivation and detail contract

**Covers:** PRD-1, PRD-2, IC-1, IC-2, IC-4, DA-3.

**Tier and location:** Unit tests in `bare-metal-fulfillment-operator/` and `fulfillment-service/`; UI component test in `osac-ui/`.

**Preconditions:** A fixture can represent the approved condition sequence: no allocation, allocation, provisioning-template completion, network attachment/handoff/IP discovery, and powered-on readiness. The UI fixture contains the corresponding existing `PROVISIONED` and `READY` condition values.

**Steps:**

1. Evaluate the derivation with no allocation condition.
2. Add allocation and then provisioning conditions.
3. Add network conditions one at a time, including a no-network `Skipped` result.
4. Add the readiness condition.
5. Render the detail view after each condition update.

**Expected results:**

- No allocation renders Host Allocation as pending or running according to the condition state, with a human-readable message.
- Allocation renders Host Allocation succeeded while Provisioning, Network Setup, and Ready remain pending.
- Provisioning renders Provisioning as the active or completed user-facing phase; internal hardware, OS, configuration, and verification substeps are not separate phases.
- Network attachment, handoff, and IP discovery progress within Network Setup; the phase does not advance to Ready until the approved readiness condition is true.
- A no-network `Skipped` result is treated as complete for Network Setup.
- The terminal result renders all four user-facing phases as succeeded and exposes the terminal READY condition.
- No new proto or CRD field is required to represent any displayed value.

### TC-PRD-2 — Order independence, retries, overlap, and folded internal work

**Covers:** PRD-2, IC-2, DA-1, DA-2, DA-4.

**Tier and location:** Unit tests in `bare-metal-fulfillment-operator/` and `fulfillment-service/`.

**Preconditions:** Equivalent condition sets can be supplied in different insertion orders, with retry conditions and overlapping internal jobs.

**Steps:**

1. Evaluate equivalent condition sets in several arrival orders.
2. Repeat a failed or in-progress internal operation and add overlapping provisioning/network conditions.
3. Evaluate a network stage with one or more `Skipped` no-work conditions.

**Expected results:**

- Equivalent condition sets produce the same user-facing phase, state, reason, and message regardless of arrival order.
- The reported stage is the furthest applicable approved stage, not the last condition received.
- Retries and overlapping internal jobs do not add phases, history rows, or user-visible substeps.
- `Skipped` no-work conditions satisfy their stage completion rule.
- The result does not expose backend job names, condition ordering, or provider-specific implementation details.

### TC-PRD-3 — Exhaustive condition mapping and lifecycle boundaries

**Covers:** PRD-2, IC-2, IC-6, DA-1, DA-3.

**Tier and location:** Unit tests co-located with the operator condition mapping and fulfillment status synchronization.

**Preconditions:** The test enumerates every current `HostCondition` constant from the source package and includes true, false, unknown, and omitted conditions.

**Steps:**

1. Run the derivation table test over every enumerated `HostCondition` constant.
2. Exercise the transition from provisioning-template completion through network completion to readiness.
3. Exercise a condition removal or false transition at each lifecycle boundary.

**Expected results:**

- Every current `HostCondition` constant has an explicit mapping outcome: user-visible stage, terminal/failure handling, or an explicitly documented non-progress condition.
- No enumerated condition silently falls through to an unclassified result.
- `PROVISIONED=True` occurs at the approved provisioning-completion point and not merely at an earlier template condition when the design requires later network completion.
- `READY=True` occurs only at powered-on readiness; an intermediate provisioned-but-not-ready state remains visible.
- A false or missing condition does not create a terminal success result.

### TC-PRD-4 — Refresh, feedback signal, and freshness boundary

**Covers:** PRD-3, IC-3, IC-4, DA-6.

**Tier and location:** UI unit/component test plus cross-component integration test for operator feedback, fulfillment persistence, and API reads.

**Preconditions:** A fake clock or request spy is available for the UI; the integration environment includes the BM operator, `osac-operator` feedback controller, fulfillment service, and its persistence store.

**Steps:**

1. Render a nonterminal instance and advance the clock through successive refresh intervals.
2. Change only the condition reason/message in the operator status.
3. Observe the feedback controller and fulfillment API result.
4. Mark the instance Ready, then advance the clock through another interval.
5. Repeat with a Failed terminal result.

**Expected results:**

- The nonterminal UI issues refreshes at the configured approximately five-second interval, within an explicitly asserted test tolerance.
- A reason/message-only status change passes the existing status-change predicate and produces a fresh fulfillment-visible value.
- The UI displays the updated phase/message without a manual page reload.
- Refreshing stops after Ready and after Failed; no further interval request is scheduled for either terminal state.
- The end-to-end condition-to-API observation is measured from the operator condition update to the fulfillment/API value; a component-local interval is not accepted as evidence for the end-to-end bound.

### TC-PRD-5 — Terminal persistence and archive boundary

**Covers:** PRD-4, IC-3, IC-4, DA-7.

**Tier and location:** Cross-component integration test covering fulfillment persistence and API retrieval.

**Preconditions:** The environment can retain an instance record, retrieve it after the operator resource is no longer changing, and exercise the defined archive boundary.

**Steps:**

1. Persist a successful terminal result and retrieve it repeatedly.
2. Persist a failed terminal result with its phase and curated message and retrieve it repeatedly.
3. Remove or stop updating the source resource without archiving the instance record.
4. Archive the instance record.

**Expected results:**

- The successful result continues to identify all four phases as succeeded until archival.
- The failed result continues to identify the failed phase and curated message until archival.
- Source-resource disappearance or inactivity does not erase the terminal result before archival.
- Retrieval after archival follows the existing archive contract; no new unapproved historical timeline or duration data is required.

### TC-PRD-6 — Interface compatibility and condition message shape

**Covers:** PRD-5, IC-1, IC-2, DA-8.

**Tier and location:** Unit tests in fulfillment synchronization and compatibility/schema inspection across `proto/`, the operator API, fulfillment, and UI clients.

**Preconditions:** Existing condition fields and unrelated condition consumers are represented in fixtures.

**Steps:**

1. Synchronize staged reason/message values through fulfillment.
2. Inspect the generated and source proto/CRD/API definitions for added progress fields.
3. Exercise unrelated conditions and existing sanitization behavior.

**Expected results:**

- Progress is represented using existing condition fields with the approved coarse reason/message shape.
- No progress-specific proto, CRD, or status-schema field is added.
- Existing unrelated condition values remain available to their current consumers.
- The message sanitizer removes or replaces internal values according to the approved user-facing vocabulary.
- The design-referenced CaaS/VMaaS consistency claim remains a source gap until the corresponding approved contracts are named and inspected; this test does not invent a new cross-product schema.

### TC-PRD-7 — Curated failure vocabulary and raw-value sanitization

**Covers:** PRD-6, IC-2, IC-5, DA-5.

**Tier and location:** Unit tests in the operator derivation and fulfillment sanitizer.

**Preconditions:** Inputs can represent each named approved failure reason and an unknown provider/job error containing internal identifiers.

**Steps:**

1. Exercise each approved failure mapping.
2. Exercise an unknown reason and a raw provider/job error.
3. Exercise failure while each user-facing phase is active.

**Expected results:**

- `NoMatchingHosts` maps to `No bare metal host matched the requested profile.`
- `HostAllocationFailed` maps to `Host allocation failed.`
- `ProvisionJobFailed` maps to `OS installation and configuration did not complete; the provisioning job failed.`
- Network attachment failure maps to `Network attachment did not complete.`
- Network handoff failure maps to `Network handoff (reboot) did not complete.`
- IP discovery failure maps to `IP address discovery did not complete.`
- `ReadyTimeout` maps to `The instance did not reach its powered-on ready state.`
- Each failure identifies the active user-facing phase and failed state.
- Unknown reasons, raw provider messages, job identifiers, host identifiers, and internal error text are not exposed in the user-facing message.

### TC-PRD-8 — Read-only UI boundary

**Covers:** PRD-7, IC-4.

**Tier and location:** UI component test in `osac-ui/`.

**Preconditions:** The progress detail view is rendered for nonterminal, successful, and failed results.

**Steps:**

1. Inspect rendered controls and their event handlers for each state.
2. Attempt to activate every displayed progress control in the test harness.

**Expected results:**

- The view exposes status and message information only.
- No retry, remediation, deprovisioning-progress, per-phase-log, or aggregate-list control is rendered by this feature.
- No progress control performs a mutation or creates a cross-tenant query.

### TC-PRD-9 — Tenant and schema boundary regression

**Covers:** PRD-7, IC-1, DA-8.

**Tier and location:** Existing authorization/tenant unit coverage and schema inspection; no new test infrastructure is claimed by this plan.

**Preconditions:** A tenant-scoped instance fixture and an unrelated tenant fixture exist.

**Steps:**

1. Request progress for an instance visible to the caller.
2. Request progress for an instance owned by another tenant.
3. Compare the API/resource schema before and after the planned interface implementation.

**Expected results:**

- The caller receives only progress for the authorized tenant-scoped instance.
- The caller cannot use progress retrieval to enumerate another tenant's instance or aggregate progress.
- Tenant and owner-reference isolation annotations remain unchanged where applicable.
- No new schema field is required for progress.

## Execution evidence and readiness

The following is a plan, not execution evidence. No command in this table was run during draft regeneration.

| Evidence ID | Cases | Tier/boundary | Test location | Command, workdir, prerequisites, and source | Dependencies | Readiness/gap |
|---|---|---|---|---|---|---|
| E-UNIT-OP | TC-PRD-1, TC-PRD-2, TC-PRD-3, TC-PRD-7 | Unit | `bare-metal-fulfillment-operator/` co-located controller/API tests | `make test`; workdir `bare-metal-fulfillment-operator/`; command documented by the component instructions; requires Go dependencies. | None beyond the repository checkout. | Planned and command-ready; not executed. Add the exhaustive mapping fixture if absent. |
| E-UNIT-FULFILLMENT | TC-PRD-1, TC-PRD-3, TC-PRD-6, TC-PRD-7 | Unit | `fulfillment-service/internal/controllers/baremetalinstance/` | `ginkgo run -r internal`; workdir `fulfillment-service/`; command documented by the component instructions; requires Go dependencies and package fixtures. | Fulfillment source and existing reconciliation tests. | Planned and command-ready; not executed. Existing tests reflect older synchronization behavior and need implementation-aligned additions. |
| E-UNIT-UI | TC-PRD-1, TC-PRD-4, TC-PRD-8 | Unit/component | `osac-ui/libs/ui-components/src/components/BareMetalInstance/` and related API hook tests | `pnpm test`; workdir `osac-ui/`; command documented by `osac-ui/AGENTS.md`; requires the prepared pnpm dependencies. | Existing UI test runner and fake-query/fake-clock support. | Planned and command-ready; not executed. The inspected UI area has no progress-specific test coverage. |
| E-INTEGRATION-FEEDBACK | TC-PRD-4 | Integration: operator → feedback controller → fulfillment/API | Cross-component BMaaS integration harness | Use the documented component/integration tier setup from `docs/INTEGRATION-TESTING.md`; an exact single command for this full freshness path was not established from the inspected instructions. | Running operator, `osac-operator`, fulfillment service, persistence, and API together. | Gap: missing execution infrastructure for the complete condition-update-to-API measurement. A component refresh interval is not sufficient evidence. |
| E-INTEGRATION-PERSISTENCE | TC-PRD-5 | Integration: persistence and archive boundary | Fulfillment persistence/API integration harness | Use the fulfillment integration setup documented by the component and integration-testing instructions; archive-boundary command is not established in the inspected sources. | Database, fulfillment service, and defined archive lifecycle. | Gap: archive semantics and a repeatable source-removal/persistence fixture are not identified. |
| E-E2E-UI-API | TC-PRD-1, TC-PRD-4, TC-PRD-5, TC-PRD-8, TC-PRD-9 | E2E: API/resource/UI | `tests/e2e/` plus `osac-ui/` browser/component coverage | The repository documents E2E as the cross-component tier, but no existing OSAC-3459 scenario or execution command was asserted as present during this phase. | Provisioned BMaaS environment, tenant fixtures, operator/feedback/fulfillment/API, and browser/UI environment. | Gap: new scenario and harness wiring are required; not execution-ready. |
| E-PROVIDER | TC-PRD-1, TC-PRD-3, TC-PRD-7 | Manual/contract boundary | External AAP/Metal3/Ironic/BMC/hardware | No provider or hardware command is claimed. The integration-testing guidance identifies these as outside current local envtest coverage. | Real provider and hardware infrastructure. | Gap: missing external-provider execution infrastructure; qualify through the documented follow-up path before claiming coverage. |

## Gaps and classifications

| ID | Classification | Gap | Impact |
|---|---|---|---|
| GAP-REQ-1 | Unspecified behavior | The PRD requires CaaS/VMaaS consistency but names no authoritative condition contract or exact fields to compare. | The shape can be tested for internal consistency, but cross-product equivalence cannot be asserted yet. |
| GAP-REQ-2 | Unspecified behavior | The design requires exhaustive mapping over all `HostCondition` constants but does not define the expected user-visible outcome for every existing constant, including several failure/power/template reasons. | The exhaustive test needs an approved mapping table or explicit non-progress classifications. |
| GAP-REQ-3 | Unspecified behavior | Retry, overlapping work, `Skipped` handling, no-work phases, and the exact `PROVISIONED=True` transition are described at design level but not fully enumerated for every existing condition combination. | Parameterized unit cases can expose drift, but unresolved combinations remain contract gaps. |
| GAP-REQ-4 | Implementation drift | Current fulfillment synchronization and UI behavior still reflect the pre-change implementation, including old `PROVISIONED` timing/message behavior and no dedicated progress view/interval. | This is implementation work, not a reason to reinterpret the approved requirement. |
| GAP-REQ-5 | Unspecified behavior | Design-referenced `FR-1`–`FR-5` and `NFR-1`–`NFR-3` have no definitions in the approved PRD. | Traceability is complete only against local PRD IDs and IC IDs; canonical label coverage remains unresolved. |
| GAP-EXEC-1 | Missing execution infrastructure | A repeatable full-path measurement from operator status/reason change through feedback `Signal`, fulfillment persistence, and API/UI observation is not identified. | The approximately five-second UI interval and single-digit end-to-end visibility promise cannot be verified by unit tests alone. |
| GAP-EXEC-2 | Missing execution infrastructure | A documented fixture for persistence after source-resource inactivity and through the archive boundary is not identified. | Terminal persistence readiness is planned but not verified. |
| GAP-EXEC-3 | Missing execution infrastructure | Existing local envtest/component tiers do not include real AAP/Metal3/Ironic/BMC/hardware providers. | Real provider failure vocabulary and timing remain unverified; no local test may claim that coverage. |
| GAP-SOURCE-1 | Stale Jira context | Read-only Jira text contains older timeline, aggregate, and schema expectations that are not present in the approved PRD/design. | Those items are excluded from this plan and must not be treated as implementation requirements. |
| GAP-UI-1 | Unspecified behavior | The design leaves visual/interaction details to a UI-focused design, including exact labels, accessibility semantics, and failure-state presentation. | UI structural and polling coverage is planned; pixel/accessibility assertions need the missing approved UI detail. |

## Preparation, correction, and recheck record

### Preparation

- Loaded the current context artifact and the approved PRD/design.
- Resolved the project draft override and the pinned `design-test-planning` skill.
- Inspected applicable component instructions and integration-testing guidance.
- Preserved the approved design as an unchanged copy in `03-design.md`.
- Identified the source-label issue before creating traceability IDs; no canonical PRD FR/NFR labels were invented.

### Internal correction

The first plan pass was corrected within this phase to:

1. Add a separate PRD/design assertion inventory, including design-only assertions and all six approved interface contracts.
2. Add explicit expected results for intermediate states, no-network `Skipped` handling, the `PROVISIONED`/`READY` boundary, exact failure strings, and refresh stop conditions.
3. Separate planned/command-ready unit evidence from unverified cross-component and provider evidence.
4. Classify implementation drift, unspecified behavior, stale Jira expectations, and missing execution infrastructure separately.
5. Preserve the approved design's byte identity by avoiding provenance-footer mutation of `03-design.md`.

### Recheck

Recheck criteria:

- Every `PRD-*`, `IC-*`, and `DA-*` assertion has a case or explicit gap.
- Every case has Preconditions, Steps, and explicit Expected results.
- Every execution row names a tier/boundary, location, command or an explicit command gap, dependencies, and readiness state.
- Async behavior names the trigger, observation endpoint, and bound; component-local polling is not treated as end-to-end timing evidence.
- No test execution is claimed.

The internal recheck found that a prose statement of coverage was not sufficient for review, so the plan was corrected with this explicit inventory cross-check:

| Source set | IDs checked | Case-backed result |
|---|---|---|
| PRD assertions | PRD-1 through PRD-7 | All seven have at least one named test case. |
| Approved interfaces | IC-1 through IC-6 | All six have at least one named test case; IC-3 also has an execution gap for the full feedback path. |
| Design-only assertions | DA-1 through DA-8 | All eight have at least one named test case; DA-6 and DA-7 also have execution gaps for cross-component persistence/freshness. |

Result: **PASS with flagged gaps**. The plan is suitable as a draft artifact for review, but it is not execution-ready for the full end-to-end, archive-boundary, or external-provider claims until the listed infrastructure and contract gaps are resolved.

## Summary

| Metric | Result |
|---|---:|
| Local PRD assertions | 7 |
| Approved interface contracts | 6 |
| Design-only assertions | 8 |
| Assertions with named case coverage | 21 |
| Test cases | 9 |
| Execution evidence rows | 7 |
| Remaining gaps | 10 |
| Tests run in this phase | 0 |

Overall readiness: **draft-ready for review; not implementation- or execution-ready for the unresolved contract and cross-component evidence gaps.**
