from contextlib import asynccontextmanager

from app.database import create_db_and_tables, engine
from app.routers import auth, tasks, groups
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Создаём таблицы при старте
    await create_db_and_tables()
    print("✅ База данных инициализирована и таблицы созданы")
    yield


app = FastAPI(
    title="Веб-платформа проверки кода с LLM",
    description="Дипломная работа - Нижельский И.И.",
    version="0.1.0",
    lifespan=lifespan
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(tasks.router)
app.include_router(groups.router)


@app.get("/")
async def root():
    return {
        "message": "Платформа для проверки кода работает!",
        "docs": "/docs"
    }


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/check-tables")
async def check_tables():
    from sqlalchemy import text

    async with engine.begin() as conn:
        result = await conn.execute(
            text("SELECT tablename FROM pg_tables WHERE schemaname = 'public';")
        )
        tables = [row[0] for row in result.fetchall()]

    return {
        "status": "ok",
        "tables": tables,
        "message": f"Найдено {len(tables)} таблиц в базе"
    }
