# Product Requirements Document: VM Worker Node Support for CaaS Clusters

**Feature:** OSAC-1589 — Add VM worker node support for CaaS clusters
**Status:** Draft
**Author:** AI-Generated (Forge Default Template)
**Date:** 2026-07-30

---

## Executive Summary

This feature enables CaaS (Cluster as a Service) clusters to use virtual machine (VM) worker nodes in addition to bare-metal servers. By removing the bare-metal-only constraint, the platform can support faster provisioning for development, testing, and small workloads without requiring dedicated hardware, while also enabling end-to-end flow validation in virtualized environments.

## Problem Statement

### Current State

CaaS clusters currently require bare-metal servers for all worker nodes. This creates a hard dependency on physical hardware availability, which slows provisioning and limits adoption in environments where dedicated bare-metal resources are scarce or unnecessary.

### Desired State

CaaS clusters support VM-based worker nodes as a first-class option. Users can create clusters with VM workers for use cases that do not require bare-metal performance, enabling faster spin-up times and broader environment compatibility.

### Impact

- **Dev/test velocity**: Teams waiting on bare-metal hardware allocation experience provisioning delays ranging from minutes to hours; VM workers can provision significantly faster.
- **Hardware cost reduction**: Dev/test and small workloads no longer consume dedicated bare-metal servers.
- **Validation coverage**: The full CaaS provisioning flow can be validated without requiring physical hardware, unblocking CI/CD and demo environments.

## Goals & Objectives

| # | Goal | Success Metric | Target |
|---|------|---------------|--------|
| G1 | Enable VM-based worker nodes for CaaS clusters | Users can successfully create a CaaS cluster with VM worker nodes | 100% of cluster creation requests with VM workers succeed |
| G2 | Reduce provisioning time for non-bare-metal workloads | Time from cluster creation request to ready state with VM workers | < 50% of bare-metal provisioning time |
| G3 | Allow mixed or VM-only worker node configurations | Users can specify worker node type (VM, bare-metal, or mixed) at cluster creation | Configuration option available and functional |
| G4 | Maintain parity with bare-metal clusters for supported workloads | VM-based clusters pass the same functional test suite as bare-metal clusters (excluding hardware-specific tests) | 100% pass rate on applicable tests |

## User Personas

### Platform Operator

A platform administrator who provisions and manages CaaS clusters for tenants. They need to offer VM-based clusters to reduce hardware costs and speed up delivery for tenants who don't require bare-metal performance. They want straightforward configuration to specify worker node types without complex setup.

### Developer / QE Engineer

A developer or quality engineer who needs a CaaS cluster for development, testing, or CI pipelines. They don't have access to dedicated bare-metal hardware and need a cluster quickly. They care about provisioning speed and don't require bare-metal-specific features (GPU passthrough, SR-IOV).

### Platform Validator

An engineer responsible for validating the entire CaaS provisioning flow. They need to test the end-to-end cluster creation workflow without requiring physical bare-metal hardware, enabling validation in virtualized environments.

## Requirements

### Functional Requirements

| ID | Requirement | Priority | Acceptance Criteria |
|----|------------|----------|-------------------|
| FR-1 | The system shall allow users to create a CaaS cluster with VM-based worker nodes | MVP | Given a cluster creation request specifying VM worker type, when the request is submitted, then a cluster with VM worker nodes is provisioned successfully |
| FR-2 | The system shall support specifying worker node type (VM or bare-metal) at cluster creation time | MVP | Given the cluster creation interface, when a user selects worker node type, then the system provisions workers matching the selected type |
| FR-3 | The system shall validate that the requested VM worker configuration is compatible with the target environment | MVP | Given a cluster creation request with VM workers, when the environment does not support virtualization, then the system returns a clear error message |
| FR-4 | The system shall report worker node type in cluster status and details | MVP | Given a cluster with VM workers, when a user queries cluster details, then the worker node type is clearly indicated |
| FR-5 | The system shall support scaling VM worker nodes (add/remove) after initial cluster creation | Non-MVP | Given an existing cluster with VM workers, when a user requests a scale operation, then VM workers are added or removed accordingly |
| FR-6 | The system shall support mixed clusters with both VM and bare-metal worker nodes | Non-MVP | Given a cluster creation request specifying both VM and bare-metal workers, when the request is submitted, then both worker types are provisioned and functional |

### Non-Functional Requirements

| ID | Requirement | Priority | Acceptance Criteria |
|----|------------|----------|-------------------|
| NFR-1 | VM worker provisioning shall complete faster than bare-metal provisioning | MVP | VM worker provisioning time is at least 50% faster than equivalent bare-metal provisioning |
| NFR-2 | VM-based clusters shall support the same workload APIs as bare-metal clusters | MVP | All non-hardware-specific cluster operations succeed identically on VM and bare-metal clusters |
| NFR-3 | The feature shall not degrade provisioning performance for existing bare-metal clusters | MVP | Bare-metal provisioning latency remains within 5% of pre-feature baseline |

## User Stories

### US-1: Create a CaaS cluster with VM workers

**Given** a platform operator with access to the cluster creation interface
**When** they create a new CaaS cluster and select VM as the worker node type
**Then** the system provisions a fully functional cluster with VM-based worker nodes

### US-2: Validate CaaS flow without bare-metal hardware

**Given** a QE engineer with access to a virtualized environment
**When** they create a CaaS cluster with VM workers for testing purposes
**Then** the cluster provisions successfully and passes the standard functional test suite

### US-3: View worker node type in cluster details

**Given** a platform operator managing multiple clusters
**When** they view the details of a cluster
**Then** they can see whether each worker node is a VM or bare-metal server

### US-4: Fast provisioning for development

**Given** a developer who needs a cluster for a feature branch
**When** they request a CaaS cluster with VM workers
**Then** the cluster is ready significantly faster than a bare-metal cluster would be

## Scope

### In Scope

- Creating CaaS clusters with VM-based worker nodes
- Specifying worker node type at cluster creation time
- Reporting worker node type in cluster status
- Validating environment compatibility for VM workers
- Documentation for the new capability

### Out of Scope

- GPU passthrough or SR-IOV support on VM workers
- Live migration of workloads between VM and bare-metal workers
- Automatic selection of worker type based on workload characteristics
- Performance optimization of VM workers beyond standard virtualization
- Bare-metal to VM worker node conversion for existing clusters

## Assumptions, Constraints & Dependencies

### Assumptions

- The target environment has a virtualization layer capable of running VM-based worker nodes
- VM workers will run the same Kubernetes components as bare-metal workers
- Users understand the performance trade-offs between VM and bare-metal workers

### Constraints

- VM workers cannot provide bare-metal-specific capabilities (direct hardware access, SR-IOV, GPU passthrough)
- VM worker performance is bounded by the underlying hypervisor and host resources
- Customer label: `customer:moc` — initial deployment targets the MOC (Massachusetts Open Cloud) environment

### Dependencies

- Virtualization infrastructure must be available in the target deployment environment
- Existing CaaS provisioning flow must be extensible to support a new worker node type
- Cluster lifecycle management (scaling, deletion) must handle VM workers alongside bare-metal

## Risks & Mitigations

| # | Risk | Probability | Impact | Mitigation |
|---|------|------------|--------|-----------|
| R1 | VM worker performance insufficient for some workloads users expect to run | Medium | Medium | Clearly document supported vs. unsupported workload types; provide guidance on when to use bare-metal instead |
| R2 | Provisioning flow diverges significantly between VM and bare-metal paths, increasing maintenance burden | Medium | High | Design a unified provisioning abstraction that handles both worker types through a common interface |
| R3 | Environment compatibility issues in target deployments | Low | High | Add pre-flight validation checks that verify virtualization support before attempting VM worker provisioning |
| R4 | Users accidentally choose VM workers for workloads requiring bare-metal | Low | Medium | Provide clear documentation and warnings in the UI when selecting VM workers for workload types known to need bare-metal |

## Timeline

| Phase | Description | Duration |
|-------|------------|----------|
| Phase 1 | Design and architecture review | 1-2 sprints |
| Phase 2 | Core implementation — VM worker provisioning flow | 2-3 sprints |
| Phase 3 | Integration testing and validation | 1-2 sprints |
| Phase 4 | Documentation and release | 1 sprint |
