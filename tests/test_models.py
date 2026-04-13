"""Tests for Pydantic data models."""

from vinyl_recorder.vinyl_cover_identifier import VinylData
from vinyl_recorder.collection_tracker import TrackerData
from vinyl_recorder.album_enricher import EnrichmentData, TracklistData


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


class TestEnrichmentData:
    def test_enrichment_data(self):
        data = EnrichmentData(
            image_url="https://example.com/cover.jpg",
            tracklist=["1 Smells Like Teen Spirit", "2 In Bloom"],
        )
        assert data.image_url == "https://example.com/cover.jpg"
        assert len(data.tracklist) == 2

    def test_empty_enrichment(self):
        data = EnrichmentData()
        assert data.image_url == ""
        assert data.tracklist == []


class TestTracklistData:
    def test_tracklist_data(self):
        data = TracklistData(tracks=["1 Track A", "2 Track B"])
        assert data.tracks == ["1 Track A", "2 Track B"]
