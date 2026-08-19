from src import config


def _login(client):
    return client.post(
        "/api/admin/login",
        json={"usuario": config.ADMIN_USERNAME, "clave": config.ADMIN_PASSWORD},
    )


def test_login_correcto(client):
    response = _login(client)
    assert response.status_code == 200
    assert response.json()["exito"] is True


def test_login_incorrecto(client):
    response = client.post(
        "/api/admin/login", json={"usuario": "admin", "clave": "clave-mala"}
    )
    assert response.status_code == 401


def test_whoami_sin_sesion(client):
    response = client.get("/api/admin/whoami")
    assert response.json()["autenticado"] is False


def test_whoami_con_sesion(client):
    _login(client)
    response = client.get("/api/admin/whoami")
    assert response.json()["autenticado"] is True


def test_logout(client):
    _login(client)
    client.post("/api/admin/logout")
    response = client.get("/api/admin/whoami")
    assert response.json()["autenticado"] is False


def test_admin_productos_requiere_sesion(client):
    response = client.get("/api/admin/productos")
    assert response.status_code == 401


def test_crear_y_listar_producto(client):
    _login(client)
    payload = {
        "nombre": "Café molido 500g",
        "descripcion": "Café tostado de origen, presentación familiar.",
        "precio": 6.5,
        "moneda": "USD",
        "activo": True,
        "orden": 1,
    }
    response = client.post("/api/admin/productos", json=payload)
    assert response.status_code == 200
    creado = response.json()
    assert creado["nombre"] == payload["nombre"]

    publico = client.get("/api/detal/productos")
    assert publico.status_code == 200
    assert len(publico.json()) == 1


def test_producto_inactivo_no_aparece_en_publico(client):
    _login(client)
    client.post(
        "/api/admin/productos",
        json={
            "nombre": "Producto oculto",
            "descripcion": "No debería verse en la web pública.",
            "activo": False,
            "orden": 0,
        },
    )

    publico = client.get("/api/detal/productos")
    assert publico.json() == []

    admin_lista = client.get("/api/admin/productos")
    assert len(admin_lista.json()) == 1


def test_actualizar_y_eliminar_producto(client):
    _login(client)
    creado = client.post(
        "/api/admin/productos",
        json={"nombre": "Cacao 250g", "descripcion": "Cacao en polvo.", "activo": True},
    ).json()

    actualizado = client.put(
        f"/api/admin/productos/{creado['id']}",
        json={
            "nombre": "Cacao 250g",
            "descripcion": "Cacao en polvo, edición actualizada.",
            "precio": 4.0,
            "moneda": "EUR",
            "activo": True,
        },
    )
    assert actualizado.status_code == 200
    assert actualizado.json()["precio"] == 4.0

    eliminado = client.delete(f"/api/admin/productos/{creado['id']}")
    assert eliminado.status_code == 200
    assert client.get("/api/detal/productos").json() == []


def test_crear_post_genera_slug(client):
    _login(client)
    response = client.post(
        "/api/admin/blog",
        json={
            "titulo": "Cómo Empezar en la Agricultura",
            "resumen": "Una guía breve.",
            "contenido": "Contenido de prueba del artículo.",
            "audiencia": "Para agricultores",
            "publicado": True,
        },
    )
    assert response.status_code == 200
    post = response.json()
    assert post["slug"] == "como-empezar-en-la-agricultura"

    publico = client.get(f"/api/blog/posts/{post['slug']}")
    assert publico.status_code == 200
    assert publico.json()["titulo"] == "Cómo Empezar en la Agricultura"


def test_slugs_duplicados_se_desambiguan(client):
    _login(client)
    payload = {
        "titulo": "Recetas con Maíz",
        "resumen": "resumen",
        "contenido": "contenido",
        "publicado": True,
    }
    p1 = client.post("/api/admin/blog", json=payload).json()
    p2 = client.post("/api/admin/blog", json=payload).json()
    assert p1["slug"] == "recetas-con-maiz"
    assert p2["slug"] == "recetas-con-maiz-2"


def test_post_no_publicado_no_aparece_en_publico(client):
    _login(client)
    creado = client.post(
        "/api/admin/blog",
        json={
            "titulo": "Borrador",
            "resumen": "resumen",
            "contenido": "contenido",
            "publicado": False,
        },
    ).json()

    assert client.get("/api/blog/posts").json() == []
    assert client.get(f"/api/blog/posts/{creado['slug']}").status_code == 404

    # pero sí debe verse en el listado de administración
    admin_lista = client.get("/api/admin/blog").json()
    assert len(admin_lista) == 1


def test_editar_post_no_cambia_el_slug(client):
    _login(client)
    creado = client.post(
        "/api/admin/blog",
        json={
            "titulo": "Título Original",
            "resumen": "resumen",
            "contenido": "contenido",
            "publicado": True,
        },
    ).json()

    editado = client.put(
        f"/api/admin/blog/{creado['id']}",
        json={
            "titulo": "Título Completamente Distinto",
            "resumen": "resumen editado",
            "contenido": "contenido editado",
            "publicado": True,
        },
    )
    assert editado.status_code == 200
    assert editado.json()["slug"] == creado["slug"]


def test_eliminar_post(client):
    _login(client)
    creado = client.post(
        "/api/admin/blog",
        json={
            "titulo": "Para Borrar",
            "resumen": "resumen",
            "contenido": "contenido",
            "publicado": True,
        },
    ).json()

    response = client.delete(f"/api/admin/blog/{creado['id']}")
    assert response.status_code == 200
    assert client.get("/api/blog/posts").json() == []


def test_upload_requiere_sesion(client):
    response = client.post(
        "/api/admin/upload", files={"archivo": ("foto.jpg", b"contenido", "image/jpeg")}
    )
    assert response.status_code == 401


def test_upload_rechaza_formato_no_soportado(client):
    _login(client)
    response = client.post(
        "/api/admin/upload",
        files={"archivo": ("archivo.txt", b"no es una imagen", "text/plain")},
    )
    assert response.status_code == 400


def test_upload_guarda_imagen_valida(client, tmp_path, monkeypatch):
    _login(client)
    import src.routers.uploads as uploads_module

    monkeypatch.setattr(uploads_module, "UPLOAD_DIR", tmp_path)

    response = client.post(
        "/api/admin/upload",
        files={"archivo": ("foto.jpg", b"\xff\xd8\xff\xe0falsojpeg", "image/jpeg")},
    )
    assert response.status_code == 200
    url = response.json()["url"]
    assert url.startswith("/uploads/")
    assert url.endswith(".jpg")
    assert (tmp_path / url.removeprefix("/uploads/")).exists()
