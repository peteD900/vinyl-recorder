"""
Album enrichment: fetch cover art from MusicBrainz/Cover Art Archive and
tracklist from the LLM. Replaces the old Discogs-based enrichment.
"""

import json
from typing import Optional

from pydantic import BaseModel

from vinyl_recorder.config import get_logger
from vinyl_recorder.database import AlbumRepository
from vinyl_recorder.llm_client import get_llm_client
from vinyl_recorder.musicbrainz import CoverArtFetcher

logger = get_logger()


# ==== DATA MODELS ==== #
class TracklistData(BaseModel):
    """Structured tracklist returned by the LLM."""

    tracks: list[str]


class EnrichmentData(BaseModel):
    """Combined cover + tracklist enrichment result."""

    image_url: str = ""
    tracklist: list[str] = []


# ==== ENRICHER ==== #
class AlbumEnricher:
    def __init__(
        self,
        repo: AlbumRepository,
        cover_fetcher: Optional[CoverArtFetcher] = None,
        llm_choice: str = "anthropic",
        model_choice: str = None,
    ):
        self.repo = repo
        self.cover_fetcher = cover_fetcher or CoverArtFetcher()
        self.llm = get_llm_client(llm=llm_choice, model=model_choice)

    def fetch_tracklist(
        self, artist: str, album: str, album_year: str = None
    ) -> list[str]:
        """
        Ask the LLM for the tracklist of an album. Returns a list of track
        strings like "1 Song Title". Returns [] on any failure.
        """
        year_hint = f" ({album_year})" if album_year else ""
        system_prompt = (
            "You are an expert discographer. When given an album, return its "
            "full tracklist in original release order. Format each track as "
            '"<track_number> <track_title>" (e.g. "1 Come As You Are"). '
            "Only include tracks you are confident about; if you are unsure, "
            "return an empty list."
        )
        user_prompt = (
            f"Album: {album}{year_hint}\n"
            f"Artist: {artist}\n\n"
            "List every track in order."
        )

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": [{"type": "text", "text": user_prompt}]},
        ]

        try:
            result = self.llm.parse_completion(
                messages=messages, response_format=TracklistData
            )
            return result.tracks
        except Exception as e:
            logger.error(f"LLM tracklist fetch failed for {artist} - {album}: {e}")
            return []

    def fetch_enrichment(
        self, artist: str, album: str, album_year: str = None
    ) -> EnrichmentData:
        """Fetch both cover art and tracklist for an album."""
        cover_url = self.cover_fetcher.fetch_cover_url(artist, album) or ""
        tracks = self.fetch_tracklist(artist, album, album_year)
        return EnrichmentData(image_url=cover_url, tracklist=tracks)

    def enrich_row(
        self, album_id: int, artist: str, album: str, album_year: str = None
    ) -> bool:
        """Enrich one album in the DB. Returns True if anything was written."""
        logger.info(f"Enriching album {album_id}: {artist} - {album}")

        data = self.fetch_enrichment(artist, album, album_year)

        updates = {}
        if data.image_url:
            updates["cover_image_url"] = data.image_url
        if data.tracklist:
            updates["tracklist"] = json.dumps(data.tracklist)

        if not updates:
            logger.warning(f"Could not enrich: {artist} - {album}")
            return False

        self.repo.update_album(album_id, updates)
        logger.info(f"Enriched: {artist} - {album}")
        return True

    def enrich_all_pending(self):
        """Enrich every album in the DB that is missing cover art or tracklist."""
        logger.info("Starting enrichment process...")

        for album in self.repo.get_albums_needing_enrichment():
            self.enrich_row(
                album_id=album["id"],
                artist=album["artist"],
                album=album["album_title"],
                album_year=album.get("album_year"),
            )

        logger.info("Enrichment complete")
