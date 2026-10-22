"""Hybrid retrieval: vector similarity + knowledge-graph traversal, fused with reciprocal rank fusion."""
from app.core import config
from app.database import vectorstore
from app.knowledge.graph import get_graph

RRF_K = 60


def _fact(e: dict) -> str:
    return f"{e['source_name']} ({e['source_type']}) --{e['relation']}--> {e['target_name']} ({e['target_type']})"


def retrieve(query: str, k: int = 6, mode: str = "hybrid") -> dict:
    """mode: 'hybrid' (graph + vector) or 'vector' (baseline used in the evaluation)."""
    # member profiles reach the chatbot only through graph paths, so they don't crowd out curriculum text
    vec_hits = vectorstore.search(query, k=k, where={"source": {"$ne": "member"}})
    best = vec_hits[0]["distance"] if vec_hits else None
    vec_hits = [h for h in vec_hits if h["distance"] <= config.MAX_DISTANCE]

    scores: dict[str, float] = {}
    via: dict[str, set] = {}
    info: dict[str, dict] = {}
    for rank, h in enumerate(vec_hits):
        scores[h["id"]] = scores.get(h["id"], 0) + 1 / (RRF_K + rank)
        via.setdefault(h["id"], set()).add("vector")
        info[h["id"]] = h

    edges, linked = [], []
    if mode == "hybrid":
        kg = get_graph()
        linked = kg.link_entities(query)
        edges = kg.neighbourhood(linked) if linked else []

        support: dict[str, int] = {}
        for e in edges:
            for cid in e["chunks"]:
                support[cid] = support.get(cid, 0) + 1
        ranked = sorted(support, key=lambda c: -support[c])[:k]
        missing = [c for c in ranked if c not in info]
        for h in vectorstore.get_by_ids(missing):
            info[h["id"]] = h
        for rank, cid in enumerate(ranked):
            if cid in info:
                scores[cid] = scores.get(cid, 0) + 1 / (RRF_K + rank)
                via.setdefault(cid, set()).add("graph")

    top = sorted(scores, key=lambda c: -scores[c])[:k]
    contexts = [{
        "id": cid,
        "text": info[cid]["text"],
        "title": info[cid]["metadata"].get("title", ""),
        "url": info[cid]["metadata"].get("url", ""),
        "via": sorted(via[cid]),
    } for cid in top]

    node_ids = set(linked)
    for e in edges:
        node_ids.update((e["source"], e["target"]))
    kg = get_graph()
    return {
        "contexts": contexts,
        "facts": [_fact(e) for e in edges],
        "graph": {
            "nodes": [{"id": n, "name": kg.g.nodes[n]["name"], "type": kg.g.nodes[n]["type"]} for n in node_ids],
            "edges": [{"source": e["source"], "target": e["target"], "relation": e["relation"]} for e in edges],
        },
        "sufficient": bool(contexts) or bool(edges),
        "best_distance": best,
    }
