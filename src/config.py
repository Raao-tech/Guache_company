import os
from dotenv import load_dotenv

#Cargar variables del aricho .env
load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
GROQ_API_KEY= os.getenv("GROQ_API_KEY")

if not TELEGRAM_TOKEN:
    raise ValueError("⚠️ ERROR: No se encontró la clave del bot de Telegram (TELEGRAM_BOT_TOKEN) en el archivo .env")
if not GROQ_API_KEY:
    raise ValueError("⚠️ ERROR: No se encontró la clave de la API de GROQ (GROQ_API_KEY) en el archivo .env")
