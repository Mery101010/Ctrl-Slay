# Silent Stakeholder

Surface the needs users **didn't say out loud** — then defend them in chat.

Compares **Western Union Mobile** Play Store reviews against the live GitHub roadmap:
[Mery101010/Western-Union-Mobile-App-Draft](https://github.com/Mery101010/Western-Union-Mobile-App-Draft)

The pipeline ranks **12 gaps** (`TOP_N_GAPS`); the brief highlights the **top 5** (`PRIMARY_GAPS`). Committed **`gaps.json`** / **`evidence_index.json`** ship with the repo so the chat UI works out of the box — re-run analysis when you want fresh numbers.

## Quick start

```bash
pip install -r requirements.txt
python app.py                  # chatbot → http://127.0.0.1:7860
```

Optional — refresh analysis from reviews + live GitHub issues:

```bash
python main.py --sample 3000   # default top_n=12
python main.py --top 5         # smaller backlog
python main.py --chat          # same as python app.py
```

## LLMs (optional)

Copy `.env.example` → `.env`. Variables are loaded at startup (built-in loader; no `python-dotenv`).

**Priority** — first configured provider wins:

| Order | Provider | Env var(s) | Notes |
|---|---|---|---|
| 1 | OpenAI | `OPENAI_API_KEY`, `OPENAI_MODEL` | e.g. promo credits — [platform.openai.com](https://platform.openai.com/api-keys) |
| 2 | Groq (free tier) | `GROQ_API_KEY`, `GROQ_MODEL` | [console.groq.com](https://console.groq.com) |
| 3 | Gemini (free tier) | `GEMINI_API_KEY`, `GEMINI_MODEL` | [aistudio.google.com](https://aistudio.google.com/apikey) |
| 4 | OpenRouter | `OPENROUTER_API_KEY`, `OPENROUTER_MODEL` | Optional free models |
| 5 | Ollama | `OLLAMA_MODEL` | Local `:11434` — `ollama pull llama3.2` |
| 6 | Anthropic | `ANTHROPIC_API_KEY` | Paid, if you already have a key |
| — | Heuristics | *(none)* | Offline pattern packs; structured chat answers without an API |

With **no key**, **`Run analysis`** and chat still work; LLM improves latent-theme synthesis and scope checks when available.

## How gaps are scored

**Synchronizer v2** links merged review themes to roadmap embeddings, then classifies each gap:

- **Verdicts:** `IGNORED`, `UNDER-PRIORITIZED`, `MISUNDERSTOOD` (from similarity, roadmap activity, and **scope check** on the nearest issue).
- **Confidence:** blend of evidence **volume** (upvote-weighted reviews), **recency**, **roadmap gap** (distance to nearest issue), and **scope alignment** when a close issue exists.

Chat and the evidence pane can show breakdown fields from `gaps.json` when you ask *why* a gap ranked.

## Chat UI

- **Run analysis** — POST `/api/analyze` (same pipeline as CLI; ~1 min on 3k reviews).
- **Evidence sidebar** — review excerpts and GitHub issue links for the focused gap.
- **Status pill** — active LLM provider and model (or heuristics).

Example questions (or use the suggestion chips):

- What are the top unmet needs?
- Why is #1 ranked first?
- Which GitHub issues are closest to these gaps?
- Show evidence for gap #2

## Data

- Reviews: `../data/csv/app_id_1/reviews.csv` (or local `reviews.csv` in this folder)
- Roadmap: live GitHub issues API (+ `roadmap_cache.json` fallback)
- Outputs: `gaps.json`, `evidence_index.json` (committed snapshot + regenerated on analyze)

## API (for integrators)

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/status` | Product, provider, gap count |
| GET | `/api/gaps` | Full ranked gap list |
| GET | `/api/evidence/{id}` | Review or issue snippet |
| POST | `/api/chat` | `{ "message", "history?" }` |
| POST | `/api/analyze` | `{ "sample_n?", "top_n?" }` |

## Deploy notes

FastAPI app (`app.py`). Free hosts that work well:

- [Render](https://render.com) — Web Service, start command `uvicorn app:app --host 0.0.0.0 --port $PORT`
- [Railway](https://railway.app)
- Local share while presenting: `npx localtunnel --port 7860`
