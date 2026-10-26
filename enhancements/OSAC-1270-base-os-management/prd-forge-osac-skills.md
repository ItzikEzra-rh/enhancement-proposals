---
prd_id: OSAC-1270
title: Base OS Management for Bare Metal Instances
jira_key: OSAC-1270
status: Draft
---
# Base OS Management for Bare Metal Instances

| Field       | Value                                                        |
|-------------|--------------------------------------------------------------|
| Author(s)   | Adrien Gentil                                                |
| Jira        | [OSAC-1270](https://redhat.atlassian.net/browse/OSAC-1270)   |
| Service     | BMaaS |
| Date        | 2026-07-26                                                   |

## Problem Statement

The OS image applied to a bare metal instance is fixed by the BaremetalInstanceTemplate and cannot be changed by tenants. There is no lifecycle management for the OS and tenants have no visibility into the images available to them. Cloud Provider Admins have no structured surface to publish and version OS images independently of the full template. Tenant Admins have no way to publish organization-specific OS images for their users. If unaddressed, bare metal provisioning remains inflexible — tenants who need different base operating systems must request a new template for each OS variant.

## In Scope

- OS images exposed as a queryable resource in the fulfillment-service API, reusing the DiskImage resource defined in OSAC-2540
- Tenants can specify a DiskImage when creating a BaremetalInstance — either explicitly or defaulted from the BaremetalInstanceCatalogItem; creation is rejected when neither provides a reference
- Tenant Admins can publish organization-specific DiskImages visible only to their tenant's users
- Cloud Provider Admins can publish and manage global DiskImages for bare metal provisioning
- DiskImage deletion blocked when referenced by active BaremetalInstances or BaremetalInstanceCatalogItems
- Validation at creation time: non-existent, deleted, or obsolete images rejected with descriptive error; deprecated images allowed with warning
- UI support for DiskImage selection in the bare metal provisioning flow
- E2E test coverage for DiskImage selection at bare metal provision time
- Tenant isolation: tenant-scoped images visible only within the owning tenant; global images visible to all tenants

## Out of Scope

- Custom OS image upload by tenants — images are curated and published by Cloud Provider Admins or Tenant Admins only
- In-place OS upgrade (package-level) — OS image selection applies at provision time only
- OS configuration management beyond initial boot (e.g., configuration drift detection)
- DiskImage resource definition, metadata schema, and lifecycle management — fully specified in OSAC-2540
- Image scanning or CVE detection
- Private registry authentication (pull credential management)

## User Stories

### Cloud Provider Admin

- As a Cloud Provider Admin, I want to register global DiskImages for bare metal provisioning so that all tenants can discover and select from a curated set of OS images.
- As a Cloud Provider Admin, I want to deprecate or obsolete a bare metal OS image so that tenants are warned or blocked from provisioning new instances with unsupported images.
- As a Cloud Provider Admin, I want DiskImage deletion blocked when referenced by any BaremetalInstance or BaremetalInstanceCatalogItem so that I do not break running workloads or catalog offerings.

### Cloud Infrastructure Admin

Not affected by this feature.

### Tenant Admin

- As a Tenant Admin, I want to publish tenant-scoped DiskImages for bare metal provisioning so that my users can select from our organization's approved OS images alongside the global catalog.

### Tenant User

- As a Tenant User, I want to see the list of OS images available to me so that I can select the appropriate base OS when provisioning a bare metal instance.
- As a Tenant User, I want to select a DiskImage when creating a BaremetalInstance so that the instance is provisioned with my chosen OS.

## Assumptions

- The DiskImage resource (OSAC-2540) is service-neutral and supports both VMaaS and BMaaS. This feature extends its use to BaremetalInstance.
- OSAC does not support in-place upgrades, so backward compatibility for existing BaremetalInstances using the current fixed-image template pattern is not a concern.

## Dependencies

- **OSAC-2540 (DiskImage resource):** Defines the DiskImage API resource, metadata schema, two-tier visibility (global + tenant-scoped), lifecycle management (active, deprecated, obsolete, reactivation), and image source format. Must land before or alongside this feature.
- **OSAC-1118 (Baremetal OSAC API):** Provides the BaremetalInstance lifecycle foundation. Closed — prerequisite is met.

## Acceptance Criteria

- [ ] OS images are exposed as a queryable resource in the fulfillment-service public API
- [ ] Tenants can specify an OS image at BaremetalInstance creation time
- [ ] Tenant Admins can publish organization-specific OS images visible only to their users
- [ ] Cloud Provider Admins can publish and manage global OS images
- [ ] E2E tests cover OS image selection at provision time
