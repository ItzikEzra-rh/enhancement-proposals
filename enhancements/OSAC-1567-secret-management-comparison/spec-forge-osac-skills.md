---
title: secret-management-encrypted-storage-pluggable-backends
authors:
  - Itzik Ezra
creation-date: 2026-07-30
last-updated: 2026-07-30
tracking-link:
  - https://redhat.atlassian.net/browse/OSAC-1567
prd:
  - "prd.md"
see-also:
  - "/enhancements/OSAC-1330-type-safe-resource-references"
replaces:
  - N/A
superseded-by:
  - N/A
---

# Secret Management — Encrypted Storage with Pluggable Backends

## Summary

This enhancement introduces a `Secret` resource type with full CRUD service,
envelope encryption (RSA wrapping AES-256-GCM data keys) for database-backed
storage, a `SecretClass` abstraction for pluggable secret backends, and a
`SecretReference` type (from OSAC-1330) for replacing ad-hoc secret retrieval
RPCs across the fulfillment API. See [PRD](prd.md) for detailed requirements.

## Motivation

Secrets in the OSAC fulfillment-service are currently stored as plaintext
fields embedded in resource database rows (e.g., `kubeconfig` in
`HubSpec`, IdP client secrets in org configuration). This creates four
concrete problems:

1. **No encryption at rest.** A database compromise or backup leak exposes
   every credential in cleartext. The only protection is PostgreSQL's access
   control, which is a single point of failure.

2. **No separation of lifecycle.** Secret data is tied to the parent
   resource's lifecycle. Rotating a kubeconfig requires updating the Hub
   resource itself, with all its validation and side-effects.

3. **No uniform access pattern.** Each resource that stores a secret exposes
   its own ad-hoc RPC (e.g., `GetKubeconfig`, `GetPassword`). Clients must
   know which RPC to call for each secret type, and there is no consistent
   authorization model across them.

4. **No key rotation capability.** There is no mechanism to rotate the
   encryption key without downtime. Since secrets are plaintext, the
   question is moot today, but it blocks any future encryption work.

### Goals

- Provide a standalone `Secret` resource with spec/status pattern, decoupling
  secret lifecycle from parent resource lifecycle.
- Implement envelope encryption using RSA-OAEP (key-encryption key) wrapping
  AES-256-GCM (data-encryption key) for the database backend.
- Introduce `SecretClass` as a pluggable backend abstraction supporting
  `database` and `hub` (Kubernetes Secret fetch) backends in this phase.
- Strip secret payloads from `List` responses — only `Get` returns the
  decrypted data.
- Integrate with `SecretReference` (OSAC-1330) so existing ad-hoc RPCs
  (`GetKubeconfig`, `GetPassword`) can be replaced with a uniform pattern.

### Non-Goals

- **External secret manager integration** (HashiCorp Vault, AWS Secrets
  Manager) — future enhancement; `SecretClass` provides the extension point.
- **Automated secret rotation** — rotation of the data itself (e.g.,
  regenerating a kubeconfig) is out of scope; key rotation (re-wrapping
  data-encryption keys under a new KEK) is in scope.
- **SSH key cloud-init injection** — VMaaS-specific (OSAC-51), separate
  proposal.
- **Migration of existing plaintext secrets** — the migration tooling to
  move existing embedded secrets into Secret resources is deferred to an
  implementation epic.

## Proposal

The design introduces four coordinated changes to the fulfillment-service:

1. **`Secret` resource and gRPC service** with full CRUD, envelope-encrypted
   database storage, and payload stripping on List.
2. **`SecretClass` resource and gRPC service** defining pluggable backends
   (database, hub) with provider-managed lifecycle.
3. **Hub secret backend** that fetches secret data on-demand from Kubernetes
   clusters rather than storing it locally.
4. **`SecretReference` integration** replacing ad-hoc RPCs with a uniform
   reference pattern using the type-safe reference system from OSAC-1330.

### Workflow Description

#### Secret Creation (Database Backend)

**Actors:** Tenant User or Tenant Admin (creator), fulfillment-service
(encryption, storage).

1. Cloud Infrastructure Admin creates a `SecretClass` with
   `backend_type: DATABASE` and configures the encryption key path via
   CLI flags on the fulfillment-service binary.
2. Tenant User sends `CreateSecret` with `spec.secret_class` referencing
   the database-backed `SecretClass`, `spec.type` indicating the secret
   category (e.g., `OPAQUE`, `KUBECONFIG`, `TLS`), and `spec.data` as a
   map of key-value pairs containing the plaintext secret material.
3. Fulfillment-service generates a random AES-256-GCM data-encryption key
   (DEK), encrypts `spec.data` with the DEK, wraps the DEK with the
   configured RSA public key (KEK), and stores the wrapped DEK +
   ciphertext in the `secrets` database table. The plaintext DEK is never
   persisted.
4. Service returns the Secret with `status.conditions` reflecting
   `Ready=True` and `spec.data` omitted from the response (data is only
   returned on `Get`).

#### Secret Retrieval

1. Tenant User sends `GetSecret` for a specific secret by name or ID.
2. For database backend: service reads the wrapped DEK + ciphertext from
   the database, unwraps the DEK using the RSA private key, decrypts the
   data, and returns it in `spec.data`.
3. For hub backend: service connects to the referenced Kubernetes cluster,
   reads the Kubernetes Secret, and returns the data. No local storage.
4. `ListSecrets` returns secret metadata only — `spec.data` is always
   empty in list responses.

#### Secret Reference Integration

1. A resource that needs to reference a secret (e.g., Hub kubeconfig)
   includes a `SecretReference` field in its spec.
2. On resource creation/update, the reference validation interceptor
   (OSAC-1330) confirms the referenced Secret exists and is accessible
   to the caller's tenant.
3. Clients retrieve the secret data through `GetSecret` using the reference,
   instead of ad-hoc RPCs like `GetKubeconfig`.
4. Existing ad-hoc RPCs are deprecated but retained during migration.

#### Key Rotation

1. Cloud Infrastructure Admin generates a new RSA key pair and configures
   the fulfillment-service with both old and new private keys (the service
   accepts a list of private keys for decryption).
2. Admin triggers a key rotation job (CLI command or API call) that
   re-wraps each DEK: decrypt with old KEK, re-wrap with new KEK.
3. Once all DEKs are re-wrapped, the old private key can be removed from
   configuration. Re-wrapping is idempotent — DEKs already wrapped with
   the new key are skipped.

### API Extensions

#### Secret Resource

```protobuf
// File: api/v1/secrets/v1/secret_type.proto

enum SecretType {
  SECRET_TYPE_UNSPECIFIED = 0;
  SECRET_TYPE_OPAQUE = 1;
  SECRET_TYPE_KUBECONFIG = 2;
  SECRET_TYPE_TLS = 3;
  SECRET_TYPE_BASIC_AUTH = 4;
  SECRET_TYPE_SSH_KEY = 5;
}

message Secret {
  string id = 1;
  osac.common.v1.Metadata metadata = 2;
  SecretSpec spec = 3;
  SecretStatus status = 4;
}

message SecretSpec {
  // Reference to the SecretClass that determines the storage backend.
  SecretClassLocalReference secret_class = 1;

  // The type of secret. Determines validation rules for spec.data keys.
  SecretType type = 2;

  // Secret payload as key-value pairs. Populated on Create/Update requests
  // and Get responses. Always empty in List responses.
  map<string, bytes> data = 3;

  // Human-readable description of the secret's purpose.
  string description = 4;
}

message SecretStatus {
  repeated osac.common.v1.Condition conditions = 1;
}
```

**Condition types:**
- `Ready` — secret is stored and retrievable
- `EncryptionHealthy` — DEK is wrapped with the current KEK (false during
  key rotation for not-yet-re-wrapped secrets)

#### SecretClass Resource

```protobuf
// File: api/v1/secretclasses/v1/secret_class_type.proto

enum SecretBackendType {
  SECRET_BACKEND_TYPE_UNSPECIFIED = 0;
  SECRET_BACKEND_TYPE_DATABASE = 1;
  SECRET_BACKEND_TYPE_HUB = 2;
}

message SecretClass {
  string id = 1;
  osac.common.v1.Metadata metadata = 2;
  SecretClassSpec spec = 3;
  SecretClassStatus status = 4;
}

message SecretClassSpec {
  // Backend type for this class.
  SecretBackendType backend_type = 1;

  // Human-readable description.
  string description = 2;

  // Backend-specific configuration.
  oneof backend_config {
    DatabaseBackendConfig database = 10;
    HubBackendConfig hub = 11;
  }
}

message DatabaseBackendConfig {
  // No fields required — encryption key is configured via CLI flags
  // on the fulfillment-service binary, not stored in the database.
}

message HubBackendConfig {
  // Reference to the Hub cluster from which secrets are fetched.
  HubReference hub = 1;

  // Kubernetes namespace to read secrets from.
  string namespace = 2;
}

message SecretClassStatus {
  repeated osac.common.v1.Condition conditions = 1;
}
```

**Condition types:**
- `Ready` — backend is reachable and operational

#### Secret Service

```protobuf
// File: api/v1/secrets/v1/secret_service.proto

service Secrets {
  rpc CreateSecret(CreateSecretRequest) returns (Secret) {
    option (google.api.http) = {
      post: "/api/v1/secrets"
      body: "*"
    };
  }

  rpc GetSecret(GetSecretRequest) returns (Secret) {
    option (google.api.http) = {
      get: "/api/v1/secrets/{id}"
    };
  }

  rpc ListSecrets(ListSecretsRequest) returns (ListSecretsResponse) {
    option (google.api.http) = {
      get: "/api/v1/secrets"
    };
  }

  rpc UpdateSecret(UpdateSecretRequest) returns (Secret) {
    option (google.api.http) = {
      put: "/api/v1/secrets/{id}"
      body: "*"
    };
  }

  rpc DeleteSecret(DeleteSecretRequest) returns (google.protobuf.Empty) {
    option (google.api.http) = {
      delete: "/api/v1/secrets/{id}"
    };
  }
}

message CreateSecretRequest {
  Secret secret = 1;
}

message GetSecretRequest {
  string id = 1;
}

message ListSecretsRequest {
  osac.common.v1.ListOptions list_options = 1;
}

message ListSecretsResponse {
  repeated Secret items = 1;
  osac.common.v1.ListMeta list_meta = 2;
}

message UpdateSecretRequest {
  Secret secret = 1;
}

message DeleteSecretRequest {
  string id = 1;
}
```

#### SecretClass Service

```protobuf
// File: api/v1/secretclasses/v1/secret_class_service.proto

service SecretClasses {
  rpc CreateSecretClass(CreateSecretClassRequest) returns (SecretClass) {
    option (google.api.http) = {
      post: "/api/v1/secretclasses"
      body: "*"
    };
  }

  rpc GetSecretClass(GetSecretClassRequest) returns (SecretClass) {
    option (google.api.http) = {
      get: "/api/v1/secretclasses/{id}"
    };
  }

  rpc ListSecretClasses(ListSecretClassesRequest)
      returns (ListSecretClassesResponse) {
    option (google.api.http) = {
      get: "/api/v1/secretclasses"
    };
  }

  rpc UpdateSecretClass(UpdateSecretClassRequest) returns (SecretClass) {
    option (google.api.http) = {
      put: "/api/v1/secretclasses/{id}"
      body: "*"
    };
  }

  rpc DeleteSecretClass(DeleteSecretClassRequest)
      returns (google.protobuf.Empty) {
    option (google.api.http) = {
      delete: "/api/v1/secretclasses/{id}"
    };
  }
}
```

Request/response messages follow the same pattern as the Secrets service.

#### SecretReference (from OSAC-1330)

```protobuf
// Added to the Secret type file per OSAC-1330 conventions.

message SecretReference {
  string id = 1;
  string tenant = 2;
  string project = 3;
  string name = 4;
}

message SecretLocalReference {
  string name = 1;
}
```

Resources that currently embed secret data will add a `SecretReference` or
`SecretLocalReference` field. For example, `HubSpec` gains:

```protobuf
message HubSpec {
  // ... existing fields ...

  // Reference to the Secret containing the kubeconfig.
  // Replaces the inline kubeconfig field (deprecated).
  SecretLocalReference kubeconfig_secret = N;
}
```

### Implementation Details/Notes/Constraints

#### Database Schema

```sql
CREATE TABLE secrets (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id),
    name TEXT NOT NULL,
    type TEXT NOT NULL,
    secret_class_id UUID NOT NULL REFERENCES secret_classes(id),
    description TEXT,
    encrypted_data BYTEA NOT NULL,     -- AES-256-GCM ciphertext
    wrapped_dek BYTEA NOT NULL,        -- RSA-OAEP wrapped DEK
    dek_nonce BYTEA NOT NULL,          -- GCM nonce
    kek_fingerprint TEXT NOT NULL,     -- SHA-256 of the KEK public key
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(tenant_id, name)
);

CREATE TABLE secret_classes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL UNIQUE,
    backend_type TEXT NOT NULL,
    description TEXT,
    backend_config JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

- `encrypted_data` stores the AES-256-GCM ciphertext of the serialized
  `map<string, bytes>` data.
- `wrapped_dek` stores the RSA-OAEP encrypted DEK.
- `kek_fingerprint` identifies which KEK was used, enabling multi-key
  rotation.

#### Envelope Encryption Flow

```text
CreateSecret:
  plaintext_data ──► serialize to bytes
  DEK = random 256-bit key
  nonce = random 96-bit GCM nonce
  ciphertext = AES-256-GCM(DEK, nonce, serialized_data)
  wrapped_dek = RSA-OAEP(KEK_public, DEK)
  store: (ciphertext, wrapped_dek, nonce, kek_fingerprint)
  discard: DEK, plaintext_data

GetSecret:
  read: (ciphertext, wrapped_dek, nonce, kek_fingerprint)
  DEK = RSA-OAEP-Decrypt(KEK_private[kek_fingerprint], wrapped_dek)
  plaintext = AES-256-GCM-Decrypt(DEK, nonce, ciphertext)
  deserialize to map<string, bytes>
  discard: DEK
```

#### CLI Configuration

The fulfillment-service binary accepts encryption key configuration via CLI
flags:

```
--secret-encryption-public-key   Path to RSA public key (PEM) for wrapping DEKs
--secret-encryption-private-keys Comma-separated paths to RSA private keys (PEM)
                                 for unwrapping DEKs (supports multiple for rotation)
```

When no encryption keys are configured, the Secrets service returns
`FAILED_PRECONDITION` on all write operations. Read operations for hub-backed
secrets remain functional.

#### Hub Backend Implementation

The hub backend does not store secret data locally. Instead:

1. On `GetSecret`, the service connects to the Kubernetes cluster referenced
   by `HubBackendConfig.hub` using the cluster's existing service account
   credentials.
2. It reads the Kubernetes Secret from the configured namespace using the
   Secret resource's `name` as the Kubernetes Secret name.
3. The Kubernetes Secret's `data` map is returned directly as the OSAC
   Secret's `spec.data`.
4. `CreateSecret` and `UpdateSecret` for hub-backed secrets store only
   metadata in the database (no `encrypted_data`, `wrapped_dek`, or
   `dek_nonce`). The actual secret data is assumed to exist in the
   Kubernetes cluster.
5. `DeleteSecret` removes the metadata row but does not delete the
   Kubernetes Secret.

[Assumption] The hub backend assumes the Kubernetes Secret already exists in
the target cluster. Creating secrets in remote clusters is out of scope.

#### Data Stripping on List

The `ListSecrets` server implementation explicitly sets `spec.data` to an
empty map before returning responses. This is enforced in the server code,
not via proto field behavior annotations, to ensure no backend path
accidentally leaks secret data.

#### Type-Based Validation

Each `SecretType` imposes validation rules on `spec.data` keys:

| Type | Required Keys | Optional Keys |
|------|--------------|---------------|
| `OPAQUE` | (none) | any |
| `KUBECONFIG` | `kubeconfig` | (none) |
| `TLS` | `tls.crt`, `tls.key` | `ca.crt` |
| `BASIC_AUTH` | `username`, `password` | (none) |
| `SSH_KEY` | `ssh-privatekey` | `ssh-publickey` |

Validation occurs at the API layer (`CreateSecret`, `UpdateSecret`).

#### SecretReference Migration Path

Existing resources that embed secrets will be migrated incrementally:

1. Add `SecretLocalReference` field to the resource spec (e.g.,
   `HubSpec.kubeconfig_secret`).
2. Deprecate the inline secret field (e.g., `HubSpec.kubeconfig`).
3. During the migration period, the server accepts either field. If both
   are set, `SecretLocalReference` takes precedence.
4. After migration, the deprecated field is removed.

[Assumption] The migration period duration and deprecation policy will be
defined in the implementation epic (OSAC-1337).

### Security Considerations

**Encryption at rest:** All database-backed secrets use envelope encryption
with AES-256-GCM (data) and RSA-OAEP (key wrapping). The RSA private key
must be stored securely outside the database (file system with restricted
permissions, or a future KMS integration via a new SecretClass backend).

**Key management:** RSA key pairs are managed outside OSAC. The
fulfillment-service binary reads key files from paths specified via CLI
flags. Key generation, backup, and access control are the operator's
responsibility.

**Data exposure:** Secret payloads are never included in List responses.
Get responses include the decrypted payload only for authorized callers.
The Secret resource never appears in audit logs with its `spec.data`
populated.

**Memory handling:** DEKs and plaintext data exist in memory only during
encryption/decryption operations. Go's garbage collector will eventually
reclaim the memory; explicit zeroing is not guaranteed by the Go runtime.
[Assumption] This is acceptable for the initial implementation.

**Transport security:** All gRPC and REST traffic is already TLS-encrypted.
No additional transport-layer changes are required.

### Failure Handling and Recovery

| Failure Mode | What Happens | Recovery | User Observes |
|-------------|-------------|----------|---------------|
| RSA private key unavailable | `GetSecret` returns `FAILED_PRECONDITION` for database-backed secrets | Restore the key file and restart the service | Error on Get; metadata remains accessible via List |
| Corrupt ciphertext in DB | `GetSecret` returns `INTERNAL` with "decryption failed" | Restore from backup; the secret must be re-created if no backup exists | Error on Get for the specific secret |
| Hub cluster unreachable | `GetSecret` for hub-backed secrets returns `UNAVAILABLE` | Retry after connectivity is restored; condition set to `Ready=False` | Transient error; List still returns metadata |
| K8s Secret not found on hub | `GetSecret` returns `NOT_FOUND` | Create the Kubernetes Secret in the target cluster | Error on Get |
| Key rotation partially complete | Some DEKs wrapped with old KEK, some with new | Re-run rotation job (idempotent) | No user impact — both old and new keys accepted for decryption |
| Referenced Secret deleted | Parent resource's `SecretReference` points to nonexistent Secret | Re-create the Secret or update the parent resource's reference | Parent resource's status may reflect a broken reference (depends on controller) |
| Database constraint violation on Create | `CreateSecret` returns `ALREADY_EXISTS` (duplicate name in tenant) | Choose a different name | Validation error |

### RBAC / Tenancy

**Tenant isolation:** The `secrets` table includes `tenant_id` as a
mandatory foreign key. All queries are scoped by `tenant_id` using the
caller's tenant context from the authentication token. OPA policies enforce
that a caller can only access secrets within their own tenant.

**Tenant isolation metadata:** Secret resources carry the standard OSAC
annotations:
- `osac.openshift.io/tenant` — set to the caller's tenant ID on creation
- `osac.openshift.io/owner-reference` — set when the Secret is created as
  a child of another resource (e.g., a Hub)

**SecretClass access:** SecretClasses are platform-scoped resources managed
by Cloud Infrastructure Admins. Tenants can reference SecretClasses but
cannot create, update, or delete them.

**Roles:**

| Operation | Cloud Provider Admin | Cloud Infrastructure Admin | Tenant Admin | Tenant User |
|-----------|---------------------|---------------------------|-------------|-------------|
| SecretClass CRUD | Full | Full | Read-only | Read-only |
| Secret Create/Update/Delete | Full (any tenant) | Full (any tenant) | Own tenant | Own tenant |
| Secret Get (with data) | Full (any tenant) | Full (any tenant) | Own tenant | Own tenant |
| Secret List (metadata only) | Full (any tenant) | Full (any tenant) | Own tenant | Own tenant |

### Observability and Monitoring

| Metric / Event | Type | Description |
|----------------|------|-------------|
| `osac_secret_operations_total` | Counter | Total secret operations by verb (create, get, list, update, delete) and backend type |
| `osac_secret_encryption_duration_seconds` | Histogram | Time spent on envelope encryption/decryption operations |
| `osac_secret_kek_rotation_remaining` | Gauge | Number of DEKs still wrapped with a non-current KEK (drives rotation progress) |
| `SecretEncryptionHealthy` condition | Condition | Per-secret condition indicating whether the DEK is wrapped with the current KEK |
| `osac_secret_hub_fetch_errors_total` | Counter | Hub backend fetch failures by hub reference and error type |

**Alert thresholds:**
- `osac_secret_kek_rotation_remaining > 0` for more than 24 hours after a
  key rotation is initiated indicates a stalled rotation.
- `osac_secret_hub_fetch_errors_total` rate > 5/min indicates hub
  connectivity issues.

### Risks and Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| RSA key compromise | All database-backed secrets exposed | Document key management best practices; SecretClass abstraction enables future KMS backend migration |
| Performance impact of per-request decryption | Latency increase on GetSecret | AES-256-GCM decryption is fast (~1ms for typical payloads); monitor via `osac_secret_encryption_duration_seconds` |
| Memory exposure of DEKs | Go GC does not guarantee zeroing freed memory | Acceptable for initial implementation; document as known limitation; future: use `memguard` or CGo for secure memory |
| Hub backend availability | Secrets unavailable if hub cluster is down | Conditions reflect health; tenant can use database backend for critical secrets |
| Migration complexity | Existing resources with inline secrets need coordinated migration | Incremental migration with deprecation period; both inline and reference paths supported during transition |

### Drawbacks

**Operational complexity:** Operators must manage RSA key pairs outside OSAC,
including key generation, secure storage, backup, and rotation scheduling.
This is inherent to any encryption-at-rest solution that does not use an
external KMS.

**No built-in key management:** Unlike systems that integrate with KMS
providers, OSAC's initial implementation requires manual key lifecycle
management. The SecretClass abstraction mitigates this by providing the
extension point for a future KMS backend.

**Two access patterns during migration:** While inline secret fields and
SecretReference coexist, clients and documentation must handle both patterns.
This is a temporary cost that resolves when migration completes.

## UX Alignment

*No `@temp-api` file exists for Secret or SecretClass in
`osac-ux/libs/ui-components/src/api/v1/`. This section will be completed
when the UI team defines the Secret management screens.*

## Alternatives (Not Implemented)

### Alternative 1: Application-Level Encryption Without Envelope

Encrypt secrets directly with a single AES key rather than using envelope
encryption (RSA wrapping AES DEKs).

**Rejected because:** A single AES key means key rotation requires
re-encrypting every secret simultaneously. Envelope encryption allows
rotating the KEK by re-wrapping DEKs (a fast operation) without touching
the ciphertext. This is the standard approach used by Kubernetes
(kube-apiserver envelope encryption), AWS KMS, and Google Cloud KMS.

### Alternative 2: Store Secrets in Kubernetes (etcd) Instead of PostgreSQL

Use Kubernetes Secrets as the primary storage backend, leveraging etcd's
existing encryption-at-rest support.

**Rejected because:** OSAC's fulfillment-service uses PostgreSQL as its
primary datastore. Adding a Kubernetes dependency for secret storage would
split the data plane, complicate backup/restore, and introduce a dependency
on etcd encryption configuration that OSAC does not control. The hub backend
provides Kubernetes integration for on-demand secret fetching without making
it the primary storage layer.

### Alternative 3: Integrate HashiCorp Vault Directly

Skip the abstraction layer and integrate directly with HashiCorp Vault as
the secret backend.

**Rejected because:** Not all OSAC deployments will have Vault available.
The SecretClass abstraction allows Vault integration as a future backend
without forcing it as a dependency. The database backend provides a
self-contained solution for deployments without external secret managers.

## Open Questions

1. **Maximum secret size.** Should there be an enforced limit on
   `spec.data` total size? Kubernetes limits Secrets to 1 MiB. A similar
   limit (e.g., 1 MiB pre-encryption) would prevent abuse and keep
   encryption performance predictable.

2. **Audit logging granularity.** Should `GetSecret` calls be logged at a
   higher audit level than other read operations, given that they return
   sensitive data? This may require integration with the OSAC audit
   subsystem if one exists.

3. **Default SecretClass.** Should OSAC auto-create a default database-backed
   SecretClass during installation, or require explicit creation by the
   Cloud Infrastructure Admin?

## Test Plan

### Unit Tests

- Envelope encryption round-trip: encrypt then decrypt returns original data
- DEK wrapping with RSA-OAEP produces valid ciphertext
- Decryption with wrong KEK private key returns error
- `ListSecrets` response never contains `spec.data` values
- `SecretType` validation rejects missing required keys (e.g., `TLS` without
  `tls.crt`)
- `SecretType` validation accepts valid key sets for each type
- `CreateSecret` without configured encryption keys returns
  `FAILED_PRECONDITION`
- `DeleteSecret` for a Secret referenced by another resource returns
  `FAILED_PRECONDITION` (referential integrity)
- Key rotation re-wraps DEK with new KEK and updates `kek_fingerprint`
- Key rotation skips DEKs already wrapped with the current KEK

### Integration Tests

- Create a Secret with database backend, Get it, verify decrypted data
  matches input
- Create a Secret, List secrets, verify data is stripped
- Create two Secrets with the same name in one tenant, verify
  `ALREADY_EXISTS`
- Create Secrets in two tenants, verify cross-tenant isolation (tenant A
  cannot Get tenant B's secret)
- Create a SecretClass, create a Secret referencing it, delete the
  SecretClass, verify `FAILED_PRECONDITION`
- Update a Secret's `spec.data`, Get it, verify updated data
- Key rotation with multiple KEKs: create secrets, rotate, verify all
  secrets still decryptable

### E2E Tests

- Tenant user creates a database-backed Secret, retrieves it via Get, and
  verifies the payload (uses fulfillment-service gRPC client in
  osac-test-infra)
- Cloud Infrastructure Admin creates a SecretClass, tenant user references
  it in a new Secret
- Tenant user creates a Secret, another tenant user in a different tenant
  cannot access it
- [Assumption] Hub backend E2E test requires a running Kubernetes cluster
  with a pre-existing Secret; feasibility depends on osac-test-infra's kind
  cluster setup

## Graduation Criteria

### Dev Preview

- Secret and SecretClass CRUD operations functional with database backend
- Envelope encryption operational with CLI-configured RSA keys
- Data stripping on List verified
- Unit and integration tests passing

### Tech Preview

- Hub secret backend operational
- SecretReference integration with at least one existing resource (e.g., Hub
  kubeconfig)
- Key rotation workflow documented and tested
- E2E tests in osac-test-infra

### GA

- All ad-hoc secret RPCs migrated to SecretReference pattern
- OPA policies for secret access control reviewed and hardened
- Performance benchmarked under load (encryption latency, hub fetch latency)
- Operational documentation complete (key management, rotation, backup)

## Upgrade / Downgrade Strategy

OSAC does not currently support upgrades, so data migration and backward
compatibility are not concerns at this stage. When upgrade support is added:

**Upgrade:** The `secrets` and `secret_classes` tables are additive — new
tables with no impact on existing resources. Existing resources with inline
secrets continue to function. Migration to SecretReference is opt-in during
the deprecation period.

**Downgrade:** Removing the Secret subsystem requires migrating any
SecretReference fields back to inline secret fields. The database tables can
be dropped without affecting other resources. DEKs and ciphertext are lost
on table drop — secrets must be re-created from external sources.

## Version Skew Strategy

The Secret and SecretClass services are self-contained within the
fulfillment-service. No cross-component version skew concerns exist for the
core CRUD operations.

For SecretReference integration: during the migration period, both inline
fields and SecretReference fields are supported. A newer fulfillment-service
binary can read resources created by an older version (inline fields), and an
older binary can read resources created by a newer version (it ignores the
SecretReference field and uses the inline field if present).

## Support Procedures

**Symptom: `GetSecret` returns `FAILED_PRECONDITION`**
- Check that `--secret-encryption-public-key` and
  `--secret-encryption-private-keys` CLI flags are configured
- Verify the key files exist and are readable by the service process
- Check fulfillment-service logs for key loading errors at startup

**Symptom: `GetSecret` returns `INTERNAL` with "decryption failed"**
- The `kek_fingerprint` on the secret row does not match any configured
  private key
- Verify all historical KEK private keys are in the
  `--secret-encryption-private-keys` list
- If keys were lost, the secret data is unrecoverable — re-create from
  external source

**Symptom: Hub-backed secret returns `UNAVAILABLE`**
- Check connectivity to the hub cluster referenced by the SecretClass
- Verify the service account has RBAC to read Secrets in the configured
  namespace
- Check `osac_secret_hub_fetch_errors_total` metric for error patterns

**Disabling the feature:** Remove the Secret and SecretClass service
registrations from the gRPC server configuration. Existing resources with
SecretReference fields will fail reference validation — revert to inline
fields before disabling.

## Infrastructure Needed

No new infrastructure. The feature uses the existing fulfillment-service
PostgreSQL database and gRPC server framework.
