# Story 1.04: [DOCS] Document the public Volume read surface

**As a** API consumer,
**I want** accurate reference and usage documentation for public Volume reads,
**So that** I can discover the endpoints, interpret responses, and use the generic CLI safely.

## Acceptance Criteria

- [ ] The published API specification documents `GET /api/fulfillment/v1/volumes` and `GET /api/fulfillment/v1/volumes/{id}` with the public fields and standard list parameters.
- [ ] User-facing documentation explains the immutable id request key, tenant/project visibility, Cloud Provider Admin visibility, non-archived states, archived exclusion, public/private field boundary, and documented error statuses.
- [ ] CLI guidance describes `osac get volumes` and `osac get volume <id>` through generic descriptor discovery, including the structured output expectation.
- [ ] The authorization overview and API documentation do not imply that public Volume mutations are available.
- [ ] The owner identifies the actual OpenAPI/specification artifact and validates the generated or published output; the current missing local OpenAPI path remains an explicit setup gap.

## Documentation Scope

The reader needs endpoint discovery for public gRPC/REST Volume Get/List, the public field allowlist, id/name/display-name semantics, filtering/pagination/order behavior, tenant/project visibility, inventory states, archived-record behavior, errors, and generic CLI access. The documentation should also state that provisioning and mutation remain on the private API.

## Documentation Inputs

**Story 1.01 — public Volume contract and endpoints:**

- Public `osac.public.v1.Volumes` service with `Get` and `List` only.
- REST paths `GET /api/fulfillment/v1/volumes` and `GET /api/fulfillment/v1/volumes/{id}`.
- Public fields `id`, `metadata`, `spec.storage_tier`, `spec.size_gib`, `spec.access_mode`, `status.state`, and `status.message`; private routing fields are absent.
- Public errors including `NotFound`, `InvalidArgument`, `PermissionDenied`, and `Internal`.

**Story 1.02 — list, visibility, and lifecycle behavior:**

- CEL `this.<field>` filtering, offset/limit pagination, order behavior, tenant/project scoping, Cloud Provider Admin visibility, and state/archive semantics.
- Immutable id request behavior and RFC 1123 metadata name semantics.

**Story 1.03 — deployed consumer validation:**

- Observed REST response shape, generic CLI discovery behavior, and environment-specific prerequisites once the QE harness is confirmed.

## Dependencies

Story 1.01, Story 1.02

## Design Reference

Epic: Epic 1 — Tenant-visible volume inventory read API
PRD Requirements: FR-7, FR-8
Design section: API Extensions, UX Alignment, Failure Handling and Recovery, RBAC / Tenancy, Support Procedures
Validated by: TC-FR8-02
