# ISDIC Community Intelligence Platform

```
backend/    FastAPI + ChromaDB (RAG) + local LLM via Ollama (any OpenAI-compatible API also works)
frontend/   React (Vite) – member portal + admin console at /#/admin
```

## One-time setup (from `backend/`, inside the conda env)

```
pip install -r requirements.txt
copy .env.example .env                    # then set the LLM settings and ADMIN_TOKEN
python -m scripts.scrape                  # crawl isdic.in -> data/raw/pages.jsonl
python -m scripts.build_kb                # embed pages into ChromaDB (no LLM, about a minute)
python -m scripts.generate_demo_data      # fictional members + events for search and recommendations
```

Everything is saved in `backend/data/`, so these steps are **not** repeated on later days.

## Every day

1. Make sure Ollama is running (tray icon), or `ollama serve`.
2. Backend: `uvicorn app.main:app --reload` (from `backend/`).
3. Frontend: `npm run dev` (from `frontend/`), then open http://localhost:5173.

Optional: `python -m scripts.check_llm` checks the LLM; `python -m scripts.evaluate` writes `data/eval/report.md`.
Re-run `scrape` + `build_kb` only when isdic.in content changes.
