from telegram import Update
from telegram.ext import CallbackContext
from functools import wraps

# Simulación de validación de sesión
def has_active_session(user_id: int) -> bool:
    # Aquí verificas en tu base de datos o lógica si el usuario tiene sesión
    return user_id in [123456, 789012]  # IDs de usuarios con sesiones activas (ejemplo)

# Decorador para validar sesión
def session_required(handler):
    @wraps(handler)
    async def wrapper(update: Update, context: CallbackContext):
        user_id = update.effective_user.id
        if not has_active_session(user_id):
            await update.message.reply_text("Debes iniciar sesión para usar este comando.")
            return
        return await handler(update, context)
    return wrapper
