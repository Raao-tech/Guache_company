from src import config
from src.services.llm_service import SYSTEM_PROMPT_POR_DEFECTO


def _login(client):
    return client.post(
        "/api/admin/login",
        json={"usuario": config.ADMIN_USERNAME, "clave": config.ADMIN_PASSWORD},
    )


def test_requiere_sesion(client):
    response = client.get("/api/admin/configuracion/prompt")
    assert response.status_code == 401


def test_sin_personalizar_devuelve_el_default(client):
    _login(client)
    response = client.get("/api/admin/configuracion/prompt")
    assert response.status_code == 200
    data = response.json()
    assert data["personalizado"] is False
    assert data["prompt"] == SYSTEM_PROMPT_POR_DEFECTO


def test_guardar_prompt_lo_personaliza(client):
    _login(client)
    nuevo_texto = "Sos un asistente de prueba para el catálogo de temporada."
    guardado = client.put("/api/admin/configuracion/prompt", json={"prompt": nuevo_texto})
    assert guardado.status_code == 200

    consulta = client.get("/api/admin/configuracion/prompt").json()
    assert consulta["personalizado"] is True
    assert consulta["prompt"] == nuevo_texto


def test_restaurar_default_borra_la_personalizacion(client):
    _login(client)
    client.put("/api/admin/configuracion/prompt", json={"prompt": "Texto personalizado de prueba."})
    client.delete("/api/admin/configuracion/prompt")

    consulta = client.get("/api/admin/configuracion/prompt").json()
    assert consulta["personalizado"] is False
    assert consulta["prompt"] == SYSTEM_PROMPT_POR_DEFECTO


def test_prompt_muy_corto_es_rechazado(client):
    _login(client)
    response = client.put("/api/admin/configuracion/prompt", json={"prompt": "corto"})
    assert response.status_code == 422


def test_chat_usa_el_prompt_personalizado(client, monkeypatch):
    """
    No mockea generar_respuesta_llm entero (eso saltearía la lógica que
    se quiere probar) — mockea un nivel más abajo, la llamada real a
    Groq, para verificar qué system prompt le llegó de verdad.
    """
    _login(client)
    texto_personalizado = "Sos un asistente de prueba, respondé siempre con la palabra PRUEBA-OK."
    client.put("/api/admin/configuracion/prompt", json={"prompt": texto_personalizado})

    mensajes_capturados = {}

    class RespuestaFalsa:
        class choices:
            class message:
                content = "respuesta simulada"

    async def create_fake(model, messages, temperature):
        mensajes_capturados["system"] = messages[0]["content"]
        return RespuestaFalsa()

    import src.services.llm_service as llm_service_module

    monkeypatch.setattr(
        llm_service_module.client.chat.completions, "create", create_fake
    )

    respuesta = client.post("/api/chat", json={"mensaje": "hola"})
    assert respuesta.status_code == 200
    assert mensajes_capturados["system"] == texto_personalizado
