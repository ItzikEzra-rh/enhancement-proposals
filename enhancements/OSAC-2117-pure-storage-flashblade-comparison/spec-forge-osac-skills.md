---
title: Pure Storage FlashBlade File Storage (NFS) Provider
jira: OSAC-2117
authors:
  - "@osac-team"
reviewers: []
creation-date: 2026-07-30
status: implementable
---

# Pure Storage FlashBlade File Storage (NFS) Provider

## Summary

Integrate Pure Storage FlashBlade as a file storage (NFS) provider in OSAC, extending the provider-pluggable storage architecture established by the existing VAST implementation. A new Ansible role (`osac.templates.pure_storage`) handles the full lifecycle — Realm checkout, CSI operator deployment, StorageClass provisioning, NFS export policy management, and teardown — while reusing the existing `StorageBackend` registration API with `provider: "pure"`.

## Motivation

OSAC currently supports only VAST Data as an NFS storage backend. Pure Storage FlashBlade is a widely deployed enterprise NFS platform with a fundamentally different isolation model: pre-created Realms with scoped API keys rather than dynamically provisioned tenants. Supporting FlashBlade broadens OSAC's storage ecosystem without requiring API or operator changes, validating the pluggable provider architecture.

### Goals

- Implement `osac.templates.pure_storage` AAP role with lifecycle actions matching the VAST role's interface: `setup`, `ensure_storage_class`, `teardown_cluster_storage`, `teardown_backend`, `ensure_csi_operator`.
- Realm pool checkout/release mechanism for tenant isolation using pre-created FlashBlade Realms.
- Per-tenant StorageClasses with `osac.openshift.io/tenant` and `storage-tier` labels.
- Pure CSI integration via Helm-based `pure-csi` operator deployment with Realm-scoped credentials.
- NFS export policies enforcing tenant network isolation.
- Clean teardown of all provisioned resources on tenant offboarding and cluster decommission.
- E2E test for tenant onboarding with Pure-backed storage.

### Non-Goals

- S3 or object storage support on FlashBlade.
- FlashArray block storage integration.
- RDMA or GPUDirect Storage paths.
- Keycloak-to-Realm RBAC mapping.
- SafeMode snapshot integration.
- Changes to `osac-operator` controllers.
- New protobuf definitions or API surface changes.

## Proposal

### Workflow

#### Tenant Onboarding

```text
Cloud Infra Admin registers FlashBlade array
  → StorageBackend created (provider: "pure", connection details)
  → Realm pool populated with pre-created Realm references

Tenant onboarding triggers AAP job
  → setup action: checkout available Realm from pool
  → ensure_csi_operator: deploy pure-csi via Helm on workload cluster
  → ensure_storage_class: create CSI Secret + StorageClasses + NFS export policies
  → Tenant gets Pure-backed StorageClasses for PVC creation
```

#### Tenant Offboarding

```text
Tenant offboarding triggers AAP job
  → teardown_cluster_storage: remove StorageClasses, CSI Secrets, NFS export policies
  → teardown_backend: release Realm back to pool
  → Realm becomes available for next tenant
```

### API Extensions

No protobuf or gRPC API changes are required. The existing `StorageBackend` private API accepts a free-form `provider` string field. Registration uses:

```text
StorageBackend:
  metadata:
    name: "flashblade-site-a"
    annotations:
      osac.openshift.io/tenant: "<tenant-id>"
  spec:
    provider: "pure"
    connection:
      management_endpoint: "https://flashblade.example.com"
      api_token: "<secret-ref>"
    config:
      realm_pool:
        - realm_name: "realm-01"
          api_client_id: "<secret-ref>"
        - realm_name: "realm-02"
          api_client_id: "<secret-ref>"
```

The `config` block is provider-specific and opaque to the fulfillment-service. The AAP role interprets it.

### Implementation Details

#### AAP Role: `osac.templates.pure_storage`

The role follows the same action-based interface as `osac.templates.vast_storage`:

| Action | Description |
|--------|-------------|
| `setup` | Check out an available Realm from the pool. Mark the Realm as allocated in the StorageBackend status. Validate FlashBlade API connectivity using the Realm-scoped API key. |
| `ensure_csi_operator` | Deploy `pure-csi` Helm chart on the workload cluster. Configure the operator with FlashBlade management endpoint and Realm-scoped credentials. |
| `ensure_storage_class` | Create a Kubernetes Secret with Realm API credentials. Create StorageClasses (`pure-file-standard`, `pure-file-premium`) labeled with `osac.openshift.io/tenant` and `storage-tier`. Configure NFS export policies on FlashBlade to restrict access to tenant subnet CIDRs. |
| `teardown_cluster_storage` | Remove tenant StorageClasses and CSI Secrets from the workload cluster. Remove NFS export policies from FlashBlade for the tenant. |
| `teardown_backend` | Release the Realm back to the available pool. Clear allocation metadata from StorageBackend status. |

#### Realm Pool Mechanism

FlashBlade Realms are pre-created by the infrastructure administrator. Unlike VAST, where tenants are dynamically created via API, Pure Storage requires:

1. **Pool registration**: Admin registers a StorageBackend with a list of Realm references (name + API client credentials stored as Secret references).
2. **Checkout**: The `setup` action selects an unallocated Realm, marks it as allocated (storing tenant ID and allocation timestamp in the StorageBackend annotation `osac.openshift.io/realm-allocations`).
3. **Release**: The `teardown_backend` action clears the allocation, returning the Realm to the available pool.

Concurrency safety: The AAP role uses Kubernetes resource versioning (optimistic concurrency) on the StorageBackend annotation to prevent double-allocation. On conflict, the role retries with exponential backoff (max 3 attempts).

#### Realm Allocation Annotation Schema

```yaml
osac.openshift.io/realm-allocations: |
  realm-01:
    tenant_id: "tenant-abc"
    allocated_at: "2026-07-30T12:00:00Z"
    cluster_order_id: "co-123"
  realm-02:
    tenant_id: ""
    allocated_at: ""
    cluster_order_id: ""
```

#### Pure CSI Integration

The `ensure_csi_operator` action deploys the Pure Storage CSI driver via Helm:

- **Chart**: `pure/pure-csi` from the Pure Storage Helm repository
- **Ansible collection**: `purestorage.flashblade` for FlashBlade API operations (NFS export policies, filesystem management)
- **CSI provisioner**: `pure-csi` (vs. `csi.vastdata.com` for VAST)
- **Credentials**: Realm-scoped API key stored in a Kubernetes Secret, referenced by the CSI driver configuration

#### NFS Export Policies

Tenant isolation at the storage layer uses NFS export policies instead of VAST's `client_ip_ranges`:

```yaml
- name: "tenant-{{ tenant_id }}-export-policy"
  rules:
    - client: "{{ tenant_subnet_cidr }}"
      permission: "rw"
      access: "root-squash"
```

Export policies are applied per filesystem on the FlashBlade, scoped to the tenant's allocated Realm. The `ensure_storage_class` action creates these policies; `teardown_cluster_storage` removes them.

#### Key Differences from VAST

| Aspect | VAST | Pure Storage FlashBlade |
|--------|------|------------------------|
| Tenant isolation | Dynamic tenant creation via API | Pre-created Realm pool checkout/release |
| Network isolation | `client_ip_ranges` on VIP pools | NFS export policies on filesystems |
| CSI driver | `csi.vastdata.com` | `pure-csi` (Helm-deployed) |
| Ansible collection | Custom REST modules | `purestorage.flashblade` |
| Credential scope | Per-tenant API key generated on create | Per-Realm API client, pre-provisioned |
| Teardown | Delete tenant via API | Release Realm, clear export policies |

### Security

- **Realm API keys**: Stored as Kubernetes Secrets, referenced by name in StorageBackend config. Never stored in annotations or plaintext.
- **NFS export policies**: Restrict access to tenant subnet CIDRs only. Default-deny: no export rule means no access.
- **CSI Secret rotation**: The role supports re-running `ensure_storage_class` to rotate credentials without disruption (Secret update + CSI driver restart).
- **Realm isolation**: Each Realm has independent API credentials. Compromising one Realm's credentials does not grant access to another Realm's data.

### Failure Handling

| Failure | Handling |
|---------|----------|
| FlashBlade API unreachable during `setup` | Fail the AAP job. Retry is handled by the existing job retry mechanism. Realm is not checked out. |
| No available Realms in pool | Fail with `FAILED_PRECONDITION`. Admin must add more Realms to the StorageBackend or release existing allocations. |
| Realm checkout conflict (concurrent allocation) | Optimistic concurrency retry (3 attempts with exponential backoff). If exhausted, fail the job. |
| CSI Helm deployment failure | Fail the AAP job. The `ensure_csi_operator` action is idempotent; re-running the job retries deployment. |
| NFS export policy creation failure | Fail the AAP job after StorageClass creation. On retry, the action checks for existing policies before creating. |
| Teardown with active PVCs | `teardown_cluster_storage` checks for bound PVCs using the tenant's StorageClasses. If found, fails with `FAILED_PRECONDITION` and lists the PVC names. |
| Partial teardown failure | Each teardown step is idempotent. Re-running the teardown continues from where it left off. Export policy removal is attempted even if Secret deletion fails. |

### RBAC and Tenancy

- **Cloud Infrastructure Admin**: Can register StorageBackends with `provider: "pure"`, manage Realm pools, and view allocation status.
- **Cloud Provider Admin**: Tenant onboarding/offboarding triggers AAP jobs that execute the Pure Storage role. No direct FlashBlade access.
- **Tenant Admin/User**: Sees Pure-backed StorageClasses on their workload clusters. No visibility into Realm allocation or FlashBlade management.
- **OPA policies**: Existing tenant isolation policies apply. StorageClasses are labeled with `osac.openshift.io/tenant` for policy enforcement.
- **Realm-scoped credentials**: Each tenant's CSI Secret contains only their Realm's API key, not the management-level credential.

### Observability

- **AAP job metrics**: Existing AAP job duration and success/failure metrics apply to Pure Storage actions.
- **Realm pool utilization**: A Prometheus metric `osac_storage_realm_pool_total{provider="pure",backend="<name>"}` and `osac_storage_realm_pool_allocated{provider="pure",backend="<name>"}` expose pool capacity. Emitted by the fulfillment-service when reading StorageBackend annotations.
- **Alerts**: Alert when `realm_pool_allocated / realm_pool_total > 0.8` (pool nearing exhaustion).
- **Logging**: AAP role logs Realm checkout/release events with tenant ID, Realm name, and timestamp at INFO level. API key values are never logged.

### Risks and Drawbacks

- **Realm pool exhaustion**: Fixed pool size means tenants can be blocked if all Realms are allocated. Mitigation: capacity alerts, admin documentation for adding Realms.
- **Annotation size limits**: Kubernetes annotations have a combined size limit (~256 KB). With many Realms, the allocation annotation could grow. Mitigation: for large deployments (>50 Realms), consider migrating allocation tracking to a ConfigMap or the fulfillment-service database.
- **FlashBlade API compatibility**: The `purestorage.flashblade` Ansible collection must match the FlashBlade firmware version. Mitigation: document supported firmware versions, pin collection version in `requirements.yml`.
- **No dynamic Realm creation**: Unlike VAST, scaling requires admin intervention to create new Realms on the FlashBlade and register them. This is a FlashBlade platform limitation, not an OSAC design choice.

## Alternatives

### Alternative 1: Dynamic Realm Creation via FlashBlade API

Create Realms on-demand during tenant onboarding instead of using a pre-created pool.

**Rejected because**: FlashBlade Realm creation requires array-admin-level credentials and is typically a platform engineering operation. Automating it would require storing high-privilege credentials in OSAC and add complexity for a scenario most operators handle manually.

### Alternative 2: Shared Realm with Per-Tenant Filesystem Isolation

Use a single Realm for all tenants, isolating at the filesystem/export-policy level only.

**Rejected because**: A shared Realm means a single API credential compromise affects all tenants. Per-Realm isolation provides defense-in-depth consistent with OSAC's tenant isolation requirements.

### Alternative 3: Operator-Based Storage Provisioning

Add a Pure Storage controller to `osac-operator` instead of using AAP.

**Rejected because**: The existing storage architecture uses AAP for all provider interactions. Adding an operator-based path would create two provisioning models, increasing maintenance burden. The AAP role approach is proven with VAST and keeps storage provider logic in a consistent location.

## Test Plan

### Unit Tests

- **Realm pool checkout logic**: Test allocation, release, conflict handling, and pool exhaustion scenarios using mocked StorageBackend resources.
- **NFS export policy generation**: Verify correct policy structure for various subnet CIDR inputs.
- **StorageClass template rendering**: Validate labels (`osac.openshift.io/tenant`, `storage-tier`) and CSI driver references.
- **Idempotency**: Verify that re-running each action with existing resources does not create duplicates or errors.

### Integration Tests

- **AAP role execution**: Run the full `osac.templates.pure_storage` role against a mocked FlashBlade API (using `ansible-test` with mock modules).
- **Realm lifecycle**: Checkout → use → teardown → re-checkout cycle verifying pool state consistency.
- **Concurrent checkout**: Simulate two simultaneous checkouts to verify optimistic concurrency handling.

### E2E Tests

- **Tenant onboarding with Pure storage**: Register a FlashBlade StorageBackend, onboard a tenant, verify StorageClasses appear on the workload cluster with correct labels and CSI configuration.
- **PVC creation**: Create a PVC using a Pure-backed StorageClass, verify the volume is provisioned on FlashBlade.
- **Tenant offboarding**: Offboard the tenant, verify StorageClasses, Secrets, and export policies are removed, and the Realm is released.
- **Pool exhaustion**: Allocate all Realms, attempt another tenant onboarding, verify `FAILED_PRECONDITION` error with actionable message.

## Graduation Criteria

### Dev Preview

- `osac.templates.pure_storage` role with `setup`, `ensure_storage_class`, `ensure_csi_operator` actions.
- Realm checkout/release mechanism.
- Manual testing against a FlashBlade test array.

### Tech Preview

- All lifecycle actions implemented including teardown.
- NFS export policy enforcement.
- Integration tests passing.
- Documentation for registering FlashBlade backends.

### GA

- E2E tests passing in CI.
- Concurrent checkout stress testing.
- Operational runbook for Realm pool management.
- Support for multiple FlashBlade arrays per deployment.

## Upgrade / Downgrade Strategy

- **Upgrade**: No schema migration required. Existing StorageBackends are unaffected. The new role is additive — only activated when `provider: "pure"` is registered.
- **Downgrade**: Remove Pure StorageBackends before downgrading. The role does not modify shared infrastructure. If Pure-backed PVCs exist, they must be migrated or deleted first.

## Version Skew Strategy

- **AAP collection version**: The `purestorage.flashblade` collection version is pinned in `requirements.yml`. Skew between the collection and FlashBlade firmware is handled by Pure's backward-compatibility guarantees (documented per collection version).
- **CSI driver version**: The `pure-csi` Helm chart version is pinned in the role defaults. The role supports overriding the version via StorageBackend config for environments requiring a specific CSI driver version.
- **fulfillment-service**: No version coupling. The StorageBackend API is stable and the `config` block is opaque.

## Support Procedures

### Diagnosing Realm Allocation Issues

```bash
# View Realm allocation status
kubectl get storagebackend <name> -n osac -o jsonpath='{.metadata.annotations.osac\.openshift\.io/realm-allocations}' | yq .

# Check for orphaned allocations (tenant deleted but Realm still allocated)
jira issue list -q "project = OSAC AND type = Bug AND summary ~ 'orphaned realm'" --plain
```

### Diagnosing NFS Mount Failures

1. Verify the NFS export policy exists on FlashBlade for the tenant's subnet CIDR.
2. Check the CSI driver pod logs on the workload cluster: `kubectl logs -n pure-csi -l app=pure-csi-controller`.
3. Verify the CSI Secret contains valid Realm API credentials.
4. Check network connectivity from the workload cluster nodes to the FlashBlade management endpoint.

### Emergency Realm Release

If a Realm is stuck in allocated state after tenant deletion:

```bash
# Edit the StorageBackend annotation to release the Realm
kubectl annotate storagebackend <name> -n osac \
  osac.openshift.io/realm-allocations='<updated-yaml-without-stale-entry>' --overwrite
```
