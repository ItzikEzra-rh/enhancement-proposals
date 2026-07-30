# PRD: GPU-Enabled InstanceTypes for ComputeInstances (MVP)

| Field   | Value |
|---------|-------|
| Author  | Itzik Ezra |
| Jira    | OSAC-2917 |
| Service | VMaaS |
| Date    | 2026-07-30 |

## Problem Statement

OSAC tenants running AI/ML workloads have no way to request GPU hardware when creating ComputeInstances. The current InstanceType model only describes CPU cores, memory, and disk -- tenants who need GPU-equipped VMs must fall back to manual provisioning outside OSAC, bypassing tenant isolation, lifecycle management, and self-service workflows. This blocks adoption by GPU-dependent customers (Jio) and leaves GPU capacity unmanageable through the standard OSAC control plane. [Jira: OSAC-2917]

## In Scope

- Cloud Provider Admin can define InstanceTypes that include a GPU type (free-text string) and GPU count
- Cloud Provider Admin can update or retire GPU-enabled InstanceTypes when underlying hardware changes
- Tenant User can list InstanceTypes and distinguish GPU-enabled from non-GPU InstanceTypes
- Tenant User can create a ComputeInstance using a GPU-enabled InstanceType; the resulting VM has GPU hardware attached via KubeVirt device passthrough
- GPU ComputeInstances follow the same lifecycle operations as non-GPU ComputeInstances (start, stop, restart, delete)
- GPU ComputeInstances carry standard OSAC tenant isolation metadata
- GPU type field is free text with no OSAC-side validation (Cloud Provider Admin responsibility, consistent with CPU/RAM handling)

## Out of Scope

- **GPU discovery API** -- separate feature; MVP relies on admin knowledge of available hardware [Jira: OSAC-1839]
- **Per-tenant GPU quotas** -- quota enforcement is a platform-wide concern tracked independently [Jira: OSAC-1839]
- **MIG / vGPU partitioning** -- requires GPU-specific device plugin configuration beyond MVP passthrough [Jira: OSAC-1839]
- **Preemptible GPU VMs** -- scheduling policy not yet defined at platform level
- **GPU clusters with InfiniBand interconnect** -- networking topology work deferred to future scope [Jira: OSAC-1839]
- **GPU VM live migration** -- passthrough GPUs cannot live-migrate under current KubeVirt constraints
- **GPU-compatible boot image filtering** -- image catalog filtering is a separate capability
- **Multi-cluster GPU placement** -- MVP assumes a single VMaaS cluster; cross-cluster scheduling deferred [Jira: OSAC-1839]
- **GPU type validation** -- admin-managed; OSAC does not validate GPU type strings against hardware inventory
- **Cost estimation and billing** -- billing integration is out of scope for all current VMaaS features

### Cross-Cutting Dimensions

- **Tenant Onboarding** -- no changes; GPU access is governed by InstanceType availability, not tenant config
- **Inventory** -- out of scope; no GPU discovery or inventory tracking in MVP
- **Provisioning** -- in scope; GPU passthrough plumbing already delivered in osac-aap (OSAC-42)
- **Networking** -- no changes; GPU VMs use the same VirtualNetwork/Subnet/SecurityGroup model
- **Storage** -- no changes; GPU VMs use existing storage model
- **Installation** -- no new installation prerequisites for MVP
- **E2E Testing** -- in scope; GPU provisioning flow must be covered by E2E tests
- **Documentation** -- in scope; InstanceType GPU fields and GPU VM creation must be documented
- **UI** -- in scope; InstanceType list and ComputeInstance creation flow must surface GPU information

## User Stories

### Cloud Provider Admin

- As a Cloud Provider Admin, I want to create an InstanceType that specifies a GPU type (e.g., "NVIDIA A100") and GPU count (e.g., 4) so that tenants can select GPU configurations when provisioning VMs.
- As a Cloud Provider Admin, I want to update a GPU-enabled InstanceType's GPU type or count when the underlying hardware changes, so the catalog reflects current capacity.
- As a Cloud Provider Admin, I want to delete or retire a GPU-enabled InstanceType so that tenants can no longer provision VMs with decommissioned GPU hardware.

### Cloud Infrastructure Admin

Not directly affected. GPU passthrough plumbing in the infrastructure layer (osac-aap) is already delivered under OSAC-42.

### Tenant Admin

Not directly affected. GPU access is determined by InstanceType availability; no org-level GPU configuration is required in MVP.

### Tenant User

- As a Tenant User, I want to list available InstanceTypes and see which ones include GPU hardware (type and count) so I can choose the right configuration for my AI/ML workload.
- As a Tenant User, I want to create a ComputeInstance using a GPU-enabled InstanceType so my VM is provisioned with the specified GPU hardware attached.
- As a Tenant User, I want to start, stop, restart, and delete a GPU-equipped ComputeInstance the same way I manage non-GPU VMs, so GPU does not change my operational workflow.
- As a Tenant User, I want to inspect a running GPU ComputeInstance and confirm it has the expected GPU type and count, so I can verify the VM matches my workload requirements.

## Assumptions

- Single VMaaS cluster -- MVP does not require cross-cluster GPU placement. [Assumption]
- GPU passthrough plumbing in osac-aap is functional and tested (delivered under OSAC-42). [Jira: OSAC-42]
- GPU type is an opaque string managed by the Cloud Provider Admin; OSAC does not validate it against any hardware inventory. [Jira: OSAC-2917]
- KubeVirt device passthrough supports the GPU types the Cloud Provider Admin configures. [Assumption]
- GPU count of zero or omission of GPU fields in an InstanceType means non-GPU. [Assumption]

## Dependencies

- **OSAC-42** -- Ansible-level GPU passthrough plumbing (delivered)
- **OSAC-58 / OSAC-1205** -- GPU fields extend the existing InstanceType resource definition

## Acceptance Criteria

- [ ] InstanceType supports GPU type (string) and GPU count (integer) fields
- [ ] Cloud Provider Admin can create an InstanceType with GPU type and count via API and CLI
- [ ] Cloud Provider Admin can update and delete GPU-enabled InstanceTypes
- [ ] Tenant User can list InstanceTypes and identify which ones include GPU hardware (type and count are visible)
- [ ] Tenant User can create a ComputeInstance using a GPU-enabled InstanceType
- [ ] The provisioned VM has GPU hardware attached via KubeVirt passthrough matching the InstanceType specification
- [ ] GPU ComputeInstances support start, stop, restart, and delete operations identically to non-GPU instances
- [ ] GPU ComputeInstances carry standard OSAC tenant isolation metadata
- [ ] GPU information is surfaced in the UI for InstanceType listing and ComputeInstance creation
- [ ] E2E test covers creating a ComputeInstance with a GPU-enabled InstanceType
