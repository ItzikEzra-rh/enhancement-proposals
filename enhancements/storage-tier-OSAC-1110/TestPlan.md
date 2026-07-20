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

This test plan validates the StorageTier API introduced by OSAC-1110 — a private gRPC service under `osac.private.v1` that enables Cloud Provider Admins to define named storage offerings backed by registered StorageBackends with typed QoS properties. The plan covers unit tests for the `PrivateStorageTiersServer` CRUD lifecycle and validation logic, migration-level tests for referential integrity triggers and the materialized helper table, integration tests for full gRPC/REST endpoint coverage against a kind cluster, and E2E tests for the private API lifecycle on a live OSAC cluster. Key risk areas are referential integrity between StorageTier and StorageBackend (DB triggers), name uniqueness enforcement, backend validation on Create/Update, and the v0.1 single-backend constraint.

## 2. Component Impact

| Component | Test Levels | Rationale |
|-----------|------------|-----------|
| fulfillment-service | Unit, IT | StorageTier is a DB-backed entity in the fulfillment-service. The private server, generic DAO, database migrations, and referential integrity triggers all require unit-level coverage. Integration tests verify end-to-end gRPC and REST transport against a real kind cluster with PostgreSQL. |
| osac-test-infra | E2E | StorageTier CRUD and referential integrity must be verified against a live OSAC deployment. E2E tests require new `GRPCClient` methods for `StorageTiers` and `StorageBackends` private API. |

## 3. Test Scenario Index

Quick reference — every test is detailed in Section 4 below.

| ID | Level | Component | Scenario | Priority |
|----|-------|-----------|----------|----------|
| TS-001 | Unit | fulfillment-service | Server builder validation — required parameters | P1 |
| TS-002 | Unit | fulfillment-service | Create and Get — full CRUD lifecycle | P0 |
| TS-003 | Unit | fulfillment-service | List with pagination (limit and offset) | P1 |
| TS-004 | Unit | fulfillment-service | List with CEL filtering | P1 |
| TS-005 | Unit | fulfillment-service | List with ordering | P1 |
| TS-006 | Unit | fulfillment-service | Update QoS properties via field mask | P0 |
| TS-007 | Unit | fulfillment-service | Soft delete lifecycle | P0 |
| TS-008 | Unit | fulfillment-service | Backend validation — reject non-existent backend on Create | P0 |
| TS-009 | Unit | fulfillment-service | Backend validation — reject non-existent backend on Update | P0 |
| TS-010 | Unit | fulfillment-service | Name immutability — reject name change on Update | P0 |
| TS-011 | Unit | fulfillment-service | Name uniqueness — reject duplicate active tier names | P0 |
| TS-012 | Unit | fulfillment-service | Name reuse — allow name after prior tier deleted | P1 |
| TS-013 | Unit | fulfillment-service | Optimistic concurrency — reject stale version on Update | P0 |
| TS-014 | Unit | fulfillment-service | Single backend constraint (v0.1) | P0 |
| TS-015 | Unit | fulfillment-service | Create sets state to ACTIVE | P1 |
| TS-016 | Unit | fulfillment-service | Event payload — setPayload() StorageTier case | P1 |
| TS-017 | Unit | fulfillment-service | Migration — helper table and trigger creation | P0 |
| TS-018 | Unit | fulfillment-service | Migration — materialization trigger populates helper table | P0 |
| TS-019 | Unit | fulfillment-service | Migration — backend ref trigger rejects invalid backend | P0 |
| TS-020 | Unit | fulfillment-service | Migration — backend deletion blocked by active tier | P0 |
| TS-021 | Unit | fulfillment-service | Migration — backend deletion allowed when unreferenced | P1 |
| TS-022 | Unit | fulfillment-service | Migration — backend deletion allowed when referencing tier is soft-deleted | P1 |
| TS-030 | IT | fulfillment-service | Full CRUD lifecycle via gRPC client | P0 |
| TS-031 | IT | fulfillment-service | Full CRUD lifecycle via REST endpoints | P0 |
| TS-032 | IT | fulfillment-service | Referential integrity — backend deletion blocked | P0 |
| TS-033 | IT | fulfillment-service | Name uniqueness via gRPC endpoint | P0 |
| TS-034 | IT | fulfillment-service | Helper table materialization after Create and Update | P1 |
| TS-035 | IT | fulfillment-service | Optimistic concurrency via gRPC endpoint | P1 |
| TS-040 | E2E | osac-test-infra | StorageTier private API CRUD lifecycle | P0 |
| TS-041 | E2E | osac-test-infra | Backend reference validation — reject invalid backend | P0 |
| TS-042 | E2E | osac-test-infra | StorageBackend deletion blocked by StorageTier | P0 |
| TS-043 | E2E | osac-test-infra | Name uniqueness and reuse after deletion | P1 |
| TS-044 | E2E | osac-test-infra | Pagination and CEL filtering on List | P1 |

## 4. Detailed Test Descriptions

Each test scenario below has enough detail to be implemented directly or
created as a Jira task. Every scenario includes preconditions, numbered
steps, concrete expected results, and implementation references.

---

### TS-001: Server builder validation — required parameters

**Level:** Unit | **Component:** fulfillment-service | **Priority:** P1

**What it tests:** The `PrivateStorageTiersServerBuilder` enforces that all mandatory dependencies (logger, tenancy logic, storageBackendsDAO) are set before `Build()` succeeds. This validates the builder pattern requirement from the design doc's Implementation Details section.

**Preconditions:**
- Ginkgo test suite initialized with shared logger, attribution, and tenancy mocks from `servers_suite_test.go`

**Steps:**
1. Call `NewPrivateStorageTiersServer().SetAttributionLogic(attribution).SetTenancyLogic(tenancy).Build()` — omit logger
2. Call `NewPrivateStorageTiersServer().SetLogger(logger).SetAttributionLogic(attribution).Build()` — omit tenancy and storageBackendsDAO
3. Call `NewPrivateStorageTiersServer().SetLogger(logger).SetAttributionLogic(attribution).SetTenancyLogic(tenancy).Build()` — omit storageBackendsDAO
4. Call `NewPrivateStorageTiersServer().SetLogger(logger).SetAttributionLogic(attribution).SetTenancyLogic(tenancy).SetStorageBackendsDAO(dao).Build()` — all set

**Expected Results:**
- Step 1: error `"logger is mandatory"`, server is nil
- Step 2: error `"tenancy logic is mandatory"`, server is nil
- Step 3: error `"storage backends DAO is mandatory"`, server is nil
- Step 4: no error, server is non-nil

**Test Data:**

| Parameter | Value | Notes |
|-----------|-------|-------|
| logger | shared `slog.Logger` from suite | Standard test logger |
| attribution | mock `AttributionLogic` | Returns "system" creator |
| tenancy | mock `TenancyLogic` | AllTenants, SystemTenant default |
| storageBackendsDAO | `GenericDAO[*privatev1.StorageBackend]` | Required for cross-resource validation |

**Implementation Reference:**
- Pattern: `fulfillment-service/internal/servers/private_storage_tiers_server_test.go` — `Describe("Creation")` block
- Fixtures: `servers_suite_test.go` — `logger`, `attribution`, `tenancy` shared variables
- Helpers: `dao.NewGenericDAO[*privatev1.StorageBackend]()` for building the backends DAO

**Traces to:** Design doc — "Builder pattern: `PrivateStorageTiersServerBuilder` with `SetLogger`, `SetNotifier`, `SetAttributionLogic`, `SetTenancyLogic`, `SetMetricsRegisterer`"

---

### TS-002: Create and Get — full CRUD lifecycle

**Level:** Unit | **Component:** fulfillment-service | **Priority:** P0

**What it tests:** A StorageTier can be created with a valid backend association including all QoS properties, and subsequently retrieved by ID with all fields populated. Validates FR-1, FR-3, and the acceptance criterion "CreateStorageTier creates a tier with ACTIVE state and backend associations with protocol and QoS properties."

**Preconditions:**
- A `StorageBackend` exists (created via `NewPrivateStorageBackendsServer`) with known ID
- `PrivateStorageTiersServer` built with the backends DAO injected

**Steps:**
1. Create a StorageTier with name "fast", description "High-performance tier", one backend association referencing the existing backend, protocol NFS, max_read_bandwidth_mbs=1000, max_write_bandwidth_mbs=500, quota_gib=1024, encryption_enabled=true
2. Assert the response object has a non-empty generated ID
3. Assert `spec.description` equals "High-performance tier"
4. Assert `spec.backends` has exactly one element
5. Assert the backend association's `backend_id` matches the created backend
6. Assert `protocol` equals `STORAGE_PROTOCOL_NFS`
7. Assert QoS fields: max_read_bandwidth_mbs=1000, max_write_bandwidth_mbs=500, quota_gib=1024, encryption_enabled=true
8. Assert `status.state` equals `STORAGE_TIER_STATE_ACTIVE`
9. Assert `metadata.tenant` equals `auth.SharedTenant` (platform-scoped)
10. Call `Get` with the returned ID
11. Assert the Get response matches all fields from the Create response

**Expected Results:**
- Create returns a StorageTier with generated UUID ID, ACTIVE state, all QoS fields populated
- Get returns the identical object
- `metadata.creation_timestamp` is set, `metadata.deletion_timestamp` is absent

**Test Data:**

| Parameter | Value | Notes |
|-----------|-------|-------|
| metadata.name | "fast" | Tier name, immutable after creation |
| spec.description | "High-performance tier" | Human-readable description |
| backends[0].backend_id | `{created_backend_id}` | Must reference existing StorageBackend |
| backends[0].protocol | STORAGE_PROTOCOL_NFS | Enum value 1 |
| backends[0].max_read_bandwidth_mbs | 1000 | int32 |
| backends[0].max_write_bandwidth_mbs | 500 | int32 |
| backends[0].quota_gib | 1024 | int64 for petabyte-scale headroom |
| backends[0].encryption_enabled | true | Boolean flag |

**Implementation Reference:**
- Pattern: `fulfillment-service/internal/servers/private_storage_tiers_server_test.go` — `It("Creates and gets a storage tier")`
- Fixtures: `createStorageTier()` helper that creates a real StorageBackend first
- Helpers: `privatev1.StorageTier_builder{}`, `privatev1.BackendAssociation_builder{}`

**Traces to:** FR-1, FR-3, Acceptance Criteria #1 and #3

---

### TS-003: List with pagination (limit and offset)

**Level:** Unit | **Component:** fulfillment-service | **Priority:** P1

**What it tests:** `ListStorageTiers` returns paginated results using offset and limit parameters, following the established OSAC List API pattern. Validates FR-4.

**Preconditions:**
- `PrivateStorageTiersServer` built with backends DAO
- A valid StorageBackend exists

**Steps:**
1. Create 5 storage tiers with distinct names ("tier-0" through "tier-4")
2. Call `List` with no pagination — assert `size` equals 5
3. Call `List` with `limit=2` — assert `size` equals 2
4. Call `List` with `offset=2` — assert `size` equals 3
5. Call `List` with `limit=2, offset=2` — assert `size` equals 2

**Expected Results:**
- Unbounded list returns all 5 items
- Limit=2 returns exactly 2 items
- Offset=2 skips 2 items, returns remaining 3
- Combined limit+offset returns correct page

**Test Data:**

| Parameter | Value | Notes |
|-----------|-------|-------|
| tier names | "tier-0" through "tier-4" | Distinct names for uniqueness |
| limit | 2 | Page size |
| offset | 2 | Skip count |

**Implementation Reference:**
- Pattern: `fulfillment-service/internal/servers/private_storage_tiers_server_test.go` — `It("List objects with limit")`, `It("List objects with offset")`
- Fixtures: `createStorageTierWithName()` helper

**Traces to:** FR-4, Acceptance Criteria #4

---

### TS-004: List with CEL filtering

**Level:** Unit | **Component:** fulfillment-service | **Priority:** P1

**What it tests:** `ListStorageTiers` supports CEL-based filtering on fields including `id`, `metadata.name`, and `status.state`. Validates FR-4.

**Preconditions:**
- Multiple storage tiers created with distinct names and known IDs

**Steps:**
1. Create 3 storage tiers and record their IDs
2. For each ID, call `List` with filter `"this.id == '{id}'"` — assert exactly 1 result with matching ID
3. Call `List` with filter `"this.metadata.name == 'tier-0'"` — assert exactly 1 result
4. Call `List` with filter `"this.status.state == 1"` (ACTIVE) — assert all tiers returned

**Expected Results:**
- Filter by ID returns exactly the matching tier
- Filter by name returns exactly the matching tier
- Filter by state returns all active tiers

**Test Data:**

| Parameter | Value | Notes |
|-----------|-------|-------|
| filter (by ID) | `"this.id == '{id}'"` | CEL expression |
| filter (by name) | `"this.metadata.name == 'tier-0'"` | CEL expression |
| filter (by state) | `"this.status.state == 1"` | ACTIVE enum value |

**Implementation Reference:**
- Pattern: `fulfillment-service/internal/servers/private_storage_tiers_server_test.go` — `It("List objects with filter")`
- Fixtures: `createStorageTierWithName()` helper

**Traces to:** FR-4, Acceptance Criteria #4

---

### TS-005: List with ordering

**Level:** Unit | **Component:** fulfillment-service | **Priority:** P1

**What it tests:** `ListStorageTiers` supports SQL-like ordering on fields such as `metadata.name`. Validates FR-4.

**Preconditions:**
- `PrivateStorageTiersServer` built with backends DAO

**Steps:**
1. Create tier with name "zzz-tier"
2. Create tier with name "aaa-tier"
3. Call `List` with order `"metadata.name asc"`
4. Assert first item's name is "aaa-tier", second is "zzz-tier"

**Expected Results:**
- Items returned in ascending alphabetical order by name

**Test Data:**

| Parameter | Value | Notes |
|-----------|-------|-------|
| order | `"metadata.name asc"` | SQL-like ordering |
| tier names | "aaa-tier", "zzz-tier" | Deliberately reverse-alphabetical creation order |

**Implementation Reference:**
- Pattern: `fulfillment-service/internal/servers/private_storage_tiers_server_test.go` — `It("List objects with order")`

**Traces to:** FR-4

---

### TS-006: Update QoS properties via field mask

**Level:** Unit | **Component:** fulfillment-service | **Priority:** P0

**What it tests:** `UpdateStorageTier` applies partial updates to QoS properties using a FieldMask without modifying unspecified fields. Validates FR-5 and the acceptance criterion "UpdateStorageTier applies partial updates — including QoS property changes on backend associations — without modifying unspecified fields."

**Preconditions:**
- A StorageTier created with known initial QoS values (max_read_bandwidth_mbs=1000, max_write_bandwidth_mbs=500, quota_gib=1024, encryption_enabled=true)

**Steps:**
1. Call `Update` with field mask `["spec.description"]` and new description "Updated description"
2. Assert response `spec.description` equals "Updated description"
3. Assert `spec.backends[0].max_read_bandwidth_mbs` is still 1000 (unchanged)
4. Call `Update` with field mask `["spec.backends"]` and new `max_read_bandwidth_mbs=2000`
5. Assert `spec.backends[0].max_read_bandwidth_mbs` equals 2000
6. Assert `spec.description` is still "Updated description" (unchanged)
7. Call `Get` to verify the persisted state matches

**Expected Results:**
- Description update does not affect QoS properties
- QoS update does not affect description
- All unmasked fields remain unchanged

**Test Data:**

| Parameter | Value | Notes |
|-----------|-------|-------|
| update_mask | `["spec.description"]` | Partial update to description only |
| update_mask | `["spec.backends"]` | Partial update to backends/QoS only |
| new description | "Updated description" | Replaces initial value |
| new max_read_bandwidth_mbs | 2000 | Doubles initial value |

**Implementation Reference:**
- Pattern: `fulfillment-service/internal/servers/private_storage_tiers_server_test.go` — `It("Update applies partial changes via field mask")`
- Helpers: `fieldmaskpb.FieldMask{Paths: []string{...}}`

**Traces to:** FR-5, Acceptance Criteria #5

---

### TS-007: Soft delete lifecycle

**Level:** Unit | **Component:** fulfillment-service | **Priority:** P0

**What it tests:** `DeleteStorageTier` performs a soft delete — setting `deletion_timestamp` — and subsequent List calls exclude the deleted tier. Validates FR-6 and NFR-3.

**Preconditions:**
- A StorageTier created and confirmed to appear in List results

**Steps:**
1. Create a StorageTier and record its ID
2. Call `List` — assert the tier appears in results
3. Call `Delete` with the tier ID
4. Call `List` — assert the tier is excluded from results
5. Call `Get` with the tier ID — assert `NOT_FOUND` is returned

**Expected Results:**
- Delete succeeds (no error)
- Tier is excluded from subsequent List results
- Get returns NOT_FOUND for the deleted tier
- The tier data remains in the database for audit (soft delete, not hard delete)

**Implementation Reference:**
- Pattern: `fulfillment-service/internal/servers/private_storage_tiers_server_test.go` — `It("Delete")`
- Fixtures: `createStorageTier()` helper

**Traces to:** FR-6, NFR-3, Acceptance Criteria #7

---

### TS-008: Backend validation — reject non-existent backend on Create

**Level:** Unit | **Component:** fulfillment-service | **Priority:** P0

**What it tests:** `CreateStorageTier` validates that all referenced `backend_id` values exist via `storageBackendsDAO.Get()`. A reference to a non-existent backend returns `NOT_FOUND`. Validates FR-7.

**Preconditions:**
- `PrivateStorageTiersServer` built with backends DAO
- No StorageBackend exists with ID "non-existent-backend"

**Steps:**
1. Call `Create` with `backends[0].backend_id = "non-existent-backend"` and valid QoS properties
2. Assert the error has gRPC status code `NOT_FOUND`

**Expected Results:**
- Create fails with `NOT_FOUND`
- No tier is persisted in the database

**Test Data:**

| Parameter | Value | Notes |
|-----------|-------|-------|
| backend_id | "non-existent-backend" | Does not exist in storage_backends table |

**Implementation Reference:**
- Pattern: `fulfillment-service/internal/servers/private_storage_tiers_server_test.go` — `It("Rejects creation with non-existent backend")`

**Traces to:** FR-7, Acceptance Criteria #2

---

### TS-009: Backend validation — reject non-existent backend on Update

**Level:** Unit | **Component:** fulfillment-service | **Priority:** P0

**What it tests:** `UpdateStorageTier` re-validates backend references when the `backends` field is included in the update mask. Changing a backend association to reference a non-existent backend returns `NOT_FOUND`. Validates FR-7.

**Preconditions:**
- A StorageTier created with a valid backend association

**Steps:**
1. Call `Update` with field mask `["spec.backends"]` and `backends[0].backend_id = "non-existent-backend"`
2. Assert the error has gRPC status code `NOT_FOUND`
3. Call `Get` with the tier ID — assert the original backend association is unchanged

**Expected Results:**
- Update fails with `NOT_FOUND`
- Original tier data is not modified

**Test Data:**

| Parameter | Value | Notes |
|-----------|-------|-------|
| backend_id | "non-existent-backend" | Invalid backend reference |
| update_mask | `["spec.backends"]` | Targets the backends field |

**Implementation Reference:**
- Pattern: `fulfillment-service/internal/servers/private_storage_tiers_server_test.go` — `It("Rejects update with non-existent backend")`

**Traces to:** FR-7

---

### TS-010: Name immutability — reject name change on Update

**Level:** Unit | **Component:** fulfillment-service | **Priority:** P0

**What it tests:** `UpdateStorageTier` rejects attempts to change `metadata.name` after creation. The server enforces name immutability by comparing the existing name with the update payload. Validates the design doc constraint "metadata.name carries the tier name… It is immutable after creation."

**Preconditions:**
- A StorageTier created with name "fast"

**Steps:**
1. Call `Update` with field mask including `metadata.name` and new name "slow"
2. Assert the error has gRPC status code `INVALID_ARGUMENT` (immutable field violation)
3. Call `Get` — assert name is still "fast"

**Expected Results:**
- Update fails with `INVALID_ARGUMENT`
- Original name is preserved

**Test Data:**

| Parameter | Value | Notes |
|-----------|-------|-------|
| original name | "fast" | Set at creation |
| attempted name | "slow" | Immutable — change rejected |

**Implementation Reference:**
- Pattern: `fulfillment-service/internal/servers/private_storage_tiers_server_test.go` — `It("Rejects update that changes metadata.name")`

**Traces to:** Design doc — "metadata.name is immutable after creation — enforced in the server's Update method"

---

### TS-011: Name uniqueness — reject duplicate active tier names

**Level:** Unit | **Component:** fulfillment-service | **Priority:** P0

**What it tests:** The partial unique index on `storage_tiers.name` rejects creating two active tiers with the same name. The DAO translates the constraint violation to `ALREADY_EXISTS`. Validates FR-8.

**Preconditions:**
- `PrivateStorageTiersServer` built with backends DAO

**Steps:**
1. Create a StorageTier with name "standard" — assert success
2. Create another StorageTier with name "standard" — assert error
3. Assert the error has gRPC status code `ALREADY_EXISTS`

**Expected Results:**
- Second creation fails with `ALREADY_EXISTS`
- First tier remains unchanged

**Test Data:**

| Parameter | Value | Notes |
|-----------|-------|-------|
| name | "standard" | Used for both creation attempts |

**Implementation Reference:**
- Pattern: `fulfillment-service/internal/servers/private_storage_tiers_server_test.go` — `It("Rejects duplicate names for active tiers")`
- DB constraint: `storage_tiers_unique_name` partial index in migration 75

**Traces to:** FR-8, Acceptance Criteria #8

---

### TS-012: Name reuse — allow name after prior tier deleted

**Level:** Unit | **Component:** fulfillment-service | **Priority:** P1

**What it tests:** After a StorageTier is soft-deleted, its name becomes available for a new tier. The partial unique index only covers active tiers (`deletion_timestamp = 'epoch'`). Validates FR-8.

**Preconditions:**
- `PrivateStorageTiersServer` built with backends DAO

**Steps:**
1. Create a StorageTier with name "archive"
2. Delete the tier
3. Create a new StorageTier with name "archive"
4. Assert the second creation succeeds with a new ID

**Expected Results:**
- Second tier created successfully with a different ID
- Name "archive" is reused after deletion

**Implementation Reference:**
- Pattern: `fulfillment-service/internal/servers/private_storage_tiers_server_test.go` — `It("Allows name reuse after deletion")`

**Traces to:** FR-8, Acceptance Criteria #8

---

### TS-013: Optimistic concurrency — reject stale version on Update

**Level:** Unit | **Component:** fulfillment-service | **Priority:** P0

**What it tests:** When `lock = true` in the Update request, the DAO's optimistic concurrency check rejects updates with a stale metadata version, returning `ABORTED`. Validates FR-5 and the acceptance criterion "UpdateStorageTier rejects concurrent conflicting writes."

**Preconditions:**
- A StorageTier created and its initial metadata version recorded

**Steps:**
1. Create a StorageTier — record its ID and metadata version (e.g., version 1)
2. Call `Update` with `lock=true` and the correct version — assert success (now version 2)
3. Call `Update` again with `lock=true` but the original stale version (version 1)
4. Assert the error has gRPC status code `ABORTED`

**Expected Results:**
- First update succeeds (version incremented)
- Second update fails with `ABORTED` (stale version)

**Implementation Reference:**
- Pattern: `fulfillment-service/internal/servers/private_storage_tiers_server_test.go` — `It("Rejects update with stale version when lock is true")`

**Traces to:** FR-5, Acceptance Criteria #6

---

### TS-014: Single backend constraint (v0.1)

**Level:** Unit | **Component:** fulfillment-service | **Priority:** P0

**What it tests:** The v0.1 implementation validates that exactly one backend is provided in the `backends` array. Creating a tier with zero or more than one backend returns an error. Validates the design doc constraint "v0.1 validates that exactly one backend is provided."

**Preconditions:**
- `PrivateStorageTiersServer` built with backends DAO
- At least two valid StorageBackends exist

**Steps:**
1. Call `Create` with empty `backends` array — assert error
2. Call `Create` with two backend associations — assert error
3. Call `Create` with exactly one backend association — assert success

**Expected Results:**
- Zero backends: error (likely `INVALID_ARGUMENT`)
- Two backends: error (likely `INVALID_ARGUMENT`)
- One backend: success

**Test Data:**

| Parameter | Value | Notes |
|-----------|-------|-------|
| backends (zero) | `[]` | Empty array |
| backends (two) | `[{backend_id: "sb-1"}, {backend_id: "sb-2"}]` | Two backends |
| backends (one) | `[{backend_id: "sb-1"}]` | Single backend — v0.1 valid |

**Implementation Reference:**
- Pattern: `fulfillment-service/internal/servers/private_storage_tiers_server_test.go` — `It("Rejects creation with zero backends")`, `It("Rejects creation with more than one backend")`

**Traces to:** Design doc — "v0.1 validates that exactly one backend is provided"

---

### TS-015: Create sets state to ACTIVE

**Level:** Unit | **Component:** fulfillment-service | **Priority:** P1

**What it tests:** On Create, the server sets `status.state` to `STORAGE_TIER_STATE_ACTIVE` regardless of any state value in the request. Validates FR-9.

**Preconditions:**
- `PrivateStorageTiersServer` built with backends DAO

**Steps:**
1. Create a StorageTier (do not set state explicitly in the request)
2. Assert `status.state` equals `STORAGE_TIER_STATE_ACTIVE`

**Expected Results:**
- Tier is created with ACTIVE state

**Implementation Reference:**
- Pattern: `fulfillment-service/internal/servers/private_storage_tiers_server_test.go` — assertion within `It("Creates and gets a storage tier")`

**Traces to:** FR-9, Acceptance Criteria #1

---

### TS-016: Event payload — setPayload() StorageTier case

**Level:** Unit | **Component:** fulfillment-service | **Priority:** P1

**What it tests:** The `setPayload()` switch statement in `generic_server.go` includes the `*privatev1.StorageTier` case, so that Create/Update/Delete operations emit event notifications with the StorageTier payload. Validates the design doc requirement "Add `case *privatev1.StorageTier: event.SetStorageTier(object)` to the `setPayload()` switch statement."

**Preconditions:**
- `PrivateStorageTiersServer` built with a notifier (mock or real)

**Steps:**
1. Create a StorageTier
2. Capture the event emitted by the notifier
3. Assert the event's `StorageTier` payload is set and matches the created object

**Expected Results:**
- Event notification emitted on Create with the StorageTier object as payload
- The payload type is `*privatev1.StorageTier`

**Implementation Reference:**
- Pattern: `fulfillment-service/internal/servers/generic_server_test.go` — event payload tests
- Source: `fulfillment-service/internal/servers/generic_server.go` — `setPayload()` switch statement

**Traces to:** Design doc — "generic_server.go change: Add `case *privatev1.StorageTier: event.SetStorageTier(object)` to `setPayload()`"

---

### TS-017: Migration — helper table and trigger creation

**Level:** Unit | **Component:** fulfillment-service | **Priority:** P0

**What it tests:** Migration 76 (`add_storage_tier_ref_triggers.up.sql`) creates the `storage_tier_backends` helper table, the `materialize_storage_tier_backends` function and trigger, the `check_storage_tier_backend_refs` function and trigger, and the `check_storage_backend_not_in_use_by_tier` function and trigger. Validates the database migration section of the design doc.

**Preconditions:**
- PostgreSQL test database with migrations 1-75 applied (including storage_backends and storage_tiers tables)

**Steps:**
1. Apply migration 76
2. Query `pg_catalog.pg_class` — assert `storage_tier_backends` table exists
3. Query `information_schema.routines` — assert `materialize_storage_tier_backends` function exists
4. Query `information_schema.routines` — assert `check_storage_tier_backend_refs` function exists
5. Query `information_schema.routines` — assert `check_storage_backend_not_in_use_by_tier` function exists
6. Query `information_schema.triggers` — assert all three triggers exist on their respective tables

**Expected Results:**
- Helper table created with composite PK `(storage_tier_id, backend_id)`
- All three functions registered
- All three triggers active

**Implementation Reference:**
- Pattern: `fulfillment-service/internal/database/migrations/76_add_storage_tier_ref_triggers_test.go`
- Migration: `fulfillment-service/internal/database/migrations/76_add_storage_tier_ref_triggers.up.sql`

**Traces to:** Design doc — Database Migration section, "Referential integrity triggers migration"

---

### TS-018: Migration — materialization trigger populates helper table

**Level:** Unit | **Component:** fulfillment-service | **Priority:** P0

**What it tests:** The `materialize_storage_tier_backends` trigger extracts backend IDs from the JSONB `data` column and inserts them into the `storage_tier_backends` helper table on every INSERT/UPDATE. Validates the design doc's materialized helper table pattern.

**Preconditions:**
- Migration 76 applied
- A StorageBackend row exists in `storage_backends`

**Steps:**
1. Insert a StorageTier row with `data` containing a `backends` array with `backendId: "sb-1"`
2. Query `storage_tier_backends` — assert one row exists with `storage_tier_id` = tier ID and `backend_id` = "sb-1"
3. Update the StorageTier row to change `backendId` to "sb-2" (after inserting backend "sb-2")
4. Query `storage_tier_backends` — assert the old row is replaced: one row with `backend_id` = "sb-2"

**Expected Results:**
- INSERT materializes backend IDs into helper table
- UPDATE re-materializes (deletes old rows, inserts new)
- Helper table always reflects current state

**Implementation Reference:**
- Pattern: `fulfillment-service/internal/database/migrations/76_add_storage_tier_ref_triggers_test.go` — `It("Materializes backend IDs on insert")`
- Migration: `fulfillment-service/internal/database/migrations/76_add_storage_tier_ref_triggers.up.sql` — `materialize_storage_tier_backends()` function

**Traces to:** Design doc — "Materialize backend IDs from JSONB on every insert/update"

---

### TS-019: Migration — backend ref trigger rejects invalid backend

**Level:** Unit | **Component:** fulfillment-service | **Priority:** P0

**What it tests:** The `check_storage_tier_backend_refs` BEFORE INSERT/UPDATE trigger rejects StorageTier rows that reference a non-existent or soft-deleted StorageBackend. The trigger raises SQLSTATE `Z0002`. Validates the referential integrity design.

**Preconditions:**
- Migration 76 applied
- No StorageBackend with ID "non-existent" exists

**Steps:**
1. Attempt to INSERT a StorageTier with `backends[0].backendId = "non-existent"`
2. Assert the insert fails with SQLSTATE `Z0002` and message containing "does not exist or has been deleted"
3. Insert a StorageBackend "sb-1", then soft-delete it (set `deletion_timestamp != 'epoch'`)
4. Attempt to INSERT a StorageTier referencing "sb-1" — assert failure with Z0002

**Expected Results:**
- Trigger prevents referencing non-existent backends
- Trigger prevents referencing soft-deleted backends
- Error code is Z0002

**Test Data:**

| Parameter | Value | Notes |
|-----------|-------|-------|
| backend_id | "non-existent" | No matching row in storage_backends |
| backend_id | "sb-1" (soft-deleted) | Row exists but deletion_timestamp != 'epoch' |
| SQLSTATE | Z0002 | Custom error code for ref not found |

**Implementation Reference:**
- Pattern: `fulfillment-service/internal/database/migrations/76_add_storage_tier_ref_triggers_test.go` — `It("Prevents insert with non-existent backend")`, `It("Prevents insert referencing soft-deleted backend")`
- Comparable: `fulfillment-service/internal/database/migrations/55_add_virtual_network_child_ref_triggers_test.go`

**Traces to:** Design doc — "BEFORE INSERT/UPDATE trigger validates backend existence with FOR SHARE locking"

---

### TS-020: Migration — backend deletion blocked by active tier

**Level:** Unit | **Component:** fulfillment-service | **Priority:** P0

**What it tests:** The `check_storage_backend_not_in_use_by_tier` BEFORE UPDATE trigger on `storage_backends` prevents soft-deleting a StorageBackend that is referenced by any active StorageTier. The trigger raises SQLSTATE `Z0003`. Validates FR-10.

**Preconditions:**
- Migration 76 applied
- A StorageBackend "sb-1" exists
- A StorageTier referencing "sb-1" exists and is active (not soft-deleted)

**Steps:**
1. Attempt to soft-delete "sb-1" by updating `deletion_timestamp` to a non-epoch value
2. Assert the update fails with SQLSTATE `Z0003`
3. Assert the error message contains "cannot delete StorageBackend" and the count of referencing tiers

**Expected Results:**
- Backend deletion blocked with Z0003
- Error message includes the backend ID and count of referencing tiers

**Test Data:**

| Parameter | Value | Notes |
|-----------|-------|-------|
| SQLSTATE | Z0003 | Custom error code for "in use" |
| tier count | 1 | Number of active tiers referencing the backend |

**Implementation Reference:**
- Pattern: `fulfillment-service/internal/database/migrations/76_add_storage_tier_ref_triggers_test.go` — `It("Prevents soft-delete of referenced backend")`

**Traces to:** FR-10, Acceptance Criteria #10

---

### TS-021: Migration — backend deletion allowed when unreferenced

**Level:** Unit | **Component:** fulfillment-service | **Priority:** P1

**What it tests:** A StorageBackend with no active StorageTier references can be soft-deleted normally. The trigger only blocks deletion when active tiers reference the backend.

**Preconditions:**
- Migration 76 applied
- A StorageBackend "sb-2" exists with no StorageTier references

**Steps:**
1. Soft-delete "sb-2" by updating `deletion_timestamp`
2. Assert the update succeeds

**Expected Results:**
- Backend soft-delete succeeds
- No trigger error raised

**Implementation Reference:**
- Pattern: `fulfillment-service/internal/database/migrations/76_add_storage_tier_ref_triggers_test.go` — `It("Allows delete of unused backend")`

**Traces to:** FR-10 (inverse case)

---

### TS-022: Migration — backend deletion allowed when referencing tier is soft-deleted

**Level:** Unit | **Component:** fulfillment-service | **Priority:** P1

**What it tests:** A StorageBackend can be soft-deleted if all StorageTiers that reference it have already been soft-deleted. The trigger joins `storage_tier_backends` with `storage_tiers` and only counts active tiers.

**Preconditions:**
- Migration 76 applied
- A StorageBackend "sb-1" exists
- A StorageTier referencing "sb-1" exists but has been soft-deleted

**Steps:**
1. Create backend "sb-1" and tier referencing it
2. Soft-delete the tier (set `deletion_timestamp` to non-epoch)
3. Soft-delete "sb-1"
4. Assert the backend deletion succeeds

**Expected Results:**
- Backend soft-delete succeeds because only soft-deleted tiers reference it

**Implementation Reference:**
- Pattern: `fulfillment-service/internal/database/migrations/76_add_storage_tier_ref_triggers_test.go` — `It("Allows delete when referencing tiers are already deleted")`

**Traces to:** FR-10 (edge case — only active refs block deletion)

---

### TS-030: Full CRUD lifecycle via gRPC client

**Level:** IT | **Component:** fulfillment-service | **Priority:** P0

**What it tests:** The complete StorageTier CRUD lifecycle through the real gRPC transport layer — Create, Get, List, Update, Delete — against a kind cluster with PostgreSQL. Validates FR-1, FR-2 (gRPC path), and Acceptance Criteria #11.

**Preconditions:**
- Kind cluster `fulfillment-service-it` running with PostgreSQL, Keycloak, Envoy
- Fulfillment-service deployed with StorageTier gRPC server registered
- `/etc/hosts` entries for `fulfillment-internal-api.osac.svc.cluster.local`
- A StorageBackend created via the private gRPC API

**Steps:**
1. Connect to the private gRPC endpoint via `privatev1.NewStorageTiersClient(tool.InternalView().AdminConn())`
2. Also create a StorageBackend via `privatev1.NewStorageBackendsClient(tool.InternalView().AdminConn())` and record its ID
3. Call `Create` with a unique tier name (e.g., `"it-tier-{uuid}"`), description, and a backend association referencing the created backend
4. Assert: response has generated ID, ACTIVE state, all QoS fields match
5. Call `Get` with the returned ID — assert all fields match
6. Call `List` — assert the tier appears in results
7. Call `Update` with field mask `["spec.description"]` — assert description updated
8. Call `Delete` with the tier ID — assert no error
9. Call `Get` with the tier ID — assert `NOT_FOUND`
10. Use `DeferCleanup` to ensure the backend is deleted after the test

**Expected Results:**
- All CRUD operations succeed via gRPC transport
- Create returns a tier with generated ID and ACTIVE state
- Update applies partial changes
- Delete soft-deletes the tier (excluded from List/Get)

**Test Data:**

| Parameter | Value | Notes |
|-----------|-------|-------|
| tier name | `"it-tier-{uuid}"` | Unique per test run |
| backend name | `"it-backend-{uuid}"` | Required for backend association |

**Implementation Reference:**
- Pattern: `fulfillment-service/it/it_private_instance_types_test.go` — `Describe("Private instance types")` for gRPC client lifecycle
- Setup: `fulfillment-service/it/it_tool.go` — `tool.InternalView().AdminConn()` for private gRPC connection
- Suite: `fulfillment-service/it/it_suite_test.go`

**Traces to:** FR-1, FR-2, Acceptance Criteria #11

---

### TS-031: Full CRUD lifecycle via REST endpoints

**Level:** IT | **Component:** fulfillment-service | **Priority:** P0

**What it tests:** The complete StorageTier CRUD lifecycle through the REST gateway (grpc-gateway) using HTTP methods mapped to gRPC RPCs: POST, GET, GET (list), PATCH, DELETE at `/api/private/v1/storage_tiers`. Validates FR-2 (REST transcoding path) and Acceptance Criteria #11.

**Preconditions:**
- Kind cluster running with REST gateway deployed
- `/etc/hosts` entries configured
- A StorageBackend created via REST

**Steps:**
1. POST `/api/private/v1/storage_tiers` with JSON body `{object: {metadata: {name: "it-rest-tier-{uuid}"}, spec: {description: "REST test", backends: [{backend_id: "{id}", protocol: "STORAGE_PROTOCOL_NFS", ...}]}}}` — assert HTTP 200 with created object
2. GET `/api/private/v1/storage_tiers/{id}` — assert HTTP 200 with matching fields
3. GET `/api/private/v1/storage_tiers` — assert the tier appears in the list
4. PATCH `/api/private/v1/storage_tiers/{id}` with `{object: {id: "{id}", spec: {description: "Updated"}}, update_mask: "spec.description"}` — assert HTTP 200
5. DELETE `/api/private/v1/storage_tiers/{id}` — assert HTTP 200
6. GET `/api/private/v1/storage_tiers/{id}` — assert HTTP 404

**Expected Results:**
- All HTTP methods map correctly to gRPC RPCs
- REST transcoding annotations in `storage_tiers_service.proto` produce correct routes
- JSON serialization/deserialization of proto messages works correctly

**Implementation Reference:**
- Pattern: `fulfillment-service/it/it_tool.go` — HTTP client helpers
- Proto: `fulfillment-service/proto/private/osac/private/v1/storage_tiers_service.proto` — `google.api.http` annotations

**Traces to:** FR-2, Acceptance Criteria #11

---

### TS-032: Referential integrity — backend deletion blocked via gRPC

**Level:** IT | **Component:** fulfillment-service | **Priority:** P0

**What it tests:** End-to-end referential integrity: creating a StorageTier that references a StorageBackend prevents the backend from being deleted. The Z0003 trigger error is translated to `FAILED_PRECONDITION` at the gRPC layer. Validates FR-10 and Acceptance Criteria #10.

**Preconditions:**
- Kind cluster running with fulfillment-service deployed
- gRPC client connected to private endpoint

**Steps:**
1. Create a StorageBackend via gRPC and record its ID
2. Create a StorageTier referencing the backend
3. Attempt to Delete the StorageBackend via gRPC
4. Assert the error has gRPC status code `FAILED_PRECONDITION`
5. Assert the error message indicates the backend is in use
6. Delete the StorageTier first, then delete the StorageBackend
7. Assert the second backend deletion succeeds

**Expected Results:**
- Backend deletion blocked with `FAILED_PRECONDITION` while tier references it
- Backend deletion succeeds after tier is deleted

**Implementation Reference:**
- Pattern: `fulfillment-service/internal/database/migrations/76_add_storage_tier_ref_triggers_test.go` — trigger-level test
- IT pattern: `fulfillment-service/it/it_private_instance_types_test.go` — gRPC client usage

**Traces to:** FR-10, Acceptance Criteria #10

---

### TS-033: Name uniqueness via gRPC endpoint

**Level:** IT | **Component:** fulfillment-service | **Priority:** P0

**What it tests:** The name uniqueness constraint works end-to-end through the gRPC transport. Creating two tiers with the same name returns `ALREADY_EXISTS`, and name reuse after deletion succeeds. Validates FR-8.

**Preconditions:**
- Kind cluster running with fulfillment-service deployed
- gRPC client connected to private endpoint

**Steps:**
1. Create a StorageTier with name "it-unique-{uuid}" — assert success
2. Create another StorageTier with the same name — assert `ALREADY_EXISTS`
3. Delete the first tier
4. Create a StorageTier with the same name again — assert success (new ID)

**Expected Results:**
- Duplicate active names rejected with `ALREADY_EXISTS`
- Deleted tier names can be reused

**Implementation Reference:**
- Pattern: `fulfillment-service/it/it_private_instance_types_test.go`
- DB constraint: `storage_tiers_unique_name` partial index

**Traces to:** FR-8, Acceptance Criteria #8

---

### TS-034: Helper table materialization after Create and Update

**Level:** IT | **Component:** fulfillment-service | **Priority:** P1

**What it tests:** The `storage_tier_backends` helper table is correctly populated after StorageTier Create and Update operations via the gRPC API. This verifies the materialization trigger works end-to-end through the full server stack.

**Preconditions:**
- Kind cluster running with PostgreSQL
- Direct PostgreSQL access for verification queries (via port-forward or `kubectl exec`)

**Steps:**
1. Create a StorageTier referencing backend "sb-1" via gRPC
2. Query `storage_tier_backends` table — assert one row with the tier's ID and backend_id "sb-1"
3. Update the tier to reference a different backend "sb-2"
4. Query `storage_tier_backends` — assert one row with backend_id "sb-2" (old row replaced)

**Expected Results:**
- Helper table is correctly materialized on Create
- Helper table is correctly re-materialized on Update
- Old rows are cleaned up during re-materialization

**Implementation Reference:**
- Pattern: `fulfillment-service/internal/database/migrations/76_add_storage_tier_ref_triggers_test.go`

**Traces to:** Design doc — "storage_tier_backends helper table enables efficient reverse lookup"

---

### TS-035: Optimistic concurrency via gRPC endpoint

**Level:** IT | **Component:** fulfillment-service | **Priority:** P1

**What it tests:** Optimistic concurrency control works end-to-end through the gRPC transport. Two concurrent updates to the same tier with the same initial version — only the first succeeds, the second gets `ABORTED`. Validates FR-5 and Acceptance Criteria #6.

**Preconditions:**
- Kind cluster running with fulfillment-service deployed
- gRPC client connected to private endpoint

**Steps:**
1. Create a StorageTier and record its metadata version
2. Call `Update` with `lock=true` and the correct version — assert success
3. Call `Update` with `lock=true` and the original (now stale) version — assert `ABORTED`

**Expected Results:**
- First update succeeds, version incremented
- Second update rejected with `ABORTED`

**Implementation Reference:**
- Pattern: `fulfillment-service/it/it_private_instance_types_test.go`

**Traces to:** FR-5, Acceptance Criteria #6

---

### TS-040: StorageTier private API CRUD lifecycle (E2E)

**Level:** E2E | **Component:** osac-test-infra | **Priority:** P0

**What it tests:** The full StorageTier CRUD lifecycle via the private gRPC API on a live OSAC deployment. This is the primary E2E validation that the feature works in a production-like environment. Validates FR-1 through FR-6 end-to-end.

**Preconditions:**
- OSAC cluster deployed with fulfillment-service including StorageTier support
- `private_grpc` fixture connected to the fulfillment-service private endpoint
- A StorageBackend must exist (created in test setup or pre-existing)

**Steps:**
1. Create a StorageBackend via `private_grpc.call(service="osac.private.v1.StorageBackends/Create", data={...})`
2. Create a StorageTier via `private_grpc.call(service="osac.private.v1.StorageTiers/Create", data={"object": {"metadata": {"name": "e2e-tier-{unique}"}, "spec": {"description": "E2E test tier", "backends": [{"backend_id": "{sb_id}", "protocol": 1, "max_read_bandwidth_mbs": 1000, "max_write_bandwidth_mbs": 500, "quota_gib": 1024, "encryption_enabled": true}]}}})`
3. Assert the response contains a generated ID and state `ACTIVE`
4. Get the tier via `private_grpc.call(service="osac.private.v1.StorageTiers/Get", data={"id": "{tier_id}"})` — assert all fields match
5. List tiers via `private_grpc.call(service="osac.private.v1.StorageTiers/List", data={})` — assert the created tier appears
6. Update QoS via `private_grpc.call(service="osac.private.v1.StorageTiers/Update", data={"object": {"id": "{tier_id}", "spec": {"description": "Updated"}}, "update_mask": "spec.description"})` — assert description updated
7. Delete the tier via `private_grpc.call(service="osac.private.v1.StorageTiers/Delete", data={"id": "{tier_id}"})` — assert no error
8. Verify deletion: call Get — assert error code indicates not found
9. Clean up: delete the StorageBackend

**Expected Results:**
- Full CRUD lifecycle succeeds on a live OSAC deployment
- All fields are correctly persisted and retrievable
- Soft delete excludes tier from Get and List

**Test Data:**

| Parameter | Value | Notes |
|-----------|-------|-------|
| tier name | `"e2e-tier-{uuid}"` | Unique per test run |
| backend provider | "vast" | Matches StorageBackend provider type |
| protocol | 1 (NFS) | StorageProtocol enum |
| max_read_bandwidth_mbs | 1000 | QoS property |
| max_write_bandwidth_mbs | 500 | QoS property |
| quota_gib | 1024 | QoS property |
| encryption_enabled | true | QoS property |

**Implementation Reference:**
- Pattern: `osac-test-infra/tests/catalog/test_catalog_item_lifecycle.py` — `test_catalog_item_crud()` for private API CRUD pattern
- Client: `osac-test-infra/tests/core/grpc_client.py` — `call()` and `call_unchecked()` generic methods (new `StorageTiers`/`StorageBackends` wrapper methods should be added)
- Fixtures: `osac-test-infra/tests/conftest.py` — `private_grpc` session fixture

**Traces to:** FR-1 through FR-6, Acceptance Criteria #1, #3, #4, #5, #7, #11

---

### TS-041: Backend reference validation — reject invalid backend (E2E)

**Level:** E2E | **Component:** osac-test-infra | **Priority:** P0

**What it tests:** `CreateStorageTier` and `UpdateStorageTier` reject references to non-existent StorageBackend IDs on a live OSAC deployment. Validates FR-7 end-to-end.

**Preconditions:**
- OSAC cluster deployed with fulfillment-service
- `private_grpc` fixture connected
- No StorageBackend with ID "non-existent-backend-id" exists

**Steps:**
1. Call `StorageTiers/Create` with `backends[0].backend_id = "non-existent-backend-id"`
2. Assert the call fails with a gRPC error (NOT_FOUND or equivalent)
3. Create a valid StorageBackend and StorageTier
4. Call `StorageTiers/Update` changing `backend_id` to "non-existent-backend-id"
5. Assert the update fails
6. Clean up: delete tier and backend

**Expected Results:**
- Create with invalid backend fails
- Update with invalid backend fails
- No StorageTier is persisted with an invalid backend reference

**Implementation Reference:**
- Pattern: `osac-test-infra/tests/catalog/test_catalog_item_lifecycle.py` — error assertion patterns using `call_unchecked()`
- Helpers: `osac-test-infra/tests/core/helpers.py` — `assert_grpc_rejected()`

**Traces to:** FR-7, Acceptance Criteria #2

---

### TS-042: StorageBackend deletion blocked by StorageTier (E2E)

**Level:** E2E | **Component:** osac-test-infra | **Priority:** P0

**What it tests:** Deleting a StorageBackend that is referenced by an active StorageTier is rejected on a live OSAC deployment. The referential integrity trigger (Z0003) surfaces as a gRPC error. Validates FR-10 and Acceptance Criteria #10.

**Preconditions:**
- OSAC cluster deployed
- `private_grpc` fixture connected

**Steps:**
1. Create a StorageBackend and record its ID
2. Create a StorageTier referencing the backend
3. Attempt to delete the StorageBackend via `StorageBackends/Delete`
4. Assert the call fails (FAILED_PRECONDITION or equivalent error)
5. Delete the StorageTier first
6. Delete the StorageBackend — assert success this time
7. Verify the backend is gone via `StorageBackends/Get`

**Expected Results:**
- Backend deletion blocked while active tier references it
- Backend deletion succeeds after tier is deleted
- Correct ordering: delete tier first, then backend

**Implementation Reference:**
- Pattern: `osac-test-infra/tests/catalog/test_catalog_item_lifecycle.py` — `test_delete_catalog_item_blocked_when_referenced()`
- Client: `osac-test-infra/tests/core/grpc_client.py` — `call_unchecked()` for error checking

**Traces to:** FR-10, Acceptance Criteria #10

---

### TS-043: Name uniqueness and reuse after deletion (E2E)

**Level:** E2E | **Component:** osac-test-infra | **Priority:** P1

**What it tests:** The name uniqueness constraint and name reuse after soft deletion work correctly on a live OSAC deployment. Validates FR-8 and Acceptance Criteria #8.

**Preconditions:**
- OSAC cluster deployed
- `private_grpc` fixture connected
- A valid StorageBackend exists

**Steps:**
1. Create a StorageTier with name "e2e-unique-{uuid}" — assert success
2. Attempt to create another StorageTier with the same name — assert error (ALREADY_EXISTS)
3. Delete the first tier
4. Create a StorageTier with the same name — assert success with new ID
5. Clean up: delete the second tier and the backend

**Expected Results:**
- Duplicate active name rejected with ALREADY_EXISTS
- Deleted name reusable

**Implementation Reference:**
- Pattern: `osac-test-infra/tests/catalog/test_catalog_item_lifecycle.py`
- Client: `osac-test-infra/tests/core/grpc_client.py` — `call_unchecked()`

**Traces to:** FR-8, Acceptance Criteria #8

---

### TS-044: Pagination and CEL filtering on List (E2E)

**Level:** E2E | **Component:** osac-test-infra | **Priority:** P1

**What it tests:** `ListStorageTiers` pagination (offset/limit) and CEL-based filtering work correctly on a live OSAC deployment. Validates FR-4 and Acceptance Criteria #4.

**Preconditions:**
- OSAC cluster deployed
- `private_grpc` fixture connected
- A valid StorageBackend exists

**Steps:**
1. Create 3 StorageTiers with distinct names ("e2e-page-0", "e2e-page-1", "e2e-page-2")
2. Call `StorageTiers/List` with `limit=2` — assert response contains exactly 2 items
3. Call `StorageTiers/List` with `offset=1` — assert response contains 2 items (skipped first)
4. Call `StorageTiers/List` with `filter="this.metadata.name == 'e2e-page-1'"` — assert exactly 1 result with matching name
5. Clean up: delete all 3 tiers and the backend

**Expected Results:**
- Limit restricts result count
- Offset skips items
- CEL filter returns only matching items

**Implementation Reference:**
- Pattern: `osac-test-infra/tests/catalog/test_catalog_item_lifecycle.py`
- Client: `osac-test-infra/tests/core/grpc_client.py` — `call()` with `data={"limit": 2}` or `data={"filter": "..."}`

**Traces to:** FR-4, Acceptance Criteria #4

---

## 5. Persona Coverage

| Persona | Scenarios | Coverage |
|---------|-----------|----------|
| Cloud Provider Admin | TS-002 through TS-015, TS-030 through TS-035, TS-040 through TS-044 | Full CRUD lifecycle, validation, referential integrity, concurrency — the Cloud Provider Admin is the sole actor for StorageTier management via the private API |
| Cloud Infrastructure Admin | — | Not directly affected — StorageTier is managed by Cloud Provider Admins. Cloud Infrastructure Admins manage StorageBackends (OSAC-1111) which are the dependency. |
| Tenant Admin | — | Not affected — tenants discover assigned tiers through the Tenant CR status (OSAC-23), not by querying StorageTier directly |
| Tenant User | — | Not affected — tenants have no access to the private StorageTier API |

## 6. Risk-Based Prioritization

| Risk Area | Priority | Scenarios | Rationale |
|-----------|----------|-----------|-----------|
| Referential integrity (backend ↔ tier) | HIGH | TS-008, TS-009, TS-019, TS-020, TS-032, TS-041, TS-042 | Database triggers enforce cross-entity constraints; failures could cause orphaned references or block legitimate operations. TOCTOU race protection via FOR SHARE locking must work correctly. |
| Name uniqueness constraint | HIGH | TS-011, TS-012, TS-033, TS-043 | The partial unique index on active tiers prevents duplicate offerings. A broken constraint could cause admin confusion and downstream OSAC-23 ambiguity. |
| CRUD lifecycle correctness | HIGH | TS-002, TS-006, TS-007, TS-030, TS-031, TS-040 | Core API functionality — Create, Get, List, Update, Delete must work at all test levels. Data integrity in PostgreSQL JSONB storage. |
| Backend validation on Create/Update | HIGH | TS-008, TS-009, TS-014, TS-041 | Server-side validation prevents invalid backend references and enforces the v0.1 single-backend constraint. |
| Optimistic concurrency control | MEDIUM | TS-013, TS-035 | Stale version detection prevents lost updates. Important for multi-admin environments but race conditions are less likely in the current deployment model. |
| Name immutability | MEDIUM | TS-010 | Prevents accidental tier renaming that could break downstream references. |
| Helper table materialization | MEDIUM | TS-017, TS-018, TS-034 | The materialized helper table must stay in sync with JSONB data for efficient reverse lookups. Stale data could cause incorrect referential integrity checks. |
| Pagination and filtering | LOW | TS-003, TS-004, TS-005, TS-044 | Standard List API patterns inherited from GenericServer. Lower risk because the generic implementation is well-tested across other resources. |
| Event notifications | LOW | TS-016 | setPayload() coverage ensures downstream consumers can react to StorageTier changes. Low risk as the pattern is established for all other entity types. |

## 7. Coverage Gaps

| Requirement | Gap | Reason | Risk |
|-------------|-----|--------|------|
| Tenant-reference trigger (Z0003 on StorageTier deletion) | Not testable — trigger deferred to OSAC-23 | The trigger preventing StorageTier deletion when tenants reference it depends on the Tenant proto schema for storage tier assignments, which is not yet finalized | LOW — No protection gap exists because no tenants can reference tiers until OSAC-23 lands |
| Signal RPC | No dedicated test scenario | Signal RPC is part of the generic server and has no StorageTier-specific behavior. The generic Signal implementation is tested in `generic_server_test.go` | LOW — Signal behavior is inherited from GenericServer with no customization |
| Multi-backend tiers | Not testable — deferred beyond v0.1 | v0.1 explicitly limits tiers to a single backend association. TS-014 validates the constraint is enforced | NONE — Multi-backend is a future feature |
| QoS update propagation to StorageClass | Not testable — OSAC-23 responsibility | QoS property changes on StorageTier do not directly trigger StorageClass updates. The OSAC Storage Controller (OSAC-23) handles this lifecycle | LOW — Out of scope for OSAC-1110; tracked under OSAC-23 |
| gRPC client wrapper methods for E2E | Infra gap — new methods needed | `osac-test-infra/tests/core/grpc_client.py` has no `StorageTiers` or `StorageBackends` wrapper methods | MEDIUM — E2E tests (TS-040 through TS-044) can use the generic `call()` method, but dedicated wrappers improve readability and maintainability |

## 8. Implementation Notes

- **Fixtures needed:**
  - `osac-test-infra/tests/core/grpc_client.py` — Add `create_storage_backend()`, `get_storage_backend()`, `list_storage_backend_ids()`, `delete_storage_backend()` methods for `osac.private.v1.StorageBackends` service
  - `osac-test-infra/tests/core/grpc_client.py` — Add `create_storage_tier()`, `get_storage_tier()`, `list_storage_tier_ids()`, `update_storage_tier()`, `delete_storage_tier()` methods for `osac.private.v1.StorageTiers` service
  - `osac-test-infra/tests/storage/conftest.py` — Add a `storage_backend` fixture that creates and cleans up a test StorageBackend
  - No new K8sClient methods needed — StorageTier is DB-backed with no CRD

- **Infra gaps:**
  - Integration tests (`fulfillment-service/it/`) — No StorageTier or StorageBackend IT test files exist yet. New file `it_private_storage_tiers_test.go` needed, following the pattern in `it_private_instance_types_test.go`
  - E2E tests (`osac-test-infra/tests/storage/`) — New file `test_storage_tier_api.py` needed for TS-040 through TS-044
  - IT test infrastructure may need a pre-seeded StorageBackend or a setup step to create one

- **Reference tests:**
  - Unit: `fulfillment-service/internal/servers/private_storage_tiers_server_test.go` (existing, 754 lines)
  - Unit: `fulfillment-service/internal/servers/private_storage_backends_server_test.go` (existing, 666 lines)
  - Migration: `fulfillment-service/internal/database/migrations/76_add_storage_tier_ref_triggers_test.go` (existing, 275 lines)
  - IT pattern: `fulfillment-service/it/it_private_instance_types_test.go` (existing)
  - E2E pattern: `osac-test-infra/tests/catalog/test_catalog_item_lifecycle.py` (existing)
  - E2E storage: `osac-test-infra/tests/storage/test_tenant_storage_lifecycle.py` (existing)

- **Jira tracking:** Create sub-tasks under OSAC-1110 for:
  - Unit tests: TS-001 through TS-016 (most already implemented in `private_storage_tiers_server_test.go`)
  - Migration tests: TS-017 through TS-022 (most already implemented in `76_add_storage_tier_ref_triggers_test.go`)
  - IT tests: TS-030 through TS-035 (new — `it_private_storage_tiers_test.go`)
  - E2E tests: TS-040 through TS-044 (new — `test_storage_tier_api.py` + GRPCClient methods)
