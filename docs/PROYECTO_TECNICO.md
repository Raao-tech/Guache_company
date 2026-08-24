# Guache Digital — Documento Técnico del Proyecto

**Web + Bot de Guache, C.A.**
_Última actualización: agosto 2026_

Este documento describe el estado actual del proyecto a nivel técnico y hacia dónde se dirige. Está pensado para cualquier desarrollador/a que se una al equipo: explica qué existe hoy, cómo levantarlo localmente, qué deuda técnica hay que tener en cuenta, y cuál es la hoja de ruta funcional. Para contexto de negocio (quién es Guache, su estrategia comercial), ver [`EMPRESA.md`](./EMPRESA.md).

---

## 1. Contexto estratégico: iniciativa "Guache 2027"

La web y el bot **no son un proyecto aislado**: son la infraestructura digital de la estrategia de negocio con la que Guache busca, para 2027, convertirse en el **proveedor principal de alimentos latinoamericanos para el hogar en España**, además de expandirse a Colombia.

Eso implica que el proyecto tiene dos etapas de alcance muy distintas:

- **Hoy:** una plataforma orientada a **Venezuela**, con foco en atención comercial B2B/mayorista (cotizaciones y un asistente conversacional).
- **Hacia 2027:** una plataforma con **venta al detal (e-commerce)** orientada a consumidor final en España y Colombia, con gestión de pedidos automatizada, un panel de administración para el equipo de Guache (sin depender de un desarrollador para actualizar contenido), y un blog como espacio de comunidad.

Cualquier decisión de arquitectura debería considerarse con ese destino en mente, sin sobre-construir antes de tiempo.

---

## 2. Estado actual del proyecto — resumen

El proyecto es un **monolito** relativamente simple: un único backend en **FastAPI** que:

1. Sirve el sitio web (HTML/CSS/JS sin framework de frontend, con secciones dinámicas que leen de la BD).
2. Expone una API REST (salud, cotizaciones, chat, catálogo "Al Detal", blog, panel de administración).
3. Corre en segundo plano un **bot de Telegram** dentro del mismo proceso.
4. Persiste datos en **Postgres en producción** (SQLite por defecto en desarrollo local), gestionado con Alembic.
5. Usa un **LLM externo (Groq)** para generar las respuestas del asistente "Guache, el zorro", tanto en la web como en Telegram.

Ya hay tests automatizados (pytest + CI/CD), un panel de administración básico (`/admin`, una sola cuenta compartida — §4.7) y un blog gestionable desde ahí. Sigue sin haber tienda/checkout real ni sistema de usuarios con roles múltiples — eso sigue siendo trabajo futuro de la visión 2027 (§8).

---

## 3. Estructura del repositorio

```
Project_0/
├── main.py                     # App FastAPI: endpoints, lifespan, montaje de estáticos
├── requirements.txt            # Dependencias de producción
├── requirements-dev.txt        # + dependencias de desarrollo (pytest)
├── pytest.ini                  # Configuración de pytest
├── tests/                      # Suite de tests (pytest + TestClient)
├── .env / .env.example         # Variables de entorno (tokens, claves)
├── cotizaciones.db             # Base de datos SQLite (local, generada en runtime, NO versionada — ver §7)
├── alembic.ini                 # Configuración de Alembic (migraciones de BD)
├── alembic/
│   ├── env.py                    # Usa el motor/modelo reales de src/database.py
│   └── versions/                 # Migraciones (una por cambio de esquema)
├── src/
│   ├── config.py                # Carga y valida variables de entorno
│   ├── database.py              # Motor SQLAlchemy + modelos + get_db compartido
│   ├── routers/
│   │   ├── admin_auth.py          # Login/logout de sesión + require_admin_session/require_full_admin_role
│   │   ├── uploads.py             # Subida de imágenes del panel
│   │   ├── productos.py           # CRUD del catálogo "Al Detal"
│   │   ├── blog.py                # CRUD de artículos del blog
│   │   └── usuarios.py            # CRUD de cuentas del panel (solo rol admin)
│   ├── bots/
│   │   └── telegram_bot.py      # Bot de Telegram (python-telegram-bot)
│   └── services/
│       └── llm_service.py       # Cliente Groq + prompt del asistente "Guache"
├── web/
│   ├── index.html               # Landing page: hero, servicios, rubros, mayorista, detal (dinámico), blog (teaser), cotizar
│   ├── app.js                   # Cotización, chat, menú móvil, render de detal/blog (fetch a la API)
│   ├── styles.css               # Estilos (incluye .media-slot, ver §4.5)
│   ├── uploads/                 # Imágenes subidas desde el panel (NO versionado, ver §4.7)
│   ├── admin/                   # Panel de administración (ver §4.7)
│   │   ├── login.html / admin.js / admin.css
│   │   ├── index.html             # Dashboard
│   │   ├── productos.html         # Gestión del catálogo "Al Detal"
│   │   ├── blog.html              # Gestión del blog
│   │   └── usuarios.html          # Gestión de cuentas (solo visible/accesible para rol admin)
│   └── blog/
│       ├── index.html             # Listado de artículos (dinámico, fetch a /api/blog/posts)
│       └── post.html              # Plantilla única para cualquier artículo (dinámico por slug)
├── deploy/
│   ├── agroguache.nginx           # Config de Nginx para el VPS de producción
│   ├── agroguache.service         # Unit de systemd para correr uvicorn
│   ├── backup_db.py               # Backup seguro + rotación de cotizaciones.db
│   ├── agroguache-backup.service  # Unit de systemd (oneshot) para el backup
│   ├── agroguache-backup.timer    # Timer de systemd: corre el backup a diario
│   ├── migrate_sqlite_to_postgres.py  # Migración única de datos SQLite -> Postgres
│   ├── remote_deploy.sh           # Script que ejecuta el pipeline de CD en el VPS (ver §4.6)
│   ├── seed_blog.py                # Carga los 4 artículos de ejemplo en la BD (idempotente)
│   └── seed_usuarios.py            # Crea las cuentas iniciales del panel (idempotente)
└── docs/
    ├── EMPRESA.md                # Perfil corporativo (negocio)
    └── PROYECTO_TECNICO.md       # Este documento
```

---

## 4. Componentes actuales en detalle

### 4.1 Backend — `main.py`

App FastAPI (`Agroindustria Guache API`) con un `lifespan` que:

- Al arrancar: inicializa el bot de Telegram con `polling` en segundo plano dentro del mismo proceso (el esquema de la BD lo gestiona Alembic, no el lifespan — ver §4.2).
- Al apagar: detiene el bot de Telegram limpiamente.

**Endpoints actuales:**

| Método | Ruta | Descripción | Auth |
|---|---|---|---|
| `GET` | `/api/health` | Health check simple. | No |
| `POST` | `/api/cotizar` | Registra una cotización (nombre, teléfono, empresa, SKU, cantidad en toneladas, destino, observaciones) en SQLite y devuelve un folio único. | No |
| `GET` | `/api/cotizaciones` | Devuelve el listado completo de cotizaciones registradas. | **Sí — HTTP Basic Auth** (`ADMIN_USERNAME` / `ADMIN_PASSWORD`) |
| `POST` | `/api/chat` | Envía un mensaje al asistente "Guache" y devuelve la respuesta generada por el LLM. | No |
| `/` (estático) | Sirve `web/` como sitio estático (SPA de una sola página). | — |

CORS restringido vía `ALLOWED_ORIGINS` en `.env` (lista separada por comas). Por defecto solo permite `localhost`/`127.0.0.1:8000` para desarrollo — en producción debe definirse con el dominio real del sitio.

Los endpoints del panel de administración (`/api/admin/*`, `/api/detal/*`, `/api/blog/*`) viven en `src/routers/` (montados en `main.py` vía `include_router`), no en esta tabla — ver §4.7.

### 4.2 Base de datos — `src/database.py`

SQLAlchemy con un único modelo:

- **`CotizacionDB`** — `id`, `folio` (único, ej. `COT-2026-A1B2C3D4`), `nombre_contacto`, `telefono`, `empresa` (opcional), `sku_producto`, `cantidad_toneladas`, `destino_despacho`, `observaciones` (opcional), `fecha_registro`.

**Motor (SQLite / Postgres):** `SQLALCHEMY_DATABASE_URL` se toma de la variable de entorno `DATABASE_URL`; si no está definida, usa SQLite local (`sqlite:///./cotizaciones.db`) — así el desarrollo local no requiere tener Postgres instalado. **Producción corre en Postgres desde el 17 de agosto de 2026** (instalado nativo en el mismo VPS, base `agroguache`, usuario `agroguache_user`), con `DATABASE_URL` definida en el `.env` del servidor. `cotizaciones.db` se dejó en el VPS (`/var/www/agroguache/` y una copia extra en `/root/pre_deploy_backups/`) como respaldo de los datos previos a la migración, pero ya no lo usa la app.

**Migraciones (Alembic):** el esquema no se crea con `create_all()` al arrancar — se gestiona con Alembic (`alembic/`, configurado en `alembic/env.py` para usar el mismo `Base`/URL que `src/database.py`, una única fuente de verdad, funciona igual para SQLite y Postgres). Cualquier cambio de columna/tabla debe ir acompañado de una migración nueva (`alembic revision -m "..."`, editar `upgrade()`/`downgrade()`).

### 4.3 Bot de Telegram — `src/bots/telegram_bot.py`

Construido con `python-telegram-bot`. Maneja:

- `/start` → mensaje de bienvenida fijo.
- Cualquier texto → se reenvía al mismo servicio LLM (`generar_respuesta_llm`) que usa el chat web, y se responde con el resultado.

El bot comparte lógica y prompt con el chat de la web — hoy es, en esencia, el mismo asistente en dos canales distintos, sin memoria de conversación persistida en Telegram (cada mensaje se procesa de forma independiente, a diferencia del chat web que sí arma un historial en el cliente — ver §4.5).

### 4.4 Servicio LLM — `src/services/llm_service.py`

Usa el cliente oficial de **Groq** (`AsyncGroq`), modelo `openai/gpt-oss-20b`. El prompt de sistema (`SYSTEM_PROMPT`) define:

- Identidad del asistente: "Guache", asistente comercial de Agroindustria Guache C.A. (fundada 1998, Acarigua, Portuguesa).
- Datos operativos de planta (capacidad, horarios, contacto).
- Catálogo de productos con SKUs (harinas, aceites, alimento balanceado, agroinsumos, subproductos).
- Reglas de tono y de manejo de precios (siempre remitir a cotización, nunca dar precio fijo).

> ⚠️ **Nota para quien continúe el proyecto:** este `SYSTEM_PROMPT` describe el catálogo B2B/mayorista actual (harinas, alimento balanceado a granel). Es contenido **hardcodeado en el código**, no editable sin un despliegue. A medida que avance la estrategia de detal (España/Colombia) y el panel de administración (§6.2), este prompt debería poder actualizarse sin tocar código — hoy es una limitación conocida, no un diseño final.

> ⚠️ **Riesgo conocido — modelos de Groq cambian con el tiempo:** el 17 de agosto de 2026 el bot dejó de responder porque Groq dio de baja `llama-3.1-8b-instant` (el modelo usado hasta ese momento) — devolvía `404 model_not_found`. Se reemplazó por `openai/gpt-oss-20b` tras probarlo contra el `SYSTEM_PROMPT` real (formato, regla de "nunca dar precio fijo", velocidad ~1s). El nombre del modelo está hardcodeado en `llm_service.py`; si el bot vuelve a devolver el mensaje genérico de error ("hay una revolución de manadas Guache..."), lo primero a revisar es si Groq deprecó el modelo actual — `client.models.list()` del SDK de Groq devuelve los modelos vigentes en la cuenta.

### 4.5 Frontend web — `web/`

Sitio estático, sin build step, sin framework, sin gestor de paquetes de frontend — HTML/CSS/JS plano servido directamente por FastAPI vía `StaticFiles`. Desde agosto de 2026, `index.html` dejó de ser una sola sección de catálogo y pasó a cubrir todo el recorrido comercial (mayorista, servicios, detal en preview) más un blog en páginas separadas.

**`index.html` (secciones, en orden):**
- **Hero** con propuesta de valor y estadísticas de planta.
- **Servicios** (`#servicios`) — almacenamiento, asesoramiento técnico, venta de maquinaria (contenido de `EMPRESA.md` §6.3).
- **Rubros** (`#rubros`) — café, maíz, cacao, cebada, arroz (`EMPRESA.md` §6.1).
- **Catálogo al mayor** (`#productos`) — tarjetas de producto con SKU, hardcodeadas (sigue así a propósito, ver §4.7 — nunca muestra precio fijo).
- **Al Detal** (`#detal`) — desde agosto de 2026, **catálogo real y dinámico**, administrable desde el panel (§4.7): `app.js` pide `GET /api/detal/productos` y renderiza tarjetas con nombre, descripción, precio/moneda e imagen. Si todavía no hay productos cargados, se muestra el preview estático original ("muy pronto en España y Colombia"). Sigue sin carrito ni checkout — el CTA abre el chat.
- **Blog (teaser)** (`#blog`) — dinámico, `GET /api/blog/posts` (últimos 4 publicados).
- **Formulario de cotización** (`#cotizar`) → `POST /api/cotizar`.
- **Footer** — contacto, navegación, estados con presencia.

**Widget de chat flotante** ("Guache el zorro") con chips de sugerencia rápida → `POST /api/chat`, presente en todas las páginas (home, blog y panel de administración). El historial de conversación se mantiene solo en memoria del navegador (`chatHistory` en `app.js`), no se persiste en el backend.

**Menú móvil:** a partir de 768px de ancho, la navegación colapsa a un botón hamburguesa (`inicializarMenuMovil()` en `app.js`); no depende de ningún framework, es toggle de clase CSS + `aria-expanded`.

**`web/blog/`** — desde agosto de 2026, **dinámico y respaldado por base de datos** (tabla `blog_posts`, gestionable desde §4.7). `index.html` pide `GET /api/blog/posts` y renderiza las tarjetas; `post.html` es una única plantilla que sirve para cualquier artículo — lee el slug de la URL (`GET /blog/{slug}`, ruteado en `main.py` antes del mount de estáticos) y pide `GET /api/blog/posts/{slug}`. El contenido se guarda como texto plano con un formato mínimo tipo markdown (`## ` para subtítulos, `**texto**` para negrita, líneas `- ` para listas, línea en blanco = párrafo nuevo) que `formatearContenido()` convierte a HTML **después** de escapar el texto (evita que un título con `<` rompa la página). Los 4 artículos que antes eran archivos HTML sueltos ahora son las primeras 4 filas de `blog_posts`, cargadas por `deploy/seed_blog.py` (idempotente, corre en cada deploy).

**Sin imágenes reales por defecto:** en vez de fotos, los espacios visuales usan `.media-slot` (definido en `styles.css`) — un div con degradado de marca + un ícono/emoji centrado. Si un producto o artículo tiene `imagen_url` (subida desde el panel, §4.7), se inserta una `<img>` real ahí mismo (`object-fit: cover` la hace encajar sin romper el diseño); si no, se ve el ícono. No hace falta rediseñar nada al empezar a cargar fotos.

### 4.6 Despliegue — `deploy/`

- **`agroguache.service`** — unit de systemd que corre `uvicorn main:app` con 2 workers, como usuario `root`, en un VPS.
- **`agroguache.nginx`** — Nginx sirve `styles.css` y `app.js` directamente como estáticos (por performance) y hace proxy del resto del tráfico a FastAPI en `127.0.0.1:8000`.
- **`backup_db.py` + `agroguache-backup.service` + `agroguache-backup.timer`** — backup diario de `cotizaciones.db` (ver más abajo).

**Producción:** el sitio corre en un VPS (antes accesible solo por IP `93.189.88.76`) y desde agosto 2026 responde en **https://guache.online** (y `www.guache.online`), con certificado TLS de Let's Encrypt vía Certbot (autorenovación configurada, vence 2026-11-12).

> ⚠️ **Nota:** Certbot modifica la config de Nginx directamente en el servidor (agregó los bloques HTTPS y las rutas del certificado). `deploy/agroguache.nginx` ya está sincronizado (agosto 2026) con el archivo real del VPS (`/etc/nginx/sites-enabled/agroguache`) — si Certbot vuelve a tocarlo (ej. al renovar o agregar un subdominio), hay que repetir la sincronización a mano, ya que Certbot no versiona sus cambios.

**CI/CD (agosto 2026):** `.github/workflows/ci-cd.yml` tiene dos jobs:
1. `test` — corre `pytest` en cada push y PR a `main`.
2. `deploy` — solo en push directo a `main` (no en PRs) y solo si `test` pasó. Se conecta por SSH al VPS con una llave dedicada (`secrets.VPS_SSH_DEPLOY_KEY`, privada, vive únicamente en GitHub Secrets) y ejecuta `deploy/remote_deploy.sh` en el servidor: `git fetch` + `merge --ff-only` (nunca sobreescribe cambios locales sin avisar — si el merge no es fast-forward, el deploy falla en vez de descartar algo), reinstala dependencias, corre `alembic upgrade head`, corre los scripts de siembra (`seed_blog.py`, `seed_usuarios.py`), **verifica que la siembra realmente haya insertado los datos esperados** (assert de conteo mínimo — el 19 de agosto un deploy corrió `seed_usuarios.py` sin error pero no creó ningún usuario, causa nunca determinada, y el pipeline igual reportó éxito; esta verificación existe para que eso sea un fallo visible, no algo que haya que descubrir probando a mano después), reinicia `agroguache.service` y verifica `/api/health` antes de reportar éxito.

La llave de deploy está restringida en el `authorized_keys` del VPS con un **forced command** (`command="/var/www/agroguache/deploy/remote_deploy.sh"`): sin importar qué comando le pida el cliente SSH, el servidor solo va a correr ese script — aunque la clave privada se filtrara, no permite ejecutar comandos arbitrarios en el servidor. No hay contenedor Docker todavía; el deploy sigue siendo directo sobre el filesystem del VPS vía git.

**Backups:** `deploy/backup_db.py` detecta el motor vía `DATABASE_URL` y respalda con el método correcto — API de backup online de `sqlite3` en desarrollo local (no una copia cruda — no corrompe el archivo aunque la app esté escribiendo), `pg_dump -F c` (formato comprimido, restaurable con `pg_restore`) en producción. Guarda el resultado en `/var/backups/agroguache/`, con rotación automática (borra respaldos de más de 14 días). Corre una vez al día vía un timer de systemd. Es un backup **local al VPS** — protege contra una migración/deploy que rompa datos, pero no contra la pérdida total del servidor; si en el futuro se necesita eso, hay que sumar una copia off-site (ver §8.6).

Setup en el VPS (una sola vez):
```bash
sudo cp deploy/agroguache-backup.service deploy/agroguache-backup.timer /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now agroguache-backup.timer
```

Verificar que quedó agendado y correr uno manual para probar:
```bash
systemctl list-timers agroguache-backup.timer
sudo systemctl start agroguache-backup.service   # corre un backup ya mismo, para probar
ls -la /var/backups/agroguache/
```

Restaurar un backup (con el servicio parado, para no escribir mientras se restaura):
```bash
sudo systemctl stop agroguache.service
sudo cp /var/backups/agroguache/cotizaciones_<fecha>.db /var/www/agroguache/cotizaciones.db
sudo systemctl start agroguache.service
```

### 4.7 Panel de administración — `/admin`, `src/routers/`

Permite a personas sin conocimientos técnicos actualizar el catálogo "Al Detal" y el blog sin tocar código ni pedirle nada a un desarrollador. Vive completamente en el mismo backend (sin servicio aparte).

**Autenticación:** sesión por cookie firmada (`starlette.middleware.sessions.SessionMiddleware`, `SESSION_SECRET_KEY` en `.env`). Login en `POST /api/admin/login` (`src/routers/admin_auth.py`), dependencia `require_admin_session` protege el resto de las rutas `/api/admin/*`. Dos formas de autenticarse, evaluadas en ese orden:
1. **Cuenta compartida de respaldo** (`ADMIN_USERNAME` / `ADMIN_PASSWORD` en `.env`) — la misma que protege `GET /api/cotizaciones` por HTTP Basic. Rol implícito `admin`.
2. **Usuarios individuales** (tabla `usuarios`, agosto 2026) — cada persona con su propia cuenta y clave (hasheada con `bcrypt`, nunca en texto plano). Dos roles:
   - `admin` — permisos totales, incluida la gestión de otros usuarios.
   - `asistente` — puede hacer todo lo demás (catálogo, blog, subir imágenes) pero **no** puede crear, editar ni borrar usuarios — lo bloquea la dependencia `require_full_admin_role` (`src/routers/admin_auth.py`) con `403 Forbidden`.

**Páginas** (`web/admin/`, todas con `<meta name="robots" content="noindex, nofollow">`):
- `login.html` — formulario de acceso.
- `index.html` — dashboard con accesos directos y conteos rápidos.
- `productos.html` — lista + formulario del catálogo "Al Detal" (nombre, descripción, precio, moneda —USD/EUR/USDT/BTC/VES/COP o "otra" a texto libre—, imagen opcional, visible/oculto, orden).
- `blog.html` — lista + formulario de artículos (título, resumen, contenido, a quién está dirigido, imagen de portada, publicado/borrador).
- `usuarios.html` — lista + formulario de cuentas (usuario, clave, rol, activo/inactivo). Solo rol `admin`: el link de navegación se oculta para `asistente` (`data-solo-admin` en `admin.js`) y la página redirige si igual entra por URL directa — la protección real de todos modos es del lado del servidor (`require_full_admin_role`), esto es solo UX.

Ninguna página HTML está protegida a nivel de archivo (`StaticFiles` las sirve igual que cualquier otra); la protección real está en que su JS llama a `requerirSesion()` al cargar (redirige a `login.html` si no hay sesión) y en que **todas** las rutas `/api/admin/*` exigen sesión.

**Subida de imágenes** (`POST /api/admin/upload`, `src/routers/uploads.py`): guarda el archivo en `web/uploads/` (no versionado, ver `.gitignore`) con un nombre aleatorio — la extensión se decide por el `content-type` validado, nunca por el nombre que manda el navegador. Límite de **2 MB por imagen**: el VPS tiene poco espacio en disco (~500 MB libres a agosto de 2026), vale la pena vigilarlo si se suben muchas fotos.

**CRUD administrable** (`src/routers/productos.py`, `src/routers/blog.py`, `src/routers/usuarios.py`): endpoints públicos de solo lectura (`GET /api/detal/productos`, `GET /api/blog/posts[/​{slug}]` — solo devuelven ítems activos/publicados) y endpoints `/api/admin/...` con CRUD completo. El slug de un post se genera una sola vez al crearlo (a partir del título, desambiguado con `-2`, `-3`... si se repite) y **no cambia** aunque se edite el título después — mantiene estables los links ya compartidos.

**Cuentas iniciales** (`deploy/seed_usuarios.py`, idempotente, corre en cada deploy — no pisa cuentas ya creadas): `Developer_1` y `Senaida` con rol `admin`, `Assistent_1` con rol `asistente`. Cambiar o rotar esas claves se hace desde `usuarios.html` una vez logueado como `admin`, no editando el script.

---

## 5. Stack tecnológico

| Capa | Tecnología |
|---|---|
| Backend / API | Python 3.14, FastAPI, Uvicorn |
| Validación de datos | Pydantic v2 |
| Base de datos | SQLAlchemy ORM + Alembic. SQLite en desarrollo local; Postgres (driver `psycopg` v3) en producción vía `DATABASE_URL` |
| Tests | pytest + `fastapi.testclient` |
| Sesiones (panel admin) | `starlette.middleware.sessions` (cookies firmadas, `itsdangerous`) |
| Subida de archivos | `python-multipart` (requerido por `UploadFile` de FastAPI) |
| Bot conversacional | python-telegram-bot |
| LLM / IA | Groq API (`openai/gpt-oss-20b`) |
| Frontend | HTML5 + CSS3 + JavaScript vanilla (sin framework) |
| Servidor web / proxy | Nginx |
| Gestión de proceso | systemd |
| Entorno | `venv` + `.env` (via `python-dotenv`) |

---

## 6. Cómo levantar el proyecto en local

```bash
# 1. Clonar y entrar al repo, crear entorno virtual
python3 -m venv venv
source venv/bin/activate

# 2. Instalar dependencias
pip install -r requirements.txt

# 3. Configurar variables de entorno
cp .env.example .env
# Completar TELEGRAM_BOT_TOKEN, GROQ_API_KEY, ADMIN_USERNAME, ADMIN_PASSWORD
# y SESSION_SECRET_KEY en .env (esta última: python3 -c "import secrets; print(secrets.token_hex(32))")

# 4. Aplicar migraciones (crea/actualiza el esquema de cotizaciones.db)
alembic upgrade head

# 5. (Opcional) Cargar los 4 artículos de ejemplo del blog y las cuentas iniciales del panel
python deploy/seed_blog.py
python deploy/seed_usuarios.py

# 6. Levantar el servidor (web + API + bot de Telegram)
uvicorn main:app --reload --port 8000
```

Para desarrollo (incluye pytest) instalar en su lugar `requirements-dev.txt`:

```bash
pip install -r requirements-dev.txt
pytest
```

Los tests usan una base de datos SQLite temporal aislada (no tocan `cotizaciones.db`) y deshabilitan el bot de Telegram — no requieren red ni tokens reales, salvo las variables de entorno de `.env` (necesarias porque `src/config.py` falla al importar si faltan).

- La web queda disponible en `http://localhost:8000`.
- Documentación interactiva de la API (Swagger, autogenerada por FastAPI) en `http://localhost:8000/docs`.
- Si no se configura `TELEGRAM_BOT_TOKEN`, `GROQ_API_KEY`, `ADMIN_USERNAME`, `ADMIN_PASSWORD` o `SESSION_SECRET_KEY`, la app **falla al arrancar** (`src/config.py` lanza `ValueError`) — las cinco son obligatorias hoy, no opcionales.
- `GET /api/cotizaciones` pide usuario/clave (HTTP Basic Auth) — usa las credenciales `ADMIN_USERNAME` / `ADMIN_PASSWORD` definidas en `.env`.
- Panel de administración en `http://localhost:8000/admin/login.html` — mismas credenciales `ADMIN_USERNAME` / `ADMIN_PASSWORD` (ver §4.7).
- **Si ya tenías una `cotizaciones.db` creada antes de que existieran las migraciones** (con las tablas ya presentes), no corras `alembic upgrade head` sobre ella directamente — fallaría porque la tabla ya existe. En su lugar, corré `alembic stamp head` una única vez para decirle a Alembic "esta base ya está al día", sin tocar los datos. Esto aplica en particular al **VPS de producción** al desplegar este cambio por primera vez.

---

## 7. Deuda técnica y riesgos conocidos

Para quien se una al proyecto, esto es lo que hay que tener en cuenta **antes de construir features nuevas encima**:

1. ~~`GET /api/cotizaciones` sin autenticación~~ — **Resuelto (agosto 2026).** Protegido con HTTP Basic Auth (`ADMIN_USERNAME` / `ADMIN_PASSWORD`, ver `main.py::verificar_admin`). Es una solución mínima apropiada para el estado actual del proyecto (sin usuarios/roles) — cuando exista el panel de administración (§8.2) esto debería migrar a un sistema de sesiones/roles real.
2. ~~CORS abierto (`allow_origins=["*"]`)~~ — **Resuelto (agosto 2026).** Ahora configurable vía `ALLOWED_ORIGINS` en `.env`. La web y la API comparten origen (mismo dominio, FastAPI sirve ambos), así que esto no bloquea el uso normal del sitio — igual conviene setear `ALLOWED_ORIGINS=https://guache.online,https://www.guache.online` en el `.env` del VPS explícitamente (hoy sigue con el default de `localhost`, solo funciona por ser same-origin, no por estar bien configurado).
3. ~~Sin autenticación de usuarios/roles~~ — **Resuelto (agosto 2026).** Tabla `usuarios` con cuentas individuales, clave hasheada (`bcrypt`) y dos roles (`admin` / `asistente`, ver §4.7). La cuenta compartida `ADMIN_USERNAME`/`ADMIN_PASSWORD` se mantiene como respaldo, no se retiró. **Sigue pendiente:** los roles solo distinguen "gestiona usuarios" vs. "no gestiona usuarios" — no hay permisos más finos (ej. "puede editar blog pero no catálogo"), agregar solo si aparece una necesidad real.
4. ~~Sin migraciones de base de datos~~ — **Resuelto (agosto 2026).** Esquema gestionado con Alembic (ver §4.2 y §6). **Pendiente:** correr `alembic stamp head` una vez en el VPS de producción al desplegar este cambio (la tabla ya existe ahí, creada previamente con `create_all()`).
5. ~~SQLite en un solo archivo~~ — **Resuelto (17 de agosto de 2026).** Producción corre en Postgres (§4.2). Corte hecho con downtime de ~30 segundos; los 8 registros existentes migraron sin pérdida ni colisión de IDs (verificado fila por fila antes de dar el visto bueno).
6. ~~Dependencia sin usar (`google-genai`, `google-auth`)~~ — **Resuelto (agosto 2026).** Se eliminaron de `requirements.txt` junto con sus dependencias transitivas exclusivas (`cryptography`, `cffi`, `pycparser`, `pyasn1`, `pyasn1_modules`). El servicio LLM usa únicamente Groq.
7. **Prompt del asistente hardcodeado** (§4.4) — no editable sin desplegar código nuevo.
8. ~~Sin tests automatizados~~ — **Resuelto parcialmente (agosto 2026).** Suite básica con `pytest` + `TestClient` en `tests/` cubriendo health check, registro y listado de cotizaciones (incl. auth), y chat (con LLM mockeado). Falta cobertura de `src/bots/telegram_bot.py` y de los casos límite de `src/services/llm_service.py`.
9. ~~Sin CI/CD~~ — **Resuelto (agosto 2026).** `.github/workflows/ci-cd.yml` corre `pytest` en cada push/PR a `main` (job `test`) y, si pasa y es un push directo a `main`, despliega automáticamente al VPS (job `deploy`, ver §4.6).
10. **Historial de chat no persistido** — se pierde al recargar la página; no hay forma de dar seguimiento a una conversación de un cliente.

---

## 8. Roadmap técnico hacia 2027

### 8.1 Tienda / venta al detal (e-commerce)

Hoy el sitio solo permite **cotizar al mayor**, más una sección de **preview** (`#detal` en `index.html`, agosto 2026) que presenta la categoría de productos que vendrá y deriva al chat — sin carrito, sin checkout, sin precios de detal (a propósito: no hay backend que los soporte todavía). La estrategia de negocio requiere ir más allá de ese preview y permitir que el consumidor final **compre directamente** ciertos productos (presentaciones de detal: café, cacao, harinas, arroz, etc.).

Implica, como mínimo:
- Modelo de datos de catálogo (productos de detal, precios, stock, imágenes) — independiente del catálogo mayorista actual.
- Carrito de compra y checkout.
- Integración de pasarela de pago apta para España/Colombia (ej. Stripe, Redsys, PayU, PayPal).
- Cálculo de envío internacional / logística de última milla — a definir con negocio.
- Multi-moneda (EUR, COP, USD) y probablemente multi-idioma/variante regional del español.

### 8.2 Panel de administración (CMS interno)

**Primera versión hecha (agosto 2026)** — ver §4.7. Una sola persona, sin conocimientos técnicos, puede desde `/admin`:
- Agregar/editar/ocultar/borrar productos y servicios del catálogo "Al Detal" (nombre, descripción, precio en la moneda que elija, imagen opcional).
- Escribir, editar y publicar/despublicar artículos del blog.

**Lo que todavía queda hardcodeado** (no forma parte de esta primera versión): el Hero, la sección de Servicios, Rubros, y el catálogo mayorista con SKUs (`index.html`) — editar esos textos sigue requiriendo un cambio de código y un deploy. Tampoco hay gestión de cotizaciones/pedidos desde el panel (`GET /api/cotizaciones` sigue siendo solo una vista protegida por HTTP Basic, sin UI). Y sigue sin haber **roles** — es una sola cuenta de administrador compartida (ver §7 ítem 3), suficiente mientras sea una sola persona la que administra.

### 8.3 Blog / centro de contenido

**Hecho (agosto 2026)** — el blog dejó de ser HTML estático y pasa por la base de datos (`blog_posts`, gestionable desde el panel, §4.7). Los 4 artículos de ejemplo originales (uno por tipo de cliente de `EMPRESA.md` §8) se migraron a la BD vía `deploy/seed_blog.py`. Lo que falta para que sea un "centro de contenido" completo: autoría múltiple (hoy no hay concepto de autor, todo es "Guache"), categorías/tags reales (hoy es un campo de texto libre llamado "audiencia"), y comentarios o algún espacio de interacción con la comunidad — nada de eso está planeado todavía, agregar solo si hay necesidad real.

### 8.4 Automatización de pedidos vía bot

Hoy el bot de Telegram es puramente conversacional (preguntas y respuestas vía LLM). La visión 2027 apunta a que el bot pueda **gestionar pedidos de forma activa**: iniciar y dar seguimiento a un pedido, notificar estados, y potencialmente ampliarse a otros canales (ej. WhatsApp Business API, relevante para el mercado español/colombiano donde WhatsApp es el canal dominante, más que Telegram).

### 8.5 Internacionalización

Adaptar textos, catálogo y tono de marca a España y Colombia, manteniendo la identidad "alimento tradicional latinoamericano". Incluye decisiones de producto (¿un solo sitio multi-región o instancias separadas?) que deben definirse junto con negocio antes de implementar.

### 8.6 Infraestructura y escalabilidad

- ~~Evaluar migración de SQLite → PostgreSQL~~ — **Hecho (17 de agosto de 2026).** Postgres instalado nativo en el mismo VPS (decisión tomada por costo). Referencia de los pasos que se corrieron como `root`, por si hay que repetir el proceso en otro entorno:

  ```bash
  # 1. Instalar Postgres
  sudo apt update && sudo apt install -y postgresql

  # 2. Crear base y usuario de la app
  sudo -u postgres psql -c "CREATE DATABASE agroguache;"
  sudo -u postgres psql -c "CREATE USER agroguache_user WITH PASSWORD 'elegir-una-clave-segura';"
  sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE agroguache TO agroguache_user;"
  sudo -u postgres psql -d agroguache -c "GRANT ALL ON SCHEMA public TO agroguache_user;"

  # 3. Backup extra de cotizaciones.db fuera del repo, y parar la app
  cp cotizaciones.db /root/pre_deploy_backups/cotizaciones_pre_postgres_$(date +%F_%H%M%S).db
  sudo systemctl stop agroguache.service

  # 4. En /var/www/agroguache, con el venv activado y el código ya actualizado:
  export DATABASE_URL="postgresql+psycopg://agroguache_user:elegir-una-clave-segura@localhost:5432/agroguache"
  alembic upgrade head                              # crea el esquema en Postgres
  python deploy/migrate_sqlite_to_postgres.py        # copia los datos existentes
  # verificar fila por fila antes de seguir (ver test del script)

  # 5. Agregar DATABASE_URL (la misma de arriba) al .env de producción, permanentemente

  # 6. Levantar la app de nuevo — ya va a leer DATABASE_URL del .env
  sudo systemctl start agroguache.service
  ```

  `cotizaciones.db` se dejó en el VPS como respaldo (más una copia en `/root/pre_deploy_backups/`), sin borrar — la app ya no lo usa.

- ~~CI/CD~~ — **Hecho (agosto 2026).** Ver §4.6 para el detalle del pipeline.
- ~~Backups automáticos de base de datos~~ — **Resuelto (agosto 2026).** `backup_db.py` reescrito para detectar el motor y usar `pg_dump` en Postgres (§4.6), timer de systemd instalado y corriendo en el VPS. Sigue faltando la **copia off-site** (protege contra migración/deploy que rompa datos, no contra perder el VPS entero) — agregar si/cuando se justifique el costo y complejidad extra.
- **Espacio en disco del VPS, a vigilar.** A agosto de 2026 quedan ~500 MB libres (instalar Postgres ya usó buena parte). Las imágenes del panel de administración (§4.7) suman a este límite (2 MB por imagen, sin límite de cantidad todavía) — si se cargan muchas fotos, conviene revisar espacio disponible (`df -h`) antes de que se llene, o mover a almacenamiento externo si el catálogo crece mucho.
- Contenerización (Docker) para reducir fricción entre entornos de desarrollo/producción, si el equipo crece.

---

## 9. Cómo contribuir

1. Revisar este documento y [`EMPRESA.md`](./EMPRESA.md) para entender negocio + estado técnico.
2. Levantar el proyecto en local (§6).
3. Antes de tomar una tarea del roadmap (§8), verificar si depende de resolver primero algún punto de deuda técnica (§7) — en particular, **autenticación** es prerrequisito de casi todo lo nuevo (panel admin, gestión de pedidos, protección de datos de clientes).
4. Mantener la separación de responsabilidades actual del repo (`src/services` para lógica externa/IA, `src/bots` para canales conversacionales, `src/database.py` para persistencia) al agregar nuevos módulos.
5. Correr `pytest` (`pip install -r requirements-dev.txt`) antes de subir cambios, y agregar tests para el código nuevo en `tests/`.
6. Si el cambio modifica columnas/tablas de `CotizacionDB`, generar la migración correspondiente (`alembic revision -m "..."`) en el mismo cambio — no editar el esquema a mano.

---

_Este documento debe actualizarse a medida que el proyecto avance. Si una sección queda desactualizada respecto al código, el código manda — actualizar este documento en el mismo cambio._
