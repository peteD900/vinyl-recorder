import discogs_client
import json
from pydantic import BaseModel
from typing import Optional
from vinyl_recorder.config import Config, get_logger
from vinyl_recorder.database import AlbumRepository

logger = get_logger()
TOKEN = Config.DISCOGS_API_KEY


# ==== DATA MODELS ==== #
class DiscogsData(BaseModel):
    discogs_title: str
    tracklist: list
    image_url: str


class DiscogEnricher:
    def __init__(self, repo: AlbumRepository):
        self.d = discogs_client.Client("vinyl_recorder/1.0", user_token=TOKEN)
        self.repo = repo

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

    def enrich_row(self, album_id: int, artist: str, album: str):
        """
        Search Discogs for one album and update the database.
        """
        logger.info(f"Enriching album {album_id}: {artist} - {album}")

        discogs_data = self.search_discogs(artist, album)

        if discogs_data:
            tracklist_json = json.dumps(discogs_data.tracklist)

            self.repo.update_album(album_id, {
                "cover_image_url": discogs_data.image_url,
                "tracklist": tracklist_json,
            })

            logger.info(f"Enriched: {artist} - {album}")
            return True
        else:
            logger.warning(f"Could not enrich: {artist} - {album}")
            return False

    def enrich_all_pending(self):
        """
        Enrich all albums that are missing cover art or tracklist data.
        """
        logger.info("Starting enrichment process...")

        for album in self.repo.get_albums_needing_enrichment():
            artist = album.get("artist")
            album_title = album.get("album_title")
            album_id = album.get("id")

            self.enrich_row(album_id, artist, album_title)

        logger.info("Enrichment complete")
