# ISDIC Community Intelligence Platform

```
backend/    FastAPI + ChromaDB + NetworkX knowledge graph + OpenRouter LLM
frontend/   React (Vite) – chatbot, learning path, resume check, admin
```

## Backend setup (from `backend/`, inside your conda env)

```
pip install -r requirements.txt
copy .env.example .env          # then set OPENROUTER_API_KEY and ADMIN_TOKEN

python -m scripts.scrape        # 1. crawl isdic.in -> data/raw/pages.jsonl
python -m scripts.build_kb --skip-graph   # 2a. embed into ChromaDB (no LLM calls) - chatbot already works after this
python -m scripts.build_kb      # 2b. build the knowledge graph (LLM calls, cached/resumable)
python -m scripts.generate_demo_data      # 2c. fictional members + events for search & recommendations (no LLM calls)
uvicorn app.main:app --reload   # 3. API on http://localhost:8000  (docs at /docs)
python -m scripts.evaluate      # 4. vector-only vs hybrid report -> data/eval/report.md
```

Restart the API after rebuilding the graph.

## Frontend (from `frontend/`)

```
npm install
npm run dev                     # http://localhost:5173
```

## Notes
- The OpenRouter free tier is rate limited (and has a low daily request cap unless the account has credit).
  `LLM_MIN_INTERVAL` spaces calls out; graph extraction batches several chunks per call and caches results.
- Admin endpoints need the `X-Admin-Token` header (the Admin tab sends it).
