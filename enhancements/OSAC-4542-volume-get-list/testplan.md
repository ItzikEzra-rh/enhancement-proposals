# Testplan — OSAC-4542

## Regeneration Mode and Source Labels

This is a test-plan-only regeneration from the approved PRD and the
byte-preserved approved design. `03-design.md` is not a newly drafted design.

The approved PRD supplies acceptance criteria but no FR/NFR identifiers. The
approved design likewise has no numbered Interface Changes section. The
following labels are therefore planning-local traceability labels, not source
labels:

- `REQ-1` through `REQ-8` identify the eight behavioral requirement groups
  extracted from the approved PRD/design.
- `IC-1` through `IC-8` identify the concrete interface surfaces extracted
  from the approved design's API Extensions, workflow, UX Alignment, and
  authorization sections.
- `A-*` identifiers in the audit identify individual source assertions.

The PRD's documentation/API-spec deliverable is tracked separately as `DEL-1`
because it has no behavioral test oracle. No requirement or interface was
silently dropped because the current implementation already exists or because
an execution harness is missing.

## Overview

- **Feature:** OSAC-4542 — Volume Get/List Public API
- **Total test cases:** 22
- **Requirements covered:** 8 of 8 behavioral requirement groups
- **Interface changes covered:** 8 of 8 regenerated interface entries
- **Planning result:** PASS after internal correction and recheck; several
  cases remain planned but not execution-ready.
- **Execution result:** No tests were run in this phase.

## Requirement and Interface Traceability

### Requirement inventory

| Local ID | Approved source | Observable contract |
|---|---|---|
| REQ-1 | PRD, Acceptance Criteria — Identifier; design Workflow Description and Failure Handling | A visible immutable `id` retrieves a volume; an invisible or absent id returns `NotFound`. |
| REQ-2 | PRD, Acceptance Criteria — Inventory states; design Workflow Description | `creating`, `available`, and `deleting` are readable; archived `deleted` volumes are absent; no implicit state filter is applied. |
| REQ-3 | PRD, Acceptance Criteria — Isolation; design RBAC / Tenancy | List and Get enforce tenant/project visibility; a Cloud Provider Admin can see all tenants. |
| REQ-4 | PRD, Read-only tenant-meaningful representation; design Proposal and Test Plan | The public projection contains the approved fields and excludes routing/vendor fields. |
| REQ-5 | PRD, Acceptance Criteria — standard list contract; design Implementation Details/Notes/Constraints | Public CEL filtering, offset/limit, ordering, secondary `id asc`, and private-field rejection have concrete results. |
| REQ-6 | PRD, Same access channels; design API Extensions and UX Alignment | Public gRPC, REST, CLI, and generated-console consumption use the public volume contract. |
| REQ-7 | PRD, Tenant/project visibility; design RBAC / Tenancy and authorization matrix | Tenant User, Tenant Admin, and Cloud Provider Admin read access follows the approved matrix; unauthenticated and mutation paths do not succeed publicly. |
| REQ-8 | Design Failure Handling and Recovery, Test Plan, and private-server adjustment | Invalid inputs, mapping/delegate failures, read idempotency, and resolver-dependent private behavior have explicit outcomes. |

### Interface-change inventory

These entries are derived for regeneration because the approved design has no
numbered §5 Interface Changes section. They are not asserted to be source
labels.

| Local ID | Source location | Interface surface | Requirements |
|---|---|---|---|
| IC-1 | Design Proposal item 1; API Extensions | Public `Volume` schema generated from the private proto, with the exact public field set | REQ-4 |
| IC-2 | Design API Extensions; Workflow Description | Public gRPC `Volumes.List` | REQ-2, REQ-3, REQ-4, REQ-5, REQ-6 |
| IC-3 | Design API Extensions; Workflow Description | Public gRPC `Volumes.Get` | REQ-1, REQ-2, REQ-3, REQ-4, REQ-6 |
| IC-4 | Design API Extensions | REST `GET /api/fulfillment/v1/volumes` | REQ-2, REQ-3, REQ-4, REQ-5, REQ-6 |
| IC-5 | Design API Extensions | REST `GET /api/fulfillment/v1/volumes/{id}` | REQ-1, REQ-2, REQ-3, REQ-4, REQ-6 |
| IC-6 | Design Workflow Description and Implementation Details | `filter`, `offset`, `limit`, and `order` list controls constrained by the public descriptor | REQ-5 |
| IC-7 | Design Authorization and RBAC / Tenancy | OPA method access plus tenant/project row visibility | REQ-3, REQ-7 |
| IC-8 | PRD Same access channels; design UX Alignment | Generic CLI discovery and console consumption of generated public types | REQ-6 |

## Test Cases

### REQ-1: Stable identifier and visible Get

#### TC-REQ1-01: Get a visible volume by immutable id

| Interface Change | Priority | Automation |
|---|---|---|
| IC-3, IC-5 | critical | automated |

##### Preconditions

- A volume exists in the caller's visible tenant/project scope and its
  immutable system-generated `id` is recorded.
- The public gRPC client and REST gateway are available for the selected
  execution tier.

##### Steps

1. Call public `Volumes.Get` with the recorded `id`.
2. Repeat through REST `GET /api/fulfillment/v1/volumes/{id}`.

##### Expected Results

- **ER-REQ1-01-a:** Both responses identify the volume with the recorded
  immutable `id`.
- **ER-REQ1-01-b:** The returned metadata name, storage tier, size, access
  mode, and state equal the seeded volume values.
- **ER-REQ1-01-c:** The REST response is HTTP 200 and contains the same public
  object values as the gRPC response.

#### TC-REQ1-02: Get an invisible or absent volume id

| Interface Change | Priority | Automation |
|---|---|---|
| IC-3, IC-5, IC-7 | critical | automated |

##### Preconditions

- A volume exists in tenant/project scope not visible to the caller.
- A random id that does not identify any volume is available.

##### Steps

1. Call public gRPC `Volumes.Get` with the out-of-scope id.
2. Call public gRPC `Volumes.Get` with the random id.
3. Repeat the out-of-scope request through the REST item route.

##### Expected Results

- **ER-REQ1-02-a:** The out-of-scope gRPC request returns status
  `NotFound`.
- **ER-REQ1-02-b:** The random-id gRPC request returns status `NotFound`.
- **ER-REQ1-02-c:** The REST item route returns HTTP 404 for the out-of-scope
  id, with no volume fields in the response body.

### REQ-2: Inventory state visibility and archival

#### TC-REQ2-01: List and Get every non-archived inventory state

| Interface Change | Priority | Automation |
|---|---|---|
| IC-2, IC-3, IC-4, IC-5 | high | automated |

##### Preconditions

- Fixtures exist in `creating`, `available`, and `deleting` states in a scope
  visible to the caller.
- The fixtures are not archived.

##### Steps

1. Call public List without a `status.state` filter.
2. Call public Get for each fixture id.

##### Expected Results

- **ER-REQ2-01-a:** List contains one item for each fixture with state values
  `creating`, `available`, and `deleting`.
- **ER-REQ2-01-b:** Get returns each fixture with the same state value that
  was seeded.
- **ER-REQ2-01-c:** The unfiltered List response does not omit a fixture
  because of its non-archived state.

#### TC-REQ2-02: Exclude a fully deprovisioned deleted volume

| Interface Change | Priority | Automation |
|---|---|---|
| IC-2, IC-3, IC-4, IC-5 | high | automated |

##### Preconditions

- A private lifecycle fixture has reached `deleted` and its record is
  archived.
- The former volume id is recorded.

##### Steps

1. Call public List without a state filter.
2. Call public Get with the former volume id.

##### Expected Results

- **ER-REQ2-02-a:** The archived id is absent from the List item ids.
- **ER-REQ2-02-b:** Get returns `NotFound` for the archived id.
- **ER-REQ2-02-c:** List applies no alternate implicit state filter to the
  remaining non-archived items.

### REQ-3: Tenant and project isolation

#### TC-REQ3-01: List only authorized tenant and project rows

| Interface Change | Priority | Automation |
|---|---|---|
| IC-2, IC-4, IC-7 | critical | automated |

##### Preconditions

- Volumes exist in tenant A/project A1, tenant A/project A2 outside the
  caller's project visibility, and tenant B.
- A tenant caller is authorized for tenant A/project A1 only.
- A Cloud Provider Admin credential is available.

##### Steps

1. List through public gRPC and REST as the tenant caller.
2. List through public gRPC as the Cloud Provider Admin.

##### Expected Results

- **ER-REQ3-01-a:** The tenant caller's gRPC and REST item ids contain the
  tenant A/project A1 volume and contain neither the tenant A/project A2 nor
  tenant B volume.
- **ER-REQ3-01-b:** The Cloud Provider Admin response contains the seeded
  tenant A and tenant B volume ids.
- **ER-REQ3-01-c:** The tenant response's `total` excludes every row outside
  the caller's authorized tenant/project scope.

#### TC-REQ3-02: Get enforces the same row scope as List

| Interface Change | Priority | Automation |
|---|---|---|
| IC-3, IC-5, IC-7 | critical | automated |

##### Preconditions

- The tenant A/project A1, tenant A/project A2, and tenant B fixture ids from
  TC-REQ3-01 are recorded.
- Tenant User and Tenant Admin credentials are available.

##### Steps

1. Get the project A2 and tenant B ids as the tenant user.
2. Get the same ids as the tenant admin.
3. Get the tenant B id as the Cloud Provider Admin.

##### Expected Results

- **ER-REQ3-02-a:** Tenant User Get returns `NotFound` for both ids outside
  the user's visible scope.
- **ER-REQ3-02-b:** Tenant Admin Get returns `NotFound` for the same ids when
  the admin has the same tenant/project visibility.
- **ER-REQ3-02-c:** Cloud Provider Admin Get returns HTTP/gRPC success and the
  tenant B public object.

### REQ-4: Public projection and field privacy

#### TC-REQ4-01: Enforce the exact public Volume schema allowlist

| Interface Change | Priority | Automation |
|---|---|---|
| IC-1 | critical | automated |

##### Preconditions

- The generated public `Volume` descriptor is loaded from
  `proto/gen/osac/public/v1`.

##### Steps

1. Walk the public `Volume` descriptor and reachable nested descriptors.
2. Compare the collected field paths with the approved allowlist.

##### Expected Results

- **ER-REQ4-01-a:** The collected public field paths equal exactly
  `id`, `metadata`, `spec.storage_tier`, `spec.size_gib`,
  `spec.access_mode`, `status.state`, and `status.message`.
- **ER-REQ4-01-b:** The collected field paths contain none of `backend`,
  `protocol`, `hub`, `vendor_volume_id`, or `vendor_context`.

#### TC-REQ4-02: Map public values and suppress private routing data

| Interface Change | Priority | Automation |
|---|---|---|
| IC-1, IC-2, IC-3 | critical | automated |

##### Preconditions

- A private volume is seeded with public values and internal routing values
  including backend, protocol, hub, vendor volume id, and vendor context.

##### Steps

1. Retrieve the volume through public Get.
2. Retrieve it through public List.
3. Serialize both public objects with the public protobuf/JSON descriptor.

##### Expected Results

- **ER-REQ4-02-a:** Public Get and List preserve the seeded id, metadata,
  storage tier, size, access mode, state, and message.
- **ER-REQ4-02-b:** Neither serialized public object contains a field named
  `backend`, `protocol`, `hub`, `vendor_volume_id`, or `vendor_context`.
- **ER-REQ4-02-c:** The public response does not contain a private
  `StorageProtocol`/`storage_common_type` value.

### REQ-5: Standard List contract and public query surface

#### TC-REQ5-01: Filter by a public CEL field

| Interface Change | Priority | Automation |
|---|---|---|
| IC-2, IC-4, IC-6 | high | automated |

##### Preconditions

- Visible fixtures have distinct `status.state` values.

##### Steps

1. Submit List with `this.status.state == 1`.

##### Expected Results

- **ER-REQ5-01-a:** The response has no error.
- **ER-REQ5-01-b:** Every returned item's `status.state` equals the requested
  public value, and no nonmatching fixture id is returned.

#### TC-REQ5-02: Reject a CEL filter on a private field

| Interface Change | Priority | Automation |
|---|---|---|
| IC-2, IC-4, IC-6 | high | automated |

##### Preconditions

- A visible volume exists and its private backend value is known.

##### Steps

1. Submit List with `this.status.backend == "internal-backend"`.

##### Expected Results

- **ER-REQ5-02-a:** gRPC List returns `InvalidArgument`.
- **ER-REQ5-02-b:** REST List returns HTTP 400 and does not return volume
  items.

#### TC-REQ5-03: Apply offset and limit while reporting total and page size

| Interface Change | Priority | Automation |
|---|---|---|
| IC-2, IC-4, IC-6 | high | automated |

##### Preconditions

- At least three visible fixtures match `this.metadata.name.contains('page')`.

##### Steps

1. List with the page filter and `limit=2`.
2. List with the same filter, `offset=2`, and `limit=2`.

##### Expected Results

- **ER-REQ5-03-a:** The first response contains two items, reports `size=2`,
  and reports `total` at least 3.
- **ER-REQ5-03-b:** The second response contains the remaining matching item,
  reports `size=1`, and reports the same total as the first response.
- **ER-REQ5-03-c:** No item outside the filter appears in either page.

#### TC-REQ5-04: Order by a public field with implicit id tie-breaking

| Interface Change | Priority | Automation |
|---|---|---|
| IC-2, IC-4, IC-6 | high | automated |

##### Preconditions

- Visible fixtures have two equal `metadata.name` order keys and distinct ids,
  plus a fixture with a higher name.

##### Steps

1. List with an order expression for a public field, such as
   `metadata.name desc`.
2. Inspect returned item order and compare equal-key ids.

##### Expected Results

- **ER-REQ5-04-a:** Items are ordered by the requested public field in the
  requested direction.
- **ER-REQ5-04-b:** Items tied on the requested field are ordered by `id` in
  ascending order.

#### TC-REQ5-05: Reject an order expression on a private field

| Interface Change | Priority | Automation |
|---|---|---|
| IC-2, IC-4, IC-6 | medium | automated |

##### Preconditions

- The public Volume descriptor excludes `status.backend`.

##### Steps

1. Submit List with order expression `status.backend desc`.

##### Expected Results

- **ER-REQ5-05-a:** gRPC List returns `InvalidArgument`.
- **ER-REQ5-05-b:** REST List returns HTTP 400 and does not expose backend
  values.

### REQ-6: Public access channels

#### TC-REQ6-01: Invoke public gRPC List and Get

| Interface Change | Priority | Automation |
|---|---|---|
| IC-2, IC-3 | critical | automated |

##### Preconditions

- A visible volume exists and a public gRPC connection is configured.

##### Steps

1. Invoke `osac.public.v1.Volumes/List`.
2. Invoke `osac.public.v1.Volumes/Get` with an item id.

##### Expected Results

- **ER-REQ6-01-a:** Both RPCs are present in the public service descriptor and
  return the public volume response shapes.
- **ER-REQ6-01-b:** The List response contains `items`, `size`, and `total`;
  the Get response contains `object`.

#### TC-REQ6-02: Invoke public REST collection and item routes

| Interface Change | Priority | Automation |
|---|---|---|
| IC-4, IC-5 | high | automated |

##### Preconditions

- The gRPC gateway is deployed with the public volume service registered.
- A visible volume id is recorded.

##### Steps

1. GET `/api/fulfillment/v1/volumes`.
2. GET `/api/fulfillment/v1/volumes/{id}`.

##### Expected Results

- **ER-REQ6-02-a:** The collection route returns HTTP 200 with a JSON list
  response containing `items`, `size`, and `total`.
- **ER-REQ6-02-b:** The item route returns HTTP 200 with a JSON public Volume
  object whose `id` equals the requested id.

#### TC-REQ6-03: Consume the public contract through CLI and generated console types

| Interface Change | Priority | Automation |
|---|---|---|
| IC-8 | medium | manual |

##### Preconditions

- The public service is deployed and the CLI is authenticated as a caller
  entitled to see a seeded volume.
- The UI checkout has regenerated types from the public proto.

##### Steps

1. Run `osac get volumes`.
2. Run `osac get volume <id>` for the seeded id.
3. Load the generated public Volume type in the console storage view.

##### Expected Results

- **ER-REQ6-03-a:** `osac get volumes` lists the seeded volume id and its
  public fields without private routing fields.
- **ER-REQ6-03-b:** `osac get volume <id>` prints the same public id and
  metadata values returned by public Get.
- **ER-REQ6-03-c:** The console type includes the public Volume fields and no
  private routing fields.

### REQ-7: Authorization and read-only method policy

#### TC-REQ7-01: Apply the approved read authorization matrix

| Interface Change | Priority | Automation |
|---|---|---|
| IC-7 | critical | automated |

##### Preconditions

- Tenant User, Tenant Admin, Cloud Provider Admin, and unauthenticated
  credentials are available.
- At least one volume exists in each relevant tenant.

##### Steps

1. Call public Get and List as Tenant User.
2. Call public Get and List as Tenant Admin.
3. Call public Get and List as Cloud Provider Admin.
4. Call public Get and List without credentials.

##### Expected Results

- **ER-REQ7-01-a:** Tenant User and Tenant Admin receive successful public
  Get/List responses for rows in their visible scope.
- **ER-REQ7-01-b:** Cloud Provider Admin receives successful responses that
  include rows from all seeded tenants.
- **ER-REQ7-01-c:** Unauthenticated Get and List return gRPC status
  `Unauthenticated` and no volume object.

#### TC-REQ7-02: Keep mutations out of the public service

| Interface Change | Priority | Automation |
|---|---|---|
| IC-7 | high | automated |

##### Preconditions

- The generated public `Volumes` service descriptor is loaded.
- A private admin connection exists only to confirm that the source volume
  remains available for comparison.

##### Steps

1. Inspect the public service methods for Create, Update, Delete, and Signal.
2. Attempt the public mutation method paths used by the authorization test.

##### Expected Results

- **ER-REQ7-02-a:** The public service descriptor contains List and Get but no
  Create, Update, Delete, or Signal method.
- **ER-REQ7-02-b:** No public mutation attempt returns a successful mutation
  response or changes the private volume record.

### REQ-8: Failure handling, idempotency, and private resolver behavior

#### TC-REQ8-01: Return Internal without partial data on mapping failure

| Interface Change | Priority | Automation |
|---|---|---|
| IC-2, IC-3 | high | automated |

##### Preconditions

- A unit-test double can make the public mapper return an error after a private
  object is read.

##### Steps

1. Invoke public List with the mapper failure injected.
2. Invoke public Get with the mapper failure injected.

##### Expected Results

- **ER-REQ8-01-a:** Each RPC returns gRPC status `Internal`.
- **ER-REQ8-01-b:** Neither response contains a partial item or object.
- **ER-REQ8-01-c:** The injected error is present in the structured/logged
  failure record without exposing private field values to the client.

#### TC-REQ8-02: Propagate delegate/database errors without retry or partial results

| Interface Change | Priority | Automation |
|---|---|---|
| IC-2, IC-3 | high | automated |

##### Preconditions

- The private delegate or database test double returns a known gRPC status
  and error message on the first read.

##### Steps

1. Invoke public List and Get once against the failing delegate.
2. Inspect the delegate call count and public response.

##### Expected Results

- **ER-REQ8-02-a:** The public response carries the delegate/database status
  and message without converting it to a success response.
- **ER-REQ8-02-b:** The response contains no partial items or object.
- **ER-REQ8-02-c:** The delegate call count is one for each requested read;
  the public server performs no automatic retry.

#### TC-REQ8-03: Repeat reads without side effects

| Interface Change | Priority | Automation |
|---|---|---|
| IC-2, IC-3 | medium | automated |

##### Preconditions

- A visible volume's database row, version, and deletion timestamp are
  recorded.

##### Steps

1. Call public Get twice with the same id.
2. Call public List twice with the same request.
3. Compare the stored row after the calls.

##### Expected Results

- **ER-REQ8-03-a:** Both Get responses contain the same id and public field
  values.
- **ER-REQ8-03-b:** Both List responses contain the same item ids, `size`, and
  `total` when the underlying data is unchanged.
- **ER-REQ8-03-c:** The volume row's version and deletion timestamp are
  unchanged, and no create/update/delete side effect is recorded.

#### TC-REQ8-04: Build the private read delegate without a tier resolver

| Interface Change | Priority | Automation |
|---|---|---|
| IC-2, IC-3 | medium | automated |

##### Preconditions

- The private volume server builder is available without a tier resolver.

##### Steps

1. Build the private server without configuring a tier resolver.
2. Invoke a private read operation.
3. Invoke private Create without configuring a tier resolver.

##### Expected Results

- **ER-REQ8-04-a:** The private server builds and the read operation returns
  its response without a resolver.
- **ER-REQ8-04-b:** Create returns a non-success error and does not create a
  volume row when the resolver is absent.
- **ER-REQ8-04-c:** The exact Create error code/message is recorded by the
  implementation test; the approved design does not specify that code/message
  and therefore this detail remains an explicit source gap.

## Execution Evidence Matrix

Readiness meanings: **existing path** means the checked-out repository defines
the command/harness; **planned** means the case needs test work; **blocked**
means a required fixture, deployed boundary, consumer checkout action, or
ownership decision is unavailable; **passed** is never claimed here because no
tests ran.

| Behavior and cases | Owning component | Tier / boundary | Test location | Execution and prerequisites | Real vs simulated | Readiness |
|---|---|---|---|---|---|---|
| Projection, public schema, public filter, mapping: TC-REQ4-01, TC-REQ4-02, TC-REQ5-01, TC-REQ5-02 | `fulfillment-service` | Unit; public/private mapper and descriptor boundary | Existing `fulfillment-service/internal/servers/volumes_server_test.go`; extend exact allowlist to include `vendor_context` | Existing command `ginkgo run internal/servers` from `fulfillment-service/`; no cluster required | In-process server and database test fixtures; external services mocked | Planned; command verified, cases require test extension; not run |
| Get/List builder and resolver behavior: TC-REQ8-04 | `fulfillment-service` | Unit; private server construction boundary | Existing `fulfillment-service/internal/servers/private_volumes_server_test.go` | Existing `ginkgo run internal/servers` from `fulfillment-service/` | Private server and DAO test fixtures are in-process | Planned; command verified, exact Create error remains unspecified; not run |
| Public authz and mutation surface: TC-REQ7-01, TC-REQ7-02 | `fulfillment-service` | Unit; gRPC authz interceptor and generated public service boundary | Existing `fulfillment-service/internal/servers/grpc_authz_interceptor_test.go` plus public descriptor assertions | Existing `ginkgo run internal/servers` from `fulfillment-service/` | Authz policy and interceptor test doubles; no deployed IdP | Planned; existing authz path, mutation assertion needs explicit public descriptor check; not run |
| Visible Get/List projection and error mapping: TC-REQ1-01, TC-REQ1-02, TC-REQ2-01, TC-REQ2-02, TC-REQ3-01, TC-REQ3-02, TC-REQ8-01, TC-REQ8-02, TC-REQ8-03 | `fulfillment-service` | Component integration; public gRPC/REST to fulfillment service, PostgreSQL, and tenancy boundary | Proposed `fulfillment-service/it/it_public_volumes_test.go`, patterned on existing `fulfillment-service/it/it_public_storage_tiers_test.go` | Existing installer-owned command `make -C ../osac-installer test PLATFORM=kind PROFILE=dev NS=osac SUITE=fulfillment`, run from `fulfillment-service/`; requires Kind `osac-dev`, deployed fulfillment service, PostgreSQL, tenant credentials, private seeding client, and state/archive fixtures | Fulfillment service and PostgreSQL real; private seed client is a test actor; no real provider is required for projection | Planned; proposed volume suite and fixtures do not exist; not execution-ready |
| Pagination and public query controls: TC-REQ5-03, TC-REQ5-04, TC-REQ5-05 | `fulfillment-service` | Component integration; List query boundary | Proposed additions to `fulfillment-service/it/it_public_volumes_test.go` | Same existing installer-owned command and Kind prerequisites as the public volume integration row | Fulfillment service and PostgreSQL real; volume data seeded through private API | Planned; order behavior is implementation drift because the current DAO hard-codes `id`; not execution-ready |
| REST route exposure: TC-REQ6-02 | `fulfillment-service` | Component integration; REST gateway to public gRPC boundary | Existing `fulfillment-service/it/it_rest_gateway_test.go`; extend with public volume routes | Same installer-owned fulfillment integration command; requires deployed REST gateway and public volume registration | REST gateway and fulfillment service real; database fixture seeded by private API | Planned; existing REST harness, volume cases absent; not run |
| CLI and console consumer contract: TC-REQ6-03 | `fulfillment-service` / `osac-ui` | Contract/consumer boundary; public reflection and generated UI types | CLI reflection in `fulfillment-service/internal/cmd/cli/get/get_cmd.go`; proposed CLI integration case; `osac-ui/libs/types` generated output | CLI requires authenticated deployed service; UI requires public proto generation followed by `pnpm gen-types` in `osac-ui/`; no command was run | Deployed fulfillment service real; UI generation and console are consumer-side; no console page is currently present | Blocked; no public UI types/page or checked-in CLI volume scenario exists |
| E2E tenant-visible read path: TC-REQ3-01, TC-REQ3-02, TC-REQ6-03 | `tests/e2e` | E2E; deployed OSAC user journey through public API | Proposed `tests/e2e/storage/sanity/test_public_volumes.py`, with existing `tests/e2e/storage/conftest.py` and `tests/e2e/core/grpc_client.py` as discovery points | Proposed collection `uv run pytest --collect-only tests/e2e/storage/sanity/`; proposed narrow run `uv run pytest tests/e2e/storage/sanity/test_public_volumes.py -k public_volume`; requires deployed OSAC stack, tenant credentials, and volume fixture path | Deployed API and tenancy real; provider/backend setup depends on environment; no fixed sleeps | Blocked; no public volume helper/scenario exists and approved design's `osac-test-infra` note conflicts with repository ownership guidance |
| API documentation and published spec deliverable: DEL-1 | `fulfillment-service` / docs | Static/documentation validation, not a behavioral test tier | `fulfillment-service/docs/API.md` and generated OpenAPI output | Documented command `./osac-dev generate openapi --project-dir . --output-dir pages/openapi` from `fulfillment-service/`; no generation or publication run | Service descriptors are source; OpenAPI output would be generated; no deployed boundary | Gap; API.md contains stale private-only volume guidance and current published spec was not verified |

## Source Assertion Checklist

The checklist was extracted before reviewing the generated cases. The audit
below links each assertion to an exact Expected Results bullet; a case link or
fixture alone is not counted as preserved evidence.

| Assertion | PRD source | Design source / counterpart | Case and exact decisive Expected Results wording | Verdict |
|---|---|---|---|---|
| A-PRD-01: visible immutable id retrieves the volume | Acceptance Criteria — Identifier | Workflow Description / API Extensions | TC-REQ1-01: “Both responses identify the volume with the recorded immutable `id`.” | preserved |
| A-PRD-02: invisible id is indistinguishable from absent id | Acceptance Criteria — Identifier | Failure Handling | TC-REQ1-02: “The out-of-scope gRPC request returns status `NotFound`.” and “The random-id gRPC request returns status `NotFound`.” | preserved |
| A-PRD-03: creating, available, deleting are visible | Acceptance Criteria — Inventory states | Test Plan — Integration Tests | TC-REQ2-01: “List contains one item for each fixture with state values `creating`, `available`, and `deleting`.” | preserved |
| A-PRD-04: deleted archived records are absent | Acceptance Criteria — Inventory states | Failure Handling / Test Plan | TC-REQ2-02: “The archived id is absent from the List item ids.” and “Get returns `NotFound` for the archived id.” | preserved |
| A-PRD-05: List and Get enforce tenant/project isolation | Acceptance Criteria — Isolation | RBAC / Tenancy | TC-REQ3-01: “The tenant caller's gRPC and REST item ids contain the tenant A/project A1 volume and contain neither the tenant A/project A2 nor tenant B volume.”; TC-REQ3-02: “Tenant User Get returns `NotFound` for both ids outside the user's visible scope.” | preserved |
| A-PRD-06: CEL uses the standard public-field list contract | Acceptance Criteria — standard OSAC list contract | Implementation Details/Notes/Constraints | TC-REQ5-01: “Every returned item's `status.state` equals the requested public value, and no nonmatching fixture id is returned.”; TC-REQ5-02: “gRPC List returns `InvalidArgument`.” | preserved |
| A-PRD-07: offset/limit report page and total values | Acceptance Criteria — standard OSAC list contract | Test Plan — Unit/Integration Tests | TC-REQ5-03: “The first response contains two items, reports `size=2`, and reports `total` at least 3.” | preserved |
| A-PRD-08: ordering uses the requested field and implicit id asc tie-break | Acceptance Criteria — standard OSAC list contract | Implementation Details/Notes/Constraints | TC-REQ5-04: “Items are ordered by the requested public field in the requested direction.” and “Items tied on the requested field are ordered by `id` in ascending order.” | preserved; current DAO drift blocks execution readiness |
| A-PRD-09: public gRPC and REST routes exist | Same access channels | API Extensions | TC-REQ6-01: “Both RPCs are present in the public service descriptor and return the public volume response shapes.”; TC-REQ6-02: “The collection route returns HTTP 200 with a JSON list response containing `items`, `size`, and `total`.” | preserved |
| A-PRD-10: CLI and console can consume the same public contract | Same access channels | UX Alignment | TC-REQ6-03: “`osac get volumes` lists the seeded volume id and its public fields without private routing fields.” and “The console type includes the public Volume fields and no private routing fields.” | preserved; consumer execution blocked |
| A-PRD-11: only tenant-meaningful fields are public | Read-only tenant-meaningful representation | Proposal item 1 / Test Plan | TC-REQ4-02: “Neither serialized public object contains a field named `backend`, `protocol`, `hub`, `vendor_volume_id`, or `vendor_context`.” | preserved |
| A-DES-01: exact public schema allowlist | — | Test Plan — Generated-schema guard | TC-REQ4-01: “The collected public field paths equal exactly `id`, `metadata`, `spec.storage_tier`, `spec.size_gib`, `spec.access_mode`, `status.state`, and `status.message`.” | preserved; existing test is weaker and needs extension |
| A-DES-02: public CEL filter cannot reference status.backend | — | Implementation Details / Test Plan | TC-REQ5-02: “REST List returns HTTP 400 and does not return volume items.” | preserved |
| A-DES-03: invalid public/private order returns InvalidArgument | — | Failure Handling / Implementation Details | TC-REQ5-05: “gRPC List returns `InvalidArgument`.” and “REST List returns HTTP 400 and does not expose backend values.” | preserved; current order path is implementation drift |
| A-DES-04: mapping failure is Internal with no partial data | — | Failure Handling | TC-REQ8-01: “Each RPC returns gRPC status `Internal`.” and “Neither response contains a partial item or object.” | preserved |
| A-DES-05: delegate/DB errors propagate without retries or partial data | — | Failure Handling | TC-REQ8-02: “The public response carries the delegate/database status and message without converting it to a success response.” and “The delegate call count is one for each requested read; the public server performs no automatic retry.” | preserved |
| A-DES-06: reads are idempotent and side-effect free | — | Failure Handling | TC-REQ8-03: “The volume row's version and deletion timestamp are unchanged, and no create/update/delete side effect is recorded.” | preserved |
| A-DES-07: private read delegate builds without tier resolver; Create fails without it | — | Proposal item 3 / Test Plan — Private server | TC-REQ8-04: “The private server builds and the read operation returns its response without a resolver.” and “Create returns a non-success error and does not create a volume row when the resolver is absent.” | preserved; exact Create error is unspecified by source |
| A-DES-08: tenant read methods allowed and public mutations absent/denied | — | Authorization / RBAC / Test Plan | TC-REQ7-01: “Tenant User and Tenant Admin receive successful public Get/List responses for rows in their visible scope.”; TC-REQ7-02: “The public service descriptor contains List and Get but no Create, Update, Delete, or Signal method.” | preserved |

## Gaps by Classification

### Implementation drift

- The approved PRD requires public list ordering, and the approved design
  requires `order` validation against the public schema. The current generic DAO
  hard-codes `id` ordering and the generic server does not consume the request
  order. TC-REQ5-04 and TC-REQ5-05 remain in the oracle; they are not weakened
  to match current behavior.
- The current implementation already exposes public Get/List, so implementation
  presence is not treated as proof that the contract is complete.

### Missing test coverage or execution infrastructure

- No public volume component-integration suite exists. The existing public
  storage-tier integration suite is an analogue, not volume coverage.
- No public volume E2E helper or scenario exists under `tests/e2e/`.
- The current schema unit test checks only selected forbidden names and omits
  `vendor_context`; it does not enforce the approved exact allowlist.
- State-transition/archive fixtures, injected mapper/delegate failures, and
  CLI volume scenarios are not currently present.
- No tests were executed, so no row is marked passed.

### Stale documentation

- `fulfillment-service/docs/API.md` still describes `volume_type.proto` as
  entirely private, despite the approved public Volume contract and generated
  public proto.
- The OpenAPI generation command is documented, but no OpenAPI regeneration or
  publication was run; the current published representation is unverified.
- These documentation gaps do not alter behavioral test expectations.

### Repository ownership guidance

- The approved design mentions adding a read path to an `osac-test-infra`
  vmaas suite, while repository instructions place E2E suites under
  `tests/e2e/` and assign external repositories infrastructure/backend
  ownership. The proposed mono-repo location follows the repository
  instructions, but ownership should be resolved before implementation.

### Approved-source and contract labeling

- The PRD has no formal FR/NFR labels and the design has no numbered IC
  matrix. Local labels are explicitly declared above so coverage counts remain
  auditable without fabricating source identifiers.
- The exact Create-without-resolver error code/message is not specified by the
  approved design. The test preserves the concrete non-success/no-row outcome
  and records the missing error detail rather than inventing one.
- Jira wording that differs from the approved PRD/design is not used as a
  behavioral oracle.

### Non-behavioral deliverable

- `DEL-1` requires API documentation and the published API spec to be updated.
  It is not a behavioral test requirement, so it has no TC heading; its
  execution evidence and stale documentation status are recorded above.

## Internal Correction and Recheck

The planning check applied the frozen `design-test-planning` `check-draft`
procedure after case generation. Corrections made before this final recheck:

1. Preserved the approved order and secondary-sort assertions as expected
   outcomes, then classified the current hard-coded-id behavior as
   implementation drift rather than source ambiguity.
2. Strengthened the schema assertion from selected forbidden names to the
   exact public allowlist and explicitly added `vendor_context` to the private
   field audit.
3. Added concrete error/no-partial-result outcomes for mapping and delegate
   failures, plus the private-server resolver case, instead of treating a
   fixture or case link as result evidence.
4. Added execution rows for REST, CLI/console, E2E, and the documentation
   deliverable, distinguishing existing commands from proposed cases and
   blocked infrastructure.

Recheck result: **PASS** for assertion preservation and planning evidence.
The affected cases remain planned, blocked, or not execution-ready where the
matrix says so. PASS does not mean tests ran or that the current implementation
passes the preserved order/schema assertions.

## Summary

| Metric | Count |
|---|---:|
| Total test cases | 22 |
| Critical | 8 |
| High | 10 |
| Medium | 4 |
| Low | 0 |
| Automated | 21 |
| Manual | 1 |
| Requirements with test cases | 8 / 8 |
| Interface changes with test cases | 8 / 8 |
| Assertions preserved | 19 / 19 |
| Tests executed | 0 |
| Execution-ready cases | 0 |
