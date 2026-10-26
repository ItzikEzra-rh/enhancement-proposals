# Technical Specification

**Document Version**: 1.0
**Date**: 2026-07-30
**Status**: Draft
**Parent PRD**: OSAC-1567

---

## 1. Overview

This specification defines the behavioral contracts for a secret management subsystem that provides encrypted storage with pluggable backends and a uniform interface for accessing secrets across all services.

---

## 2. User Scenarios

### Priority Legend
- P1: Critical path — must work for MVP
- P2: Important — required for full release
- P3: Enhancement — can be deferred

### 2.1 P1 Scenarios (Critical)

#### SC-001: Create and retrieve an encrypted secret

**Preconditions**: A tenant exists. An encryption key is configured.

**Trigger**: A user creates a secret via the Secret CRUD service and then retrieves it.

**Acceptance Criteria**:
```gherkin
Given a configured encryption key and an authenticated tenant user
When the user creates a Secret with name "db-password" and payload "s3cret!"
Then the system stores the secret with envelope encryption (RSA wrapping an AES data key)
And the plaintext payload is never written to the database
When the user calls Get on the secret "db-password"
Then the response contains the decrypted plaintext payload "s3cret!"
```

**Edge Cases**:
- Creating a secret with an empty payload returns a validation error
- Creating a secret with a duplicate name within the same tenant returns a conflict error

---

#### SC-002: List secrets strips payload data

**Preconditions**: A tenant exists with at least one secret.

**Trigger**: A user lists secrets.

**Acceptance Criteria**:
```gherkin
Given a tenant with secrets "db-password" and "api-key"
When the user calls List on secrets
Then the response contains metadata for both secrets (name, type, timestamps)
And no secret payload data is included in the response
When the user calls Get on "db-password"
Then the response includes the decrypted payload
```

**Edge Cases**:
- Listing secrets for a tenant with zero secrets returns an empty list, not an error

---

#### SC-003: Tenant isolation prevents cross-tenant secret access

**Preconditions**: Two tenants exist, each with secrets.

**Trigger**: A user in Tenant A attempts to access a secret belonging to Tenant B.

**Acceptance Criteria**:
```gherkin
Given Tenant A owns secret "db-password"
And Tenant B owns secret "api-key"
When a user authenticated as Tenant B calls Get on Tenant A's secret "db-password"
Then the request is denied by OPA policy
And the user receives a permission denied error
```

**Edge Cases**:
- A Cloud Provider Admin with cross-tenant privileges can access secrets across tenants if OPA policy allows

---

#### SC-004: SecretClass selects the backend for secret storage

**Preconditions**: Two SecretClass resources exist: one for database storage and one for hub/Kubernetes storage.

**Trigger**: A user creates a secret referencing a specific SecretClass.

**Acceptance Criteria**:
```gherkin
Given a SecretClass "database" configured for encrypted database storage
And a SecretClass "hub-kubernetes" configured for on-demand Kubernetes cluster fetch
When the user creates a Secret with secretClass "database"
Then the secret payload is envelope-encrypted and stored in the database
When the user creates a Secret with secretClass "hub-kubernetes"
Then the system stores a reference and fetches the payload on-demand from the Kubernetes cluster
```

**Edge Cases**:
- Creating a secret with a non-existent SecretClass returns a not-found error
- If the referenced Kubernetes cluster is unreachable during a Get on a hub-backend secret, the system returns an error indicating the backend is unavailable

---

### 2.2 P2 Scenarios (Important)

#### SC-005: SecretReference replaces ad-hoc secret retrieval RPCs

**Preconditions**: A resource (e.g., a cluster order) has an associated kubeconfig stored as a secret.

**Trigger**: A user retrieves the secret using a SecretReference instead of a resource-specific RPC.

**Acceptance Criteria**:
```gherkin
Given a cluster order "my-cluster" with an associated kubeconfig stored as a Secret
And the cluster order contains a SecretReference pointing to that Secret
When the user resolves the SecretReference
Then the user receives the decrypted kubeconfig payload
And the user does not need to call a resource-specific RPC like GetKubeconfig
```

**Edge Cases**:
- A SecretReference pointing to a deleted secret returns a not-found error

---

#### SC-006: Hub secret backend fetches data on demand from Kubernetes

**Preconditions**: A SecretClass "hub-kubernetes" is configured. A target Kubernetes cluster is reachable.

**Trigger**: A user retrieves a secret backed by the hub backend.

**Acceptance Criteria**:
```gherkin
Given a Secret "cluster-kubeconfig" with SecretClass "hub-kubernetes"
And the backing Kubernetes cluster is reachable
When the user calls Get on "cluster-kubeconfig"
Then the system fetches the secret data from the Kubernetes cluster at request time
And returns the payload to the user
```

**Edge Cases**:
- If the backing cluster becomes unreachable after secret creation, Get returns an error with the backend status

---

#### SC-007: Encryption key rotation without bulk re-encryption

**Preconditions**: Secrets exist encrypted under key version 1. A new key version 2 is configured.

**Trigger**: The admin rotates the encryption key.

**Acceptance Criteria**:
```gherkin
Given existing secrets encrypted with key version 1
When the admin configures a new encryption key version 2
Then new secrets are encrypted using key version 2
And existing secrets encrypted with key version 1 remain readable
And there is no requirement to re-encrypt all existing secrets simultaneously
```

**Edge Cases**:
- If key version 1 is removed before secrets are re-encrypted, those secrets become unreadable and the system returns an error indicating the key is unavailable

---

### 2.3 P3 Scenarios (Enhancement)

#### SC-008: Delete a secret

**Preconditions**: A secret exists.

**Trigger**: A user deletes the secret.

**Acceptance Criteria**:
```gherkin
Given a Secret "db-password" exists for the tenant
When the user calls Delete on "db-password"
Then the secret and its encrypted payload are removed from storage
And subsequent Get calls for "db-password" return a not-found error
```

**Edge Cases**:
- Deleting a secret that is referenced by a SecretReference on another resource returns an error or requires force deletion (depending on policy)

---

#### SC-009: Update a secret payload

**Preconditions**: A secret exists.

**Trigger**: A user updates the secret's payload.

**Acceptance Criteria**:
```gherkin
Given a Secret "db-password" exists with payload "old-pass"
When the user calls Update on "db-password" with new payload "new-pass"
Then the new payload is envelope-encrypted and stored
And a subsequent Get returns "new-pass"
```

**Edge Cases**:
- Updating a secret with an empty payload returns a validation error

---

## 3. Functional Requirements

### 3.1 Core Functions

| ID | Function | Description | Inputs | Outputs |
|----|----------|-------------|--------|---------|
| FR-01 | Create Secret | Create a new secret with encrypted storage | Secret name, payload, SecretClass reference, tenant context | Created Secret resource (without payload) |
| FR-02 | Get Secret | Retrieve a secret with decrypted payload | Secret identifier, tenant context | Secret resource with decrypted payload |
| FR-03 | List Secrets | List secrets for a tenant without payload data | Tenant context, optional filters | List of Secret metadata (no payloads) |
| FR-04 | Update Secret | Replace a secret's encrypted payload | Secret identifier, new payload, tenant context | Updated Secret resource (without payload) |
| FR-05 | Delete Secret | Remove a secret and its encrypted data | Secret identifier, tenant context | Confirmation of deletion |
| FR-06 | Envelope Encryption | Encrypt payload using RSA-wrapped AES data key | Plaintext payload, encryption key | Encrypted payload + wrapped data key |
| FR-07 | Envelope Decryption | Decrypt payload using RSA-unwrapped AES data key | Encrypted payload, wrapped data key, encryption key | Plaintext payload |
| FR-08 | SecretClass CRUD | Manage pluggable backend configurations | SecretClass definition (backend type, config) | SecretClass resource |
| FR-09 | Hub Backend Fetch | Fetch secret data on demand from a Kubernetes cluster | Cluster reference, secret identifier | Secret payload from cluster |
| FR-10 | SecretReference Resolution | Resolve a SecretReference to retrieve the linked secret | SecretReference (resource type, resource ID, secret name) | Decrypted secret payload |

### 3.2 Business Rules

| ID | Rule | Condition | Action |
|----|------|-----------|--------|
| BR-01 | Payload stripping on List | Any List operation on secrets | Remove payload field from all items in response |
| BR-02 | Tenant isolation | Any secret access | OPA policy enforces that only the owning tenant (or authorized cross-tenant admin) can access the secret |
| BR-03 | Encryption at rest | Any secret stored in the database backend | Payload is envelope-encrypted before database write |
| BR-04 | Key version tagging | Secret creation or re-encryption | Store the encryption key version alongside the encrypted payload |
| BR-05 | Backend dispatch | Secret Create/Get | Route to the correct backend based on the secret's SecretClass |

---

## 4. Interface Changes

- **New Secret service**: Full CRUD (Create, Get, List, Update, Delete) for Secret resources
- **New SecretClass service**: CRUD for backend configurations (database, hub/Kubernetes)
- **New SecretReference field type**: A reference type that can be embedded in other resources to point to a Secret, replacing ad-hoc RPCs (e.g., GetKubeconfig, GetPassword)
- **CLI flags**: New flags for configuring the RSA encryption key path/value at service startup
- **Deprecation**: Ad-hoc per-resource secret RPCs (GetKubeconfig, GetPassword) are superseded by SecretReference resolution

---

## 5. State Management

### Secret Lifecycle

```
Created → Active → Deleted
```

- **Created**: Secret resource exists; payload is encrypted and stored (database backend) or reference is registered (hub backend).
- **Active**: Secret is retrievable via Get. Payload is decrypted on read.
- **Deleted**: Secret and encrypted payload are removed from storage. Irreversible.

### Encryption Key Lifecycle

```
Active (current) → Rotated (previous, still valid for decryption) → Retired (removed)
```

- **Active**: Used for encrypting new secrets.
- **Rotated**: A newer key is active; this key is still used to decrypt secrets encrypted under it.
- **Retired**: Key is removed. Secrets still encrypted under this key become unreadable.

---

## 6. Error Handling

| Scenario | Error | Resolution |
|----------|-------|------------|
| Create secret with duplicate name in tenant | Conflict (already exists) | Use a unique name or update the existing secret |
| Create secret with non-existent SecretClass | Not found (SecretClass) | Create the SecretClass first or reference an existing one |
| Get secret from another tenant | Permission denied | Authenticate as the owning tenant or an authorized admin |
| Get hub-backed secret when cluster unreachable | Backend unavailable | Retry when the backing cluster is reachable |
| Decrypt secret with retired/missing key | Decryption key unavailable | Re-encrypt the secret under the current key before retiring the old key |
| Create/Update secret with empty payload | Validation error (empty payload) | Provide a non-empty payload |
| Delete secret referenced by SecretReference | Reference conflict | Remove the SecretReference from the dependent resource first, or force delete |

---

## 7. Non-Functional Requirements

| ID | Requirement | Target |
|----|-------------|--------|
| NFR-01 | Encryption standard | Envelope encryption: RSA for key wrapping, AES for data encryption |
| NFR-02 | Payload size limit | Define a maximum payload size to prevent abuse (e.g., certificates, kubeconfigs) |
| NFR-03 | Key rotation support | New keys encrypt new data; old keys remain valid for decryption until explicitly retired |

---

## 8. Testing Requirements

| ID | Scenario | Type | Priority | Automated |
|----|----------|------|----------|-----------|
| T-01 | Create and Get secret returns decrypted payload | Integration | P1 | Yes |
| T-02 | List secrets does not include payload data | Integration | P1 | Yes |
| T-03 | Cross-tenant secret access is denied by OPA | Integration | P1 | Yes |
| T-04 | SecretClass routes to correct backend | Integration | P1 | Yes |
| T-05 | Envelope encryption produces ciphertext different from plaintext | Unit | P1 | Yes |
| T-06 | Envelope decryption recovers original plaintext | Unit | P1 | Yes |
| T-07 | SecretReference resolves to the correct secret | Integration | P2 | Yes |
| T-08 | Hub backend fetches secret from Kubernetes cluster | Integration | P2 | Yes |
| T-09 | Key rotation: new secrets use new key, old secrets remain readable | Integration | P2 | Yes |
| T-10 | Delete secret removes encrypted data from storage | Integration | P3 | Yes |
| T-11 | Update secret re-encrypts with current key | Integration | P3 | Yes |
| T-12 | Error on Get with retired encryption key | Unit | P2 | Yes |
| T-13 | Error on hub backend when cluster unreachable | Integration | P2 | Yes |

---

## 9. Open Questions

| ID | Question | Impact |
|----|----------|--------|
| OQ-01 | What is the maximum payload size for a secret? | Affects validation rules and storage sizing (FR-01, NFR-02) |
| OQ-02 | When deleting a secret referenced by a SecretReference, should the system block deletion or cascade? | Affects Delete behavior (SC-008, BR-05) |
| OQ-03 | Should the hub backend cache fetched secrets, or always fetch on demand? | Affects latency and consistency for hub-backed secrets (SC-006) |
