"""
Heuristic latent-need inference — works with zero API keys.

Scores second-order PATTERN packs (multi-signal co-occurrence). A pack
fires only when ≥2 distinct signal families appear across the cluster.
"""

from __future__ import annotations

import re
from typing import Any

LATENT_PACKS = [
    {
        "id": "pricing_transparency",
        "need": (
            "Users feel nickel-and-dimed by opaque fees and want upfront, "
            "all-in pricing so they can compare options before sending."
        ),
        "families": {
            "fee": [r"\bfee\b", r"\bfees\b", r"\bcharge\b", r"\bcharges\b"],
            "hidden": [r"hidden", r"extra cost", r"surprise", r"didn't tell"],
            "compare": [r"cheaper", r"competitor", r"\bwise\b", r"remitly", r"compare"],
            "expensive": [r"expensive", r"too much", r"ripoff", r"rip.?off", r"overcharg"],
        },
    },
    {
        "id": "transfer_certainty",
        "need": (
            "Users need reliable transfer-status certainty — when money moves, "
            "why it stalls, and what happens next — not just a generic pending state."
        ),
        "families": {
            "delay": [r"delay", r"pending", r"stuck", r"waiting", r"still not"],
            "status": [r"status", r"tracking", r"where is", r"no update"],
            "failed": [r"failed", r"didn't go", r"did not go", r"cancelled", r"canceled"],
            "anxiety": [r"worried", r"scared", r"lost my money", r"where's my"],
        },
    },
    {
        "id": "human_support",
        "need": (
            "When a transfer or account is stuck, users need reachable human help "
            "with context — not bots that loop or force them into a store."
        ),
        "families": {
            "support": [r"\bsupport\b", r"customer service", r"\bagent\b", r"\bchat\b"],
            "unreachable": [r"no one", r"can't reach", r"cannot reach", r"no response", r"ignore"],
            "bot": [r"\bbot\b", r"chatbot", r"automated", r"ai assistant"],
            "store": [r"had to go", r"went to (a )?store", r"in.?store"],
        },
    },
    {
        "id": "kyc_friction",
        "need": (
            "Users need verification that feels fair and visible — clear status, "
            "fewer false rejects, and an explanation when identity checks block sending."
        ),
        "families": {
            "verify": [r"verif", r"\bkyc\b", r"identity", r"document", r"passport"],
            "reject": [r"reject", r"denied", r"failed scan", r"won't accept", r"blur"],
            "wait": [r"weeks?", r"days waiting", r"still waiting", r"no update"],
            "lock": [r"locked", r"suspend", r"frozen", r"can't send", r"cannot send"],
        },
    },
    {
        "id": "login_account",
        "need": (
            "Users need reliable login and account recovery across borders — "
            "getting locked out mid-transfer destroys trust faster than fees."
        ),
        "families": {
            "login": [r"log ?in", r"sign ?in", r"password", r"\botp\b", r"\b2fa\b"],
            "lockout": [r"locked out", r"can't access", r"cannot access", r"blocked"],
            "account": [r"\baccount\b", r"link(ed|ing)? bank", r"card (declin|fail)"],
            "country": [r"another country", r"abroad", r"cross.?border", r"travel"],
        },
    },
    {
        "id": "ads_trust",
        "need": (
            "Users distrust ads and upsells during money movement — they read as "
            "scam signals in a financial flow that should feel serious and safe."
        ),
        "families": {
            "ads": [r"\bad\b", r"\bads\b", r"advert", r"banner", r"popup", r"pop-up"],
            "upsell": [r"upsell", r"promotion", r"push(ing)? "],
            "scam": [r"scam", r"fraud", r"phish", r"fake"],
            "money_flow": [r"while send", r"during transfer", r"when I try to send"],
        },
    },
    {
        "id": "rewards_trust",
        "need": (
            "Users want rewards and points they can actually earn and redeem — "
            "broken ledgers feel like bait-and-switch on loyalty."
        ),
        "families": {
            "points": [r"points?", r"reward", r"loyalty", r"cashback"],
            "broken": [r"didn't get", r"did not get", r"missing", r"never received"],
            "redeem": [r"redeem", r"can't use", r"cannot use", r"expire"],
            "bait": [r"promised", r"advertised", r"said I would"],
        },
    },
    {
        "id": "reliability",
        "need": (
            "Users need the app to stay up during sends — crashes, freezes, and "
            "failed submissions at the moment of payment destroy confidence."
        ),
        "families": {
            "crash": [r"crash", r"freeze", r"frozen", r"force close", r"keeps closing"],
            "bug": [r"\bbug\b", r"glitch", r"error", r"doesn't work", r"not working"],
            "android": [r"android", r"samsung", r"pixel", r"update broke"],
            "mid_send": [r"while send", r"trying to send", r"in the middle"],
        },
    },
]


def _family_hits(texts: list[str], families: dict[str, list[str]]) -> dict[str, int]:
    blob = "\n".join(texts).lower()
    hits: dict[str, int] = {}
    for name, patterns in families.items():
        count = 0
        for pat in patterns:
            count += len(re.findall(pat, blob, flags=re.I))
        if count:
            hits[name] = count
    return hits


def infer_need_from_texts(texts: list[str], surface_label: str = "") -> dict[str, Any]:
    scored = []
    for pack in LATENT_PACKS:
        hits = _family_hits(texts, pack["families"])
        if len(hits) < 2:
            continue
        score = sum(hits.values()) * len(hits)
        scored.append((score, pack, hits))

    if not scored:
        cleaned = surface_label.replace(
            "[keyword summary - replace with real LLM naming call]", ""
        ).strip(" :,-")
        # Never emit raw keyword dumps as a "need"
        looks_like_keywords = cleaned.count(",") >= 2 and len(cleaned.split()) <= 12
        return {
            "latent_need": (
                "Users hit recurring app friction that slows or blocks sending, "
                "and they need the product to feel dependable at the moment of transfer."
                if looks_like_keywords or not cleaned
                else cleaned
            ),
            "why_latent": "Heuristic packs did not fire; used a conservative reliability framing.",
            "evidence_pattern": "Insufficient multi-signal co-occurrence for a pack match.",
            "source": "heuristic_fallback",
        }

    scored.sort(key=lambda x: -x[0])
    score, pack, hits = scored[0]
    return {
        "latent_need": pack["need"],
        "why_latent": (
            f"Users rarely state this verbatim; it emerges from co-occurring signals "
            f"({', '.join(hits.keys())}) across the cluster."
        ),
        "evidence_pattern": f"Pack `{pack['id']}` fired with families={dict(hits)} (score={score}).",
        "source": "heuristic_pack",
        "pack_id": pack["id"],
    }


def merge_by_pack(inferred_themes: list[dict]) -> list[dict]:
    import numpy as np

    by_pack: dict[str, list[dict]] = {}
    standalone: list[dict] = []
    for t in inferred_themes:
        pid = t.get("pack_id")
        if not pid:
            standalone.append(t)
            continue
        by_pack.setdefault(pid, []).append(t)

    merged: list[dict] = []
    for pid, group in by_pack.items():
        if len(group) == 1:
            merged.append(group[0])
            continue
        evidence: list[str] = []
        size = 0
        vecs = []
        for t in group:
            evidence.extend(t.get("evidence_ids", []))
            size += t.get("cluster_size", 0)
            if t.get("centroid_vector") is not None:
                vecs.append(t["centroid_vector"])
        centroid = np.mean(vecs, axis=0).tolist() if vecs else group[0].get("centroid_vector")
        avg_recency = float(np.mean([t.get("recency_score", 0.5) for t in group]))
        merged.append(
            {
                "theme_id": f"merged_{pid}",
                "latent_need": group[0]["latent_need"],
                "why_latent": "Merged from multiple clusters sharing the same latent pack.",
                "evidence_pattern": f"Merged {len(group)} themes via pack `{pid}`.",
                "evidence_ids": list(dict.fromkeys(evidence)),
                "cluster_size": size,
                "source_themes": [t["theme_id"] for t in group],
                "centroid_vector": centroid,
                "recency_score": avg_recency,
                "confidence_base": 0.0,
                "pack_id": pid,
                "source": "heuristic_merge",
            }
        )
    return merged + standalone
