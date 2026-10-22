"""Generate fictional demo members and events, then load them into ChromaDB and the knowledge graph.

Run from backend/:  python -m scripts.generate_demo_data [--members 72] [--seed 42]
All people and colleges are made up. Re-running replaces the previous demo data.
"""
import argparse
import json
import random
from datetime import date, timedelta

from app.core import config
from app.database import community, vectorstore
from app.knowledge.graph import KnowledgeGraph

FIRST = ["Aarav", "Vivaan", "Aditya", "Arjun", "Sai", "Reyansh", "Krishna", "Ishaan", "Rohan", "Kabir",
         "Atharva", "Omkar", "Yash", "Pranav", "Siddharth", "Tanmay", "Harsh", "Nikhil", "Varun", "Kunal",
         "Ananya", "Diya", "Saanvi", "Aditi", "Isha", "Kavya", "Meera", "Riya", "Sneha", "Pooja",
         "Shruti", "Tanvi", "Neha", "Gauri", "Mrunal", "Sakshi", "Prachi", "Janhavi", "Aarya", "Nidhi"]
LAST = ["Sharma", "Patil", "Kulkarni", "Deshpande", "Joshi", "Iyer", "Reddy", "Nair", "Gupta", "Mehta",
        "Shinde", "Pawar", "Jadhav", "Bhosale", "Rao", "Menon", "Verma", "Chavan", "Gokhale", "Rane",
        "Kapoor", "Agarwal", "Mishra", "Pandey", "Naik"]
COLLEGES = {
    "Pune": ["Sahyadri Institute of Technology", "Deccan College of Engineering"],
    "Mumbai": ["Konkan Institute of Technology", "Western Coast Engineering College"],
    "Chennai": ["Marina Institute of Technology", "Coromandel College of Engineering"],
    "Nashik": ["Godavari Institute of Engineering"],
    "Bangalore": ["Garden City Institute of Technology", "Deccan Plateau Engineering College"],
    "Hyderabad": ["Charminar Institute of Technology"],
}
INTERESTS = ["healthcare", "fintech", "open source", "gaming", "edtech", "agritech", "research", "startups",
             "competitive programming", "CTFs", "generative AI", "sustainability", "robotics"]
EVENT_TYPES = {
    "Workshop": ("Hands-on session with guided exercises.", "In-person"),
    "Lab Session": ("Practical lab with a take-home assignment.", "In-person"),
    "Webinar": ("Talk by an industry professional from the advisory board, followed by Q&A.", "Online"),
    "Hackathon": ("24-hour team build challenge with mentors and prizes.", "In-person"),
    "Open-Source Sprint": ("Contribute to real open-source projects with maintainers.", "Hybrid"),
}
FLAGSHIP = {"Cybersecurity": "CyberShield CTF", "AI and ML": "GenAI Summit",
            "Cloud and DevOps": "CloudOps Con", "Software Development": "DevFest Build-a-thon"}


def make_events(rng: random.Random) -> list[dict]:
    today, events = date.today(), []
    for domain, info in community.DOMAINS.items():
        specs = [(rng.choice(list(EVENT_TYPES)), None) for _ in range(7)] + [("Flagship Event", FLAGSHIP[domain])]
        for etype, fixed_name in specs:
            chapter = "Pune" if fixed_name else rng.choice(list(COLLEGES))
            skills = rng.sample(info["skills"], 3)
            level = "Intermediate" if fixed_name else rng.choices(community.LEVELS, [0.45, 0.35, 0.2])[0]
            day = today + timedelta(days=rng.randint(-150, 150))
            name = fixed_name or f"{skills[0]} & {skills[1]} {etype} ({chapter})"
            desc, mode = EVENT_TYPES.get(etype, ("The domain's yearly flagship event with talks, competitions and demos.", "In-person"))
            events.append({"name": f"{name} {day.year}" if fixed_name else name, "type": etype, "domain": domain,
                           "chapter": chapter, "level": level, "date": day.isoformat(), "mode": mode,
                           "skills": skills, "description": desc})
    events.sort(key=lambda e: e["date"])
    for i, e in enumerate(events, 1):
        e["id"] = f"E{i:03d}"
    return events


def make_members(rng: random.Random, n: int, events: list[dict]) -> list[dict]:
    names = rng.sample([f"{f} {l}" for f in FIRST for l in LAST], n)
    past = [e for e in events if not community.is_upcoming(e)]
    members = []
    for i, name in enumerate(names, 1):
        domain = rng.choice(list(community.DOMAINS))
        level = rng.choices(community.LEVELS, [0.45, 0.35, 0.2])[0]
        chapter = rng.choice(list(COLLEGES))
        n_skills = {"Beginner": 2, "Intermediate": 4, "Advanced": 6}[level] + rng.randint(0, 1)
        skills = rng.sample(community.DOMAINS[domain]["skills"], n_skills)
        if rng.random() < 0.3:  # some cross-domain skills
            other = rng.choice([d for d in community.DOMAINS if d != domain])
            extra = rng.choice(community.DOMAINS[other]["skills"])
            if extra not in skills:
                skills.append(extra)
        attended = [e["name"] for e in past
                    if (e["domain"] == domain and rng.random() < (0.55 if e["chapter"] == chapter else 0.15))
                    or rng.random() < 0.03][:5]
        members.append({
            "id": f"M{i:03d}", "name": name, "role": "Mentor" if level == "Advanced" and rng.random() < 0.35 else "Student",
            "college": rng.choice(COLLEGES[chapter]), "chapter": chapter, "domain": domain, "level": level,
            "skills": skills, "interests": rng.sample(INTERESTS, rng.randint(1, 3)), "attended": attended,
            "joined": f"{rng.choice([2025, 2026])}-{rng.randint(1, 12):02d}",
        })
    return members


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--members", type=int, default=72)
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()

    rng = random.Random(args.seed)
    events = make_events(rng)
    members = make_members(rng, args.members, events)
    config.DEMO_DIR.mkdir(parents=True, exist_ok=True)
    (config.DEMO_DIR / "events.json").write_text(json.dumps(events, indent=2), "utf-8")
    (config.DEMO_DIR / "members.json").write_text(json.dumps(members, indent=2), "utf-8")
    community.reload()
    print(f"Generated {len(members)} members and {len(events)} events -> {config.DEMO_DIR}")

    vectorstore.delete_where({"source": {"$in": ["member", "event"]}})
    vectorstore.upsert_chunks(community.to_chunks())

    kg = KnowledgeGraph.load()
    kg.remove_source(("member-", "event-"))
    for triple in community.to_triples():
        kg.add_triple(*triple)
    kg.save()
    print("Loaded into ChromaDB and graph:", kg.stats())


if __name__ == "__main__":
    main()
