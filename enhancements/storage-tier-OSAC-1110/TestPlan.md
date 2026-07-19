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

This test plan validates the StorageTier private gRPC API (`osac.private.v1.StorageTiers`) introduced by OSAC-1110. StorageTier is a DB-backed catalog entity in the fulfillment-service that binds named storage offerings to registered StorageBackends (OSAC-1111) with typed QoS properties. The plan covers the full CRUD lifecycle, backend reference validation, referential integrity triggers, name uniqueness, optimistic concurrency, and input validation across unit, integration, database migration, and E2E test levels. Key risk areas are referential integrity between StorageTier and StorageBackend, the materialized helper table trigger chain, and the v0.1 single-backend constraint.

## 2. Component Impact

| Component | Test Levels | Rationale |
|-----------|------------|-----------|
| fulfillment-service | Unit / IT / Migration | Hosts the `PrivateStorageTiersServer`, `GenericServer`, DAO, database migrations, and referential integrity triggers. All CRUD logic, validation, and persistence live here. |
| osac-test-infra | E2E | Validates the StorageTier private gRPC API against a live OSAC cluster, exercising the full stack (gRPC → server → DAO → PostgreSQL → triggers). |

## 3. Test Scenario Index

| ID | Level | Component | Scenario | Priority |
|----|-------|-----------|----------|----------|
| TS-001 | Unit | fulfillment-service | Create and Get StorageTier with valid backend | P0 |
| TS-002 | Unit | fulfillment-service | List StorageTiers with pagination and filtering | P1 |
| TS-003 | Unit | fulfillment-service | Update StorageTier QoS properties via field mask | P0 |
| TS-004 | Unit | fulfillment-service | Delete StorageTier (soft delete) | P0 |
| TS-005 | Unit | fulfillment-service | Reject create with non-existent backend ID | P0 |
| TS-006 | Unit | fulfillment-service | Reject create with more than one backend (v0.1) | P0 |
| TS-007 | Unit | fulfillment-service | Reject update changing metadata.name (immutable) | P0 |
| TS-008 | Unit | fulfillment-service | Reject update with stale version (optimistic lock) | P0 |
| TS-009 | Unit | fulfillment-service | Enforce name uniqueness among active tiers | P0 |
| TS-010 | Unit | fulfillment-service | Validate required fields on Create | P1 |
| TS-011 | Unit | fulfillment-service | Force state to ACTIVE and tenant to shared on Create | P1 |
| TS-012 | Unit | fulfillment-service | Signal RPC delegates to GenericServer | P2 |
| TS-013 | Unit | fulfillment-service | Builder rejects missing required dependencies | P1 |
| TS-014 | Migration | fulfillment-service | Create storage_tiers and archived_storage_tiers tables | P0 |
| TS-015 | Migration | fulfillment-service | Materialize backend IDs into helper table on insert/update | P0 |
| TS-016 | Migration | fulfillment-service | Reject tier referencing non-existent or deleted backend (Z0002) | P0 |
| TS-017 | Migration | fulfillment-service | Block StorageBackend soft-delete when referenced by active tier (Z0003) | P0 |
| TS-018 | Migration | fulfillment-service | Allow backend deletion when referencing tiers are already deleted | P1 |
| TS-019 | Migration | fulfillment-service | Enforce name/id/tenant immutability via column triggers | P1 |
| TS-020 | IT | fulfillment-service | Full CRUD lifecycle via gRPC against kind cluster | P0 |
| TS-021 | IT | fulfillment-service | Referential integrity: backend deletion blocked by active tier | P0 |
| TS-022 | IT | fulfillment-service | Name uniqueness via gRPC and name reuse after deletion | P0 |
| TS-023 | IT | fulfillment-service | REST endpoint accessibility via grpc-gateway | P1 |
| TS-024 | E2E | osac-test-infra | StorageTier CRUD lifecycle via private gRPC | P0 |
| TS-025 | E2E | osac-test-infra | Backend reference validation via private gRPC | P0 |
| TS-026 | E2E | osac-test-infra | StorageTier list pagination and CEL filtering | P1 |
| TS-027 | E2E | osac-test-infra | Name uniqueness and duplicate rejection | P1 |

## 4. Detailed Test Descriptions

---

### TS-001: Create and Get StorageTier with valid backend

**Level:** Unit | **Component:** fulfillment-service | **Priority:** P0

**What it tests:** Validates the happy-path Create and Get RPCs for StorageTier. A tier is created with a valid StorageBackend reference and QoS properties, then retrieved by ID. Verifies that all spec fields (description, backend association with protocol, bandwidth, quota, encryption) and metadata (name, state, timestamps) are correctly persisted and returned. Traces to FR-1, FR-3.

**Preconditions:**
- In-memory PostgreSQL database created via `server.MakeDatabase()` with `dao.CreateTables[*privatev1.StorageTier]` and `dao.CreateTables[*privatev1.StorageBackend]`
- A StorageBackend entity pre-created via `storageBackendsServer.Create()` to provide a valid `backend_id`
- `PrivateStorageTiersServer` built with all required dependencies (logger, tenancy, attribution, notifier, storageBackendsDAO)

**Steps:**
1. Call `Create` with a `StorageTier` object containing `metadata.name = "fast"`, `spec.description = "Fast NVMe tier"`, and a single `BackendAssociation` referencing the pre-created backend ID with `protocol = STORAGE_PROTOCOL_BLOCK`, `max_read_bandwidth_mbs = 1000`, `max_write_bandwidth_mbs = 500`, `quota_gib = 1024`, `encryption_enabled = true`.
2. Extract the returned `StorageTier.id` from the Create response.
3. Call `Get` with the returned ID.
4. Assert all fields on the Get response.

**Expected Results:**
- Create returns a `StorageTier` with a generated UUID (not the caller-provided value), `status.state = STORAGE_TIER_STATE_ACTIVE`, and `metadata.tenant = "~"` (shared tenant).
- Get returns the same object with `spec.description = "Fast NVMe tier"`, `spec.backends[0].backend_id` matching the pre-created backend, `spec.backends[0].protocol = STORAGE_PROTOCOL_BLOCK`, `spec.backends[0].max_read_bandwidth_mbs = 1000`, `spec.backends[0].max_write_bandwidth_mbs = 500`, `spec.backends[0].quota_gib = 1024`, `spec.backends[0].encryption_enabled = true`.
- `metadata.creation_timestamp` is populated with a non-zero value.

**Test Data:**

| Parameter | Value | Notes |
|-----------|-------|-------|
| metadata.name | `"fast"` | Tier offering name, immutable after creation |
| spec.description | `"Fast NVMe tier"` | Human-readable description |
| spec.backends[0].protocol | `STORAGE_PROTOCOL_BLOCK` | Enum value 2 |
| spec.backends[0].max_read_bandwidth_mbs | `1000` | int32 MB/s |
| spec.backends[0].max_write_bandwidth_mbs | `500` | int32 MB/s |
| spec.backends[0].quota_gib | `1024` | int64 GiB (1 TiB) |
| spec.backends[0].encryption_enabled | `true` | Data-at-rest encryption |

**Implementation Reference:**
- Pattern: `fulfillment-service/internal/servers/private_storage_tiers_server_test.go` — `"Creates and gets a storage tier"` test
- Pattern: `fulfillment-service/internal/servers/private_storage_backends_server_test.go` — `createStorageBackend()` helper
- Fixtures: `server.MakeDatabase()` — creates in-memory PostgreSQL; `dao.CreateTables[T]()` — applies migrations
- Helpers: `createStorageTier()` — helper that creates a backend, then creates a tier referencing it

**Traces to:** FR-1 (StorageTiers gRPC service with CRUD RPCs), FR-3 (Create accepts name, description, backend associations with protocol and QoS), NFR-1 (creation timestamp)

---

### TS-002: List StorageTiers with pagination and filtering

**Level:** Unit | **Component:** fulfillment-service | **Priority:** P1

**What it tests:** Validates List RPC with `offset`, `limit`, CEL `filter`, and `order` parameters. Ensures paginated results are correct and CEL expressions can filter by field values. Traces to FR-4.

**Preconditions:**
- Five StorageTier entities created with distinct names (`"tier-1"` through `"tier-5"`) referencing valid backends
- `PrivateStorageTiersServer` built and ready

**Steps:**
1. Call `List` with no parameters — assert 5 items returned.
2. Call `List` with `limit = 2` — assert exactly 2 items returned and `size` indicates total count.
3. Call `List` with `offset = 3, limit = 10` — assert 2 items returned (items 4 and 5).
4. Call `List` with `filter = "metadata.name == 'tier-3'"` — assert exactly 1 item returned with matching name.
5. Call `List` with `order = "metadata.name asc"` — assert items returned in alphabetical order.

**Expected Results:**
- Unbounded list returns all 5 items.
- `limit = 2` returns exactly 2 items.
- `offset = 3` skips the first 3 items.
- CEL filter `metadata.name == 'tier-3'` returns exactly 1 match.
- Ordering by `metadata.name asc` returns items in alphabetical order.

**Test Data:**

| Parameter | Value | Notes |
|-----------|-------|-------|
| Total tiers | 5 | Named `tier-1` through `tier-5` |
| limit | `2` | Tests pagination boundary |
| offset | `3` | Tests offset into result set |
| filter | `"metadata.name == 'tier-3'"` | CEL expression |
| order | `"metadata.name asc"` | SQL-like ordering |

**Implementation Reference:**
- Pattern: `fulfillment-service/internal/servers/private_storage_tiers_server_test.go` — `"List objects"`, `"List objects with limit"`, `"List objects with offset"`, `"List objects with filter"`, `"List objects with order"` tests
- Pattern: `fulfillment-service/internal/servers/private_storage_backends_server_test.go` — same List test patterns

**Traces to:** FR-4 (List supports pagination, CEL filtering, ordering)

---

### TS-003: Update StorageTier QoS properties via field mask

**Level:** Unit | **Component:** fulfillment-service | **Priority:** P0

**What it tests:** Validates partial updates using `FieldMask` — changing QoS properties on a backend association without affecting unspecified fields. Also tests replacing the entire backends array. Traces to FR-5.

**Preconditions:**
- A StorageTier created with `spec.description = "Original"`, `spec.backends[0].max_read_bandwidth_mbs = 1000`, `spec.backends[0].protocol = STORAGE_PROTOCOL_BLOCK`
- `PrivateStorageTiersServer` built and ready

**Steps:**
1. Call `Update` with `update_mask = {paths: ["spec.description"]}` and `object.spec.description = "Updated description"`.
2. Call `Get` and verify `spec.description = "Updated description"` while `spec.backends[0].max_read_bandwidth_mbs` remains `1000`.
3. Call `Update` with `object.spec.backends` replaced — new backend association with `protocol = STORAGE_PROTOCOL_NFS`, `max_read_bandwidth_mbs = 2000`, `max_write_bandwidth_mbs = 1000`, `quota_gib = 2048`, `encryption_enabled = false`.
4. Call `Get` and verify all backend fields are updated.

**Expected Results:**
- After step 2: `spec.description` is `"Updated description"`, `spec.backends` unchanged.
- After step 4: `spec.backends[0].protocol = STORAGE_PROTOCOL_NFS`, `spec.backends[0].max_read_bandwidth_mbs = 2000`, `spec.backends[0].max_write_bandwidth_mbs = 1000`, `spec.backends[0].quota_gib = 2048`, `spec.backends[0].encryption_enabled = false`.
- `metadata.name` remains unchanged in both updates.

**Test Data:**

| Parameter | Value | Notes |
|-----------|-------|-------|
| update_mask (step 1) | `["spec.description"]` | Partial update — only description |
| new description | `"Updated description"` | Replaces original |
| new protocol (step 3) | `STORAGE_PROTOCOL_NFS` | Changed from BLOCK to NFS |
| new max_read_bandwidth_mbs | `2000` | Doubled from 1000 |

**Implementation Reference:**
- Pattern: `fulfillment-service/internal/servers/private_storage_tiers_server_test.go` — `"Update applies partial changes via field mask"`, `"Update backends replaces the backend association"` tests
- Pattern: `fulfillment-service/internal/servers/private_storage_backends_server_test.go` — `"Update applies partial changes via field mask"` test

**Traces to:** FR-5 (partial updates, QoS property changes, optimistic concurrency)

---

### TS-004: Delete StorageTier (soft delete)

**Level:** Unit | **Component:** fulfillment-service | **Priority:** P0

**What it tests:** Validates that Delete performs a soft-delete (sets `deletion_timestamp`), that subsequent Get returns `NOT_FOUND`, and that List excludes the deleted tier. Traces to FR-6.

**Preconditions:**
- A StorageTier created via `Create` with a valid backend reference
- `PrivateStorageTiersServer` built and ready

**Steps:**
1. Call `Delete` with the tier's ID.
2. Call `Get` with the same ID.
3. Call `List` with no filters.

**Expected Results:**
- Delete returns successfully (no error).
- Get returns gRPC status `NOT_FOUND`.
- List results do not contain the deleted tier's ID.

**Implementation Reference:**
- Pattern: `fulfillment-service/internal/servers/private_storage_tiers_server_test.go` — `"Delete removes the object"` test
- Pattern: `fulfillment-service/internal/servers/private_storage_backends_server_test.go` — Delete test

**Traces to:** FR-6 (soft delete, excluded from List, preserved for audit)

---

### TS-005: Reject create with non-existent backend ID

**Level:** Unit | **Component:** fulfillment-service | **Priority:** P0

**What it tests:** Validates that Create rejects a StorageTier when the `backend_id` in the BackendAssociation does not match any registered StorageBackend. The server performs `DAO.Get` on each backend_id before persisting. Traces to FR-7.

**Preconditions:**
- `PrivateStorageTiersServer` built with a storageBackendsDAO that has no backends registered
- No StorageBackend with ID `"no-such-backend"` exists

**Steps:**
1. Call `Create` with `spec.backends[0].backend_id = "no-such-backend"`.
2. Capture the error response.

**Expected Results:**
- Create returns gRPC status `NOT_FOUND`.
- Error message contains `"no-such-backend"`.
- No StorageTier row is persisted (verified by List returning 0 items).

**Test Data:**

| Parameter | Value | Notes |
|-----------|-------|-------|
| backend_id | `"no-such-backend"` | Non-existent backend ID |

**Implementation Reference:**
- Pattern: `fulfillment-service/internal/servers/private_storage_tiers_server_test.go` — `"Create with non-existent backend_id fails"` test
- Helpers: `validateBackends()` method in `private_storage_tiers_server.go`

**Traces to:** FR-7 (validate referenced StorageBackend IDs exist)

---

### TS-006: Reject create with more than one backend (v0.1)

**Level:** Unit | **Component:** fulfillment-service | **Priority:** P0

**What it tests:** Validates the v0.1 constraint that exactly one backend per tier is enforced. The `backends` field is `repeated` in proto for future multi-backend support, but the server rejects requests with more than one entry. Traces to design section "v0.1: single backend per tier".

**Preconditions:**
- Two StorageBackend entities pre-created with valid IDs `backend-1` and `backend-2`
- `PrivateStorageTiersServer` built and ready

**Steps:**
1. Call `Create` with `spec.backends` containing two `BackendAssociation` entries referencing `backend-1` and `backend-2`.
2. Capture the error response.

**Expected Results:**
- Create returns gRPC status `INVALID_ARGUMENT`.
- Error message contains `"one backend"` (indicating v0.1 single-backend constraint).

**Test Data:**

| Parameter | Value | Notes |
|-----------|-------|-------|
| spec.backends | 2 entries | `backend-1` and `backend-2` |

**Implementation Reference:**
- Pattern: `fulfillment-service/internal/servers/private_storage_tiers_server_test.go` — `"Create with more than one backend fails in v0.1"` test
- Pattern: Same file — `"Update with more than one backend fails in v0.1"` test

**Traces to:** Design doc "v0.1 validates that exactly one backend is provided"

---

### TS-007: Reject update changing metadata.name (immutable)

**Level:** Unit | **Component:** fulfillment-service | **Priority:** P0

**What it tests:** Validates that the server rejects Update requests that attempt to change `metadata.name`, which is immutable after creation. Traces to design section "metadata.name is immutable after creation".

**Preconditions:**
- A StorageTier created with `metadata.name = "fast"`
- `PrivateStorageTiersServer` built and ready

**Steps:**
1. Call `Update` with `object.metadata.name = "slow"` (different from original `"fast"`).
2. Capture the error response.
3. Call `Get` to verify the original name is preserved.

**Expected Results:**
- Update returns gRPC status `INVALID_ARGUMENT`.
- Error message contains `"immutable"`.
- Get confirms `metadata.name` is still `"fast"`.

**Implementation Reference:**
- Pattern: `fulfillment-service/internal/servers/private_storage_tiers_server_test.go` — `"Update changing metadata.name fails"` test
- Pattern: `fulfillment-service/internal/servers/private_storage_backends_server_test.go` — `"Update changing metadata.name fails"` test

**Traces to:** Design doc "metadata.name is immutable after creation — enforced in the server's Update method"

---

### TS-008: Reject update with stale version (optimistic lock)

**Level:** Unit | **Component:** fulfillment-service | **Priority:** P0

**What it tests:** Validates optimistic concurrency control. When `lock = true` in the Update request, the DAO compares the `metadata.version` field against the stored version. A stale version triggers an `ABORTED` error. Traces to FR-5.

**Preconditions:**
- A StorageTier created and its current `metadata.version` noted
- `PrivateStorageTiersServer` built and ready

**Steps:**
1. Call `Update` with `lock = true` and `object.metadata.version` set to an outdated value (e.g., version 0 when current is version 1).
2. Capture the error response.

**Expected Results:**
- Update returns gRPC status `ABORTED`.
- The StorageTier remains unchanged (Get returns original values).

**Test Data:**

| Parameter | Value | Notes |
|-----------|-------|-------|
| lock | `true` | Enables optimistic concurrency check |
| metadata.version | `0` (stale) | Does not match current version |

**Implementation Reference:**
- Pattern: `fulfillment-service/internal/servers/private_storage_tiers_server_test.go` — `"Update with stale version and lock=true fails"` test
- Pattern: `fulfillment-service/internal/servers/private_storage_backends_server_test.go` — `"Update with stale version and lock=true fails"` test

**Traces to:** FR-5 (optimistic concurrency control to prevent conflicting writes)

---

### TS-009: Enforce name uniqueness among active tiers

**Level:** Unit | **Component:** fulfillment-service | **Priority:** P0

**What it tests:** Validates the partial unique index `storage_tiers_unique_name` that enforces name uniqueness among active (non-deleted) tiers. Also verifies that a deleted tier's name can be reused. Traces to FR-8.

**Preconditions:**
- `PrivateStorageTiersServer` built and ready
- A valid StorageBackend pre-created

**Steps:**
1. Call `Create` with `metadata.name = "standard"` — succeeds.
2. Call `Create` with `metadata.name = "standard"` (duplicate) — capture error.
3. Call `Delete` on the first tier.
4. Call `Create` with `metadata.name = "standard"` (reuse after delete) — assert success.

**Expected Results:**
- Step 1: Create succeeds, returns `StorageTier` with `metadata.name = "standard"`.
- Step 2: Create returns gRPC status `ALREADY_EXISTS`.
- Step 4: Create succeeds — name reuse after soft-delete is allowed.

**Implementation Reference:**
- Pattern: `fulfillment-service/internal/servers/private_storage_tiers_server_test.go` — `"Create with duplicate active name fails"`, `"Create after delete of same name succeeds"` tests
- Migration: `fulfillment-service/internal/database/migrations/75_create_storage_tiers_tables.up.sql` — `storage_tiers_unique_name` partial unique index

**Traces to:** FR-8 (unique names among active tiers, name reuse after deletion)

---

### TS-010: Validate required fields on Create

**Level:** Unit | **Component:** fulfillment-service | **Priority:** P1

**What it tests:** Validates that Create rejects requests missing mandatory fields: `metadata.name`, `spec.backends`, and `spec.backends[].backend_id`. Also validates rejection of nil `object`. Traces to FR-3.

**Preconditions:**
- `PrivateStorageTiersServer` built and ready
- A valid StorageBackend pre-created

**Steps:**
1. Call `Create` with `metadata.name` empty — capture error.
2. Call `Create` with `spec.backends` empty — capture error.
3. Call `Create` with `spec.backends[0].backend_id` empty — capture error.
4. Call `Create` with `object = nil` — capture error.

**Expected Results:**
- Step 1: `INVALID_ARGUMENT`, message contains `"metadata.name"`.
- Step 2: `INVALID_ARGUMENT`, message contains `"backends"`.
- Step 3: `INVALID_ARGUMENT`, message contains `"backend_id"`.
- Step 4: `INVALID_ARGUMENT`, message contains `"storage tier is mandatory"`.

**Implementation Reference:**
- Pattern: `fulfillment-service/internal/servers/private_storage_tiers_server_test.go` — `"Create without name fails"`, `"Create without backends fails"`, `"Create with empty backend_id fails"`, `"Create with nil object fails"` tests

**Traces to:** FR-3 (Create must accept name, description, backend associations)

---

### TS-011: Force state to ACTIVE and tenant to shared on Create

**Level:** Unit | **Component:** fulfillment-service | **Priority:** P1

**What it tests:** Validates that Create overrides any caller-provided `status.state` with `STORAGE_TIER_STATE_ACTIVE` and forces `metadata.tenant` to the shared tenant (`"~"`). Also validates UUID generation ignoring caller-provided ID. Traces to FR-3, FR-9.

**Preconditions:**
- `PrivateStorageTiersServer` built and ready
- A valid StorageBackend pre-created

**Steps:**
1. Call `Create` with `id = "my-custom-id"`, `status.state = STORAGE_TIER_STATE_UNSPECIFIED`, `metadata.tenant = "tenant-1"`.
2. Inspect the returned StorageTier.

**Expected Results:**
- `id` is a generated UUID, not `"my-custom-id"`.
- `status.state` is `STORAGE_TIER_STATE_ACTIVE` regardless of the caller-provided value.
- `metadata.tenant` is `"~"` (shared/platform-scoped), not `"tenant-1"`.

**Test Data:**

| Parameter | Value | Notes |
|-----------|-------|-------|
| id (caller) | `"my-custom-id"` | Ignored; server generates UUID |
| status.state (caller) | `UNSPECIFIED` | Overridden to `ACTIVE` |
| metadata.tenant (caller) | `"tenant-1"` | Forced to `"~"` (shared) |

**Implementation Reference:**
- Pattern: `fulfillment-service/internal/servers/private_storage_tiers_server_test.go` — `"Generates UUID for id"`, `"Create always sets state to ACTIVE"`, `"Create forces tenant to shared"` tests
- Pattern: `fulfillment-service/internal/servers/private_storage_backends_server_test.go` — same state/tenant forcing pattern

**Traces to:** FR-3 (initial state ACTIVE), FR-9 (StorageTier state includes ACTIVE), design doc (platform-scoped entity)

---

### TS-012: Signal RPC delegates to GenericServer

**Level:** Unit | **Component:** fulfillment-service | **Priority:** P2

**What it tests:** Validates that the Signal RPC is registered and delegates to the embedded `GenericServer.Signal()` method. Signal enables future consumption by the OSAC Storage Controller. Traces to design Goals ("Include Signal RPC").

**Preconditions:**
- A StorageTier created via `Create`
- `PrivateStorageTiersServer` built and ready

**Steps:**
1. Call `Signal` with the tier's ID and a signal payload.
2. Verify the call does not return an error.

**Expected Results:**
- Signal returns successfully (delegates to `GenericServer.Signal()`).
- No `UNIMPLEMENTED` error.

**Implementation Reference:**
- Pattern: `fulfillment-service/internal/servers/private_storage_tiers_server.go` — `Signal()` method delegates to `s.server.Signal()`
- Pattern: `fulfillment-service/internal/servers/generic_server.go` — `Signal()` implementation

**Traces to:** Design doc Goals ("Include Signal RPC to support future consumption by the OSAC Storage Controller")

---

### TS-013: Builder rejects missing required dependencies

**Level:** Unit | **Component:** fulfillment-service | **Priority:** P1

**What it tests:** Validates that `PrivateStorageTiersServerBuilder.Build()` returns an error when mandatory dependencies are not set: logger, tenancy logic, and storageBackendsDAO. Ensures the builder pattern enforces correct initialization. Traces to design section (builder pattern).

**Preconditions:**
- None (tests builder validation before any server is constructed)

**Steps:**
1. Call `NewPrivateStorageTiersServer()` without calling `SetLogger()` — attempt `Build()`.
2. Call `NewPrivateStorageTiersServer()` without calling `SetTenancyLogic()` — attempt `Build()`.
3. Call `NewPrivateStorageTiersServer()` without calling `SetStorageBackendsDAO()` — attempt `Build()`.
4. Call `NewPrivateStorageTiersServer()` with all required setters — attempt `Build()`.

**Expected Results:**
- Steps 1-3: `Build()` returns a non-nil error indicating the missing dependency.
- Step 4: `Build()` succeeds, returns a valid server instance.

**Implementation Reference:**
- Pattern: `fulfillment-service/internal/servers/private_storage_tiers_server_test.go` — `"Can be built if all required parameters are set"`, `"Fails if logger is not set"`, `"Fails if tenancy logic is not set"`, `"Fails if storage backends DAO is not set"` tests
- Pattern: `fulfillment-service/internal/servers/private_storage_backends_server_test.go` — builder validation tests

**Traces to:** Design doc (builder pattern: `PrivateStorageTiersServerBuilder` with `SetLogger`, `SetNotifier`, `SetAttributionLogic`, `SetTenancyLogic`, `SetMetricsRegisterer`)

---

### TS-014: Create storage_tiers and archived_storage_tiers tables

**Level:** Migration | **Component:** fulfillment-service | **Priority:** P0

**What it tests:** Validates that migration 75 creates the `storage_tiers` table with all required columns (id, name, creation_timestamp, deletion_timestamp, finalizers, creator, tenant, labels, annotations, data), the `archived_storage_tiers` table, all required indexes (by_name, by_owner, by_tenant, by_label GIN), and the partial unique index `storage_tiers_unique_name`. Traces to design section (Database Migration).

**Preconditions:**
- Database at migration level 74 (pre-StorageTier)
- Migration 62 (storage_backends tables) already applied

**Steps:**
1. Apply migration 75.
2. Insert a row into `storage_tiers` with valid data — verify success.
3. Query the row count — verify 1.
4. Attempt to insert a row with an invalid `tenant` FK reference — verify constraint violation.
5. Insert two rows with the same `name` where both have `deletion_timestamp = 'epoch'` — verify unique constraint violation.

**Expected Results:**
- Migration applies without error.
- `storage_tiers` table accepts valid inserts.
- FK constraint on `tenant` is enforced.
- Partial unique index prevents duplicate active names.

**Implementation Reference:**
- Pattern: `fulfillment-service/internal/database/migrations/75_create_storage_tiers_tables_test.go` — `"Creates the storage_tiers table"`, `"Rejects invalid tenant reference"`, `"Enforces name uniqueness"`, `"Enforces immutability of id, name, and tenant"` tests
- Migration: `fulfillment-service/internal/database/migrations/75_create_storage_tiers_tables.up.sql`

**Traces to:** Design doc Database Migration section (storage_tiers table DDL, indexes, unique name constraint)

---

### TS-015: Materialize backend IDs into helper table on insert/update

**Level:** Migration | **Component:** fulfillment-service | **Priority:** P0

**What it tests:** Validates the `materialize_storage_tier_backends` trigger that extracts `backend_id` values from the JSONB `data->'spec'->'backends'` array and populates the `storage_tier_backends` helper table on every insert or update of an active storage tier. Traces to design section (materialized helper table pattern).

**Preconditions:**
- Database at migration level 76 (ref triggers applied)
- At least two StorageBackend rows pre-inserted

**Steps:**
1. Insert a `storage_tiers` row with JSONB data containing `spec.backends` with 1 backend reference.
2. Query `storage_tier_backends` — verify 1 row with correct `storage_tier_id` and `backend_id`.
3. Update the tier's JSONB data to reference a different backend.
4. Query `storage_tier_backends` — verify the old row is replaced with the new backend reference.

**Expected Results:**
- After insert: `storage_tier_backends` has exactly 1 row mapping tier to backend.
- After update: old mapping is deleted and new mapping is inserted (trigger does `DELETE` then `INSERT`).
- Helper table has correct composite PK `(storage_tier_id, backend_id)`.

**Implementation Reference:**
- Pattern: `fulfillment-service/internal/database/migrations/76_add_storage_tier_ref_triggers_test.go` — `"Materializes backend references into the helper table on insert"` test
- Migration: `fulfillment-service/internal/database/migrations/76_add_storage_tier_ref_triggers.up.sql` — `materialize_storage_tier_backends()` function

**Traces to:** Design doc ("storage_tier_backends helper table enables efficient reverse lookup")

---

### TS-016: Reject tier referencing non-existent or deleted backend (Z0002)

**Level:** Migration | **Component:** fulfillment-service | **Priority:** P0

**What it tests:** Validates the `check_storage_tier_backend_refs` BEFORE INSERT/UPDATE trigger that validates all `backend_id` values in a StorageTier's JSONB data exist as active (non-deleted) rows in `storage_backends`. Uses `FOR SHARE` locking to prevent TOCTOU races. Traces to FR-7.

**Preconditions:**
- Database at migration level 76
- One active StorageBackend and one soft-deleted StorageBackend

**Steps:**
1. Insert a `storage_tiers` row referencing a `backend_id` that does not exist in `storage_backends` — capture error.
2. Insert a `storage_tiers` row referencing the soft-deleted backend — capture error.
3. Insert a `storage_tiers` row referencing the active backend — verify success.

**Expected Results:**
- Step 1: PostgreSQL raises exception with SQLSTATE `Z0002` and message containing the non-existent backend ID.
- Step 2: PostgreSQL raises exception with SQLSTATE `Z0002` and message indicating the backend is deleted.
- Step 3: Insert succeeds.

**Test Data:**

| Parameter | Value | Notes |
|-----------|-------|-------|
| SQLSTATE | `Z0002` | Custom code for missing/deleted reference |
| Locking | `FOR SHARE` | Prevents TOCTOU race with concurrent backend deletion |

**Implementation Reference:**
- Pattern: `fulfillment-service/internal/database/migrations/76_add_storage_tier_ref_triggers_test.go` — `"Prevents creating a storage tier referencing a non-existent backend"`, `"Prevents creating a storage tier referencing a soft-deleted backend"` tests
- Migration: `fulfillment-service/internal/database/migrations/76_add_storage_tier_ref_triggers.up.sql` — `check_storage_tier_backend_refs()` function

**Traces to:** FR-7 (Create and Update must validate that all referenced StorageBackend IDs exist)

---

### TS-017: Block StorageBackend soft-delete when referenced by active tier (Z0003)

**Level:** Migration | **Component:** fulfillment-service | **Priority:** P0

**What it tests:** Validates the `check_storage_backend_not_in_use_by_tier` BEFORE UPDATE trigger on `storage_backends` that prevents soft-deleting a backend when active (non-deleted) StorageTiers reference it. Traces to FR-10.

**Preconditions:**
- Database at migration level 76
- A StorageBackend created, then a StorageTier created referencing it via `storage_tier_backends` helper table

**Steps:**
1. Attempt to soft-delete the StorageBackend (update `deletion_timestamp` from `'epoch'` to `now()`).
2. Capture the error.
3. Verify the backend remains active (deletion_timestamp = 'epoch').

**Expected Results:**
- Soft-delete raises PostgreSQL exception with SQLSTATE `Z0003`.
- Error message contains the backend ID and count of referencing tiers (e.g., `"1 StorageTier(s) still reference it"`).
- Backend row is not modified (trigger rolls back the UPDATE).

**Implementation Reference:**
- Pattern: `fulfillment-service/internal/database/migrations/76_add_storage_tier_ref_triggers_test.go` — `"Prevents soft-deleting a backend referenced by an active storage tier"`, `"Reports the count of referencing storage tiers"` tests
- Migration: `fulfillment-service/internal/database/migrations/76_add_storage_tier_ref_triggers.up.sql` — `check_storage_backend_not_in_use_by_tier()` function

**Traces to:** FR-10 (Deleting a StorageBackend must be rejected if any active StorageTier references it)

---

### TS-018: Allow backend deletion when referencing tiers are already deleted

**Level:** Migration | **Component:** fulfillment-service | **Priority:** P1

**What it tests:** Validates the edge case where a StorageBackend can be soft-deleted when all StorageTiers that previously referenced it have already been soft-deleted. The trigger joins `storage_tier_backends` with `storage_tiers` and only counts tiers with `deletion_timestamp = 'epoch'`. Traces to FR-10 boundary condition.

**Preconditions:**
- Database at migration level 76
- A StorageBackend created, a StorageTier created referencing it, then the tier soft-deleted

**Steps:**
1. Soft-delete the StorageTier (set `deletion_timestamp = now()`).
2. Attempt to soft-delete the StorageBackend.

**Expected Results:**
- Step 2 succeeds — no `Z0003` error because no active tiers reference the backend.
- Backend `deletion_timestamp` is updated to a non-epoch value.

**Implementation Reference:**
- Pattern: `fulfillment-service/internal/database/migrations/76_add_storage_tier_ref_triggers_test.go` — `"Allows soft-deleting a backend when referencing tiers are already deleted"` test

**Traces to:** FR-10 (referential integrity check considers only active tiers)

---

### TS-019: Enforce name/id/tenant immutability via column triggers

**Level:** Migration | **Component:** fulfillment-service | **Priority:** P1

**What it tests:** Validates the database-level immutability triggers on `storage_tiers` that prevent changes to `id`, `name`, and `tenant` columns after initial creation. These triggers complement the server-level immutability check. Traces to design doc ("metadata.name is immutable after creation").

**Preconditions:**
- Database at migration level 75
- A `storage_tiers` row inserted with `id = "st-1"`, `name = "fast"`, `tenant = "~"`

**Steps:**
1. Attempt `UPDATE storage_tiers SET name = 'slow' WHERE id = 'st-1'` — capture error.
2. Attempt `UPDATE storage_tiers SET id = 'st-2' WHERE id = 'st-1'` — capture error.
3. Attempt `UPDATE storage_tiers SET tenant = 'tenant-1' WHERE id = 'st-1'` — capture error.

**Expected Results:**
- All three UPDATE attempts fail with a constraint violation raised by the immutability trigger.
- Original values are preserved.

**Implementation Reference:**
- Pattern: `fulfillment-service/internal/database/migrations/75_create_storage_tiers_tables_test.go` — `"Enforces immutability of id, name, and tenant"` test
- Migration: `fulfillment-service/internal/database/migrations/75_create_storage_tiers_tables.up.sql` — column immutability triggers

**Traces to:** Design doc ("metadata.name is immutable after creation")

---

### TS-020: Full CRUD lifecycle via gRPC against kind cluster

**Level:** IT | **Component:** fulfillment-service | **Priority:** P0

**What it tests:** End-to-end CRUD lifecycle of StorageTier via gRPC against a real kind cluster with PostgreSQL. Validates Create, Get, List, Update (with field mask), and Delete through the full server stack including interceptors, DAO, and database. Traces to FR-1, FR-2 (gRPC endpoints).

**Preconditions:**
- Kind cluster `fulfillment-service-it` running with PostgreSQL, Keycloak, and Envoy
- `/etc/hosts` entries configured for `fulfillment-api.osac.svc.cluster.local`
- A StorageBackend pre-created via the private StorageBackends gRPC API

**Steps:**
1. Create a `privatev1.StorageTiersClient` using `tool.InternalView().AdminConn()`.
2. Call `Create` with `metadata.name = "it-tier-{uuid}"`, `spec.description = "Integration test tier"`, one `BackendAssociation` referencing the pre-created backend.
3. Register `DeferCleanup` to delete the tier after the test.
4. Call `Get` by ID — verify all fields match the Create response.
5. Call `List` — verify the created tier appears in results.
6. Call `Update` with `update_mask = {paths: ["spec.description"]}` and `spec.description = "Updated"`.
7. Call `Get` — verify description is `"Updated"`, other fields unchanged.
8. Call `Delete` by ID.
9. Call `Get` — verify `NOT_FOUND`.

**Expected Results:**
- All CRUD operations succeed through the full gRPC stack.
- Create returns a valid UUID as ID with `status.state = ACTIVE`.
- Update applies partial changes correctly.
- Delete soft-deletes; subsequent Get returns `NOT_FOUND`.

**Test Data:**

| Parameter | Value | Notes |
|-----------|-------|-------|
| metadata.name | `"it-tier-{uuid}"` | UUID suffix for test isolation |
| gRPC client | `privatev1.NewStorageTiersClient(tool.InternalView().AdminConn())` | Admin connection to private API |

**Implementation Reference:**
- Pattern: `fulfillment-service/it/it_private_instance_types_test.go` — full CRUD lifecycle test for private InstanceTypes API
- Pattern: `fulfillment-service/it/it_private_host_types_test.go` — same pattern for HostTypes
- Helpers: `tool.InternalView().AdminConn()` — admin gRPC connection; `DeferCleanup` — Ginkgo cleanup
- Registration: `fulfillment-service/internal/cmd/service/start/grpcserver/start_grpc_server_cmd.go` — `privatev1.RegisterStorageTiersServer()` registration

**Traces to:** FR-1 (StorageTiers gRPC service with CRUD RPCs), FR-2 (gRPC endpoints)

---

### TS-021: Referential integrity: backend deletion blocked by active tier

**Level:** IT | **Component:** fulfillment-service | **Priority:** P0

**What it tests:** End-to-end referential integrity through the full gRPC stack: creating a StorageTier that references a StorageBackend, then attempting to delete the backend. Validates that the database trigger `check_storage_backend_not_in_use_by_tier` propagates the Z0003 error through the DAO and gRPC server as a `FAILED_PRECONDITION` status. Traces to FR-10.

**Preconditions:**
- Kind cluster running with PostgreSQL
- StorageBackends and StorageTiers gRPC clients created via `tool.InternalView().AdminConn()`

**Steps:**
1. Create a StorageBackend via the StorageBackends gRPC client.
2. Create a StorageTier referencing the backend via the StorageTiers gRPC client.
3. Attempt to delete the StorageBackend via the StorageBackends gRPC client.
4. Capture the error response.
5. Delete the StorageTier first, then retry deleting the StorageBackend.

**Expected Results:**
- Step 3: Delete returns gRPC status `FAILED_PRECONDITION` (Z0003 translated by DAO).
- Error message indicates the backend is in use by StorageTier(s).
- Step 5: After deleting the tier, the backend deletion succeeds.

**Implementation Reference:**
- Pattern: `fulfillment-service/it/it_private_instance_types_test.go` — deletion protection test pattern
- Pattern: `fulfillment-service/internal/database/migrations/76_add_storage_tier_ref_triggers_test.go` — trigger-level test for same behavior

**Traces to:** FR-10 (Deleting a StorageBackend must be rejected if any StorageTier references it)

---

### TS-022: Name uniqueness via gRPC and name reuse after deletion

**Level:** IT | **Component:** fulfillment-service | **Priority:** P0

**What it tests:** End-to-end name uniqueness through the full gRPC stack: creating two tiers with the same name is rejected, but after deleting the first tier, the name can be reused. Validates the partial unique index behavior through the DAO's error translation to `ALREADY_EXISTS`. Traces to FR-8.

**Preconditions:**
- Kind cluster running with PostgreSQL
- StorageTiers gRPC client created

**Steps:**
1. Create tier with `metadata.name = "unique-test-{uuid}"`.
2. Create another tier with the same `metadata.name` — capture error.
3. Delete the first tier.
4. Create a tier with `metadata.name = "unique-test-{uuid}"` — verify success.

**Expected Results:**
- Step 2: Create returns gRPC status `ALREADY_EXISTS`.
- Step 4: Create succeeds — name reuse after deletion is allowed.

**Implementation Reference:**
- Pattern: `fulfillment-service/it/it_private_instance_types_test.go` — name uniqueness tests
- Pattern: `fulfillment-service/internal/servers/private_storage_tiers_server_test.go` — unit-level name uniqueness tests

**Traces to:** FR-8 (unique names among active tiers, name reuse after deletion)

---

### TS-023: REST endpoint accessibility via grpc-gateway

**Level:** IT | **Component:** fulfillment-service | **Priority:** P1

**What it tests:** Validates that all StorageTier CRUD operations are accessible via REST endpoints through the grpc-gateway. The proto service definition includes `google.api.http` annotations mapping RPCs to REST paths. Traces to FR-2.

**Preconditions:**
- Kind cluster running with REST gateway (Envoy) configured
- A StorageBackend pre-created
- HTTP client configured with admin authentication

**Steps:**
1. `POST /api/private/v1/storage_tiers` with JSON body — verify 200 and created object.
2. `GET /api/private/v1/storage_tiers/{id}` — verify 200 and object fields.
3. `GET /api/private/v1/storage_tiers` — verify 200 and list response.
4. `PATCH /api/private/v1/storage_tiers/{id}` with JSON body — verify 200 and updated object.
5. `DELETE /api/private/v1/storage_tiers/{id}` — verify 200.

**Expected Results:**
- All HTTP methods return 200 with correct JSON response bodies.
- REST responses match the gRPC response structure (via grpc-gateway transcoding).

**Test Data:**

| Endpoint | Method | Notes |
|----------|--------|-------|
| `/api/private/v1/storage_tiers` | POST | Create with `{object: {...}}` |
| `/api/private/v1/storage_tiers/{id}` | GET | Get by ID, response_body: "object" |
| `/api/private/v1/storage_tiers` | GET | List with query params |
| `/api/private/v1/storage_tiers/{id}` | PATCH | Update with `{object: {...}}` |
| `/api/private/v1/storage_tiers/{id}` | DELETE | Soft delete |

**Implementation Reference:**
- Pattern: `fulfillment-service/proto/private/osac/private/v1/storage_tiers_service.proto` — HTTP annotations
- Pattern: `fulfillment-service/proto/private/osac/private/v1/network_classes_service.proto` — reference REST annotations

**Traces to:** FR-2 (all CRUD RPCs must include HTTP annotations for REST access via grpc-gateway)

---

### TS-024: StorageTier CRUD lifecycle via private gRPC

**Level:** E2E | **Component:** osac-test-infra | **Priority:** P0

**What it tests:** Full CRUD lifecycle of StorageTier against a live OSAC cluster via the private gRPC API. Creates a StorageBackend, then creates a StorageTier referencing it, exercises Get/List/Update/Delete, and verifies all fields. This is the top-level E2E validation of the StorageTier feature. Traces to FR-1, FR-3, FR-4, FR-5, FR-6.

**Preconditions:**
- Live OSAC cluster with fulfillment-service deployed (StorageTier server registered)
- `private_grpc` fixture providing authenticated `GRPCClient` for the private API
- New `GRPCClient` methods: `create_storage_backend()`, `create_storage_tier()`, `get_storage_tier()`, `list_storage_tier_ids()`, `update_storage_tier()`, `delete_storage_tier()`
- A `unique_name("st")` fixture for test isolation

**Steps:**
1. Create a StorageBackend via `private_grpc.create_storage_backend(name=unique_name("sb"), provider="vast", endpoint="https://vast.example.com", ...)`.
2. Create a StorageTier via `private_grpc.create_storage_tier(name=unique_name("st"), backend_id=backend_id, protocol="BLOCK", max_read_bandwidth_mbs=1000, max_write_bandwidth_mbs=500, quota_gib=1024, encryption_enabled=True)`.
3. Assert returned ID is a UUID, state is `"ACTIVE"`.
4. Call `private_grpc.list_storage_tier_ids()` — assert created ID is present.
5. Call `private_grpc.get_storage_tier(tier_id)` — verify all fields: name, description, backend_id, protocol, QoS properties.
6. Call `private_grpc.update_storage_tier(tier_id, description="Updated E2E tier")` — verify updated description.
7. Call `private_grpc.get_storage_tier(tier_id)` — verify description is `"Updated E2E tier"`, other fields unchanged.
8. Call `private_grpc.delete_storage_tier(tier_id)`.
9. Call `private_grpc.list_storage_tier_ids()` — assert deleted ID is absent.
10. Call `private_grpc.get_storage_tier(tier_id)` — assert gRPC error `NotFound`.
11. Cleanup: delete the StorageBackend.

**Expected Results:**
- Full CRUD cycle completes without errors.
- All fields round-trip correctly through the live system.
- Soft-deleted tier excluded from List and returns NotFound on Get.

**Test Data:**

| Parameter | Value | Notes |
|-----------|-------|-------|
| name | `"st-{uuid8}"` | Unique name per test run |
| protocol | `"BLOCK"` | `STORAGE_PROTOCOL_BLOCK` |
| max_read_bandwidth_mbs | `1000` | int32 MB/s |
| quota_gib | `1024` | int64 GiB |

**Implementation Reference:**
- Pattern: `osac-test-infra/tests/catalog/test_catalog_item_lifecycle.py` — `test_catalog_item_crud` function (Create → List → Get → Update → Get → Delete → List → Get pattern)
- Fixtures: `osac-test-infra/tests/conftest.py` — `private_grpc` fixture for private API access
- Client: `osac-test-infra/tests/core/grpc_client.py` — new methods needed following `create_instance_type()` / `create_external_ip_pool()` patterns
- Helpers: `osac-test-infra/tests/catalog/conftest.py` — `unique_name()` fixture for test isolation

**Traces to:** FR-1 (CRUD RPCs), FR-3 (Create with QoS), FR-4 (List), FR-5 (Update), FR-6 (Delete)

---

### TS-025: Backend reference validation via private gRPC

**Level:** E2E | **Component:** osac-test-infra | **Priority:** P0

**What it tests:** Validates backend reference validation and referential integrity through the live OSAC cluster. Tests three scenarios: (1) creating a tier with a non-existent backend fails, (2) deleting a backend referenced by an active tier fails, and (3) deleting the tier first unblocks the backend deletion. Traces to FR-7, FR-10.

**Preconditions:**
- Live OSAC cluster with fulfillment-service deployed
- `private_grpc` fixture
- New `GRPCClient` methods for StorageBackend and StorageTier

**Steps:**
1. Call `private_grpc.create_storage_tier(name="ref-test", backend_id="nonexistent-backend-id", ...)` — capture error.
2. Assert gRPC error code is `NotFound` and message contains the invalid backend ID.
3. Create a real StorageBackend via `private_grpc.create_storage_backend(...)`.
4. Create a StorageTier referencing the real backend.
5. Attempt to delete the StorageBackend via `private_grpc.delete_storage_backend(backend_id)` — capture error.
6. Assert gRPC error code is `FailedPrecondition` and message indicates the backend is in use.
7. Delete the StorageTier first.
8. Retry deleting the StorageBackend — assert success.

**Expected Results:**
- Step 1: `NotFound` error with the non-existent backend ID.
- Step 5: `FailedPrecondition` error indicating the backend is referenced by StorageTier(s).
- Step 8: Backend deletion succeeds after the referencing tier is removed.

**Implementation Reference:**
- Pattern: `osac-test-infra/tests/catalog/test_catalog_item_lifecycle.py` — `test_delete_catalog_item_blocked_when_referenced` function (referential integrity E2E test)
- Helpers: `osac-test-infra/tests/core/helpers.py` — `assert_grpc_rejected()` for gRPC error code assertions

**Traces to:** FR-7 (Create/Update must validate StorageBackend IDs), FR-10 (StorageBackend deletion blocked when referenced by StorageTier)

---

### TS-026: StorageTier list pagination and CEL filtering

**Level:** E2E | **Component:** osac-test-infra | **Priority:** P1

**What it tests:** Validates List RPC pagination (`offset`/`limit`) and CEL-based filtering against a live OSAC cluster. Creates multiple tiers, then exercises pagination and filter parameters. Traces to FR-4.

**Preconditions:**
- Live OSAC cluster with fulfillment-service deployed
- `private_grpc` fixture
- A StorageBackend pre-created
- Three StorageTiers created with distinct names (`"page-tier-1"`, `"page-tier-2"`, `"page-tier-3"`)

**Steps:**
1. Call `private_grpc.call(service="osac.private.v1.StorageTiers/List", data={"limit": 1})` — assert exactly 1 item returned.
2. Call `private_grpc.call(service="osac.private.v1.StorageTiers/List", data={"offset": 1, "limit": 10})` — assert remaining items returned.
3. Call `private_grpc.call(service="osac.private.v1.StorageTiers/List", data={"filter": "metadata.name == 'page-tier-2'"})` — assert exactly 1 item with matching name.
4. Cleanup: delete all three tiers and the backend.

**Expected Results:**
- Step 1: Response contains 1 item and `size` indicates total count >= 3.
- Step 2: Response contains items starting from offset 1.
- Step 3: Response contains exactly 1 item with `metadata.name == "page-tier-2"`.

**Implementation Reference:**
- Pattern: `osac-test-infra/tests/core/grpc_client.py` — `client.call()` method for generic gRPC calls
- Pattern: `osac-test-infra/tests/catalog/test_catalog_item_lifecycle.py` — list/filter test patterns

**Traces to:** FR-4 (List supports pagination, CEL filtering, SQL-like ordering)

---

### TS-027: Name uniqueness and duplicate rejection

**Level:** E2E | **Component:** osac-test-infra | **Priority:** P1

**What it tests:** Validates name uniqueness enforcement through the live OSAC cluster. Creating two active tiers with the same name fails with `AlreadyExists`. After deleting the first tier, the name can be reused. Traces to FR-8.

**Preconditions:**
- Live OSAC cluster with fulfillment-service deployed
- `private_grpc` fixture
- A StorageBackend pre-created

**Steps:**
1. Create a StorageTier with `name = "unique-e2e-{uuid}"` — assert success.
2. Create another StorageTier with the same name — capture error.
3. Assert error code is `AlreadyExists`.
4. Delete the first tier.
5. Create a StorageTier with `name = "unique-e2e-{uuid}"` — assert success (name reuse).
6. Cleanup: delete all tiers and backend.

**Expected Results:**
- Step 2: `AlreadyExists` error.
- Step 5: Create succeeds — name reuse after deletion works.

**Implementation Reference:**
- Pattern: `osac-test-infra/tests/core/helpers.py` — `assert_grpc_rejected()` for error code validation
- Pattern: `osac-test-infra/tests/catalog/test_catalog_item_lifecycle.py` — CRUD lifecycle patterns

**Traces to:** FR-8 (unique names among active tiers, name reuse after deletion)

---

## 5. Persona Coverage

| Persona | Scenarios | Coverage |
|---------|-----------|----------|
| Cloud Provider Admin | TS-001 through TS-027 | All CRUD operations, validation, and referential integrity — Cloud Provider Admin is the sole actor for the StorageTier private API |
| Cloud Infrastructure Admin | — | Not applicable — StorageTier is managed by Cloud Provider Admin; infrastructure-level storage configuration is via StorageBackend (OSAC-1111) |
| Tenant Admin | — | Not applicable — tenants do not access StorageTier directly (per Non-Goals) |
| Tenant User | — | Not applicable — tenants discover assigned tiers through Tenant CR status (OSAC-23, future) |

## 6. Risk-Based Prioritization

| Risk Area | Priority | Scenarios | Rationale |
|-----------|----------|-----------|-----------|
| Referential integrity (Tier↔Backend) | HIGH | TS-005, TS-016, TS-017, TS-018, TS-021, TS-025 | Database triggers enforce cross-entity consistency. Trigger failures or TOCTOU races could allow orphaned references or block legitimate operations. Z0002/Z0003 error propagation through DAO and gRPC layers must be tested end-to-end. |
| Helper table materialization | HIGH | TS-015 | The `storage_tier_backends` helper table is populated by an AFTER INSERT/UPDATE trigger. If the trigger fails or extracts incorrect JSONB paths, reverse lookups (backend deletion protection) silently break. |
| Data integrity (name uniqueness) | HIGH | TS-009, TS-022, TS-027 | Partial unique index must correctly allow name reuse after soft-delete. Incorrect trigger behavior could either allow duplicates or block legitimate name reuse. |
| CRUD lifecycle correctness | HIGH | TS-001, TS-003, TS-004, TS-020, TS-024 | Core API functionality — any regression blocks Cloud Provider Admin workflow. |
| Optimistic concurrency | MEDIUM | TS-008 | Prevents conflicting writes. Incorrect behavior could cause data loss on concurrent updates. |
| Input validation | MEDIUM | TS-006, TS-007, TS-010, TS-011 | Enforces v0.1 constraints (single backend) and immutability guarantees. Missing validation could allow schema violations. |
| Pagination and filtering | LOW | TS-002, TS-026 | Standard GenericServer behavior already tested for other resources. Low regression risk. |
| Builder validation | LOW | TS-013 | Catches misconfiguration at startup, not at runtime. |

## 7. Coverage Gaps

| Requirement | Gap | Reason | Risk |
|-------------|-----|--------|------|
| FR-6: Tenant reference block on delete | No test for `check_storage_tier_not_in_use` trigger | Trigger deferred to OSAC-23 follow-up migration — depends on Tenant proto schema for storage tier assignments not yet finalized | LOW — No tenants can reference tiers until OSAC-23 lands, so no protection gap exists |
| NFR-3: Delete does not affect Kubernetes StorageClasses | No test verifying StorageClass preservation | StorageClass lifecycle is managed by OSAC Storage Controller (OSAC-23), not by StorageTier API | LOW — StorageTier is DB-only, has no Kubernetes resource lifecycle |
| `setPayload()` event notification | No explicit test for StorageTier case in `setPayload()` switch | Covered implicitly by GenericServer's existing `setPayload()` tests; the new case is a one-line switch branch | LOW — existing proto reflection mechanism tested for other types |
| Multi-backend tiers (future) | No test for >1 backend succeeding | v0.1 explicitly rejects >1 backend; multi-backend support deferred | NONE — out of scope by design |
| REST endpoint E2E | No E2E test for REST paths | REST testing deferred to IT level (TS-023); E2E tests use gRPC directly | LOW — grpc-gateway transcoding is well-established |

## 8. Implementation Notes

- **Fixtures needed (osac-test-infra):** New `GRPCClient` methods must be added to `osac-test-infra/tests/core/grpc_client.py` for StorageBackend and StorageTier CRUD: `create_storage_backend()`, `delete_storage_backend()`, `create_storage_tier()`, `get_storage_tier()`, `list_storage_tier_ids()`, `update_storage_tier()`, `delete_storage_tier()`. Follow the `create_instance_type()` / `create_external_ip_pool()` pattern for private-API methods.
- **Infra gaps:** No new infrastructure required. StorageTier uses the existing PostgreSQL, Keycloak, and kind cluster infrastructure. E2E tests require the fulfillment-service deployment to include the `PrivateStorageTiersServer` registration (already in `start_grpc_server_cmd.go`).
- **Reference tests:**
  - Unit: `fulfillment-service/internal/servers/private_storage_tiers_server_test.go` (already exists with comprehensive coverage)
  - Unit: `fulfillment-service/internal/servers/private_storage_backends_server_test.go` (pattern reference)
  - Migration: `fulfillment-service/internal/database/migrations/76_add_storage_tier_ref_triggers_test.go` (already exists)
  - IT: `fulfillment-service/it/it_private_instance_types_test.go` (pattern for new `it_private_storage_tiers_test.go`)
  - E2E: `osac-test-infra/tests/catalog/test_catalog_item_lifecycle.py` (pattern for new `tests/storage/test_storage_tier_api.py`)
- **Existing test coverage:** Unit tests (`private_storage_tiers_server_test.go`) and migration tests (`75_*_test.go`, `76_*_test.go`, `77_*_test.go`) are already implemented. The primary implementation gaps are integration tests (new `it/it_private_storage_tiers_test.go`) and E2E tests (new `tests/storage/test_storage_tier_api.py` + `GRPCClient` extensions).
- **Jira tracking:** Create sub-tasks under OSAC-1110 for each test level: one for IT tests (`it_private_storage_tiers_test.go`), one for E2E tests (`test_storage_tier_api.py`), and one for `GRPCClient` extensions.
