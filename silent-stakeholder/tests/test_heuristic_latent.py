import heuristic_latent as hl


def test_pack_fires_when_two_families_present():
    texts = [
        "There is a hidden fee on every transfer",
        "The fee is way more expensive than the competitor",
    ]
    result = hl.infer_need_from_texts(texts, surface_label="fee, charge, hidden")
    assert result["pack_id"] == "pricing_transparency"
    assert result["source"] == "heuristic_pack"
    assert "nickel-and-dimed" in result["latent_need"]


def test_pack_does_not_fire_on_single_family():
    # Only the "fee" family matches - pricing_transparency needs >=2 families.
    texts = ["There is a fee on every transfer"]
    result = hl.infer_need_from_texts(texts, surface_label="fee, transfer, charge")
    assert result["source"] == "heuristic_fallback"


def test_fallback_on_keyword_dump_label_is_generic_and_tagged():
    """
    Regression test: generic fallbacks must carry a shared pack_id so
    merge_by_pack can collapse duplicates instead of emitting the same
    filler "need" text as multiple separate gaps.
    """
    texts = ["The app is slow sometimes"]
    result = hl.infer_need_from_texts(texts, surface_label="slow, app, littl, keep, close, freez")
    assert result["source"] == "heuristic_fallback"
    assert result["pack_id"] == "generic_reliability_fallback"
    assert "recurring app friction" in result["latent_need"]


def test_fallback_on_empty_label_is_generic_and_tagged():
    texts = ["Nothing distinctive here"]
    result = hl.infer_need_from_texts(texts, surface_label="")
    assert result["pack_id"] == "generic_reliability_fallback"


def test_fallback_keeps_real_cleaned_label_without_pack_id():
    # A real (non keyword-dump) surface label should be used verbatim
    # and NOT tagged into the generic merge bucket.
    texts = ["Some review text with no pattern-pack signal"]
    label = "Users want a dark mode option for the app"
    result = hl.infer_need_from_texts(texts, surface_label=label)
    assert result["latent_need"] == label
    assert result["pack_id"] is None


def _theme(theme_id, pack_id, need, evidence_ids, size=10, recency=0.5):
    return {
        "theme_id": theme_id,
        "latent_need": need,
        "evidence_ids": evidence_ids,
        "cluster_size": size,
        "recency_score": recency,
        "centroid_vector": [0.1, 0.2],
        "pack_id": pack_id,
        "source": "heuristic_pack" if pack_id and pack_id != "generic_reliability_fallback" else "heuristic_fallback",
    }


def test_merge_by_pack_collapses_duplicate_generic_fallbacks():
    """
    Regression test for the top-5-gaps duplicate bug: three unrelated
    clusters that all fell back to the generic filler text must merge
    into ONE theme, not survive as three separate entries.
    """
    themes = [
        _theme("theme_0", "generic_reliability_fallback", "generic need", ["r1", "r2"], size=10),
        _theme("theme_1", "generic_reliability_fallback", "generic need", ["r3"], size=5),
        _theme("theme_2", "generic_reliability_fallback", "generic need", ["r4", "r5"], size=8),
    ]
    merged = hl.merge_by_pack(themes)
    assert len(merged) == 1
    assert set(merged[0]["evidence_ids"]) == {"r1", "r2", "r3", "r4", "r5"}
    assert merged[0]["cluster_size"] == 23


def test_merge_by_pack_keeps_distinct_real_packs_separate():
    themes = [
        _theme("theme_0", "pricing_transparency", "fee need", ["r1"]),
        _theme("theme_1", "kyc_friction", "kyc need", ["r2"]),
    ]
    merged = hl.merge_by_pack(themes)
    assert len(merged) == 2
    pack_ids = {t["pack_id"] for t in merged}
    assert pack_ids == {"pricing_transparency", "kyc_friction"}


def test_merge_by_pack_passes_through_standalone_themes():
    themes = [_theme("theme_0", None, "a unique real need", ["r1"])]
    merged = hl.merge_by_pack(themes)
    assert merged == themes
