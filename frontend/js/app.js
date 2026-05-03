// =================================================================
// 1. UTILIDADES CRIPTOGRÁFICAS
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
// 2. LÓGICA PRINCIPAL DEL ESCÁNER Y EDGE COMPUTING
// =================================================================
function onScanSuccess(decodedText, decodedResult) {
    html5QrcodeScanner.clear(); 
    const resultadoDiv = document.getElementById('resultado');
    resultadoDiv.style.display = 'block';

    const datosReserva = decodificarJWT(decodedText);

    if (datosReserva) {
        // Defensa local: ¿Ya escaneamos esto?
        if (localStorage.getItem(datosReserva.id_transaccion)) {
            resultadoDiv.className = 'error';
            resultadoDiv.innerHTML = `
                <h3 style="color: #dc3545; margin-top:0;">🛑 CÓDIGO YA CANJEADO</h3>
                <p>Este código ya fue entregado por esta caja recientemente.</p>
                <button class="btn-recargar" onclick="location.reload()">Siguiente Cliente</button>`;
            return; 
        }

        // Validación de expiración
        const tiempoActual = Math.floor(Date.now() / 1000);
        if (datosReserva.exp < tiempoActual) {
            resultadoDiv.className = 'error';
            resultadoDiv.innerHTML = `
                <h3 style="color: #dc3545; margin-top:0;">❌ Código Expirado</h3>
                <p>El tiempo límite de reserva ha finalizado.</p>
                <button class="btn-recargar" onclick="location.reload()">Siguiente Cliente</button>`;
            return;
        }

        // Pantalla de espera
        resultadoDiv.className = 'warning';
        resultadoDiv.innerHTML = `
            <h3 style="color: #856404; margin-top:0; text-align:center;">⏳ Verificando Servidor...</h3>
            <p style="text-align:center; color: #666;">Validando conexión central.</p>`;

        // Petición al Backend
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
            
            // Éxito Online
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
                // Éxito Offline (Edge)
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
                    <p style="text-align:center; font-style:italic; color:#ff9800; font-size:13px;">⚠️ El inventario se sincronizará automáticamente al reconectar.</p>
                    <button class="btn-recargar" onclick="location.reload()">Siguiente Cliente</button>`;
            } else {
                // Fraude Online
                resultadoDiv.className = 'error';
                resultadoDiv.innerHTML = `
                    <h3 style="color: #dc3545; margin-top:0;">🛑 TRANSACCIÓN RECHAZADA</h3>
                    <p><strong>${error.message}</strong></p>
                    <button class="btn-recargar" onclick="location.reload()">Siguiente Cliente</button>`;
            }
        });
    } else {
        resultadoDiv.className = 'error';
        resultadoDiv.innerHTML = `<h3 style="color: #dc3545; margin-top:0;">🚨 FIRMA INVÁLIDA</h3><p>QR no reconocido por SREPI.</p><button class="btn-recargar" onclick="location.reload()">Reintentar</button>`;
    }
}

// Inicializamos la cámara
const html5QrcodeScanner = new Html5QrcodeScanner("reader", { fps: 10, qrbox: {width: 250, height: 250} });
html5QrcodeScanner.render(onScanSuccess);

// =================================================================
// 3. MOTOR DE ESTADO HÍBRIDO Y SINCRONIZACIÓN
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
                    if(data.detail && data.detail.includes("ya fue canjeado")) {
                        localStorage.removeItem(key);
                        localStorage.setItem(datosReserva.id_transaccion, "quemado_servidor");
                    }
                }
            })
            .catch(e => { /* Silencioso */ });
        }
    }
}

// Inicialización del Heartbeat
verificarServidor(); 
setInterval(verificarServidor, 10000);