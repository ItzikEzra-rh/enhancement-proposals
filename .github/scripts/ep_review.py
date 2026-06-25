#!/usr/bin/env python3
"""
AI EP Review — thin wrapper around the ep-review skill.

Reads SKILL.md as the system prompt, fetches the PR diff,
calls Claude API for structured review, sanitizes output,
posts the result as a PR comment, and applies the reviewed label.
"""

import json
import os
import re
import subprocess
import sys
import tempfile

from anthropic import AnthropicVertex

REPO = os.environ["REPO"]
PR_NUMBER = os.environ["PR_NUMBER"]
SKILL_PATH = ".osac-workspace/skills/ep-review/SKILL.md"
TEMPLATE_PATH = "guidelines/enhancement_template.md"
REVIEWED_LABEL = "rfe-creator-auto-reviewed"
GCP_PROJECT = os.environ["GCP_PROJECT"]
GCP_REGION = os.environ["GCP_REGION"]
MODEL = "claude-sonnet-4@20250514"
BOT_LOGIN = "github-actions[bot]"

REVIEW_TOOL = {
    "name": "submit_review",
    "description": "Submit a structured EP review with scores and findings.",
    "input_schema": {
        "type": "object",
        "properties": {
            "title": {"type": "string", "description": "EP title from the PR"},
            "scores": {
                "type": "object",
                "properties": {
                    "what": {"type": "integer", "minimum": 0, "maximum": 2,
                             "description": "Problem clarity and template compliance (0-2)"},
                    "why": {"type": "integer", "minimum": 0, "maximum": 2,
                            "description": "Business justification and user stories (0-2)"},
                    "how": {"type": "integer", "minimum": 0, "maximum": 2,
                            "description": "Approach, architecture alignment, acceptance criteria (0-2)"},
                    "task": {"type": "integer", "minimum": 0, "maximum": 2,
                             "description": "Enhancement quality, cross-cutting concerns (0-2)"},
                    "size": {"type": "integer", "minimum": 0, "maximum": 2,
                             "description": "Scope appropriateness, completeness (0-2)"},
                },
                "required": ["what", "why", "how", "task", "size"]
            },
            "criterionNotes": {
                "type": "object",
                "properties": {
                    "what": {"type": "string"},
                    "why": {"type": "string"},
                    "how": {"type": "string"},
                    "task": {"type": "string"},
                    "size": {"type": "string"},
                },
                "required": ["what", "why", "how", "task", "size"]
            },
            "findings": {
                "type": "object",
                "properties": {
                    "critical": {"type": "array", "items": {"type": "string"}},
                    "important": {"type": "array", "items": {"type": "string"}},
                    "suggestions": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["critical", "important", "suggestions"]
            }
        },
        "required": ["title", "scores", "criterionNotes", "findings"]
    }
}


def gh(args):
    """Run a gh CLI command and return stdout."""
    result = subprocess.run(
        ["gh"] + args, capture_output=True, text=True, timeout=60
    )
    if result.returncode != 0:
        print(f"gh command failed with exit code {result.returncode}", file=sys.stderr)
        sys.exit(1)
    return result.stdout


def read_file(path):
    """Read and return the contents of a file."""
    with open(path) as f:
        return f.read()


def sanitize_text(text, max_len=500):
    """Strip dangerous markdown constructs from model output."""
    text = re.sub(r'!\[[^\]]*\]\([^\)]*\)', '', text)
    text = re.sub(r'\[([^\]]*)\]\([^\)]*\)', r'\1', text)
    text = re.sub(r'<[^>]+>', '', text)
    text = re.sub(r'@(\w+)', r'\1', text)
    text = re.sub(r'https?://(?!redhat\.atlassian\.net)\S+', '[link removed]', text)
    return text.strip()[:max_len]


def validate_review(review):
    """Clamp scores to valid range and sanitize all string fields."""
    for k in ["what", "why", "how", "task", "size"]:
        review["scores"][k] = max(0, min(2, int(review["scores"][k])))
    review["title"] = sanitize_text(review.get("title", ""), 200)
    for k in review.get("criterionNotes", {}):
        review["criterionNotes"][k] = sanitize_text(review["criterionNotes"][k], 200)
    for sev in ["critical", "important", "suggestions"]:
        review["findings"][sev] = [sanitize_text(f) for f in review["findings"].get(sev, [])]
    return review


def format_comment(review):
    """Format a validated review into a markdown PR comment."""
    title = review["title"]
    s = review["scores"]
    total = sum(s.values())
    verdict = "PASS" if total >= 5 else "FAIL"
    notes = review["criterionNotes"]
    findings = review["findings"]

    lines = [
        f"## AI EP Review: {title}",
        "",
        f"**Score: {total}/10** | **Verdict: {verdict}**",
        "",
        "| Criterion | Score | Notes |",
        "|-----------|-------|-------|",
    ]
    for key in ["what", "why", "how", "task", "size"]:
        label = key.capitalize()
        note = notes.get(key, "").replace("|", "\\|").replace("\n", " ")
        lines.append(f"| {label} | {s[key]}/2 | {note} |")

    for severity in ["critical", "important", "suggestions"]:
        items = findings.get(severity, [])
        lines.append("")
        lines.append(f"### {severity.capitalize()} ({len(items)})")
        if items:
            for i, item in enumerate(items, 1):
                lines.append(f"{i}. {item}")
        else:
            lines.append("None.")

    return "\n".join(lines)


def main():
    """Run the EP review: read inputs, call Claude, sanitize, post comment, apply label."""
    skill_prompt = read_file(SKILL_PATH)
    template = read_file(TEMPLATE_PATH)

    diff_file = os.environ.get("PR_DIFF_FILE")
    meta_file = os.environ.get("PR_META_FILE")
    if diff_file and meta_file:
        diff = read_file(diff_file)
        pr_info = json.loads(read_file(meta_file))
    else:
        diff = gh(["pr", "diff", PR_NUMBER, "--repo", REPO])
        pr_meta = gh(["pr", "view", PR_NUMBER, "--repo", REPO,
                      "--json", "title,body,author,files"])
        pr_info = json.loads(pr_meta)

    if not diff.strip():
        print("No diff found — skipping review.")
        return

    truncated = len(diff) > 50000
    if truncated:
        print(f"Diff truncated from {len(diff)} to 50000 chars")

    client = AnthropicVertex(project_id=GCP_PROJECT, region=GCP_REGION)
    user_message = (
        "Review this Enhancement Proposal PR against the OSAC EP template.\n\n"
        f"## PR: {pr_info['title']}\n\n"
        f"## EP Template\n\n{template}\n\n"
        f"## PR Diff\n\n```\n{diff[:50000]}\n```\n\n"
        "Use the submit_review tool to provide your structured review."
    )

    print(f"Reviewing EP: {pr_info['title']}")

    response = client.messages.create(
        model=MODEL,
        max_tokens=4096,
        system=skill_prompt,
        tools=[REVIEW_TOOL],
        messages=[{"role": "user", "content": user_message}],
    )

    review = None
    for block in response.content:
        if block.type == "tool_use" and block.name == "submit_review":
            review = block.input
            break

    if not review:
        print("No structured review returned — model did not call submit_review tool.", file=sys.stderr)
        sys.exit(1)

    review = validate_review(review)
    comment = format_comment(review)
    if truncated:
        comment += "\n\n> **Note:** PR diff was truncated to 50,000 characters. Review may be incomplete."
    total = sum(review["scores"].values())
    print(f"Review complete: {total}/10 ({'PASS' if total >= 5 else 'FAIL'})")

    existing = gh(["api", f"repos/{REPO}/issues/{PR_NUMBER}/comments",
                   "--jq", f'[.[] | select(.user.login == "{BOT_LOGIN}") | select(.body | startswith("## AI EP Review:"))][0].id // empty'])
    comment_id = existing.strip()

    with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
        f.write(comment)
        comment_file = f.name

    if comment_id:
        gh(["api", f"repos/{REPO}/issues/comments/{comment_id}",
            "--method", "PATCH", "--field", f"body=@{comment_file}"])
        print(f"Updated existing review comment on PR #{PR_NUMBER}")
    else:
        gh(["pr", "comment", PR_NUMBER, "--repo", REPO, "--body-file", comment_file])
        print(f"Posted new review comment on PR #{PR_NUMBER}")

    os.unlink(comment_file)

    gh(["pr", "edit", PR_NUMBER, "--repo", REPO,
        "--add-label", REVIEWED_LABEL])
    print(f"Applied label: {REVIEWED_LABEL}")


if __name__ == "__main__":
    main()
