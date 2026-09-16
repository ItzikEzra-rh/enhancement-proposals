# OSAC-4542 Test Plan — Volume Get/List Public API

## Regeneration mode and authority

This is a test-plan-only regeneration for OSAC-4542. The approved design is
preserved as `03-design.md` byte-for-byte; this artifact adds execution
evidence and planning reconciliation without revising the approved design.

Authoritative inputs:

- PRD: `enhancement-proposals/enhancements/OSAC-4542-volume-get-list/prd.md`
  (SHA-256 `1606dc76d10d21b6657af91717057949ec1ac63e60f7bb7afdff41a48313f104`).
- Approved design:
  `enhancement-proposals/enhancements/OSAC-4542-volume-get-list/design.md`
  (SHA-256 `9fcc2b6612ad7fb5ce6150ec1355383f55ae7d1f0b651194d82f04aeee3bf61a`).
- Context: `01-context.md` in this artifact directory.
- Planning rules: pinned `design-test-planning` skill, SHA-256
  `6308e7ffe194c504a2074cca5b112ca9685d3857031901c0cc4d25b6583d17b6`.
- Installed project draft override: `.workflows/design/skills/draft.md`, SHA-256
  `00a6ffc943f97edb73ff2023821a3544b21988098b79922c86bd1929882a05f6`.

The approved PRD does not define formal `FR-*` or `NFR-*` identifiers. The
local `A-*`, `R-*`, `IC-*`, `TC-*`, `D-*`, and `X-*` identifiers below are
stable planning identifiers only; they do not alter the approved sources.

## Coverage summary

| Dimension | Result |
|---|---|
| PRD source accounting | All 11 headings, metadata, user-story subsections, and provenance accounted for |
| Approved-design source accounting | All 27 headings, front matter, optional sections, and provenance accounted for |
| Behavioral requirement groups | 8 of 8 mapped to assertions and cases or an explicit deliverable |
| Interface inventory | 6 local interface records; all have a case or an explicit gap |
| Source assertions | 22 split assertions; 21 preserved, 1 remains an unresolved source contract around ordering |
| Missing or weakened assertions after correction | None identified |
| Planning result | **FLAG**: ordering contract and several execution prerequisites remain unresolved or unavailable |
| Actual test execution | None; this regeneration is planning-only |

## Source accounting

Every PRD and approved-design section is accounted for below. A row can point
to more than one destination when a section mixes behavior, deliverables, and
scope rules.

### PRD accounting

| Source section | Decisive statement or obligation | Classification | Destination |
|---|---|---|---|
| Metadata and Target Release | Feature is OSAC-4542 for release 0.3. | Background | Artifact metadata and execution scope |
| Problem Statement | Existing private inventory is not visible through a supported tenant-facing surface. | Background | `R-01`, `R-06`; context only |
| In Scope — release boundary | This release is read-only Get/List over existing OSAC-2872 inventory. | Required behavior; explicit scope | `R-01`, `R-08`, `X-01` |
| In Scope — retrieve | A caller can retrieve tenant-meaningful volume details. | Required behavior | `R-01`, `A-01`, `TC-01` |
| In Scope — list | A caller can list entitled volumes using the standard list contract. | Required behavior | `R-01`, `R-02`, `A-02`, `A-08`, `TC-02`–`TC-07` |
| In Scope — visibility | Visibility follows tenant/project scope; Cloud Provider Admin spans tenants. | Required behavior | `R-03`, `A-03`, `A-13`, `TC-08`, `TC-09` |
| In Scope — representation | Public output is read-only and omits internal routing fields. | Required behavior | `R-04`, `A-04`, `A-05`, `TC-01`, `TC-12` |
| In Scope — identifier | `id` is the immutable Get/List key; name and display name are not request keys. | Required behavior | `R-04`, `A-06`, `TC-01`, `TC-02` |
| In Scope — access channels | Public gRPC/REST, console, and CLI use the normal resource patterns. | Required behavior; downstream dependency | `R-06`, `D-01`, `TC-11`, `TC-13` |
| In Scope — tests/docs | Automated Get/List isolation coverage and API documentation/spec updates are required. | Non-test deliverable plus required behavior | `R-07`, `D-02`, `TC-08`–`TC-11` |
| Out of Scope | Public create, update, delete, expansion, snapshots, clones, restore, attach/detach, provenance, file storage, and object storage are deferred or excluded. | Explicit exclusion | `X-01`–`X-05`; negative surface check in `TC-12` |
| User Stories — Cloud Provider Admin | Admin can Get/List across tenants for operations. | Required behavior | `R-03`, `A-03`, `TC-08` |
| User Stories — Tenant Admin/User | Tenant members can Get/List within their tenant/project scope; both roles have the same read scope in this release. | Required behavior | `R-03`, `A-03`, `A-13`, `TC-08`, `TC-09` |
| User Stories — Cloud Infrastructure Admin | This persona is unaffected. | Explicit exclusion | `X-06`; no feature case |
| Assumptions | Volumes already exist; standard visibility applies; public shape is a subset of private shape. | Background and contract basis | `R-03`, `R-04`, `R-08`, `TC-01`, `TC-08` |
| Dependencies | OSAC-2872 supplies inventory/private API; UI/UX consumers are separate work. | Non-test deliverable/dependency | `D-03`; readiness prerequisites |
| Acceptance Criteria — list contract | CEL uses `this.<field>`; offset/limit paginate; ordering is SQL-like with implicit `id asc` tie-break. | Required behavior; unresolved implementation contract | `R-02`, `A-08`, `TC-03`, `TC-05`–`TC-07` |
| Acceptance Criteria — identifier | Visible id succeeds; an outside-scope id is indistinguishable from absent and returns NotFound. | Required behavior | `A-06`, `A-09`, `A-10`, `TC-01`, `TC-09` |
| Acceptance Criteria — states | `creating`, `available`, and `deleting` are returned; archived `deleted` is absent; no implicit state filter exists. | Required behavior | `R-05`, `A-11`, `A-12`, `TC-10` |
| Acceptance Criteria — isolation | Neither List nor Get returns a volume outside entitled tenants/projects; automated isolation coverage is required. | Required behavior and deliverable | `R-03`, `A-13`, `D-02`, `TC-08`, `TC-09` |
| Provenance | PRD is a committed approved source; no new requirement is introduced here. | Background | Artifact provenance and source hashes |

### Approved-design accounting

| Source section | Decisive statement or obligation | Classification | Destination |
|---|---|---|---|
| Front matter | Approved design is the OSAC-4542 Volume Get/List public API design. | Background | Artifact identity; `03-design.md` byte identity |
| Summary | Public read-only `Volumes` exposes List/Get over gRPC and REST, wraps private service, reuses tenancy/CEL, and strips routing fields. | Required behavior | `R-01`–`R-04`, `IC-01`–`IC-04`, `TC-01`–`TC-04` |
| Motivation | Private inventory exists but is not available to console/tenants. | Background | `R-01`, `R-06` |
| Goals | Reuse wrapper/DAO, inherit tenancy/CEL, expose tenant fields only, make no schema change. | Required behavior and constraint | `R-02`–`R-04`, `R-08`, `TC-03`, `TC-08`, `TC-12` |
| Non-Goals | Public lifecycle and other storage capabilities are deferred/excluded. | Explicit exclusion | `X-01`–`X-05`, `TC-12` |
| Proposal 1 — public proto | Cleanapi generates public List/Get and excludes backend/protocol/hub/vendor fields; exact schema guard is required. | Required behavior and deliverable | `R-04`, `IC-04`, `A-04`, `A-15`, `TC-12` |
| Proposal 2 — public server | Public server delegates List/Get, maps private to public, and uses public CEL descriptor. | Required behavior | `R-01`, `R-02`, `R-04`, `IC-01`, `TC-01`–`TC-04` |
| Proposal 3 — private server | Read-only delegation can build without a tier resolver; Create still requires one. | Required behavior | `A-22`, `TC-15` |
| Proposal 4 — wiring | Public gRPC and REST services are registered. | Required behavior | `IC-01`, `IC-02`, `IC-03`, `TC-11`, `TC-12` |
| Proposal 5 — authorization | Tenant clients are allowed on public Get/List. | Required behavior | `R-03`, `IC-05`, `A-20`, `TC-11` |
| Workflow Description | Authn → authz → tenancy → public wrapper → private server → generic DAO → PostgreSQL; List returns items/size/total and Get hides absent/non-visible ids as NotFound. | Required behavior and execution boundary | `A-02`, `A-09`, `A-10`, `A-13`, `TC-01`, `TC-02`, `TC-08`, `TC-09`, `TC-11` |
| API Extensions | Public `osac.public.v1.Volumes` List/Get, REST paths, public Volume message, no CRDs/webhooks/aggregated API server/finalizers. | Required behavior and explicit exclusion | `IC-01`–`IC-04`, `X-07`, `TC-11`, `TC-12` |
| UX Alignment | `osac-ui` generates public types from backend proto after this API lands; `osac-ux` is not authoritative. | Non-test deliverable/dependency | `IC-06`, `D-03`, readiness gap |
| Implementation Details/Notes/Constraints | Mapping is non-strict; filters use public descriptor; order is validated against public schema but the current DAO sorts by id and ignores requested order; generated import pruning is a tooling constraint. | Required behavior, known drift, and deliverable | `A-04`, `A-08`, `A-16`, `A-17`, `D-04`, `TC-04`, `TC-06`, `TC-07`, `TC-12` |
| Security Considerations | Read-only surface, existing tenancy, hidden routing fields, and public-field-only CEL input. | Required behavior | `R-03`, `R-04`, `A-04`, `A-13`, `TC-04`, `TC-08`, `TC-09`, `TC-11` |
| Failure Handling and Recovery | NotFound for absent/non-visible Get; InvalidArgument for invalid filter/order; Internal for mapping; delegate/DB errors propagate; reads are idempotent and not retried. | Required behavior | `A-10`, `A-17`, `A-18`, `A-19`, `TC-07`, `TC-09`, `TC-14` |
| RBAC/Tenancy | Tenant User/Admin have identical read scope; Cloud Provider Admin sees all; unauthenticated is denied; no public mutating method exists. | Required behavior and explicit exclusion | `R-03`, `A-03`, `A-05`, `A-20`, `TC-08`, `TC-11`, `TC-12` |
| Observability and Monitoring | Existing metrics, request logs, and interceptors apply; no new observability changes. | Background/constraint | `D-05`; no new behavior case |
| Risks and Mitigations | Generated public imports may require documented pruning so buf lint passes. | Non-test deliverable | `D-04`, `TC-12`, `make -C proto lint` |
| Drawbacks | Capability is read-only until later phases. | Background/explicit scope | `X-01`, `X-02` |
| Alternatives | Hand-written public proto and exposing/providing protocol types are rejected. | Decision provenance | `D-06`; no extra behavior case |
| Open Questions | Approved design says none. | No unresolved design question | Recheck result; remaining ordering contract is implementation/source mismatch, not an approved open question |
| Test Plan | Unit projection/schema/filter/authz cases; Kind integration; external VMAAS E2E. | Required deliverable and evidence basis | `TC-01`–`TC-15`, execution evidence |
| Graduation Criteria | Ships in 0.3; no separate maturity ladder. | Release criterion | `D-07`; readiness gate |
| Upgrade/Downgrade Strategy | Additive read-only endpoints, no schema/data migration, existing clients remain valid. | Required compatibility behavior | `A-21`, `TC-12` |
| Version Skew Strategy | Same-process generation avoids cross-component skew; older consoles remain valid; public type is a strict subset. | Required compatibility behavior | `A-21`, `D-03`, `TC-12` |
| Support Procedures | Standard errors/logs apply; removing OPA entries disables reads without affecting provisioning. | Operational deliverable | `D-05`, `TC-11`, readiness checklist |
| Infrastructure Needed | None in approved design. | Background; contradicted by execution prerequisites found in context | Readiness gap classification |
| Provenance | Approved design is a committed snapshot; no authoring phases are recorded in that source. | Background | Artifact provenance and byte-identity audit |

## Requirements and interface coverage

The following requirement groups are derived from the approved sources; none is
a new product requirement. “Planned” means a concrete case and expected result
are recorded, not that the case has run.

| Local requirement | Source basis | Covered assertion(s) | Cases or deliverable | Coverage |
|---|---|---|---|---|
| `R-01` Public read retrieval and listing | PRD In Scope; design Summary/API Extensions | `A-01`, `A-02`, `A-09` | `TC-01`, `TC-02` | Planned |
| `R-02` Standard List behavior | PRD Acceptance Criteria; design Workflow/Implementation Details | `A-08`, `A-16`, `A-17` | `TC-03`–`TC-07` | Planned; ordering contract flagged |
| `R-03` Tenant/project visibility | PRD In Scope/Acceptance; design RBAC/Tenancy | `A-03`, `A-10`, `A-13`, `A-20` | `TC-08`, `TC-09`, `TC-11` | Planned |
| `R-04` Tenant-safe public projection | PRD In Scope/Assumptions; design Proposal/Security | `A-04`, `A-05`, `A-15` | `TC-01`, `TC-04`, `TC-12` | Planned |
| `R-05` Inventory state semantics | PRD Acceptance Criteria | `A-11`, `A-12` | `TC-10` | Planned |
| `R-06` Normal public access channels | PRD In Scope; design API Extensions/UX Alignment | `A-06`, `A-07` | `TC-11`, `TC-13`; UI generation deliverable | Partial: CLI/UI prerequisites unresolved |
| `R-07` Automated isolation and documentation/spec | PRD In Scope/Acceptance; design Test Plan | `A-13` | `TC-08`–`TC-11`; `D-02` | Partial: documentation/spec update not executable in this phase |
| `R-08` Reuse existing inventory without schema change | PRD Assumptions/Dependencies; design Goals/Upgrade | `A-21`, `A-22` | `TC-12`, `TC-15`; `D-03` | Planned |

### Local interface inventory

The approved design does not contain the built-in template’s explicit “§5
Interface Changes” section. These are local inventory IDs for coverage only.

| Interface | Source basis | Observable contract | Coverage |
|---|---|---|---|
| `IC-01` Public gRPC `osac.public.v1.Volumes.List` | Design API Extensions/Workflow | List returns public items plus size/total under standard list inputs. | `TC-02`–`TC-10` |
| `IC-02` Public gRPC `osac.public.v1.Volumes.Get` | Design API Extensions/Workflow | Get accepts public `id`, returns visible public volume, and returns NotFound for absent/non-visible id. | `TC-01`, `TC-09`, `TC-10` |
| `IC-03` REST `/api/fulfillment/v1/volumes` and `/{id}` | PRD access channels; design API Extensions | REST transcoding has the same projection, visibility, and error contract. | `TC-11` |
| `IC-04` Public protobuf/schema projection | Design Proposal 1/Implementation Details | Exact public field allowlist is generated; internal routing fields and types are absent. | `TC-04`, `TC-12` |
| `IC-05` Authorization surface | PRD visibility; design Proposal 5/RBAC | Allowed tenant/admin calls reach Get/List; unauthenticated and public mutation paths are denied or absent. | `TC-11`, `TC-12` |
| `IC-06` Existing CLI resource patterns | PRD In Scope access channels; design Workflow/UX | `osac get volumes` and `osac get volume <id>` can use the public read surface. | `TC-13`; blocked by current CLI discovery gap |

## Test cases and exact expected results

| ID | Tier / boundary | Setup and target | Expected result (decisive wording) | Evidence state |
|---|---|---|---|---|
| `TC-01` | Unit / public server mapper | `fulfillment-service/internal/servers/volumes_server_test.go`; use a private delegate fixture containing a visible volume. Run from `fulfillment-service/`: `ginkgo run internal/servers`. | **The public Get response contains the same immutable `id`, tenant-meaningful metadata/spec/status fields, and no private routing fields.** | Existing target and analogous projection tests verified; assertion coverage planned |
| `TC-02` | Unit / public List contract | Same package and command; fixture returns multiple visible private rows. | **The public List response contains only public volume items and reports the returned item count as `size` and the matching result count as `total`.** | Existing target and analogous list tests verified; assertion coverage planned |
| `TC-03` | Unit / filter boundary | Same package; submit CEL `this.status.state == 'available'`. | **Only volumes whose public `status.state` is `available` are returned, and the request succeeds.** | Existing target and analogous public filter test verified; planned case |
| `TC-04` | Unit / filter security boundary | Same package; submit CEL `this.status.backend == '...'`. | **A CEL filter that names private `status.backend` is rejected with gRPC `InvalidArgument` before private data is queried or returned.** | Existing target and analogous private-filter rejection verified; planned exact case |
| `TC-05` | Integration / List pagination | `fulfillment-service/it/it_public_volumes_test.go` (new planned coverage), real Kind `osac-dev` deployment with volumes created through the private path. Run from `fulfillment-service/`: `make -C ../osac-installer test PLATFORM=kind PROFILE=dev NS=osac SUITE=fulfillment`. | **`offset` skips the requested number of visible rows and `limit` caps the returned items without changing the visibility-filtered `total`.** | Integration command verified; target test file absent, so not runnable yet |
| `TC-06` | Integration / List ordering | Same Kind setup and command; create rows with distinct public sortable fields and an `id` tie. | **A valid SQL-like public-field order changes result order as requested, and equal sort keys use implicit ascending `id` as the secondary order.** | Planned; current DAO sorts by `id` regardless of requested order, so execution is blocked by implementation drift and contract recheck |
| `TC-07` | Unit/integration / input validation | Public server/filter translator target; submit an order expression naming `status.backend`. | **An order expression naming a field absent from the public descriptor is rejected with `InvalidArgument`.** | Design contract identified; exact existing coverage not found, so planned and blocked pending implementation confirmation |
| `TC-08` | Integration / tenancy boundary | Same Kind setup; create volumes in tenant/project A and tenant/project B; exercise Tenant User, Tenant Admin, and Cloud Provider Admin credentials. | **Tenant User and Tenant Admin receive only their entitled tenant/project rows, while Cloud Provider Admin receives rows across all tenants.** | Existing tenancy harness and analogous public isolation tests verified; public volume target absent |
| `TC-09` | Integration / Get visibility boundary | Same Kind setup; request a visible id and an id belonging to another tenant/project. | **Get returns the visible volume for an entitled id and returns `NotFound` for an outside-scope id, indistinguishable from a nonexistent id.** | Existing REST/tenancy harness verified; public volume target absent |
| `TC-10` | Integration / lifecycle state boundary | Same Kind setup; observe or create volumes in `creating`, `available`, and `deleting`, then a fully archived `deleted` record. | **List and Get return `creating`, `available`, and `deleting` volumes; an archived `deleted` record is absent from both; no other implicit state filter is applied.** | Private lifecycle fixture exists; public read-path case absent |
| `TC-11` | Integration / REST and authz boundary | Extend the existing REST gateway/authz integration target; use authenticated tenant and unauthenticated clients. | **REST List/Get match the gRPC public projection and visibility contract; an authenticated tenant client is allowed on public List/Get, and an unauthenticated client receives `Unauthenticated`.** | Existing REST gateway and authz targets verified; exact public volume case absent |
| `TC-12` | Unit/static / schema and negative surface | `fulfillment-service/internal/servers/volumes_server_test.go` plus generated descriptors; run `ginkgo run internal/servers` from `fulfillment-service/`, and `make -C proto lint` from the repository root. | **The public Volume descriptor contains exactly `id`, `metadata`, `spec.storage_tier`, `spec.size_gib`, `spec.access_mode`, `status.state`, and `status.message`; `backend`, `protocol`, `hub`, `vendor_volume_id`, and `vendor_context` are absent, and no public Create/Update/Delete/Signal method exists.** | Existing schema-guard target and proto lint command verified; exact allowlist and method-surface assertions planned |
| `TC-13` | Component/CLI boundary | Existing CLI discovery and command test targets under `fulfillment-service/internal/cmd/cli`; use the repository’s normal `ginkgo run internal` command once public methods are discoverable. | **`osac get volumes` lists the public volumes and `osac get volume <id>` retrieves the same public projection using `id` as the request key.** | PRD contract preserved; current reflection helpers require the full CRUD method set, so execution is blocked pending CLI design/implementation correction |
| `TC-14` | Unit / failure boundary | Public server tests with mapper/delegate/DB error fixtures. | **A mapping failure returns `Internal` with no partial data, and delegate/DB errors propagate unchanged; read calls perform no retry or side effect.** | Approved design specifies the contract; concrete failure fixtures were not found, so planned |
| `TC-15` | Unit / private-server construction boundary | `fulfillment-service/internal/servers/private_volumes_server_test.go`; run `ginkgo run internal/servers` from `fulfillment-service/`. | **The read-only private server builds without a tier resolver, while Create without a tier resolver fails as a server configuration error.** | Existing target and analogous private-server behavior verified; exact assertion planned |

## Assertion-preservation audit

Assertions were extracted independently from the PRD and approved design, then
split where a source sentence contains separate trigger, state, outcome, or
error obligations. The expected-result wording below is copied exactly from the
case table above; it is the decision point for review.

| Assertion | Source | Case / exact expected-result reference | Verdict |
|---|---|---|---|
| `A-01` Get exposes tenant-meaningful details | PRD In Scope — retrieve | `TC-01`: “The public Get response contains the same immutable `id`, tenant-meaningful metadata/spec/status fields, and no private routing fields.” | Preserved |
| `A-02` List returns entitled inventory | PRD In Scope — list | `TC-02`: “The public List response contains only public volume items and reports the returned item count as `size` and the matching result count as `total`.” | Preserved |
| `A-03` Role/scope matrix | PRD visibility/user stories; design RBAC | `TC-08`: “Tenant User and Tenant Admin receive only their entitled tenant/project rows, while Cloud Provider Admin receives rows across all tenants.” | Preserved |
| `A-04` Internal fields are hidden | PRD representation; design Proposal 1/Security | `TC-12`: exact descriptor allowlist and absence of named internal fields | Preserved |
| `A-05` Public API is read-only | PRD representation/out-of-scope; design RBAC | `TC-12`: “no public Create/Update/Delete/Signal method exists.” | Preserved |
| `A-06` Immutable id is the key | PRD identifier | `TC-01` and `TC-13`: response/request key uses immutable `id`; name is not substituted | Preserved |
| `A-07` gRPC/REST/CLI access pattern | PRD access channels; design API/UX | `TC-11` and `TC-13`: public REST parity and CLI read commands | Preserved; CLI execution gap remains |
| `A-08` CEL, pagination, ordering, tie-break | PRD Acceptance Criteria; design Implementation Details | `TC-03`, `TC-05`, `TC-06`: public filter, offset/limit, requested ordering, implicit `id asc` tie-break | **Unresolved source contract**: PRD requires ordering, while approved design records current id-only DAO behavior as a known limitation |
| `A-09` Visible Get succeeds | PRD Identifier; design Workflow | `TC-09`: “Get returns the visible volume for an entitled id” | Preserved |
| `A-10` Hidden Get is NotFound | PRD Identifier; design Failure Handling | `TC-09`: “returns `NotFound` for an outside-scope id, indistinguishable from a nonexistent id” | Preserved |
| `A-11` Non-archived states are returned | PRD Inventory states | `TC-10`: “List and Get return `creating`, `available`, and `deleting` volumes” | Preserved |
| `A-12` Archived deleted state is absent/no implicit filter | PRD Inventory states | `TC-10`: “an archived `deleted` record is absent from both; no other implicit state filter is applied” | Preserved |
| `A-13` List and Get isolation | PRD Isolation; design Security/RBAC | `TC-08` and `TC-09`: entitled rows only and hidden id NotFound | Preserved |
| `A-14` Public service and routes are registered | Design API Extensions/Proposal 4 | `TC-11`: REST paths and gRPC parity | Preserved |
| `A-15` Exact public schema allowlist | Design Test Plan/Proposal 1 | `TC-12`: exact seven-field allowlist | Preserved |
| `A-16` Private CEL field is rejected | Design Proposal 2/Security/Test Plan | `TC-04`: InvalidArgument before private data is queried/returned | Preserved |
| `A-17` Private order field is rejected | Design Implementation Details/Failure Handling | `TC-07`: InvalidArgument for a field absent from the public descriptor | Preserved |
| `A-18` Mapping error is Internal/no partial response | Design Failure Handling | `TC-14`: Internal and no partial data | Preserved |
| `A-19` Delegate/DB errors propagate; reads are idempotent | Design Failure Handling | `TC-14`: unchanged propagation and no retry/side effect | Preserved |
| `A-20` Authz allows reads and denies unauthenticated/mutation | Design Proposal 5/RBAC; PRD read-only scope | `TC-11` and `TC-12`: allowed public reads, Unauthenticated, and absent public mutators | Preserved |
| `A-21` No schema change/backward-compatible addition | PRD assumptions; design Goals/Upgrade/Version Skew | `TC-12`: generated schema/service surface check; no migration is planned | Preserved as compatibility/deliverable |
| `A-22` Optional tier resolver behavior | Design Proposal 3/Test Plan | `TC-15`: read server builds without resolver; Create without it fails | Preserved |

No source assertion was dropped or weakened during correction. The one flagged
assertion is explicitly kept as a concrete test expectation; its verdict is
unresolved because the PRD requirement and the design’s documented current
implementation limitation do not say whether the limitation is accepted for
this release.

## Internal correction and recheck

The first planning pass was corrected before this result was recorded:

1. Added source-accounting rows for mixed PRD sections (access channels,
   test/documentation, assumptions, dependencies, and state criteria) and for
   the approved design’s UX, compatibility, support, optional infrastructure,
   and provenance sections.
2. Split compound visibility, identifier, state, filter, ordering, error, and
   authorization statements into separate assertion IDs with decisive expected
   results.
3. Added the missing public-field order rejection, archived-state, REST/authz,
   CLI, mapping/DB failure, and optional-resolver cases.
4. Corrected execution tiers and commands to the repository instructions:
   focused unit tests use `ginkgo run internal/servers`; Kind integration uses
   the installer-owned fulfillment target; E2E collection remains conditional
   on identifying the owning storage suite.
5. Marked implementation drift and missing test files as readiness gaps rather
   than treating analogous tests as executed evidence.

Recheck results:

- Independent PRD and approved-design source-accounting passes found no
  unexplained source section or unassigned behavior/deliverable.
- Every assertion maps to a case with an explicit expected result, except for
  compatibility/deliverable assertions that are explicitly labeled as such.
- Every case reference in the assertion audit resolves to a case in this file.
- Tier labels, commands, and prerequisites are supported by the applicable
  component instructions or are explicitly marked blocked/proposed.
- No correction round beyond the recorded pass was needed.

## Remaining gaps by classification

| Classification | Gap | Effect on readiness | Owning source/ticket |
|---|---|---|---|
| Unresolved source contract | PRD requires SQL-like ordering with `id asc` tie-break; approved design documents that the current DAO ignores `order` and does not resolve whether this is acceptable. | `TC-06` cannot be accepted until the contract is resolved and implementation matches it or an approved source changes. | PRD Acceptance Criteria; design Implementation Details; OSAC-4542 |
| Implementation drift | `generic_dao_list.go` currently hardcodes `id` ordering; the planned ordering case is expected to expose this. | Blocks ordering execution/acceptance. | OSAC-4542 |
| Implementation drift | Generic CLI reflection/completion currently requires List/Get/Create/Update/Delete, while this public service intentionally has only List/Get. | Blocks `TC-13` until the existing CLI pattern supports read-only public resources or the scope is clarified. | OSAC-4542; fulfillment-service CLI instructions |
| Documentation/spec drift | `fulfillment-service/docs/API.md` still describes volumes as private/all-five-method public services, contrary to the approved public read-only design. | `D-02` and published API-spec verification are not ready for sign-off. | OSAC-4542 |
| Missing implementation test target | No dedicated public Volume Kind integration test file was found; analogous storage-tier, REST, and tenancy harnesses exist. | `TC-05`–`TC-11` are planned, not runnable from this artifact alone. | OSAC-4542 |
| Missing E2E evidence | No public Volume read-path case exists under `tests/e2e/`; the approved design names an external VMAAS suite, while repository instructions place suites under `tests/e2e/`. | E2E ownership/path must be resolved before collection or execution. | OSAC-4542; `tests/e2e/AGENTS.md` |
| Downstream dependency | `osac-ui` currently has private generated Volume types only; public types require backend proto merge and `pnpm gen-types`. | UI-consumption readiness is conditional and is not executed in this test-plan-only phase. | OSAC-4546/4547; approved design UX Alignment |
| External-context discrepancy | Read-only Jira context states a different tenant-admin/user visibility split than the approved PRD/design. | Not used as the test oracle; requires Jira cleanup or explicit clarification before implementation tracking. | OSAC-4542 Jira, read-only |
| Deliberately out of scope | Public mutation, expansion/snapshots/clones/restore, attach/detach, provenance, file/object storage, and Cloud Infrastructure Admin behavior. | No acceptance cases; negative surface is checked only where the public service descriptor is observable. | PRD Out of Scope; design Non-Goals |

## Execution readiness

Overall readiness is **FLAG / not ready for acceptance execution**. The plan is
actionable once the listed gaps are resolved, but no test was run in this
regeneration and no implementation or test file was created.

| Evidence area | Current readiness |
|---|---|
| Focused unit target | Ready as a command and location: `ginkgo run internal/servers` from `fulfillment-service/`; new/expanded assertions are still required. |
| Proto/static validation | Ready as a command: `make -C proto lint` from the repository root; generated changes are not made in this phase. |
| Kind integration | Conditional: installer-owned command is known, but the public Volume integration target is absent and a Kind deployment is a prerequisite. |
| REST/authz integration | Conditional: existing gateway/authz harness is present; public Volume coverage is absent. |
| CLI | Blocked by current read-only service discovery mismatch. |
| E2E | Blocked pending owning suite/path and infrastructure prerequisites; no collection was run. |
| Documentation/API spec | Not ready for verification while the repository documentation remains stale; exact generator/update path requires the implementation phase. |
| UI consumer | Conditional on public proto generation and `osac-ui` type regeneration; not part of this phase. |
| Actual evidence | None collected, by request and scope. |
