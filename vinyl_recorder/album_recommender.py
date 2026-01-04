from vinyl_recorder.llm_client import get_llm_client
from vinyl_recorder.config import get_logger
from vinyl_recorder.ghseets import GoogleSheeter

from pydantic import BaseModel
from typing import List

logger = get_logger()


# ==== DATA MODELS ==== #
class RecommendedAlbum(BaseModel):
    artist: str
    album: str


class RecommendedAlbums(BaseModel):
    albums: list[RecommendedAlbum]


# ==== ALBUM RECOMMENDER ==== #
class AlbumRecommender:
    def __init__(
        self, sheeter, llm_choice: str = "openai", model_choice: str = "gpt-4o"
    ):
        logger.info("Starting Album Recommender")

        self.llm = get_llm_client(llm=llm_choice, model=model_choice)
        self.sheeter = sheeter

    def build_album_context(self, n_suggestions: int, taste_distance: int) -> str:
        """
        Pulls in gsheet with all albums and build a string with the full
        list of artist-album to pass into the LLM as context in order
        to recommend new albums.
        """

        # ==== Album input ==== #
        # From google sheets
        df_sheet = self.sheeter.df_sheet
        # df_sheet = df_sheet.head(10)

        album_list = df_sheet["discogs_title"].tolist()

        album_context = "The following is a list of albums I already own and like:\n"
        album_context += "They represent my overall taste in music.\n\n"

        for i, album in enumerate(album_list):
            album_context += f"{i + 1}. - {album}\n"

        album_context += f"""
        Based on this list, suggest {n_suggestions} albums I might like.
        DO NOT provide albums already listed.

        Use a taste_distance scale from 1 to 10:

        1 = extremely close to my existing albums (same artists, genres, era)
        5 = adjacent but exploratory (related genres or influences)
        10 = very exploratory (still plausible, but far from my usual taste)

        Current distance setting: {taste_distance}.
        Match the recommendations as closely as possible to the specified distance.
        """

        return album_context

    def recommend_albums(
        self, taste_distance: int = 5, n_suggestions: int = 5
    ) -> RecommendedAlbums:
        """
        LLM call to suggest n-albums with a param taste distance (0-10).

        :param taste_distance: int (1-10). A param to control how similar suggestions should
            be to the input album selection. A value of 1 is very close and 10 almost random.

        :param n_suggestions: int. Default 5. Number of albums to return.
        """

        if taste_distance not in range(1, 11):
            raise ValueError("taste_distance must be an integer between 1 and 10")

        if not 1 <= n_suggestions <= 10:
            raise ValueError("n_suggestions must be between 1 and 10")

        system_prompt = """
        You are an expert DJ, record collector, and music curator with deep knowledge of albums, 
        artists, genres, eras, and musical influences. Your job is to recommend albums that a 
        listener should consider buying based on their existing music taste, which will be 
        provided as a list of albums they already own and like.

        You must:

         - Analyse the user’s existing albums to infer their musical taste
         - Suggest exactly N albums that the user does not already own
         - Choose albums that are appropriate for the specified taste distance value

        The taste distance scale works as follows:

         - 1: Extremely close matches (same artists, very similar genres, era, or direct stylistic neighbours)
         - 5: Adjacent and exploratory (related genres, influences, or natural stylistic extensions)
         - 10: Very exploratory (clearly different, but still plausibly enjoyable given the user’s taste)

        You must prioritise matching the recommendations to the given distance value.
        Lower distances favour similarity and familiarity; higher distances favour 
        exploration while remaining musically credible.

        For each suggested album:

         - Provide the artist name
         - Provide the album title

        Do not:

         - Recommend albums already listed by the user
         - Mention the distance scale explicitly in the output
         - Add extra commentary outside the requested structure

        Your output must strictly follow the structured format expected by the application.
        """

        album_context = self.build_album_context(n_suggestions, taste_distance)

        messages = [
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": album_context,
                    }
                ],
            },
        ]

        result = self.llm.parse_completion(
            messages=messages, response_format=RecommendedAlbums
        )

        return result

    def parse_albums(self, results: RecommendedAlbums) -> str:
        albums = results.albums

        album_str = ""

        for album in albums:
            album_str += f"{album.artist} - {album.album}\n"

        return album_str


if __name__ == "__main__":
    sheeter = GoogleSheeter()
    suggestor = AlbumRecommender(sheeter=sheeter)
    results = suggestor.recommend_albums(n_suggestions=2, taste_distance=3)
    print(suggestor.parse_albums(results))
