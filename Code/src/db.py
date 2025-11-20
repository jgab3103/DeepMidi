import sqlite3
import json
from pathlib import Path
from .utils import now_iso, now_ts

DB_PATH = Path(__file__).resolve().parents[1] / "data" / "midi.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS devices (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE,
    parent_device TEXT,
    midi_in_port TEXT,
    midi_out_port TEXT,
    default_channel INTEGER,
    notes TEXT,
    created_at TEXT
);

CREATE TABLE IF NOT EXISTS midi_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts REAL,
    ts_iso TEXT,
    src_port TEXT,
    src_device TEXT,
    src_channel INTEGER,
    msg_type TEXT,
    note INTEGER,
    velocity INTEGER,
    control INTEGER,
    value INTEGER,
    raw_bytes BLOB,
    parsed_json TEXT
);
"""

class DB:
    def __init__(self, db_path=DB_PATH):
        db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(str(db_path), check_same_thread=False)
        self.conn.execute("PRAGMA journal_mode=WAL;")
        self.conn.execute("PRAGMA synchronous=NORMAL;")
        self._init_schema()

    def _init_schema(self):
        self.conn.executescript(SCHEMA)
        self.conn.commit()

    def upsert_device(self, name, parent_device=None, midi_in_port=None, midi_out_port=None, default_channel=None, notes=None):
        now = now_iso()
        cur = self.conn.cursor()
        cur.execute("""
        INSERT INTO devices (name, parent_device, midi_in_port, midi_out_port, default_channel, notes, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(name) DO UPDATE SET
            parent_device=excluded.parent_device,
            midi_in_port=excluded.midi_in_port,
            midi_out_port=excluded.midi_out_port,
            default_channel=excluded.default_channel,
            notes=excluded.notes
        """, (name, parent_device, midi_in_port, midi_out_port, default_channel, json.dumps(notes) if notes else None, now))
        self.conn.commit()

    def insert_midi_event(self, src_port, src_device, src_channel, msg, parsed=None):
        ts = now_ts()
        ts_iso = now_iso()
        raw = bytes(msg.bytes()) if hasattr(msg, "bytes") else None
        cur = self.conn.cursor()
        cur.execute("""
        INSERT INTO midi_events (ts, ts_iso, src_port, src_device, src_channel, msg_type, note, velocity, control, value, raw_bytes, parsed_json)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (ts, ts_iso, src_port, src_device, src_channel, msg.type, getattr(msg, "note", None), getattr(msg, "velocity", None), getattr(msg, "control", None), getattr(msg, "value", None), raw, json.dumps(parsed) if parsed else None))
        self.conn.commit()

    def close(self):
        self.conn.close()

