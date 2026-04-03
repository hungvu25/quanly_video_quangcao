from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from . import db
from .player import MPVPlayer
from .scanner import scan_video_files

app = FastAPI(title="Video Box Manager", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

STATIC_DIR = Path(__file__).resolve().parent / "static"
player = MPVPlayer()


class ScanRequest(BaseModel):
    directory: str


class AddPlaylistRequest(BaseModel):
    video_id: int


class ReorderPlaylistRequest(BaseModel):
    ordered_item_ids: list[int] = Field(min_items=1)


@app.on_event("startup")
def on_startup() -> None:
    db.init_db()


@app.get("/")
def root() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/videos")
def get_videos() -> dict[str, list[dict]]:
    return {"items": db.list_videos()}


@app.delete("/api/videos/{video_id}")
def delete_video(video_id: int) -> dict[str, str]:
    db.delete_video(video_id)
    return {"message": "deleted"}


@app.post("/api/videos/scan")
def scan_videos(payload: ScanRequest) -> dict[str, int]:
    try:
        files = scan_video_files(payload.directory)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    imported = 0
    for path in files:
        db.upsert_video(name=path.name, path=str(path))
        imported += 1

    db.set_setting("video_root", payload.directory)
    return {"imported": imported}


@app.get("/api/playlist")
def get_playlist() -> dict[str, list[dict]]:
    return {"items": db.list_playlist()}


@app.post("/api/playlist/add")
def add_playlist(payload: AddPlaylistRequest) -> dict[str, int]:
    item_id = db.add_to_playlist(payload.video_id)
    return {"item_id": item_id}


@app.delete("/api/playlist/{item_id}")
def delete_playlist_item(item_id: int) -> dict[str, str]:
    db.remove_playlist_item(item_id)
    return {"message": "removed"}


@app.post("/api/playlist/reorder")
def reorder_playlist(payload: ReorderPlaylistRequest) -> dict[str, str]:
    db.reorder_playlist(payload.ordered_item_ids)
    return {"message": "reordered"}


@app.post("/api/player/start")
def start_player() -> dict[str, str]:
    player.start()
    return {"message": "started"}


@app.post("/api/player/stop")
def stop_player() -> dict[str, str]:
    player.stop()
    return {"message": "stopped"}


@app.post("/api/player/next")
def next_player() -> dict[str, str]:
    player.next()
    return {"message": "next"}


@app.post("/api/player/pause")
def pause_player() -> dict[str, str]:
    player.pause_toggle()
    return {"message": "toggled"}


@app.get("/api/player/status")
def status_player() -> dict[str, dict]:
    return {"state": player.status()}
