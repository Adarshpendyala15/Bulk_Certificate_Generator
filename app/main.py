from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api.certificates import router as certificates_router
from app.api.jobs import router as jobs_router
from app.database import create_db_and_tables


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    create_db_and_tables()
    app.state.executor = ThreadPoolExecutor(max_workers=4)
    try:
        yield
    finally:
        if hasattr(app.state, "executor"):
            app.state.executor.shutdown(wait=True)


app = FastAPI(title="Bulk Certificate Generator", lifespan=lifespan)
app.include_router(jobs_router)
app.include_router(certificates_router)
app.mount("/static", StaticFiles(directory="app/static"), name="static")


@app.get("/")
def index() -> FileResponse:
    return FileResponse(Path(__file__).parent / "static" / "index.html")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
