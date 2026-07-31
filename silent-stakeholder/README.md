# Silent Stakeholder

Surface the needs users **didn't say out loud** — then defend them in chat.

Compares **Western Union Mobile** Play Store reviews against the live GitHub roadmap:
[Mery101010/Western-Union-Mobile-App-Draft](https://github.com/Mery101010/Western-Union-Mobile-App-Draft)

**Top unmet need (64.1% confidence, UNDER-PRIORITIZED):** users hit recurring app friction that slows or blocks sending, and need the product to feel dependable at the moment of transfer.

## Quick start

```bash
pip install -r requirements.txt
python main.py --sample 3000   # analyze (heuristics or free LLM)
python app.py                  # chatbot UI → http://127.0.0.1:7860
```

## Free LLMs (optional, no Anthropic required)

Copy `.env.example` → `.env` and set **one**:

| Provider | Env var | Get key |
|---|---|---|
| Groq (recommended) | `GROQ_API_KEY` | [console.groq.com](https://console.groq.com) |
| Gemini | `GEMINI_API_KEY` | [aistudio.google.com](https://aistudio.google.com/apikey) |
| Ollama | local on `:11434` | `ollama pull llama3.2` |

With **no key**, the pipeline still runs on offline heuristic pattern packs.

## Chat UI

Ask judge-style questions:

- What are the top unmet needs?
- Why is #1 ranked first?
- Show evidence for gap #2

## Data

- Reviews: `Ctrl-Slay/data/csv/app_id_1/reviews.csv` (or local `reviews.csv`)
- Roadmap: live GitHub issues API (+ `roadmap_cache.json` fallback)

## Deploy notes

This is a FastAPI app (`app.py`). Free hosts that work well:

- [Render](https://render.com) — Web Service, start command `uvicorn app:app --host 0.0.0.0 --port $PORT`
- [Railway](https://railway.app)
- Local share while presenting: `npx localtunnel --port 7860`
