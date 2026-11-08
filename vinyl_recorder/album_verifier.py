"""
LLM-based album verification for the /tobuy wishlist flow.

Takes freeform user text (e.g. "new Radiohead album" or "kind of blue miles")
and asks Claude to identify the album they mean.
"""

from typing import Optional

from pydantic import BaseModel

from vinyl_recorder.config import get_logger
from vinyl_recorder.llm_client import get_llm_client

logger = get_logger()


class VerifiedAlbum(BaseModel):
    """Result of LLM album verification."""

    found: bool
    artist: Optional[str] = None
    album_title: Optional[str] = None
    album_year: Optional[str] = None
    clarification: Optional[str] = None


class AlbumVerifier:
    def __init__(self, llm_choice: str = "anthropic", model_choice: str = None):
        self.llm = get_llm_client(llm=llm_choice, model=model_choice)

    def verify_album(self, user_input: str) -> VerifiedAlbum:
        """
        Parse a freeform album description from the user and return a
        structured VerifiedAlbum. Returns found=False with a clarification
        message when the input is ambiguous.
        """
        system_prompt = (
            "You are a music expert helping a user add an album to their "
            "wishlist. The user will describe an album in freeform text. "
            "Identify exactly which album they mean and return the canonical "
            "artist name, album title, and release year.\n\n"
            "Rules:\n"
            "- If you are confident about the album, set found=true and fill "
            "in artist, album_title, and album_year. Leave clarification null.\n"
            "- If the input is ambiguous (e.g. multiple possible matches) or "
            "you cannot identify the album, set found=false and put a short "
            "question in clarification explaining what you need. Leave the "
            "album fields null in that case.\n"
            "- Always use the canonical/official artist name and album title."
        )

        messages = [
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": f'The user wrote: "{user_input}"',
                    }
                ],
            },
        ]

        try:
            result = self.llm.parse_completion(
                messages=messages, response_format=VerifiedAlbum
            )
            return result
        except Exception as e:
            logger.error(f"Album verification failed for {user_input!r}: {e}")
            return VerifiedAlbum(
                found=False,
                clarification="Sorry, I couldn't process that. Try again?",
            )
