# database_manager.py
import sqlite3
import json
from pathlib import Path
import datetime
from typing import Optional, List, Dict

class DatabaseManager:
    def __init__(self, db_path: Path):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(str(self.db_path))
        self.conn.row_factory = sqlite3.Row
        print("DB PATH:", self.db_path.resolve())
        self._create_tables()

    def _create_tables(self):
        cur = self.conn.cursor()
        cur.execute("""
        CREATE TABLE IF NOT EXISTS notebooks (
            id TEXT PRIMARY KEY,
            title TEXT,
            path TEXT,
            scene_json TEXT,
            created_at TEXT
        )
        """)
        self.conn.commit()

    def list_notebooks(self) -> List[Dict]:
        cur = self.conn.cursor()
        cur.execute("SELECT id, title, path, scene_json, created_at FROM notebooks ORDER BY created_at")
        rows = cur.fetchall()
        return [dict(r) for r in rows]

    def get_notebook(self, nb_id: str) -> Optional[Dict]:
        cur = self.conn.cursor()
        cur.execute("SELECT id, title, path, scene_json, created_at FROM notebooks WHERE id=?", (nb_id,))
        row = cur.fetchone()
        return dict(row) if row else None

    def create_notebook(self, nb_id: str, title: str, path: str, scene_json: str | None = None):
        cur = self.conn.cursor()
        created_at = datetime.datetime.now().isoformat()
        cur.execute("""
            INSERT OR REPLACE INTO notebooks(id, title, path, scene_json, created_at) 
            VALUES (?, ?, ?, ?, ?)
        """, (nb_id, title, path, scene_json or "{}", created_at))
        self.conn.commit()

    def update_notebook(self, nb_id: str, title: str | None = None, scene_json: str | None = None, path: str | None = None):
        cur = self.conn.cursor()
        # Build update dynamically
        fields = []
        params = []
        if title is not None:
            fields.append("title=?"); params.append(title)
        if scene_json is not None:
            fields.append("scene_json=?"); params.append(scene_json)
        if path is not None:
            fields.append("path=?"); params.append(path)
        if not fields:
            return
        params.append(nb_id)
        sql = "UPDATE notebooks SET " + ", ".join(fields) + " WHERE id=?"
        cur.execute(sql, params)
        self.conn.commit()

    def delete_notebook(self, nb_id: str):
        cur = self.conn.cursor()
        cur.execute("DELETE FROM notebooks WHERE id=?", (nb_id,))
        self.conn.commit()

    def close(self):
        try:
            self.conn.close()
        except Exception:
            pass
