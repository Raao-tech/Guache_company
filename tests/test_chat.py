from src import config

import main


async def _fake_respuesta_llm(prompt_usuario: str) -> str:
    return f"Respuesta simulada para: {prompt_usuario}"


def _login(client):
    return client.post(
        "/api/admin/login",
        json={"usuario": config.ADMIN_USERNAME, "clave": config.ADMIN_PASSWORD},
    )


def test_chat_responde_usando_el_llm(client, monkeypatch):
    monkeypatch.setattr(main, "generar_respuesta_llm", _fake_respuesta_llm)

    response = client.post("/api/chat", json={"mensaje": "¿Tienen harina de maíz?"})

    assert response.status_code == 200
    assert response.json()["respuesta"] == "Respuesta simulada para: ¿Tienen harina de maíz?"


def test_chat_genera_sesion_id_si_no_se_manda(client, monkeypatch):
    monkeypatch.setattr(main, "generar_respuesta_llm", _fake_respuesta_llm)

    response = client.post("/api/chat", json={"mensaje": "hola"})

    assert response.json()["sesion_id"]


def test_chat_reusa_el_sesion_id_que_se_le_manda(client, monkeypatch):
    monkeypatch.setattr(main, "generar_respuesta_llm", _fake_respuesta_llm)

    response = client.post("/api/chat", json={"mensaje": "hola", "sesion_id": "sesion-fija-123"})

    assert response.json()["sesion_id"] == "sesion-fija-123"


def test_chat_guarda_los_mensajes_en_el_historial(client, monkeypatch):
    monkeypatch.setattr(main, "generar_respuesta_llm", _fake_respuesta_llm)
    _login(client)

    client.post("/api/chat", json={"mensaje": "primer mensaje", "sesion_id": "sesion-test"})
    client.post("/api/chat", json={"mensaje": "segundo mensaje", "sesion_id": "sesion-test"})

    hilo = client.get("/api/admin/conversaciones/sesion-test").json()
    assert len(hilo) == 4  # 2 del usuario + 2 del asistente
    assert hilo[0]["rol"] == "usuario"
    assert hilo[0]["contenido"] == "primer mensaje"
    assert hilo[1]["rol"] == "asistente"

    resumen = client.get("/api/admin/conversaciones").json()
    sesion = next(c for c in resumen if c["sesion_id"] == "sesion-test")
    assert sesion["canal"] == "web"
    assert sesion["cantidad_mensajes"] == 4


def test_mensaje_de_usuario_queda_guardado_aunque_el_llm_falle(client, monkeypatch):
    async def _falla(prompt_usuario: str) -> str:
        raise RuntimeError("Groq no disponible")

    monkeypatch.setattr(main, "generar_respuesta_llm", _falla)
    _login(client)

    client.post("/api/chat", json={"mensaje": "este mensaje debe quedar", "sesion_id": "sesion-error"})

    hilo = client.get("/api/admin/conversaciones/sesion-error").json()
    assert len(hilo) == 1
    assert hilo[0]["rol"] == "usuario"


def test_chat_rechaza_mensaje_vacio(client):
    response = client.post("/api/chat", json={"mensaje": ""})

    assert response.status_code == 422


def test_chat_devuelve_500_si_el_llm_falla(client, monkeypatch):
    async def _falla(prompt_usuario: str) -> str:
        raise RuntimeError("Groq no disponible")

    monkeypatch.setattr(main, "generar_respuesta_llm", _falla)

    response = client.post("/api/chat", json={"mensaje": "hola"})

    assert response.status_code == 500
