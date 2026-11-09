"""Deterministic validation metrics (paper, Section 3.3 Eq. (5) and Table 7). No LLM calls here.

- hit_rate, answered_rate      Eq. (5)
- exact_set_match              multi-constraint questions (Table 10)
- average_precision            RAGAS context precision from per-chunk relevance verdicts
- cohen_kappa, spearman_rho    judge-human agreement (Section 5.7)
"""
from __future__ import annotations

import math
from statistics import mean


def hit_rate(rows: list[dict]) -> float | None:
    """|{q : gold chunk in Ctx(q)}| / |Q|."""
    return mean(1.0 if r["hit"] else 0.0 for r in rows) if rows else None


def answered_rate(rows: list[dict]) -> float | None:
    """|{q : accept(a_q)}| / |Q|; its complement is the refusal rate."""
    return mean(1.0 if r["answered"] else 0.0 for r in rows) if rows else None


def mean_over_answered(rows: list[dict], key: str) -> float | None:
    vals = [float(r[key]) for r in rows if r.get("answered") and r.get(key) is not None]
    return mean(vals) if vals else None


def mean_of(rows: list[dict], key: str) -> float | None:
    vals = [float(r[key]) for r in rows if r.get(key) is not None]
    return mean(vals) if vals else None


def exact_set_match(predicted, truth) -> bool:
    norm = lambda xs: {" ".join(str(x).lower().split()) for x in xs}
    return norm(predicted) == norm(truth)


def average_precision(relevant: list[bool]) -> float:
    """RAGAS context precision@k: mean of precision@i over the ranks i that hold a relevant chunk.
    Rewards putting the useful chunks first; 0 when no retrieved chunk is relevant."""
    hits, total = 0, 0.0
    for i, rel in enumerate(relevant, 1):
        if rel:
            hits += 1
            total += hits / i
    return total / hits if hits else 0.0


def cohen_kappa(a: list, b: list) -> float | None:
    """Cohen's kappa for two raters over the same items (nominal labels)."""
    if len(a) != len(b) or not a:
        return None
    n = len(a)
    labels = sorted(set(a) | set(b), key=str)
    po = sum(x == y for x, y in zip(a, b)) / n
    pe = sum((a.count(l) / n) * (b.count(l) / n) for l in labels)
    if pe == 1:
        return 1.0 if po == 1 else 0.0  # both raters used one identical label everywhere
    return (po - pe) / (1 - pe)


def _ranks(xs: list[float]) -> list[float]:
    """Average ranks (1-based), ties share the mean rank."""
    order = sorted(range(len(xs)), key=lambda i: xs[i])
    ranks = [0.0] * len(xs)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and xs[order[j + 1]] == xs[order[i]]:
            j += 1
        for t in range(i, j + 1):
            ranks[order[t]] = (i + j) / 2 + 1
        i = j + 1
    return ranks


def spearman_rho(a: list[float], b: list[float]) -> float | None:
    """Spearman's rank correlation = Pearson correlation of the (tie-averaged) ranks."""
    if len(a) != len(b) or len(a) < 2:
        return None
    ra, rb = _ranks([float(x) for x in a]), _ranks([float(x) for x in b])
    ma, mb = mean(ra), mean(rb)
    cov = sum((x - ma) * (y - mb) for x, y in zip(ra, rb))
    sa = math.sqrt(sum((x - ma) ** 2 for x in ra))
    sb = math.sqrt(sum((y - mb) ** 2 for y in rb))
    if sa == 0 or sb == 0:
        return None  # one rater gave the same score everywhere: correlation undefined
    return cov / (sa * sb)


def pct(x: float | None) -> str:
    return "n/a" if x is None else f"{x:.0%}"


def num(x: float | None, digits: int = 2) -> str:
    return "n/a" if x is None else f"{x:.{digits}f}"
