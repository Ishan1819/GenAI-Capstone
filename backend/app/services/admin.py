"""Admin features: unanswered-question queue that feeds the knowledge base, and the insights dashboard."""
import re

import numpy as np

from app.core import llm
from app.database import community, db, vectorstore

CLUSTER_THRESHOLD = 0.72


def resolve_with_answer(item_id: int, answer: str) -> None:
    """Store the admin's answer in the vector store so the chatbot can use it immediately."""
    item = db.get_unanswered(item_id)
    if not item:
        raise KeyError(item_id)
    vectorstore.upsert_chunks([{
        "id": f"faq-{item_id}",
        "text": f"Q: {item['question']}\nA: {answer}",
        "metadata": {"url": "", "title": "ISDIC team answer", "chunk": 0, "source": "faq"},
    }])
    db.resolve_unanswered(item_id, "answered", answer)


def _cluster(questions: list[str]) -> list[dict]:
    if not questions:
        return []
    vecs = np.array(vectorstore.embed(questions))
    vecs = vecs / np.linalg.norm(vecs, axis=1, keepdims=True)
    clusters: list[dict] = []
    for i, v in enumerate(vecs):
        for c in clusters:
            if float(vecs[c["rep"]] @ v) >= CLUSTER_THRESHOLD:
                c["members"].append(i)
                break
        else:
            clusters.append({"rep": i, "members": [i]})
    clusters.sort(key=lambda c: -len(c["members"]))
    return [{"label": questions[c["rep"]], "count": len(c["members"]),
             "examples": [questions[i] for i in c["members"][:3]]} for c in clusters]


def _domain_demand(questions: list[str]) -> list[dict]:
    rows = []
    for name, info in community.DOMAINS.items():
        aliases = [name.lower()] + info["aliases"]
        n = sum(any(re.search(rf"\b{re.escape(a)}\b", q.lower()) for a in aliases) for q in questions)
        rows.append({"domain": name, "questions": n})
    return sorted(rows, key=lambda r: -r["questions"])


def compute_insights(narrative: bool = True) -> dict:
    rows = db.recent_interactions()
    total = len(rows)
    answered = sum(r["answered"] for r in rows)
    asked = [r["standalone"] for r in rows]
    missed = [r["standalone"] for r in rows if not r["answered"]]

    data = {
        "total_questions": total,
        "answered_rate": round(answered / total, 2) if total else None,
        "top_topics": _cluster(asked)[:8],
        "knowledge_gaps": _cluster(missed)[:8],
        "domain_demand": _domain_demand(asked),
        "kb_chunks": vectorstore.collection().count(),
    }
    data["narrative"] = None
    if narrative and total:
        slim = {k: data[k] for k in ("total_questions", "answered_rate", "top_topics", "knowledge_gaps", "domain_demand")}
        data["narrative"] = llm.chat([
            {"role": "system", "content": "You write short insight briefs for the admins of ISDIC, a skill-development community. "
                                          "From the aggregated chatbot data, write three short sections: "
                                          "'What members are asking', 'Knowledge gaps' (topics the chatbot could not answer), "
                                          "'Suggested actions' (curriculum or content changes). Under 200 words. Use only the data given."},
            {"role": "user", "content": str(slim)},
        ], max_tokens=1200)
    return data
