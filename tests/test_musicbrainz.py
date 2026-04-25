"""Tests for CoverArtFetcher."""

from unittest.mock import MagicMock, patch

from vinyl_recorder.musicbrainz import CoverArtFetcher


class TestSearchRelease:
    @patch("vinyl_recorder.musicbrainz.requests.get")
    def test_returns_mbid_when_found(self, mock_get):
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "releases": [{"id": "abc-123"}, {"id": "def-456"}]
        }
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        fetcher = CoverArtFetcher(rate_limit_seconds=0)
        mbid = fetcher._search_release("Nirvana", "Nevermind")

        assert mbid == "abc-123"

    @patch("vinyl_recorder.musicbrainz.requests.get")
    def test_returns_none_when_no_releases(self, mock_get):
        mock_response = MagicMock()
        mock_response.json.return_value = {"releases": []}
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        fetcher = CoverArtFetcher(rate_limit_seconds=0)
        assert fetcher._search_release("Unknown", "Unknown") is None

    @patch("vinyl_recorder.musicbrainz.requests.get")
    def test_returns_none_on_request_error(self, mock_get):
        import requests as req_mod
        mock_get.side_effect = req_mod.RequestException("boom")

        fetcher = CoverArtFetcher(rate_limit_seconds=0)
        assert fetcher._search_release("Nirvana", "Nevermind") is None


class TestFetchCoverUrl:
    @patch("vinyl_recorder.musicbrainz.requests.head")
    @patch("vinyl_recorder.musicbrainz.requests.get")
    def test_returns_cover_url_on_success(self, mock_get, mock_head):
        mock_search = MagicMock()
        mock_search.json.return_value = {"releases": [{"id": "abc-123"}]}
        mock_search.raise_for_status.return_value = None
        mock_get.return_value = mock_search

        mock_head_resp = MagicMock()
        mock_head_resp.status_code = 200
        mock_head_resp.url = "https://coverartarchive.org/image.jpg"
        mock_head.return_value = mock_head_resp

        fetcher = CoverArtFetcher(rate_limit_seconds=0)
        url = fetcher.fetch_cover_url("Nirvana", "Nevermind")
        assert url == "https://coverartarchive.org/image.jpg"

    @patch("vinyl_recorder.musicbrainz.requests.head")
    @patch("vinyl_recorder.musicbrainz.requests.get")
    def test_returns_none_when_caa_404(self, mock_get, mock_head):
        mock_search = MagicMock()
        mock_search.json.return_value = {"releases": [{"id": "abc-123"}]}
        mock_search.raise_for_status.return_value = None
        mock_get.return_value = mock_search

        mock_head_resp = MagicMock()
        mock_head_resp.status_code = 404
        mock_head.return_value = mock_head_resp

        fetcher = CoverArtFetcher(rate_limit_seconds=0)
        assert fetcher.fetch_cover_url("Nirvana", "Nevermind") is None

    @patch("vinyl_recorder.musicbrainz.requests.get")
    def test_returns_none_when_no_mbid(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"releases": []}
        mock_resp.raise_for_status.return_value = None
        mock_get.return_value = mock_resp

        fetcher = CoverArtFetcher(rate_limit_seconds=0)
        assert fetcher.fetch_cover_url("Unknown", "Unknown") is None
