"""Personalised learning path: retrieve the track's curriculum, LLM orders it into a roadmap."""
from app.core import llm
from app.database import community, vectorstore
from app.rag import retrieval
from app.services import search

SYSTEM = """You design learning roadmaps using ONLY the ISDIC curriculum supplied below.
Do not invent modules or tools that are not in the supplied material.
If a TRACK is given, include only steps from that track; ignore material about other tracks.
Follow the curriculum's level order (Level 01 -> 02 -> 03) and skip what the learner already knows.
Reply with JSON only:
{"summary": "2-3 sentence overview", "steps": [{"order": 1, "title": "...", "level": "Beginner|Intermediate|Advanced|unknown", "why": "why this step for this learner", "skills_gained": ["..."]}]}"""


def detect_domain(goal: str, domain: str = "") -> str | None:
    """The track the learner means: the chosen domain if it names one, else keywords in the goal."""
    exact = next((d for d in community.DOMAINS if d.lower() == domain.strip().lower()), None)
    return exact or search.parse_rules(f"{domain} {goal}")["domain"]


def _track_curriculum(track: str) -> list[dict]:
    """All chunks of the track's own curriculum page, in page order."""
    title = community.DOMAINS[track].get("curriculum_page")
    chunks = vectorstore.get_where({"title": title}) if title else []
    chunks.sort(key=lambda c: c["metadata"].get("chunk", 0))
    return [{"text": c["text"], "title": c["metadata"].get("title", ""), "url": c["metadata"].get("url", "")}
            for c in chunks]


def build_path(goal: str, current_skills: list[str], domain: str = "") -> dict:
    track = detect_domain(goal, domain)
    contexts = _track_curriculum(track) if track else []
    if not contexts:  # no track recognised: fall back to semantic search over all pages
        contexts = retrieval.retrieve(f"{domain} {goal} skill progression levels months tools", k=6,
                                      where={"source": "web"})["contexts"]
    context = (
        f"LEARNER GOAL: {goal}\nTRACK: {track or 'not specified'}\n"
        f"ALREADY KNOWS: {', '.join(current_skills) or 'nothing stated'}\n\n"
        "CURRICULUM TEXT:\n" + ("\n\n".join(c["text"] for c in contexts) or "(nothing found)")
    )
    out = llm.chat_json([{"role": "system", "content": SYSTEM}, {"role": "user", "content": context}],
                        max_tokens=1200)
    sources = list({c["url"]: {"title": c["title"], "url": c["url"]} for c in contexts if c["url"]}.values())
    return {"summary": out.get("summary", ""), "steps": out.get("steps", []), "sources": sources}
