"""Evaluate the RAG chatbot.

Run from backend/ (after build_kb):
    python -m scripts.evaluate --n 10
Questions are auto-generated once from random knowledge-base chunks and saved to data/eval/questions.json -- edit
that file by hand to curate them; it is reused on later runs.
Metrics: retrieval hit rate (the source chunk is retrieved), answered rate (guardrail passed),
faithfulness (0/1, LLM judge) and relevance (1-5, LLM judge).
"""
import argparse
import json

from app.core import config, llm
from app.database import vectorstore
from app.rag import chat, retrieval

Q_FILE = config.EVAL_DIR / "questions.json"


def make_questions(n: int) -> list[dict]:
    qs = []
    for c in vectorstore.sample_chunks(n * 3):
        if len(qs) >= n:
            break
        if len(c["text"]) < 200 or c["metadata"].get("source") != "web":
            continue
        out = llm.chat_json([
            {"role": "system", "content": 'Write one question that can be answered ONLY from the passage, '
                                          'without mentioning "the passage". JSON: {"question": "..."}'},
            {"role": "user", "content": c["text"]}])
        if out.get("question"):
            qs.append({"question": out["question"], "gold": [c["id"]]})
    return qs


def judge(question: str, context: str, answer: str) -> dict:
    return llm.chat_json([
        {"role": "system", "content": 'You grade a RAG answer. "faithfulness": 1 if every claim in the answer is supported by '
                                      'the context, else 0. "relevance": 1-5 for how well it answers the question. '
                                      'JSON: {"faithfulness": 0, "relevance": 1}'},
        {"role": "user", "content": f"QUESTION: {question}\n\nCONTEXT:\n{context}\n\nANSWER: {answer}"}])


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=10, help="number of questions to generate")
    args = ap.parse_args()

    config.EVAL_DIR.mkdir(parents=True, exist_ok=True)
    if Q_FILE.exists():
        questions = json.loads(Q_FILE.read_text("utf-8"))
    else:
        questions = make_questions(args.n)
        Q_FILE.write_text(json.dumps(questions, indent=2, ensure_ascii=False), "utf-8")
    print(f"{len(questions)} questions")

    rows = []
    for q in questions:
        r = retrieval.retrieve(q["question"])
        hit = bool(set(q["gold"]) & {c["id"] for c in r["contexts"]})
        try:
            gen = chat.generate(q["question"], r) if r["sufficient"] else None
            answer = gen["answer"] if gen else ""
            grade = judge(q["question"], chat.format_context(r), answer) if answer else {"faithfulness": 0, "relevance": 1}
        except Exception as e:
            print("  skipped:", e)
            continue
        rows.append({"question": q["question"], "hit": hit, "answered": bool(gen and gen["answered"]),
                     "faithfulness": grade.get("faithfulness", 0), "relevance": grade.get("relevance", 1)})
        print(f"  hit={hit} answered={rows[-1]['answered']} faith={grade.get('faithfulness')} rel={grade.get('relevance')}")

    if not rows:
        raise SystemExit("No results.")
    avg = lambda key: sum(float(r[key]) for r in rows) / len(rows)
    report = "\n".join([
        "| Questions | Retrieval hit rate | Answered | Faithfulness | Relevance (1-5) |",
        "|---|---|---|---|---|",
        f"| {len(rows)} | {avg('hit'):.0%} | {avg('answered'):.0%} | {avg('faithfulness'):.0%} | {avg('relevance'):.2f} |",
    ])
    (config.EVAL_DIR / "report.md").write_text(report, "utf-8")
    (config.EVAL_DIR / "results.json").write_text(json.dumps(rows, indent=2), "utf-8")
    print("\n" + report + f"\n\nSaved to {config.EVAL_DIR}")


if __name__ == "__main__":
    main()
