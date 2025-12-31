import os
import pandas as pd
import base64
import json
import gspread
from vinyl_recorder.config import Config, get_logger
from google.oauth2.service_account import Credentials

logger = get_logger()


class GoogleSheeter:
    def __init__(self):
        logger.info(f"Running sheeter in {Config.APP_ENV.upper()} mode")
        self.client = self.connect_client()
        self.sheet_id = Config.vinyl_sheet_id()
        self.sheet = self.load_sheet()
        self.df_sheet = self.load_sheet_as_df()

    def connect_client(self):
        json_bytes = base64.b64decode(Config.GOOGLE_SERVICE_ACCOUNT)
        service_account_info = json.loads(json_bytes)
        creds = Credentials.from_service_account_info(
            service_account_info,
            scopes=[
                "https://www.googleapis.com/auth/spreadsheets",
                "https://www.googleapis.com/auth/drive",
            ],
        )
        client = gspread.authorize(creds)
        return client

    def load_sheet(self):
        """Load google sheet"""
        spreadsheet = self.client.open_by_key(self.sheet_id)
        sheet = spreadsheet.sheet1
        return sheet

    def load_sheet_as_df(self) -> pd.DataFrame:
        """Load sheet data as pandas DataFrame."""
        data = self.sheet.get_all_records()
        return pd.DataFrame(data)

    def refresh_df(self):
        """Reload DataFrame from sheet (call after making changes)."""
        self.df_sheet = self.load_sheet_as_df()
        return self.df_sheet

    def get_existing_values(self, column_name: str) -> set:
        """Get unique values from a column as a set."""
        df = self.refresh_df()
        if column_name in df.columns:
            return set(df[column_name].dropna().unique())
        return set()

    def is_duplicate(self, artist: str, album_title: str) -> bool:
        """Check if album already exists in sheet."""

        df = self.refresh_df()
        # Handle empty sheet
        if df.empty or "artist" not in df.columns:
            return False

        matches = df[(df["artist"] == artist) & (df["album_title"] == album_title)]
        return len(matches) > 0

    def append_row(self, row_data: list):
        """
        Append a new row to the sheet.
        row_data should be a list matching column order.
        """
        self.sheet.append_row(row_data)
        logger.info(f"Appended row: {row_data[0]}")

    def find_row_by_image_name(self, image_name: str) -> int:
        """
        Find row number for a given image_name.
        Returns row number (1-indexed) or None if not found.
        """
        try:
            cell = self.sheet.find(image_name)
            return cell.row
        except gspread.exceptions.CellNotFound:
            logger.warning(f"Image not found: {image_name}")
            return None

    def update_cell(self, row_num: int, col_num: int, value):
        """Update a specific cell."""
        self.sheet.update_cell(row_num, col_num, value)

    def update_row_cells(self, row_num: int, updates: dict):
        """
        Update multiple cells in a row.
        updates is a dict of {column_name: value}
        """
        # Get column positions from headers
        headers = self.sheet.row_values(1)

        for col_name, value in updates.items():
            col_num = headers.index(col_name) + 1  # 1-indexed
            self.update_cell(row_num, col_num, value)

        logger.info(f"Updated row {row_num}")

    def iterate_rows_needing_enrichment(self):
        """
        Generator that yields rows missing enrichment data.
        Yields (row_number, row_dict) for each row needing enrichment.
        """
        df = self.refresh_df()

        # Handle empty sheet or missing column
        if df.empty or "discogs_title" not in df.columns:
            return  # No rows to enrich

        # Find rows where discogs_title is empty/missing
        mask = (df["discogs_title"].isna()) | (df["discogs_title"] == "")
        rows_needing_enrichment = df[mask]

        for idx, row in rows_needing_enrichment.iterrows():
            # Find actual sheet row number (accounting for header)
            row_num = idx + 2  # +2 because: +1 for header, +1 for 1-indexing
            yield row_num, row.to_dict()

    def get_column_number(self, column_name: str) -> int:
        """Get column number (1-indexed) for a column name."""
        headers = self.sheet.row_values(1)
        if column_name in headers:
            return headers.index(column_name) + 1
        return None

    def get_headers(self) -> list:
        """Get list of column headers from sheet."""
        headers = self.sheet.row_values(1)
        return headers

    def print_headers(self):
        """Print headers in useful formats for building row data."""
        headers = self.get_headers()

        print("Column headers (in order):")
        for i, header in enumerate(headers, 1):
            print(f"  {i}. {header}")

        print("\nAs Python list:")
        print(f"  {headers}")


if __name__ == "__main__":
    sheeter = GoogleSheeter()

    # Test getting data
    df_sheet = sheeter.df_sheet
    sheeter.print_headers()
