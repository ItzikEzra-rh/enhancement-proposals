# OSAC-2117: Pure Storage FlashBlade — Design Comparison Analysis

## Overview

Three design generation approaches evaluated against the OSAC design rubric (4 criteria, /8, pass >= 5 with no zeros).

| Approach | Score | Verdict |
|----------|-------|---------|
| Original (Danni Shi, PR #171) | 8/8 | PASS |
| Forge + OSAC skills | 6/8 | PASS |
| Forge defaults | 4/8 | FAIL |

---

## Deterministic Checks

| Check | Original | Forge+OSAC | Forge defaults |
|-------|:--------:|:----------:|:--------------:|
| Structure (15 sections) | PASS | FAIL (missing sections) | FAIL (0/15) |
| Frontmatter | FAIL (missing delimiters) | FAIL (missing tracking-link, prd) | FAIL (missing all 5 fields) |
| Proto schemas | FAIL (N/A — no new API resources) | FAIL (N/A — no new API resources) | FAIL (no proto) |
| Tenant isolation | PASS (prose + label strings) | PASS (annotations) | PASS (prose) |
| Length | PASS (641 lines) | PASS | FAIL (short) |
| Placeholders | PASS | PASS | PASS |
| **Pass rate** | **4/6** | **3/6** | **2/6** |

Note: Proto check FAIL is expected for all three — this feature adds an Ansible role, not new API resources. No proto schemas are architecturally appropriate here.

---

## Rubric Scores

| Criterion | Original | Forge+OSAC | Forge defaults |
|-----------|:--------:|:----------:|:--------------:|
| Architecture | 2/2 | 1/2 | 1/2 |
| Feasibility | 2/2 | 2/2 | 1/2 |
| Scope | 2/2 | 1/2 | 1/2 |
| Testability | 2/2 | 2/2 | 1/2 |
| **Total** | **8/8** | **6/8** | **4/8** |
| **Verdict** | **PASS** | **PASS** | **FAIL** |

---

## Per-Criterion Analysis

### Architecture (Original 2, OSAC 1, Defaults 1)

**Original (2/2):** Fully leverages OSAC's storage provider dispatch system. Uses the established four-action interface from VAST. Three-tier credential model (array-admin, Realm-scoped, PX-CSI token) with blast-radius analysis. Explicitly confirms no osac-operator or fulfillment-service changes needed. Terminology defined upfront and used consistently.

**Forge+OSAC (1/2):** Core patterns correct — recognizes provider-pluggable architecture and AAP role structure. Lost a point because the Observability section proposes fulfillment-service metrics but never lists fulfillment-service as an affected component — a cross-repo dependency gap. The design says "no API changes" in Non-Goals but then implies a code change elsewhere.

**Forge defaults (1/2):** Sound provider-pluggable approach recognized from the Jira description. But Realm pool persistence model unspecified (database? ConfigMap? CRD?), cross-repo impacts not enumerated, and OSAC tenant isolation annotations not discussed for downstream resources (StorageClasses, CSI Secrets).

### Feasibility (Original 2, OSAC 2, Defaults 1)

**Original (2/2):** Exact file structures, variable names, YAML manifests, Secret formats, ConfigMap schemas, and default values specified. Six failure scenarios with rollback behavior and recovery procedures. Three open questions with impact analysis and owners assigned. Drawbacks section genuinely engages trade-offs.

**Forge+OSAC (2/2):** Specific action tables, complete lifecycle description, concrete failure handling matrix. VAST comparison table is a differentiator. Realm pool mechanism described with annotation-based state tracking.

**Forge defaults (1/2):** Good error handling table (7 failure modes with detection/response/recovery). But the Realm pool — the hardest implementation problem — gets the least detail. No data structures, no state machine, no concurrency model. Risks framed as Open Questions instead of risks with mitigations. No Drawbacks or Alternatives sections.

### Scope (Original 2, OSAC 1, Defaults 1)

**Original (2/2):** Well-bounded single Ansible role addition. PRD referenced in frontmatter. Four real alternatives evaluated. All four OSAC personas addressed. Cross-cutting dimensions covered: Services, Tenant Onboarding, Provisioning, Storage, Installation, E2E Testing. Only gap: Documentation dimension not explicitly addressed.

**Forge+OSAC (1/2):** Strong non-goals and alternatives (3 rejected approaches). But missing PRD reference in frontmatter. Installation, Documentation, and UI dimensions from osac-dimensions.md not addressed. Some goals are implementation tasks ("Implement pure_storage role") rather than user-visible outcomes.

**Forge defaults (1/2):** Clear focus, avoids scope creep. But no YAML frontmatter, no PRD reference, no Goals/Non-Goals section. Services, Installation, UI, Documentation, Networking, and Milestone dimensions all silent. Persona coverage implicit rather than explicit.

### Testability (Original 2, OSAC 2, Defaults 1)

**Original (2/2):** Concrete scenarios at all three levels. Molecule/integration tests for each lifecycle action. Kind-based dispatch verification. E2E with hardware skip flag. Staged graduation criteria (Dev Preview → Tech Preview → GA) with measurable conditions.

**Forge+OSAC (2/2):** Concrete scenarios at all levels including pool exhaustion and concurrent checkout. Measurable graduation criteria with staged rollout.

**Forge defaults (1/2):** Structured test table covering unit/integration/E2E. But no graduation criteria. Integration test infrastructure vague ("FlashBlade access" — mock? lab array? simulator?). No concurrency testing for the Realm pool.

---

## Key Qualitative Differences

### Architectural Approach

All three correctly identify this as an Ansible role addition, not a new CRD/API resource. The differentiation is in depth:

- **Original** specifies exact file structures, variable names, ConfigMap schemas, and credential formats. The three-tier credential model and blast-radius analysis are unique to this variant.
- **Forge+OSAC** produces a well-structured EP-format document with comparison tables and failure matrices, but introduces a contradiction (metrics requiring fulfillment-service changes vs. "no API changes").
- **Forge defaults** uses Gherkin scenarios (product spec format, not design format) and leaves the Realm pool — the novel and hardest part — underspecified.

### Realm Pool Design

The Realm pool checkout/release mechanism is the central novel concept. How each approach handles it:

- **Original:** ConfigMap-based tracker with `osac.openshift.io/realm-allocations` annotation, optimistic concurrency via resourceVersion, rollback on failure, explicit single-use vs. reuse flag design.
- **Forge+OSAC:** StorageBackend annotation-based tracking with optimistic concurrency, similar to original but less detailed on edge cases (concurrent checkout, partial teardown recovery).
- **Forge defaults:** Mentions Realm pool but never specifies where state lives, how concurrency is handled, or what the state machine looks like. Open Questions substitute for design decisions.

### Template Compliance

- **Original:** Full EP template with all sections. YAML frontmatter present (missing `---` delimiters per automated check).
- **Forge+OSAC:** Full EP template with all 15 sections. Frontmatter present but missing tracking-link and prd fields.
- **Forge defaults:** Uses the generic Forge spec template (Overview, Scenarios, Functions, Interface Changes). 0/15 required EP sections. No frontmatter.

---

## What the Original Does That AI Approaches Don't

1. **Blast-radius analysis** — three-tier credential isolation with explicit scope per tier
2. **Both-paths design** — OQ-1 designed for both outcomes (Realm reuse vs. single-use) rather than deferring
3. **Drawbacks that engage** — genuinely argues against the Realm pool model rather than dismissing concerns
4. **Persona-specific workflow sections** — distinct flows for Cloud Infrastructure Admin, Cloud Provider Admin, Tenant Admin/User
5. **Exact implementation artifacts** — file structures, variable names, YAML manifests, default values

## What Forge+OSAC Does Well

1. **Structured comparison** — VAST vs. Pure comparison table is clearer than the original's prose
2. **Failure handling matrix** — tabular format with consistent columns
3. **Metrics proposal** — Realm pool utilization Prometheus metrics (though with the cross-repo gap)
4. **Template discipline** — all 15 EP sections filled, no placeholders

## What Forge Defaults Lacks

1. **Wrong document type** — Gherkin behavioral spec instead of architectural design
2. **The hard part is missing** — Realm pool implementation left as open questions
3. **No alternatives** — no rejected approaches documented
4. **No OSAC conventions** — no frontmatter, no tenant annotations, no dimension coverage

---

## Summary

The original human-written design (PR #171) scores highest because it goes deepest on the novel problem — the Realm pool — and provides implementation-ready specificity. Forge+OSAC produces a structurally compliant design that passes the rubric but misses depth on cross-repo dependencies and dimension coverage. Forge defaults produces a behavioral specification that fails as a design document — it answers "what should the system do?" but not "how should we build it?"

This feature is an interesting test case because it introduces no new API resources (the typical OSAC design challenge). The differentiation is entirely in operational architecture — Ansible role design, credential management, pool lifecycle — areas where domain-specific skills and human expertise show their value most clearly.
