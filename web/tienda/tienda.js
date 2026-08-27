// Lógica de la tienda: catálogo, carrito y checkout (/tienda/index.html,
// /tienda/checkout.html) y seguimiento de pedido (/tienda/pedido/{numero}).
// Depende de las funciones compartidas de app.js (obtenerCarrito,
// guardarCarrito, escaparHtmlPublico, showToast).

let productosCache = [];

function obtenerMercadoPreferido() {
    return sessionStorage.getItem('guache_mercado_tienda') || 'venezuela';
}

function guardarMercadoPreferido(mercado) {
    sessionStorage.setItem('guache_mercado_tienda', mercado);
}

// ------------------------------------------------------------------
// /tienda/index.html — catálogo + agregar al carrito
// ------------------------------------------------------------------
async function inicializarTienda() {
    const grid = document.getElementById('tiendaGrid');
    if (!grid) return;

    const toggle = document.getElementById('mercadoToggle');
    let mercado = obtenerMercadoPreferido();

    function activarBoton() {
        toggle.querySelectorAll('button').forEach((btn) => {
            btn.classList.toggle('activo', btn.dataset.mercado === mercado);
        });
    }

    toggle.querySelectorAll('button').forEach((btn) => {
        btn.addEventListener('click', () => {
            mercado = btn.dataset.mercado;
            guardarMercadoPreferido(mercado);
            activarBoton();
            renderizarProductos(mercado);
        });
    });
    activarBoton();

    try {
        const respuesta = await fetch('/api/detal/productos');
        productosCache = await respuesta.json();
    } catch (error) {
        productosCache = [];
    }
    renderizarProductos(mercado);
}

function renderizarProductos(mercado) {
    const grid = document.getElementById('tiendaGrid');
    const campoDisponible = mercado === 'venezuela' ? 'disponible_venezuela' : 'disponible_espana';
    const productos = productosCache.filter((p) => p[campoDisponible] && p.precio);

    if (productos.length === 0) {
        grid.innerHTML = '<p class="empty-state">Todavía no hay productos disponibles para este mercado.</p>';
        return;
    }

    grid.innerHTML = productos.map((p) => {
        const sinStock = p.stock !== null && p.stock <= 0;
        const pocoStock = p.stock !== null && p.stock > 0 && p.stock <= 5;
        return `
            <div class="tienda-card">
                <div class="media-slot" aria-hidden="true">
                    ${p.imagen_url ? `<img src="${p.imagen_url}" alt="${escaparHtmlPublico(p.nombre)}">` : '🛍️'}
                </div>
                <div class="tienda-card-body">
                    <h3>${escaparHtmlPublico(p.nombre)}</h3>
                    <p>${escaparHtmlPublico(p.descripcion)}</p>
                    <span class="tienda-card-precio">${p.precio} ${escaparHtmlPublico(p.moneda || '')}</span>
                    ${sinStock ? '<span class="tienda-card-stock agotado">Sin stock</span>' : ''}
                    ${pocoStock ? `<span class="tienda-card-stock">Últimas ${p.stock} unidades</span>` : ''}
                    <div class="tienda-card-agregar">
                        <input type="number" id="cantidad-${p.id}" value="1" min="1" ${sinStock ? 'disabled' : ''}>
                        <button class="btn-primary-sm" ${sinStock ? 'disabled' : ''} onclick="agregarAlCarrito(${p.id})">Agregar</button>
                    </div>
                </div>
            </div>
        `;
    }).join('');
}

function agregarAlCarrito(productoId) {
    const producto = productosCache.find((p) => p.id === productoId);
    if (!producto) return;

    const inputCantidad = document.getElementById(`cantidad-${productoId}`);
    const cantidad = parseInt(inputCantidad.value || '1', 10);
    if (!cantidad || cantidad < 1) return;

    const carrito = obtenerCarrito();

    // Un carrito no puede mezclar productos en distintas monedas: es una
    // restricción dura de Stripe (una sesión de pago es de una sola
    // moneda), aplicada parejo en los dos mercados para no complicar
    // tampoco la revisión manual de Venezuela. El servidor vuelve a
    // exigir esto igual al crear el pedido, esto es solo para avisar antes.
    if (carrito.length > 0) {
        const primerProducto = productosCache.find((p) => p.id === carrito[0].producto_id);
        if (primerProducto && primerProducto.moneda !== producto.moneda) {
            showToast(`⚠️ Tu carrito ya tiene productos en ${escaparHtmlPublico(primerProducto.moneda)}. Finalizá esa compra o vaciá el carrito antes de agregar algo en ${escaparHtmlPublico(producto.moneda)}.`, 'error');
            return;
        }
    }

    const existente = carrito.find((item) => item.producto_id === productoId);
    if (existente) {
        existente.cantidad += cantidad;
    } else {
        carrito.push({ producto_id: productoId, cantidad });
    }
    guardarCarrito(carrito);
    showToast(`${escaparHtmlPublico(producto.nombre)} agregado al carrito.`, 'success');
}

// ------------------------------------------------------------------
// /tienda/checkout.html — resumen del carrito + envío del pedido
// ------------------------------------------------------------------
async function inicializarCheckout() {
    const resumen = document.getElementById('carritoResumen');
    if (!resumen) return;

    try {
        const respuesta = await fetch('/api/detal/productos');
        productosCache = await respuesta.json();
    } catch (error) {
        productosCache = [];
    }
    renderizarResumenCarrito();

    document.querySelectorAll('input[name="mercado"]').forEach((radio) => {
        radio.addEventListener('change', () => {
            actualizarBloquePago();
            renderizarResumenCarrito();
        });
    });
    document.querySelectorAll('input[name="metodo_pago"]').forEach((radio) => {
        radio.addEventListener('change', actualizarInstruccionesPago);
    });
    actualizarBloquePago();
    actualizarInstruccionesPago();
}

function mercadoSeleccionado() {
    const radio = document.querySelector('input[name="mercado"]:checked');
    return radio ? radio.value : 'venezuela';
}

function metodoPagoSeleccionado() {
    const radio = document.querySelector('input[name="metodo_pago"]:checked');
    return radio ? radio.value : null;
}

function actualizarBloquePago() {
    const esEspana = mercadoSeleccionado() === 'espana';
    document.getElementById('bloquePagoVenezuela').style.display = esEspana ? 'none' : 'block';
    document.getElementById('bloquePagoEspana').style.display = esEspana ? 'block' : 'none';
    const boton = document.getElementById('btnFinalizarCompra');
    boton.disabled = esEspana || obtenerCarrito().length === 0;
    boton.innerText = esEspana ? 'Pago con tarjeta próximamente' : 'Confirmar pedido';
}

// NOTA: los datos de USDT siguen como placeholder ([completar]) — falta
// la wallet real, el resto (Pago Móvil, Zelle) ya son los datos reales.
const INSTRUCCIONES_METODO_PAGO = {
    pago_movil_ves: `
        <h4>📱 Pago Móvil</h4>
        <p>Hacé el Pago Móvil por el monto exacto de tu pedido a la tasa del día, y luego escribí acá el número de referencia.</p>
        <dl>
            <dt>Banco</dt><dd>Banco Provincial (BBVA)</dd>
            <dt>Teléfono</dt><dd>+58 414 1584092</dd>
            <dt>Cédula/RIF</dt><dd>V-10559375</dd>
        </dl>
    `,
    zelle_usd: `
        <h4>💵 Zelle</h4>
        <p>Enviá el pago exacto por Zelle y luego escribí acá el número de confirmación o el correo desde el que enviaste.</p>
        <dl>
            <dt>Correo Zelle</dt><dd>rafaelaraujordono@gmail.com</dd>
            <dt>A nombre de</dt><dd>Rafael Araujo</dd>
        </dl>
    `,
    usdt: `
        <h4>₿ USDT</h4>
        <p>Enviá el pago en USDT a la siguiente wallet y luego escribí acá el hash de la transacción.</p>
        <dl>
            <dt>Red</dt><dd>[completar]</dd>
            <dt>Wallet</dt><dd>[completar]</dd>
        </dl>
    `,
};

function actualizarInstruccionesPago() {
    const contenedor = document.getElementById('instruccionesPago');
    if (!contenedor) return;
    const metodo = metodoPagoSeleccionado();
    contenedor.innerHTML = INSTRUCCIONES_METODO_PAGO[metodo] || '';
}

function renderizarResumenCarrito() {
    const resumen = document.getElementById('carritoResumen');
    const carrito = obtenerCarrito();

    if (carrito.length === 0) {
        resumen.innerHTML = '<div class="carrito-vacio">Tu carrito está vacío. <a href="/tienda/">Ir a la tienda →</a></div>';
        document.getElementById('btnFinalizarCompra').disabled = true;
        return;
    }

    let total = 0;
    const filas = carrito.map((item) => {
        const producto = productosCache.find((p) => p.id === item.producto_id);
        if (!producto) return '';
        const subtotal = producto.precio * item.cantidad;
        total += subtotal;
        return `
            <div class="carrito-item-row">
                <div class="carrito-item-info">
                    <h4>${escaparHtmlPublico(producto.nombre)}</h4>
                    <p>${producto.precio} ${escaparHtmlPublico(producto.moneda || '')} c/u</p>
                </div>
                <div class="carrito-item-acciones">
                    <input type="number" min="1" value="${item.cantidad}" onchange="actualizarCantidadCarrito(${producto.id}, this.value)">
                    <span>${subtotal.toFixed(2)} ${escaparHtmlPublico(producto.moneda || '')}</span>
                    <button type="button" class="carrito-item-quitar" onclick="quitarDelCarrito(${producto.id})" aria-label="Quitar">✕</button>
                </div>
            </div>
        `;
    }).join('');

    const primerProducto = productosCache.find((p) => p.id === carrito[0].producto_id);
    const moneda = primerProducto ? primerProducto.moneda : '';

    resumen.innerHTML = `${filas}<div class="carrito-total"><span>Total</span><span>${total.toFixed(2)} ${escaparHtmlPublico(moneda || '')}</span></div>`;
    document.getElementById('btnFinalizarCompra').disabled = mercadoSeleccionado() === 'espana';
}

function actualizarCantidadCarrito(productoId, nuevaCantidad) {
    const cantidad = parseInt(nuevaCantidad, 10);
    if (!cantidad || cantidad < 1) {
        quitarDelCarrito(productoId);
        return;
    }
    const carrito = obtenerCarrito();
    const item = carrito.find((i) => i.producto_id === productoId);
    if (!item) return;
    item.cantidad = cantidad;
    guardarCarrito(carrito);
    renderizarResumenCarrito();
}

function quitarDelCarrito(productoId) {
    const carrito = obtenerCarrito().filter((i) => i.producto_id !== productoId);
    guardarCarrito(carrito);
    renderizarResumenCarrito();
}

async function enviarPedido(event) {
    event.preventDefault();

    const carrito = obtenerCarrito();
    if (carrito.length === 0) {
        showToast('⚠️ Tu carrito está vacío.', 'error');
        return;
    }

    const mercado = mercadoSeleccionado();
    if (mercado === 'espana') return; // el botón ya queda deshabilitado, esto es defensivo

    const referenciaPago = document.getElementById('referenciaPago').value.trim();
    if (!referenciaPago) {
        showToast('⚠️ Falta el número de referencia del pago.', 'error');
        return;
    }

    const boton = document.getElementById('btnFinalizarCompra');
    boton.disabled = true;
    boton.innerText = 'Procesando...';

    const payload = {
        mercado,
        metodo_pago: metodoPagoSeleccionado(),
        nombre_cliente: document.getElementById('nombreCliente').value,
        email_cliente: document.getElementById('emailCliente').value,
        telefono_cliente: document.getElementById('telefonoCliente').value,
        direccion_entrega: document.getElementById('direccionEntrega').value,
        notas_cliente: document.getElementById('notasCliente').value || null,
        referencia_pago: referenciaPago,
        items: carrito,
    };

    try {
        const respuesta = await fetch('/api/tienda/pedidos', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload),
        });
        const data = await respuesta.json();
        if (!respuesta.ok) {
            throw new Error(data.detail || 'No se pudo registrar el pedido.');
        }
        guardarCarrito([]);
        window.location.href = `/tienda/pedido/${data.numero_pedido}?nuevo=1`;
    } catch (error) {
        showToast(`⚠️ ${error.message}`, 'error');
        boton.disabled = false;
        boton.innerText = 'Confirmar pedido';
    }
}

// ------------------------------------------------------------------
// /tienda/pedido/{numero} — seguimiento / confirmación
// ------------------------------------------------------------------
async function inicializarPaginaPedido() {
    const contenedor = document.getElementById('contenidoPedido');
    if (!contenedor) return;

    const numeroPedido = window.location.pathname.split('/').filter(Boolean).pop();
    const esNuevo = new URLSearchParams(window.location.search).get('nuevo') === '1';

    try {
        const respuesta = await fetch(`/api/tienda/pedidos/${encodeURIComponent(numeroPedido)}`);
        if (!respuesta.ok) {
            contenedor.innerHTML = '<p class="empty-state">No encontramos ese pedido. Revisá el enlace que te llegó.</p>';
            return;
        }
        const pedido = await respuesta.json();

        const confirmando = esNuevo && pedido.estado === 'pendiente_pago';
        const nombresEstado = {
            pendiente_pago: 'Pendiente de confirmar pago',
            pagado: 'Pago confirmado',
            cancelado: 'Cancelado',
        };

        const filas = pedido.items.map((item) => `
            <div class="carrito-item-row">
                <div class="carrito-item-info">
                    <h4>${escaparHtmlPublico(item.nombre_producto)}</h4>
                    <p>${item.cantidad} x ${item.precio_unitario} ${escaparHtmlPublico(pedido.moneda)}</p>
                </div>
                <span>${item.subtotal.toFixed(2)} ${escaparHtmlPublico(pedido.moneda)}</span>
            </div>
        `).join('');

        contenedor.innerHTML = `
            ${esNuevo ? '<h1>¡Gracias por tu pedido! 🎉</h1>' : '<h1>Tu pedido</h1>'}
            ${confirmando ? '<p>Ya registramos tu pedido — un administrador va a confirmar tu pago en breve. Guardá este enlace para consultar el estado más adelante.</p>' : ''}
            <p><strong>Número de pedido:</strong> ${escaparHtmlPublico(pedido.numero_pedido)}</p>
            <p><span class="pedido-estado ${pedido.estado}">${nombresEstado[pedido.estado] || pedido.estado}</span></p>
            <div class="carrito-resumen" style="margin-top:1.5rem;">
                ${filas}
                <div class="carrito-total"><span>Total</span><span>${pedido.total.toFixed(2)} ${escaparHtmlPublico(pedido.moneda)}</span></div>
            </div>
        `;
    } catch (error) {
        contenedor.innerHTML = '<p class="empty-state">No se pudo cargar el pedido. Intentá de nuevo más tarde.</p>';
    }
}

document.addEventListener('DOMContentLoaded', inicializarTienda);
document.addEventListener('DOMContentLoaded', inicializarCheckout);
document.addEventListener('DOMContentLoaded', inicializarPaginaPedido);
