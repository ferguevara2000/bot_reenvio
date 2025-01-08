# src/client_manager.py
import os
from telethon import TelegramClient
from src.config.settings import API_ID, API_HASH

# Diccionario global para almacenar clientes por usuario
clients = {}


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
    session_name = os.path.join("sessions", f"user_{user_id}")
    client = TelegramClient(session_name, API_ID, API_HASH)

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
