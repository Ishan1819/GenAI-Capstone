"""Personalised learning path: graph supplies the module order, LLM turns it into a roadmap."""
import networkx as nx

from app.core import llm
from app.rag import retrieval
from app.knowledge.graph import get_graph, tokens

SYSTEM = """You design learning roadmaps using ONLY the ISDIC curriculum supplied below.
Do not invent modules or tools that are not in the supplied material.
Order the steps so prerequisites come first and skip what the learner already knows.
Reply with JSON only:
{"summary": "2-3 sentence overview", "steps": [{"order": 1, "title": "...", "level": "Beginner|Intermediate|Advanced|unknown", "why": "why this step for this learner", "skills_gained": ["..."]}]}"""


def _candidate_modules(goal: str, domain: str, known: list[str]) -> list[str]:
    kg = get_graph()
    anchors = kg.link_entities(f"{domain} {goal}")
    modules: set[str] = set()
    for a in anchors:
        if kg.g.nodes[a]["type"] == "Module":
            modules.add(a)
        for m in kg.successors(a, "HAS_MODULE"):
            modules.add(m)

    known_tokens = [tokens(k) for k in known if k.strip()]

    def already_known(m: str) -> bool:
        names = [kg.g.nodes[m]["name"]] + [kg.g.nodes[s]["name"] for s in kg.successors(m, "TEACHES_SKILL")]
        return any(kt and kt <= tokens(n) or tokens(n) and tokens(n) <= kt for n in names for kt in known_tokens)

    modules = {m for m in modules if not already_known(m)}
    sub = nx.DiGraph()
    sub.add_nodes_from(modules)
    for m in modules:
        for _, nxt, k in kg.g.out_edges(m, keys=True):
            if k == "PREREQUISITE_OF" and nxt in modules:
                sub.add_edge(m, nxt)
    try:
        return list(nx.topological_sort(sub))
    except nx.NetworkXUnfeasible:
        return list(modules)


def build_path(goal: str, current_skills: list[str], domain: str = "") -> dict:
    kg = get_graph()
    ordered = _candidate_modules(goal, domain, current_skills)
    r = retrieval.retrieve(f"{domain} {goal} curriculum modules levels", k=6)

    mods = []
    for m in ordered:
        levels = [kg.g.nodes[l]["name"] for l in kg.successors(m, "AT_LEVEL")]
        mods.append(f"- {kg.g.nodes[m]['name']}" + (f" (level: {', '.join(levels)})" if levels else ""))
    context = (
        f"LEARNER GOAL: {goal}\nDOMAIN INTEREST: {domain or 'not specified'}\n"
        f"ALREADY KNOWS: {', '.join(current_skills) or 'nothing stated'}\n\n"
        "CURRICULUM MODULES IN PREREQUISITE ORDER (from the knowledge graph):\n" + ("\n".join(mods) or "(none found)")
        + "\n\nCURRICULUM TEXT:\n" + "\n\n".join(c["text"] for c in r["contexts"])
    )
    out = llm.chat_json([{"role": "system", "content": SYSTEM}, {"role": "user", "content": context}])
    return {
        "summary": out.get("summary", ""),
        "steps": out.get("steps", []),
        "sources": [{"title": c["title"], "url": c["url"]} for c in r["contexts"] if c["url"]],
    }
