"""
Scope checking via free LLM when available; keyword/heuristic fallback otherwise.
"""

from __future__ import annotations

import re

import llm


def check_scope_alignment(
    latent_need: str,
    evidence_ids: list,
    evidence_texts: list,
    issue_title: str,
    issue_body: str,
    issue_number: int,
    client=None,
) -> dict:
    evidence_excerpt = "\n".join(f"- {text[:150]}" for text in evidence_texts[:5])

    if llm.available():
        prompt = f"""Does this GitHub issue address the user need?

USER NEED: {latent_need}

Sample evidence ({len(evidence_ids)} reviews):
{evidence_excerpt}

ISSUE #{issue_number}: {issue_title}
{issue_body[:800]}

Return ONLY JSON:
{{
  "matches_scope": true/false,
  "scope_type": "full" | "partial" | "tangential" | "none",
  "reasoning": "2-3 sentences",
  "gap_analysis": "what's missing if partial",
  "verdict": "what would fully solve it"
}}"""
        try:
            resp = llm.complete(prompt, max_tokens=400)
            result = llm.parse_json_object(resp.text)
            return {
                "matches_scope": bool(result.get("matches_scope", False)),
                "scope_type": result.get("scope_type", "none"),
                "reasoning": result.get("reasoning", ""),
                "gap_analysis": result.get("gap_analysis", ""),
                "verdict": result.get("verdict", ""),
                "source": f"llm:{resp.provider}",
            }
        except Exception as e:
            print(f"  Scope LLM failed: {e} — heuristic fallback")

    return _heuristic_scope(latent_need, issue_title, issue_body)


def _heuristic_scope(latent_need: str, issue_title: str, issue_body: str) -> dict:
    need = latent_need.lower()
    issue = f"{issue_title}\n{issue_body}".lower()

    topic_map = {
        "fee": ["fee", "pricing", "cost", "transparent"],
        "kyc": ["kyc", "verif", "document", "identity", "scan"],
        "support": ["chat", "support", "agent", "diagnostic", "delay"],
        "login": ["login", "account-link", "account linking", "cross-border"],
        "crash": ["crash", "freeze", "android", "reliab"],
        "status": ["status", "tracker", "pending", "delay", "diagnostic"],
        "ads": ["ad", "upsell", "promo"],
        "reward": ["reward", "point", "loyalty"],
    }

    need_topics = {k for k, words in topic_map.items() if any(w in need for w in words)}
    issue_topics = {k for k, words in topic_map.items() if any(w in issue for w in words)}
    overlap = need_topics & issue_topics

    if not overlap:
        return {
            "matches_scope": False,
            "scope_type": "none",
            "reasoning": "No shared topic families between latent need and issue text.",
            "gap_analysis": "Roadmap item appears unrelated to this need.",
            "verdict": "Add or expand an issue that targets this need directly.",
            "source": "heuristic_scope",
        }

    # Token overlap as a rough partial/full signal
    need_tokens = set(re.findall(r"[a-z]{4,}", need))
    issue_tokens = set(re.findall(r"[a-z]{4,}", issue))
    jacc = len(need_tokens & issue_tokens) / max(len(need_tokens | issue_tokens), 1)

    if jacc >= 0.12 and len(overlap) >= 1:
        return {
            "matches_scope": True,
            "scope_type": "partial",
            "reasoning": (
                f"Shared topics {sorted(overlap)}; lexical overlap={jacc:.2f}. "
                "Issue is related but may not cover the full latent need."
            ),
            "gap_analysis": "Confirm acceptance criteria cover the latent need statement.",
            "verdict": "Expand issue scope or add a sibling issue for the uncovered part.",
            "source": "heuristic_scope",
        }

    return {
        "matches_scope": False,
        "scope_type": "tangential",
        "reasoning": f"Weak topical overlap only ({sorted(overlap)}).",
        "gap_analysis": "Issue touches a related area but not the core need.",
        "verdict": "Reframe or split the issue to match what users actually need.",
        "source": "heuristic_scope",
    }
