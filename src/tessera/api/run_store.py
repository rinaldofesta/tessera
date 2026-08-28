"""Durable SQLite-backed run store. Replaces the in-memory JobRegistry so runs survive
a restart and can power history + trends. Single file, stdlib sqlite3 — on-prem friendly.
"""

from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path

from tessera.api.schemas import RunRequest
from tessera.api.scrub import scrub_error


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class RunStore:
    def __init__(self, db_path: str | Path) -> None:
        self.db_path = str(db_path)
        parent = Path(self.db_path).parent
        if str(parent) not in ("", "."):
            parent.mkdir(parents=True, exist_ok=True)
        with self._conn() as c:
            c.execute(
                """CREATE TABLE IF NOT EXISTS runs(
                    id TEXT PRIMARY KEY, status TEXT NOT NULL,
                    created_at TEXT, finished_at TEXT,
                    model TEXT, org TEXT, judge TEXT, grader TEXT, epochs INTEGER,
                    report TEXT, error TEXT)""")

    def _conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    # ---- write ----
    def create(self, req: RunRequest) -> str:
        job_id = uuid.uuid4().hex
        with self._conn() as c:
            c.execute(
                "INSERT INTO runs(id,status,created_at,model,org,judge,grader,epochs) "
                "VALUES(?,?,?,?,?,?,?,?)",
                (job_id, "running", _now(), req.model, req.org, req.judge, req.grader, req.epochs))
        return job_id

    def complete(self, job_id: str, report: dict) -> None:
        with self._conn() as c:
            c.execute("UPDATE runs SET status='done', finished_at=?, report=? WHERE id=?",
                      (_now(), json.dumps(report), job_id))

    def error(self, job_id: str, message: str) -> None:
        # Scrubbed here as well as by the caller: this is the boundary that persists the
        # text, so a future writer that forgets to scrub cannot reopen the leak.
        # Redaction is idempotent, so the double pass costs nothing.
        message = scrub_error(message)
        with self._conn() as c:
            c.execute("UPDATE runs SET status='error', finished_at=?, error=? WHERE id=?",
                      (_now(), message, job_id))

    # ---- read ----
    def _row(self, r: sqlite3.Row) -> dict:
        return {
            "id": r["id"], "status": r["status"],
            "report": json.loads(r["report"]) if r["report"] else None,
            "error": r["error"], "model": r["model"], "org": r["org"],
            "judge": r["judge"], "grader": r["grader"], "epochs": r["epochs"],
            "created_at": r["created_at"], "finished_at": r["finished_at"],
        }

    def get(self, job_id: str) -> dict | None:
        with self._conn() as c:
            row = c.execute("SELECT * FROM runs WHERE id=?", (job_id,)).fetchone()
        return self._row(row) if row else None

    def list(self) -> list[dict]:
        """History summaries (no full report), newest first."""
        with self._conn() as c:
            rows = c.execute("SELECT * FROM runs ORDER BY created_at DESC").fetchall()
        out = []
        for r in rows:
            d = self._row(r)
            rep = d.pop("report")
            d["pass_k_rate"] = rep["overall"]["pass_k_rate"] if rep else None
            d["mean_rate"] = rep["overall"]["mean_rate"] if rep else None
            out.append(d)
        return out

    def finished(self) -> list[dict]:
        """Full rows for done runs, oldest first (for trends)."""
        with self._conn() as c:
            rows = c.execute("SELECT * FROM runs WHERE status='done' ORDER BY created_at ASC").fetchall()
        return [self._row(r) for r in rows]
