# Epic 1: Tenant-visible volume inventory read API

- **T-Shirt Size:** L

## Summary

This epic gives tenant users, tenant admins, and Cloud Provider Admins a supported read-only public view of existing standalone volumes. It delivers the public gRPC and REST surface, the tenant-meaningful projection, standard visibility and list behavior, local and deployed validation paths, and the documentation needed to consume the API.

## Acceptance Criteria

- [ ] A caller authorized for public volume reads can retrieve and list existing standalone volumes through the public gRPC and REST surfaces.
- [ ] The public representation exposes tenant-meaningful identity, specification, and state fields while excluding internal routing and vendor fields.
- [ ] List and Get preserve tenant/project visibility, non-archived inventory states, archived-record exclusion, public filtering, pagination, and the approved identifier behavior.
- [ ] Unit, fulfillment component-integration, and standalone QE coverage identify the execution boundary and any unavailable environment instead of claiming unexecuted coverage.
- [ ] The public REST/gRPC surface, generic CLI behavior, errors, states, filtering, visibility, and API specification requirements have documented inputs and owners.

## Design Reference

Feature: OSAC-4542 — Volume Get/List Public API
PRD Requirements: FR-1, FR-2, FR-3, FR-4, FR-5, FR-6, FR-7, FR-8
Design sections: Summary, Proposal, Workflow Description, API Extensions, Implementation Details/Notes/Constraints, Failure Handling and Recovery, RBAC / Tenancy, Test Plan

