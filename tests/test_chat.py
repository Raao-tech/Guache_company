import main


async def _fake_respuesta_llm(prompt_usuario: str) -> str:
    return f"Respuesta simulada para: {prompt_usuario}"


def test_chat_responde_usando_el_llm(client, monkeypatch):
    monkeypatch.setattr(main, "generar_respuesta_llm", _fake_respuesta_llm)

    response = client.post("/api/chat", json={"mensaje": "¿Tienen harina de maíz?"})

    assert response.status_code == 200
    assert response.json()["respuesta"] == "Respuesta simulada para: ¿Tienen harina de maíz?"


def test_chat_rechaza_mensaje_vacio(client):
    response = client.post("/api/chat", json={"mensaje": ""})

    assert response.status_code == 422


def test_chat_devuelve_500_si_el_llm_falla(client, monkeypatch):
    async def _falla(prompt_usuario: str) -> str:
        raise RuntimeError("Groq no disponible")

    monkeypatch.setattr(main, "generar_respuesta_llm", _falla)

    response = client.post("/api/chat", json={"mensaje": "hola"})

    assert response.status_code == 500
