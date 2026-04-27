from contextlib import asynccontextmanager

from app.database import engine
from app.routers import auth, groups, submissions, tasks, users
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.connect() as conn:
        await conn.execute(text("SELECT 1"))
    print("Database connection verified")
    yield


app = FastAPI(
    title="Code Review Platform with LLM",
    description="Diploma project backend API",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(tasks.router)
app.include_router(groups.router)
app.include_router(users.router)
app.include_router(submissions.router)


@app.get("/")
async def root():
    return {
        "message": "Code review platform is running",
        "docs": "/docs",
    }


@app.get("/health")
async def health():
    return {"status": "ok"}
