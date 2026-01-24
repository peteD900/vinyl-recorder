from pydantic import BaseModel
import sqlite3
import json
import pandas as pd
from pathlib import Path
from vinyl_recorder.config import Config, get_logger
from vinyl_recorder.data_models import Vinyl

logger = get_logger()


class VinylDatabase:
    """Manages SQLite database for vinyl collection"""

    def __init__(self, db_path: str = Config.db_path()):
        self.db_path = Path(db_path)
        self._create_table()

    def _get_connection(self):
        """Get a database connection"""
        return sqlite3.connect(self.db_path)

    def _create_table(self):
        """Create the vinyls table if it doesn't exist"""

        db_exists = self.db_path.exists()

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS vinyls (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    image_name TEXT,
                    process_date TEXT,
                    source TEXT,
                    success TEXT,
                    artist TEXT,
                    album_title TEXT,
                    album_year INTEGER,
                    discogs_attempted INTEGER DEFAULT 0,
                    discogs_title TEXT,
                    image_url TEXT,
                    tracklist TEXT,
                    UNIQUE(artist, album_title)
                )
            """)

        if db_exists:
            logger.info(f"SQLite file already exists: {self.db_path.name}")
        else:
            logger.info(f"Database initialized at {self.db_path}")

    def add_vinyl(self, vinyl: Vinyl) -> int | None:
        """Add a new vinyl record, returns the new ID or None if already exists"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            tracklist_json = json.dumps(vinyl.tracklist) if vinyl.tracklist else None

            try:
                cursor.execute(
                    """
                    INSERT OR IGNORE INTO vinyls (
                        image_name, process_date, source, success,
                        artist, album_title, album_year, 
                        discogs_title, image_url, tracklist
                    ) VALUES (
                        :image_name, :process_date, :source, :success,
                        :artist, :album_title, :album_year, 
                        :discogs_title, :image_url, :tracklist
                    )
                    """,
                    {
                        "image_name": vinyl.image_name,
                        "process_date": vinyl.process_date,
                        "source": vinyl.source,
                        "success": vinyl.success,
                        "artist": vinyl.artist,
                        "album_title": vinyl.album_title,
                        "album_year": vinyl.album_year,
                        "discogs_title": vinyl.discogs_title,
                        "image_url": vinyl.image_url,
                        "tracklist": tracklist_json,
                    },
                )
                vinyl_id = cursor.lastrowid

                if vinyl_id == 0:
                    logger.info(
                        f"Vinyl already exists: {vinyl.artist} - {vinyl.album_title}"
                    )
                    return None

                logger.info(
                    f"Added vinyl: {vinyl.artist} - {vinyl.album_title} (ID: {vinyl_id})"
                )
                return vinyl_id

            except sqlite3.IntegrityError as e:
                logger.warning(f"Failed to add vinyl: {e}")
                return None

    def unpack_tracklist(self, df: pd.DataFrame) -> pd.DataFrame:
        """Unpacks the json tracklist to string."""

        if df.empty:
            return df

        df["tracklist"] = df["tracklist"].apply(lambda x: json.loads(x) if x else None)

        return df

    def get_all_vinyls(self) -> pd.DataFrame:
        """Get all vinyl records as a DataFrame"""
        with self._get_connection() as conn:
            df = pd.read_sql_query("SELECT * FROM vinyls", conn)

        df = self.unpack_tracklist(df)

        logger.info(f"Retrieved {len(df)} vinyls from database")
        return df

    def get_vinyl_by_artist_album(self, artist: str, album_title: str) -> pd.DataFrame:
        """Get vinyl by artist and album as DataFrame"""
        with self._get_connection() as conn:
            df = pd.read_sql_query(
                """
                SELECT * FROM vinyls 
                WHERE artist = ? AND album_title = ?
            """,
                conn,
                params=(artist, album_title),
            )

        # return none or df?
        if df.empty:
            logger.info(f"No vinyl found for artist: {artist}, album: {album_title}")
            return pd.DataFrame()

        df = self.unpack_tracklist(df)

        return df

    def get_vinyls_needing_enrichment(self) -> pd.DataFrame:
        """Get all vinyls that haven't been enriched yet"""
        with self._get_connection() as conn:
            df = pd.read_sql_query(
                """
                SELECT * FROM vinyls 
                WHERE discogs_attempted = 0
            """,
                conn,
            )

        logger.info(f"Found {len(df)} vinyls needing enrichment")
        return df

    def update_vinyl_enrichment(
        self,
        vinyl_id: int,
        discogs_title: str | None = None,
        image_url: str | None = None,
        tracklist: list[str] | None = None,
    ) -> bool:
        """Update a vinyl's enrichment data and mark as attempted"""
        with self._get_connection() as conn:
            cursor = conn.cursor()

            tracklist_json = json.dumps(tracklist) if tracklist else None

            cursor.execute(
                """
                UPDATE vinyls 
                SET discogs_title = :discogs_title,
                    image_url = :image_url,
                    tracklist = :tracklist
                WHERE id = :id
            """,
                {
                    "id": vinyl_id,
                    "discogs_title": discogs_title,
                    "image_url": image_url,
                    "tracklist": tracklist_json,
                },
            )

            rows_affected = cursor.rowcount

        if rows_affected > 0:
            logger.info(f"Updated enrichment for vinyl ID: {vinyl_id}")
            return True
        else:
            logger.warning(f"No vinyl found with ID: {vinyl_id}")
            return False

    def mark_discogs_attempted(self, vinyl_id: int) -> bool:
        """Mark attempted to enrich this vinyl"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                UPDATE vinyls 
                SET discogs_attempted = 1
                WHERE id = :id
            """,
                {"id": vinyl_id},
            )
            rows_affected = cursor.rowcount

        if rows_affected > 0:
            logger.info(f"Marked vinyl ID {vinyl_id} as attempted")
            return True
        return False


if __name__ == "__main__":
    db = VinylDatabase()

    def load_test_json(test_no: int) -> json:
        test_path = Config.DATA_DIR / "test_data/vinyl_examples.json"

        with open(test_path) as f:
            test_data = json.load(f)

        ts1 = Vinyl(**test_data[test_no])
        return ts1

    tvx = load_test_json(1)

    idx = db.add_vinyl(vinyl=tvx)
    df = db.get_all_vinyls()
    df

    df_need_enrichment = db.get_vinyls_needing_enrichment()
    # df_need_enrichment = df

    # for _, row in df_need_enrichment.iterrows():
    #     idr = row["id"]
    #     db.update_vinyl_enrichment(
    #         vinyl_id=idr, discogs_title=f"fake_{idr}", image_url="test.com", tracklist=["t1", "t2"]
    #     )
    #     db.mark_discogs_attempted(vinyl_id=idr)

    # db.get_vinyl_by_artist_album(artist="The Beatles", album_title="Abbey Road")
    # db.get_vinyl_by_artist_album(artist="dhdh", album_title="Abbey Road")
