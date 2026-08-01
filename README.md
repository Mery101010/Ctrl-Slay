# Ctrl-Slay

Western Union mobile app research + **Silent Stakeholder** gap analysis.

## Repo layout

| Path | What |
|---|---|
| `silent-stakeholder/` | Chat UI + latent-need pipeline vs GitHub roadmap |
| `data/csv/app_id_1/` | Western Union app reviews used by the pipeline |
| `data/csv/catalog/` | Dataset category summaries |
| `scripts/` | Dataset download + Month 1 GitHub issue helpers |
| `WU_App_6Month_Roadmap.pdf` | 6-month product roadmap |

Roadmap issues live in: [Western-Union-Mobile-App-Draft](https://github.com/Mery101010/Western-Union-Mobile-App-Draft)

## Run the chatbot

```bash
cd silent-stakeholder
pip install -r requirements.txt
python app.py
# → http://127.0.0.1:7860
```

The UI loads precomputed **`gaps.json`** and **`evidence_index.json`**, so you can demo chat without running analysis first. To refresh rankings:

```bash
python main.py --sample 3000   # CLI
# or click "Run analysis" in the UI
```

Full setup, LLM options, and deploy notes: [`silent-stakeholder/README.md`](silent-stakeholder/README.md).

## Optional LLM

Copy `silent-stakeholder/.env.example` → `.env`. The app loads `.env` automatically (no extra package). If multiple keys are set, the first provider in the priority list wins — see the child README for order (OpenAI, Groq, Gemini, OpenRouter, Ollama, Anthropic). With **no key**, analysis and chat still work via offline heuristics.

## Note on data

Large raw corpora (`play_market_*_reviews`, Trustpilot dump, etc.) are gitignored (GitHub 100MB limit). Regenerated via `scripts/download_datasets.py`.
