from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.backend import constants
from app.backend.validators.types import RunRecords


def _now_iso() -> str:
	return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _get_db_path(db_path: Optional[str]) -> str:
	if db_path:
		return db_path
	return constants.DEFAULT_DB_PATH


def _connect(path: str) -> sqlite3.Connection:
	conn = sqlite3.connect(path, timeout=constants.SQLITE_BUSY_TIMEOUT_MS / 1000)
	conn.execute("PRAGMA journal_mode=WAL")
	conn.execute("PRAGMA synchronous=NORMAL")
	conn.execute(f"PRAGMA busy_timeout={constants.SQLITE_BUSY_TIMEOUT_MS}")
	conn.execute("PRAGMA foreign_keys=ON")
	return conn


def init_db(db_path: Optional[str] = None) -> None:
	path = _get_db_path(db_path)
	Path(path).parent.mkdir(parents=True, exist_ok=True)
	conn = _connect(path)
	try:
		conn.execute(
			"""
			CREATE TABLE IF NOT EXISTS run_records (
				id INTEGER PRIMARY KEY AUTOINCREMENT,
				run_type TEXT NOT NULL,
				exit_code INTEGER,
				started_at TEXT,
				ended_at TEXT,
				stdout TEXT,
				stderr TEXT
			)
			"""
		)
		conn.execute(
			"""
			CREATE TABLE IF NOT EXISTS finding_state (
				finding_id TEXT PRIMARY KEY,
				status TEXT NOT NULL,
				note TEXT,
				updated_at TEXT NOT NULL
			)
			"""
		)
		conn.commit()
	finally:
		conn.close()


def record_run_event(
	run_type: str,
	exit_code: int,
	started_at: str,
	ended_at: str,
	stdout: str,
	stderr: str,
	db_path: Optional[str] = None,
) -> None:
	init_db(db_path)
	path = _get_db_path(db_path)
	conn = _connect(path)
	try:
		conn.execute(
			"""
			INSERT INTO run_records (run_type, exit_code, started_at, ended_at, stdout, stderr)
			VALUES (?, ?, ?, ?, ?, ?)
			""",
			(run_type, exit_code, started_at, ended_at, stdout, stderr),
		)
		conn.commit()
	finally:
		conn.close()


def get_latest_run_records(db_path: Optional[str] = None) -> RunRecords:
	init_db(db_path)
	path = _get_db_path(db_path)
	conn = _connect(path)
	try:
		conn.row_factory = sqlite3.Row
		cursor = conn.cursor()
		cursor.execute(
			"""
			SELECT run_type, exit_code
			FROM run_records
			WHERE run_type IN ('sync', 'validate')
			ORDER BY id DESC
			"""
		)
		rows = cursor.fetchall()
	finally:
		conn.close()

	sync_code = None
	validate_code = None
	for row in rows:
		if row["run_type"] == "sync" and sync_code is None:
			sync_code = row["exit_code"]
		if row["run_type"] == "validate" and validate_code is None:
			validate_code = row["exit_code"]
		if sync_code is not None and validate_code is not None:
			break

	return RunRecords(sync_exit_code=sync_code, validate_exit_code=validate_code)


def upsert_finding_state(
	finding_id: str,
	status: str,
	note: Optional[str],
	db_path: Optional[str] = None,
) -> Dict[str, Any]:
	init_db(db_path)
	path = _get_db_path(db_path)
	updated_at = _now_iso()
	conn = _connect(path)
	try:
		conn.execute(
			"""
			INSERT INTO finding_state (finding_id, status, note, updated_at)
			VALUES (?, ?, ?, ?)
			ON CONFLICT(finding_id)
			DO UPDATE SET status=excluded.status, note=excluded.note, updated_at=excluded.updated_at
			""",
			(finding_id, status, note, updated_at),
		)
		conn.commit()
	finally:
		conn.close()
	return {"finding_id": finding_id, "status": status, "note": note, "updated_at": updated_at}


def get_finding_state(finding_id: str, db_path: Optional[str] = None) -> Optional[Dict[str, Any]]:
	init_db(db_path)
	path = _get_db_path(db_path)
	conn = _connect(path)
	try:
		conn.row_factory = sqlite3.Row
		cursor = conn.cursor()
		cursor.execute(
			"SELECT finding_id, status, note, updated_at FROM finding_state WHERE finding_id = ?",
			(finding_id,),
		)
		row = cursor.fetchone()
		if row is None:
			return None
		return dict(row)
	finally:
		conn.close()


def list_finding_states(
	status: Optional[str] = None,
	db_path: Optional[str] = None,
) -> List[Dict[str, Any]]:
	init_db(db_path)
	path = _get_db_path(db_path)
	conn = _connect(path)
	try:
		conn.row_factory = sqlite3.Row
		cursor = conn.cursor()
		if status:
			cursor.execute(
				"SELECT finding_id, status, note, updated_at FROM finding_state WHERE status = ?",
				(status,),
			)
		else:
			cursor.execute("SELECT finding_id, status, note, updated_at FROM finding_state")
		rows = cursor.fetchall()
		return [dict(row) for row in rows]
	finally:
		conn.close()


def get_finding_states(db_path: Optional[str] = None) -> List[Dict[str, Any]]:
	return list_finding_states(db_path=db_path)


def get_storage_meta(db_path: Optional[str] = None) -> Dict[str, object]:
	init_db(db_path)
	path = _get_db_path(db_path)
	conn = _connect(path)
	try:
		conn.row_factory = sqlite3.Row
		quick_check = conn.execute("PRAGMA quick_check").fetchone()[0]
		journal_mode = conn.execute("PRAGMA journal_mode").fetchone()[0]
		return {
			"path": path,
			"journal_mode": journal_mode,
			"quick_check": quick_check,
		}
	finally:
		conn.close()
