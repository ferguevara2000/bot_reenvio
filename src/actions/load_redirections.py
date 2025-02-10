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
            await client.send_message(destination, event.message)
        except Exception as e:
            print(f"Error al redirigir mensaje: {str(e)}")
            return

    # Detectar mensajes editados
    @client.on(events.MessageEdited(chats=source))
    async def forward_edited_message(event):
        try:
            await client.send_message(destination, f"{event.message.text}")
        except Exception as e:
            print(f"Error al redirigir mensaje editado: {str(e)}")
            return

    # Guardar el callback asociado
    if user_id not in event_handlers:
        event_handlers[user_id] = {}
    event_handlers[user_id][redirection_id] = forward_message

    print(f"Redirección '{redirection_id}' iniciada automáticamente: {source} -> {destination}")

    # Asegúrate de que el cliente esté conectado
    await client.start()
    print(f"Cliente Telethon para {user_id} y redirección {redirection_id} está ahora activo.")
