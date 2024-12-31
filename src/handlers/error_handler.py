import logging
from telegram import Update
from telegram.ext import ContextTypes

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.error(msg="Exception while handling an update:", exc_info=context.error)
    await update.message.reply_text("Ocurrió un error. Por favor, inténtalo de nuevo.")
