import asyncio
from src.actions.load_redirections import bot_startup
from src.bot import start_bot, main

if __name__ == "__main__":# Obtener el bucle de eventos actual
    loop = asyncio.get_event_loop()
    loop.create_task(bot_startup())
    start_bot()
    #main()
