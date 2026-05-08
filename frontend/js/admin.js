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
const categoriaTag = document.getElementById('segmento-categoria-actual');
const productoTag = document.getElementById('segmento-producto-actual');
const productosTotalTag = document.getElementById('segmento-productos-total');
const productoDdaList = document.getElementById('producto-dda-list');

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
        if (!productoOverrides.has(prod.id)) {
            productoOverrides.set(prod.id, Number(prod.descuento || 0));
        }
    });

    productos.forEach(prod => {
        const option = document.createElement('option');
        option.value = prod.id;
        option.textContent = prod.nombre;
        productoSelect.appendChild(option);
    });
}

function obtenerCategoriaActual() {
    if (!categoriaSelect || !categoriaSelect.value) return null;
    const categoriaId = Number(categoriaSelect.value);
    return categorias.find(categoria => Number(categoria.id) === categoriaId) || null;
}

function obtenerProductoActual() {
    if (!productoSelect || !productoSelect.value) return null;
    return productos.find(prod => String(prod.id) === productoSelect.value) || null;
}

function normalizarDescuentoProducto(valor) {
    const numero = Number(valor);
    if (Number.isNaN(numero)) return 0;
    return Math.max(0, Math.min(40, numero));
}

function actualizarListadoProductosDda() {
    if (!productoDdaList) return;
    productoDdaList.innerHTML = '';

    const categoria = obtenerCategoriaActual();
    if (!categoria) {
        productoDdaList.innerHTML = '<p class="producto-dda-empty">Selecciona una categoria para ver sus productos.</p>';
        if (productosTotalTag) {
            productosTotalTag.textContent = '0 productos';
        }
        return;
    }

    if (!productos.length) {
        productoDdaList.innerHTML = '<p class="producto-dda-empty">No hay productos disponibles en esta categoria.</p>';
        if (productosTotalTag) {
            productosTotalTag.textContent = '0 productos';
        }
        return;
    }

    const productoSeleccionadoId = productoSelect?.value || '';
    productos.forEach(prod => {
        const item = document.createElement('div');
        item.className = 'producto-dda-item';
        item.dataset.productoId = String(prod.id);
        if (String(prod.id) === productoSeleccionadoId) {
            item.classList.add('is-selected');
        }

        const boton = document.createElement('button');
        boton.type = 'button';
        boton.setAttribute('data-producto-id', String(prod.id));

        const nombre = document.createElement('span');
        nombre.className = 'producto-dda-name';
        nombre.textContent = prod.nombre;

        const referencia = document.createElement('span');
        referencia.className = 'producto-dda-id';
        referencia.textContent = String(prod.id);

        boton.appendChild(nombre);
        boton.appendChild(referencia);

        const valorDescuento = normalizarDescuentoProducto(productoOverrides.get(prod.id) ?? prod.descuento ?? 0);

        const sliderWrap = document.createElement('div');
        sliderWrap.className = 'producto-dda-slider-wrap';

        const sliderValSpan = document.createElement('span');
        sliderValSpan.className = 'producto-dda-slider-val';
        sliderValSpan.textContent = `${valorDescuento}%`;

        const input = document.createElement('input');
        input.type = 'range';
        input.className = 'producto-dda-input slider-accent';
        input.min = '0';
        input.max = '40';
        input.step = '1';
        input.value = String(valorDescuento);
        input.setAttribute('data-producto-id', String(prod.id));

        input.addEventListener('input', () => {
            sliderValSpan.textContent = `${input.value}%`;
        });

        sliderWrap.appendChild(sliderValSpan);
        sliderWrap.appendChild(input);

        item.appendChild(boton);
        item.appendChild(sliderWrap);
        productoDdaList.appendChild(item);
    });

    if (productosTotalTag) {
        productosTotalTag.textContent = `${productos.length} productos`;
    }
}

function sincronizarSegmento() {
    const categoria = obtenerCategoriaActual();
    const producto = obtenerProductoActual();

    if (categoriaTag) {
        categoriaTag.textContent = categoria?.nombre || 'Sin seleccionar';
    }

    if (productoTag) {
        productoTag.textContent = producto?.nombre || 'Sin seleccionar';
    }

    if (categoriaMultiplicadorInput) {
        const valorCategoria = categoriaOverrides.get(categoria?.id) ?? categoria?.multiplicador ?? 1.0;
        categoriaMultiplicadorInput.value = valorCategoria;
        setText('categoria-multiplicador-val', `${Number(valorCategoria).toFixed(1)}x`);
    }

    if (productoDescuentoInput) {
        const valorProducto = productoOverrides.get(producto?.id) ?? producto?.descuento ?? 0;
        productoDescuentoInput.value = valorProducto;
        setText('producto-descuento-val', `${valorProducto}%`);
    }

    actualizarListadoProductosDda();
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

    const card = document.getElementById('resultado-card');
    if (card) {
        card.className = 'resultado-card resultado-card-' + zona.toLowerCase();
    }
}

function sincronizarChips() {
    setText('dda-roja-dias-val', `${leerNumero('dda-roja-dias')}d`);
    setText('dda-amarilla-dias-val', `${leerNumero('dda-amarilla-dias')}d`);
    setText('dda-desc-roja-val', `${leerNumero('dda-desc-roja')}%`);
    setText('dda-desc-amarilla-val', `${leerNumero('dda-desc-amarilla')}%`);
    setText('dda-desc-verde-val', `${leerNumero('dda-desc-verde')}%`);
    setText('xp-roja-val', `${leerNumero('xp-roja')}`);
    setText('xp-amarilla-val', `${leerNumero('xp-amarilla')}`);
    setText('xp-verde-val', `${leerNumero('xp-verde')}`);
    const multiplicador = leerNumero('xp-multiplicador') || 0;
    setText('xp-multiplicador-val', `${multiplicador.toFixed(1)}x`);
    const unidadReserva = reservaUnidadSelect?.value || 'horas';
    const valorReserva = leerNumero('dda-reserva-valor');
    const etiquetaUnidad = unidadReserva === 'dias' ? 'dias' : 'horas';
    setText('dda-reserva-valor-val', `${valorReserva} ${etiquetaUnidad}`);
    const catMult = leerNumero('categoria-multiplicador') || 1;
    setText('categoria-multiplicador-val', `${catMult.toFixed(1)}x`);
    const prodDesc = leerNumero('producto-descuento');
    setText('producto-descuento-val', `${prodDesc}%`);
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
    cargarCategorias().then(async () => {
        if (categoriaSelect.options.length > 1) {
            categoriaSelect.selectedIndex = 1;
            await cargarProductos(categoriaSelect.value);
            if (productoSelect && productoSelect.options.length > 1) {
                productoSelect.selectedIndex = 1;
            }
        }
        sincronizarSegmento();
        calcularVistaRapida();
    });
    categoriaSelect.addEventListener('change', async () => {
        await cargarProductos(categoriaSelect.value);
        if (productoSelect) {
            productoSelect.value = '';
        }
        sincronizarSegmento();
        calcularVistaRapida();
    });
}

if (productoSelect) {
    productoSelect.addEventListener('change', () => {
        sincronizarSegmento();
        calcularVistaRapida();
    });
}

if (productoDdaList) {
    productoDdaList.addEventListener('click', event => {
        const boton = event.target.closest('button[data-producto-id]');
        if (!boton || !productoSelect) return;
        productoSelect.value = boton.getAttribute('data-producto-id') || '';
        sincronizarSegmento();
        calcularVistaRapida();
    });

    productoDdaList.addEventListener('input', event => {
        const input = event.target.closest('input[data-producto-id]');
        if (!input) return;
        const productoId = input.getAttribute('data-producto-id') || '';
        const valor = normalizarDescuentoProducto(input.value);
        input.value = String(valor);

        const producto = productos.find(item => String(item.id) === productoId);
        if (producto) {
            productoOverrides.set(producto.id, valor);
        }

        if (productoSelect && productoSelect.value === productoId && productoDescuentoInput) {
            productoDescuentoInput.value = String(valor);
            setText('producto-descuento-val', `${valor}%`);
        }

        calcularVistaRapida();
    });
}

if (categoriaMultiplicadorInput) {
    categoriaMultiplicadorInput.addEventListener('input', () => {
        const categoria = obtenerCategoriaActual();
        if (categoria) {
            categoriaOverrides.set(categoria.id, Number(categoriaMultiplicadorInput.value || 1));
        }
        setText('categoria-multiplicador-val', `${Number(categoriaMultiplicadorInput.value || 1).toFixed(1)}x`);
    });
}

if (productoDescuentoInput) {
    productoDescuentoInput.addEventListener('input', () => {
        const producto = obtenerProductoActual();
        if (producto) {
            const valor = normalizarDescuentoProducto(productoDescuentoInput.value);
            productoDescuentoInput.value = String(valor);
            productoOverrides.set(producto.id, valor);
            setText('producto-descuento-val', `${valor}%`);
            sincronizarSegmento();
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

async function cargarParamsDDA() {
    try {
        const response = await fetch(`${API_BASE}/api/dda/params`, { cache: 'no-store' });
        if (!response.ok) return;
        const data = await response.json();
        const map = {
            'dda-roja-dias': data.dias_roja,
            'dda-amarilla-dias': data.dias_amarilla,
            'dda-desc-roja': data.desc_roja,
            'dda-desc-amarilla': data.desc_amarilla,
            'dda-desc-verde': data.desc_verde,
            'xp-roja': data.xp_roja,
            'xp-amarilla': data.xp_amarilla,
            'xp-verde': data.xp_verde,
            'xp-multiplicador': data.multiplicador_xp
        };
        Object.entries(map).forEach(([id, valor]) => {
            const el = document.getElementById(id);
            if (el && valor !== undefined) el.value = valor;
        });
        sincronizarChips();
        calcularVistaRapida();
    } catch (_) {}
}

async function guardarConfiguracion() {
    if (!guardarBtn) return;
    guardarBtn.disabled = true;
    if (guardarEstado) {
        guardarEstado.textContent = 'Guardando...';
    }

    const categoriasPayload = [];
    const categoriaActual = obtenerCategoriaActual();
    if (categoriaActual) {
        categoriasPayload.push({
            id: categoriaActual.id,
            multiplicador: categoriaOverrides.get(categoriaActual.id) ?? categoriaActual.multiplicador
        });
    }

    const productosPayload = Array.from(productoOverrides.entries()).map(([id, descuento]) => ({
        id,
        descuento
    }));

    const paramsPayload = {
        dias_roja: leerNumero('dda-roja-dias'),
        dias_amarilla: leerNumero('dda-amarilla-dias'),
        desc_roja: leerNumero('dda-desc-roja'),
        desc_amarilla: leerNumero('dda-desc-amarilla'),
        desc_verde: leerNumero('dda-desc-verde'),
        xp_roja: leerNumero('xp-roja'),
        xp_amarilla: leerNumero('xp-amarilla'),
        xp_verde: leerNumero('xp-verde'),
        multiplicador_xp: leerNumero('xp-multiplicador') || 1
    };

    try {
        const [resConfig, resParams] = await Promise.all([
            fetch(`${API_BASE}/api/dda/config`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    categorias: categoriasPayload,
                    productos: productosPayload
                })
            }),
            fetch(`${API_BASE}/api/dda/params`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(paramsPayload)
            })
        ]);

        if (!resConfig.ok || !resParams.ok) {
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
cargarParamsDDA();
