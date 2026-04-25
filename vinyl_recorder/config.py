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

    # SQLITE DB FILES
    DB_PATH_PROD = LOCAL_WD / "data/vinyl_collection.db"
    DB_PATH_TEST = LOCAL_WD / "data/vinyl_collection_test.db"

    # LLM ANTHROPIC
    ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
    ANTHROPIC_MODEL = "claude-haiku-4-5-20251001"

    # TELEGRAM
    BOT_TOKEN = os.getenv("BOT_TOKEN")
    BOT_TOKEN_TEST = os.getenv("BOT_TOKEN_TEST")

    @classmethod
    def validate(cls):
        """Check that required environment variables are set."""
        required = {
            "APP_ENV": cls.APP_ENV,
            "ANTHROPIC_API_KEY": cls.ANTHROPIC_API_KEY,
        }
        missing = [name for name, value in required.items() if not value]
        if missing:
            raise EnvironmentError(
                f"Missing required environment variables: {', '.join(missing)}"
            )

    @classmethod
    def bot_token(cls) -> str:
        if cls.APP_ENV == "prod":
            return cls.BOT_TOKEN
        if cls.APP_ENV == "test":
            return cls.BOT_TOKEN_TEST
        raise ValueError(f"APP_ENV must be 'prod' or 'test', got: {cls.APP_ENV!r}")

    @classmethod
    def local_image_dir(cls):
        if cls.APP_ENV == "prod":
            return cls.IMAGES_DIR_PROD
        if cls.APP_ENV == "test":
            return cls.IMAGES_DIR_TEST
        raise ValueError(f"APP_ENV must be 'prod' or 'test', got: {cls.APP_ENV!r}")

    @classmethod
    def db_path(cls):
        if cls.APP_ENV == "prod":
            return cls.DB_PATH_PROD
        if cls.APP_ENV == "test":
            return cls.DB_PATH_TEST
        raise ValueError(f"APP_ENV must be 'prod' or 'test', got: {cls.APP_ENV!r}")


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
