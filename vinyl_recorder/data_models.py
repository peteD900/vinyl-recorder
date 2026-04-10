from pydantic import BaseModel
from typing import Optional


# ---- VINYL IDENTIFICATION ---- #
class VinylIdentity(BaseModel):
    """
    Output format for identification of album cover from llm.
    """

    success: bool
    artist: str | None = None
    album_title: str | None = None
    album_year: str | None = None


# ---- TRACKER ---- #
class TrackerData(VinylIdentity):
    """
    Format for one row of tracking info
    """

    image_name: str
    source: str
    process_date: str


# ---- DISCOGS ENRICHMENT ---- #
class DiscogsData(BaseModel):
    discogs_title: str
    tracklist: list
    image_url: str


# ---- DB TABLE ---- #
class Vinyl(BaseModel):
    """Represents a vinyl record in the collection"""

    id: int | None = None
    image_name: str
    process_date: str
    source: str
    success: str
    artist: str
    album_title: str
    album_year: int | None = None
    discogs_attempted: bool = False
    discogs_title: str | None = None
    image_url: str | None = None
    tracklist: list[str] | None = None


# ---- VINYL RECOMMENDATION ---- #
class RecommendedAlbum(BaseModel):
    artist: str
    album: str


class RecommendedAlbums(BaseModel):
    albums: list[RecommendedAlbum]
