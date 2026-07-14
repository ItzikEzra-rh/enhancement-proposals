"""Regression test for OSAC-2131: rubric table Notes column truncation."""

from unittest.mock import patch

import pytest

from ep_hooks import EPHooks


def _capture_comment(verdict):
    """Run apply_labels in non-shadow mode, return the posted comment body."""
    hooks = EPHooks(repo="test/repo", skills_path="/tmp", shadow=False)
    captured = []

    def fake_gh(args, check=False):
        if "--body-file" in args:
            path = args[args.index("--body-file") + 1]
            with open(path) as f:
                captured.append(f.read())
        return ""

    with patch.object(hooks, "_gh", side_effect=fake_gh):
        hooks.apply_labels("EP-99", verdict, "review", "/tmp")

    assert len(captured) == 1
    return captured[0]


# -- Real notes from EP-70 (PRD review) that were truncated at 200 chars --

EP70_NOTES = {
    "what": (
        "Clear, specific, user-observable capabilities. Tenant users place "
        "workloads in AZs, cloud infrastructure admins manage AZs and deploy "
        "HA regions. Both personas are identified. Services are implied "
        "through user-facing requirements rather than named directly, though "
        "FR-1 leaks internal component names."
    ),
    "why": (
        "Strong justification in the problem statement: names the specific "
        "pain (no fault domain selection, no AZ in data model), describes "
        "consequences (cannot offer HA guarantees and placement controls), "
        "and ties to business value (competitive parity with hyperscalers)."
    ),
    "how": (
        "Requirements are mostly specific and measurable, but design leakage "
        "weakens the approach. FR-1 names 'fulfillment-service' and 'operator "
        "instances'; FR-9 prescribes deployment topology (control plane "
        "separation) rather than user-observable behavior. These belong in "
        "the enhancement proposal, not the PRD."
    ),
    "task": (
        "This is clearly a new enhancement introducing region/AZ architecture "
        "and user-facing placement controls — not a bug fix or operational "
        "task. It defines new capabilities, new API surfaces (AZ entity, "
        "AZ-aware placement), and new admin workflows."
    ),
    "size": (
        "The PRD bundles user-facing AZ workload placement (FR-3 through FR-8) "
        "with HA control plane deployment and zero-downtime upgrades (FR-14, "
        "FR-15). These serve different personas and workflows — a tenant "
        "placing VMs in AZs vs. an admin deploying HA control planes — and "
        "could ship independently."
    ),
}

# -- Real notes from EP-114 (Design review) that were truncated --

EP114_NOTES = {
    "feasibility": (
        "The change is a straightforward text update to a user story. Replacing "
        "generic IdP references with Keycloak as IdP broker is technically "
        "sound — Keycloak natively supports LDAP, AD, OIDC, and SAML brokering. "
        "No code or infrastructure changes required."
    ),
    "testability": (
        "The updated user story drops the 'so that' clause required by the "
        "template's three-part formula ('As a role, I want to action so that I "
        "can goal'). Without an explicit goal, it becomes harder to define "
        "acceptance criteria and write meaningful validation tests."
    ),
    "scope": (
        "Well-defined and appropriately sized — a single user story update with "
        "a clear rationale (persona correction and technology specificity). No "
        "unnecessary changes."
    ),
    "architecture": (
        "Narrowing from generic IdP to Keycloak as IdP broker is a valid "
        "architectural clarification, and changing the persona to Cloud "
        "Infrastructure Admin correctly reflects the infrastructure-level "
        "responsibility. However the grammar error weakens clarity."
    ),
}


class TestRealPRDNotes:
    """Replay real EP-70 PRD review notes — all were truncated at 200 chars."""

    def test_all_ep70_notes_preserved(self):
        verdict = {
            "verdict": "pass",
            "scores": {"what": 2, "why": 2, "how": 1, "task": 2, "size": 1},
            "total": 8,
            "criterionNotes": EP70_NOTES,
            "summary": "Good PRD.",
            "feedback": "Remove design leakage.",
            "findings": {"critical": [], "important": [], "suggestions": []},
        }
        comment = _capture_comment(verdict)
        for key, note in EP70_NOTES.items():
            sanitized = EPHooks._sanitize_text(note)
            assert sanitized in comment, (
                f"{key} note truncated: expected {len(sanitized)} chars, "
                f"got cut in comment"
            )


class TestRealDesignNotes:
    """Replay real EP-114 design review notes."""

    def test_all_ep114_notes_preserved(self):
        verdict = {
            "verdict": "pass",
            "scores": {"feasibility": 2, "testability": 1, "scope": 2, "architecture": 1},
            "total": 6,
            "criterionNotes": EP114_NOTES,
            "summary": "Solid design.",
            "feedback": "Fix grammar.",
            "findings": {"critical": [], "important": [], "suggestions": []},
        }
        comment = _capture_comment(verdict)
        for key, note in EP114_NOTES.items():
            sanitized = EPHooks._sanitize_text(note)
            assert sanitized in comment, (
                f"{key} note truncated: expected {len(sanitized)} chars, "
                f"got cut in comment"
            )


class TestSyntheticBoundaries:
    """Verify the 500-char default boundary."""

    def test_300_char_notes_preserved(self):
        verdict = {
            "verdict": "pass",
            "scores": {"what": 2, "why": 2, "how": 1, "task": 2, "size": 1},
            "total": 8,
            "criterionNotes": {k: "A" * 300 for k in ["what", "why", "how", "task", "size"]},
            "summary": "Good.",
            "feedback": "None.",
            "findings": {"critical": [], "important": [], "suggestions": []},
        }
        comment = _capture_comment(verdict)
        assert "A" * 300 in comment

    def test_notes_beyond_500_truncated(self):
        verdict = {
            "verdict": "pass",
            "scores": {"what": 2, "why": 2, "how": 1, "task": 2, "size": 1},
            "total": 8,
            "criterionNotes": {k: "C" * 600 for k in ["what", "why", "how", "task", "size"]},
            "summary": "Good.",
            "feedback": "None.",
            "findings": {"critical": [], "important": [], "suggestions": []},
        }
        comment = _capture_comment(verdict)
        assert "C" * 600 not in comment
        assert "C" * 500 in comment
