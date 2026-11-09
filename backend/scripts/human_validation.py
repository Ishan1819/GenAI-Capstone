"""Judge-human agreement (paper, Section 5.7 and Table 7 "Judge-human agreement").

Step 1  python -m scripts.evaluate                      -> writes data/eval/labels_<tag>.csv (one row per accepted answer)
Step 2  Two authors fill human1_* and human2_* columns INDEPENDENTLY, using the judge's rubric
        (faithfulness 0/1: every claim supported by the retrieved sources; relevance 1-5). Settle disagreements on the
        retrieved sources only afterwards.
Step 3  python -m scripts.human_validation data/eval/labels_<tag>.csv

Optional second judge (does the score depend on the judging model?):
        python -m scripts.evaluate --judge-model qwen2.5:3b --tag judge2
        python -m scripts.human_validation data/eval/labels_<tag>.csv --judge2 data/eval/results_judge2.json

Reports Cohen's kappa (faithfulness) and Spearman's rho (relevance) for: human1 vs human2, judge vs each human,
judge vs the human consensus, and judge1 vs judge2. The judge is treated as reliable if kappa(judge, consensus) >= 0.6.
"""
import argparse
import csv
import json
from pathlib import Path

from app.evaluation.metrics import cohen_kappa, num, spearman_rho

RELIABLE_KAPPA = 0.6


def _int(x):
    try:
        return int(round(float(x)))
    except (TypeError, ValueError):
        return None


def load(path: Path) -> list[dict]:
    with open(path, encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _float(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def pairs(rows, a: str, b: str, conv=_int):
    got = [(conv(r.get(a)), conv(r.get(b))) for r in rows]
    got = [(x, y) for x, y in got if x is not None and y is not None]
    return [x for x, _ in got], [y for _, y in got]


def agreement(rows, a_f, b_f, a_r, b_r) -> dict:
    fa, fb = pairs(rows, a_f, b_f)
    ra, rb = pairs(rows, a_r, b_r, conv=_float)  # consensus relevance can be x.5
    return {"n": len(fa), "kappa": cohen_kappa(fa, fb), "faith_agree": (sum(x == y for x, y in zip(fa, fb)) / len(fa))
            if fa else None, "rho": spearman_rho(ra, rb)}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("labels", type=Path, help="filled labels_<tag>.csv")
    ap.add_argument("--judge2", type=Path, default=None, help="results_<tag>.json from a run with a second judge")
    args = ap.parse_args()

    rows = load(args.labels)
    labelled = [r for r in rows if _int(r.get("human1_faithfulness")) is not None
                and _int(r.get("human2_faithfulness")) is not None]
    if not labelled:
        raise SystemExit("No rows with both human1_faithfulness and human2_faithfulness filled in yet.")

    for r in labelled:  # consensus: faithful only if both humans say so; relevance = mean of the two
        r["consensus_faithfulness"] = int(_int(r["human1_faithfulness"]) == 1 and _int(r["human2_faithfulness"]) == 1)
        rel = [x for x in (_int(r.get("human1_relevance")), _int(r.get("human2_relevance"))) if x is not None]
        r["consensus_relevance"] = sum(rel) / len(rel) if rel else ""

    if args.judge2:
        j2 = {(x["id"], str(x["k"]), str(x["tau"])): x for x in json.loads(args.judge2.read_text("utf-8"))["rows"]}
        for r in labelled:
            x = j2.get((r["id"], str(r["k"]), str(r["tau"])))
            r["judge2_faithfulness"] = x.get("faithfulness") if x else ""
            r["judge2_relevance"] = x.get("relevance") if x else ""

    comparisons = {
        "Human 1 vs Human 2": ("human1_faithfulness", "human2_faithfulness", "human1_relevance", "human2_relevance"),
        "Judge vs Human 1": ("judge_faithfulness", "human1_faithfulness", "judge_relevance", "human1_relevance"),
        "Judge vs Human 2": ("judge_faithfulness", "human2_faithfulness", "judge_relevance", "human2_relevance"),
        "Judge vs consensus": ("judge_faithfulness", "consensus_faithfulness", "judge_relevance", "consensus_relevance"),
    }
    if args.judge2:
        comparisons["Judge 1 vs Judge 2"] = ("judge_faithfulness", "judge2_faithfulness", "judge_relevance",
                                             "judge2_relevance")
        comparisons["Judge 2 vs consensus"] = ("judge2_faithfulness", "consensus_faithfulness", "judge2_relevance",
                                               "consensus_relevance")

    lines = ["# Judge-human agreement", "", f"Labelled answers: {len(labelled)}", "",
             "| Comparison | n | Faithfulness raw agreement | Cohen's kappa | Spearman's rho (relevance) |",
             "|---|---|---|---|---|"]
    results = {}
    for name, cols in comparisons.items():
        a = agreement(labelled, *cols)
        results[name] = a
        lines.append(f"| {name} | {a['n']} | {num(a['faith_agree'])} | {num(a['kappa'])} | {num(a['rho'])} |")
    k = results["Judge vs consensus"]["kappa"]
    verdict = ("reliable" if k is not None and k >= RELIABLE_KAPPA else "NOT reliable")
    lines += ["", f"Judge is **{verdict}** (kappa vs consensus = {num(k)}, threshold {RELIABLE_KAPPA})."]
    text = "\n".join(lines) + "\n"

    out = args.labels.with_name(args.labels.stem.replace("labels", "agreement") + ".md")
    out.write_text(text, "utf-8")
    print(text + f"\nSaved to {out}")


if __name__ == "__main__":
    main()
