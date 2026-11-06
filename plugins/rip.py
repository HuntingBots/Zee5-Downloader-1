import os
import time
import shutil
import asyncio
import logging
import uuid
import yt_dlp
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from providers.net79 import Net79Provider
from providers.generic import GenericProvider
from providers.ott_drm import OTTDRMProvider
from providers.zee5 import Zee5Provider
from database.mongo import db
from utils.auth import authorized_only
from core.metadata import get_media_info

logger = logging.getLogger(__name__)

# Providers in order of evaluation
PROVIDERS = [
    Net79Provider(),
    OTTDRMProvider(),
    Zee5Provider(),
    GenericProvider()
]

# In-memory download cache for callback sessions
DOWNLOAD_CACHE = {}

def clean_url_string(text: str) -> str:
    return text.strip().strip("<>\"' ")

def human_bytes(size: int) -> str:
    if not size:
        return "0 B"
    units = ["B", "KB", "MB", "GB", "TB"]
    i = 0
    size_f = float(size)
    while size_f >= 1024.0 and i < len(units) - 1:
        size_f /= 1024.0
        i += 1
    return f"{size_f:.2f} {units[i]}"

async def generate_thumbnail(video_path: str, thumb_path: str) -> str:
    try:
        cmd = [
            "ffmpeg", "-y",
            "-ss", "00:00:02",
            "-i", video_path,
            "-vframes", "1",
            "-q:v", "2",
            thumb_path
        ]
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        await process.communicate()
        return thumb_path if os.path.exists(thumb_path) else None
    except Exception as e:
        logger.warning(f"Could not generate thumbnail: {e}")
        return None

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
            "• **Web video sites** supported by yt-dlp\n\n"
            "💡 *Ensure your link starts with `http://` or `https://`.*"
        )
        await status_msg.edit(unsupported_text)
        return

    logger.info(f"Selected provider: {selected_provider.__class__.__name__} for {url}")

    # Special handling for DRM-protected OTT platforms
    if isinstance(selected_provider, (OTTDRMProvider, Zee5Provider)):
        platform = getattr(selected_provider, "get_platform_name", lambda u: "OTT Platform")(url)
        drm_text = (
            f"⚠️ **DRM Protected Content Detected**\n\n"
            f"📌 **Platform:** {platform}\n\n"
            f"🔒 Media streams on **{platform}** are encrypted using Widevine DRM and protected against unauthorized extraction.\n\n"
            f"Per project guidelines, DRM decryption bypass is strictly disabled.\n\n"
            f"💡 *Supported for ripping:* NetMirror/Net79 (`net79.cc`), direct `.m3u8` / `.mp4` links, YouTube, and unencrypted web streams."
        )
        await status_msg.edit(drm_text)
        return

    try:
        # Retrieve metadata & formats
        metadata = await selected_provider.get_metadata(url)
        formats = await selected_provider.get_formats(url)

        if not formats:
            err = metadata.get("error")
            err_msg = f"\n\n*Details:* `{err}`" if err else ""
            await status_msg.edit(f"❌ No downloadable streams or formats found for this link.{err_msg}")
            return

        title = metadata.get("title", "Media Stream")
        provider_name = metadata.get("provider", selected_provider.__class__.__name__)
        ext = metadata.get("ext", "mp4")
        size = metadata.get("size", "Auto")

        cache_id = str(uuid.uuid4())[:8]
        DOWNLOAD_CACHE[cache_id] = {
            "url": url,
            "title": title,
            "provider": provider_name,
            "ext": ext,
            "metadata": metadata,
            "provider_obj": selected_provider
        }

        # Prepare Modern UI
        text = (
            f"✨ **MEDIA ANALYSIS COMPLETE**\n\n"
            f"📌 **Title:** `{title}`\n"
            f"🌐 **Source:** `{provider_name}`\n"
            f"📦 **Container:** `{ext}`\n"
            f"⚖️ **Est. Size:** `{size}`\n\n"
            f"Choose a quality to download:"
        )

        buttons = []
        for fmt in formats[:8]:
            btn_text = f"▶️ {fmt.get('resolution', 'Default')} | {fmt.get('note', ext)}"
            buttons.append([
                InlineKeyboardButton(btn_text, callback_data=f"dl_{cache_id}_{fmt.get('format_id')}")
            ])

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
    parts = callback_query.data.split("_", 2)
    if len(parts) < 3:
        await callback_query.answer("Invalid selection data.", show_alert=True)
        return

    cache_id = parts[1]
    format_id = parts[2]

    data = DOWNLOAD_CACHE.get(cache_id)
    if not data:
        await callback_query.answer("⚠️ Session expired. Please send the link again.", show_alert=True)
        return

    await callback_query.answer("Starting download process...", show_alert=False)
    
    title = data.get("title", "Video")
    url = data["url"]
    chat_id = callback_query.message.chat.id
    user_id = callback_query.from_user.id if callback_query.from_user else chat_id

    status_msg = await callback_query.message.reply_text(
        f"⏳ **Starting download...**\n"
        f"📌 **Title:** `{title}`\n"
        f"⚙️ **Format:** `{format_id}`\n\n"
        f"Please wait, fetching media stream..."
    )

    work_dir = f"/tmp/tgh_downloads/{user_id}_{cache_id}"
    os.makedirs(work_dir, exist_ok=True)
    out_template = os.path.join(work_dir, "%(title).60s.%(ext)s")

    loop = asyncio.get_running_loop()

    # yt-dlp download options
    ydl_opts = {
        "outtmpl": out_template,
        "quiet": True,
        "no_warnings": True,
        "max_filesize": 2000 * 1024 * 1024, # 2 GB Telegram Limit
    }
    if format_id not in ["direct", "default", "best"]:
        ydl_opts["format"] = f"{format_id}+bestaudio/best"
    else:
        ydl_opts["format"] = "best"

    try:
        await status_msg.edit_text(f"⬇️ **Downloading:** `{title}`\n⏳ Fetching stream fragments...")

        def _do_download():
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])

        await loop.run_in_executor(None, _do_download)

        # Find downloaded file
        downloaded_files = [
            os.path.join(work_dir, f) for f in os.listdir(work_dir)
            if not f.endswith((".part", ".ytdl")) and os.path.isfile(os.path.join(work_dir, f))
        ]

        if not downloaded_files:
            await status_msg.edit_text("❌ Download failed: No media file was created.")
            return

        file_path = downloaded_files[0]
        file_size = os.path.getsize(file_path)

        if file_size > 2000 * 1024 * 1024:
            await status_msg.edit_text(
                f"❌ File size `{human_bytes(file_size)}` exceeds Telegram's 2GB upload limit."
            )
            return

        await status_msg.edit_text(
            f"⬆️ **Uploading to Telegram:** `{human_bytes(file_size)}`\n⏳ Please wait..."
        )

        # Generate thumbnail
        thumb_path = os.path.join(work_dir, "thumb.jpg")
        thumb = await generate_thumbnail(file_path, thumb_path)

        # Extract metadata
        media_info = await get_media_info(file_path)
        duration = int(media_info.get("duration", 0))
        res_parts = str(media_info.get("resolution", "0x0")).split("x")
        width = int(res_parts[0]) if len(res_parts) == 2 and res_parts[0].isdigit() else 0
        height = int(res_parts[1]) if len(res_parts) == 2 and res_parts[1].isdigit() else 0

        caption = (
            f"🎬 **{title}**\n\n"
            f"⚖️ **Size:** `{human_bytes(file_size)}`\n"
            f"⏱️ **Duration:** `{duration}s`\n\n"
            f"🤖 *Downloaded via TGH OTT Downloader*"
        )

        last_edit = [0]
        async def upload_progress(current, total):
            now = time.time()
            if now - last_edit[0] >= 3.5:
                last_edit[0] = now
                pct = round((current / total) * 100)
                try:
                    await status_msg.edit_text(
                        f"⬆️ **Uploading:** `{pct}%`\n"
                        f"📦 `{human_bytes(current)}` / `{human_bytes(total)}`"
                    )
                except Exception:
                    pass

        try:
            await client.send_video(
                chat_id=chat_id,
                video=file_path,
                caption=caption,
                duration=duration,
                width=width,
                height=height,
                thumb=thumb,
                supports_streaming=True,
                progress=upload_progress
            )
        except Exception as ve:
            logger.warning(f"send_video failed ({ve}), trying send_document...")
            await client.send_document(
                chat_id=chat_id,
                document=file_path,
                caption=caption,
                thumb=thumb,
                progress=upload_progress
            )

        await status_msg.delete()
        if user_id:
            await db.log_download(user_id, url, "completed")

    except Exception as e:
        logger.error(f"Download or upload failed: {e}", exc_info=True)
        await status_msg.edit_text(f"❌ An error occurred during download/upload:\n`{str(e)}`")
    finally:
        shutil.rmtree(work_dir, ignore_errors=True)


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
