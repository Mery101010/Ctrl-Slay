"""
Silent Stakeholder chat server.

  python app.py
  → http://127.0.0.1:7860
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

import llm
from config import GAPS_JSON, EVIDENCE_INDEX_JSON, CHAT_PORT, PRODUCT_NAME, GITHUB_OWNER, GITHUB_REPO
from chat_engine import answer, load_gaps, load_evidence

ROOT = Path(__file__).resolve().parent
STATIC = ROOT / "static"

app = FastAPI(title="Silent Stakeholder")
app.mount("/static", StaticFiles(directory=str(STATIC)), name="static")


class ChatRequest(BaseModel):
    message: str
    history: Optional[list] = None


class AnalyzeRequest(BaseModel):
    sample_n: Optional[int] = 3000
    top_n: int = 5


@app.get("/")
def index():
    return FileResponse(STATIC / "index.html")


@app.get("/api/status")
def status():
    gaps = load_gaps()
    provider = llm.active_provider()
    return {
        "product": PRODUCT_NAME,
        "roadmap": f"https://github.com/{GITHUB_OWNER}/{GITHUB_REPO}",
        "provider": provider,
        "gaps_count": len(gaps),
        "has_gaps": bool(gaps),
        "has_evidence": EVIDENCE_INDEX_JSON.exists(),
    }


@app.get("/api/gaps")
def gaps():
    return load_gaps()


@app.get("/api/evidence/{item_id}")
def evidence_item(item_id: str):
    index = load_evidence()
    if item_id not in index:
        raise HTTPException(404, f"Unknown evidence id: {item_id}")
    return index[item_id]


@app.post("/api/chat")
def chat(req: ChatRequest):
    if not (req.message or "").strip():
        raise HTTPException(400, "Empty message")
    return answer(req.message.strip(), history=req.history or [])


@app.post("/api/analyze")
def analyze(req: AnalyzeRequest):
    from pipeline import run_analysis

    gaps_out = run_analysis(sample_n=req.sample_n, top_n=req.top_n)
    return {
        "ok": True,
        "count": len(gaps_out),
        "provider": llm.active_provider(),
        "gaps": [
            {
                "rank": i + 1,
                "need": g.need,
                "confidence": g.confidence,
                "verdict": g.verdict,
            }
            for i, g in enumerate(gaps_out)
        ],
    }


def main():
    import uvicorn

    print(f"Silent Stakeholder -> http://127.0.0.1:{CHAT_PORT}")
    print(f"LLM: {llm.active_provider()}")
    uvicorn.run(app, host="127.0.0.1", port=CHAT_PORT, log_level="info")


if __name__ == "__main__":
    main()
