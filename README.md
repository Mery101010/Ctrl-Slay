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
python main.py --sample 3000
python app.py
# → http://127.0.0.1:7860
```

Optional free LLM: copy `silent-stakeholder/.env.example` → `.env` and set `GROQ_API_KEY` from [console.groq.com](https://console.groq.com).

## Note on data

Large raw corpora (`play_market_*_reviews`, Trustpilot dump, etc.) are gitignored (GitHub 100MB limit). Regenerated via `scripts/download_datasets.py`.
