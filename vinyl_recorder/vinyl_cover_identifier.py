import base64
from vinyl_recorder.llm_client import get_llm_client
from vinyl_recorder.config import get_logger
from pydantic import BaseModel
from typing import Optional

logger = get_logger()


# ==== DATA MODELS ==== #
class VinylData(BaseModel):
    """
    Output format for identification of album cover from llm.
    """

    success: bool
    artist: Optional[str] = None
    album_title: Optional[str] = None
    album_year: Optional[str] = None
    confidence: Optional[str] = None


# ==== IDENTIFIER ==== #
class VinylIdentifier:
    def __init__(self, llm_choice: str = "openai"):
        logger.info("Starting Vinly Identifier")

        self.llm = get_llm_client(llm=llm_choice)

    def load_image_base64(self, image_path: str) -> str:
        "Convert image to base64 for llm."

        # Read and encode the image
        with open(image_path, "rb") as image_file:
            image_data = base64.b64encode(image_file.read()).decode("utf-8")

        return image_data

    def identify(self, image_base64: str) -> VinylData:
        """
        Pass base64 image to llm for identification.

        :param image_base64: Image in base64
        :type image_base64: str
        :return: results of llm call
        :rtype: VinylData
        """

        system_prompt = """
        You are an expert at identifying vinyl album covers. 

        When shown an image, identify the artist, album title, and release year.

        If you can clearly identify the album, set success to true and provide the information.
        If the image is unclear, not an album cover, or you're uncertain, set success to false and leave the other fields as null.

        Set confidence to "high", "medium", or "low" based on how certain you are of the identification.

        Be accurate - only provide information you're confident about.
        """

        messages = [
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": "What album is this? Identify the artist, title, and year.",
                    },
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/jpeg;base64,{image_base64}"},
                    },
                ],
            },
        ]

        result = self.llm.parse_completion(messages=messages, response_format=VinylData)

        return result

    def identify_image(self, image_path: str) -> VinylData:
        """
        Load photo as base64 and identify album cover with llm call.
        """
        logger.info(f"Identifing image: {image_path.name}")

        image_base64 = self.load_image_base64(image_path)

        results = self.identify(image_base64)

        return results


if __name__ == "__main__":
    image_path = "../data/google_photos/PXL_20251228_171823574.jpg"
    identifier = VinylIdentifier()
    results = identifier.identify_image(image_path=image_path)
    print(results.model_dump_json(indent=2))
