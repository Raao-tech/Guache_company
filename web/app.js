// MEMORIA DEL CHAT (Historial de conversación, solo en memoria del navegador)
const chatHistory = [];

// ID de sesión para agrupar la conversación en el backend (visible desde
// el panel de administración). Vive en sessionStorage: sobrevive a un
// F5 de la página, se pierde si se cierra la pestaña — una conversación
// nueva es una sesión nueva.
function obtenerSesionIdChat() {
    let sesionId = sessionStorage.getItem('guache_sesion_chat');
    if (!sesionId) {
        sesionId = crypto.randomUUID();
        sessionStorage.setItem('guache_sesion_chat', sesionId);
    }
    return sesionId;
}

// CARRITO DE COMPRAS -> localStorage (a diferencia de la sesión de chat,
// tiene que sobrevivir a cerrar la pestaña). Guarda SOLO producto_id +
// cantidad, nunca precio ni nombre: el precio real siempre se vuelve a
// pedir al servidor (acá al mostrar el carrito, y de nuevo al crear el
// pedido) — así un localStorage manipulado a mano nunca puede mostrar
// ni cobrar un precio falso.
function obtenerCarrito() {
    try {
        const carrito = JSON.parse(localStorage.getItem('guache_carrito'));
        return Array.isArray(carrito) ? carrito : [];
    } catch (error) {
        return [];
    }
}

function guardarCarrito(carrito) {
    localStorage.setItem('guache_carrito', JSON.stringify(carrito));
    actualizarBadgeCarrito();
}

function contarItemsCarrito() {
    return obtenerCarrito().reduce((total, item) => total + item.cantidad, 0);
}

function actualizarBadgeCarrito() {
    const cantidad = contarItemsCarrito();
    document.querySelectorAll('.carrito-badge').forEach((badge) => {
        badge.textContent = cantidad;
        badge.style.display = cantidad > 0 ? 'inline-flex' : 'none';
    });
}

document.addEventListener('DOMContentLoaded', actualizarBadgeCarrito);

// Alternar visibilidad de la ventana de chat
function toggleChat() {
    const chatWindow = document.getElementById('chatWindow');
    chatWindow.classList.toggle('hidden');
    if (!chatWindow.classList.contains('hidden')) {
        document.getElementById('chatInput').focus();
        scrollToBottom();
    }
}

// Abre el chat y pregunta directamente por la venta al detal
function preguntarSobreDetal() {
    const chatWindow = document.getElementById('chatWindow');
    if (chatWindow.classList.contains('hidden')) {
        toggleChat();
    }
    usarSugerencia('¿Cuándo estará disponible la venta al detal en España y Colombia?');
}

// MENÚ MÓVIL (hamburguesa)
function inicializarMenuMovil() {
    const toggle = document.getElementById('navToggle');
    const links = document.getElementById('navLinks');
    if (!toggle || !links) return;

    toggle.addEventListener('click', () => {
        const abierto = links.classList.toggle('open');
        toggle.setAttribute('aria-expanded', abierto);
    });

    // Cerrar el menú al navegar a una sección
    links.querySelectorAll('a').forEach((enlace) => {
        enlace.addEventListener('click', () => {
            links.classList.remove('open');
            toggle.setAttribute('aria-expanded', 'false');
        });
    });
}

document.addEventListener('DOMContentLoaded', inicializarMenuMovil);

// Escapa texto antes de insertarlo en innerHTML (nombres/descripciones vienen de la BD)
function escaparHtmlPublico(texto) {
    const div = document.createElement('div');
    div.textContent = texto ?? '';
    return div.innerHTML;
}

// CATÁLOGO "AL DETAL" -> GET /api/detal/productos
// Si no hay productos cargados todavía, se deja el preview estático que ya
// trae el HTML (las 4 categorías con "muy pronto").
async function cargarCatalogoDetal() {
    const contenedor = document.getElementById('detalContenido');
    if (!contenedor) return;

    try {
        const respuesta = await fetch('/api/detal/productos');
        const productos = await respuesta.json();
        if (!Array.isArray(productos) || productos.length === 0) return;

        contenedor.innerHTML = `
            <div class="producto-grid">
                ${productos.map((p) => `
                    <div class="producto-card">
                        <div class="media-slot" aria-hidden="true">
                            ${p.imagen_url ? `<img src="${p.imagen_url}" alt="${escaparHtmlPublico(p.nombre)}">` : '🛍️'}
                        </div>
                        <div class="producto-card-body">
                            <h3>${escaparHtmlPublico(p.nombre)}</h3>
                            <p>${escaparHtmlPublico(p.descripcion)}</p>
                            ${p.precio ? `<span class="producto-precio">${p.precio} ${escaparHtmlPublico(p.moneda || '')}</span>` : ''}
                        </div>
                    </div>
                `).join('')}
            </div>
        `;
    } catch (error) {
        // Si falla la carga, queda el preview estático — la sección no se rompe.
    }
}

// BLOG (VISTA PREVIA EN EL HOME) -> GET /api/blog/posts
async function cargarBlogTeaser() {
    const contenedor = document.getElementById('blogTeaserGrid');
    if (!contenedor) return;

    try {
        const respuesta = await fetch('/api/blog/posts');
        const posts = await respuesta.json();

        if (!Array.isArray(posts) || posts.length === 0) {
            contenedor.innerHTML = '<p class="empty-state">Todavía no hay artículos publicados.</p>';
            return;
        }

        contenedor.innerHTML = posts.slice(0, 4).map((p) => `
            <a href="/blog/${p.slug}" class="blog-card">
                <div class="media-slot tone-tierra" aria-hidden="true">
                    ${p.imagen_url ? `<img src="${p.imagen_url}" alt="${escaparHtmlPublico(p.titulo)}">` : '📰'}
                </div>
                <div class="blog-card-body">
                    ${p.audiencia ? `<span class="audience-tag">${escaparHtmlPublico(p.audiencia)}</span>` : ''}
                    <h3>${escaparHtmlPublico(p.titulo)}</h3>
                    <p>${escaparHtmlPublico(p.resumen)}</p>
                    <span class="read-more">Leer más →</span>
                </div>
            </a>
        `).join('');
    } catch (error) {
        contenedor.innerHTML = '<p class="empty-state">No se pudieron cargar los artículos.</p>';
    }
}

document.addEventListener('DOMContentLoaded', cargarCatalogoDetal);
document.addEventListener('DOMContentLoaded', cargarBlogTeaser);

// Desplazamiento automático al final de la conversación
function scrollToBottom() {
    const messagesContainer = document.getElementById('chatMessages');
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
}

// SISTEMA DE NOTIFICACIONES TOAST
function showToast(mensaje, tipo = 'success'){
    const container = document.getElementById('toastContainer');
    const toast = document.createElement('div');
    toast.className = `toast ${tipo}`;
    toast.innerHTML = mensaje;

    container.appendChild(toast);

    setTimeout(() => {
        toast.style.opacity = '0';
        toast.style.transition = 'opacity 0.3s ease';
        setTimeout(() => toast.remove(), 300);
    }, 4000);
}

// Clic en sugerencia rápida
function usarSugerencia(texto) {
    const input = document.getElementById('chatInput');
    input.value = texto;
    document.querySelector('.chat-footer').dispatchEvent(new Event('submit', { cancelable: true, bubbles: true }));
}

// ------------------------------------------------------------------
// ENVÍO DE FORMULARIO DE COTIZACIÓN -> POST /api/cotizar
// ------------------------------------------------------------------
async function enviarCotizacion(event) {
    event.preventDefault();

    const btnSubmit = document.getElementById('btnSubmitQuote');
    btnSubmit.disabled = true;
    btnSubmit.innerText = "Procesando...";

    const payload = {
        nombre_contacto: document.getElementById('nombre').value,
        telefono: document.getElementById('telefono').value,
        empresa: document.getElementById('empresa').value || null,
        sku_producto: document.getElementById('sku').value,
        cantidad_toneladas: parseFloat(document.getElementById('cantidad').value),
        destino_despacho: document.getElementById('destino').value,
        observaciones: document.getElementById('observaciones').value || null
    };

    try {
        const response = await fetch('/api/cotizar', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });

        const data = await response.json();

        if (response.ok && data.exito) {
            showToast(`<strong>¡Cotización Registrada!</strong><br>Folio: <code>${data.id_cotizacion}</code>`, 'success');
            document.getElementById('quoteForm').reset();
        } else {
            throw new Error(data.detail || "Error al procesar la cotización.");
        }
    } catch (error) {
        showToast(`⚠️ ${error.message}`, 'error');
    } finally {
        btnSubmit.disabled = false;
        btnSubmit.innerText = "Enviar Solicitud de Cotización";
    }
}

// ------------------------------------------------------------------
// CHAT CON GUACHE EL ZORRO -> POST /api/chat
// ------------------------------------------------------------------
async function enviarMensajeChat(event) {
    event.preventDefault();

    const input = document.getElementById('chatInput');
    const sendBtn = document.getElementById('chatSendBtn');
    const messagesContainer = document.getElementById('chatMessages');
    const mensajeTexto = input.value.trim();

    if (!mensajeTexto) return;

    // 1. Mostrar mensaje del usuario en la interfaz
    const userDiv = document.createElement('div');
    userDiv.className = 'message user-message';
    userDiv.textContent = mensajeTexto;
    messagesContainer.appendChild(userDiv);

    // Guardar en el historial local
    chatHistory.push({ role: 'user', content: mensajeTexto });

    input.value = '';
    input.disabled = true;
    sendBtn.disabled = true;
    scrollToBottom();

    // 2. Indicador de escritura animado
    const typingDiv = document.createElement('div');
    typingDiv.className = 'message bot-message';
    typingDiv.innerHTML = `
        <div class="typing-dots">
            <span></span><span></span><span></span>
        </div>
    `;
    messagesContainer.appendChild(typingDiv);
    scrollToBottom();

    try {
        const response = await fetch('/api/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                mensaje: mensajeTexto,
                sesion_id: obtenerSesionIdChat(),
            })
        });

        const data = await response.json();

        if (response.ok) {
            // Remplazar el indicador con la respuesta formateada
            typingDiv.innerHTML = data.respuesta.replace(/\n/g, '<br>');
            // Guardar respuesta del bot en el historial
            chatHistory.push({ role: 'assistant', content: data.respuesta });
            // El backend genera el sesion_id la primera vez — nos aseguramos
            // de tener guardado exactamente el mismo para el resto de la charla.
            sessionStorage.setItem('guache_sesion_chat', data.sesion_id);
        } else {
            typingDiv.innerHTML = '⚠️ Ocurrió un detalle al consultar con el asistente.';
        }
    } catch (error) {
        typingDiv.innerHTML = '⚠️ Error de conexión con el servidor.';
    } finally {
        input.disabled = false;
        sendBtn.disabled = false;
        input.focus();
        scrollToBottom();
    }
}