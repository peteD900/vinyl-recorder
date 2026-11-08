"""Tests for CollectionTracker."""

from unittest.mock import MagicMock

from vinyl_recorder.collection_tracker import CollectionTracker
from vinyl_recorder.vinyl_cover_identifier import VinylData


class TestGetPendingImages:
    def _make_tracker(self, repo_mock, images_path="/tmp/test_images"):
        return CollectionTracker(
            repo=repo_mock,
            images_path=images_path,
            source="local",
        )

    def test_all_pending_when_db_empty(self, tmp_path):
        (tmp_path / "img1.jpg").touch()
        (tmp_path / "img2.jpg").touch()

        repo = MagicMock()
        repo.find_by_image_name.return_value = None

        tracker = self._make_tracker(repo, str(tmp_path))
        pending = tracker.get_pending_images()

        assert len(pending) == 2

    def test_no_pending_when_all_processed(self, tmp_path):
        (tmp_path / "img1.jpg").touch()
        (tmp_path / "img2.jpg").touch()

        repo = MagicMock()
        repo.find_by_image_name.return_value = {"id": 1}

        tracker = self._make_tracker(repo, str(tmp_path))
        pending = tracker.get_pending_images()

        assert len(pending) == 0

    def test_partial_pending(self, tmp_path):
        (tmp_path / "img1.jpg").touch()
        (tmp_path / "img2.jpg").touch()
        (tmp_path / "img3.jpg").touch()

        repo = MagicMock()
        # Only img1.jpg exists in the DB
        repo.find_by_image_name.side_effect = lambda name: (
            {"id": 1} if name == "img1.jpg" else None
        )

        tracker = self._make_tracker(repo, str(tmp_path))
        pending = tracker.get_pending_images()

        pending_names = [p.name for p in pending]
        assert "img1.jpg" not in pending_names
        assert "img2.jpg" in pending_names
        assert "img3.jpg" in pending_names


class TestBuildAlbumData:
    def test_build_album_data_structure(self):
        repo = MagicMock()
        tracker = CollectionTracker(repo=repo, source="local")

        result = VinylData(
            success=True,
            artist="Nirvana",
            album_title="Nevermind",
            album_year="1991",
            confidence="high",
        )

        data = tracker._build_album_data("test.jpg", "local", result)

        assert data["image_name"] == "test.jpg"
        assert data["source"] == "local"
        assert data["success"] is True
        assert data["artist"] == "Nirvana"
        assert data["album_title"] == "Nevermind"
        assert data["album_year"] == "1991"
        assert data["confidence"] == "high"
        assert "process_date" in data


class TestAddResults:
    def test_add_result_local_skips_duplicate(self):
        repo = MagicMock()
        repo.is_duplicate.return_value = True

        tracker = CollectionTracker(repo=repo, source="local")
        result = VinylData(success=True, artist="Nirvana", album_title="Nevermind")

        image_path = MagicMock()
        image_path.name = "test.jpg"
        tracker.add_result_local(image_path, result)

        repo.add_album.assert_not_called()

    def test_add_result_local_adds_new(self):
        repo = MagicMock()
        repo.is_duplicate.return_value = False

        tracker = CollectionTracker(repo=repo, source="local")
        result = VinylData(success=True, artist="Nirvana", album_title="Nevermind")

        image_path = MagicMock()
        image_path.name = "test.jpg"
        tracker.add_result_local(image_path, result)

        repo.add_album.assert_called_once()

    def test_add_result_telegram_adds(self):
        repo = MagicMock()

        tracker = CollectionTracker(repo=repo, source="telegram")
        result = VinylData(success=True, artist="Radiohead", album_title="OK Computer")

        tracker.add_result_telegram("telegram_001.jpg", result)

        repo.add_album.assert_called_once()
        data = repo.add_album.call_args[0][0]
        assert data["image_name"] == "telegram_001.jpg"
        assert data["source"] == "telegram"
