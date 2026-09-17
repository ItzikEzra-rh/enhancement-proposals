# Story 1.03: [QE] Validate the deployed public Volume read journey

**As a** QE engineer,
**I want** a standalone deployed test path for public Volume reads,
**So that** tenant visibility and public access channels are validated through the user-facing environment.

## Acceptance Criteria

- [ ] The external VMaaS E2E path provisions a standalone volume through the existing path, then retrieves and lists it through the public API.
- [ ] The E2E assertions cover public representation, tenant/project visibility, and gRPC `NotFound` for a caller outside the volume's scope.
- [ ] The deployed REST collection/item paths and generic CLI reflection path are exercised where the owning harness supports them, covering the behavior in `TC-FR7-01` and `TC-FR7-02`.
- [ ] The test reports provider, environment, and harness prerequisites separately from behavioral pass/fail; unavailable external infrastructure is recorded as blocked rather than represented as executed coverage.
- [ ] The story does not duplicate the server unit tests or the Kind component-integration setup from Story 1.02.

## Implementation Guidance

- Add the read-path check to the external `osac-test-infra` VMaaS suite named by the approved design. That workspace was intentionally not inspected during this pilot, so the exact suite path, command, fixture, and owner must be confirmed before implementation.
- Use the existing volume provisioning path as the fixture source and make the public Get/List calls through the deployed API. Assert the public field allowlist and the cross-tenant not-found behavior.
- Include the REST and generic CLI scenarios only if that suite owns those deployed channels; otherwise link the cases to the owning QE harness rather than silently dropping them.
- Keep the external provider boundary explicit. A local Kind test, mocked provider, or unit test cannot satisfy this story's deployed E2E boundary.

## Testing Approach

- **E2E:** External `osac-test-infra` VMaaS suite; concrete command and working directory are unresolved because the external workspace is outside the permitted read scope.
- **Manual/deployed access:** `TC-FR7-02` is marked manual in the test plan and requires the QE owner to define credentials, CLI binary/version, and output capture.
- **Mapped test cases:** `TC-FR8-01` (public Get/List and isolation), `TC-FR7-01` (deployed REST), and `TC-FR7-02` (generic CLI reflection).

## Dependencies

Story 1.01, Story 1.02

## Design Reference

Epic: Epic 1 — Tenant-visible volume inventory read API
PRD Requirements: FR-4, FR-7, FR-8
Design section: Workflow Description, API Extensions, RBAC / Tenancy, Test Plan — E2E Tests
Interface Changes: IC-1, IC-2, IC-3
Validated by: TC-FR7-01, TC-FR7-02, TC-FR8-01
