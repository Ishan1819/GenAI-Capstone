"""Core chatbot: query condensing, RAG retrieval, grounded generation, guardrail."""
import re

from app.core import llm
from app.database import db
from app.rag import retrieval

FALLBACK = ("I couldn't find this in ISDIC's information, so I don't want to guess. "
            "I've passed your question to the ISDIC team so it can be answered and added.")

SYSTEM = """You are the ISDIC assistant (Industry Skill Development and Innovation Cell).
Answer ONLY from the numbered sources provided. Never use outside knowledge.
- Cite claims with the source number in square brackets, e.g. [1] or [2][3].
- List the numbers of every source you used in "sources".
- Be concise and direct (at most 5 sentences).
- If the sources do not contain the answer, set "grounded" to false.
Reply with JSON only:
{"grounded": true, "answer": "...", "sources": [1, 2], "followups": ["short follow-up question", "...", "..."]}"""


_sessions: dict[str, list[dict]] = {}
_REFERENCE_WORDS = {"it", "its", "that", "this", "those", "these", "they", "them", "their", "he", "she", "one",
                    "more", "also", "else", "same", "there"}


def condense(question: str, history: list[dict]) -> str:
    """Turn a follow-up like 'and the intermediate one?' into a standalone question."""
    words = re.findall(r"[a-z']+", question.lower())
    if not history or (len(words) >= 6 and not set(words) & _REFERENCE_WORDS):
        return question  # already standalone: skip an LLM call
    convo = "\n".join(f"{m['role']}: {m['content'][:400]}" for m in history[-6:])
    try:
        out = llm.chat([
            {"role": "system", "content": "Rewrite the user's last message as one standalone question, "
                                          "using the conversation for context. Reply with the question only."},
            {"role": "user", "content": f"Conversation:\n{convo}\n\nLast message: {question}"},
        ], max_tokens=300)
        return out.strip().strip('"') or question
    except Exception:
        return question


def format_context(r: dict) -> str:
    parts = [f"[{i}] {c['title']} ({c['url'] or 'ISDIC team'})\n{c['text']}" for i, c in enumerate(r["contexts"], 1)]
    return "SOURCES:\n" + "\n\n".join(parts)


def _cited_numbers(text: str, listed) -> set[int]:
    nums = {int(n) for n in re.findall(r"\[(\d+)\]", text)}
    for n in listed if isinstance(listed, list) else []:
        if str(n).strip("[] ").isdigit():
            nums.add(int(str(n).strip("[] ")))
    return nums


def _supporting(answer: str, contexts: list[dict], min_overlap: float = 0.35) -> list[int]:
    """Sources sharing most of the answer's content words; empty if none support it."""
    words = lambda s: {w for w in re.findall(r"[a-z0-9]+", s.lower()) if len(w) > 3}
    target = words(answer)
    if not target:
        return []
    scored = sorted(((len(target & words(c["text"])) / len(target), i) for i, c in enumerate(contexts, 1)),
                    reverse=True)
    return sorted(i for share, i in scored[:2] if share >= min_overlap)


def generate(question: str, r: dict, history: list[dict] | None = None) -> dict:
    """Grounded generation + guardrail. 'answered' is False when the answer can't be traced to sources."""
    msgs = [{"role": "system", "content": SYSTEM}]
    msgs += [{"role": m["role"], "content": m["content"][:600]} for m in (history or [])[-4:]]
    msgs.append({"role": "user", "content": f"{format_context(r)}\n\nQUESTION: {question}"})
    out = llm.chat_json(msgs, max_tokens=600)

    text = str(out.get("answer", "")).strip()
    cited = sorted({n for n in _cited_numbers(text, out.get("sources")) if 1 <= n <= len(r["contexts"])})
    if out.get("grounded") and text and not cited:
        cited = _supporting(text, r["contexts"])  # small models often skip citations; match by wording instead
    answered = bool(out.get("grounded")) and bool(text) and bool(cited)  # guardrail: must trace to evidence
    sources = [{"n": n, "title": r["contexts"][n - 1]["title"], "url": r["contexts"][n - 1]["url"],
                "snippet": r["contexts"][n - 1]["text"][:220]} for n in cited]
    return {"answered": answered, "answer": text, "sources": sources,
            "followups": [str(f) for f in out.get("followups", [])][:3]}


def answer(session_id: str, message: str) -> dict:
    history = _sessions.setdefault(session_id, [])
    standalone = condense(message, history)
    r = retrieval.retrieve(standalone, k=4)  # fewer chunks = shorter prompt = much faster on a CPU

    gen = generate(standalone, r, history) if r["sufficient"] else None
    ok = bool(gen and gen["answered"])

    db.log_interaction(session_id, message, standalone, ok, r["best_distance"])
    if not ok:
        db.add_unanswered(standalone)

    reply = {
        "answered": ok,
        "answer": gen["answer"] if ok else FALLBACK,
        "sources": gen["sources"] if ok else [],
        "followups": gen["followups"] if ok else [],
    }
    history += [{"role": "user", "content": message}, {"role": "assistant", "content": reply["answer"]}]
    del history[:-12]
    return reply
