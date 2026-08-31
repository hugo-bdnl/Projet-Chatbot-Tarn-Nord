"""Base SQLite (bibliothèque standard) : annuaire, configuration métier, journal des questions.

Une connexion est ouverte par opération (peu coûteux en SQLite, et sans problème de threads avec
FastAPI qui exécute les endpoints synchrones dans un pool). Le mode WAL autorise les lectures
pendant une écriture.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS organizations (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT COLLATE NOCASE NOT NULL UNIQUE,
    description TEXT NOT NULL DEFAULT '',
    website     TEXT NOT NULL DEFAULT '',
    keywords    TEXT NOT NULL DEFAULT '[]',
    active      INTEGER NOT NULL DEFAULT 1,
    created_at  TEXT NOT NULL,
    updated_at  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS sites (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    organization_id INTEGER NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    label       TEXT NOT NULL DEFAULT '',
    address     TEXT NOT NULL DEFAULT '',
    postal_code TEXT NOT NULL DEFAULT '',
    city        TEXT NOT NULL DEFAULT '',
    position    INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_sites_org ON sites(organization_id);

CREATE TABLE IF NOT EXISTS contacts (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    organization_id INTEGER NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    last_name   TEXT NOT NULL DEFAULT '',
    first_name  TEXT NOT NULL DEFAULT '',
    role        TEXT NOT NULL DEFAULT '',
    email       TEXT NOT NULL DEFAULT '',
    phone       TEXT NOT NULL DEFAULT '',
    position    INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_contacts_org ON contacts(organization_id);

CREATE TABLE IF NOT EXISTS domains (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT COLLATE NOCASE NOT NULL UNIQUE,
    description TEXT NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS organization_domains (
    organization_id INTEGER NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    domain_id       INTEGER NOT NULL REFERENCES domains(id) ON DELETE CASCADE,
    position        INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (organization_id, domain_id)
);

CREATE TABLE IF NOT EXISTS settings (
    key        TEXT PRIMARY KEY,
    value      TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS queries (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    ts            TEXT NOT NULL,            -- UTC ISO 8601
    local_date    TEXT NOT NULL,            -- AAAA-MM-JJ heure locale du serveur
    local_hour    INTEGER NOT NULL,
    question      TEXT NOT NULL,
    question_norm TEXT NOT NULL,
    answered      INTEGER NOT NULL,
    intent        TEXT NOT NULL,
    category      TEXT,
    top_score     REAL,
    latency_ms    REAL NOT NULL,
    mode          TEXT NOT NULL,
    organizations TEXT NOT NULL DEFAULT '[]',  -- JSON : noms des acteurs proposés
    session_hash  TEXT,
    helpful       INTEGER,
    feedback_comment TEXT,
    feedback_ts   TEXT
);
CREATE INDEX IF NOT EXISTS idx_queries_ts ON queries(ts);
"""


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class Database:
    def __init__(self, path: Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as conn:
            conn.execute("PRAGMA journal_mode = WAL")
            conn.executescript(SCHEMA)

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(self.path, timeout=30)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()
