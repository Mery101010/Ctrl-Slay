import numpy as np
import pytest

import synchronizer as sync
from schema import RoadmapItem


# ---------- pure helpers ----------

def test_normalize_volume_caps_at_one():
    assert sync._normalize_volume(50, 10) == 1.0


def test_normalize_volume_zero_max_is_zero():
    assert sync._normalize_volume(5, 0) == 0.0


def test_normalize_volume_scales_linearly():
    assert sync._normalize_volume(5, 10) == 0.5


class _Review:
    def __init__(self, raw_metadata=None):
        self.raw_metadata = raw_metadata or {}


def test_helpful_count_missing_metadata_is_zero():
    assert sync._helpful_count(_Review()) == 0


def test_helpful_count_reads_metadata():
    assert sync._helpful_count(_Review({"helpful_count": 12})) == 12


def test_helpful_count_negative_clamped_to_zero():
    assert sync._helpful_count(_Review({"helpful_count": -3})) == 0


def test_helpful_count_non_numeric_is_zero():
    assert sync._helpful_count(_Review({"helpful_count": "lots"})) == 0


def test_evidence_mass_empty_is_zero():
    assert sync._evidence_mass([], {}) == 0.0


def test_evidence_mass_without_reviews_counts_ids():
    assert sync._evidence_mass(["a", "b", "c"], None) == 3.0


def test_evidence_mass_weights_by_upvotes():
    reviews = {"a": _Review({"helpful_count": 0}), "b": _Review({"helpful_count": 10})}
    mass = sync._evidence_mass(["a", "b"], reviews)
    expected = (1.0 + np.log1p(0)) + (1.0 + np.log1p(10))
    assert mass == pytest.approx(expected)


# ---------- _classify_verdict ----------

def test_classify_verdict_ignored_below_threshold():
    verdict, reasoning = sync._classify_verdict(0.05, 1.0, {"matches_scope": False, "scope_type": "none"})
    assert verdict == "IGNORED"


def test_classify_verdict_under_prioritized_weak_match():
    verdict, _ = sync._classify_verdict(0.25, 1.0, {"matches_scope": False, "scope_type": "none"})
    assert verdict == "UNDER-PRIORITIZED"


def test_classify_verdict_under_prioritized_low_activity():
    verdict, _ = sync._classify_verdict(0.9, 0.1, {"matches_scope": False, "scope_type": "none"})
    assert verdict == "UNDER-PRIORITIZED"


def test_classify_verdict_full_scope_match_is_not_a_gap():
    verdict, reasoning = sync._classify_verdict(
        0.9, 1.0, {"matches_scope": True, "scope_type": "full"}
    )
    assert verdict is None


def test_classify_verdict_partial_scope_is_under_prioritized():
    verdict, _ = sync._classify_verdict(
        0.9, 1.0, {"matches_scope": True, "scope_type": "partial", "gap_analysis": "x"}
    )
    assert verdict == "UNDER-PRIORITIZED"


def test_classify_verdict_scope_mismatch_is_misunderstood():
    verdict, _ = sync._classify_verdict(
        0.9, 1.0, {"matches_scope": False, "scope_type": "tangential", "reasoning": "x", "verdict": "y"}
    )
    assert verdict == "MISUNDERSTOOD"


# ---------- run() integration ----------

def _issue(id_, number, vector, activity_score=1.0, title="Issue", body="Body"):
    item = RoadmapItem(
        id=id_,
        number=number,
        title=title,
        body=body,
        labels=[],
        milestone=None,
        state="open",
        created_at="2026-01-01T00:00:00",
        updated_at="2026-01-01T00:00:00",
        comments=0,
    )
    return {"item": item, "vector": np.array(vector, dtype=float), "activity_score": activity_score}


def _theme(evidence_ids, recency_score, centroid_vector, need="Some latent need"):
    return {
        "theme_id": "theme_x",
        "latent_need": need,
        "evidence_ids": evidence_ids,
        "recency_score": recency_score,
        "centroid_vector": centroid_vector,
    }


def test_run_returns_empty_for_no_themes():
    assert sync.run([], [{"item": None, "vector": np.array([1.0]), "activity_score": 1.0}]) == []


def test_run_renormalizes_confidence_when_scope_not_applicable():
    """
    Regression test: when the nearest roadmap item is a weak/no match,
    scope_alignment never applies (scope_type stays "none"). The
    confidence weight for that inapplicable factor must be redistributed
    across the remaining signals instead of silently capping confidence
    at 75% (0.25+0.15+0.35 of the original weights).
    """
    theme = _theme(evidence_ids=["r1", "r2", "r3"], recency_score=1.0, centroid_vector=[1.0, 0.0])
    roadmap = [_issue("issue_9", 9, vector=[0.0, 1.0], activity_score=1.0)]

    [gap] = sync.run([theme], roadmap, reviews_by_id=None, client=None)

    assert gap.verdict == "IGNORED"
    assert gap.confidence_breakdown["scope_type"] == "none"
    assert "scope_alignment" not in gap.confidence_breakdown["active_weights"]
    assert sum(gap.confidence_breakdown["active_weights"].values()) == pytest.approx(1.0)
    # With the old (un-renormalized) formula this scenario would be capped
    # at 75.0; the fixed formula must be able to exceed that ceiling.
    assert gap.confidence > 75.0
    assert gap.confidence == pytest.approx(77.8, abs=0.1)


def test_run_filters_out_fully_addressed_gap(monkeypatch):
    theme = _theme(evidence_ids=["r1"], recency_score=0.5, centroid_vector=[1.0, 0.0])
    roadmap = [_issue("issue_1", 1, vector=[1.0, 0.0], activity_score=1.0)]

    monkeypatch.setattr(
        sync.scope_check,
        "check_scope_alignment",
        lambda **kwargs: {"matches_scope": True, "scope_type": "full", "reasoning": ""},
    )

    results = sync.run([theme], roadmap, reviews_by_id=None, client=True)
    assert results == []


def test_run_partial_scope_match_includes_scope_alignment_weight(monkeypatch):
    theme = _theme(evidence_ids=["r1"], recency_score=0.5, centroid_vector=[1.0, 0.0])
    roadmap = [_issue("issue_1", 1, vector=[1.0, 0.0], activity_score=1.0)]

    monkeypatch.setattr(
        sync.scope_check,
        "check_scope_alignment",
        lambda **kwargs: {
            "matches_scope": True,
            "scope_type": "partial",
            "reasoning": "partial",
            "gap_analysis": "missing X",
        },
    )

    [gap] = sync.run([theme], roadmap, reviews_by_id=None, client=True)
    assert gap.verdict == "UNDER-PRIORITIZED"
    assert "scope_alignment" in gap.confidence_breakdown["active_weights"]
    assert gap.confidence_breakdown["scope_alignment"] == 1.0


def test_run_sorts_results_by_confidence_descending():
    high_conf_theme = _theme(evidence_ids=["r1", "r2", "r3", "r4"], recency_score=1.0, centroid_vector=[1.0, 0.0])
    low_conf_theme = _theme(evidence_ids=["r5"], recency_score=0.0, centroid_vector=[1.0, 0.0])
    roadmap = [_issue("issue_9", 9, vector=[0.0, 1.0], activity_score=1.0)]

    results = sync.run([low_conf_theme, high_conf_theme], roadmap, reviews_by_id=None, client=None)

    assert len(results) == 2
    assert results[0].confidence >= results[1].confidence
