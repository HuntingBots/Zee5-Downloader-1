from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from providers.net79 import Net79Provider
from providers.generic import GenericProvider
from providers.zee5 import Zee5Provider
from database.mongo import db
from utils.auth import authorized_only
import logging
import re

logger = logging.getLogger(__name__)

# Initialize providers in order of priority
PROVIDERS = [
    Net79Provider(),
    Zee5Provider(),
    GenericProvider()
]

def clean_url_string(text: str) -> str:
    # Remove leading/trailing spaces, angle brackets, markdown symbols
    url = text.strip().strip("<>\"' ")
    return url

async def process_media_url(client: Client, message: Message, raw_url: str):
    url = clean_url_string(raw_url)
    user_id = message.from_user.id if message.from_user else "unknown"
    logger.info(f"Processing URL from user {user_id}: {url}")

    status_msg = await message.reply_text("🔍 Analyzing link...")

    # Identify provider
    selected_provider = None
    for provider in PROVIDERS:
        try:
            if await provider.can_handle(url):
                selected_provider = provider
                break
        except Exception as e:
            logger.error(f"Error checking provider {provider.__class__.__name__}: {e}")

    if not selected_provider:
        logger.warning(f"No provider found for URL: {url}")
        unsupported_text = (
            "❌ **Unsupported provider or invalid link.**\n\n"
            "📌 **Supported formats:**\n"
            "• **NetMirror / Net79** (`net79.cc`, `netmirror`)\n"
            "• **Direct streams** (`.m3u8`, `.mp4`, `.mkv`, etc.)\n"
            "• **Streaming sites** supported by yt-dlp\n\n"
            "💡 *Make sure your link starts with `http://` or `https://`.*"
        )
        await status_msg.edit(unsupported_text)
        return

    logger.info(f"Selected provider: {selected_provider.__class__.__name__} for {url}")

    # Special handling for Zee5 DRM
    if isinstance(selected_provider, Zee5Provider):
        drm_text = (
            "⚠️ **DRM Protected Content Detected**\n\n"
            "📌 **Platform:** Zee5\n\n"
            "🔒 Zee5 media streams are encrypted with Widevine DRM. "
            "Per security policies, DRM decryption bypass is strictly disabled.\n\n"
            "💡 *Please provide non-DRM streams or links from NetMirror/Net79 or direct video URLs.*"
        )
        await status_msg.edit(drm_text)
        return

    try:
        # Retrieve metadata & formats
        metadata = await selected_provider.get_metadata(url)
        formats = await selected_provider.get_formats(url)

        if not formats:
            await status_msg.edit("❌ No downloadable formats found for this link.")
            return

        title = metadata.get("title", "Media Stream")
        provider_name = metadata.get("provider", selected_provider.__class__.__name__)
        ext = metadata.get("ext", "mp4")
        size = metadata.get("size", "Unknown")

        # Prepare Modern UI
        text = (
            f"✨ **MEDIA ANALYSIS COMPLETE**\n\n"
            f"📌 **Title:** `{title}`\n"
            f"🌐 **Source:** `{provider_name}`\n"
            f"📦 **Container:** `{ext}`\n"
            f"⚖️ **Est. Size:** `{size}`\n\n"
            f"Choose a quality to proceed:"
        )

        buttons = []
        # Group formats into buttons (limit to first 8 for Telegram markup limit)
        for fmt in formats[:8]:
            btn_text = f"▶️ {fmt.get('resolution', 'Default')} | {fmt.get('note', ext)}"
            buttons.append([
                InlineKeyboardButton(btn_text, callback_data=f"dl_{fmt.get('format_id')}")
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
        poster = metadata.get("poster")
        if poster and isinstance(poster, str) and poster.startswith("http"):
            try:
                await message.reply_photo(
                    photo=poster,
                    caption=text,
                    reply_markup=InlineKeyboardMarkup(buttons)
                )
            except Exception:
                await message.reply_text(
                    text=text,
                    reply_markup=InlineKeyboardMarkup(buttons)
                )
        else:
            await message.reply_text(
                text=text,
                reply_markup=InlineKeyboardMarkup(buttons)
            )

        # Log to DB
        user = message.from_user
        if user:
            await db.add_user(user.id, user.first_name)
            await db.log_download(user.id, url, "analyzed")

    except Exception as e:
        logger.error(f"Error analyzing media for {url}: {e}", exc_info=True)
        await status_msg.edit(f"❌ An error occurred while analyzing the media:\n`{str(e)}`")


@Client.on_message(filters.command("rip") & authorized_only())
async def rip_command(client: Client, message: Message):
    if len(message.command) < 2:
        await message.reply_text(
            "ℹ️ **Usage:** `/rip <content_link>`\n\n"
            "Example:\n`/rip https://net79.cc/watch/...`\n`/rip https://example.com/video.m3u8`"
        )
        return

    raw_url = message.command[1]
    await process_media_url(client, message, raw_url)


@Client.on_message(filters.regex(r"^https?://") & filters.private & authorized_only())
async def direct_url_message(client: Client, message: Message):
    raw_url = message.text.strip()
    await process_media_url(client, message, raw_url)


@Client.on_callback_query(filters.regex(r"^dl_"))
async def download_callback(client: Client, callback_query: CallbackQuery):
    format_id = callback_query.data.split("dl_", 1)[1]
    await callback_query.answer("Download requested! Processing...", show_alert=False)
    await callback_query.message.reply_text(f"🚀 Processing download for format: `{format_id}`")


@Client.on_callback_query(filters.regex(r"^cancel$"))
async def cancel_callback(client: Client, callback_query: CallbackQuery):
    await callback_query.message.delete()
    await callback_query.answer("Cancelled", show_alert=False)


@Client.on_callback_query(filters.regex(r"^info$"))
async def info_callback(client: Client, callback_query: CallbackQuery):
    await callback_query.answer("TGH OTT Downloader - Quality Selection Menu", show_alert=True)


@Client.on_callback_query(filters.regex(r"^refresh$"))
async def refresh_callback(client: Client, callback_query: CallbackQuery):
    await callback_query.answer("Refreshed details!", show_alert=False)
