import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    API_ID = int(os.environ.get("API_ID", 0))
    API_HASH = os.environ.get("API_HASH", "")
    BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
    MONGO_URI = os.environ.get("MONGO_URI", "mongodb://localhost:27017")
    DB_NAME = os.environ.get("DB_NAME", "tgh_downloader")
    OWNER_ID = int(os.environ.get("OWNER_ID", 0))
    ALLOWED_USERS = [int(x) for x in os.environ.get("ALLOWED_USERS", "").split(",") if x]
    ALLOWED_GROUPS = [int(x) for x in os.environ.get("ALLOWED_GROUPS", "").split(",") if x]

