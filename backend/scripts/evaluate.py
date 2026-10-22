"""Compare vector-only RAG against hybrid GraphRAG.

Run from backend/ (after build_kb):
    python -m scripts.evaluate --n 8
Questions are auto-generated once (factual from single chunks, relational from 2-hop graph paths) and saved to
data/eval/questions.json -- edit that file by hand to curate them; it is reused on later runs.
Metrics per mode: retrieval hit rate (gold chunk retrieved), faithfulness (0/1, LLM judge), relevance (1-5, LLM judge).
"""
import argparse
import json
import random

from app.core import config, llm
from app.database import vectorstore
from app.rag import chat, retrieval
from app.knowledge.graph import get_graph

Q_FILE = config.EVAL_DIR / "questions.json"


def make_factual(n: int) -> list[dict]:
    qs = []
    for c in vectorstore.sample_chunks(n * 2):
        if len(c["text"]) < 200 or len(qs) >= n:
            continue
        out = llm.chat_json([
            {"role": "system", "content": 'Write one question that can be answered ONLY from the passage, '
                                          'without mentioning "the passage". JSON: {"question": "..."}'},
            {"role": "user", "content": c["text"]}])
        qs.append({"type": "factual", "question": out["question"], "gold": [c["id"]]})
    return qs


def make_relational(n: int) -> list[dict]:
    kg, qs = get_graph(), []
    paths = [(u, v, w) for u, v in kg.g.edges() for w in kg.g.successors(v) if w != u]
    random.shuffle(paths)
    for u, v, w in paths[: n * 3]:
        if len(qs) >= n:
            break
        e1, e2 = list(kg.g[u][v].values())[0], list(kg.g[v][w].values())[0]
        rel1, rel2 = list(kg.g[u][v])[0], list(kg.g[v][w])[0]
        names = [kg.g.nodes[x]["name"] for x in (u, v, w)]
        out = llm.chat_json([
            {"role": "system", "content": 'Write one natural question whose answer requires following BOTH relationships. '
                                          'Do not reveal the answer entity. JSON: {"question": "..."}'},
            {"role": "user", "content": f"{names[0]} --{rel1}--> {names[1]} --{rel2}--> {names[2]}. Answer entity: {names[2]}"}])
        qs.append({"type": "relational", "question": out["question"], "gold": list({*e1["chunks"], *e2["chunks"]})})
    return qs


def judge(question: str, context: str, answer: str) -> dict:
    return llm.chat_json([
        {"role": "system", "content": 'You grade a RAG answer. "faithfulness": 1 if every claim in the answer is supported by '
                                      'the context, else 0. "relevance": 1-5 for how well it answers the question. '
                                      'JSON: {"faithfulness": 0|1, "relevance": 1-5}'},
        {"role": "user", "content": f"QUESTION: {question}\n\nCONTEXT:\n{context}\n\nANSWER: {answer}"}])


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=8, help="questions per type")
    args = ap.parse_args()

    config.EVAL_DIR.mkdir(parents=True, exist_ok=True)
    if Q_FILE.exists():
        questions = json.loads(Q_FILE.read_text("utf-8"))
    else:
        questions = make_factual(args.n) + make_relational(args.n)
        Q_FILE.write_text(json.dumps(questions, indent=2, ensure_ascii=False), "utf-8")
    print(f"{len(questions)} questions")

    rows = []
    for q in questions:
        for mode in ("vector", "hybrid"):
            r = retrieval.retrieve(q["question"], mode=mode)
            hit = bool(set(q["gold"]) & {c["id"] for c in r["contexts"]})
            try:
                gen = chat.generate(q["question"], r) if r["sufficient"] else None
                answer = gen["answer"] if gen else ""
                grade = judge(q["question"], chat.format_context(r), answer) if answer else {"faithfulness": 0, "relevance": 1}
            except Exception as e:
                print("  skipped:", e)
                continue
            rows.append({"type": q["type"], "mode": mode, "hit": hit, "answered": bool(gen and gen["answered"]),
                         "faithfulness": grade.get("faithfulness", 0), "relevance": grade.get("relevance", 1)})
            print(f"  [{q['type']:<10}] {mode:<6} hit={hit} faith={grade.get('faithfulness')} rel={grade.get('relevance')}")

    lines = ["| Question type | Mode | n | Retrieval hit | Answered | Faithfulness | Relevance (1-5) |",
             "|---|---|---|---|---|---|---|"]
    for qtype in ("factual", "relational"):
        for mode in ("vector", "hybrid"):
            sel = [r for r in rows if r["type"] == qtype and r["mode"] == mode]
            if not sel:
                continue
            avg = lambda key: sum(r[key] for r in sel) / len(sel)
            lines.append(f"| {qtype} | {mode} | {len(sel)} | {avg('hit'):.0%} | {avg('answered'):.0%} | "
                         f"{avg('faithfulness'):.0%} | {avg('relevance'):.2f} |")
    report = "\n".join(lines)
    (config.EVAL_DIR / "report.md").write_text(report, "utf-8")
    (config.EVAL_DIR / "results.json").write_text(json.dumps(rows, indent=2), "utf-8")
    print("\n" + report + f"\n\nSaved to {config.EVAL_DIR}")


if __name__ == "__main__":
    main()
