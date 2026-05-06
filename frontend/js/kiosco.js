// =================================================================
// 1. UTILIDADES CRIPTOGRAFICAS
// =================================================================
function decodificarJWT(token) {
    try {
        const base64Url = token.split('.')[1];
        const base64 = base64Url.replace(/-/g, '+').replace(/_/g, '/');
        const jsonPayload = decodeURIComponent(atob(base64).split('').map(function(c) {
            return '%' + ('00' + c.charCodeAt(0).toString(16)).slice(-2);
        }).join(''));
        return JSON.parse(jsonPayload);
    } catch (e) { return null; }
}

// =================================================================
// 2. LOGICA PRINCIPAL DEL ESCANER Y EDGE COMPUTING
// =================================================================
function onScanSuccess(decodedText, decodedResult) {
    html5QrcodeScanner.clear();
    const resultadoDiv = document.getElementById('resultado');
    resultadoDiv.style.display = 'block';

    const datosReserva = decodificarJWT(decodedText);

    if (datosReserva) {
        if (localStorage.getItem(datosReserva.id_transaccion)) {
            resultadoDiv.className = 'error';
            resultadoDiv.innerHTML = `
                <h3 style="color: #dc3545; margin-top:0;">🛑 CODIGO YA CANJEADO</h3>
                <p>Este codigo ya fue entregado por esta caja recientemente.</p>
                <button class="btn-recargar" onclick="location.reload()">Siguiente Cliente</button>`;
            return;
        }

        const tiempoActual = Math.floor(Date.now() / 1000);
        if (datosReserva.exp < tiempoActual) {
            resultadoDiv.className = 'error';
            resultadoDiv.innerHTML = `
                <h3 style="color: #dc3545; margin-top:0;">❌ Codigo Expirado</h3>
                <p>El tiempo limite de reserva ha finalizado.</p>
                <button class="btn-recargar" onclick="location.reload()">Siguiente Cliente</button>`;
            return;
        }

        resultadoDiv.className = 'warning';
        resultadoDiv.innerHTML = `
            <h3 style="color: #856404; margin-top:0; text-align:center;">⏳ Verificando Servidor...</h3>
            <p style="text-align:center; color: #666;">Validando conexion central.</p>`;

        fetch("http://localhost:8000/api/kiosco/confirmar-retiro", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                id_transaccion: datosReserva.id_transaccion,
                id_lote: datosReserva.id_lote,
                usuario: datosReserva.usuario,
                xp_ganada: datosReserva.xp
            })
        })
        .then(async response => {
            if (!response.ok) {
                const data = await response.json();
                throw new Error(data.detail || "Error del servidor");
            }

            localStorage.setItem(datosReserva.id_transaccion, "sincronizado");
            resultadoDiv.className = 'success';
            resultadoDiv.innerHTML = `
                <h3 style="color: #28a745; margin-top:0; text-align:center;">✅ ENTREGA AUTORIZADA</h3>
                <h4 style="text-align:center; margin-bottom: 5px; color:#666;">(MODO ONLINE)</h4>
                <hr style="border: 0; border-top: 1px solid #ccc;">
                <div class="datos">
                    <p><strong>👤 Cliente:</strong> ${datosReserva.usuario}</p>
                    <p><strong>📦 Producto:</strong> ${datosReserva.producto}</p>
                </div>
                <button class="btn-recargar" onclick="location.reload()">Siguiente Cliente</button>`;
        })
        .catch(error => {
            if (error.message === "Failed to fetch" || error.message.includes("Network")) {
                actualizarUI(false);
                localStorage.setItem("offline_" + datosReserva.id_transaccion, JSON.stringify(datosReserva));
                localStorage.setItem(datosReserva.id_transaccion, "pendiente_sincronizacion");

                resultadoDiv.className = 'success';
                resultadoDiv.innerHTML = `
                    <h3 style="color: #28a745; margin-top:0; text-align:center;">✅ ENTREGA AUTORIZADA</h3>
                    <h4 style="text-align:center; margin-bottom: 5px; color:#ff9800;">(MODO OFFLINE)</h4>
                    <hr style="border: 0; border-top: 1px solid #ccc;">
                    <div class="datos">
                        <p><strong>👤 Cliente:</strong> ${datosReserva.usuario}</p>
                        <p><strong>📦 Producto:</strong> ${datosReserva.producto}</p>
                    </div>
                    <p style="text-align:center; font-style:italic; color:#ff9800; font-size:13px;">⚠️ El inventario se sincronizara automaticamente al reconectar.</p>
                    <button class="btn-recargar" onclick="location.reload()">Siguiente Cliente</button>`;
            } else {
                resultadoDiv.className = 'error';
                resultadoDiv.innerHTML = `
                    <h3 style="color: #dc3545; margin-top:0;">🛑 TRANSACCION RECHAZADA</h3>
                    <p><strong>${error.message}</strong></p>
                    <button class="btn-recargar" onclick="location.reload()">Siguiente Cliente</button>`;
            }
        });
    } else {
        resultadoDiv.className = 'error';
        resultadoDiv.innerHTML = `<h3 style="color: #dc3545; margin-top:0;">🚨 FIRMA INVALIDA</h3><p>QR no reconocido por SREPI.</p><button class="btn-recargar" onclick="location.reload()">Reintentar</button>`;
    }
}

const html5QrcodeScanner = new Html5QrcodeScanner("reader", { fps: 10, qrbox: {width: 250, height: 250} });
html5QrcodeScanner.render(onScanSuccess);

// Localizacion basica de la UI de html5-qrcode (sin romper eventos)
const QR_UI_TRANSLATIONS = {
    "Select Camera": "Camara seleccionada",
    "Start Scanning": "Iniciar escaneo",
    "Stop Scanning": "Detener escaneo",
    "Scan an Image File": "Escanear imagen",
    "Scan using camera directly": "Escanear con camara",
    "Choose Image": "Elegir imagen",
    "No image chosen": "Ninguna imagen seleccionada",
    "Or drop an image to scan": "O arrastra una imagen para escanear",
    "Scanning": "Escaneando",
    "Request Camera Permissions": "Solicitar permisos de camara"
};

function traducirTextoNodo(texto) {
    const limpio = texto.trim();
    if (QR_UI_TRANSLATIONS[limpio]) {
        return texto.replace(limpio, QR_UI_TRANSLATIONS[limpio]);
    }

    if (limpio.startsWith("Select Camera")) {
        return texto.replace(limpio, limpio.replace("Select Camera", "Camara seleccionada"));
    }

    if (limpio.includes("Choose Image")) {
        return texto.replace("Choose Image", "Elegir imagen");
    }

    if (limpio.includes("No image chosen")) {
        return texto.replace("No image chosen", "Ninguna imagen seleccionada");
    }

    if (limpio.includes("Or drop an image to scan")) {
        return texto.replace("Or drop an image to scan", "O arrastra una imagen para escanear");
    }

    if (limpio.includes("Scan using camera directly")) {
        return texto.replace("Scan using camera directly", "Escanear con camara");
    }

    return null;
}

function localizarUIQr() {
    const reader = document.getElementById('reader');
    if (!reader) return false;

    let actualizado = false;
    const walker = document.createTreeWalker(reader, NodeFilter.SHOW_TEXT, null);
    let nodo = walker.nextNode();

    while (nodo) {
        if (nodo.nodeValue) {
            const nuevo = traducirTextoNodo(nodo.nodeValue);
            if (nuevo && nuevo !== nodo.nodeValue) {
                nodo.nodeValue = nuevo;
                actualizado = true;
            }
        }
        nodo = walker.nextNode();
    }

    return actualizado;
}

let intentosLocalizacion = 0;
const maxIntentos = 12;
const intervaloLocalizacion = setInterval(() => {
    intentosLocalizacion += 1;
    localizarUIQr();

    if (intentosLocalizacion >= maxIntentos) {
        clearInterval(intervaloLocalizacion);
    }
}, 400);

const readerRoot = document.getElementById('reader');
if (readerRoot && window.MutationObserver) {
    const observer = new MutationObserver(() => {
        localizarUIQr();
    });
    observer.observe(readerRoot, { childList: true, subtree: true, characterData: true });
}

// =================================================================
// 3. MOTOR DE ESTADO HIBRIDO Y SINCRONIZACION
// =================================================================
const badge = document.getElementById('badge-estado');
let servidorVivo = false;

function actualizarUI(estaOnline) {
    if (estaOnline) {
        badge.className = 'badge-edge badge-online';
        badge.innerHTML = '🟢 CONECTADO (ONLINE)';
    } else {
        badge.className = 'badge-edge badge-offline';
        badge.innerHTML = '🔴 MODO EDGE (OFFLINE)';
    }
}

window.addEventListener('offline', () => {
    servidorVivo = false;
    actualizarUI(false);
});

window.addEventListener('online', () => {
    verificarServidor();
});

function verificarServidor() {
    if (!navigator.onLine) {
        if (servidorVivo) { servidorVivo = false; actualizarUI(false); }
        return;
    }

    fetch("http://localhost:8000/", { method: "GET", cache: "no-store" })
    .then(() => {
        if (!servidorVivo) {
            servidorVivo = true;
            actualizarUI(true);
            sincronizarPendientes();
        }
    })
    .catch(() => {
        if (servidorVivo || badge.className.includes("online")) {
            servidorVivo = false;
            actualizarUI(false);
        }
    });
}

function sincronizarPendientes() {
    if (!servidorVivo) return;

    for (let i = 0; i < localStorage.length; i++) {
        let key = localStorage.key(i);

        if (key && key.startsWith("offline_")) {
            let datosReserva = JSON.parse(localStorage.getItem(key));

            fetch("http://localhost:8000/api/kiosco/confirmar-retiro", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(datosReserva)
            })
            .then(async response => {
                if (response.ok) {
                    localStorage.removeItem(key);
                    localStorage.setItem(datosReserva.id_transaccion, "sincronizado");
                } else {
                    const data = await response.json();
                    if (data.detail && data.detail.includes("ya fue canjeado")) {
                        localStorage.removeItem(key);
                        localStorage.setItem(datosReserva.id_transaccion, "quemado_servidor");
                    }
                }
            })
            .catch(() => { /* Silencioso */ });
        }
    }
}

verificarServidor();
setInterval(verificarServidor, 10000);
