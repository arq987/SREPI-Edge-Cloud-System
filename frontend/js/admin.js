// =================================================================
// ADMIN DDA: UI Y VISTA RAPIDA (LOCAL)
// =================================================================
const adminInputs = [
    'categoria-multiplicador',
    'producto-descuento',
    'dda-roja-dias',
    'dda-amarilla-dias',
    'dda-desc-roja',
    'dda-desc-amarilla',
    'dda-desc-verde',
    'xp-roja',
    'xp-amarilla',
    'xp-verde',
    'xp-multiplicador',
    'dda-reserva-valor',
    'dda-reserva-unidad',
    'preview-precio',
    'preview-dias'
];

const API_BASE = window.SREPI_API_BASE || 'https://srepi-backend.onrender.com';
let categorias = [];
let productos = [];

const categoriaSelect = document.getElementById('categoria-select');
const productoSelect = document.getElementById('producto-select');
const categoriaMultiplicadorInput = document.getElementById('categoria-multiplicador');
const productoDescuentoInput = document.getElementById('producto-descuento');
const guardarBtn = document.getElementById('guardar-config');
const guardarEstado = document.getElementById('guardar-estado');
const dashboardRefresh = document.getElementById('dashboard-refresh');
const dashboardEstado = document.getElementById('dashboard-estado');
const adminTabs = document.querySelectorAll('.admin-tab');
const adminViews = document.querySelectorAll('.view');
const reservaValorInput = document.getElementById('dda-reserva-valor');
const reservaUnidadSelect = document.getElementById('dda-reserva-unidad');
const simuladorBtn = document.getElementById('simulador-btn');

const categoriaOverrides = new Map();
const productoOverrides = new Map();

async function cargarCategorias() {
    if (!categoriaSelect) return;
    categoriaSelect.innerHTML = '<option value="">Selecciona una categoria</option>';

    try {
        const response = await fetch(`${API_BASE}/api/categorias`, { cache: 'no-store' });
        if (!response.ok) {
            throw new Error('No se pudieron cargar las categorias');
        }
        const data = await response.json();
        categorias = Array.isArray(data.categorias) ? data.categorias : [];
    } catch (error) {
        categorias = [];
        return;
    }

    categoriaOverrides.clear();
    categorias.forEach(categoria => {
        categoriaOverrides.set(categoria.id, Number(categoria.multiplicador || 1));
    });

    categorias.forEach(categoria => {
        const option = document.createElement('option');
        option.value = categoria.id;
        option.textContent = categoria.nombre;
        categoriaSelect.appendChild(option);
    });
}

async function cargarProductos(categoriaId) {
    if (!productoSelect) return;
    productoSelect.innerHTML = '<option value="">Selecciona un producto</option>';

    if (!categoriaId) {
        productos = [];
        return;
    }

    try {
        const response = await fetch(`${API_BASE}/api/productos?categoria_id=${categoriaId}`, { cache: 'no-store' });
        if (!response.ok) {
            throw new Error('No se pudieron cargar los productos');
        }
        const data = await response.json();
        productos = Array.isArray(data.productos) ? data.productos : [];
    } catch (error) {
        productos = [];
        return;
    }

    productos.forEach(prod => {
        productoOverrides.set(prod.id, Number(prod.descuento || 0));
    });

    productos.forEach(prod => {
        const option = document.createElement('option');
        option.value = prod.id;
        option.textContent = prod.nombre;
        productoSelect.appendChild(option);
    });
}

function obtenerCategoriaActual() {
    if (!categoriaSelect) return null;
    return categorias.find(categoria => categoria.id === categoriaSelect.value) || null;
}

function obtenerProductoActual() {
    if (!productoSelect) return null;
    return productos.find(prod => String(prod.id) === productoSelect.value) || null;
}

function sincronizarSegmento() {
    const categoria = obtenerCategoriaActual();
    const producto = obtenerProductoActual();

    if (categoriaMultiplicadorInput) {
        const valorCategoria = categoriaOverrides.get(categoria?.id) ?? categoria?.multiplicador ?? 1.0;
        categoriaMultiplicadorInput.value = valorCategoria;
    }

    if (productoDescuentoInput) {
        const valorProducto = productoOverrides.get(producto?.id) ?? producto?.descuento ?? 0;
        productoDescuentoInput.value = valorProducto;
    }
}

function setText(id, value) {
    const el = document.getElementById(id);
    if (el) {
        el.textContent = value;
    }
}

function leerNumero(id) {
    const input = document.getElementById(id);
    if (!input) return 0;
    return Number(input.value || 0);
}

function calcularVistaRapida() {
    const rojaDias = leerNumero('dda-roja-dias');
    const amarillaDias = leerNumero('dda-amarilla-dias');
    const descRoja = leerNumero('dda-desc-roja') / 100;
    const descAmarilla = leerNumero('dda-desc-amarilla') / 100;
    const descVerde = leerNumero('dda-desc-verde') / 100;
    const xpRoja = leerNumero('xp-roja');
    const xpAmarilla = leerNumero('xp-amarilla');
    const xpVerde = leerNumero('xp-verde');
    const multiplicadorBase = leerNumero('xp-multiplicador') || 1;
    const multiplicadorCategoria = leerNumero('categoria-multiplicador') || 1;
    const ajusteProducto = leerNumero('producto-descuento') / 100;
    const precioBase = leerNumero('preview-precio');
    const dias = leerNumero('preview-dias');

    let descuento = descVerde;
    let xpBase = xpVerde;
    let zona = 'Verde';

    if (dias <= rojaDias) {
        descuento = descRoja;
        xpBase = xpRoja;
        zona = 'Roja';
    } else if (dias <= amarillaDias) {
        descuento = descAmarilla;
        xpBase = xpAmarilla;
        zona = 'Amarilla';
    }

    const descuentoFinal = Math.max(0, Math.min(0.95, descuento + ajusteProducto));
    const precioOferta = Math.max(0, Math.round(precioBase * (1 - descuentoFinal)));
    const xpTotal = Math.max(0, Math.round(xpBase * multiplicadorBase * multiplicadorCategoria));

    setText('preview-precio-oferta', `$${precioOferta.toLocaleString('es-CO')}`);
    setText('preview-xp', `${xpTotal} XP`);
    setText('preview-zona', zona);
}

function sincronizarChips() {
    setText('dda-roja-dias-val', `${leerNumero('dda-roja-dias')}d`);
    setText('dda-amarilla-dias-val', `${leerNumero('dda-amarilla-dias')}d`);
    setText('dda-desc-roja-val', `${leerNumero('dda-desc-roja')}%`);
    setText('dda-desc-amarilla-val', `${leerNumero('dda-desc-amarilla')}%`);
    setText('dda-desc-verde-val', `${leerNumero('dda-desc-verde')}%`);
    const multiplicador = leerNumero('xp-multiplicador') || 0;
    setText('xp-multiplicador-val', `${multiplicador.toFixed(1)}x`);
    const unidadReserva = reservaUnidadSelect?.value || 'horas';
    const valorReserva = leerNumero('dda-reserva-valor');
    const etiquetaUnidad = unidadReserva === 'dias' ? 'dias' : 'horas';
    setText('dda-reserva-valor-val', `${valorReserva} ${etiquetaUnidad}`);
}

function ajustarReservaRango() {
    if (!reservaValorInput || !reservaUnidadSelect) return;
    const unidad = reservaUnidadSelect.value;
    if (unidad === 'dias') {
        reservaValorInput.min = '1';
        reservaValorInput.max = '30';
        reservaValorInput.step = '1';
    } else {
        reservaValorInput.min = '1';
        reservaValorInput.max = '24';
        reservaValorInput.step = '1';
    }
    const valor = Number(reservaValorInput.value || 0);
    if (valor < Number(reservaValorInput.min)) {
        reservaValorInput.value = reservaValorInput.min;
    } else if (valor > Number(reservaValorInput.max)) {
        reservaValorInput.value = reservaValorInput.max;
    }
}

async function cargarConfigReserva() {
    if (!reservaValorInput || !reservaUnidadSelect) return;
    try {
        const response = await fetch(`${API_BASE}/api/dda/reserva-config`, { cache: 'no-store' });
        if (!response.ok) {
            throw new Error('No se pudo cargar la configuracion de reserva');
        }
        const data = await response.json();
        reservaUnidadSelect.value = data.unidad === 'dias' ? 'dias' : 'horas';
        ajustarReservaRango();
        reservaValorInput.value = data.valor || reservaValorInput.value;
        sincronizarChips();
    } catch (error) {
        ajustarReservaRango();
        sincronizarChips();
    }
}

function formatearMoneda(valor) {
    const numero = Number(valor || 0);
    return new Intl.NumberFormat('es-CO', {
        style: 'currency',
        currency: 'COP',
        maximumFractionDigits: 0
    }).format(numero);
}

function pintarDashboard(data) {
    if (!data) return;
    const riesgo = data.riesgo || {};
    const ventas = data.ventas || {};
    const recaudo = data.recaudo || {};

    const riesgoTotal = (riesgo.roja ?? 0) + (riesgo.amarilla ?? 0) + (riesgo.verde ?? 0);
    setText('riesgo-total', riesgoTotal);

    setText('riesgo-roja', riesgo.roja ?? 0);
    setText('riesgo-amarilla', riesgo.amarilla ?? 0);
    setText('riesgo-verde', riesgo.verde ?? 0);

    setText('ventas-roja', ventas.roja ?? 0);
    setText('ventas-amarilla', ventas.amarilla ?? 0);
    setText('ventas-verde', ventas.verde ?? 0);
    setText('ventas-total', ventas.total ?? 0);

    setText('recaudo-roja', formatearMoneda(recaudo.roja));
    setText('recaudo-amarilla', formatearMoneda(recaudo.amarilla));
    setText('recaudo-verde', formatearMoneda(recaudo.verde));
    setText('recaudo-total', formatearMoneda(recaudo.total));
}

async function cargarDashboard() {
    if (dashboardEstado) {
        dashboardEstado.textContent = 'Actualizando...';
    }

    try {
        const response = await fetch(`${API_BASE}/api/dashboard/resumen`, { cache: 'no-store' });
        if (!response.ok) {
            throw new Error('No se pudo cargar el dashboard');
        }
        const data = await response.json();
        pintarDashboard(data);
        if (dashboardEstado) {
            dashboardEstado.textContent = 'Actualizado';
        }
    } catch (error) {
        if (dashboardEstado) {
            dashboardEstado.textContent = 'Sin conexion';
        }
    }
}

adminInputs.forEach(id => {
    const input = document.getElementById(id);
    if (input) {
        input.addEventListener('input', () => {
            sincronizarChips();
        });
    }
});

if (categoriaSelect) {
    cargarCategorias().then(() => {
        sincronizarSegmento();
    });
    categoriaSelect.addEventListener('change', async () => {
        await cargarProductos(categoriaSelect.value);
        sincronizarSegmento();
    });
}

if (productoSelect) {
    productoSelect.addEventListener('change', () => {
        sincronizarSegmento();
    });
}

if (categoriaMultiplicadorInput) {
    categoriaMultiplicadorInput.addEventListener('input', () => {
        const categoria = obtenerCategoriaActual();
        if (categoria) {
            categoriaOverrides.set(categoria.id, Number(categoriaMultiplicadorInput.value || 1));
        }
    });
}

if (productoDescuentoInput) {
    productoDescuentoInput.addEventListener('input', () => {
        const producto = obtenerProductoActual();
        if (producto) {
            productoOverrides.set(producto.id, Number(productoDescuentoInput.value || 0));
        }
    });
}

if (reservaUnidadSelect) {
    reservaUnidadSelect.addEventListener('change', () => {
        ajustarReservaRango();
        sincronizarChips();
    });
}

if (dashboardRefresh) {
    dashboardRefresh.addEventListener('click', () => {
        cargarDashboard();
    });
}

if (adminTabs.length) {
    adminTabs.forEach(tab => {
        tab.addEventListener('click', () => {
            adminTabs.forEach(btn => btn.classList.remove('is-active'));
            tab.classList.add('is-active');
            const targetId = tab.getAttribute('data-target');
            adminViews.forEach(view => {
                view.classList.toggle('view-active', view.id === targetId);
            });
        });
    });
}

if (simuladorBtn) {
    simuladorBtn.addEventListener('click', () => {
        calcularVistaRapida();
    });
}

cargarDashboard();

async function guardarConfiguracion() {
    if (!guardarBtn) return;
    guardarBtn.disabled = true;
    if (guardarEstado) {
        guardarEstado.textContent = 'Guardando...';
    }

    const categoriasPayload = Array.from(categoriaOverrides.entries()).map(([id, multiplicador]) => ({
        id,
        multiplicador
    }));

    const productosPayload = Array.from(productoOverrides.entries()).map(([id, descuento]) => ({
        id,
        descuento
    }));

    try {
        const response = await fetch(`${API_BASE}/api/dda/config`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                categorias: categoriasPayload,
                productos: productosPayload
            })
        });

        if (!response.ok) {
            throw new Error('No se pudo guardar la configuracion');
        }

        if (reservaValorInput && reservaUnidadSelect) {
            await fetch(`${API_BASE}/api/dda/reserva-config`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    valor: Number(reservaValorInput.value || 0),
                    unidad: reservaUnidadSelect.value
                })
            });
        }

        if (guardarEstado) {
            guardarEstado.textContent = 'Cambios guardados.';
        }
    } catch (error) {
        if (guardarEstado) {
            guardarEstado.textContent = 'Error al guardar.';
        }
    } finally {
        guardarBtn.disabled = false;
    }
}

if (guardarBtn) {
    guardarBtn.addEventListener('click', guardarConfiguracion);
}

sincronizarChips();
sincronizarSegmento();
cargarConfigReserva();
