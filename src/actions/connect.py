import os
import re
import requests
import telethon
import phonenumbers
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes
from telethon.sync import TelegramClient
from datetime import datetime, timedelta
from src.config.settings import API_ID, API_HASH, URL_API, API_KEY, SESSION_PATH
from src.clients.client_manager import get_or_create_client

# Diccionario para rastrear el estado de autenticación de cada usuario
user_states = {}

# Variable global para el cliente de Telethon
telethon_client = None


# Función para verificar si la sesión está activa y es completa
async def is_session_complete(user_id: int) -> bool:
    session_file = os.path.join(SESSION_PATH, f"user_{user_id}.session")

    # Verificar si el archivo de sesión existe
    if not os.path.exists(session_file):
        return False

    # Crear cliente de Telethon para verificar estado de autenticación
    global telethon_client
    telethon_client = await get_or_create_client(user_id)
    await ensure_connected(telethon_client)

    # Verificar si el usuario está autorizado (autenticado correctamente)
    if await telethon_client.is_user_authorized():
        return True
    return False


async def ensure_connected(client: TelegramClient) -> None:
    if not client.is_connected():
        try:
            await client.connect()
        except Exception as e:
            await client.disconnect()
            raise Exception(f"Error al conectar el cliente: {str(e)}")


# Función para manejar la acción de "Conectar"
async def connect(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id

    # Verificar si la sesión ya está completa
    if await is_session_complete(user_id):
        await update.message.reply_text(
            "Ya existe una conexión activa para tu cuenta. No es necesario volver a conectarse. 🎉"
        )
        return

    # Iniciar el proceso de autenticación si no hay sesión activa
    user_states[user_id] = {"stage": "phone"}  # Iniciar en la etapa de teléfono

    # Solicitar el número de teléfono
    phone_message = "Por favor, introduce tu número de teléfono en formato internacional (por ejemplo, +123456789). Asegúrate de incluir el símbolo '+' seguido del código de tu país y tu número completo. Si no recuerdas tu número, puedes consultarlo en Telegram: Settings > Phone Number."
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
    telethon_client = await get_or_create_client(user_id)

    try:
        # Asegurar conexión antes de cualquier operación
        await ensure_connected(telethon_client)

        # Paso 1: Solicitar teléfono
        if state["stage"] == "phone":
            phone = update.message.text
            # Validar si el número tiene un formato válido
            try:
                parsed_phone = phonenumbers.parse(phone, None)  # Validación sin un país predeterminado
                if not phonenumbers.is_valid_number(parsed_phone):
                    raise ValueError("Número no válido")

                # Guardar el teléfono validado
                state["phone"] = phone
                # Solicitar el código de verificación
                await update.message.reply_text(
                    "Espera unos momentos mientras te llega el código de verificación. \n"                    
                    "Una vez recibido, introdúcelo con el prefijo 'aa' (por ejemplo, aa12345).\n\n"
                    "Telegram no permite compartir este código directamente. Por seguridad, siempre agrégale el prefijo indicado antes de enviarlo.",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("Cancelar Conexión", callback_data="cancel")]
                    ])
                )

                # Solicitar código y guardar hash
                result = await telethon_client.send_code_request(phone)
                state["phone_code_hash"] = result.phone_code_hash

                # Cambiar estado
                state["stage"] = "code"

            except Exception as e:
                await update.message.reply_text(
                    "El número de teléfono ingresado no es válido. Por favor, introduce un número en formato internacional (+123456789)."
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

            # Intentar autenticar usando el código y el hash
            try:
                await telethon_client.sign_in(phone, code_without_prefix, phone_code_hash=phone_code_hash)

                # Cambiar estado
                state["stage"] = "done"
                await update.message.reply_text("¡Conexión exitosa! 🎉")

                # Mensaje explicativo sobre la notificación de inicio de sesión
                await update.message.reply_text(
                    "Es posible que recibas una notificación de inicio de sesión desde un nuevo dispositivo. Esto es normal y garantiza la seguridad de tu cuenta. "
                    "El bot solo utilizará esta conexión para los propósitos indicados y no accederá a tus mensajes personales sin tu autorización. 😊"
                )

                # Crear o actualizar usuario en la API
                try:
                    user_info = update.effective_user
                    username = user_info.username or "SinUsername"
                    name = user_info.full_name or "SinNombre"

                    # Llamada a la función para persistir datos
                    api_response = await create_or_update_user_in_api(
                        user_id=user_id,
                        username=username,
                        name=name,
                        phone=phone
                    )
                    print(api_response)
                except Exception as e:
                    await update.message.reply_text(f"Error al sincronizar con la API: {str(e)}")
                del user_states[user_id]

                # Cerrar cliente
                await telethon_client.disconnect()

            except telethon.errors.SessionPasswordNeededError:
                # Si se requiere contraseña 2FA, pedirla al usuario
                state["stage"] = "password"
                await update.message.reply_text("Tu cuenta tiene habilitada la autenticación de dos factores. Por favor, introduce tu contraseña:")

        # Paso 3: Verificar contraseña 2FA
        elif state["stage"] == "password":
            password = update.message.text

            try:
                # Intentar iniciar sesión con la contraseña 2FA
                await telethon_client.sign_in(password=password)

                # Cambiar estado
                state["stage"] = "done"
                await update.message.reply_text("¡Conexión exitosa con autenticación de dos factores! 🎉")

                # Crear o actualizar usuario en la API
                user_info = update.effective_user
                username = user_info.username or "SinUsername"
                name = user_info.full_name or "SinNombre"

                api_response = await create_or_update_user_in_api(
                    user_id=user_id,
                    username=username,
                    name=name,
                    phone=state["phone"]
                )
                print(api_response)
                del user_states[user_id]

                # Cerrar cliente
                await telethon_client.disconnect()

            except Exception as e:
                await telethon_client.disconnect()
                await update.message.reply_text(f"Error al autenticar con 2FA: {str(e)}")
                del user_states[user_id]

    except Exception as e:
        await telethon_client.disconnect()
        await update.message.reply_text(f"Error: {str(e)}")
        del user_states[user_id]


async def create_or_update_user_in_api(user_id, username, name, phone):
    """
    Función para crear o actualizar un usuario en la API.
    """
    today = datetime.now()
    next_day = today + timedelta(days=1)

    # Crear el payload de datos
    user_data = {
        "id": user_id,
        "username": username,
        "name": name,
        "phonenumber": phone,
        "lastpaymentdate": today.isoformat(),  # Convertir a formato ISO 8601
        "paymentdate": next_day.isoformat(),  # Convertir a formato ISO 8601
        "createat": today.isoformat()
    }

    headers = {
        "apiKey": API_KEY,
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }

    # Paso 1: Buscar usuario en la API
    url_get_user = URL_API + "rpc/get_user_by_id"
    payload = {"user_id_input": user_id}

    response = requests.post(url_get_user, headers=headers, json=payload)

    if response.status_code == 200:
        data = response.json()
        if "error" in data and data["status_code"] == 404:
            # Usuario no encontrado, proceder a registrarlo
            url_create_user = URL_API + "rpc/create_user"
            payload_create = {"user_data": user_data}  # Enviar los datos con la clave 'user_data'

            response_create = requests.post(url_create_user, headers=headers, json=payload_create)

            if response_create.status_code == 200:
                # Obtener el contenido del cuerpo de la respuesta
                json_response = response_create.json()

                # Verificar que el cuerpo de la respuesta tenga el valor 201
                if json_response == 201:
                    return f"Usuario creado con exito {json_response}"
                else:
                    return f"Error: La respuesta no contiene el código esperado (201). Respuesta: {json_response}"
            else:
                return f"Error al registrar el usuario. Status: {response_create.status_code}, Detalles: {response_create.text}"
        else:
            # Usuario encontrado, devolver datos
            return {"data": data, "status_code": 200}

    else:
        return {"error": f"Error en la API: {response.text}", "status_code": response.status_code}

async def cancel_process(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    # Verificar si el cliente de Telethon está activo
    if user_id in user_states:
        try:
            # Obtener el cliente de Telethon para el usuario
            telethon_client = await get_or_create_client(user_id)

            # Cerrar el cliente de Telethon
            await telethon_client.disconnect()

            # Limpiar cualquier estado relacionado con este usuario
            del user_states[user_id]

            # Verificar si update.message no es None antes de intentar usarlo
            if update.message:
                await update.message.reply_text(
                    "La operación ha sido cancelada. 👋")
            else:
                # Si update.message es None, manejar de otra manera (por ejemplo, no hay mensaje)
                await update.effective_user.send_message(
                    "La operación ha sido cancelada. 👋")

        except Exception as e:
            # Manejar cualquier error que ocurra al intentar cerrar el cliente
            if update.message:
                await update.message.reply_text(f"Hubo un error al cerrar la sesión de Telethon: {e}")
            else:
                await update.effective_user.send_message(f"Hubo un error al cerrar la sesión de Telethon: {e}")
    else:
        # Si no hay sesión activa, enviar un mensaje adecuado
        if update.message:
            await update.message.reply_text("No hay una sesión activa para cerrar.")
        else:
            await update.effective_user.send_message("No hay una sesión activa para cerrar.")
