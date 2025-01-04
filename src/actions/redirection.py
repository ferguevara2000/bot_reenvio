from telethon import events
from telegram import Update
from telegram.ext import ContextTypes

from src.actions.connect import get_telethon_client, ensure_connected

# Diccionario para rastrear redirecciones por usuario
user_redirections = {}

# Comando para manejar redirecciones
async def redirection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    args = context.args

    if len(args) < 2 or args[0] != "add":
        await update.message.reply_text(
            "Uso del comando:\n"
            "/redirection add [redireccionID]\n"
            "Luego especifica los chats: source - destination"
        )
        return

    # Paso 1: Extraer redirection_id
    redirection_id = args[1]

    # Verificar si ya existe una redirección con ese ID
    if user_id in user_redirections and redirection_id in user_redirections[user_id]:
        await update.message.reply_text(
            f"La redirección '{redirection_id}' ya está configurada. Usa otro ID."
        )
        return

    # Crear una nueva entrada para esta redirección
    if user_id not in user_redirections:
        user_redirections[user_id] = {}

    user_redirections[user_id][redirection_id] = {"source": None, "destination": None}
    await update.message.reply_text(
        f"Redirección '{redirection_id}' creada. Ahora envía los chats en el formato:\n"
        "`source - destination`"
    )

async def handle_chat_ids(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    message_text = update.message.text

    # Buscar redirección activa
    active_redirection = None
    if user_id in user_redirections:
        for redirection_id, data in user_redirections[user_id].items():
            if data["source"] is None or data["destination"] is None:
                active_redirection = redirection_id
                break

    if not active_redirection:
        await update.message.reply_text(
            "No hay una redirección activa. Usa /redirection add para crear una."
        )
        return

    # Validar el formato source - destination
    try:
        source, destination = map(int, message_text.split("-"))
    except ValueError:
        await update.message.reply_text("El formato debe ser: source - destination.")
        return

    # Guardar los IDs en la redirección activa
    user_redirections[user_id][active_redirection]["source"] = source
    user_redirections[user_id][active_redirection]["destination"] = destination

    await update.message.reply_text(
        f"Chats configurados para la redirección '{active_redirection}'.\n"
        f"Source: {source}\nDestination: {destination}"
    )

    # Iniciar la redirección automáticamente
    await start_redirection(user_id, active_redirection)

async def start_redirection(user_id: int, redirection_id: str) -> None:
    redirection = user_redirections[user_id].get(redirection_id)

    if not redirection or not redirection["source"] or not redirection["destination"]:
        raise ValueError("La redirección no está completamente configurada.")

    source = redirection["source"]
    destination = redirection["destination"]

    # Crear cliente Telethon
    client = await get_telethon_client(user_id)
    await ensure_connected(client)

    @client.on(events.NewMessage(chats=source))
    async def forward_message(event):
        try:
            await client.send_message(destination, event.message)
        except Exception as e:
            print(f"Error al redirigir mensaje: {str(e)}")

    print(f"Redirección '{redirection_id}' iniciada automáticamente: {source} -> {destination}")
