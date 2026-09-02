"""SQLite persistence for indexed evaluations, experiments, and their cells."""

from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

from tessera.api.schemas import ExperimentRequest
from tessera.api.scrub import scrub_error


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class WorkbenchStore:
    def __init__(self, db_path: str | Path) -> None:
        self.db_path = str(db_path)
        parent = Path(self.db_path).parent
        if str(parent) not in ("", "."):
            parent.mkdir(parents=True, exist_ok=True)
        with self._conn() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS evaluations(
                    id TEXT PRIMARY KEY,
                    kind TEXT NOT NULL,
                    source TEXT NOT NULL,
                    source_ref TEXT NOT NULL UNIQUE,
                    status TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    model TEXT NOT NULL,
                    org TEXT,
                    engine TEXT NOT NULL,
                    grader TEXT,
                    epochs INTEGER NOT NULL,
                    pass_k_rate REAL,
                    mean_rate REAL,
                    artifact_path TEXT,
                    artifact_sha256 TEXT,
                    protocol_hash TEXT NOT NULL,
                    execution_hash TEXT NOT NULL,
                    receipt TEXT NOT NULL,
                    report TEXT
                );
                CREATE INDEX IF NOT EXISTS evaluations_created
                    ON evaluations(created_at DESC);

                CREATE TABLE IF NOT EXISTS experiments(
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    status TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    baseline_variant TEXT NOT NULL,
                    request TEXT NOT NULL,
                    error TEXT,
                    total_cost REAL NOT NULL DEFAULT 0,
                    cost_known INTEGER NOT NULL DEFAULT 1
                );
                CREATE TABLE IF NOT EXISTS experiment_cells(
                    id TEXT PRIMARY KEY,
                    experiment_id TEXT NOT NULL,
                    variant_id TEXT NOT NULL,
                    repeat_index INTEGER NOT NULL,
                    status TEXT NOT NULL,
                    run_id TEXT,
                    error TEXT,
                    UNIQUE(experiment_id, variant_id, repeat_index),
                    FOREIGN KEY(experiment_id) REFERENCES experiments(id)
                );
                CREATE INDEX IF NOT EXISTS experiment_cells_experiment
                    ON experiment_cells(experiment_id, variant_id, repeat_index);
                """
            )

    def _conn(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    # ---- evaluations -------------------------------------------------------------

    def record_evaluation(self, *, evaluation_id: str, kind: str, source: str,
                          source_ref: str, status: str, report: Mapping[str, Any],
                          receipt: Mapping[str, Any], artifact_path: str | None = None,
                          artifact_sha256: str | None = None,
                          persist_report: bool = False) -> None:
        header = report["header"]
        overall = report.get("overall", {})
        created = str(header.get("created") or _now())
        values = (
            evaluation_id, kind, source, source_ref, status, created, _now(),
            str(header.get("model") or ""), header.get("org"),
            str(header.get("engine") or "deterministic"), header.get("grader"),
            int(header.get("k") or 1), overall.get("pass_k_rate"), overall.get("mean_rate"),
            artifact_path, artifact_sha256, receipt["protocol_hash"],
            receipt["execution_hash"], json.dumps(receipt),
            json.dumps(report) if persist_report else None,
        )
        with self._conn() as connection:
            connection.execute(
                """INSERT INTO evaluations(
                    id,kind,source,source_ref,status,created_at,updated_at,model,org,engine,
                    grader,epochs,pass_k_rate,mean_rate,artifact_path,artifact_sha256,
                    protocol_hash,execution_hash,receipt,report)
                    VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                    ON CONFLICT(source_ref) DO UPDATE SET
                    id=excluded.id, kind=excluded.kind, status=excluded.status,
                    updated_at=excluded.updated_at, model=excluded.model, org=excluded.org,
                    engine=excluded.engine, grader=excluded.grader, epochs=excluded.epochs,
                    pass_k_rate=excluded.pass_k_rate, mean_rate=excluded.mean_rate,
                    artifact_path=excluded.artifact_path,
                    artifact_sha256=excluded.artifact_sha256,
                    protocol_hash=excluded.protocol_hash,
                    execution_hash=excluded.execution_hash,
                    receipt=excluded.receipt, report=excluded.report""",
                values,
            )

    @staticmethod
    def _evaluation_row(row: sqlite3.Row) -> dict[str, Any]:
        return {
            "id": row["id"], "kind": row["kind"], "source": row["source"],
            "status": row["status"], "created_at": row["created_at"],
            "model": row["model"], "org": row["org"], "engine": row["engine"],
            "grader": row["grader"], "epochs": row["epochs"],
            "pass_k_rate": row["pass_k_rate"], "mean_rate": row["mean_rate"],
            "artifact_path": row["artifact_path"],
            "artifact_sha256": row["artifact_sha256"],
            "protocol_hash": row["protocol_hash"], "execution_hash": row["execution_hash"],
            "receipt": json.loads(row["receipt"]),
            "report": json.loads(row["report"]) if row["report"] else None,
        }

    def get_evaluation(self, evaluation_id: str) -> dict[str, Any] | None:
        with self._conn() as connection:
            row = connection.execute(
                "SELECT * FROM evaluations WHERE id=?", (evaluation_id,),
            ).fetchone()
        return self._evaluation_row(row) if row else None

    def list_evaluations(self) -> list[dict[str, Any]]:
        with self._conn() as connection:
            rows = connection.execute(
                "SELECT * FROM evaluations ORDER BY created_at DESC, id",
            ).fetchall()
        out = []
        for row in rows:
            item = self._evaluation_row(row)
            item.pop("report")
            out.append(item)
        return out

    # ---- experiments -------------------------------------------------------------

    def create_experiment(self, request: ExperimentRequest) -> str:
        experiment_id = uuid.uuid4().hex
        created = _now()
        with self._conn() as connection:
            connection.execute(
                "INSERT INTO experiments(id,name,status,created_at,updated_at,baseline_variant,request) "
                "VALUES(?,?,?,?,?,?,?)",
                (experiment_id, request.name, "running", created, created,
                 request.baseline_variant, request.model_dump_json()),
            )
            for variant in request.variants:
                for repeat in range(1, request.repeats + 1):
                    connection.execute(
                        "INSERT INTO experiment_cells(id,experiment_id,variant_id,repeat_index,status) "
                        "VALUES(?,?,?,?,?)",
                        (uuid.uuid4().hex, experiment_id, variant.id, repeat, "pending"),
                    )
        return experiment_id

    def _experiment(self, row: sqlite3.Row) -> dict[str, Any]:
        with self._conn() as connection:
            cells = connection.execute(
                "SELECT * FROM experiment_cells WHERE experiment_id=? "
                "ORDER BY variant_id, repeat_index", (row["id"],),
            ).fetchall()
        return {
            "id": row["id"], "name": row["name"], "status": row["status"],
            "created_at": row["created_at"], "updated_at": row["updated_at"],
            "baseline_variant": row["baseline_variant"],
            "request": json.loads(row["request"]), "error": row["error"],
            "total_cost": row["total_cost"] if row["cost_known"] else None,
            "cells": [dict(cell) for cell in cells],
        }

    def get_experiment(self, experiment_id: str) -> dict[str, Any] | None:
        with self._conn() as connection:
            row = connection.execute(
                "SELECT * FROM experiments WHERE id=?", (experiment_id,),
            ).fetchone()
        return self._experiment(row) if row else None

    def list_experiments(self) -> list[dict[str, Any]]:
        with self._conn() as connection:
            rows = connection.execute(
                "SELECT * FROM experiments ORDER BY created_at DESC",
            ).fetchall()
        return [self._experiment(row) for row in rows]

    def next_cell(self, experiment_id: str) -> dict[str, Any] | None:
        """Atomically claim the next pending cell."""
        with self._conn() as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                "SELECT * FROM experiment_cells WHERE experiment_id=? AND status='pending' "
                "ORDER BY repeat_index, variant_id LIMIT 1", (experiment_id,),
            ).fetchone()
            if row is None:
                return None
            connection.execute(
                "UPDATE experiment_cells SET status='running', error=NULL WHERE id=?",
                (row["id"],),
            )
        item = dict(row)
        item["status"] = "running"
        return item

    def attach_run(self, cell_id: str, run_id: str) -> None:
        with self._conn() as connection:
            connection.execute(
                "UPDATE experiment_cells SET run_id=? WHERE id=?", (run_id, cell_id),
            )

    def finish_cell(self, cell_id: str, *, status: str, error: str | None = None,
                    cost: float | None = None) -> None:
        safe_error = scrub_error(error) if error else None
        with self._conn() as connection:
            row = connection.execute(
                "SELECT experiment_id FROM experiment_cells WHERE id=?", (cell_id,),
            ).fetchone()
            if row is None:
                return
            connection.execute(
                "UPDATE experiment_cells SET status=?, error=? WHERE id=?",
                (status, safe_error, cell_id),
            )
            # Only a *done* cell with no cost figure means the provider didn't report
            # cost — an error cell has no cost to report either way and must not be
            # confused with that. Otherwise one transient error would permanently mark
            # the experiment's cost as unenforceable, force-stopping it forever (resume
            # never recomputes cost_known, so it would just re-trigger the same stop).
            cost_unknown = status == "done" and cost is None
            connection.execute(
                "UPDATE experiments SET updated_at=?, total_cost=total_cost+?, "
                "cost_known=CASE WHEN ? THEN 0 ELSE cost_known END WHERE id=?",
                (_now(), float(cost or 0), cost_unknown, row["experiment_id"]),
            )

    def finish_experiment(self, experiment_id: str, *, status: str,
                          error: str | None = None) -> None:
        with self._conn() as connection:
            connection.execute(
                "UPDATE experiments SET status=?, updated_at=?, error=? WHERE id=?",
                (status, _now(), scrub_error(error) if error else None, experiment_id),
            )

    def skip_pending(self, experiment_id: str, reason: str) -> None:
        with self._conn() as connection:
            connection.execute(
                "UPDATE experiment_cells SET status='skipped', error=? "
                "WHERE experiment_id=? AND status='pending'",
                (scrub_error(reason), experiment_id),
            )

    def resume_experiment(self, experiment_id: str) -> bool:
        with self._conn() as connection:
            row = connection.execute(
                "SELECT id FROM experiments WHERE id=?", (experiment_id,),
            ).fetchone()
            if row is None:
                return False
            connection.execute(
                "UPDATE experiment_cells SET status='pending', error=NULL, run_id=NULL "
                "WHERE experiment_id=? AND status IN ('error','skipped')", (experiment_id,),
            )
            connection.execute(
                "UPDATE experiments SET status='running', error=NULL, updated_at=? WHERE id=?",
                (_now(), experiment_id),
            )
        return True

    def recover_interrupted(self) -> None:
        """Make work left running by a previous server process explicitly resumable."""
        reason = "server stopped before the experiment completed"
        with self._conn() as connection:
            connection.execute(
                "UPDATE experiment_cells SET status='pending', error=? "
                "WHERE status='running' AND experiment_id IN "
                "(SELECT id FROM experiments WHERE status='running')", (reason,),
            )
            connection.execute(
                "UPDATE experiments SET status='stopped', updated_at=?, error=? "
                "WHERE status='running'", (_now(), reason),
            )
