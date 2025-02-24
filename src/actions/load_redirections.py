# src/main.py
import time
import aiohttp
from telethon import events
from src.clients.client_manager import get_or_create_client, event_handlers
from src.config import settings  # Configuración con URL_API, API_KEY

user_redirections = {}
active_redirections = {}

async def bot_startup() -> None:
    print("Cargando redirecciones existentes...")
    await load_all_redirections_from_db()
    print("Redirecciones cargadas y configuradas.")

async def load_all_redirections_from_db() -> None:
    url = f"{settings.URL_API}/rpc/get_all_redirections"
    headers = {
        "apikey": settings.API_KEY,
        "Authorization": f"Bearer {settings.API_KEY}",
        "Content-Type": "application/json"
    }

    retries = 3
    while retries > 0:
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, headers=headers) as response:
                    if response.status == 200:
                        redirections = await response.json()
                        for redirection in redirections:
                            user_id = int(redirection["user_id"])
                            redirection_id = redirection["redirection_id"]
                            source_chat_id = int(redirection["source_chat_id"])
                            destination_chat_id = int(redirection["destination_chat_id"])

                            if user_id not in user_redirections:
                                user_redirections[user_id] = {}
                            user_redirections[user_id][redirection_id] = {
                                "source": source_chat_id,
                                "destination": destination_chat_id
                            }

                            await start_redirection(user_id, redirection_id)
                        break
                    else:
                        print(f"Error al cargar redirecciones: {response.status}")
                        retries -= 1
                        time.sleep(1)
        except aiohttp.ClientError as e:
            print(f"Error al hacer la solicitud a la API: {str(e)}. Intentando de nuevo...")
            retries -= 1
            time.sleep(1)
    if retries == 0:
        print("No se pudo cargar la información después de varios intentos.")

async def start_redirection(user_id: int, redirection_id: str) -> None:
    redirection = user_redirections[user_id].get(redirection_id)
    if not redirection or not redirection["source"] or not redirection["destination"]:
        raise ValueError("La redirección no está completamente configurada.")

    source = redirection["source"]
    destination = redirection["destination"]

    # Usamos la función para obtener o crear el cliente
    client = await get_or_create_client(user_id)

    # Comprobar si la redirección ya está activa
    if user_id in active_redirections and redirection_id in active_redirections[user_id]:
        print(f"Redirección {redirection_id} ya está activa para el usuario {user_id}: {source} -> {destination}")
        return

    if user_id not in active_redirections:
        active_redirections[user_id] = {}

    active_redirections[user_id][redirection_id] = {"source": source, "destination": destination}

    @client.on(events.NewMessage(chats=source))
    async def forward_message(event):
        try:
            # Enviar el mensaje al destino
            message = await client.send_message(destination, event.message)
            # Guardar el ID del mensaje clonado para ediciones futuras
            active_redirections[event.message.id] = message.id
        except Exception as e:
            print(f"Error al redirigir mensaje: {str(e)}")
            return

    # Registrar el evento para mensajes editados
    @client.on(events.MessageEdited(chats=source))
    async def edit_forwarded_message(event):
        try:
            original_message_id = event.message.id

            if original_message_id in active_redirections:
                cloned_message_id = active_redirections[original_message_id]

                # Verificar si el mensaje editado tiene multimedia
                if event.message.media:
                    # Editar el mensaje multimedia reemplazándolo con el nuevo archivo
                    await client.edit_message(
                        destination,
                        cloned_message_id,
                        file=event.message.media,  # Nuevo archivo multimedia
                        text=event.message.text  # Texto del mensaje
                    )
                else:
                    # Editar solo el texto si no hay multimedia
                    await client.edit_message(destination, cloned_message_id, text=event.message.text)

        except Exception as e:
            print(f"Error al editar mensaje redirigido: {str(e)}")

    # Registrar el evento para respuestas a mensajes
    @client.on(events.NewMessage(chats=source))
    async def reply_forwarded_message(event):
        try:
            # Verificar si el mensaje es una respuesta a otro mensaje
            if event.message.is_reply:
                replied_message = await event.get_reply_message()
                original_message_id = replied_message.id

                # Verificar si el mensaje original está en active_redirections
                if original_message_id in active_redirections:
                    cloned_message_id = active_redirections[original_message_id]

                    # Enviar la respuesta al mensaje clonado en el destino
                    if event.message.media:
                        await client.send_message(
                            destination,
                            file=event.message.media,
                            message=event.message.text,
                            reply_to=cloned_message_id  # Responder al mensaje clonado
                        )
                    else:
                        await client.send_message(
                            destination,
                            message=event.message.text,
                            reply_to=cloned_message_id  # Responder al mensaje clonado
                        )

        except Exception as e:
            print(f"Error al replicar respuesta: {str(e)}")

    print(f"Redirección '{redirection_id}' iniciada automáticamente: {source} -> {destination}")

    # Guardar los callbacks asociados
    if user_id not in event_handlers:
        event_handlers[user_id] = {}
    event_handlers[user_id][redirection_id] = (forward_message, edit_forwarded_message, reply_forwarded_message)

    # Ejecutar la conexión del cliente sin desconectarlo inmediatamente
    await client.start()
    print(f"Cliente Telethon para {user_id} y redirección {redirection_id} está ahora activo.")
