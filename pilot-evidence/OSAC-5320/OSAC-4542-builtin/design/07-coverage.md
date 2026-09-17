# Coverage Matrix — OSAC-4542

## Traceability Note

The approved PRD has no formal FR/NFR identifiers. This matrix uses the
document-local `FR-1`–`FR-8` aliases already present in `04-testplan.md`.
The approved design has no formal §5 Interface Changes section; `IC-1`–`IC-3`
are the test plan's local API-extension aliases. These aliases preserve source
traceability and do not add requirements or interfaces.

## PRD Requirement → Epic/Story Mapping

| PRD Requirement | Epic | Stories | Status |
|-----------------|------|---------|--------|
| FR-1: Public read-only Get/List access | Epic 1 | Story 1.01, Story 1.02 | Covered |
| FR-2: Stable ids and tenant-facing names | Epic 1 | Story 1.02 | Covered |
| FR-3: Standard filtering, pagination, and ordering | Epic 1 | Story 1.02 | **GAP — ordering decision required** |
| FR-4: Tenant/project visibility and Cloud Provider Admin access | Epic 1 | Story 1.02, Story 1.03 | Covered with harness gaps |
| FR-5: Public field projection and internal-field hiding | Epic 1 | Story 1.01, Story 1.02 | Covered |
| FR-6: Non-archived states and archived exclusion | Epic 1 | Story 1.02 | Covered |
| FR-7: REST and generic CLI access channels | Epic 1 | Story 1.01, Story 1.03, Story 1.04 | Covered with deployed-harness gap |
| FR-8: Automated coverage and API documentation | Epic 1 | Story 1.02, Story 1.03, Story 1.04 | **GAP — E2E/specification ownership unresolved** |

## Interface Change → Story Mapping

| Local API-extension alias | Approved design surface | Implementing stories | Validating test cases |
|---------------------------|-------------------------|----------------------|------------------------|
| IC-1 | Public gRPC `osac.public.v1.Volumes` Get/List service | Story 1.01, Story 1.02, Story 1.03 | TC-FR1-01, TC-FR1-02, TC-FR2-01, TC-FR3-01, TC-FR3-02, TC-FR3-03, TC-FR4-01, TC-FR4-02, TC-FR6-01, TC-FR6-02, TC-FR7-02, TC-FR8-01 |
| IC-2 | REST transcoding at the public collection and item paths | Story 1.01, Story 1.03 | TC-FR7-01, TC-FR8-02 |
| IC-3 | Public Volume message projection | Story 1.01, Story 1.02, Story 1.03 | TC-FR2-02, TC-FR5-01, TC-FR5-02, TC-FR7-01 |

Every local API-extension alias has at least one implementing story. Formal
§5 coverage cannot be computed because the approved design does not contain
that section.

## Test Case → Story Mapping

All 17 testplan cases have at least one implementing story through the local
IC or requirement aliases.

| Test case | Primary story | Additional story | Boundary / note |
|------------|---------------|------------------|-----------------|
| TC-FR1-01 | Story 1.01 | — | Public gRPC read surface; server/unit coverage |
| TC-FR1-02 | Story 1.01 | — | Public mutation absence and authz denial |
| TC-FR2-01 | Story 1.02 | — | Identifier and name behavior |
| TC-FR2-02 | Story 1.01 | Story 1.02 | Public projection and name constraints |
| TC-FR3-01 | Story 1.02 | — | Pagination and totals |
| TC-FR3-02 | Story 1.02 | — | Public/private CEL boundary |
| TC-FR3-03 | Story 1.02 | — | Blocked by the PRD/design ordering conflict |
| TC-FR4-01 | Story 1.02 | — | Unit/server plus Kind isolation |
| TC-FR4-02 | Story 1.02 | Story 1.03 | Admin visibility; deployed harness remains unresolved |
| TC-FR5-01 | Story 1.01 | — | Generated public schema allowlist |
| TC-FR5-02 | Story 1.01 | Story 1.02 | Public mapping and hidden fields |
| TC-FR6-01 | Story 1.02 | — | Active non-archived states |
| TC-FR6-02 | Story 1.02 | — | Archived exclusion |
| TC-FR7-01 | Story 1.01 | Story 1.03 | REST unit/registration plus deployed REST path |
| TC-FR7-02 | Story 1.01 | Story 1.03 | Reflection-based CLI; manual QE execution |
| TC-FR8-01 | Story 1.02 | Story 1.03 | Kind component integration and external VMaaS E2E realization |
| TC-FR8-02 | Story 1.04 | Story 1.01 | Published API specification; artifact path unresolved |

## Integration and E2E Ownership

| Test case | Required tier | Story owner | Setup dependencies | Ownership status |
|------------|---------------|-------------|--------------------|-----------------|
| TC-FR8-01 — Kind realization | Component integration | Story 1.02 `[DEV]` | `osac-dev` Kind, deployed fulfillment service, PostgreSQL, authn/authz/tenancy interceptors, existing private volume inventory | The environment entry point is documented, but the focused public-read suite invocation is not identified |
| TC-FR8-01 — external realization | E2E | Story 1.03 `[QE]` | External `osac-test-infra` VMaaS suite, volume provisioning path, public API credentials, tenant fixtures | Harness path, command, owner, and availability are unresolved because that workspace was out of scope |
| TC-FR7-01 | Deployed REST/E2E | Story 1.03 `[QE]` | Deployed REST gateway, public handlers, tenant credentials | QE ownership and exact deployed command are unresolved |
| TC-FR7-02 | Manual deployed access | Story 1.03 `[QE]` | CLI binary/version, public reflection, tenant credentials, output capture | Manual procedure and owner are unresolved |
| TC-FR8-02 | Documentation/specification validation | Story 1.04 `[DOCS]` | Generated or published OpenAPI artifact | Local OpenAPI path is absent; owner and validation command are unresolved |

The approved testplan has one `TC-FR8-01` identifier for both the Kind
integration behavior and the design's named external E2E read path. The
decomposition preserves that source identity and records the two-harness
mapping; it does not invent a second test-case id.

## Gaps

- **Ordering contract:** `TC-FR3-03` and Story 1.02 carry the PRD's SQL-like
  ordering requirement, while the approved design says `generic_dao_list.go`
  currently sorts by id regardless of `order`. A source decision or
  implementation evaluation is required before this requirement can be marked
  execution-ready.
- **Baseline implementation status:** `01-context.md` says the current
  baseline already contains the public Volume implementation. The owner must
  determine whether the stories represent missing behavior, missing assertions,
  or a verification/documentation delta before implementation tickets are
  created.
- **Tenant role scope conflict:** The approved PRD and design give Tenant User
  and Tenant Admin the same read scope for this release, while the read-only
  Jira Feature text describes Tenant Users as seeing only their own volumes.
  The approved PRD/design are the decomposition inputs; this conflict requires
  source-owner resolution before the visibility story is finalized.
- **Kind execution readiness:** The documented Kind command starts the
  fulfillment suite, but no focused public Volume invocation is identified.
- **External E2E ownership:** The VMaaS suite, command, credentials, fixtures,
  and owning QE team are outside the permitted workspace and remain unknown.
- **API specification ownership:** The local OpenAPI artifact referenced by
  the fulfillment README is absent, so Story 1.05 cannot name a concrete
  validation command.
- **Registration assertions:** Existing local REST/gRPC registration
  expectation tests omit the public Volume handler/service even though
  production registration includes them. Story 1.01 owns reconciling this
  gap.

## Scenarios Without an Implementing Story

No testplan scenario is entirely unmapped. The following scenarios have
implementing stories but are not execution-ready:

- TC-FR3-03 is blocked by the approved PRD/design ordering conflict.
- The external E2E realization of TC-FR8-01, TC-FR7-01, and TC-FR7-02 lacks a
  confirmed harness owner and command.
- TC-FR8-02 lacks a confirmed specification artifact and validation owner.

## Stories Without PRD Traceability

All stories trace to one or more approved local requirement aliases. Story 1.02
and Story 1.03 are testing work required by FR-4 and FR-8 rather than
unrelated infrastructure; their setup dependencies are recorded above.
