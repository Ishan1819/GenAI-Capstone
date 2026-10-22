"""Knowledge graph over ISDIC entities (NetworkX, persisted as JSON)."""
import hashlib
import json
import re
from itertools import chain

import networkx as nx

from app.core import config, llm

ENTITY_TYPES = ["Organization", "Domain", "Level", "Module", "Skill", "Tool", "Event",
                "Partner", "Mentor", "Chapter", "Location", "Program"]
RELATIONS = ["HAS_MODULE", "AT_LEVEL", "PREREQUISITE_OF", "TEACHES_SKILL", "USES_TOOL",
             "OFFERS", "HOSTS_EVENT", "PARTNERS_WITH", "MENTORED_BY", "LOCATED_IN"]
# Types/relations loaded from structured community records (demo members and events), not extracted by the LLM
RECORD_TYPES = ["Member", "College", "Interest"]
RECORD_RELATIONS = ["MEMBER_OF", "STUDIES_AT", "IN_DOMAIN", "HAS_SKILL", "INTERESTED_IN",
                    "ATTENDED", "COVERS_SKILL", "HELD_IN"]
ALL_TYPES = set(ENTITY_TYPES + RECORD_TYPES)
ALL_RELATIONS = set(RELATIONS + RECORD_RELATIONS)
STOPWORDS = {"and", "the", "of", "a", "in", "for", "to", "is", "are", "what", "which", "who", "how"}

EXTRACT_SYSTEM = f"""You extract a knowledge graph about ISDIC (Industry Skill Development and Innovation Cell) from text.
Allowed entity types: {", ".join(ENTITY_TYPES)}.
Allowed relations: {", ".join(RELATIONS)}.
Meaning: Domain HAS_MODULE Module; Module AT_LEVEL Level; Module PREREQUISITE_OF Module (head must be done first);
Module TEACHES_SKILL Skill; Module/Domain USES_TOOL Tool; Program/Chapter/Organization OFFERS Domain/Event/Program;
Domain/Chapter HOSTS_EVENT Event; Organization PARTNERS_WITH Partner; Domain MENTORED_BY Mentor; Chapter LOCATED_IN Location.
The text is split into blocks labelled [C1], [C2], ... Return JSON only:
{{"triples": [{{"src": "C1", "head": "...", "head_type": "...", "relation": "...", "tail": "...", "tail_type": "..."}}]}}
Rules: use short canonical names as written in the text; only facts stated explicitly; at most 15 triples per block;
return {{"triples": []}} if there is nothing to extract."""


def norm(name: str) -> str:
    s = re.sub(r"[^a-z0-9+#. ]+", " ", name.lower().replace("&", " and "))
    return re.sub(r"\s+", " ", s).strip()


def tokens(name: str) -> set[str]:
    return {t.strip(".") for t in norm(name).split()} - STOPWORDS - {""}


class KnowledgeGraph:
    def __init__(self):
        self.g = nx.MultiDiGraph()

    # ---- construction ----
    def _node(self, name: str, ntype: str, chunk_id: str) -> str:
        nid = norm(name)
        if nid not in self.g:
            self.g.add_node(nid, name=name.strip(), type=ntype, chunks=[])
        if chunk_id not in self.g.nodes[nid]["chunks"]:
            self.g.nodes[nid]["chunks"].append(chunk_id)
        return nid

    def add_triple(self, head, head_type, relation, tail, tail_type, chunk_id) -> bool:
        if head_type not in ALL_TYPES or tail_type not in ALL_TYPES or relation not in ALL_RELATIONS:
            return False
        if not norm(head) or not norm(tail) or norm(head) == norm(tail):
            return False
        h, t = self._node(head, head_type, chunk_id), self._node(tail, tail_type, chunk_id)
        if self.g.has_edge(h, t, key=relation):
            chunks = self.g[h][t][relation]["chunks"]
            if chunk_id not in chunks:
                chunks.append(chunk_id)
        else:
            self.g.add_edge(h, t, key=relation, relation=relation, chunks=[chunk_id])
        return True

    def remove_source(self, prefixes: tuple[str, ...]) -> None:
        """Drop everything that came only from chunks with these id prefixes (used when regenerating demo data)."""
        for u, v, k, d in list(self.g.edges(keys=True, data=True)):
            d["chunks"] = [c for c in d["chunks"] if not c.startswith(prefixes)]
            if not d["chunks"]:
                self.g.remove_edge(u, v, key=k)
        for n, d in list(self.g.nodes(data=True)):
            d["chunks"] = [c for c in d["chunks"] if not c.startswith(prefixes)]
            if not d["chunks"]:
                self.g.remove_node(n)

    def predecessors(self, node_id: str, relation: str) -> list[str]:
        return [u for u, _, k in self.g.in_edges(node_id, keys=True) if k == relation]

    def extract_batch(self, batch: list[dict], cache: dict) -> int:
        """Run LLM extraction over a batch of chunks; returns triples added."""
        key = hashlib.sha1("".join(c["id"] for c in batch).encode()).hexdigest()
        if key not in cache:
            body = "\n\n".join(f"[C{i + 1}]\n{c['text']}" for i, c in enumerate(batch))
            data = llm.chat_json([{"role": "system", "content": EXTRACT_SYSTEM},
                                  {"role": "user", "content": body}])
            cache[key] = data.get("triples", []) if isinstance(data, dict) else []
        added = 0
        for tr in cache[key]:
            try:
                idx = int(str(tr.get("src", "C1")).lstrip("Cc")) - 1
                chunk_id = batch[idx if 0 <= idx < len(batch) else 0]["id"]
                added += self.add_triple(tr["head"], tr["head_type"], tr["relation"],
                                         tr["tail"], tr["tail_type"], chunk_id)
            except (KeyError, ValueError, TypeError):
                continue
        return added

    def build(self, chunks: list[dict], batch_chars: int = 3500, max_batches: int | None = None) -> None:
        cache = json.loads(config.EXTRACTION_CACHE.read_text("utf-8")) if config.EXTRACTION_CACHE.exists() else {}
        batches, cur, size = [], [], 0
        for c in chunks:
            if len(c["text"]) < 120:
                continue
            if cur and size + len(c["text"]) > batch_chars:
                batches.append(cur)
                cur, size = [], 0
            cur.append(c)
            size += len(c["text"])
        if cur:
            batches.append(cur)

        for n, batch in enumerate(batches[:max_batches], 1):
            try:
                added = self.extract_batch(batch, cache)
            except llm.LLMAuthError:
                raise  # every later batch would fail the same way
            except Exception as e:  # keep going; the cache makes reruns resume
                print(f"  batch {n}/{len(batches)} failed: {e}")
                continue
            config.EXTRACTION_CACHE.parent.mkdir(parents=True, exist_ok=True)
            config.EXTRACTION_CACHE.write_text(json.dumps(cache), "utf-8")
            print(f"  batch {n}/{len(batches)}: +{added} triples "
                  f"({self.g.number_of_nodes()} nodes, {self.g.number_of_edges()} edges)")

    # ---- persistence ----
    def save(self) -> None:
        config.GRAPH_PATH.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "nodes": [{"id": n, **d} for n, d in self.g.nodes(data=True)],
            "edges": [{"source": u, "target": v, "relation": k, "chunks": d["chunks"]}
                      for u, v, k, d in self.g.edges(keys=True, data=True)],
        }
        config.GRAPH_PATH.write_text(json.dumps(data, ensure_ascii=False), "utf-8")

    @classmethod
    def load(cls) -> "KnowledgeGraph":
        kg = cls()
        if config.GRAPH_PATH.exists():
            data = json.loads(config.GRAPH_PATH.read_text("utf-8"))
            for n in data["nodes"]:
                kg.g.add_node(n["id"], name=n["name"], type=n["type"], chunks=n["chunks"])
            for e in data["edges"]:
                kg.g.add_edge(e["source"], e["target"], key=e["relation"], relation=e["relation"], chunks=e["chunks"])
        return kg

    # ---- querying ----
    def link_entities(self, query: str, limit: int = 6) -> list[str]:
        q = tokens(query)
        hits = [n for n, d in self.g.nodes(data=True)
                if d["type"] != "Organization" and (t := tokens(d["name"])) and t <= q and len(norm(d["name"])) >= 3]
        hits.sort(key=lambda n: -len(tokens(self.g.nodes[n]["name"])))
        return hits[:limit]

    def _edge(self, u, v, k, d) -> dict:
        nu, nv = self.g.nodes[u], self.g.nodes[v]
        return {"source": u, "source_name": nu["name"], "source_type": nu["type"], "relation": k,
                "target": v, "target_name": nv["name"], "target_type": nv["type"], "chunks": d["chunks"]}

    def neighbourhood(self, node_ids: list[str], hops: int = 2, max_edges: int = 30) -> list[dict]:
        edges, seen, visited, frontier = [], set(), set(node_ids), list(node_ids)
        for _ in range(hops):
            nxt = []
            for n in frontier:
                for u, v, k, d in chain(self.g.out_edges(n, keys=True, data=True),
                                        self.g.in_edges(n, keys=True, data=True)):
                    if (u, v, k) in seen:
                        continue
                    seen.add((u, v, k))
                    edges.append(self._edge(u, v, k, d))
                    for m in (u, v):
                        if m not in visited:
                            visited.add(m)
                            nxt.append(m)
            frontier = nxt
        return edges[:max_edges]

    def successors(self, node_id: str, relation: str) -> list[str]:
        return [v for _, v, k in self.g.out_edges(node_id, keys=True) if k == relation]

    def nodes_of_type(self, ntype: str) -> list[str]:
        return [n for n, d in self.g.nodes(data=True) if d["type"] == ntype]

    def subgraph(self, focus: str | None = None, types: set[str] | None = None, limit: int = 80) -> dict:
        """Nodes/edges for the explorer: a node's neighbourhood, or the best-connected nodes overall."""
        allowed = lambda n: not types or self.g.nodes[n]["type"] in types
        if focus and focus in self.g:
            nodes = [focus] + [m for m in nx.all_neighbors(self.g, focus) if allowed(m)]
            nodes = list(dict.fromkeys(nodes))[:limit]
        else:
            ranked = sorted((n for n in self.g if allowed(n)), key=lambda n: -self.g.degree(n))
            nodes = ranked[:limit]
        keep = set(nodes)
        edges = [{"source": u, "target": v, "relation": k}
                 for u, v, k in self.g.edges(keys=True) if u in keep and v in keep]
        return {
            "nodes": [{"id": n, "name": self.g.nodes[n]["name"], "type": self.g.nodes[n]["type"],
                       "degree": self.g.degree(n)} for n in nodes],
            "edges": edges,
        }

    def node_detail(self, node_id: str) -> dict | None:
        if node_id not in self.g:
            return None
        d = self.g.nodes[node_id]
        out_rel: dict[str, list] = {}
        for _, v, k in self.g.out_edges(node_id, keys=True):
            out_rel.setdefault(k, []).append({"id": v, "name": self.g.nodes[v]["name"]})
        in_rel: dict[str, list] = {}
        for u, _, k in self.g.in_edges(node_id, keys=True):
            in_rel.setdefault(k, []).append({"id": u, "name": self.g.nodes[u]["name"]})
        return {"id": node_id, "name": d["name"], "type": d["type"], "degree": self.g.degree(node_id),
                "outgoing": out_rel, "incoming": in_rel, "sources": len(d["chunks"])}

    def find(self, query: str, limit: int = 15) -> list[dict]:
        q = norm(query)
        hits = [n for n in self.g if q and q in n]
        hits.sort(key=lambda n: (not n.startswith(q), -self.g.degree(n)))
        return [{"id": n, "name": self.g.nodes[n]["name"], "type": self.g.nodes[n]["type"]} for n in hits[:limit]]

    def stats(self) -> dict:
        counts: dict[str, int] = {}
        for _, d in self.g.nodes(data=True):
            counts[d["type"]] = counts.get(d["type"], 0) + 1
        return {"nodes": self.g.number_of_nodes(), "edges": self.g.number_of_edges(), "by_type": counts}


_graph = None


def get_graph() -> KnowledgeGraph:
    global _graph
    if _graph is None:
        _graph = KnowledgeGraph.load()
    return _graph
