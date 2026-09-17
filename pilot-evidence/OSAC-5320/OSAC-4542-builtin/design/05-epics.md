# Epic Breakdown — OSAC-4542

## Feature

- **Key:** OSAC-4542
- **Title:** Volume Get/List Public API
- **Traceability:** The approved PRD has no formal FR/NFR identifiers. This decomposition carries forward the document-local `FR-1`–`FR-8` aliases from `04-testplan.md`. The approved design has no formal §5 Interface Changes section; `IC-1`–`IC-3` are the test plan's local API-extension aliases.

## Epics

| # | Epic | T-Shirt Size | Stories | PRD Requirements | Dependencies |
|---|------|-------------|---------|-----------------|--------------|
| 1 | [Tenant-visible volume inventory read API](06-stories/epic-1-public-volume-read-api.md) | L | [4 stories](06-stories/epic-1/) | FR-1 through FR-8; see coverage matrix for the full mapping | Existing OSAC-2872 private Volume API and inventory |

## Dependency Order

Epic 1 is the complete user-value slice: it exposes the public read API, preserves the standard visibility and inventory behavior, adds local integration coverage, provides a deployed QE path, and documents the surface. Story 1.01 establishes the public contract and endpoint wiring. Story 1.02 builds the list, visibility, identifier, and lifecycle behavior on that contract. Story 1.03 adds fulfillment Kind coverage, while Story 1.04 validates the deployed user journey when its external harness is available. Story 1.05 can document the stable API surface after Stories 1.01 and 1.02; it does not depend on a new UI implementation.

The external OSAC-2872 inventory/private API is a prerequisite supplied by another feature. No story in this decomposition creates or mutates that dependency.

## Story Implementation Notes

- **Story 1.01** precedes all other stories because it establishes the public Volume contract, public gRPC/REST surface, authorization, and public field projection.
- **Story 1.02** follows 1.01 and owns standard List behavior, tenant/project visibility, identifiers, filters, states, archival, and the unresolved ordering decision.
- **Story 1.02** includes the local Kind component-integration coverage because it owns the behavior and its implementation tests.
- **Story 1.03** depends on the public behavior from 1.01/1.02 and may run once the external VMaaS harness owner and setup are confirmed.
- **Story 1.04** follows 1.01 and 1.02. It can proceed before 1.03, but its published specification path is currently unresolved.

## Sizing Gate

- Jira Feature OSAC-4542 was retrieved read-only. Its Size and Story Points fields are unset, so no feature-level size comparison was available.
- Epic 1 is sized **L** because the slice spans generated protobuf/API surfaces, fulfillment servers, authorization and tenancy, PostgreSQL-backed tests, Kind integration, external E2E ownership, and documentation.
- No epic is sized XXL.
