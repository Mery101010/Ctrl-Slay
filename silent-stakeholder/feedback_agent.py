"""
Feedback Agent — one implementation, used for BOTH "reviews agent" and
"tickets agent" (parameterized by source). They do the same job: turn a
pile of noisy text into cohesive, evidence-linked latent-need clusters.

Pipeline within this agent:
  1. TF-IDF vectorize the text, then TruncatedSVD (LSA) to a dense
     lower-dim space. This does double duty: makes clustering tractable
     at real-world corpus sizes (10k-100k+ reviews), and smooths over
     some of raw TF-IDF's literal-keyword-only blindness by picking up
     co-occurring term structure.
  2. Cluster with KMeans (fixed k, full coverage - no density parameter
     to mistune, unlike DBSCAN/Agglomerative which failed badly on a
     real 21k-review corpus - see README for what we tried and why).
  3. Compute cohesion (avg pairwise similarity) per cluster and DROP any
     cluster below MIN_COHESION - this is the actual noise filter. A
     KMeans catch-all cluster with weak internal similarity is not a
     real pattern; we do not trust it enough to name a "need" from it.
  4. For each surviving cluster: compute size, cohesion, recency trend,
     avg rating, and name the theme (LLM step - grounded, stubbed here).

No cluster's "need" text is ever invented without size >= MIN_CLUSTER_SIZE
AND cohesion >= MIN_COHESION grounded evidence items backing it.
"""

import numpy as np
from datetime import datetime
from sklearn.cluster import KMeans
from sklearn.metrics.pairwise import cosine_similarity

from schema import FeedbackItem, ThemeCluster

MIN_CLUSTER_SIZE = 15         # below this, too few independent voices to trust
MIN_COHESION = 0.30           # below this, cluster is too internally scattered to trust
N_CLUSTERS = 40                # tune per corpus size; ~500 items/cluster is a reasonable start
# ^ On a real 21k-review corpus, DBSCAN and Agglomerative clustering (both
# density/linkage based) either found almost nothing or merged everything -
# TF-IDF's literal-keyword similarity is too sparse and unevenly distributed
# for those methods to find a good threshold. KMeans with a cohesion floor
# is more robust: it guarantees full coverage, and we simply refuse to
# trust (and therefore don't report) whichever clusters come out loose.


def _recency_trend(timestamps: list) -> float:
    """
    -1..1 score: are these items concentrated in the recent half of the
    time range, or the older half? Simple, auditable, no ML magic.
    """
    if len(timestamps) < 2:
        return 0.0
    dates = sorted(datetime.fromisoformat(t) for t in timestamps)
    midpoint = dates[0] + (dates[-1] - dates[0]) / 2
    recent = sum(1 for d in dates if d >= midpoint)
    older = len(dates) - recent
    total = recent + older
    return (recent - older) / total if total else 0.0


def _theme_label_stub(items: list, feature_names, tfidf_vectors) -> str:
    """
    STUB for the LLM call that names a theme from grounded excerpts.
    Real version: force a one-sentence output constrained to only the
    provided excerpts, e.g.:

        prompt = (
            "Here are grounded user excerpts and their top distinguishing "
            "keywords. In one sentence, describe the underlying need they "
            "share. Do not add anything not implied by these excerpts.\\n\\n"
            + "\\n---\\n".join(i.text for i in items[:15])
        )
        response = call_llm(prompt)

    This stub instead surfaces the top TF-IDF terms for the cluster as a
    keyword summary - crude, but unlike a hardcoded if/elif keyword list
    (the previous version of this stub), it generalizes to ANY corpus
    without being hand-tuned to one product's vocabulary.
    """
    mean_vec = tfidf_vectors.mean(axis=0)
    top_idx = np.argsort(mean_vec)[::-1][:6]
    top_terms = [feature_names[i] for i in top_idx if mean_vec[i] > 0]
    return f"[keyword summary - replace with real LLM naming call] {', '.join(top_terms)}"


def run(items: list[FeedbackItem], vectorizer, svd) -> list[ThemeCluster]:
    """
    `vectorizer` and `svd` must be fit ONCE on the combined corpus
    (reviews + roadmap issue text) - see embeddings.py. Fitting separately
    per-source would put reviews and issues in different vector spaces,
    making cross-source similarity meaningless.
    """
    if len(items) < MIN_CLUSTER_SIZE:
        return []

    texts = [i.text for i in items]
    tfidf = vectorizer.transform(texts)
    X = svd.transform(tfidf)
    X_norm = X / (np.linalg.norm(X, axis=1, keepdims=True) + 1e-9)

    k = min(N_CLUSTERS, len(items) // MIN_CLUSTER_SIZE) or 1
    km = KMeans(n_clusters=k, random_state=42, n_init=10)
    labels = km.fit_predict(X_norm)

    feature_names = vectorizer.get_feature_names_out()
    tfidf_dense = tfidf.toarray()

    themes = []
    for cluster_id in range(k):
        idxs = np.where(labels == cluster_id)[0]
        if len(idxs) < MIN_CLUSTER_SIZE:
            continue

        cluster_items = [items[i] for i in idxs]
        cluster_vecs = X_norm[idxs]

        # cohesion = avg pairwise cosine similarity within the cluster
        # (sample for speed on large clusters - doesn't change the estimate much)
        sample_idxs = idxs if len(idxs) <= 300 else np.random.RandomState(0).choice(idxs, 300, replace=False)
        sample_vecs = X_norm[sample_idxs]
        sim_matrix = cosine_similarity(sample_vecs)
        n = len(sample_idxs)
        cohesion = float((sim_matrix.sum() - n) / (n * (n - 1))) if n > 1 else 1.0

        if cohesion < MIN_COHESION:
            continue  # not trusted - too internally scattered to be a real pattern

        ratings = [it.rating for it in cluster_items if it.rating is not None]
        avg_rating = float(np.mean(ratings)) if ratings else None

        sources = set(it.source for it in cluster_items)
        source_label = sources.pop() if len(sources) == 1 else "mixed"

        themes.append(ThemeCluster(
            theme_id=f"theme_{cluster_id}_{source_label}",
            label=_theme_label_stub(cluster_items, feature_names, tfidf_dense[idxs]),
            evidence_ids=[it.id for it in cluster_items],
            size=len(cluster_items),
            cohesion=round(cohesion, 3),
            avg_rating=round(avg_rating, 2) if avg_rating is not None else None,
            recency_trend=round(_recency_trend([it.timestamp for it in cluster_items]), 3),
            source=source_label,
            centroid_vector=cluster_vecs.mean(axis=0).tolist(),
        ))

    # deterministic ordering for reproducibility
    themes.sort(key=lambda t: -t.size)
    return themes
