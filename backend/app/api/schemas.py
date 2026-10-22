from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=1000)
    session_id: str | None = None


class PathRequest(BaseModel):
    goal: str = Field(min_length=3, max_length=500)
    current_skills: list[str] = []
    domain: str = ""


class QuizRequest(BaseModel):
    domain: str = Field(min_length=2, max_length=60)
    level: str = Field(min_length=2, max_length=40)
    count: int = Field(default=5, ge=3, le=10)


class ProjectRequest(BaseModel):
    domain: str = Field(min_length=2, max_length=60)
    level: str = Field(min_length=2, max_length=40)
    interests: str = Field(default="", max_length=300)
    skills: list[str] = []


class SearchRequest(BaseModel):
    query: str = Field(default="", max_length=500)
    entity_type: str | None = None
    domain: str | None = None
    chapter: str | None = None
    level: str | None = None
    upcoming: bool = False


class SessionPlanRequest(BaseModel):
    domain: str = Field(min_length=2, max_length=60)
    topic: str = Field(min_length=3, max_length=200)
    level: str = Field(default="Beginner", max_length=40)
    duration_hours: float = Field(default=3, ge=0.5, le=16)
    format: str = Field(default="Workshop", max_length=40)
    notes: str = Field(default="", max_length=500)


class AnswerRequest(BaseModel):
    answer: str = Field(min_length=3)
