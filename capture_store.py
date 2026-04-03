import base64
import json
import os
import sqlite3
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DEFAULT_DB_PATH = Path("~/.cc-proxy/sqlite.db").expanduser()
DEFAULT_LOG_DIR = Path("~/.cc-proxy/logs").expanduser()
BODY_PREVIEW_LIMIT = 256 * 1024


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def get_db_path() -> Path:
    return Path(os.environ.get("CC_PROXY_DB_PATH", str(DEFAULT_DB_PATH))).expanduser()


def get_log_dir() -> Path:
    return Path(os.environ.get("CC_PROXY_LOG_DIR", str(DEFAULT_LOG_DIR))).expanduser()


@dataclass
class BodyPreview:
    content: str
    content_type: str
    encoding: str
    total_bytes: int
    truncated: bool


class CaptureStore:
    def __init__(self, db_path: Path | None = None, log_dir: Path | None = None) -> None:
        self.db_path = db_path or get_db_path()
        self.log_dir = log_dir or get_log_dir()
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS request_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    request_url TEXT NOT NULL,
                    request_headers TEXT NOT NULL,
                    started_at TEXT NOT NULL,
                    finished_at TEXT,
                    duration_ms INTEGER
                )
                """
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_request_logs_started_at ON request_logs(started_at DESC)"
            )
            conn.commit()

    def create_capture(self, request_url: str, request_headers: dict[str, Any], request_body: bytes) -> int:
        started_at = utc_now_iso()
        with self._connect() as conn:
            cursor = conn.execute(
                """
                INSERT INTO request_logs (request_url, request_headers, started_at)
                VALUES (?, ?, ?)
                """,
                (request_url, json.dumps(request_headers, ensure_ascii=False, indent=2), started_at),
            )
            capture_id = int(cursor.lastrowid)
            conn.commit()

        self.write_request_body(capture_id, request_body)
        return capture_id

    def finalize_capture(self, capture_id: int, started_monotonic: float, finished_at: str | None = None) -> None:
        end_time = finished_at or utc_now_iso()
        duration_ms = max(0, int((time.perf_counter() - started_monotonic) * 1000))
        with self._connect() as conn:
            conn.execute(
                """
                UPDATE request_logs
                SET finished_at = ?, duration_ms = ?
                WHERE id = ?
                """,
                (end_time, duration_ms, capture_id),
            )
            conn.commit()

    def write_request_body(self, capture_id: int, body: bytes) -> None:
        self._write_file(self.request_body_path(capture_id), body)

    def append_response_chunk(self, capture_id: int, chunk: bytes) -> None:
        if not chunk:
            return
        path = self.response_body_path(capture_id)
        with path.open("ab") as fh:
            fh.write(chunk)

    def request_body_path(self, capture_id: int) -> Path:
        return self.log_dir / f"log_{capture_id}_req"

    def response_body_path(self, capture_id: int) -> Path:
        return self.log_dir / f"log_{capture_id}_res"

    def _write_file(self, path: Path, body: bytes) -> None:
        with path.open("wb") as fh:
            fh.write(body)

    def list_records(self, limit: int = 200) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT id, request_url, request_headers, started_at, finished_at, duration_ms
                FROM request_logs
                ORDER BY started_at DESC, id DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()

        return [dict(row) for row in rows]

    def get_record(self, capture_id: int) -> dict[str, Any] | None:
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT id, request_url, request_headers, started_at, finished_at, duration_ms
                FROM request_logs
                WHERE id = ?
                """,
                (capture_id,),
            ).fetchone()

        if row is None:
            return None

        record = dict(row)
        record["request_body_size"] = self._file_size(self.request_body_path(capture_id))
        record["response_body_size"] = self._file_size(self.response_body_path(capture_id))
        return record

    def read_body_preview(self, capture_id: int, kind: str, max_bytes: int = BODY_PREVIEW_LIMIT) -> BodyPreview:
        path = self._body_path(capture_id, kind)
        data = b""
        total_size = 0

        if path.exists():
            total_size = path.stat().st_size
            with path.open("rb") as fh:
                data = fh.read(max_bytes)

        truncated = total_size > len(data)
        content, content_type, encoding = self._decode_body(data)
        return BodyPreview(
            content=content,
            content_type=content_type,
            encoding=encoding,
            total_bytes=total_size,
            truncated=truncated,
        )

    def read_body_bytes(self, capture_id: int, kind: str) -> bytes:
        path = self._body_path(capture_id, kind)
        if not path.exists():
            return b""
        return path.read_bytes()

    def _body_path(self, capture_id: int, kind: str) -> Path:
        if kind == "request":
            return self.request_body_path(capture_id)
        if kind == "response":
            return self.response_body_path(capture_id)
        raise ValueError(f"Unsupported body kind: {kind}")

    def _file_size(self, path: Path) -> int:
        if not path.exists():
            return 0
        return path.stat().st_size

    def _decode_body(self, data: bytes) -> tuple[str, str, str]:
        if not data:
            return "", "text", "utf-8"

        try:
            return data.decode("utf-8"), "text", "utf-8"
        except UnicodeDecodeError:
            encoded = base64.b64encode(data).decode("ascii")
            return encoded, "base64", "base64"
