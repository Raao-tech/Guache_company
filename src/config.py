import os
from dotenv import load_dotenv

#Cargar variables del aricho .env
load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
GROQ_API_KEY= os.getenv("GROQ_API_KEY")
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD")
SESSION_SECRET_KEY = os.getenv("SESSION_SECRET_KEY")

if not TELEGRAM_TOKEN:
    raise ValueError("⚠️ ERROR: No se encontró la clave del bot de Telegram (TELEGRAM_BOT_TOKEN) en el archivo .env")
if not GROQ_API_KEY:
    raise ValueError("⚠️ ERROR: No se encontró la clave de la API de GROQ (GROQ_API_KEY) en el archivo .env")
if not ADMIN_USERNAME or not ADMIN_PASSWORD:
    raise ValueError("⚠️ ERROR: Faltan credenciales de administrador (ADMIN_USERNAME / ADMIN_PASSWORD) en el archivo .env")
if not SESSION_SECRET_KEY:
    raise ValueError("⚠️ ERROR: No se encontró SESSION_SECRET_KEY en el archivo .env (firma las cookies de sesión del panel de administración)")

# Orígenes permitidos para CORS. En .env se define como lista separada por comas,
# ej: ALLOWED_ORIGINS="https://agroguache.com.ve,https://www.agroguache.com.ve"
_default_origins = "http://localhost:8000,http://127.0.0.1:8000"
ALLOWED_ORIGINS = [
    origin.strip()
    for origin in os.getenv("ALLOWED_ORIGINS", _default_origins).split(",")
    if origin.strip()
]
