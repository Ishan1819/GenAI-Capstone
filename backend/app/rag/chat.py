"""Core chatbot: query condensing, hybrid retrieval, grounded generation, guardrail."""
import re

from app.core import llm
from app.database import db
from app.rag import retrieval

FALLBACK = ("I couldn't find this in ISDIC's information, so I don't want to guess. "
            "I've passed your question to the ISDIC team so it can be answered and added.")

SYSTEM = """You are the ISDIC assistant (Industry Skill Development and Innovation Cell).
Answer ONLY from the numbered sources and the graph facts provided. Never use outside knowledge.
- Cite every claim with the source number in square brackets, e.g. [1] or [2][3].
- Graph facts are verified relationships between entities; use them to explain how things connect, and cite the source that supports them.
- Be concise and direct.
- If the sources do not contain the answer, set "grounded" to false.
Reply with JSON only:
{"grounded": true, "answer": "...", "followups": ["short follow-up question", "...", "..."]}"""


_sessions: dict[str, list[dict]] = {}


def condense(question: str, history: list[dict]) -> str:
    """Turn a follow-up like 'and the intermediate one?' into a standalone question."""
    if not history:
        return question
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
    block = "SOURCES:\n" + "\n\n".join(parts)
    if r["facts"]:
        block += "\n\nGRAPH FACTS:\n" + "\n".join(f"- {f}" for f in r["facts"][:25])
    return block


def generate(question: str, r: dict, history: list[dict] | None = None) -> dict:
    """Grounded generation + guardrail. 'answered' is False when the answer can't be traced to sources."""
    msgs = [{"role": "system", "content": SYSTEM}]
    msgs += [{"role": m["role"], "content": m["content"][:600]} for m in (history or [])[-4:]]
    msgs.append({"role": "user", "content": f"{format_context(r)}\n\nQUESTION: {question}"})
    out = llm.chat_json(msgs)

    text = str(out.get("answer", "")).strip()
    cited = sorted({int(n) for n in re.findall(r"\[(\d+)\]", text) if 1 <= int(n) <= len(r["contexts"])})
    answered = bool(out.get("grounded")) and bool(text) and bool(cited)  # guardrail: must trace to evidence
    sources = [{"n": n, "title": r["contexts"][n - 1]["title"], "url": r["contexts"][n - 1]["url"],
                "snippet": r["contexts"][n - 1]["text"][:220]} for n in cited]
    return {"answered": answered, "answer": text, "sources": sources,
            "followups": [str(f) for f in out.get("followups", [])][:3]}


def answer(session_id: str, message: str, mode: str = "hybrid") -> dict:
    history = _sessions.setdefault(session_id, [])
    standalone = condense(message, history)
    r = retrieval.retrieve(standalone, mode=mode)

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
        "reasoning": {"facts": r["facts"], "graph": r["graph"]} if ok else {"facts": [], "graph": {"nodes": [], "edges": []}},
    }
    history += [{"role": "user", "content": message}, {"role": "assistant", "content": reply["answer"]}]
    del history[:-12]
    return reply
