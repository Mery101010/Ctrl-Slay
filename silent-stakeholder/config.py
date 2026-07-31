"""Shared paths and product knobs."""

from pathlib import Path

ROOT = Path(__file__).resolve().parent

_REPO_REVIEWS = ROOT.parent / "data" / "csv" / "app_id_1" / "reviews.csv"
REVIEWS_CSV = (ROOT / "reviews.csv") if (ROOT / "reviews.csv").exists() else _REPO_REVIEWS

GAPS_JSON = ROOT / "gaps.json"
EVIDENCE_INDEX_JSON = ROOT / "evidence_index.json"
ROADMAP_CACHE_JSON = ROOT / "roadmap_cache.json"

GITHUB_OWNER = "Mery101010"
GITHUB_REPO = "Western-Union-Mobile-App-Draft"
PRODUCT_NAME = "Western Union Mobile"
TOP_N_GAPS = 5
CHAT_PORT = 7860
