from pyrogram import filters
from config import Config

def authorized_only():
    async def func(_, __, message):
        user_id = message.from_user.id if message.from_user else None
        chat_id = message.chat.id if message.chat else None
        
        # Owner always has access
        if user_id and user_id == Config.OWNER_ID:
            return True
        
        # Check if user is in allowed list
        if user_id and user_id in Config.ALLOWED_USERS:
            return True
            
        # Check if group is in allowed list
        allowed_groups = getattr(Config, "ALLOWED_GROUP_IDS", getattr(Config, "ALLOWED_GROUPS", []))
        if chat_id and chat_id in allowed_groups:
            return True
            
        return False
    
    return filters.create(func)
