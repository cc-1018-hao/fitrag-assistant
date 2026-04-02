from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.chat import router as chat_router
from app.api.index import router as index_router
from app.api.retrieve import router as retrieve_router
from app.indexing.build_index import run_build_index
from app.indexing.service import get_index_status

app = FastAPI(title="Fitness RAG Backend", version="0.2.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:5500",
        "http://localhost:5500",
        "http://127.0.0.1:8000",
        "http://localhost:8000",
    ],
    allow_origin_regex=r"^https://.*\.onrender\.com$",
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(index_router)
app.include_router(retrieve_router)
app.include_router(chat_router)


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


frontend_dir = Path(__file__).resolve().parents[1] / "frontend"
if frontend_dir.exists():
    app.mount("/", StaticFiles(directory=str(frontend_dir), html=True), name="frontend")


@app.on_event("startup")
def startup_bootstrap_index() -> None:
    try:
        status = get_index_status()
        if int(status.get("chroma_count", 0)) > 0 and int(status.get("bm25_count", 0)) > 0:
            return
        data_dir = Path(__file__).resolve().parents[1] / "data" / "raw"
        if data_dir.exists():
            run_build_index(data_dir=str(data_dir), recreate=False)
    except Exception:  # noqa: BLE001
        # Keep service alive even if bootstrap fails.
        return
