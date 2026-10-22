from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import admin_routes, chat_routes, community_routes, member_routes
from app.core import config
from app.database import db


@asynccontextmanager
async def lifespan(_: FastAPI):
    db.init()
    yield


app = FastAPI(title="ISDIC Community Intelligence Platform", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=config.CORS_ORIGINS, allow_methods=["*"], allow_headers=["*"])

app.include_router(chat_routes.router)
app.include_router(member_routes.router)
app.include_router(community_routes.router)
app.include_router(admin_routes.router)
