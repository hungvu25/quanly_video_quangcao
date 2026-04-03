from __future__ import annotations

import threading
from pathlib import Path
from typing import Any

from .scanner import scan_video_files


class AppState:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._current_scan_dir = "/videos"
        self._videos_by_id: dict[int, dict[str, Any]] = {}
        self._playlist: list[dict[str, Any]] = []
        self._video_id_counter = 1
        self._playlist_item_id_counter = 1
        self._playback_state: dict[str, Any] = {
            "id": 1,
            "is_playing": 0,
            "is_paused": 0,
            "current_playlist_item_id": None,
            "status": "idle",
            "error_message": None,
            "updated_at": None,
        }

    def set_scan_dir(self, directory: str) -> None:
        with self._lock:
            self._current_scan_dir = directory

    def get_scan_dir(self) -> str:
        with self._lock:
            return self._current_scan_dir

    def refresh_videos(self, directory: str | None = None) -> list[dict[str, Any]]:
        target = directory or self.get_scan_dir()
        files = scan_video_files(target)

        with self._lock:
            existing_by_path = {
                str(item["path"]): item_id for item_id, item in self._videos_by_id.items()
            }
            new_map: dict[int, dict[str, Any]] = {}

            for path in files:
                path_str = str(path)
                item_id = existing_by_path.get(path_str)
                if item_id is None:
                    item_id = self._video_id_counter
                    self._video_id_counter += 1

                new_map[item_id] = {
                    "id": item_id,
                    "name": path.name,
                    "path": path_str,
                    "enabled": 1,
                    "created_at": None,
                }

            self._videos_by_id = new_map
            self._playlist = [
                item for item in self._playlist if item.get("video_id") in self._videos_by_id
            ]
            return list(self._videos_by_id.values())

    def list_videos(self) -> list[dict[str, Any]]:
        try:
            self.refresh_videos()
        except ValueError:
            return []
        with self._lock:
            videos = list(self._videos_by_id.values())
        videos.sort(key=lambda item: str(item["name"]).lower())
        return videos

    def delete_video(self, video_id: int) -> None:
        with self._lock:
            video = self._videos_by_id.get(video_id)
        if not video:
            return

        path = Path(str(video["path"]))
        if path.exists() and path.is_file():
            path.unlink()

        with self._lock:
            self._videos_by_id.pop(video_id, None)
            self._playlist = [item for item in self._playlist if item.get("video_id") != video_id]

    def add_to_playlist(self, video_id: int) -> int:
        with self._lock:
            video = self._videos_by_id.get(video_id)
            if not video:
                raise ValueError("Video not found")

            item_id = self._playlist_item_id_counter
            self._playlist_item_id_counter += 1
            self._playlist.append(
                {
                    "id": item_id,
                    "video_id": video_id,
                    "position": len(self._playlist) + 1,
                    "name": video["name"],
                    "path": video["path"],
                    "enabled": 1,
                }
            )
            return item_id

    def list_playlist(self) -> list[dict[str, Any]]:
        with self._lock:
            items = [dict(item) for item in self._playlist]
        items.sort(key=lambda item: int(item["position"]))
        return items

    def remove_playlist_item(self, item_id: int) -> None:
        with self._lock:
            self._playlist = [item for item in self._playlist if item.get("id") != item_id]
            self._normalize_playlist_positions()

    def reorder_playlist(self, item_ids: list[int]) -> None:
        with self._lock:
            by_id = {int(item["id"]): dict(item) for item in self._playlist}
            reordered: list[dict[str, Any]] = []
            for item_id in item_ids:
                if item_id in by_id:
                    reordered.append(by_id.pop(item_id))

            for item in self._playlist:
                if int(item["id"]) in by_id:
                    reordered.append(dict(item))
                    by_id.pop(int(item["id"]), None)

            self._playlist = reordered
            self._normalize_playlist_positions()

    def _normalize_playlist_positions(self) -> None:
        for index, item in enumerate(self._playlist, start=1):
            item["position"] = index

    def get_playback_state(self) -> dict[str, Any]:
        with self._lock:
            return dict(self._playback_state)

    def set_playback_state(
        self,
        *,
        is_playing: bool,
        is_paused: bool,
        status: str,
        current_playlist_item_id: int | None = None,
        error_message: str | None = None,
    ) -> None:
        with self._lock:
            self._playback_state.update(
                {
                    "is_playing": int(is_playing),
                    "is_paused": int(is_paused),
                    "current_playlist_item_id": current_playlist_item_id,
                    "status": status,
                    "error_message": error_message,
                }
            )

    def clear_error(self) -> None:
        with self._lock:
            self._playback_state["error_message"] = None


state = AppState()
