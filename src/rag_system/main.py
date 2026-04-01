from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
import uvicorn

from rag_system.api import api_router
from rag_system.config import settings
from rag_system.database import init_db


@asynccontextmanager
async def lifespan(_: FastAPI):
    settings.uploads_dir.mkdir(parents=True, exist_ok=True)
    await init_db()
    yield


app = FastAPI(title=settings.app_name, lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)

static_path = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=static_path), name="static")


@app.get("/", include_in_schema=False)
async def home() -> FileResponse:
    return FileResponse(static_path / "index.html")


def run() -> None:
    uvicorn.run(
        "rag_system.main:app",
        host=settings.host,
        port=settings.port,
        log_level=settings.log_level,
    )


if __name__ == "__main__":
    run()
