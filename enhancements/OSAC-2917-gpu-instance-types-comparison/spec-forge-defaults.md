# Technical Specification

**Document Version**: 1.0
**Date**: 2026-07-30
**Status**: Draft
**Parent PRD**: OSAC-2917

---

## 1. Overview

This spec defines the behavior for extending InstanceTypes with GPU type and count fields, enabling tenants to create ComputeInstances with GPU hardware attached via KubeVirt passthrough.

---

## 2. User Scenarios

### Priority Legend
- P1: Critical path — must work for MVP
- P2: Important — required for full release
- P3: Enhancement — can be deferred

### 2.1 P1 Scenarios (Critical)

#### SC-001: Cloud Provider Admin creates a GPU-enabled InstanceType
**Preconditions**: Authenticated as Cloud Provider Admin
**Trigger**: Admin creates an InstanceType with GPU type and GPU count fields populated

**Acceptance Criteria**:
```gherkin
Given I am authenticated as a Cloud Provider Admin
When I create an InstanceType with GPU type "NVIDIA A100" and GPU count 2
Then the InstanceType is created successfully
And the InstanceType record includes GPU type "NVIDIA A100" and GPU count 2
```

**Edge Cases**:
- GPU count of 0 with a non-empty GPU type is accepted (treated as no GPU)
- GPU type as empty string with GPU count 0 represents a non-GPU InstanceType
- GPU type is free text — no validation is performed on the string value

---

#### SC-002: Tenant User lists InstanceTypes and identifies GPU-enabled ones
**Preconditions**: Authenticated as Tenant User; at least one GPU-enabled and one non-GPU InstanceType exist
**Trigger**: Tenant User lists available InstanceTypes

**Acceptance Criteria**:
```gherkin
Given I am authenticated as a Tenant User
And InstanceType "gpu-large" exists with GPU type "NVIDIA A100" and GPU count 4
And InstanceType "cpu-medium" exists with no GPU fields
When I list InstanceTypes
Then I see both "gpu-large" and "cpu-medium" in the results
And "gpu-large" displays GPU type "NVIDIA A100" and GPU count 4
And "cpu-medium" displays no GPU information
```

**Edge Cases**:
- InstanceTypes with GPU count 0 appear as non-GPU instances in listings

---

#### SC-003: Tenant User creates a ComputeInstance with a GPU-enabled InstanceType
**Preconditions**: Authenticated as Tenant User; a GPU-enabled InstanceType exists
**Trigger**: Tenant User creates a ComputeInstance referencing a GPU-enabled InstanceType

**Acceptance Criteria**:
```gherkin
Given I am authenticated as a Tenant User
And InstanceType "gpu-large" exists with GPU type "NVIDIA A100" and GPU count 2
When I create a ComputeInstance with InstanceType "gpu-large"
Then the ComputeInstance is created successfully
And the provisioned VM has 2 GPU devices attached via KubeVirt passthrough
And the ComputeInstance carries standard tenant isolation metadata
```

**Edge Cases**:
- If the referenced InstanceType does not exist, creation fails with a not-found error

---

#### SC-004: GPU ComputeInstance supports standard lifecycle operations
**Preconditions**: A running GPU-equipped ComputeInstance exists
**Trigger**: Tenant User performs lifecycle operations (stop, start, restart, delete)

**Acceptance Criteria**:
```gherkin
Given I have a running ComputeInstance provisioned with a GPU-enabled InstanceType
When I stop the ComputeInstance
Then the ComputeInstance stops successfully

Given I have a stopped GPU ComputeInstance
When I start the ComputeInstance
Then the ComputeInstance starts successfully
And the GPU devices are reattached

Given I have a running GPU ComputeInstance
When I restart the ComputeInstance
Then the ComputeInstance restarts successfully
And the GPU devices are reattached

Given I have a GPU ComputeInstance
When I delete the ComputeInstance
Then the ComputeInstance is deleted successfully
And GPU resources are released
```

**Edge Cases**:
- Lifecycle behavior is identical to non-GPU ComputeInstances — no GPU-specific failure modes are introduced

---

### 2.2 P2 Scenarios (Important)

#### SC-005: Cloud Provider Admin updates a GPU-enabled InstanceType
**Preconditions**: Authenticated as Cloud Provider Admin; a GPU-enabled InstanceType exists
**Trigger**: Admin updates the GPU type or GPU count on an existing InstanceType

**Acceptance Criteria**:
```gherkin
Given I am authenticated as a Cloud Provider Admin
And InstanceType "gpu-large" exists with GPU type "NVIDIA A100" and GPU count 2
When I update the InstanceType GPU type to "NVIDIA H100" and GPU count to 4
Then the InstanceType is updated successfully
And the InstanceType now reflects GPU type "NVIDIA H100" and GPU count 4
```

**Edge Cases**:
- Updating GPU fields does not affect already-provisioned ComputeInstances using this InstanceType
- Removing GPU fields (setting GPU type to empty, GPU count to 0) converts a GPU InstanceType to a non-GPU InstanceType

---

#### SC-006: Cloud Provider Admin deletes a GPU-enabled InstanceType
**Preconditions**: Authenticated as Cloud Provider Admin; a GPU-enabled InstanceType exists
**Trigger**: Admin deletes the InstanceType

**Acceptance Criteria**:
```gherkin
Given I am authenticated as a Cloud Provider Admin
And InstanceType "gpu-large" exists
When I delete the InstanceType "gpu-large"
Then the InstanceType is deleted successfully
```

**Edge Cases**:
- Deletion behavior for GPU-enabled InstanceTypes is identical to non-GPU InstanceTypes
- Existing ComputeInstances referencing a deleted InstanceType continue running

---

## 3. Functional Requirements

### 3.1 Core Functions
| ID | Function | Description | Inputs | Outputs |
|----|----------|-------------|--------|---------|
| FR-001 | Create GPU InstanceType | Cloud Provider Admin creates an InstanceType with GPU type and count | InstanceType name, CPU, memory, disk, GPU type (string), GPU count (integer) | Created InstanceType |
| FR-002 | List InstanceTypes with GPU info | Tenant User lists InstanceTypes; GPU fields are visible | List request | List of InstanceTypes including GPU type and GPU count |
| FR-003 | Create GPU ComputeInstance | Tenant User creates a ComputeInstance referencing a GPU-enabled InstanceType | ComputeInstance spec with InstanceType reference | ComputeInstance with GPU hardware attached via KubeVirt passthrough |
| FR-004 | Update GPU InstanceType | Cloud Provider Admin updates GPU type and/or GPU count | InstanceType ID, updated GPU fields | Updated InstanceType |
| FR-005 | Delete GPU InstanceType | Cloud Provider Admin deletes a GPU-enabled InstanceType | InstanceType ID | Deletion confirmation |
| FR-006 | GPU ComputeInstance lifecycle | Stop, start, restart, delete operations on GPU ComputeInstances | ComputeInstance ID, lifecycle action | Lifecycle operation result |

### 3.2 Business Rules
| ID | Rule | Condition | Action |
|----|------|-----------|--------|
| BR-001 | GPU type is free text | Always | No validation is performed on GPU type string; correctness is the Cloud Admin's responsibility |
| BR-002 | GPU fields are optional | InstanceType creation/update | GPU type and GPU count default to empty/zero if not provided |
| BR-003 | Tenant isolation applies to GPU VMs | ComputeInstance creation | GPU ComputeInstances carry the same tenant isolation metadata as non-GPU instances |
| BR-004 | Single cluster assumption | ComputeInstance placement | No cross-cluster placement logic; GPU VMs are provisioned on the same VMaaS cluster |

---

## 4. Interface Changes

### InstanceType Resource
Two new fields added to the InstanceType resource:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `gpu_type` | string | No | Free-text GPU hardware identifier (e.g., "NVIDIA A100"). Empty string means no GPU. |
| `gpu_count` | int32 | No | Number of GPU devices. Defaults to 0. |

These fields appear in:
- Create InstanceType request/response
- Update InstanceType request/response
- Get InstanceType response
- List InstanceTypes response

### ComputeInstance Resource
No new fields on ComputeInstance. GPU configuration is derived from the referenced InstanceType at provisioning time.

---

## 6. Error Handling
| Scenario | Error | Resolution |
|----------|-------|------------|
| Create ComputeInstance with non-existent InstanceType | Not found error | User corrects the InstanceType reference |
| Negative GPU count | Validation error | User provides a non-negative integer |

---

## 8. Testing Requirements
| ID | Scenario | Type | Priority | Automated |
|----|----------|------|----------|-----------|
| T-001 | Create InstanceType with GPU fields | Unit / Integration | P1 | Yes |
| T-002 | List InstanceTypes shows GPU info | Unit / Integration | P1 | Yes |
| T-003 | Create ComputeInstance with GPU InstanceType provisions GPU hardware | Integration / E2E | P1 | Yes |
| T-004 | GPU ComputeInstance lifecycle (stop, start, restart, delete) | Integration / E2E | P1 | Yes |
| T-005 | Update GPU InstanceType fields | Unit / Integration | P2 | Yes |
| T-006 | Delete GPU InstanceType | Unit / Integration | P2 | Yes |
| T-007 | GPU ComputeInstance carries tenant isolation metadata | Integration | P1 | Yes |
| T-008 | Non-GPU InstanceType creation unaffected by new fields | Unit | P1 | Yes |

---

## 9. Open Questions

1. **GPU count validation bounds**: Is there an upper limit on GPU count per InstanceType, or is any positive integer accepted?
2. **InstanceType immutability for running VMs**: When an InstanceType's GPU fields are updated, should existing ComputeInstances reflect the change on next restart, or are they permanently bound to the values at creation time?
3. **GPU type empty string vs. null**: Should the API distinguish between "no GPU type provided" (null/absent) and "explicitly empty GPU type" (empty string), or treat both as no GPU?
