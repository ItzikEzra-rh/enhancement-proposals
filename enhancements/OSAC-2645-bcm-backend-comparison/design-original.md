title: bcm-backend-integration
authors:
  - mennyaboush@gmail.com
creation-date: 2026-07-23
last-updated: 2026-07-23
tracking-link:
  - https://redhat.atlassian.net/browse/OSAC-1339
prd:
  - "prd.md"
see-also:
  - "/enhancements/bare-metal-fulfillment"
  - "/enhancements/OSAC-1118-baremetal-instance-api"
replaces:
  - N/A
superseded-by:
  - N/A

# BCM Backend Integration for BMaaS

## Summary

This design adds NVIDIA Base Command Manager (BCM) as a pluggable inventory
backend for the bare-metal-fulfillment-operator, using a hybrid architecture:
BCM serves as the inventory source of truth while Metal3 BareMetalHost CRs
handle power management. See [PRD](prd.md) for detailed requirements.

## Motivation

The bare-metal-fulfillment-operator provisions bare metal hosts through a
pluggable backend interface defined in OSAC-1032. Customers who manage their
bare metal infrastructure through BCM cannot fulfill BareMetalInstance
requests through OSAC without a BCM inventory backend.

Adding BCM also validates that the pluggable architecture accommodates
inventory sources with different characteristics: BCM has no native assignment
concept, no optimistic locking, and introduces a host readiness delay when
bridging to Metal3 for power management. Solving these constraints within the
existing interface proves the architecture is extensible to future backends
(Netbox, NICo).

### Goals

- Implement the BCM inventory backend within the existing `inventory.Client`
  interface — no changes to CRDs or main.go initialization flow. The
  controller requires two minor additions: ErrHostNotReady handling and
  InventoryHostID write-back after AssignHost (no-op for existing backends).
  [Codebase: bare-metal-fulfillment-operator/internal/inventory/client.go]
- Reuse the Metal3 management backend for power control — no new management
  client. [Locked: D2]
- Handle the BMH readiness delay (~2-5 minutes) unique to the BCM hybrid
  approach with clear status messaging and automatic retry. [Locked: D11]
- Support E2E testing in CI without a real BCM instance via a BCM simulator.
  [Locked: D13]
- Keep BCM transparent to tenants — no tenant-facing API or workflow changes.
  [Locked: D7]

### Non-Goals

- Sysinfo-based hardware auto-classification from BCM. Host type matching uses
  admin-assigned labels.
- BCM power control via BCM API. Power control goes exclusively through
  Metal3/BMH.
- PhysicalNode support. Only LiteNode is supported — OSAC manages the OS.
  [Locked: D4]
- Multi-backend deployments. Each deployment uses one inventory backend.
  [Locked: D9]
- Automated node registration in BCM. Admins pre-register LiteNodes as a Day-0
  prerequisite. [Locked: D5]

## Proposal

The BCM backend consists of three components:

1. **BCM Go HTTP client** — a lightweight JSON API client with mTLS
   authentication that wraps BCM's `cmdevice` service calls (`getDevices`,
   `getDevice`, `updateDevice`).

2. **BCM inventory client** (`internal/inventory/bcm.go`) — implements the
   `inventory.Client` interface. `FindFreeHost` queries BCM for unassigned
   LiteNodes. `AssignHost` writes the assignment identifier to BCM
   `extra_values` and creates an on-demand BareMetalHost CR. `UnassignHost`
   clears `extra_values` and deletes the BMH CR.

3. **ErrHostNotReady handling** — a new sentinel error in the management
   interface that the controller uses to requeue with a clear status message
   when the on-demand BMH is not yet ready for power operations.

No changes are required to the BareMetalInstance or BareMetalPool CRD types
or the main.go initialization flow. The BCM backend self-registers via the
existing `init()` pattern. The controller requires two minor changes:
ErrHostNotReady handling in `reconcileManagement`, and writing back the
`InventoryHostID` from `AssignHost` to `ExternalHostID` (the BCM backend
returns a different format than `FindFreeHost` because the BMH CR does not
exist yet at discovery time — see InventoryHostID mapping below). This
write-back is a no-op for existing backends since their format does not
change between FindFreeHost and AssignHost.

### Workflow Description

#### Day-0: Admin Configures BCM Backend

**Actor:** Cloud Infrastructure Admin
**Starting state:** bare-metal-fulfillment-operator deployed, LiteNodes
pre-registered in BCM.

1. Admin creates a Kubernetes Secret `bcm-certs` containing the mTLS client
   certificate and key for BCM access.
2. Admin creates the inventory configuration (`inventory.yaml`) as a
   Kubernetes Secret:
   ```yaml
   name: bcm-inventory
   type: bcm
   hostClass: bcm
   networkClass: cudn_net
   options:
     bcm:
       url: "https://bcm-head:8081"
       credentialsSecret: "bcm-certs"
       insecureSkipVerify: false
      ```
3. Admin sets the management configuration to Metal3:
   ```yaml
   name: metal3-management
   type: metal3
   options:
     metal3:
       namespace: "osac-baremetal"
   ```
4. Admin deploys or restarts the operator. The operator loads the BCM
   inventory client and Metal3 management client.

#### Day-2: Tenant Provisions a BareMetalInstance

**Actor:** Tenant User (via fulfillment-service API)
**Starting state:** BCM backend configured, LiteNodes available in BCM.

```mermaid
sequenceDiagram
    participant TU as Tenant User
    participant FS as fulfillment-service
    participant BMI as BareMetalInstance CR
    participant CTRL as BMI Controller
    participant BCM as BCM JSON API
    participant BMH as BareMetalHost CR
    participant M3 as Metal3/BMO
    participant AAP as AAP Controller

    TU->>FS: Create BareMetalInstance
    FS->>BMI: Create CR (hostType=h100)

    rect rgb(240, 248, 255)
    Note over CTRL,BMI: reconcileInventory (Phase: Allocating)

    Note over CTRL,BMI: Reconcile 1: FindFreeHost
    CTRL->>BCM: getDevices (filter LiteNode, unassigned)
    BCM-->>CTRL: List of free hosts
    CTRL->>CTRL: Select matching host
    CTRL-->>BMI: Write ExternalHostID = BCM hostname
    Note over CTRL: Return — requeue

    Note over CTRL,BMI: Reconcile 2: AssignHost
    CTRL->>BCM: updateDevice (set extra_values.osac_instance_id)
    BCM-->>CTRL: success
    CTRL->>BCM: getDevice (re-read to verify assignment)
    BCM-->>CTRL: confirmed owner
    CTRL->>BMH: Create BMH CR (BMC address, credentials, boot MAC)
    CTRL-->>BMI: Write ExternalHostID = namespace/name, HostClass, NetworkClass
    Note over CTRL,BMI: Phase: Progressing
    Note over CTRL: Return — HostClass set triggers routing switch
    end

    rect rgb(245, 245, 240)
    Note over CTRL,BMI: reconcileManagement (HostClass != "")

    Note over CTRL,M3: BMH readiness delay (~2-5 min)
    CTRL->>BMH: Check BMH status (via GetPowerState)
    alt BMH not ready (ErrHostNotReady)
        CTRL-->>BMI: Update status: "Host being readied"
        CTRL->>CTRL: Requeue (10s interval)
    else BMH ready
        Note over CTRL,AAP: Reconcile 3+: Provisioning (async, multi-reconcile)
        CTRL->>AAP: Trigger provision job
        loop Poll until complete
            CTRL->>AAP: Check job status
            AAP-->>CTRL: In progress / Complete
        end
        CTRL->>BMH: Patch spec.online=true
        Note over BMH,M3: BMO reconciles actual power change
        CTRL-->>BMI: Phase: Ready
    end
    end
```

The diagram shows the full provisioning flow across multiple reconcile loops.
Key architectural points:

- **Reconcile boundaries:** FindFreeHost and AssignHost happen in separate
  reconcile loops. ExternalHostID is persisted to the CR between them, making
  the flow crash-safe at every boundary.
- **HostClass routing switch:** The controller routes to `reconcileInventory`
  when `Spec.HostClass` is empty and to `reconcileManagement` when it is set.
  AssignHost writes HostClass, which is a one-way gate — all subsequent
  reconciles go to the management path.
- **ExternalHostID format change:** FindFreeHost returns the BCM hostname
  (e.g., `node001`). After AssignHost creates the BMH CR, ExternalHostID is
  updated to `namespace/name` format (e.g., `osac-baremetal/node001`) so the
  Metal3 management client can locate the BMH. This write-back is a no-op for
  existing backends.
- **Async provisioning:** The AAP provision template is triggered as a job
  and polled across multiple reconcile loops, not a synchronous call.
- **BMH readiness delay:** Unique to the BCM backend (~2-5 minutes) because
  the BMH is created on-demand. Surfaced via a clear status condition.

#### Deprovisioning Flow

**Starting state:** BareMetalInstance in Ready state.

1. User deletes the BareMetalInstance.
2. Controller runs `handleDeletion`:
   a. Management cleanup: triggers AAP deprovision template (wipes OS, detaches
      networks, powers off via Metal3). Removes management finalizer.
   b. Inventory cleanup: calls `UnassignHost` which clears
      `extra_values.osac_instance_id` in BCM and deletes the on-demand BMH CR.
      Removes inventory finalizer.
3. Kubernetes deletes the BareMetalInstance CR.

#### Error: BCM Unreachable

When the BCM JSON API is unreachable (connection refused, TLS handshake
failure, timeout), the controller:

1. Sets the BareMetalInstance condition `Allocated=False` with reason
   `BCMConnectionError` and a message identifying BCM as the failing component.
2. Returns the error to controller-runtime (`return ctrl.Result{}, err`),
   which applies its built-in rate-limited exponential backoff. This is the
   same behavior as any other inventory backend error — no BCM-specific
   retry logic is needed.
3. The status message is visible to the user: "BCM inventory backend
   unreachable: \<error detail\>".

### API Extensions

**New finalizer:** None — reuses the existing `osac.openshift.io/inventory`
finalizer.

**New CRDs:** None.

**Modified resources:**
- `BareMetalHost` CRs (metal3.io/v1alpha1) — created on-demand during
  `AssignHost` and deleted during `UnassignHost`. These are owned by the
  operator, not by users. If the operator is down, existing BMH CRs remain
  and Metal3 continues managing power for already-provisioned hosts. New
  provisioning requests queue until the operator recovers.

## UX Alignment

No `@temp-api` file exists for BareMetalInstance in osac-ux. BCM is transparent
to tenants — no UI changes are required. [Locked: D8]

### Implementation Details/Notes/Constraints

#### BCM Go HTTP Client

A new package `internal/inventory/bcm/` (or a file `internal/inventory/bcm.go`)
implements the HTTP client for BCM's JSON API.

**Authentication:** mTLS with client certificate and key. The JSON API does not
accept basic auth. [Locked: D10]

**Transport configuration:**
```go
type BCMClientConfig struct {
    URL                string `json:"url"`
    CredentialsSecret  string `json:"credentialsSecret"`
    InsecureSkipVerify bool   `json:"insecureSkipVerify"`
}
```

**API call pattern:** All JSON API calls use `POST /json` with a body of
`{"service": "<svc>", "call": "<method>", "args": <args>}`. Args are positional
arrays, not named objects.

**Key API methods used:**

| Operation | Service.Call | Args | Returns |
|-----------|-------------|------|---------|
| List all devices | `cmdevice.getDevices` | `[]` | Array of device objects |
| Get single device | `cmdevice.getDevice` | `["<hostname>"]` | Device object or `null` |
| Update device | `cmdevice.updateDevice` | `[<full device object>]` | `{success: bool, validation: []}` |

**Critical constraint — full-object replacement:** BCM's `updateDevice`
requires the entire device object, not partial updates. The client must GET the
device, modify `extra_values`, and PUT the full object back. Sending only
changed fields causes validation errors (`NOT_NULL` on required fields like
`partition`).

**`getNode` vs `getDevice`:** `getNode` returns `null` for LiteNodes without
error. The client must always use `getDevice`.

**Error handling:** The client maps BCM error responses to typed Go errors:

| BCM Response | Go Error |
|-------------|----------|
| TCP connection refused / timeout | `ErrBCMConnectionFailed` |
| TLS handshake failure | `ErrBCMTLSFailed` |
| `{"errormessage": "certificate..."}` | `ErrBCMAuthFailed` |
| `{"success": false, "validation": [...]}` | `ErrBCMValidation` (wraps validation details) |
| `null` response for `getDevice` | Not an error — device not found |
| HTTP 5xx | `ErrBCMServerError` |

#### BCM Inventory Client

Implements `inventory.Client` and registers as `newClientFuncs["bcm"]` via
`init()`.
[Codebase: bare-metal-fulfillment-operator/internal/inventory/client.go]

**`FindFreeHost(ctx, matchExpressions) (*Host, error)`**

1. Calls `cmdevice.getDevices` to list all devices.
2. Filters client-side:
   - `childType == "LiteNode"` (hardcoded, per [Locked: D4])
   - `extra_values` is not `null`. Hosts with `extra_values: null` are
     skipped with a warning: "Host (hostname) has no extra_values
     configured — set resource_class and osac_bmc_credentials_secret
     in BCM extra_values during Day-0 registration"
   - `extra_values.resource_class` matches `matchExpressions["hostType"]`.
     Hosts without `resource_class` are skipped with a warning:
     "Host (hostname) has no resource_class in extra_values"
   - `extra_values.osac_instance_id` is absent (host is not already
     assigned)
   - hostname does not contain `/` (required because `namespace/name`
     composite IDs use `/` as delimiter — a hostname with `/` would cause
     `ParseHostID` to silently misparse the ID)
3. Shuffles candidates randomly (same pattern as OpenStack and Metal3 backends)
   to reduce contention.
4. Returns the first match as an `inventory.Host`:
   - `InventoryHostID` = BCM device `hostname` (unique identifier in BCM)
   - `HostType` = `extra_values.resource_class` (the same field used for matching)
   - `HostClass` = config `HostClass` (e.g., `"bcm"`)
   - `NetworkClass` = config `NetworkClass` (e.g., `"cudn_net"`)
   - `ManagedBy` = `shared.OsacDefaultManagedByValue` (`"baremetal"`)
5. Returns `nil, nil` if no matching free host is found.

**`AssignHost(ctx, inventoryHostID, bareMetalInstanceID, labels) (*Host, error)`**

1. Calls `cmdevice.getDevice(inventoryHostID)` to get the full device object.
   If `getDevice` returns `null` (device was removed from BCM between
   FindFreeHost and AssignHost), returns `nil, nil` — the controller clears
   ExternalHostID and retries FindFreeHost on the next reconcile.
2. Checks `extra_values.osac_instance_id` — if present and different from
   `bareMetalInstanceID`, returns `nil, nil` (host taken by another instance,
   same contention convention as OpenStack/Metal3).
3. Sets `extra_values.osac_instance_id = bareMetalInstanceID` on the device
   object. If BMC address discovery (Priority 2) was performed, also sets
   `extra_values.osac_bmc_address` to the validated BMC URL — the single
   `updateDevice` call persists both fields atomically, ensuring the
   discovered address is cached for future assignments. No tenant data is
   stored — only the opaque instance ID and infrastructure metadata.
   [Locked: D14]
4. Calls `cmdevice.updateDevice` with the full modified device object.
5. **Verify-after-write:** Re-reads the device via `getDevice` and confirms
   `extra_values.osac_instance_id` still equals `bareMetalInstanceID`. If not,
   another writer overwrote the assignment — returns `nil, nil`.
   **Concurrency note:** The operator's process-local mutex
   (`inventory.TryLock`) and controller-runtime leader election already
   prevent concurrent allocations from the same operator deployment. The
   verify-after-write serves as defense-in-depth against external writers
   (e.g., manual BCM edits or a second deployment without leader election).
   Neither the OpenStack nor Metal3 backends implement verify-after-write —
   they rely on the lock and leader election alone. The BCM backend adds the
   extra check because BCM lacks the optimistic concurrency that Kubernetes
   provides for Metal3 BMH updates.
6. Creates a BareMetalHost CR in the configured Metal3 namespace:
   - `metadata.name` = BCM device hostname
   - `metadata.namespace` = Metal3 namespace from management config
   - `metadata.labels`:
     - `osac.openshift.io/managed-by` = `"baremetal"`
   - `spec.bmc.address` = resolved via the layered BMC discovery strategy
     (see "BMC Address Discovery" section below)
   - `spec.bmc.credentialsName` = read from
     `extra_values.osac_bmc_credentials_secret` — a pre-existing K8s Secret
     created by the admin or setup tooling during Day-0
   - `spec.bootMACAddress` = device MAC from BCM
   - `spec.online` = `false` (controller manages power via reconcileManagement)
   - `spec.consumerRef` = `{apiVersion: "osac.openshift.io/v1alpha1", kind:
     "BareMetalInstance", name: bareMetalInstanceID}`
**Partial failure recovery:** The ordering of operations (BCM write before BMH creation) is deliberate. If the operator crashes after writing `osac_instance_id` to BCM but before creating the BMH, the next reconcile calls `AssignHost` again with the same `bareMetalInstanceID`. The BCM client detects that `osac_instance_id` already matches (step 2), skips the write, and proceeds to create the BMH — idempotent recovery. If the BMH creation fails after a successful BCM write, the controller retries on the next reconcile. The `osac_instance_id` in BCM acts as a reservation — no other instance can claim the host. During unassignment, the reverse applies: BMH deletion before BCM update means a crash after BMH deletion leaves `osac_instance_id` set in BCM. The next reconcile retries `UnassignHost`, which handles the missing BMH (ignores NotFound) and clears `osac_instance_id` — also idempotent.

7. Returns the `Host` struct with the BMH `namespace/name` as the
   `InventoryHostID` so the management client can locate it.

**`UnassignHost(ctx, inventoryHostID, labels) error`**

1. Parses `inventoryHostID` using `ParseHostID(inventoryHostID)` to extract
   `(namespace, hostname)` — does NOT read the BMH to get the hostname.
2. Calls `cmdevice.getDevice(hostname)` to get the full device. If BCM
   returns `null` (device not found), treats the device as already cleaned
   up and skips to step 5.
3. Removes `osac_instance_id` AND the labels passed in the `labels`
   parameter from `extra_values`. Preserves admin-configured keys
   (`osac_bmc_address`, `osac_bmc_credentials_secret`, `resource_class`)
   and any non-OSAC metadata. This ensures the host is immediately
   available for re-assignment without repeating Day-0 setup or BMC
   discovery.
4. Calls `cmdevice.updateDevice` with the modified device.
5. Deletes the BMH CR by `namespace/name` (ignoring NotFound if already
   deleted). The BMC credentials Secret is not touched — it is
   admin-managed and reusable for future assignments of the same host.

This approach is idempotent — if the BMH is already deleted, the delete is
a no-op. If the BCM device is not found (returns null), it is treated as
already cleaned up.

**InventoryHostID mapping:** During the allocation flow, the controller calls
`FindFreeHost` which returns the BCM hostname as `InventoryHostID`. After
`AssignHost` creates a BMH, the `InventoryHostID` is updated to the BMH's
`namespace/name` (the standard Metal3 format) so the management client can
operate on it. Since the BMH `metadata.name` is the BCM hostname,
`UnassignHost` can derive the hostname directly from the BMH name.

#### BMC Address Discovery (Layered Strategy)

When `AssignHost` creates a BMH CR, it needs `spec.bmc.address` (the full BMC
URL) and `spec.bmc.credentialsName` (a K8s Secret). This is a consequence of
the hybrid architecture [Locked: D1, D2]: BCM handles inventory but Metal3
handles power management. Metal3 requires `spec.bmc.address` on every
BareMetalHost CR to communicate with the host's baseboard management
controller for power operations (on/off/reboot via IPMI or Redfish). BCM
itself already knows how to reach each host's BMC, but it does not expose this
in a format Metal3 can consume — the operator must bridge the gap.

The BCM backend uses a layered strategy that accommodates different deployment
scenarios:

**Priority 1 — Pre-configured BMC address in `extra_values`:**
If `extra_values.osac_bmc_address` exists on the BCM device, use it directly
as `spec.bmc.address`. This allows admins or tooling to provide a
fully-formed BMC URL (e.g.,
`redfish-virtualmedia+https://10.141.0.1/redfish/v1/Systems/1`) during Day-0
registration. No Redfish discovery or network access to BMC is required.

**Priority 2 — Extract from BCM device data + Redfish discovery:**
If no pre-configured address exists, the client reads the BCM device's
`interfaces` array for `childType == "NetworkBmcInterface"`:
- The interface `ip` field provides the BMC IP address.
- The interface `name` determines the BMC protocol:
  `rf0` → Redfish, `ipmi0` → IPMI, `ilo0` → iLO, `drac0` → iDRAC.
  [Codebase: osac-aap/collections/.../plugins/filter/bcm.py lines 4-9]
- For IPMI: the URL is `ipmi://<bmc_ip>` — no further discovery needed.
- For Redfish/iDRAC/iLO: the client must discover the system path by
  querying the BMC's Redfish API:
  1. `GET https://<bmc_ip>/redfish/v1/Systems/` → list of system URIs
  2. For each system, fetch `EthernetInterfaces` and read MAC addresses
  3. Match the host's `bootMACAddress` to find the correct system path
  4. Construct: `redfish-virtualmedia+https://<bmc_ip><system_path>`
  5. Validate the constructed URL by making a Redfish health check call
     to the BMC. If it fails, return an error rather than caching a
     broken URL.

**BMC target validation:** Before making any outbound connection to a BMC IP (for Redfish discovery or health check), the client validates the target:
   - Allowed URL schemes: `ipmi`, `redfish-virtualmedia+https`, `idrac-virtualmedia+https`, `ilo5-virtualmedia+https` (the composite `<protocol>+https` form matches what Priority 2 constructs and what Metal3 BMO expects)
   - Rejected targets: loopback addresses (`127.0.0.0/8`, `::1`), link-local (`169.254.0.0/16`, `fe80::/10`), cloud metadata endpoints (`169.254.169.254`)
   - Rejected ports: only standard BMC ports are accepted (443 for Redfish, 623 for IPMI)
   - If validation fails, the client returns an actionable error and does NOT cache the invalid URL

- The validated URL is cached in BCM `extra_values.osac_bmc_address` so
  subsequent assignments skip discovery entirely (Priority 1 applies).

**Priority 3 — Fail with actionable error:**
If neither `extra_values.osac_bmc_address` nor a `NetworkBmcInterface` exists,
`AssignHost` returns an error: "BMC info not available for host \<hostname\> —
configure osac_bmc_address in BCM extra_values or register the node with BMC
interface data."

**BMC credentials:** The admin or setup tooling pre-creates a K8s Secret
with BMC credentials (`username`, `password` keys) in the Metal3 namespace
during Day-0 and stores the Secret name in
`extra_values.osac_bmc_credentials_secret`. The operator reads this value
and sets it as `spec.bmc.credentialsName` on the BMH CR. If
`osac_bmc_credentials_secret` is not set, `AssignHost` fails with error:
"BMC credentials Secret not configured for host (hostname) — set
osac_bmc_credentials_secret in BCM extra_values."

**Redfish discovery requirements:**
- The operator pod must have network access to BMC IP addresses. If BMCs are
  on an isolated out-of-band network unreachable from the management cluster,
  use Priority 1 (pre-configured addresses) instead.
- A Go Redfish client library (`github.com/stmcginnis/gofish`) is required as
  a new dependency.
- BCM LiteNodes must be registered with `NetworkBmcInterface` data (via
  `bcm_add_lite_nodes.py` with the `bmc:` block in the inventory YAML)
  for Priority 2 BMC address discovery. Nodes registered without BMC
  interface data fall through to Priority 3.
- Admin must pre-create a BMC credentials Secret in the Metal3 namespace
  and store its name in `extra_values.osac_bmc_credentials_secret`.

#### ErrHostNotReady Sentinel Error

A new sentinel error in the management package:

```go
var ErrHostNotReady = errors.New("host is not ready for management operations")
```

The Metal3 management client's `GetPowerState` returns `ErrHostNotReady` when
the BMH exists but is not in an operational state (e.g., `registering`,
`inspecting`, or `preparing`). [Locked: D11]

The BareMetalInstance controller handles `ErrHostNotReady` in
`reconcileManagement`:

1. Sets condition `Available=False` with reason `HostNotReady` and message
   "Host is being readied for provisioning (~2-5 minutes)".
2. Returns `ctrl.Result{RequeueAfter: ManagementRecheckIntervalDuration}` (10s
   default).
3. Tracks the first `ErrHostNotReady` timestamp and the BMH UID in
   annotations (`osac.openshift.io/host-ready-since` and
   `osac.openshift.io/host-ready-bmh-uid`). The timer is tied to the
   current BMH identity:
   - If the BMH UID changes (BMH was recreated), the timer resets — a
     fresh BMH gets a full timeout window.
   - When the BMH becomes ready, both annotations are cleared so that
     any future readiness failure (e.g., after a BMH recreation) starts
     a fresh timeout period.
   - If the elapsed time exceeds `OSAC_HOST_READY_TIMEOUT` (default 15
     minutes) for the same BMH UID:
     - Calls `UnassignHost` to clear `osac_instance_id` from BCM
       `extra_values` and delete the BMH CR — releasing the host back
       to the available pool.
     - Transitions the BareMetalInstance to `Failed` with message: "Host
       preparation timed out after (duration) — BMH (name) did not reach
       ready state. Host released back to inventory."
4. The user sees the status message on the BareMetalInstance.

This is a small, scoped change to the existing Metal3 management client and the
controller's management reconciliation path.

#### Inventory Configuration

The BCM backend uses the same configuration pattern as OpenStack and Metal3
— YAML file at `OSAC_INVENTORY_CONFIG_PATH` (default
`/etc/osac/inventory/inventory.yaml`):

```yaml
name: bcm-inventory
type: bcm
hostClass: bcm
networkClass: cudn_net
options:
  bcm:
    url: "https://bcm-head:8081"
    credentialsSecret: "bcm-certs"
    insecureSkipVerify: false
```

The `options.bcm` sub-map is unmarshaled into `BCMClientConfig`. The
`credentialsSecret` field references a Kubernetes Secret containing:
- `tls.crt` — mTLS client certificate (required)
- `tls.key` — mTLS client key (required)
- `ca.crt` — CA certificate for verifying the BCM server's TLS identity
  (optional — if omitted, the system trust store is used)

When `insecureSkipVerify` is `false` (the production default), the client
verifies the BCM server's certificate against the CA in `ca.crt` or the
system trust store. `insecureSkipVerify: true` disables server verification
and should only be used in test environments.

Management configuration remains `type: metal3` — no change required.
[Locked: D2]

Networking is independent of the inventory backend. The existing OSAC
networking stack handles all network operations via the configured
`networkClass`. BCM has no networking role. [Locked: D12]

#### Helm Chart Changes

The operator Helm chart (`charts/operator/values.yaml`) adds:

```yaml
secrets:
  bcmCerts: "bcm-certs"  # K8s Secret with tls.crt and tls.key
```

The `credentialsSecret` field in the inventory config names the K8s Secret
directly — the operator reads it via the Kubernetes API at startup.

#### CaaS/BMaaS Coexistence and Migration

CaaS currently manages BCM nodes through a sync playbook
(`playbook_osac_import_bcm_agents.yml`) that runs every ~10 minutes via AAP.
It reads all LiteNodes from BCM, creates BareMetalHost CRs and BMC Secrets
on the cluster, cleans up stale resources, and labels agents. The playbook
is read-only toward BCM — it never writes to `extra_values` or `notes`.

With the BMaaS BCM backend, the target state is: CaaS consumes BCM nodes
through the BMaaS API (BareMetalInstance requests) rather than querying BCM
directly. BMaaS becomes the single owner of the BCM node pool.

**Why migration matters:** The playbook and BMaaS operator cannot run
simultaneously against the same nodes. The playbook imports ALL LiteNodes
and creates BMH CRs for each one. BMaaS creates BMH CRs on-demand. If both
run, they create duplicate BMH CRs pointing at the same physical BMC,
causing Metal3 conflicts. Additionally, the playbook does not read BCM
`extra_values`, so it cannot detect nodes that BMaaS has already assigned.

**Migration from playbook to BMaaS requires addressing these issues:**

1. **Existing CaaS BMH CRs must be adopted.** Nodes currently managed by
   CaaS have BMH CRs labeled `managed-by: import-bcm-agents` and no
   `osac_instance_id` in BCM `extra_values`. The migration must either
   re-create these as BMaaS-managed resources or update their labels and
   mark them as assigned in BCM.

2. **Existing CaaS nodes must be marked in BCM.** Without `osac_instance_id`
   in `extra_values`, BMaaS sees these nodes as "free" and could
   double-assign them. The migration must write assignment data to BCM for
   every node currently in use by CaaS.

3. **Deletion of CaaS-era instances must work through BMaaS.** After
   migration, the playbook no longer runs — it was responsible for cleaning
   up stale BMH CRs. BMaaS must be able to deprovision and release nodes
   that were originally provisioned by CaaS.

4. **The playbook must be disabled before BMaaS goes live.** Running both
   simultaneously causes duplicate BMH CRs. The AAP job must be stopped
   as part of the cutover.

5. **Rollback path.** If BMaaS has issues after migration, re-enabling the
   playbook must be possible without orphaning resources.

This migration is a prerequisite for CaaS to use the BMaaS API for BCM
nodes and should be tracked as a separate Jira task under OSAC-1339.

### Security Considerations

**mTLS credential management:** BCM client certificates are stored as
Kubernetes Secrets and mounted as files. The BCM HTTP client uses
`tls.Config.GetClientCertificate` with a filesystem watcher (same
`certwatcher.CertWatcher` the operator already uses for webhook and
metrics certs) to detect rotated certificates automatically. No operator
restart is needed for certificate rotation. [Locked: D10]

**Tenant isolation:** Only the opaque `osac_instance_id` (BareMetalInstance
UID) is written to BCM `extra_values`. No tenant name, namespace, or other
identifying data is exposed to BCM. A BCM administrator who needs tenant
context can query the fulfillment-service API using the instance ID.
[Locked: D14]

**BCM API access scope:** The operator requires only `cmdevice.getDevices`, `cmdevice.getDevice`, and `cmdevice.updateDevice`. Production deployments SHOULD use a BCM certificate profile scoped to these three methods rather than the `admin` profile. The `admin` profile (full CMDevice access) works but grants more permissions than needed. Creating a scoped profile is a BCM-side configuration step documented in the operator deployment guide — no code change is required.

**Input validation:** The BCM client validates all responses before use:
- Device hostname must be non-empty
- `extra_values` must be a valid JSON object or null
- MAC address must be non-empty and match the Metal3 BMH CRD pattern
  (`[0-9a-fA-F]{2}(:[0-9a-fA-F]{2}){5}`). Hosts with missing or malformed
  MAC are skipped with a warning
- BCM hostnames are used in BMH CR names — validated against Kubernetes naming
  rules (lowercase, DNS-safe)
- BCM hostnames must not contain `/` — the operator uses `/` as the
  delimiter in `namespace/name` composite IDs. Hosts with hostnames
  containing `/` are skipped during `FindFreeHost` with a warning:
  "Host (hostname) has invalid hostname — must not contain '/'"

### Failure Handling and Recovery

| Failure Mode | What Happens | Recovery | User Observes |
|-------------|-------------|----------|---------------|
| BCM unreachable during FindFreeHost | Controller returns error, requeues | Automatic retry (30s default) with controller-runtime backoff | BareMetalInstance stays in `Allocating`, condition message: "BCM inventory backend unreachable" |
| BCM unreachable during AssignHost | Controller returns error, requeues | Automatic retry. No partial state — assignment is atomic (write + verify) | Same as above |
| BCM unreachable during UnassignHost | Controller returns error, requeues | Automatic retry. BMH CR may already be deleted; unassign is idempotent | BareMetalInstance stays in `Deleting` |
| Assignment race (another writer overwrites) | Verify-after-write detects mismatch, returns nil | Controller clears ExternalHostID, retries FindFreeHost on next reconcile | Brief delay, then allocates a different host |
| BMH not ready after creation | Metal3 management returns ErrHostNotReady | Controller requeues every 10s, surfaces status message | "Host is being readied for provisioning (~2-5 minutes)" |
| BMH never becomes ready (stuck) | Controller requeues until `OSAC_HOST_READY_TIMEOUT` (default 15 min) | Calls UnassignHost (releases host back to BCM pool, deletes BMH CR), then transitions to `Failed` | "Host preparation timed out after 15m — BMH node001 did not reach ready state. Host released back to inventory." |
| BCM device removed while assigned | Not detected — OSAC does not health-check assigned nodes in BCM. The instance continues in `Ready` state. When the user eventually deletes the instance, UnassignHost calls getDevice, gets null, treats it as already cleaned up | Deprovisioning completes normally despite the missing BCM device | No immediate impact. Known limitation — periodic health checks are a future enhancement |
| Operator restart mid-reconciliation | Controller restarts reconciliation from current CR state | All operations are idempotent: FindFreeHost returns already-assigned host, AssignHost detects existing assignment, BMH creation is idempotent via generateName | No visible impact — reconciliation continues |
| AAP provision/deprovision failure | Handled by existing provisioning lifecycle | Existing retry and failure handling applies unchanged | BareMetalInstance shows `Failed` with AAP error details |
| mTLS certificate expired | All BCM API calls fail with TLS error | Admin replaces certificate Secret — certwatcher detects the new files automatically. No operator restart required | All BCM-backed instances stuck; status shows TLS error |

**Retry timeout consideration:** All BCM API failures (unreachable,
auth expired, server error) retry indefinitely following the existing
operator pattern — no backend today implements a "give up after N" timeout
for API failures. This means a BareMetalInstance can stay stuck in
`Allocating` or `Deleting` indefinitely if BCM remains unreachable.
Adding a bounded timeout with a clear terminal error state (similar to
`OSAC_HOST_READY_TIMEOUT` for BMH readiness) would improve operational
visibility but affects all backends, not just BCM. This should be
considered as a cross-backend improvement tracked separately.

**Idempotency guarantees:**
- `FindFreeHost` is read-only and inherently idempotent.
- `AssignHost` checks existing assignment before writing — re-running with the
  same `bareMetalInstanceID` succeeds without side effects.
- `UnassignHost` handles already-unassigned hosts (null `extra_values`) and
  already-deleted BMH CRs gracefully.
- BMH creation uses a deterministic name (the BCM hostname) — creating an
  already-existing BMH returns a conflict error that the client handles by
  verifying the existing BMH's `consumerRef`.

### RBAC / Tenancy

**Tenant-facing RBAC:** No changes required. The BCM backend operates at the
infrastructure level — Cloud Infrastructure Admins configure it via
Kubernetes Secrets. Tenant isolation is enforced by the existing
fulfillment-service OPA policies and the BareMetalInstance controller's
namespace scoping. BCM is transparent to tenants. [Locked: D7]

**Operator RBAC:** The existing operator has `get`, `list`, `watch`, `update`,
`patch` on `metal3.io/baremetalhosts` and no Secret permissions. The BCM
backend requires one additional permission because it creates and deletes
BMH CRs (unlike existing backends that only update pre-existing resources):

- `metal3.io/baremetalhosts`: add `create` and `delete` verbs to the
  existing RBAC marker.

No Secret permissions are needed — the operator references pre-existing
BMC credential Secrets by name but never reads, creates, or deletes them.
Metal3 reads the Secrets directly using its own permissions.

### Observability and Monitoring

**New Prometheus metrics:**

| Metric | Type | Labels | Description |
|--------|------|--------|-------------|
| `osac_bcm_api_requests_total` | Counter | `method` (`getDevices`, `getDevice`, `updateDevice`), `status` (`success`, `error`) | Total BCM API calls |
| `osac_bcm_api_duration_seconds` | Histogram | `method` | BCM API call latency |
| `osac_bcm_hosts_available` | Gauge | `host_type` | Number of unassigned LiteNodes by host type (updated on each FindFreeHost call) |
| `osac_bcm_bmh_readiness_duration_seconds` | Histogram | — | Time from BMH creation to BMH ready state |

**Kubernetes events:**

| Event | Type | Reason | When |
|-------|------|--------|------|
| BCM host assigned | Normal | `BCMHostAssigned` | After successful AssignHost |
| BCM host released | Normal | `BCMHostReleased` | After successful UnassignHost |
| BCM connection error | Warning | `BCMConnectionError` | When BCM API is unreachable |
| BMH readiness wait | Normal | `BMHReadinessWait` | When waiting for on-demand BMH to become ready |

### Risks and Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| BCM API changes in future versions break the client | Low | High | Pin minimum BCM version (10.25.03+). BCM JSON API has been stable across major versions. Implement version check at startup |
| BMH readiness takes longer than expected (>5 min) | Medium | Medium | Configurable timeout via env var. Clear status messaging so admins can diagnose |
| Full-object replacement causes data loss if BCM schema changes | Low | Medium | GET immediately before PUT (minimize stale window). Log method name, hostname, and status code at debug level — never log full device objects (they may contain BMC credentials in `bmcSettings`) |
| Single-writer assumption violated (multiple operator replicas) | Low | High | Controller-runtime leader election ensures single active instance. Document this as a deployment requirement |
| BCM mTLS certificates expire | Medium | High | certwatcher detects the rotated certificate files automatically — no operator restart required. See Security Considerations |

### Drawbacks

The hybrid architecture (BCM inventory + Metal3 management) adds complexity
in one specific area: the BCM inventory client creates and deletes
BareMetalHost CRs as part of assignment and unassignment. In existing
backends, hosts are pre-existing — the inventory client only marks them
as taken or releases them, never creates or deletes BareMetalHost CRs.
The BCM client owns the full BMH lifecycle, which makes `AssignHost` and
`UnassignHost` more involved and harder to test.

The ordering of operations (BCM write before BMH creation) and idempotency
guarantees prevent state divergence between BCM and Kubernetes — a crash
at any point recovers cleanly on the next reconcile.

This complexity is justified because:
- Pure BCM (Solution A) requires implementing unproven BCM power control and
  building the entire management path from scratch.
- Pure Metal3 sync (Solution B) introduces sync lag and makes BMH CRs the
  source of truth instead of BCM, which doesn't align with the long-term
  vision of inventory backends as the source of truth.
- The hybrid approach uses BCM where it's strong (inventory) and Metal3 where
  it's proven (power management), at the cost of the inventory client also
  managing BMH lifecycle.

## Alternatives (Not Implemented)

### Solution A: Direct BCM Inventory and Management Client

Implement both `inventory.Client` and `management.Client` for BCM. BCM handles
everything: inventory discovery via `getDevices`, assignment via `extra_values`,
and power control via `cmdevice.powerOn/powerOff`.

**Pros:**
- Single integration point — no BMH CRs, no Metal3 dependency.
- BCM is the sole source of truth for both inventory and power state.
- Simpler state model — no BMH lifecycle management, no BMH readiness
  delay, no dual system coordination.

**Cons:**
- BCM power control is unproven in OSAC — no existing test coverage or
  operational experience. The BCM power API works (sends IPMI/Redfish to
  the BMC) but building a full management client (GetPowerState,
  SetPowerState, TriggerRestart, IsRestartComplete) and handling all edge
  cases that Metal3 already handles is significant effort.
- No BMH CRs means no admin visibility via `kubectl get bmh`.
- Higher risk — if BCM power API has issues, no fallback.

**Rejection reason:** The Metal3 power management path is proven and tested
across CaaS and OpenStack flows. Taking on BCM power control adds risk without
clear benefit for the initial implementation. [Locked: D2]

### Solution B: BCM-to-BMH Sync + Metal3 Inventory

A sync controller (or adapted Ansible playbook) periodically reads BCM
inventory and creates/updates BMH CRs. The existing Metal3 inventory backend
then handles FindFreeHost/AssignHost against the synced BMHs.

**Pros:**
- Reuses existing Metal3 inventory + management backends entirely.
- Consistent with the CaaS integration pattern.
- Less new code.

**Cons:**
- Sync lag — hosts added to BCM are not immediately available.
- BMH CRs become the source of truth, not BCM — divergence risk.
- Creates BMH CRs for every LiteNode in BCM regardless of whether they are
  ever assigned. Large deployments (hundreds of nodes) would have many idle
  BMHs, each triggering Metal3 hardware inspection and consuming controller
  resources.
- Sync controller is additional operational complexity.
- Does not validate the pluggable inventory interface with a new backend type.

**Rejection reason:** BCM should be the inventory source of truth, queried
on-demand rather than synced. The hybrid approach preserves this while reusing
Metal3 for management. [Locked: D1]

### Solution C: PhysicalNode Instead of LiteNode

Use BCM PhysicalNodes (where BCM manages the full lifecycle including OS)
instead of LiteNodes (where OSAC manages the OS). Customers with existing
BCM-managed data centers would not need to convert their nodes.

**Pros:**
- No Day-0 node conversion needed — customers use existing PhysicalNodes
  as-is.
- BCM handles OS provisioning, monitoring, and power control natively —
  less for OSAC to build.
- Could enable Solution A (pure BCM) architecture — no BMH CRs, no
  Metal3 dependency, simpler state model.
- Full BCM monitoring (CMDaemon agent, GPU metrics via DCGM) remains
  available.

**Cons:**
- **OS conflict (fatal gap).** BCM re-provisions PhysicalNodes on every
  reboot by design — syncing the assigned software image to local disk.
  Any OSAC-provisioned configuration (SSH keys, network config, tenant
  workloads) is wiped. There is no supported BCM mechanism to prevent
  this per-node. Image locking is global (all nodes), and category
  separation does not prevent re-provisioning on reboot. A normal
  tenant operation (restart, power cycle) or any hardware reset would
  destroy the tenant's environment. The only way to stop BCM from
  managing the OS is to convert to LiteNode.
- **Breaks the pluggable architecture.** The inventory/management
  separation (OSAC-1032) allows mixing any inventory backend with any
  management backend. PhysicalNode forces both to be BCM — BCM's OS
  provisioning is tied to its boot process, so inventory, OS management,
  and power control are inseparable. This requires a monolithic
  BCM-does-everything approach (Solution A) instead of the pluggable
  interface the operator was designed for.
- **CaaS incompatibility forces dual node-type support.** CaaS provisions
  OpenShift clusters, which require a specific immutable OS (RHCOS) that
  BCM cannot provision — BCM supports Rocky, RHEL, Ubuntu, and SLES
  only. CaaS nodes must therefore remain LiteNodes. Since CaaS is
  planned to consume BCM nodes through the BMaaS API, BMaaS would need
  to support both PhysicalNode (for BMaaS tenants) and LiteNode (for
  CaaS requests). This dual node-type support adds significant
  complexity to the first iteration.

**Rejection reason:** BCM re-provisions PhysicalNodes on every reboot,
wiping tenant workloads. There is no per-node override. This also forces
a monolithic BCM-only approach that bypasses the pluggable
inventory/management architecture. CaaS adds further complexity —
its nodes require an OS that BCM cannot provision, forcing dual
node-type support. If BCM adds a per-node provisioning hold flag in a
future version, this alternative should be reconsidered. [Locked: D4]

## Open Questions

### 1. BCM Simulator Scope for E2E Testing

The BCM simulator needs to fake enough of the JSON API for E2E tests. Minimum
surface:

- `cmdevice.getDevices` — return a configurable set of LiteNodes
- `cmdevice.getDevice` — return a single device by hostname
- `cmdevice.updateDevice` — accept and persist `extra_values` changes
- mTLS authentication (or a test-mode bypass)

Should the simulator also support `addLiteNode` and `removeDevice`, or
should the simulator be constructed with pre-configured LiteNodes at startup
(matching the scenario-based mock pattern used in fulfillment-service)?

**Owner:** To be determined
**Impact:** Affects E2E test ergonomics and CI setup complexity. Can be
resolved during implementation.

### 2. Operator-Managed BMC Secrets as Future Alternative

The current design requires admins to pre-create BMC credential Secrets
during Day-0 and store the Secret name in
`extra_values.osac_bmc_credentials_secret`. This keeps the operator simple
(no Secret RBAC needed) but adds Day-0 setup work.

An alternative is to have the operator create BMC Secrets programmatically
by reading `bmcSettings` (userName, password) from the BCM device object.
This would reduce admin work but requires granting the operator `get`,
`create`, and `delete` permissions on Secrets. Since the operator's RBAC
is cluster-scoped, Secret permissions would need a namespace-scoped Role
+ RoleBinding (limited to the Metal3 namespace) to avoid overly broad
access. Even namespace-scoped, the operator would gain read access to all
Secrets in that namespace, including unrelated ones like `pull-secret`.

**Owner:** To be determined
**Impact:** Tradeoff between admin setup burden and operator permissions
scope. The current approach (admin pre-creates) is more secure. Can be
revisited if the Day-0 setup proves too burdensome.


## Test Plan

### Unit Tests

**BCM HTTP client (`internal/inventory/bcm_client_test.go`):**
- Successful `getDevices` call parses device list correctly
- Successful `getDevice` returns device object
- `getDevice` for nonexistent host returns nil (not error)
- `updateDevice` with full device object succeeds
- `updateDevice` with partial object returns validation error
- mTLS client initializes correctly with valid certificate and key
- On TLS error, client re-reads Secret and retries with new certificate
- Connection failure returns `ErrBCMConnectionFailed`
- TLS handshake failure returns `ErrBCMTLSFailed`
- Authentication failure returns `ErrBCMAuthFailed`
- Server error returns `ErrBCMServerError`
- Malformed JSON response returns parse error

**BCM inventory client (`internal/inventory/bcm_test.go`):**

FindFreeHost:
- Filters by `childType == "LiteNode"` (hardcoded)
- Skips hosts with `extra_values: null` with warning (missing required
  configuration)
- Skips hosts without `resource_class` in `extra_values` with warning
- Excludes hosts with `extra_values.osac_instance_id` set (already assigned)
- Matches `extra_values.resource_class` against
  `matchExpressions["hostType"]`
- Skips hosts with missing or malformed MAC with warning
- Returns nil when no matching hosts available

AssignHost:
- Writes `osac_instance_id` to `extra_values` using full-object
  replacement (GET-modify-PUT)
- Returns nil when host already assigned to different instance
- Succeeds when host already assigned to same instance (idempotent)
- Verify-after-write detects race condition (another writer overwrote)
- Creates BMH CR with correct fields: `metadata.name` = hostname,
  `managed-by` label, `spec.bmc.address`, `spec.bmc.credentialsName`,
  `spec.bootMACAddress`, `spec.online = false`, `spec.consumerRef`
- Reads `spec.bmc.credentialsName` from
  `extra_values.osac_bmc_credentials_secret`
- Returns error when `osac_bmc_credentials_secret` is missing
- BMC address Priority 1: uses `extra_values.osac_bmc_address` directly
- BMC address Priority 2: discovers from `NetworkBmcInterface` + Redfish,
  validates URL, caches in `extra_values.osac_bmc_address`
- BMC address Priority 3: returns error when no BMC info available

UnassignHost:
- Removes only `osac_instance_id` from `extra_values` (preserves
  other keys)
- Deletes BMH CR
- Does NOT delete BMC credentials Secret
- Handles already-unassigned host (null `extra_values`)
- Handles already-deleted BMH CR

**ErrHostNotReady (`internal/management/metal3_test.go`):**
- `GetPowerState` returns `ErrHostNotReady` for BMH in registering state
- `GetPowerState` returns `ErrHostNotReady` for BMH in inspecting state
- `GetPowerState` returns normal power state for BMH in available state

**Controller ErrHostNotReady handling
(`internal/controller/baremetalinstance_controller_test.go`):**
- Controller sets `Available=False` condition with reason `HostNotReady` when
  management returns `ErrHostNotReady`
- Controller requeues with `ManagementRecheckIntervalDuration`
- Controller proceeds normally once BMH becomes ready
- Controller transitions to `Failed` after `OSAC_HOST_READY_TIMEOUT` expires
- On timeout, controller calls UnassignHost — clears `osac_instance_id` from
  BCM `extra_values` and deletes BMH CR
- After timeout cleanup, host is available for re-assignment via FindFreeHost

### Integration Tests

**BCM inventory + Metal3 management integration
(`internal/controller/baremetalinstance_bcm_integration_test.go`):**

Using envtest with a mock BCM HTTP server (httptest.Server):

- Full allocation flow: FindFreeHost → AssignHost → BMH created → management
  reconciliation
- Deallocation flow: UnassignHost → BMH deleted → extra_values cleared
- BMH readiness delay: AssignHost creates BMH, management returns
  ErrHostNotReady, simulated BMH becomes ready, management proceeds
- BMH readiness timeout: BMH never becomes ready → timeout → UnassignHost
  releases host → controller transitions to Failed
- Assignment contention: Two concurrent reconciles for same host type — one
  succeeds, one retries with different host
- BCM unreachable during allocation: connection refused → controller
  requeues with error status
- BCM error response during allocation: BCM returns error message →
  controller requeues with descriptive status
- BCM unreachable during deallocation: connection refused → controller
  retries → BCM comes back → unassign completes
- BCM error response during deallocation: BCM returns error → controller
  retries until successful
- Missing `osac_bmc_credentials_secret` during allocation: AssignHost
  fails with actionable error message
- Deallocation with missing BCM device: BCM returns null → unassign
  treats as already cleaned up → completes normally

### E2E Tests

**BCM simulator-based E2E (osac-test-infra):**

Following the PR #224 pattern — same test suite in `tests/bmaas/`, different
setup script that deploys the BCM simulator instead of Metal3-only
infrastructure:

- Create BareMetalInstance with BCM backend → instance reaches Ready state
- Delete BareMetalInstance → host released back to BCM pool, can be
  re-assigned
- Create BareMetalInstance with no matching host type → instance stays in
  Allocating with clear error message
- Create BareMetalInstance when BCM is unavailable → instance shows BCM
  connection error
- Multiple BareMetalInstances from same pool → each gets a different host
- Host preparation timeout → instance transitions to Failed, host released
  back to BCM pool and available for new assignments
- During normal host preparation, BareMetalInstance status shows readiness
  message before BMH becomes ready
- After assignment, BCM simulator's `extra_values` contains
  `osac_instance_id` and no tenant-identifying data (name, namespace, org)
- After deletion, BCM simulator's `extra_values` no longer contains
  `osac_instance_id` — host is free for re-assignment

## Graduation Criteria

Graduation criteria will be defined when targeting a release. Expected stages:
Dev Preview -> Tech Preview -> GA based on production deployment feedback.

**Dev Preview exit criteria:**
- BCM inventory backend passes all unit and integration tests
- E2E tests pass with BCM simulator in CI
- Operator configuration guide published documenting `inventory.yaml` setup
  with `type: bcm`, mTLS credential management, and Helm values
- Node registration documentation references existing CaaS setup scripts
  (`bcm_add_lite_nodes.py`) for the Day-0 LiteNode registration prerequisite
- Troubleshooting guide in `osac-docs/architecture/bcm-backend/` covering
  common failure scenarios and manual recovery procedures (following the
  aap-provisioning docs pattern)
- At least one successful deployment against a real BCM environment

## Upgrade / Downgrade Strategy

This is a new inventory backend with no upgrade impact on existing deployments.
Deployments using OpenStack or Metal3 inventory backends are unaffected.

**Switching to BCM backend:** Admin changes `inventory.yaml` to `type: bcm`,
completes BCM-side prerequisites (see Day-0 workflow), and restarts the
operator. Existing BareMetalInstances from the previous backend are not
affected.

**Switching away from BCM backend:** Admin changes `inventory.yaml` back
and restarts. On-demand BMH CRs remain until their BareMetalInstances are
deleted. Stale `osac_instance_id` values may remain in BCM `extra_values`
but have no operational impact while the BCM backend is not active.

## Version Skew Strategy

The BCM inventory backend changes are concentrated in the
bare-metal-fulfillment-operator. Cross-component impact is minimal:

- **bare-metal-fulfillment-operator:** All code changes happen here — new BCM
  inventory client, ErrHostNotReady in the Metal3 management client, RBAC
  marker updates, Helm chart values. An older BMFO version without these
  changes cannot use the BCM backend.
- **osac-installer:** Values and schema updates needed to expose the new
  `bcmCerts` Helm value from the BMFO subchart.
- **fulfillment-service:** No changes — the BareMetalInstance API is unchanged.
- **osac-operator:** No changes — no new CRDs or shared-package changes.
- **Metal3/BMO:** No changes — the BCM backend creates standard `v1alpha1`
  BMH CRs.
- **BCM:** Minimum version 10.25.03+ enforced at startup via a version check
  against `/rest/v1/version`.

## Support Procedures

**Detecting BCM backend issues:**
- **Metrics:** `osac_bcm_api_requests_total{status="error"}` increasing
  (connectivity or API issues), `osac_bcm_hosts_available` dropping to
  zero (pool exhaustion), `osac_bcm_bmh_readiness_duration_seconds`
  increasing (Metal3 or BMC infrastructure problems).
- **Events:** `BCMConnectionError` warning events (BCM unreachable),
  `BMHReadinessWait` normal events (waiting for on-demand BMH).
- **Status:** BareMetalInstances stuck in `Allocating` (BCM issues),
  stuck in `Deleting` (BCM unreachable during cleanup), or in `Failed`
  with "Host preparation timed out" (BMH never became ready).
- **Log:** Operator logs at `error` level include the BCM API method name, target hostname, and error message. Full device objects are never logged because they may contain BMC credentials (`bmcSettings`). Warning logs identify hosts skipped due to
  missing `extra_values` configuration.

**Disabling the BCM backend:**
- Change `inventory.yaml` to `type: metal3` and restart the operator.
- Existing BareMetalInstances in `Ready` state continue to function
  (their BMH CRs remain).
- On-demand BMH CRs created by the BCM backend remain on the cluster.
  Do not delete them if you plan to re-enable the BCM backend — the
  recovery procedure depends on them being present.
- If permanently switching away, delete orphaned BMH CRs after all
  associated BareMetalInstances are deprovisioned.

**Recovery:**
- Restore `inventory.yaml` to `type: bcm` and restart.
- The operator reconciles existing BareMetalInstances. BCM `extra_values`
  and BMH CRs both persist across operator restarts.
- If BMH CRs were deleted during the outage, the affected
  BareMetalInstances will need manual cleanup — delete them and let
  tenants create new ones.

See the troubleshooting guide (`osac-docs/architecture/bcm-backend/`)
for manual recovery procedures and detailed failure investigation steps.

## Infrastructure Needed

- **BCM simulator:** A small Python HTTP server that fakes BCM's JSON API for
  E2E testing in CI. Deployed as a container in the kind cluster alongside the
  operator. [Locked: D13]
- **CI integration:** The E2E test pipeline needs a BCM simulator deployment
  step, following the PR #224 pattern for backend-specific test setup.
