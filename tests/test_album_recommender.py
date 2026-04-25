"""Tests for AlbumRecommender."""

import pytest
from unittest.mock import MagicMock, patch

from vinyl_recorder.album_recommender import (
    AlbumRecommender,
    RecommendedAlbum,
    RecommendedAlbums,
)


class TestBuildAlbumContext:
    @patch("vinyl_recorder.album_recommender.get_llm_client")
    def test_context_contains_albums(self, mock_llm):
        repo = MagicMock()
        repo.get_album_titles.return_value = [
            "Nirvana - Nevermind",
            "Radiohead - OK Computer",
        ]

        recommender = AlbumRecommender(repo=repo)
        context = recommender.build_album_context(n_suggestions=3, taste_distance=5)

        assert "Nirvana - Nevermind" in context
        assert "Radiohead - OK Computer" in context
        assert "3" in context  # n_suggestions
        assert "5" in context  # taste_distance

    @patch("vinyl_recorder.album_recommender.get_llm_client")
    def test_context_distance_setting(self, mock_llm):
        repo = MagicMock()
        repo.get_album_titles.return_value = ["Test Album"]

        recommender = AlbumRecommender(repo=repo)
        context = recommender.build_album_context(n_suggestions=2, taste_distance=8)

        assert "Current distance setting: 8" in context


class TestRecommendAlbumsValidation:
    @patch("vinyl_recorder.album_recommender.get_llm_client")
    def test_invalid_taste_distance(self, mock_llm):
        repo = MagicMock()
        recommender = AlbumRecommender(repo=repo)

        with pytest.raises(ValueError, match="taste_distance"):
            recommender.recommend_albums(taste_distance=0)

        with pytest.raises(ValueError, match="taste_distance"):
            recommender.recommend_albums(taste_distance=11)

    @patch("vinyl_recorder.album_recommender.get_llm_client")
    def test_invalid_n_suggestions(self, mock_llm):
        repo = MagicMock()
        recommender = AlbumRecommender(repo=repo)

        with pytest.raises(ValueError, match="n_suggestions"):
            recommender.recommend_albums(n_suggestions=0)

        with pytest.raises(ValueError, match="n_suggestions"):
            recommender.recommend_albums(n_suggestions=11)


class TestParseAlbums:
    @patch("vinyl_recorder.album_recommender.get_llm_client")
    def test_parse_albums(self, mock_llm):
        repo = MagicMock()
        recommender = AlbumRecommender(repo=repo)

        results = RecommendedAlbums(albums=[
            RecommendedAlbum(artist="Miles Davis", album="Kind of Blue"),
            RecommendedAlbum(artist="John Coltrane", album="A Love Supreme"),
        ])

        output = recommender.parse_albums(results)

        assert "Miles Davis - Kind of Blue" in output
        assert "John Coltrane - A Love Supreme" in output
