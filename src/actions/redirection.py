import os
import re
from numbers import Number

import requests
import aiohttp
from telethon import events, TelegramClient
from telegram import Update
from telegram.ext import ContextTypes
from src.config import settings  # Configuración con URL_API, API_KEY
from src.config.settings import API_ID, API_HASH
from src.clients.client_manager import get_or_create_client, event_handlers

# Diccionario para rastrear redirecciones por usuario
user_redirections = {}
# Diccionario para almacenar los clientes de Telethon activos por usuario
active_clients = {}
active_redirections = {}

async def start_redirection(user_id: int, redirection_id: str) -> None:
    # Obtener la redirección configurada para el usuario
    redirection = user_redirections[user_id].get(redirection_id)
    if not redirection or not redirection["source"] or not redirection["destination"]:
        raise ValueError("La redirección no está completamente configurada.")

    source = redirection["source"]
    destination = redirection["destination"]

    # Comprobar si ya hay un cliente activo para este usuario
    if user_id not in active_clients:
        # Crear cliente Telethon si no existe uno activo
        client = await get_or_create_client(user_id)
        await ensure_connected(client)
        active_clients[user_id] = client  # Guardar el cliente activo
    else:
        # Usar el cliente ya existente
        client = active_clients[user_id]

    # Registrar el evento de la redirección
    @client.on(events.NewMessage(chats=source))
    async def forward_message(event):
        try:
            await client.send_message(destination, event.message)
        except Exception as e:
            print(f"Error al redirigir mensaje: {str(e)}")
            return

    print(f"Redirección '{redirection_id}' iniciada automáticamente: {source} -> {destination}")

    # Guardar el callback asociado
    if user_id not in event_handlers:
        event_handlers[user_id] = {}
    event_handlers[user_id][redirection_id] = forward_message

    # Ejecutar la conexión del cliente sin desconectarlo inmediatamente
    await client.start()
    print(f"Cliente Telethon para {user_id} y redirección {redirection_id} está ahora activo.")


# Comando para manejar redirecciones (sin cambios)
async def redirection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    args = context.args

    if len(args) < 2:
        await update.message.reply_text(
            "Uso del comando:\n"
            "/redirection add [redireccionID]\n"
            "/redirection delete [redireccionID]"
        )
        return

    subcommand = args[0]  # El primer argumento será el subcomando (add o delete)
    redirection_id = args[1]  # El segundo argumento será el ID de la redirección

    if subcommand == "add":
        # Lógica para agregar una redirección
        if user_id in user_redirections and redirection_id in user_redirections[user_id]:
            await update.message.reply_text(
                f"La redirección '{redirection_id}' ya está configurada. Usa otro ID."
            )
            return

        if user_id not in user_redirections:
            user_redirections[user_id] = {}

        user_redirections[user_id][redirection_id] = {"source": None, "destination": None}
        await update.message.reply_text(
            f"Redirección '{redirection_id}' creada. Ahora envía los chats en el formato:\n"
            "`source - destination`"
        )

        await insert_redirection_to_db(user_id, redirection_id)

    elif subcommand == "delete":
        # Eliminar la redirección de la base de datos
        result = await delete_redirection(user_id, redirection_id)

        if result == 204:
            await update.message.reply_text(
                f"La redirección '{redirection_id}' ha sido eliminada con éxito."
            )
            if user_id in user_redirections and redirection_id in user_redirections[user_id]:
                del user_redirections[user_id][redirection_id]
            else:
                print(f"El usuario {user_id} o la redirección {redirection_id} no existen.")

        else:
            await update.message.reply_text(
                f"No se encontro la redirección '{redirection_id}'."
            )

    else:
        # Subcomando inválido
        await update.message.reply_text(
            "Subcomando no reconocido. Usa:\n"
            "/redirection add [redireccionID]\n"
            "/redirection delete [redireccionID]"
        )



# Inserción de redirecciones en la base de datos (sin cambios)
async def insert_redirection_to_db(user_id: int, redirection_id: str) -> None:
    url = f"{settings.URL_API}/rpc/insert_redirection"
    payload = {
        "user_id": str(user_id),
        "redirection_id": redirection_id
    }
    headers = {
        "apikey": settings.API_KEY,
        "Authorization": f"Bearer {settings.API_KEY}",
        "Content-Type": "application/json"
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload, headers=headers) as response:
                if response.status == 201:
                    print(f"Redirección {redirection_id} guardada correctamente en la base de datos.")
                else:
                    print(f"Error al guardar redirección: {response.status}")
    except aiohttp.ClientError as e:
        print(f"Error al hacer la solicitud a la API: {str(e)}")


async def handle_chat_ids(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Maneja los mensajes en el formato 'source - destination' para configurar los chats en una redirección.
    """
    user_id = update.effective_user.id
    message_text = update.message.text.strip()

    # Validar el formato 'source - destination' o 'source-destination'
    try:
        match = re.match(r"^(\d+)\s*-\s*(\d+)$", message_text)
        if not match:
            raise ValueError("Formato inválido")

        source_chat_id, destination_chat_id = map(int, match.groups())
    except ValueError:
        await update.message.reply_text(
            "Formato inválido. Usa el formato:\n`source - destination`"
        )
        return

    # Buscar redirección incompleta
    user_redirection = user_redirections.get(user_id)
    if not user_redirection:
        await update.message.reply_text(
            "No tienes ninguna redirección en proceso. Usa el comando /redirection para comenzar."
        )
        return

    # Buscar redirección incompleta
    user_redirection = user_redirections.get(user_id)
    if not user_redirection:
        await update.message.reply_text(
            "No tienes ninguna redirección en proceso. Usa el comando /redirection para comenzar."
        )
        return

    # Encontrar la redirección activa
    active_redirection = None
    for redirection_id, data in user_redirection.items():
        if data["source"] is None or data["destination"] is None:
            active_redirection = redirection_id
            break

    if not active_redirection:
        await update.message.reply_text(
            "No hay redirecciones pendientes de configuración. Usa el comando /redirection para agregar una nueva."
        )
        return

    # Completar la configuración de la redirección
    user_redirections[user_id][active_redirection]["source"] = source_chat_id
    user_redirections[user_id][active_redirection]["destination"] = destination_chat_id

    # Guardar en la base de datos
    await insert_chat_redirection(user_id, active_redirection, source_chat_id, "source")
    await insert_chat_redirection(user_id, active_redirection, destination_chat_id, "destination")

    # Iniciar la redirección
    await start_redirection(user_id, active_redirection)

    await update.message.reply_text(
        f"Redirección '{active_redirection}' configurada: \n"
        f"Source: {source_chat_id} \n"
        f"Destination: {destination_chat_id}"
    )

async def insert_chat_redirection(user_id: int, redirection_id: str, chat_id: int, role: str) -> None:
    """
    Actualiza una redirección existente en la base de datos con los chats de origen y destino.
    """
    url = f"{settings.URL_API}/rpc/insert_chats_redirection"
    payload = {
        "p_chat_id": str(chat_id),
        "p_role": role,
        "p_user_id": str(user_id),
        "p_redirection_id": redirection_id,
    }

    print(payload)
    headers = {
        "apikey": settings.API_KEY,
        "Authorization": f"Bearer {settings.API_KEY}",
        "Content-Type": "application/json"
    }

    try:
        response = requests.post(url, json=payload, headers=headers)
        if response.status_code == 204:
            print(f"Redirección {redirection_id} guardada correctamente en la base de datos.")
        else:
            print(f"Error al actualizar redirección: {response.status_code}")
    except requests.exceptions.RequestException as e:
        print(f"Error al hacer la solicitud a la API: {str(e)}")

async def delete_redirection(user_id: int, redirection_id: str) -> Number:
    """
    Elimina una redirección existente de la base de datos.
    """
    # Verificar si la redirección existe en la base de datos antes de intentar eliminarla
    url = f"{settings.URL_API}/rpc/delete_redirection"
    payload = {
        "redirection_id_input": redirection_id,
        "user_id_input": str(user_id),
    }
    print(payload)
    headers = {
        "apikey": settings.API_KEY,
        "Authorization": f"Bearer {settings.API_KEY}",
        "Content-Type": "application/json"
    }

    try:
        source = await get_chat_id_from_api(user_id, redirection_id)
        if source is not None:
            await stop_redirection(user_id, redirection_id, str(source))
            print(f"Redirección {redirection_id} detenida para el usuario {user_id}")
        else:
            print(f'No se encontro la redireccion {redirection_id} para el usuario {user_id}')

        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload, headers=headers) as response:
                if response.status == 204:
                    print(f"Redirección '{redirection_id}' eliminada correctamente de la base de datos.")

                    return 204
                elif response.status == 400:
                    print(f"No se encontro la redireccion {redirection_id} asignada al usuario {user_id}")
                    return 400
                else:
                    print(f"Error al eliminar redirección '{redirection_id}': {response.status}")
    except aiohttp.ClientError as e:
        print(f"Error al hacer la solicitud a la API: {str(e)}")



async def ensure_connected(client: TelegramClient) -> None:
    if not client.is_connected():
        try:
            await client.connect()
        except Exception as e:
            raise Exception(f"Error al conectar el cliente: {str(e)}")


async def get_chat_id_from_api(user_id: int, redirection_id: str) -> str | None:
    """
    Consulta el chat_id de la redirección a través de la API.

    :param user_id: ID del usuario.
    :param redirection_id: ID de la redirección.
    :return: ID del chat fuente asociado a la redirección.
    """
    url = f"{settings.URL_API}/rpc/get_chat_redirection_by_user_and_id"
    payload = {
        "redirection_id_input": redirection_id,
        "user_id_input": str(user_id),
    }
    headers = {
        "apikey": settings.API_KEY,
        "Authorization": f"Bearer {settings.API_KEY}",
        "Content-Type": "application/json"
    }

    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(url, json=payload, headers=headers) as response:
                if response.status != 200:
                    return None

                # Leer directamente el texto de la respuesta
                chat_id = await response.text()

                return chat_id  # Convertir a entero antes de devolver

        except Exception as e:
            raise Exception(f"Error al consultar el chat_id desde la API: {e}")


async def stop_redirection(user_id: int, redirection_id: str, source: str) -> None:
    """
    Detiene una redirección activa para el usuario y elimina su evento asociado.

    :param source:
    :param user_id: ID del usuario que solicita detener la redirección.
    :param redirection_id: ID de la redirección a detener.
    """
    try:

        # Obtener o crear el cliente de Telegram
        client = await get_or_create_client(user_id)

        # Recuperar el callback almacenado
        callback = event_handlers.get(user_id, {}).get(redirection_id)
        if callback is None:
            print(f"No se encontró un callback para la redirección '{redirection_id}' del usuario {user_id}.")
            return

        # Eliminar el evento asociado a la redirección
        client.remove_event_handler(callback, event=events.NewMessage(chats=source))
        print(f"Redirección '{redirection_id}' detenida para el usuario {user_id}.")
    except Exception as e:
        print(f"Error al detener la redirección '{redirection_id}' para el usuario {user_id}: {e}")

