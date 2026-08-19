from src import config


def _login(client, usuario, clave):
    return client.post("/api/admin/login", json={"usuario": usuario, "clave": clave})


def _login_admin_legacy(client):
    return _login(client, config.ADMIN_USERNAME, config.ADMIN_PASSWORD)


def test_cuenta_compartida_sigue_funcionando(client):
    """La cuenta ADMIN_USERNAME/ADMIN_PASSWORD de siempre no se rompió."""
    response = _login_admin_legacy(client)
    assert response.status_code == 200

    whoami = client.get("/api/admin/whoami").json()
    assert whoami["autenticado"] is True
    assert whoami["rol"] == "admin"


def test_asistente_no_puede_gestionar_usuarios(client):
    _login_admin_legacy(client)
    client.post(
        "/api/admin/usuarios",
        json={"username": "Assistent_1", "clave": "12345_assistent", "rol": "asistente"},
    )
    client.post("/api/admin/logout")

    _login(client, "Assistent_1", "12345_assistent")
    whoami = client.get("/api/admin/whoami").json()
    assert whoami["rol"] == "asistente"

    response = client.get("/api/admin/usuarios")
    assert response.status_code == 403


def test_asistente_si_puede_gestionar_catalogo_y_blog(client):
    _login_admin_legacy(client)
    client.post(
        "/api/admin/usuarios",
        json={"username": "Assistent_1", "clave": "12345_assistent", "rol": "asistente"},
    )
    client.post("/api/admin/logout")

    _login(client, "Assistent_1", "12345_assistent")

    producto = client.post(
        "/api/admin/productos",
        json={"nombre": "Producto de asistente", "descripcion": "Creado por asistente.", "activo": True},
    )
    assert producto.status_code == 200

    post = client.post(
        "/api/admin/blog",
        json={
            "titulo": "Post de asistente",
            "resumen": "resumen",
            "contenido": "contenido",
            "publicado": True,
        },
    )
    assert post.status_code == 200


def test_admin_completo_puede_gestionar_usuarios(client):
    _login_admin_legacy(client)
    creado = client.post(
        "/api/admin/usuarios",
        json={"username": "Developer_1", "clave": "6871_raao", "rol": "admin"},
    )
    assert creado.status_code == 200
    data = creado.json()
    assert data["username"] == "Developer_1"
    assert data["rol"] == "admin"
    assert "clave" not in data
    assert "password_hash" not in data


def test_password_nunca_se_expone(client):
    _login_admin_legacy(client)
    client.post(
        "/api/admin/usuarios",
        json={"username": "Senaida", "clave": "SES_acarigua1998", "rol": "admin"},
    )
    lista = client.get("/api/admin/usuarios").json()
    for usuario in lista:
        assert "clave" not in usuario
        assert "password_hash" not in usuario


def test_username_duplicado_rechazado(client):
    _login_admin_legacy(client)
    payload = {"username": "Senaida", "clave": "clave-cualquiera1", "rol": "admin"}
    client.post("/api/admin/usuarios", json=payload)
    duplicado = client.post("/api/admin/usuarios", json=payload)
    assert duplicado.status_code == 400


def test_usuario_nuevo_puede_loguearse(client):
    _login_admin_legacy(client)
    client.post(
        "/api/admin/usuarios",
        json={"username": "Senaida", "clave": "SES_acarigua1998", "rol": "admin"},
    )
    client.post("/api/admin/logout")

    response = _login(client, "Senaida", "SES_acarigua1998")
    assert response.status_code == 200


def test_clave_incorrecta_rechazada(client):
    _login_admin_legacy(client)
    client.post(
        "/api/admin/usuarios",
        json={"username": "Senaida", "clave": "SES_acarigua1998", "rol": "admin"},
    )
    client.post("/api/admin/logout")

    response = _login(client, "Senaida", "clave-incorrecta")
    assert response.status_code == 401


def test_usuario_inactivo_no_puede_loguearse(client):
    _login_admin_legacy(client)
    creado = client.post(
        "/api/admin/usuarios",
        json={"username": "Senaida", "clave": "SES_acarigua1998", "rol": "admin", "activo": False},
    ).json()
    assert creado["activo"] is False
    client.post("/api/admin/logout")

    response = _login(client, "Senaida", "SES_acarigua1998")
    assert response.status_code == 401


def test_actualizar_usuario_cambia_clave(client):
    _login_admin_legacy(client)
    creado = client.post(
        "/api/admin/usuarios",
        json={"username": "Senaida", "clave": "clave-vieja123", "rol": "admin"},
    ).json()

    actualizado = client.put(
        f"/api/admin/usuarios/{creado['id']}",
        json={"rol": "admin", "activo": True, "clave": "clave-nueva456"},
    )
    assert actualizado.status_code == 200
    client.post("/api/admin/logout")

    vieja = _login(client, "Senaida", "clave-vieja123")
    assert vieja.status_code == 401

    nueva = _login(client, "Senaida", "clave-nueva456")
    assert nueva.status_code == 200


def test_actualizar_usuario_sin_clave_no_la_cambia(client):
    _login_admin_legacy(client)
    creado = client.post(
        "/api/admin/usuarios",
        json={"username": "Senaida", "clave": "clave-original1", "rol": "admin"},
    ).json()

    client.put(
        f"/api/admin/usuarios/{creado['id']}",
        json={"rol": "admin", "activo": True},
    )
    client.post("/api/admin/logout")

    response = _login(client, "Senaida", "clave-original1")
    assert response.status_code == 200


def test_eliminar_usuario(client):
    _login_admin_legacy(client)
    creado = client.post(
        "/api/admin/usuarios",
        json={"username": "Senaida", "clave": "SES_acarigua1998", "rol": "admin"},
    ).json()

    eliminado = client.delete(f"/api/admin/usuarios/{creado['id']}")
    assert eliminado.status_code == 200

    lista = client.get("/api/admin/usuarios").json()
    assert all(u["id"] != creado["id"] for u in lista)


def test_usuarios_requiere_sesion(client):
    response = client.get("/api/admin/usuarios")
    assert response.status_code == 401
