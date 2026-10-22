"""Module 3: explainable recommendations of peers, events and curriculum modules.

Candidates come from graph paths (works without interaction history); peers are re-ranked with profile
embedding similarity; the LLM turns each item's graph evidence into a one-line justification.
"""
from collections import defaultdict

import numpy as np

from app.core import llm
from app.database import community, vectorstore
from app.knowledge.graph import get_graph, norm, tokens

PEER_LINKS = {"IN_DOMAIN": 2.0, "ATTENDED": 1.5, "HAS_SKILL": 1.0, "INTERESTED_IN": 1.0, "MEMBER_OF": 1.0, "STUDIES_AT": 0.5}
RANK = community.LEVEL_RANK

EXPLAIN_SYSTEM = """You explain recommendations to a member of ISDIC, a tech skill-development community.
For each item write ONE sentence (max 30 words) addressed to the member as "you", explaining why it fits them.
Use ONLY the evidence given for that item; do not invent facts.
Reply with JSON only: {"<key>": "sentence", ...}"""


def _name(kg, n: str) -> str:
    return kg.g.nodes[n]["name"]


def _peers(kg, me: str, member: dict, k: int) -> list[dict]:
    scores, paths = defaultdict(float), defaultdict(list)
    for rel, weight in PEER_LINKS.items():
        for x in kg.successors(me, rel):
            for p in kg.predecessors(x, rel):
                if p != me and kg.g.nodes[p]["type"] == "Member":
                    scores[p] += weight
                    paths[p].append(f"You —{rel}→ {_name(kg, x)} ←{rel}— {_name(kg, p)}")

    candidates = []
    for p in sorted(scores, key=lambda p: -scores[p])[:15]:
        other = community.member_by_node(p)
        if not other:
            continue
        if other["domain"] == member["domain"] and RANK[other["level"]] > RANK[member["level"]]:
            scores[p] += 1.0
            paths[p].append(f"{other['name']} —AT_LEVEL→ {other['level']} (ahead of you in {member['domain']}: possible mentor)")
        candidates.append((p, other))
    if not candidates:
        return []

    vecs = np.array(vectorstore.embed([community.member_text(member)] + [community.member_text(o) for _, o in candidates]))
    vecs /= np.linalg.norm(vecs, axis=1, keepdims=True)
    sims = vecs[1:] @ vecs[0]
    top = max(scores[p] for p, _ in candidates)
    ranked = sorted(zip(candidates, sims), key=lambda t: -(0.7 * scores[t[0][0]] / top + 0.3 * float(t[1])))[:k]
    return [{"id": o["id"], "name": o["name"], "subtitle": f"{o['role']} · {o['level']} · {o['domain']} · {o['chapter']}",
             "score": round(0.7 * scores[p] / top + 0.3 * float(s), 2), "evidence": paths[p][:6]}
            for (p, o), s in ranked]


def _events(kg, me: str, member: dict, k: int) -> list[dict]:
    attended = set(kg.successors(me, "ATTENDED"))
    my_skills = set(kg.successors(me, "HAS_SKILL"))
    my_domains = set(kg.successors(me, "IN_DOMAIN"))
    my_chapters = set(kg.successors(me, "MEMBER_OF"))
    out = []
    for ev in community.events():
        e = norm(ev["name"])
        if not community.is_upcoming(ev) or e not in kg.g or e in attended:
            continue
        score, ev_paths = 0.0, []
        for d in set(kg.successors(e, "IN_DOMAIN")) & my_domains:
            score += 2.0
            ev_paths.append(f"You —IN_DOMAIN→ {_name(kg, d)} ←IN_DOMAIN— {ev['name']}")
        for c in set(kg.successors(e, "HELD_IN")) & my_chapters:
            score += 1.5
            ev_paths.append(f"You —MEMBER_OF→ {_name(kg, c)} ←HELD_IN— {ev['name']}")
        skills = set(kg.successors(e, "COVERS_SKILL"))
        for s in skills & my_skills:
            score += 0.5
            ev_paths.append(f"You —HAS_SKILL→ {_name(kg, s)} ←COVERS_SKILL— {ev['name']} (builds on it)")
        if my_domains & set(kg.successors(e, "IN_DOMAIN")):
            for s in sorted(skills - my_skills)[:2]:
                score += 0.75
                ev_paths.append(f"{ev['name']} —COVERS_SKILL→ {_name(kg, s)} (new skill for you)")
        gap = RANK[ev["level"]] - RANK[member["level"]]
        if gap == 0:
            score += 1.5
            ev_paths.append(f"{ev['name']} —AT_LEVEL→ {ev['level']} (your level)")
        elif gap == 1:
            score += 1.0
            ev_paths.append(f"{ev['name']} —AT_LEVEL→ {ev['level']} (your next level)")
        elif gap < 0:
            score -= 1.0
        if score >= 2.5:
            out.append({"id": ev["id"], "name": ev["name"],
                        "subtitle": f"{ev['type']} · {ev['date']} · {ev['level']} · {ev['chapter']} · {ev['mode']}",
                        "score": round(score, 2), "evidence": ev_paths})
    return sorted(out, key=lambda x: -x["score"])[:k]


def _modules(kg, member: dict, k: int) -> list[dict]:
    """Curriculum modules from the scraped-site graph, matched to the member's domain and level."""
    aliases = [member["domain"]] + community.DOMAINS[member["domain"]]["aliases"]
    domain_nodes = [n for n in kg.nodes_of_type("Domain")
                    if any(tokens(a) and tokens(a) <= tokens(_name(kg, n)) for a in aliases)]
    my_skills = {norm(s) for s in member["skills"]}
    out, seen = [], set()
    for d in domain_nodes:
        for mod in kg.successors(d, "HAS_MODULE"):
            if mod in seen:
                continue
            seen.add(mod)
            teaches = kg.successors(mod, "TEACHES_SKILL")
            new = [s for s in teaches if s not in my_skills]
            if teaches and not new:
                continue
            score, m_paths = 1.0 + 0.5 * len(new), [f"{_name(kg, d)} —HAS_MODULE→ {_name(kg, mod)}"]
            for lvl in (_name(kg, l).title() for l in kg.successors(mod, "AT_LEVEL")):
                if lvl in RANK:
                    gap = RANK[lvl] - RANK[member["level"]]
                    score += {0: 1.5, 1: 1.0}.get(gap, -1.5 if gap < 0 else 0)
                    m_paths.append(f"{_name(kg, mod)} —AT_LEVEL→ {lvl}")
            m_paths += [f"{_name(kg, mod)} —TEACHES_SKILL→ {_name(kg, s)} (you don't have this yet)" for s in new[:3]]
            out.append({"id": mod, "name": _name(kg, mod), "subtitle": _name(kg, d),
                        "score": round(score, 2), "evidence": m_paths})
    return sorted(out, key=lambda x: -x["score"])[:k]


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
    kg = get_graph()
    me = norm(member["name"])
    if me not in kg.g:
        raise ValueError("Member is not in the knowledge graph. Run `python -m scripts.generate_demo_data` and restart the API.")

    groups = {"peers": _peers(kg, me, member, k), "events": _events(kg, me, member, k), "modules": _modules(kg, member, k)}
    if explain:
        _explain(member, groups)
    notes = []
    if not groups["modules"]:
        notes.append("No curriculum modules for this domain in the graph yet. Run `python -m scripts.build_kb` "
                     "to extract them from the scraped site.")
    return {"member": member, **groups, "notes": notes}
