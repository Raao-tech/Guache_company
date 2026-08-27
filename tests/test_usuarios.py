from src import config


def _login(client, usuario, clave):
    return client.post("/api/admin/login", json={"usuario": usuario, "clave": clave})


def _login_admin_legacy(client):
    return _login(client, config.ADMIN_USERNAME, config.ADMIN_PASSWORD)


def _crear_usuario(client, username, clave, permisos=None, activo=True):
    return client.post(
        "/api/admin/usuarios",
        json={
            "username": username,
            "clave": clave,
            "permisos": permisos or {},
            "activo": activo,
        },
    )


TODOS_LOS_PERMISOS = {
    "productos": True,
    "blog": True,
    "asistente": True,
    "conversaciones": True,
    "usuarios": True,
}


def test_cuenta_compartida_sigue_funcionando(client):
    """La cuenta ADMIN_USERNAME/ADMIN_PASSWORD de siempre no se rompió."""
    response = _login_admin_legacy(client)
    assert response.status_code == 200

    whoami = client.get("/api/admin/whoami").json()
    assert whoami["autenticado"] is True
    assert whoami["permisos"] == TODOS_LOS_PERMISOS


def test_usuario_sin_permiso_no_puede_gestionar_usuarios(client):
    _login_admin_legacy(client)
    _crear_usuario(client, "Assistent_1", "12345_assistent", {"productos": True, "blog": True})
    client.post("/api/admin/logout")

    _login(client, "Assistent_1", "12345_assistent")
    whoami = client.get("/api/admin/whoami").json()
    assert whoami["permisos"]["usuarios"] is False

    response = client.get("/api/admin/usuarios")
    assert response.status_code == 403


def test_permiso_productos_no_alcanza_para_blog(client):
    """Un permiso no otorga acceso a otro módulo — son independientes."""
    _login_admin_legacy(client)
    _crear_usuario(client, "SoloCatalogo", "clave-cualquiera1", {"productos": True})
    client.post("/api/admin/logout")

    _login(client, "SoloCatalogo", "clave-cualquiera1")

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
    assert post.status_code == 403


def test_asistente_con_todos_los_permisos_menos_usuarios(client):
    _login_admin_legacy(client)
    _crear_usuario(
        client,
        "Assistent_1",
        "12345_assistent",
        {"productos": True, "blog": True, "asistente": True, "conversaciones": True},
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

    assert client.get("/api/admin/usuarios").status_code == 403


def test_admin_completo_puede_gestionar_usuarios(client):
    _login_admin_legacy(client)
    creado = _crear_usuario(client, "Developer_1", "6871_raao", TODOS_LOS_PERMISOS)
    assert creado.status_code == 200
    data = creado.json()
    assert data["username"] == "Developer_1"
    assert data["permiso_usuarios"] is True
    assert "clave" not in data
    assert "password_hash" not in data


def test_password_nunca_se_expone(client):
    _login_admin_legacy(client)
    _crear_usuario(client, "Senaida", "SES_acarigua1998", TODOS_LOS_PERMISOS)
    lista = client.get("/api/admin/usuarios").json()
    for usuario in lista:
        assert "clave" not in usuario
        assert "password_hash" not in usuario


def test_username_duplicado_rechazado(client):
    _login_admin_legacy(client)
    _crear_usuario(client, "Senaida", "clave-cualquiera1", TODOS_LOS_PERMISOS)
    duplicado = _crear_usuario(client, "Senaida", "clave-cualquiera1", TODOS_LOS_PERMISOS)
    assert duplicado.status_code == 400


def test_usuario_nuevo_puede_loguearse(client):
    _login_admin_legacy(client)
    _crear_usuario(client, "Senaida", "SES_acarigua1998", TODOS_LOS_PERMISOS)
    client.post("/api/admin/logout")

    response = _login(client, "Senaida", "SES_acarigua1998")
    assert response.status_code == 200


def test_clave_incorrecta_rechazada(client):
    _login_admin_legacy(client)
    _crear_usuario(client, "Senaida", "SES_acarigua1998", TODOS_LOS_PERMISOS)
    client.post("/api/admin/logout")

    response = _login(client, "Senaida", "clave-incorrecta")
    assert response.status_code == 401


def test_usuario_inactivo_no_puede_loguearse(client):
    _login_admin_legacy(client)
    creado = _crear_usuario(
        client, "Senaida", "SES_acarigua1998", TODOS_LOS_PERMISOS, activo=False
    ).json()
    assert creado["activo"] is False
    client.post("/api/admin/logout")

    response = _login(client, "Senaida", "SES_acarigua1998")
    assert response.status_code == 401


def test_actualizar_usuario_cambia_clave(client):
    _login_admin_legacy(client)
    creado = _crear_usuario(client, "Senaida", "clave-vieja123", TODOS_LOS_PERMISOS).json()

    actualizado = client.put(
        f"/api/admin/usuarios/{creado['id']}",
        json={"permisos": TODOS_LOS_PERMISOS, "activo": True, "clave": "clave-nueva456"},
    )
    assert actualizado.status_code == 200
    client.post("/api/admin/logout")

    vieja = _login(client, "Senaida", "clave-vieja123")
    assert vieja.status_code == 401

    nueva = _login(client, "Senaida", "clave-nueva456")
    assert nueva.status_code == 200


def test_actualizar_usuario_sin_clave_no_la_cambia(client):
    _login_admin_legacy(client)
    creado = _crear_usuario(client, "Senaida", "clave-original1", TODOS_LOS_PERMISOS).json()

    client.put(
        f"/api/admin/usuarios/{creado['id']}",
        json={"permisos": TODOS_LOS_PERMISOS, "activo": True},
    )
    client.post("/api/admin/logout")

    response = _login(client, "Senaida", "clave-original1")
    assert response.status_code == 200


def test_actualizar_usuario_cambia_permisos(client):
    _login_admin_legacy(client)
    creado = _crear_usuario(client, "Senaida", "clave-original1", {"productos": True}).json()
    assert creado["permiso_blog"] is False

    actualizado = client.put(
        f"/api/admin/usuarios/{creado['id']}",
        json={"permisos": {"productos": False, "blog": True}, "activo": True},
    ).json()
    assert actualizado["permiso_productos"] is False
    assert actualizado["permiso_blog"] is True


def test_eliminar_usuario(client):
    _login_admin_legacy(client)
    creado = _crear_usuario(client, "Senaida", "SES_acarigua1998", TODOS_LOS_PERMISOS).json()

    eliminado = client.delete(f"/api/admin/usuarios/{creado['id']}")
    assert eliminado.status_code == 200

    lista = client.get("/api/admin/usuarios").json()
    assert all(u["id"] != creado["id"] for u in lista)


def test_usuarios_requiere_sesion(client):
    response = client.get("/api/admin/usuarios")
    assert response.status_code == 401
