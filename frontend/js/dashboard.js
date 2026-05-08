const API_BASE = window.SREPI_API_BASE || 'https://srepi-backend.onrender.com';
let lineChartInstance = null;
let riskChartInstance = null;

function renderLineChart(config) {
    const canvas = document.getElementById('graficoRetiros');
    if (!canvas || typeof Chart === 'undefined') return;
    const ctx = canvas.getContext('2d');
    if (lineChartInstance) {
        lineChartInstance.destroy();
    }
    lineChartInstance = new Chart(ctx, {
        type: 'line',
        data: {
            labels: config.labels,
            datasets: [{
                label: 'Productos Rescatados',
                data: config.data,
                borderColor: '#0284c7',
                backgroundColor: 'rgba(2, 132, 199, 0.1)',
                borderWidth: 2,
                fill: true,
                tension: 0.4
            }]
        },
        options: { responsive: true, maintainAspectRatio: false }
    });
}

function renderRiskChart(config) {
    const canvas = document.getElementById('graficoRiesgo');
    if (!canvas || typeof Chart === 'undefined') return;
    const ctx = canvas.getContext('2d');
    if (riskChartInstance) {
        riskChartInstance.destroy();
    }
    riskChartInstance = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: config.labels,
            datasets: [{
                data: config.data,
                backgroundColor: ['#ef4444', '#f59e0b', '#22c55e'],
                borderWidth: 0,
                hoverOffset: 4
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { position: 'bottom' }
            }
        }
    });
}

function setText(id, value) {
    const el = document.getElementById(id);
    if (el) {
        el.textContent = value;
    }
}

function formatearMoneda(valor) {
    return new Intl.NumberFormat('es-CO', {
        style: 'currency',
        currency: 'COP',
        maximumFractionDigits: 0
    }).format(Number(valor || 0));
}

function renderTransacciones(transacciones) {
    const cuerpo = document.getElementById('tabla-transacciones');
    if (!cuerpo) return;
    cuerpo.innerHTML = '';
    if (!transacciones || !transacciones.length) {
        const fila = document.createElement('tr');
        fila.innerHTML = '<td colspan="5">Sin transacciones recientes</td>';
        cuerpo.appendChild(fila);
        return;
    }

    transacciones.forEach(item => {
        const fila = document.createElement('tr');
        const ahorroTexto = formatearMoneda(item.ahorro);
        const recaudoTexto = formatearMoneda(item.recaudo);
        fila.innerHTML = `
            <td>${item.id}</td>
            <td>${item.usuario || '-'}</td>
            <td>${item.producto || '-'}</td>
            <td><strong style="color: #16a34a;">${ahorroTexto} / ${recaudoTexto}</strong></td>
            <td><span class="badge badge-active">${item.estado}</span></td>
        `;
        cuerpo.appendChild(fila);
    });
}

async function cargarDashboard() {
    try {
        const response = await fetch(`${API_BASE}/api/dashboard/operacion`, { cache: 'no-store' });
        if (!response.ok) {
            throw new Error('No se pudo cargar el dashboard');
        }
        const data = await response.json();

        setText('kpi-recaudo', formatearMoneda(data.kpis?.recaudo));
        setText('kpi-desperdicio', `${Number(data.kpis?.desperdicio_kg || 0).toFixed(1)} Kg`);
        setText('kpi-retiros', data.kpis?.retiros_hoy ?? 0);
        setText('kpi-xp', `${data.kpis?.xp_total ?? 0} XP`);

        renderLineChart(data.charts?.retiros || { labels: [], data: [] });
        renderRiskChart(data.charts?.riesgo || { labels: [], data: [] });
        renderTransacciones(data.transacciones || []);
    } catch (error) {
        renderLineChart({ labels: [], data: [] });
        renderRiskChart({ labels: [], data: [] });
        renderTransacciones([]);
    }
}

document.addEventListener('DOMContentLoaded', () => {
    cargarDashboard();
});