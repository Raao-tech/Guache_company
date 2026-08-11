import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
from src.config import TELEGRAM_TOKEN
from src.services.llm_service import generar_respuesta_llm

#  1. Configuaración de Logs (Para depuración en consola)
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# 2. Manejador del comando /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("HOLA!! Soy Guache el zorro asistente de la compañía. Encantado de poder ayudarte.")

# 3. Manejador para mensajes de texto respondidos meddiante LLMs
async def responder_con_ia(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    texto_usuario = update.message.text

    # Muestra el estado "Escribiendo..." en Telegram
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")

    # Consulta a la IA
    respuesta_ia = await generar_respuesta_llm(texto_usuario)

    await update.message.reply_text(respuesta_ia)

# 4. Función de inicialización y arranque del servidor
def run_telegram_bot():
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), responder_con_ia))

    print("El Zorro Guache listo para cazar más ventas. Esperando consultas de clientes...")
    app.run_polling()
