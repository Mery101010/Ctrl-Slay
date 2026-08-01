from schema import RoadmapItem, issue_matching_text


def _issue(title="", body="", labels=None):
    return RoadmapItem(
        id="issue_1",
        number=1,
        title=title,
        body=body,
        labels=labels or [],
        milestone=None,
        state="open",
        created_at="2026-01-01T00:00:00",
        updated_at="2026-01-01T00:00:00",
        comments=0,
    )


def test_issue_matching_text_includes_title_and_body():
    issue = _issue(title="Add fee breakdown", body="Show all-in pricing upfront")
    text = issue_matching_text(issue)
    assert "Add fee breakdown" in text
    assert "Show all-in pricing upfront" in text


def test_issue_matching_text_drops_boilerplate_labels():
    issue = _issue(title="T", body="B", labels=["month-1", "phase-1", "enhancement", "bug", "documentation"])
    text = issue_matching_text(issue)
    for boilerplate in ("month-1", "phase-1", "enhancement", "bug", "documentation"):
        assert boilerplate not in text


def test_issue_matching_text_keeps_content_labels():
    issue = _issue(title="T", body="B", labels=["month-1", "kyc", "pricing"])
    text = issue_matching_text(issue)
    assert "kyc" in text
    assert "pricing" in text
    assert "month-1" not in text
