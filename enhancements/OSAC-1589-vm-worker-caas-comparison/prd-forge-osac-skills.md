# PRD: VM Worker Node Support for CaaS Clusters

| Field       | Value                                      |
|-------------|--------------------------------------------|
| Jira        | OSAC-1589                                  |
| Type        | Feature                                    |
| Service     | CaaS                                       |
| Label       | customer:moc                               |
| Status      | Draft                                      |

## Problem Statement

CaaS clusters currently require bare-metal servers for all worker nodes. This creates two problems: (1) organizations without dedicated bare-metal hardware cannot validate or use CaaS at all, and (2) environments that do have bare metal are forced to consume expensive physical resources even for dev/test or small workloads where VM-based workers would suffice. Adding VM worker node support removes the bare-metal-only constraint, enabling faster provisioning, lower cost for lightweight workloads, and broader accessibility for validation and development.

## In Scope

- Allow tenants to create CaaS clusters with VM-based worker nodes provisioned through VMaaS (KubeVirt ComputeInstances)
- Support mixed-mode clusters: bare-metal control plane with VM worker nodes
- Expose VM worker node configuration in the CaaS provisioning API (ClusterOrder spec)
- Integrate VM worker node lifecycle with existing CaaS cluster lifecycle (scale up, scale down, delete)
- Surface VM worker node status and health in cluster details (API and UI)
- Validate VM worker nodes meet minimum resource requirements for OpenShift worker role
- Support VM worker nodes in the OSAC UI cluster creation and management flows

## Out of Scope

- **VM-based control plane nodes** -- control plane remains bare-metal or HCP-managed; VM control plane introduces stability and certification concerns that require separate evaluation
- **Live migration of worker node type** (bare-metal to VM or vice versa) -- converting running workers between types is a complex operation better addressed as a follow-on feature
- **GPU passthrough to VM workers** -- GPU scheduling for VMs requires device plugin and IOMMU configuration not yet available in the VMaaS layer
- **Custom VM images for workers** -- initial implementation uses the standard RHCOS image; custom image support can be added incrementally
- **Nested virtualization** -- running VMs inside VM workers is not a supported topology

## User Stories

### Tenant Admin

- As a Tenant Admin, I want to create a CaaS cluster with VM worker nodes so that my team can provision OpenShift clusters without requiring dedicated bare-metal hardware.
- As a Tenant Admin, I want to specify the number and size (CPU, memory, storage) of VM worker nodes when creating a cluster so that I can right-size the cluster for my workload.
- As a Tenant Admin, I want to scale VM worker nodes up or down on an existing cluster so that I can adjust capacity without reprovisioning.
- As a Tenant Admin, I want to see the type (VM or bare-metal) and status of each worker node in the cluster details so that I can monitor my infrastructure.

### Tenant User

- As a Tenant User, I want to request a CaaS cluster with VM workers through the self-service UI so that I can quickly get a development or test environment.
- As a Tenant User, I want the cluster I receive with VM workers to behave identically to a bare-metal cluster from a Kubernetes API perspective so that my workloads run without modification.

### Cloud Infrastructure Admin

- As a Cloud Infrastructure Admin, I want to define which compute flavors are eligible for CaaS VM workers so that I can control resource allocation and prevent undersized VMs from being used as OpenShift nodes.
- As a Cloud Infrastructure Admin, I want VM worker nodes to respect existing tenant quotas and network policies so that multi-tenancy guarantees are preserved.

### Cloud Provider Admin

- As a Cloud Provider Admin, I want to enable or disable VM worker node support per environment so that I can control rollout and limit the feature to validated configurations.

## Assumptions

- The VMaaS (KubeVirt) layer is operational and can provision ComputeInstances that meet OpenShift worker node requirements.
- Hosted Control Planes (HCP) supports adding VM-based workers to a hosted cluster through the NodePool API.
- Network connectivity between the HCP control plane and VM worker nodes can be established through existing VirtualNetwork and Subnet resources.
- Existing tenant quota enforcement applies to VM resources (vCPU, memory) consumed by worker nodes.

## Dependencies

- **VMaaS / KubeVirt**: ComputeInstance provisioning must support the resource sizes and network configurations required for OpenShift worker nodes.
- **HCP NodePool API**: Must support a KubeVirt provider type for worker node pools.
- **Networking**: VirtualNetwork and Subnet resources must support connectivity between hosted control plane components and VM workers.
- **OSAC Operator**: ClusterOrder controller must be extended to manage VM-backed NodePools.
- **Fulfillment Service API**: ClusterOrder proto must be extended with VM worker node configuration fields.

## Acceptance Criteria

- [ ] A tenant can create a CaaS cluster specifying VM worker nodes via the API
- [ ] A tenant can create a CaaS cluster specifying VM worker nodes via the UI
- [ ] VM worker nodes are provisioned as KubeVirt ComputeInstances and join the hosted cluster as ready nodes
- [ ] Cluster details (API and UI) display worker node type (VM or bare-metal) and individual node status
- [ ] VM worker node count can be scaled up and down on a running cluster
- [ ] Deleting a CaaS cluster with VM workers cleans up all associated ComputeInstances
- [ ] VM worker nodes respect tenant quotas -- provisioning fails gracefully if quota is exceeded
- [ ] VM worker nodes are reachable on the cluster's VirtualNetwork and Subnets
- [ ] E2E test covers the full lifecycle: create cluster with VM workers, verify nodes ready, scale, delete
- [ ] The feature can be validated without dedicated bare-metal hardware (addresses the original MOC requirement)
