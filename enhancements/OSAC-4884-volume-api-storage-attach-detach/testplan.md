# Testplan — OSAC-4884

## Overview

- **Feature:** OSAC-4884 — Volume API Storage Attach and Detach
- **Total test cases:** 23
- **Requirements covered:** 8 of 8 derived requirements
- **Interface changes covered:** 9 of 9

The published PRD has no formal requirement IDs. `FR-1` through `FR-6` and
`NFR-1` through `NFR-2` are derived labels used only to provide traceability
from the PRD's scope and user stories. They do not add requirements.

## Test Cases

### FR-1: Authorized users can attach and detach through public gRPC, REST, CLI, and UI surfaces

#### TC-FR1-01: Attach and detach through public gRPC

| Interface Change | Priority | Automation |
|-----------------|----------|------------|
| IC-1 | high | automated |

##### Preconditions

- An authorized tenant user owns an available volume and a compatible ComputeInstance target.
- The fulfillment service and provider adapter are running.

##### Steps

1. Call public `Volumes.Attach` with the volume, ComputeInstance target, and `DATA` role.
2. Poll `GetAttachment` until the phase is `ATTACHED`.
3. Call public `Volumes.Detach` for the same relationship.
4. Poll until the phase is `DETACHED`.

##### Expected Results

- Attach returns an attachment ID and a phase of `ATTACHING` or `ATTACHED`.
- GetAttachment reports `ATTACHED` with a non-empty operation ID.
- Detach returns the same attachment ID with a phase of `DETACHING` or `DETACHED`.
- The final status is `DETACHED` and the provider has one attach and one detach effect.

#### TC-FR1-02: Attach and detach through REST

| Interface Change | Priority | Automation |
|-----------------|----------|------------|
| IC-1 | high | automated |

##### Preconditions

- A REST client has credentials for an authorized tenant user.
- An available volume and compatible BareMetalInstance target exist.

##### Steps

1. POST to `/api/fulfillment/v1/volumes/{volume_id}:attach` with the bare-metal target and `DATA` role.
2. GET the returned attachment collection until the attachment is `ATTACHED`.
3. POST to `/api/fulfillment/v1/volumes/{volume_id}:detach` with the attachment target.
4. GET the attachment until it is `DETACHED`.

##### Expected Results

- The attach response is HTTP 200 and contains the attachment ID and phase.
- The collection response contains the requested target and role without provider credentials.
- The detach response contains the same attachment ID.
- The final GET response contains `phase: DETACHED`.

#### TC-FR1-03: Attach and detach through the CLI

| Interface Change | Priority | Automation |
|-----------------|----------|------------|
| IC-3 | high | automated |

##### Preconditions

- The CLI is configured for an authorized tenant user.
- An available volume and VM target exist.

##### Steps

1. Run `volume attach` with the volume ID, VM target ID, and `DATA` role.
2. Run the CLI status option with the returned attachment ID.
3. Run `volume detach` with the attachment ID.
4. Run the CLI status option again.

##### Expected Results

- The attach output contains the attachment ID and `ATTACHING` or `ATTACHED`.
- The status output eventually contains `ATTACHED` and an operation ID.
- The detach output contains `DETACHING` or `DETACHED`.
- The final status output contains `DETACHED` and no force-detach option is offered.

#### TC-FR1-04: Attach and detach through the UI

| Interface Change | Priority | Automation |
|-----------------|----------|------------|
| IC-4 | medium | manual |

##### Preconditions

- An authorized user can open an available volume in the UI.
- A compatible VM target is visible to the user.

##### Steps

1. Open the volume detail view and choose Attach.
2. Select the VM target and `DATA` role, then submit.
3. Observe the Attachments panel until the phase changes to `ATTACHED`.
4. Choose Detach and observe the panel until the phase changes to `DETACHED`.

##### Expected Results

- The form displays the target and role fields and rejects an empty required target.
- The panel displays the attachment ID, target, role, phase, and last update time.
- The panel displays `ATTACHED` and then `DETACHED` after the corresponding operations.
- The page contains no provider secret, vendor context, or force-detach control.

### FR-2: Direct BMaaS and VMaaS attachment supports target lifecycle and VM boot/data roles

#### TC-FR2-01: Attach and detach a volume from a bare-metal target

| Interface Change | Priority | Automation |
|-----------------|----------|------------|
| IC-1, IC-6 | critical | automated |

##### Preconditions

- A provisioned BareMetalInstance belongs to the caller's tenant.
- The provider adapter advertises the target and volume capability.

##### Steps

1. Attach an available volume to the BareMetalInstance with `DATA` role.
2. Wait for the attachment phase to reach `ATTACHED`.
3. Detach the relationship.
4. Wait for `DETACHED`.

##### Expected Results

- The provider receives the structured bare-metal target and vendor volume ID.
- The attachment phase reaches `ATTACHED` without a CSI call.
- The provider receives one matching detach request.
- The attachment phase reaches `DETACHED`.

#### TC-FR2-02: Attach an existing volume as a VM boot disk

| Interface Change | Priority | Automation |
|-----------------|----------|------------|
| IC-7 | critical | automated |

##### Preconditions

- A VM target is in a lifecycle state that permits boot-disk selection.
- An available volume belongs to the same tenant.

##### Steps

1. Attach the volume to the VM target with `BOOT` role.
2. Wait for storage publication and VM disk reconciliation.
3. Read the ComputeInstance and attachment status.

##### Expected Results

- The ComputeInstance contains the volume reference in its boot-disk configuration.
- The KubeVirt representation contains a matching named volume and disk entry.
- The attachment reports `ATTACHED` only after both storage publication and disk presentation are observed.

#### TC-FR2-03: Hotplug an additional VM data disk

| Interface Change | Priority | Automation |
|-----------------|----------|------------|
| IC-7 | critical | automated |

##### Preconditions

- A running VM target supports data-disk hotplug.
- An available volume belongs to the same tenant.

##### Steps

1. Attach the volume to the VM target with `DATA` role.
2. Wait for the KubeVirt hotplug status and attachment status.
3. Detach the data disk.

##### Expected Results

- KubeVirt reports a named hotplug disk for the attachment.
- The attachment reaches `ATTACHED` after hotplug readiness is observed.
- Detach removes the disk and volume entries and the attachment reaches `DETACHED`.

### FR-3: CaaS continues to use PVC/CSI while adopting the attachment lifecycle

#### TC-FR3-01: CSI publish and unpublish use the Volume API path

| Interface Change | Priority | Automation |
|-----------------|----------|------------|
| IC-5 | critical | automated |

##### Preconditions

- A CSI volume has a valid OSAC volume handle and a registered node.
- The CSI sidecars and private fulfillment attachment API are running.

##### Steps

1. Invoke CSI `ControllerPublishVolume` for the volume, node, capability, and read-only flag.
2. Observe the private attachment record.
3. Invoke CSI `ControllerUnpublishVolume` for the same volume and node.

##### Expected Results

- The private record has `source: CSI` and a `CSI_NODE` target.
- ControllerPublish returns after `ATTACHED` or returns the CSI deadline error while the record remains pending.
- ControllerUnpublish returns after `DETACHED` and retains the same volume handle.

#### TC-FR3-02: Existing CSI attachment remains usable during adoption

| Interface Change | Priority | Automation |
|-----------------|----------|------------|
| IC-5 | critical | automated |

##### Preconditions

- A provider test fixture contains a volume already published to a node through the pre-adoption CSI path.
- The provider's migration capability has passed the rollout gate.

##### Steps

1. Enable the Volume API CSI path for the fixture backend.
2. Reconcile the existing published relationship.
3. Unpublish and publish the same volume on the same node.

##### Expected Results

- The existing vendor volume ID and CSI handle remain unchanged.
- Adoption creates or finds one `CSI_NODE` attachment without recreating the volume.
- Repeated publish and unpublish produce one logical relationship and no duplicate provider attachment.

### FR-4: Attach and detach expose pending outcomes, honor deadlines, retry, and remain idempotent

#### TC-FR4-01: Pending state is observable before provider completion

| Interface Change | Priority | Automation |
|-----------------|----------|------------|
| IC-2 | high | automated |

##### Preconditions

- The provider fixture delays completion of an attach operation.
- The caller has permission to attach the volume.

##### Steps

1. Submit an attach request.
2. Immediately call GetAttachment and ListAttachments.
3. Release the provider delay and poll status.

##### Expected Results

- The attach response contains `ATTACHING`.
- Get and List expose the same attachment ID and `ATTACHING` phase.
- After provider completion, both reads contain `ATTACHED` and the same operation ID.

#### TC-FR4-02: Caller deadline does not create a duplicate operation

| Interface Change | Priority | Automation |
|-----------------|----------|------------|
| IC-1, IC-6 | high | automated |

##### Preconditions

- The provider delays longer than the client RPC deadline.
- The attachment target and volume are valid.

##### Steps

1. Submit attach with a deadline shorter than provider completion.
2. Confirm the client receives `DEADLINE_EXCEEDED`.
3. Retry the same attach request.
4. Read the attachment after provider completion.

##### Expected Results

- The first call returns `DEADLINE_EXCEEDED` after the specified deadline.
- Exactly one attachment row and operation ID exist for the relationship.
- The retry returns the existing attachment rather than creating a second provider call.
- The final phase is `ATTACHED`.

#### TC-FR4-03: Repeated attach and detach are idempotent

| Interface Change | Priority | Automation |
|-----------------|----------|------------|
| IC-1, IC-2, IC-6 | critical | automated |

##### Preconditions

- A volume and target are valid and the provider records call counts.

##### Steps

1. Submit the same attach request twice.
2. Wait for `ATTACHED`.
3. Submit the same detach request twice.
4. Wait for `DETACHED`.

##### Expected Results

- Both attach responses contain the same attachment ID.
- The provider attach call count is one.
- Both detach responses contain the same attachment ID.
- The provider detach call count is one and the final phase is `DETACHED`.

#### TC-FR4-04: Transient provider failure is retried with the same operation ID

| Interface Change | Priority | Automation |
|-----------------|----------|------------|
| IC-6 | high | automated |

##### Preconditions

- The provider fails the first attach call with a retryable error and accepts the next call.
- The retry queue is enabled.

##### Steps

1. Submit attach and record the operation ID.
2. Observe the first retryable failure and pending phase.
3. Wait for the controller retry.

##### Expected Results

- The attachment remains `ATTACHING` after the first retryable error.
- The attempt counter increases and the operation ID remains unchanged.
- The next provider call reaches `ATTACHED` and the retry metric increments once.

### FR-5: Access modes and provider capabilities control multi-attachment and no-op behavior

#### TC-FR5-01: Supported multi-attachment is accepted

| Interface Change | Priority | Automation |
|-----------------|----------|------------|
| IC-1, IC-6 | high | automated |

##### Preconditions

- The volume uses a multi-target access mode.
- The provider advertises multi-attachment support.

##### Steps

1. Attach the volume to target A.
2. Attach the same volume to target B with the compatible read-only mode.
3. Read both attachment records.

##### Expected Results

- Both requests are accepted.
- Two attachment IDs exist with distinct target keys.
- Both phases reach `ATTACHED`.

#### TC-FR5-02: Unsupported multi-attachment is rejected

| Interface Change | Priority | Automation |
|-----------------|----------|------------|
| IC-1, IC-6 | high | automated |

##### Preconditions

- The volume uses a single-target access mode or the provider reports no multi-attachment capability.
- The volume is already attached to target A.

##### Steps

1. Submit attach to target B.
2. Read the volume attachment collection.

##### Expected Results

- The second request returns `FAILED_PRECONDITION`.
- No attachment row for target B is created.
- The existing target A relationship remains `ATTACHED`.

#### TC-FR5-03: Controller-side no-op backend reaches the requested state

| Interface Change | Priority | Automation |
|-----------------|----------|------------|
| IC-5, IC-6 | medium | automated |

##### Preconditions

- The backend capability reports controller-side attach/detach disabled.
- The volume and target pass authorization and access-mode validation.

##### Steps

1. Attach the volume to the target.
2. Detach the same relationship.

##### Expected Results

- Attach reaches `ATTACHED` without a provider publish call.
- Detach reaches `DETACHED` without a provider unpublish call.
- The status identifies the no-op capability rather than an unsupported or failed operation.

### FR-6: Target cleanup, volume deletion protection, and terminal recovery are visible

#### TC-FR6-01: Compute target deletion cleans up attachments

| Interface Change | Priority | Automation |
|-----------------|----------|------------|
| IC-7 | critical | automated |

##### Preconditions

- A ComputeInstance has an `ATTACHED` volume relationship.
- The provider accepts detach.

##### Steps

1. Delete the ComputeInstance.
2. Observe the target cleanup controller and attachment status.
3. Query the volume deletion guard.

##### Expected Results

- Cleanup creates a detach intent for the active relationship.
- The provider receives a detach request before the target reaches final cleanup.
- The attachment reaches `DETACHED` and the target deletion path proceeds.

#### TC-FR6-02: Volume deletion is blocked while attached

| Interface Change | Priority | Automation |
|-----------------|----------|------------|
| IC-8 | critical | automated |

##### Preconditions

- A volume has an `ATTACHED` or `DETACHING` relationship.
- The caller is authorized to delete the volume.

##### Steps

1. Submit volume deletion.
2. Detach the relationship.
3. Submit volume deletion again after the relationship reaches `DETACHED`.

##### Expected Results

- The first deletion returns `FAILED_PRECONDITION`.
- The volume remains available and the attachment remains queryable.
- The second deletion enters the existing volume deletion lifecycle after all attachments are detached.

#### TC-FR6-03: Terminal detach failure remains visible for recovery

| Interface Change | Priority | Automation |
|-----------------|----------|------------|
| IC-8 | high | automated |

##### Preconditions

- A volume is attached and the provider returns a non-retryable detach failure.
- The caller has permission to view the relationship.

##### Steps

1. Submit detach.
2. Wait for the controller to classify the failure as terminal.
3. Read the attachment through API and CLI status.
4. Repair the provider fixture and invoke the operator recovery requeue.

##### Expected Results

- The attachment phase is `FAILED` with a detach operation and sanitized error category.
- Volume deletion returns `FAILED_PRECONDITION` while the failure remains.
- API and CLI output retain the attachment ID and recovery message.
- Requeue reconciles the same operation to `DETACHED` without a force-detach call.

### NFR-1: Authorization and tenant isolation remain enforced across attachment surfaces

#### TC-NFR1-01: Cross-tenant attachment is denied

| Interface Change | Priority | Automation |
|-----------------|----------|------------|
| IC-1, IC-2 | critical | automated |

##### Preconditions

- Tenant A owns the volume and Tenant B owns the target.
- A caller authenticated as Tenant A can access the public API.

##### Steps

1. Submit attach from Tenant A using Tenant B's target ID.
2. Attempt to list or get the relationship from Tenant A.
3. Attempt the same attach from Tenant B using Tenant A's volume ID.

##### Expected Results

- Each cross-tenant attach returns `PERMISSION_DENIED`.
- List/Get does not reveal the other tenant's target or attachment existence.
- No attachment row or provider call is created.

#### TC-NFR1-02: Authorized administrator sees only permitted attachment data

| Interface Change | Priority | Automation |
|-----------------|----------|------------|
| IC-2 | high | automated |

##### Preconditions

- Two tenants have volumes and attachments.
- A Cloud Provider Admin and a Tenant User have their existing role bindings.

##### Steps

1. List attachments as the Tenant User.
2. List attachments as the Cloud Provider Admin.
3. Inspect both responses for provider routing data.

##### Expected Results

- The Tenant User receives only attachments in the tenant scope.
- The Cloud Provider Admin receives the cross-tenant view allowed by existing role policy.
- Neither response contains vendor credentials, CSI secrets, or vendor context.

### NFR-2: Documentation and automated verification cover the public lifecycle and recovery behavior

#### TC-NFR2-01: Documentation covers all required attachment surfaces

| Interface Change | Priority | Automation |
|-----------------|----------|------------|
| IC-9 | medium | manual |

##### Preconditions

- The API, CLI, UI, migration, lifecycle, error, and recovery documentation is available for review.

##### Steps

1. Check the gRPC and REST request/response examples.
2. Check CLI and UI attach/detach instructions.
3. Check pending, retry, deadline, authorization, no-op, migration, deletion guard, and terminal recovery sections.

##### Expected Results

- Each documented surface names the target, role, phase, error behavior, and status observation path.
- The documentation states that force detach is unavailable.
- The migration section labels provider inventory/adoption as a rollout prerequisite rather than an established capability.

#### TC-NFR2-02: Backend-neutral end-to-end suite exercises attach, detach, and required failures

| Interface Change | Priority | Automation |
|-----------------|----------|------------|
| IC-9 | medium | automated |

##### Preconditions

- The designated backend-neutral E2E environment is deployed with fulfillment, operator, CSI driver, and test provider components.

##### Steps

1. Run the representative BMaaS or VMaaS attach/detach flow.
2. Run success, retry, invalid-target, cross-tenant, backend-failure, and CSI-migration scenarios.
3. Collect attachment status, provider call records, and deletion-guard results.

##### Expected Results

- The suite records an `ATTACHED` then `DETACHED` relationship for the representative flow.
- Retry and backend-failure cases record the expected attempt and terminal states.
- Invalid-target and cross-tenant cases record the specified gRPC error codes.
- Migration leaves the existing volume handle and active relationship usable.

## Gaps

### Requirement Coverage Gaps

All 8 derived PRD requirements have test cases. The provider-specific
capability and migration adoption questions remain design gates; tests are
conditioned on the provider fixture proving those capabilities.

### Interface Change Coverage Gaps

All 9 interface changes are exercised by at least one test case.

## Summary

| Metric | Count |
|--------|-------|
| Total test cases | 23 |
| Critical | 9 |
| High | 10 |
| Medium | 4 |
| Low | 0 |
| Automated | 21 |
| Manual | 2 |
| Requirements with test cases | 8 / 8 |
| Interface changes with test cases | 9 / 9 |

---

## Provenance

Authored: draft @ design 0.11.1 - f1d6a4b, workspace main @ 554e5a07a

<!-- ai-workflow-provenance:{"schema_version":1,"provenance_kind":"session","workflow":"design","workflow_version":"0.11.1","ai_workflows":"f1d6a4b","source_repo":"554e5a07a","source_repo_branch":"main","commits_behind_main":0,"commits_ahead_main":0,"main_ref":"main","phases":["draft"],"authoring_modes":["skill"],"context_changed":false,"origin_untracked":false} -->
