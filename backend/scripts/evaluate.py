"""Automated RAG evaluation (paper, Sections 4.6 (ii)+(iv), 5.3, 5.5, 5.6 and Tables 9 and 11).

Run from backend/ (after build_kb + generate_demo_data):
    python -m scripts.evaluate                      # default config k=4, tau=0.65, 20 questions
    python -m scripts.evaluate --sweep              # sensitivity analysis: tau in {0.50,0.65,0.80} with k=4, and k=6
    python -m scripts.evaluate --k 6 --tau 0.65     # one specific configuration
    python -m scripts.evaluate --judge-model qwen2.5:3b --tag judge2   # repeat the judging with a second judge
    python -m scripts.evaluate --no-ragas           # skip context precision/recall (fewer LLM calls)

Protocol
1. Question set (RAGAS-style, no gold answers): an LLM writes one question for each of N randomly sampled web chunks
   (fixed seed), phrased so only that chunk answers it; the chunk is the gold label. Saved to data/eval/questions.json
   and reused (edit it by hand to curate; --regen to rebuild).
2. Every question goes through the FULL chatbot pipeline (condense -> retrieve Eq. (2) -> generate -> guardrail Eq. (3)),
   in a fresh session, on a fresh copy of the vector store and SQLite logs (Section 4.7).
3. Metrics: retrieval hit rate and answered rate (Eq. (5), deterministic); faithfulness 0/1 and relevance 1-5 by the
   LLM judge over answered questions; RAGAS context precision and context recall; answer-generation wall-clock time.

Outputs in data/eval/: results_<tag>.json (one row per question and config), report_<tag>.md, labels_<tag>.csv
(the sheet for human validation, see scripts/human_validation.py).
"""
import argparse
import sys

# Section 4.7: isolate BEFORE any app module reads DATA_DIR
if "--live" not in sys.argv:
    from app.core.isolation import use_fresh_copy

    use_fresh_copy()

import csv  # noqa: E402
import json  # noqa: E402
import time  # noqa: E402
import uuid  # noqa: E402

from app.core import config, llm  # noqa: E402
from app.database import db, vectorstore  # noqa: E402
from app.evaluation import judge, metrics  # noqa: E402
from app.rag import chat  # noqa: E402

Q_FILE = config.EVAL_DIR / "questions.json"
SWEEP = [(4, 0.50), (4, 0.65), (4, 0.80), (6, 0.65)]  # Table 6 "configurations compared"

QGEN_SYSTEM = ('Write ONE question that can be answered only from this passage of the ISDIC community website. '
               'It must be specific to the passage (names, numbers, programme details), sound like a real member '
               'asking, and must not mention "the passage" or "the text". JSON only: {"question": "..."}')


def make_questions(n: int, seed: int) -> list[dict]:
    qs = []
    for c in vectorstore.sample_chunks(n * 4, seed=seed):
        if len(qs) >= n:
            break
        if len(c["text"]) < 200 or c["metadata"].get("source") != "web":
            continue
        try:
            out = llm.chat_json([{"role": "system", "content": QGEN_SYSTEM}, {"role": "user", "content": c["text"]}],
                                max_tokens=400)
        except RuntimeError as e:
            print("  question generation failed:", e)
            continue
        if out.get("question"):
            qs.append({"id": f"Q{len(qs) + 1:02d}", "question": str(out["question"]).strip(), "gold": [c["id"]],
                       "gold_url": c["metadata"].get("url", "")})
            print(f"  {qs[-1]['id']}: {qs[-1]['question']}")
    return qs


def load_questions(n: int, seed: int, regen: bool) -> list[dict]:
    config.EVAL_DIR.mkdir(parents=True, exist_ok=True)
    if Q_FILE.exists() and not regen:
        qs = json.loads(Q_FILE.read_text("utf-8"))
    else:
        print(f"Generating {n} questions (seed {seed})...")
        qs = make_questions(n, seed)
        Q_FILE.write_text(json.dumps(qs, indent=2, ensure_ascii=False), "utf-8")
    for i, q in enumerate(qs, 1):
        q.setdefault("id", f"Q{i:02d}")
    gold_text = {c["id"]: c["text"] for c in vectorstore.get_by_ids(sorted({g for q in qs for g in q["gold"]}))}
    for q in qs:
        q["gold_text"] = "\n\n".join(gold_text.get(g, "") for g in q["gold"])
    return qs


def judge_name(judge_model: str | None) -> str:
    model = judge_model or config.JUDGE_MODEL or config.LLM_MODEL
    return f"{model} via {config.JUDGE_BASE_URL or config.LLM_BASE_URL}"


def preflight(judge_model: str | None) -> None:
    """Fail fast with a clear message instead of retrying every question against a dead endpoint."""
    checks = [("generator", {}),
              ("judge", {"model": judge_model or config.JUDGE_MODEL or None,
                         "base_url": config.JUDGE_BASE_URL or None, "api_key": config.JUDGE_API_KEY or None})]
    for name, kw in checks:
        try:
            llm.chat([{"role": "user", "content": "Reply with the word OK."}], max_tokens=50, retries=1, **kw)
        except RuntimeError as e:
            where = kw.get("base_url") or config.LLM_BASE_URL
            raise SystemExit(f"The {name} LLM at {where} is not reachable: {e}\n"
                             "Start Ollama (or check the API key / URL in backend/.env) and try again.")


def reset_logs() -> None:
    """Fresh SQLite logs and admin queue for each configuration (nothing queued in one run leaks into the next)."""
    if config.DB_PATH.exists():
        config.DB_PATH.unlink()
    db.init()


def run_config(questions: list[dict], k: int, tau: float, judge_model: str | None, ragas: bool) -> list[dict]:
    config.CHAT_K, config.MAX_DISTANCE = k, tau
    reset_logs()
    rows = []
    for q in questions:
        trace: dict = {}
        t0 = time.perf_counter()
        try:
            reply = chat.answer(f"eval-{uuid.uuid4()}", q["question"], trace=trace)
        except RuntimeError as e:
            print(f"  {q['id']} skipped (LLM error): {e}")
            continue
        total_s = time.perf_counter() - t0
        r = trace["retrieval"]
        ctx_ids = [c["id"] for c in r["contexts"]]
        row = {
            "id": q["id"], "question": q["question"], "k": k, "tau": tau, "model": config.LLM_MODEL,
            "judge_model": judge_name(judge_model),
            "hit": bool(set(q["gold"]) & set(ctx_ids)),
            "answered": reply["answered"],
            "refusal_reason": None if reply["answered"] else
            ("no chunk within threshold" if not trace["llm_called"] else "no citation / not traceable to a source"),
            "retrieved": ctx_ids, "best_distance": r["best_distance"],
            "filters": r.get("filters"),
            "answer": reply["answer"] if reply["answered"] else "",
            "cited": [s["n"] for s in reply["sources"]],
            "gen_seconds": trace["gen_seconds"], "total_seconds": total_s,
            "faithfulness": None, "faithfulness_score": None, "relevance": None,
            "context_precision": None, "context_recall": None,
        }
        context = chat.format_context(r) if r["contexts"] else ""
        chunks = [c["text"] for c in r["contexts"]]
        tasks = []
        if reply["answered"]:  # judge-assigned scores are over answered questions only (Table 7)
            tasks.append(("answer", lambda: judge.judge_answer(q["question"], context, reply["answer"], model=judge_model)))
        if ragas:
            tasks.append(("context precision", lambda: judge.context_precision(q["question"], chunks, model=judge_model)))
            tasks.append(("context recall",
                          lambda: judge.context_recall(q["question"], q["gold_text"], chunks, model=judge_model)))
        for name, fn in tasks:  # one failing judge call leaves the other metrics intact
            try:
                row.update(fn())
            except RuntimeError as e:
                print(f"  {q['id']} judge error ({name}): {e}")
        rows.append(row)
        print(f"  {q['id']} hit={int(row['hit'])} answered={int(row['answered'])} faith={row['faithfulness']} "
              f"rel={row['relevance']} cp={metrics.num(row['context_precision'])} "
              f"cr={metrics.num(row['context_recall'])} gen={metrics.num(row['gen_seconds'], 1)}s")
    return rows


def summarise(rows: list[dict]) -> dict:
    gen = [r["gen_seconds"] for r in rows if r["gen_seconds"] is not None]
    return {
        "n": len(rows),
        "hit_rate": metrics.hit_rate(rows),
        "answered_rate": metrics.answered_rate(rows),
        "faithfulness": metrics.mean_over_answered(rows, "faithfulness"),
        "faithfulness_score": metrics.mean_over_answered(rows, "faithfulness_score"),
        "n_judged": sum(r.get("faithfulness") is not None for r in rows),
        "relevance": metrics.mean_over_answered(rows, "relevance"),
        "context_precision": metrics.mean_of(rows, "context_precision"),
        "context_recall": metrics.mean_of(rows, "context_recall"),
        "mean_gen_seconds": sum(gen) / len(gen) if gen else None,
        "n_generated": len(gen),
        "refused_no_context": sum(r["refusal_reason"] == "no chunk within threshold" for r in rows),
        "refused_no_citation": sum(r["refusal_reason"] == "no citation / not traceable to a source" for r in rows),
    }


def report(results: dict, tag: str, judge_model: str | None) -> str:
    m = metrics
    lines = [f"# RAG evaluation ({tag})", "",
             f"- Generator: `{config.LLM_MODEL}` via `{config.LLM_BASE_URL}`",
             f"- Judge: `{judge_name(judge_model)}`",
             f"- Questions: {next(iter(results.values()))['n'] if results else 0}", "",
             "## Table 9 / sensitivity analysis", "",
             "| Configuration | Retrieval hit rate | Answered rate | Faithfulness | Relevance (1-5) |",
             "|---|---|---|---|---|"]
    for name, s in results.items():
        lines.append(f"| {name} | {m.pct(s['hit_rate'])} | {m.pct(s['answered_rate'])} | "
                     f"{m.pct(s['faithfulness'])} | {m.num(s['relevance'])} |")
    lines += ["", "## RAGAS metrics", "",
              "| Configuration | Faithfulness score (claims supported) | Context precision | Context recall | Answers judged |",
              "|---|---|---|---|---|"]
    for name, s in results.items():
        lines.append(f"| {name} | {m.num(s['faithfulness_score'])} | {m.num(s['context_precision'])} | "
                     f"{m.num(s['context_recall'])} | {s['n_judged']} |")
    lines += ["", "## Refusals and response time (Table 11)", "",
              "| Configuration | Refused: no chunk within tau | Refused: not traceable | Mean answer generation time |",
              "|---|---|---|---|"]
    for name, s in results.items():
        lines.append(f"| {name} | {s['refused_no_context']} | {s['refused_no_citation']} | "
                     f"{m.num(s['mean_gen_seconds'], 1)} s (n = {s['n_generated']}) |")
    return "\n".join(lines) + "\n"


def write_label_sheet(rows: list[dict], path) -> None:
    """Blank sheet for two human annotators (Section 5.7): one row per accepted answer."""
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["id", "k", "tau", "question", "answer", "judge_faithfulness", "judge_relevance",
                    "human1_faithfulness", "human1_relevance", "human2_faithfulness", "human2_relevance"])
        for r in rows:
            if r["answered"]:
                w.writerow([r["id"], r["k"], r["tau"], r["question"], r["answer"], r["faithfulness"], r["relevance"],
                            "", "", "", ""])


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--n", type=int, default=20, help="number of questions to generate (first run / --regen)")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--regen", action="store_true", help="regenerate data/eval/questions.json")
    ap.add_argument("--k", type=int, default=None, help=f"chunks retrieved (default {config.CHAT_K})")
    ap.add_argument("--tau", type=float, default=None, help=f"distance threshold (default {config.MAX_DISTANCE})")
    ap.add_argument("--sweep", action="store_true", help="run all sensitivity configurations")
    ap.add_argument("--judge-model", default=None, help="model used as judge (default: the generator model)")
    ap.add_argument("--no-ragas", action="store_true", help="skip context precision / recall")
    ap.add_argument("--tag", default=None, help="name for the output files")
    ap.add_argument("--live", action="store_true", help="use the live data folder instead of a fresh copy")
    args = ap.parse_args()

    db.init()
    preflight(args.judge_model)
    questions = load_questions(args.n, args.seed, args.regen)
    if not questions:
        raise SystemExit("No questions. Is the knowledge base built and the LLM reachable?")
    configs = SWEEP if args.sweep else [(args.k or config.CHAT_K, args.tau if args.tau is not None else config.MAX_DISTANCE)]
    tag = args.tag or ("sweep" if args.sweep else f"k{configs[0][0]}_tau{configs[0][1]:.2f}")
    print(f"{len(questions)} questions, configs {configs}, generator {config.LLM_MODEL}")

    all_rows, results = [], {}
    for k, tau in configs:
        print(f"\n== k = {k}, tau = {tau:.2f} ==")
        rows = run_config(questions, k, tau, args.judge_model, not args.no_ragas)
        results[f"k = {k}, tau = {tau:.2f}"] = summarise(rows)
        all_rows += rows

    if not all_rows:
        raise SystemExit("No results.")
    config.EVAL_DIR.mkdir(parents=True, exist_ok=True)
    text = report(results, tag, args.judge_model)
    (config.EVAL_DIR / f"report_{tag}.md").write_text(text, "utf-8")
    (config.EVAL_DIR / f"results_{tag}.json").write_text(
        json.dumps({"summary": results, "rows": all_rows}, indent=2, ensure_ascii=False), "utf-8")
    write_label_sheet(all_rows, config.EVAL_DIR / f"labels_{tag}.csv")
    print("\n" + text + f"\nSaved to {config.EVAL_DIR}")


if __name__ == "__main__":
    main()
