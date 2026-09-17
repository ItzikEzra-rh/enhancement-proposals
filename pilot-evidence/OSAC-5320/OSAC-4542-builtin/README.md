# OSAC-4542: built-in test-planning handoff evidence

This package supports a workflow-ownership question for Andy. It preserves an
existing-design pilot from test-plan generation through local decomposition and
E2E planning. It is evaluation evidence, not an implementation proposal or a
request to approve these generated stories.

Tracking: [OSAC-5320](https://redhat.atlassian.net/browse/OSAC-5320), under
[OSAC-4835](https://redhat.atlassian.net/browse/OSAC-4835).
The original test-plan publication is [fork PR #75](https://github.com/ItzikEzra-rh/enhancement-proposals/pull/75).
That PR and earlier pilots remain unchanged.

## The question

Andy explained that the reviewed `testplan.md` feeds decomposition, with unit
coverage included in DEV implementation and integration tests represented by QE
issues. Our pinned E2E ingest phase explicitly assigns unit and integration
tests to the implement workflow. We want to clarify the intended boundary and
whether terminology or the pinned workflow version explains the difference.

The concrete example is public Volume API validation with fulfillment-service,
PostgreSQL and tenancy/authentication boundaries running in Kind, without a real
storage-provider lifecycle. The generated decomposition assigns that component
integration work to DEV Story 1.02. It assigns the deployed provider journey to
QE Story 1.03.

1. Is that DEV/component-integration versus QE/deployed-E2E split intended?
   If integration should instead be a QE issue, which workflow consumes it?
2. Does the pinned phase reflect the intended behavior, or should we evaluate
   a newer workflow revision? Please identify the relevant version if so.
3. Is the expected design-stage handoff: scenarios, explicit expected results,
   tier/boundary, setup needs and dependencies, with the consuming implementation
   workflow designing and creating missing fixtures/helpers?

These questions concern workflow responsibility. We are not asking Andy to
resolve OSAC provider credentials, product behavior, or team ownership for us.

## Read these three files first

| Evidence | What to inspect |
|---|---|
| [DEV Story 1.02](design/06-stories/epic-1/story-02-list-visibility-and-lifecycle-behavior.md) | Testing Approach assigns Kind component integration to DEV; provider behavior is outside that tier. |
| [QE Story 1.03](design/06-stories/epic-1/story-03-public-volume-e2e-validation.md) | Deployed public reads and provider setup; explicitly excludes duplicate Kind coverage. |
| [E2E plan](e2e/02-plan.md) | Reconciliation Corrections, scenario ownership, implementable helper work, execution prerequisites, and remaining decisions. |

Supporting evidence: [test plan](design/04-testplan.md),
[epic breakdown](design/05-epics.md), [coverage mapping](design/07-coverage.md),
and [input/artifact hashes](manifest.json).

## What we ran

Built-in design ingest and test-plan-only draft, followed by local built-in
decomposition, E2E ingest and E2E plan. The approved design remained unchanged.
Decomposition was a pilot evaluation, not production approval; no issues were
synced and dependencies were not assumed complete.

The experiment excluded our draft/decompose overrides and the custom
`design-test-planning` skill. It retained OSAC repository/component guidance,
including our planning-evidence documentation. It therefore does not isolate
the contribution of that guidance or establish stock-workflow sufficiency.

The workflow was pinned to
[`f1d6a4b645ac7ea6c8dfce49c36f7bf826b75a05`](https://github.com/flightctl/ai-workflows/tree/f1d6a4b645ac7ea6c8dfce49c36f7bf826b75a05).
The relevant [E2E ingest source](https://github.com/flightctl/ai-workflows/blob/f1d6a4b645ac7ea6c8dfce49c36f7bf826b75a05/e2e/skills/ingest.md#L13-L14)
says unit and integration testing are handled by the implement workflow.
This is a claim about the pinned pilot version, not the latest release.

## What we obtained

- 17 test cases, assigned across two DEV stories, one QE story and one DOCS story.
- E2E ingest selected six cases through the QE story's requirement references.
- The downstream plan retained gRPC/tenant isolation, provider-admin visibility,
  REST and manual CLI scenarios. It kept Kind integration with DEV and API
  specification validation with DOCS.
- TC-FR8-01 has both a Kind realization and a deployed realization in the
  generated handoff. These are distinct boundaries; the shared identifier does
  not mean one execution proves both.

## What we corrected afterward

One explicitly requested reconciliation changed only the local E2E plan:

- Missing helpers and fixtures were classified as implementable test work.
- Environment/credential/configuration and dependency availability were
  separated from unresolved provider lifecycle contracts and harness ownership.
- REST/CLI remain assigned to the QE story at requirement level, but concrete
  owners are unresolved. Unsupported "assigned elsewhere" claims were removed.
- The Kind/deployed distinction was made explicit.
- Publication metadata was corrected to local evaluation and contributor-fork
  only; no upstream PR target is authorized.

The copied E2E plan is the reconciled version. Its correction table records the
changes; this package does not include a preserved pre-reconciliation plan.
The design test plan and decomposition copies were not rewritten during that
reconciliation. Seven copied artifacts match their local sources byte-for-byte.
The repository's end-of-file hook removed surplus trailing blank lines from the
epic summary and DEV Story 1.01 copies only; their text is otherwise unchanged.
The manifest records original and published hashes for these two copies.

## Limits and open findings

This shows a handoff through built-in phases, not correction-free generation,
complete behavioral acceptance, implemented tests, or successful execution.
No product tests, collection, installation, or implementation were performed.
Documentation publication checks are separate from product test execution.

Provider lifecycle contracts, concrete harness ownership and the dual-boundary
decision remain unresolved. Ordering classification and specification/command
ownership also remain findings in the generated artifacts. Some coverage-table
wording still calls missing fixtures blockers despite the corrected categories;
the snapshots intentionally preserve that inconsistency. Missing credentials
alone do not prevent writing tests, and unsynchronized Jira dependencies are not
proof of missing implementation.

Artifact-local source paths refer to the pinned OSAC workspace. They are evidence
references, not runnable files in this documentation repository. The manifest
maps each copy to its original artifact path. Use the reading links above to
navigate this package.

Our provisional conclusion is that this pilot has not demonstrated a need for
our phase overrides or new planning skill. Clarifying the intended integration
handoff comes before deciding whether any workflow change is necessary.
