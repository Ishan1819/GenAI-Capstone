from fastapi import APIRouter, HTTPException

from app.api.schemas import SearchRequest
from app.database import community
from app.services import recommend, search

router = APIRouter(prefix="/api", tags=["community"])


@router.get("/search/filters")
def search_filters():
    return community.vocabulary()


@router.post("/search")
def search_endpoint(req: SearchRequest):
    overrides = req.model_dump(include={"entity_type", "domain", "chapter", "level", "upcoming"})
    if not req.upcoming:
        overrides.pop("upcoming")  # an unticked box shouldn't cancel "upcoming" parsed from the text
    return search.search(req.query, overrides)


@router.get("/members")
def list_members():
    return [{k: m[k] for k in ("id", "name", "domain", "level", "chapter")} for m in community.members()]


@router.get("/recommendations/{member_id}")
def recommendations(member_id: str, explain: bool = True):
    try:
        return recommend.recommend(member_id, explain=explain)
    except KeyError:
        raise HTTPException(404, "Member not found")
