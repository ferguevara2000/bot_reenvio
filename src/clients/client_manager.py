# src/client_manager.py
import os

import aiohttp
from telethon import TelegramClient

from ..config.settings import API_ID, API_HASH, URL_API, API_KEY, SESSION_PATH

# Diccionario global para almacenar clientes por usuario
clients = {}

event_handlers = {}


async def get_or_create_client(user_id: int) -> TelegramClient:
    """
    Obtiene o crea un cliente para un usuario específico.
    Si ya existe un cliente para este usuario, lo reutiliza.
    """
    if user_id in clients:
        client = clients[user_id]
        if not client.is_connected():
            await client.connect()
        return client

    # Si no existe un cliente para este usuario, lo creamos
    session_name = os.path.join(SESSION_PATH, f"user_{user_id}")
    client = TelegramClient(str(session_name), API_ID, API_HASH)

    try:
        await client.connect()
    except Exception as e:
        await client.disconnect()
        raise Exception(f"Error al conectar el cliente: {str(e)}")

    clients[user_id] = client
    return client


async def disconnect_client(user_id: int) -> None:
    """
    Desconecta el cliente para el usuario específico.
    """
    if user_id in clients:
        client = clients[user_id]
        if client.is_connected():
            await client.disconnect()
        del clients[user_id]

async def get_session_data(user_id: int):
    async with aiohttp.ClientSession() as session:
        # El cuerpo de la solicitud POST con el user_id
        payload = {
            "user_id": user_id
        }

        # Definir los encabezados para la solicitud
        headers = {
            "Content-Type": "application/json",
            "apikey": API_KEY,
            "Authorization": f"Bearer {API_KEY}"
        }

        try:
            # Hacer la solicitud POST asincrónica
            async with session.post(URL_API, json=payload, headers=headers) as response:
                # Verificar si la respuesta es exitosa
                if response.status != 200:
                    print(f"Error: {response.status} - {await response.text()}")
                    return None

                # Obtener el contenido JSON de la respuesta
                data = await response.json()

                # Verificar si session_data está presente y no es null
                if not data:
                    # Si session_data es None, null o vacío, la sesión no está completa
                    print("Session data is null or empty.")
                    return None

                # Retornar los datos de la sesión
                return data

        except Exception as e:
            # Manejar errores durante la solicitud
            print(f"Error al obtener sesión para el usuario {user_id}: {e}")
            return None
