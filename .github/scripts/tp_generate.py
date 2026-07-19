#!/usr/bin/env python3
"""
Test Plan Generate — GitHub Action entry point.

Runs from osac-workspace (after bootstrap.sh clones all component repos).
Detects which EP had a design document merged, generates a TestPlan.md
via agentic-ci with full workspace context, and opens a new PR.
"""

import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, os.environ.get("EP_REPO_PATH", ".") + "/.github/scripts")

from tp_hooks import TestPlanHooks
from tp_skill_config import build_skill_config


REPO = os.environ.get("GITHUB_REPOSITORY",
                       "ItzikEzra-rh/enhancement-proposals")
SKILLS_PATH = os.environ.get("SKILLS_PATH", "/opt/osac-workspace/osac-test-plan")
WORKSPACE_PATH = os.environ.get("WORKSPACE_PATH", "/opt/osac-workspace")
EP_REPO_PATH = os.environ.get("EP_REPO_PATH", "enhancement-proposals")
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
            config_dir=Path(WORKSPACE_PATH),
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
    shadow = os.environ.get("TP_SHADOW", "true").lower() == "true"

    if not pr_number:
        print("PR_NUMBER not set", file=sys.stderr)
        sys.exit(1)

    print(f"Test Plan Generate — PR #{pr_number} (sha: {head_sha[:8]})")
    print(f"Workspace: {WORKSPACE_PATH}")
    print(f"EP repo: {EP_REPO_PATH}")
    print(f"Skills: {SKILLS_PATH}")
    if shadow:
        print("SHADOW MODE: will run but not create PR")

    files = get_changed_files(pr_number)
    if not files:
        print("No files changed")
        return

    ep_slug = detect_ep_slug(files)
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

    # Check design and PRD exist in the EP repo
    ep_dir = Path(EP_REPO_PATH) / "enhancements" / ep_slug
    design_file = None
    for name in ["README.md", "design.md", "DESIGN.md"]:
        candidate = ep_dir / name
        if candidate.exists():
            design_file = candidate
            break
    prd_file = ep_dir / "prd.md"

    print(f"  Design: {design_file or 'NOT FOUND'}")
    print(f"  PRD: {prd_file if prd_file.exists() else 'NOT FOUND'}")

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
        workspace_path=WORKSPACE_PATH,
        ep_repo_path=EP_REPO_PATH,
    )
    hooks.set_mode("generate")

    ticket = {
        "number": int(pr_number),
        "title": pr.get("title", ""),
        "body": pr.get("body", ""),
        "author": pr.get("author", {}).get("login", "unknown"),
        "headRefOid": pr.get("headRefOid", head_sha),
        "labels": [l.get("name", "") for l in pr.get("labels", [])],
        "_ep_slug": ep_slug,
        "_design_file": str(design_file) if design_file else "",
        "_prd_file": str(prd_file) if prd_file.exists() else "",
    }

    skill_name = "test-plan-create"
    skill_path = "skills/test-plan-create/SKILL.md"
    ticket_key = f"TP-{pr_number}"

    # Work dir gets mounted as /workspace/ inside the container.
    # Copy skills + all component repos into it so the agent has everything.
    work_dir = Path(WORKSPACE_PATH) / f"workdir-{skill_name}"
    if work_dir.exists():
        shutil.rmtree(work_dir)
    shutil.copytree(SKILLS_PATH, work_dir,
                    ignore=shutil.ignore_patterns('.git'))

    # Write EP slug for the PR creation step to read
    (work_dir / "ep-slug.txt").write_text(ep_slug)

    # Copy component repos into work_dir so they're visible inside container
    ws = Path(WORKSPACE_PATH)
    for repo_dir in ws.iterdir():
        if repo_dir.is_dir() and (repo_dir / ".git").exists() and repo_dir.name != work_dir.name:
            dest = work_dir / repo_dir.name
            if not dest.exists():
                print(f"  Copying {repo_dir.name}/ into work_dir...")
                shutil.copytree(repo_dir, dest,
                                ignore=shutil.ignore_patterns('.git'),
                                symlinks=True)

    print(f"\nRunning {skill_name} from {WORKSPACE_PATH}...")
    try:
        run_generate(hooks, skill_name, skill_path, ticket_key,
                     ticket, work_dir)
    except Exception as e:
        print(f"  [{skill_name}] failed: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        if IN_CI:
            sys.exit(1)

    # Create PR with the generated test plan (outside agentic-ci pipeline)
    output_file = work_dir / "testplan-output.md"
    if not output_file.exists():
        print("No testplan-output.md — skipping PR creation")
        return

    target_path = Path(EP_REPO_PATH) / "enhancements" / ep_slug / "TestPlan.md"
    branch_name = f"test-plan/{ep_slug}"
    pr_title = f"Test Plan: {pr.get('title', ep_slug)}"

    if shadow:
        print(f"  SHADOW: would create branch '{branch_name}'")
        print(f"  SHADOW: would write {target_path}")
        print(f"  SHADOW: would open PR '{pr_title}'")
        return

    print(f"  Creating PR with TestPlan.md...")
    ep_repo = Path(EP_REPO_PATH)

    def git(*args):
        result = subprocess.run(
            ["git", "-C", str(ep_repo)] + list(args),
            capture_output=True, text=True
        )
        if result.returncode != 0:
            print(f"  git {' '.join(args[:3])}: {result.stderr.strip()}")
        return result.returncode

    # Configure git identity for commits
    git("config", "user.email", "test-plan-bot@osac.openshift.io")
    git("config", "user.name", "Test Plan Bot")

    # Delete remote/local branch if exists from previous run
    git("push", "origin", "--delete", branch_name)
    git("branch", "-D", branch_name)

    rc = git("checkout", "-b", branch_name)
    if rc != 0:
        print("  Failed to create branch — aborting PR creation")
        return

    target_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(output_file, target_path)
    git("add", str(target_path))

    rc = git("commit", "-m",
             f"Add test plan for {ep_slug}\n\n"
             f"Generated from PR #{pr_number}\n\n"
             "Assisted-by: Claude Code <noreply@anthropic.com>")
    if rc != 0:
        print("  Failed to commit — aborting PR creation")
        return

    rc = git("push", "origin", branch_name)
    if rc != 0:
        print("  Failed to push — aborting PR creation")
        return
    gh(["pr", "create", "--repo", REPO,
        "--head", branch_name, "--base", "main",
        "--title", pr_title,
        "--body",
        f"Auto-generated test plan for `enhancements/{ep_slug}/`.\n\n"
        f"Source: PR #{pr_number}\n\n"
        "Review and comment. Type `/test-plan-respond` to trigger AI revision."])
    print(f"  Created PR on branch {branch_name}")


if __name__ == "__main__":
    main()
