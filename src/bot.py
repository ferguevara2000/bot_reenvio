import asyncio

from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, MessageHandler, filters
from config.settings import TELEGRAM_TOKEN
from handlers.start import start
from handlers.menu import menu, handle_callback_query, handle_back
from actions.connect import connect, handle_user_message, cancel_process
from actions.chats import chats
from actions.redirection import redirection, handle_chat_ids

# Configuración del bot
def start_bot():

    # Crear la aplicación del bot
    application = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    # Agregar el comando /start
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("menu", menu))

    application.add_handler(CommandHandler("connect", connect))

    # Manejar los mensajes con los IDs source - destination (prioridad alta)
    application.add_handler(MessageHandler(filters.TEXT & filters.Regex(r'^\d+\s*-\s*\d+$'), handle_chat_ids))

    # Manejador genérico (prioridad baja)
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_user_message))

    application.add_handler(CommandHandler("chats", chats))  # Aquí se agrega el comando chats

    # Agregar el comando /redirection
    application.add_handler(CommandHandler("redirection", redirection))

    # Agregar los manejadores de callback con los patrones correctos
    application.add_handler(CallbackQueryHandler(handle_callback_query, pattern='^(connect|chats)$'))
    application.add_handler(CallbackQueryHandler(handle_back, pattern='^back$'))

    # Registrar el handler para el botón de cancelar
    application.add_handler(CallbackQueryHandler(cancel_process, pattern="^cancel$"))

    application.add_handler(CallbackQueryHandler(handle_callback_query))

    # Iniciar el bot
    print("El bot está ejecutándose...")
    application.run_polling()

def main():

    # Crear la aplicación del bot
    application = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    application.add_handler(CommandHandler("chats", chats))  # Aquí se agrega el comando chats
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("menu", menu))
    application.add_handler(CommandHandler("connect", connect))

    # Iniciar el bot
    print("El bot está ejecutándose...")
    application.run_polling()
