"""Session plan generator for chapter leads: a ready-to-run plan for one curriculum activity."""
from app.core import llm
from app.rag import retrieval

SYSTEM = """You are an experienced ISDIC chapter lead planning a session for the {domain} community.
ISDIC sessions are hands-on: every session ends with students having done something real, no slides-only sessions.
Use ONLY tools and topics that appear in the curriculum text provided. Fit the plan exactly into the duration.
Reply with JSON only:
{{"title": "...", "summary": "2 sentences", "audience": "...",
 "objectives": ["3-5 learning objectives"], "prerequisites": ["..."],
 "agenda": [{{"time": "0:00-0:15", "segment": "...", "activity": "what the lead and students do"}}],
 "lab": {{"title": "...", "steps": ["5-8 hands-on steps"], "tools": ["..."]}},
 "quiz": [{{"question": "...", "answer": "..."}}],
 "materials": ["what to prepare beforehand"],
 "follow_up": "homework or next session suggestion"}}"""


def generate_plan(domain: str, topic: str, level: str, duration_hours: float, fmt: str, notes: str = "") -> dict:
    r = retrieval.retrieve(f"{domain} {topic} {level} workshop lab tools", k=6)
    context = "\n\n".join(c["text"] for c in r["contexts"])
    request = (f"TOPIC: {topic}\nFORMAT: {fmt}\nLEVEL: {level}\nDURATION: {duration_hours} hours\n"
               f"EXTRA NOTES FROM THE LEAD: {notes or 'none'}\nInclude 3 quick quiz questions.")
    out = llm.chat_json([
        {"role": "system", "content": SYSTEM.format(domain=domain)},
        {"role": "user", "content": f"CURRICULUM:\n{context}\n\n{request}"},
    ], temperature=0.4)
    if not out.get("title") or not out.get("agenda"):
        raise RuntimeError("Could not generate a session plan right now, please try again.")
    out["sources"] = [{"title": c["title"], "url": c["url"]} for c in r["contexts"] if c["url"]]
    return out
