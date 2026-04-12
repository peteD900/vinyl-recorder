"""Tests for web_app helper functions."""

from vinyl_recorder.web_app import parse_tracklist


class TestParseTracklist:
    def test_valid_json_tracklist(self):
        album = {"tracklist": '["1 Song A", "2 Song B"]'}
        result = parse_tracklist(album)
        assert result == ["1 Song A", "2 Song B"]

    def test_empty_string(self):
        album = {"tracklist": ""}
        result = parse_tracklist(album)
        assert result == []

    def test_missing_key(self):
        album = {}
        result = parse_tracklist(album)
        assert result == []

    def test_none_value(self):
        album = {"tracklist": None}
        result = parse_tracklist(album)
        assert result == []

    def test_invalid_json(self):
        album = {"tracklist": "not valid json"}
        result = parse_tracklist(album)
        assert result == []

    def test_zero_value(self):
        album = {"tracklist": 0}
        result = parse_tracklist(album)
        assert result == []
