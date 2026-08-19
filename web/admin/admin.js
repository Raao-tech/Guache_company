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
// Devuelve {username, rol} y oculta cualquier elemento marcado
// data-solo-admin si el usuario logueado no tiene rol "admin" (ej. Assistent_1).
async function requerirSesion() {
    const respuesta = await fetch("/api/admin/whoami", { credentials: "same-origin" });
    const data = await respuesta.json();
    if (!data.autenticado) {
        window.location.href = "/admin/login.html";
        return null;
    }

    document.querySelectorAll("[data-solo-admin]").forEach((el) => {
        if (data.rol !== "admin") el.style.display = "none";
    });

    return data;
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
