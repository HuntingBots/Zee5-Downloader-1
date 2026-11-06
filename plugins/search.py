import os
import time
import shutil
import asyncio
import logging
import uuid
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from providers.net79 import Net79Provider
from database.mongo import db
from utils.auth import authorized_only
from core.metadata import get_media_info

logger = logging.getLogger(__name__)

net79_client = Net79Provider()

# Search session storage
SEARCH_SESSIONS = {}

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
            "-ss", "00:00:03",
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
        logger.warning(f"Thumbnail generation error: {e}")
        return None

def build_search_results_markup(session_id: str, items: list) -> InlineKeyboardMarkup:
    buttons = []
    for idx, it in enumerate(items[:8]):
        m_type = "🎬" if it.get("type") == "movie" else "📺"
        year = f" ({it.get('year')})" if it.get("year") else ""
        rating = f" ⭐{it.get('rating')}" if it.get("rating") else ""
        btn_text = f"{m_type} {it.get('title')}{year}{rating}"
        buttons.append([
            InlineKeyboardButton(btn_text, callback_data=f"n79_pk_{session_id}_{idx}")
        ])

    buttons.append([
        InlineKeyboardButton("❌ Cancel", callback_data="cancel")
    ])
    return InlineKeyboardMarkup(buttons)

@Client.on_message(filters.command(["search"]) & authorized_only())
async def search_command(client: Client, message: Message):
    if len(message.command) < 2:
        await message.reply_text(
            "🔍 **How to Search:**\n\n"
            "Send `/search <Movie or Show Name>`\n\n"
            "**Examples:**\n"
            "• `/search Mirzapur`\n"
            "• `/search Panchayat`\n"
            "• `/search Oppenheimer`\n"
            "• `/search Karle Tu Bhi Mohabbat`",
            quote=True
        )
        return

    query = message.text.split(" ", 1)[1].strip()
    status_msg = await message.reply_text(f"🔍 Searching NetMirror for `{query}`...")

    items = await net79_client.search(query)
    if not items:
        await status_msg.edit_text(f"❌ No matching titles found for `{query}` on NetMirror / Net79.")
        return

    session_id = str(uuid.uuid4())[:8]
    SEARCH_SESSIONS[session_id] = {
        "query": query,
        "items": items,
        "selected_item": None,
        "qualities": [],
        "seasons": [],
        "cur_se": 1,
        "cur_ep": 1
    }

    reply_text = (
        f"🔍 **Search Results for:** `{query}`\n\n"
        f"Found {len(items)} titles on NetMirror.\n"
        f"Select a title below to view options & download:"
    )

    markup = build_search_results_markup(session_id, items)
    await status_msg.edit_text(reply_text, reply_markup=markup)


@Client.on_callback_query(filters.regex(r"^n79_pk_"))
async def handle_pick_title(client: Client, callback_query: CallbackQuery):
    parts = callback_query.data.split("_")
    session_id = parts[2]
    idx = int(parts[3])

    session = SEARCH_SESSIONS.get(session_id)
    if not session or idx >= len(session["items"]):
        await callback_query.answer("⚠️ Session expired. Please search again.", show_alert=True)
        return

    item = session["items"][idx]
    session["selected_item"] = item

    title = item.get("title", "Media")
    year = item.get("year", "")
    m_type = item.get("type", "movie")
    is_streamable = item.get("streamable", False)
    subject_id = item.get("subjectId")
    overview = item.get("overview", "")
    rating = item.get("rating", "N/A")

    # If Coming Soon or Not Streamable
    if not is_streamable or not subject_id:
        cta = item.get("cta", "Coming Soon")
        text = (
            f"📌 **{title}** ({year})\n\n"
            f"📝 {overview[:200]}...\n\n"
            f"⚠️ **Status:** `{cta}` on NetMirror.\n"
            f"Streaming sources for this title are not yet indexed on NetMirror.\n\n"
            f"💡 *Tip: Try searching for fully available titles like Mirzapur, Panchayat, Oppenheimer, etc.*"
        )
        buttons = [
            [InlineKeyboardButton("⬅️ Back to Results", callback_data=f"n79_back_{session_id}")],
            [InlineKeyboardButton("❌ Close", callback_data="cancel")]
        ]
        await callback_query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(buttons))
        await callback_query.answer()
        return

    await callback_query.answer("Loading media details...", show_alert=False)

    # If it is a Movie
    if m_type == "movie":
        status_msg = await callback_query.message.edit_text(f"⏳ Fetching quality options for **{title}**...")
        dl_info = await net79_client.get_download_info(
            subject_id=subject_id,
            detail_path=item.get("detailPath", ""),
            season=0,
            episode=0,
            media_type=1
        )
        qualities = dl_info.get("qualities", [])
        if not qualities:
            await status_msg.edit_text(f"❌ No downloadable qualities found for **{title}**.")
            return

        session["qualities"] = qualities
        text = (
            f"🎬 **{title}** ({year})\n"
            f"⭐ Rating: `{rating}`\n\n"
            f"📝 {overview[:180]}...\n\n"
            f"Select a download quality:"
        )

        buttons = []
        for q_idx, q in enumerate(qualities):
            res = q.get("res", "HD")
            size = human_bytes(q.get("size", 0))
            buttons.append([
                InlineKeyboardButton(f"▶️ {res}p | {size}", callback_data=f"n79_dl_{session_id}_{q_idx}")
            ])
        buttons.append([InlineKeyboardButton("⬅️ Back", callback_data=f"n79_back_{session_id}")])

        await status_msg.edit_text(text, reply_markup=InlineKeyboardMarkup(buttons))
        return

    # If it is a TV Show (Series)
    if m_type == "tv":
        tmdb_id = item.get("tmdbId")
        status_msg = await callback_query.message.edit_text(f"⏳ Fetching seasons for **{title}**...")
        details = await net79_client.get_title_details(tmdb_id, "tv")
        seasons = details.get("seasons", [])
        if not seasons:
            seasons = [{"season_number": 1, "episode_count": 10, "name": "Season 1"}]

        session["seasons"] = seasons

        text = (
            f"📺 **{title}** ({year})\n"
            f"⭐ Rating: `{rating}`\n\n"
            f"📝 {overview[:180]}...\n\n"
            f"Select a Season:"
        )

        buttons = []
        row = []
        for s in seasons:
            s_num = s.get("season_number", 1)
            if s_num == 0:
                continue # Skip specials
            row.append(InlineKeyboardButton(f"Season {s_num}", callback_data=f"n79_se_{session_id}_{s_num}"))
            if len(row) == 2:
                buttons.append(row)
                row = []
        if row:
            buttons.append(row)

        buttons.append([InlineKeyboardButton("⬅️ Back", callback_data=f"n79_back_{session_id}")])
        await status_msg.edit_text(text, reply_markup=InlineKeyboardMarkup(buttons))


@Client.on_callback_query(filters.regex(r"^n79_se_"))
async def handle_pick_season(client: Client, callback_query: CallbackQuery):
    parts = callback_query.data.split("_")
    session_id = parts[2]
    season_num = int(parts[3])

    session = SEARCH_SESSIONS.get(session_id)
    if not session or not session.get("selected_item"):
        await callback_query.answer("⚠️ Session expired.", show_alert=True)
        return

    session["cur_se"] = season_num
    item = session["selected_item"]
    title = item.get("title", "Show")
    tmdb_id = item.get("tmdbId")

    await callback_query.answer(f"Loading Season {season_num} episodes...", show_alert=False)

    # Find episode count
    ep_count = 10
    for s in session.get("seasons", []):
        if s.get("season_number") == season_num:
            ep_count = s.get("episode_count", 10)
            break

    # Build episode buttons in rows of 5
    buttons = []
    row = []
    for ep in range(1, ep_count + 1):
        row.append(InlineKeyboardButton(f"EP {ep}", callback_data=f"n79_ep_{session_id}_{season_num}_{ep}"))
        if len(row) == 5:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)

    buttons.append([InlineKeyboardButton("⬅️ Back to Seasons", callback_data=f"n79_pk_{session_id}_0")])

    text = (
        f"📺 **{title}** — Season {season_num}\n\n"
        f"Select an episode to download:"
    )
    await callback_query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(buttons))


@Client.on_callback_query(filters.regex(r"^n79_ep_"))
async def handle_pick_episode(client: Client, callback_query: CallbackQuery):
    parts = callback_query.data.split("_")
    session_id = parts[2]
    season_num = int(parts[3])
    ep_num = int(parts[4])

    session = SEARCH_SESSIONS.get(session_id)
    if not session or not session.get("selected_item"):
        await callback_query.answer("⚠️ Session expired.", show_alert=True)
        return

    session["cur_se"] = season_num
    session["cur_ep"] = ep_num
    item = session["selected_item"]
    title = item.get("title", "Show")

    await callback_query.answer(f"Loading Episode {ep_num}...", show_alert=False)
    status_msg = await callback_query.message.edit_text(f"⏳ Fetching qualities for **{title} S{season_num}E{ep_num}**...")

    dl_info = await net79_client.get_download_info(
        subject_id=item.get("subjectId"),
        detail_path=item.get("detailPath", ""),
        season=season_num,
        episode=ep_num,
        media_type=2
    )

    qualities = dl_info.get("qualities", [])
    if not qualities:
        await status_msg.edit_text(f"❌ No downloadable streams found for **{title} S{season_num}E{ep_num}**.")
        return

    session["qualities"] = qualities

    text = (
        f"📺 **{title}** — Season {season_num}, Episode {ep_num}\n\n"
        f"Select a download quality:"
    )

    buttons = []
    for q_idx, q in enumerate(qualities):
        res = q.get("res", "HD")
        size = human_bytes(q.get("size", 0))
        buttons.append([
            InlineKeyboardButton(f"▶️ {res}p | {size}", callback_data=f"n79_dl_{session_id}_{q_idx}")
        ])

    buttons.append([InlineKeyboardButton("⬅️ Back to Episodes", callback_data=f"n79_se_{session_id}_{season_num}")])
    await status_msg.edit_text(text, reply_markup=InlineKeyboardMarkup(buttons))


@Client.on_callback_query(filters.regex(r"^n79_dl_"))
async def handle_download_selected(client: Client, callback_query: CallbackQuery):
    parts = callback_query.data.split("_")
    session_id = parts[2]
    q_idx = int(parts[3])

    session = SEARCH_SESSIONS.get(session_id)
    if not session or not session.get("qualities") or q_idx >= len(session["qualities"]):
        await callback_query.answer("⚠️ Session expired. Please search again.", show_alert=True)
        return

    q = session["qualities"][q_idx]
    item = session.get("selected_item", {})
    title = item.get("title", "Video")
    m_type = item.get("type", "movie")
    se = session.get("cur_se", 1)
    ep = session.get("cur_ep", 1)
    res = q.get("res", "720")
    stream_url = q.get("url") or q.get("raw")

    if m_type == "tv":
        full_title = f"{title} S{se:02d}E{ep:02d}"
    else:
        full_title = f"{title} ({item.get('year', '')})"

    await callback_query.answer(f"Starting download: {res}p", show_alert=False)

    chat_id = callback_query.message.chat.id
    user_id = callback_query.from_user.id if callback_query.from_user else chat_id

    status_msg = await callback_query.message.reply_text(
        f"⏳ **Starting download...**\n"
        f"📌 `{full_title}`\n"
        f"⚙️ Quality: `{res}p`\n\n"
        f"Connecting to NetMirror proxy..."
    )

    work_dir = f"/tmp/tgh_downloads/{user_id}_{session_id}"
    os.makedirs(work_dir, exist_ok=True)
    safe_name = "".join(c for c in full_title if c.isalnum() or c in (" ", "_", "-")).strip()
    dest_path = os.path.join(work_dir, f"{safe_name}_{res}p.mp4")

    # Progress reporting for download
    last_dl_edit = [0]
    async def dl_progress(current, total):
        now = time.time()
        if now - last_dl_edit[0] >= 3.5 or current == total:
            last_dl_edit[0] = now
            pct = round((current / total) * 100) if total else 0
            try:
                await status_msg.edit_text(
                    f"⬇️ **Downloading:** `{full_title}`\n"
                    f"📊 Progress: `{pct}%`\n"
                    f"📦 `{human_bytes(current)}` / `{human_bytes(total)}`"
                )
            except Exception:
                pass

    try:
        success = await net79_client.download_file(stream_url, dest_path, progress_callback=dl_progress)
        if not success or not os.path.exists(dest_path):
            await status_msg.edit_text("❌ Download failed. Could not fetch media stream.")
            return

        file_size = os.path.getsize(dest_path)
        if file_size > 2000 * 1024 * 1024:
            await status_msg.edit_text(f"❌ File size exceeds Telegram's 2GB limit ({human_bytes(file_size)}).")
            return

        await status_msg.edit_text(
            f"⬆️ **Uploading to Telegram:** `{human_bytes(file_size)}`\n"
            f"⏳ Generating preview and metadata..."
        )

        thumb_path = os.path.join(work_dir, "thumb.jpg")
        thumb = await generate_thumbnail(dest_path, thumb_path)

        media_info = await get_media_info(dest_path)
        duration = int(media_info.get("duration", 0))
        r_parts = str(media_info.get("resolution", "0x0")).split("x")
        width = int(r_parts[0]) if len(r_parts) == 2 and r_parts[0].isdigit() else 0
        height = int(r_parts[1]) if len(r_parts) == 2 and r_parts[1].isdigit() else 0

        caption = (
            f"🎬 **{full_title}**\n\n"
            f"✨ Quality: `{res}p`\n"
            f"⚖️ Size: `{human_bytes(file_size)}`\n"
            f"⏱️ Duration: `{duration}s`\n\n"
            f"🤖 *Downloaded via NetMirror / Net79*"
        )

        last_up_edit = [0]
        async def up_progress(current, total):
            now = time.time()
            if now - last_up_edit[0] >= 3.5:
                last_up_edit[0] = now
                pct = round((current / total) * 100) if total else 0
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
                video=dest_path,
                caption=caption,
                duration=duration,
                width=width,
                height=height,
                thumb=thumb,
                supports_streaming=True,
                progress=up_progress
            )
        except Exception as ve:
            logger.warning(f"send_video error ({ve}), sending as document...")
            await client.send_document(
                chat_id=chat_id,
                document=dest_path,
                caption=caption,
                thumb=thumb,
                progress=up_progress
            )

        await status_msg.delete()
        if user_id:
            await db.log_download(user_id, stream_url, "completed")

    except Exception as e:
        logger.error(f"Download/Upload error in search: {e}", exc_info=True)
        await status_msg.edit_text(f"❌ An error occurred: `{str(e)}`")
    finally:
        shutil.rmtree(work_dir, ignore_errors=True)


@Client.on_callback_query(filters.regex(r"^n79_back_"))
async def handle_back_to_results(client: Client, callback_query: CallbackQuery):
    session_id = callback_query.data.split("_")[2]
    session = SEARCH_SESSIONS.get(session_id)
    if not session:
        await callback_query.answer("Session expired.", show_alert=True)
        return

    items = session["items"]
    query = session["query"]
    markup = build_search_results_markup(session_id, items)
    await callback_query.message.edit_text(
        f"🔍 **Search Results for:** `{query}`\n\n"
        f"Select a title below to view options & download:",
        reply_markup=markup
    )
    await callback_query.answer()
