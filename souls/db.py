"""The database: one SQLite file, its schema, and the game data loaded from data/*.json."""
import json
import sqlite3
from pathlib import Path

DATA = Path(__file__).resolve().parent.parent / "data"

SCHEMA = """
CREATE TABLE IF NOT EXISTS areas (
    slug TEXT PRIMARY KEY,
    name TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS bosses (
    slug TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    area TEXT NOT NULL REFERENCES areas(slug),
    required INTEGER NOT NULL,
    lord_soul INTEGER NOT NULL,
    position INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS classes (
    slug TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    level INTEGER NOT NULL
);
"""


def connect(path):
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def _load(name):
    with open(DATA / f"{name}.json", encoding="utf-8") as f:
        return json.load(f)


def init(path):
    """Create the tables and load the game data. Safe to run again: rows are updated, never duplicated."""
    conn = connect(path)
    with conn:
        conn.executescript(SCHEMA)
        conn.executemany(
            "INSERT INTO areas (slug, name) VALUES (:slug, :name) "
            "ON CONFLICT(slug) DO UPDATE SET name = excluded.name",
            _load("areas"))
        conn.executemany(
            "INSERT INTO classes (slug, name, level) VALUES (:slug, :name, :level) "
            "ON CONFLICT(slug) DO UPDATE SET name = excluded.name, level = excluded.level",
            _load("classes"))
        bosses = [dict(b, position=i) for i, b in enumerate(_load("bosses"))]
        conn.executemany(
            "INSERT INTO bosses (slug, name, area, required, lord_soul, position) "
            "VALUES (:slug, :name, :area, :required, :lord_soul, :position) "
            "ON CONFLICT(slug) DO UPDATE SET name = excluded.name, area = excluded.area, "
            "required = excluded.required, lord_soul = excluded.lord_soul, position = excluded.position",
            bosses)
    conn.close()
