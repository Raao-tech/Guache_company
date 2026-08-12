import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
from src.config import TELEGRAM_TOKEN
from src.services.llm_service import generar_respuesta_llm

logger = logging.getLogger("agroguache_telegram")

# Manejador del comando /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "¡Hola! Soy Guache 🦊, asistente comercial de Agroindustria Guache. "
        "Encantado de poder ayudarte. ¿En qué producto estás interesado?"
    )

# Manejador para mensajes de texto
async def responder_con_ia(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    texto_usuario = update.message.text

    # Muestra el estado "Escribiendo..." en Telegram
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")

    # Consulta a la IA (Groq)
    respuesta_ia = await generar_respuesta_llm(texto_usuario)

    await update.message.reply_text(respuesta_ia)

def crear_aplicacion_bot():
    """
    Construye la aplicación de Telegram pero NO inicia el polling.
    Esto permite que FastAPI controle cuándo encenderlo y apagarlo.
    """
    if not TELEGRAM_TOKEN:
        logger.warning("No se encontró TELEGRAM_TOKEN. El bot de Telegram estará deshabilitado.")
        return None
        
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), responder_con_ia))
    
    return app