# Secret Management — Encrypted Storage with Pluggable Backends

| Field       | Value   |
|-------------|---------|
| Author(s)   | Forge   |
| Jira        | [OSAC-4022](https://issues.redhat.com/browse/OSAC-4022) |
| Date        | 2026-08-13 |

## Problem Statement

Credentials across OSAC services — cluster kubeconfigs, identity provider secrets, storage credentials, SSH keys — are stored unencrypted alongside the resources that use them. Cloud Infrastructure Admins cannot meet data-at-rest security and compliance requirements because credential data is exposed to anyone with database access. Tenant users cannot revoke or rotate a credential without modifying the resource it belongs to, and retrieving credentials requires learning a different method for each resource type (e.g., GetKubeconfig, GetPassword). There is no single place for a tenant to see what credentials exist or who has access to them.

## In Scope

- Applies to all OSAC services (BMaaS, CaaS, VMaaS, MaaS, Enclave) — any service that creates or consumes credentials
- Uniform secret management across all OSAC services (CLI and API)
- Encrypted storage of tenant and platform credentials at rest, with support for encryption key rotation
- Pluggable secret backends, so cloud providers can bring their own secret store
- Secret payload excluded from list responses — only individual retrieval returns decrypted data
- On-demand credential retrieval for provisioned resources (e.g., cluster kubeconfigs, admin passwords)
- Self-service secret creation for tenants (e.g., SSH key pairs, OIDC client secrets, cloud-init credentials)
- Automatic secret creation during resource provisioning (e.g., cluster kubeconfigs generated at provision time)
- Tenant-scoped RBAC for secret access control — OSAC limits its access to only a tenant's secrets when operating on that tenant's behalf
- Secret CRUD operations complete synchronously with immediate error feedback
- Installation — cloud provider must deploy and configure a Vault-compatible secret store as a prerequisite
- E2E testing — secret CRUD, automatic secret creation during provisioning, and tenant isolation require coverage
- Documentation — user guides for secret management CLI/API workflows per persona; API reference

## Out of Scope

- Secret rotation automation — users can manually update secrets, but automated rotation workflows are not in scope
- SSH key cloud-init injection for VMs — VMaaS-specific, tracked separately in OSAC-51
- UI — secret management is CLI and API only for 0.2

## User Stories

### Cloud Infrastructure Admin

- As a Cloud Infrastructure Admin, I want secrets encrypted at rest so that database access does not expose sensitive credentials.
- As a Cloud Infrastructure Admin, I want to rotate encryption keys without re-encrypting all secrets simultaneously so that key rotation does not require downtime or a bulk migration operation.

### Cloud Provider Admin

- As a Cloud Provider Admin, I want tenant secrets securely managed and isolated per tenant so that the platform meets data-at-rest compliance requirements.
- As a Cloud Provider Admin, I want to see secrets scoped to each tenant so that I can verify tenant isolation and manage cross-tenant secret governance.

### Tenant Admin

- As a Tenant Admin, I want to create and manage secrets within my organization (e.g., OIDC client secrets for identity provider integration) so that my team's credentials are centrally managed.
- As a Tenant Admin, I want to control which users can access secrets through RBAC so that I can enforce credential access policies consistent with other OSAC resources.

### Tenant User

- As a Tenant User, I want to create secrets (e.g., SSH key pairs, cloud-init credentials) and reference them when provisioning resources so that I can manage my credentials in one place.
- As a Tenant User, I want to retrieve credentials for provisioned resources (e.g., cluster kubeconfigs, admin passwords) through the same secret interface I use for my own secrets so that credential access is consistent regardless of how the secret was created.
- As a Tenant User, I want to list my secrets and see metadata without exposing the actual secret data so that I can browse credentials safely.
- As a Tenant User, I want to update the value of a secret I own so that I can rotate credentials without recreating resource references.
- As a Tenant User, I want to delete a secret I no longer need so that stale credentials do not persist in the system.

## Assumptions

- The Vault-compatible API is a stable and widely supported interface for secret storage.
- Credentials for provisioned resources (e.g., cluster kubeconfigs) can be retrieved on demand from the management cluster.
- The existing ad-hoc secret retrieval RPCs (GetKubeconfig, GetPassword) can be replaced by uniform secret lookups without breaking existing client workflows, since OSAC does not support in-place upgrades.

## Dependencies

- **Vault-compatible secret store:** The cloud provider deploys and operates a Vault-compatible secret store and provides OSAC access to use it. Must be in place before secrets can be stored or retrieved.
- **OSAC-1330 (Type-safe resource references):** Provides the SecretReference type used to link resources to their associated secrets. Must land before ad-hoc RPCs can be replaced by uniform secret lookups.