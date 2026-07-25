"""SQLite audit log for desktop actions."""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

from deskbridge.domain.models import ActionRecord


class AuditService:
    def __init__(self, db_file: Path) -> None:
        self.db_file = db_file
        self.db_file.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_file))
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS action_records (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ts TEXT NOT NULL,
                    action TEXT NOT NULL,
                    params_json TEXT NOT NULL,
                    risk TEXT NOT NULL,
                    ok INTEGER NOT NULL,
                    result_json TEXT NOT NULL,
                    error TEXT,
                    source TEXT NOT NULL
                )
                """
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_action_records_ts ON action_records(ts DESC)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_action_records_action ON action_records(action)"
            )
            conn.commit()

    def add(self, record: ActionRecord) -> ActionRecord:
        with self._connect() as conn:
            cur = conn.execute(
                """
                INSERT INTO action_records
                    (ts, action, params_json, risk, ok, result_json, error, source)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    record.ts,
                    record.action,
                    record.params_json,
                    record.risk,
                    1 if record.ok else 0,
                    record.result_json,
                    record.error,
                    record.source,
                ),
            )
            conn.commit()
            record.id = int(cur.lastrowid)
        return record

    def list(
        self,
        *,
        limit: int = 50,
        action: str | None = None,
        ok: bool | None = None,
    ) -> list[ActionRecord]:
        limit = max(1, min(int(limit), 500))
        clauses: list[str] = []
        params: list[Any] = []
        if action:
            clauses.append("action = ?")
            params.append(action)
        if ok is not None:
            clauses.append("ok = ?")
            params.append(1 if ok else 0)
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        sql = f"""
            SELECT id, ts, action, params_json, risk, ok, result_json, error, source
            FROM action_records
            {where}
            ORDER BY id DESC
            LIMIT ?
        """
        params.append(limit)
        with self._connect() as conn:
            rows = conn.execute(sql, params).fetchall()
        return [
            ActionRecord(
                id=row["id"],
                ts=row["ts"],
                action=row["action"],
                params_json=row["params_json"],
                risk=row["risk"],
                ok=bool(row["ok"]),
                result_json=row["result_json"],
                error=row["error"],
                source=row["source"],
            )
            for row in rows
        ]

    def latest_screenshot_filename(self) -> str | None:
        rows = self.list(limit=20, action="screenshot", ok=True)
        for row in rows:
            result = row.to_dict().get("result") or {}
            filename = result.get("filename")
            if filename:
                return str(filename)
            path = result.get("path") or result.get("media")
            if path:
                return Path(str(path)).name
        return None

    def count(self) -> int:
        with self._connect() as conn:
            row = conn.execute("SELECT COUNT(*) AS c FROM action_records").fetchone()
        return int(row["c"] if row else 0)
