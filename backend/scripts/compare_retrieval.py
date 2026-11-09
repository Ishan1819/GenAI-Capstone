"""Plain vector RAG vs metadata-filtered RAG on multi-constraint member questions (paper, Section 4.6 (iii),
Section 5.4, Table 10, Figure 7(b)). Answers RQ2.

Run from backend/ (after build_kb + generate_demo_data):
    python -m scripts.compare_retrieval                 # 10 questions: 6 domain+chapter+level, 4 domain+level+interest
    python -m scripts.compare_retrieval --k 6 --tau 0.65

Protocol
- Questions are generated from the fixed-seed member records. The TRUE answer set is computed directly from the records
  (no LLM, no judgement). Only combinations with 1..k members are used, so a perfect retriever could fit them all in k.
- Both strategies retrieve k chunks for the same question and use the SAME generator prompt:
    plain     similarity over ALL chunks (web, faq, member, event), no attribute predicate
    filtered  the question's domain / chapter / level, parsed by the search module's rules, become phi in Eq. (2)
              (interest is NOT a filter field: it stays in the text and is left to similarity)
- An answer is correct only if the set of members it names equals the true set exactly (exact-set accuracy).

Outputs: data/eval/multi_constraint_questions.json, compare_results.json, compare_report.md
"""
import argparse
import sys

if "--live" not in sys.argv:
    from app.core.isolation import use_fresh_copy

    use_fresh_copy()

import json  # noqa: E402
import random  # noqa: E402
import re  # noqa: E402

from app.core import config, llm  # noqa: E402
from app.database import community  # noqa: E402
from app.evaluation import metrics  # noqa: E402
from app.rag import retrieval  # noqa: E402
from app.services import search  # noqa: E402

Q_FILE = config.EVAL_DIR / "multi_constraint_questions.json"

GEN_SYSTEM = """You answer questions about members of ISDIC, a tech skill-development community.
Use ONLY the numbered sources. List EVERY member in the sources who satisfies ALL conditions in the question, and
NO member who does not. If no source member satisfies all conditions, return an empty list.
Reply with JSON only: {"members": ["Full Name", ...], "answer": "one or two sentences citing sources like [1]"}"""


def _ok_parse(question: str, want: dict) -> bool:
    """Keep only questions whose wording the rule parser reads correctly (an interest such as 'generative AI' would
    otherwise be parsed as the AI and ML domain). Both strategies still receive the identical question."""
    f = search.parse_rules(question)
    return f["entity_type"] == "member" and all(f.get(key) == val for key, val in want.items())


def make_questions(seed: int, n_dcl: int, n_dli: int, k: int) -> list[dict]:
    rng = random.Random(seed)
    ms = community.members()
    out = []

    combos = sorted({(m["domain"], m["chapter"], m["level"]) for m in ms})
    rng.shuffle(combos)
    for domain, chapter, level in combos:
        if sum(q["kind"] == "domain+chapter+level" for q in out) >= n_dcl:
            break
        truth = sorted(m["name"] for m in ms if (m["domain"], m["chapter"], m["level"]) == (domain, chapter, level))
        q = f"Which {level} members of the {domain} community are in the {chapter} chapter?"
        if 1 <= len(truth) <= k and _ok_parse(q, {"domain": domain, "chapter": chapter, "level": level}):
            out.append({"kind": "domain+chapter+level", "question": q, "truth": truth,
                        "constraints": {"domain": domain, "chapter": chapter, "level": level}})

    combos = sorted({(m["domain"], m["level"], i) for m in ms for i in m["interests"]})
    rng.shuffle(combos)
    for domain, level, interest in combos:
        if sum(q["kind"] == "domain+level+interest" for q in out) >= n_dli:
            break
        truth = sorted(m["name"] for m in ms
                       if m["domain"] == domain and m["level"] == level and interest in m["interests"])
        q = f"Which {level} members of the {domain} community are interested in {interest}?"
        if 1 <= len(truth) <= k and _ok_parse(q, {"domain": domain, "level": level}):
            out.append({"kind": "domain+level+interest", "question": q, "truth": truth,
                        "constraints": {"domain": domain, "level": level, "interest": interest}})

    for i, q in enumerate(out, 1):
        q["id"] = f"MC{i:02d}"
    return out


def generate(question: str, r: dict) -> dict:
    sources = "\n\n".join(f"[{i}] {c['text']}" for i, c in enumerate(r["contexts"], 1)) or "(no sources)"
    out = llm.chat_json([{"role": "system", "content": GEN_SYSTEM},
                         {"role": "user", "content": f"SOURCES:\n{sources}\n\nQUESTION: {question}"}],
                        max_tokens=800, temperature=0.0)
    return {"members": [str(x) for x in out.get("members", []) if str(x).strip()],
            "answer": str(out.get("answer", ""))}


def named_members(predicted: list[str], answer: str) -> list[str]:
    """Map generator output onto real member names (case/spacing-insensitive)."""
    known = {" ".join(m["name"].lower().split()): m["name"] for m in community.members()}
    names = {known[" ".join(p.lower().split())] for p in predicted if " ".join(p.lower().split()) in known}
    if not predicted:  # fall back to names mentioned in the free-text answer
        names |= {v for k, v in known.items() if re.search(rf"\b{re.escape(k)}\b", answer.lower())}
    return sorted(names)


def run(questions: list[dict], k: int, tau: float) -> list[dict]:
    rows = []
    for q in questions:
        row = {"id": q["id"], "kind": q["kind"], "question": q["question"], "truth": q["truth"]}
        f = retrieval.filters_for(q["question"])
        strategies = {
            "plain": lambda: retrieval.plain_retrieve(q["question"], k=k, max_distance=tau),
            "filtered": lambda: retrieval.filtered_retrieve(q["question"], f, k=k, max_distance=tau) if f
            else retrieval.plain_retrieve(q["question"], k=k, max_distance=tau),
        }
        for name, fn in strategies.items():
            r = fn()
            member_ctx = [c["title"] for c in r["contexts"] if c["metadata"].get("source") == "member"]
            try:
                gen = generate(q["question"], r)
            except RuntimeError as e:
                print(f"  {q['id']} {name}: LLM error {e}")
                gen = {"members": [], "answer": ""}
            pred = named_members(gen["members"], gen["answer"])
            row[name] = {
                "predicted": pred,
                "correct": metrics.exact_set_match(pred, q["truth"]),
                "retrieved_members": member_ctx,
                "truth_in_context": sum(t in member_ctx for t in q["truth"]) / len(q["truth"]),
                "filters": r.get("filters"),
                "answer": gen["answer"],
            }
        rows.append(row)
        print(f"  {q['id']} [{q['kind']}] truth={len(q['truth'])} plain={'OK' if row['plain']['correct'] else 'x'} "
              f"filtered={'OK' if row['filtered']['correct'] else 'x'}")
    return rows


def report(rows: list[dict], k: int, tau: float) -> str:
    def score(name, kind=None):
        sel = [r for r in rows if kind is None or r["kind"] == kind]
        return f"{sum(r[name]['correct'] for r in sel)} / {len(sel)}"

    def ctx(name):
        return metrics.pct(sum(r[name]["truth_in_context"] for r in rows) / len(rows)) if rows else "n/a"

    return "\n".join([
        "# Plain vs metadata-filtered retrieval (Table 10)", "",
        f"- Generator: `{config.LLM_MODEL}`; k = {k}; tau = {tau:.2f}", "",
        "| Measure | Vector-only RAG | Metadata-filtered RAG |", "|---|---|---|",
        f"| Questions answered with exactly the correct members | {score('plain')} | {score('filtered')} |",
        f"| Domain + chapter + level questions correct | {score('plain', 'domain+chapter+level')} | "
        f"{score('filtered', 'domain+chapter+level')} |",
        f"| Domain + level + interest questions correct | {score('plain', 'domain+level+interest')} | "
        f"{score('filtered', 'domain+level+interest')} |",
        f"| True members present in retrieved context (mean) | {ctx('plain')} | {ctx('filtered')} |",
    ]) + "\n"


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--k", type=int, default=6, help="chunks retrieved by both strategies")
    ap.add_argument("--tau", type=float, default=2.0,
                    help="distance threshold for both strategies (default 2.0 = off, so only k and phi differ)")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--n-dcl", type=int, default=6, help="domain+chapter+level questions")
    ap.add_argument("--n-dli", type=int, default=4, help="domain+level+interest questions")
    ap.add_argument("--regen", action="store_true")
    ap.add_argument("--live", action="store_true", help="use the live data folder instead of a fresh copy")
    args = ap.parse_args()

    config.EVAL_DIR.mkdir(parents=True, exist_ok=True)
    if Q_FILE.exists() and not args.regen:
        questions = json.loads(Q_FILE.read_text("utf-8"))
    else:
        questions = make_questions(args.seed, args.n_dcl, args.n_dli, args.k)
        Q_FILE.write_text(json.dumps(questions, indent=2, ensure_ascii=False), "utf-8")
    if not questions:
        raise SystemExit("No questions: run scripts.generate_demo_data first.")
    print(f"{len(questions)} multi-constraint questions; k = {args.k}; generator {config.LLM_MODEL}")

    rows = run(questions, args.k, args.tau)
    text = report(rows, args.k, args.tau)
    (config.EVAL_DIR / "compare_results.json").write_text(json.dumps(rows, indent=2, ensure_ascii=False), "utf-8")
    (config.EVAL_DIR / "compare_report.md").write_text(text, "utf-8")
    print("\n" + text + f"\nSaved to {config.EVAL_DIR}")


if __name__ == "__main__":
    main()
