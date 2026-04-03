from __future__ import annotations

import os
import sqlite3
import threading
from pathlib import Path
from typing import Any

DB_PATH = Path(os.getenv("VIDEO_BOX_DB_PATH", str(Path(__file__).resolve().parent.parent / "app.db")))
_DB_LOCK = threading.Lock()


def _get_conn() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with _DB_LOCK:
        with _get_conn() as conn:
            conn.executescript(
                """
                PRAGMA journal_mode=WAL;

                CREATE TABLE IF NOT EXISTS videos (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    path TEXT NOT NULL UNIQUE,
                    enabled INTEGER NOT NULL DEFAULT 1,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS playlist_items (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    video_id INTEGER NOT NULL,
                    position INTEGER NOT NULL,
                    FOREIGN KEY (video_id) REFERENCES videos(id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS playback_state (
                    id INTEGER PRIMARY KEY CHECK (id = 1),
                    is_playing INTEGER NOT NULL DEFAULT 0,
                    is_paused INTEGER NOT NULL DEFAULT 0,
                    current_playlist_item_id INTEGER,
                    status TEXT NOT NULL DEFAULT 'idle',
                    error_message TEXT,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS app_settings (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                );
                """
            )

            conn.execute(
                """
                INSERT INTO playback_state (id, is_playing, is_paused, status, error_message)
                VALUES (1, 0, 0, 'idle', NULL)
                ON CONFLICT(id) DO NOTHING
                """
            )
            conn.commit()


def list_videos() -> list[dict[str, Any]]:
    with _get_conn() as conn:
        rows = conn.execute(
            "SELECT id, name, path, enabled, created_at FROM videos ORDER BY id DESC"
        ).fetchall()
    return [dict(row) for row in rows]


def upsert_video(name: str, path: str) -> int:
    with _DB_LOCK:
        with _get_conn() as conn:
            conn.execute(
                """
                INSERT INTO videos (name, path, enabled)
                VALUES (?, ?, 1)
                ON CONFLICT(path) DO UPDATE SET name = excluded.name
                """,
                (name, path),
            )
            row = conn.execute("SELECT id FROM videos WHERE path = ?", (path,)).fetchone()
            conn.commit()
            return int(row["id"])


def delete_video(video_id: int) -> None:
    with _DB_LOCK:
        with _get_conn() as conn:
            conn.execute("DELETE FROM playlist_items WHERE video_id = ?", (video_id,))
            conn.execute("DELETE FROM videos WHERE id = ?", (video_id,))
            conn.commit()


def list_playlist() -> list[dict[str, Any]]:
    with _get_conn() as conn:
        rows = conn.execute(
            """
            SELECT
                p.id,
                p.video_id,
                p.position,
                v.name,
                v.path,
                v.enabled
            FROM playlist_items p
            JOIN videos v ON v.id = p.video_id
            ORDER BY p.position ASC, p.id ASC
            """
        ).fetchall()
    return [dict(row) for row in rows]


def add_to_playlist(video_id: int) -> int:
    with _DB_LOCK:
        with _get_conn() as conn:
            next_pos_row = conn.execute(
                "SELECT COALESCE(MAX(position), 0) + 1 AS next_pos FROM playlist_items"
            ).fetchone()
            next_pos = int(next_pos_row["next_pos"])
            cursor = conn.execute(
                "INSERT INTO playlist_items (video_id, position) VALUES (?, ?)",
                (video_id, next_pos),
            )
            conn.commit()
            return int(cursor.lastrowid)


def remove_playlist_item(item_id: int) -> None:
    with _DB_LOCK:
        with _get_conn() as conn:
            conn.execute("DELETE FROM playlist_items WHERE id = ?", (item_id,))
            _normalize_playlist_positions(conn)
            conn.commit()


def reorder_playlist(item_ids: list[int]) -> None:
    with _DB_LOCK:
        with _get_conn() as conn:
            for index, item_id in enumerate(item_ids, start=1):
                conn.execute(
                    "UPDATE playlist_items SET position = ? WHERE id = ?",
                    (index, item_id),
                )
            _normalize_playlist_positions(conn)
            conn.commit()


def _normalize_playlist_positions(conn: sqlite3.Connection) -> None:
    rows = conn.execute(
        "SELECT id FROM playlist_items ORDER BY position ASC, id ASC"
    ).fetchall()
    for index, row in enumerate(rows, start=1):
        conn.execute("UPDATE playlist_items SET position = ? WHERE id = ?", (index, row["id"]))


def get_playback_state() -> dict[str, Any]:
    with _get_conn() as conn:
        row = conn.execute(
            """
            SELECT id, is_playing, is_paused, current_playlist_item_id, status, error_message, updated_at
            FROM playback_state
            WHERE id = 1
            """
        ).fetchone()
    return dict(row) if row else {}


def set_playback_state(
    *,
    is_playing: bool,
    is_paused: bool,
    status: str,
    current_playlist_item_id: int | None = None,
    error_message: str | None = None,
) -> None:
    with _DB_LOCK:
        with _get_conn() as conn:
            conn.execute(
                """
                UPDATE playback_state
                SET
                    is_playing = ?,
                    is_paused = ?,
                    current_playlist_item_id = ?,
                    status = ?,
                    error_message = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = 1
                """,
                (int(is_playing), int(is_paused), current_playlist_item_id, status, error_message),
            )
            conn.commit()


def clear_error() -> None:
    with _DB_LOCK:
        with _get_conn() as conn:
            conn.execute(
                "UPDATE playback_state SET error_message = NULL, updated_at = CURRENT_TIMESTAMP WHERE id = 1"
            )
            conn.commit()


def set_setting(key: str, value: str) -> None:
    with _DB_LOCK:
        with _get_conn() as conn:
            conn.execute(
                """
                INSERT INTO app_settings (key, value)
                VALUES (?, ?)
                ON CONFLICT(key) DO UPDATE SET value = excluded.value
                """,
                (key, value),
            )
            conn.commit()


def get_setting(key: str, default: str | None = None) -> str | None:
    with _get_conn() as conn:
        row = conn.execute("SELECT value FROM app_settings WHERE key = ?", (key,)).fetchone()
    if row:
        return str(row["value"])
    return default
