# Story 1.01: [DEV] Expose the public Volume read contract and endpoints

**As a** tenant user, tenant admin, or Cloud Provider Admin,
**I want** a public Volume service with the tenant-facing object shape,
**So that** clients can retrieve and list existing volume inventory through the standard OSAC channels.

## Acceptance Criteria

- [ ] The public service exposes read-only Volume `Get` and `List` operations over gRPC and REST at the approved collection and item paths.
- [ ] Public Volume responses contain the approved tenant-facing fields and omit backend, protocol, hub, vendor identifier, and vendor context fields.
- [ ] Public reads reuse the existing volume inventory and return gRPC `Internal` when private-to-public mapping fails; they do not create a second persistence or provisioning path.
- [ ] Tenant clients can call public `Get` and `List`; public mutation methods are absent or rejected with the specified authorization behavior.
- [ ] The generic CLI can discover the public Volume type from descriptors without a volume-specific command implementation.
- [ ] Unit/server coverage exercises the public projection, exact public schema allowlist, public filter descriptor, endpoint registration, and authorization behavior.

## Implementation Guidance

- Edit only the private proto sources under `proto/private/osac/private/v1/`; regenerate the public proto and committed Go tree with `make -C proto generate`, then review generated diffs and run the component's proto lint. Do not hand-edit generated output.
- Follow the public-wraps-private pattern in `fulfillment-service/internal/servers/volumes_server.go` and `external_ips_server.go`. Keep the mapper non-strict so private fields absent from the public descriptor are omitted, and convert mapping failures to gRPC `Internal`.
- Keep the read-only delegate construction in `private_volumes_server.go` independent of the tier resolver used by `Create`; configure the public descriptor for CEL filtering before forwarding requests.
- Register both generated public gRPC and REST handlers in `fulfillment-service/internal/cmd/service/start/grpcserver/register_servers.go` and `internal/cmd/service/start/restgateway/start_rest_gateway_cmd.go`. Add the public read allowlist entries in `internal/auth/policies/authz.rego`.
- Reconcile the existing registration expectation tests, which currently assert only the private Volume handler/service even though production registration contains the public service.
- The current baseline already contains this public implementation according to `01-context.md`; before coding, compare the branch state with the approved design and treat any difference as implementation-drift evaluation rather than silently duplicating or changing behavior.

## Testing Approach

- **Unit/server:** Extend the Ginkgo/Gomega server tests in `fulfillment-service/internal/servers/volumes_server_test.go`, `private_volumes_server_test.go`, and relevant auth/registration tests. The suite uses a real PostgreSQL test container; the repository guidance names `ginkgo run internal/servers` and `ginkgo run -r internal` from `fulfillment-service`.
- **Contract/build validation:** Run `make -C proto generate` and the proto lint after private-source changes. Generated output must remain synchronized; this is generation/lint validation, not a substitute for behavior tests.
- **E2E:** No E2E is owned by this story; deployed access is assigned to Story 1.04.

## Dependencies

None

## Design Reference

Epic: Epic 1 — Tenant-visible volume inventory read API
PRD Requirements: FR-1, FR-5, FR-7
Design section: Proposal, Workflow Description, API Extensions, Implementation Details/Notes/Constraints, Security Considerations, RBAC / Tenancy
Interface Changes: IC-1, IC-2, IC-3
Validated by: TC-FR1-01, TC-FR1-02, TC-FR2-02, TC-FR5-01, TC-FR5-02, TC-FR7-01, TC-FR7-02
