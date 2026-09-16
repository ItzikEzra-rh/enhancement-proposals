# Testplan — OSAC-4542

## Regeneration controls

- **Mode:** test-plan-only regeneration for confirmation iteration v3.
- **Workflow:** installed `design-test-planning` v0.7.0, with its prepare and
  check-draft rules applied locally.
- **Approved design baseline:** `03-design.md` is a byte-for-byte copy of
  `enhancement-proposals/enhancements/OSAC-4542-volume-get-list/design.md`.
- **Authority:** the approved PRD and approved design are authoritative;
  `01-context.md` supplies the stable clause/assertion IDs and checked-out
  execution evidence. Jira remains read-only context and does not override
  the approved sources.
- **This artifact is a plan, not a result:** no tests, generation, deployment,
  Jira write, decomposition, commit, push, or publication was performed.

## Overview

- **Feature:** OSAC-4542 — Volume Get/List Public API
- **Operation scope:** public `Volumes.List` and `Volumes.Get` only. Private
  fixture operations are setup only; no public Create/Update/Delete operation
  is introduced.
- **Formal requirement labels:** the approved PRD has no `FR-*`/`NFR-*` labels
  and the approved design has no `IC-*` labels. The source-clause and `A-*`
  IDs below are therefore the traceability keys; local case IDs are not new
  product requirements.
- **Planning correctness:** **FLAG** after two check-draft passes. Every
  retained assertion has a concrete expected result or an explicit gap, but
  approved assertions A-09 (name constraints), A-24, and A-25 lack a valid
  in-scope carrier in the checked-out read-only evidence. This is a planning
  testability gap, not a change to the approved contract.
- **Execution readiness:** **Not ready for all cases.** Existing unit/authz
  paths are named; ordering is implementation drift, the schema guard is
  weaker than the approved allowlist, public Kind coverage is proposed, and
  the approved vmaas E2E owner/harness is absent.

## Source-clause ledger

The following rows preserve the clause IDs, source section context, exact
qualifiers, classification, and destination recorded in `01-context.md`.
Background and provenance rows remain visible so that they cannot be mistaken
for behavior; exclusions remain scope rules rather than test cases.

### Approved PRD

| ID | Section / line | Exact source clause | Classification / destination |
|---|---|---|---|
| PRD-PROB-01 | Problem Statement / l12 | “The OSAC storage control plane (OSAC-2872) already provisions standalone storage volumes and tracks them in a central inventory, but that inventory is only reachable through the internal API.” | Background; establishes the existing inventory. |
| PRD-IS-01 | In Scope / l16 | “This release delivers the first, read-only slice of the public Volume API: retrieving individual volumes and listing them. It reuses the volumes already provisioned and inventoried by OSAC-2872 — no new provisioning path is introduced.” | Approved behavior/scope; A-01. |
| PRD-IS-02 | In Scope / l18 | “A user can fetch a single volume and see its tenant-meaningful attributes — name, tier, size, access mode, and current state — so they can confirm its configuration and availability.” | Approved behavior; A-02. |
| PRD-IS-03 | In Scope / l19 | “A user can list the volumes they are entitled to see, consistent with the standard OSAC list contract, so the console and CLI can present and navigate storage inventory.” | Approved behavior; A-03/A-04. |
| PRD-IS-04 | In Scope / l20 | “Each caller sees only the volumes they are entitled to under OSAC's standard tenant- and project-based visibility: a Cloud Provider Admin across all tenants, and tenant members within the tenants and projects visible to them — the same visibility model used by every other OSAC resource.” | Approved behavior/tenancy constraint; A-05/A-06. |
| PRD-IS-05 | In Scope / l21 | “The public view exposes only information that is meaningful to tenants; internal placement and routing details used to serve a volume — the serving backend, its storage protocol, the hub that hosts it, and the vendor-assigned volume identifier — are never shown. Volumes are read-only through this API.” | Approved behavior/exclusion; A-07/A-08. |
| PRD-IS-06 | In Scope / l22 | “Each volume has an immutable, system-generated `id` that `List` returns and `Get` accepts as the request key. `name` is a separate, immutable attribute that is unique within the volume's tenant/project scope (a valid RFC 1123 label), and `display_name` is an optional human-friendly label; neither is the request key. Console deep-links and `Get` requests use `id`.” | Approved identifier/data constraint; A-09/A-10/A-11. |
| PRD-IS-07 | In Scope / l23 | “Volumes are reachable over the same public gRPC and REST endpoints, console, and CLI as other OSAC resources; no storage-specific access path is introduced. CLI support (`osac get volumes`, `osac get volume <id>`) comes for free from the existing `get_cmd.go` / `list_cmd.go` patterns and requires no separate tracking.” | Approved channels and non-test deliverable; A-12. |
| PRD-IS-08 | In Scope / l24 | “Tests cover retrieving and listing standalone volumes through the public API, including tenant-scoped isolation; API documentation and the published API spec are updated with the new read endpoints.” | Deliverables D-01 (tests), D-02 (docs), D-03 (spec); A-28/A-29. |
| PRD-OOS-01 | Out of Scope / l28–35 | “Deferred to later work (this release is read-only Get/List only):” “Volume lifecycle through the public API — creating, updating, and deleting volumes”; “Volume expansion, snapshots, clones, and restore”; “Volume attach / detach”; “Volume identifiability / provenance”; “File storage (NFS/SMB — OSAC-4515) and object storage (S3).” | Explicit exclusion X-01; never add these operations to prove reads. |
| PRD-US-01 | User Stories / Cloud Provider Admin / l38–40 | “As a Cloud Provider Admin, I want to get and list storage volumes across all tenants, so that I have operational visibility for troubleshooting and monitoring.” | Approved persona behavior; A-05. |
| PRD-US-02 | User Stories / Tenant Admin / Tenant User / l42–45 | “As a tenant member, I want to get the details of a specific storage volume — its size, tier, and state” and “list all volumes visible within my tenant and project scope”; “Tenant User and Tenant Admin have the same read scope in this release (both see all volumes in the tenant).” | Approved persona behavior; A-02/A-03/A-06; approved wording supersedes stale Jira text. |
| PRD-US-03 | User Stories / Cloud Infrastructure Admin / l47–49 | “Not affected by this feature.” | Explicit exclusion/background; no behavior to test. |
| PRD-AS-01 | Assumptions / l53–55 | “The volumes to be read already exist and are inventoried by the storage control plane”; “Tenant- and project-scoped visibility is the correct and consistent default”; “The public representation of a volume is a subset of the internal one.” | Design constraints; A-01/A-05/A-07. |
| PRD-DEP-01 | Dependencies / l59–60 | “OSAC-2872 (Storage Control Plane): provides the private Volume API, the volume inventory, and the tier/backend model this read API surfaces. Must be in place for volumes to exist and be retrievable.” “Console UI / UX and UI design gates (OSAC-4546, OSAC-4547): consume this API to present the volume list and detail views; tracked separately.” | Dependency and named downstream deliverable D-04; no UI scope expansion. |
| PRD-AC-BASE | Acceptance Criteria preface / l64 | “`List` inherits the standard OSAC list contract (CEL filtering via `this.<field>`, `offset`/`limit` pagination, SQL-like ordering with implicit secondary sort on `id asc`).” | Approved behavior; A-03/A-04/A-13. |
| PRD-AC-ID | Acceptance Criteria / Identifier / l66 | “`List` items and `Get` both key on the immutable `id`; a `Get` by the `id` of a visible volume returns it, and a `Get` by an id outside the caller's tenants returns `not found` (indistinguishable from a non-existent id, so existence is not leaked across tenants).” | Approved security behavior; A-09/A-10/A-11/A-14. |
| PRD-AC-STATES | Acceptance Criteria / Inventory states / l67 | “`List` and `Get` return volumes in every non-archived state tracked by OSAC-2872 (`creating`, `available`, `deleting`). Once a volume is fully deprovisioned its record is archived (`deleted`) and no longer appears through `List`/`Get`. There is no other implicit state filter — callers filter by `status.state` for a subset.” | Approved lifecycle behavior; A-15/A-16/A-17. |
| PRD-AC-ISO | Acceptance Criteria / Isolation / l68 | “A caller never receives a volume outside their entitled tenants and projects through either `List` or `Get`, and this is covered by automated tenant- and project-isolation tests.” | Approved behavior and test deliverable D-05; A-05/A-06/A-14/A-28. |
| PRD-PROV-01 | Provenance / l72–78 | “Commit-only provenance records PRD 0.9.0 and states authoring phases were not recorded in that snapshot.” | Background/traceability; no product obligation. |

### Approved design

| ID | Section / line | Exact source clause | Classification / destination |
|---|---|---|---|
| DES-SUM-01 | Summary / l20–24 | “Add a read-only public projection of the existing private Volume API: a public `Volumes` service exposing only `List` and `Get` over gRPC and REST at `/api/fulfillment/v1/volumes`.” It “wraps the already-shipped `PrivateVolumesServer`, reusing its DAO, tenancy enforcement, and CEL filtering, and maps private→public so that internal routing fields never leave the service.” | Approved behavior/architecture; A-01/A-07/A-12. |
| DES-MOT-01 | Motivation / l29–33 | “OSAC-2872 delivered the private Volume API, the volume inventory, and tier→backend resolution, but volumes are only reachable through the internal API.” | Background/dependency; no additional contract. |
| DES-GOAL-01 | Goals / l37–43 | Reuse the “public-wraps-private server pattern”; “inherit tenant scoping and CEL filtering”; “expose only tenant-meaningful fields”; “introduce no schema change — reuse the OSAC-2872 `volumes` table.” | Design constraints; A-05/A-07/A-18. |
| DES-NONGOAL-01 | Non-Goals / l47–56 | Lifecycle create/update/delete/resize, expansion/snapshots/clones/restore, attach/detach, identifiability/provenance, file storage, and object storage are deferred or excluded. | Explicit exclusion X-01. |
| DES-PROP-01 | Proposal intro / l60 | “Enumerated changes, all in `fulfillment-service`.” | Deliverable boundary; D-01. |
| DES-PROP-02 | Proposal / Public proto / l62–73 | “Opt the private `Volumes` service and `Volume` type into public generation; expose only `List` and `Get`; strip the internal status fields (`backend`, `protocol`, `hub`, `vendor_volume_id`) by annotating each with `[(cleanapi.field).private = true]` on the private proto — cleanapi excludes annotated fields from the generated public message, so a private field can only reach the public schema if someone both adds it and forgets the annotation. A generated-schema test guards against that.” The private fields also include `vendor_context`, while `StorageProtocol`/`storage_common_type` stay private. | Schema/deliverable; A-07/A-19. |
| DES-PROP-03 | Proposal / Public server / l74–77 | “`Public VolumesServer` ... delegates `List`/`Get` to `PrivateVolumesServer`, maps private→public (dropping internal fields), and sets the CEL filter descriptor to the public `Volume`.” | Architecture/security; A-07/A-18/A-20. |
| DES-PROP-04 | Proposal / Private server adjustment / l78–80 | “make the tier resolver optional (it is used only by `Create`) so the read-only delegate can be built without one; add `SetFilterDesc`.” | Design constraint; A-21. |
| DES-PROP-05 | Proposal / Wiring and authorization / l81–85 | “register the public `Volumes` gRPC service (`register_servers.go`) and REST handler (`start_rest_gateway_cmd.go`)”; “allow tenant clients on the public `Volumes/Get` and `Volumes/List` methods.” | Deliverable/security; A-12/A-22. |
| DES-WF-01 | Workflow Description / l88–101 | Actors are “Tenant User / Tenant Admin” and “Cloud Provider Admin”; volumes already exist. The path is client → REST gateway (REST only) → authn → OPA authz → public server → private server → generic server (tenant scoping + CEL) → DAO → PostgreSQL. | Boundary model; A-05/A-12/A-22. |
| DES-WF-02 | Workflow Description / l103–107 | List is `GET /api/fulfillment/v1/volumes` with optional filter/order/offset/limit; OPA authorizes; private delegate scopes and filters; public server maps and returns items + size + total. Get is by id and returns `NotFound` when id is not visible/absent. | Approved behavior; A-02–A-04/A-10/A-14/A-20. |
| DES-API-01 | API Extensions / l111–121 | Public gRPC `osac.public.v1.Volumes` has `List`/`Get`; REST paths are collection and `/{id}`; public `Volume` is a subset; collection name is resolved as `volumes`; “No CRDs, webhooks, aggregated API servers, or finalizers.” | API deliverable/path/exclusion; A-12/A-19. |
| DES-UX-01 | UX Alignment / l125–136 | `osac-ux` is deprecated; `osac-ui` types are generated from the backend proto via `pnpm gen-types`; the public Volume API is net-new and the UI action after proto merge is regenerating types. | Downstream deliverable D-04; no UI test in this plan. |
| DES-CON-01 | Implementation Details / l140–146 | Private→public mapping uses `GenericMapper` with `SetStrict(false)`; no `inMapper`; `SetFilterDesc((*publicv1.Volume)(nil).ProtoReflect().Descriptor())` limits CEL filters to public fields. | Constraint; A-07/A-18/A-20. |
| DES-CON-02 | Implementation Details / order / l147–156 | The request carries `order`; the generic DAO “currently ignores it and always sorts by `id`”; if ordering is implemented later it must use the public descriptor. The design also states that `order` is validated against the public Volume schema, rejects hidden fields, and documents the current id-sort limitation. | Approved contract plus current drift; A-13. |
| DES-CON-03 | Implementation Details / cleanapi / l157–164 | cleanapi v0.0.8 leaves unused imports; `buf lint (IMPORT_USED)` rejects them; two generated public imports are pruned by hand in the committed state, with tooling automation as a candidate follow-up. | Generation/build constraint; D-06 static check. |
| DES-SEC-01 | Security Considerations / l168–172 | Read-only endpoints; no new secrets or mutation paths; tenancy is existing; routing fields are excluded by public type; input is id and standard list parameters; CEL filters are constrained to public fields. | Security constraints; A-07/A-14/A-20/A-22. |
| DES-FAIL-01 | Failure Handling and Recovery / l176–182 | Not found/not visible: Get `NotFound`, List excludes invisible rows; invalid CEL filter/order: `InvalidArgument`; mapping error: `Internal` with no partial data; delegate/DB errors propagate; reads are idempotent with no retries or side effects. | Approved negative behavior; A-14/A-20/A-23–A-25. |
| DES-RBAC-01 | RBAC / Tenancy / l186–207 | OPA gates method access; row scoping is inherited from `GenericServer`/`GenericDAO` and `DefaultTenancyLogic.DetermineVisibleTenants`; Tenant User and Tenant Admin both see their tenant(s) plus `shared`; Cloud Provider Admin sees all; unauthenticated is denied; no public mutating methods exist. | Authorization/isolation; A-05/A-06/A-14/A-22/A-26. |
| DES-OBS-01 | Observability / l211–212 | “No new observability changes. Existing gRPC metrics, structured request logging, and the interceptor chain apply to the new methods automatically.” | Background/constraint; no new deliverable. |
| DES-RISK-01 | Risks and Mitigations / l216–218 | cleanapi unused imports can make `buf lint` fail; mitigation is documented pruning and a possible tooling follow-up. | Background/generation risk. |
| DES-DRAW-01 | Drawbacks / l222–223 | “Read-only is a partial capability — the console can display but not manage volumes until later phases.” | Background/scope reminder. |
| DES-ALT-01 | Alternatives (Not Implemented) / l227–235 | Hand-written public proto, exposing `protocol`, and publishing an empty `storage_common_type` are each rejected. | Explicit design exclusions X-03. |
| DES-OQ-01 | Open Questions / l237–239 | “None.” | Approved source has no product question; planning gaps below are evidence gaps. |
| DES-TP-01 | Test Plan / Unit Tests / l243–264 | “Public `Get` returns the public projection; `List` returns items with size/total.” “Field mapping: public `Volume` carries spec (tier/size/access mode) and status (state/message); internal fields are absent by type.” “The generated-schema guard test uses an exact-field allowlist: it asserts the public `Volume` descriptor contains precisely the expected set of fields (`id`, `metadata`, `spec.storage_tier`, `spec.size_gib`, `spec.access_mode`, `status.state`, `status.message`).” The section also requires public/private CEL filtering, nonexistent Get, authz allow/deny, and private-server resolver behavior. | Unit deliverable/assertions A-02–A-04/A-07/A-19–A-22/A-27. |
| DES-TP-02 | Test Plan / Integration Tests / l265–269 | “Against the kind `osac-dev` cluster: list/get standalone volumes created via the private path through the public gRPC endpoint, asserting the public shape and tenant scoping (a subject in tenant A does not see tenant B's volumes).” | Integration deliverable; A-28. |
| DES-TP-03 | Test Plan / E2E Tests / l270–273 | “Add a read-path check to the osac-test-infra vmaas suite: provision a volume via the existing path, then Get/List it through the public API and assert the public representation and tenant-scoped visibility.” | E2E deliverable; A-29; infrastructure absent. |
| DES-LIFE-01 | Graduation Criteria / l275–279 | Ships with public Volume API 0.3; no separate maturity ladder; later OSAC-984 phases add lifecycle mutations. | Release/background/exclusion X-01. |
| DES-UP-01 | Upgrade / Downgrade / l281–285 | Additive read-only API with no schema change; upgrade adds endpoints, downgrade removes them, and existing clients need not change. | Compatibility constraint; A-30. |
| DES-SKEW-01 | Version Skew / l287–292 | Public API is generated from private and served by the same process; older console does not call new endpoints; public Volume is a strict subset and follows additive proto evolution. | Compatibility constraint; A-07/A-30. |
| DES-SUPPORT-01 | Support Procedures / l294–300 | Failures surface as standard `NotFound`, `InvalidArgument`, `PermissionDenied`, and `Internal`; removing public OPA allowlist entries effectively disables read access without affecting provisioning/workloads. | Operational behavior; A-23–A-26. |
| DES-INFRA-01 | Infrastructure Needed / l302–304 | “None.” | Approved source says no new infrastructure deliverable; existing prerequisites remain readiness concerns. |
| DES-PROV-01 | Provenance / l308–314 | “Commit-only provenance records design 0.9.0 and states authoring phases were not recorded in that snapshot.” | Background/traceability. |

## Current implementation and drift (not the test oracle)

The approved PRD/design remain the oracle. These checked-out observations are
implementation or evidence status only:

| Area | Current implementation/evidence | Classification |
|---|---|---|
| Public shape and wiring | Public proto, `VolumesServer`, gRPC registration, and REST registration for List/Get exist; mapping delegates through the private server. | Current implementation matching A-01/A-12/A-18. |
| Projection/filter | `GenericMapper` uses non-strict private→public mapping; public descriptor is passed to CEL; current unit coverage rejects `status.backend`. | Current implementation matching A-07/A-20, with exact-schema evidence still needed. |
| Tenancy/hidden Get | Generic DAO applies tenant/project visibility before id lookup and translates invisible Get to not-found. | Current path matching A-05/A-11/A-14; deployed public evidence absent. |
| Ordering | `fulfillment-service/internal/database/dao/generic_dao_list.go` forces `const order = "id"` and ignores request order. | Implementation drift against A-04/A-13; never an expected result. |
| Schema guard | `volumes_server_test.go` rejects four private names but does not assert the exact seven-field allowlist and omits `vendor_context`. | Test/evidence drift against A-19/A-27; GAP-SCHEMA. |
| Integration/E2E | `fulfillment-service/it/it_volume_lifecycle_test.go` is private-only; no public Volume read case exists; `osac-test-infra` is absent. | Missing boundary evidence against A-28/A-29; GAP-KIND/GAP-E2E. |
| Documentation/spec | Approved design requires API documentation and published spec updates; no proof artifact was available in this read-only scope. | Deliverable gap GAP-DOCS, not a product ambiguity. |

## Stable assertion checklist

Every stable assertion from `01-context.md` is retained. A result reference is
an exact Expected Results bullet below; a `GAP-*` reference is an explicit
testability gap naming the missing carrier and owner. Current implementation
differences are labelled drift and never substituted for the approved result.

| ID | Approved obligation and source clauses | Valid carrier / result or gap |
|---|---|---|
| A-01 | Read-only public List/Get over existing inventory; PRD-IS-01, DES-SUM-01, DES-API-01 | TC-UNIT-01, TC-KIND-01; ER-UNIT-01-01/ER-KIND-01-01. |
| A-02 | Get exposes name, tier, size, access mode, state; PRD-IS-02, PRD-US-02, DES-TP-01 | TC-UNIT-01; ER-UNIT-01-02. |
| A-03 | List returns entitled items and size/total/items; PRD-IS-03, DES-WF-02, DES-TP-01 | TC-UNIT-01; ER-UNIT-01-03. |
| A-04 | CEL `this.<field>`, offset/limit, standard order; PRD-AC-BASE, DES-WF-02 | TC-UNIT-02; ER-UNIT-02-01/02/03/04. Ordering execution is blocked by drift. |
| A-05 | Cloud Provider Admin all tenants; tenant members visible tenant/project scope; PRD-IS-04, PRD-US-01, DES-RBAC-01 | TC-KIND-01; ER-KIND-01-02/03. |
| A-06 | Tenant User/Admin have identical read scope; PRD-US-02, DES-RBAC-01 | TC-KIND-01; ER-KIND-01-04. |
| A-07 | No backend/protocol/hub/vendor id/vendor context in public projection; PRD-IS-05, DES-PROP-02, DES-CON-01 | TC-UNIT-01/03; ER-UNIT-01-02/ER-SCHEMA-01-01. |
| A-08 | No public create/update/delete/resize/attach/detach path; PRD-IS-05, PRD-OOS-01, DES-NONGOAL-01 | TC-AUTH-01/static descriptor; ER-AUTH-01-03. |
| A-09 | Immutable system id is only Get key; name separately immutable RFC1123 scoped-unique; display optional; PRD-IS-06, PRD-AC-ID | id/key: TC-UNIT-01/04; name constraints: GAP-09 (read-only scope has no valid carrier). |
| A-10 | Visible id Get succeeds; PRD-AC-ID, DES-WF-02 | TC-UNIT-01; ER-UNIT-01-01. |
| A-11 | Outside-scope id is indistinguishable NotFound; PRD-AC-ID, PRD-AC-ISO, DES-FAIL-01 | TC-KIND-01/TC-ERROR-01; ER-KIND-01-05/ER-ERROR-01-01. |
| A-12 | Standard gRPC/REST paths, no storage-specific path; PRD-IS-07, DES-SUM-01, DES-API-01 | TC-WIRE-01; ER-WIRE-01-01/02. CLI is inherited pattern, not a new path. |
| A-13 | Public-field order validation and SQL-like order with implicit id asc tie-break; current id-only DAO is drift; PRD-AC-BASE, DES-CON-02 | TC-UNIT-02; ER-UNIT-02-03/04; execution gap GAP-13. |
| A-14 | List/Get never return outside entitlement; PRD-AC-ID, PRD-AC-ISO, DES-RBAC-01 | TC-KIND-01; ER-KIND-01-02/05. |
| A-15 | creating/available/deleting are returned; PRD-AC-STATES | TC-KIND-02; ER-KIND-02-01/02/03. |
| A-16 | archived/deleted absent; PRD-AC-STATES | TC-KIND-02; ER-KIND-02-04. |
| A-17 | No implicit state filter; caller filters `status.state`; PRD-AC-STATES, DES-WF-02 | TC-KIND-02/TC-UNIT-02; ER-KIND-02-05/ER-UNIT-02-01. |
| A-18 | Public wraps private/DAO and reuses tenancy/CEL; no new path/schema; DES-SUM-01, DES-GOAL-01, DES-PROP-03 | TC-WIRE-01/TC-STATIC-01; ER-WIRE-01-03/ER-STATIC-01-01. |
| A-19 | Exact public allowlist of seven fields; DES-PROP-02, DES-TP-01 | TC-SCHEMA-01; ER-SCHEMA-01-01; current guard drift GAP-SCHEMA. |
| A-20 | Public filter succeeds; hidden filter is InvalidArgument; DES-PROP-03, DES-CON-01, DES-FAIL-01, DES-TP-01 | TC-UNIT-02/TC-ERROR-01; ER-UNIT-02-01/ER-ERROR-01-02. |
| A-21 | Read delegate builds without tier resolver; private Create without resolver fails; DES-PROP-04, DES-TP-01 | TC-PRIVATE-01; ER-PRIVATE-01-01/02. Private setup is not a public mutation. |
| A-22 | Tenant clients allowed List/Get; unauthenticated/public mutations denied; DES-PROP-05, DES-SEC-01, DES-RBAC-01, DES-TP-01 | TC-AUTH-01; ER-AUTH-01-01/02/03. |
| A-23 | Invalid filter/order InvalidArgument; DES-FAIL-01, DES-SUPPORT-01 | TC-ERROR-01; ER-ERROR-01-02/03; order execution GAP-13. |
| A-24 | Mapping failure Internal with no partial data; DES-FAIL-01 | GAP-24: no approved fault-injection fixture in checked-out scope; owner fulfillment-service test owner. |
| A-25 | Delegate/DB errors propagate; read idempotent/no retries/side effects; DES-FAIL-01 | GAP-25: no approved delegate/DB fault harness; owner fulfillment-service test owner. |
| A-26 | Standard NotFound/InvalidArgument/PermissionDenied/Internal surface; DES-FAIL-01, DES-SUPPORT-01 | TC-ERROR-01/TC-AUTH-01 plus GAP-24; ER-ERROR-01-01/02/ER-AUTH-01-02. |
| A-27 | Keep independent unit assertions separate; DES-TP-01 | TC-UNIT-01/02/03/ERROR/AUTH; each has separate ER bullets; ER-AUDIT-01. |
| A-28 | Kind private-create/inventory → public gRPC shape and isolation; DES-TP-02 | TC-KIND-01/02; ER-KIND-01-01..05/ER-KIND-02-01..05; proposed work. |
| A-29 | vmaas provisioning → public Get/List shape and visibility; DES-TP-03 | TC-E2E-01; ER-E2E-01-01/02; infrastructure GAP-E2E. |
| A-30 | Additive/read-only, same-process generated contract, no migration, old clients continue; DES-UP-01, DES-SKEW-01 | TC-STATIC-01; ER-STATIC-01-01..04. |

## Test Cases

### Proof carriers and scope

Private Create/Update/Delete calls below are fixture/setup mechanisms already
used by the approved private lifecycle harness. They are not public operations
and do not expand this read-only plan.

### TC-UNIT-01 — public projection and List envelope

| Interface Change | Priority | Automation |
|---|---|---|
| API-01 (derived from DES-API-01: public gRPC List/Get) | critical | automated |

**Tier/boundary:** Unit/component-local; public server mapper and generic List/Get
against a real PostgreSQL test container, with auth attribution/tenancy mocked.

**Preconditions:** Use the existing `volumes_server_test.go` fixture with an
approved private inventory row containing all tenant-visible values and private
routing values. Invoke only public Get/List.

**Steps:**

1. Call public Get with the fixture's returned immutable id.
2. Call public List for the fixture's entitled scope.

**Expected Results:**

- **ER-UNIT-01-01 (A-01, A-10):** Get returns the fixture row for the supplied visible `id`; the response contains no create/update/delete operation.
- **ER-UNIT-01-02 (A-02, A-07):** Get contains `metadata.name`, `spec.storage_tier`, `spec.size_gib`, `spec.access_mode`, `status.state`, and `status.message`, and contains none of `status.backend`, `status.protocol`, `status.hub`, `status.vendor_volume_id`, or `status.vendor_context`.
- **ER-UNIT-01-03 (A-03):** List returns an `items` entry for each entitled fixture row and its `size` and `total` values equal the observed result set counts.
- **ER-UNIT-01-04 (A-09):** The Get request schema contains the immutable `id` as its resource key; `metadata.name` and the optional display label are response fields, not request keys.

**Readiness:** Existing suite path; fixture/projection case exists, but exact
schema evidence is strengthened separately in TC-SCHEMA-01.

### TC-UNIT-02 — public filter, pagination, and approved ordering

| Interface Change | Priority | Automation |
|---|---|---|
| API-01 | critical | automated |

**Tier/boundary:** Unit/component-local public List against the generic DAO;
assertion is public request/response, not SQL internals.

**Preconditions:** Approved private fixture has at least three entitled rows
with different visible `status.state` values and a tie on the primary order
field; fixture ids are known so the expected `id asc` tie-break can be stated.

**Steps:**

1. List with `filter = "this.status.state == 'available'"`.
2. List with `offset` and `limit` selecting a strict page.
3. List with an approved visible-field order expression and inspect the full returned sequence.
4. List with a hidden-field order expression.

**Expected Results:**

- **ER-UNIT-02-01 (A-04, A-17, A-20):** The state CEL expression returns only rows whose visible `status.state` is `available`; no row is removed by an implicit state filter when no filter is supplied.
- **ER-UNIT-02-02 (A-04):** The response contains exactly the requested `limit` rows after the requested `offset`, and `size`/`total` describe the filtered collection according to the standard list response.
- **ER-UNIT-02-03 (A-04, A-13):** A valid public-field order expression is accepted and rows are in that SQL-like order; equal primary keys are ordered by increasing immutable `id` (`id asc`).
- **ER-UNIT-02-04 (A-13, A-23):** An order expression naming a field absent from the public Volume descriptor returns `InvalidArgument` and no partial item list.

**Drift note:** `generic_dao_list.go` currently forces `id` ordering and does
not validate/translate request order. That is implementation drift, never the
expected result. The case is planned but not execution-ready until the DAO and
public validation path satisfy ER-UNIT-02-03/04 (GAP-13).

### TC-SCHEMA-01 — generated public exact allowlist

| Interface Change | Priority | Automation |
|---|---|---|
| API-03 (derived from DES-PROP-02 and DES-TP-01) | critical | automated |

**Tier/boundary:** Static/artifact check over the generated public protobuf
descriptor; no service call or mutation is needed.

**Preconditions:** Generated public descriptor is available from the checked-out
`proto/public`/`proto/gen` source. The owning generator is `make -C proto generate`
and validation is `make -C proto lint`; neither is run in this phase.

**Steps:** Inspect the public `Volume` descriptor recursively, including nested
`metadata`, `spec`, and `status` messages.

**Expected Results:**

- **ER-SCHEMA-01-01 (A-07, A-19, A-27):** The descriptor contains exactly `id`, `metadata`, `spec.storage_tier`, `spec.size_gib`, `spec.access_mode`, `status.state`, and `status.message`; it contains no backend, protocol, hub, vendor volume id, or vendor context field.

**Readiness:** Proposed correction to the current guard. Existing guard rejects
four names and omits `vendor_context`; it does not prove the exact allowlist
(GAP-SCHEMA), so current evidence is drift.

### TC-ERROR-01 — not-found and invalid-input surfaces

| Interface Change | Priority | Automation |
|---|---|---|
| API-01 | high | automated |

**Tier/boundary:** Unit/component-local public server and filter translator;
tenant isolation for an outside id is separately exercised at Kind boundary.

**Preconditions:** Existing nonexistent-id and invalid-CEL fixtures; Kind case
provides a second tenant's id. No operation is added to manufacture an error.

**Steps:** Call Get for an absent id; call List with a hidden CEL field; call
List with an invalid order expression; call Get for the other tenant's id in
TC-KIND-01.

**Expected Results:**

- **ER-ERROR-01-01 (A-11, A-26):** Get for an absent id returns gRPC/REST `NotFound`.
- **ER-ERROR-01-02 (A-20, A-23, A-26):** A CEL filter naming `status.backend` returns `InvalidArgument` and no response items.
- **ER-ERROR-01-03 (A-13, A-23):** An invalid public order expression returns `InvalidArgument`; it is not treated as id-only success.
- **ER-ERROR-01-04 (A-11, A-14, A-26):** Get for an id belonging to a tenant outside the caller's visible scope returns the same `NotFound` status and externally observable shape as an absent id.

**Gaps:** Mapping `Internal` and delegate/DB propagation are retained as
GAP-24/GAP-25 rather than forcing an invented failure setup.

### TC-AUTH-01 — method authorization and mutation exclusion

| Interface Change | Priority | Automation |
|---|---|---|
| API-04 (derived from DES-PROP-05 and DES-RBAC-01) | critical | automated |

**Tier/boundary:** Unit authz/interceptor and static service descriptor; this
does not claim deployed identity-provider coverage.

**Preconditions:** Existing Rego/interceptor fixture with tenant client and
unauthenticated subjects; public service descriptor is available.

**Steps:** Evaluate public Get/List for a tenant client; evaluate the same
methods unauthenticated; inspect the public Volumes service methods and policy.

**Expected Results:**

- **ER-AUTH-01-01 (A-22):** An authenticated tenant client is authorized for public `Volumes/Get` and `Volumes/List`.
- **ER-AUTH-01-02 (A-22, A-26):** An unauthenticated caller receives `PermissionDenied`/the repository's specified unauthenticated denial for the public read methods.
- **ER-AUTH-01-03 (A-08, A-22):** The public service descriptor and allowlist contain no public Create, Update, Delete, Resize, Attach, or Detach method; those operations remain private/out of scope.

### TC-PRIVATE-01 — read delegate construction

| Interface Change | Priority | Automation |
|---|---|---|
| — | high | automated |

**Tier/boundary:** Unit `private_volumes_server_test.go`; internal constructor
behavior only.

**Preconditions:** Existing private server test fixture can construct the
read-only delegate without a tier resolver and can exercise the Create path's
resolver guard without exposing a public mutation method.

**Steps:** Construct the public read delegate without a resolver; separately
exercise the existing private Create constructor guard.

**Expected Results:**

- **ER-PRIVATE-01-01 (A-18, A-21):** The read-only delegate is constructed without a tier resolver and delegates List/Get through the existing private/generic path.
- **ER-PRIVATE-01-02 (A-21):** The private Create path refuses construction/use without its required resolver; this is an internal guard, not a public API operation.

### TC-WIRE-01 — standard gRPC and REST registration

| Interface Change | Priority | Automation |
|---|---|---|
| API-02 (derived from DES-API-01) | high | automated |

**Tier/boundary:** Static/artifact registration check over service startup and
generated route descriptors.

**Preconditions:** Source files named by the context are checked out; no
deployment is required.

**Steps:** Inspect gRPC registration, REST gateway registration, generated
service methods, and route annotations.

**Expected Results:**

- **ER-WIRE-01-01 (A-12):** `osac.public.v1.Volumes` exposes only List/Get, with collection path `/api/fulfillment/v1/volumes` and item path `/api/fulfillment/v1/volumes/{id}`.
- **ER-WIRE-01-02 (A-12):** Both public gRPC registration and REST handler registration refer to the public Volumes service; no storage-specific alternate path is present.
- **ER-WIRE-01-03 (A-18, A-30):** The public handlers delegate to the existing private/generic path in the same process and do not add a second persistence/schema path.

### TC-KIND-01 — public gRPC tenant/project boundary

| Interface Change | Priority | Automation |
|---|---|---|
| API-01 | critical | automated |

**Tier/boundary:** Component Integration/Kind; real deployed fulfillment,
PostgreSQL, Keycloak/auth, gateway/interceptors, and public gRPC endpoint.

**Preconditions:** Extend `fulfillment-service/it/` using the existing private
fixture setup to create/inventory rows in tenant A and tenant B. Use Tenant User,
Tenant Admin, and Cloud Provider Admin subjects. No public mutation is used.

**Steps:** Each subject calls public List; tenant subjects call Get for their
visible id and the other tenant's id; the provider admin calls List.

**Expected Results:**

- **ER-KIND-01-01 (A-01, A-28):** A volume created through the approved private fixture is retrievable through public gRPC Get and its response has the public seven-field shape.
- **ER-KIND-01-02 (A-05, A-14, A-28):** A Tenant User's List contains only rows in its entitled tenant/project scope and contains no tenant B row.
- **ER-KIND-01-03 (A-05, A-28):** A Cloud Provider Admin's List contains rows from both tenant A and tenant B.
- **ER-KIND-01-04 (A-06, A-28):** Tenant User and Tenant Admin calls over the same tenant return the same entitled row set.
- **ER-KIND-01-05 (A-11, A-14, A-28):** Tenant A Get for tenant B's id returns indistinguishable `NotFound`, matching Get for a nonexistent id.

**Execution:** Proposed extension of the existing Kind suite; the command is
defined by `osac-installer/Makefile` but this public case does not yet exist.

### TC-KIND-02 — public lifecycle-state visibility

| Interface Change | Priority | Automation |
|---|---|---|
| API-01 | high | automated |

**Tier/boundary:** Component Integration/Kind, same real services as TC-KIND-01;
private lifecycle actions are setup and public List/Get are observations.

**Preconditions:** Extend the existing private lifecycle fixture to observe a
volume while it is `creating`, `available`, and `deleting`, then after its
record is archived as `deleted`.

**Steps:** At each fixture state call public List/Get without a state filter;
then call List with `this.status.state` for a subset.

**Expected Results:**

- **ER-KIND-02-01 (A-15):** Public List/Get returns the volume while `status.state` is `creating`.
- **ER-KIND-02-02 (A-15):** Public List/Get returns the volume while `status.state` is `available`.
- **ER-KIND-02-03 (A-15):** Public List/Get returns the volume while `status.state` is `deleting`.
- **ER-KIND-02-04 (A-16):** After full deprovisioning archives the record as `deleted`, public List omits it and public Get returns `NotFound`.
- **ER-KIND-02-05 (A-17):** Without a state filter all non-archived states remain eligible; with `this.status.state == 'available'`, only available rows are returned.

### TC-E2E-01 — existing provisioning to public read path

| Interface Change | Priority | Automation |
|---|---|---|
| API-01 | high | automated |

**Tier/boundary:** E2E across the approved vmaas provisioning path and public
API, as required by DES-TP-03.

**Preconditions:** Named `osac-test-infra` vmaas owner provides the existing
provisioning fixture, command, credentials, and tenant subjects.

**Steps:** Provision a standalone volume through the existing path; call public
Get and List; repeat visibility check from an unrelated tenant.

**Expected Results:**

- **ER-E2E-01-01 (A-29):** The provisioned volume is returned by public Get/List with only the approved tenant-meaningful fields.
- **ER-E2E-01-02 (A-29):** A caller outside the volume's entitled tenant/project scope cannot observe it through public Get/List.

**Readiness:** Blocked: the `osac-test-infra` checkout and authoritative
command/owner are absent (GAP-E2E). No guessed command is presented.

### TC-STATIC-01 — additive/schema/skew artifact check

| Interface Change | Priority | Automation |
|---|---|---|
| API-03 | high | automated |

**Tier/boundary:** Static/build artifact review; generated proto source and
service descriptors, not a deployment.

**Preconditions:** Inspect editable private proto, committed generated public
and Go trees, database migration set, and same-process registrations.

**Steps:** Compare public/private generated descriptors and inspect migration
and registration diffs for the feature.

**Expected Results:**

- **ER-STATIC-01-01 (A-18, A-30):** The public Volume descriptor is generated from the private source and is a strict subset; no second data path or new schema is introduced.
- **ER-STATIC-01-02 (A-30):** The feature adds public read endpoints without a database migration; existing private clients retain their prior descriptors and methods.
- **ER-STATIC-01-03 (A-30):** An older client that does not call the new endpoints remains compatible with the unchanged existing methods.
- **ER-STATIC-01-04 (A-08):** No public mutation method, CRD, webhook, aggregated API server, or finalizer is added.

## Explicit testability gaps

These are not silently dropped requirements and are not product decisions:

| Gap | Preserved assertion | Missing carrier/check and owner |
|---|---|---|
| GAP-09 | A-09 name immutability, RFC 1123 validity, tenant/project uniqueness, and optional display name | Read-only public List/Get cannot establish creation/update invariants. Need an approved private-fixture/artifact check owned by fulfillment-service; do not add a public mutation. |
| GAP-13 | A-13 ordered result and invalid order rejection | Current DAO forces `id` order and lacks the approved public order validation path. Owner: fulfillment-service implementation/test owner; repair before running TC-UNIT-02. |
| GAP-24 | A-24 mapping `Internal` with no partial data | No approved mapper fault-injection fixture or named harness exists in this checkout. Owner: fulfillment-service test owner; add a separate delegate/mapper fault setup. |
| GAP-25 | A-25 delegate/DB error propagation and no retries/side effects | No approved delegate/DB fault harness exists in this checkout. Owner: fulfillment-service test owner; add a separate dependency-failure setup. |
| GAP-SCHEMA | A-19/A-27 exact allowlist evidence | Current guard checks four forbidden names and omits `vendor_context`; add the exact descriptor allowlist check in `volumes_server_test.go`. Owner: fulfillment-service/proto test owner. |
| GAP-KIND | A-05/A-06/A-14/A-28 and A-15–A-17 | Existing Kind suite is private lifecycle only; add public gRPC cases in `fulfillment-service/it/`. Owner: fulfillment-service integration owner. |
| GAP-E2E | A-29 | `osac-test-infra` vmaas checkout, command, credentials, and owner are unavailable. Owner: osac-test-infra/vmaas maintainer. |
| GAP-DOCS | PRD-IS-08 / D-02/D-03 | Approved design requires API documentation and published API spec updates; no artifact/command was available in the read-only planning scope. Owner: fulfillment-service documentation/spec owner. |

## Gaps

### Requirement coverage gaps

The approved PRD defines no formal `FR-*` or `NFR-*` requirement labels. Its
Problem Statement, In Scope, Out of Scope, User Stories, Assumptions,
Dependencies, Acceptance Criteria, and Provenance sections are all accounted
for in the source ledger. The explicit proof gaps above retain the affected
assertion IDs and owners; no PRD obligation is silently omitted.

### Interface-change coverage gaps

The approved design defines API surfaces but assigns no `IC-*` labels. The
local derived surfaces used in case metadata are:

| Local surface | Approved design source | Covered by |
|---|---|---|
| API-01 public gRPC `Volumes.List`/`Get` | DES-SUM-01, DES-API-01 | TC-UNIT-01/02, TC-ERROR-01, TC-KIND-01/02, TC-E2E-01 |
| API-02 REST collection/item routes | DES-PROP-05, DES-API-01 | TC-WIRE-01 |
| API-03 generated public `Volume` schema | DES-PROP-02, DES-TP-01 | TC-SCHEMA-01, TC-STATIC-01 |
| API-04 OPA method authorization | DES-PROP-05, DES-RBAC-01 | TC-AUTH-01 |

All four local surfaces have cases. API documentation/spec completion remains
GAP-DOCS; it is a deliverable gap, not an invented interface.

## Execution-evidence table

The rows distinguish assertion tier from suite setup and do not claim that any
case ran.

| Evidence row / behavior and cases | Tier and boundary | Test location | Execution command, cwd, prerequisites, defining source | Dependencies | Readiness / gap |
|---|---|---|---|---|---|
| E-UNIT: projection, List envelope, filters, errors — TC-UNIT-01/02, TC-ERROR-01 | Unit/component-local; public server/DAO response; DB setup is not a deployed boundary | Existing `fulfillment-service/internal/servers/volumes_server_test.go`, `private_volumes_server_test.go` | Existing `cd fulfillment-service && ginkgo run internal/servers`; component AGENTS and `servers_suite_test.go`; container runtime and dependencies required | Real PostgreSQL test container; auth/tenancy mocked; no gateway/OPA | Existing path; exact schema and order checks proposed. GAP-13/GAP-SCHEMA/GAP-24/GAP-25. |
| E-AUTH: method allow/deny — TC-AUTH-01 | Unit authz/interceptor; policy boundary, not deployed identity | `fulfillment-service/internal/auth/grpc_authz_interceptor_test.go`, `auth/policies/authz.rego` | `cd fulfillment-service && ginkgo run -r internal` (or focused package); command from component guidance | Rego/interceptor in process; no IdP/deployed gateway | Existing method-level evidence; no row-isolation proof. |
| E-PRIVATE: resolver/delegate — TC-PRIVATE-01 | Unit internal constructor | `fulfillment-service/internal/servers/private_volumes_server_test.go` | Included in `cd fulfillment-service && ginkgo run internal/servers` | In-process private fixture | Existing path named; no public mutation. |
| E-WIRE: gRPC/REST/proto registration — TC-WIRE-01 | Static/build artifact | `register_servers.go`, `start_rest_gateway_cmd.go`, generated route/service descriptors | Static inspection; generation command `make -C proto generate` and lint `make -C proto lint` are defined but not run | Generated outputs and source descriptors | Existing wiring evidence; API documentation gap GAP-DOCS. |
| E-SCHEMA: exact public descriptor — TC-SCHEMA-01/TC-STATIC-01 | Static/artifact/schema, not integration | `proto/private/.../volume_type.proto`, `proto/public/...`, `proto/gen/...`, proposed schema assertion in `volumes_server_test.go` | `make -C proto generate`; `make -C proto lint` (future execution only) | Generator and buf toolchain; no DB | Proposed exact check; GAP-SCHEMA. |
| E-KIND: deployed public gRPC shape/isolation/state — TC-KIND-01/02 | Component Integration/Kind; public endpoint through authn/authz/gateway/service/DB | Proposed extension under `fulfillment-service/it/`, based on `it_volume_lifecycle_test.go` | `make -C osac-installer test PLATFORM=kind PROFILE=dev NS=osac SUITE=fulfillment`; Makefile defines image build/load, install, CRDs, and `ginkgo run --timeout 1h -v it` | Real Kind, runtime, Helm, PostgreSQL, Keycloak, Envoy, credentials; private fixture setup | Command exists, cases do not. GAP-KIND; no execution claimed. |
| E-E2E: provision-to-public read — TC-E2E-01 | E2E across provider/provisioning and public API | Proposed `osac-test-infra` vmaas suite per DES-TP-03 | No command is available; do not invent one | External vmaas backend, provisioning, tenant credentials | Blocked; GAP-E2E. |
| E-COMPAT: additive/skew — TC-STATIC-01 | Static artifact; generated contract and migrations | Proto trees, service descriptors, migration set | Static review; no tests/generation run | Same-process generated public/private contract | Planned static evidence; no migration expected. |

## Assertion-to-result audit

Each row quotes the decisive Expected Results wording, not merely a case or
fixture link. “Preserved” means the approved result is concrete; readiness may
still be blocked. “Unresolved source contract” is used only where the
read-only scope has no valid carrier and the explicit gap names the missing
evidence.

- **ER-AUDIT-01 (A-27):** The audit below gives every atomic assertion its
  source clause, exact decisive Expected Results bullet (or named gap), and a
  verdict; independent projection, schema, filter, authorization, lifecycle,
  and error observations are not collapsed into one compatibility statement.

| Assertion | Source clause(s) | Exact result reference and decisive wording | Verdict |
|---|---|---|---|
| A-01 | PRD-IS-01, DES-SUM-01, DES-API-01 | ER-UNIT-01-01: “Get returns the fixture row ...”; ER-KIND-01-01: “retrievable through public gRPC Get” | Preserved; Kind execution pending. |
| A-02 | PRD-IS-02, PRD-US-02, DES-TP-01 | ER-UNIT-01-02: “contains `metadata.name`, `spec.storage_tier`, `spec.size_gib`, `spec.access_mode`, `status.state`, and `status.message`” | Preserved. |
| A-03 | PRD-IS-03, DES-WF-02, DES-TP-01 | ER-UNIT-01-03: “`size` and `total` values equal the observed result set counts” | Preserved. |
| A-04 | PRD-AC-BASE, DES-WF-02 | ER-UNIT-02-01: “only rows whose visible `status.state` is `available`”; ER-UNIT-02-02: “exactly the requested `limit` rows”; ER-UNIT-02-03: “rows are in that SQL-like order” | Preserved; order portion blocked by GAP-13. |
| A-05 | PRD-IS-04, PRD-US-01, DES-RBAC-01 | ER-KIND-01-02: “only rows in its entitled tenant/project scope”; ER-KIND-01-03: “rows from both tenant A and tenant B” | Preserved; proposed Kind carrier. |
| A-06 | PRD-US-02, DES-RBAC-01 | ER-KIND-01-04: “Tenant User and Tenant Admin ... return the same entitled row set” | Preserved; proposed Kind carrier. |
| A-07 | PRD-IS-05, DES-PROP-02, DES-CON-01 | ER-UNIT-01-02: “contains none of `status.backend` ... `status.vendor_context`”; ER-SCHEMA-01-01: “contains no backend, protocol, hub, vendor volume id, or vendor context field” | Preserved; exact schema evidence pending. |
| A-08 | PRD-IS-05, PRD-OOS-01, DES-NONGOAL-01 | ER-AUTH-01-03: “no public Create, Update, Delete, Resize, Attach, or Detach method” | Preserved. |
| A-09 | PRD-IS-06, PRD-AC-ID | ER-UNIT-01-04: “The Get request field is the immutable `id`”; GAP-09 names name/display constraints | Unresolved source contract for name/display sub-obligations; no public mutation invented. |
| A-10 | PRD-AC-ID, DES-WF-02 | ER-UNIT-01-01: “Get returns the fixture row for the supplied visible `id`” | Preserved. |
| A-11 | PRD-AC-ID, PRD-AC-ISO, DES-FAIL-01 | ER-ERROR-01-01: “returns gRPC/REST `NotFound`”; ER-KIND-01-05: “same `NotFound` status ... as an absent id” | Preserved; isolation case pending. |
| A-12 | PRD-IS-07, DES-SUM-01, DES-API-01 | ER-WIRE-01-01: “collection path `/api/fulfillment/v1/volumes` and item path `/api/fulfillment/v1/volumes/{id}`”; ER-WIRE-01-02: “Both public gRPC registration and REST handler registration” | Preserved. |
| A-13 | PRD-AC-BASE, DES-CON-02 | ER-UNIT-02-03: “equal primary keys are ordered by increasing immutable `id` (`id asc`)”; ER-UNIT-02-04: “returns `InvalidArgument`” | Preserved approved result; implementation execution blocked by GAP-13, not changed to id-only. |
| A-14 | PRD-AC-ID, PRD-AC-ISO, DES-RBAC-01 | ER-KIND-01-02: “contains no tenant B row”; ER-KIND-01-05: “outside ... scope returns ... `NotFound`” | Preserved; proposed Kind carrier. |
| A-15 | PRD-AC-STATES | ER-KIND-02-01/02/03: “returns the volume while ... `creating`/`available`/`deleting`” | Preserved; proposed Kind carrier. |
| A-16 | PRD-AC-STATES | ER-KIND-02-04: “after ... archives ... public List omits it and public Get returns `NotFound`” | Preserved; proposed Kind carrier. |
| A-17 | PRD-AC-STATES, DES-WF-02 | ER-KIND-02-05: “Without a state filter all non-archived states remain eligible; with ... only available rows” | Preserved; proposed Kind carrier. |
| A-18 | DES-SUM-01, DES-GOAL-01, DES-PROP-03 | ER-WIRE-01-03: “delegate to the existing private/generic path ... no second persistence/schema path”; ER-STATIC-01-01: “strict subset” | Preserved. |
| A-19 | DES-PROP-02, DES-TP-01 | ER-SCHEMA-01-01: “contains exactly `id`, `metadata`, ... `status.message`” | Preserved; GAP-SCHEMA execution gap. |
| A-20 | DES-PROP-03, DES-CON-01, DES-FAIL-01, DES-TP-01 | ER-UNIT-02-01: public field filter subset; ER-ERROR-01-02: “returns `InvalidArgument` and no response items” | Preserved. |
| A-21 | DES-PROP-04, DES-TP-01 | ER-PRIVATE-01-01: “constructed without a tier resolver”; ER-PRIVATE-01-02: “private Create ... refuses ... without ... resolver” | Preserved as internal setup/guard. |
| A-22 | DES-PROP-05, DES-SEC-01, DES-RBAC-01, DES-TP-01 | ER-AUTH-01-01: “authorized for public `Volumes/Get` and `Volumes/List`”; ER-AUTH-01-02: “receives `PermissionDenied`” | Preserved. |
| A-23 | DES-FAIL-01, DES-SUPPORT-01 | ER-ERROR-01-02/03: “returns `InvalidArgument`” for hidden filter/order | Preserved; order execution pending. |
| A-24 | DES-FAIL-01 | GAP-24: “no approved mapper fault-injection fixture” | Unresolved source contract carrier; explicit owner/gap retained. |
| A-25 | DES-FAIL-01 | GAP-25: “no approved delegate/DB fault harness” | Unresolved source contract carrier; explicit owner/gap retained. |
| A-26 | DES-FAIL-01, DES-SUPPORT-01 | ER-ERROR-01-01/02: `NotFound`/`InvalidArgument`; ER-AUTH-01-02: `PermissionDenied`; GAP-24 for `Internal` | Preserved for three errors; Internal carrier unresolved under GAP-24. |
| A-27 | DES-TP-01 | ER-AUDIT-01: “each has separate ER bullets”; ER-SCHEMA-01-01 exact allowlist | Preserved as evidence-structure obligation; schema check pending. |
| A-28 | DES-TP-02 | ER-KIND-01-01: “private fixture ... public gRPC”; ER-KIND-01-02: “no tenant B row” | Preserved; proposed Kind carrier. |
| A-29 | DES-TP-03 | ER-E2E-01-01/02: “provisioned volume ... public Get/List” and “cannot observe it” | Preserved with GAP-E2E infrastructure block. |
| A-30 | DES-UP-01, DES-SKEW-01 | ER-STATIC-01-01: “strict subset”; ER-STATIC-01-02: “without a database migration”; ER-STATIC-01-03: “remains compatible” | Preserved as static/artifact checks. |

**Audit note:** ER-AUDIT-01 is the required audit observation itself; it is
the only meta-result and does not replace any behavioral result. No stable
assertion ID was removed, renumbered, or silently weakened during correction.

## PRD/design coverage and corrections

### Source accounting

All PRD sections are accounted for: Problem Statement (background), In Scope
(A-01–A-12 and D-01–D-04), Out of Scope (X-01), User Stories (A-02/A-03/A-05/
A-06 and the unaffected persona), Assumptions (constraints), Dependencies
(D-04), Acceptance Criteria (A-03/A-04/A-09–A-17), and Provenance (background).
All design sections are accounted for: Summary/Motivation/Goals/Non-Goals,
Proposal, Workflow, API Extensions, UX Alignment, Implementation Constraints,
Security, Failure Handling, RBAC, Observability, Risks, Drawbacks, Alternatives,
Open Questions, Test Plan, Graduation, Upgrade, Skew, Support, Infrastructure,
and Provenance. No design section was treated as an unexamined omission.

### Local check-draft correction rounds

1. **Round 1:** Split List envelope, filtering, ordering, schema, isolation,
   state, and error observations into distinct Expected Results bullets;
   added the exact `id asc` tie-break and marked current DAO id-only ordering
   as GAP-13 implementation drift. Added explicit GAP-09/GAP-24/GAP-25 rather
   than inventing mutation or fault operations.
2. **Round 2:** Re-read the PRD/design ledgers and assertion audit; restored
   the exact qualifiers “indistinguishable,” “no partial data,” “no retries or
   side effects,” and “Tenant User and Tenant Admin have the same read scope.”
   Added the execution-evidence table, exact result references, schema-guard
   drift, Kind setup boundary, and absent vmaas owner/harness.

### Check-draft result

- **Planning correctness:** **FLAG** — source accounting and stable-ID
  preservation are complete, and every assertion has a concrete result or a
  named testability gap. The remaining GAP-09/GAP-24/GAP-25 carriers prevent a
  PASS because approved behavior is not provable within the current read-only
  evidence. GAP-13 and GAP-SCHEMA are implementation/evidence drift, not
  approved-contract changes.
- **Execution readiness:** **Not ready overall** — unit/authz/static commands
  are named, while public Kind cases, exact schema guard, ordering repair,
  fault fixtures, documentation/spec evidence, and vmaas E2E ownership remain
  proposed or blocked. No execution result is claimed.

## Summary

| Metric | Count / status |
|---|---|
| Behavioral cases | 11 local cases (`TC-UNIT-01`, `TC-UNIT-02`, `TC-SCHEMA-01`, `TC-ERROR-01`, `TC-AUTH-01`, `TC-PRIVATE-01`, `TC-WIRE-01`, `TC-KIND-01`, `TC-KIND-02`, `TC-E2E-01`, and `TC-STATIC-01`) |
| Assertions retained | 30 / 30 (`A-01` through `A-30`) |
| Assertions with concrete result bullets | 27 (some have execution/readiness gaps) |
| Explicit testability gaps | A-09 name sub-obligations, A-24, A-25; plus execution gaps GAP-13, GAP-SCHEMA, GAP-KIND, GAP-E2E, GAP-DOCS |
| Planning correctness | FLAG |
| Execution readiness | Not ready overall |
| Tests run | 0, by instruction |
