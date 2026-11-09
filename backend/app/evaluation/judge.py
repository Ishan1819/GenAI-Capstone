"""LLM-as-a-judge (paper, Sections 4.6 and 5.7) and RAGAS-style metrics [Es et al., EACL 2024].

The judge can run on a different provider than the generator (JUDGE_BASE_URL / JUDGE_API_KEY / JUDGE_MODEL in .env,
or --judge-model), e.g. generate with local qwen2.5:3b and judge with gpt-oss-20b on Groq, as in the paper.

Prompts ask for reasoning FIRST and use word labels ("yes"/"no", "fully"/"partially"...) instead of numbers, because
small models otherwise copy the example JSON verbatim (e.g. always returning faithfulness 0, relevance 1).

Metrics
- faithfulness (0/1)          1 only if EVERY claim in the answer is supported by the retrieved context
- faithfulness_score (0-1)    RAGAS faithfulness: supported claims / all claims
- relevance (1-5)             how well the answer addresses the question
- context precision (0-1)     RAGAS: are the useful chunks ranked first? (average precision over per-chunk verdicts)
- context recall (0-1)        RAGAS: share of the reference's statements that the retrieved context covers.
                              The reference is the gold chunk the question was written from (no hand-written answers).
"""
from app.core import config, llm
from app.evaluation.metrics import average_precision

MAX_STATEMENTS = 8
RELEVANCE_WORDS = {"fully": 5, "mostly": 4, "partially": 3, "barely": 2, "not": 1}

ANSWER_SYSTEM = """You are a strict, impartial evaluator of a retrieval-augmented chatbot.
Judge ONLY against the CONTEXT; ignore your own knowledge. Do not reward length or style.

Step 1. Break the ANSWER into its individual factual claims (at most 8).
Step 2. For each claim, look for it in the CONTEXT. "supported" is "yes" only if the CONTEXT states it
        (paraphrase is fine); otherwise "no". Quote the supporting words as "evidence" (or "none").
Step 3. Decide how well the ANSWER addresses the QUESTION, using exactly one word:
        "fully", "mostly", "partially", "barely" or "not".

Reply with JSON only, in this shape:
{"claims": [{"claim": "<claim text>", "evidence": "<quote from context or none>", "supported": "<yes or no>"}],
 "relevance_reason": "<why>", "relevance": "<fully|mostly|partially|barely|not>"}"""

CONTEXT_PRECISION_SYSTEM = """You check which retrieved CONTEXT chunks are useful for answering a QUESTION.
For EACH numbered chunk, in order, say in a few words what it contains, then decide: "useful" is "yes" if the chunk
contains information needed to answer the QUESTION, otherwise "no". Judge each chunk on its own.

Reply with JSON only, in this shape:
{"chunks": [{"chunk": <number>, "contains": "<few words>", "useful": "<yes or no>"}]}"""

CONTEXT_RECALL_SYSTEM = """You check whether retrieved CONTEXT covers a REFERENCE passage.
Step 1. List the distinct factual statements in the REFERENCE that are relevant to the QUESTION (at most 8).
Step 2. For each statement, search the CONTEXT. "found" is "yes" only if the CONTEXT itself states it; "no" if the
        statement only appears in the REFERENCE. Quote the matching CONTEXT words as "evidence" (or "none").

Reply with JSON only, in this shape:
{"statements": [{"statement": "<text>", "evidence": "<quote from context or none>", "found": "<yes or no>"}]}"""


def _yes(x) -> bool:
    return str(x).strip().lower().strip('."\'') in ("yes", "y", "true", "1", "supported", "found", "useful")


def _call(system: str, user: str, model: str | None, max_tokens: int):
    return llm.chat_json([{"role": "system", "content": system}, {"role": "user", "content": user}],
                         max_tokens=max_tokens, temperature=0.0, model=model or config.JUDGE_MODEL or None,
                         base_url=config.JUDGE_BASE_URL or None, api_key=config.JUDGE_API_KEY or None)


def judge_answer(question: str, context: str, answer: str, model: str | None = None) -> dict:
    out = _call(ANSWER_SYSTEM, f"QUESTION: {question}\n\nCONTEXT:\n{context}\n\nANSWER: {answer}", model, 1500)
    claims = [c for c in (out.get("claims") or []) if isinstance(c, dict)][:MAX_STATEMENTS]
    supported = [_yes(c.get("supported")) for c in claims]
    rel_word = str(out.get("relevance", "")).strip().lower().strip('."\'')
    relevance = RELEVANCE_WORDS.get(rel_word.split()[0] if rel_word else "", None)
    if relevance is None:  # tolerate a number
        try:
            relevance = max(1, min(5, int(float(rel_word))))
        except ValueError:
            relevance = None
    if not claims or relevance is None:
        raise RuntimeError(f"judge reply missing claims or relevance: {str(out)[:200]}")
    return {
        "faithfulness": int(all(supported)),
        "faithfulness_score": sum(supported) / len(supported),
        "relevance": relevance,
        "judge_claims": [{"claim": str(c.get("claim", ""))[:200], "supported": int(s)} for c, s in zip(claims, supported)],
        "judge_reason": str(out.get("relevance_reason", ""))[:300],
    }


def context_precision(question: str, chunks: list[str], model: str | None = None) -> dict:
    if not chunks:
        return {"context_precision": 0.0, "chunk_verdicts": []}
    numbered = "\n\n".join(f"[{i}] {c[:1200]}" for i, c in enumerate(chunks, 1))
    out = _call(CONTEXT_PRECISION_SYSTEM, f"QUESTION: {question}\n\nCONTEXT:\n{numbered}", model, 1000)
    by_num = {}
    for i, c in enumerate(x for x in (out.get("chunks") or []) if isinstance(x, dict)):
        try:
            n = int(c.get("chunk", i + 1))
        except (TypeError, ValueError):
            n = i + 1
        by_num[n] = _yes(c.get("useful"))
    if not by_num:
        raise RuntimeError(f"judge reply missing chunk verdicts: {str(out)[:200]}")
    verdicts = [by_num.get(i, False) for i in range(1, len(chunks) + 1)]
    return {"context_precision": average_precision(verdicts), "chunk_verdicts": [int(v) for v in verdicts]}


def context_recall(question: str, reference: str, chunks: list[str], model: str | None = None) -> dict:
    if not chunks:
        return {"context_recall": 0.0, "recall_statements": []}
    context = "\n\n".join(c[:1200] for c in chunks)
    out = _call(CONTEXT_RECALL_SYSTEM, f"QUESTION: {question}\n\nREFERENCE:\n{reference}\n\nCONTEXT:\n{context}",
                model, 1500)
    stmts = [s for s in (out.get("statements") or []) if isinstance(s, dict)][:MAX_STATEMENTS]
    if not stmts:
        return {"context_recall": None, "recall_statements": []}
    # a "yes" with no quoted evidence is not trusted
    got = [_yes(s.get("found")) and str(s.get("evidence", "none")).strip().lower() not in ("", "none", "n/a")
           for s in stmts]
    return {"context_recall": sum(got) / len(got),
            "recall_statements": [{"text": str(s.get("statement", ""))[:200], "found": int(g)}
                                  for s, g in zip(stmts, got)]}
