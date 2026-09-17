# E2E Test Plan — OSAC-4542

## Summary

This plan covers the deployed public Volume read journey requested by the local [QE] story: provision a standalone volume through the owning deployed path, read it through public gRPC, verify tenant isolation, and route REST and generic CLI checks to the harnesses that own those channels. The missing helpers and fixtures are implementable test work; test scoping still requires the unresolved harness ownership and provider contract, while execution requires the environment, credentials, and unsynchronized [DEV] dependencies.

The plan follows the actual local story files and the approved design. It does not treat local story dependencies as completed and does not duplicate the Kind component-integration realization assigned to Story 1.02.

## Reconciliation Corrections

This is a correction pass over the existing plan, not a new generation cycle.

| Existing plan treatment | Corrected treatment | Reason |
|---|---|---|
| Missing Volume, REST, admin-identity, and CLI helpers/fixtures were described alongside blockers | Classified as implementable test work, subject to the confirmed owner and provider contract | A missing helper alone does not block implementation. The test work can add wrappers, fixtures, and bounded polling once the external behavior is defined. |
| Missing provider, gateway, credentials, CLI version, and deployed identities were mixed with implementation status | Classified as execution prerequisites | These block running or evaluating the scenarios in an environment; they do not by themselves prevent writing the test work. |
| Unknown VMaaS/REST/CLI ownership was phrased as an existing assignment for REST and CLI | REST and CLI ownership are explicitly unresolved | The current artifacts identify Story 1.03 as the [QE] owner but do not identify a repository, harness, or QE owner for those channels. |
| Kind and deployed `TC-FR8-01` realizations were described together without a dedicated boundary record | Kept as two tier realizations of the same published case id | Story 1.02 owns the Kind component-integration realization; Story 1.03 owns the external deployed realization. The [QE] story must not duplicate Kind coverage. |
| The branch section named `main` as a PR target | Replaced with local-only, contributor-fork-only publication metadata and no PR target | This pilot must not establish or imply an upstream PR target. Existing PR #75 remains untouched. |

## Branch

- **Name:** `OSAC-4542-public-volume-e2e`
- **Local Base:** `pilot/OSAC-5320-builtin-4542-v1` (the current prepared branch; no branch operation is performed)

## Publication Metadata

- **Mode:** local pilot handoff evaluation only; no publication is performed by this plan.
- **Push policy:** any future authorized push must go only to the contributor fork. The current checkout's `origin` resolves to `osac-project/osac`, so it is not an approved push target; the contributor-fork URL must be resolved explicitly before any push.
- **PR target:** none. This pilot has no upstream PR target and must not create one.
- **Existing publication:** enhancement-proposals PR `#75` and its published test plan remain unchanged.

## Reference Suite

- **Primary path candidate:** `tests/e2e/vmaas/regression/test_compute_instance_api_fields.py`
- **Storage lifecycle reference:** `tests/e2e/storage/test_tenant_storage_lifecycle.py`
- **Why selected:** the VMaaS suite exercises a deployed user journey through `OsacCLI`, `GRPCClient`, `K8sClient`, and bounded polling. The storage suite supplies the closest resource-lifecycle pattern with unique names, explicit `try/finally` cleanup, and observable condition waits.
- **Patterns adopted:** pytest functions with typed fixtures, module `pytestmark = pytest.mark.regression`, session fixtures for environment access, unique resource names, `GRPCClient.call`/`call_unchecked`, bounded `poll_until` or resource-specific wait helpers, and cleanup in `finally`.
- **Ownership caveat:** repository guidance places E2E suites under `tests/e2e/` and says `osac-test-infra` owns infrastructure backends. The story and design name an external VMaaS suite. The final repository and owner remain a prerequisite.

## Test File Structure

### Suite Directory

The local candidate is `tests/e2e/storage/regression/` because the user journey is public storage Volume inventory. If the owning QE decision keeps the story in the external VMaaS suite, that external path replaces this candidate; it was intentionally not inspected and cannot be named here.

### Files to Create

| File | Purpose | Status |
|---|---|---|
| `tests/e2e/storage/regression/test_public_volume_reads.py` | Candidate local test file for the deployed public gRPC scenario and any locally owned REST check | Implementable test work after the owner/path decision |
| `tests/e2e/storage/conftest.py` | Extend only if the confirmed owner requires a local Volume provisioning, identity, or cleanup fixture; existing file has storage-controller gates but no Volume fixture | Implementable test work once the provider contract is defined |
| External VMaaS suite path | Candidate location named by the story/design | Planning blocker: repository, harness, and owner remain unknown |

No helper is an implementation blocker solely because it is absent. The plan uses existing shared clients where possible and identifies the wrappers, fixtures, and polling helpers that test work may add after the ownership and provider contracts are confirmed.

## Test Scenarios

### Consolidated Scenario C1: External deployed owner reads and isolates a provisioned Volume

- **Covers:** AC-1, AC-2, AC-4, AC-5
- **Source references:** `TC-FR4-01`; external realization of `TC-FR8-01`; Story 1.03 acceptance criteria 1, 2, 4, and 5
- **Block structure:** one pytest test function in the confirmed storage or VMaaS regression suite, marked `pytest.mark.regression`; no Kind-only marker or component-integration setup
- **Status:** The scenario is implementation-plannable. Execution is blocked by environment/credential/dependency prerequisites; implementation remains blocked only by the unresolved owning harness and provider contract.
- **Setup (given):**
  1. Run the confirmed external VMaaS or repository-owned deployed E2E environment preflight. Report provider, environment, and harness prerequisites separately from behavioral results.
  2. Obtain a tenant-A public client and a tenant-B public client. Existing local candidates are `jwt_grpc_tenant1` and `jwt_grpc_tenant2`; the external harness must confirm equivalent identities and scope.
  3. Add or obtain the standalone-volume provisioning fixture. The local repository has no Volume-specific creator, readiness waiter, or cleanup method; adding those helpers is test work. The exact private API operation, returned id, readiness signal, and delete operation must come from the owning harness before implementation is finalized.
- **Action (when):**
  1. Provision one standalone Volume through the existing deployed provider path and wait until the owner considers it readable.
  2. Call public `osac.public.v1.Volumes/List` and `osac.public.v1.Volumes/Get` as tenant A using `GRPCClient.call`.
  3. Call public `List` and `Get` as tenant B using the equivalent public client; use `GRPCClient.call_unchecked` for the expected `Get` error.
- **Validations (then):**
  1. [AC-1] The existing deployed path creates one standalone Volume and returns a stable id that the public API can read.
  2. [AC-1] Tenant A's public `List` includes the created id and public `Get` returns the same id.
  3. [AC-2] The response exposes the approved tenant-facing projection, including the expected specification/state fields, and omits backend, protocol, hub, vendor id, and vendor context fields.
  4. [AC-2] Tenant B's public `List` excludes tenant A's id.
  5. [AC-2] Tenant B's public `Get` returns gRPC `NotFound` without revealing existence.
  6. [AC-4] Provider, environment, and harness prerequisites are reported independently; an unavailable prerequisite is recorded as blocked and does not become executed behavioral coverage.
  7. [AC-5] The scenario uses the deployed provider boundary and public API only; it does not invoke the Kind component-integration path or server/unit test path.
- **Cleanup:** use the confirmed owner’s Volume deletion/teardown path in `finally`, then poll the observable removal condition. If the provider does not support deletion in this story, the owner must document a safe fixture cleanup strategy before implementation.

- **Implementation work:** add the local fixture/wrapper and bounded Volume readiness/cleanup polling if this repository owns the test.
- **Execution prerequisites:** deployed provider, configured storage, tenant credentials, external harness availability, and the unsynchronized [DEV] dependencies.
- **Genuine planning blockers:** owning repository/harness and the provider's Volume lifecycle contract.

The source test plan's `TC-FR8-01` explicitly names an `osac-dev` Kind environment, while decomposition also assigns an external realization to Story 1.03. This scenario follows the [QE] story's external boundary and treats the identifier's dual realization as a planning prerequisite, not as evidence that the Kind case is covered here.

### Standalone Scenario S1: Cloud Provider Admin reads across tenants

- **Covers:** AC-2, AC-4
- **Source reference:** `TC-FR4-02`
- **Block structure:** separate pytest function because the caller identity and authorization scope differ from tenant-A/tenant-B clients
- **Status:** The scenario is implementation-plannable. Execution requires a Cloud Provider Admin credential and a deployed multi-tenant environment; ownership of that fixture remains unresolved.
- **Setup (given):** provision visible Volumes in at least two tenants through the confirmed deployed path, or consume an equivalent owner fixture. Add a public Cloud Provider Admin fixture if this repository owns the test. Existing local fixtures expose tenant users and a private service-account client, but no public Cloud Provider Admin fixture.
- **Action (when):** call public `Volumes/List` as the Cloud Provider Admin, then call public `Volumes/Get` for one id from each tenant.
- **Validations (then):**
  1. [AC-2] List includes the visible Volume from each permitted tenant.
  2. [AC-2] Get returns the requested public Volume for each tenant.
  3. [AC-4] Missing admin identity or provider capability is reported as a blocked prerequisite, separate from a behavioral failure.
- **Cleanup:** owner fixture teardown for all created Volumes, with bounded removal polling.

- **Implementation work:** add the admin identity fixture and reuse the Volume fixture if the local suite owns this scenario.
- **Execution prerequisites:** public admin credentials, two-tenant provider data, and a deployed environment with the required authorization configuration.
- **Genuine planning blocker:** the owning harness and the identity contract are unresolved.

### Standalone Scenario S2: Deployed REST collection and item reads

- **Covers:** AC-3, AC-4
- **Source reference:** `TC-FR7-01`
- **Block structure:** separate deployed-channel test or the owning external REST harness; do not duplicate gRPC setup if the harness can share the provisioned fixture safely
- **Status:** Ownership unresolved; the scenario is implementable in the confirmed owning harness. No assignment elsewhere is claimed.
- **Setup (given):** a visible Volume exists; the REST gateway is deployed with public handlers; the confirmed owner supplies or adds an authenticated HTTP client/command, base URL, credentials, and response capture convention. No REST client helper or item-id-aware helper is present in the inspected local E2E infrastructure, which is test work rather than a blocker by itself.
- **Action (when):** send `GET /api/fulfillment/v1/volumes`, select a returned id, then send `GET /api/fulfillment/v1/volumes/{id}`.
- **Validations (then):**
  1. [AC-3] The collection response is HTTP 200 and contains `size`, `total`, and public Volume items.
  2. [AC-3] The item response is HTTP 200 and returns the selected public Volume.
  3. [AC-3] REST output omits the private routing fields.
  4. [AC-4] Missing gateway, credentials, or owner harness is reported as blocked rather than as a behavioral failure.
- **Cleanup:** reuse the confirmed Volume fixture; no REST mutation is expected.

- **Implementation work:** add an authenticated HTTP helper if the confirmed owner is local, or use the owner's existing helper.
- **Execution prerequisites:** deployed REST gateway, credentials, endpoint reachability, and a visible Volume.
- **Genuine planning blocker:** REST repository/harness ownership and evidence ownership are unresolved.

### Standalone Scenario S3: Manual generic CLI reflection reads

- **Covers:** AC-3, AC-4
- **Source reference:** `TC-FR7-02`
- **Block structure:** manual/deployed QE procedure, not an automated pytest scenario unless the owning harness confirms an item-id-capable CLI fixture
- **Status:** Ownership unresolved; the published plan marks this case manual. No assignment elsewhere is claimed.
- **Setup (given):** CLI binary and version, public endpoint, tenant credentials, reflection enabled, visible Volume id, structured-output capture, and owner are defined by QE. The local `OsacCLI.get` helper accepts only a resource string and does not document the required `get volume <id>` form; an item-aware helper may be added if the confirmed owner automates this case.
- **Action (when):** run `osac get volumes`, then `osac get volume <id>` with structured output.
- **Validations (then):**
  1. [AC-3] Generic reflection discovers the public Volume collection and lists only caller-visible items.
  2. [AC-3] Generic Get uses the immutable id and prints only public fields without a Volume-specific command implementation.
  3. [AC-4] CLI prerequisites and captured output are reported separately from behavioral pass/fail.
- **Cleanup:** none through the read-only CLI path; use the owner fixture's teardown.

- **Implementation work:** optional item-aware CLI wrapper and evidence helper if QE chooses to automate the manual case.
- **Execution prerequisites:** CLI binary/version, reflection, endpoint, credentials, visible Volume, and output-capture location.
- **Genuine planning blocker:** manual procedure and owning QE harness are unresolved.

## Scenario Consolidation

| Consolidated Scenario | Merged From | Validation Count | Rationale |
|---|---|---:|---|
| C1 | Story AC-1/2 external public-read path; `TC-FR4-01`; external realization of `TC-FR8-01` | 7 | One expensive provider provisioning action supplies the owner read, public projection, cross-tenant exclusion, and blocked-prerequisite reporting. |

S1 remains separate because Cloud Provider Admin credentials and authorization scope are distinct. S2 and S3 remain separate because REST and manual CLI are different channels with unresolved owners and infrastructure. No consolidated scenario exceeds the 15-validation limit.

## Test Infrastructure Usage

### Methods Needed

| Method or fixture | Purpose | Used in Scenarios | Availability |
|---|---|---|---|
| `GRPCClient.call(service=..., data=...)` | Public `Volumes/List` and `Volumes/Get` calls | C1, S1 | Exists in `tests/e2e/core/grpc_client.py`; no Volume wrapper required for the call itself |
| `GRPCClient.call_unchecked(service=..., data=...)` | Capture tenant-B `NotFound` without raising | C1 | Exists |
| `jwt_grpc_tenant1`, `jwt_grpc_tenant2` | Tenant-scoped public identities | C1 | Exist in root E2E conftest; external harness equivalence unresolved |
| `private_grpc` / `GRPCClient.call` | Candidate private provisioning path | C1, S1 | Client exists, but Volume create request shape and readiness contract are not documented in the local E2E tree |
| `poll_until` | Bounded readiness and cleanup polling | C1, S1 | Exists; Volume-specific observable predicate is missing |
| `OsacCLI.get` | Generic collection CLI read | S3 | Exists, but does not expose an item-id parameter |
| Item-aware CLI helper | `osac get volume <id>` | S3 | Missing helper is implementable test work; manual execution remains valid |
| Authenticated HTTP client/helper | REST collection/item calls | S2 | Missing helper is implementable test work if the confirmed owner is local |
| Cloud Provider Admin public identity fixture | Cross-tenant List/Get | S1 | Missing fixture is implementable test work; actual credential availability is an execution prerequisite |
| Volume provisioning/readiness/cleanup fixture | Create, wait, and delete standalone Volume | C1, S1 | Implementable test work once the provider lifecycle contract and owner are confirmed |

### Auxiliary Services Needed

Tests run against a pre-existing deployed environment; no auxiliary service is started by this plan.

| Service | Why Needed | How Started | Used in Scenarios |
|---|---|---|---|
| Fulfillment/Kubernetes stack | Deployed public API and provider path | Installer/full-install environment | C1, S1, S2, S3 |
| Keycloak/JWT | Tenant and admin authentication | Deployed environment plus existing identity fixtures | C1, S1, S2, S3 |
| Volume provider/storage backend | Standalone Volume creation and inventory | External VMaaS/storage profile | C1, S1 |
| REST gateway | Public collection/item path | Deployed environment | S2 |
| CLI binary/reflection endpoint | Manual generic CLI validation | QE-provided environment | S3 |

## Task Breakdown

No implementation task is authorized in this local evaluation. The following are conditional code tasks after the ownership and provider-contract decisions are resolved; missing helpers alone are not a blocker.

### Task 1: Establish the owning suite and Volume fixture contract

- **Files:** candidate `tests/e2e/storage/regression/test_public_volume_reads.py`; possibly `tests/e2e/storage/conftest.py`, or the confirmed external suite path
- **What:** establish the fixture interface for standalone Volume creation, readiness, tenant identities, Cloud Provider Admin identity, and cleanup; preserve provider/environment/harness prerequisite reporting
- **Why:** C1 and S1 cannot be implemented against the current local infrastructure without this contract
- **Commit message:** `OSAC-4542: add public Volume E2E fixture contract`
- **Status:** Test fixture work is implementable. Scoping is blocked by repository ownership and the provider lifecycle contract; unsynchronized [DEV] dependencies and provider setup are execution prerequisites.

### Task 2: Implement consolidated scenario C1

- **Files:** confirmed owning test file
- **What:** provision one standalone Volume, exercise public gRPC List/Get for the owner and outside tenant, assert public projection and `NotFound`, and clean up through the owning fixture
- **Why:** AC-1, AC-2, AC-4, AC-5; `TC-FR4-01` and the external realization of `TC-FR8-01`
- **Commit message:** `OSAC-4542: cover deployed public Volume reads`
- **Status:** Implementation can proceed after the owner and provider contract are confirmed; execution remains blocked until the environment, credentials, and dependencies are available.

### Task 3: Implement standalone scenario S1

- **Files:** confirmed owning test file and admin identity fixture if local
- **What:** use a Cloud Provider Admin identity to list and get Volumes across tenants with separate prerequisite reporting
- **Why:** AC-2 and AC-4; `TC-FR4-02`
- **Commit message:** `OSAC-4542: cover public Volume admin visibility`
- **Status:** Fixture work can be implemented after ownership is confirmed; execution is blocked by public admin credentials and the deployed identity configuration.

### Task 4: Implement or hand off standalone scenario S2

- **Files:** owning REST E2E suite, if confirmed
- **What:** exercise public REST collection/item paths and assert status, totals, projection, and hidden fields; add an authenticated HTTP helper if the confirmed owner is local
- **Why:** AC-3 and AC-4; `TC-FR7-01`
- **Commit message:** `OSAC-4542: cover public Volume REST reads`
- **Status:** Ownership unresolved; implementable if this repository owns the case, otherwise it requires an explicit handoff decision.

### Task 5: Execute the manual CLI procedure for S3

- **Files:** QE runbook or owning harness evidence location
- **What:** run generic CLI collection/item reads with declared binary/version, credentials, reflection, and structured output capture
- **Why:** AC-3 and AC-4; `TC-FR7-02`
- **Commit message:** `OSAC-4542: record public Volume CLI validation`
- **Status:** Ownership unresolved and manual by source plan; no automated implementation is planned until QE confirms the owner and automation boundary.

## Acceptance Criteria Coverage

| AC | Description | Scenarios | Task |
|---|---|---|---|
| AC-1 | External deployed path provisions a standalone Volume, then public Get/List reads it | C1 | Task 2 |
| AC-2 | Public representation, tenant/project visibility, and outside-scope `NotFound` are asserted | C1, S1 | Tasks 2–3 |
| AC-3 | Deployed REST and generic CLI reflection paths are exercised where owned | S2, S3 | Tasks 4–5 |
| AC-4 | Provider, environment, and harness prerequisites are separated from behavioral results; unavailable infrastructure is blocked | C1, S1, S2, S3 | Tasks 1–5 |
| AC-5 | E2E does not duplicate unit or Kind component-integration coverage | C1 | Tasks 1–2 |

All five acceptance criteria have planned coverage. Implementation is conditionally possible for the local scenarios after ownership/provider-contract decisions; execution remains blocked where the environment, credentials, or dependencies are unavailable.

## Test Plan Coverage

| TC ID | Title | Covered by Scenario | Notes |
|---|---|---|---|
| `TC-FR4-01` | Tenant member cannot list or get another tenant's volume | C1 | Planned external deployed realization; blocked by Volume fixture and tenant identities |
| `TC-FR4-02` | Cloud Provider Admin sees volumes across tenants | S1 | Blocked by missing public admin identity and owner fixture |
| `TC-FR7-01` | REST Get and List expose the public volume endpoints | S2 | Story 1.03 `[QE]` owns the requirement-level handoff; the repository, deployed REST harness, and channel owner remain unresolved |
| `TC-FR7-02` | Generic CLI discovers public Volume types through reflection | S3 | Story 1.03 `[QE]` owns the requirement-level handoff; the manual QE owner, harness, and item-id helper remain unresolved |
| `TC-FR8-01` | Public gRPC integration path reads a privately created volume | C1 for the external realization | The source case names Kind, while decomposition assigns both Kind to Story 1.02 and external realization to Story 1.03. The Kind realization is assigned elsewhere and must not be duplicated here. |
| `TC-FR8-02` | Published API specification documents only the public read endpoints | N/A — Story 1.04 documentation/spec owner | No local OpenAPI artifact or validation command was found; this is outside the deployed user-journey implementation file. |

The set-difference check is clean: every scoped test-case id is assigned to a scenario or has an explicit elsewhere/N/A rationale.

## Cases Assigned Elsewhere, Deferred, or Blocked

- **Assigned to Story 1.02:** the Kind component-integration realization of `TC-FR8-01`. The story explicitly excludes duplicating this setup.
- **Execution-blocked in C1:** external realization of `TC-FR8-01` and `TC-FR4-01`, pending provider environment, tenant credentials, dependency availability, and the external/local suite owner. The missing local fixture is implementable test work.
- **Execution-blocked in S1:** `TC-FR4-02`, pending a public Cloud Provider Admin credential and cross-tenant environment. The missing fixture is implementable test work.
- **Ownership unresolved in S2:** `TC-FR7-01` is assigned at the story level to Story 1.03 `[QE]`, but no repository, REST harness, channel owner, authenticated HTTP access, or response capture convention is established. No “assigned elsewhere” claim is made.
- **Ownership unresolved in S3:** `TC-FR7-02` is assigned at the story level to Story 1.03 `[QE]` and marked manual by the published plan, but no manual QE owner, harness, credentials, or evidence location is identified. No “assigned elsewhere” claim is made.
- **Assigned to Story 1.04/documentation:** `TC-FR8-02`, because API specification validation is not an E2E user-journey test and its artifact/command is unresolved.

## Missing Information by Category

### Missing helpers and fixtures — implementable test work

- The local tree lacks a Volume provisioning wrapper, readiness predicate, cleanup helper, public Cloud Provider Admin fixture, authenticated REST helper, and item-aware CLI wrapper. These are candidate additions to the owning test suite; their absence alone does not block implementation.
- The helper signatures and assertions must follow the existing `GRPCClient`, `OsacCLI`, `poll_until`, and cleanup patterns after the provider contract is confirmed.

### Missing environment and credentials — execution prerequisites

- A deployed provider/storage environment, public tenant identities, Cloud Provider Admin credentials, REST gateway, CLI binary/version, reflection, endpoint reachability, and output capture are required to execute the planned cases.
- The unsynchronized [DEV] dependencies and any missing public API deployment are execution prerequisites. They must not be reported as completed.

### Unresolved behavior, provider contracts, and ownership — planning/implementation blockers

- `TC-FR8-01` has one id with two boundaries: the testplan's explicit Kind precondition and the decomposition's external E2E realization. The source owner must confirm whether the external case is an allowed realization or needs a distinct downstream case without changing the published plan during this phase.
- The story requires provisioning a standalone Volume, but the scoped testplan assumes that a Volume already exists and does not define the create request, readiness condition, returned id, or cleanup semantics.
- REST and CLI checks are conditional on the owning harness; no owner or evidence contract is established in the current artifacts.
- The plan must preserve the approved PRD/design role scope while resolving the decomposition-noted conflict with feature-level tenant-role wording.
- The published plan uses document-local aliases, and the ordering conflict versus implementation drift remains a source decision for Story 1.02. It is outside this E2E scenario set but can affect what behavior is considered valid.

- The external `osac-test-infra` VMaaS suite path, branch/ref, command, provider fixture, credentials, harness owner, and blocked-result mechanism were not available within the permitted read scope.
- No local OpenAPI/specification artifact or validation command was found for `TC-FR8-02`.
- Stories 1.01 and 1.02 are local generated [DEV] artifacts with unknown synchronization and merge status. The context says the baseline may contain the public implementation, but this plan cannot claim that the deployed feature exists.

## `TC-FR8-01` Boundary Reconciliation

- **Kind realization:** Story 1.02 `[DEV]` owns the component-integration case using `osac-dev`, the deployed fulfillment service, PostgreSQL, authn/authz/tenancy interceptors, and the private Volume inventory. Its focused invocation is still unresolved.
- **Deployed realization:** Story 1.03 `[QE]` owns the external provider-boundary case using the existing VMaaS Volume provisioning path and public API reads. Its suite, command, owner, credentials, and availability are unresolved.
- **Published identity:** the test plan intentionally has one `TC-FR8-01` id for both realizations. This plan keeps both mappings visible, assigns Kind to Story 1.02, and does not claim either realization executed.

## Risk Assessment

- **Critical — unresolved ownership boundary:** implementing in the local storage suite while the owning QE harness is external, or vice versa, could create duplicate or unowned coverage. Resolve repository and harness ownership first.
- **High — unresolved provider lifecycle contract:** without the Volume create/readiness/delete contract, a test could report API behavior without proving the requested standalone provisioning journey or could leak resources. The missing wrapper itself is implementable once that contract is available.
- **High — ambiguous `TC-FR8-01` boundary:** treating the Kind precondition as external coverage would violate AC-5; treating the external decomposition row as covered by Story 1.02 would leave the [QE] handoff incomplete.
- **High — authorization fixture gap:** tenant-B and Cloud Provider Admin identities must be confirmed before isolation assertions can be trusted.
- **Medium — channel ownership gap:** REST and CLI cases may be silently dropped unless assigned to explicit owners with commands and evidence requirements.
- **Medium — source behavior conflict:** ordering versus implementation drift remains unresolved even though it is outside this story's direct scenario set.

## Open Questions

1. Which repository and service-tier owner is authoritative for this story: local `tests/e2e/storage/`, local `tests/e2e/vmaas/`, or the external VMaaS harness?
2. Does the existing provider path create a standalone inventory Volume, and what exact API/fixture returns its immutable public id, readiness state, and cleanup handle?
3. Should the external realization of `TC-FR8-01` use the existing id with an explicit boundary note, or should a new downstream test-case identity be approved without modifying the published plan in this evaluation?
4. Which public identity represents Cloud Provider Admin in the deployed harness, and how are tenant-A and tenant-B identities isolated in parallel xdist workers?
5. Which owner or repository supplies authenticated REST execution and captures HTTP status, totals, public fields, and omitted private fields for `TC-FR7-01`?
6. Which QE owner supplies the manual CLI procedure for `TC-FR7-02`, including binary/version, reflection configuration, credentials, structured output, and evidence storage?
7. What mechanism records provider, environment, and harness prerequisites as blocked independently from behavioral failures?
8. Which artifact and command validate `TC-FR8-02` once Story 1.04 owns the specification path?
9. Are the local [DEV] dependencies synchronized and deployed, or is the current baseline implementation only an unverified local state?
10. How will the source owner resolve the decomposition prose that describes Story 1.03 as Kind coverage and Story 1.04 as deployed coverage, while the actual local story files assign Story 1.03 to [QE] deployed E2E and Story 1.04 to [DOCS]?

## Built-in Self-Review

- **Acceptance criteria coverage:** pass; all five ACs map to C1/S1/S2/S3, with blocked prerequisites recorded.
- **User-facing boundary:** pass; planned assertions use deployed public gRPC/REST/CLI surfaces and leave unit/Kind coverage to the owning stories.
- **Reference patterns:** pass; pytest functions, typed fixtures, `pytestmark`, bounded polling, unique resources, and `try/finally` cleanup follow inspected suites.
- **Existing methods verified:** pass for `GRPCClient.call`, `call_unchecked`, tenant JWT fixtures, `poll_until`, and `OsacCLI.get`; missing Volume, REST, admin, and item-id helpers are explicitly marked.
- **Locations and labels:** conditional; the proposed local path is within `tests/e2e/storage/regression/` and uses `regression`, but final location depends on ownership resolution.
- **Auxiliary services:** pass as a pre-existing deployed environment; no test-managed service is assumed.
- **No duplicate coverage:** pass; the Kind realization of `TC-FR8-01` is assigned to Story 1.02 and is excluded from the proposed E2E implementation.
- **Scenario consolidation:** pass; C1 has 7 validations and no consolidated scenario exceeds 15.
- **Task count:** pass; five conditional tasks.
- **Testplan set-diff:** pass; all six scoped test cases are assigned or explicitly marked elsewhere/N/A.
- **Implementation readiness:** conditional; missing helpers and fixtures can be implemented in the owning test work, but implementation cannot be scoped to a repository until ownership and the provider lifecycle contract are resolved. Execution additionally requires the listed environment, credentials, and dependency prerequisites.
