from pathlib import Path
from datetime import datetime

from vinyl_recorder.config import get_logger
from vinyl_recorder.vinyl_cover_identifier import VinylData
from vinyl_recorder.database import AlbumRepository

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
        repo: AlbumRepository,
        images_path: str = None,
        image_type: str = "jpg",
        source: str = "local",
    ):
        self.images_path = Path(images_path) if images_path else None
        self.image_type = image_type
        self.source = source
        self.repo = repo

    def get_image_list(self) -> list:
        """
        Get list of full path to all images in the supplied dir images_path.
        """
        images = list(self.images_path.glob(pattern=f"*.{self.image_type}"))
        return images

    def get_pending_images(self) -> list:
        """
        Compare database with full list of images and
        return only those that have not been processed.
        """
        all_images = self.get_image_list()
        pending = [
            img for img in all_images
            if not self.repo.find_by_image_name(img.name)
        ]
        return pending

    def _build_album_data(self, image_name: str, source: str, result: VinylData) -> dict:
        """Build an album data dict from identification results."""
        return {
            "image_name": image_name,
            "process_date": datetime.now().isoformat(timespec="seconds"),
            "source": source,
            "success": result.success,
            "artist": result.artist,
            "album_title": result.album_title,
            "album_year": result.album_year,
            "confidence": result.confidence,
        }

    def add_result_local(self, image_path, result: VinylData):
        """Add local identification result to database, skipping duplicates."""
        if self.repo.is_duplicate(result.artist, result.album_title):
            logger.warning(f"Already got data for {result.artist} - {result.album_title}")
            return

        data = self._build_album_data(image_path.name, self.source, result)
        self.repo.add_album(data)

    def add_result_telegram(self, image_name: str, result: VinylData):
        """Add Telegram identification result to database."""
        data = self._build_album_data(image_name, "telegram", result)
        self.repo.add_album(data)
