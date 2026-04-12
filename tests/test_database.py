"""Tests for AlbumRepository using an in-memory SQLite database."""

import pytest
from vinyl_recorder.database import AlbumRepository


@pytest.fixture
def repo():
    """Fresh in-memory SQLite repository per test."""
    r = AlbumRepository(db_path=":memory:")
    yield r
    r.close()


def _sample_album(image_name="test.jpg", artist="Nirvana", album_title="Nevermind"):
    return {
        "image_name": image_name,
        "process_date": "2024-01-01T00:00:00",
        "source": "local",
        "success": 1,
        "artist": artist,
        "album_title": album_title,
        "album_year": "1991",
        "confidence": "high",
    }


class TestAlbumsCRUD:
    def test_add_and_find_by_image_name(self, repo):
        album_id = repo.add_album(_sample_album())
        assert album_id > 0

        found = repo.find_by_image_name("test.jpg")
        assert found is not None
        assert found["artist"] == "Nirvana"
        assert found["album_title"] == "Nevermind"

    def test_find_by_image_name_missing(self, repo):
        assert repo.find_by_image_name("nope.jpg") is None

    def test_is_duplicate(self, repo):
        assert not repo.is_duplicate("Nirvana", "Nevermind")
        repo.add_album(_sample_album())
        assert repo.is_duplicate("Nirvana", "Nevermind")
        assert not repo.is_duplicate("Nirvana", "In Utero")

    def test_get_all_albums(self, repo):
        repo.add_album(_sample_album("a.jpg", "Nirvana", "Nevermind"))
        repo.add_album(_sample_album("b.jpg", "Radiohead", "OK Computer"))

        albums = repo.get_all_albums()
        assert len(albums) == 2
        artists = {a["artist"] for a in albums}
        assert artists == {"Nirvana", "Radiohead"}

    def test_update_album(self, repo):
        album_id = repo.add_album(_sample_album())
        repo.update_album(album_id, {
            "cover_image_url": "https://example.com/cover.jpg",
            "tracklist": '["1 Track A"]',
        })
        row = repo.find_by_image_name("test.jpg")
        assert row["cover_image_url"] == "https://example.com/cover.jpg"
        assert row["tracklist"] == '["1 Track A"]'

    def test_get_albums_needing_enrichment(self, repo):
        repo.add_album(_sample_album("a.jpg", "Artist A", "Album A"))
        b_id = repo.add_album(_sample_album("b.jpg", "Artist B", "Album B"))
        repo.update_album(b_id, {
            "cover_image_url": "https://x/x.jpg",
            "tracklist": '["1 x"]',
        })

        needing = repo.get_albums_needing_enrichment()
        assert len(needing) == 1
        assert needing[0]["artist"] == "Artist A"

    def test_get_album_titles(self, repo):
        repo.add_album(_sample_album("a.jpg", "Nirvana", "Nevermind"))
        repo.add_album(_sample_album("b.jpg", "Radiohead", "OK Computer"))

        titles = repo.get_album_titles()
        assert "Nirvana - Nevermind" in titles
        assert "Radiohead - OK Computer" in titles


class TestToBuyList:
    def test_add_and_get_to_buy(self, repo):
        repo.add_to_buy("Radiohead", "In Rainbows", album_year="2007", verified=True)
        items = repo.get_to_buy_list()
        assert len(items) == 1
        assert items[0]["artist"] == "Radiohead"
        assert items[0]["album_title"] == "In Rainbows"
        assert items[0]["verified"] == 1

    def test_is_on_buy_list(self, repo):
        assert not repo.is_on_buy_list("Radiohead", "In Rainbows")
        repo.add_to_buy("Radiohead", "In Rainbows")
        assert repo.is_on_buy_list("Radiohead", "In Rainbows")

    def test_remove_from_to_buy(self, repo):
        item_id = repo.add_to_buy("Radiohead", "In Rainbows")
        repo.remove_from_to_buy(item_id)
        assert repo.get_to_buy_list() == []

    def test_already_owned(self, repo):
        assert not repo.already_owned("Nirvana", "Nevermind")
        repo.add_album(_sample_album())
        assert repo.already_owned("Nirvana", "Nevermind")
