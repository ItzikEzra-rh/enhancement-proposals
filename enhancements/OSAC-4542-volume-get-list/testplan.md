# Testplan — OSAC-4542

## Overview

- **Feature:** OSAC-4542 — Volume Get/List Public API
- **Total test cases:** 17
- **Requirements covered:** 8 of 8 document-local requirement aliases; the approved PRD defines no formal FR/NFR identifiers
- **Interface changes covered:** 3 of 3 document-local API-extension aliases; the approved design has no formal §5 Interface Changes section
- **Traceability note:** The `FR-1`–`FR-8` and `IC-1`–`IC-3` labels below are local aliases for the approved PRD behavior groups and approved design API Extensions. They add no requirements or interfaces and are used only to keep this regenerated plan mechanically traceable without changing either pinned source.

## Test Cases

### FR-1: The public API exposes read-only Get and List access

#### TC-FR1-01: Tenant client retrieves and lists volumes through the public gRPC service

| Interface Change | Priority | Automation |
|-----------------|----------|------------|
| IC-1 | critical | automated |

##### Preconditions

- A tenant client has valid credentials and visibility to at least one active volume in the database.
- The public `osac.public.v1.Volumes` service is registered with `Get` and `List`.

##### Steps

1. Call public gRPC `Volumes/List`) with the tenant client.
2. Take an `id` from the returned items and call public gRPC `Volumes/Get`) with that id.

##### Expected Results

- `List` returns gRPC status `OK` with the visible volume and its `size` and `total` values.
- `Get` returns the same volume id and a public volume object without a mutation response or write side effect.

#### TC-FR1-02: Public mutation methods are unavailable to tenant clients

| Interface Change | Priority | Automation |
|-----------------|----------|------------|
| IC-1 | high | automated |

##### Preconditions

- A tenant client has valid credentials.
- The public service descriptor and authorization policy are loaded.

##### Steps

1. Inspect the public `osac.public.v1.Volumes` service methods.
2. Attempt requests using the public method paths for `Create` and `Delete`) used by the authorization test.

##### Expected Results

- The public service descriptor contains `List` and `Get`) but no public `Create`, `Update`, `Delete`, or `Signal`) method.
- Requests to the nonexistent public mutation paths return gRPC `PermissionDenied` rather than creating or deleting a volume.

### FR-2: Volumes use stable ids and separate tenant-facing names

#### TC-FR2-01: Get uses a visible immutable id as the request key

| Interface Change | Priority | Automation |
|-----------------|----------|------------|
| IC-1 | critical | automated |

##### Preconditions

- A visible active volume exists with a system-generated id, metadata name, and optional display name.

##### Steps

1. List visible volumes and record one item's `id`), `metadata.name`, and `metadata.display_name`.
2. Call public `Get`) using the recorded `id`).
3. Repeat `Get`) with the same id after a second list request.

##### Expected Results

- Both `Get`) responses use the recorded id and preserve the recorded name and display name.
- The request returns gRPC status `OK` when the id is visible; the name is not used as the request key.

#### TC-FR2-02: Volume names remain distinct from ids in the public projection

| Interface Change | Priority | Automation |
|-----------------|----------|------------|
| IC-3 | medium | automated |

##### Preconditions

- At least two visible volumes have different system-generated ids and tenant/project-scoped metadata names.

##### Steps

1. Call public `List`) and collect each item's `id`) and `metadata.name`).
2. Compare the id and name fields for every returned item.
3. Check each name against the RFC 1123 label grammar and compare names within each tenant/project scope.

##### Expected Results

- Every returned item contains both `id`) and `metadata.name`) as separate fields.
- No item uses `metadata.name`) in place of `id`), and duplicate ids are absent from the response.
- Each `metadata.name` matches the RFC 1123 label grammar, and no two active items share a name within the same tenant/project scope.

### FR-3: List follows the standard filter, pagination, and ordering contract

#### TC-FR3-01: List applies offset, limit, size, and total

| Interface Change | Priority | Automation |
|-----------------|----------|------------|
| IC-1 | critical | automated |

##### Preconditions

- More than two visible volumes exist in a deterministic id order.

##### Steps

1. Call public `List`) with `offset=1`) and `limit=1`).
2. Call public `List`) with no pagination limit.
3. Compare the returned item counts and pagination fields.

##### Expected Results

- The paginated response contains one item beginning at the requested offset.
- `size`) equals the number of returned items, and `total`) equals the number of visible matching records.

#### TC-FR3-02: CEL filters accept public fields and reject private fields

| Interface Change | Priority | Automation |
|-----------------|----------|------------|
| IC-1 | high | automated |

##### Preconditions

- Visible volumes exist with at least two distinct `status.state`) values, including `available`).
- A private `status.backend`) value exists on a stored volume.

##### Steps

1. Call public `List`) with the filter `this.status.state == "available"`.
2. Call public `List`) with the filter `this.status.backend == "..." `.

##### Expected Results

- The public-state filter returns only items whose `status.state`) is `available`.
- The private-field filter returns gRPC `InvalidArgument`) and no volume items.

#### TC-FR3-03: List ordering uses the requested order with implicit id ascending tie-break

| Interface Change | Priority | Automation |
|-----------------|----------|------------|
| IC-1 | high | automated |

##### Preconditions

- Visible volumes exist with equal primary sort values and distinct ids.

##### Steps

1. Call public `List`) with a SQL-like order expression on a public field.
2. Inspect the returned sequence for equal primary sort values.

##### Expected Results

- Items are ordered by the requested public field.
- Items with equal primary sort values are ordered by ascending id.
- An order expression naming a private field is rejected with gRPC `InvalidArgument`).

### FR-4: Visibility is isolated by tenant and project scope

#### TC-FR4-01: Tenant member cannot list or get another tenant's volume

| Interface Change | Priority | Automation |
|-----------------|----------|------------|
| IC-1 | critical | automated |

##### Preconditions

- Tenant A and Tenant B each own a visible volume.
- The caller is a tenant member entitled to Tenant A but not Tenant B.

##### Steps

1. Call public `List`) as the Tenant A caller.
2. Call public `Get`) with Tenant B's volume id.

##### Expected Results

- `List`) contains the Tenant A volume and excludes the Tenant B volume.
- `Get`) for Tenant B's id returns gRPC `NotFound`), with no existence-revealing response.

#### TC-FR4-02: Cloud Provider Admin sees volumes across tenants

| Interface Change | Priority | Automation |
|-----------------|----------|------------|
| IC-1 | critical | automated |

##### Preconditions

- Volumes exist in at least two tenants.
- The caller has Cloud Provider Admin visibility.

##### Steps

1. Call public `List`) as the Cloud Provider Admin.
2. Call public `Get`) for one volume from each tenant.

##### Expected Results

- `List`) includes the visible volume from each tenant.
- Each cross-tenant `Get`) returns the requested public volume.

### FR-5: The public representation exposes tenant fields and hides internal routing data

#### TC-FR5-01: Public Volume descriptor matches the exact allowlist

| Interface Change | Priority | Automation |
|-----------------|----------|------------|
| IC-3 | critical | automated |

##### Preconditions

- The generated public Volume descriptor is available.

##### Steps

1. Enumerate the public Volume descriptor fields.
2. Inspect the nested `spec`) and `status`) descriptors.

##### Expected Results

- The descriptor contains exactly `id`, `metadata`), `spec.storage_tier`, `spec.size_gib`, `spec.access_mode`, `status.state`, and `status.message`).
- The descriptor contains no `status.backend`, `status.protocol`, `status.hub`, `status.vendor_volume_id`), or `status.vendor_context`) field.

#### TC-FR5-02: Public Get and List map tenant-facing specification and status fields

| Interface Change | Priority | Automation |
|-----------------|----------|------------|
| IC-3 | high | automated |

##### Preconditions

- A stored volume has known storage tier, size, access mode, state, message, and private routing fields.

##### Steps

1. Retrieve the volume through public `Get`).
2. Retrieve the same volume through public `List`).
3. Inspect the returned objects.

##### Expected Results

- Both public responses contain the storage tier, size, access mode, state, and message values from the stored volume.
- Neither response contains a serialized or reflected value for any private routing field.

### FR-6: Public reads include non-archived states and omit archived records

#### TC-FR6-01: Get and List return creating, available, and deleting volumes

| Interface Change | Priority | Automation |
|-----------------|----------|------------|
| IC-1 | high | automated |

##### Preconditions

- Active inventory records exist in states `creating`), `available`), and `deleting`).

##### Steps

1. Call public `List`) without a state filter.
2. Call public `Get`) for one id in each state.

##### Expected Results

- `List`) includes all three non-archived states.
- Each `Get`) returns the matching state and does not apply an implicit state filter.

#### TC-FR6-02: Fully deprovisioned archived volumes are absent

| Interface Change | Priority | Automation |
|-----------------|----------|------------|
| IC-1 | medium | automated |

##### Preconditions

- A volume has completed deprovisioning and is present in the archived inventory with state `deleted`).

##### Steps

1. Call public `List`) without a state filter.
2. Call public `Get`) using the archived volume id.

##### Expected Results

- The archived `deleted`) volume id is absent from `List`).
- `Get`) returns gRPC `NotFound`) for the archived id.

### FR-7: The same public resource is available through REST and the generic CLI

#### TC-FR7-01: REST Get and List expose the public volume endpoints

| Interface Change | Priority | Automation |
|-----------------|----------|------------|
| IC-2 | high | automated |

##### Preconditions

- The REST gateway has registered the generated public Volume handlers.
- A visible volume exists.

##### Steps

1. Send `GET /api/fulfillment/v1/volumes`).
2. Send `GET /api/fulfillment/v1/volumes/{id}`) for the returned id.

##### Expected Results

- The collection request returns HTTP 200 with a list response containing `size`), `total`), and public volume items.
- The item request returns HTTP 200 with the selected public volume in the response body.
- REST responses omit the private routing fields listed in FR-5.

#### TC-FR7-02: Generic CLI discovers public Volume types through reflection

| Interface Change | Priority | Automation |
|-----------------|----------|------------|
| IC-1 | medium | manual |

##### Preconditions

- The CLI is configured against the public API with credentials for a tenant containing a visible volume.
- Public protobuf reflection exposes the Volume type and Get/List methods.

##### Steps

1. Run `osac get volumes` against the public API.
2. Run `osac get volume <id>` with a visible volume id and structured output.

##### Expected Results

- The list command discovers the public Volume type and prints only the caller-visible items.
- The get command uses the id and prints the public fields without requiring a volume-specific command implementation.

### FR-8: Automated coverage and API documentation describe the public read surface

#### TC-FR8-01: Public gRPC integration path reads a privately created volume

| Interface Change | Priority | Automation |
|-----------------|----------|------------|
| IC-1 | high | automated |

##### Preconditions

- The `osac-dev`) Kind environment is running.
- A standalone volume can be created through the existing private path.
- A tenant-scoped client is available for the public gRPC endpoint.

##### Steps

1. Create a standalone volume through the private API.
2. Call public gRPC `List`) and `Get`) for the created volume.
3. Repeat the read as a client from a tenant without visibility.

##### Expected Results

- The owning tenant receives the created volume through public `List`) and `Get`), with the public field shape.
- The other tenant's `List`) excludes the volume and `Get`) returns gRPC `NotFound`).

#### TC-FR8-02: Published API specification documents only the public read endpoints

| Interface Change | Priority | Automation |
|-----------------|----------|------------|
| IC-2 | low | automated |

##### Preconditions

- The generated or published API specification artifact is available to the documentation validation job.

##### Steps

1. Search the specification for `GET /api/fulfillment/v1/volumes`).
2. Search for `GET /api/fulfillment/v1/volumes/{id}`) and public Volume fields.
3. Search for public Volume mutation operations.

##### Expected Results

- The specification documents both GET paths and the public fields from FR-5.
- The specification contains no public Create, Update, Delete, or Signal operation for Volumes.

## Gaps

### Requirement Coverage Gaps

- All eight approved behavior groups have at least one test case through the document-local `FR-1`–`FR-8` aliases.
- **Formal traceability gap:** the approved PRD has no formal FR/NFR identifiers, so formal built-in requirement coverage cannot be computed. The aliases map one-to-one to the approved in-scope and acceptance behavior groups and must be replaced or confirmed if formal identifiers are established later.
- **Ordering behavior gap:** the PRD requires SQL-like ordering with an implicit `id asc` tie-break, while the approved design documents that the current GenericDAO ignores the requested `order`) and always sorts by id. TC-FR3-03 captures the approved requirement, but the implementation/design conflict must be resolved before the test can pass.

### Interface Change Coverage Gaps

- All three document-local API-extension aliases have test cases: IC-1 covers the public gRPC service, IC-2 covers REST transcoding and specification, and IC-3 covers the public Volume projection.
- **Formal interface traceability gap:** the approved design has no §5 Interface Changes section, so formal built-in IC coverage cannot be computed. The aliases correspond to the three observable API extensions described under “API Extensions” and do not change the approved design.
- **Integration ownership gap:** the approved design names a Kind integration and an external `osac-test-infra` VMaaS E2E read path, but the owning harness for tenant/project isolation is not identified in the permitted workspace.

## Summary

| Metric | Count |
|--------|-------|
| Total test cases | 17 |
| Critical | 6 |
| High | 7 |
| Medium | 3 |
| Low | 1 |
| Automated | 16 |
| Manual | 1 |
| Requirements with test cases | 8 / 8 local aliases; formal FR/NFR total unavailable |
| Interface changes with test cases | 3 / 3 local aliases; formal §5 IC total unavailable |

---

## Provenance

Authored: draft @ design 0.11.1 - f1d6a4b, workspace pilot/OSAC-5320-builtin-4542-v1 @ 554e5a07a (dirty)

<!-- ai-workflow-provenance:{"schema_version":1,"provenance_kind":"session","workflow":"design","workflow_version":"0.11.1","ai_workflows":"f1d6a4b","source_repo":"554e5a07a (dirty)","source_repo_branch":"pilot/OSAC-5320-builtin-4542-v1","commits_behind_main":0,"commits_ahead_main":0,"main_ref":"main","phases":["draft"],"authoring_modes":["skill"],"context_changed":false,"origin_untracked":false} -->
