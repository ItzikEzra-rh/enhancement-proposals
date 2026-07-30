# Technical Specification: OSAC Storage Control Plane

**Jira:** OSAC-2872
**Priority:** Major
**Service:** Storage

---

## Overview

This specification defines the storage control plane that enables tenants to consume block storage through opaque tiers without exposure to vendor details, credentials, or backend addresses. The system comprises three main components: a CSI driver (`csi.osac.openshift.io`) providing standard Kubernetes PVC interface, internal gRPC services for storage decisions, and packaging/deployment automation for tenant clusters.

The control plane abstracts multiple storage vendors (NetApp ONTAP, VAST, Pure Storage) behind a single CSI driver interface, enforces per-tenant policy, delivers credentials per-request without persisting them on tenant clusters, and maintains a volume inventory.

### Goals

- Present tenants with opaque storage tiers that hide vendor implementation details
- Support multiple storage vendors behind a unified CSI driver
- Enforce per-tenant storage policy at the control plane level
- Provide credentials on a per-request basis, never stored on tenant clusters
- Maintain an authoritative volume inventory with tenant, tier, state, and size tracking
- Automate CSI driver deployment to tenant clusters as part of cluster provisioning

### Non-Goals

- Public Volume API (covered by OSAC-984)
- UI integration for storage management
- Vendor-specific REST adapters
- Storage metering and billing

---

## User Scenarios

### P1 - Critical Path

#### Scenario: Tenant provisions a persistent volume via PVC

```gherkin
Given a tenant cluster with the CSI driver installed
  And the cluster has StorageClasses mapped to opaque storage tiers
When a tenant creates a PersistentVolumeClaim referencing a StorageClass
Then the CSI driver intercepts the provisioning request
  And delegates tier resolution to the storage control plane
  And the control plane resolves the tier to a specific vendor backend
  And the control plane checks tenant policy for the requested tier and size
  And the control plane returns per-request credentials for the vendor backend
  And the CSI driver proxies the volume creation to the vendor CSI controller
  And a PersistentVolume is created and bound to the PVC
  And the volume is recorded in the volume inventory
```

#### Scenario: Tenant deletes a persistent volume

```gherkin
Given a tenant cluster with an existing PVC bound to a PersistentVolume
When the tenant deletes the PVC with ReclaimPolicy set to Delete
Then the CSI driver intercepts the deletion request
  And requests credentials from the control plane for the volume's backend
  And proxies the deletion to the vendor CSI controller
  And the volume inventory record is updated to reflect deletion
  And credentials are not retained on the tenant cluster
```

#### Scenario: Volume inventory tracks volume lifecycle

```gherkin
Given the storage control plane is running
When a volume is created, updated, or deleted through the CSI driver
Then the volume inventory is updated with the current state
  And the inventory record includes tenant ID, tier, state, and size
  And the inventory is queryable by tenant, tier, and state
```

#### Scenario: CSI driver is deployed to a new tenant cluster

```gherkin
Given a ClusterOrder has completed and a tenant cluster is available
When the post-install provisioning runs
Then the AAP role deploys the CSI driver Helm chart to the tenant cluster
  And the deployment includes controller and node components
  And RBAC resources are configured for the CSI driver service account
  And StorageClasses for available tiers are created
  And the CSI driver registers with the kubelet on each node
```

### P2 - Important

#### Scenario: Control plane enforces tenant storage policy

```gherkin
Given a tenant with a storage policy limiting allowed tiers
When the tenant requests a volume on a tier not permitted by policy
Then the control plane rejects the request with a policy violation error
  And no volume is created
  And no credentials are issued
```

#### Scenario: Credentials are scoped per-request

```gherkin
Given a CSI driver handling a volume operation
When the driver requests credentials from the control plane
Then the control plane returns credentials scoped to the specific operation
  And credentials are not cached or persisted on the tenant cluster
  And credentials are valid only for the duration of the operation
```

#### Scenario: Multiple vendor backends are supported transparently

```gherkin
Given storage tiers configured with different vendor backends
  And one tier backed by NetApp ONTAP and another by VAST
When tenants provision volumes on different tiers
Then each request is routed to the correct vendor CSI controller
  And tenants see no difference in the PVC interface
  And vendor-specific details are not exposed in StorageClass parameters
```

### P3 - Nice to Have

#### Scenario: CSI driver passes certification tests

```gherkin
Given the CSI driver is deployed to a test cluster
When the Kubernetes CSI certification test suite is executed
Then all required CSI specification tests pass
  And the driver is compatible with standard CSI sidecar containers
```

#### Scenario: Storage is provisioned for VMaaS workloads

```gherkin
Given a ComputeInstance (VM) running on a tenant cluster
When the VM requires block storage
Then storage can be provisioned through the same CSI driver and tier abstraction
  And the volume is attached to the VM through standard Kubernetes volume mechanisms
```

---

## Functional Requirements

### FR-1: CSI Driver Core

The CSI driver (`csi.osac.openshift.io`) must implement the CSI specification with both controller and node service modes.

- **Controller service:** Handles `CreateVolume`, `DeleteVolume`, `ControllerPublishVolume`, `ControllerUnpublishVolume`, and `ValidateVolumeCapabilities` RPCs
- **Node service:** Handles `NodeStageVolume`, `NodeUnstageVolume`, `NodePublishVolume`, `NodeUnpublishVolume`, and `NodeGetCapabilities` RPCs
- The controller delegates all provisioning decisions to the storage control plane via internal gRPC calls
- The controller proxies actual volume operations to the resolved vendor CSI controller using per-request credentials
- The driver must not store vendor credentials locally beyond the scope of a single RPC

### FR-2: Storage Internal gRPC Service

The `StorageInternal` gRPC service exposes the following RPCs to the CSI driver:

- **ResolveTier:** Accepts a StorageClass name and tenant identifier; returns the resolved vendor backend and connection parameters
- **CheckPolicy:** Accepts a tenant identifier, tier, and requested capacity; returns an allow/deny decision with reason
- **GetCredentials:** Accepts a tenant identifier, vendor backend reference, and operation type; returns scoped credentials for the specific operation

All RPCs require authenticated callers. The service enforces tenant isolation on every request.

### FR-3: Volume Inventory

The volume inventory provides CRUD operations for volume records via a private API.

- Each volume record includes: volume ID, tenant ID, tier, vendor backend reference, state (creating, available, in-use, deleting, deleted), size, and timestamps
- The inventory supports listing and filtering by tenant, tier, and state
- State transitions follow a defined lifecycle: creating -> available -> in-use -> deleting -> deleted
- The inventory is the authoritative source of volume state

### FR-4: CSI Driver Packaging

The CSI driver is packaged as a Helm chart containing:

- Controller Deployment with CSI sidecar containers (provisioner, attacher, resizer)
- Node DaemonSet with CSI node-driver-registrar
- RBAC resources (ServiceAccount, ClusterRole, ClusterRoleBinding)
- StorageClass definitions for each available tier
- CSIDriver object registration
- Configurable values for control plane endpoint, TLS certificates, and resource limits

### FR-5: Automated Cluster Storage Deployment

AAP roles automate CSI driver deployment as part of the ClusterOrder post-install workflow.

- A dedicated AAP role installs the CSI driver Helm chart on the tenant cluster
- The role configures the control plane endpoint and injects required TLS certificates
- The role verifies the CSI driver is healthy before marking deployment complete
- The deployment integrates with the existing ClusterOrder provisioning lifecycle

---

## Interface Changes

### New gRPC Service: StorageInternal

```
service StorageInternal {
  rpc ResolveTier(ResolveTierRequest) returns (ResolveTierResponse);
  rpc CheckPolicy(CheckPolicyRequest) returns (CheckPolicyResponse);
  rpc GetCredentials(GetCredentialsRequest) returns (GetCredentialsResponse);
}
```

### New Private API: Volumes

```
service Volumes {
  rpc Create(CreateVolumeRequest) returns (Volume);
  rpc Get(GetVolumeRequest) returns (Volume);
  rpc List(ListVolumesRequest) returns (ListVolumesResponse);
  rpc Update(UpdateVolumeRequest) returns (Volume);
  rpc Delete(DeleteVolumeRequest) returns (google.protobuf.Empty);
}
```

### New Kubernetes Resources

- **CSIDriver:** `csi.osac.openshift.io` registration object
- **StorageClass:** One per opaque tier (e.g., `osac-standard`, `osac-performance`)
- **Deployment:** CSI controller with sidecar containers
- **DaemonSet:** CSI node plugin on each worker node
- **ServiceAccount, ClusterRole, ClusterRoleBinding:** RBAC for CSI components

### New Helm Chart

- `charts/osac-csi-driver/` with values for control plane endpoint, TLS, resource limits, and tier configuration

---

## Error Handling

| Error Condition | Behavior | User-Visible Effect |
|----------------|----------|-------------------|
| Tier resolution fails (unknown tier) | `ResolveTier` returns `NOT_FOUND` | PVC remains in Pending state with event describing unknown tier |
| Policy check denies request | `CheckPolicy` returns `PERMISSION_DENIED` with reason | PVC remains in Pending state with event describing policy violation |
| Credential retrieval fails | `GetCredentials` returns `UNAVAILABLE` | PVC provisioning retries with exponential backoff; event logged |
| Vendor CSI controller unreachable | CSI driver returns `UNAVAILABLE` to kubelet | PVC remains in Pending state; CSI driver retries per CSI spec |
| Volume inventory write fails | Inventory returns `INTERNAL` error | CSI operation fails; volume is not created on the vendor backend |
| Tenant not found | All RPCs return `NOT_FOUND` | PVC remains in Pending state with event describing unknown tenant |
| Invalid volume state transition | Inventory returns `FAILED_PRECONDITION` | Operation is rejected; current state preserved |
| Control plane unavailable during deletion | CSI driver retries with backoff | PV deletion is retried by the PV controller |

---

## Testing Requirements

### Unit Tests

- StorageInternal service: tier resolution logic, policy evaluation, credential scoping
- Volume inventory: CRUD operations, state machine transitions, invalid transition rejection
- CSI driver controller: request delegation, credential forwarding, error propagation
- CSI driver node: mount/unmount operations, device staging

### Integration Tests

- CSI driver end-to-end: PVC create -> volume provision -> attach -> mount -> unmount -> detach -> delete
- Multi-vendor: verify tier resolution routes to correct vendor backend
- Policy enforcement: verify denied requests never reach the vendor backend
- Credential lifecycle: verify credentials are not persisted after operation completes
- Volume inventory consistency: verify inventory state matches actual vendor state after operations

### Deployment Tests

- Helm chart: template rendering with various value combinations
- AAP role: deployment to a test cluster, verify CSI driver health checks pass
- Upgrade: verify CSI driver upgrade does not disrupt existing mounted volumes

### CSI Conformance

- Run the Kubernetes CSI certification test suite against the driver
- Verify compatibility with CSI sidecar containers at their specified versions

---

## Open Questions

1. **Credential TTL:** What is the maximum lifetime for per-request credentials? Should the control plane enforce an upper bound, or is this delegated to each vendor adapter?

2. **Tier discovery:** How are available tiers communicated to the CSI driver? Are they configured statically in the Helm chart values, or discovered dynamically from the control plane?

3. **Volume migration:** If a vendor backend is decommissioned, is there a path to migrate volumes to another backend within the same tier? This is likely out of scope for the initial implementation but may affect data model decisions.

4. **Quota enforcement:** The extension stories mention quota lifecycle. Should the `CheckPolicy` RPC account for quota in the initial implementation, or is quota enforcement deferred?

5. **Multi-attach:** Should the CSI driver support `ReadWriteMany` access mode, or is it limited to `ReadWriteOnce` for the initial release?

6. **Observability:** What metrics should the CSI driver and control plane export? Are there specific SLIs (e.g., provisioning latency, credential issuance time) that need to be tracked from day one?

7. **Failure domain:** If the storage control plane is unavailable, should the CSI driver allow reads/writes to already-mounted volumes, or does it require control plane connectivity for all operations?
