from telegram import Update
from telegram.ext import ContextTypes
from telethon.sync import TelegramClient
from telethon.tl.types import Chat, User, Channel
from src.config.settings import API_ID, API_HASH
from src.actions.connect import get_telethon_client, ensure_connected
import html  # Importa la librería para escapear caracteres especiales en HTML


async def chats(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id

    # Mensaje inicial para informar al usuario
    waiting_message = await update.message.reply_text(
        "🔄 Obteniendo chats... Por favor, espera.") if update.message else None

    try:
        # Obtener el cliente Telethon
        telethon_client = await get_telethon_client(user_id)
        await ensure_connected(telethon_client)

        # Obtener los chats
        dialogs = await telethon_client.get_dialogs()

        # Listas para clasificar los chats
        user_chats = []
        bot_chats = []
        channel_chats = []
        group_chats = []

        for dialog in dialogs:
            entity = dialog.entity
            chat_name = ""
            chat_id = entity.id

            if isinstance(entity, User):
                # Usuario
                if entity.bot:
                    bot_chats.append(f"{entity.first_name or ''} | {chat_id}")
                else:
                    user_chats.append(
                        f"{entity.first_name or ''} {entity.last_name or ''} | {chat_id}"
                    )
            elif isinstance(entity, Chat):
                # Grupo
                group_chats.append(f"{entity.title or ''} | {chat_id}")
            elif isinstance(entity, Channel):
                # Canal
                channel_chats.append(f"{entity.title or ''} | {chat_id}")

        # Enviar mensajes separados por categoría
        if user_chats:
            await send_message_by_category(update, "👤 Usuarios (Username/Name | ID)", user_chats)
        if bot_chats:
            await send_message_by_category(update, "🤖 Bots (Bot Username | ID)", bot_chats)
        if channel_chats:
            await send_message_by_category(update, "📡 Canales (Channel Title | ID)", channel_chats)
        if group_chats:
            await send_message_by_category(update, "👥 Grupos (Group Title | ID)", group_chats)

    except Exception as e:
        if update.message:
            await update.message.reply_text(f"❌ Error: {str(e)}")
    finally:
        # Eliminar el mensaje de "obteniendo chats" una vez completado
        if waiting_message:
            await waiting_message.delete()


async def send_message_by_category(update, title, chat_list):
    """
    Envía un mensaje con la información de una categoría específica.
    Si la lista es demasiado grande, se divide en fragmentos.
    """
    MAX_MESSAGE_LENGTH = 4096
    message = f"<b>{title}</b>\n\n" + "\n".join([html.escape(chat) for chat in chat_list])
    fragments = split_message(message, MAX_MESSAGE_LENGTH)

    # Verificar si el update tiene un mensaje y enviarlo
    if update.message:
        for fragment in fragments:
            await update.message.reply_text(fragment, parse_mode='HTML')


def split_message(message, max_length):
    """
    Divide un mensaje largo en fragmentos más pequeños.
    """
    fragments = []
    while len(message) > max_length:
        # Buscar el último salto de línea dentro del límite
        split_index = message[:max_length].rfind("\n")
        if split_index == -1:  # Si no hay salto de línea, dividir en el límite
            split_index = max_length
        fragments.append(message[:split_index])
        message = message[split_index:].strip()
    fragments.append(message)  # Agregar el último fragmento
    return fragments
