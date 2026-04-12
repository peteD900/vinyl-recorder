"""Tests for Pydantic data models."""

from vinyl_recorder.vinyl_cover_identifier import VinylData
from vinyl_recorder.collection_tracker import TrackerData
from vinyl_recorder.discogs import DiscogsData


class TestVinylData:
    def test_successful_identification(self):
        data = VinylData(
            success=True,
            artist="Nirvana",
            album_title="Nevermind",
            album_year="1991",
            confidence="high",
        )
        assert data.success is True
        assert data.artist == "Nirvana"
        assert data.album_title == "Nevermind"
        assert data.album_year == "1991"
        assert data.confidence == "high"

    def test_failed_identification(self):
        data = VinylData(success=False)
        assert data.success is False
        assert data.artist is None
        assert data.album_title is None
        assert data.album_year is None
        assert data.confidence is None

    def test_partial_identification(self):
        data = VinylData(
            success=True,
            artist="Unknown",
            album_title=None,
            confidence="low",
        )
        assert data.success is True
        assert data.artist == "Unknown"
        assert data.album_title is None
        assert data.album_year is None


class TestTrackerData:
    def test_tracker_extends_vinyl_data(self):
        data = TrackerData(
            success=True,
            artist="Radiohead",
            album_title="OK Computer",
            album_year="1997",
            confidence="high",
            image_name="test_001.jpg",
            source="local",
            process_date="2025-01-01T12:00:00",
        )
        assert data.image_name == "test_001.jpg"
        assert data.source == "local"
        assert data.process_date == "2025-01-01T12:00:00"
        # Inherited fields
        assert data.artist == "Radiohead"
        assert data.success is True


class TestDiscogsData:
    def test_discogs_data(self):
        data = DiscogsData(
            discogs_title="Nirvana - Nevermind",
            tracklist=["1 Smells Like Teen Spirit", "2 In Bloom"],
            image_url="https://example.com/cover.jpg",
        )
        assert data.discogs_title == "Nirvana - Nevermind"
        assert len(data.tracklist) == 2
        assert data.image_url == "https://example.com/cover.jpg"

    def test_empty_tracklist(self):
        data = DiscogsData(
            discogs_title="Test Album",
            tracklist=[],
            image_url="",
        )
        assert data.tracklist == []
        assert data.image_url == ""
