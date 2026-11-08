"""Tests for AlbumVerifier."""

from unittest.mock import MagicMock, patch

from vinyl_recorder.album_verifier import AlbumVerifier, VerifiedAlbum


def _make_verifier(llm_mock):
    with patch("vinyl_recorder.album_verifier.get_llm_client") as mock_get_llm:
        mock_get_llm.return_value = llm_mock
        return AlbumVerifier()


class TestVerifyAlbum:
    def test_returns_verified_album_when_found(self):
        llm = MagicMock()
        llm.parse_completion.return_value = VerifiedAlbum(
            found=True,
            artist="Radiohead",
            album_title="OK Computer",
            album_year="1997",
        )
        verifier = _make_verifier(llm)

        result = verifier.verify_album("ok computer radiohead")

        assert result.found is True
        assert result.artist == "Radiohead"
        assert result.album_title == "OK Computer"
        assert result.album_year == "1997"

    def test_returns_clarification_when_ambiguous(self):
        llm = MagicMock()
        llm.parse_completion.return_value = VerifiedAlbum(
            found=False,
            clarification="Which Radiohead album?",
        )
        verifier = _make_verifier(llm)

        result = verifier.verify_album("some radiohead thing")

        assert result.found is False
        assert result.clarification == "Which Radiohead album?"

    def test_handles_llm_exception_gracefully(self):
        llm = MagicMock()
        llm.parse_completion.side_effect = RuntimeError("LLM down")
        verifier = _make_verifier(llm)

        result = verifier.verify_album("test")
        assert result.found is False
        assert result.clarification is not None
