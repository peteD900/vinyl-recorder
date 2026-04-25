"""
MusicBrainz + Cover Art Archive client for fetching album cover art.

Uses the public MusicBrainz REST API (no key required, just a User-Agent)
to look up a release, then fetches the cover image URL from the Cover Art
Archive.

Rate limit: MusicBrainz asks for no more than 1 request per second.
"""

import time
import requests
from typing import Optional

from vinyl_recorder.config import get_logger

logger = get_logger()

USER_AGENT = "vinyl_recorder/1.0 ( https://github.com/peted900/vinyl-recorder )"
MB_SEARCH_URL = "https://musicbrainz.org/ws/2/release/"
CAA_FRONT_URL = "https://coverartarchive.org/release/{mbid}/front-250"


class CoverArtFetcher:
    def __init__(self, rate_limit_seconds: float = 1.0):
        self.rate_limit_seconds = rate_limit_seconds
        self._last_request_time = 0.0

    def _throttle(self):
        """Sleep just enough to respect MusicBrainz's 1 req/sec limit."""
        elapsed = time.time() - self._last_request_time
        wait = self.rate_limit_seconds - elapsed
        if wait > 0:
            time.sleep(wait)
        self._last_request_time = time.time()

    def _search_release(self, artist: str, album: str) -> Optional[str]:
        """Search MusicBrainz for a release and return its MBID (or None)."""
        self._throttle()
        query = f'release:"{album}" AND artist:"{artist}"'
        try:
            response = requests.get(
                MB_SEARCH_URL,
                params={"query": query, "fmt": "json", "limit": 5},
                headers={"User-Agent": USER_AGENT},
                timeout=10,
            )
            response.raise_for_status()
        except requests.RequestException as e:
            logger.error(f"MusicBrainz search failed for {artist} - {album}: {e}")
            return None

        data = response.json()
        releases = data.get("releases", [])
        if not releases:
            logger.warning(f"No MusicBrainz release for: {artist} - {album}")
            return None

        return releases[0].get("id")

    def fetch_cover_url(self, artist: str, album: str) -> Optional[str]:
        """
        Search MusicBrainz for an album and return a cover art URL from
        the Cover Art Archive. Returns None if nothing is found.
        """
        mbid = self._search_release(artist, album)
        if not mbid:
            return None

        cover_url = CAA_FRONT_URL.format(mbid=mbid)
        # Verify the image exists via HEAD — CAA returns 404 when no art.
        try:
            head = requests.head(
                cover_url,
                headers={"User-Agent": USER_AGENT},
                allow_redirects=True,
                timeout=10,
            )
            if head.status_code != 200:
                logger.warning(
                    f"No cover art on CAA for {artist} - {album} (mbid={mbid})"
                )
                return None
            # After redirect the final URL is the real image URL
            return head.url
        except requests.RequestException as e:
            logger.error(f"Cover Art Archive lookup failed for {mbid}: {e}")
            return None
