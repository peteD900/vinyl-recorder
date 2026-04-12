"""Tests for CollectionTracker."""

import pandas as pd
from pathlib import Path
from unittest.mock import MagicMock

from vinyl_recorder.collection_tracker import CollectionTracker
from vinyl_recorder.vinyl_cover_identifier import VinylData


class TestGetPendingImages:
    def _make_tracker(self, sheeter_mock, images_path="/tmp/test_images"):
        return CollectionTracker(
            sheeter=sheeter_mock,
            images_path=images_path,
            source="local",
        )

    def test_all_pending_when_sheet_empty(self, tmp_path):
        # Create test images
        (tmp_path / "img1.jpg").touch()
        (tmp_path / "img2.jpg").touch()

        sheeter = MagicMock()
        sheeter.load_sheet_as_df.return_value = pd.DataFrame()

        tracker = self._make_tracker(sheeter, str(tmp_path))
        pending = tracker.get_pending_images()

        assert len(pending) == 2

    def test_no_pending_when_all_processed(self, tmp_path):
        (tmp_path / "img1.jpg").touch()
        (tmp_path / "img2.jpg").touch()

        sheeter = MagicMock()
        sheeter.load_sheet_as_df.return_value = pd.DataFrame(
            {"image_name": ["img1.jpg", "img2.jpg"]}
        )

        tracker = self._make_tracker(sheeter, str(tmp_path))
        pending = tracker.get_pending_images()

        assert len(pending) == 0

    def test_partial_pending(self, tmp_path):
        (tmp_path / "img1.jpg").touch()
        (tmp_path / "img2.jpg").touch()
        (tmp_path / "img3.jpg").touch()

        sheeter = MagicMock()
        sheeter.load_sheet_as_df.return_value = pd.DataFrame(
            {"image_name": ["img1.jpg"]}
        )

        tracker = self._make_tracker(sheeter, str(tmp_path))
        pending = tracker.get_pending_images()

        assert len(pending) == 2
        pending_names = [p.name for p in pending]
        assert "img1.jpg" not in pending_names
        assert "img2.jpg" in pending_names
        assert "img3.jpg" in pending_names


class TestBuildRow:
    def test_build_row_structure(self):
        sheeter = MagicMock()
        tracker = CollectionTracker(sheeter=sheeter, source="local")

        result = VinylData(
            success=True,
            artist="Nirvana",
            album_title="Nevermind",
            album_year="1991",
            confidence="high",
        )

        row = tracker._build_row("test.jpg", "local", result)

        assert len(row) == 11
        assert row[0] == "test.jpg"
        # row[1] is process_date (dynamic)
        assert row[2] == "local"
        assert row[3] is True
        assert row[4] == "Nirvana"
        assert row[5] == "Nevermind"
        assert row[6] == "1991"
        assert row[7] == "high"
        assert row[8] == ""  # discogs_title
        assert row[9] == ""  # image_url
        assert row[10] == ""  # tracklist


class TestAddResults:
    def test_add_result_local_skips_duplicate(self):
        sheeter = MagicMock()
        sheeter.is_duplicate.return_value = True

        tracker = CollectionTracker(sheeter=sheeter, source="local")
        result = VinylData(success=True, artist="Nirvana", album_title="Nevermind")

        image_path = MagicMock()
        image_path.name = "test.jpg"
        tracker.add_result_local(image_path, result)

        sheeter.append_row.assert_not_called()

    def test_add_result_local_appends_new(self):
        sheeter = MagicMock()
        sheeter.is_duplicate.return_value = False

        tracker = CollectionTracker(sheeter=sheeter, source="local")
        result = VinylData(success=True, artist="Nirvana", album_title="Nevermind")

        image_path = MagicMock()
        image_path.name = "test.jpg"
        tracker.add_result_local(image_path, result)

        sheeter.append_row.assert_called_once()

    def test_add_result_telegram_appends(self):
        sheeter = MagicMock()

        tracker = CollectionTracker(sheeter=sheeter, source="telegram")
        result = VinylData(success=True, artist="Radiohead", album_title="OK Computer")

        tracker.add_result_telegram("telegram_001.jpg", result)

        sheeter.append_row.assert_called_once()
        row = sheeter.append_row.call_args[1]["row_data"]
        assert row[0] == "telegram_001.jpg"
        assert row[2] == "telegram"
