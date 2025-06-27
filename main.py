import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    filters,
    CallbackContext,
    CallbackQueryHandler,
)
from datetime import datetime, timedelta
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from flask import Flask
import threading

# Logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# Bot Credentials (Hardcoded)
BOT_TOKEN = "7935176546:AAEV4kJjhWykYYzOVQdA4hWgXQw5hEmLSRY"
GOOGLE_SHEET_ID = "1xAsBiibQSLDB8rRiFRQ5HxuWtNYCzPiaYXjt_wKANHg"
OWNER_USERNAME = "priteshsadhukhan"
OWNER_GROUP_LINK = "https://t.me/starkmoviesh"
PREMIUM_CONTACT = "@priteshsadhukhan"
PREMIUM_GROUP_LINK = "https://t.me/thestarkpremium"
BOT_NAME = "J.A.R.V.I.S (FREE)"
GROUP_NAME = "THE STARK MOVIES HUB (FREE)"
NULL_STICKER_ID = "simulated_file_id_for_null_sticker.jpg"
GROUP_LOGO_FILE_ID = "simulated_file_id_for_group_logo.jpg"
ALLOWED_GROUP_ID =  -1002850733237  # (এইটা Replace করো যখন গ্রুপ ID জানা যাবে)

# Initialize Flask App (Render always-on)
app = Flask(__name__)
@app.route('/')
def home():
    return "Bot is running!"

def run_flask():
    app.run(host="0.0.0.0", port=8080)

# Google Sheet Auth
def connect_sheet():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
    client = gspread.authorize(creds)
    sheet = client.open_by_key(GOOGLE_SHEET_ID).sheet1
    return sheet

sheet = connect_sheet()
user_request_log = {}

# Start Command
async def start(update: Update, context: CallbackContext):
    if update.effective_chat.type != "group":
        await context.bot.send_sticker(chat_id=update.effective_chat.id, sticker=NULL_STICKER_ID)
        return
    await update.message.reply_text("✅ Bot is ready to serve!")

# Language Prompt Every 2 Hours
async def send_language_prompt(context: CallbackContext):
    group_id = ALLOWED_GROUP_ID
    kb = InlineKeyboardMarkup.from_button(
        InlineKeyboardButton("🌐 Change Language", url=f"https://t.me/{context.bot.username}")
    )
    await context.bot.send_message(chat_id=group_id, text="🌐 Dɪᴅ Yᴏᴜ Kɴᴏᴡ ⁉️\nCʟɪᴄᴋ ʙᴇʟᴏᴡ ᴛᴏ ᴄʜᴀɴɢᴇ ʟᴀɴɢᴜᴀɢᴇ 👇", reply_markup=kb)

# Delete all group messages every 3 minutes
async def delete_messages(context: CallbackContext):
    group_id = ALLOWED_GROUP_ID
    async for message in context.bot.get_chat_history(group_id, limit=100):
        if not message.text or "language" not in message.text.lower():
            try:
                await context.bot.delete_message(chat_id=group_id, message_id=message.message_id)
            except:
                pass

# Main Movie Search Handler
async def handle_movie_request(update: Update, context: CallbackContext):
    user = update.effective_user
    chat = update.effective_chat

    if chat.type != "group":
        await context.bot.send_sticker(chat_id=chat.id, sticker=NULL_STICKER_ID)
        return

    if chat.username != OWNER_USERNAME and chat.id != ALLOWED_GROUP_ID:
        await update.message.reply_text("❌ This bot can only be added by the owner.")
        return

    now = datetime.utcnow()
    user_id = user.id
    if user_id not in user_request_log:
        user_request_log[user_id] = []

    # Request Limit: 2 movies per 24 hrs
    recent_requests = [t for t in user_request_log[user_id] if now - t < timedelta(hours=24)]
    if len(recent_requests) >= 2:
        await update.message.reply_text(f"Hi {user.first_name}, you’ve reached your daily limit (2 movies).\nGet Premium Access: {PREMIUM_CONTACT}")
        return

    movie_name = update.message.text.strip().lower()
    rows = sheet.get_all_records()

    for row in rows:
        sheet_movie = row['MoviesName'].strip().lower()
        release_date = datetime.strptime(row['Release Date'], "%Y-%m-%d")
        if movie_name == sheet_movie:
            if (now - release_date).days < 30:
                await update.message.reply_text(
                    f"Hello 👋 {user.first_name}\nI know you're in a hurry to download '{movie_name.title()}' "
                    f"but it's available only in our PREMIUM group.\n📥 Contact: {PREMIUM_CONTACT}\n🔗 Join: {PREMIUM_GROUP_LINK}"
                )
                return

            file_id = row['File ID']
            kb = InlineKeyboardMarkup([
                [InlineKeyboardButton("📥 480p", callback_data=f"{file_id}|480")],
                [InlineKeyboardButton("📥 720p", callback_data=f"{file_id}|720")],
                [InlineKeyboardButton("📥 1080p", callback_data=f"{file_id}|1080")],
            ])
            await update.message.reply_text(
                f"🎬 Movie Found: {movie_name.title()}\nOnly {user.first_name} can click this.",
                reply_markup=kb
            )
            user_request_log[user_id].append(now)
            return

    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("🌍 GOOGLE", url=f"https://www.google.com/search?q={movie_name}")],
        [InlineKeyboardButton("🎬 IMDB", url=f"https://www.imdb.com/find?q={movie_name}")],
        [InlineKeyboardButton("❓ HELP", callback_data="help")],
        [InlineKeyboardButton("👤 Contact", url=f"https://t.me/{PREMIUM_CONTACT}")]
    ])
    await update.message.reply_text(
        f"Hᴇʟʟᴏ 👋 {user.first_name}\nI Cᴏᴜʟᴅɴ'ᴛ 🔍 Fɪɴᴅ '{movie_name.title()}'\nClick the buttons below 👇",
        reply_markup=kb
    )

# Callback Button Handler
async def button_handler(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == "help":
        await query.edit_message_text("✅ Do: TYPE ONLY IN ENGLISH\n❌ DON'T: Avoid punctuation, repeat requests, unreleased movies")
        return

    file_id, quality = data.split("|")
    caption = (
        f"╭──[ミ★ {GROUP_NAME} ★彡]──╮\n"
        f"├• Tɪᴛʟᴇ : Unknown ({quality})\n"
        f"├• Exᴛᴇɴsɪᴏɴ : mkv\n"
        f"├• Sɪᴢᴇ : Variable\n"
        f"├• Jᴏɪɴ 《 Sʜᴀʀᴇ 》 Sᴜᴘᴘᴏʀᴛ\n"
        f"{OWNER_GROUP_LINK}\n"
        f"╰──────[ ✥ ]───────╯"
    )
    await context.bot.send_video(chat_id=query.from_user.id, video=file_id, caption=caption)

# Run Bot
def main():
    app_thread = threading.Thread(target=run_flask)
    app_thread.start()

    application = ApplicationBuilder().token(BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_movie_request))
    application.add_handler(CallbackQueryHandler(button_handler))

    # Jobs: language prompt & message cleanup
    job_queue = application.job_queue
    job_queue.run_repeating(send_language_prompt, interval=7200, first=10)
    job_queue.run_repeating(delete_messages, interval=180, first=60)

    application.run_polling()

if __name__ == "__main__":
    main()
