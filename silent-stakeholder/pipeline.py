"""
End-to-end analysis: reviews + live GitHub roadmap -> top N gaps + evidence index.
Works with free LLMs (Groq/Gemini/Ollama) or offline heuristics.
"""

from __future__ import annotations

import dataclasses
import json
from typing import Optional

from embeddings import fit_shared_space
import feedback_agent
import roadmap_agent
import synchronizer
import latent_inference
import llm
from schema import issue_matching_text
from config import GAPS_JSON, EVIDENCE_INDEX_JSON, TOP_N_GAPS, PRODUCT_NAME


def run_analysis(sample_n: Optional[int] = None, top_n: int = TOP_N_GAPS) -> list:
    import real_data as data_source

    provider = llm.active_provider()
    print(f"LLM backend: {provider['label']} ({provider['model']})")

    all_reviews = data_source.get_reviews(sample_n=sample_n)
    issues = data_source.get_roadmap_issues()

    reviews = [r for r in all_reviews if r.rating is None or r.rating <= 3]
    print(
        f"Filtered {len(all_reviews)} reviews -> {len(reviews)} rating<=3 "
        f"| {len(issues)} GitHub issues"
    )

    all_texts = [r.text for r in reviews] + [issue_matching_text(i) for i in issues]
    vectorizer, svd = fit_shared_space(all_texts)

    review_themes = feedback_agent.run(reviews, vectorizer, svd)
    print(f"Themes: {len(review_themes)}")

    roadmap_enriched = roadmap_agent.run(issues, vectorizer, svd)
    reviews_by_id = {r.id: r for r in reviews}

    print("=== LATENT INFERENCE ===")
    inferred = latent_inference.infer_latent_needs(review_themes, reviews_by_id)
    print(f"Inferred: {len(inferred)}")

    print("=== MERGE ===")
    merged = latent_inference.merge_related_themes(inferred)
    print(f"After merge: {len(merged)}")

    gaps = synchronizer.run(merged, roadmap_enriched, reviews_by_id, client=True)
    # Drop leftover keyword-stub / comma-dump labels if any slipped through
    def _is_real_need(text: str) -> bool:
        if not text:
            return False
        if text.startswith("[keyword summary"):
            return False
        if "replace with real LLM" in text:
            return False
        # keyword dumps look like: "slow, app slow, app, littl"
        if text.count(",") >= 2 and len(text.split()) <= 14 and "Users " not in text:
            return False
        return True

    gaps = [g for g in gaps if _is_real_need(g.need)]
    # Allow a deeper ranked list (default 12); brief still highlights top 3–5.
    gaps = gaps[: max(3, min(20, top_n))]

    payload = [dataclasses.asdict(g) for g in gaps]
    for i, g in enumerate(payload, 1):
        g["rank"] = i
        g["product"] = PRODUCT_NAME

    GAPS_JSON.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    # Compact evidence index for chat drawer
    index = {}
    for g in gaps:
        for eid in g.evidence_ids[:40]:
            if eid in reviews_by_id and eid not in index:
                r = reviews_by_id[eid]
                upvotes = int((r.raw_metadata or {}).get("helpful_count") or 0)
                index[eid] = {
                    "id": eid,
                    "text": r.text[:500],
                    "rating": r.rating,
                    "date": r.timestamp,
                    "upvotes": upvotes,
                    "label": f"Play Store review #{eid.rsplit('_', 1)[-1]}",
                }
    # also index roadmap issues referenced
    issue_by_id = {i.id: i for i in issues}
    for g in gaps:
        nid = g.nearest_roadmap_item
        if nid and nid in issue_by_id:
            issue = issue_by_id[nid]
            index[nid] = {
                "id": nid,
                "title": issue.title,
                "body": (issue.body or "")[:800],
                "number": issue.number,
                "labels": issue.labels,
                "state": issue.state,
                "url": f"https://github.com/{data_source.GITHUB_OWNER}/{data_source.GITHUB_REPO}/issues/{issue.number}",
            }

    EVIDENCE_INDEX_JSON.write_text(json.dumps(index, indent=2), encoding="utf-8")
    print(f"Saved top {len(gaps)} gaps -> {GAPS_JSON.name}")
    print(f"Saved evidence index ({len(index)} items) -> {EVIDENCE_INDEX_JSON.name}")
    return gaps
