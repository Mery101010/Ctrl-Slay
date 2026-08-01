import chat_engine as ce
from config import GITHUB_OWNER, GITHUB_REPO


# ---------- _issue_link ----------

def test_issue_link_builds_github_url():
    link = ce._issue_link("issue_4")
    assert link == f"[issue_4](https://github.com/{GITHUB_OWNER}/{GITHUB_REPO}/issues/4)"


def test_issue_link_none_returns_none_text():
    assert ce._issue_link(None) == "none"


def test_issue_link_non_issue_id_falls_back_to_code_span():
    assert ce._issue_link("weird_id") == "`weird_id`"


# ---------- _pick_gap ----------

def _gap(need, evidence_ids=None):
    return {"need": need, "evidence_ids": evidence_ids or []}


def test_pick_gap_by_hash_number():
    gaps = [_gap("fees"), _gap("kyc"), _gap("crashes")]
    assert ce._pick_gap("why is #2 ranked there", gaps) is gaps[1]


def test_pick_gap_by_gap_number_word():
    gaps = [_gap("fees"), _gap("kyc")]
    assert ce._pick_gap("show evidence for gap 2", gaps) is gaps[1]


def test_pick_gap_by_keyword_match():
    gaps = [_gap("Users hate hidden fees"), _gap("Users want dark mode")]
    assert ce._pick_gap("tell me about fees", gaps) is gaps[0]


def test_pick_gap_defaults_to_first_when_no_match():
    gaps = [_gap("fees"), _gap("kyc")]
    assert ce._pick_gap("hello there", gaps) is gaps[0]


def test_pick_gap_empty_list_returns_none():
    assert ce._pick_gap("anything", []) is None


# ---------- _looks_truncated ----------

def test_looks_truncated_empty_string():
    assert ce._looks_truncated("") is True


def test_looks_truncated_ends_mid_markdown():
    assert ce._looks_truncated("Here is the answer **" ) is True


def test_looks_truncated_short_without_punctuation():
    assert ce._looks_truncated("short answer") is True


def test_looks_truncated_complete_sentence_is_false():
    text = (
        "This is a complete, sufficiently long answer that ends with proper "
        "punctuation so it should not be flagged as truncated."
    )
    assert ce._looks_truncated(text) is False


# ---------- _heuristic_answer ----------

def test_heuristic_answer_no_gaps_prompts_to_run_analysis():
    result = ce._heuristic_answer("what are the top needs?", [], {})
    assert "Run analysis" in result["reply"]
    assert result["focus_rank"] is None


def test_heuristic_answer_list_question_includes_all_gaps_and_links():
    gaps = [
        {"need": "Fee transparency", "confidence": 60.0, "verdict": "UNDER-PRIORITIZED",
         "nearest_roadmap_item": "issue_8", "roadmap_similarity": 0.2, "evidence_ids": ["r1"]},
        {"need": "Reliable status", "confidence": 55.0, "verdict": "IGNORED",
         "nearest_roadmap_item": "issue_4", "roadmap_similarity": 0.1, "evidence_ids": ["r2"]},
    ]
    result = ce._heuristic_answer("What are the top unmet needs?", gaps, {})
    assert "Fee transparency" in result["reply"]
    assert "Reliable status" in result["reply"]
    assert f"https://github.com/{GITHUB_OWNER}/{GITHUB_REPO}/issues/8" in result["reply"]
    assert f"https://github.com/{GITHUB_OWNER}/{GITHUB_REPO}/issues/4" in result["reply"]


def test_heuristic_answer_single_gap_question_includes_breakdown():
    gaps = [{
        "need": "Fee transparency",
        "confidence": 60.0,
        "verdict": "UNDER-PRIORITIZED",
        "nearest_roadmap_item": "issue_8",
        "roadmap_similarity": 0.2,
        "evidence_ids": ["r1"],
        "reasoning": "because reasons",
        "confidence_breakdown": {"volume": 0.5, "recency": 0.5, "roadmap_gap": 0.5, "scope_alignment": 0.0},
    }]
    evidence = {"r1": {"text": "This app has hidden fees everywhere"}}
    result = ce._heuristic_answer("why is #1 ranked first?", gaps, evidence)
    assert "Gap #1" in result["reply"]
    assert "hidden fees" in result["reply"]
    assert result["focus_rank"] == 1
