import discogs_client
import json
from typing import Optional
from vinyl_recorder.config import Config, get_logger
from vinyl_recorder.vinyl_db import VinylDatabase
from vinyl_recorder.data_models import DiscogsData

logger = get_logger()
TOKEN = Config.DISCOGS_API_KEY


# ==== DATA MODELS ==== #
class DiscogEnricher:
    def __init__(self, db: VinylDatabase):
        self.d = discogs_client.Client("vinyl_recorder/1.0", user_token=TOKEN)
        self.db = db

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

    def enrich_vinyl(self, vinyl_id: int, artist: str, album: str) -> bool:
        """
        Search Discogs for one vinyl and update the database.
        """
        logger.info(f"Enriching vinyl ID {vinyl_id}: {artist} - {album}")
        discogs_data = self.search_discogs(artist, album)

        if discogs_data:
            # Update the vinyl in database
            success = self.db.update_vinyl_enrichment(
                vinyl_id=vinyl_id,
                discogs_title=discogs_data.discogs_title,
                image_url=discogs_data.image_url,
                tracklist=discogs_data.tracklist,
            )

            if success:
                logger.info(f"✓ Enriched: {artist} - {album}")
                return True
            else:
                logger.error(f"✗ Failed to update database for: {artist} - {album}")
                return False
        else:
            logger.warning(f"✗ Could not enrich: {artist} - {album}")
            return False

    def enrich_all_pending(self):
        """
        Enrich all vinyls that are missing Discogs data.
        """
        logger.info("Starting enrichment process...")

        # Get vinyls needing enrichment
        pending_df = self.db.get_vinyls_needing_enrichment()

        if pending_df.empty:
            logger.info("No vinyls need enrichment")
            return

        logger.info(f"Found {len(pending_df)} vinyls to enrich")

        # Iterate through each vinyl
        for _, row in pending_df.iterrows():
            vinyl_id = row["id"]
            artist = row["artist"]
            album = row["album_title"]

            self.enrich_vinyl(vinyl_id, artist, album)

        logger.info("Enrichment complete")


if __name__ == "__main__":
    # Initialize with database
    db = VinylDatabase()
    enricher = DiscogEnricher(db)
    result = enricher.search_discogs(artist="foo fighters", album="color and the shape")
    result.model_dump()

    # Option 1: Enrich all pending vinyls
    # enricher.enrich_all_pending()

    # Option 2: Enrich specific vinyl manually (need to know the ID)
    # enricher.enrich_vinyl(vinyl_id=1, artist="Nirvana", album="Nevermind")

    # View results
    # df = db.get_all_vinyls()
    # print(df[["artist", "album_title", "discogs_title", "image_url"]])
