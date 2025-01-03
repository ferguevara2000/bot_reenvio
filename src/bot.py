from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, MessageHandler, filters
from src.config.settings import TELEGRAM_TOKEN
from src.handlers.start import start
from src.handlers.menu import menu, handle_callback_query, handle_back
from src.actions.connect import connect, handle_user_message
from src.actions.chats import chats

# Configuración del bot
def start_bot():
    # Crear la aplicación del bot
    application = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    # Agregar el comando /start
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("menu", menu))

    application.add_handler(CommandHandler("connect", connect))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_user_message))

    application.add_handler(CommandHandler("chats", chats))  # Aquí se agrega el comando chats

    # Agregar los manejadores de callback con los patrones correctos
    application.add_handler(CallbackQueryHandler(handle_callback_query, pattern='^(connect|chats)$'))
    application.add_handler(CallbackQueryHandler(handle_back, pattern='^back$'))

    application.add_handler(CallbackQueryHandler(handle_callback_query))

    # Iniciar el bot
    print("El bot está ejecutándose...")
    application.run_polling()
