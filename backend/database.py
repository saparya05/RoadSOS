"""
RoadSOS – SQLite Database Layer
Handles all persistent storage: chat history, sessions, emergency logs.
"""

import sqlite3
import os
import json
from datetime import datetime
from typing import List, Dict, Optional

# ── DB file lives next to this module inside the data/ folder ─────────────────
_BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(_BASE_DIR, "data", "roadsos.db")


# ─────────────────────────────────────────────────────────────────────────────
# Connection helper
# ─────────────────────────────────────────────────────────────────────────────

def _get_connection() -> sqlite3.Connection:
    """Return a new sqlite3 connection with row_factory set."""
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row          # access columns by name
    conn.execute("PRAGMA journal_mode=WAL") # better concurrency
    return conn


# ─────────────────────────────────────────────────────────────────────────────
# Schema initialisation  (called once on import)
# ─────────────────────────────────────────────────────────────────────────────

def init_db() -> None:
    """Create all tables if they do not exist yet."""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

    conn = _get_connection()
    try:
        cursor = conn.cursor()

        # ── sessions ──────────────────────────────────────────────────────────
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                id              TEXT PRIMARY KEY,
                created_at      TEXT NOT NULL,
                last_active_at  TEXT NOT NULL,
                title           TEXT,
                emergency_type  TEXT,
                latitude        REAL,
                longitude       REAL
            )
        """)

        # ── chat_messages ─────────────────────────────────────────────────────
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS chat_messages (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id      TEXT    NOT NULL REFERENCES sessions(id),
                timestamp       TEXT    NOT NULL,
                role            TEXT    NOT NULL CHECK(role IN ('user','assistant')),
                user_text       TEXT,
                ai_response     TEXT,
                emergency_type  TEXT,
                priority        TEXT,
                confidence      REAL,
                latitude        REAL,
                longitude       REAL,
                services_json   TEXT    -- JSON-encoded list of nearby services
            )
        """)

        # ── emergency_log ──────────────────────────────────────────────────────
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS emergency_log (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id      TEXT    NOT NULL,
                timestamp       TEXT    NOT NULL,
                emergency_type  TEXT    NOT NULL,
                priority        TEXT    NOT NULL,
                latitude        REAL,
                longitude       REAL,
                user_text       TEXT,
                services_count  INTEGER DEFAULT 0,
                resolved        INTEGER DEFAULT 0
            )
        """)

        conn.commit()
    finally:
        conn.close()


# Initialise schema immediately on import
init_db()


# ─────────────────────────────────────────────────────────────────────────────
# Session helpers
# ─────────────────────────────────────────────────────────────────────────────

def upsert_session(session_id: str, title: str = None,
                   emergency_type: str = None,
                   lat: float = None, lon: float = None) -> None:
    """Insert a new session or update its last_active_at timestamp."""
    now = datetime.utcnow().isoformat()
    conn = _get_connection()
    try:
        conn.execute("""
            INSERT INTO sessions (id, created_at, last_active_at, title, emergency_type, latitude, longitude)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                last_active_at = excluded.last_active_at,
                title          = COALESCE(excluded.title, sessions.title),
                emergency_type = COALESCE(excluded.emergency_type, sessions.emergency_type),
                latitude       = COALESCE(excluded.latitude,  sessions.latitude),
                longitude      = COALESCE(excluded.longitude, sessions.longitude)
        """, (session_id, now, now, title, emergency_type, lat, lon))
        conn.commit()
    finally:
        conn.close()


def get_session(session_id: str) -> Optional[Dict]:
    conn = _get_connection()
    try:
        row = conn.execute(
            "SELECT * FROM sessions WHERE id = ?", (session_id,)
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def list_sessions(limit: int = 20) -> List[Dict]:
    """Return most-recently-active sessions."""
    conn = _get_connection()
    try:
        rows = conn.execute(
            "SELECT * FROM sessions ORDER BY last_active_at DESC LIMIT ?", (limit,)
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def delete_session(session_id: str) -> None:
    conn = _get_connection()
    try:
        conn.execute("DELETE FROM chat_messages WHERE session_id = ?", (session_id,))
        conn.execute("DELETE FROM emergency_log  WHERE session_id = ?", (session_id,))
        conn.execute("DELETE FROM sessions       WHERE id = ?",         (session_id,))
        conn.commit()
    finally:
        conn.close()


# ─────────────────────────────────────────────────────────────────────────────
# Chat message helpers
# ─────────────────────────────────────────────────────────────────────────────

def save_chat_turn(
    session_id:     str,
    user_text:      str,
    ai_response:    str,
    emergency_type: Optional[str] = None,
    priority:       Optional[str] = None,
    confidence:     Optional[float] = None,
    lat:            Optional[float] = None,
    lon:            Optional[float] = None,
    services:       Optional[List[Dict]] = None,
) -> int:
    """
    Persist one full user↔AI turn.
    Returns the auto-incremented row id.
    """
    now       = datetime.utcnow().isoformat()
    svc_json  = json.dumps(services or [])

    # Ensure session row exists
    upsert_session(session_id,
                   title=user_text[:60] if user_text else None,
                   emergency_type=emergency_type,
                   lat=lat, lon=lon)

    conn = _get_connection()
    try:
        cursor = conn.execute("""
            INSERT INTO chat_messages
                (session_id, timestamp, role,
                 user_text, ai_response,
                 emergency_type, priority, confidence,
                 latitude, longitude, services_json)
            VALUES (?, ?, 'assistant', ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            session_id, now,
            user_text, ai_response,
            emergency_type, priority, confidence,
            lat, lon, svc_json,
        ))
        conn.commit()
        return cursor.lastrowid
    finally:
        conn.close()


def get_chat_history(session_id: str) -> List[Dict]:
    """Return all chat turns for a session, oldest first."""
    conn = _get_connection()
    try:
        rows = conn.execute("""
            SELECT * FROM chat_messages
            WHERE session_id = ?
            ORDER BY id ASC
        """, (session_id,)).fetchall()
        result = []
        for r in rows:
            d = dict(r)
            try:
                d["services"] = json.loads(d.get("services_json") or "[]")
            except Exception:
                d["services"] = []
            result.append(d)
        return result
    finally:
        conn.close()


def get_all_sessions_with_last_message() -> List[Dict]:
    """Used by the sidebar: sessions joined with their first user message."""
    conn = _get_connection()
    try:
        rows = conn.execute("""
            SELECT
                s.id,
                s.created_at,
                s.last_active_at,
                s.title,
                s.emergency_type,
                s.latitude,
                s.longitude
            FROM sessions s
            ORDER BY s.last_active_at DESC
            LIMIT 30
        """).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


# ─────────────────────────────────────────────────────────────────────────────
# Emergency log helpers
# ─────────────────────────────────────────────────────────────────────────────

def log_emergency(
    session_id:     str,
    emergency_type: str,
    priority:       str,
    user_text:      str,
    lat:            Optional[float] = None,
    lon:            Optional[float] = None,
    services_count: int = 0,
) -> None:
    """Write a record to the emergency_log table."""
    now = datetime.utcnow().isoformat()
    conn = _get_connection()
    try:
        conn.execute("""
            INSERT INTO emergency_log
                (session_id, timestamp, emergency_type, priority,
                 latitude, longitude, user_text, services_count)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (session_id, now, emergency_type, priority,
              lat, lon, user_text, services_count))
        conn.commit()
    finally:
        conn.close()


def get_emergency_stats() -> Dict:
    """Aggregate stats – handy for a dashboard or health endpoint."""
    conn = _get_connection()
    try:
        total  = conn.execute("SELECT COUNT(*) FROM emergency_log").fetchone()[0]
        by_type = conn.execute("""
            SELECT emergency_type, COUNT(*) as cnt
            FROM emergency_log
            GROUP BY emergency_type
            ORDER BY cnt DESC
        """).fetchall()
        return {
            "total_emergencies": total,
            "by_type": {r["emergency_type"]: r["cnt"] for r in by_type},
        }
    finally:
        conn.close()
