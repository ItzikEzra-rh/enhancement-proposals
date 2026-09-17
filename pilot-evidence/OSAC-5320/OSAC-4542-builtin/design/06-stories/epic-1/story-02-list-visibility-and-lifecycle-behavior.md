# Story 1.02: [DEV] Preserve standard list, visibility, and volume lifecycle behavior

**As a** volume consumer,
**I want** List and Get to honor standard filtering, pagination, visibility, identifiers, and inventory-state rules,
**So that** the public inventory is predictable and does not disclose another tenant's data.

## Acceptance Criteria

- [ ] List accepts public CEL fields using `this.<field>`, offset/limit pagination, and rejects private fields in filters and order expressions with gRPC `InvalidArgument`.
- [ ] List reports the returned size and matching total, and Get uses the immutable system-generated id; metadata name remains a separate RFC 1123 label scoped to tenant/project.
- [ ] Tenant and project visibility excludes unauthorized rows from List and returns gRPC `NotFound` for an unauthorized Get; Cloud Provider Admin visibility spans the permitted tenants.
- [ ] List and Get expose `creating`, `available`, and `deleting` records, omit archived `deleted` records, and apply no additional implicit state filter.
- [ ] Unit/server and Kind component-integration tests cover public and private field filtering, pagination, identifiers, tenant/project isolation, Cloud Provider Admin visibility, and non-archived state behavior.
- [ ] The requested ordering contract is either implemented with the PRD's SQL-like order and implicit ascending id tie-break, or a reviewed source decision updates the approved inputs before implementation proceeds; the current id-only DAO behavior is not silently accepted as complete.

## Implementation Guidance

- Preserve the existing `DefaultTenancyLogic.DetermineVisibleTenants` and DAO visibility predicates in `fulfillment-service/internal/database/dao/generic_dao_request.go`, `generic_dao_get.go`, and `generic_dao_list.go`. A non-visible id must remain indistinguishable from a missing id.
- Configure CEL and order validation against the public Volume descriptor through the public server's filter descriptor. Keep private fields such as `status.backend` outside the public filter surface.
- Account for active and archived storage in `volumes` and `archived_volumes`, including the asynchronous deletion/finalizer behavior described by the approved design.
- Treat the approved design's statement that `generic_dao_list.go` ignores `order` as an explicit source conflict with the PRD's ordering acceptance criterion. Do not resolve that conflict by changing `03-design.md` or `04-testplan.md` in this phase.
- The current baseline already contains the public behavior according to `01-context.md`; implementation ownership must first determine whether this story is missing code, missing assertions, or a verification-only delta.

## Testing Approach

- **Unit/server:** Extend `fulfillment-service/internal/servers/volumes_server_test.go` and related private/DAO tests with the testplan cases for IDs, pagination, public/private filters, visibility, state inclusion, and archival exclusion. Run the repository's documented Ginkgo server/internal commands when implementation is authorized.
- **Component integration:** Extend the existing fulfillment Kind integration path to create through the private API and read through public gRPC, asserting public shape and tenant isolation. The deployed fulfillment service, PostgreSQL, interceptors, and existing inventory are real; external provider behavior is outside this tier.
- **Execution readiness:** The repository documents `make -C ../osac-installer test PLATFORM=kind PROFILE=dev NS=osac SUITE=fulfillment` as the Kind entry point, but it does not identify the focused public Volume invocation. Record that invocation before implementation; no test was run during decomposition.
- **Execution status:** The order case is planned but not execution-ready until the PRD/design conflict is evaluated.

## Dependencies

Story 1.01

## Design Reference

Epic: Epic 1 — Tenant-visible volume inventory read API
PRD Requirements: FR-2, FR-3, FR-4, FR-5, FR-6, FR-8
Design section: Workflow Description, Implementation Details/Notes/Constraints, Failure Handling and Recovery, RBAC / Tenancy, Test Plan
Interface Changes: IC-1, IC-3
Validated by: TC-FR2-01, TC-FR3-01, TC-FR3-02, TC-FR3-03, TC-FR4-01, TC-FR4-02, TC-FR5-02, TC-FR6-01, TC-FR6-02, TC-FR8-01
