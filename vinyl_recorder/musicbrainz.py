"""
MusicBrainz + Cover Art Archive client for fetching album cover art.

Uses the public MusicBrainz REST API (no key required, just a User-Agent)
to look up a release, then fetches the cover image URL from the Cover Art
Archive (checking both release pressings and the overall release-group).

Rate limit: MusicBrainz asks for no more than 1 request per second.
"""

import time
import requests
from typing import Optional, List, Tuple

from vinyl_recorder.config import get_logger

logger = get_logger()

USER_AGENT = "vinyl_recorder/1.0 ( https://github.com/peted900/vinyl-recorder )"
MB_SEARCH_URL = "https://musicbrainz.org/ws/2/release/"
CAA_FRONT_URL = "https://coverartarchive.org/release/{mbid}/front-250"
CAA_RG_FRONT_URL = "https://coverartarchive.org/release-group/{mbid}/front-250"


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
        """Search MusicBrainz for a release and return the first MBID (or None)."""
        releases, _ = self._search_candidates(artist, album)
        return releases[0] if releases else None

    def _search_candidates(self, artist: str, album: str) -> Tuple[List[str], List[str]]:
        """
        Search MusicBrainz and return:
        - List of release MBIDs (prioritizing releases flagged with front cover art)
        - List of release-group MBIDs
        """
        self._throttle()
        query = f'release:"{album}" AND artist:"{artist}"'
        try:
            response = requests.get(
                MB_SEARCH_URL,
                params={"query": query, "fmt": "json", "limit": 10},
                headers={"User-Agent": USER_AGENT},
                timeout=10,
            )
            response.raise_for_status()
        except requests.RequestException as e:
            logger.error(f"MusicBrainz search failed for {artist} - {album}: {e}")
            return [], []

        data = response.json()
        releases_data = data.get("releases", [])
        if not releases_data:
            logger.warning(f"No MusicBrainz release for: {artist} - {album}")
            return [], []

        releases_with_art = []
        other_releases = []
        rg_ids = []

        for rel in releases_data:
            rel_id = rel.get("id")
            if not rel_id:
                continue

            has_front = rel.get("cover-art-archive", {}).get("front") is True
            if has_front:
                releases_with_art.append(rel_id)
            else:
                other_releases.append(rel_id)

            rg_id = rel.get("release-group", {}).get("id")
            if rg_id and rg_id not in rg_ids:
                rg_ids.append(rg_id)

        ordered_releases = releases_with_art + other_releases
        return ordered_releases, rg_ids

    def _check_caa_url(self, url: str) -> Optional[str]:
        """Verify image exists on Cover Art Archive via HEAD request."""
        try:
            head = requests.head(
                url,
                headers={"User-Agent": USER_AGENT},
                allow_redirects=True,
                timeout=10,
            )
            if head.status_code == 200:
                return head.url
        except requests.RequestException:
            pass
        return None

    def fetch_cover_url(self, artist: str, album: str) -> Optional[str]:
        """
        Search MusicBrainz for an album and return a cover art URL from
        the Cover Art Archive. Checks both release and release-group endpoints.
        """
        releases, rg_ids = self._search_candidates(artist, album)
        if not releases and not rg_ids:
            return None

        # 1. Try releases (prioritized by those with artwork)
        for mbid in releases[:5]:
            url = CAA_FRONT_URL.format(mbid=mbid)
            found = self._check_caa_url(url)
            if found:
                return found

        # 2. Try release-groups (holds master cover art for albums)
        for rg_id in rg_ids[:3]:
            url = CAA_RG_FRONT_URL.format(mbid=rg_id)
            found = self._check_caa_url(url)
            if found:
                return found

        logger.warning(f"No cover art found on CAA for {artist} - {album}")
        return None
