// Helpers compartidos por todas las páginas del panel de administración.

async function apiFetch(url, opciones = {}) {
    const respuesta = await fetch(url, { credentials: "same-origin", ...opciones });
    if (respuesta.status === 401) {
        window.location.href = "/admin/login.html";
        throw new Error("No autenticado");
    }
    return respuesta;
}

// Llamar al cargar cualquier página protegida del panel (todas menos login.html).
// Devuelve {username, permisos} y oculta cualquier elemento marcado
// data-permiso="modulo" si el usuario logueado no tiene ese permiso
// (ej. data-permiso="usuarios" para el link a Usuarios).
async function requerirSesion() {
    const respuesta = await fetch("/api/admin/whoami", { credentials: "same-origin" });
    const data = await respuesta.json();
    if (!data.autenticado) {
        window.location.href = "/admin/login.html";
        return null;
    }

    document.querySelectorAll("[data-permiso]").forEach((el) => {
        if (!data.permisos[el.dataset.permiso]) el.style.display = "none";
    });

    return data;
}

// Para usar al principio de una página cuyo contenido entero requiere un
// permiso puntual (no solo ocultar un link de nav) — ej. productos.html
// necesita "productos". Si falta, reemplaza #contenidoPagina con un aviso
// y devuelve false.
function requerirPermiso(sesion, modulo) {
    if (sesion.permisos[modulo]) return true;
    const contenedor = document.getElementById("contenidoPagina") || document.querySelector("main.admin-main");
    contenedor.innerHTML =
        '<h1>Sin acceso</h1><p class="empty-state">No tenés permiso para ver esta página. <a href="/admin/">Volver al inicio</a>.</p>';
    return false;
}

async function cerrarSesion() {
    await apiFetch("/api/admin/logout", { method: "POST" });
    window.location.href = "/admin/login.html";
}

// Sube un archivo de imagen y devuelve la URL pública, o null si no se eligió archivo
async function subirImagenSiHay(inputFile) {
    if (!inputFile.files || inputFile.files.length === 0) {
        return null;
    }
    const formData = new FormData();
    formData.append("archivo", inputFile.files[0]);

    const respuesta = await apiFetch("/api/admin/upload", {
        method: "POST",
        body: formData,
    });
    if (!respuesta.ok) {
        const error = await respuesta.json();
        throw new Error(error.detail || "No se pudo subir la imagen.");
    }
    const data = await respuesta.json();
    return data.url;
}

function mostrarPreviewImagen(inputFile, contenedorPreview) {
    inputFile.addEventListener("change", () => {
        if (!inputFile.files || inputFile.files.length === 0) return;
        const url = URL.createObjectURL(inputFile.files[0]);
        contenedorPreview.innerHTML = `<img src="${url}" alt="Vista previa">`;
    });
}

function escaparHtml(texto) {
    const div = document.createElement("div");
    div.textContent = texto;
    return div.innerHTML;
}
