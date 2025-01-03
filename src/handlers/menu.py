from telegram import InlineKeyboardMarkup, InlineKeyboardButton, Update
from telegram.ext import ContextTypes, CallbackQueryHandler
from src.actions.connect import connect
from src.actions.chats import chats


# Función para generar el menú
async def show_menu() -> InlineKeyboardMarkup:
    # Menú de opciones con botones
    menu = [
        [InlineKeyboardButton("Conectar", callback_data="connect")],
        [InlineKeyboardButton("Chats", callback_data="chats")]
    ]
    return InlineKeyboardMarkup(menu)


# Función para mostrar el menú
async def menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    # Mensaje para mostrar el menú
    menu_message = "Aquí tienes el menú principal:"

    # Generar el menú
    reply_markup = await show_menu()

    # Verificar si hay un mensaje o callback_query para responder
    if update.message:
        await update.message.reply_text(menu_message, reply_markup=reply_markup)
    elif update.callback_query:
        await update.callback_query.message.edit_text(menu_message, reply_markup=reply_markup)


# Función para manejar la acción del botón "Conectar"
async def handle_callback_query(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query

    # Responder al callback query para confirmar la acción
    await query.answer()

    if query.data == "connect":
        # Simular el envío del comando /connect
        await connect(update, context)  # Llamar a la función /connect
        # Mostrar mensaje con un botón "Volver" al menú
        await show_back_button(update, context, "Conexión establecida")
    elif query.data == "chats":
        # Aquí solo mostramos un mensaje sin llamar a la función chats
        await show_message_chats(update, context)


# Función para mostrar un mensaje cuando se selecciona "Chats"
async def show_message_chats(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = "Has seleccionado la opción de *Chats*. Aquí iría la lógica para obtener los chats."

    # Crear el botón "Volver" que llevará al menú principal
    keyboard = [
        [InlineKeyboardButton("Volver", callback_data="back")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    # Enviar el mensaje con la acción seleccionada y el botón "Volver"
    await update.callback_query.message.reply_text(  # Usamos query.message para responder al callback
        message,
        reply_markup=reply_markup,
        parse_mode='Markdown'  # Esto permite que el texto se muestre con formato en Markdown
    )


# Función para mostrar un mensaje con el botón "Volver" al menú
async def show_back_button(update: Update, context: ContextTypes.DEFAULT_TYPE, message: str) -> None:
    # Crear el botón "Volver" que llevará al menú principal
    keyboard = [
        [InlineKeyboardButton("Volver", callback_data="back")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    # Enviar el mensaje con la acción seleccionada y el botón "Volver"
    await update.callback_query.message.reply_text(  # Usamos query.message para responder al callback
        f"{message}\n\nHaz clic en 'Volver' para regresar al menú principal.",
        reply_markup=reply_markup
    )


# Función para manejar el botón "Volver"
async def handle_back(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query

    # Responder al callback query para confirmar la acción
    await query.answer()

    # Mostrar el menú principal nuevamente
    await menu(update, context)

# Agregar los manejadores para los botones
def setup_handlers(dp):
    dp.add_handler(CallbackQueryHandler(handle_callback_query, pattern='^(connect|chats)$'))
    dp.add_handler(CallbackQueryHandler(handle_back, pattern='^back$'))