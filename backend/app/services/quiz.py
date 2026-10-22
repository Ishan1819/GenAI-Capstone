"""Skill quiz: multiple-choice questions generated from ISDIC's curriculum for a domain and level."""
from app.core import llm
from app.rag import retrieval

SYSTEM = """You write multiple-choice quiz questions for students in ISDIC's {domain} community at the {level} level.
Base every question on the skills, tools and topics in the curriculum text provided; ask about the concepts themselves
(e.g. what a tool is used for, how a technique works), not about the curriculum document.
Each question has exactly 4 options and one correct answer. Keep questions short and practical.
Reply with JSON only:
{{"questions": [{{"question": "...", "options": ["...", "...", "...", "..."], "answer_index": 0,
"explanation": "one sentence on why", "topic": "short topic name"}}]}}"""


def generate_quiz(domain: str, level: str, n: int = 5) -> dict:
    r = retrieval.retrieve(f"{domain} {level} level skill progression tools curriculum", k=6)
    context = "\n\n".join(c["text"] for c in r["contexts"])
    out = llm.chat_json([
        {"role": "system", "content": SYSTEM.format(domain=domain, level=level)},
        {"role": "user", "content": f"CURRICULUM:\n{context}\n\nWrite {n} questions."},
    ], temperature=0.5)

    questions = []
    for q in out.get("questions", []):
        opts = q.get("options", [])
        idx = q.get("answer_index")
        if q.get("question") and isinstance(opts, list) and len(opts) == 4 and isinstance(idx, int) and 0 <= idx < 4:
            questions.append({k: q.get(k, "") for k in ("question", "options", "answer_index", "explanation", "topic")})
    if not questions:
        raise RuntimeError("Could not generate a quiz right now, please try again.")
    return {"domain": domain, "level": level, "questions": questions[:n],
            "sources": [{"title": c["title"], "url": c["url"]} for c in r["contexts"] if c["url"]]}
