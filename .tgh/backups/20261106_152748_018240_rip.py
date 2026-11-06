from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from providers.generic import GenericProvider
from database.mongo import db
import logging

logger = logging.getLogger(__name__)

# Initialize providers
PROVIDERS = [
    GenericProvider()
]

@Client.on_message(filters.command("rip") & filters.private)
async def rip_command(client: Client, message: Message):
    if len(message.command) < 2:
        await message.reply_text("Usage: `/rip <content_link>`")
        return

    url = message.command[1]
    status_msg = await message.reply_text("🔍 Analyzing link...")

    # Identify provider
    selected_provider = None
    for provider in PROVIDERS:
        if await provider.can_handle(url):
            selected_provider = provider
            break

    if not selected_provider:
        await status_msg.edit("❌ Unsupported provider or invalid link.")
        return

    try:
        # Retrieve metadata
        metadata = await selected_provider.get_metadata(url)
        formats = await selected_provider.get_formats(url)

        if not formats:
            await status_msg.edit("❌ No downloadable formats found.")
            return

        # Prepare UI
        text = (
            f"**Title:** {metadata.get('title')}\n"
            f"**Provider:** {metadata.get('provider')}\n\n"
            f"Select a format to download:"
        )

        buttons = []
        for fmt in formats:
            buttons.append([
                InlineKeyboardButton(
                    f"🎬 {fmt['resolution']} ({fmt['ext'].upper()}) - {fmt['note']}",
                    callback_data=f"dl_{fmt['format_id']}"
                )
            ])
        
        buttons.append([InlineKeyboardButton("❌ Cancel", callback_data="cancel")])

        await status_msg.delete()
        if metadata.get("poster"):
            await message.reply_photo(
                photo=metadata["poster"],
                caption=text,
                reply_markup=InlineKeyboardMarkup(buttons)
            )
        else:
            await message.reply_text(
                text=text,
                reply_markup=InlineKeyboardMarkup(buttons)
            )

        # Log to DB
        await db.add_user(message.from_user.id, message.from_user.first_name)
        await db.log_download(message.from_user.id, url, "analyzed")

    except Exception as e:
        logger.error(f"Error in /rip: {e}")
        await status_msg.edit(f"❌ An error occurred: {str(e)}")
