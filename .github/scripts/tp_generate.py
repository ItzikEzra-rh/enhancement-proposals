#!/usr/bin/env python3
"""
Test Plan Generate — GitHub Action entry point.

Detects which EP had a design document merged, generates a TestPlan.md
via agentic-ci, and opens a new PR with the test plan.
"""

import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

from tp_hooks import TestPlanHooks
from tp_skill_config import build_skill_config


REPO = os.environ.get("GITHUB_REPOSITORY",
                       "ItzikEzra-rh/enhancement-proposals")
SKILLS_PATH = "/opt/test-plan-skills"
IN_CI = os.environ.get("GITHUB_ACTIONS") == "true"


def gh(args):
    result = subprocess.run(
        ["gh"] + args, capture_output=True, text=True, timeout=120
    )
    if result.returncode != 0:
        msg = f"gh {' '.join(args[:3])}... failed: {result.stderr[:300]}"
        if IN_CI:
            raise RuntimeError(msg)
        print(f"gh error: {msg}", file=sys.stderr)
    return result.stdout


def get_changed_files(pr_number):
    raw = gh(["api", f"repos/{REPO}/pulls/{pr_number}/files",
              "--paginate", "--jq", "[.[].filename]"])
    return json.loads(raw) if raw.strip() else []


def detect_ep_slug(files):
    pattern = re.compile(
        r"enhancements/([^/]+)/"
        r"(?:design\.md|DESIGN\.md|Design\.md|README\.md)",
        re.IGNORECASE,
    )
    for f in files:
        m = pattern.match(f)
        if m:
            return m.group(1)
    return None


def run_generate(hooks, skill_name, skill_path, ticket_key, ticket, work_dir):
    ticket = {**ticket, "_skill_name": skill_name, "_skill_path": skill_path}

    try:
        from agentic_ci.skill import run_skill

        config = build_skill_config(
            hooks=hooks,
            skill_name=skill_name,
            skills_path=SKILLS_PATH,
            post_gates=[hooks.validate_testplan_output],
        )

        rc = run_skill(
            config,
            ticket_key=ticket_key,
            work_dir=work_dir,
            config_dir=Path("."),
            mode="resolve",
            ticket=ticket,
        )

        output = work_dir / "testplan-output.md"
        if output.exists():
            print(f"  [{skill_name}] Generated testplan-output.md "
                  f"({output.stat().st_size} bytes, rc={rc})")
        else:
            print(f"  [{skill_name}] No testplan-output.md (rc={rc})")

    except ImportError:
        if IN_CI:
            print("agentic-ci not installed in CI — this is a fatal error",
                  file=sys.stderr)
            sys.exit(1)
        print(f"  [{skill_name}] dry-run (agentic-ci not available)")
        hooks.write_context(
            ticket_key=ticket_key, ticket=ticket,
            mode="resolve", work_dir=work_dir,
        )


def main():
    pr_number = os.environ.get("PR_NUMBER")
    head_sha = os.environ.get("PR_HEAD_SHA", "")
    ep_slug_env = os.environ.get("EP_SLUG", "")
    shadow = os.environ.get("TP_SHADOW", "true").lower() == "true"

    if not pr_number:
        print("PR_NUMBER not set", file=sys.stderr)
        sys.exit(1)

    print(f"Test Plan Generate — PR #{pr_number} (sha: {head_sha[:8]})")
    if shadow:
        print("SHADOW MODE: will run but not create PR")

    files = get_changed_files(pr_number)
    if not files:
        print("No files changed")
        return

    ep_slug = ep_slug_env or detect_ep_slug(files)
    if not ep_slug:
        print("No EP slug detected from changed files — skipping")
        return

    has_design = any(
        f.lower().endswith("design.md") or
        (f.lower().endswith("readme.md") and "enhancements/" in f.lower())
        for f in files
    )
    if not has_design:
        print("No design document found in changed files — skipping")
        return

    print(f"Detected EP: {ep_slug}")

    pr_raw = gh(["pr", "view", str(pr_number), "--repo", REPO,
                  "--json", "number,title,body,author,labels,headRefOid"])
    if not pr_raw.strip():
        print("Could not fetch PR details", file=sys.stderr)
        sys.exit(1)
    pr = json.loads(pr_raw)

    hooks = TestPlanHooks(
        repo=REPO,
        skills_path=SKILLS_PATH,
        shadow=shadow,
    )

    ticket = {
        "number": int(pr_number),
        "title": pr.get("title", ""),
        "body": pr.get("body", ""),
        "author": pr.get("author", {}).get("login", "unknown"),
        "headRefOid": pr.get("headRefOid", head_sha),
        "labels": [l.get("name", "") for l in pr.get("labels", [])],
        "_ep_slug": ep_slug,
    }

    skill_name = "test-plan-create"
    skill_path = "skills/test-plan-create/SKILL.md"
    ticket_key = f"TP-{pr_number}"
    work_dir = Path(f"workdir-{skill_name}")

    if work_dir.exists():
        shutil.rmtree(work_dir)
    shutil.copytree(SKILLS_PATH, work_dir,
                    ignore=shutil.ignore_patterns('.git'))

    print(f"\nRunning {skill_name}...")
    try:
        run_generate(hooks, skill_name, skill_path, ticket_key,
                     ticket, work_dir)
    except Exception as e:
        print(f"  [{skill_name}] failed: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        if IN_CI:
            sys.exit(1)


if __name__ == "__main__":
    main()
