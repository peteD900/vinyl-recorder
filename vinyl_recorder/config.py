import os
from dotenv import load_dotenv
from pyprojroot import here
import logging

# Load environment variables
load_dotenv()

# For relative paths
LOCAL_WD = here()


class Config:
    # ENV
    APP_ENV = os.getenv("APP_ENV")

    # LOCAL IMAGE DIRS
    IMAGES_DIR_PROD = LOCAL_WD / "data/all_images"
    IMAGES_DIR_TEST = LOCAL_WD / "data/test_images"

    # LLM OPENAI
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    OPENAI_MODEL = "gpt-4o"

    # TELEGRAM
    BOT_TOKEN = os.getenv("BOT_TOKEN")
    BOT_TOKEN_TEST = os.getenv("BOT_TOKEN_TEST")

    # DISCOGS
    DISCOGS_API_KEY = os.getenv("DISCOGS_API_KEY")

    # GOOGLE SHEETS
    GOOGLE_SERVICE_ACCOUNT = os.getenv("GOOGLE_SERVICE_ACCOUNT")
    VINYL_SHEET_TEST = os.getenv("VINYL_SHEET_TEST")
    VINYL_SHEET_PROD = os.getenv("VINYL_SHEET_PROD")

    # WEB APP
    WEB_APP_LINK = os.getenv("WEB_APP_LINK")

    @classmethod
    def vinyl_sheet_id(cls) -> str:
        if cls.APP_ENV == "prod":
            return cls.VINYL_SHEET_PROD

        if cls.APP_ENV == "test":
            return cls.VINYL_SHEET_TEST

    @classmethod
    def bot_token(cls) -> str:
        if cls.APP_ENV == "prod":
            return cls.BOT_TOKEN

        if cls.APP_ENV == "test":
            return cls.BOT_TOKEN_TEST

    @classmethod
    def local_image_dir(cls) -> str:
        if cls.APP_ENV == "prod":
            return cls.IMAGES_DIR_PROD

        if cls.APP_ENV == "test":
            return cls.IMAGES_DIR_TEST


def get_logger(name: str = __name__) -> logging.Logger:
    """
    Configures and returns a logger with a consistent format.

    Args:
        name (str): The logger name (typically __name__)

    Returns:
        logging.Logger: Configured logger instance
    """
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    return logging.getLogger(name)


if __name__ == "__main__":
    print(Config.APP_ENV)
