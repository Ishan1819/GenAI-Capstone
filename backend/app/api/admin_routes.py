"""Admin-only endpoints (ISDIC team and chapter leads). Every route needs the X-Admin-Token header."""
from fastapi import APIRouter, Depends, Header, HTTPException

from app.api.schemas import AnswerRequest, SessionPlanRequest
from app.core import config
from app.database import db
from app.knowledge.graph import get_graph
from app.services import admin, session_plan


def require_admin(x_admin_token: str = Header(default="")):
    if x_admin_token != config.ADMIN_TOKEN:
        raise HTTPException(401, "Invalid admin token")


router = APIRouter(prefix="/api/admin", tags=["admin"], dependencies=[Depends(require_admin)])


@router.get("/verify")
def verify():
    return {"ok": True}


@router.get("/unanswered")
def list_unanswered(status: str = "open"):
    return db.list_unanswered(status)


@router.post("/unanswered/{item_id}/answer")
def answer_unanswered(item_id: int, req: AnswerRequest):
    try:
        admin.resolve_with_answer(item_id, req.answer)
    except KeyError:
        raise HTTPException(404, "Not found")
    return {"ok": True}


@router.post("/unanswered/{item_id}/dismiss")
def dismiss_unanswered(item_id: int):
    db.resolve_unanswered(item_id, "dismissed")
    return {"ok": True}


@router.get("/insights")
def insights(narrative: bool = True):
    try:
        return admin.compute_insights(narrative)
    except RuntimeError as e:
        raise HTTPException(503, str(e))


@router.post("/session-plan")
def session_plan_endpoint(req: SessionPlanRequest):
    try:
        return session_plan.generate_plan(req.domain, req.topic, req.level, req.duration_hours, req.format, req.notes)
    except RuntimeError as e:
        raise HTTPException(503, str(e))


@router.get("/graph")
def graph(focus: str = "", types: str = "", limit: int = 80):
    kg = get_graph()
    wanted = {t for t in types.split(",") if t} or None
    return {**kg.subgraph(focus or None, wanted, min(limit, 200)), "stats": kg.stats()}


@router.get("/graph/node")
def graph_node(id: str):  # query param: node ids can contain "/" (e.g. "ci/cd")
    detail = get_graph().node_detail(id)
    if not detail:
        raise HTTPException(404, "Node not found")
    return detail


@router.get("/graph/find")
def graph_find(q: str):
    return get_graph().find(q)
