from telegram import Update
from telegram.ext import ContextTypes
from src.config.settings import ALLOWED_USERS

async def is_authenticated(update: Update, context: ContextTypes.DEFAULT_TYPE, next_handler):
    user_id = str(update.effective_user.id)
    if user_id not in ALLOWED_USERS:
        await update.message.reply_text("No tienes permiso para usar este bot.")
        return
    await next_handler(update, context)
