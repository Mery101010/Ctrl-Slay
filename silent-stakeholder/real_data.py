"""
Real data loader — Western Union Mobile App.

Reviews: reviews.csv (local) or Ctrl-Slay twin at
  Desktop/Ctrl-Slay/data/csv/app_id_1/reviews.csv

Roadmap: live GitHub issues from
  https://github.com/Mery101010/Western-Union-Mobile-App-Draft
"""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import pandas as pd
import requests

from schema import FeedbackItem, RoadmapItem

ROOT = Path(__file__).resolve().parent
GITHUB_OWNER = "Mery101010"
GITHUB_REPO = "Western-Union-Mobile-App-Draft"
ROADMAP_CACHE_JSON = ROOT / "roadmap_cache.json"

_REPO_REVIEWS = ROOT.parent / "data" / "csv" / "app_id_1" / "reviews.csv"
REVIEWS_CSV = (ROOT / "reviews.csv") if (ROOT / "reviews.csv").exists() else _REPO_REVIEWS


def get_reviews(csv_path=None, sample_n=None):
    path = Path(csv_path) if csv_path else REVIEWS_CSV
    df = pd.read_csv(path)
    if sample_n:
        df = df.sample(n=min(sample_n, len(df)), random_state=42).reset_index(drop=True)

    items = []
    for _, row in df.iterrows():
        items.append(
            FeedbackItem(
                id=str(row["signal_id"]),
                source="review",
                text=str(row["review_text"]),
                timestamp=str(row["review_date"]),
                rating=float(row["review_score"]),
                raw_metadata={"helpful_count": int(row["helpful_count"])},
            )
        )
    return items


def _auth_headers() -> dict:
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if not token:
        try:
            r = subprocess.run(
                ["gh", "auth", "token"],
                capture_output=True,
                text=True,
                check=False,
                timeout=10,
            )
            if r.returncode == 0 and r.stdout.strip():
                token = r.stdout.strip()
        except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
            token = None
    if not token:
        return {"Accept": "application/vnd.github+json"}
    return {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {token}",
    }


def _issues_from_api_payload(data: list) -> list[RoadmapItem]:
    items = []
    for item in data:
        if "pull_request" in item:
            continue
        milestone = item["milestone"]["title"] if item.get("milestone") else None
        items.append(
            RoadmapItem(
                id=f"issue_{item['number']}",
                number=item["number"],
                title=item["title"],
                body=item.get("body") or "",
                labels=[lab["name"] for lab in item.get("labels", [])],
                milestone=milestone,
                state=item["state"],
                created_at=item["created_at"],
                updated_at=item["updated_at"],
                comments=item.get("comments", 0),
                raw_metadata={
                    "html_url": item.get("html_url"),
                    "source": f"github:{GITHUB_OWNER}/{GITHUB_REPO}",
                },
            )
        )
    return items


def _cache_issues(issues: list[RoadmapItem]) -> None:
    payload = [
        {
            "number": i.number,
            "title": i.title,
            "body": i.body,
            "labels": i.labels,
            "milestone": i.milestone,
            "state": i.state,
            "created_at": i.created_at,
            "updated_at": i.updated_at,
            "comments": i.comments,
        }
        for i in issues
    ]
    ROADMAP_CACHE_JSON.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _issues_from_cache() -> list[RoadmapItem] | None:
    if not ROADMAP_CACHE_JSON.exists():
        return None
    data = json.loads(ROADMAP_CACHE_JSON.read_text(encoding="utf-8"))
    return [
        RoadmapItem(
            id=f"issue_{item['number']}",
            number=item["number"],
            title=item["title"],
            body=item.get("body") or "",
            labels=item.get("labels") or [],
            milestone=item.get("milestone"),
            state=item.get("state", "open"),
            created_at=item.get("created_at", ""),
            updated_at=item.get("updated_at", ""),
            comments=int(item.get("comments") or 0),
            raw_metadata={"source": "roadmap_cache.json"},
        )
        for item in data
    ]


def fetch_github_issues_live(
    owner: str = GITHUB_OWNER,
    repo: str = GITHUB_REPO,
    token: str | None = None,
) -> list[RoadmapItem]:
    """Pull open+closed issues (excluding PRs) from the GitHub REST API."""
    headers = _auth_headers()
    if token:
        headers["Authorization"] = f"Bearer {token}"

    url = f"https://api.github.com/repos/{owner}/{repo}/issues"
    params = {"state": "all", "per_page": 100}
    resp = requests.get(url, headers=headers, params=params, timeout=30)
    resp.raise_for_status()
    return _issues_from_api_payload(resp.json())


def get_roadmap_issues() -> list[RoadmapItem]:
    """
    Load roadmap from live GitHub issues on
    Mery101010/Western-Union-Mobile-App-Draft.

    Order: live API → roadmap_cache.json → raise (no silent stub roadmap).
    """
    try:
        issues = fetch_github_issues_live()
        if issues:
            _cache_issues(issues)
            print(
                f"Loaded {len(issues)} roadmap issues from "
                f"github.com/{GITHUB_OWNER}/{GITHUB_REPO}"
            )
            return issues
    except Exception as exc:  # noqa: BLE001 — fall through to cache
        print(f"GitHub live fetch failed ({exc}); trying roadmap_cache.json")

    cached = _issues_from_cache()
    if cached:
        print(f"Loaded {len(cached)} roadmap issues from {ROADMAP_CACHE_JSON.name}")
        return cached

    raise RuntimeError(
        "Could not load roadmap issues from GitHub or roadmap_cache.json. "
        f"Set GITHUB_TOKEN or run `gh auth login`, then retry. "
        f"Expected repo: https://github.com/{GITHUB_OWNER}/{GITHUB_REPO}"
    )
