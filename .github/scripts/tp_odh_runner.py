#!/usr/bin/env python3
"""
Runner for odh-test-gen test-plan-create skill via agentic-ci.

Wraps the odh-test-gen skill to run inside the same agentic-ci
container infrastructure used by the EP review and our test plan tools.
"""

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

ODH_SKILLS_PATH = "/opt/odh-test-gen"
WORKSPACE_PATH = os.environ.get("WORKSPACE_PATH", "/opt/osac-workspace")
OUTPUT_DIR = "/opt/test-plans/plans/osac"
IN_CI = os.environ.get("GITHUB_ACTIONS") == "true"

sys.path.insert(0, os.environ.get("EP_REPO_PATH",
    os.environ.get("GITHUB_WORKSPACE", ".") + "/enhancement-proposals")
    + "/.github/scripts")


def main():
    jira_key = os.environ.get("JIRA_KEY", "")
    ep_slug = os.environ.get("EP_SLUG", "")

    if not jira_key:
        print("JIRA_KEY not set — cannot run odh-test-gen", file=sys.stderr)
        sys.exit(1)

    print(f"odh-test-gen runner — Jira key: {jira_key}, EP: {ep_slug}")

    design_doc = "/opt/design-doc.md"
    prd_doc = "/opt/prd-doc.md"

    # Build args for the skill
    skill_args = jira_key
    if Path(design_doc).exists():
        skill_args += f" {design_doc}"
    skill_args += f" --output-dir {OUTPUT_DIR}"

    print(f"  Skill args: {skill_args}")
    print(f"  Output dir: {OUTPUT_DIR}")

    try:
        from tp_skill_config import build_skill_config

        class ODHHooks:
            """Minimal hooks for odh-test-gen — context is handled by the skill itself."""

            def __init__(self):
                self.jira_key = jira_key
                self.design_doc = design_doc
                self.prd_doc = prd_doc

            def write_context(self, ticket_key, ticket, mode, work_dir, **kw):
                context_dir = Path(work_dir) / ".context"
                context_dir.mkdir(parents=True, exist_ok=True)
                if Path(self.design_doc).exists():
                    (context_dir / "design.md").write_text(
                        Path(self.design_doc).read_text())
                if Path(self.prd_doc).exists():
                    (context_dir / "prd.md").write_text(
                        Path(self.prd_doc).read_text())

            def build_prompt(self, ticket_key, mode, skill_name, **kw):
                prompt = (
                    f"Run the test-plan-create skill from {ODH_SKILLS_PATH}/skills/test-plan-create/SKILL.md\n\n"
                    f"Arguments: {skill_args}\n\n"
                    "Follow the skill instructions exactly. "
                    "The Jira credentials are in environment variables "
                    "(JIRA_URL, JIRA_USER, JIRA_TOKEN).\n\n"
                    f"Write output to {OUTPUT_DIR}/"
                )
                return prompt

            def load_verdict(self, work_dir):
                return {"generated": True, "verdict": "generated"}

            def apply_labels(self, ticket_key, verdict, mode, work_dir, **kw):
                print(f"  [{ticket_key}] odh-test-gen completed")

            @staticmethod
            def format_cost(cost_data):
                if not cost_data:
                    return None
                try:
                    cost_totals = cost_data.get("cost_totals", {})
                    total = sum(cost_totals.values())
                    return f"**Total cost:** ${total:.4f}"
                except:
                    return None

        hooks = ODHHooks()
        from agentic_ci.skill import run_skill, SkillConfig

        config = SkillConfig(
            skill_name="test-plan-create-odh",
            skill_source=ODH_SKILLS_PATH,
            prompt_builder=hooks.build_prompt,
            context_writer=hooks.write_context,
            verdict_loader=hooks.load_verdict,
            label_applier=hooks.apply_labels,
            cost_formatter=hooks.format_cost,
            pre_gates=[],
            post_gates=[],
            backend_name="podman",
            harness_name="claude-code",
            container_image="quay.io/aipcc/agentic-ci/claude-runner:latest",
            container_env={
                "JIRA_URL": os.environ.get("JIRA_URL", ""),
                "JIRA_USER": os.environ.get("JIRA_USER", ""),
                "JIRA_TOKEN": os.environ.get("JIRA_TOKEN", ""),
            },
            max_retries=1,
        )

        # Create work dir with odh-test-gen + component repos
        work_dir = Path(WORKSPACE_PATH) / "workdir-odh-test-gen"
        if work_dir.exists():
            shutil.rmtree(work_dir)
        shutil.copytree(ODH_SKILLS_PATH, work_dir,
                        ignore=shutil.ignore_patterns('.git'))

        # Copy component repos for codebase browsing
        ws = Path(WORKSPACE_PATH)
        for repo_dir in ws.iterdir():
            if repo_dir.is_dir() and (repo_dir / ".git").exists() and repo_dir.name != work_dir.name:
                dest = work_dir / repo_dir.name
                if not dest.exists():
                    shutil.copytree(repo_dir, dest,
                                    ignore=shutil.ignore_patterns('.git'),
                                    symlinks=True)

        # Create output dir inside work_dir so it's visible in container
        (work_dir / "test-plans" / "plans" / "osac").mkdir(parents=True, exist_ok=True)

        ticket = {
            "_jira_key": jira_key,
            "_ep_slug": ep_slug,
        }

        rc = run_skill(
            config,
            ticket_key=f"ODH-{jira_key}",
            work_dir=work_dir,
            config_dir=Path(WORKSPACE_PATH),
            mode="resolve",
            ticket=ticket,
        )
        print(f"  odh-test-gen completed with rc={rc}")

        # Copy output to the expected location
        for tp in work_dir.rglob("TestPlan.md"):
            dest = Path(OUTPUT_DIR) / tp.name
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(tp, dest)
            print(f"  Copied {tp} -> {dest}")

    except ImportError:
        if IN_CI:
            print("agentic-ci not installed in CI — fatal", file=sys.stderr)
            sys.exit(1)
        print("  dry-run (agentic-ci not available)")


if __name__ == "__main__":
    main()
