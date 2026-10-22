from fastapi import APIRouter, File, HTTPException, UploadFile

from app.api.schemas import PathRequest, ProjectRequest, QuizRequest
from app.services import learning_path, projects, quiz, resume

router = APIRouter(prefix="/api", tags=["member"])


@router.post("/learning-path")
def learning_path_endpoint(req: PathRequest):
    try:
        return learning_path.build_path(req.goal, req.current_skills, req.domain)
    except RuntimeError as e:
        raise HTTPException(503, str(e))


@router.post("/resume")
async def resume_endpoint(file: UploadFile = File(...)):
    data = await file.read()
    if len(data) > 5_000_000:
        raise HTTPException(413, "File too large (max 5 MB)")
    try:
        return resume.analyse(resume.read_text(file.filename or "", data))
    except ValueError as e:
        raise HTTPException(422, str(e))
    except RuntimeError as e:
        raise HTTPException(503, str(e))


@router.post("/quiz")
def quiz_endpoint(req: QuizRequest):
    try:
        return quiz.generate_quiz(req.domain, req.level, req.count)
    except RuntimeError as e:
        raise HTTPException(503, str(e))


@router.post("/projects")
def projects_endpoint(req: ProjectRequest):
    try:
        return projects.suggest_projects(req.domain, req.level, req.interests, req.skills)
    except RuntimeError as e:
        raise HTTPException(503, str(e))
