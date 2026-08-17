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

1. Sirve el sitio web estático (HTML/CSS/JS, sin framework de frontend).
2. Expone una API REST (salud, cotizaciones, chat).
3. Corre en segundo plano un **bot de Telegram** dentro del mismo proceso.
4. Persiste datos en **SQLite** (un solo archivo, `cotizaciones.db`).
5. Usa un **LLM externo (Groq)** para generar las respuestas del asistente "Guache, el zorro", tanto en la web como en Telegram.

No hay frontend framework, no hay autenticación, no hay panel de administración, no hay tienda/checkout, no hay blog y no hay tests automatizados. Es, deliberadamente, un MVP comercial (cotizaciones + asistente conversacional) sobre el que se construirá el resto de la visión 2027.

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
│   ├── database.py              # Motor SQLAlchemy + modelo CotizacionDB
│   ├── bots/
│   │   └── telegram_bot.py      # Bot de Telegram (python-telegram-bot)
│   └── services/
│       └── llm_service.py       # Cliente Groq + prompt del asistente "Guache"
├── web/
│   ├── index.html               # Landing page (una sola página)
│   ├── app.js                   # Lógica de cotización y chat (fetch a la API)
│   ├── styles.css               # Estilos
│   └── assets/                  # (vacío por ahora)
├── deploy/
│   ├── agroguache.nginx           # Config de Nginx para el VPS de producción
│   ├── agroguache.service         # Unit de systemd para correr uvicorn
│   ├── backup_db.py               # Backup seguro + rotación de cotizaciones.db
│   ├── agroguache-backup.service  # Unit de systemd (oneshot) para el backup
│   └── agroguache-backup.timer    # Timer de systemd: corre el backup a diario
└── docs/
    ├── EMPRESA.md                # Perfil corporativo (negocio)
    └── PROYECTO_TECNICO.md       # Este documento
```

---

## 4. Componentes actuales en detalle

### 4.1 Backend — `main.py`

App FastAPI (`Agroindustria Guache API`) con un `lifespan` que:

- Al arrancar: crea las tablas de SQLite (`Base.metadata.create_all`) e inicializa el bot de Telegram con `polling` en segundo plano dentro del mismo proceso.
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

### 4.2 Base de datos — `src/database.py`

SQLite vía SQLAlchemy, un único modelo:

- **`CotizacionDB`** — `id`, `folio` (único, ej. `COT-2026-A1B2C3D4`), `nombre_contacto`, `telefono`, `empresa` (opcional), `sku_producto`, `cantidad_toneladas`, `destino_despacho`, `observaciones` (opcional), `fecha_registro`.

**Migraciones (Alembic):** el esquema ya no se crea con `create_all()` al arrancar — se gestiona con Alembic (`alembic/`, configurado en `alembic/env.py` para usar el mismo `Base`/URL que `src/database.py`, una única fuente de verdad). Cualquier cambio de columna/tabla debe ir acompañado de una migración nueva (`alembic revision -m "..."`, editar `upgrade()`/`downgrade()`).

No hay sistema de migraciones (Alembic u otro): el esquema se crea con `create_all()` al arrancar, lo cual funciona para el MVP pero no es viable en cuanto haya que versionar cambios de esquema en producción con datos reales.

### 4.3 Bot de Telegram — `src/bots/telegram_bot.py`

Construido con `python-telegram-bot`. Maneja:

- `/start` → mensaje de bienvenida fijo.
- Cualquier texto → se reenvía al mismo servicio LLM (`generar_respuesta_llm`) que usa el chat web, y se responde con el resultado.

El bot comparte lógica y prompt con el chat de la web — hoy es, en esencia, el mismo asistente en dos canales distintos, sin memoria de conversación persistida en Telegram (cada mensaje se procesa de forma independiente, a diferencia del chat web que sí arma un historial en el cliente — ver §4.5).

### 4.4 Servicio LLM — `src/services/llm_service.py`

Usa el cliente oficial de **Groq** (`AsyncGroq`), modelo `llama-3.1-8b-instant`. El prompt de sistema (`SYSTEM_PROMPT`) define:

- Identidad del asistente: "Guache", asistente comercial de Agroindustria Guache C.A. (fundada 1998, Acarigua, Portuguesa).
- Datos operativos de planta (capacidad, horarios, contacto).
- Catálogo de productos con SKUs (harinas, aceites, alimento balanceado, agroinsumos, subproductos).
- Reglas de tono y de manejo de precios (siempre remitir a cotización, nunca dar precio fijo).

> ⚠️ **Nota para quien continúe el proyecto:** este `SYSTEM_PROMPT` describe el catálogo B2B/mayorista actual (harinas, alimento balanceado a granel). Es contenido **hardcodeado en el código**, no editable sin un despliegue. A medida que avance la estrategia de detal (España/Colombia) y el panel de administración (§6.2), este prompt debería poder actualizarse sin tocar código — hoy es una limitación conocida, no un diseño final.

### 4.5 Frontend web — `web/`

Sitio estático de una sola página (sin build step, sin framework):

- **Hero** con propuesta de valor y estadísticas de planta.
- **Catálogo de productos** (tarjetas estáticas, hardcodeadas en `index.html`).
- **Formulario de cotización** (`#cotizar`) → `POST /api/cotizar`.
- **Widget de chat flotante** ("Guache el zorro") con chips de sugerencia rápida → `POST /api/chat`. El historial de conversación se mantiene solo en memoria del navegador (`chatHistory` en `app.js`), no se persiste en el backend.

No hay build tool (Webpack/Vite), no hay componentes, no hay gestor de paquetes de frontend — es HTML/CSS/JS plano servido directamente por FastAPI vía `StaticFiles`.

### 4.6 Despliegue — `deploy/`

- **`agroguache.service`** — unit de systemd que corre `uvicorn main:app` con 2 workers, como usuario `root`, en un VPS.
- **`agroguache.nginx`** — Nginx sirve `styles.css` y `app.js` directamente como estáticos (por performance) y hace proxy del resto del tráfico a FastAPI en `127.0.0.1:8000`.
- **`backup_db.py` + `agroguache-backup.service` + `agroguache-backup.timer`** — backup diario de `cotizaciones.db` (ver más abajo).

**Producción:** el sitio corre en un VPS (antes accesible solo por IP `93.189.88.76`) y desde agosto 2026 responde en **https://guache.online** (y `www.guache.online`), con certificado TLS de Let's Encrypt vía Certbot (autorenovación configurada, vence 2026-11-12).

> ⚠️ **Nota:** Certbot modifica la config de Nginx directamente en el servidor (agregó los bloques HTTPS y las rutas del certificado). `deploy/agroguache.nginx` ya está sincronizado (agosto 2026) con el archivo real del VPS (`/etc/nginx/sites-enabled/agroguache`) — si Certbot vuelve a tocarlo (ej. al renovar o agregar un subdominio), hay que repetir la sincronización a mano, ya que Certbot no versiona sus cambios.

Hay CI (tests automáticos, §7), pero no CD: el despliegue al VPS sigue siendo manual, sin contenedor Docker.

**Backups:** `deploy/backup_db.py` hace un respaldo seguro de `cotizaciones.db` (usa el API de backup online de `sqlite3`, no una copia cruda — no corrompe el archivo aunque la app esté escribiendo) y guarda el resultado en `/var/backups/agroguache/`, con rotación automática (borra respaldos de más de 14 días). Corre una vez al día vía un timer de systemd. Es un backup **local al VPS** — protege contra una migración/deploy que rompa datos, pero no contra la pérdida total del servidor; si en el futuro se necesita eso, hay que sumar una copia off-site (ver §8.6).

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

---

## 5. Stack tecnológico

| Capa | Tecnología |
|---|---|
| Backend / API | Python 3.14, FastAPI, Uvicorn |
| Validación de datos | Pydantic v2 |
| Base de datos | SQLite + SQLAlchemy ORM, migraciones con Alembic |
| Tests | pytest + `fastapi.testclient` |
| Bot conversacional | python-telegram-bot |
| LLM / IA | Groq API (`llama-3.1-8b-instant`) |
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
# Completar TELEGRAM_BOT_TOKEN, GROQ_API_KEY, ADMIN_USERNAME y ADMIN_PASSWORD en .env

# 4. Aplicar migraciones (crea/actualiza el esquema de cotizaciones.db)
alembic upgrade head

# 5. Levantar el servidor (web + API + bot de Telegram)
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
- Si no se configura `TELEGRAM_BOT_TOKEN`, `GROQ_API_KEY`, `ADMIN_USERNAME` o `ADMIN_PASSWORD`, la app **falla al arrancar** (`src/config.py` lanza `ValueError`) — las cuatro son obligatorias hoy, no opcionales.
- `GET /api/cotizaciones` pide usuario/clave (HTTP Basic Auth) — usa las credenciales `ADMIN_USERNAME` / `ADMIN_PASSWORD` definidas en `.env`.
- **Si ya tenías una `cotizaciones.db` creada antes de que existieran las migraciones** (con las tablas ya presentes), no corras `alembic upgrade head` sobre ella directamente — fallaría porque la tabla ya existe. En su lugar, corré `alembic stamp head` una única vez para decirle a Alembic "esta base ya está al día", sin tocar los datos. Esto aplica en particular al **VPS de producción** al desplegar este cambio por primera vez.

---

## 7. Deuda técnica y riesgos conocidos

Para quien se una al proyecto, esto es lo que hay que tener en cuenta **antes de construir features nuevas encima**:

1. ~~`GET /api/cotizaciones` sin autenticación~~ — **Resuelto (agosto 2026).** Protegido con HTTP Basic Auth (`ADMIN_USERNAME` / `ADMIN_PASSWORD`, ver `main.py::verificar_admin`). Es una solución mínima apropiada para el estado actual del proyecto (sin usuarios/roles) — cuando exista el panel de administración (§8.2) esto debería migrar a un sistema de sesiones/roles real.
2. ~~CORS abierto (`allow_origins=["*"]`)~~ — **Resuelto (agosto 2026).** Ahora configurable vía `ALLOWED_ORIGINS` en `.env`. La web y la API comparten origen (mismo dominio, FastAPI sirve ambos), así que esto no bloquea el uso normal del sitio — igual conviene setear `ALLOWED_ORIGINS=https://guache.online,https://www.guache.online` en el `.env` del VPS explícitamente (hoy sigue con el default de `localhost`, solo funciona por ser same-origin, no por estar bien configurado).
3. **Sin autenticación de usuarios/roles** — la protección del punto 1 es una clave de administrador compartida, no un sistema de usuarios. Sigue siendo un prerrequisito para el panel de administración (§8.2), que necesitará roles diferenciados (admin/secretaría vs. público).
4. ~~Sin migraciones de base de datos~~ — **Resuelto (agosto 2026).** Esquema gestionado con Alembic (ver §4.2 y §6). **Pendiente:** correr `alembic stamp head` una vez en el VPS de producción al desplegar este cambio (la tabla ya existe ahí, creada previamente con `create_all()`).
5. **SQLite en un solo archivo** — válido para el volumen actual (cotizaciones B2B), pero no escala bien a concurrencia alta ni a un catálogo de e-commerce con pedidos, usuarios e inventario. Migrar a PostgreSQL es un prerrequisito realista para la fase de detal.
6. ~~Dependencia sin usar (`google-genai`, `google-auth`)~~ — **Resuelto (agosto 2026).** Se eliminaron de `requirements.txt` junto con sus dependencias transitivas exclusivas (`cryptography`, `cffi`, `pycparser`, `pyasn1`, `pyasn1_modules`). El servicio LLM usa únicamente Groq.
7. **Prompt del asistente hardcodeado** (§4.4) — no editable sin desplegar código nuevo.
8. ~~Sin tests automatizados~~ — **Resuelto parcialmente (agosto 2026).** Suite básica con `pytest` + `TestClient` en `tests/` cubriendo health check, registro y listado de cotizaciones (incl. auth), y chat (con LLM mockeado). Falta cobertura de `src/bots/telegram_bot.py` y de los casos límite de `src/services/llm_service.py`.
9. ~~Sin CI~~ — **Resuelto parcialmente (agosto 2026).** GitHub Actions (`.github/workflows/tests.yml`) corre la suite de `pytest` en cada push/PR a `main`. **El despliegue al VPS sigue siendo manual** — falta el CD (§8.6).
10. **Historial de chat no persistido** — se pierde al recargar la página; no hay forma de dar seguimiento a una conversación de un cliente.

---

## 8. Roadmap técnico hacia 2027

### 8.1 Tienda / venta al detal (e-commerce)

Hoy el sitio solo permite **cotizar al mayor**. La estrategia de negocio requiere una sección donde el consumidor final pueda **comprar directamente** ciertos productos (presentaciones de detal: café, cacao, harinas, arroz, etc.).

Implica, como mínimo:
- Modelo de datos de catálogo (productos de detal, precios, stock, imágenes) — independiente del catálogo mayorista actual.
- Carrito de compra y checkout.
- Integración de pasarela de pago apta para España/Colombia (ej. Stripe, Redsys, PayU, PayPal).
- Cálculo de envío internacional / logística de última milla — a definir con negocio.
- Multi-moneda (EUR, COP, USD) y probablemente multi-idioma/variante regional del español.

### 8.2 Panel de administración (CMS interno)

Hoy **todo el contenido de la web está hardcodeado** en `index.html` (productos, textos, precios de referencia). La meta es que alguien del equipo de Guache — no necesariamente un desarrollador — pueda:
- Editar el catálogo (productos, precios, disponibilidad, imágenes).
- Editar textos y secciones de la landing.
- Publicar entradas de blog (§8.3).
- Ver y gestionar cotizaciones/pedidos (reemplazando el actual `GET /api/cotizaciones` abierto por una vista protegida).

Requiere primero **autenticación y roles** (mínimo: rol administrador/secretaría vs. público), lo cual hoy no existe en absoluto en el proyecto.

### 8.3 Blog / centro de contenido

Sección pensada para construir comunidad alrededor de la marca Guache: artículos de ayuda para productores, contenido de valor para clientes de detal (recetas, origen del producto, etc.). Requiere modelo de contenido (posts, autor, fecha, imagen) gestionable desde el panel de administración (§8.2).

### 8.4 Automatización de pedidos vía bot

Hoy el bot de Telegram es puramente conversacional (preguntas y respuestas vía LLM). La visión 2027 apunta a que el bot pueda **gestionar pedidos de forma activa**: iniciar y dar seguimiento a un pedido, notificar estados, y potencialmente ampliarse a otros canales (ej. WhatsApp Business API, relevante para el mercado español/colombiano donde WhatsApp es el canal dominante, más que Telegram).

### 8.5 Internacionalización

Adaptar textos, catálogo y tono de marca a España y Colombia, manteniendo la identidad "alimento tradicional latinoamericano". Incluye decisiones de producto (¿un solo sitio multi-región o instancias separadas?) que deben definirse junto con negocio antes de implementar.

### 8.6 Infraestructura y escalabilidad

- Evaluar migración de SQLite → PostgreSQL antes de lanzar e-commerce real.
- Ya existe CI (tests automáticos en GitHub Actions, §7). Falta el **CD**: automatizar el despliegue al VPS en lugar del proceso manual actual.
- ~~Backups automáticos de base de datos~~ — **Resuelto parcialmente (agosto 2026).** Backup diario local al VPS con rotación (§4.6). Falta la copia off-site (otro servidor o almacenamiento en la nube) para estar protegidos ante la pérdida total del VPS.
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
