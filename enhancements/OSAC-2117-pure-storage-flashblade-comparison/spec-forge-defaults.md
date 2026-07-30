# Technical Specification: Pure Storage FlashBlade File Storage (NFS) Provider

**Jira:** OSAC-2117
**Type:** Feature
**Service:** Storage

## Overview

Integrate Pure Storage FlashBlade as a file storage (NFS) provider, enabling deployments to provision tenant-isolated NFS storage on Pure hardware. This adds FlashBlade as a second storage backend option alongside the existing VAST implementation, following a provider-pluggable architecture.

The core challenge is that Pure FlashBlade uses a fundamentally different tenant isolation model from VAST: datacenter admins pre-create Realms on FlashBlade with capacity and network constraints already configured, then hand Realm-scoped API keys to the platform. The automation layer manages a pool of these Realms, checking them out during tenant onboarding and releasing them on teardown.

## User Scenarios

### P1 - Critical Path

**Scenario: Register a Pure FlashBlade storage backend**
```gherkin
Given a Cloud Infrastructure Admin with access to a Pure FlashBlade array
When they register a StorageBackend with provider set to "pure"
  And supply the FlashBlade management endpoint and Realm API keys
Then the system accepts the registration
  And the FlashBlade array is available as a storage backend
  And storage tiers can be defined referencing the Pure provider
```

**Scenario: Tenant onboarding provisions Pure NFS storage**
```gherkin
Given a registered Pure FlashBlade storage backend with available Realms in the pool
  And a storage tier configured with provider "pure"
When a new tenant is onboarded with that storage tier
Then the system checks out an available Realm from the pool
  And creates StorageClasses on the tenant's provisioned cluster
  And deploys CSI secrets using Realm-scoped credentials
  And configures NFS export policies for tenant isolation
  And the tenant's cluster has Pure-backed StorageClasses available
```

**Scenario: Tenant offboarding releases Pure FlashBlade Realm**
```gherkin
Given a tenant with active Pure FlashBlade storage
When the tenant is offboarded
Then the system removes StorageClasses from the tenant's cluster
  And removes CSI secrets and export policies
  And releases the FlashBlade Realm back to the available pool
  And the Realm is available for checkout by future tenants
```

### P2 - Important

**Scenario: Tenant user creates PVCs using Pure-backed StorageClasses**
```gherkin
Given a tenant cluster with Pure-backed StorageClasses provisioned during onboarding
When a Tenant User creates a PersistentVolumeClaim referencing a Pure StorageClass
Then the PVC is fulfilled by the Pure CSI driver
  And an NFS volume is provisioned on the FlashBlade Realm
  And the volume is accessible only by workloads in the tenant's namespace
```

**Scenario: Supply multiple Realm API keys for pool management**
```gherkin
Given a Cloud Infrastructure Admin registering a Pure FlashBlade backend
When they supply multiple pre-created FlashBlade Realm API keys
Then each Realm is added to the available pool
  And the system tracks which Realms are checked out vs available
  And no array_admin privileges are required for any Realm key
```

**Scenario: StorageClasses include tenant and tier labels**
```gherkin
Given a tenant onboarded with a Pure storage tier
When StorageClasses are created on the tenant's cluster
Then each StorageClass includes labels identifying the tenant
  And each StorageClass includes labels identifying the storage tier
```

### P3 - Nice to Have

**Scenario: Realm pool exhaustion prevents onboarding**
```gherkin
Given a Pure FlashBlade backend where all Realms are checked out
When a new tenant onboarding requests Pure storage
Then the system reports that no Realms are available
  And the onboarding does not proceed for the storage component
  And existing tenant storage is not affected
```

**Scenario: Partial teardown failure leaves Realm checked out**
```gherkin
Given a tenant offboarding is in progress
When the teardown of cluster resources succeeds but Realm release fails
Then the system reports the failure
  And the Realm remains marked as checked out
  And an administrator can manually release the Realm
```

## Functional Requirements

### Core Functions

| ID | Function | Input | Output | Rules |
|----|----------|-------|--------|-------|
| F1 | Register Pure StorageBackend | FlashBlade endpoint, Realm API keys, provider: "pure" | Registered StorageBackend resource | Must validate connectivity to FlashBlade; Realm keys must be Realm-scoped (not array_admin) |
| F2 | Realm pool checkout | Tenant ID, storage tier | Checked-out Realm with credentials | Must select an available Realm; mark it as checked out; associate with tenant |
| F3 | Realm pool release | Tenant ID | Released Realm | Must clean up tenant data on Realm before release; mark Realm as available |
| F4 | Provision StorageClasses | Tenant cluster, Realm credentials | StorageClasses with tenant/tier labels | Must deploy pure-csi Helm chart; create CSI secrets from Realm credentials |
| F5 | Configure NFS export policies | Realm, tenant network info | Export policies on FlashBlade | Must restrict NFS access to tenant's network; use filesystem-level export policies |
| F6 | Teardown cluster storage | Tenant cluster | Removed StorageClasses, CSI secrets | Must remove all Pure-related resources from cluster |
| F7 | Teardown backend storage | Realm | Cleaned and released Realm | Must remove export policies; release Realm to pool |

### Business Rules

| ID | Rule | Condition | Action |
|----|------|-----------|--------|
| BR1 | Realm-scoped credentials only | API key has array_admin privileges | Reject registration with clear error |
| BR2 | One Realm per tenant | Tenant requests Pure storage | Check out exactly one Realm; do not share Realms across tenants |
| BR3 | Realm availability check | No Realms available in pool | Fail onboarding for storage tier with descriptive error |
| BR4 | Idempotent provisioning | Setup action called for already-provisioned tenant | Must not create duplicate resources; converge to desired state |
| BR5 | Clean release | Realm released back to pool | All tenant data, export policies, and credentials must be removed before release |
| BR6 | No operator changes | New provider implementation | Must work through existing storage controller; Ansible role only |

## Interface Changes

### New Ansible Role

**Role:** `osac.templates.pure_storage`

**Actions:**
- `setup` - Register FlashBlade backend, add Realms to pool
- `ensure_storage_class` - Check out Realm, deploy pure-csi, create StorageClasses and CSI secrets
- `teardown_cluster_storage` - Remove StorageClasses, CSI secrets, pure-csi from tenant cluster
- `teardown_backend` - Remove export policies, release Realm to pool

### StorageBackend Registration

Uses existing private API with `provider: "pure"` field value. No new API endpoints required.

### Dependencies

- `purestorage.flashblade` Ansible collection for FlashBlade API interactions
- `pure-csi` Helm chart for CSI driver deployment on tenant clusters

## Error Handling

| Error Condition | Detection | Response | Recovery |
|----------------|-----------|----------|----------|
| FlashBlade unreachable | Connection timeout during registration | Reject registration with connectivity error | Admin verifies network path and retries |
| Invalid Realm API key | Authentication failure on FlashBlade API | Reject key with authentication error; do not add to pool | Admin provides valid Realm-scoped key |
| Realm pool exhausted | No available Realms at checkout time | Fail storage provisioning; report to onboarding workflow | Admin adds more Realm keys or offboards unused tenants |
| CSI driver deployment failure | Helm install/upgrade failure | Report failure; do not mark Realm as fully provisioned | Retry ensure_storage_class action |
| Export policy creation failure | FlashBlade API error during NFS policy setup | Report failure; Realm remains checked out but not usable | Retry setup or manual intervention |
| Teardown partial failure | Any cleanup step fails during offboarding | Report which steps failed; Realm stays checked out | Admin runs teardown again or manually releases Realm |
| Realm release failure after cleanup | FlashBlade API error during release | Log error; Realm remains checked out | Admin manually releases via FlashBlade UI or retries |

## Testing Requirements

| Test Type | Scope | Method | Acceptance Criteria |
|-----------|-------|--------|-------------------|
| Unit | Ansible role tasks | Molecule with mocked FlashBlade API | Each action (setup, ensure_storage_class, teardown_cluster_storage, teardown_backend) tested independently |
| Unit | Realm pool logic | Molecule | Checkout, release, exhaustion, and idempotency scenarios pass |
| Integration | StorageBackend registration | Test environment with FlashBlade access | Backend registers successfully with provider: "pure" |
| Integration | CSI driver deployment | Test cluster | pure-csi Helm chart deploys; StorageClasses created with correct labels |
| Integration | NFS export policies | Test environment with FlashBlade | Export policies restrict access to tenant network only |
| E2E | Tenant onboarding with Pure storage | Full stack with FlashBlade hardware | Tenant onboarded; PVCs created and bound; NFS volumes accessible |
| E2E | Tenant offboarding with Pure storage | Full stack with FlashBlade hardware | All resources cleaned; Realm released and available for reuse |
| E2E | Realm pool management | Full stack | Multiple tenants onboard/offboard; Realms cycle correctly through the pool |

## Open Questions

1. **Realm capacity tracking:** Should the system track remaining capacity on each Realm, or is checkout/release binary (available/checked-out)?
2. **Multi-Realm per tenant:** The spec assumes one Realm per tenant (BR2). Are there scenarios where a tenant needs multiple Realms (e.g., multiple storage tiers on the same FlashBlade)?
3. **Realm health monitoring:** Should the system periodically verify that checked-out Realms are healthy, or is that the FlashBlade admin's responsibility?
4. **Credential rotation:** How are Realm API keys rotated? Does the system need to support key update without tenant disruption?
5. **Migration path:** If a tenant is on VAST storage, is migration to Pure (or vice versa) in scope for future work?
6. **Concurrent onboarding:** What happens if two tenants attempt to check out the last available Realm simultaneously? Is there a locking mechanism?
