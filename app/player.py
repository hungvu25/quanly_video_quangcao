from __future__ import annotations

import signal
import subprocess
import threading
import time
from typing import Any

from . import db


class MPVPlayer:
    def __init__(self) -> None:
        self._thread: threading.Thread | None = None
        self._stop_event = threading.Event()
        self._next_event = threading.Event()
        self._lock = threading.Lock()
        self._proc: subprocess.Popen[str] | None = None
        self._current_index = 0

    def start(self) -> None:
        with self._lock:
            if self._thread and self._thread.is_alive():
                return

            playlist = db.list_playlist()
            if not playlist:
                db.set_playback_state(
                    is_playing=False,
                    is_paused=False,
                    status="error",
                    error_message="Playlist is empty",
                )
                return

            self._stop_event.clear()
            self._next_event.clear()
            db.clear_error()
            self._thread = threading.Thread(target=self._play_loop, daemon=True)
            self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        self._next_event.clear()
        self._terminate_current_process()
        db.set_playback_state(
            is_playing=False,
            is_paused=False,
            status="stopped",
            error_message=None,
        )

    def next(self) -> None:
        self._next_event.set()
        self._terminate_current_process()

    def pause_toggle(self) -> None:
        with self._lock:
            state = db.get_playback_state()
            if not self._proc or not state.get("is_playing"):
                return

            paused = bool(state.get("is_paused"))
            try:
                if paused:
                    self._proc.send_signal(signal.SIGCONT)
                    db.set_playback_state(
                        is_playing=True,
                        is_paused=False,
                        status="playing",
                        current_playlist_item_id=state.get("current_playlist_item_id"),
                        error_message=None,
                    )
                else:
                    self._proc.send_signal(signal.SIGSTOP)
                    db.set_playback_state(
                        is_playing=True,
                        is_paused=True,
                        status="paused",
                        current_playlist_item_id=state.get("current_playlist_item_id"),
                        error_message=None,
                    )
            except Exception as exc:
                db.set_playback_state(
                    is_playing=False,
                    is_paused=False,
                    status="error",
                    current_playlist_item_id=state.get("current_playlist_item_id"),
                    error_message=f"Pause/resume failed: {exc}",
                )

    def _play_loop(self) -> None:
        while not self._stop_event.is_set():
            playlist = db.list_playlist()
            if not playlist:
                db.set_playback_state(
                    is_playing=False,
                    is_paused=False,
                    status="error",
                    error_message="Playlist is empty",
                )
                return

            if self._current_index >= len(playlist):
                self._current_index = 0

            item = playlist[self._current_index]
            cmd = [
                "mpv",
                "--fs",
                "--force-window=yes",
                "--no-terminal",
                "--really-quiet",
                item["path"],
            ]

            try:
                self._proc = subprocess.Popen(cmd, text=True)
            except Exception as exc:
                db.set_playback_state(
                    is_playing=False,
                    is_paused=False,
                    status="error",
                    current_playlist_item_id=item["id"],
                    error_message=f"Cannot start mpv: {exc}",
                )
                return

            db.set_playback_state(
                is_playing=True,
                is_paused=False,
                status="playing",
                current_playlist_item_id=item["id"],
                error_message=None,
            )

            while self._proc and self._proc.poll() is None:
                if self._stop_event.is_set() or self._next_event.is_set():
                    self._terminate_current_process()
                    break
                time.sleep(0.2)

            if self._stop_event.is_set():
                return

            if self._next_event.is_set():
                self._next_event.clear()
                self._current_index = (self._current_index + 1) % len(playlist)
                continue

            return_code = self._proc.returncode if self._proc else 1
            self._proc = None
            if return_code != 0:
                db.set_playback_state(
                    is_playing=False,
                    is_paused=False,
                    status="error",
                    current_playlist_item_id=item["id"],
                    error_message=f"Playback failed with exit code {return_code}",
                )
                return

            self._current_index = (self._current_index + 1) % len(playlist)

    def _terminate_current_process(self) -> None:
        with self._lock:
            if not self._proc:
                return
            try:
                if self._proc.poll() is None:
                    self._proc.terminate()
                    self._proc.wait(timeout=2)
            except subprocess.TimeoutExpired:
                self._proc.kill()
            finally:
                self._proc = None

    def status(self) -> dict[str, Any]:
        return db.get_playback_state()
