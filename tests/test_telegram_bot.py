"""Tests for VinylBot helper methods."""

from unittest.mock import MagicMock
from vinyl_recorder.vinyl_cover_identifier import VinylData
from vinyl_recorder.album_enricher import EnrichmentData
from vinyl_recorder.telegram_bot import VinylBot


def _make_bot():
    """Create a VinylBot with mocked dependencies."""
    return VinylBot(
        repo=MagicMock(),
        identifier=MagicMock(),
        enricher=MagicMock(),
        tracker=MagicMock(),
        recommender=MagicMock(),
    )


class TestFormatResultsMessage:
    def test_with_enrichment_data(self):
        bot = _make_bot()
        vinyl = VinylData(
            success=True,
            artist="Nirvana",
            album_title="Nevermind",
            album_year="1991",
            confidence="high",
        )
        enrichment = EnrichmentData(
            image_url="https://example.com/cover.jpg",
            tracklist=["1 Smells Like Teen Spirit", "2 In Bloom"],
        )

        msg = bot.format_results_message(vinyl, enrichment)

        assert "Nirvana" in msg
        assert "Nevermind" in msg
        assert "1991" in msg
        assert "high" in msg
        assert "Smells Like Teen Spirit" in msg
        assert "In Bloom" in msg
        assert "Add this to your collection?" in msg

    def test_without_enrichment_data(self):
        bot = _make_bot()
        vinyl = VinylData(
            success=True,
            artist="Unknown Artist",
            album_title="Rare Album",
            album_year=None,
            confidence="low",
        )

        msg = bot.format_results_message(vinyl, None)

        assert "Unknown Artist" in msg
        assert "Rare Album" in msg
        assert "Unknown" in msg  # year fallback
        assert "Could not find enrichment data" in msg
        assert "Add this to your collection?" in msg
