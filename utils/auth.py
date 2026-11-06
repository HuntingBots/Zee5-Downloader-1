from pyrogram import filters
from config import Config

def authorized_only():
    async def func(_, __, message):
        user_id = message.from_user.id
        chat_id = message.chat.id
        
        # Owner always has access
        if user_id == Config.OWNER_ID:
            return True
        
        # Check if user is in allowed list
        if user_id in Config.ALLOWED_USERS:
            return True
            
        # Check if group is in allowed list
        if chat_id in Config.ALLOWED_GROUPS:
            return True
            
        return False
    
    return filters.create(func)
