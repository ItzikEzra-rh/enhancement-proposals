---
ep_slug: "storage-tier-api"
ep_title: "StorageTier API"
jira_key: "OSAC-1110"
verdict: ""
score: 0
scores:
  specificity: 0
  grounding: 0
  scope_fidelity: 0
  actionability: 0
  consistency: 0
reviewed_at: ""
---

# Test Plan: StorageTier API

**Enhancement Proposal:** `enhancements/storage-tier-api/`
**Jira:** OSAC-1110
**Components:** fulfillment-service, osac-test-infra

## 1. Summary

This test plan validates the StorageTier private gRPC API — a DB-backed CRUD service under `osac.private.v1` that enables Cloud Provider Admins to define named storage offerings bound to registered StorageBackends with typed QoS properties. Key risk areas are referential integrity between StorageTier and StorageBackend (database triggers with Z0002/Z0003 error codes), name uniqueness among active tiers, v0.1 single-backend constraint enforcement, and name immutability after creation. StorageTier has no CRD, no controller, and no public API — it is entirely within the fulfillment-service.

## 2. Component Impact

| Component | Test Levels | Rationale |
|-----------|------------|-----------|
| fulfillment-service | Unit / IT | Private gRPC server with custom validation (backend existence, name immutability, v0.1 backend count), database migrations with referential integrity triggers, event payloads. Unit tests validate server logic and migration triggers; IT tests validate full gRPC/REST endpoints against a kind cluster with PostgreSQL. |
| osac-test-infra | E2E | End-to-end validation of the StorageTier private API lifecycle against a live OSAC cluster, including cross-resource referential integrity with StorageBackend. |

## 3. Test Scenario Index

Quick reference — every test is detailed in Section 4 below.

| ID | Level | Component | Scenario | Priority |
|----|-------|-----------|----------|----------|
| TS-001 | Unit | fulfillment-service | StorageTier CRUD lifecycle (Create, Get, List, Update, Delete) | P0 |
| TS-002 | Unit | fulfillment-service | Backend validation rejects non-existent backend on Create | P0 |
| TS-003 | Unit | fulfillment-service | Backend validation rejects non-existent backend on Update | P0 |
| TS-004 | Unit | fulfillment-service | Name immutability rejects name change on Update | P0 |
| TS-005 | Unit | fulfillment-service | v0.1 single-backend constraint on Create and Update | P0 |
| TS-006 | Unit | fulfillment-service | Name uniqueness among active tiers | P0 |
| TS-007 | Unit | fulfillment-service | Name reuse after soft-delete | P1 |
| TS-008 | Unit | fulfillment-service | Optimistic concurrency rejects stale version on Update | P0 |
| TS-009 | Unit | fulfillment-service | Create always sets state to ACTIVE | P1 |
| TS-010 | Unit | fulfillment-service | Create validation edge cases (nil object, empty name, empty backends, empty backend_id) | P1 |
| TS-011 | Unit | fulfillment-service | Builder construction validation | P2 |
| TS-012 | Unit | fulfillment-service | List pagination (offset, limit) and CEL filtering | P1 |
| TS-013 | Unit | fulfillment-service | List ordering | P2 |
| TS-014 | Unit | fulfillment-service | Update partial changes via field mask | P1 |
| TS-015 | Unit | fulfillment-service | Create forces tenant to shared (platform-scoped) | P1 |
| TS-016 | Unit | fulfillment-service | Update rejects metadata.tenant in update_mask | P1 |
| TS-017 | Unit | fulfillment-service | Event payload — setPayload populates StorageTier in Event | P1 |
| TS-018 | Unit | fulfillment-service | Migration: storage_tiers table and indexes created | P0 |
| TS-019 | Unit | fulfillment-service | Migration: helper table materialization trigger populates storage_tier_backends | P0 |
| TS-020 | Unit | fulfillment-service | Migration: forward ref validation trigger rejects non-existent backend (Z0002) | P0 |
| TS-021 | Unit | fulfillment-service | Migration: reverse deletion protection trigger blocks backend delete (Z0003) | P0 |
| TS-022 | Unit | fulfillment-service | Migration: forward ref validation rejects soft-deleted backend | P1 |
| TS-023 | IT | fulfillment-service | Full CRUD lifecycle via gRPC private endpoint | P0 |
| TS-024 | IT | fulfillment-service | Full CRUD lifecycle via REST (grpc-gateway) endpoint | P0 |
| TS-025 | IT | fulfillment-service | Referential integrity — StorageBackend deletion blocked by active tier | P0 |
| TS-026 | IT | fulfillment-service | Name uniqueness and soft-delete reuse via gRPC | P0 |
| TS-027 | IT | fulfillment-service | CEL filtering and pagination on List via gRPC | P1 |
| TS-028 | IT | fulfillment-service | Optimistic locking conflict via gRPC | P1 |
| TS-029 | E2E | osac-test-infra | StorageTier CRUD lifecycle via private gRPC API | P0 |
| TS-030 | E2E | osac-test-infra | StorageTier referential integrity with StorageBackend | P0 |
| TS-031 | E2E | osac-test-infra | StorageTier duplicate name rejection | P1 |

## 4. Detailed Test Descriptions

Each test scenario below has enough detail to be implemented directly or
created as a Jira task. Every scenario includes preconditions, numbered
steps, concrete expected results, and implementation references.

---

### TS-001: StorageTier CRUD Lifecycle

**Level:** Unit | **Component:** fulfillment-service | **Priority:** P0

**What it tests:** The complete Create → Get → List → Update → Delete lifecycle for a StorageTier with valid inputs, validating that all CRUD operations work correctly through the `PrivateStorageTiersServer` and `GenericServer` infrastructure. Traces to FR-1, FR-2, FR-3, FR-5, FR-6.

**Preconditions:**
- A `StorageBackend` is created in the test database via `NewPrivateStorageBackendsServer()` (cross-resource dependency setup)
- `PrivateStorageTiersServer` is built via the builder pattern with logger, attribution logic, tenancy logic, and the StorageBackends DAO
- Fresh database transaction per test via `servers_suite_test.go` `BeforeEach`

**Steps:**
1. Create a StorageTier with `metadata.name = "fast"`, `description = "High-performance tier"`, and one `BackendAssociation` referencing the pre-created backend's ID with `protocol = STORAGE_PROTOCOL_NFS`, `max_read_bandwidth_mbs = 1000`, `max_write_bandwidth_mbs = 500`, `quota_gib = 1024`, `encryption_enabled = true`.
2. Assert the Create response returns a generated UUID as `id` and `state = STORAGE_TIER_STATE_ACTIVE`.
3. Get the tier by ID and verify all fields match the Create input.
4. List tiers and verify the created tier appears in the result set.
5. Update the tier: change `max_read_bandwidth_mbs` to 2000 using a field mask on `backends`.
6. Get the tier again and verify `max_read_bandwidth_mbs` is 2000 and other fields are unchanged.
7. Delete the tier by ID.
8. List tiers and verify the deleted tier is excluded from results.

**Expected Results:**
- Create returns a StorageTier with a non-empty UUID `id`, `state = STORAGE_TIER_STATE_ACTIVE`, and all input fields preserved.
- Get returns the exact object created.
- List includes the created tier.
- Update modifies only the specified fields; all other fields remain unchanged.
- After Delete, List excludes the tier (soft-delete).

**Test Data:**

| Parameter | Value | Notes |
|-----------|-------|-------|
| metadata.name | "fast" | Immutable after creation |
| backends[0].backend_id | (pre-created backend ID) | Must reference existing active backend |
| backends[0].protocol | STORAGE_PROTOCOL_NFS | Enum value 1 |
| backends[0].max_read_bandwidth_mbs | 1000 → 2000 | Updated in step 5 |
| backends[0].quota_gib | 1024 | int64 for petabyte-scale headroom |

**Implementation Reference:**
- Pattern: `fulfillment-service/internal/servers/private_storage_tiers_server_test.go:180` — "Creates and gets a storage tier"
- Fixtures: `servers_suite_test.go` `BeforeEach` — fresh DB transaction per test
- Helpers: `createStorageTier()` at line 131, `createStorageTierWithName()` at line 156

**Traces to:** FR-1 (CRUD RPCs), FR-3 (Create with backend associations and QoS), FR-5 (partial Update), FR-6 (soft Delete)

---

### TS-002: Backend Validation Rejects Non-Existent Backend on Create

**Level:** Unit | **Component:** fulfillment-service | **Priority:** P0

**What it tests:** That `CreateStorageTier` returns `NOT_FOUND` when the request references a `backend_id` that does not exist in the database. Validates the server-side validation in `validateStorageTierCreate` (line 194) which calls `storageBackendsDAO.Get()` for each backend. Traces to FR-7.

**Preconditions:**
- `PrivateStorageTiersServer` is built with a `StorageBackendsDAO` that contains no backends (or a specific set that does not include the referenced ID)
- No StorageBackend with ID "nonexistent-backend-id" exists

**Steps:**
1. Call `Create` with a StorageTier that has `backends[0].backend_id = "nonexistent-backend-id"`.
2. Assert the call returns an error.
3. Extract the gRPC status from the error.

**Expected Results:**
- The gRPC error code is `codes.NotFound`.
- The error message contains the invalid backend ID "nonexistent-backend-id".
- No StorageTier row is created in the database.

**Test Data:**

| Parameter | Value | Notes |
|-----------|-------|-------|
| backends[0].backend_id | "nonexistent-backend-id" | ID that does not exist in storage_backends table |

**Implementation Reference:**
- Pattern: `fulfillment-service/internal/servers/private_storage_tiers_server_test.go:486` — "Create with non-existent backend_id fails"
- Helpers: `status.FromError(err)` + `Expect(st.Code()).To(Equal(codes.NotFound))`

**Traces to:** FR-7 (Create must validate StorageBackend IDs exist)

---

### TS-003: Backend Validation Rejects Non-Existent Backend on Update

**Level:** Unit | **Component:** fulfillment-service | **Priority:** P0

**What it tests:** That `UpdateStorageTier` returns `NOT_FOUND` when the updated backends list references a `backend_id` that does not exist. Validates the server-side validation in `validateStorageTierUpdate` (line 210) which re-validates all backend references on every update. Traces to FR-7.

**Preconditions:**
- A valid StorageTier exists (created with a valid backend)
- No StorageBackend with ID "nonexistent-backend-id" exists

**Steps:**
1. Create a valid StorageTier referencing an existing backend.
2. Update the tier, changing `backends[0].backend_id` to "nonexistent-backend-id".
3. Assert the Update call returns an error.
4. Extract the gRPC status from the error.

**Expected Results:**
- The gRPC error code is `codes.NotFound`.
- The original StorageTier is unchanged in the database.

**Test Data:**

| Parameter | Value | Notes |
|-----------|-------|-------|
| backends[0].backend_id | "nonexistent-backend-id" | Attempted change to non-existent backend |

**Implementation Reference:**
- Pattern: `fulfillment-service/internal/servers/private_storage_tiers_server_test.go:536` — "Update with non-existent backend_id fails"
- Helpers: `validateBackends()` at `private_storage_tiers_server.go:240`

**Traces to:** FR-7 (Update must validate StorageBackend IDs exist)

---

### TS-004: v0.1 Single-Backend Constraint on Create and Update

**Level:** Unit | **Component:** fulfillment-service | **Priority:** P0

**What it tests:** That StorageTier enforces exactly one backend per tier in v0.1 — Create and Update with more than one backend association return an error. Validates the constraint in `validateBackends()` which checks `len(backends) > 1`. Traces to design decision: "v0.1 validates that exactly one backend is provided."

**Preconditions:**
- Two StorageBackends exist (backend A and backend B)
- `PrivateStorageTiersServer` is built with a StorageBackendsDAO containing both backends

**Steps:**
1. Call `Create` with a StorageTier having two `BackendAssociation` entries (referencing backend A and backend B).
2. Assert the Create call returns an error with gRPC code `codes.InvalidArgument`.
3. Create a valid StorageTier with one backend (backend A).
4. Call `Update` on the tier, providing two backends (backend A and backend B).
5. Assert the Update call returns an error with gRPC code `codes.InvalidArgument`.

**Expected Results:**
- Create with 2 backends returns `codes.InvalidArgument`.
- Update with 2 backends returns `codes.InvalidArgument`.
- The error messages indicate that v0.1 supports only a single backend per tier.

**Test Data:**

| Parameter | Value | Notes |
|-----------|-------|-------|
| backends | [backendA, backendB] | Two valid backends — rejected by v0.1 constraint |

**Implementation Reference:**
- Pattern: `fulfillment-service/internal/servers/private_storage_tiers_server_test.go:509` — "Create with more than one backend fails in v0.1"
- Pattern: `fulfillment-service/internal/servers/private_storage_tiers_server_test.go:560` — "Update with more than one backend fails in v0.1"
- Helpers: `validateBackends()` at `private_storage_tiers_server.go:240`

**Traces to:** Design: "v0.1 validates that exactly one backend is provided" (backends is repeated to support future multi-backend tiers)

---

### TS-005: Name Uniqueness Among Active Tiers

**Level:** Unit | **Component:** fulfillment-service | **Priority:** P0

**What it tests:** That creating two StorageTiers with the same `metadata.name` returns `ALREADY_EXISTS` due to the partial unique index `storage_tiers_unique_name`. Validates FR-8: tier names must be unique among active (non-deleted) tiers.

**Preconditions:**
- A StorageBackend exists
- `PrivateStorageTiersServer` is built

**Steps:**
1. Create a StorageTier with `metadata.name = "standard"`.
2. Assert it succeeds and returns an ID.
3. Create a second StorageTier with `metadata.name = "standard"`.
4. Assert the second Create returns an error.
5. Extract the gRPC status from the error.

**Expected Results:**
- The second Create returns gRPC code `codes.AlreadyExists`.
- Only one tier with name "standard" exists in the database.

**Test Data:**

| Parameter | Value | Notes |
|-----------|-------|-------|
| metadata.name | "standard" | Duplicated across two Create calls |

**Implementation Reference:**
- Pattern: `fulfillment-service/internal/servers/private_storage_tiers_server_test.go:664` — "Create with duplicate active name fails"
- Database: Partial unique index `storage_tiers_unique_name` on `(name) WHERE deletion_timestamp = 'epoch' AND name != ''`

**Traces to:** FR-8 (Tier names must be unique among active tiers)

---

### TS-006: Name Immutability Rejects Name Change on Update

**Level:** Unit | **Component:** fulfillment-service | **Priority:** P0

**What it tests:** That `UpdateStorageTier` rejects any attempt to change `metadata.name` after creation, returning an error. The server's `validateStorageTierUpdate` method (line 210) compares the existing name with the requested name. Traces to design: "metadata.name is immutable after creation."

**Preconditions:**
- A StorageTier with `metadata.name = "fast"` exists

**Steps:**
1. Create a StorageTier with `metadata.name = "fast"`.
2. Call `Update` with `metadata.name = "slow"` and include `metadata.name` in the field mask.
3. Assert the Update returns an error.

**Expected Results:**
- The gRPC error code indicates the field is immutable (e.g., `codes.InvalidArgument`).
- The tier's name remains "fast" in the database.

**Test Data:**

| Parameter | Value | Notes |
|-----------|-------|-------|
| metadata.name (original) | "fast" | Set during Create |
| metadata.name (attempted) | "slow" | Rejected by immutability check |

**Implementation Reference:**
- Pattern: `fulfillment-service/internal/servers/private_storage_tiers_server_test.go:624` — "Update changing metadata.name fails"
- Server: `validateStorageTierUpdate` at `private_storage_tiers_server.go:210`

**Traces to:** Design: "metadata.name carries the tier name. It is immutable after creation."

---

### TS-007: Name Reuse After Soft-Delete

**Level:** Unit | **Component:** fulfillment-service | **Priority:** P1

**What it tests:** That a deleted tier's name can be reused for a new tier, validating that the partial unique index only enforces uniqueness among active (non-deleted) tiers. Traces to FR-8: "Deleted tier names can be reused."

**Preconditions:**
- A StorageBackend exists

**Steps:**
1. Create a StorageTier with `metadata.name = "archive"`.
2. Delete the tier.
3. Create a new StorageTier with `metadata.name = "archive"`.
4. Assert the second Create succeeds and returns a new ID.

**Expected Results:**
- The second Create succeeds (no `ALREADY_EXISTS` error).
- The new tier has a different `id` than the deleted one.
- The deleted tier remains in the database for audit (soft-delete).

**Test Data:**

| Parameter | Value | Notes |
|-----------|-------|-------|
| metadata.name | "archive" | Reused after deletion |

**Implementation Reference:**
- Pattern: `fulfillment-service/internal/servers/private_storage_tiers_server_test.go:688` — "Create after delete of same name succeeds"
- Database: Partial unique index condition `WHERE deletion_timestamp = 'epoch'` allows name reuse

**Traces to:** FR-8 (Allowing name reuse after deletion)

---

### TS-008: Optimistic Concurrency Rejects Stale Version on Update

**Level:** Unit | **Component:** fulfillment-service | **Priority:** P0

**What it tests:** That `UpdateStorageTier` with `lock = true` rejects updates that use a stale metadata version, preventing conflicting writes. The GenericDAO's optimistic concurrency check compares the metadata version and returns `ABORTED` on mismatch. Traces to FR-5.

**Preconditions:**
- A StorageTier exists in the database

**Steps:**
1. Create a StorageTier. Note the returned `metadata.version`.
2. Update the tier once (version increments).
3. Attempt a second Update using the original (stale) `metadata.version` from step 1, with `lock = true`.
4. Assert the Update returns an error.

**Expected Results:**
- The gRPC error code is `codes.Aborted`.
- The tier retains the values from step 2 (the successful update), not step 3.

**Test Data:**

| Parameter | Value | Notes |
|-----------|-------|-------|
| lock | true | Enables optimistic concurrency check |
| metadata.version | (stale) | Version from before the first update |

**Implementation Reference:**
- Pattern: `fulfillment-service/internal/servers/private_storage_tiers_server_test.go:703` — "Update with stale version and lock=true fails"
- Server: GenericServer's DAO optimistic concurrency via `generic_dao.go`

**Traces to:** FR-5 (Optimistic concurrency control to prevent conflicting writes)

---

### TS-009: Create Always Sets State to ACTIVE

**Level:** Unit | **Component:** fulfillment-service | **Priority:** P1

**What it tests:** That `CreateStorageTier` always sets `state = STORAGE_TIER_STATE_ACTIVE` regardless of what the caller provides. The server overrides any caller-provided state in the Create method. Traces to FR-3, FR-9.

**Preconditions:**
- A StorageBackend exists

**Steps:**
1. Create a StorageTier with `state = STORAGE_TIER_STATE_UNSPECIFIED` (or any non-ACTIVE value).
2. Get the created tier.

**Expected Results:**
- The returned tier has `state = STORAGE_TIER_STATE_ACTIVE` regardless of input.

**Test Data:**

| Parameter | Value | Notes |
|-----------|-------|-------|
| state (input) | STORAGE_TIER_STATE_UNSPECIFIED | Caller attempts to set non-ACTIVE state |
| state (expected) | STORAGE_TIER_STATE_ACTIVE | Server overrides to ACTIVE |

**Implementation Reference:**
- Pattern: `fulfillment-service/internal/servers/private_storage_tiers_server_test.go:374` — "Create always sets state to ACTIVE regardless..."

**Traces to:** FR-3 (tier must be created with initial state ACTIVE), FR-9 (StorageTier state includes ACTIVE)

---

### TS-010: Create Validation Edge Cases

**Level:** Unit | **Component:** fulfillment-service | **Priority:** P1

**What it tests:** That `CreateStorageTier` rejects malformed requests with appropriate error codes: nil object, empty name, empty backends array, and empty `backend_id` within a backend association. Validates input validation in `validateStorageTierCreate`.

**Preconditions:**
- `PrivateStorageTiersServer` is built

**Steps:**
1. Call Create with `object = nil`. Assert error code `codes.InvalidArgument`.
2. Call Create with `metadata.name = ""` (empty). Assert error code `codes.InvalidArgument`.
3. Call Create with `backends = []` (empty array). Assert error code `codes.InvalidArgument`.
4. Call Create with `backends[0].backend_id = ""` (empty string). Assert error code `codes.InvalidArgument`.

**Expected Results:**
- Each invalid request returns `codes.InvalidArgument`.
- No StorageTier rows are created.

**Test Data:**

| Parameter | Value | Notes |
|-----------|-------|-------|
| object | nil | Nil object check |
| metadata.name | "" | Empty name check |
| backends | [] | Empty backends check |
| backends[0].backend_id | "" | Empty backend_id check |

**Implementation Reference:**
- Pattern: `fulfillment-service/internal/servers/private_storage_tiers_server_test.go:420-477` — "Create without name fails", "Create without backends fails", "Create with empty backend_id fails", "Create with nil object fails"

**Traces to:** FR-3 (Create must accept a tier name and backend associations)

---

### TS-011: Builder Construction Validation

**Level:** Unit | **Component:** fulfillment-service | **Priority:** P2

**What it tests:** That the `PrivateStorageTiersServerBuilder` fails to build if required dependencies are missing (logger, tenancy logic, storage backends DAO) and succeeds when all are provided. Validates the builder pattern consistency.

**Preconditions:**
- None beyond test infrastructure

**Steps:**
1. Build with all required parameters set. Assert success.
2. Build without logger. Assert error.
3. Build without tenancy logic. Assert error.
4. Build without storage backends DAO. Assert error.

**Expected Results:**
- Build succeeds only when all required parameters are set.
- Missing any required parameter returns a clear error.

**Implementation Reference:**
- Pattern: `fulfillment-service/internal/servers/private_storage_tiers_server_test.go:33-68` — "Can be built if all the required parameters are set", "Fails if logger is not set", "Fails if tenancy logic is not set", "Fails if storage backends DAO is not set"

**Traces to:** Design: Builder pattern with SetLogger, SetNotifier, SetAttributionLogic, SetTenancyLogic, SetStorageBackendsDAO

---

### TS-012: List Pagination and CEL Filtering

**Level:** Unit | **Component:** fulfillment-service | **Priority:** P1

**What it tests:** That `ListStorageTiers` supports pagination via `offset` and `limit` parameters, and CEL-based filtering to select tiers by field values. Validates FR-4.

**Preconditions:**
- Three or more StorageTiers exist with distinct names (e.g., "fast", "standard", "archive")

**Steps:**
1. Call List with no pagination. Assert all tiers are returned.
2. Call List with `limit = 1`. Assert exactly 1 tier is returned.
3. Call List with `offset = 1, limit = 1`. Assert exactly 1 tier is returned and it differs from step 2.
4. Call List with a CEL filter expression matching a specific tier name (e.g., `metadata.name == "fast"`). Assert only the matching tier is returned.

**Expected Results:**
- Pagination returns correct subsets.
- CEL filter returns only matching tiers.
- Total count reflects all active tiers regardless of pagination.

**Implementation Reference:**
- Pattern: `fulfillment-service/internal/servers/private_storage_tiers_server_test.go:229` — "List objects with limit"
- Pattern: `fulfillment-service/internal/servers/private_storage_tiers_server_test.go:242` — "List objects with offset"
- Pattern: `fulfillment-service/internal/servers/private_storage_tiers_server_test.go:255` — "List objects with filter"

**Traces to:** FR-4 (ListStorageTiers must support pagination, CEL-based filtering)

---

### TS-013: List Ordering

**Level:** Unit | **Component:** fulfillment-service | **Priority:** P2

**What it tests:** That `ListStorageTiers` supports SQL-like ordering via the `order` parameter. Validates FR-4.

**Preconditions:**
- Multiple StorageTiers exist

**Steps:**
1. Call List with `order = "metadata.name ASC"`. Assert results are sorted alphabetically by name.
2. Call List with `order = "metadata.name DESC"`. Assert results are sorted in reverse.

**Expected Results:**
- Results are returned in the specified order.

**Implementation Reference:**
- Pattern: `fulfillment-service/internal/servers/private_storage_tiers_server_test.go:273` — "List objects with order"

**Traces to:** FR-4 (SQL-like ordering)

---

### TS-014: Update Partial Changes via Field Mask

**Level:** Unit | **Component:** fulfillment-service | **Priority:** P1

**What it tests:** That `UpdateStorageTier` applies only the fields specified in the `FieldMask`, leaving all other fields unchanged. Validates partial update semantics from FR-5.

**Preconditions:**
- A StorageTier exists with `description = "Original"`, `backends[0].max_read_bandwidth_mbs = 1000`

**Steps:**
1. Update the tier with `description = "Updated"` and `update_mask.paths = ["description"]`.
2. Get the tier and verify `description` is "Updated" and `backends[0].max_read_bandwidth_mbs` is still 1000.
3. Update the tier with a new backend association (replacing `backends`) via `update_mask.paths = ["backends"]`.
4. Get the tier and verify backends changed but description remains "Updated".

**Expected Results:**
- Only fields in the field mask are modified.
- Unmasked fields retain their original values.

**Implementation Reference:**
- Pattern: `fulfillment-service/internal/servers/private_storage_tiers_server_test.go:286` — "Update applies partial changes via field mask"
- Pattern: `fulfillment-service/internal/servers/private_storage_tiers_server_test.go:304` — "Update backends replaces the backend association"

**Traces to:** FR-5 (partial updates including backend association QoS properties)

---

### TS-015: Create Forces Tenant to Shared (Platform-Scoped)

**Level:** Unit | **Component:** fulfillment-service | **Priority:** P1

**What it tests:** That StorageTier is platform-scoped — the server forces the tenant assignment to "shared" regardless of what the caller provides. Validates the RBAC/Tenancy design: "StorageTier is platform-scoped, managed exclusively by Cloud Provider Admins."

**Preconditions:**
- `PrivateStorageTiersServer` is built with standard tenancy logic

**Steps:**
1. Create a StorageTier (tenancy logic automatically assigns).
2. Get the tier and inspect the `metadata` for tenant assignment.

**Expected Results:**
- The tier is assigned to the shared/system tenant, not a specific tenant.
- The tenancy logic's `AllTenants` is used for visibility.

**Implementation Reference:**
- Pattern: `fulfillment-service/internal/servers/private_storage_tiers_server_test.go:398` — "Create forces tenant to shared"

**Traces to:** RBAC/Tenancy section: "StorageTier is platform-scoped"

---

### TS-016: Update Rejects metadata.tenant in Update Mask

**Level:** Unit | **Component:** fulfillment-service | **Priority:** P1

**What it tests:** That attempting to change the tenant assignment of a StorageTier via Update is rejected, enforcing platform-scoping immutability.

**Preconditions:**
- A StorageTier exists

**Steps:**
1. Update the tier with `metadata.tenant` in the update mask, attempting to change the tenant.
2. Assert the Update returns an error.

**Expected Results:**
- The gRPC error code indicates the field is immutable or unauthorized.

**Implementation Reference:**
- Pattern: `fulfillment-service/internal/servers/private_storage_tiers_server_test.go:643` — "Update with metadata.tenant in update_mask fails"

**Traces to:** RBAC/Tenancy section: "StorageTier is platform-scoped"

---

### TS-017: Event Payload — setPayload Populates StorageTier

**Level:** Unit | **Component:** fulfillment-service | **Priority:** P1

**What it tests:** That when a StorageTier is created/updated/deleted, the notification event payload includes the StorageTier object via the `setPayload()` switch case added in `generic_server.go`. Validates the `case *privatev1.StorageTier: event.SetStorageTier(object)` change.

**Preconditions:**
- `PrivateStorageTiersServer` is built with a mock notifier (`events.NewMockNotifier`)

**Steps:**
1. Create a StorageTier.
2. Capture the event sent to the mock notifier.
3. Assert that `event.GetStorageTier()` returns a non-nil object matching the created tier.

**Expected Results:**
- The event payload contains the StorageTier object.
- The StorageTier in the payload matches the created resource (id, name, backends).

**Implementation Reference:**
- Pattern: `fulfillment-service/internal/servers/generic_server_test.go:36` — "Sets the payload via reflection for a simple object type"
- Server: `generic_server.go:899` — `setPayload()` method
- Server: `generic_server.go:355` — `findPayloadField()` matches message type

**Traces to:** Design: "generic_server.go change: Add case *privatev1.StorageTier: event.SetStorageTier(object) to the setPayload() switch statement"

---

### TS-018: Migration — storage_tiers Table and Indexes Created

**Level:** Unit | **Component:** fulfillment-service | **Priority:** P0

**What it tests:** That the storage_tiers table migration creates the `storage_tiers` table, `archived_storage_tiers` table, and all required indexes (by_name, by_owner, by_tenant, by_label GIN, and the partial unique index `storage_tiers_unique_name`). Validates the database schema from the design.

**Preconditions:**
- Database migrated to the migration immediately before the storage_tiers table creation migration
- `DescribeMigration` helper provides the test infrastructure

**Steps:**
1. Apply the storage_tiers table creation migration.
2. Query `information_schema.tables` to verify `storage_tiers` and `archived_storage_tiers` exist.
3. Query `pg_indexes` to verify all indexes exist: `storage_tiers_by_name`, `storage_tiers_by_owner`, `storage_tiers_by_tenant`, `storage_tiers_by_label`, `storage_tiers_unique_name`.
4. Verify the unique index has the correct partial predicate: `WHERE deletion_timestamp = 'epoch' AND name != ''`.

**Expected Results:**
- Both tables exist with correct columns.
- All five indexes exist with correct definitions.

**Implementation Reference:**
- Pattern: `fulfillment-service/internal/database/migrations/migrations_suite_test.go:79` — `DescribeMigration` helper
- Migration SQL: `fulfillment-service/internal/database/migrations/` — the create_storage_tiers_tables migration

**Traces to:** Design: Database Migration section (storage_tiers table schema)

---

### TS-019: Migration — Helper Table Materialization Trigger

**Level:** Unit | **Component:** fulfillment-service | **Priority:** P0

**What it tests:** That the `materialize_storage_tier_backends` trigger correctly populates the `storage_tier_backends` helper table when a StorageTier row is inserted or updated, extracting `backendId` values from the JSONB `data->'backends'` array. Validates the materialized helper table pattern.

**Preconditions:**
- Database migrated through the storage_tier_ref_triggers migration (migration 76)
- At least one row exists in `storage_backends`

**Steps:**
1. Insert a row into `storage_tiers` with `data` containing one backend association with `backendId = "sb-1"`.
2. Query `storage_tier_backends` for the inserted tier's ID.
3. Assert one row exists with `backend_id = "sb-1"`.
4. Update the `storage_tiers` row, changing the backend to `backendId = "sb-2"`.
5. Query `storage_tier_backends` again.
6. Assert the old row is gone and one row exists with `backend_id = "sb-2"`.

**Expected Results:**
- After INSERT: `storage_tier_backends` contains exactly `{storage_tier_id, "sb-1"}`.
- After UPDATE: `storage_tier_backends` contains exactly `{storage_tier_id, "sb-2"}` (old row deleted, new row inserted).

**Implementation Reference:**
- Pattern: `fulfillment-service/internal/database/migrations/76_add_storage_tier_ref_triggers_test.go` — materialization tests
- Migration SQL: `fulfillment-service/internal/database/migrations/76_add_storage_tier_ref_triggers.up.sql:38-60` — `materialize_storage_tier_backends()` function

**Traces to:** Design: "Helper table: extracts backend IDs from the JSONB backends array for trigger-based reverse lookup"

---

### TS-020: Migration — Forward Ref Validation Rejects Non-Existent Backend (Z0002)

**Level:** Unit | **Component:** fulfillment-service | **Priority:** P0

**What it tests:** That the `check_storage_tier_backend_refs` BEFORE INSERT/UPDATE trigger on `storage_tiers` raises SQLSTATE `Z0002` when the referenced `backendId` does not exist in `storage_backends`. Validates database-level referential integrity as a safety net behind the server-level validation.

**Preconditions:**
- Database migrated through migration 76
- No StorageBackend with ID "nonexistent" exists

**Steps:**
1. Attempt to INSERT a row into `storage_tiers` with `data` containing `backendId = "nonexistent"`.
2. Assert the INSERT fails with SQLSTATE `Z0002`.
3. Assert the error message contains "does not exist or has been deleted".

**Expected Results:**
- INSERT is rejected at the database level with error code Z0002.
- No row is created in `storage_tiers` or `storage_tier_backends`.

**Implementation Reference:**
- Pattern: `fulfillment-service/internal/database/migrations/76_add_storage_tier_ref_triggers_test.go` — forward ref validation tests
- Migration SQL: `fulfillment-service/internal/database/migrations/76_add_storage_tier_ref_triggers.up.sql:63-93` — `check_storage_tier_backend_refs()` function

**Traces to:** FR-7 (referential integrity validation), Design: "BEFORE INSERT/UPDATE trigger validates backend existence with FOR SHARE locking"

---

### TS-021: Migration — Reverse Deletion Protection Blocks Backend Delete (Z0003)

**Level:** Unit | **Component:** fulfillment-service | **Priority:** P0

**What it tests:** That the `check_storage_backend_not_in_use_by_tier` BEFORE UPDATE trigger on `storage_backends` raises SQLSTATE `Z0003` when attempting to soft-delete a StorageBackend that is referenced by an active StorageTier. Validates FR-10.

**Preconditions:**
- Database migrated through migration 76
- A StorageBackend "sb-1" exists
- A StorageTier exists referencing "sb-1"

**Steps:**
1. Attempt to soft-delete the StorageBackend (set `deletion_timestamp` to current time).
2. Assert the UPDATE fails with SQLSTATE `Z0003`.
3. Assert the error message contains "cannot delete StorageBackend" and the count of referencing tiers.
4. Delete the StorageTier first, then retry the StorageBackend soft-delete.
5. Assert the second attempt succeeds.

**Expected Results:**
- Soft-delete of a referenced backend is blocked with Z0003.
- After removing all tier references, the backend can be soft-deleted.

**Implementation Reference:**
- Pattern: `fulfillment-service/internal/database/migrations/76_add_storage_tier_ref_triggers_test.go` — reverse deletion protection tests
- Migration SQL: `fulfillment-service/internal/database/migrations/76_add_storage_tier_ref_triggers.up.sql:96-121` — `check_storage_backend_not_in_use_by_tier()` function
- Analog: `fulfillment-service/internal/database/migrations/55_add_virtual_network_child_ref_triggers.up.sql` — VirtualNetwork reverse check pattern

**Traces to:** FR-10 (Deleting a StorageBackend must be rejected if any active StorageTier references it)

---

### TS-022: Migration — Forward Ref Validation Rejects Soft-Deleted Backend

**Level:** Unit | **Component:** fulfillment-service | **Priority:** P1

**What it tests:** That the forward validation trigger also rejects referencing a soft-deleted (non-active) backend, since the trigger checks `deletion_timestamp = 'epoch'`. A backend that has been soft-deleted should not be referenceable by new tiers.

**Preconditions:**
- Database migrated through migration 76
- A StorageBackend "sb-1" exists and has been soft-deleted (deletion_timestamp != epoch)

**Steps:**
1. Soft-delete the StorageBackend (set `deletion_timestamp` to current time).
2. Attempt to INSERT a StorageTier referencing the soft-deleted backend ID.
3. Assert the INSERT fails with SQLSTATE `Z0002`.

**Expected Results:**
- The trigger rejects the reference to a soft-deleted backend with Z0002.

**Implementation Reference:**
- Migration SQL: `fulfillment-service/internal/database/migrations/76_add_storage_tier_ref_triggers.up.sql:78-80` — `WHERE id = bid AND deletion_timestamp = 'epoch' FOR SHARE`

**Traces to:** FR-7 (backend validation), Design: "validate backend exists and is active"

---

### TS-023: IT — Full CRUD Lifecycle via gRPC Private Endpoint

**Level:** IT | **Component:** fulfillment-service | **Priority:** P0

**What it tests:** End-to-end CRUD lifecycle of StorageTier through the actual gRPC private API endpoint running in a kind cluster with PostgreSQL, Keycloak, and Envoy. Validates that the full server stack (interceptors, authentication, database, triggers) works together. Traces to FR-1, FR-2.

**Preconditions:**
- Kind cluster `fulfillment-service-it` is running with PostgreSQL, Keycloak, and Envoy
- All database migrations applied (including storage_backends and storage_tiers)
- Authenticated gRPC connection to the private API via `tool.InternalView().AdminConn()`
- A StorageBackend exists (created as a prerequisite or via `DeferCleanup`)

**Steps:**
1. Create a `privatev1.NewStorageTiersClient(tool.InternalView().AdminConn())`.
2. Create a StorageBackend first via `privatev1.NewStorageBackendsClient(...)`.
3. Create a StorageTier with `metadata.name = "it-fast-{uuid}"`, referencing the backend.
4. Assert Create response has a generated ID, `state = ACTIVE`, and all QoS fields populated.
5. Get the tier by ID. Assert all fields match.
6. List tiers. Assert the created tier appears.
7. Update the tier: change `max_read_bandwidth_mbs` to 2000.
8. Get again. Assert the update is reflected.
9. Delete the tier.
10. List. Assert the tier is no longer returned.
11. Get the deleted tier. Assert `NOT_FOUND`.
12. Clean up the StorageBackend via `DeferCleanup`.

**Expected Results:**
- Full lifecycle completes without errors through the real gRPC stack.
- Authentication interceptors accept the admin token.
- Database triggers fire correctly (helper table populated, constraints enforced).

**Test Data:**

| Parameter | Value | Notes |
|-----------|-------|-------|
| metadata.name | "it-fast-{uuid}" | UUID suffix for test isolation |
| backends[0].protocol | STORAGE_PROTOCOL_NFS | |
| backends[0].max_read_bandwidth_mbs | 1000 → 2000 | Updated in step 7 |

**Implementation Reference:**
- Pattern: `fulfillment-service/it/it_private_instance_types_test.go` — private API CRUD lifecycle via gRPC
- Fixtures: `it_tool.go` — `Tool`, `InternalView()`, `AdminConn()`
- Cleanup: `DeferCleanup` pattern for resource teardown

**Traces to:** FR-1 (CRUD RPCs), FR-2 (gRPC endpoints), FR-3 (Create with QoS), FR-5 (partial Update)

---

### TS-024: IT — Full CRUD Lifecycle via REST Endpoint

**Level:** IT | **Component:** fulfillment-service | **Priority:** P0

**What it tests:** That all StorageTier CRUD operations work via REST (grpc-gateway) endpoints with correct HTTP methods and paths. Validates FR-2: all RPCs must include HTTP annotations for REST access.

**Preconditions:**
- Kind cluster running with grpc-gateway
- A StorageBackend exists

**Steps:**
1. POST `https://fulfillment-api.osac.svc.cluster.local/api/private/v1/storage_tiers` with JSON body containing the tier definition. Assert HTTP 200 and response contains the created tier.
2. GET `https://fulfillment-api.osac.svc.cluster.local/api/private/v1/storage_tiers/{id}`. Assert HTTP 200 and `response_body = "object"`.
3. GET `https://fulfillment-api.osac.svc.cluster.local/api/private/v1/storage_tiers` (List). Assert HTTP 200 and the tier appears in the list.
4. PATCH `https://fulfillment-api.osac.svc.cluster.local/api/private/v1/storage_tiers/{id}` with updated QoS. Assert HTTP 200.
5. DELETE `https://fulfillment-api.osac.svc.cluster.local/api/private/v1/storage_tiers/{id}`. Assert HTTP 200.

**Expected Results:**
- All HTTP methods map correctly to gRPC operations.
- REST responses contain the expected `object` field in response body (per `response_body: "object"` annotation).
- JSON serialization of proto enums, int32/int64 fields, and nested messages works correctly.

**Implementation Reference:**
- Proto: `storage_tiers_service.proto` HTTP annotations (POST, GET, PATCH, DELETE paths)
- Pattern: REST gateway testing via `curl` or HTTP client in IT suite

**Traces to:** FR-2 (HTTP annotations for REST access via grpc-gateway)

---

### TS-025: IT — Referential Integrity: StorageBackend Deletion Blocked by Active Tier

**Level:** IT | **Component:** fulfillment-service | **Priority:** P0

**What it tests:** End-to-end referential integrity through the real gRPC API: attempting to delete a StorageBackend that is referenced by an active StorageTier returns `FAILED_PRECONDITION`. Validates the complete chain: server → DAO → database trigger (Z0003) → gRPC error code mapping. Traces to FR-10.

**Preconditions:**
- Kind cluster running with all migrations applied
- gRPC clients for both StorageTiers and StorageBackends

**Steps:**
1. Create a StorageBackend "sb-it-{uuid}".
2. Create a StorageTier "st-it-{uuid}" referencing the backend.
3. Attempt to delete the StorageBackend via `StorageBackends/Delete`.
4. Assert the delete returns gRPC code `codes.FailedPrecondition`.
5. Assert the error message references StorageTier(s).
6. Delete the StorageTier first.
7. Retry deleting the StorageBackend.
8. Assert the second delete succeeds.

**Expected Results:**
- Step 4: `FAILED_PRECONDITION` error with message indicating the backend is in use.
- Step 8: Backend deletion succeeds after removing all tier references.

**Implementation Reference:**
- Pattern: `fulfillment-service/it/` — integration test patterns with `DeferCleanup`
- Database: `76_add_storage_tier_ref_triggers.up.sql` — `check_storage_backend_not_in_use_by_tier` trigger
- DAO error mapping: `ErrInUse` → `codes.FailedPrecondition` in `generic_server.go`

**Traces to:** FR-10 (Deleting a StorageBackend must be rejected if any active StorageTier references it)

---

### TS-026: IT — Name Uniqueness and Soft-Delete Reuse via gRPC

**Level:** IT | **Component:** fulfillment-service | **Priority:** P0

**What it tests:** That duplicate tier names are rejected at the API level with `ALREADY_EXISTS`, and that names become available for reuse after the tier is soft-deleted. Validates FR-8 through the full stack.

**Preconditions:**
- Kind cluster running
- A StorageBackend exists

**Steps:**
1. Create a StorageTier with `metadata.name = "unique-{uuid}"`.
2. Attempt to create a second StorageTier with the same name.
3. Assert the second Create returns gRPC code `codes.AlreadyExists`.
4. Delete the first StorageTier.
5. Create a third StorageTier with the same name.
6. Assert the third Create succeeds.

**Expected Results:**
- Duplicate active names return `ALREADY_EXISTS`.
- After soft-delete, the name can be reused.

**Implementation Reference:**
- Database: Partial unique index `storage_tiers_unique_name` on `(name) WHERE deletion_timestamp = 'epoch' AND name != ''`

**Traces to:** FR-8 (Tier names must be unique among active tiers; deleted tier names can be reused)

---

### TS-027: IT — CEL Filtering and Pagination on List via gRPC

**Level:** IT | **Component:** fulfillment-service | **Priority:** P1

**What it tests:** That `ListStorageTiers` supports CEL-based filtering and pagination through the real gRPC endpoint, including filtering by state and by referenced backend. Validates FR-4.

**Preconditions:**
- Kind cluster running
- Multiple StorageTiers exist with distinct names

**Steps:**
1. Create 3 StorageTiers with names "it-alpha-{uuid}", "it-beta-{uuid}", "it-gamma-{uuid}".
2. List with `limit = 2`. Assert 2 items returned.
3. List with `offset = 2`. Assert 1 item returned.
4. List with `filter = "metadata.name == 'it-beta-{uuid}'"`. Assert exactly 1 item returned matching the filter.
5. List with `order = "metadata.name ASC"`. Assert items sorted alphabetically.

**Expected Results:**
- Pagination returns correct subsets.
- CEL filters select matching tiers.
- Ordering works correctly.

**Implementation Reference:**
- Pattern: `fulfillment-service/it/it_private_instance_types_test.go` — pagination and filtering patterns

**Traces to:** FR-4 (ListStorageTiers with pagination, CEL filtering, SQL-like ordering)

---

### TS-028: IT — Optimistic Locking Conflict via gRPC

**Level:** IT | **Component:** fulfillment-service | **Priority:** P1

**What it tests:** That concurrent updates with stale versions are correctly rejected through the full gRPC stack when `lock = true`. Validates FR-5 concurrency control end-to-end.

**Preconditions:**
- Kind cluster running
- A StorageTier exists

**Steps:**
1. Create a StorageTier.
2. Get the tier (note `metadata.version = V1`).
3. Update the tier (version becomes V2).
4. Attempt an Update using the stale version V1 with `lock = true`.
5. Assert the Update returns gRPC code `codes.Aborted`.

**Expected Results:**
- Stale-version update returns `ABORTED`.
- The tier retains the V2 values.

**Implementation Reference:**
- Pattern: `fulfillment-service/internal/servers/private_storage_tiers_server_test.go:703` — unit test analog

**Traces to:** FR-5 (optimistic concurrency control)

---

### TS-029: E2E — StorageTier CRUD Lifecycle via Private gRPC API

**Level:** E2E | **Component:** osac-test-infra | **Priority:** P0

**What it tests:** Full CRUD lifecycle of StorageTier against a live OSAC cluster, using the `private_grpc` fixture and the `grpcurl`-based `GRPCClient`. Validates that the StorageTier API is accessible and functional in a deployed OSAC environment. Traces to FR-1 through FR-6.

**Preconditions:**
- OSAC cluster deployed with fulfillment-service including StorageTier migrations
- `private_grpc` fixture providing authenticated access to the private API endpoint
- A StorageBackend exists (created via `private_grpc.call()` to `StorageBackends/Create` or a setup fixture)

**Steps:**
1. Create a StorageBackend via `private_grpc.call(service="osac.private.v1.StorageBackends/Create", data={...})`.
2. Create a StorageTier: `private_grpc.call(service="osac.private.v1.StorageTiers/Create", data={"object": {"metadata": {"name": "e2e-fast-{uuid8}"}, "description": "E2E test tier", "backends": [{"backendId": backend_id, "protocol": "STORAGE_PROTOCOL_NFS", "maxReadBandwidthMbs": 1000, "maxWriteBandwidthMbs": 500, "quotaGib": "1024", "encryptionEnabled": true}]}})`.
3. Assert the response contains `object.id` and `object.state == "STORAGE_TIER_STATE_ACTIVE"`.
4. Get the tier: `private_grpc.call(service="osac.private.v1.StorageTiers/Get", data={"id": tier_id})`.
5. Assert all fields match the Create input.
6. List tiers: `private_grpc.call(service="osac.private.v1.StorageTiers/List")`.
7. Assert the created tier ID appears in the results.
8. Update QoS: `private_grpc.call(service="osac.private.v1.StorageTiers/Update", data={"object": {"id": tier_id, "backends": [{"backendId": backend_id, "maxReadBandwidthMbs": 2000, ...}]}, "updateMask": {"paths": ["backends"]}})`.
9. Get again and assert `maxReadBandwidthMbs == 2000`.
10. Delete the tier: `private_grpc.call(service="osac.private.v1.StorageTiers/Delete", data={"id": tier_id})`.
11. List again and assert the tier is gone.
12. Verify Get on deleted tier fails: `private_grpc.call_unchecked(service="osac.private.v1.StorageTiers/Get", data={"id": tier_id})` returns non-zero exit code.
13. Clean up the StorageBackend.

**Expected Results:**
- Full CRUD lifecycle succeeds against the live cluster.
- All QoS fields round-trip correctly through proto serialization.
- Soft-delete excludes the tier from List and Get.

**Test Data:**

| Parameter | Value | Notes |
|-----------|-------|-------|
| metadata.name | "e2e-fast-{uuid8}" | UUID suffix for isolation per test run |
| backends[0].protocol | "STORAGE_PROTOCOL_NFS" | String enum in JSON |
| backends[0].maxReadBandwidthMbs | 1000 → 2000 | JSON uses camelCase |
| backends[0].quotaGib | "1024" | int64 serialized as string in JSON |

**Implementation Reference:**
- Pattern: `osac-test-infra/tests/catalog/test_catalog_item_lifecycle.py:11` — `test_catalog_item_crud` using `grpc.call()` for private API CRUD
- Fixtures: `osac-test-infra/tests/conftest.py:55` — `private_grpc` session fixture
- Helpers: `GRPCClient.call()` at `osac-test-infra/tests/core/grpc_client.py:26`, `call_unchecked()` at line 104
- New file: `osac-test-infra/tests/storage/test_storage_tier_lifecycle.py` (to be created)
- New GRPCClient methods needed: `create_storage_tier()`, `get_storage_tier()`, `list_storage_tier_ids()`, `update_storage_tier()`, `delete_storage_tier()` following the InstanceType pattern at `grpc_client.py:299-339`

**Traces to:** FR-1 (CRUD RPCs), FR-2 (REST and gRPC access), FR-3 (Create), FR-5 (Update), FR-6 (soft Delete)

---

### TS-030: E2E — StorageTier Referential Integrity with StorageBackend

**Level:** E2E | **Component:** osac-test-infra | **Priority:** P0

**What it tests:** End-to-end referential integrity enforcement in a live OSAC cluster: (1) creating a tier with a non-existent backend fails, and (2) deleting a backend referenced by an active tier fails. Traces to FR-7, FR-10.

**Preconditions:**
- OSAC cluster deployed with fulfillment-service
- `private_grpc` fixture
- A StorageBackend exists

**Steps:**
1. Attempt to create a StorageTier referencing a non-existent backend ID "nonexistent-{uuid8}".
2. Assert the call fails (non-zero exit code from `call_unchecked`).
3. Assert the error output contains "NOT_FOUND" or the non-existent backend ID.
4. Create a valid StorageTier referencing the existing backend.
5. Attempt to delete the StorageBackend.
6. Assert the delete fails with an error containing "FAILED_PRECONDITION" or "in use".
7. Delete the StorageTier.
8. Retry deleting the StorageBackend.
9. Assert the second delete attempt succeeds.

**Expected Results:**
- Step 2-3: Create with invalid backend returns NOT_FOUND.
- Step 5-6: Backend deletion blocked with FAILED_PRECONDITION while tier references it.
- Step 8-9: Backend deletion succeeds after tier is removed.

**Test Data:**

| Parameter | Value | Notes |
|-----------|-------|-------|
| invalid_backend_id | "nonexistent-{uuid8}" | ID that does not exist |
| valid_backend_id | (from setup) | Created in preconditions |

**Implementation Reference:**
- Pattern: `osac-test-infra/tests/catalog/test_catalog_item_lifecycle.py:188` — `test_delete_catalog_item_blocked_when_referenced`
- Helpers: `GRPCClient.call_unchecked()` for negative-path assertions
- New file: `osac-test-infra/tests/storage/test_storage_tier_lifecycle.py` (to be created)

**Traces to:** FR-7 (backend validation on Create), FR-10 (backend deletion blocked by active tier)

---

### TS-031: E2E — StorageTier Duplicate Name Rejection

**Level:** E2E | **Component:** osac-test-infra | **Priority:** P1

**What it tests:** That the live OSAC cluster enforces name uniqueness among active StorageTiers — creating two tiers with the same name fails, and the name becomes available after the first tier is deleted. Traces to FR-8.

**Preconditions:**
- OSAC cluster deployed with fulfillment-service
- `private_grpc` fixture
- A StorageBackend exists

**Steps:**
1. Create a StorageTier with `metadata.name = "e2e-dup-{uuid8}"`.
2. Attempt to create a second StorageTier with the same name.
3. Assert the second Create fails with `call_unchecked` (non-zero exit code).
4. Assert the error output contains "ALREADY_EXISTS".
5. Delete the first StorageTier.
6. Create a third StorageTier with the same name.
7. Assert it succeeds.
8. Clean up: delete the third tier and the backend.

**Expected Results:**
- Duplicate active names rejected with ALREADY_EXISTS.
- Name reusable after soft-delete.

**Implementation Reference:**
- Pattern: `osac-test-infra/tests/catalog/test_catalog_item_lifecycle.py:11` — CRUD lifecycle with negative paths
- Helpers: `GRPCClient.call_unchecked()` for error assertions

**Traces to:** FR-8 (Tier names must be unique among active tiers; deleted tier names can be reused)

---

## 5. Persona Coverage

| Persona | Scenarios | Coverage |
|---------|-----------|----------|
| Cloud Provider Admin | TS-001 through TS-031 | All CRUD operations, validation, referential integrity — Cloud Provider Admin is the sole actor for StorageTier management via the private API |
| Cloud Infrastructure Admin | — | Not applicable — StorageTier is managed by Cloud Provider Admins; infrastructure admins manage StorageBackends (OSAC-1111) |
| Tenant Admin | — | Not applicable — tenants discover assigned tiers through Tenant CR status (OSAC-23), not by querying StorageTier directly |
| Tenant User | — | Not applicable — no public StorageTier API; tenant users access storage through provisioned StorageClasses |

## 6. Risk-Based Prioritization

| Risk Area | Priority | Scenarios | Rationale |
|-----------|----------|-----------|-----------|
| Referential integrity (StorageTier ↔ StorageBackend) | HIGH | TS-002, TS-003, TS-020, TS-021, TS-022, TS-025, TS-030 | Database triggers (Z0002/Z0003) are the primary safety mechanism preventing orphaned references and dangling backends. Failure leads to data integrity violations that are difficult to detect and repair. |
| Name uniqueness constraint | HIGH | TS-005, TS-007, TS-026, TS-031 | Partial unique index enforces business rule across soft-deletes. Failure leads to duplicate tier names confusing downstream consumers (OSAC Storage Controller). |
| CRUD lifecycle correctness | HIGH | TS-001, TS-023, TS-024, TS-029 | Core API functionality — all downstream features (OSAC-23 Tenant Storage Onboarding) depend on correct CRUD behavior. |
| Name immutability | MEDIUM | TS-004, TS-006 | Prevents accidental name changes that would break downstream references. Server-side validation only (no DB constraint). |
| Optimistic concurrency | MEDIUM | TS-008, TS-028 | Prevents lost updates in multi-admin environments. Standard GenericDAO behavior. |
| v0.1 single-backend constraint | MEDIUM | TS-005 | Temporary constraint — failure allows multi-backend tiers before the feature is ready. |
| Input validation edge cases | LOW | TS-010, TS-011 | Standard proto validation and builder patterns. Well-tested generic infrastructure. |
| List pagination/filtering/ordering | LOW | TS-012, TS-013, TS-027 | Delegated to GenericServer, which is broadly tested across all resources. |

## 7. Coverage Gaps

| Requirement | Gap | Reason | Risk |
|-------------|-----|--------|------|
| FR-6: Delete rejected if Tenant references the tier | Not testable until OSAC-23 | Tenant-reference trigger (`check_storage_tier_not_in_use`) is deferred to a follow-up migration that ships with OSAC-23. No tenants can reference tiers until then. | No protection gap — no tenant can reference a tier without OSAC-23. Test should be added when the trigger migration lands. |
| Signal RPC | Not covered | Signal RPC is included in the proto service for future consumption by the OSAC Storage Controller (OSAC-23). No current consumer exists. | Low — Signal follows the standard GenericServer pattern and requires no custom logic. |
| Multi-backend tier (future) | Not covered | v0.1 enforces single backend. Multi-backend selection logic is deferred. | Low — the constraint is tested (TS-005); multi-backend tests should be added when the constraint is lifted. |
| REST endpoint content-type and error format | Partially covered by TS-024 | REST-specific edge cases (e.g., malformed JSON, incorrect Content-Type) are not individually tested. | Low — grpc-gateway handles serialization generically. |
| Load/performance under concurrent CRUD | Not covered | No performance test infrastructure exists for StorageTier specifically. | Low — StorageTier is a low-volume catalog entity managed by admins, not a high-throughput API. |

## 8. Implementation Notes

- **Fixtures needed:**
  - **osac-test-infra:** New `GRPCClient` convenience methods for StorageTier CRUD in `tests/core/grpc_client.py`, following the InstanceType pattern (lines 299-339): `create_storage_tier()`, `get_storage_tier()`, `list_storage_tier_ids()`, `update_storage_tier()`, `delete_storage_tier()`. Also need `create_storage_backend()` and `delete_storage_backend()` if not already added by OSAC-1111.
  - **osac-test-infra:** A session-scoped `storage_backend` fixture in `tests/storage/conftest.py` that creates and tears down a StorageBackend for the test session.
  - **fulfillment-service IT:** StorageBackend setup helper in the IT suite, or a shared `DeferCleanup` pattern for cross-resource dependencies.

- **Infra gaps:**
  - **fulfillment-service IT:** No existing IT test file for StorageTier (`it_private_storage_tiers_test.go` needs to be created). Use `it_private_instance_types_test.go` as the structural template.
  - **osac-test-infra E2E:** No existing E2E test file for StorageTier (`tests/storage/test_storage_tier_lifecycle.py` needs to be created). The `tests/storage/conftest.py` skip logic may need updating if StorageTier tests should run independently of the storage controller.

- **Reference tests:**
  - Unit: `fulfillment-service/internal/servers/private_storage_tiers_server_test.go` (existing, 738+ lines)
  - Unit (migration): `fulfillment-service/internal/database/migrations/76_add_storage_tier_ref_triggers_test.go` (existing)
  - IT pattern: `fulfillment-service/it/it_private_instance_types_test.go`
  - E2E CRUD pattern: `osac-test-infra/tests/catalog/test_catalog_item_lifecycle.py`
  - E2E ref integrity pattern: `osac-test-infra/tests/catalog/test_catalog_item_lifecycle.py:188` (`test_delete_catalog_item_blocked_when_referenced`)

- **Jira tracking:** Create sub-tasks under OSAC-1110 for each test level:
  - `OSAC-1110: Unit tests — PrivateStorageTiersServer` (TS-001 through TS-017) — largely complete
  - `OSAC-1110: Unit tests — migration triggers` (TS-018 through TS-022) — partially complete
  - `OSAC-1110: IT tests — StorageTier gRPC/REST lifecycle` (TS-023 through TS-028) — to be created
  - `OSAC-1110: E2E tests — StorageTier private API` (TS-029 through TS-031) — to be created, including GRPCClient method additions
