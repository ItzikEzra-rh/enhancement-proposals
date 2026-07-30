# Product Requirements Document

**Document Version**: 1.0
**Date**: 2026-07-30
**Status**: Draft
**Ticket**: OSAC-1270

---

## 1. Executive Summary

This feature enables tenants to select a base OS image when provisioning bare metal instances, replacing the current fixed-image behavior. Cloud Provider Admins and Tenant Admins gain the ability to publish and manage curated OS image catalogs available for provisioning.

---

## 2. Problem Statement

### 2.1 Current State
The OS image applied to a bare metal instance is fixed by the BaremetalInstanceTemplate and cannot be changed by tenants. There is no lifecycle management for OS images, no visibility into available images, and no structured surface for admins to publish or version OS images independently of the full template.

### 2.2 Desired State
Tenants can browse available OS images and select one at provisioning time. Cloud Provider Admins can publish, version, deprecate, and remove global OS images. Tenant Admins can publish organization-specific images visible only to their users.

### 2.3 Business Impact
Removes a provisioning bottleneck where tenants must request template changes to get a different OS. Enables Cloud Provider Admins to manage OS image lifecycle independently, reducing coordination overhead and improving time-to-provision for tenants.

---

## 3. Goals & Objectives

### Primary Goals
- [ ] Expose OS images as a queryable, selectable resource during bare metal provisioning
- [ ] Enable Cloud Provider Admins to publish and manage a global OS image catalog
- [ ] Enable Tenant Admins to publish organization-scoped OS images for their users

### Success Metrics
| Metric | Current | Target | Measurement Method |
|--------|---------|--------|-------------------|
| OS image selection available at provision time | No | Yes | API and UI support OS image parameter |
| Admin-managed OS image catalog exists | No | Yes | CRUD operations available for OS images |

---

## 4. User Personas

### Persona 1: Tenant User
- **Role**: Developer or operator provisioning bare metal instances
- **Goals**: Select the appropriate base OS when provisioning an instance
- **Pain Points**: Currently has no choice of OS; must accept whatever the template provides
- **Usage Context**: During bare metal instance creation workflows

### Persona 2: Tenant Admin
- **Role**: Organization administrator managing tenant-level resources
- **Goals**: Publish custom OS images available only to users within their organization
- **Pain Points**: Cannot provide organization-specific OS images to users
- **Usage Context**: Managing tenant resource catalogs and provisioning options

### Persona 3: Cloud Provider Admin
- **Role**: Platform administrator managing global infrastructure resources
- **Goals**: Publish, version, deprecate, and remove OS images available for bare metal provisioning
- **Pain Points**: No structured way to manage OS images independently of instance templates
- **Usage Context**: OS lifecycle management, catalog curation, image deprecation

---

## 5. Requirements

### 5.1 Functional Requirements

| ID | Requirement | Priority | Acceptance Criteria |
|----|-------------|----------|---------------------|
| FR-001 | OS images are exposed as a queryable resource in the public API | MVP | API endpoint returns list of available OS images with name, version, and metadata |
| FR-002 | Tenants can specify an OS image when creating a bare metal instance | MVP | Create request accepts an OS image reference; instance provisions with the selected image |
| FR-003 | Cloud Provider Admins can publish new OS images | MVP | Admin can create an OS image resource with name, version, and source reference |
| FR-004 | Cloud Provider Admins can deprecate or remove OS images | MVP | Deprecated images are excluded from default listings; removed images cannot be used for new provisioning |
| FR-005 | Tenant Admins can publish organization-specific OS images | MVP | Tenant-scoped images are visible only to users within that tenant |
| FR-006 | OS image listing respects tenant visibility rules | MVP | Tenants see global images plus their own tenant-scoped images; they do not see other tenants' images |

### 5.2 Non-Functional Requirements

| ID | Requirement | Category | Target |
|----|-------------|----------|--------|
| NFR-001 | OS image listing responds within acceptable latency | Performance | Comparable to other resource list endpoints |
| NFR-002 | Tenant isolation enforced for organization-scoped images | Security | No cross-tenant image visibility |

---

## 6. User Stories

**US-001**: As a Tenant User, I want to see the list of OS images available to me so that I can select the appropriate base OS when provisioning a bare metal instance.
- **Acceptance Criteria**:
  - Given a tenant user, when they query available OS images, then they see global images and their tenant-scoped images
  - Given a tenant user, when they create a bare metal instance, then they can specify an OS image from the available list

**US-002**: As a Tenant Admin, I want to publish my own base image so that my tenant users can provision instances with organization-specific OS images.
- **Acceptance Criteria**:
  - Given a tenant admin, when they create an OS image, then it is visible only to users within their tenant
  - Given a tenant admin, when they remove an OS image, then it is no longer available for new provisioning by their users

**US-003**: As a Cloud Provider Admin, I want to define and publish OS images available for bare metal provisioning so that tenants can select from a curated set.
- **Acceptance Criteria**:
  - Given a Cloud Provider Admin, when they publish an OS image, then it is visible to all tenants
  - Given a Cloud Provider Admin, when they deprecate an OS image, then it is excluded from default listings but existing instances are unaffected

**US-004**: As a Cloud Provider Admin, I want to deprecate or remove an OS image so that tenants cannot provision new instances with unsupported images.
- **Acceptance Criteria**:
  - Given a deprecated image, when a tenant lists images, then the image is hidden by default but retrievable with an explicit filter
  - Given a removed image, when a tenant attempts to provision with it, then the request is rejected

---

## 7. Scope

### In Scope
- OS image as a new queryable resource in the public API
- OS image selection at bare metal instance creation time
- Cloud Provider Admin CRUD operations for global OS images
- Tenant Admin CRUD operations for organization-scoped OS images
- Deprecation and removal lifecycle for OS images
- Tenant visibility rules (global + own tenant images)

### Out of Scope
- Custom OS image upload by tenants — images are curated and published by Cloud Provider Admins or Tenant Admins only
- In-place OS upgrade (package-level) — this feature covers image selection at provision time only
- OS configuration management beyond initial boot (e.g. configuration drift detection)
- Unification with VMaaS image management (noted as related work in OSAC-2540)

---

## 8. Assumptions & Constraints

### Assumptions
- The baremetal provisioning infrastructure already supports applying different OS images at provision time (i.e., the underlying tooling accepts an image reference)
- OS images are referenced by metadata (name, version, source reference) rather than uploaded as binary artifacts

### Constraints
- Must depend on the existing Baremetal OSAC API (OSAC-1118, closed)
- Tenant isolation must be enforced at the API level

### Dependencies
- OSAC-1118: Baremetal OSAC API (closed — assumed available)
- OSAC-2540: DiskImage resource for disk image metadata management (related, in progress)

---

## 9. Risks & Mitigations

| Risk | Context | Likelihood | Impact | Mitigation |
|------|---------|------------|--------|------------|
| OS image source reference becomes stale or unreachable after publishing | Cloud Provider Admin publishes an image pointing to an external source that is later moved or deleted | Medium | High | Validate image source accessibility at publish time; surface warnings on periodic health checks |
| Tenant-scoped and global images have naming collisions causing user confusion | Tenant Admin publishes an image with the same name as a global image | Medium | Medium | Enforce unique naming within scope or clearly differentiate global vs. tenant images in listings |
| Deprecation of a widely-used image disrupts tenant provisioning workflows | Cloud Provider Admin deprecates an image still in active use by multiple tenants | Low | High | Require a deprecation notice period; alert tenants using the image before removal |

---

## 10. Timeline & Milestones

| Phase | Milestone | Target Date | Dependencies |
|-------|-----------|-------------|--------------|
| Planning: PRD | PRD approved | TBD | Stakeholder review |
| Planning: Spec | Technical spec approved | TBD | PRD approval |
| Implementation | PRs merged | TBD | Spec approval |
| Testing | QA sign-off | TBD | Implementation complete |
