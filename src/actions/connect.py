import re

from telegram import Update
from telegram.ext import ContextTypes
from telethon.sync import TelegramClient
from telethon.errors import SessionPasswordNeededError, AuthRestartError
from telethon import events
from src.config.settings import API_ID, API_HASH

# Diccionario para rastrear el estado de autenticación de cada usuario
user_states = {}

# Función para crear un cliente Telethon para cada usuario
async def get_telethon_client(user_id: int) -> TelegramClient:
    session_name = f"sessions/user_{user_id}"
    client = TelegramClient(session_name, API_ID, API_HASH)
    if not client.is_connected():
        try:
            await client.connect()
        except Exception as e:
            raise Exception(f"Error al conectar el cliente: {str(e)}")
    return client


async def request_phone_code(client, phone):
    result = await client.send_code_request(phone)
    return result.phone_code_hash


async def ensure_connected(client: TelegramClient) -> None:
    if not client.is_connected():
        try:
            await client.connect()
        except Exception as e:
            raise Exception(f"Error al conectar el cliente: {str(e)}")


# Función para manejar la acción de "Conectar"
async def connect(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    user_states[user_id] = {"stage": "phone"}  # Iniciar en la etapa de teléfono

    # Solicitar el número de teléfono
    phone_message = "Por favor, introduce tu número de teléfono en formato internacional (+123456789):"
    if update.message:  # Si es un mensaje de texto directo
        await update.message.reply_text(phone_message)
    elif update.callback_query:  # Si es un callback query (por ejemplo, clic en un botón)
        await update.callback_query.answer()  # Responder al callback para evitar errores en Telegram
        await update.callback_query.message.reply_text(phone_message)


# Función para manejar mensajes del usuario
async def handle_user_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    # Verificar si el mensaje corresponde al formato de chat IDs
    if re.match(r'^\d+ - \d+$', update.message.text):
        return  # Ignorar, ya que será manejado por handle_chat_ids

    user_id = update.effective_user.id

    # Verificar si el usuario ha iniciado el proceso
    if user_id not in user_states:
        await update.message.reply_text("Usa /connect para comenzar.")
        return

    state = user_states[user_id]
    telethon_client = await get_telethon_client(user_id)

    try:
        # Asegurar conexión antes de cualquier operación
        await ensure_connected(telethon_client)

        # Paso 1: Solicitar teléfono
        if state["stage"] == "phone":
            phone = update.message.text
            state["phone"] = phone

            # Solicitar código y guardar hash
            result = await telethon_client.send_code_request(phone)
            state["phone_code_hash"] = result.phone_code_hash

            # Cambiar estado
            state["stage"] = "code"
            await update.message.reply_text(
                "Introduce el código recibido en Telegram, con el prefijo 'aa' (por ejemplo, aa12345):"
            )

        # Paso 2: Verificar código
        elif state["stage"] == "code":
            code = "aa" + update.message.text

            # Verificar que el código comience con 'aa'
            if not code.startswith("aa"):
                await update.message.reply_text("Por favor, agrega el prefijo 'aa' al código.")
                return

            # Eliminar el prefijo 'aa' y procesar el código
            code_without_prefix = code[2:]

            phone = state["phone"]
            phone_code_hash = state["phone_code_hash"]

            # Autenticar usando código y hash
            await telethon_client.sign_in(phone, code_without_prefix, phone_code_hash=phone_code_hash)

            # Cambiar estado
            state["stage"] = "done"
            await update.message.reply_text("¡Conexión exitosa! 🎉")
            del user_states[user_id]

            # Cerrar cliente
            await telethon_client.disconnect()

    except Exception as e:
        await update.message.reply_text(f"Error: {str(e)}")
        del user_states[user_id]

