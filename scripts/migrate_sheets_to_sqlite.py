"""
One-time migration: Google Sheets → SQLite.

Pulls all rows from the existing Google Sheet and inserts them into the
new SQLite database. Run once before removing the Sheets code entirely.

Usage: python scripts/migrate_sheets_to_sqlite.py
"""

from vinyl_recorder.gsheets import GoogleSheeter
from vinyl_recorder.database import AlbumRepository
from vinyl_recorder.config import get_logger

logger = get_logger()


def main():
    logger.info("Starting migration from Google Sheets to SQLite...")

    # Load data from Google Sheets
    sheeter = GoogleSheeter()
    df = sheeter.refresh_df()
    logger.info(f"Loaded {len(df)} rows from Google Sheets")

    # Initialize SQLite repository
    repo = AlbumRepository()
    logger.info(f"SQLite database: {repo.db_path}")

    migrated = 0
    skipped = 0
    errors = 0

    for _, row in df.iterrows():
        try:
            album_data = {
                "image_name": str(row.get("image_name", "")),
                "process_date": str(row.get("process_date", "")),
                "source": str(row.get("source", "local")),
                "success": bool(row.get("success", False)),
                "artist": str(row.get("artist", "")) or None,
                "album_title": str(row.get("album_title", "")) or None,
                "album_year": str(row.get("album_year", "")) or None,
                "confidence": str(row.get("confidence", "")) or None,
                "cover_image_url": str(row.get("image_url", "")),
                "tracklist": str(row.get("tracklist", "")),
            }

            # Skip if already migrated (by image_name uniqueness)
            if repo.find_by_image_name(album_data["image_name"]):
                skipped += 1
                continue

            repo.add_album(album_data)
            migrated += 1

        except Exception as e:
            errors += 1
            logger.error(f"Failed to migrate row: {row.get('image_name', '?')} - {e}")

    logger.info(
        f"Migration complete: {migrated} migrated, {skipped} skipped, {errors} errors"
    )
    repo.close()


if __name__ == "__main__":
    main()
