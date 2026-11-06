from motor.motor_asyncio import AsyncIOMotorClient
from config import Config

class Database:
    def __init__(self):
        self.client = AsyncIOMotorClient(Config.MONGO_URI)
        self.db = self.client[Config.DB_NAME]
        self.users = self.db.users
        self.downloads = self.db.downloads

    async def add_user(self, user_id: int, name: str):
        await self.users.update_one(
            {"user_id": user_id},
            {"$set": {"name": name}},
            upsert=True
        )

    async def get_user(self, user_id: int):
        return await self.users.find_one({"user_id": user_id})

    async def log_download(self, user_id: int, url: str, status: str):
        await self.downloads.insert_one({
            "user_id": user_id,
            "url": url,
            "status": status,
            "timestamp": "now" # In real app use datetime.utcnow()
        })

db = Database()
