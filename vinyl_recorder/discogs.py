import discogs_client
import json
from pydantic import BaseModel
from typing import Optional
from vinyl_recorder.config import Config, get_logger
from vinyl_recorder.ghseets import GoogleSheeter

logger = get_logger()
TOKEN = Config.DISCOGS_API_KEY


# ==== DATA MODELS ==== #
class DiscogsData(BaseModel):
    discogs_title: str
    tracklist: list
    image_url: str


class DiscogEnricher:
    def __init__(self, sheeter):
        self.d = discogs_client.Client("vinyl_recorder/1.0", user_token=TOKEN)
        self.sheeter = sheeter

    def search_discogs(self, artist: str, album: str) -> Optional[DiscogsData]:
        """
        Search discogs db for album data.
        Returns None if not found.
        """
        try:
            query = f"{artist} {album}"
            results = self.d.search(query, type="release")

            # Check if any results
            if not results or results.count == 0:
                logger.warning(f"No Discogs results for: {artist} - {album}")
                return None

            page1 = results.page(1)
            item = page1[0]

            title = item.title

            # Get tracklist
            tracklist = []
            if hasattr(item, "tracklist") and item.tracklist:
                tracklist = [
                    f"{track.position} {track.title}" for track in item.tracklist
                ]

            # Get image URL
            image_url = ""
            if hasattr(item, "images") and item.images:
                image_url = item.images[0].get("uri150", "")

            if not image_url:
                logger.warning(f"No image found for: {artist} - {album}")

            return DiscogsData(
                discogs_title=title,
                tracklist=tracklist,
                image_url=image_url,
            )

        except IndexError as e:
            logger.error(f"Index error searching Discogs for {artist} - {album}: {e}")
            return None
        except Exception as e:
            logger.error(f"Error searching Discogs for {artist} - {album}: {e}")
            return None

    def enrich_row(self, row_num: int, artist: str, album: str):
        """
        Search Discogs for one row and update the sheet.
        """
        logger.info(f"Enriching row {row_num}: {artist} - {album}")

        discogs_data = self.search_discogs(artist, album)

        if discogs_data:
            # Convert tracklist to JSON string for storage
            tracklist_json = json.dumps(discogs_data.tracklist)

            # Update the row
            self.sheeter.update_row_cells(
                row_num,
                {
                    "discogs_title": discogs_data.discogs_title,
                    "image_url": discogs_data.image_url,
                    "tracklist": tracklist_json,
                },
            )

            logger.info(f"✓ Enriched: {artist} - {album}")
            return True
        else:
            logger.warning(f"✗ Could not enrich: {artist} - {album}")
            return False

    def enrich_all_pending(self):
        """
        Enrich all rows that are missing Discogs data.
        """

        logger.info("Starting enrichment process...")

        for row_num, row_data in self.sheeter.iterate_rows_needing_enrichment():
            artist = row_data.get("artist")
            album = row_data.get("album_title")

            self.enrich_row(row_num, artist, album)

        logger.info("Enrichment complete")


if __name__ == "__main__":
    # Initialize with shared sheeter
    sheeter = GoogleSheeter()
    enricher = DiscogEnricher(sheeter)

    # Option 1: Enrich all pending rows
    enricher.enrich_all_pending()

    # Option 2: Enrich specific row manually
    # enricher.enrich_row(row_num=2, artist="Nirvana", album="Nevermind")

    # View results
    df = enricher.sheeter.refresh_df()
    print(df[["artist", "album_title", "discogs_title", "image_url"]])
