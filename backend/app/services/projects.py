"""Portfolio project ideas grounded in a domain's curriculum, tools and target outcomes."""
from app.core import llm
from app.rag import retrieval

SYSTEM = """You suggest portfolio projects for a student in ISDIC's {domain} community.
ISDIC's target outcomes are live, public, portfolio-ready work. Use ONLY tools and skills that appear in the
curriculum text provided, and fit the student's level and interests. Make each project concrete and finishable.
Reply with JSON only:
{{"projects": [{{"title": "...", "summary": "2 sentences", "difficulty": "Beginner|Intermediate|Advanced",
"duration": "e.g. 2 weekends", "skills": ["..."], "tools": ["..."], "steps": ["4-6 short steps"],
"portfolio_value": "one sentence on what it proves to a recruiter"}}]}}"""


def suggest_projects(domain: str, level: str, interests: str = "", skills: list[str] | None = None) -> dict:
    r = retrieval.retrieve(f"{domain} {level} tools target outcomes projects portfolio", k=6)
    context = "\n\n".join(c["text"] for c in r["contexts"])
    profile = (f"LEVEL: {level}\nINTERESTS: {interests or 'not stated'}\n"
               f"SKILLS ALREADY: {', '.join(skills or []) or 'not stated'}")
    out = llm.chat_json([
        {"role": "system", "content": SYSTEM.format(domain=domain)},
        {"role": "user", "content": f"CURRICULUM:\n{context}\n\nSTUDENT:\n{profile}\n\nSuggest 3 projects."},
    ], temperature=0.6)
    projects = [p for p in out.get("projects", []) if isinstance(p, dict) and p.get("title")]
    if not projects:
        raise RuntimeError("Could not generate project ideas right now, please try again.")
    return {"projects": projects[:3],
            "sources": [{"title": c["title"], "url": c["url"]} for c in r["contexts"] if c["url"]]}
