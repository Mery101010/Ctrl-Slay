"""
Shared data contracts between agents.

Every piece of evidence that flows through the system carries a stable `id`.
No downstream output is allowed to reference a claim without tracing back
to one or more of these ids. This is what makes the evidence trace real
instead of decorative.
"""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class FeedbackItem:
    """A single normalized review or support ticket."""
    id: str                # e.g. "review_0042" or "ticket_0017"
    source: str             # "review" | "ticket"
    text: str
    timestamp: str          # ISO date
    rating: Optional[float] = None   # 1-5 for reviews, None for tickets
    severity: Optional[str] = None   # "low"|"medium"|"high" for tickets
    raw_metadata: dict = field(default_factory=dict)


@dataclass
class RoadmapItem:
    """A single normalized GitHub issue."""
    id: str                 # e.g. "issue_412"
    number: int
    title: str
    body: str
    labels: list
    milestone: Optional[str]
    state: str               # "open" | "closed"
    created_at: str
    updated_at: str
    comments: int
    raw_metadata: dict = field(default_factory=dict)


# Process/workflow labels every issue in a milestone tends to share
# (e.g. "month-1", "phase-1", "enhancement", "bug"). These carry zero
# distinguishing signal for matching - if every issue has the same label,
# it can't help tell them apart, and including it just adds noise that
# can produce false-positive similarity matches (confirmed empirically:
# see README "Known limitations").
_BOILERPLATE_LABELS = {"month-1", "phase-1", "enhancement", "bug", "documentation"}


def issue_matching_text(issue: "RoadmapItem") -> str:
    """The ONE place issue text-for-matching is constructed. Used both when
    fitting the shared vector space and when embedding issues - keeping
    this in one function guarantees they never drift out of sync."""
    content_labels = [l for l in issue.labels if l not in _BOILERPLATE_LABELS]
    return f"{issue.title}. {' '.join(content_labels)}. {issue.body}"


@dataclass
class ThemeCluster:
    """Output of the Reviews/Tickets agent: a latent need extracted from feedback."""
    theme_id: str
    label: str                       # human-readable name of the need (LLM-assisted, grounded)
    evidence_ids: list               # FeedbackItem ids that support this theme
    size: int                        # number of items in the cluster
    cohesion: float                  # avg pairwise similarity within cluster (0-1)
    avg_rating: Optional[float]      # None if not applicable (tickets)
    recency_trend: float             # -1..1, negative = fading, positive = growing
    source: str                      # "review" | "ticket" | "mixed"
    centroid_vector: list = field(default_factory=list)  # not serialized to output, used internally


@dataclass
class GapResult:
    """Final output of the Synchronizer: one unmet need, fully justified."""
    need: str
    confidence: float                # 0-100, computed by formula, not guessed
    confidence_breakdown: dict        # component scores that fed the formula
    evidence_ids: list                # FeedbackItem ids
    verdict: str                      # "IGNORED" | "UNDER-PRIORITIZED" | "MISUNDERSTOOD"
    nearest_roadmap_item: Optional[str]   # RoadmapItem id, if any
    roadmap_similarity: float         # cosine similarity to nearest roadmap item
    reasoning: str                    # short grounded explanation
