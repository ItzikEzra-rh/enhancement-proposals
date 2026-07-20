---
ep_slug: "caas-cluster-storage"
ep_title: "CaaS Cluster Storage"
jira_key: "OSAC-1123"
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

# Test Plan: CaaS Cluster Storage

**Enhancement Proposal:** `enhancements/caas-cluster-storage/`
**Jira:** [OSAC-1123](https://redhat.atlassian.net/browse/OSAC-1123)
**Components:** osac-operator, osac-aap, osac-installer

## 1. Summary

This test plan validates the CaaS cluster storage provisioning lifecycle:
when a ClusterOrder reaches Ready, the storage controller retrieves the
cluster kubeconfig, triggers AAP to install CSI driver + StorageClasses,
and sets `ClusterStorageReady` condition. It also validates teardown on
ClusterOrder deletion and tenant isolation of storage resources.

Key risk areas: kubeconfig retrieval chain (3-step lookup), finalizer
lifecycle (blocks deletion), cross-component workflow (operator -> AAP -> CaaS cluster),
and tenant isolation of StorageClasses.

## 2. Component Impact

| Component | Test Levels | Rationale |
|-----------|------------|-----------|
| osac-operator | Unit + IT | Storage controller extension: new reconciliation path, kubeconfig retrieval, condition management, finalizer lifecycle |
| osac-aap | Unit (playbook) | Kubeconfig parameter passing to `kubernetes.core.k8s` calls |
| osac-installer | IT | RBAC manifest updates must grant correct permissions |
| osac-test-infra | E2E | End-to-end CaaS storage lifecycle against live cluster |

## 3. Test Scenario Index

| ID | Level | Component | Scenario | Priority |
|----|-------|-----------|----------|----------|
| TS-001 | Unit | osac-operator | mapClusterOrderToTenant — valid annotation | P0 |
| TS-002 | Unit | osac-operator | mapClusterOrderToTenant — missing annotation | P0 |
| TS-003 | Unit | osac-operator | mapClusterOrderToTenant — non-existent Tenant | P0 |
| TS-004 | Unit | osac-operator | Kubeconfig retrieval — happy path | P0 |
| TS-005 | Unit | osac-operator | Kubeconfig retrieval — missing clusterReference | P0 |
| TS-006 | Unit | osac-operator | Kubeconfig retrieval — missing HostedControlPlane | P0 |
| TS-007 | Unit | osac-operator | Kubeconfig retrieval — missing Secret | P0 |
| TS-008 | Unit | osac-operator | Kubeconfig retrieval — missing key in Secret | P1 |
| TS-009 | Unit | osac-operator | CaaS provisioning triggers when Tenant + ClusterOrder ready | P0 |
| TS-010 | Unit | osac-operator | CaaS provisioning — finalizer added before AAP call | P0 |
| TS-011 | Unit | osac-operator | CaaS provisioning — ClusterStorageReady=True on success | P0 |
| TS-012 | Unit | osac-operator | CaaS provisioning — Tenant status.clusterStorage updated | P0 |
| TS-013 | Unit | osac-operator | CaaS provisioning — AAP failure sets condition False | P1 |
| TS-014 | Unit | osac-operator | CaaS teardown — triggers on DeletionTimestamp | P0 |
| TS-015 | Unit | osac-operator | CaaS teardown — finalizer removed after cleanup | P0 |
| TS-016 | Unit | osac-operator | CaaS teardown — HostedControlPlane already gone | P0 |
| TS-017 | Unit | osac-operator | CaaS teardown — Tenant clusterStorage entry removed | P1 |
| TS-018 | Unit | osac-operator | Duplicate StorageClass detection emits warning | P1 |
| TS-019 | Unit | osac-operator | VMaaS regression — unchanged with CaaS clusters present | P0 |
| TS-020 | Unit | osac-operator | Provisioning skipped when Tenant StorageBackendReady=False | P1 |
| TS-021 | E2E | osac-test-infra | Full CaaS storage lifecycle — provision + PVC | P0 |
| TS-022 | E2E | osac-test-infra | CaaS cluster deletion — storage cleanup | P0 |
| TS-023 | E2E | osac-test-infra | Tenant isolation — cross-tenant StorageClass visibility | P0 |

## 4. Detailed Test Descriptions

---

### TS-001: mapClusterOrderToTenant — valid annotation

**Level:** Unit | **Component:** osac-operator | **Priority:** P0

**What it tests:** The `mapClusterOrderToTenant` function correctly reads the
`osac.openshift.io/tenant` annotation from a ClusterOrder and returns a
reconcile request for the owning Tenant. This is the entry point for CaaS
storage reconciliation.

**Preconditions:**
- envtest API server running
- Tenant CR `tenant-a` exists in namespace `osac`
- ClusterOrder CR `co-1` exists with annotation `osac.openshift.io/tenant=tenant-a`

**Steps:**
1. Call `mapClusterOrderToTenant(ctx, clusterOrder)` with `co-1`
2. Assert the returned reconcile request targets `tenant-a`

**Expected Results:**
- Returns `[]reconcile.Request` with exactly one entry
- Entry has `Name: "tenant-a"` and correct namespace

**Test Data:**

| Parameter | Value | Notes |
|-----------|-------|-------|
| ClusterOrder name | `co-1` | Standard test naming |
| Tenant annotation | `osac.openshift.io/tenant=tenant-a` | Must match existing Tenant |

**Implementation Reference:**
- Pattern: `storage_controller_test.go` (existing VMaaS storage controller tests)
- Fixtures: envtest suite setup in `controllers/suite_test.go`
- Helpers: `Expect(result).To(ContainElement(reconcile.Request{...}))`

**Traces to:** EP section "Reconciliation Flow" — "reads the `osac.openshift.io/tenant` annotation from the ClusterOrder and looks up the owning Tenant"

---

### TS-002: mapClusterOrderToTenant — missing annotation

**Level:** Unit | **Component:** osac-operator | **Priority:** P0

**What it tests:** When a ClusterOrder has no `osac.openshift.io/tenant` annotation,
the mapping function returns an empty list (no reconciliation triggered).

**Preconditions:**
- envtest API server running
- ClusterOrder CR `co-orphan` exists WITHOUT the tenant annotation

**Steps:**
1. Call `mapClusterOrderToTenant(ctx, clusterOrder)` with `co-orphan`
2. Assert the returned list is empty

**Expected Results:**
- Returns empty `[]reconcile.Request`
- No error logged (this is a valid state for non-OSAC ClusterOrders)

**Test Data:**

| Parameter | Value | Notes |
|-----------|-------|-------|
| ClusterOrder name | `co-orphan` | No tenant annotation |

**Implementation Reference:**
- Pattern: `storage_controller_test.go` — similar nil-return tests
- Fixtures: envtest

**Traces to:** EP section "Reconciliation Flow" — handles missing annotation

---

### TS-003: mapClusterOrderToTenant — non-existent Tenant

**Level:** Unit | **Component:** osac-operator | **Priority:** P0

**What it tests:** When a ClusterOrder references a Tenant that doesn't exist,
the function returns an empty list and logs a warning.

**Preconditions:**
- envtest API server running
- ClusterOrder CR `co-bad` exists with annotation `osac.openshift.io/tenant=no-such-tenant`
- No Tenant CR named `no-such-tenant` exists

**Steps:**
1. Call `mapClusterOrderToTenant(ctx, clusterOrder)` with `co-bad`
2. Assert the returned list is empty
3. Assert a warning log entry was emitted

**Expected Results:**
- Returns empty `[]reconcile.Request`
- Warning log with `clusterOrder=co-bad` and `tenant=no-such-tenant`

**Implementation Reference:**
- Pattern: `storage_controller_test.go`
- Fixtures: envtest, GinkgoWriter for log capture

**Traces to:** EP section "Reconciliation Flow" — edge case for annotation pointing to nonexistent Tenant

---

### TS-004: Kubeconfig retrieval — happy path

**Level:** Unit | **Component:** osac-operator | **Priority:** P0

**What it tests:** The 3-step kubeconfig lookup: ClusterOrder.status.clusterReference
-> HostedControlPlane -> kubeconfig Secret. Validates that the controller correctly
traverses the chain and returns a usable kubeconfig.

**Preconditions:**
- envtest API server with HyperShift CRDs registered
- ClusterOrder `co-1` with `status.clusterReference` pointing to namespace `clusters-tenant-a`
- HostedControlPlane in `clusters-tenant-a` with `status.kubeConfig.name=admin-kubeconfig`
- Secret `admin-kubeconfig` in `clusters-tenant-a` with key `kubeconfig` containing valid kubeconfig data

**Steps:**
1. Call `getClusterKubeconfig(ctx, clusterOrder)` with `co-1`
2. Assert the returned kubeconfig matches the Secret data
3. Assert no error

**Expected Results:**
- Returns `[]byte` matching the kubeconfig Secret data
- Error is nil

**Test Data:**

| Parameter | Value | Notes |
|-----------|-------|-------|
| ClusterOrder | `co-1` | With clusterReference |
| HostedControlPlane namespace | `clusters-tenant-a` | HyperShift convention |
| Secret name | `admin-kubeconfig` | From HCP status.kubeConfig.name |
| Secret key | `kubeconfig` | Standard key |

**Implementation Reference:**
- Pattern: `storage_controller_test.go` — mock HostedControlPlane resources
- Fixtures: envtest with HyperShift API types registered via `AddToScheme`
- Helpers: `runtime.NewScheme()` + `hypershift.AddToScheme`

**Traces to:** EP section "Kubeconfig Retrieval" — "Three-step lookup"

---

### TS-005: Kubeconfig retrieval — missing clusterReference

**Level:** Unit | **Component:** osac-operator | **Priority:** P0

**What it tests:** When ClusterOrder has no `status.clusterReference`, the controller
sets `ClusterStorageReady=False` with reason `KubeConfigNotAvailable`.

**Preconditions:**
- ClusterOrder `co-1` with empty `status.clusterReference`

**Steps:**
1. Trigger reconciliation for `co-1`
2. Read ClusterOrder conditions

**Expected Results:**
- Condition `ClusterStorageReady` is `False`
- Reason is `KubeConfigNotAvailable`
- Message mentions missing cluster reference

**Implementation Reference:**
- Pattern: `storage_controller_test.go` — condition assertion helpers
- Helpers: `Expect(conditions).To(ContainElement(MatchFields(...)))`

**Traces to:** EP "Failure Handling" table — "Kubeconfig not available"

---

### TS-006: Kubeconfig retrieval — missing HostedControlPlane

**Level:** Unit | **Component:** osac-operator | **Priority:** P0

**What it tests:** When ClusterOrder has a clusterReference but the HostedControlPlane
resource doesn't exist, the controller sets the appropriate failure condition.

**Preconditions:**
- ClusterOrder `co-1` with `status.clusterReference` pointing to `clusters-tenant-a`
- No HostedControlPlane in `clusters-tenant-a`

**Steps:**
1. Trigger reconciliation for `co-1`
2. Read ClusterOrder conditions

**Expected Results:**
- Condition `ClusterStorageReady` is `False`
- Reason is `KubeConfigNotAvailable`

**Traces to:** EP "Failure Handling" table — "Kubeconfig not available"

---

### TS-007: Kubeconfig retrieval — missing Secret

**Level:** Unit | **Component:** osac-operator | **Priority:** P0

**What it tests:** HostedControlPlane exists but the kubeconfig Secret it references
is missing.

**Preconditions:**
- HostedControlPlane exists with `status.kubeConfig.name=admin-kubeconfig`
- No Secret named `admin-kubeconfig` in the namespace

**Steps:**
1. Trigger reconciliation
2. Read ClusterOrder conditions

**Expected Results:**
- Condition `ClusterStorageReady` is `False`
- Reason is `KubeConfigNotAvailable`

**Traces to:** EP "Kubeconfig Retrieval" — step 3

---

### TS-008: Kubeconfig retrieval — missing key in Secret

**Level:** Unit | **Component:** osac-operator | **Priority:** P1

**What it tests:** Secret exists but doesn't contain the expected `kubeconfig` key.

**Preconditions:**
- Secret `admin-kubeconfig` exists but with key `wrong-key` instead of `kubeconfig`

**Steps:**
1. Trigger reconciliation
2. Read ClusterOrder conditions

**Expected Results:**
- Condition `ClusterStorageReady` is `False`
- Reason is `KubeConfigNotAvailable`
- Message mentions the missing key name

**Traces to:** EP "Kubeconfig Retrieval" — step 3 ("name and key")

---

### TS-009: CaaS provisioning triggers when Tenant + ClusterOrder ready

**Level:** Unit | **Component:** osac-operator | **Priority:** P0

**What it tests:** The CaaS provisioning path activates only when BOTH the Tenant
has `StorageBackendReady=True` AND the ClusterOrder has `Phase=Ready`. If either
is not met, provisioning does not trigger.

**Preconditions:**
- Tenant `tenant-a` with `StorageBackendReady=True`
- ClusterOrder `co-1` with `Phase=Ready` and tenant annotation
- Mock provisioning provider (AAP mock)

**Steps:**
1. Trigger reconciliation for `tenant-a`
2. Assert mock AAP was called with the correct parameters
3. Now test with `StorageBackendReady=False` — assert AAP is NOT called
4. Test with `Phase=Pending` — assert AAP is NOT called

**Expected Results:**
- AAP called exactly once in step 2 with `admin_kubeconfig` in extra vars
- AAP NOT called in steps 3 and 4
- No error conditions set in steps 3 and 4

**Test Data:**

| Parameter | Value | Notes |
|-----------|-------|-------|
| AAP template | `osac-create-tenant-cluster-storage` | Existing template name |
| Extra var | `admin_kubeconfig` | Kubeconfig passed to AAP |

**Implementation Reference:**
- Pattern: `storage_controller_test.go` — mock provisioning provider pattern
- Fixtures: `NewMockProvisioningProvider(ctrl)`
- Helpers: `mockProvider.EXPECT().RunJob(gomock.Any(), gomock.Any()).Return(nil)`

**Traces to:** EP "Prerequisites" — both conditions required; EP "CaaS Storage Provisioning" sequence diagram

---

### TS-010: CaaS provisioning — finalizer added before AAP call

**Level:** Unit | **Component:** osac-operator | **Priority:** P0

**What it tests:** The `osac.openshift.io/cluster-storage` finalizer is added to
the ClusterOrder BEFORE the AAP provisioning job is triggered.

**Preconditions:**
- Ready ClusterOrder without the storage finalizer

**Steps:**
1. Trigger reconciliation
2. Read ClusterOrder before AAP mock returns
3. Assert finalizer is present

**Expected Results:**
- ClusterOrder has finalizer `osac.openshift.io/cluster-storage` in `metadata.finalizers`
- Finalizer is added before AAP call (verify via mock call ordering)

**Implementation Reference:**
- Pattern: existing finalizer tests in osac-operator controllers
- Helpers: `Expect(co.Finalizers).To(ContainElement("osac.openshift.io/cluster-storage"))`

**Traces to:** EP "Reconciliation Flow" — step 1: "Add the finalizer"

---

### TS-011: CaaS provisioning — ClusterStorageReady=True on success

**Level:** Unit | **Component:** osac-operator | **Priority:** P0

**What it tests:** After successful AAP job and StorageClass discovery, the
`ClusterStorageReady` condition is set to `True` on the ClusterOrder.

**Preconditions:**
- Mock AAP returns success
- Mock StorageClass discovery returns 2 StorageClasses (NFS + Block)

**Steps:**
1. Trigger reconciliation
2. Read ClusterOrder conditions after reconciliation completes

**Expected Results:**
- Condition `ClusterStorageReady` type exists
- Status is `True`
- Reason is `ClusterStorageProvisioned`

**Traces to:** EP "CaaS Storage Provisioning" — final step: "Set ClusterStorageReady=True condition"

---

### TS-012: CaaS provisioning — Tenant status.clusterStorage updated

**Level:** Unit | **Component:** osac-operator | **Priority:** P0

**What it tests:** On successful provisioning, the Tenant CR's `status.clusterStorage`
list is updated with an entry for the CaaS cluster, keyed by ClusterOrder name.

**Preconditions:**
- Successful provisioning of `co-1` for `tenant-a`

**Steps:**
1. Trigger reconciliation to completion
2. Read Tenant `tenant-a` status

**Expected Results:**
- `status.clusterStorage` contains entry with `clusterName: "co-1"`
- Entry includes discovered StorageClass names

**Traces to:** EP "Reconciliation Flow" — step 5: "Update the Tenant's status.clusterStorage"

---

### TS-013: CaaS provisioning — AAP failure sets condition False

**Level:** Unit | **Component:** osac-operator | **Priority:** P1

**What it tests:** When the AAP provisioning job fails, the condition is set to
False with reason `ProvisionFailed` and the specific error message.

**Preconditions:**
- Mock AAP returns error "template execution failed: timeout"

**Steps:**
1. Trigger reconciliation
2. Read ClusterOrder conditions

**Expected Results:**
- Condition `ClusterStorageReady` is `False`
- Reason is `ProvisionFailed`
- Message contains "template execution failed"

**Implementation Reference:**
- Pattern: `storage_controller_test.go` — error path tests

**Traces to:** EP "Failure Handling" — "AAP provisioning fails"

---

### TS-014: CaaS teardown — triggers on DeletionTimestamp

**Level:** Unit | **Component:** osac-operator | **Priority:** P0

**What it tests:** When a ClusterOrder with the storage finalizer has a
DeletionTimestamp, the controller triggers teardown AAP job instead of provisioning.

**Preconditions:**
- ClusterOrder `co-1` with finalizer `osac.openshift.io/cluster-storage`
- ClusterOrder has `DeletionTimestamp` set (being deleted)

**Steps:**
1. Set DeletionTimestamp on `co-1`
2. Trigger reconciliation
3. Assert mock AAP was called with teardown template

**Expected Results:**
- AAP called with template `osac-delete-tenant-cluster-storage`
- NOT called with provisioning template

**Test Data:**

| Parameter | Value | Notes |
|-----------|-------|-------|
| AAP template | `osac-delete-tenant-cluster-storage` | Teardown template |

**Traces to:** EP "CaaS Storage Teardown" sequence diagram

---

### TS-015: CaaS teardown — finalizer removed after cleanup

**Level:** Unit | **Component:** osac-operator | **Priority:** P0

**What it tests:** The storage finalizer is only removed AFTER the teardown AAP
job succeeds. This is critical — premature finalizer removal would allow the
ClusterOrder to be deleted before storage cleanup.

**Preconditions:**
- ClusterOrder being deleted with storage finalizer
- Mock AAP teardown returns success

**Steps:**
1. Trigger reconciliation
2. Assert finalizer is still present before AAP completes
3. Allow AAP mock to return success
4. Assert finalizer is removed after reconciliation

**Expected Results:**
- Finalizer removed only after successful teardown
- ClusterOrder can now be garbage collected

**Traces to:** EP "CaaS Storage Teardown" — "removes the finalizer"

---

### TS-016: CaaS teardown — HostedControlPlane already gone

**Level:** Unit | **Component:** osac-operator | **Priority:** P0

**What it tests:** When the HostedControlPlane is already deleted (cluster deleted
outside OSAC), the controller skips teardown, removes the clusterStorage entry,
and removes the finalizer. This prevents the finalizer from blocking deletion
forever.

**Preconditions:**
- ClusterOrder being deleted with storage finalizer
- HostedControlPlane does NOT exist (404)

**Steps:**
1. Trigger reconciliation
2. Assert AAP was NOT called (no cluster to clean up)
3. Assert Tenant `status.clusterStorage` entry removed
4. Assert finalizer removed from ClusterOrder

**Expected Results:**
- No AAP call (nothing to clean up)
- Tenant status updated (entry removed)
- Finalizer removed
- Warning event logged

**Traces to:** EP "CaaS Storage Teardown" — "If the HostedControlPlane or kubeconfig Secret is already gone"

---

### TS-017: CaaS teardown — Tenant clusterStorage entry removed

**Level:** Unit | **Component:** osac-operator | **Priority:** P1

**What it tests:** On successful teardown, the Tenant's `status.clusterStorage`
entry for the deleted ClusterOrder is removed.

**Preconditions:**
- Tenant `tenant-a` with `status.clusterStorage` containing entry `clusterName: "co-1"`
- ClusterOrder `co-1` being deleted

**Steps:**
1. Complete teardown
2. Read Tenant status

**Expected Results:**
- Entry with `clusterName: "co-1"` no longer in `status.clusterStorage`
- Other entries (if any) remain unchanged

**Traces to:** EP "CaaS Storage Teardown" — "removes the status.clusterStorage entry"

---

### TS-018: Duplicate StorageClass detection emits warning

**Level:** Unit | **Component:** osac-operator | **Priority:** P1

**What it tests:** When StorageClass discovery finds multiple classes for the same
tier on a CaaS cluster, the controller emits a warning event and sets the
condition to False.

**Preconditions:**
- Mock StorageClass discovery returns 2 NFS StorageClasses for the same tier

**Steps:**
1. Trigger reconciliation
2. Check events on ClusterOrder

**Expected Results:**
- Warning event with reason `DuplicateStorageClass`
- Condition `ClusterStorageReady` is `False`, reason `MultipleFound`

**Traces to:** EP "Failure Handling" — "Duplicate StorageClasses per tier"

---

### TS-019: VMaaS regression — unchanged with CaaS clusters present

**Level:** Unit | **Component:** osac-operator | **Priority:** P0

**What it tests:** The existing VMaaS storage provisioning flow works correctly
when CaaS ClusterOrders also exist for the same Tenant.

**Preconditions:**
- Tenant `tenant-a` with `StorageBackendReady=True`
- VMaaS target cluster configured (existing setup)
- CaaS ClusterOrder `co-1` also exists for `tenant-a`

**Steps:**
1. Trigger reconciliation for `tenant-a`
2. Assert VMaaS provisioning runs as before
3. Assert VMaaS and CaaS provisioning are independent

**Expected Results:**
- VMaaS StorageClasses created on VMaaS target cluster
- CaaS provisioning triggered separately for `co-1`
- No interference between the two paths

**Traces to:** EP "Goals" — "Keep VMaaS storage provisioning unchanged"

---

### TS-020: Provisioning skipped when Tenant StorageBackendReady=False

**Level:** Unit | **Component:** osac-operator | **Priority:** P1

**What it tests:** CaaS provisioning does NOT trigger when the Tenant hasn't
completed Stage 1 (backend provisioning).

**Preconditions:**
- Tenant `tenant-a` with `StorageBackendReady=False`
- ClusterOrder `co-1` with `Phase=Ready`

**Steps:**
1. Trigger reconciliation
2. Assert AAP is NOT called
3. Assert no condition is set on ClusterOrder (storage controller hasn't acted)

**Expected Results:**
- No AAP call
- No `ClusterStorageReady` condition on ClusterOrder

**Traces to:** EP "Prerequisites" — "Tenant CR has StorageBackendReady=True (Stage 1 completed)"

---

### TS-021: Full CaaS storage lifecycle — provision + PVC

**Level:** E2E | **Component:** osac-test-infra | **Priority:** P0

**What it tests:** End-to-end: create a CaaS cluster, wait for storage to be
provisioned, create a PVC, verify it binds successfully.

**Preconditions:**
- OSAC deployed with storage controller and AAP
- Tenant `e2e-tenant` exists with `StorageBackendReady=True`
- VAST storage backend accessible

**Steps:**
1. Create a ClusterOrder via gRPC: `grpc.clusters.create(name="e2e-storage-test", tenant="e2e-tenant")`
2. `poll_until` ClusterOrder `Phase=Ready` (timeout 300s)
3. `poll_until` ClusterOrder `ClusterStorageReady=True` (timeout 120s)
4. Get cluster kubeconfig via gRPC `GetCredentials`
5. Using the CaaS cluster kubeconfig, create a PVC with StorageClass `osac-csi-vast-nfs`
6. `poll_until` PVC phase=Bound (timeout 60s)
7. Assert PVC `spec.storageClassName` matches `osac-csi-vast-nfs`
8. Delete the PVC
9. Delete the ClusterOrder

**Expected Results:**
- ClusterOrder reaches `Phase=Ready`
- `ClusterStorageReady=True` condition appears
- PVC binds successfully
- StorageClass labels include `osac.openshift.io/tenant=e2e-tenant`

**Test Data:**

| Parameter | Value | Notes |
|-----------|-------|-------|
| Cluster name | `e2e-storage-test` | Unique per run |
| StorageClass | `osac-csi-vast-nfs` | NFS tier |
| PVC size | `1Gi` | Minimal |

**Implementation Reference:**
- Pattern: `tests/storage/test_tenant_storage_lifecycle.py`
- Fixtures: `grpc` (session-scoped), `k8s_hub_client`
- Helpers: `poll_until()`, `GRPCClient.clusters.create()`

**Traces to:** PRD user story — "persistent storage to be available on my CaaS cluster when it is ready"

---

### TS-022: CaaS cluster deletion — storage cleanup

**Level:** E2E | **Component:** osac-test-infra | **Priority:** P0

**What it tests:** When a CaaS cluster is deleted, storage resources (StorageClasses,
CSI resources) are cleaned up from the cluster before it's removed.

**Preconditions:**
- ClusterOrder with `ClusterStorageReady=True` from TS-021

**Steps:**
1. Delete the ClusterOrder via gRPC: `grpc.clusters.delete(cluster_id)`
2. `poll_until` ClusterOrder is fully deleted (timeout 180s)
3. Verify no orphaned StorageClasses with `osac.openshift.io/tenant=e2e-tenant` label exist

**Expected Results:**
- ClusterOrder deleted successfully (finalizer honored, then removed)
- No orphaned storage resources

**Implementation Reference:**
- Pattern: `tests/caas/test_cluster_lifecycle.py` — deletion path
- Fixtures: `grpc`, `k8s_hub_client`
- Helpers: `poll_until(lambda: not grpc.clusters.exists(id))`

**Traces to:** PRD user story — "storage resources cleaned up when the cluster is deleted"

---

### TS-023: Tenant isolation — cross-tenant StorageClass visibility

**Level:** E2E | **Component:** osac-test-infra | **Priority:** P0

**What it tests:** StorageClasses from one tenant's CaaS cluster are NOT visible
or usable from another tenant's cluster.

**Preconditions:**
- Two tenants: `e2e-tenant-a` and `e2e-tenant-b`, both with storage backends
- Each has a Ready CaaS cluster with `ClusterStorageReady=True`

**Steps:**
1. Get kubeconfig for tenant-a's cluster
2. List StorageClasses with label `osac.openshift.io/tenant=e2e-tenant-b` on tenant-a's cluster
3. Assert the list is empty
4. Get kubeconfig for tenant-b's cluster
5. List StorageClasses with label `osac.openshift.io/tenant=e2e-tenant-a` on tenant-b's cluster
6. Assert the list is empty

**Expected Results:**
- Tenant A's cluster has only tenant A's StorageClasses
- Tenant B's cluster has only tenant B's StorageClasses
- No cross-tenant visibility

**Implementation Reference:**
- Pattern: `tests/vmaas/test_tenant_isolation.py` (if exists)
- Fixtures: `grpc`, `k8s_hub_client`, two tenant fixtures
- Helpers: `k8s_client.list("storageclasses", label_selector="...")`

**Traces to:** EP "Security Considerations" — "StorageClasses are scoped to tenants via the osac.openshift.io/tenant label"

---

## 5. Persona Coverage

| Persona | Scenarios | Coverage |
|---------|-----------|----------|
| Cloud Provider Admin | TS-011, TS-012, TS-018 | Monitors storage readiness, sees conditions and events |
| Tenant Admin / Tenant User | TS-021, TS-022, TS-023 | Creates PVCs, sees storage readiness, storage cleaned on delete |
| Cloud Infrastructure Admin | — | Not affected by this EP (no backend config changes) |

## 6. Risk-Based Prioritization

| Risk Area | Priority | Scenarios | Rationale |
|-----------|----------|-----------|-----------|
| Tenant isolation | HIGH | TS-023 | Cross-tenant StorageClass leak would be a security issue |
| Provisioning lifecycle | HIGH | TS-009 to TS-013, TS-021 | Core functionality, cross-component |
| Finalizer lifecycle | HIGH | TS-010, TS-014, TS-015 | Finalizer bugs block deletion or skip cleanup |
| Kubeconfig retrieval | HIGH | TS-004 to TS-008 | 3-step lookup chain, any break fails silently |
| Teardown edge cases | HIGH | TS-016 | Prevents stuck finalizer when infra is gone |
| VMaaS regression | HIGH | TS-019 | Must not break existing functionality |
| Error handling | MEDIUM | TS-013, TS-018, TS-020 | Failure conditions and events |

## 7. Coverage Gaps

| Requirement | Gap | Reason | Risk |
|-------------|-----|--------|------|
| AAP kubeconfig parameter passing | No unit test for AAP playbook changes | AAP playbooks tested via E2E only, no unit test framework for Ansible roles | LOW — covered by E2E TS-021 |
| osac-installer RBAC updates | No explicit test for RBAC manifests | Covered implicitly by E2E (if RBAC is wrong, provisioning fails) | LOW — deployment would fail visibly |
| Kubeconfig rotation during AAP job | No test | Requires timing-sensitive test, EP says "retries on next reconciliation" | MEDIUM — accepted risk for v0.1 |
| Multiple CaaS clusters per tenant concurrency | No test | EP says "single-digit expected" for v0.1 | LOW — deferred |

## 8. Implementation Notes

- **Fixtures needed:** HyperShift API types must be registered in envtest scheme for unit tests
- **Infra gaps:** E2E tests require VAST storage backend accessible from test cluster — may need test environment provisioning
- **Reference tests:** `storage_controller_test.go` in osac-operator is the primary pattern; `tests/storage/test_tenant_storage_lifecycle.py` in osac-test-infra for E2E
- **Jira tracking:** Create sub-tasks under OSAC-1123 for each test group (kubeconfig retrieval, provisioning, teardown, E2E)
