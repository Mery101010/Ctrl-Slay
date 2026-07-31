"""
Latent Need Inference — LLM when available (Groq/Gemini/Ollama free),
else heuristic pattern packs (zero keys).
"""

from __future__ import annotations

import llm
import heuristic_latent
from schema import ThemeCluster


def infer_latent_needs(themes: list[ThemeCluster], reviews: dict, client=None) -> list[dict]:
    """
    `client` is ignored (legacy). Uses llm.complete() when a free/paid
    provider is configured; otherwise heuristic packs.
    """
    use_llm = llm.available()
    results = []

    for theme in themes:
        sample_ids = theme.evidence_ids[:15]
        sample_reviews = [reviews[rid] for rid in sample_ids if rid in reviews]
        if not sample_reviews:
            continue

        texts = [r.text for r in sample_reviews]
        base = {
            "theme_id": theme.theme_id,
            "surface_label": theme.label,
            "evidence_ids": theme.evidence_ids,
            "cluster_size": theme.size,
            "confidence_base": theme.cohesion,
            "centroid_vector": theme.centroid_vector,
            "recency_score": (theme.recency_trend + 1) / 2,
        }

        if use_llm:
            excerpts = "\n".join(
                f'{i+1}. "{r.text[:200]}"' for i, r in enumerate(sample_reviews)
            )
            prompt = f"""You are reading user reviews from a mobile money-transfer app.
These reviews form a cluster around this theme: {theme.label}

Here are {len(sample_reviews)} representative excerpts:

{excerpts}

Identify the LATENT need — the underlying problem users share that they
DIDN'T say explicitly. Return ONLY JSON:
{{
  "latent_need": "1-2 sentence underlying need",
  "why_latent": "why this is latent",
  "evidence_pattern": "pattern in the excerpts"
}}"""
            try:
                resp = llm.complete(prompt, max_tokens=300)
                inference = llm.parse_json_object(resp.text)
                results.append(
                    {
                        **base,
                        "latent_need": inference.get("latent_need", theme.label),
                        "why_latent": inference.get("why_latent", ""),
                        "evidence_pattern": inference.get("evidence_pattern", ""),
                        "source": f"llm:{resp.provider}",
                    }
                )
                continue
            except Exception as e:
                print(f"  LLM infer failed for {theme.theme_id}: {e} — using heuristics")

        h = heuristic_latent.infer_need_from_texts(texts, theme.label)
        results.append({**base, **h})

    return results


def merge_related_themes(inferred_themes: list[dict], client=None) -> list[dict]:
    if len(inferred_themes) <= 1:
        return inferred_themes

    # Prefer pack merge when heuristics produced pack_ids
    if any(t.get("pack_id") for t in inferred_themes) and not llm.available():
        return heuristic_latent.merge_by_pack(inferred_themes)

    if not llm.available():
        return heuristic_latent.merge_by_pack(inferred_themes)

    clusters_summary = "\n".join(
        f"{i+1}. {t['theme_id']} (n={t['cluster_size']}): {t['latent_need']}"
        for i, t in enumerate(inferred_themes)
    )
    prompt = f"""Analyze latent needs from a money-transfer app. Identify which
clusters are the SAME underlying need from different angles.

{clusters_summary}

Return ONLY JSON:
{{
  "merge_groups": [
    {{"group_name": "unified need", "theme_ids": ["theme_X"], "reasoning": "why"}}
  ],
  "standalone": ["theme_ids that stand alone"]
}}"""
    try:
        resp = llm.complete(prompt, max_tokens=600)
        merge_plan = llm.parse_json_object(resp.text)
    except Exception as e:
        print(f"Warning: LLM merge failed ({e}); using heuristic pack merge")
        return heuristic_latent.merge_by_pack(inferred_themes)

    import numpy as np

    merged_results = []
    processed = set()
    for group in merge_plan.get("merge_groups", []):
        theme_ids = group.get("theme_ids") or []
        if len(theme_ids) < 2:
            continue
        combined_evidence = []
        combined_size = 0
        source_vecs = []
        for theme_id in theme_ids:
            for t in inferred_themes:
                if t["theme_id"] == theme_id:
                    combined_evidence.extend(t["evidence_ids"])
                    combined_size += t["cluster_size"]
                    processed.add(theme_id)
                    if t.get("centroid_vector") is not None:
                        source_vecs.append(t["centroid_vector"])
                    break
        centroid = np.mean(source_vecs, axis=0).tolist() if source_vecs else None
        avg_recency = float(
            np.mean(
                [t.get("recency_score", 0.5) for t in inferred_themes if t["theme_id"] in theme_ids]
            )
        )
        merged_results.append(
            {
                "theme_id": f"merged_{len(merged_results)}",
                "latent_need": group.get("group_name", ""),
                "why_latent": "Merged from multiple clusters",
                "evidence_pattern": group.get("reasoning", ""),
                "evidence_ids": list(dict.fromkeys(combined_evidence)),
                "cluster_size": combined_size,
                "source_themes": theme_ids,
                "centroid_vector": centroid,
                "recency_score": avg_recency,
                "confidence_base": 0.0,
                "source": f"llm_merge:{resp.provider}",
            }
        )

    for t in inferred_themes:
        if t["theme_id"] not in processed:
            merged_results.append(t)
    return merged_results
