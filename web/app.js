// MEMORIA DEL CHAT (Historial de conversación)
const chatHistory = [];

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
                historial: chatHistory 
            })
        });

        const data = await response.json();

        if (response.ok) {
            // Remplazar el indicador con la respuesta formateada
            typingDiv.innerHTML = data.respuesta.replace(/\n/g, '<br>');
            // Guardar respuesta del bot en el historial
            chatHistory.push({ role: 'assistant', content: data.respuesta });
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