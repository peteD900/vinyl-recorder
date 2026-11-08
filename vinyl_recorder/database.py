"""SQLite database layer for vinyl collection."""

import sqlite3
import json
from vinyl_recorder.config import Config, get_logger

logger = get_logger()

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS albums (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    image_name TEXT UNIQUE NOT NULL,
    process_date TEXT NOT NULL,
    source TEXT NOT NULL,
    success INTEGER NOT NULL,
    artist TEXT,
    album_title TEXT,
    album_year TEXT,
    confidence TEXT,
    cover_image_url TEXT DEFAULT '',
    tracklist TEXT DEFAULT '',
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_artist_album ON albums(artist, album_title);

CREATE TABLE IF NOT EXISTS to_buy (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    artist TEXT NOT NULL,
    album_title TEXT NOT NULL,
    album_year TEXT,
    verified INTEGER DEFAULT 0,
    notes TEXT,
    added_date TEXT DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(artist, album_title)
);
"""


class AlbumRepository:
    def __init__(self, db_path: str = None):
        self.db_path = str(db_path or Config.db_path())
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
        self._init_schema()
        logger.info(f"Connected to database: {self.db_path}")

    def _init_schema(self):
        """Create tables if they don't exist."""
        self.conn.executescript(SCHEMA_SQL)
        self.conn.commit()

    def close(self):
        self.conn.close()

    # ---- Albums CRUD ---- #

    def add_album(self, album_data: dict) -> int:
        """Insert a new album row. Returns the new row ID."""
        sql = """
            INSERT INTO albums (image_name, process_date, source, success,
                                artist, album_title, album_year, confidence,
                                cover_image_url, tracklist)
            VALUES (:image_name, :process_date, :source, :success,
                    :artist, :album_title, :album_year, :confidence,
                    :cover_image_url, :tracklist)
        """
        defaults = {"cover_image_url": "", "tracklist": ""}
        row = {**defaults, **album_data}
        cursor = self.conn.execute(sql, row)
        self.conn.commit()
        logger.info(f"Added album: {row.get('image_name')}")
        return cursor.lastrowid

    def is_duplicate(self, artist: str, album_title: str) -> bool:
        """Check if an album already exists in the collection (case-insensitive & trimmed)."""
        if not artist or not album_title:
            return False
        sql = """
            SELECT COUNT(*) FROM albums
            WHERE LOWER(TRIM(artist)) = LOWER(TRIM(?))
              AND LOWER(TRIM(album_title)) = LOWER(TRIM(?))
        """
        count = self.conn.execute(sql, (artist, album_title)).fetchone()[0]
        return count > 0

    def deduplicate_collection(self) -> list[dict]:
        """
        Find duplicate albums (same artist and title case-insensitively).
        Keep the best record (one with cover art and tracklist, or lowest id)
        and delete redundant duplicates. Returns list of removed album info.
        """
        sql = """
            SELECT LOWER(TRIM(artist)) as norm_artist,
                   LOWER(TRIM(album_title)) as norm_title,
                   COUNT(*) as cnt
            FROM albums
            GROUP BY norm_artist, norm_title
            HAVING cnt > 1
        """
        duplicate_groups = self.conn.execute(sql).fetchall()
        removed = []

        for group in duplicate_groups:
            rows = self.conn.execute(
                """
                SELECT id, artist, album_title, cover_image_url, tracklist
                FROM albums
                WHERE LOWER(TRIM(artist)) = ? AND LOWER(TRIM(album_title)) = ?
                ORDER BY
                    CASE WHEN cover_image_url IS NOT NULL AND cover_image_url != '' THEN 1 ELSE 0 END DESC,
                    CASE WHEN tracklist IS NOT NULL AND tracklist != '' AND tracklist != '[]' THEN 1 ELSE 0 END DESC,
                    id ASC
                """,
                (group["norm_artist"], group["norm_title"]),
            ).fetchall()

            if len(rows) > 1:
                keep_id = rows[0]["id"]
                for dup in rows[1:]:
                    dup_id = dup["id"]
                    self.delete_album(dup_id)
                    removed.append({
                        "id": dup_id,
                        "artist": dup["artist"],
                        "album_title": dup["album_title"],
                        "kept_id": keep_id,
                    })

        return removed

    def get_all_albums(self) -> list[dict]:
        """Return all albums as a list of dicts."""
        rows = self.conn.execute("SELECT * FROM albums ORDER BY artist COLLATE NOCASE").fetchall()
        return [dict(row) for row in rows]

    def get_albums_needing_enrichment(self) -> list[dict]:
        """Return albums where cover_image_url or tracklist is empty."""
        sql = """
            SELECT * FROM albums
            WHERE success = 1
              AND (cover_image_url IS NULL OR cover_image_url = ''
                   OR tracklist IS NULL OR tracklist = '')
        """
        rows = self.conn.execute(sql).fetchall()
        return [dict(row) for row in rows]

    def update_album(self, album_id: int, updates: dict):
        """Update specific fields on an album row."""
        set_clause = ", ".join(f"{key} = ?" for key in updates)
        values = list(updates.values()) + [album_id]
        sql = f"UPDATE albums SET {set_clause} WHERE id = ?"
        self.conn.execute(sql, values)
        self.conn.commit()

    def delete_album(self, album_id: int):
        """Delete an album by its ID."""
        self.conn.execute("DELETE FROM albums WHERE id = ?", (album_id,))
        self.conn.commit()
        logger.info(f"Deleted album: {album_id}")

    def find_by_image_name(self, image_name: str) -> dict | None:
        """Find an album by its image_name."""
        row = self.conn.execute(
            "SELECT * FROM albums WHERE image_name = ?", (image_name,)
        ).fetchone()
        return dict(row) if row else None

    def get_album_titles(self) -> list[str]:
        """Get list of 'artist - album_title' strings for the recommender."""
        rows = self.conn.execute(
            "SELECT artist, album_title FROM albums WHERE success = 1"
        ).fetchall()
        return [f"{row['artist']} - {row['album_title']}" for row in rows]

    # ---- To Buy CRUD ---- #

    def add_to_buy(self, artist: str, album_title: str, album_year: str = None,
                   verified: bool = False, notes: str = None) -> int:
        """Add an album to the to_buy list. Returns the new row ID."""
        sql = """
            INSERT INTO to_buy (artist, album_title, album_year, verified, notes)
            VALUES (?, ?, ?, ?, ?)
        """
        cursor = self.conn.execute(sql, (artist, album_title, album_year, int(verified), notes))
        self.conn.commit()
        logger.info(f"Added to buy list: {artist} - {album_title}")
        return cursor.lastrowid

    def get_to_buy_list(self) -> list[dict]:
        """Return all items on the to_buy list."""
        rows = self.conn.execute("SELECT * FROM to_buy ORDER BY added_date DESC").fetchall()
        return [dict(row) for row in rows]

    def remove_from_to_buy(self, item_id: int):
        """Remove an item from the to_buy list by ID."""
        self.conn.execute("DELETE FROM to_buy WHERE id = ?", (item_id,))
        self.conn.commit()

    def is_on_buy_list(self, artist: str, album_title: str) -> bool:
        """Check if an album is already on the to_buy list."""
        sql = "SELECT COUNT(*) FROM to_buy WHERE artist = ? AND album_title = ?"
        count = self.conn.execute(sql, (artist, album_title)).fetchone()[0]
        return count > 0

    def already_owned(self, artist: str, album_title: str) -> bool:
        """Check if an album is already in the collection (alias for is_duplicate)."""
        return self.is_duplicate(artist, album_title)
