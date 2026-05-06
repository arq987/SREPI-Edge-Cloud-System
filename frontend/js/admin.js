// =================================================================
// ADMIN DDA: UI Y VISTA RAPIDA (LOCAL)
// =================================================================
const adminInputs = [
    'categoria-multiplicador',
    'producto-descuento',
    'dda-roja-horas',
    'dda-amarilla-horas',
    'dda-desc-roja',
    'dda-desc-amarilla',
    'dda-desc-verde',
    'xp-roja',
    'xp-amarilla',
    'xp-verde',
    'xp-multiplicador',
    'preview-precio',
    'preview-horas'
];

const API_BASE = window.SREPI_API_BASE || 'http://localhost:8000';
let categorias = [];
let productos = [];

const categoriaSelect = document.getElementById('categoria-select');
const productoSelect = document.getElementById('producto-select');
const categoriaMultiplicadorInput = document.getElementById('categoria-multiplicador');
const productoDescuentoInput = document.getElementById('producto-descuento');
const guardarBtn = document.getElementById('guardar-config');
const guardarEstado = document.getElementById('guardar-estado');

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
    const rojaHoras = leerNumero('dda-roja-horas');
    const amarillaHoras = leerNumero('dda-amarilla-horas');
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
    const horas = leerNumero('preview-horas');

    let descuento = descVerde;
    let xpBase = xpVerde;
    let zona = 'Verde';

    if (horas <= rojaHoras) {
        descuento = descRoja;
        xpBase = xpRoja;
        zona = 'Roja';
    } else if (horas <= amarillaHoras) {
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
    setText('dda-roja-horas-val', `${leerNumero('dda-roja-horas')}h`);
    setText('dda-amarilla-horas-val', `${leerNumero('dda-amarilla-horas')}h`);
    setText('dda-desc-roja-val', `${leerNumero('dda-desc-roja')}%`);
    setText('dda-desc-amarilla-val', `${leerNumero('dda-desc-amarilla')}%`);
    setText('dda-desc-verde-val', `${leerNumero('dda-desc-verde')}%`);
}

adminInputs.forEach(id => {
    const input = document.getElementById(id);
    if (input) {
        input.addEventListener('input', () => {
            sincronizarChips();
            calcularVistaRapida();
        });
    }
});

if (categoriaSelect) {
    cargarCategorias().then(() => {
        sincronizarSegmento();
        calcularVistaRapida();
    });
    categoriaSelect.addEventListener('change', async () => {
        await cargarProductos(categoriaSelect.value);
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

if (categoriaMultiplicadorInput) {
    categoriaMultiplicadorInput.addEventListener('input', () => {
        const categoria = obtenerCategoriaActual();
        if (categoria) {
            categoriaOverrides.set(categoria.id, Number(categoriaMultiplicadorInput.value || 1));
        }
        calcularVistaRapida();
    });
}

if (productoDescuentoInput) {
    productoDescuentoInput.addEventListener('input', () => {
        const producto = obtenerProductoActual();
        if (producto) {
            productoOverrides.set(producto.id, Number(productoDescuentoInput.value || 0));
        }
        calcularVistaRapida();
    });
}

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
calcularVistaRapida();
