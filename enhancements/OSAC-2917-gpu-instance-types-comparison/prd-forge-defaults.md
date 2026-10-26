# Product Requirements Document

**Document Version**: 1.0
**Date**: 2026-07-30
**Status**: Draft
**Ticket**: OSAC-2917

---

## 1. Executive Summary

OSAC tenants currently cannot provision VMs with GPU hardware, blocking AI/ML workloads on the platform. This feature extends InstanceTypes with GPU type and count fields so that Cloud Provider Admins can define GPU configurations and Tenant Users can create GPU-equipped ComputeInstances through the existing self-service workflow.

---

## 2. Problem Statement

### 2.1 Current State

ComputeInstances are defined by CPU cores, memory, and disk. There is no mechanism to request or attach GPU hardware to a VM. Tenants needing GPU resources must provision them outside the platform or through manual operator intervention.

### 2.2 Desired State

InstanceTypes include optional GPU type (free text string) and GPU count fields. Tenants browse available InstanceTypes, identify GPU-enabled options, and create ComputeInstances that are automatically provisioned with GPU hardware attached via KubeVirt passthrough. GPU VMs share the same lifecycle, networking, storage, and tenant isolation model as existing non-GPU VMs.

### 2.3 Business Impact

- Unlocks AI/ML workloads on the platform, expanding the addressable use-case set
- Enables self-service GPU provisioning, eliminating manual operator intervention
- Addresses a specific customer requirement (Jio) for GPU-equipped VMs

---

## 3. Goals & Objectives

### Primary Goals

- [ ] Cloud Provider Admins can define InstanceTypes with GPU type and count
- [ ] Tenant Users can discover and select GPU-enabled InstanceTypes
- [ ] ComputeInstances created from GPU-enabled InstanceTypes are provisioned with GPU hardware attached
- [ ] GPU VMs behave identically to non-GPU VMs for all lifecycle operations

### Success Metrics

| Metric | Current | Target | Measurement Method |
|--------|---------|--------|-------------------|
| GPU InstanceType creation success rate | N/A | 100% of valid definitions succeed | System testing |
| GPU ComputeInstance provisioning success rate | N/A | Same as non-GPU ComputeInstance success rate | System testing |
| GPU VM lifecycle parity | N/A | All lifecycle operations (start, stop, restart, delete) work on GPU VMs | Functional testing |

---

## 4. User Personas

### Persona 1: Cloud Provider Admin

- **Role**: Platform operator responsible for defining available hardware configurations
- **Goals**: Define and manage InstanceTypes that accurately represent available GPU hardware; retire or update GPU configurations when underlying hardware changes
- **Pain Points**: No way to expose GPU hardware options to tenants through the platform; GPU provisioning requires manual intervention
- **Usage Context**: Configures InstanceTypes when new GPU hardware is onboarded or decommissioned

### Persona 2: Tenant User

- **Role**: End user who provisions and manages VMs for their workloads
- **Goals**: Discover GPU-enabled InstanceTypes and create VMs with GPU hardware for AI/ML workloads
- **Pain Points**: Cannot self-service GPU VMs; must go outside the platform or request manual setup
- **Usage Context**: Creates and manages ComputeInstances through the platform's API or UI

---

## 5. Requirements

### 5.1 Functional Requirements

| ID | Requirement | Priority | Acceptance Criteria |
|----|-------------|----------|---------------------|
| FR-01 | InstanceType resource supports a GPU type field (free text string) | MVP | An InstanceType can be created with a GPU type string; the field is persisted and returned on read |
| FR-02 | InstanceType resource supports a GPU count field (integer) | MVP | An InstanceType can be created with a GPU count; the field is persisted and returned on read |
| FR-03 | GPU fields are optional on InstanceTypes | MVP | InstanceTypes without GPU fields continue to work as before; no breaking changes to existing resources |
| FR-04 | Tenant Users can list InstanceTypes and see GPU information | MVP | List and describe responses include GPU type and count when present |
| FR-05 | Tenant Users can create a ComputeInstance from a GPU-enabled InstanceType | MVP | A ComputeInstance created with a GPU-enabled InstanceType is provisioned with GPU hardware attached via passthrough |
| FR-06 | GPU ComputeInstances support all existing lifecycle operations | MVP | Start, stop, restart, and delete work identically to non-GPU ComputeInstances |
| FR-07 | Cloud Provider Admin can create GPU-enabled InstanceTypes | MVP | Admin API accepts GPU type and count fields when creating an InstanceType |
| FR-08 | Cloud Provider Admin can update GPU-enabled InstanceTypes | MVP | Admin API allows modifying GPU fields on existing InstanceTypes |
| FR-09 | Cloud Provider Admin can delete GPU-enabled InstanceTypes | MVP | Admin API allows deleting GPU-enabled InstanceTypes (same as non-GPU) |

### 5.2 Non-Functional Requirements

| ID | Requirement | Category | Target |
|----|-------------|----------|--------|
| NFR-01 | GPU ComputeInstances carry standard tenant isolation metadata | Security | All GPU VMs include tenant isolation annotations identical to non-GPU VMs |
| NFR-02 | GPU field additions are backward-compatible | Compatibility | Existing InstanceTypes and ComputeInstances are unaffected; no migration required for non-GPU resources |
| NFR-03 | GPU type field requires no platform-side validation | Simplicity | The platform stores the string as-is; correctness is the Cloud Admin's responsibility |

---

## 6. User Stories

**US-001**: As a Cloud Provider Admin, I want to define InstanceTypes that include GPU type and count so that tenants can select GPU configurations when creating VMs.
- **Acceptance Criteria**: Given I am a Cloud Provider Admin, when I create an InstanceType with GPU type "NVIDIA A100" and GPU count 2, then the InstanceType is persisted with those GPU fields and visible to tenants.

**US-002**: As a Cloud Provider Admin, I want to retire or update GPU-enabled InstanceTypes when the underlying GPU hardware changes.
- **Acceptance Criteria**: Given I am a Cloud Provider Admin, when I update or delete a GPU-enabled InstanceType, then the change takes effect and tenants see the updated or removed InstanceType.

**US-003**: As a Tenant User, I want to see which InstanceTypes include GPU hardware so I can choose the right configuration for my workload.
- **Acceptance Criteria**: Given I am a Tenant User, when I list InstanceTypes, then GPU-enabled InstanceTypes show the GPU type and count alongside CPU and memory information.

**US-004**: As a Tenant User, I want to create a ComputeInstance using a GPU-enabled InstanceType so my VM is provisioned with GPU hardware attached.
- **Acceptance Criteria**: Given I am a Tenant User, when I create a ComputeInstance referencing a GPU-enabled InstanceType, then the resulting VM has GPU hardware attached via passthrough and is accessible within the VM.

**US-005**: As a Tenant User, I want GPU VMs to behave the same as non-GPU VMs for lifecycle operations (start, stop, restart, delete).
- **Acceptance Criteria**: Given I have a running GPU ComputeInstance, when I stop, restart, or delete it, then the operation completes with the same behavior and status transitions as a non-GPU ComputeInstance.

---

## 7. Scope

### In Scope

- GPU type (string) and GPU count (integer) fields on the InstanceType resource
- Cloud Provider Admin CRUD operations on GPU-enabled InstanceTypes
- Tenant User visibility of GPU fields when listing/describing InstanceTypes
- ComputeInstance creation from GPU-enabled InstanceTypes with GPU passthrough
- Full lifecycle parity between GPU and non-GPU ComputeInstances
- Tenant isolation metadata on GPU ComputeInstances

### Out of Scope

- GPU discovery API
- Per-tenant GPU quotas
- Preemptible VMs
- MIG / vGPU support
- GPU clusters with InfiniBand interconnect
- GPU VM live migration
- GPU-compatible boot image filtering
- Multi-cluster GPU placement
- GPU type validation (platform-side)
- Cost estimation and billing

---

## 8. Assumptions & Constraints

### Assumptions

- GPU passthrough at the infrastructure level (Ansible/KubeVirt) is already functional (delivered in OSAC-42)
- GPU type is a free text string with no platform-side validation — the Cloud Provider Admin is responsible for entering correct GPU identifiers
- A single VMaaS cluster is assumed — no cross-cluster placement decisions
- GPU fields extend the existing InstanceType resource (OSAC-58 / OSAC-1205) rather than introducing a new resource type

### Constraints

- GPU VMs must use the same networking, storage, and lifecycle model as existing ComputeInstances — no special-case handling in the provisioning path beyond GPU attachment
- Backward compatibility: existing InstanceTypes and ComputeInstances must be unaffected

### Dependencies

- OSAC-42: Ansible-level GPU passthrough plumbing (already delivered)
- OSAC-58 / OSAC-1205: GPU fields extend the existing InstanceType resource

---

## 9. Risks & Mitigations

| Risk | Context | Likelihood | Impact | Mitigation |
|------|---------|------------|--------|------------|
| GPU passthrough fails silently during provisioning | KubeVirt passthrough may succeed at the API level but fail to attach hardware inside the VM due to host configuration or driver issues | Medium | High | Validate GPU attachment inside the VM during acceptance testing; ensure provisioning surfaces passthrough errors rather than silently creating a VM without GPU |
| Free-text GPU type leads to user confusion | Without validation, admins may enter inconsistent or incorrect GPU type strings, leading to tenant confusion about what hardware is available | Medium | Medium | Document recommended GPU type naming conventions; consider adding a non-enforced "known types" reference in future iterations |
| Existing InstanceType consumers break on schema change | Adding new fields to InstanceType may affect clients that do not expect GPU fields | Low | High | Ensure GPU fields are optional with zero-value defaults; verify backward compatibility with existing API consumers |
| GPU hardware unavailable at provisioning time | A tenant selects a GPU-enabled InstanceType but the underlying host has no available GPU devices | Medium | High | Rely on KubeVirt scheduling to fail the pod placement; ensure the ComputeInstance status reflects the scheduling failure clearly |

---

## 10. Timeline & Milestones

No specific dates have been provided. This is an MVP feature driven by a customer requirement (Jio). Timeline should be determined during planning based on team capacity and the dependency on OSAC-42 (already delivered) and OSAC-58/OSAC-1205.

| Phase | Milestone | Target Date | Dependencies |
|-------|-----------|-------------|--------------|
| 1 | InstanceType GPU field support (API + persistence) | TBD | OSAC-58, OSAC-1205 |
| 2 | ComputeInstance provisioning with GPU passthrough | TBD | Phase 1, OSAC-42 |
| 3 | End-to-end testing and validation | TBD | Phase 2 |
