"""
Delete/close all issues in Mery101010/Ctrl-Slay, then create Month 1 roadmap issues.
Requires: gh auth login
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPO = "Mery101010/Ctrl-Slay"
GH = Path(r"C:\Program Files\GitHub CLI\gh.exe")

# Import issue payloads
sys.path.insert(0, str(Path(__file__).resolve().parent))
from month1_issues import ISSUES  # noqa: E402


def run(args: list[str], check: bool = True, input_text: str | None = None) -> subprocess.CompletedProcess:
    cmd = [str(GH), *args]
    print(">", " ".join(cmd[:6]), ("..." if len(cmd) > 6 else ""))
    return subprocess.run(
        cmd,
        check=check,
        text=True,
        input=input_text,
        capture_output=True,
    )


def ensure_labels() -> None:
    labels = {
        "phase-1": "1D76DB",
        "month-1": "0E8A16",
        "trust-onboarding": "FBCA04",
        "support": "D93F0B",
        "reliability": "B60205",
        "instrumentation": "5319E7",
        "security": "000000",
        "compliance": "6A737D",
        "priority-p0": "FF0000",
        "priority-p1": "FFA500",
        "bug": "D73A4A",
        "android": "A2EEEF",
    }
    existing = run(["label", "list", "--repo", REPO, "--limit", "100", "--json", "name"], check=False)
    names = set()
    if existing.returncode == 0 and existing.stdout.strip():
        names = {x["name"] for x in json.loads(existing.stdout)}
    for name, color in labels.items():
        if name in names:
            continue
        r = run(
            ["label", "create", name, "--repo", REPO, "--color", color, "--force"],
            check=False,
        )
        if r.returncode != 0:
            print("label warn:", name, r.stderr.strip())


def list_all_issue_numbers() -> list[int]:
    r = run(
        [
            "issue",
            "list",
            "--repo",
            REPO,
            "--state",
            "all",
            "--limit",
            "500",
            "--json",
            "number,title,state",
        ]
    )
    items = json.loads(r.stdout or "[]")
    print(f"Found {len(items)} existing issues")
    for it in items:
        print(f"  #{it['number']} [{it['state']}] {it['title']}")
    return [int(it["number"]) for it in items]


def delete_issue(number: int) -> None:
    """Prefer hard delete via GraphQL; fall back to close."""
    # Resolve node id
    r = run(
        ["api", f"repos/{REPO}/issues/{number}", "--jq", ".node_id"],
        check=False,
    )
    if r.returncode != 0 or not r.stdout.strip():
        print(f"  cannot resolve node_id for #{number}; closing instead")
        run(["issue", "close", str(number), "--repo", REPO, "--reason", "not planned"], check=False)
        return
    node_id = r.stdout.strip()
    mutation = (
        "mutation($id:ID!){ deleteIssue(input:{issueId:$id}){ clientMutationId } }"
    )
    r2 = run(
        [
            "api",
            "graphql",
            "-f",
            f"query={mutation}",
            "-f",
            f"id={node_id}",
        ],
        check=False,
    )
    if r2.returncode == 0 and "errors" not in (r2.stdout or "").lower():
        print(f"  deleted #{number}")
        return
    print(f"  delete failed for #{number} ({r2.stderr or r2.stdout}); closing instead")
    run(["issue", "close", str(number), "--repo", REPO, "--reason", "not planned"], check=False)


def create_issues() -> None:
    for issue in ISSUES:
        body = issue["body"]
        labels = issue["labels"]
        title = issue["title"]
        args = [
            "issue",
            "create",
            "--repo",
            REPO,
            "--title",
            title,
            "--body",
            body,
        ]
        for lab in labels:
            args.extend(["--label", lab])
        r = run(args, check=False)
        if r.returncode != 0:
            # retry without labels if label attach fails
            print("create with labels failed:", r.stderr.strip())
            r = run(
                [
                    "issue",
                    "create",
                    "--repo",
                    REPO,
                    "--title",
                    title,
                    "--body",
                    body,
                ],
                check=True,
            )
        print("CREATED:", (r.stdout or "").strip())


def main() -> int:
    status = run(["auth", "status"], check=False)
    if status.returncode != 0:
        print("Not authenticated. Run: gh auth login")
        print(status.stderr)
        return 1

    ensure_labels()
    nums = list_all_issue_numbers()
    for n in nums:
        delete_issue(n)

    create_issues()

    print("\n=== Current open issues ===")
    r = run(
        ["issue", "list", "--repo", REPO, "--state", "open", "--limit", "50"],
        check=False,
    )
    print(r.stdout)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
