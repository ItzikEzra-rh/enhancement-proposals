# Testplan — OSAC-4841 fork fixture (frozen OSAC-4542 Volume Get/List)

## Overview

This disposable fork fixture evaluates gate behavior. PRD/design are byte-identical copies of approved OSAC-4542 sources. Current OSAC source is execution guidance, not a new product oracle. No Volume implementation or deployed feature tests were executed here.

- Behavioral groups planned: the eight local aliases FR1–FR8 defined in the table below. This is a count of this plan's groups; the authoritative PRD/design define no formal FR/NFR or AC IDs. Source-clause accounting and assertion preservation are audited separately below.
- Interface aliases: IC1 public gRPC Get/List; IC2 REST paths; IC3 public Volume projection.
- Story aliases: DEV-READ (implementation/unit/component-integration), QE-READ (deployed journey), UI-READ (OSAC-4546/4547). These are local assignments, not fabricated Jira tickets.
- Total test cases: 21 (20 automated intent, 1 manual).
- Fixture identifiers such as `vol-a` are symbolic aliases for the system-generated IDs returned by private Create, never literal request IDs. Capture the returned ID and use that value in Get/List assertions.
- Execution status: all not run; future additions explicitly proposed. A Ready plan is not executed coverage.
- Skills SHA: f09511abd3f349b4a3a7c0bec023d3666a22bc24; OSAC SHA: 1411b33bfb0fa109e4299675b8038906df56b0b5.

## Local behavior and interface mappings

FR1–FR8 are aliases for organizing cases; they do not rename or invent approved
requirements. Pxx and Dxx identify the exact quoted source sections in the
source-clause ledger. The assertion-to-result audit preserves the individual
obligations and expected results within these sections.

| Local group | Approved behavior organized here | Source-clause IDs | Cases |
|---|---|---|---|
| FR1 | Public read projection and absence of public mutations | P03, P08, D02, D04 | TC-FR1-01, TC-FR1-02 |
| FR2 | System-generated id, name/display_name distinctions and immutable naming scope | P03, P08, D04 | TC-FR2-01, TC-FR2-02 |
| FR3 | List filtering, pagination, ordering and counts | P03, P08, D04 | TC-FR3-01 through TC-FR3-03 |
| FR4 | Tenant/project visibility, shared/provider access and authorization | P03, P05, P06, P08, D04, D12 | TC-FR4-01 through TC-FR4-03 |
| FR5 | Public schema allowlist, hidden routing fields and mapper/delegate handling | P03, P06, P08, D04 | TC-FR5-01 through TC-FR5-03 |
| FR6 | Observable inventory states and archive exclusion | P03, P08, D04, D08 | TC-FR6-01, TC-FR6-02 |
| FR7 | Public access channels, CLI/UI consumers and id-based navigation | P03, P05, P08, D04, D05 | TC-FR7-01 through TC-FR7-03 |
| FR8 | Optional resolver, deployed provision/read journey, API artifacts and compatibility | P03, P07, P08, D04, D08, D09, D10, D11, D13 | TC-FR8-01 through TC-FR8-03 |

IC1 denotes the public gRPC Get/List contract; IC2 denotes the REST routes;
IC3 denotes the public Volume projection. Each case's metadata now identifies
its asserted interfaces. CLI/UI consumer cases identify IC3 explicitly;
transport parity is asserted by TC-FR7-01. A descriptor/mapper check remains
Unit coverage even when it names an interface; it does not establish a deployed
boundary.

## Source-clause ledger and section accounting

All source sections are retained below with exact wording and line numbers. Clause IDs are stable source section IDs. Assertions/cases provide observable carriers. Scope exclusions stay excluded. Authors/provenance/problem/motivation are background; dependencies and UX actions are non-test work; no new behavior is inferred from examples.

### P01: prd.md:1 — Header

Classification: background or explicit exclusion. Destination: Background explains existing inventory/read-only intent; alternatives are rejected, non-goals are excluded; no test obligation added.

> # Volume Get/List Public API
>
> | Field       | Value   |
> |-------------|---------|
> | Author(s)   | Zoltan Szabo |
> | Jira        | [OSAC-4542](https://redhat.atlassian.net/browse/OSAC-4542) |
> | Date        | 2026-08-27 |
> | Target Release | 0.3 |

### P02: prd.md:10 — Problem Statement

Classification: background or explicit exclusion. Destination: Background explains existing inventory/read-only intent; alternatives are rejected, non-goals are excluded; no test obligation added.

> ## Problem Statement
>
> The OSAC storage control plane (OSAC-2872) already provisions standalone storage volumes and tracks them in a central inventory, but that inventory is only reachable through the internal API. Tenants and the OSAC console have no supported way to see the volumes that exist. As a result, the console cannot show storage to users, and tenants have no operational visibility into their own volumes — they cannot confirm a volume's size, tier, or state, and administrators cannot review storage usage for troubleshooting or monitoring. This blocks the console's storage experience and leaves volume inventory effectively invisible to the people who own it.

### P03: prd.md:14 — In Scope

Classification: required behavior / deliverable. Destination: FR1–FR8 assertions below; non-test work and explicit exclusions in Gaps

> ## In Scope
>
> *This release delivers the first, read-only slice of the public Volume API: retrieving individual volumes and listing them. It reuses the volumes already provisioned and inventoried by OSAC-2872 — no new provisioning path is introduced. Mutating operations remain internal and are deferred to later phases of the public Volume API (OSAC-984). See Out of Scope.*
>
> - **Retrieve a volume's details.** A user can fetch a single volume and see its tenant-meaningful attributes — name, tier, size, access mode, and current state — so they can confirm its configuration and availability.
> - **List volumes.** A user can list the volumes they are entitled to see, consistent with the standard OSAC list contract, so the console and CLI can present and navigate storage inventory.
> - **Tenant- and project-scoped visibility.** Each caller sees only the volumes they are entitled to under OSAC's standard tenant- and project-based visibility: a Cloud Provider Admin across all tenants, and tenant members within the tenants and projects visible to them — the same visibility model used by every other OSAC resource.
> - **Read-only, tenant-meaningful representation.** The public view exposes only information that is meaningful to tenants; internal placement and routing details used to serve a volume — the serving backend, its storage protocol, the hub that hosts it, and the vendor-assigned volume identifier — are never shown. Volumes are read-only through this API.
> - **Stable public identifier.** Each volume has an immutable, system-generated `id` that `List` returns and `Get` accepts as the request key. `name` is a separate, immutable attribute that is unique within the volume's tenant/project scope (a valid RFC 1123 label), and `display_name` is an optional human-friendly label; neither is the request key. Console deep-links and `Get` requests use `id`.
> - **Same access channels as other resources.** Volumes are reachable over the same public gRPC and REST endpoints, console, and CLI as other OSAC resources; no storage-specific access path is introduced. CLI support (`osac get volumes`, `osac get volume <id>`) comes for free from the existing `get_cmd.go` / `list_cmd.go` patterns and requires no separate tracking.
> - **Test and documentation.** Tests cover retrieving and listing standalone volumes through the public API, including tenant-scoped isolation; API documentation and the published API spec are updated with the new read endpoints.

### P04: prd.md:26 — Out of Scope

Classification: required behavior / deliverable. Destination: FR1–FR8 assertions below; non-test work and explicit exclusions in Gaps

> ## Out of Scope
>
> Deferred to later work (this release is read-only Get/List only):
>
> - **Volume lifecycle through the public API** — creating, updating, and deleting volumes. These remain on the internal API and are tracked under [OSAC-984](https://redhat.atlassian.net/browse/OSAC-984).
> - **Volume expansion, snapshots, clones, and restore** — tracked under [OSAC-48](https://redhat.atlassian.net/browse/OSAC-48).
> - **Volume attach / detach** — tracked under [OSAC-4884](https://redhat.atlassian.net/browse/OSAC-4884).
> - **Volume identifiability / provenance** — distinguishing what each volume represents (e.g. a VM filesystem disk vs. a workload PV) and which tenant cluster it belongs to. Deferred to [OSAC-4793](https://redhat.atlassian.net/browse/OSAC-4793) under the OSAC-2871 Storage Volumes outcome.
> - **File storage** (NFS/SMB — OSAC-4515) and **object storage** (S3).

### P05: prd.md:36 — User Stories

Classification: required behavior / deliverable. Destination: FR1–FR8 assertions below; non-test work and explicit exclusions in Gaps

> ## User Stories
>
> ### Cloud Provider Admin
>
> - As a Cloud Provider Admin, I want to get and list storage volumes across all tenants, so that I have operational visibility for troubleshooting and monitoring.
>
> ### Tenant Admin / Tenant User
>
> - As a tenant member, I want to get the details of a specific storage volume — its size, tier, and state — so that I can understand its configuration and verify its availability.
> - As a tenant member, I want to list all volumes visible within my tenant and project scope, so that I can find a volume and navigate storage inventory in the console. Tenant User and Tenant Admin have the same read scope in this release (both see all volumes in the tenant), consistent with OSAC-2872, where both roles share the same storage capabilities.
>
> ### Cloud Infrastructure Admin
>
> - Not affected by this feature.

### P06: prd.md:51 — Assumptions

Classification: required behavior / deliverable. Destination: FR1–FR8 assertions below; non-test work and explicit exclusions in Gaps

> ## Assumptions
>
> - The volumes to be read already exist and are inventoried by the storage control plane (OSAC-2872); this feature adds a read surface, not a new source of data.
> - Tenant- and project-scoped visibility is the correct and consistent default for this release, matching how every other OSAC resource scopes reads.
> - The public representation of a volume is a subset of the internal one; fields that are not meaningful to tenants are omitted rather than reshaped.

### P07: prd.md:57 — Dependencies

Classification: required behavior / deliverable. Destination: FR1–FR8 assertions below; non-test work and explicit exclusions in Gaps

> ## Dependencies
>
> - **OSAC-2872 (Storage Control Plane):** provides the private Volume API, the volume inventory, and the tier/backend model this read API surfaces. Must be in place for volumes to exist and be retrievable.
> - **Console UI / UX and UI design gates (OSAC-4546, OSAC-4547):** consume this API to present the volume list and detail views; tracked separately.

### P08: prd.md:62 — Acceptance Criteria

Classification: required behavior / deliverable. Destination: FR1–FR8 assertions below; non-test work and explicit exclusions in Gaps

> ## Acceptance Criteria
>
> `List` inherits the standard OSAC list contract (CEL filtering via `this.<field>`, `offset`/`limit` pagination, SQL-like ordering with implicit secondary sort on `id asc`). The following volume-specific criteria apply:
>
> - **Identifier.** `List` items and `Get` both key on the immutable `id`; a `Get` by the `id` of a visible volume returns it, and a `Get` by an id outside the caller's tenants returns `not found` (indistinguishable from a non-existent id, so existence is not leaked across tenants).
> - **Inventory states.** `List` and `Get` return volumes in every non-archived state tracked by OSAC-2872 (`creating`, `available`, `deleting`). Once a volume is fully deprovisioned its record is archived (`deleted`) and no longer appears through `List`/`Get`. There is no other implicit state filter — callers filter by `status.state` for a subset.
> - **Isolation.** A caller never receives a volume outside their entitled tenants and projects through either `List` or `Get`, and this is covered by automated tenant- and project-isolation tests.
>
> ---

### P09: prd.md:72 — Provenance

Classification: background or explicit exclusion. Destination: Background explains existing inventory/read-only intent; alternatives are rejected, non-goals are excluded; no test obligation added.

> ## Provenance
>
> Committed: commit @ prd 0.9.0 - 562b610, workspace prd/OSAC-4542-review-followups @ 04971f4
>
> > Authoring phases not recorded this session (commit-time snapshot only).
>
> <!-- ai-workflow-provenance:{"schema_version":1,"provenance_kind":"commit_only","workflow":"prd","workflow_version":"0.9.0","ai_workflows":"562b610","source_repo":"04971f4","source_repo_branch":"prd/OSAC-4542-review-followups","commits_behind_main":0,"commits_ahead_main":1,"main_ref":"main","phases":["commit"],"authoring_modes":["skill"],"context_changed":false,"origin_untracked":false} -->

### D01: design.md:1 — Header

Classification: background or explicit exclusion. Destination: Background explains existing inventory/read-only intent; alternatives are rejected, non-goals are excluded; no test obligation added.

> ---
> title: volume-get-list-public-api
> authors:
>   - Zoltan Szabo
> creation-date: 2026-08-27
> last-updated: 2026-08-27
> tracking-link:
>   - https://redhat.atlassian.net/browse/OSAC-4542
> prd:
>   - "prd.md"
> see-also:
>   - "OSAC-2872 (storage control plane — private Volume API)"
>   - "OSAC-984 (public Volume API epic)"
> ---
>
> # Volume Get/List Public API

### D02: design.md:18 — Summary

Classification: background or explicit exclusion. Destination: Background explains existing inventory/read-only intent; alternatives are rejected, non-goals are excluded; no test obligation added.

> ## Summary
>
> Add a read-only public projection of the existing private Volume API: a public
> `Volumes` service exposing only `List` and `Get` over gRPC and REST at
> `/api/fulfillment/v1/volumes`. The public server wraps the already-shipped
> `PrivateVolumesServer`, reusing its DAO, tenancy enforcement, and CEL filtering,
> and maps private→public so that internal routing fields never leave the service.
> See [PRD](prd.md) for detailed requirements.

### D03: design.md:27 — Motivation

Classification: background or explicit exclusion. Destination: Background explains existing inventory/read-only intent; alternatives are rejected, non-goals are excluded; no test obligation added.

> ## Motivation
>
> OSAC-2872 delivered the private Volume API, the volume inventory, and tier→backend
> resolution, but volumes are only reachable through the internal API. The console
> and tenants cannot read the inventory, so the storage UI is blocked and tenants
> have no operational visibility. This enhancement adds the minimal read surface —
> `Get` and `List` — needed to unblock the console, without touching provisioning.
>
> ### Goals
>
> - Reuse the established public-wraps-private server pattern (as in
>   `external_ips_server.go`), adding no new data path.
> - Inherit tenant scoping and CEL filtering from the private server / generic DAO
>   rather than reimplementing them.
> - Expose only tenant-meaningful fields; keep internal routing (backend, protocol,
>   hub, vendor volume id) private.
> - Introduce no schema change — reuse the OSAC-2872 `volumes` table.
>
> ### Non-Goals
>
> - Volume lifecycle through the public API (create/update/delete/resize) — deferred
>   to later [OSAC-984](https://redhat.atlassian.net/browse/OSAC-984) phases.
> - Volume expansion, snapshots, clones, and restore —
>   [OSAC-48](https://redhat.atlassian.net/browse/OSAC-48).
> - Volume attach/detach —
>   [OSAC-4884](https://redhat.atlassian.net/browse/OSAC-4884).
> - Volume identifiability / provenance — deferred to
>   [OSAC-4793](https://redhat.atlassian.net/browse/OSAC-4793).
> - File storage ([OSAC-4515](https://redhat.atlassian.net/browse/OSAC-4515))
>   and object storage.

### D04: design.md:58 — Proposal

Classification: required behavior / deliverable. Destination: FR1–FR8 assertions below; non-test work and explicit exclusions in Gaps

> ## Proposal
>
> Enumerated changes, all in `fulfillment-service`:
>
> 1. **Public proto (generated from private via cleanapi).** Opt the private
>    `Volumes` service and `Volume` type into public generation; expose only `List`
>    and `Get`; strip the internal status fields (`backend`, `protocol`, `hub`,
>    `vendor_volume_id`) by annotating each with `[(cleanapi.field).private = true]`
>    on the private proto — cleanapi excludes annotated fields from the generated
>    public message, so a private field can only reach the public schema if someone
>    both adds it and forgets the annotation. A generated-schema test guards against
>    that (see Test Plan). The following private Volume fields carry
>    `[(cleanapi.field).private = true]` annotations on the private proto and are
>    excluded from the generated public message: `vendor_volume_id`, `backend`,
>    `protocol`, `hub`, and `vendor_context`.
>    `StorageProtocol`/`storage_common_type` stay fully private.
> 2. **Public `VolumesServer`** (`internal/servers/volumes_server.go`): delegates
>    `List`/`Get` to `PrivateVolumesServer`, maps private→public (dropping internal
>    fields), and sets the CEL filter descriptor to the public `Volume` so callers
>    can only filter on visible fields.
> 3. **Private server adjustment** (`private_volumes_server.go`): make the tier
>    resolver optional (it is used only by `Create`) so the read-only delegate can be
>    built without one; add `SetFilterDesc`.
> 4. **Wiring**: register the public `Volumes` gRPC service (`register_servers.go`)
>    and REST handler (`start_rest_gateway_cmd.go`).
> 5. **Authorization** (`authz.rego`): allow tenant clients on the public
>    `Volumes/Get` and `Volumes/List` methods.
>
> ### Workflow Description
>
> Actors: **Tenant User / Tenant Admin** (read their tenant's volumes via console or
> CLI), **Cloud Provider Admin** (read across all tenants). Starting state:
> volumes already exist and are inventoried by OSAC-2872.
>
> Request path:
>
> ```text
> HTTP/gRPC client
>   -> REST gateway (grpc-gateway mux)            [REST callers only]
>   -> gRPC interceptors: authn (JWT) -> authz (OPA) -> tenancy
>   -> public VolumesServer.List/Get
>   -> PrivateVolumesServer.List/Get
>   -> GenericServer[Volume] (tenant scoping + CEL filter) -> GenericDAO -> PostgreSQL
> ```
>
> Steps (List): the caller requests `GET /api/fulfillment/v1/volumes` (optionally
> with filter/order/offset/limit); OPA authorizes the method; the private delegate
> scopes rows to the caller's visible tenants and applies the CEL filter; the public
> server maps each row to the public shape and returns items + size + total. Get is
> the same by id, returning `NotFound` when the id is not visible/absent.
>
> ### API Extensions
>
> - New **public gRPC service** `osac.public.v1.Volumes` with `List` and `Get`, and
>   REST transcoding at `/api/fulfillment/v1/volumes` and `/{id}`.
> - New public `Volume` message (subset of the private one).
> - **Resource name (resolved):** the public collection is `volumes` (path
>   `/api/fulfillment/v1/volumes`), matching the private resource name and the
>   plural-noun convention used by every other public resource. An earlier draft
>   raised `block_volumes` as a candidate; it is not adopted — the public API mirrors
>   the private name, and file/block/object distinctions are carried in fields, not
>   the resource path.
> - No CRDs, webhooks, aggregated API servers, or finalizers. No change to any
>   externally-owned resource.

### D05: design.md:123 — UX Alignment

Classification: required behavior / deliverable. Destination: FR1–FR8 assertions below; non-test work and explicit exclusions in Gaps

> ## UX Alignment
>
> The `osac-ux` repo (whose hand-written `@temp-api` files an earlier draft of this
> section referenced) is **deprecated** (osac-project/osac-workspace#224) and is no
> longer a source of truth for UI types. The authoritative UI types live in
> **`osac-ui`** (`libs/types`) and are **generated directly from the backend proto**
> via `pnpm gen-types`.
>
> The public Volume API is net-new: `osac-ui` currently has only the *private*
> Volume types (generated from OSAC-2872) — no *public* Volume types exist yet,
> because this EP is what introduces them. Once this EP's public proto merges and
> `osac-ui` runs `gen-types`, the public `Volume` types are generated straight from
> this proto, so there are **no deviations to reconcile** by construction. The only
> UI-side action is regenerating types after this lands. (Confirmed with the UI owner.)
>
> ### Implementation Details/Notes/Constraints
>
> - The private→public field hiding is done by a `GenericMapper` with
>   `SetStrict(false)` — the copy silently omits fields absent from the public type
>   (the same mechanism `external_ips_server.go` uses). There is no `inMapper`
>   because there are no write RPCs.
> - `SetFilterDesc((*publicv1.Volume)(nil).ProtoReflect().Descriptor())` restricts
>   CEL filters to public fields, so a caller cannot filter on hidden fields such as
>   `status.backend`.
> - **`order` parameter:** the `List` request carries an `order` field (inherited
>   from the shared list-request shape), but the generic DAO currently ignores it and
>   always sorts by `id` (`generic_dao_list.go`). It is therefore *not* a private-field
>   exposure vector today. If server-side ordering is implemented later, it must be
>   translated against the same public descriptor as the filter so it cannot reference
>   hidden fields — called out here so the constraint is not lost.
>   The `order` parameter is validated against the public Volume schema; field names
>   not present in the public descriptor (e.g. private fields like `status.backend`)
>   are rejected. The GenericDAO currently sorts by `id` regardless of the requested
>   order — this is a known, documented limitation.
> - **cleanapi import pruning (tooling note):** cleanapi v0.0.8 copies imports
>   verbatim and does not prune those that become unused after fields/methods are
>   stripped (`storage_common_type` in the public `volume_type`, `field_mask` in the
>   public `volumes_service`); `buf lint` (`IMPORT_USED`) then rejects them. The two
>   unused imports are pruned by hand in the generated public protos, matching the
>   committed state of other read-only public resources (e.g.
>   `baremetal_instance_types_service`). A follow-up to automate this in
>   `dev.py build protos` (or bump cleanapi) is a candidate.
>
> ### Security Considerations
>
> Read-only endpoints; no new secrets or data-mutation paths. Tenant isolation is
> enforced by the existing tenancy layer (below). Internal routing fields that could
> leak backend topology are excluded from the public type by construction. Input is
> limited to an id and standard list parameters; CEL filters are constrained to the
> public field set.
>
> ### Failure Handling and Recovery
>
> - **Not found / not visible:** `Get` returns `NotFound`; `List` excludes rows
>   outside the caller's visible tenants.
> - **Invalid CEL filter / order:** returns `InvalidArgument` from the existing
>   filter translator.
> - **Mapping error:** returns `Internal` (logged); no partial data is returned.
> - **Delegate/DB errors:** propagated unchanged from the private server. No retries
>   or side effects (reads are idempotent).
>
> ### RBAC / Tenancy
>
> Scoping is inherited, not reimplemented. OPA (`authz.rego`) gates *method* access —
> this EP adds `Volumes/Get` and `Volumes/List` to the tenant-client allowlist.
> *Row* scoping comes from `GenericServer`/`GenericDAO` via
> `DefaultTenancyLogic.DetermineVisibleTenants`, which restricts results to the
> caller's tenants (plus shared). This is **tenant- and project-level** scoping — the same model
> every other resource uses; role does not change which rows are visible, only which
> methods may be called.
>
> Authorization matrix for this EP:
>
> | Actor | `Get` / `List` allowed? | Rows returned |
> |---|---|---|
> | Tenant User | Yes | All volumes in the caller's own tenant(s) (+ `shared`) |
> | Tenant Admin | Yes | Same as Tenant User — identical row scope |
> | Cloud Provider Admin | Yes | All volumes across all tenants, per `DetermineVisibleTenants` |
> | Unauthenticated | No | — (`Unauthenticated`) |
> | Mutating methods (`Create`/`Update`/`Delete`/`Signal`) | No public method exists | — (private API only) |
>
> Tenant User and Tenant Admin have identical read scope, consistent with OSAC-2872,
> where both roles share the same storage capabilities. A Cloud Provider Admin sees
> all tenants. The row predicate is the same `tenant IN (visible)` for everyone;
> there is no role-specific query path.
>
> ### Observability and Monitoring
>
> No new observability changes. Existing gRPC metrics, structured request logging,
> and the interceptor chain apply to the new methods automatically.
>
> ### Risks and Mitigations
>
> | Risk | Impact | Mitigation |
> |---|---|---|
> | cleanapi leaves unused imports in generated public protos | `buf lint` fails on regeneration | Prune the two imports (documented); follow-up to automate in tooling |
>
> ### Drawbacks
>
> Read-only is a partial capability — the console can display but not manage volumes
> until later phases.

### D06: design.md:225 — Alternatives (Not Implemented)

Classification: background or explicit exclusion. Destination: Background explains existing inventory/read-only intent; alternatives are rejected, non-goals are excluded; no test obligation added.

> ## Alternatives (Not Implemented)
>
> - **Hand-write the public proto.** Rejected — public protos are generated from
>   private via cleanapi by convention; hand-writing would diverge from every other
>   resource and drift on regeneration.
> - **Expose `protocol` (and thus `storage_common_type`) publicly** to avoid the
>   dangling-import problem. Rejected — protocol is an internal routing detail; the
>   import is pruned instead.
> - **Publish an empty public `storage_common_type`** so the import resolves.
>   Rejected — `buf lint IMPORT_USED` still fails, and it publishes a meaningless
>   type.

### D07: design.md:237 — Open Questions [optional]

Classification: background or explicit exclusion. Destination: Background explains existing inventory/read-only intent; alternatives are rejected, non-goals are excluded; no test obligation added.

> ## Open Questions [optional]
>
> None.

### D08: design.md:241 — Test Plan

Classification: required behavior / deliverable. Destination: FR1–FR8 assertions below; non-test work and explicit exclusions in Gaps

> ## Test Plan
>
> ### Unit Tests
> - Public `Get` returns the public projection; `List` returns items with size/total.
> - Field mapping: public `Volume` carries spec (tier/size/access mode) and status
>   (state/message); internal fields are absent by type.
> - **Generated-schema guard:** a test asserts the public `Volume` descriptor
>   contains *only* the intended public fields — i.e. none of `backend`, `protocol`,
>   `hub`, `vendor_volume_id` appear — so a future private field added without the
>   `private = true` annotation fails the build rather than silently leaking.
>   The generated-schema guard test uses an exact-field allowlist: it asserts the
>   public `Volume` descriptor contains precisely the expected set of fields (`id`,
>   `metadata`, `spec.storage_tier`, `spec.size_gib`, `spec.access_mode`,
>   `status.state`, `status.message`). A future private field added without
>   `[(cleanapi.field).private = true]` fails the build rather than silently leaking.
> - CEL filter over a public field (`status.state`) returns the expected subset.
> - **CEL filter over a private field is rejected:** a filter referencing
>   `status.backend` returns `InvalidArgument` (proves `SetFilterDesc` restricts the
>   public filter surface).
> - `Get` on a nonexistent id returns an error.
> - Authz: a tenant client is allowed on `Volumes/Get` + `/List` and denied on
>   (nonexistent) public `Volumes/Create` + `/Delete`.
> - Private server: builds without a tier resolver; `Create` without a resolver fails.
>
> ### Integration Tests
> - Against the kind `osac-dev` cluster: list/get standalone volumes created via the
>   private path through the public gRPC endpoint, asserting the public shape and
>   tenant scoping (a subject in tenant A does not see tenant B's volumes).
>
> ### E2E Tests
> - Add a read-path check to the osac-test-infra vmaas suite: provision a volume via
>   the existing path, then Get/List it through the public API and assert the public
>   representation and tenant-scoped visibility.

### D09: design.md:275 — Graduation Criteria

Classification: required behavior / deliverable. Destination: FR1–FR8 assertions below; non-test work and explicit exclusions in Gaps

> ## Graduation Criteria
>
> Ships as part of the public Volume API (0.3). No separate maturity ladder; the
> read endpoints graduate with the rest of the public API. Later OSAC-984 phases add
> the mutating lifecycle.

### D10: design.md:281 — Upgrade / Downgrade Strategy

Classification: required behavior / deliverable. Destination: FR1–FR8 assertions below; non-test work and explicit exclusions in Gaps

> ## Upgrade / Downgrade Strategy
>
> Additive, read-only API surface with no schema change. Upgrade adds the new
> endpoints; downgrade removes them with no data migration. No existing client must
> change to keep working.

### D11: design.md:287 — Version Skew Strategy

Classification: required behavior / deliverable. Destination: FR1–FR8 assertions below; non-test work and explicit exclusions in Gaps

> ## Version Skew Strategy
>
> The public API is generated from the private API and served by the same process;
> there is no cross-component skew. An older console simply does not call the new
> endpoints. The public `Volume` is a strict subset of the private type, so proto
> evolution follows the standard additive-field rules.

### D12: design.md:294 — Support Procedures

Classification: required behavior / deliverable. Destination: FR1–FR8 assertions below; non-test work and explicit exclusions in Gaps

> ## Support Procedures
>
> Failures surface as standard gRPC/REST errors (`NotFound`, `InvalidArgument`,
> `PermissionDenied`, `Internal`) visible in request logs. The endpoints can be
> effectively disabled by removing the `Volumes/Get`+`/List` entries from the OPA
> allowlist (callers then receive `PermissionDenied`); this affects only read access
> and has no effect on provisioning or running workloads.

### D13: design.md:302 — Infrastructure Needed [optional]

Classification: background or explicit exclusion. Destination: Background explains existing inventory/read-only intent; alternatives are rejected, non-goals are excluded; no test obligation added.

> ## Infrastructure Needed [optional]
>
> None.
>
> ---

### D14: design.md:308 — Provenance

Classification: background or explicit exclusion. Destination: Background explains existing inventory/read-only intent; alternatives are rejected, non-goals are excluded; no test obligation added.

> ## Provenance
>
> Committed: commit @ design 0.9.0 - f7f8c6d, workspace main @ b177ce9 (dirty)
>
> > Authoring phases not recorded this session (commit-time snapshot only).
>
> <!-- ai-workflow-provenance:{"schema_version":1,"provenance_kind":"commit_only","workflow":"design","workflow_version":"0.9.0","ai_workflows":"f7f8c6d","source_repo":"b177ce9 (dirty)","source_repo_branch":"main","commits_behind_main":0,"commits_ahead_main":0,"main_ref":"main","phases":["commit","commit","commit"],"authoring_modes":["skill"],"context_changed":false,"origin_untracked":false} -->

## Execution evidence matrix

The canonical ownership follows `docs/INTEGRATION-TESTING.md`, `fulfillment-service/AGENTS.md` and `tests/e2e/AGENTS.md`. No Envtest or Contract requirement is invented for this read-only API change. Static generation/lint checks supplement tests and are not an integration tier.

| Row | Behavior / requirements / cases | Component / owner / tier / boundary | Location and execution | Prerequisites and real/faked dependencies | Readiness / status / follow-up |
|---|---|---|---|---|---|
| E-U | FR1/2/5/8, IC1/3; TC-FR1-02, TC-FR2-02, TC-FR5-01, TC-FR5-02, TC-FR5-03, TC-FR8-01, TC-FR8-03 | fulfillment-service, DEV-READ [DEV], Unit; in-process public/private delegation, mapper and generated descriptor assertions | Proposed frozen-feature fixture file `fulfillment-service/internal/servers/volume_read_contract_test.go`, reusing patterns from existing `fulfillment-service/internal/servers/volumes_server_test.go`, `fulfillment-service/internal/servers/private_volumes_server_test.go`; fixtures in `fulfillment-service/internal/servers/servers_suite_test.go`. Existing command `ginkgo run --timeout 10m internal/servers`, cwd `fulfillment-service/`, defined in component AGENTS.md. New generator fault fixture proposed in same suite. Frozen descriptor/wiring and optional-resolver assertions use a separate historical feature fixture built from the retained read-only design; do not disable or replace current CRUD tests. Existing current-server read projection tests are extended alongside CRUD tests. This plan never claims current production schema is read-only. | Go/Ginkgo and suite database transaction setup required; database may be real as suite setup but assertions are in-process; tier resolver, mapper/delegate error seams simulated; no real provider/operator/AAP. | not run; suite paths exist but new frozen-contract cases proposed; current lifecycle code differs from frozen read-only oracle. Implementation work owned DEV-READ; no separate follow-up ticket allocated. |
| E-I | FR1/2/3/4/6/7, IC1/2/3; TC-FR1-01, TC-FR2-01, TC-FR3-01, TC-FR3-02, TC-FR3-03, TC-FR4-01, TC-FR4-02, TC-FR4-03, TC-FR6-01, TC-FR6-02, TC-FR7-01, TC-FR7-02 | fulfillment-service, DEV-READ [DEV], Integration (canonical component-integration); client→deployed API→JWT/OPA/tenancy→private delegate→PostgreSQL | Extend `fulfillment-service/it/it_public_volumes_test.go` and `fulfillment-service/it/it_volume_lifecycle_test.go`; clients/setup in `fulfillment-service/it/it_suite_test.go`. Existing command from root: `make -C osac-installer test PLATFORM=kind PROFILE=dev NS=osac SUITE=fulfillment`, defined in `osac-installer/Makefile` / `fulfillment-service/AGENTS.md`. | Dedicated fresh osac-dev Kind, KUBECONFIG, host mappings, install-infra and service image, real API/gateway/PostgreSQL/auth; private admin clients seed fixtures with DeferCleanup. Storage provider/operator/AAP omitted deliberately: this boundary validates inventory projection/isolation, not provisioning. CLI harness builds checkout CLI. Project restriction fixture extension proposed; use the concrete tenant/project setup below, with real Keycloak-issued JWTs and private ProjectMembership records; no mocked tenancy logic in this tier. | not run; existing harness available; extensions proposed; project fixture follows the concrete setup below; new helper remains proposed. DEV-READ owns implementation and fixture work; no separate follow-up ticket allocated. |
| E-E | FR8 and design E2E, IC1/2/3; TC-FR8-02 | tests/e2e, QE-READ [QE], E2E; provisioner/provider→inventory→public read→tenant client | Proposed `tests/e2e/storage/test_volume_public_reads.py`, following cleanup/polling in existing `tests/e2e/storage/test_tenant_storage_lifecycle.py`, `tests/e2e/vmaas/regression/test_compute_instance_storage_tier.py`, shared `tests/e2e/conftest.py`, `tests/e2e/storage/conftest.py`, `tests/e2e/core/grpc_client.py`, `tests/e2e/core/runner.py`. Proposed command `uv run pytest tests/e2e/storage/test_volume_public_reads.py`, cwd OSAC root (pytest execution pattern defined by tests/e2e/AGENTS.md; new file does not yet exist). | Real deployed fulfillment/PostgreSQL/auth, operator, AAP and real storage provider; selected provider is a real VAST backend (not mock VMS), with backend endpoint/credentials provisioned in the disposable lab configuration, private StorageBackend/StorageTier inventory and AAP templates configured; tenant A/B credentials, tier/backend, private volume provisioning client and cleanup helper to be added using the concrete lab setup below. No mocked provider or reconciliation. Enable storage controller and OSAC_STORAGE_BACKEND_AAP_PROVISION_TEMPLATE; set OSAC_NAMESPACE and OSAC_STORAGE_CONFIG_NAMESPACE as defined in storage/conftest.py, KUBECONFIG and authenticated API addresses as defined in tests/e2e/conftest.py. QE-READ adds private volume provisioning/public Get/List/cleanup methods to GRPCClient; these are proposed work. Fail environment preflight if real VAST is missing; skipped/mock-backed runs do not satisfy the boundary. Standard bounded polling, no product timing SLA invented. | not run; proposed harness, private provision/read helper additions and disposable full environment required. QE-READ owns work; QE-READ [QE] owns the proposed harness and private Volume gRPC client additions; no assigned person or separate infrastructure ticket exists, explicitly unresolved. This is disclosed setup work, not an omitted required E2E case. Existing storage lifecycle may use mock VMS; that variant cannot prove this real provider boundary. |
| E-M | FR7, IC1/2/3; TC-FR7-03 | osac-ui consumer, UI-READ [QE], E2E; manual deployed browser→gateway→service | Manual browser procedure in case; cwd N/A because browser execution; new UI consumer work OSAC-4546/4547, generated types under `osac-ui/libs/types` | Real console, API/auth/PostgreSQL, tenant credentials, seeded private volume; provisioning omitted because separate E-E proves it | not run; consumer UI delivery tracked [OSAC-4546](https://redhat.atlassian.net/browse/OSAC-4546) / [OSAC-4547](https://redhat.atlassian.net/browse/OSAC-4547); no result claimed |

Supplemental build validation: `make -C proto generate` and `make -C proto lint` from OSAC root, definitions `proto/Makefile` and `proto/AGENTS.md`; `pnpm gen-types` for UI per design. Generation is not a test tier. Never hand-edit generated files despite the historical design import-pruning note.

## Concrete setup work for E-I and E-E

These procedures are proposed implementation work owned by DEV-READ and QE-READ
under OSAC-4542. They identify the setup deliverable and boundary. They have not
been executed, and no new helper or lab is claimed to exist. The approved
read-only PRD/design remains the behavior oracle. References below use OSAC
commit `1411b33bfb0fa109e4299675b8038906df56b0b5`.

### Project-isolation setup: DEV-READ, component integration

1. Start the dedicated Kind fulfillment integration environment using E-I's
   existing installer command. Reuse the private admin connection and real
   Keycloak admin helper from `fulfillment-service/it/it_catalog_items_fixtures_test.go:494-553`
   (`createCatalogItemTenantAdminFixture`, `tool.KeycloakAdminRequest`). Add a
   proposed `createVolumeProjectReadFixture` helper to `it_public_volumes_test.go`.
2. Create unique tenants A and B with private `Tenants/Create`, await their
   synchronization, and create named projects project1/project3 in A and project2
   in B with private `Projects/Create`: metadata tenant and name, spec title.
   This shape is demonstrated by
   `fulfillment-service/internal/servers/private_projects_server_test.go:40-115`.
3. Create two ordinary test users in A through the real lab Keycloak admin API,
   leave one as an ordinary tenant member and grant the other the existing
   `tenant-admin` realm role using the fixture pattern, log in through
   `tool.makeKeycloakTokenSource`, and use `tool.makeGrpcConn` for the public
   connection. The existing login pattern is in
   `fulfillment-service/it/it_catalog_items_fixtures_test.go:872-892` (`createCatalogItemMemberFixture`). Keep each user's
   Fulfillment User ID after first authentication. Do not use a provider-admin
   token or the break-glass account for the restricted subjects.
4. Using private `ProjectMemberships/Create`, set metadata tenant=A,
   project=project1, a unique name, spec role=VIEWER and spec users containing
   each user's ID. Wait for membership status READY, then obtain fresh JWTs.
   The authoritative shapes and state are in
   `proto/private/osac/private/v1/project_membership_type.proto`; reconciliation
   is in `fulfillment-service/internal/controllers/projectmembership/project_membership_reconciler_function.go:245-328`.
   Do not grant project3 or B to either subject.
5. Preflight the authenticated entitlements: the JWT organization claim for A
   includes `/project1/system:viewers`, excludes project3, and neither user has
   universal tenant access. `fulfillment-service/internal/auth/default_tenancy_logic.go`
   (`DetermineVisibility`, `addProjectsFromTenantGroups`) consumes these grants;
   its test `Includes projects from Keycloak groups in JWT token` in
   `default_tenancy_logic_test.go` establishes the exact claim shape. Existing
   `auth_visibility.go` grants A's default project independently, so no assertion
   equates project1 membership with exclusion of the default project.
6. Seed volumes through the private Volume client with metadata tenant/project
   set explicitly, then capture returned IDs as vol-a, vol-b and vol-c. Reuse
   backend/tier seeding and DeferCleanup from `it_public_volumes_test.go` while
   keeping provider execution omitted for this inventory boundary. Run
   TC-FR4-01 as both users. Exercise the real deployed JWT/OPA/DAO path; the
   mocked `Generic DAO visibility` tests are supporting examples only.
7. Register cleanup immediately after each successful Create. Delete volumes,
   memberships, users, projects and tenants in dependency order, await absence,
   close connections, and report cleanup failures. Existing tenant fixture
   cleanup is in `createCatalogItemTenantAdminFixture`. The new helper must
   implement this cleanup before the case becomes execution-ready.

### Real storage lab setup: QE-READ, E2E

1. QE-READ prepares a disposable deployment with real fulfillment/database/auth,
   the OSAC operator, AAP and an allocated real VAST block-storage backend.
   Obtain endpoint/credentials from the lab administrator at runtime. No lab
   allocation, assigned person, credentials or infrastructure ticket is present
   in this repository; allocation remains an explicit execution prerequisite.
   No mocked VMS endpoint may be used for this case.
2. Register the backend through private `StorageBackends/Create`: provider=vast,
   real management endpoint, username and exactly one password source. Use
   `proto/private/osac/private/v1/storage_backend_type.proto` for credential
   validation. Register a block StorageTier associated with that returned
   backend ID, following `it_public_volumes_test.go`. Keep admin credentials in
   the private backend API; `osac-aap/config/base/secret-storage-operations-ig-example.yaml`
   explicitly excludes copying VAST admin credentials into tenant secrets.
3. Deploy/configure the real VAST CSI controller endpoint; enable the operator
   volume controller (`OSAC_ENABLE_VOLUME_CONTROLLER`) and provider routing
   (`OSAC_VENDOR_CONTROLLERS` with the vast provider and actual controller
   endpoint). Existing parsing/registration is in `osac-operator/cmd/main.go:737-870`
   (`parseVendorControllers`, `setupVolumeControllers`,
   `newVendorProvisionerRegistry`), with environment names in
   `osac-operator/cmd/main.go:80-150`. This is runtime lab configuration, not a
   proposed new installer value or a networking API change.
4. Configure AAP's existing tenant storage onboarding templates and enable the
   storage controller. Onboard test tenants and await StorageBackendReady using
   `tests/e2e/storage/test_tenant_storage_lifecycle.py`. Verify the per-tenant hub
   configuration exists in OSAC_STORAGE_CONFIG_NAMESPACE and the selected tier
   has its VAST view/subsystem. The exact required hub-secret keys and subsystem
   construction are in `osac-operator/internal/controller/vast_vendor_provisioner.go`
   (`readTenantCreds`, `CreateVolume`). Check presence and readiness without
   emitting credential values. Lab routing and tenant storage resources are
   prerequisites supplied by onboarding, not new networking test requirements.
5. Add the proposed private Volume Create/Get/Delete and public Get/List wrappers
   to `tests/e2e/core/grpc_client.py`, following its existing `call` and storage-tier
   wrappers. Create a standalone A volume through the private path, register
   cleanup immediately, and await provider-backed readiness through actual
   operator feedback. Run TC-FR8-02 with real A/B authenticated clients.
6. Preflight requires actual provider routing, successful onboarding and reachable
   real CSI/VAST services. A missing environment fails preflight; the storage
   suite's existing skip mechanism in `tests/e2e/storage/conftest.py` must not be
   reported as passing TC-FR8-02. A fake provider can support lower tiers only.
7. In finally, delete the private volume and await both inventory absence and
   vendor deletion, then remove temporary tenant/tier/backend resources in
   reverse dependency order. Retain sanitized resource IDs, timing, observations
   and cleanup outcome as execution evidence. Use existing bounded polling
   patterns; the runner timeout is operational and establishes no product SLA.

## Test Cases

### FR1: local approved behavior group

#### TC-FR1-01: Read public projection

| Story | AC | Priority | Automation | Tier | Owner | Evidence |
|---|---|---|---|---|---|---|
| DEV-READ | FR1 local alias, IC1, IC3 | high | automated | Integration | [DEV] | E-I |

##### Preconditions

- A private-path standalone volume id=vol-a, name=alpha in tenant A, tier=gold, size_gib=10, access_mode=READ_WRITE_ONCE, state=available, message=ready.

##### Steps

1. As tenant A, call public Volumes.Get(id=vol-a), then Volumes.List.

##### Expected Results

- **A-FR1-01-1**: Get returns id=vol-a and name=alpha.
- **A-FR1-01-2**: Get returns spec.storage_tier=gold, spec.size_gib=10, spec.access_mode=READ_WRITE_ONCE.
- **A-FR1-01-3**: Get returns status.state=available and status.message=ready.
- **A-FR1-01-4**: List contains the same public projection, with size equal to returned items and total equal to all matching visible rows.

#### TC-FR1-02: No public mutations

| Story | AC | Priority | Automation | Tier | Owner | Evidence |
|---|---|---|---|---|---|---|
| DEV-READ | FR1 local alias, IC1, IC2 | high | automated | Unit | [DEV] | E-U |

##### Preconditions

- The frozen feature public service descriptor is generated.

##### Steps

1. Inspect public Volumes descriptor and REST specification; attempt dispatch of Create, Update, Delete, Signal and Resize through the public service.

##### Expected Results

- **A-FR1-02-1**: The descriptor contains exactly Get and List.
- **A-FR1-02-2**: No public mutation routes are registered; dispatch has no public method.
- **A-FR1-02-3**: Private lifecycle setup remains available; this fixture adds no public lifecycle test.

### FR2: local approved behavior group

#### TC-FR2-01: Immutable id and request key

| Story | AC | Priority | Automation | Tier | Owner | Evidence |
|---|---|---|---|---|---|---|
| DEV-READ | FR2 local alias, IC1, IC3 | high | automated | Integration | [DEV] | E-I |

##### Preconditions

- Private fixture vol-a has system-generated id, metadata.name=alpha, display_name=Human Alpha.

##### Steps

1. List; Get by returned id; Get using alpha or Human Alpha as request id; repeat Get/List without writes.

##### Expected Results

- **A-FR2-01-1**: List returns a nonempty system-generated id.
- **A-FR2-01-2**: Get by that id returns the same object.
- **A-FR2-01-3**: Get using name or display_name as id returns NotFound.
- **A-FR2-01-4**: Repeated reads preserve the id and name.

#### TC-FR2-02: Scoped names and optional display labels

| Story | AC | Priority | Automation | Tier | Owner | Evidence |
|---|---|---|---|---|---|---|
| DEV-READ | FR2 local alias, IC1, IC3 | high | automated | Unit | [DEV] | E-U |

##### Preconditions

- Use existing private fixture setup for tenant/project A and B; create RFC1123 name alpha in each scope, one with no display_name.

##### Steps

1. Inspect private fixture validation; reject Alpha! and duplicate alpha within A; read both valid objects through public Get with entitled subjects.

##### Expected Results

- **A-FR2-02-1**: Invalid RFC1123 name Alpha! is rejected by fixture validation.
- **A-FR2-02-2**: Duplicate alpha within one tenant/project scope is rejected.
- **A-FR2-02-3**: Equal names in distinct authorized scopes have distinct ids.
- **A-FR2-02-4**: The public projection preserves name alpha and permits an absent display_name; a supplied label is not the lookup key.

### FR3: local approved behavior group

#### TC-FR3-01: Pagination and counts

| Story | AC | Priority | Automation | Tier | Owner | Evidence |
|---|---|---|---|---|---|---|
| DEV-READ | FR3 local alias, IC1 | high | automated | Integration | [DEV] | E-I |

##### Preconditions

- Five visible volumes ids sorted a,b,c,d,e; another tenant has one hidden volume.

##### Steps

1. List(offset=1,limit=2); List with offset beyond total; List without filter.

##### Expected Results

- **A-FR3-01-1**: Page contains b,c; size=2 and total=5.
- **A-FR3-01-2**: Past-end page has no items and size=0, total=5.
- **A-FR3-01-3**: Hidden tenant row never contributes to items, size or total.

#### TC-FR3-02: Public CEL and invalid input

| Story | AC | Priority | Automation | Tier | Owner | Evidence |
|---|---|---|---|---|---|---|
| DEV-READ | FR3 local alias, IC1 | high | automated | Integration | [DEV] | E-I |

##### Preconditions

- Visible records in creating, available and deleting; private status.backend=secret-backend.

##### Steps

1. List(filter='this.status.state == "available"'); List with invalid CEL and filter referencing this.status.backend.

##### Expected Results

- **A-FR3-02-1**: Public state filter returns only available rows.
- **A-FR3-02-2**: Malformed CEL returns InvalidArgument.
- **A-FR3-02-3**: Private-field CEL returns InvalidArgument and no private data.

#### TC-FR3-03: SQL ordering and tie break

| Story | AC | Priority | Automation | Tier | Owner | Evidence |
|---|---|---|---|---|---|---|
| DEV-READ | FR3 local alias, IC1 | high | automated | Integration | [DEV] | E-I |

##### Preconditions

- Three visible records: id=a,size=20; id=c,size=10; id=b,size=10.

##### Steps

1. List(order="spec.size_gib asc"); List(order="spec.size_gib desc"); List(order="status.backend asc").

##### Expected Results

- **A-FR3-03-1**: Ascending size order is b,c,a, with implicit secondary id asc.
- **A-FR3-03-2**: Descending size order is a,b,c, retaining secondary id asc.
- **A-FR3-03-3**: Private-field order returns InvalidArgument. This is the approved PRD oracle despite the design describing historical DAO drift.

### FR4: local approved behavior group

#### TC-FR4-01: Tenant and project isolation

| Story | AC | Priority | Automation | Tier | Owner | Evidence |
|---|---|---|---|---|---|---|
| DEV-READ | FR4 local alias, IC1 | high | automated | Integration | [DEV] | E-I |

##### Preconditions

- Follow the project-isolation setup below. Private Create returns IDs aliased as vol-a (A/project1), vol-b (B/project2), and vol-c (A/project3). Two real Keycloak users in A have identical project1-only grants, one Tenant User and one Tenant Admin. Their default project remains visible under the existing tenancy contract; this case seeds no default-project volume.

##### Steps

1. As A/project1 call List and Get(vol-a), Get(vol-b), Get(vol-c), Get(missing). Repeat with Tenant User and Tenant Admin credentials with identical entitlements.

##### Expected Results

- **A-FR4-01-1**: List includes vol-a and excludes vol-b and vol-c for both roles.
- **A-FR4-01-2**: Get(vol-a) succeeds for both roles.
- **A-FR4-01-3**: Invisible vol-b/vol-c and nonexistent missing all return NotFound, with no existence leak.
- **A-FR4-01-4**: Tenant User and Tenant Admin have identical row visibility for identical entitlements. Fixture setup must establish project restrictions through the existing tenancy mechanism; no invented API parameter.

#### TC-FR4-02: Shared and provider administration

| Story | AC | Priority | Automation | Tier | Owner | Evidence |
|---|---|---|---|---|---|---|
| DEV-READ | FR4 local alias, IC1 | high | automated | Integration | [DEV] | E-I |

##### Preconditions

- Volumes in tenants A, B and shared, subjects with standard tenant memberships plus a Cloud Provider Admin.

##### Steps

1. As tenant A List/Get shared and B volumes; repeat as provider admin.

##### Expected Results

- **A-FR4-02-1**: Tenant A can read its own and shared volumes but cannot read B volumes.
- **A-FR4-02-2**: Cloud Provider Admin List/Get can read A, B and shared volumes.
- **A-FR4-02-3**: Method authorization does not introduce a role-specific row query.

#### TC-FR4-03: Unauthenticated and disabled access

| Story | AC | Priority | Automation | Tier | Owner | Evidence |
|---|---|---|---|---|---|---|
| DEV-READ | FR4 local alias, IC1 | high | automated | Integration | [DEV] | E-I |

##### Preconditions

- Public service with real JWT and OPA interceptors; a dedicated test deployment allows policy restoration.

##### Steps

1. Call Get/List without authentication. In the disposable deployment remove public Volumes/Get and Volumes/List from allowlist, call as tenant, restore policy.

##### Expected Results

- **A-FR4-03-1**: Unauthenticated calls return Unauthenticated.
- **A-FR4-03-2**: Authenticated denied methods return PermissionDenied.
- **A-FR4-03-3**: Disabling read access does not mutate existing volumes or disrupt provisioned workloads; policy is restored.

### FR5: local approved behavior group

#### TC-FR5-01: Exact generated-schema allowlist

| Story | AC | Priority | Automation | Tier | Owner | Evidence |
|---|---|---|---|---|---|---|
| DEV-READ | FR5 local alias, IC3 | high | automated | Unit | [DEV] | E-U |

##### Preconditions

- Generated public descriptors from the frozen read-only contract.

##### Steps

1. Recursively compare Volume descriptor to exact public field allowlist; simulate a private-field addition lacking annotation in a generator regression fixture.

##### Expected Results

- **A-FR5-01-1**: Allowed public fields are exactly id, metadata, spec.storage_tier, spec.size_gib, spec.access_mode, status.state, status.message (metadata follows the shared public metadata contract).
- **A-FR5-01-2**: backend, protocol, hub, vendor_volume_id and vendor_context are absent.
- **A-FR5-01-3**: The generator regression fails its exact allowlist assertion when an unannotated private field appears; generated production files are never hand-edited.

#### TC-FR5-02: Mapper drops routing details

| Story | AC | Priority | Automation | Tier | Owner | Evidence |
|---|---|---|---|---|---|---|
| DEV-READ | FR5 local alias, IC3 | high | automated | Unit | [DEV] | E-U |

##### Preconditions

- Private object contains all five internal fields plus public spec/status and metadata.

##### Steps

1. Map private object with GenericMapper SetStrict(false); inspect resulting public protobuf and JSON.

##### Expected Results

- **A-FR5-02-1**: All tenant-meaningful fields remain equal to private values.
- **A-FR5-02-2**: None of backend, protocol, hub, vendor_volume_id, vendor_context are present in public output.
- **A-FR5-02-3**: No input mapper or writes are used for Get/List.

#### TC-FR5-03: Mapping and delegate errors

| Story | AC | Priority | Automation | Tier | Owner | Evidence |
|---|---|---|---|---|---|---|
| DEV-READ | FR5 local alias, IC1, IC3 | high | automated | Unit | [DEV] | E-U |

##### Preconditions

- Test seams for a mapper error and delegate/DB errors, with call counters.

##### Steps

1. Call Get and List with mapper failing; separately inject delegate codes Unavailable and Internal; repeat successful reads.

##### Expected Results

- **A-FR5-03-1**: Mapper failures return Internal and no partial public data; errors are logged.
- **A-FR5-03-2**: Delegate codes are propagated unchanged.
- **A-FR5-03-3**: Each read delegates once with no retry or write side effect; repeated reads leave inventory unchanged.

### FR6: local approved behavior group

#### TC-FR6-01: All active states and explicit filter

| Story | AC | Priority | Automation | Tier | Owner | Evidence |
|---|---|---|---|---|---|---|
| DEV-READ | FR6 local alias, IC1, IC3 | high | automated | Integration | [DEV] | E-I |

##### Preconditions

- Private path seeds creating vol-a, available vol-b, deleting vol-c.

##### Steps

1. Get each id and List unfiltered; List with explicit available filter.

##### Expected Results

- **A-FR6-01-1**: Unfiltered List contains all three active states, without another implicit state filter.
- **A-FR6-01-2**: Get returns the corresponding state for each id.
- **A-FR6-01-3**: Explicit state filter returns only vol-b; deleting remains readable until archival.

#### TC-FR6-02: Archived boundary

| Story | AC | Priority | Automation | Tier | Owner | Evidence |
|---|---|---|---|---|---|---|
| DEV-READ | FR6 local alias, IC1, IC3 | high | automated | Integration | [DEV] | E-I |

##### Preconditions

- Private storage lifecycle fixture transitions vol-c from deleting to archived deleted.

##### Steps

1. Read vol-c while deleting; archive through existing private test setup; then List and Get(vol-c).

##### Expected Results

- **A-FR6-02-1**: Deleting object is readable before archival.
- **A-FR6-02-2**: After archival List excludes vol-c.
- **A-FR6-02-3**: After archival Get(vol-c) returns NotFound.

### FR7: local approved behavior group

#### TC-FR7-01: REST and gRPC registration

| Story | AC | Priority | Automation | Tier | Owner | Evidence |
|---|---|---|---|---|---|---|
| DEV-READ | FR7 local alias, IC1, IC2, IC3 | high | automated | Integration | [DEV] | E-I |

##### Preconditions

- Service and grpc-gateway expose the public endpoint with valid tenant credentials and vol-a.

##### Steps

1. GET /api/fulfillment/v1/volumes and /api/fulfillment/v1/volumes/vol-a; compare with public gRPC List/Get; exercise filter/order/offset/limit through REST.

##### Expected Results

- **A-FR7-01-1**: Both REST routes are registered and return the same public object/counts as gRPC.
- **A-FR7-01-2**: List query parameters produce the same filtered, ordered and paged result as gRPC.
- **A-FR7-01-3**: Requests use standard JWT/OPA/tenancy path and no storage-specific endpoint.

#### TC-FR7-02: CLI and console read navigation

| Story | AC | Priority | Automation | Tier | Owner | Evidence |
|---|---|---|---|---|---|---|
| DEV-READ | FR7 local alias, IC3 (CLI/UI consumer) | high | automated | Integration | [DEV] | E-I |

##### Preconditions

- A deployed service and CLI built from checkout; Console UI consumers tracked separately in OSAC-4546/4547.

##### Steps

1. Run osac get volumes and osac get volume <id> through the existing CLI harness with tenant credentials; inspect generated public UI types and read-view navigation artifact.

##### Expected Results

- **A-FR7-02-1**: CLI lists visible public volumes and gets the object keyed by id.
- **A-FR7-02-2**: Neither name nor display_name substitutes for id in Get.
- **A-FR7-02-3**: Public UI types derive from the backend proto; list/detail consumers use id for deep links and the standard public API. Separate UI delivery belongs to OSAC-4546/4547, with UI navigation verified manually in TC-FR7-03 below.

#### TC-FR7-03: Console deep-link consumer

| Story | AC | Priority | Automation | Tier | Owner | Evidence |
|---|---|---|---|---|---|---|
| UI-READ | FR7 local alias, IC3 (console consumer) | high | manual | E2E | [QE] | E-M |

##### Preconditions

- A deployed console using regenerated public types, real backend, tenant A login and vol-a; UI work delivered by OSAC-4546/4547.

##### Steps

1. Open storage list, click alpha, copy detail URL, reload URL, then inspect network request; log out and re-open.

##### Expected Results

- **A-FR7-03-1**: List shows visible volume alpha.
- **A-FR7-03-2**: Detail URL and public Get request carry vol-a id, not alpha/display_name.
- **A-FR7-03-3**: Details show public tier/size/state and no internal routing fields.
- **A-FR7-03-4**: Unauthenticated session cannot fetch the object.

### FR8: local approved behavior group

#### TC-FR8-01: Private resolver optional for reads

| Story | AC | Priority | Automation | Tier | Owner | Evidence |
|---|---|---|---|---|---|---|
| DEV-READ | FR8 local alias, IC1, IC3 | high | automated | Unit | [DEV] | E-U |

##### Preconditions

- PrivateVolumesServer configured with required logger/DAO/tenancy but no tier resolver.

##### Steps

1. Build server; call Get/List on seeded rows; call private Create without resolver.

##### Expected Results

- **A-FR8-01-1**: The private server builds without a tier resolver.
- **A-FR8-01-2**: Get/List work without invoking tier resolution.
- **A-FR8-01-3**: Create without a resolver fails, with no new volume persisted.

#### TC-FR8-02: Provision then public read

| Story | AC | Priority | Automation | Tier | Owner | Evidence |
|---|---|---|---|---|---|---|
| QE-READ | FR8 local alias, IC1, IC3 | high | automated | E2E | [QE] | E-E |

##### Preconditions

- Disposable deployed OSAC with real fulfillment, PostgreSQL, auth, operator, AAP and storage provider; tenant A and B credentials and a pre-existing private volume provisioning path.

##### Steps

1. Using existing private provisioning path create an A standalone volume; poll its actual inventory state with bounded runner; Get/List through public API as A and B; teardown through existing private path in finally.

##### Expected Results

- **A-FR8-02-1**: The real provisioned volume becomes readable by A under its immutable id.
- **A-FR8-02-2**: Public fields reflect the provisioned tier, size, access mode, state and message.
- **A-FR8-02-3**: Internal routing fields never appear.
- **A-FR8-02-4**: B List excludes the volume and B Get returns NotFound.
- **A-FR8-02-5**: Private teardown completes and archived volume is absent; this scenario cannot be replaced by fake provider responses.

#### TC-FR8-03: API artifacts and additive compatibility

| Story | AC | Priority | Automation | Tier | Owner | Evidence |
|---|---|---|---|---|---|---|
| DEV-READ | FR8 local alias, IC1, IC2, IC3 | high | automated | Unit | [DEV] | E-U |

##### Preconditions

- Generated public API spec and service registration; existing unrelated resource fixtures.

##### Steps

1. Check generated spec routes and field descriptors, compare migration/schema artifacts before/after read-only change; call existing resource clients.

##### Expected Results

- **A-FR8-03-1**: Published API docs/spec contain GET /api/fulfillment/v1/volumes and /{id}, public fields, and no public Volume mutation operation.
- **A-FR8-03-2**: No database migration, CRD, webhook, aggregated server or finalizer is added by this read-only feature.
- **A-FR8-03-3**: Existing resource clients keep working; an old console need not call new endpoints.
- **A-FR8-03-4**: Downgrade removes read endpoint registration without migrating or removing inventory data; verify in isolated wiring fixture.

## Assertion-to-result audit

Every result above is independently falsifiable. Stable assertion IDs refer to exact result bullets; this audit preserves the written observation rather than claiming mere case-link coverage. Source group links below refer to the exact retained sections in the source-clause ledger.

| Assertion | Approved source section | TC / exact Expected Result | Verdict |
|---|---|---|---|
| A-FR1-01-1 | PRD In Scope; design Summary / Proposal | TC-FR1-01 ER1: Get returns id=vol-a and name=alpha. | preserved |
| A-FR1-01-2 | PRD In Scope; design Summary / Proposal | TC-FR1-01 ER2: Get returns spec.storage_tier=gold, spec.size_gib=10, spec.access_mode=READ_WRITE_ONCE. | preserved |
| A-FR1-01-3 | PRD In Scope; design Summary / Proposal | TC-FR1-01 ER3: Get returns status.state=available and status.message=ready. | preserved |
| A-FR1-01-4 | PRD In Scope; design Summary / Proposal | TC-FR1-01 ER4: List contains the same public projection, with size equal to returned items and total equal to all matching visible rows. | preserved |
| A-FR1-02-1 | PRD In Scope; design Summary / Proposal | TC-FR1-02 ER1: The descriptor contains exactly Get and List. | preserved |
| A-FR1-02-2 | PRD In Scope; design Summary / Proposal | TC-FR1-02 ER2: No public mutation routes are registered; dispatch has no public method. | preserved |
| A-FR1-02-3 | PRD In Scope; design Summary / Proposal | TC-FR1-02 ER3: Private lifecycle setup remains available; this fixture adds no public lifecycle test. | preserved |
| A-FR2-01-1 | PRD Stable public identifier / Acceptance Criteria | TC-FR2-01 ER1: List returns a nonempty system-generated id. | preserved |
| A-FR2-01-2 | PRD Stable public identifier / Acceptance Criteria | TC-FR2-01 ER2: Get by that id returns the same object. | preserved |
| A-FR2-01-3 | PRD Stable public identifier / Acceptance Criteria | TC-FR2-01 ER3: Get using name or display_name as id returns NotFound. | preserved |
| A-FR2-01-4 | PRD Stable public identifier / Acceptance Criteria | TC-FR2-01 ER4: Repeated reads preserve the id and name. | preserved |
| A-FR2-02-1 | PRD Stable public identifier / Acceptance Criteria | TC-FR2-02 ER1: Invalid RFC1123 name Alpha! is rejected by fixture validation. | preserved |
| A-FR2-02-2 | PRD Stable public identifier / Acceptance Criteria | TC-FR2-02 ER2: Duplicate alpha within one tenant/project scope is rejected. | preserved |
| A-FR2-02-3 | PRD Stable public identifier / Acceptance Criteria | TC-FR2-02 ER3: Equal names in distinct authorized scopes have distinct ids. | preserved |
| A-FR2-02-4 | PRD Stable public identifier / Acceptance Criteria | TC-FR2-02 ER4: The public projection preserves name alpha and permits an absent display_name; a supplied label is not the lookup key. | preserved |
| A-FR3-01-1 | PRD Acceptance Criteria; design Workflow / Constraints / Failure Handling | TC-FR3-01 ER1: Page contains b,c; size=2 and total=5. | preserved |
| A-FR3-01-2 | PRD Acceptance Criteria; design Workflow / Constraints / Failure Handling | TC-FR3-01 ER2: Past-end page has no items and size=0, total=5. | preserved |
| A-FR3-01-3 | PRD Acceptance Criteria; design Workflow / Constraints / Failure Handling | TC-FR3-01 ER3: Hidden tenant row never contributes to items, size or total. | preserved |
| A-FR3-02-1 | PRD Acceptance Criteria; design Workflow / Constraints / Failure Handling | TC-FR3-02 ER1: Public state filter returns only available rows. | preserved |
| A-FR3-02-2 | PRD Acceptance Criteria; design Workflow / Constraints / Failure Handling | TC-FR3-02 ER2: Malformed CEL returns InvalidArgument. | preserved |
| A-FR3-02-3 | PRD Acceptance Criteria; design Workflow / Constraints / Failure Handling | TC-FR3-02 ER3: Private-field CEL returns InvalidArgument and no private data. | preserved |
| A-FR3-03-1 | PRD Acceptance Criteria; design Workflow / Constraints / Failure Handling | TC-FR3-03 ER1: Ascending size order is b,c,a, with implicit secondary id asc. | preserved |
| A-FR3-03-2 | PRD Acceptance Criteria; design Workflow / Constraints / Failure Handling | TC-FR3-03 ER2: Descending size order is a,b,c, retaining secondary id asc. | preserved |
| A-FR3-03-3 | PRD Acceptance Criteria; design Workflow / Constraints / Failure Handling | TC-FR3-03 ER3: Private-field order returns InvalidArgument. This is the approved PRD oracle despite the design describing historical DAO drift. | preserved |
| A-FR4-01-1 | PRD Visibility / User Stories / Acceptance Criteria; design RBAC / Support Procedures | TC-FR4-01 ER1: List includes vol-a and excludes vol-b and vol-c for both roles. | preserved |
| A-FR4-01-2 | PRD Visibility / User Stories / Acceptance Criteria; design RBAC / Support Procedures | TC-FR4-01 ER2: Get(vol-a) succeeds for both roles. | preserved |
| A-FR4-01-3 | PRD Visibility / User Stories / Acceptance Criteria; design RBAC / Support Procedures | TC-FR4-01 ER3: Invisible vol-b/vol-c and nonexistent missing all return NotFound, with no existence leak. | preserved |
| A-FR4-01-4 | PRD Visibility / User Stories / Acceptance Criteria; design RBAC / Support Procedures | TC-FR4-01 ER4: Tenant User and Tenant Admin have identical row visibility for identical entitlements. Fixture setup must establish project restrictions through the existing tenancy mechanism; no invented API parameter. | preserved |
| A-FR4-02-1 | PRD Visibility / User Stories / Acceptance Criteria; design RBAC / Support Procedures | TC-FR4-02 ER1: Tenant A can read its own and shared volumes but cannot read B volumes. | preserved |
| A-FR4-02-2 | PRD Visibility / User Stories / Acceptance Criteria; design RBAC / Support Procedures | TC-FR4-02 ER2: Cloud Provider Admin List/Get can read A, B and shared volumes. | preserved |
| A-FR4-02-3 | PRD Visibility / User Stories / Acceptance Criteria; design RBAC / Support Procedures | TC-FR4-02 ER3: Method authorization does not introduce a role-specific row query. | preserved |
| A-FR4-03-1 | PRD Visibility / User Stories / Acceptance Criteria; design RBAC / Support Procedures | TC-FR4-03 ER1: Unauthenticated calls return Unauthenticated. | preserved |
| A-FR4-03-2 | PRD Visibility / User Stories / Acceptance Criteria; design RBAC / Support Procedures | TC-FR4-03 ER2: Authenticated denied methods return PermissionDenied. | preserved |
| A-FR4-03-3 | PRD Visibility / User Stories / Acceptance Criteria; design RBAC / Support Procedures | TC-FR4-03 ER3: Disabling read access does not mutate existing volumes or disrupt provisioned workloads; policy is restored. | preserved |
| A-FR5-01-1 | PRD Representation; design Proposal / Constraints / Failure Handling / Unit Tests | TC-FR5-01 ER1: Allowed public fields are exactly id, metadata, spec.storage_tier, spec.size_gib, spec.access_mode, status.state, status.message (metadata follows the shared public metadata contract). | preserved |
| A-FR5-01-2 | PRD Representation; design Proposal / Constraints / Failure Handling / Unit Tests | TC-FR5-01 ER2: backend, protocol, hub, vendor_volume_id and vendor_context are absent. | preserved |
| A-FR5-01-3 | PRD Representation; design Proposal / Constraints / Failure Handling / Unit Tests | TC-FR5-01 ER3: The generator regression fails its exact allowlist assertion when an unannotated private field appears; generated production files are never hand-edited. | preserved |
| A-FR5-02-1 | PRD Representation; design Proposal / Constraints / Failure Handling / Unit Tests | TC-FR5-02 ER1: All tenant-meaningful fields remain equal to private values. | preserved |
| A-FR5-02-2 | PRD Representation; design Proposal / Constraints / Failure Handling / Unit Tests | TC-FR5-02 ER2: None of backend, protocol, hub, vendor_volume_id, vendor_context are present in public output. | preserved |
| A-FR5-02-3 | PRD Representation; design Proposal / Constraints / Failure Handling / Unit Tests | TC-FR5-02 ER3: No input mapper or writes are used for Get/List. | preserved |
| A-FR5-03-1 | PRD Representation; design Proposal / Constraints / Failure Handling / Unit Tests | TC-FR5-03 ER1: Mapper failures return Internal and no partial public data; errors are logged. | preserved |
| A-FR5-03-2 | PRD Representation; design Proposal / Constraints / Failure Handling / Unit Tests | TC-FR5-03 ER2: Delegate codes are propagated unchanged. | preserved |
| A-FR5-03-3 | PRD Representation; design Proposal / Constraints / Failure Handling / Unit Tests | TC-FR5-03 ER3: Each read delegates once with no retry or write side effect; repeated reads leave inventory unchanged. | preserved |
| A-FR6-01-1 | PRD Acceptance Criteria | TC-FR6-01 ER1: Unfiltered List contains all three active states, without another implicit state filter. | preserved |
| A-FR6-01-2 | PRD Acceptance Criteria | TC-FR6-01 ER2: Get returns the corresponding state for each id. | preserved |
| A-FR6-01-3 | PRD Acceptance Criteria | TC-FR6-01 ER3: Explicit state filter returns only vol-b; deleting remains readable until archival. | preserved |
| A-FR6-02-1 | PRD Acceptance Criteria | TC-FR6-02 ER1: Deleting object is readable before archival. | preserved |
| A-FR6-02-2 | PRD Acceptance Criteria | TC-FR6-02 ER2: After archival List excludes vol-c. | preserved |
| A-FR6-02-3 | PRD Acceptance Criteria | TC-FR6-02 ER3: After archival Get(vol-c) returns NotFound. | preserved |
| A-FR7-01-1 | PRD Same access channels; design API Extensions / UX Alignment | TC-FR7-01 ER1: Both REST routes are registered and return the same public object/counts as gRPC. | preserved |
| A-FR7-01-2 | PRD Same access channels; design API Extensions / UX Alignment | TC-FR7-01 ER2: List query parameters produce the same filtered, ordered and paged result as gRPC. | preserved |
| A-FR7-01-3 | PRD Same access channels; design API Extensions / UX Alignment | TC-FR7-01 ER3: Requests use standard JWT/OPA/tenancy path and no storage-specific endpoint. | preserved |
| A-FR7-02-1 | PRD Same access channels; design API Extensions / UX Alignment | TC-FR7-02 ER1: CLI lists visible public volumes and gets the object keyed by id. | preserved |
| A-FR7-02-2 | PRD Same access channels; design API Extensions / UX Alignment | TC-FR7-02 ER2: Neither name nor display_name substitutes for id in Get. | preserved |
| A-FR7-02-3 | PRD Same access channels; design API Extensions / UX Alignment | TC-FR7-02 ER3: Public UI types derive from the backend proto; list/detail consumers use id for deep links and the standard public API. Separate UI delivery belongs to OSAC-4546/4547, with UI navigation verified manually in TC-FR7-03 below. | preserved |
| A-FR7-03-1 | PRD Same access channels; design API Extensions / UX Alignment | TC-FR7-03 ER1: List shows visible volume alpha. | preserved |
| A-FR7-03-2 | PRD Same access channels; design API Extensions / UX Alignment | TC-FR7-03 ER2: Detail URL and public Get request carry vol-a id, not alpha/display_name. | preserved |
| A-FR7-03-3 | PRD Same access channels; design API Extensions / UX Alignment | TC-FR7-03 ER3: Details show public tier/size/state and no internal routing fields. | preserved |
| A-FR7-03-4 | PRD Same access channels; design API Extensions / UX Alignment | TC-FR7-03 ER4: Unauthenticated session cannot fetch the object. | preserved |
| A-FR8-01-1 | PRD Test and documentation / Dependencies; design Private adjustment / E2E / Upgrade / Version Skew | TC-FR8-01 ER1: The private server builds without a tier resolver. | preserved |
| A-FR8-01-2 | PRD Test and documentation / Dependencies; design Private adjustment / E2E / Upgrade / Version Skew | TC-FR8-01 ER2: Get/List work without invoking tier resolution. | preserved |
| A-FR8-01-3 | PRD Test and documentation / Dependencies; design Private adjustment / E2E / Upgrade / Version Skew | TC-FR8-01 ER3: Create without a resolver fails, with no new volume persisted. | preserved |
| A-FR8-02-1 | PRD Test and documentation / Dependencies; design Private adjustment / E2E / Upgrade / Version Skew | TC-FR8-02 ER1: The real provisioned volume becomes readable by A under its immutable id. | preserved |
| A-FR8-02-2 | PRD Test and documentation / Dependencies; design Private adjustment / E2E / Upgrade / Version Skew | TC-FR8-02 ER2: Public fields reflect the provisioned tier, size, access mode, state and message. | preserved |
| A-FR8-02-3 | PRD Test and documentation / Dependencies; design Private adjustment / E2E / Upgrade / Version Skew | TC-FR8-02 ER3: Internal routing fields never appear. | preserved |
| A-FR8-02-4 | PRD Test and documentation / Dependencies; design Private adjustment / E2E / Upgrade / Version Skew | TC-FR8-02 ER4: B List excludes the volume and B Get returns NotFound. | preserved |
| A-FR8-02-5 | PRD Test and documentation / Dependencies; design Private adjustment / E2E / Upgrade / Version Skew | TC-FR8-02 ER5: Private teardown completes and archived volume is absent; this scenario cannot be replaced by fake provider responses. | preserved |
| A-FR8-03-1 | PRD Test and documentation / Dependencies; design Private adjustment / E2E / Upgrade / Version Skew | TC-FR8-03 ER1: Published API docs/spec contain GET /api/fulfillment/v1/volumes and /{id}, public fields, and no public Volume mutation operation. | preserved |
| A-FR8-03-2 | PRD Test and documentation / Dependencies; design Private adjustment / E2E / Upgrade / Version Skew | TC-FR8-03 ER2: No database migration, CRD, webhook, aggregated server or finalizer is added by this read-only feature. | preserved |
| A-FR8-03-3 | PRD Test and documentation / Dependencies; design Private adjustment / E2E / Upgrade / Version Skew | TC-FR8-03 ER3: Existing resource clients keep working; an old console need not call new endpoints. | preserved |
| A-FR8-03-4 | PRD Test and documentation / Dependencies; design Private adjustment / E2E / Upgrade / Version Skew | TC-FR8-03 ER4: Downgrade removes read endpoint registration without migrating or removing inventory data; verify in isolated wiring fixture. | preserved |

## Gaps and scope rules

- All 8 local behavior groups and IC1/2/3 have cases; no formal labels exist in approved docs. Local aliases never claim canonical Jira ACs.
- Historical design describes DAO ignoring order; FR3 retains PRD ordering oracle and treats divergence as implementation work, not unspecified behavior or a new decision.
- Pinned current source has later public mutations / resolver requirements. That is evolution beyond the frozen feature; fixture cases use approved read-only expectations and may require historical feature wiring. Current implementation test success is not asserted.
- New generation fault seams, project fixture, manual consumer and real deployed provision/read helper are proposed work, not existing passed suites. Owners are DEV-READ/QE-READ/UI-READ; no fabricated follow-up issue.
- API docs/spec publication, service/gateway registration, private-proto annotations, auth allowlist, UI type regeneration are DEV-READ/UI-READ deliverables. Tests inspect these artifacts; no schema migration, new CRDs, webhook/finalizer, retries or data path.
- Design references external osac-test-infra E2E location and hand import pruning. Current repo guidance owns suites under tests/e2e and source-owned generators; execution layout follows current guidance without changing approved behavior.
- Out of scope: public lifecycle/resize, snapshots/clones/restore, attach/detach, provenance, file/object storage. Setup uses existing private lifecycle, never invents new public operations. No timing or monitoring SLA was approved.
- Background accounted: problem/motivation explains inventory visibility; author/provenance and alternatives impose no additional behavior; Cloud Infrastructure Admin unaffected; no new observability/infrastructure promised; graduation is release packaging work. Standard existing logging/interceptors are checked through API path/error tests, not a new metric.

## Summary

| Metric | Count |
|---|---|
| Total test cases | 21 |
| High | 21 |
| Critical / Medium / Low | 0 / 0 / 0 |
| Automated intent / Manual | 20 / 1 |
| Requirement groups | 8 / 8 local aliases |
| Interface groups | 3 / 3 local aliases |
| Executed tests | 0 |

Planning check: source sections accounted; assertions mapped with concrete results; execution paths and proposed gaps disclosed. Planning readiness does not mean test execution. No product sources were modified. Correction round 1 adds missing error/project/shared/deployed cases and replaces old unresolved ordering classification with implementation drift.

Correction round 2: select real VAST prerequisites and explicitly separate the proposed historical read-only descriptor fixture from current CRUD suites. Proposed commands/files remain proposed; no passing execution or new product requirement is claimed.

Continuation planning pass, correction 1: specify project membership/JWT setup and real provider lab steps from pinned source. Preserve all existing clauses, assertion IDs and 21 cases. Allocation and proposed helper execution remain not run; a plan score must not be presented as feature execution.

Traceability follow-up pass: clarify local group counts, approved source-clause mappings and exact per-case interfaces. All 21 case IDs and assertion IDs are preserved; expected results and frozen PRD/design bytes are unchanged. This local revision has not been model-scored or executed.
