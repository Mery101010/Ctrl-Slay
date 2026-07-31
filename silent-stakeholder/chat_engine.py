"""
Chat engine — answers judge-style questions grounded in gaps + evidence.
Uses free LLM when configured; otherwise deterministic grounded replies.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Optional

import llm
from config import GAPS_JSON, EVIDENCE_INDEX_JSON, PRODUCT_NAME, GITHUB_OWNER, GITHUB_REPO


def load_gaps() -> list[dict]:
    if not GAPS_JSON.exists():
        return []
    return json.loads(GAPS_JSON.read_text(encoding="utf-8"))


def load_evidence() -> dict:
    if not EVIDENCE_INDEX_JSON.exists():
        return {}
    return json.loads(EVIDENCE_INDEX_JSON.read_text(encoding="utf-8"))


def _gap_summary(gaps: list[dict]) -> str:
    lines = []
    for i, g in enumerate(gaps, 1):
        lines.append(
            f"#{i} [{g.get('verdict')}] conf={g.get('confidence')}% — {g.get('need')}\n"
            f"   nearest={g.get('nearest_roadmap_item')} sim={g.get('roadmap_similarity')}\n"
            f"   evidence_n={len(g.get('evidence_ids') or [])}\n"
            f"   reasoning={ (g.get('reasoning') or '')[:280]}"
        )
    return "\n".join(lines)


def _pick_gap(question: str, gaps: list[dict]) -> Optional[dict]:
    q = question.lower()
    m = re.search(r"#\s*(\d+)|gap\s*(\d+)|number\s*(\d+)", q)
    if m:
        n = int(next(g for g in m.groups() if g))
        if 1 <= n <= len(gaps):
            return gaps[n - 1]
    for i, g in enumerate(gaps, 1):
        need = (g.get("need") or "").lower()
        if any(w in need for w in q.split() if len(w) > 4):
            return g
    return gaps[0] if gaps else None


def _heuristic_answer(question: str, gaps: list[dict], evidence: dict) -> dict:
    q = question.lower()
    if not gaps:
        return {
            "reply": (
                "No gaps loaded yet. Click **Run analysis** or run "
                "`python main.py --sample 3000` first."
            ),
            "focus_rank": None,
            "evidence_ids": [],
            "provider": "heuristic",
        }

    if any(w in q for w in ("top", "list", "summary", "what are", "unmet", "gaps")):
        bullets = []
        for i, g in enumerate(gaps, 1):
            bullets.append(
                f"**#{i} · {g.get('confidence')}% · {g.get('verdict')}**\n"
                f"{g.get('need')}\n"
                f"_Nearest roadmap:_ `{g.get('nearest_roadmap_item')}` "
                f"(sim={g.get('roadmap_similarity')})"
            )
        return {
            "reply": (
                f"Here are the top {len(gaps)} unmet needs for **{PRODUCT_NAME}**, "
                f"ranked against [GitHub roadmap](https://github.com/{GITHUB_OWNER}/{GITHUB_REPO}):\n\n"
                + "\n\n".join(bullets)
            ),
            "focus_rank": 1,
            "evidence_ids": (gaps[0].get("evidence_ids") or [])[:8],
            "provider": "heuristic",
        }

    gap = _pick_gap(question, gaps)
    rank = gaps.index(gap) + 1
    eids = (gap.get("evidence_ids") or [])[:8]
    excerpts = []
    for eid in eids[:3]:
        item = evidence.get(eid)
        if item and item.get("text"):
            excerpts.append(f"- `{eid}`: \"{item['text'][:160]}…\"")

    bd = gap.get("confidence_breakdown") or {}
    reply = (
        f"**Gap #{rank}** is ranked here because confidence is "
        f"**{gap.get('confidence')}%** with verdict **{gap.get('verdict')}**.\n\n"
        f"**Need:** {gap.get('need')}\n\n"
        f"**Why this verdict:** {(gap.get('reasoning') or '')[:500]}\n\n"
        f"**Confidence breakdown:** volume={bd.get('volume')}, "
        f"recency={bd.get('recency')}, roadmap_gap={bd.get('roadmap_gap')}, "
        f"scope_alignment={bd.get('scope_alignment')}\n\n"
        f"**Nearest roadmap item:** `{gap.get('nearest_roadmap_item')}` "
        f"(similarity={gap.get('roadmap_similarity')})\n\n"
    )
    if excerpts:
        reply += "**Evidence excerpts:**\n" + "\n".join(excerpts)

    if "why" in q or "rank" in q or "confident" in q:
        reply += (
            "\n\nRank is by confidence formula (volume + recency + roadmap distance "
            "+ scope). Higher volume with weaker roadmap coverage rises."
        )

    return {
        "reply": reply,
        "focus_rank": rank,
        "evidence_ids": eids,
        "provider": "heuristic",
    }


def answer(question: str, history: Optional[list] = None) -> dict:
    gaps = load_gaps()
    evidence = load_evidence()
    history = history or []

    if not llm.available():
        return _heuristic_answer(question, gaps, evidence)

    # Build compact evidence snippets for the focused gap
    focus = _pick_gap(question, gaps) if gaps else None
    eids = (focus.get("evidence_ids") or [])[:6] if focus else []
    snippets = []
    for eid in eids:
        item = evidence.get(eid)
        if item and item.get("text"):
            snippets.append(f"{eid}: {item['text'][:180]}")

    system = (
        f"You are Silent Stakeholder, defending a gap analysis for {PRODUCT_NAME}. "
        "Answer only from the provided gaps and evidence. Cite evidence IDs. "
        "Be concise, direct, and honest about uncertainty. Use markdown sparingly."
    )
    hist_txt = "\n".join(
        f"{m.get('role','user').upper()}: {m.get('content','')}" for m in history[-6:]
    )
    prompt = f"""GAPS:
{_gap_summary(gaps)}

EVIDENCE SNIPPETS:
{chr(10).join(snippets) or '(none)'}

CHAT SO FAR:
{hist_txt or '(none)'}

USER QUESTION:
{question}

Answer the question. If asking about a specific gap, defend the ranking with
confidence breakdown + evidence IDs + nearest roadmap item.
"""
    try:
        resp = llm.complete(prompt, system=system, max_tokens=700)
        rank = gaps.index(focus) + 1 if focus else None
        return {
            "reply": resp.text,
            "focus_rank": rank,
            "evidence_ids": eids,
            "provider": resp.provider,
            "model": resp.model,
        }
    except Exception as e:
        fallback = _heuristic_answer(question, gaps, evidence)
        fallback["reply"] = (
            f"_(LLM call failed: {e} — falling back to grounded heuristic)_\n\n"
            + fallback["reply"]
        )
        return fallback
