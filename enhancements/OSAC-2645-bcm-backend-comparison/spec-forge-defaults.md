# Technical Specification: BCM Backend Integration for BMaaS

**Jira Feature:** OSAC-1339
**Spec ID:** OSAC-2645
**Status:** Draft

## Overview

This specification defines the behavioral contracts for integrating BCM (Bare Metal Cloud) as a bare metal provisioning backend within the system. BCM will serve as an additional production backend that fulfills BaremetalInstance provisioning and deprovisioning requests through a pluggable backend interface. The integration must be transparent to tenants and configurable by infrastructure administrators.

## User Scenarios

### P1 - Critical Path

#### Scenario: Configure BCM backend for provisioning

```gherkin
Given a Cloud Infrastructure Admin has access to backend configuration
When they register BCM as a provisioning backend via the pluggable backend interface
Then the BCM backend is available for the lifecycle controller to route requests
And the backend configuration is persisted
```

#### Scenario: Provision a BaremetalInstance via BCM

```gherkin
Given the BCM backend is configured and registered
And a tenant has submitted a BaremetalInstance provisioning request
When the lifecycle controller routes the request to the BCM backend
Then BCM provisions the bare metal host
And the BaremetalInstance state transitions from "provisioning" to "ready"
And the lifecycle state is reflected accurately in the system
```

#### Scenario: Deprovision a BaremetalInstance via BCM

```gherkin
Given a BaremetalInstance is in "ready" state and was provisioned via BCM
When a deprovisioning request is submitted
Then the lifecycle controller routes the deprovisioning to BCM
And the BaremetalInstance state transitions from "deprovisioning" to "deleted"
And the BCM host resources are released
```

### P2 - Important

#### Scenario: Lifecycle state feedback reflects BCM status accurately

```gherkin
Given a BaremetalInstance provisioning request has been routed to BCM
When BCM reports an intermediate or terminal state change
Then the system updates the BaremetalInstance lifecycle state to match
And the state transition follows the expected sequence: provisioning -> ready -> deprovisioning -> deleted
```

#### Scenario: BCM backend operates transparently to tenants

```gherkin
Given a Cloud Provider Admin has configured BCM as the provisioning backend
When a tenant submits a BaremetalInstance request
Then the tenant sees standard lifecycle states without BCM-specific details
And no BCM internal identifiers or configuration are exposed to the tenant
```

#### Scenario: Validate BCM backend configuration

```gherkin
Given a Cloud Infrastructure Admin is configuring the BCM backend
When they provide the BCM connection and authentication parameters
Then the system validates the configuration is correct and BCM is reachable
And reports an error if the configuration is invalid or BCM is unreachable
```

### P3 - Nice to Have

#### Scenario: Reconfigure BCM backend without downtime

```gherkin
Given the BCM backend is actively handling provisioning requests
When an admin updates the BCM backend configuration
Then in-flight requests complete against the previous configuration
And new requests use the updated configuration
```

## Functional Requirements

### Core Functions

| ID | Function | Input | Output | Rules |
|----|----------|-------|--------|-------|
| CF-1 | Register BCM backend | BCM connection config, authentication credentials | Registered backend available for lifecycle controller | Must conform to pluggable backend interface (OSAC-1032) |
| CF-2 | Route provisioning to BCM | BaremetalInstance provisioning request | Provisioned bare metal host | Lifecycle controller routes without controller code changes |
| CF-3 | Route deprovisioning to BCM | BaremetalInstance deprovisioning request | Released bare metal host | Lifecycle controller routes without controller code changes |
| CF-4 | Sync lifecycle state from BCM | BCM state feedback | Updated BaremetalInstance lifecycle state | States: provisioning, ready, deprovisioning, deleted |
| CF-5 | Configure BCM backend via operator | Operator configuration parameters | Configured and validated BCM backend | Must be operator-configurable |

### Business Rules

| ID | Rule | Condition | Action |
|----|------|-----------|--------|
| BR-1 | Backend interface conformance | BCM backend is registered | Must implement the pluggable backend interface defined in OSAC-1032 |
| BR-2 | No controller modifications | Provisioning/deprovisioning requests are received | Lifecycle controller routes to BCM via the interface without changes to controller logic |
| BR-3 | Tenant isolation | Tenant submits BaremetalInstance request | No BCM-specific details (endpoints, credentials, internal IDs) are exposed to the tenant |
| BR-4 | State sequence enforcement | BCM reports a state change | State transitions must follow: provisioning -> ready -> deprovisioning -> deleted |
| BR-5 | Operator configurability | Admin configures the BCM backend | Configuration must be manageable through operator-level configuration mechanisms |

## Interface Changes

- **Pluggable Backend Interface:** BCM backend must implement the existing pluggable backend interface (OSAC-1032). No changes to the interface definition itself are expected; BCM is a new implementation of the existing contract.
- **Operator Configuration:** New configuration fields for BCM connection parameters (endpoint, authentication) must be added to the operator configuration surface.
- **Lifecycle Controller:** No interface changes. The controller routes to BCM via the pluggable backend interface without modification.

## Error Handling

| Error Condition | Detection | Response | User Impact |
|----------------|-----------|----------|-------------|
| BCM unreachable during provisioning | Connection timeout or failure when calling BCM API | Retry with backoff; set BaremetalInstance to error state if retries exhausted | Provisioning fails; admin notified |
| BCM returns unexpected state | State value not in recognized set | Log warning; do not transition BaremetalInstance state | No state change; requires admin investigation |
| Invalid BCM configuration | Validation at registration time | Reject configuration; report validation errors | Backend not registered until configuration is corrected |
| BCM provisioning failure | BCM reports provisioning error | Set BaremetalInstance to error state with reason | Tenant sees failed provisioning with generic error |
| BCM authentication failure | Authentication rejected by BCM | Log error; set backend status to degraded | New provisioning requests fail until credentials are fixed |
| Deprovisioning failure | BCM reports deprovisioning error | Retry deprovisioning; escalate to admin after retries | Resource may remain allocated; admin intervention required |

## Testing Requirements

| Test Type | Scope | Criteria |
|-----------|-------|----------|
| Unit tests | BCM backend plugin implementation | All pluggable backend interface methods covered; state mapping logic verified |
| Unit tests | BCM configuration validation | Valid and invalid configurations tested; edge cases for connection parameters |
| Integration tests | BCM backend registration and routing | Lifecycle controller correctly routes to BCM via interface; no controller changes required |
| Integration tests | State synchronization | BCM state feedback correctly maps to BaremetalInstance lifecycle states |
| E2E tests | Full BaremetalInstance lifecycle via BCM | Provisioning -> ready -> deprovisioning -> deleted runs successfully in CI |
| E2E tests | Tenant isolation verification | Tenant-facing APIs expose no BCM-specific details |
| Negative tests | Error handling paths | BCM unreachable, auth failure, invalid state feedback all handled correctly |

## Open Questions

1. What authentication mechanism does BCM use (API keys, OAuth, certificates), and does the pluggable backend interface already support it?
2. What is the expected latency for BCM provisioning operations, and should timeout thresholds be configurable?
3. Does BCM support webhook-style state callbacks, or must the system poll for state changes?
4. Are there BCM-specific resource constraints (quotas, regions, host types) that need to be surfaced through the backend interface?
5. How should the system handle partial failures (e.g., BCM provisions the host but the state callback never arrives)?
6. Is there a BCM staging or sandbox environment available for integration testing in CI?
