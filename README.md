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

Optional: `python -m scripts.check_llm` checks the LLM.
Re-run `scrape` + `build_kb` only when isdic.in content changes.

## Tests and evaluation (research paper, Sections 4.6–5.7)

All commands run from `backend/`. Every test and experiment works on a **fresh temporary copy** of `data/`
(vector store + SQLite logs), so the live app's data is never touched. Results go to `backend/data/eval/`.

| What | Command | Paper |
|---|---|---|
| 16 functional tests TC01–TC16 (+ metric unit tests); fake LLM, real retrieval | `python -m pytest -v` | Table 8 |
| Automated RAG evaluation: hit rate, answered rate, faithfulness, relevance, RAGAS context precision / recall, generation time | `python -m scripts.evaluate` | Tables 9, 11 |
| Sensitivity analysis: tau ∈ {0.50, 0.65, 0.80} with k = 4, and k = 6 | `python -m scripts.evaluate --sweep` | Section 5.6 |
| Plain vs metadata-filtered retrieval on 10 multi-constraint questions | `python -m scripts.compare_retrieval` | Table 10 |
| Second judge (e.g. local qwen2.5:3b) | `python -m scripts.evaluate --judge-model qwen2.5:3b --tag judge2` | Section 5.7 |
| Judge–human agreement (Cohen's kappa, Spearman's rho) | fill `data/eval/labels_<tag>.csv`, then `python -m scripts.human_validation data/eval/labels_<tag>.csv [--judge2 data/eval/results_judge2.json]` | Section 5.7 |

Response times for the two LLMs (Table 11): run `scripts.evaluate` once with the hosted model and once with Ollama
(switch `LLM_BASE_URL` / `LLM_MODEL` in `.env`); each report includes the mean answer-generation time.

Question sets are generated once with a fixed seed and saved (`questions.json`, `multi_constraint_questions.json`);
edit them by hand to curate, or pass `--regen` to rebuild.
