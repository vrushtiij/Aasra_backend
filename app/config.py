import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    DATABASE_URL: str = os.getenv("DATABASE_URL", "")

    # Path to a Firebase service-account JSON file (recommended), OR the raw
    # JSON contents in an env var (handy for hosts where you can't ship a file).
    FIREBASE_CREDENTIALS_PATH: str = os.getenv("FIREBASE_CREDENTIALS_PATH", "")
    FIREBASE_CREDENTIALS_JSON: str = os.getenv("FIREBASE_CREDENTIALS_JSON", "")

    # How many times a due medicine/task/appointment reminder is re-pushed
    # before it counts as "repeatedly missed" for alerting purposes.
    REMINDER_REPEAT_LIMIT: int = int(os.getenv("REMINDER_REPEAT_LIMIT", "3"))


settings = Settings()

if not settings.DATABASE_URL:
    raise ValueError("DATABASE_URL is not set in .env")
