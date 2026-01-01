import os
from dotenv import load_dotenv
import logging

# Load environment variables
load_dotenv()


class Config:
    # ENV
    APP_ENV = os.getenv("APP_ENV")

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
