from __future__ import annotations

from datetime import datetime
import os
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from .player import MPVPlayer
from .scanner import VIDEO_EXTENSIONS, scan_video_files
from .state import state

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
    try:
        state.refresh_videos(state.get_scan_dir())
    except ValueError:
        pass


@app.get("/")
def root() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/videos")
def get_videos() -> dict[str, list[dict]]:
    return {"items": state.list_videos()}


@app.get("/api/files/list")
def list_box_directory(path: str = Query(default="/videos")) -> dict[str, object]:
    target = Path(path).expanduser().resolve()
    if not target.exists():
        raise HTTPException(status_code=404, detail=f"Path not found: {target}")
    if not target.is_dir():
        raise HTTPException(status_code=400, detail=f"Not a directory: {target}")

    entries: list[dict[str, object]] = []
    try:
        with os.scandir(target) as iterator:
            for entry in iterator:
                try:
                    stat = entry.stat(follow_symlinks=False)
                    entries.append(
                        {
                            "name": entry.name,
                            "path": str(Path(entry.path).resolve()),
                            "type": "dir" if entry.is_dir(follow_symlinks=False) else "file",
                            "size": stat.st_size,
                            "modified_at": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                        }
                    )
                except PermissionError:
                    continue
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=f"Permission denied: {target}") from exc

    entries.sort(key=lambda item: (item["type"] != "dir", str(item["name"]).lower()))
    parent_path = str(target.parent) if target.parent != target else None
    return {
        "current_path": str(target),
        "parent_path": parent_path,
        "entries": entries,
    }


@app.delete("/api/videos/{video_id}")
def delete_video(video_id: int) -> dict[str, str]:
    state.delete_video(video_id)
    return {"message": "deleted"}


@app.post("/api/videos/scan")
def scan_videos(payload: ScanRequest) -> dict[str, int]:
    try:
        files = scan_video_files(payload.directory)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    state.set_scan_dir(payload.directory)
    state.refresh_videos(payload.directory)
    return {"imported": len(files)}


@app.post("/api/videos/upload")
async def upload_video(
    file: UploadFile = File(...),
    target_dir: str = Form("/videos"),
) -> dict[str, object]:
    destination_dir = Path(target_dir).expanduser().resolve()
    destination_dir.mkdir(parents=True, exist_ok=True)
    if not destination_dir.is_dir():
        raise HTTPException(status_code=400, detail=f"Not a directory: {destination_dir}")

    source_name = Path(file.filename or "").name
    if not source_name:
        raise HTTPException(status_code=400, detail="Missing filename")

    ext = Path(source_name).suffix.lower()
    if ext not in VIDEO_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported extension: {ext or 'unknown'}",
        )

    destination_path = destination_dir / source_name
    data = await file.read()
    destination_path.write_bytes(data)
    state.set_scan_dir(str(destination_dir))
    videos = state.refresh_videos(str(destination_dir))
    uploaded = next((v for v in videos if v["path"] == str(destination_path)), None)
    video_id = int(uploaded["id"]) if uploaded else None
    return {
        "message": "uploaded",
        "video_id": video_id,
        "path": str(destination_path),
        "size": len(data),
    }


@app.get("/api/playlist")
def get_playlist() -> dict[str, list[dict]]:
    return {"items": state.list_playlist()}


@app.post("/api/playlist/add")
def add_playlist(payload: AddPlaylistRequest) -> dict[str, int]:
    try:
        item_id = state.add_to_playlist(payload.video_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"item_id": item_id}


@app.delete("/api/playlist/{item_id}")
def delete_playlist_item(item_id: int) -> dict[str, str]:
    state.remove_playlist_item(item_id)
    return {"message": "removed"}


@app.post("/api/playlist/reorder")
def reorder_playlist(payload: ReorderPlaylistRequest) -> dict[str, str]:
    state.reorder_playlist(payload.ordered_item_ids)
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
