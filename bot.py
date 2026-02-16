import logging
import random
import string
import asyncio

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters
)
from telegram.constants import ParseMode

# ================= CONFIG =================
BOT_TOKEN = "YOUR_BOT_TOKEN"
BOT_USERNAME = "preview2Bot" # Change your bot username without @
CHANNEL_ID = -1003454021940        # private storage channel
DELETE_AFTER = 300                        # 5 minutes
# =========================================

# In-memory database (link -> file info)
file_db = {}

# Logging
logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s",
    level=logging.INFO
)

# Generate random link code
def generate_code(length=8):
    chars = string.ascii_letters + string.digits
    return "".join(random.choice(chars) for _ in range(length))

# ================= /START =================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user

    # If user opened a shared link
    if context.args:
        code = context.args[0]

        if code not in file_db:
            await update.message.reply_text("❌ Invalid or expired link.")
            return

        data = file_db[code]
        chat_id = update.effective_chat.id

        await update.message.reply_text("⏳ Fetching your file...")

        # Send file to user
        if data["type"] == "photo":
            sent = await update.message.reply_photo(
                data["file_id"], caption=data["caption"]
            )
        elif data["type"] == "video":
            sent = await update.message.reply_video(
                data["file_id"], caption=data["caption"]
            )
        elif data["type"] == "audio":
            sent = await update.message.reply_audio(
                data["file_id"], caption=data["caption"]
            )
        else:
            sent = await update.message.reply_document(
                data["file_id"], caption=data["caption"]
            )

        # Warning message
        await update.message.reply_text(
            "⚠️ <b>SECURITY NOTICE</b>\n\n"
            "This file will be automatically deleted from your chat in <b>5 minutes</b>.\n"
            "Please download or save it immediately.",
            parse_mode=ParseMode.HTML
        )

        # Start auto-delete ONLY for this user
        asyncio.create_task(
            auto_delete(context, chat_id, sent.message_id)
        )
        return

    # Normal /start
    await update.message.reply_text(
        f"👋 <b> Hello {user.first_name}! This Is Premium Preview Bot</b>\n\n"
        "• Upload any video, document, image or audio ⬇️",
        parse_mode=ParseMode.HTML
    )

# ================= FILE UPLOAD =================
async def handle_upload(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message

    if not (msg.photo or msg.video or msg.document or msg.audio):
        return

    status = await msg.reply_text("⏳ Uploading & securing your file...")

    # Forward file to private channel (storage)
    forwarded = await msg.forward(chat_id=CHANNEL_ID)

    # Detect file from forwarded message
    if forwarded.photo:
        file_id = forwarded.photo[-1].file_id
        ftype = "photo"
    elif forwarded.video:
        file_id = forwarded.video.file_id
        ftype = "video"
    elif forwarded.audio:
        file_id = forwarded.audio.file_id
        ftype = "audio"
    else:
        file_id = forwarded.document.file_id
        ftype = "document"

    code = generate_code()

    # Save file info (DO NOT DELETE — unlimited access)
    file_db[code] = {
        "file_id": file_id,
        "type": ftype,
        "caption": forwarded.caption
    }

    link = f"https://t.me/{BOT_USERNAME}?start={code}"

    await status.edit_text(
        f"✅ <b>Secure Link Generated</b>\n\n"
        f"🔗 <b>Private Link:</b>\n"
        f"{link}",
        parse_mode=ParseMode.HTML
    )

# ================= AUTO DELETE =================
async def auto_delete(context, chat_id, message_id):
    await asyncio.sleep(DELETE_AFTER)

    try:
        await context.bot.delete_message(
            chat_id=chat_id,
            message_id=message_id
        )
    except:
        pass

# ================= MAIN =================
def main():
    app = (
        Application.builder()
        .token(BOT_TOKEN)
        .job_queue(None)   # prevents timezone / APScheduler errors
        .build()
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(
        MessageHandler(
            filters.PHOTO | filters.VIDEO | filters.AUDIO | filters.Document.ALL,
            handle_upload
        )
    )

    print("✅ UR File Sharing Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()
