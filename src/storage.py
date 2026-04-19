import sqlite3
from pathlib import Path
from typing import Any, Dict, List


class StorageEngine:
    def __init__(self, db_path: str = "data/github_relations.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
        self._init_db()

    def _init_db(self):
        """Initialize the database schema."""
        cursor = self.conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY,
                login TEXT NOT NULL UNIQUE,
                avatar_url TEXT,
                html_url TEXT
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS relations (
                owner_login TEXT NOT NULL,
                target_id INTEGER NOT NULL,
                relation_type TEXT NOT NULL CHECK(relation_type IN ('followers', 'following')),

                PRIMARY KEY (owner_login, target_id, relation_type),
                FOREIGN KEY (target_id) REFERENCES users(id)
            )
        """)
        self.conn.commit()

    def save_users(
        self, owner_login: str, users: List[Dict[str, Any]], relation_type: str
    ):
        """Save users and their relationship to the owner."""
        cursor = self.conn.cursor()

        # Upsert users
        for user in users:
            cursor.execute(
                """
                INSERT INTO users (id, login, avatar_url, html_url)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    login=excluded.login,
                    avatar_url=excluded.avatar_url,
                    html_url=excluded.html_url
            """,
                (user["id"], user["login"], user["avatar_url"], user["html_url"]),
            )

            # Upsert relationship
            cursor.execute(
                """
                INSERT OR IGNORE INTO relations (owner_login, target_id, relation_type)
                VALUES (?, ?, ?)
            """,
                (owner_login, user["id"], relation_type),
            )

        self.conn.commit()

    def get_relations(
        self, owner_login: str, relation_type: str
    ) -> List[Dict[str, Any]]:
        """Get users by relationship type."""
        cursor = self.conn.cursor()
        cursor.execute(
            """
            SELECT u.* FROM users u
            JOIN relations r ON u.id = r.target_id
            WHERE r.owner_login = ? AND r.relation_type = ?
        """,
            (owner_login, relation_type),
        )
        return [dict(row) for row in cursor.fetchall()]

    def close(self):
        self.conn.close()
