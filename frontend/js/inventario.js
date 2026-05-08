const API_BASE = window.SREPI_API_BASE || 'https://srepi-backend.onrender.com';

let todosLosLotes = [];
let filtroZona = 'todos';
let filtroCategoriaId = null;
let filtroBusqueda = '';
let incluirVencidos = false;

// ── UTILS ─────────────────────────────────────────────────
function setText(id, value) {
    const el = document.getElementById(id);
    if (el) el.textContent = value;
}

function formatearMoneda(valor) {
    return new Intl.NumberFormat('es-CO', {
        style: 'currency', currency: 'COP', maximumFractionDigits: 0
    }).format(Number(valor || 0));
}

function formatearFecha(iso) {
    if (!iso || iso === '-') return '-';
    const [y, m, d] = iso.split('-');
    return `${d}/${m}/${y}`;
}

function zonaBadgeHTML(zona, dias) {
    const map = {
        roja:    { cls: 'badge-zona-roja',    txt: 'Roja' },
        amarilla:{ cls: 'badge-zona-amarilla', txt: 'Amarilla' },
        verde:   { cls: 'badge-zona-verde',    txt: 'Verde' },
        vencido: { cls: 'badge-zona-vencido',  txt: 'Vencido' }
    };
    const { cls, txt } = map[zona] || map.vencido;
    const diasTxt = zona === 'vencido'
        ? `${Math.abs(dias)}d vencido`
        : `${dias}d`;
    return `<span class="inv-badge ${cls}">${txt}</span>
            <span class="dias-chip dias-${zona}">${diasTxt}</span>`;
}

function stockBarHTML(disponible, inicial) {
    const pct = inicial > 0 ? Math.min(100, Math.round(disponible / inicial * 100)) : 0;
    let barClass = 'stock-bar-ok';
    if (pct < 25) barClass = 'stock-bar-low';
    else if (pct < 60) barClass = 'stock-bar-mid';
    return `
        <div class="stock-wrap">
            <span class="stock-num">${disponible}<span class="stock-total">/${inicial}</span></span>
            <div class="stock-bar-track"><div class="stock-bar ${barClass}" style="width:${pct}%"></div></div>
        </div>`;
}

// ── FILTROS ───────────────────────────────────────────────
function aplicarFiltros() {
    let resultado = todosLosLotes;

    if (filtroZona !== 'todos') {
        resultado = resultado.filter(l => l.zona === filtroZona);
    }
    if (filtroCategoriaId !== null) {
        resultado = resultado.filter(l => l.categoria_id === filtroCategoriaId);
    }
    if (filtroBusqueda.trim()) {
        const term = filtroBusqueda.toLowerCase();
        resultado = resultado.filter(l =>
            l.nombre.toLowerCase().includes(term) ||
            l.sku.toLowerCase().includes(term) ||
            l.categoria.toLowerCase().includes(term)
        );
    }
    if (!incluirVencidos) {
        resultado = resultado.filter(l => l.zona !== 'vencido');
    }

    renderTabla(resultado);
    setText('inv-count', `${resultado.length} lote${resultado.length !== 1 ? 's' : ''}`);
}

function setFiltroZona(zona) {
    filtroZona = zona;
    document.querySelectorAll('.zona-filter-btn').forEach(btn => {
        btn.classList.toggle('is-active', btn.dataset.zona === zona);
    });
    aplicarFiltros();
}

// ── TABLA ─────────────────────────────────────────────────
function renderTabla(lotes) {
    const tbody = document.getElementById('inv-tbody');
    if (!tbody) return;
    tbody.innerHTML = '';

    if (!lotes.length) {
        tbody.innerHTML = `<tr><td colspan="9" class="inv-empty">Sin lotes para los filtros seleccionados</td></tr>`;
        return;
    }

    lotes.forEach(l => {
        const tr = document.createElement('tr');
        tr.className = `inv-row inv-row-${l.zona}`;
        tr.innerHTML = `
            <td class="inv-td-id">#${l.id_lote}</td>
            <td>
                <span class="inv-prod-name">${l.nombre}</span>
                <span class="inv-sku">${l.sku}</span>
            </td>
            <td class="inv-cat">${l.categoria}</td>
            <td>${stockBarHTML(l.cantidad_disponible, l.cantidad_inicial)}</td>
            <td class="inv-precio">${formatearMoneda(l.precio_base)}</td>
            <td class="inv-fecha">${formatearFecha(l.fecha_vencimiento)}</td>
            <td>${zonaBadgeHTML(l.zona, l.dias_para_vencer)}</td>
            <td class="inv-kg">${Number(l.peso_kg).toFixed(2)} kg</td>
        `;
        tbody.appendChild(tr);
    });
}

// ── KPI CARDS ─────────────────────────────────────────────
function pintarResumen(data) {
    setText('kpi-total-lotes', data.total_lotes ?? 0);
    setText('kpi-total-unidades', (data.total_unidades ?? 0).toLocaleString('es-CO'));
    setText('kpi-zona-roja', data.por_zona?.roja ?? 0);
    setText('kpi-zona-amarilla', data.por_zona?.amarilla ?? 0);
    setText('kpi-zona-verde', data.por_zona?.verde ?? 0);
    setText('kpi-vencidos', data.vencidos ?? 0);
}

// ── POBLAR SELECTOR CATEGORIAS ────────────────────────────
function poblarCategorias(lotes) {
    const sel = document.getElementById('inv-cat-select');
    if (!sel) return;
    const cats = new Map();
    lotes.forEach(l => cats.set(l.categoria_id, l.categoria));
    sel.innerHTML = '<option value="">Todas las categorias</option>';
    cats.forEach((nombre, id) => {
        const opt = document.createElement('option');
        opt.value = id;
        opt.textContent = nombre;
        sel.appendChild(opt);
    });
}

// ── CARGA PRINCIPAL ───────────────────────────────────────
async function cargarInventario() {
    setText('inv-estado', 'Cargando...');
    try {
        const [resLotes, resResumen] = await Promise.all([
            fetch(`${API_BASE}/api/inventario/lotes?incluir_vencidos=true`, { cache: 'no-store' }),
            fetch(`${API_BASE}/api/inventario/resumen`, { cache: 'no-store' })
        ]);

        if (!resLotes.ok || !resResumen.ok) throw new Error('Error en la respuesta del servidor');

        const dataLotes = await resLotes.json();
        const dataResumen = await resResumen.json();

        todosLosLotes = dataLotes.lotes || [];
        poblarCategorias(todosLosLotes);
        pintarResumen(dataResumen);
        aplicarFiltros();
        setText('inv-estado', `Actualizado — ${todosLosLotes.length} lotes en total`);
    } catch (err) {
        setText('inv-estado', 'Error al cargar datos');
        renderTabla([]);
    }
}

// ── EVENTOS ───────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
    cargarInventario();

    document.querySelectorAll('.zona-filter-btn').forEach(btn => {
        btn.addEventListener('click', () => setFiltroZona(btn.dataset.zona));
    });

    const searchInput = document.getElementById('inv-search');
    if (searchInput) {
        searchInput.addEventListener('input', e => {
            filtroBusqueda = e.target.value;
            aplicarFiltros();
        });
    }

    const catSelect = document.getElementById('inv-cat-select');
    if (catSelect) {
        catSelect.addEventListener('change', e => {
            filtroCategoriaId = e.target.value ? parseInt(e.target.value) : null;
            aplicarFiltros();
        });
    }

    const vencidosToggle = document.getElementById('inv-vencidos-toggle');
    if (vencidosToggle) {
        vencidosToggle.addEventListener('change', e => {
            incluirVencidos = e.target.checked;
            aplicarFiltros();
        });
    }

    const refreshBtn = document.getElementById('inv-refresh');
    if (refreshBtn) refreshBtn.addEventListener('click', cargarInventario);
});
