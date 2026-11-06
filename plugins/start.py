import time
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from database.mongo import db

START_TEXT = """
👋 **Hello, {}!**

Welcome to **TGH Universal OTT Downloader** 🎬.

I can help you extract and download media streams from supported OTT platforms.

Use `/help` to see available commands and usage guide.
"""

HELP_TEXT = """
📖 **How to Use:**

1. Send `/rip <content_link>` to analyze media.
2. Choose your preferred quality/resolution from the inline buttons.
3. The bot will process and deliver the media.

**Supported Platforms:**
• Net79 (`net79.cc`)
• More coming soon!

**Commands:**
• `/start` - Start the bot
• `/help` - Show this help message
• `/rip <link>` - Analyze & download media
• `/about` - About this bot
• `/ping` - Check bot latency
"""

ABOUT_TEXT = """
🤖 **About This Bot**

• **Name:** TGH Universal OTT Downloader
• **Framework:** Pyrogram
• **Database:** MongoDB
• **Engine:** FFmpeg / FFprobe
"""

def get_start_buttons():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("📖 Help", callback_data="help_menu"),
            InlineKeyboardButton("ℹ️ About", callback_data="about_menu")
        ]
    ])

def get_back_button():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("⬅️ Back", callback_data="start_menu")]
    ])

@Client.on_message(filters.command(["start"]))
async def start_handler(client: Client, message: Message):
    user = message.from_user
    if user:
        await db.add_user(user.id, user.first_name)
    name = user.first_name if user else "there"
    await message.reply_text(
        text=START_TEXT.format(name),
        reply_markup=get_start_buttons(),
        disable_web_page_preview=True
    )

@Client.on_message(filters.command(["help"]))
async def help_handler(client: Client, message: Message):
    await message.reply_text(
        text=HELP_TEXT,
        disable_web_page_preview=True
    )

@Client.on_message(filters.command(["about"]))
async def about_handler(client: Client, message: Message):
    await message.reply_text(
        text=ABOUT_TEXT,
        disable_web_page_preview=True
    )

@Client.on_message(filters.command(["ping"]))
async def ping_handler(client: Client, message: Message):
    start = time.time()
    reply = await message.reply_text("🏓 Pong!")
    end = time.time()
    await reply.edit_text(f"🏓 Pong! `{round((end - start) * 1000)}ms`")

@Client.on_callback_query(filters.regex(r"^help_menu$"))
async def help_menu_callback(client: Client, callback_query: CallbackQuery):
    await callback_query.message.edit_text(
        text=HELP_TEXT,
        reply_markup=get_back_button(),
        disable_web_page_preview=True
    )
    await callback_query.answer()

@Client.on_callback_query(filters.regex(r"^about_menu$"))
async def about_menu_callback(client: Client, callback_query: CallbackQuery):
    await callback_query.message.edit_text(
        text=ABOUT_TEXT,
        reply_markup=get_back_button(),
        disable_web_page_preview=True
    )
    await callback_query.answer()

@Client.on_callback_query(filters.regex(r"^start_menu$"))
async def start_menu_callback(client: Client, callback_query: CallbackQuery):
    name = callback_query.from_user.first_name if callback_query.from_user else "there"
    await callback_query.message.edit_text(
        text=START_TEXT.format(name),
        reply_markup=get_start_buttons(),
        disable_web_page_preview=True
    )
    await callback_query.answer()
