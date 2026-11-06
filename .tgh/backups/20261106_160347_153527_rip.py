from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from providers.net79 import Net79Provider
from database.mongo import db
from utils.auth import authorized_only
import logging

logger = logging.getLogger(__name__)

# Initialize providers
PROVIDERS = [
    Net79Provider()
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

        # Prepare Modern UI
        text = (
            f"✨ **MEDIA ANALYSIS COMPLETE**\n\n"
            f"📌 **Title:** `{metadata.get('title')}`\n"
            f"🌐 **Source:** `{metadata.get('provider')}`\n"
            f"📦 **Container:** `{metadata.get('ext', 'N/A')}`\n"
            f"⚖️ **Est. Size:** `{metadata.get('size', 'Unknown')}`\n\n"
            f"Choose a quality to proceed:"
        )

        buttons = []
        # Grouping buttons for better UX
        for fmt in formats:
            # Example: 1080p | 2.5GB | MP4
            btn_text = f"▶️ {fmt['resolution']} | {fmt['note']}"
            buttons.append([
                InlineKeyboardButton(btn_text, callback_data=f"dl_{fmt['format_id']}")
            ])

        # Footer Action Bar
        buttons.append([
            InlineKeyboardButton("🔄 Refresh", callback_data="refresh"),
            InlineKeyboardButton("ℹ️ Details", callback_data="info")
        ])
        buttons.append([
            InlineKeyboardButton("❌ Cancel", callback_data="cancel")
        ])

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
