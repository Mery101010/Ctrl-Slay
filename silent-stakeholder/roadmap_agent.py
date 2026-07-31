"""
Roadmap Agent — normalizes GitHub issues and embeds them in the shared
vector space. Mostly extraction, not inference: the interesting judgment
calls happen in the Synchronizer, not here.

Also computes a simple "activity_score" per issue — used by the
Synchronizer to help distinguish UNDER-PRIORITIZED (issue exists but is
stale/unlabeled/low-activity) from properly-scoped work in progress.
"""

import numpy as np
from datetime import datetime
from schema import RoadmapItem, issue_matching_text


def _activity_score(issue: RoadmapItem) -> float:
    """
    0..1 score combining: has milestone, is open & recently updated,
    has engagement (comments). Crude but auditable — every input here
    is a raw GitHub field, nothing invented.
    """
    score = 0.0
    if issue.milestone:
        score += 0.4
    if issue.state == "open":
        score += 0.2
    updated = issue.updated_at.replace("Z", "+00:00")
    # Compare in naive UTC against "today" for activity freshness.
    updated_dt = datetime.fromisoformat(updated)
    if updated_dt.tzinfo is not None:
        updated_dt = updated_dt.replace(tzinfo=None)
    days_since_update = (datetime.utcnow() - updated_dt).days
    if days_since_update < 30:
        score += 0.2
    score += min(issue.comments / 20, 1.0) * 0.2
    return round(min(score, 1.0), 3)


def run(issues: list[RoadmapItem], vectorizer, svd):
    texts = [issue_matching_text(i) for i in issues]
    tfidf = vectorizer.transform(texts)
    X = svd.transform(tfidf)
    X = X / (np.linalg.norm(X, axis=1, keepdims=True) + 1e-9)

    enriched = []
    for issue, vec in zip(issues, X):
        enriched.append({
            "item": issue,
            "vector": vec,
            "activity_score": _activity_score(issue),
        })
    return enriched
