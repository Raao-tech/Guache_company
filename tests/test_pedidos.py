from src import config


def _login_admin(client):
    return client.post(
        "/api/admin/login",
        json={"usuario": config.ADMIN_USERNAME, "clave": config.ADMIN_PASSWORD},
    )


def _crear_producto(client, **overrides):
    payload = {
        "nombre": "Café molido 500g",
        "descripcion": "Café tostado de origen, presentación familiar.",
        "precio": 6.5,
        "moneda": "USD",
        "activo": True,
        "stock": 10,
        "disponible_venezuela": True,
        "disponible_espana": True,
    }
    payload.update(overrides)
    respuesta = client.post("/api/admin/productos", json=payload)
    assert respuesta.status_code == 200, respuesta.text
    return respuesta.json()


def _datos_cliente_venezuela(**overrides):
    payload = {
        "mercado": "venezuela",
        "metodo_pago": "zelle_usd",
        "nombre_cliente": "Juan Pérez",
        "email_cliente": "juan@example.com",
        "telefono_cliente": "04141234567",
        "direccion_entrega": "Av. Bolívar, Acarigua",
        "referencia_pago": "REF-123456",
        "items": [],
    }
    payload.update(overrides)
    return payload


def test_crear_pedido_venezuela_descuenta_stock(client):
    _login_admin(client)
    producto = _crear_producto(client, stock=10)

    payload = _datos_cliente_venezuela(items=[{"producto_id": producto["id"], "cantidad": 3}])
    respuesta = client.post("/api/tienda/pedidos", json=payload)
    assert respuesta.status_code == 200, respuesta.text
    data = respuesta.json()
    assert data["estado"] == "pendiente_pago"
    assert data["mercado"] == "venezuela"
    assert data["moneda"] == "USD"
    assert data["total"] == 19.5
    assert data["numero_pedido"].startswith("PED-")

    productos = client.get("/api/admin/productos").json()
    assert productos[0]["stock"] == 7


def test_stock_insuficiente_no_crea_pedido_ni_descuenta(client):
    _login_admin(client)
    producto = _crear_producto(client, stock=2)

    payload = _datos_cliente_venezuela(items=[{"producto_id": producto["id"], "cantidad": 5}])
    respuesta = client.post("/api/tienda/pedidos", json=payload)
    assert respuesta.status_code == 400

    productos = client.get("/api/admin/productos").json()
    assert productos[0]["stock"] == 2  # no se tocó

    pedidos = client.get("/api/admin/pedidos").json()
    assert pedidos == []


def test_stock_none_no_se_descuenta(client):
    _login_admin(client)
    producto = _crear_producto(client, stock=None)

    payload = _datos_cliente_venezuela(items=[{"producto_id": producto["id"], "cantidad": 100}])
    respuesta = client.post("/api/tienda/pedidos", json=payload)
    assert respuesta.status_code == 200

    productos = client.get("/api/admin/productos").json()
    assert productos[0]["stock"] is None


def test_carrito_con_monedas_mezcladas_rechazado(client):
    _login_admin(client)
    usd = _crear_producto(client, nombre="Café", moneda="USD")
    eur = _crear_producto(client, nombre="Cacao", moneda="EUR")

    payload = _datos_cliente_venezuela(
        items=[{"producto_id": usd["id"], "cantidad": 1}, {"producto_id": eur["id"], "cantidad": 1}]
    )
    respuesta = client.post("/api/tienda/pedidos", json=payload)
    assert respuesta.status_code == 400


def test_producto_no_disponible_en_el_mercado_rechazado(client):
    _login_admin(client)
    producto = _crear_producto(client, disponible_venezuela=False)

    payload = _datos_cliente_venezuela(items=[{"producto_id": producto["id"], "cantidad": 1}])
    respuesta = client.post("/api/tienda/pedidos", json=payload)
    assert respuesta.status_code == 400


def test_producto_inactivo_rechazado(client):
    _login_admin(client)
    producto = _crear_producto(client, activo=False)

    payload = _datos_cliente_venezuela(items=[{"producto_id": producto["id"], "cantidad": 1}])
    respuesta = client.post("/api/tienda/pedidos", json=payload)
    assert respuesta.status_code == 400


def test_producto_sin_precio_rechazado(client):
    _login_admin(client)
    producto = _crear_producto(client, precio=None, moneda=None)

    payload = _datos_cliente_venezuela(items=[{"producto_id": producto["id"], "cantidad": 1}])
    respuesta = client.post("/api/tienda/pedidos", json=payload)
    assert respuesta.status_code == 400


def test_metodo_de_pago_invalido_para_el_mercado(client):
    _login_admin(client)
    producto = _crear_producto(client)

    payload = _datos_cliente_venezuela(
        metodo_pago="stripe", items=[{"producto_id": producto["id"], "cantidad": 1}]
    )
    respuesta = client.post("/api/tienda/pedidos", json=payload)
    assert respuesta.status_code == 400


def test_venezuela_sin_referencia_de_pago_rechazado(client):
    _login_admin(client)
    producto = _crear_producto(client)

    payload = _datos_cliente_venezuela(
        referencia_pago=None, items=[{"producto_id": producto["id"], "cantidad": 1}]
    )
    respuesta = client.post("/api/tienda/pedidos", json=payload)
    assert respuesta.status_code == 400


def test_seguimiento_publico_no_expone_pii_y_404_si_no_existe(client):
    _login_admin(client)
    producto = _crear_producto(client)
    creado = client.post(
        "/api/tienda/pedidos",
        json=_datos_cliente_venezuela(items=[{"producto_id": producto["id"], "cantidad": 1}]),
    ).json()

    respuesta = client.get(f"/api/tienda/pedidos/{creado['numero_pedido']}")
    assert respuesta.status_code == 200
    data = respuesta.json()
    assert data["estado"] == "pendiente_pago"
    assert len(data["items"]) == 1
    assert "telefono_cliente" not in data
    assert "direccion_entrega" not in data
    assert "referencia_pago" not in data

    assert client.get("/api/tienda/pedidos/PED-NO-EXISTE").status_code == 404


def test_admin_pedidos_requiere_permiso(client):
    _login_admin(client)
    client.post(
        "/api/admin/usuarios",
        json={
            "username": "Assistent_1",
            "clave": "12345_assistent",
            "permisos": {"productos": True},
        },
    )
    client.post("/api/admin/logout")
    client.post("/api/admin/login", json={"usuario": "Assistent_1", "clave": "12345_assistent"})

    assert client.get("/api/admin/pedidos").status_code == 403
    assert client.post("/api/admin/pedidos/1/confirmar").status_code == 403
    assert client.post("/api/admin/pedidos/1/cancelar").status_code == 403


def test_confirmar_pedido_cambia_estado_y_rechaza_doble_confirmacion(client):
    _login_admin(client)
    producto = _crear_producto(client)
    creado = client.post(
        "/api/tienda/pedidos",
        json=_datos_cliente_venezuela(items=[{"producto_id": producto["id"], "cantidad": 1}]),
    ).json()

    lista = client.get("/api/admin/pedidos").json()
    pedido_id = lista[0]["id"]

    confirmado = client.post(f"/api/admin/pedidos/{pedido_id}/confirmar")
    assert confirmado.status_code == 200
    assert confirmado.json()["estado"] == "pagado"

    doble = client.post(f"/api/admin/pedidos/{pedido_id}/confirmar")
    assert doble.status_code == 400


def test_cancelar_pedido_restaura_stock_y_es_idempotente(client):
    _login_admin(client)
    producto = _crear_producto(client, stock=10)
    client.post(
        "/api/tienda/pedidos",
        json=_datos_cliente_venezuela(items=[{"producto_id": producto["id"], "cantidad": 4}]),
    )

    productos = client.get("/api/admin/productos").json()
    assert productos[0]["stock"] == 6

    pedido_id = client.get("/api/admin/pedidos").json()[0]["id"]

    cancelado = client.post(f"/api/admin/pedidos/{pedido_id}/cancelar")
    assert cancelado.status_code == 200
    assert cancelado.json()["estado"] == "cancelado"

    productos = client.get("/api/admin/productos").json()
    assert productos[0]["stock"] == 10  # se restauró

    # Cancelar de nuevo debe rechazarse (400), no restaurar el stock otra vez
    doble = client.post(f"/api/admin/pedidos/{pedido_id}/cancelar")
    assert doble.status_code == 400
    productos = client.get("/api/admin/productos").json()
    assert productos[0]["stock"] == 10


def test_cancelar_pedido_con_stock_none_no_falla(client):
    _login_admin(client)
    producto = _crear_producto(client, stock=None)
    client.post(
        "/api/tienda/pedidos",
        json=_datos_cliente_venezuela(items=[{"producto_id": producto["id"], "cantidad": 2}]),
    )

    pedido_id = client.get("/api/admin/pedidos").json()[0]["id"]
    cancelado = client.post(f"/api/admin/pedidos/{pedido_id}/cancelar")
    assert cancelado.status_code == 200

    productos = client.get("/api/admin/productos").json()
    assert productos[0]["stock"] is None


def test_filtros_de_lista_admin(client):
    _login_admin(client)
    producto = _crear_producto(client, stock=10)
    client.post(
        "/api/tienda/pedidos",
        json=_datos_cliente_venezuela(items=[{"producto_id": producto["id"], "cantidad": 1}]),
    )

    todos = client.get("/api/admin/pedidos").json()
    assert len(todos) == 1

    pendientes = client.get("/api/admin/pedidos?estado=pendiente_pago").json()
    assert len(pendientes) == 1

    pagados = client.get("/api/admin/pedidos?estado=pagado").json()
    assert pagados == []

    espana = client.get("/api/admin/pedidos?mercado=espana").json()
    assert espana == []
