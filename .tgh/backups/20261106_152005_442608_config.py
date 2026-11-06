import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    API_ID = int(os.getenv("API_ID", 0))
    API_HASH = os.getenv("API_HASH", "")
    BOT_TOKEN = os.getenv("BOT_TOKEN", "")
    MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
    OWNER_ID = int(os.getenv("OWNER_ID", 0))
    DOWNLOAD_PATH = os.getenv("DOWNLOAD_PATH", "./downloads")
    LOG_CHANNEL = int(os.getenv("LOG_CHANNEL", 0))
    
    # Database Name
    DB_NAME = "tgh_downloader"
    
    # Supported Providers (Internal names)
    SUPPORTED_PROVIDERS = ["generic"]
