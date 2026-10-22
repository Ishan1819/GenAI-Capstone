"""Module 2: natural-language community search with structured filters.

"beginner cybersecurity events in Pune" -> {entity_type: event, domain: Cybersecurity, level: Beginner, chapter: Pune}
plus a semantic query, executed as a filtered vector search over ChromaDB.
"""
import re
from datetime import date

from app.core import llm
from app.database import community, vectorstore

TYPE_ALIASES = {
    "event": ["event", "events", "workshop", "workshops", "session", "sessions", "hackathon", "hackathons", "webinar",
              "webinars", "lab", "labs", "sprint", "competition", "ctf", "meetup"],
    "member": ["member", "members", "people", "person", "student", "students", "peer", "peers", "mentor", "mentors",
               "someone", "who"],
    "page": ["page", "pages", "curriculum", "information", "info", "about"],
}
UPCOMING_WORDS = ["upcoming", "next", "future", "coming", "soon", "scheduled"]
FIELDS = ("entity_type", "domain", "chapter", "level")


def _has(q: str, phrase: str) -> bool:
    return re.search(rf"\b{re.escape(phrase)}\b", q) is not None


def parse_rules(query: str) -> dict:
    """Keyword parser: always available, no LLM call."""
    q = query.lower()
    vocab = community.vocabulary()
    pick = lambda options: next((k for k, aliases in options.items() if any(_has(q, a) for a in aliases)), None)
    return {
        "entity_type": pick(TYPE_ALIASES),
        "domain": pick({d: info["aliases"] for d, info in community.DOMAINS.items()}),
        "chapter": pick({c: [c.lower()] for c in vocab["chapters"]}),
        "level": pick(community.LEVEL_ALIASES),
        "upcoming": any(_has(q, w) for w in UPCOMING_WORDS),
        "semantic_query": query,
    }


def parse_llm(query: str) -> dict:
    v = community.vocabulary()
    system = (
        "Convert a search request for the ISDIC community platform into filters.\n"
        f"entity_type: one of {v['entity_types']} or null; domain: one of {v['domains']} or null; "
        f"chapter: one of {v['chapters']} or null; level: one of {v['levels']} or null; "
        "upcoming: true only if the user wants future events.\n"
        "semantic_query: the remaining topic words (skills, interests, subject), or \"\".\n"
        "Only set a filter when the request clearly asks for it. Reply with JSON only:\n"
        '{"entity_type": null, "domain": null, "chapter": null, "level": null, "upcoming": false, "semantic_query": ""}'
    )
    return llm.chat_json([{"role": "system", "content": system}, {"role": "user", "content": query}], max_tokens=800)


def understand(query: str) -> dict:
    """LLM parse validated against the vocabulary; keyword parse fills gaps or replaces it on failure."""
    rules = parse_rules(query)
    try:
        out = parse_llm(query)
    except Exception:
        return {**rules, "parser": "rules"}
    v = community.vocabulary()
    allowed = {"entity_type": v["entity_types"], "domain": v["domains"], "chapter": v["chapters"], "level": v["levels"]}
    parsed = {f: out.get(f) if out.get(f) in allowed[f] else rules[f] for f in FIELDS}
    parsed["upcoming"] = bool(out.get("upcoming")) or rules["upcoming"]
    parsed["semantic_query"] = str(out.get("semantic_query") or "").strip()
    parsed["parser"] = "llm"
    return parsed


def _where(f: dict) -> dict | None:
    conds = []
    if f.get("entity_type") == "page":
        conds.append({"source": {"$in": ["web", "faq"]}})
    elif f.get("entity_type"):
        conds.append({"source": f["entity_type"]})
    else:
        conds.append({"source": {"$in": ["member", "event", "web", "faq"]}})
    for field in ("domain", "chapter", "level"):
        if f.get(field):
            conds.append({field: f[field]})
    if f.get("upcoming"):
        conds.append({"date_int": {"$gte": int(date.today().strftime("%Y%m%d"))}})
    return conds[0] if len(conds) == 1 else {"$and": conds}


def _why(meta: dict, f: dict, semantic: str) -> list[str]:
    reasons = [f"{field.capitalize()}: {meta[field]}" for field in ("domain", "chapter", "level") if f.get(field)]
    if f.get("upcoming") and meta.get("date"):
        reasons.append(f"Upcoming on {meta['date']}")
    words = {w for w in re.findall(r"[a-z0-9+#.]+", semantic.lower()) if len(w) > 1}
    skills = [s for s in meta.get("skills", "").split(", ") if s and set(s.lower().split()) & words]
    if skills:
        reasons.append(f"Mentions {', '.join(skills)}")
    return reasons


def search(query: str, overrides: dict | None = None, k: int = 10, use_llm: bool = True) -> dict:
    query = query.strip()
    if query:
        f = understand(query) if use_llm else {**parse_rules(query), "parser": "rules"}
    else:
        f = {"entity_type": None, "domain": None, "chapter": None, "level": None, "upcoming": False,
             "semantic_query": "", "parser": "none"}
    for key, val in (overrides or {}).items():  # filters chosen in the UI win over parsed ones
        if val not in (None, ""):
            f[key] = val

    text = f["semantic_query"] or query or " ".join(str(f[x]) for x in FIELDS if f.get(x)) or "ISDIC community"
    hits = vectorstore.search(text, k=k, where=_where(f))
    results = []
    for h in hits:
        m = h["metadata"]
        source = m.get("source", "web")
        subtitle = {
            "member": f"{m.get('level')} · {m.get('domain')} · {m.get('chapter')}",
            "event": f"{m.get('event_type')} · {m.get('date')} · {m.get('level')} · {m.get('chapter')}",
        }.get(source, m.get("url", ""))
        results.append({
            "type": "page" if source in ("web", "faq") else source,
            "id": m.get("entity_id") or h["id"],
            "title": m.get("title", ""),
            "subtitle": subtitle,
            "url": m.get("url", ""),
            "snippet": h["text"][:240],
            "relevance": round(1 - h["distance"], 2),
            "why": _why(m, f, f["semantic_query"]),
        })
    return {"understood": f, "results": results}
