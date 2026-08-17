def test_registrar_cotizacion_exitosa(client, cotizacion_payload):
    response = client.post("/api/cotizar", json=cotizacion_payload)

    assert response.status_code == 200
    data = response.json()
    assert data["exito"] is True
    assert data["id_cotizacion"].startswith("COT-")


def test_registrar_cotizacion_invalida(client, cotizacion_payload):
    payload = {**cotizacion_payload, "cantidad_toneladas": -5}

    response = client.post("/api/cotizar", json=payload)

    assert response.status_code == 422


def test_listar_cotizaciones_sin_auth_es_rechazado(client):
    response = client.get("/api/cotizaciones")

    assert response.status_code == 401


def test_listar_cotizaciones_con_auth_incorrecta_es_rechazado(client):
    response = client.get("/api/cotizaciones", auth=("admin", "clave-incorrecta"))

    assert response.status_code == 401


def test_listar_cotizaciones_con_auth_correcta(client, admin_auth, cotizacion_payload):
    client.post("/api/cotizar", json=cotizacion_payload)

    response = client.get("/api/cotizaciones", auth=admin_auth)

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["nombre_contacto"] == cotizacion_payload["nombre_contacto"]
