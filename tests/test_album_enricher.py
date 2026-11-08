"""Tests for AlbumEnricher."""

import json
from unittest.mock import MagicMock, patch

from vinyl_recorder.album_enricher import AlbumEnricher, EnrichmentData, TracklistData


def _make_enricher(llm_mock=None, cover_mock=None):
    with patch("vinyl_recorder.album_enricher.get_llm_client") as mock_get_llm:
        mock_get_llm.return_value = llm_mock or MagicMock()
        enricher = AlbumEnricher(
            repo=MagicMock(),
            cover_fetcher=cover_mock or MagicMock(),
        )
    return enricher


class TestFetchTracklist:
    def test_returns_tracks_from_llm(self):
        llm = MagicMock()
        llm.parse_completion.return_value = TracklistData(
            tracks=["1 Smells Like Teen Spirit", "2 In Bloom"]
        )
        enricher = _make_enricher(llm_mock=llm)

        tracks = enricher.fetch_tracklist("Nirvana", "Nevermind", "1991")

        assert tracks == ["1 Smells Like Teen Spirit", "2 In Bloom"]
        llm.parse_completion.assert_called_once()

    def test_returns_empty_list_on_llm_error(self):
        llm = MagicMock()
        llm.parse_completion.side_effect = RuntimeError("LLM down")
        enricher = _make_enricher(llm_mock=llm)

        tracks = enricher.fetch_tracklist("Nirvana", "Nevermind")
        assert tracks == []


class TestFetchEnrichment:
    def test_combines_cover_and_tracklist(self):
        llm = MagicMock()
        llm.parse_completion.return_value = TracklistData(tracks=["1 A", "2 B"])
        cover = MagicMock()
        cover.fetch_cover_url.return_value = "https://example.com/cover.jpg"

        enricher = _make_enricher(llm_mock=llm, cover_mock=cover)
        data = enricher.fetch_enrichment("Nirvana", "Nevermind", "1991")

        assert isinstance(data, EnrichmentData)
        assert data.image_url == "https://example.com/cover.jpg"
        assert data.tracklist == ["1 A", "2 B"]

    def test_handles_missing_cover(self):
        llm = MagicMock()
        llm.parse_completion.return_value = TracklistData(tracks=["1 A"])
        cover = MagicMock()
        cover.fetch_cover_url.return_value = None

        enricher = _make_enricher(llm_mock=llm, cover_mock=cover)
        data = enricher.fetch_enrichment("Artist", "Album")

        assert data.image_url == ""
        assert data.tracklist == ["1 A"]


class TestEnrichRow:
    def test_writes_both_fields(self):
        llm = MagicMock()
        llm.parse_completion.return_value = TracklistData(tracks=["1 A"])
        cover = MagicMock()
        cover.fetch_cover_url.return_value = "https://img"

        enricher = _make_enricher(llm_mock=llm, cover_mock=cover)
        result = enricher.enrich_row(42, "Artist", "Album", "2000")

        assert result is True
        enricher.repo.update_album.assert_called_once()
        call_id, updates = enricher.repo.update_album.call_args[0]
        assert call_id == 42
        assert updates["cover_image_url"] == "https://img"
        assert json.loads(updates["tracklist"]) == ["1 A"]

    def test_no_update_when_nothing_found(self):
        llm = MagicMock()
        llm.parse_completion.return_value = TracklistData(tracks=[])
        cover = MagicMock()
        cover.fetch_cover_url.return_value = None

        enricher = _make_enricher(llm_mock=llm, cover_mock=cover)
        result = enricher.enrich_row(42, "Artist", "Album")

        assert result is False
        enricher.repo.update_album.assert_not_called()
