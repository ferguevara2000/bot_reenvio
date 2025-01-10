import os
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
ALLOWED_USERS = os.getenv("ALLOWED_USERS", "").split(",")  # Lista de usuarios permitidos
API_ID = os.getenv("API_ID")
API_HASH = os.getenv("API_HASH")
SESSION_NAME = os.getenv("SESSION_NAME")
URL_API = os.getenv("URL_API")
API_KEY = os.getenv("API_KEY")
SESSION_PATH = os.getenv("SESSION_PATH")
