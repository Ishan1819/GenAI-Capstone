"""Module 3: explainable recommendations of peers, events and curriculum to study next.

Peers and events are scored from shared attributes in the community records (works without interaction history);
peers are re-ranked by profile embedding similarity; curriculum comes from RAG over ISDIC's pages. The LLM turns each
item's evidence into a one-line justification.
"""
import numpy as np

from app.core import llm
from app.database import community, vectorstore

RANK = community.LEVEL_RANK

EXPLAIN_SYSTEM = """You explain recommendations to a member of ISDIC, a tech skill-development community.
For each item write ONE sentence (max 30 words) addressed to the member as "you", explaining why it fits them.
Use ONLY the evidence given for that item; do not invent facts.
Reply with JSON only: {"<key>": "sentence", ...}"""


def _peers(member: dict, k: int) -> list[dict]:
    candidates = []
    for o in community.members():
        if o["id"] == member["id"]:
            continue
        score, why = 0.0, []
        if o["domain"] == member["domain"]:
            score += 2.0
            why.append(f"Both in the {o['domain']} community")
        shared = sorted(set(o["skills"]) & set(member["skills"]))
        if shared:
            score += 1.0 * len(shared)
            why.append(f"Both know {', '.join(shared)}")
        events = sorted(set(o["attended"]) & set(member["attended"]))
        if events:
            score += 1.5 * len(events)
            why.append(f"Both attended {', '.join(events)}")
        interests = sorted(set(o["interests"]) & set(member["interests"]))
        if interests:
            score += 1.0 * len(interests)
            why.append(f"Both interested in {', '.join(interests)}")
        if o["chapter"] == member["chapter"]:
            score += 1.0
            why.append(f"Same chapter: {o['chapter']}")
        if o["college"] == member["college"]:
            score += 0.5
            why.append(f"Same college: {o['college']}")
        if o["domain"] == member["domain"] and RANK[o["level"]] > RANK[member["level"]]:
            score += 1.0
            why.append(f"{o['level']} in {o['domain']}, ahead of you: possible mentor")
        if score > 0:
            candidates.append((score, o, why))
    candidates = sorted(candidates, key=lambda c: -c[0])[:15]
    if not candidates:
        return []

    vecs = np.array(vectorstore.embed([community.member_text(member)] + [community.member_text(o) for _, o, _ in candidates]))
    vecs /= np.linalg.norm(vecs, axis=1, keepdims=True)
    sims = vecs[1:] @ vecs[0]
    top = max(c[0] for c in candidates)
    ranked = sorted(zip(candidates, sims), key=lambda t: -(0.7 * t[0][0] / top + 0.3 * float(t[1])))[:k]
    return [{"id": o["id"], "name": o["name"], "subtitle": f"{o['role']} · {o['level']} · {o['domain']} · {o['chapter']}",
             "score": round(0.7 * s / top + 0.3 * float(sim), 2), "evidence": why[:6]}
            for (s, o, why), sim in ranked]


def _events(member: dict, k: int) -> list[dict]:
    out = []
    for ev in community.events():
        if not community.is_upcoming(ev) or ev["name"] in member["attended"]:
            continue
        score, why = 0.0, []
        if ev["domain"] == member["domain"]:
            score += 2.0
            why.append(f"Run by your {ev['domain']} community")
        if ev["chapter"] == member["chapter"]:
            score += 1.5
            why.append(f"In your chapter ({ev['chapter']})")
        known = [s for s in ev["skills"] if s in member["skills"]]
        if known:
            score += 0.5 * len(known)
            why.append(f"Builds on what you know: {', '.join(known)}")
        if ev["domain"] == member["domain"]:
            new = [s for s in ev["skills"] if s not in member["skills"]][:2]
            if new:
                score += 0.75 * len(new)
                why.append(f"Teaches new skills: {', '.join(new)}")
        gap = RANK[ev["level"]] - RANK[member["level"]]
        if gap == 0:
            score += 1.5
            why.append(f"{ev['level']} level, matches yours")
        elif gap == 1:
            score += 1.0
            why.append(f"{ev['level']} level, your next step")
        elif gap < 0:
            score -= 1.0
        if score >= 2.5:
            out.append({"id": ev["id"], "name": ev["name"],
                        "subtitle": f"{ev['type']} · {ev['date']} · {ev['level']} · {ev['chapter']} · {ev['mode']}",
                        "score": round(score, 2), "evidence": why})
    return sorted(out, key=lambda x: -x["score"])[:k]


def _curriculum(member: dict, k: int) -> list[dict]:
    """Curriculum passages from isdic.in for the member's domain at their current/next level."""
    nxt = community.LEVELS[min(RANK[member["level"]] + 1, 2)]
    hits = vectorstore.search(f"{member['domain']} curriculum skill progression {member['level']} {nxt} level",
                              k=k, where={"source": "web"})
    return [{"id": h["id"], "name": h["metadata"].get("title", "").replace(" | ISDIC", ""),
             "subtitle": h["metadata"].get("url", ""), "url": h["metadata"].get("url", ""),
             "score": round(1 - h["distance"], 2),
             "evidence": [f"Curriculum text: {h['text'][:400]}", f"You are {member['level']} in {member['domain']}"]}
            for h in hits]


def _explain(member: dict, groups: dict[str, list[dict]]) -> None:
    keyed = {f"{kind[0]}{i}": item for kind, items in groups.items() for i, item in enumerate(items, 1)}
    if not keyed:
        return
    lines = "\n".join(f"{key}: {item['name']} | evidence: {'; '.join(item['evidence'][:5])}" for key, item in keyed.items())
    try:
        out = llm.chat_json([{"role": "system", "content": EXPLAIN_SYSTEM},
                             {"role": "user", "content": f"MEMBER: {community.member_text(member)}\n\nITEMS:\n{lines}"}])
    except Exception:
        out = {}
    for key, item in keyed.items():
        item["explanation"] = str(out.get(key) or "Suggested because: " + "; ".join(item["evidence"][:3]))


def recommend(member_id: str, k: int = 5, explain: bool = True) -> dict:
    member = community.member(member_id)
    if not member:
        raise KeyError(member_id)
    groups = {"peers": _peers(member, k), "events": _events(member, k), "modules": _curriculum(member, 3)}
    if explain:
        _explain(member, groups)
    return {"member": member, **groups, "notes": []}
