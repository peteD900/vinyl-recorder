import pandas as pd
from pathlib import Path
from datetime import datetime

from vinyl_recorder.config import get_logger
from vinyl_recorder.vinyl_cover_identifier import VinylIdentifier
from vinyl_recorder.vinyl_cover_identifier import VinylData
from vinyl_recorder.ghseets import GoogleSheeter

logger = get_logger()


# ==== DATA MODELS ==== #
class TrackerData(VinylData):
    """
    Format for one row of tracking info
    """

    image_name: str
    source: str
    process_date: str


# ==== TRACKER CLASS ==== #
class CollectionTracker:
    def __init__(
        self,
        sheeter,
        images_path: str = None,
        image_type: str = "jpg",
        source: str = "local",
    ):
        self.images_path = Path(images_path) if images_path else None
        self.image_type = image_type
        self.source = source
        self.sheeter = sheeter

    def get_image_list(self) -> list:
        """
        Get list of full path to all images in the supplied dir images_path.
        """
        images = self.images_path.glob(pattern=f"*.{self.image_type}")
        images = [image for image in images]
        return images

    def load_tracker_sheet(self) -> pd.DataFrame:
        df_tracker = self.sheeter.load_sheet_as_df()
        return df_tracker

    def get_pending_images(self) -> list:
        """
        Compare tracker sheet with full list of images and
        return only those that have not been processed.
        """
        df_processed = self.load_tracker_sheet()
        all_images = self.get_image_list()
        all_image_names = [str(image.name) for image in all_images]

        if df_processed.empty:
            pending = all_images
        else:
            images_got = df_processed["image_name"].unique()
            pending = [
                Path(self.images_path, p)
                for p in all_image_names
                if p not in images_got
            ]

        return pending

    def add_result_local(self, image_path, result: VinylData):
        """
        Add results to google sheet. Column headers (in order):
            1. image_name
            2. process_date
            3. source
            4. success
            5. artist
            6. album_title
            7. album_year
            8. confidence
            9. discogs_title
            10. image_url
            11. tracklist
        """

        image_name = image_path.name
        process_date = datetime.now().isoformat(timespec="seconds")
        source = self.source
        success = result.success
        artist = result.artist
        album_title = result.album_title
        album_year = result.album_year
        confidence = result.confidence

        new_row = [
            image_name,
            process_date,
            source,
            success,
            artist,
            album_title,
            album_year,
            confidence,
            "",  # discogs_title - filled during enrichment
            "",  # image_url - filled during enrichment
            "",  # tracklist - filled during enrichment
        ]

        self.sheeter.append_row(row_data=new_row)

    def add_result_telegram(self, image_name: str, result: VinylData):
        """Add result from Telegram (no full_path)."""
        date_now = datetime.now().isoformat(timespec="seconds")

        new_row = [
            image_name,
            date_now,
            "telegram",  # source
            result.success,
            result.artist,
            result.album_title,
            result.album_year,
            result.confidence,
            "",  # discogs_title
            "",  # image_url
            "",  # tracklist
        ]

        self.sheeter.append_row(row_data=new_row)


if __name__ == "__main__":
    from pyprojroot import here

    sheeter = GoogleSheeter()
    # sheeter.print_headers()

    # set local working dir
    LOCAL_WD = here()

    IMAGES_DIR = LOCAL_WD / "data/test_images"

    tracker = CollectionTracker(sheeter=sheeter, images_path=IMAGES_DIR, source="local")
    identifier = VinylIdentifier()

    # tracker.overwrite_tracker_sheet()

    pending_list = tracker.get_pending_images()

    # for dev mode
    # n = 2
    # pending_list = pending_list[0:n]
    # print(pending_list)

    if len(pending_list) == 0:
        logger.info("No images left to identify")

    for image_path in pending_list:
        result = identifier.identify_image(image_path)
        print(result.model_dump_json(indent=2))
        tracker.add_result_local(image_path, result)
