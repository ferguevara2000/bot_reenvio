from telegram.ext import Application, CommandHandler, MessageHandler, filters
from src.config.settings import TELEGRAM_TOKEN
from src.handlers.error_handler import error_handler

def start_bot():
    app = Application.builder().token(TELEGRAM_TOKEN).build()

    # Registro de comandos
    app.add_handler(CommandHandler("start", help_command))


    # Manejo de errores
    app.add_error_handler(error_handler)

    # Inicio del bot
    print("Bot iniciado...")
    app.run_polling()
