---
title: osac-storage-control-plane
authors:
  - TBD
creation-date: 2026-07-30
last-updated: 2026-07-30
tracking-link:
  - https://redhat.atlassian.net/browse/OSAC-2872
prd:
  - "prd.md"
see-also:
  - "/enhancements/OSAC-984-public-volume-api"
---

# OSAC Storage Control Plane

## Summary

This enhancement introduces a storage control plane for OSAC that enables tenants to consume block storage through opaque tiers without exposure to vendor-specific details. The design adds a new CSI driver (`csi.osac.openshift.io`) that delegates volume lifecycle operations to fulfillment-service internal APIs, a volume inventory resource for tracking provisioned volumes, Helm packaging for the CSI components, and AAP roles for automated deployment on provisioned clusters. See [PRD](prd.md) for detailed requirements.

## Motivation

OSAC provisions Kubernetes clusters and compute instances but currently has no storage abstraction. Tenants on provisioned CaaS clusters need persistent block storage, and the underlying storage vendors (NetApp ONTAP, VAST Data, Pure Storage) vary across deployments. Without a storage control plane, each deployment would require manual CSI driver configuration, per-vendor credential distribution, and ad-hoc quota enforcement -- none of which respect OSAC's multi-tenant isolation model.

The storage control plane fills this gap by presenting a single CSI interface on every provisioned cluster. The CSI driver delegates all provisioning, attachment, and credential decisions to the fulfillment-service, which resolves opaque tier names to vendor-specific backends and enforces tenant policy centrally. This keeps vendor details off the tenant cluster entirely and routes all storage decisions through the same authorization and audit path used by networking and compute.

### Goals

- Reuse the existing fulfillment-service gRPC server patterns (generic server, conditions, reconciliation lifecycle) for all new storage APIs.
- Enforce tenant isolation through the standard `osac.openshift.io/tenant` and `osac.openshift.io/owner-reference` annotation model and OPA policies.
- Support multiple storage vendors behind a single CSI driver without any vendor-specific configuration visible to tenants.
- Deliver CSI components as a Helm sub-chart integrated into the osac-installer umbrella chart.
- Automate CSI driver deployment on provisioned clusters via AAP roles triggered by ClusterOrder post-install hooks.
- Provide per-request credential injection so that long-lived storage credentials never reside on tenant clusters.

### Non-Goals

- **Public Volume API (OSAC-984):** A tenant-facing gRPC/REST API for volume CRUD is deferred to a separate enhancement. This design covers only the internal control plane and CSI driver.
- **UI integration:** No osac-ui console changes are included. Volume visibility in the console is deferred until the public Volume API ships.
- **Vendor-specific REST adapters:** Direct REST integration with vendor management APIs (e.g., ONTAP REST, VAST management) is out of scope. The CSI driver proxies to vendor CSI drivers already deployed on the hub.
- **Metering and billing:** Storage consumption metering is not addressed in this design.
- **Snapshot and clone operations:** CSI snapshot and clone capabilities are deferred to a future phase.

## Proposal

The storage control plane introduces five new components spanning four OSAC repositories plus a new `osac-csi-driver` repository:

1. **osac-csi-driver** (new repo): A Kubernetes CSI driver that implements the CSI Identity, Controller, and Node services. Instead of communicating directly with storage backends, the controller plugin calls fulfillment-service internal gRPC APIs to resolve tiers, check policy, obtain short-lived credentials, and then proxies the actual CSI call to the appropriate vendor CSI driver on the hub cluster.

2. **fulfillment-service** (storage internal API): Three new internal gRPC services -- `StorageTierResolver`, `StoragePolicyChecker`, and `StorageCredentialProvider` -- exposed on the internal API port (not the public tenant API). These services look up tier-to-vendor mappings, evaluate tenant storage policies, and issue short-lived credentials for the resolved vendor backend.

3. **fulfillment-service** (volume inventory): A new `Volume` resource with full CRUD, tracked in PostgreSQL, recording tenant, tier, state, size, and the underlying vendor volume ID. The volume inventory is the system of record for what has been provisioned.

4. **osac-installer** (CSI Helm sub-chart): A `charts/osac-csi-driver/` Helm chart packaging the CSI controller Deployment, node DaemonSet, CSIDriver object, RBAC, and StorageClass definitions. Integrated as a dependency in the osac umbrella chart.

5. **osac-aap** (deployment roles) and **osac-operator** (ClusterOrder hook): An Ansible role that deploys the CSI driver Helm chart onto a provisioned cluster, triggered by a new post-install hook in the ClusterOrder controller.

### Workflow Description

#### Storage Tier Configuration (Cloud Infrastructure Admin)

1. The Cloud Infrastructure Admin registers storage vendors in the fulfillment-service configuration, specifying vendor type (NetApp, VAST, Pure), connection endpoints, and the corresponding vendor CSI driver deployed on the hub cluster.
2. The admin creates StorageTier resources that map an opaque tier name (e.g., `standard`, `premium`) to one or more vendor backends, with selection policy (affinity, capacity-weighted).
3. The admin assigns StorageTier availability per tenant or globally.

#### CSI Driver Deployment (Automated)

1. When a ClusterOrder reaches the `Provisioned` state, the ClusterOrder controller fires a post-install hook.
2. The hook triggers an AAP job that runs the `osac-csi-driver-deploy` role against the newly provisioned cluster.
3. The role installs the `osac-csi-driver` Helm chart, configuring the controller plugin with the fulfillment-service internal API endpoint and a service account token for authentication.
4. StorageClass objects are created on the tenant cluster for each StorageTier available to that tenant, with the provisioner set to `csi.osac.openshift.io`.

#### Volume Provisioning (Tenant User)

1. The tenant user creates a PVC on their provisioned cluster referencing a StorageClass provisioned by the CSI driver (e.g., `osac-standard`).
2. The CSI controller plugin intercepts the `CreateVolume` call and sends a `ResolveTier` request to fulfillment-service, passing the tier name and requesting tenant ID.
3. Fulfillment-service resolves the tier to a specific vendor backend and returns the vendor CSI driver name and connection parameters.
4. The CSI controller plugin sends a `CheckPolicy` request to validate that the tenant has not exceeded quota and the requested size is within policy limits.
5. The CSI controller plugin sends a `GetCredentials` request to obtain short-lived credentials for the resolved vendor backend.
6. The CSI controller plugin proxies the `CreateVolume` call to the vendor CSI driver on the hub cluster, using the short-lived credentials.
7. On success, the CSI controller plugin creates a Volume inventory record in fulfillment-service via the internal API, recording tenant, tier, size, vendor volume ID, and state `Bound`.
8. The CSI controller plugin returns the volume ID to the Kubernetes provisioner, which creates the PV and binds the PVC.

#### Volume Deletion

1. When a PVC is deleted, the CSI controller plugin receives a `DeleteVolume` call.
2. The plugin retrieves the Volume inventory record from fulfillment-service to determine the vendor backend.
3. The plugin obtains short-lived credentials via `GetCredentials` and proxies the `DeleteVolume` call to the vendor CSI driver.
4. On success, the plugin updates the Volume inventory record state to `Deleted`.

#### Error Handling

- **Tier resolution failure:** If `ResolveTier` returns `NOT_FOUND` (no backends available for the tier), the CSI driver returns a gRPC `INVALID_ARGUMENT` error to Kubernetes, which marks the PVC as `Pending` with a descriptive event.
- **Policy violation:** If `CheckPolicy` returns `PERMISSION_DENIED` (quota exceeded), the CSI driver returns `RESOURCE_EXHAUSTED`. The PVC remains `Pending` with an event indicating the quota limit.
- **Credential failure:** If `GetCredentials` fails, the CSI driver returns `UNAVAILABLE` and retries with exponential backoff. The PVC stays `Pending`.
- **Vendor CSI failure:** If the proxied vendor CSI call fails, the error is propagated with the original gRPC code. The Volume inventory record is not created (CreateVolume) or not updated (DeleteVolume), so the system remains consistent.
- **Inventory write failure:** If the Volume inventory update fails after a successful vendor CSI call, the CSI driver logs the orphaned volume and returns success to Kubernetes. A reconciliation loop in fulfillment-service periodically scans for orphaned vendor volumes and creates missing inventory records.

### API Extensions

#### New Internal gRPC Services (fulfillment-service)

These services are internal (not exposed on the public API port) and are consumed only by the osac-csi-driver.

```protobuf
// internal/api/v1/storage_tier_resolver.proto
service StorageTierResolver {
  rpc ResolveTier(ResolveTierRequest) returns (ResolveTierResponse);
}

message ResolveTierRequest {
  string tier_name = 1;
  string tenant_id = 2;
  int64 requested_capacity_bytes = 3;
}

message ResolveTierResponse {
  string vendor_csi_driver = 1;
  string vendor_endpoint = 2;
  map<string, string> vendor_parameters = 3;
  string backend_id = 4;
}
```

```protobuf
// internal/api/v1/storage_policy_checker.proto
service StoragePolicyChecker {
  rpc CheckPolicy(CheckPolicyRequest) returns (CheckPolicyResponse);
}

message CheckPolicyRequest {
  string tenant_id = 1;
  string tier_name = 2;
  int64 requested_capacity_bytes = 3;
}

message CheckPolicyResponse {
  bool allowed = 1;
  string denial_reason = 2;
  int64 remaining_capacity_bytes = 3;
}
```

```protobuf
// internal/api/v1/storage_credential_provider.proto
service StorageCredentialProvider {
  rpc GetCredentials(GetCredentialsRequest) returns (GetCredentialsResponse);
}

message GetCredentialsRequest {
  string backend_id = 1;
  string tenant_id = 2;
  string operation = 3; // "CREATE", "DELETE", "ATTACH", "DETACH"
}

message GetCredentialsResponse {
  map<string, string> credentials = 1;
  google.protobuf.Timestamp expiry = 2;
}
```

#### Volume Inventory Resource (fulfillment-service)

```protobuf
// api/v1/volume.proto
message Volume {
  string id = 1;
  VolumeMetadata metadata = 2;
  VolumeSpec spec = 3;
  VolumeStatus status = 4;
}

message VolumeMetadata {
  string name = 1;
  map<string, string> labels = 2;
  map<string, string> annotations = 3;
  google.protobuf.Timestamp created_at = 4;
  google.protobuf.Timestamp updated_at = 5;
  string tenant_id = 6;
}

message VolumeSpec {
  string storage_tier = 1;
  int64 capacity_bytes = 2;
  string access_mode = 3; // "ReadWriteOnce", "ReadWriteMany"
  string source_cluster_order_id = 4;
}

message VolumeStatus {
  VolumeState state = 1;
  string vendor_volume_id = 2;
  string vendor_backend_id = 3;
  repeated Condition conditions = 4;
  google.protobuf.Timestamp bound_at = 5;
}

enum VolumeState {
  VOLUME_STATE_UNSPECIFIED = 0;
  VOLUME_STATE_PENDING = 1;
  VOLUME_STATE_CREATING = 2;
  VOLUME_STATE_BOUND = 3;
  VOLUME_STATE_DELETING = 4;
  VOLUME_STATE_DELETED = 5;
  VOLUME_STATE_ERROR = 6;
}

// Internal CRUD service (not public API)
service Volumes {
  rpc Create(CreateVolumeRequest) returns (Volume);
  rpc Get(GetVolumeRequest) returns (Volume);
  rpc List(ListVolumesRequest) returns (ListVolumesResponse);
  rpc Update(UpdateVolumeRequest) returns (Volume);
  rpc Delete(DeleteVolumeRequest) returns (google.protobuf.Empty);
}
```

#### StorageTier Configuration Resource (fulfillment-service)

```protobuf
// api/v1/storage_tier.proto
message StorageTier {
  string id = 1;
  StorageTierMetadata metadata = 2;
  StorageTierSpec spec = 3;
  StorageTierStatus status = 4;
}

message StorageTierMetadata {
  string name = 1;
  string display_name = 2;
  string description = 3;
  map<string, string> labels = 4;
  map<string, string> annotations = 5;
}

message StorageTierSpec {
  repeated StorageBackendRef backends = 1;
  BackendSelectionPolicy selection_policy = 2;
  StorageTierQuotaDefaults quota_defaults = 3;
}

message StorageBackendRef {
  string backend_id = 1;
  string vendor_type = 2; // "netapp", "vast", "pure"
  string vendor_csi_driver = 3;
  string vendor_endpoint = 4;
  map<string, string> vendor_parameters = 5;
  int64 capacity_bytes = 6;
}

enum BackendSelectionPolicy {
  BACKEND_SELECTION_POLICY_UNSPECIFIED = 0;
  BACKEND_SELECTION_POLICY_ROUND_ROBIN = 1;
  BACKEND_SELECTION_POLICY_CAPACITY_WEIGHTED = 2;
  BACKEND_SELECTION_POLICY_AFFINITY = 3;
}

message StorageTierQuotaDefaults {
  int64 max_volume_size_bytes = 1;
  int64 max_total_capacity_bytes = 2;
  int32 max_volume_count = 3;
}

message StorageTierStatus {
  int64 total_capacity_bytes = 1;
  int64 available_capacity_bytes = 2;
  int32 backend_count = 3;
  repeated Condition conditions = 4;
}

service StorageTiers {
  rpc Create(CreateStorageTierRequest) returns (StorageTier);
  rpc Get(GetStorageTierRequest) returns (StorageTier);
  rpc List(ListStorageTiersRequest) returns (ListStorageTiersResponse);
  rpc Update(UpdateStorageTierRequest) returns (StorageTier);
  rpc Delete(DeleteStorageTierRequest) returns (google.protobuf.Empty);
}
```

#### ClusterOrder Post-Install Hook (osac-operator)

The ClusterOrder CRD is extended with a new status condition:

```yaml
conditions:
  - type: StorageReady
    status: "True"
    reason: CSIDriverDeployed
    message: "OSAC CSI driver deployed and StorageClasses created"
```

The ClusterOrder controller adds a post-install lifecycle hook that creates a Job CR referencing the `osac-csi-driver-deploy` AAP role.

### Implementation Details/Notes/Constraints

#### osac-csi-driver Architecture

The CSI driver runs as two components on the tenant cluster:

- **Controller plugin** (Deployment, 1 replica): Handles `CreateVolume`, `DeleteVolume`, `ControllerPublishVolume`, `ControllerUnpublishVolume`. Communicates with fulfillment-service internal API over mTLS. Proxies resolved CSI calls to vendor CSI drivers on the hub cluster via a gRPC forwarder.
- **Node plugin** (DaemonSet): Handles `NodeStageVolume`, `NodePublishVolume`, `NodeUnstageVolume`, `NodeUnpublishVolume`. Mounts volumes using standard Linux block device operations after the controller plugin has attached the volume via the vendor CSI driver.

The controller plugin authenticates to fulfillment-service using a Kubernetes service account token projected into the pod and exchanged for a fulfillment-service session token via the existing authentication flow.

#### Hub-Spoke CSI Proxy Pattern

The CSI driver does not communicate directly with storage backends. Instead:

1. The controller plugin on the tenant cluster calls fulfillment-service to resolve the tier and obtain credentials.
2. The controller plugin makes a gRPC call to the vendor CSI driver's controller service running on the hub cluster, passing the short-lived credentials as CSI secrets.
3. The vendor CSI driver on the hub cluster performs the actual storage operation.

This pattern ensures:
- No long-lived storage credentials on tenant clusters.
- Vendor CSI drivers are managed centrally on the hub, not per-tenant cluster.
- The fulfillment-service remains the single control point for policy, quota, and audit.

#### Database Schema (fulfillment-service)

Two new tables:

```sql
CREATE TABLE storage_tiers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL UNIQUE,
    display_name TEXT,
    description TEXT,
    spec JSONB NOT NULL,
    status JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    deleted_at TIMESTAMPTZ
);

CREATE TABLE volumes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    tenant_id UUID NOT NULL REFERENCES tenants(id),
    storage_tier TEXT NOT NULL REFERENCES storage_tiers(name),
    capacity_bytes BIGINT NOT NULL,
    access_mode TEXT NOT NULL DEFAULT 'ReadWriteOnce',
    state TEXT NOT NULL DEFAULT 'Pending',
    vendor_volume_id TEXT,
    vendor_backend_id TEXT,
    source_cluster_order_id UUID,
    spec JSONB NOT NULL DEFAULT '{}',
    status JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    deleted_at TIMESTAMPTZ,
    UNIQUE(tenant_id, name)
);

CREATE INDEX idx_volumes_tenant_id ON volumes(tenant_id);
CREATE INDEX idx_volumes_state ON volumes(state);
CREATE INDEX idx_volumes_storage_tier ON volumes(storage_tier);
```

#### Fulfillment-Service Server Implementation

The storage internal API follows the existing generic server pattern in `internal/servers/`:

- `storage_tier_server.go` implements CRUD for StorageTier resources.
- `volume_server.go` implements CRUD for Volume resources.
- `storage_tier_resolver_server.go` implements the `ResolveTier` RPC with backend selection logic.
- `storage_policy_checker_server.go` implements `CheckPolicy` by querying tenant quota allocations against current volume inventory.
- `storage_credential_provider_server.go` implements `GetCredentials` by retrieving vendor credentials from a configured secret store and wrapping them with a short TTL.

The `setPayload()` switch statement in `internal/servers/generic_server.go` must be updated to handle the new `Volume` and `StorageTier` types. Table rendering definitions are added in `internal/rendering/tables/volumes.yaml` and `internal/rendering/tables/storage_tiers.yaml`.

#### AAP Role: osac-csi-driver-deploy

A new Ansible role in `osac-aap/roles/osac_csi_driver_deploy/` that:

1. Adds the OSAC Helm chart repository to the target cluster.
2. Installs the `osac-csi-driver` chart with values derived from the ClusterOrder and tenant configuration.
3. Creates StorageClass objects for each StorageTier available to the tenant.
4. Waits for the CSI driver pods to reach Ready state.
5. Reports status back via the Job CR, which the ClusterOrder controller reads to set the `StorageReady` condition.

#### Helm Chart Structure

```
charts/osac-csi-driver/
  Chart.yaml
  values.yaml
  templates/
    csidriver.yaml           # CSIDriver object
    controller-deployment.yaml
    controller-rbac.yaml     # ServiceAccount, ClusterRole, ClusterRoleBinding
    node-daemonset.yaml
    node-rbac.yaml
    storageclass.yaml        # Template for StorageClass generation
    configmap.yaml           # Fulfillment-service endpoint configuration
```

The chart is added as a dependency in `osac-installer/charts/osac/Chart.yaml` but is disabled by default (`csi-driver.enabled: false`) since it is deployed per-cluster via AAP, not on the hub.

### Security Considerations

**Credential isolation:** Storage vendor credentials never reside on tenant clusters. The CSI controller plugin obtains short-lived credentials per-operation from fulfillment-service, which retrieves them from a central secret store. Credentials expire after a configurable TTL (default: 5 minutes) and are scoped to the specific operation and backend.

**mTLS between CSI driver and fulfillment-service:** The CSI controller plugin communicates with the fulfillment-service internal API over mTLS. The client certificate is provisioned during CSI driver deployment and rotated via cert-manager or AAP automation.

**Tenant isolation at the API layer:** All internal storage API calls include the tenant ID, which is validated against the requesting service account's tenant binding. OPA policies enforce that a CSI driver instance authenticated for tenant A cannot perform operations on tenant B's volumes.

**No cross-tenant volume access:** Volume inventory records include the tenant ID as a foreign key. The Volume CRUD service filters all queries by tenant ID, enforced by OPA policies identical to those used for networking and compute resources.

**Input validation:** The `ResolveTier`, `CheckPolicy`, and volume CRUD endpoints validate all inputs: tier names must match existing StorageTier resources, capacity must be positive and within configured limits, and access modes must be one of the supported values.

### Failure Handling and Recovery

| Failure Mode | Behavior | Recovery | User Observation |
|---|---|---|---|
| Fulfillment-service unreachable | CSI driver returns `UNAVAILABLE` | Kubernetes retries PVC provisioning with exponential backoff | PVC stays `Pending` with event "storage control plane unavailable" |
| StorageTier has no healthy backends | `ResolveTier` returns `UNAVAILABLE` | Admin adds/repairs backends; next CSI call succeeds | PVC stays `Pending` with event "no storage backends available for tier" |
| Tenant quota exceeded | `CheckPolicy` returns `PERMISSION_DENIED` | Tenant deletes volumes or admin increases quota | PVC stays `Pending` with event "storage quota exceeded" |
| Vendor CSI CreateVolume fails | Error propagated to Kubernetes | Kubernetes retries; admin investigates vendor backend | PVC stays `Pending` with vendor-specific error event |
| Volume inventory write fails after successful vendor create | Orphaned volume logged; reconciler creates record | Periodic reconciliation loop (every 5 minutes) scans vendor backends | PVC is bound (Kubernetes perspective); inventory eventually consistent |
| AAP CSI deployment fails | Job CR reports failure; `StorageReady` condition is `False` | ClusterOrder controller retries the AAP job | Cluster reports `StorageReady=False` with reason and message |
| CSI driver pod crash on tenant cluster | Kubernetes restarts pod | Automatic via Deployment/DaemonSet | Temporary PVC provisioning delay; in-flight operations may need retry |

**Idempotency:** All CSI operations are idempotent per the CSI specification. The fulfillment-service internal APIs are also idempotent: `ResolveTier` and `CheckPolicy` are read-only, and `GetCredentials` issues new credentials on each call (stateless). Volume inventory CRUD uses UUIDs for deduplication.

### RBAC / Tenancy

**New roles:**

| Role | Persona | Permissions |
|---|---|---|
| `storage-tier-admin` | Cloud Infrastructure Admin | CRUD on StorageTier resources, view all Volumes |
| `storage-tier-viewer` | Cloud Provider Admin | View StorageTier and Volume resources across tenants |
| `volume-viewer` | Tenant Admin | View Volume resources within their tenant |

**Tenant isolation:**

- `StorageTier` is a platform-level resource (no tenant annotation). Tier availability per-tenant is controlled via a separate `StorageTierBinding` configuration (similar to how NetworkClass works).
- `Volume` resources carry `osac.openshift.io/tenant` annotation set to the owning tenant ID. All Volume CRUD operations filter by tenant.
- OPA policies enforce that the CSI driver's service account can only operate on volumes belonging to its tenant.
- The `osac.openshift.io/owner-reference` annotation on Volume records points to the source ClusterOrder, enabling cascade deletion when a cluster is deprovisioned.

### Observability and Monitoring

**New metrics (fulfillment-service):**

| Metric | Type | Description |
|---|---|---|
| `osac_storage_volume_total` | Gauge | Total volume count by tenant, tier, and state |
| `osac_storage_capacity_bytes_total` | Gauge | Total provisioned capacity by tenant and tier |
| `osac_storage_tier_available_capacity_bytes` | Gauge | Available capacity per storage tier |
| `osac_storage_resolve_tier_duration_seconds` | Histogram | Latency of ResolveTier calls |
| `osac_storage_check_policy_duration_seconds` | Histogram | Latency of CheckPolicy calls |
| `osac_storage_get_credentials_duration_seconds` | Histogram | Latency of GetCredentials calls |
| `osac_storage_orphaned_volumes_total` | Gauge | Count of volumes in vendor backends without inventory records |

**New metrics (osac-csi-driver):**

| Metric | Type | Description |
|---|---|---|
| `osac_csi_operations_total` | Counter | CSI operations by type (create, delete, attach, detach) and status (success, error) |
| `osac_csi_operation_duration_seconds` | Histogram | End-to-end CSI operation latency |
| `osac_csi_credential_refresh_total` | Counter | Credential refresh count by backend |

**Kubernetes events:**
- `StorageReady` / `StorageNotReady` events on ClusterOrder when CSI deployment succeeds/fails.
- `VolumeProvisioned` / `VolumeProvisionFailed` events on the CSI driver pod.

**Alerts:**
- `OSACStorageOrphanedVolumes` fires when `osac_storage_orphaned_volumes_total > 0` for more than 15 minutes.
- `OSACStorageTierDegraded` fires when a StorageTier has fewer than the minimum required healthy backends.
- `OSACCSIDriverUnavailable` fires when the CSI controller plugin pod is not Ready for more than 5 minutes.

### Risks and Mitigations

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Hub-spoke gRPC latency adds provisioning overhead | Medium | Medium | Credential caching (within TTL), connection pooling, and async inventory writes reduce critical-path latency. Target: < 2s added latency for CreateVolume. |
| Vendor CSI driver incompatibilities | Medium | High | Abstract vendor differences behind the proxy layer. Start with NetApp Trident (most mature), add VAST and Pure in subsequent phases with conformance test suite. |
| Orphaned volumes from inventory write failures | Low | Medium | Periodic reconciliation loop and orphaned volume metric/alert. Manual cleanup via admin CLI. |
| Credential TTL too short for large volume operations | Low | Medium | Configurable TTL per operation type. Default 5 minutes for create/delete, 2 minutes for attach/detach. CSI driver can request credential extension. |
| AAP deployment race with cluster readiness | Medium | Low | ClusterOrder controller waits for `KubernetesAPIReady` condition before firing the storage hook. AAP role includes readiness checks. |
| mTLS certificate rotation disrupts CSI driver | Low | High | Use cert-manager with 30-day rotation and 7-day overlap. CSI driver watches for certificate file changes and reloads without restart. |

### Drawbacks

**Complexity of the hub-spoke CSI proxy pattern:** Introducing a proxy CSI driver that delegates to vendor CSI drivers on the hub cluster adds an architectural layer that does not exist in standard Kubernetes storage. This increases the debugging surface for storage issues and requires operators to understand the OSAC-specific CSI flow rather than standard CSI troubleshooting. The tradeoff is justified by the multi-tenant credential isolation requirement, which cannot be met by deploying vendor CSI drivers directly on tenant clusters.

**New repository:** Creating `osac-csi-driver` as a separate repository adds a component to the release and CI matrix. This is necessary because the CSI driver has a distinct deployment lifecycle (per-cluster, not per-hub) and different build tooling (Go + CSI sidecar containers) from other OSAC components.

**Internal API surface growth:** Three new internal gRPC services increase the internal API surface. These are intentionally internal (not on the public port) to keep the public API clean until the public Volume API (OSAC-984) is designed. The internal services may be refactored or merged when the public API is introduced.

## UX Alignment

No `@temp-api` file exists for storage resources in `osac-ux/libs/ui-components/src/api/v1/`. UI integration is explicitly out of scope for this enhancement and deferred until the public Volume API (OSAC-984) ships.

## Alternatives (Not Implemented)

### Direct vendor CSI deployment on tenant clusters

Deploy vendor-specific CSI drivers (e.g., NetApp Trident) directly on each tenant cluster with pre-configured credentials. This is simpler but violates tenant isolation: long-lived vendor credentials would reside on tenant clusters, and each tenant would need per-vendor CSI configuration. Rejected because multi-tenant credential isolation is a core requirement.

### Storage proxy as a sidecar

Instead of a standalone CSI driver, run the OSAC storage proxy as a sidecar to each vendor CSI driver on the hub. This reduces the component count but couples OSAC tightly to vendor CSI driver deployment patterns and makes per-tenant policy enforcement harder. Rejected because the standalone CSI driver provides a cleaner abstraction boundary.

### Fulfillment-service as the CSI controller

Have the fulfillment-service itself implement the CSI Controller service, eliminating the separate `osac-csi-driver`. This collapses the architecture but mixes Kubernetes CSI lifecycle (sidecar containers, socket communication) with the fulfillment-service's gRPC server model. Rejected to maintain separation of concerns and allow independent scaling and deployment of the CSI layer.

### Virtual volume abstraction without CSI

Provide storage to tenants through a custom API that creates volumes via vendor REST APIs without implementing CSI at all. Tenants would reference volumes by OSAC resource ID instead of PVC. Rejected because it breaks Kubernetes-native storage workflows (PVC, StorageClass, dynamic provisioning) that tenant workloads expect.

## Open Questions

1. **Vendor CSI driver lifecycle on hub:** Should vendor CSI drivers (e.g., NetApp Trident) be managed by the osac-operator as CRDs, or deployed manually by the Cloud Infrastructure Admin? The current design assumes pre-deployed vendor CSI drivers.

2. **Credential store backend:** Should short-lived credentials be generated from a Vault instance, derived from Kubernetes secrets on the hub, or managed by a dedicated credential service? The current design abstracts this behind the `StorageCredentialProvider` service.

3. **StorageTier availability model:** Should tier-to-tenant availability be a separate `StorageTierBinding` resource (like NetworkClass) or embedded as a field in the StorageTier spec? The binding model is more flexible but adds another resource type.

4. **Volume lifecycle on cluster deletion:** When a ClusterOrder is deleted, should all volumes on that cluster be automatically deleted, detached and preserved, or should deletion be blocked until volumes are manually removed? This affects the `osac.openshift.io/owner-reference` cascade behavior.

## Test Plan

### Unit Tests

- **StorageTierResolver:** Verify tier resolution with single backend, multiple backends with round-robin, capacity-weighted selection, and affinity. Test fallback when primary backend is unavailable.
- **StoragePolicyChecker:** Verify quota enforcement for volume count, per-volume size limit, and total capacity limit. Test quota check when tenant has no quota configured (default behavior).
- **StorageCredentialProvider:** Verify credential generation with correct TTL, scoped to the requested operation and backend. Test credential request for non-existent backend.
- **Volume CRUD:** Verify create with valid/invalid inputs, list with tenant filtering, state transitions (Pending -> Creating -> Bound -> Deleting -> Deleted), and idempotent delete.
- **StorageTier CRUD:** Verify create with valid backend references, update backend list, delete with existing volumes (should fail).
- **CSI driver controller:** Verify the full CreateVolume flow with mocked fulfillment-service calls. Test each error path (tier not found, policy denied, credential failure, vendor CSI failure).
- **`setPayload()` switch:** Verify Volume and StorageTier types are handled in `generic_server.go`.

### Integration Tests

- **End-to-end provisioning in kind cluster:** Create a StorageTier with a mock vendor backend, deploy the CSI driver, create a PVC, and verify the Volume inventory record is created with correct state.
- **Tenant isolation:** Create volumes for two tenants and verify that each tenant's Volume list query returns only their own volumes. Verify that a CSI driver authenticated as tenant A cannot operate on tenant B's volumes.
- **Quota enforcement:** Configure a tenant with a 100Gi total quota, provision 90Gi, and verify that a 20Gi request is rejected by `CheckPolicy`.
- **Orphan reconciliation:** Create a volume in the mock vendor backend without a corresponding inventory record and verify the reconciliation loop creates the record within the scan interval.
- **ClusterOrder post-install hook:** Create a ClusterOrder in the kind cluster and verify the AAP job is triggered and the `StorageReady` condition is set on completion.

### E2E Tests

- **Tenant provisions storage on a new cluster:** Full workflow from ClusterOrder creation through CSI driver deployment, PVC creation, and volume inventory verification. Reference `osac-test-infra` pytest fixtures for tenant and cluster setup.
- **Storage tier configuration by infrastructure admin:** Create and update StorageTiers, verify StorageClass creation on tenant clusters.
- **Volume deletion cascade:** Delete a PVC and verify the Volume inventory record transitions to `Deleted` and the vendor volume is cleaned up.
- **Multi-tenant isolation E2E:** Two tenants on separate clusters each provision storage from the same tier; verify no cross-tenant volume visibility.

Tricky test areas: vendor CSI driver mocking in kind (no real storage backends), mTLS certificate setup in CI, AAP job simulation without a full AWX deployment.

## Graduation Criteria

### Dev Preview

- CSI driver deploys on kind clusters with a mock storage backend.
- Volume inventory CRUD functional with PostgreSQL.
- StorageTier resolution works with a single backend.
- Manual CSI deployment (no AAP automation).
- Unit and integration test coverage > 80%.

### Tech Preview

- Support for at least two vendor backends (NetApp + one other).
- Automated CSI deployment via AAP on ClusterOrder provisioning.
- Quota enforcement functional.
- Orphan volume reconciliation operational.
- E2E test coverage for the primary provisioning workflow.

### GA

- All three vendor backends supported (NetApp, VAST, Pure).
- mTLS certificate rotation automated.
- Performance validated: < 2s added latency for CreateVolume.
- Operational runbooks and support documentation complete.
- Full E2E test coverage including failure scenarios.

## Upgrade / Downgrade Strategy

OSAC does not currently support upgrades, so data migration and backward compatibility are not concerns at this stage. The storage control plane follows the same deployment model as other OSAC components.

When upgrades are supported in the future:
- **CSI driver upgrades** will use rolling updates (Deployment for controller, DaemonSet for node plugin) with PodDisruptionBudget to maintain availability.
- **Proto schema changes** to the internal storage API will follow the fulfillment-service's existing backward-compatibility policy (additive field additions, no field removal without deprecation).
- **Database migrations** for the `volumes` and `storage_tiers` tables will use the fulfillment-service's existing migration framework.
- **Helm chart upgrades** will be managed by the AAP role, which will perform `helm upgrade` with the new chart version.

## Version Skew Strategy

During phased rollouts:
- **CSI driver on tenant cluster vs. fulfillment-service on hub:** The internal gRPC services use versioned proto packages. The CSI driver should tolerate receiving fields it does not recognize (additive-only proto evolution). If a required field is missing in a response, the CSI driver logs a warning and fails the operation gracefully.
- **AAP role vs. Helm chart:** The AAP role pins the Helm chart version. Version skew between the role and the chart is prevented by including the chart version in the AAP role defaults and validating it before deployment.
- **Multiple tenant clusters at different CSI driver versions:** Supported. Each tenant cluster's CSI driver communicates with the same fulfillment-service internal API, which handles version differences via proto compatibility.

## Support Procedures

### Detecting failures

- **CSI driver not provisioning volumes:** Check the CSI controller plugin pod logs on the tenant cluster (`kubectl logs -n osac-csi deployment/osac-csi-controller`). Look for gRPC error codes from fulfillment-service calls. Check the `osac_csi_operations_total` metric for error rate.
- **StorageTier degraded:** Query `osac_storage_tier_available_capacity_bytes` for the affected tier. Check StorageTier conditions in fulfillment-service for backend health status.
- **Orphaned volumes:** Alert `OSACStorageOrphanedVolumes` fires. Query the `osac_storage_orphaned_volumes_total` metric. Review the reconciliation loop logs in fulfillment-service.
- **CSI deployment failed on cluster:** Check ClusterOrder conditions for `StorageReady=False`. Review the AAP job logs in AWX/AAP for deployment errors.

### Disabling the storage control plane

- **Per-cluster:** Delete the `osac-csi-driver` Helm release on the tenant cluster. Existing PVCs and PVs remain but cannot be dynamically provisioned.
- **Platform-wide:** Set `csi-driver.enabled: false` in the osac-installer values and remove the ClusterOrder post-install hook. Existing volumes continue to function but no new volumes can be provisioned.

Consequences:
- Existing mounted volumes remain available (the node plugin handles unmount on pod deletion).
- PVCs in `Pending` state will remain pending indefinitely.
- No data loss -- volumes persist on the vendor backend regardless of CSI driver state.

### Re-enabling

Re-deploy the CSI driver Helm chart. The driver reconnects to fulfillment-service and resumes operations. No volume data migration is needed.

## Infrastructure Needed

- **New repository:** `osac-project/osac-csi-driver` for the CSI driver source code and Helm chart.
- **CI pipeline:** GitHub Actions workflow for `osac-csi-driver` with Go build, unit tests, CSI sanity test suite, container image build and push.
- **Container images:** `osac-csi-driver-controller` and `osac-csi-driver-node` images published to the OSAC container registry.
- **Kind test fixtures:** Mock storage backend for integration testing (a minimal CSI driver that creates local PVs, simulating vendor CSI behavior).
