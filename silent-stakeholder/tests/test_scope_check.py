from scope_check import _heuristic_scope


def test_no_shared_topic_returns_none_scope():
    result = _heuristic_scope(
        latent_need="Users want a dark mode theme option",
        issue_title="Improve app icon and splash screen branding",
        issue_body="Update the app icon and add a splash screen animation",
    )
    assert result["matches_scope"] is False
    assert result["scope_type"] == "none"


def test_shared_topic_with_high_overlap_is_partial_match():
    result = _heuristic_scope(
        latent_need="Users feel nickel-and-dimed by opaque transfer fees and pricing",
        issue_title="Transparent fee pricing breakdown",
        issue_body="Show transparent fee pricing breakdown before every transfer",
    )
    assert result["matches_scope"] is True
    assert result["scope_type"] == "partial"


def test_shared_topic_with_low_overlap_is_tangential_or_none():
    result = _heuristic_scope(
        latent_need="Users feel nickel-and-dimed by opaque fees",
        issue_title="Reward points program",
        issue_body="Add a loyalty reward points system with cashback",
    )
    assert result["matches_scope"] is False
    assert result["scope_type"] == "none"
