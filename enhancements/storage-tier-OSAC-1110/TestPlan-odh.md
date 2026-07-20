---
feature: caas_tenant_storage_setup
source_key: OSAC-1123
source_type: issue
status: Draft
author: osac
components:
- Storage
additional_docs: []
last_updated: '2026-07-20'
version: 1.0.0
reviewers: []
---
# CaaS Tenant Storage Setup Test Plan
**OSAC Storage – CaaS Tenant Storage Provisioning and Lifecycle**

**Strategy**: [OSAC-1123](https://redhat.atlassian.net/browse/OSAC-1123)

---

## 1. Executive Summary

### 1.1 Purpose

This test plan covers the CaaS Tenant Storage Setup feature, which enables
persistent storage for CaaS tenant clusters by integrating with the Tier API
and TenantStorage CR. The feature automatically installs the VAST CSI driver
and creates per-tenant, per-tier StorageClasses when a CaaS cluster reaches
ClusterOrderPhaseReady status, allowing tenant users to create PVCs targeting
the correct storage tier (e.g., fast, standard, archive) without manual
cluster configuration.

Testing validates the end-to-end storage provisioning workflow — from cluster
readiness detection through CSI driver installation, StorageClass creation,
PVC consumption, storage readiness tracking, and teardown cleanup — ensuring
that multi-tenant storage isolation is maintained and Cloud Provider Admins
have visibility into cluster storage readiness status.

### 1.2 Scope

#### In Scope (OSAC Storage Responsibilities)

- Automatic CSI driver installation on CaaS target clusters when
  ClusterOrderPhaseReady is reached
- Tier API integration (Get/List) to determine available tiers per tenant
- Per-tenant, per-tier StorageClass creation using tier information from
  fulfillment-service and connection details from K8s secrets and VAST VMS API
- VolumeSnapshotClass creation associated with storage tiers
- Storage readiness tracking on the ClusterOrder CR
- Cloud Provider Admin ability to distinguish compute-ready vs storage-ready
  clusters
- Tenant User PVC creation using tier-specific StorageClasses
- Teardown of cluster-side storage resources (StorageClasses,
  VolumeSnapshotClasses, CSI Secret) on cluster deletion
- Preservation of backend resources (VAST tenant, views, quotas) and
  per-tenant Secret during teardown
- v0.1 constraint validation: only networked storage for application data;
  etcd and control plane use local storage

#### Out of Scope (Other Teams)

- Backend VAST infrastructure provisioning (provided by CSP infrastructure
  admin)
- Long-term S3 object storage integration
- Storage caching and GPU direct access via RDMA/RoCE
- Local storage management for etcd and control plane (assumed to be handled
  by existing mechanisms)
- Web UI implementation for storage management
- Bare Metal Fulfillment operations
- Cluster provisioning up to ClusterOrderPhaseReady (handled by Cluster
  Fulfillment)

### 1.3 Test Objectives

1. Verify that the VAST CSI driver is automatically installed on a CaaS
   target cluster when it reaches ClusterOrderPhaseReady status
2. Verify that the Tier API is correctly queried to retrieve available tiers
   for a tenant, and that per-tenant, per-tier StorageClasses are created
   with correct connection details from K8s secrets and VAST VMS API
3. Verify that storage readiness is accurately tracked on the ClusterOrder
   CR, and that Cloud Provider Admins can distinguish between compute-ready
   and storage-ready clusters
4. Verify that Tenant Users can successfully create PVCs using tier-specific
   StorageClasses (e.g., fast, standard, archive) and that workloads can
   consume the provisioned storage
5. Verify that cluster teardown correctly cleans up cluster-side resources
   (StorageClasses, VolumeSnapshotClasses, CSI Secret) while preserving
   backend resources (VAST tenant, views, quotas) and per-tenant Secrets
6. Verify that the v0.1 constraint is enforced: only networked storage is
   available for application data, with etcd and control plane using local
   storage

---

## 2. Test Strategy

### 2.1 Test Levels

- **API Integration Testing** — Testing Tier API queries (Get/List) and
  VAST VMS API interactions for retrieving StorageProvider connection details,
  VIPPools, tenant credentials, views, QoS policies, and Realms
- **Functional Testing** — Validating the end-to-end storage setup workflow:
  ClusterOrderPhaseReady trigger, CSI driver installation, StorageClass
  creation, PVC provisioning, storage readiness tracking on ClusterOrder CR
- **Data Validation Testing** — Verifying correct per-tenant, per-tier
  StorageClass configurations, K8s secret data integrity, and ClusterOrder CR
  status field updates
- **Security Testing** — Validating credential management for VAST storage,
  K8s secret access controls, and multi-tenant isolation of storage resources

### 2.2 Test Types

- **Positive Testing** — Valid cluster reaching ClusterOrderPhaseReady,
  successful CSI driver installation, correct StorageClass creation for
  available tiers, successful PVC creation per tier
- **Negative Testing** — Cluster not reaching ready state, missing VAST
  credentials, unavailable Tier API, invalid tier configurations, PVC
  creation with non-existent StorageClass
- **Boundary Testing** — Maximum number of tiers per tenant, multiple tenants
  with overlapping tier configurations, concurrent cluster provisioning with
  storage setup
- **Regression Testing** — Ensure existing cluster provisioning workflow
  (compute-ready) remains intact after adding storage readiness tracking

### 2.3 Test Priorities

- **P0 (Critical)** — Core storage setup functionality that must work for
  tenants to consume persistent storage: CSI driver installation on
  ClusterOrderPhaseReady, per-tenant per-tier StorageClass creation from
  Tier API data, and PVC creation using tier-specific StorageClasses
- **P1 (High)** — Storage lifecycle management and admin visibility: storage
  readiness tracking on ClusterOrder CR, distinction between compute-ready
  and storage-ready states, and teardown cleanup of cluster-side resources
  (StorageClasses, VolumeSnapshotClasses, CSI Secret)
- **P2 (Medium)** — Edge cases and advanced scenarios: backend resource
  preservation during teardown (VAST tenant, views, quotas), error recovery
  from partial storage setup failures, multi-tier boundary conditions

---

## 3. Test Environment

### 3.1 Test Cluster Configuration

- OpenShift version: TBD
- Hub cluster with access to VAST storage infrastructure
- At least one CaaS target cluster capable of reaching
  ClusterOrderPhaseReady state
- ACM (Advanced Cluster Management) with HCP configured for cluster
  management
- VAST CSI driver installable on the CaaS target cluster
- Networking: Ethernet-only with dedicated L2 networks for tenant isolation;
  DHCP, floating IPs, and routing services required
- Storage backend: VAST storage accessible from hub cluster (networked
  storage only for v0.1; etcd and control plane use local storage)

### 3.2 Test Data Requirements

- Tier API responses: Sample tier definitions for multiple tiers (e.g.,
  fast, standard, archive) to validate per-tenant, per-tier StorageClass
  creation
- StorageProvider connection details: K8s secrets containing VAST connection
  information (VMS API endpoints, credentials)
- TenantStorage CR samples: Example custom resources representing tenant
  storage configurations
- ClusterOrder CR samples: Example CRs in ClusterOrderPhaseReady state to
  trigger the storage setup workflow
- VAST VMS API responses: Mock or real responses for VIPPools, tenant
  credentials, views, QoS policies, and Realms
- StorageClass definitions: Expected per-tenant, per-tier StorageClass YAML
  templates for validation
- VolumeSnapshotClass definitions: Expected VolumeSnapshotClass resources
  for cleanup validation
- PVC test manifests: Sample PersistentVolumeClaim YAML targeting different
  tier StorageClasses (fast, standard, archive)

### 3.3 Test Users

- **Cloud Provider Admin**: User with permissions to view ClusterOrder CR
  status and distinguish between compute-ready and storage-ready clusters
- **Tenant User**: User with permissions to create PVCs using tier-specific
  StorageClasses within their namespace
- **Cluster Admin (hub)**: User with permissions to manage VAST credentials,
  install CSI drivers, and create StorageClasses on target clusters
- **Service account for storage controller**: Account used by the automated
  storage setup process to interact with Tier API, K8s secrets, VAST VMS
  API, and target cluster resources
- **Unprivileged user**: User without storage permissions to validate that
  unauthorized PVC creation is rejected (negative testing)

---

## 4. API Endpoints / Methods / Components Under Test

| Endpoint/Method | Type | Purpose | Priority |
|-----------------|------|---------|----------|
| Tier API — Get | REST | Retrieve details for a specific storage tier available to a tenant | P0 |
| Tier API — List | REST | List all storage tiers available for a tenant | P0 |
| TenantStorage CR | Config | Custom resource defining tenant storage configuration; triggers storage setup workflow | P0 |
| ClusterOrder CR — Storage Readiness | Config | Track and report storage readiness status on the ClusterOrder custom resource | P0 |
| VAST CSI Driver Installation | Method | Install VAST CSI driver on CaaS target cluster upon ClusterOrderPhaseReady | P0 |
| StorageClass Creation | Config | Create per-tenant, per-tier StorageClasses on target cluster | P0 |
| VAST VMS API — VIPPools | REST | Retrieve VIPPool configuration for StorageProvider connection details | P1 |
| VAST VMS API — Tenant Credentials | REST | Manage tenant-specific credentials for VAST storage access | P1 |
| VAST VMS API — Views | REST | Manage VAST views for tenant storage isolation | P1 |
| VolumeSnapshotClass Creation | Config | Create VolumeSnapshotClasses associated with storage tiers | P1 |
| CSI Secret Management | Config | Manage CSI driver authentication secrets on target cluster | P1 |
| Teardown — Cluster-side Cleanup | Method | Remove StorageClasses, VolumeSnapshotClasses, and CSI Secret from deleted cluster | P1 |
| Teardown — Backend Preservation | Method | Verify VAST tenant, views, quotas, and per-tenant Secret are not deleted | P1 |
| K8s Secrets — StorageProvider Details | Config | K8s secrets containing VAST connection information used during StorageClass creation | P1 |
| VAST VMS API — QoS Policies | REST | Retrieve/manage QoS policies for tier-based storage performance | P2 |
| VAST VMS API — Realms | REST | Manage VAST Realms for multi-tenant storage organization | P2 |

---

## 5. Test Cases

> **Note**: Test cases have not been generated yet. To be filled later in
> the process.

**Test Cases Directory**: [test_cases/](test_cases/)
**Complete Test Case Index**: [test_cases/INDEX.md](test_cases/INDEX.md)

### 5.1 Test Case Organization

> **Note**: To be filled later in the process.

| Category | Test Cases | Priority Distribution |
|----------|------------|----------------------|
| | | |

### 5.2 Test Case Naming Convention

Test cases follow the naming pattern: `TC-<CATEGORY>-<NUMBER>`

- `TC-CSI` — CSI driver installation and lifecycle
- `TC-TIER` — Tier API integration and tier retrieval
- `TC-SC` — StorageClass creation and management
- `TC-PVC` — PVC provisioning and consumption
- `TC-STATUS` — ClusterOrder CR storage readiness tracking
- `TC-TEARDOWN` — Cluster teardown and resource cleanup
- `TC-RBAC` — RBAC and multi-tenant isolation
- `TC-E2E` — End-to-end scenarios

---

## 6. E2E Test Scenarios

End-to-end scenarios that validate the user journeys defined in the
strategy. Each scenario maps to one or more TC-E2E-*.md test cases
generated by `/test-plan-create-cases`.

> **Requirement**: At least one E2E scenario MUST be generated for each
> P0 endpoint in Section 4.
> E2E scenarios will be filled by `/test-plan-create-cases`.

### 6.1 Scenario Summary

> **Note**: E2E scenarios have not been generated yet. To be filled later
> in the process.

| ID | Scenario | Endpoints Covered | Priority |
|----|----------|-------------------|----------|
| | | | |

### 6.2 E2E Coverage Matrix

> **Note**: To be filled later in the process.

| Endpoint (from Section 4) | E2E Scenarios |
|----------------------------|---------------|
| | |

---

## 7. Non-Functional Requirements

Each category below must be explicitly addressed. If a category
does not apply to this feature, state **Not Applicable** with a
brief justification.

### 7.1 Disconnected/Air-Gapped

The VAST CSI driver must be installed on the CaaS target cluster, which
requires pulling container images. In a disconnected environment, testing
must verify:

- VAST CSI driver images can be installed from a mirrored registry
- Tier API queries function without external network access (if the Tier
  API is internal)
- StorageClass creation does not depend on external network connectivity
- VAST VMS API connectivity works within air-gapped network boundaries

### 7.2 Upgrade/Migration

The feature introduces new CRDs and persistent state that must be tested
during upgrades:

- TenantStorage CR schema backwards compatibility when upgrading the
  storage controller
- ClusterOrder CR storage readiness field additions must not break existing
  ClusterOrder consumers
- VAST CSI driver upgrade paths on existing clusters with active PVCs
- StorageClass definitions must remain valid after operator upgrades
- Backend resources (VAST tenant, views, quotas) must persist across
  upgrades

### 7.3 Performance/Scalability

- Time from ClusterOrderPhaseReady to storage-ready state (CSI driver
  installation + StorageClass creation latency)
- Tier API query response time with large numbers of tiers and tenants
- Concurrent storage setup for multiple clusters reaching ready state
  simultaneously
- PVC provisioning latency across different storage tiers (fast, standard,
  archive)
- VAST VMS API response time under load for credential and connection
  detail retrieval

### 7.4 RBAC/Authorization

- Cloud Provider Admin can view storage readiness status on ClusterOrder
  CR but cannot modify storage configurations directly
- Tenant Users can only create PVCs using StorageClasses assigned to their
  tenant, not other tenants' StorageClasses
- Service accounts managing storage setup have minimal required permissions
  (principle of least privilege)
- VAST credentials in K8s secrets are accessible only to the storage
  controller service account
- Multi-tenant isolation: one tenant's storage operations cannot affect
  another tenant's storage resources

---

## 8. Risks and Mitigation

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| VAST storage not accessible from hub cluster during testing | High | Medium | Verify VAST connectivity as pre-test step; document network requirements for test environment setup |
| Tier API unavailable or returning inconsistent data | High | Medium | Implement health check for Tier API before storage setup; test with mock Tier API responses for functional validation |
| VAST CSI driver installation failure on target cluster | High | Low | Test CSI driver installation independently before full workflow; verify image availability and node compatibility |
| Credential provisioning race condition with concurrent clusters | Medium | Medium | Idempotent credential creation (check-then-create); VAST API rate limiting and retry; per-cluster credential isolation |
| Multi-tenant StorageClass isolation breach | High | Low | Strict RBAC testing; credential scoping validation; StorageClass namespace isolation; penetration testing for cross-tenant access |
| ClusterOrder CR storage readiness tracking conflicts with existing status fields | Medium | Medium | Review ClusterOrder CRD schema changes; test that compute-ready status remains unaffected by storage readiness additions |
| Teardown leaves orphaned cluster-side resources | Medium | Medium | Verify complete cleanup of StorageClasses, VolumeSnapshotClasses, and CSI Secrets; test teardown with active PVCs |
| Backend resources incorrectly deleted during teardown | High | Low | Verify backend resources persist after cluster deletion; test with multiple clusters sharing the same backend tenant |
| v0.1 constraint not clearly enforced | Medium | Low | Validate that only networked storage tiers are exposed through StorageClasses; ensure etcd/control plane local storage is unaffected |

---

## 9. Test Environment Requirements

### 9.1 Infrastructure

- Hub cluster with network access to VAST storage backend
- At least one CaaS target cluster provisionable to ClusterOrderPhaseReady
  state
- VAST storage system accessible from hub cluster with CRUD support for
  VIPPools, tenant credentials, views, QoS policies, and Realms
- VAST VMS API management endpoint for retrieving StorageProvider connection
  details
- Network infrastructure: Ethernet-based with L2 isolation capability,
  DHCP services, floating IP allocation, and routing
- DNS service required for OpenShift cluster provisioning
- Identity Provider (Keycloak) for authentication and authorization of
  different user personas

### 9.2 Configuration

- VAST credentials secret: K8s secret on hub cluster containing VAST
  management credentials
- Tier API configuration: Endpoint and credentials for the Tier API service
- TenantStorage CRD: Custom Resource Definition installed on hub cluster
- ClusterOrder CRD: Custom Resource Definition with storage readiness
  status fields
- CSI driver configuration: VAST CSI driver Helm chart or operator
  subscription details
- StorageClass templates: Parameterized templates for per-tenant, per-tier
  StorageClass generation
- VolumeSnapshotClass configuration: Snapshot class definitions tied to
  VAST CSI driver

### 9.3 Test Tools

- **kubectl / oc** — Managing Kubernetes/OpenShift resources, creating PVCs,
  inspecting StorageClasses, and validating CR status
- **curl / httpie** — Direct Tier API and VAST VMS API endpoint testing
- **Helm** — CSI driver installation validation (if Helm-based)
- **jq / yq** — Parsing JSON/YAML responses from APIs and CRs
- **k9s** — Interactive cluster resource inspection and debugging
- **Prometheus / Grafana** — Monitoring storage-related metrics during testing
- **fio** — Validating PVC performance across different tiers

---

## 10. Appendix

### 10.1 Test Case Summary

> **Note**: To be filled later in the process.

| Category | Total | P0 | P1 | P2 |
|----------|-------|----|----|-----|
| | | | | |

### 10.2 Endpoint/Method Coverage

| Endpoint | Test Cases | Coverage |
|----------|------------|----------|
| Tier API — Get | | |
| Tier API — List | | |
| TenantStorage CR | | |
| ClusterOrder CR — Storage Readiness | | |
| VAST CSI Driver Installation | | |
| StorageClass Creation | | |
| VAST VMS API — VIPPools | | |
| VAST VMS API — Tenant Credentials | | |
| VAST VMS API — Views | | |
| VolumeSnapshotClass Creation | | |
| CSI Secret Management | | |
| Teardown — Cluster-side Cleanup | | |
| Teardown — Backend Preservation | | |
| K8s Secrets — StorageProvider Details | | |
| VAST VMS API — QoS Policies | | |
| VAST VMS API — Realms | | |

### 10.3 Document Change Log

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | 2026-07-20 | Initial test plan |

---

**End of Test Plan**
