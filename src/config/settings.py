import os
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
ALLOWED_USERS = os.getenv("ALLOWED_USERS", "").split(",")  # Lista de usuarios permitidos
