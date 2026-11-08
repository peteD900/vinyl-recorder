"""
One-shot migration: Google Sheets → SQLite.

Self-contained — does NOT depend on vinyl_recorder.gsheets (which has been
removed). Uses gspread directly. Install the extra deps first:

    pip install gspread google-auth

Then run:

    python scripts/migrate_sheets_to_sqlite.py

Env vars required:
    APP_ENV               prod | test
    GOOGLE_SERVICE_ACCOUNT base64-encoded service account JSON
    VINYL_SHEET_PROD      sheet ID (if APP_ENV=prod)
    VINYL_SHEET_TEST      sheet ID (if APP_ENV=test)

Delete this file once the migration is done.
"""

import base64
import json
import os
import sys

from dotenv import load_dotenv

from vinyl_recorder.database import AlbumRepository
from vinyl_recorder.config import get_logger

load_dotenv()
logger = get_logger()


def _resolve_sheet_id() -> str:
    env = os.getenv("APP_ENV")
    if env == "prod":
        sheet_id = os.getenv("VINYL_SHEET_PROD")
    elif env == "test":
        sheet_id = os.getenv("VINYL_SHEET_TEST")
    else:
        raise ValueError(f"APP_ENV must be 'prod' or 'test', got: {env!r}")
    if not sheet_id:
        raise ValueError(f"VINYL_SHEET_{env.upper()} is not set")
    return sheet_id


def _load_sheet_rows(sheet_id: str) -> list[dict]:
    """Connect to Google Sheets and return all rows as list of dicts."""
    import gspread
    from google.oauth2.service_account import Credentials

    service_account_b64 = os.getenv("GOOGLE_SERVICE_ACCOUNT")
    if not service_account_b64:
        raise ValueError("GOOGLE_SERVICE_ACCOUNT is not set")

    info = json.loads(base64.b64decode(service_account_b64))
    creds = Credentials.from_service_account_info(
        info,
        scopes=[
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive",
        ],
    )
    client = gspread.authorize(creds)
    sheet = client.open_by_key(sheet_id).sheet1
    return sheet.get_all_records()


def _row_to_album_data(row: dict) -> dict:
    """Map a sheet row (dict) to the AlbumRepository insert shape."""
    return {
        "image_name": str(row.get("image_name", "")),
        "process_date": str(row.get("process_date", "")),
        "source": str(row.get("source", "local")) or "local",
        "success": bool(row.get("success", False)),
        "artist": str(row.get("artist", "")) or None,
        "album_title": str(row.get("album_title", "")) or None,
        "album_year": str(row.get("album_year", "")) or None,
        "confidence": str(row.get("confidence", "")) or None,
        "cover_image_url": str(row.get("image_url", "")),
        "tracklist": str(row.get("tracklist", "")),
    }


def main():
    logger.info("Starting migration from Google Sheets to SQLite...")

    sheet_id = _resolve_sheet_id()
    rows = _load_sheet_rows(sheet_id)
    logger.info(f"Loaded {len(rows)} rows from Google Sheets")

    repo = AlbumRepository()
    logger.info(f"SQLite database: {repo.db_path}")

    migrated = 0
    skipped = 0
    errors = 0

    for row in rows:
        image_name = str(row.get("image_name", ""))
        if not image_name:
            skipped += 1
            continue

        try:
            if repo.find_by_image_name(image_name):
                skipped += 1
                continue

            repo.add_album(_row_to_album_data(row))
            migrated += 1

        except Exception as e:
            errors += 1
            logger.error(f"Failed to migrate row {image_name!r}: {e}")

    logger.info(
        f"Migration complete: {migrated} migrated, {skipped} skipped, {errors} errors"
    )
    repo.close()

    if errors:
        sys.exit(1)


if __name__ == "__main__":
    main()
