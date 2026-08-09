"""
database.py — SQLite-backed caller memory for the Financial Services voice agent.

Schema (table: callers):
  user_id           TEXT PRIMARY KEY   — LiveKit participant identity (stable UUID from browser)
  name              TEXT               — caller's preferred name
  language_preference TEXT             — e.g. "en", "hi-en" (Hinglish)
  facts             TEXT               — JSON blob: schemes discussed, eligibility answers
  last_interaction  TEXT               — ISO-8601 UTC timestamp

Privacy rules (Financial Services — hard rules):
  - NEVER store: account numbers, PAN, Aadhaar, OTP, PIN, passwords, credit scores,
    transaction histories, or any security credentials.
  - Only store what the agent explicitly asks consent for.
"""

import json
import logging
import os
import sqlite3
from datetime import datetime, timezone

logger = logging.getLogger("agent.database")

# DB file sits one level above src/, inside the backend/ directory
_DB_PATH = os.path.join(os.path.dirname(__file__), "..", "caller_memory.db")


def _get_connection() -> sqlite3.Connection:
    """Return a connection with row_factory set to dict-like rows."""
    conn = sqlite3.connect(os.path.abspath(_DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    """Create the callers table if it does not already exist. Call once at startup."""
    with _get_connection() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS callers (
                user_id            TEXT PRIMARY KEY,
                name               TEXT,
                language_preference TEXT,
                facts              TEXT DEFAULT '{}',
                last_interaction   TEXT
            )
            """
        )
        conn.commit()
    logger.info("Database initialised at %s", os.path.abspath(_DB_PATH))


def lookup_caller(user_id: str) -> dict | None:
    """
    Look up a caller by their stable user_id.

    Returns a dict with keys: user_id, name, language_preference, facts (dict),
    last_interaction — or None if the caller is not found.
    """
    with _get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM callers WHERE user_id = ?", (user_id,)
        ).fetchone()

    if row is None:
        return None

    record = dict(row)
    # Deserialise the JSON facts blob
    try:
        record["facts"] = json.loads(record["facts"] or "{}")
    except (json.JSONDecodeError, TypeError):
        record["facts"] = {}

    logger.info("Caller found: user_id=%s name=%s", user_id, record.get("name"))
    return record


def save_caller(record: dict) -> None:
    """
    Upsert a caller record.  The record dict must contain 'user_id'.
    Automatically sets / updates 'last_interaction' to the current UTC time.

    Expected keys (all optional except user_id):
      user_id, name, language_preference, facts (dict), last_interaction
    """
    user_id = record.get("user_id")
    if not user_id:
        raise ValueError("save_caller: record must contain a non-empty 'user_id'")

    name = record.get("name", "")
    language_preference = record.get("language_preference", "")
    facts_raw = json.dumps(record.get("facts", {}), ensure_ascii=False)
    last_interaction = datetime.now(timezone.utc).isoformat()

    with _get_connection() as conn:
        conn.execute(
            """
            INSERT INTO callers (user_id, name, language_preference, facts, last_interaction)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                name               = excluded.name,
                language_preference = excluded.language_preference,
                facts              = excluded.facts,
                last_interaction   = excluded.last_interaction
            """,
            (user_id, name, language_preference, facts_raw, last_interaction),
        )
        conn.commit()

    logger.info(
        "Caller saved: user_id=%s name=%s last_interaction=%s",
        user_id,
        name,
        last_interaction,
    )
