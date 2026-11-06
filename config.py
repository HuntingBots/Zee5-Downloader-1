import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    API_ID = int(os.environ.get("API_ID", 3975570))
    API_HASH = os.environ.get("API_HASH", "680b62f2844aa1954216f6cb99d2f3d9")
    BOT_TOKEN = os.environ.get("BOT_TOKEN", "8701802803:AAFimFrQ3OXeED12FIdFql6OTB9GKDJgJO8")
    MONGO_URI = os.environ.get("MONGO_URI", "mongodb+srv://Hauntingbots:ghost24@cluster0.5drldta.mongodb.net/?appName=Cluster0")
    DB_NAME = os.environ.get("DB_NAME", "tgh_downloader")
    OWNER_ID = int(os.environ.get("OWNER_ID", 1606221784))
    ALLOWED_GROUP_IDS = [
        -1003346392301,
        -1003943851323
    ]
    ALLOWED_GROUPS = ALLOWED_GROUP_IDS
    ALLOWED_USERS = [int(x) for x in os.environ.get("ALLOWED_USERS", "").split(",") if x]
