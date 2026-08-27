from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.bots import telegram_bot
from src.database import Base, MensajeChatDB


@pytest.fixture()
def db_bot(tmp_path, monkeypatch):
    """
    Base SQLite temporal y aislada, igual que el fixture `client` de
    conftest.py pero sin levantar FastAPI: el bot usa su propio
    SessionLocal (no pasa por Depends de FastAPI), así que hay que
    parchear directamente la referencia que telegram_bot.py ya importó
    — mismo patrón que conftest.py usa para llm_service.SessionLocal.
    """
    engine = create_engine(
        f"sqlite:///{tmp_path / 'test_bot.db'}", connect_args={"check_same_thread": False}
    )
    TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    monkeypatch.setattr(telegram_bot, "SessionLocal", TestSessionLocal)
    return TestSessionLocal


def _mensajes(SessionLocal, sesion_id):
    db = SessionLocal()
    try:
        return (
            db.query(MensajeChatDB)
            .filter(MensajeChatDB.sesion_id == sesion_id)
            .order_by(MensajeChatDB.id)
            .all()
        )
    finally:
        db.close()


def _fake_update(chat_id=12345, texto="hola"):
    update = MagicMock()
    update.effective_chat.id = chat_id
    update.message.text = texto
    update.message.reply_text = AsyncMock()
    return update


def _fake_context():
    context = MagicMock()
    context.bot.send_chat_action = AsyncMock()
    return context


def test_guardar_mensaje_escribe_en_la_base(db_bot):
    telegram_bot._guardar_mensaje("telegram-1", "usuario", "hola guache")

    mensajes = _mensajes(db_bot, "telegram-1")
    assert len(mensajes) == 1
    assert mensajes[0].canal == "telegram"
    assert mensajes[0].rol == "usuario"
    assert mensajes[0].contenido == "hola guache"


async def test_start_saluda_sin_tocar_la_base(db_bot):
    update = _fake_update()
    await telegram_bot.start(update, _fake_context())

    update.message.reply_text.assert_awaited_once()
    texto_enviado = update.message.reply_text.call_args[0][0]
    assert "Guache" in texto_enviado
    assert _mensajes(db_bot, "telegram-12345") == []


async def test_responder_con_ia_guarda_ambos_mensajes_y_responde(db_bot, monkeypatch):
    async def _fake_llm(prompt_usuario):
        return f"Respuesta simulada para: {prompt_usuario}"

    monkeypatch.setattr(telegram_bot, "generar_respuesta_llm", _fake_llm)

    update = _fake_update(chat_id=999, texto="¿Tienen harina de maíz?")
    context = _fake_context()

    await telegram_bot.responder_con_ia(update, context)

    context.bot.send_chat_action.assert_awaited_once_with(chat_id=999, action="typing")
    update.message.reply_text.assert_awaited_once_with(
        "Respuesta simulada para: ¿Tienen harina de maíz?"
    )

    mensajes = _mensajes(db_bot, "telegram-999")
    assert len(mensajes) == 2
    assert mensajes[0].rol == "usuario"
    assert mensajes[0].contenido == "¿Tienen harina de maíz?"
    assert mensajes[1].rol == "asistente"
    assert mensajes[1].contenido == "Respuesta simulada para: ¿Tienen harina de maíz?"


async def test_responder_con_ia_agrupa_por_chat_id_no_por_mensaje(db_bot, monkeypatch):
    """Dos mensajes del mismo chat de Telegram deben quedar en la misma sesión."""

    async def _fake_llm(prompt_usuario):
        return "ok"

    monkeypatch.setattr(telegram_bot, "generar_respuesta_llm", _fake_llm)

    await telegram_bot.responder_con_ia(_fake_update(chat_id=42, texto="primero"), _fake_context())
    await telegram_bot.responder_con_ia(_fake_update(chat_id=42, texto="segundo"), _fake_context())

    mensajes = _mensajes(db_bot, "telegram-42")
    assert len(mensajes) == 4


async def test_responder_con_ia_guarda_el_mensaje_del_usuario_aunque_el_llm_falle(db_bot, monkeypatch):
    async def _falla(prompt_usuario):
        raise RuntimeError("Groq no disponible")

    monkeypatch.setattr(telegram_bot, "generar_respuesta_llm", _falla)

    with pytest.raises(RuntimeError):
        await telegram_bot.responder_con_ia(_fake_update(chat_id=7, texto="hola"), _fake_context())

    mensajes = _mensajes(db_bot, "telegram-7")
    assert len(mensajes) == 1
    assert mensajes[0].rol == "usuario"


def test_crear_aplicacion_bot_deshabilitado_sin_token(monkeypatch):
    monkeypatch.setattr(telegram_bot, "TELEGRAM_TOKEN", "")
    assert telegram_bot.crear_aplicacion_bot() is None


def test_crear_aplicacion_bot_arma_la_app_con_token(monkeypatch):
    monkeypatch.setattr(telegram_bot, "TELEGRAM_TOKEN", "123456:FAKE-TOKEN-para-tests")
    app = telegram_bot.crear_aplicacion_bot()
    assert app is not None
