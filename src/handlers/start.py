from telegram import Update
from telegram.ext import ContextTypes
from src.handlers.menu import show_menu

# Función para manejar el comando /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    # Mensaje de bienvenida
    welcome_message = (
        "¡Hola! Bienvenido. 😊\n"
        "Si es la primera vez que usas el bot, selecciona primero la opción de Conectar.\n"
        "Para comenzar, selecciona una opción en el menú.\n"
        "Ahí encontrarás información detallada sobre cada comando disponible."
    )

    # Generar el menú
    reply_markup = await show_menu()

    # Enviar mensaje con el menú
    await update.message.reply_text(welcome_message, reply_markup=reply_markup)