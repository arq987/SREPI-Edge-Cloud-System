const API_BASE = window.SREPI_API_BASE || 'https://srepi-backend.onrender.com';
let lineChartInstance = null;
let riskChartInstance = null;

function setText(id, value) {
    const el = document.getElementById(id);
    if (el) el.textContent = value;
}

function formatearMoneda(valor) {
    return new Intl.NumberFormat('es-CO', {
        style: 'currency',
        currency: 'COP',
        maximumFractionDigits: 0
    }).format(Number(valor || 0));
}

function renderLineChart(config) {
    const canvas = document.getElementById('graficoRetiros');
    if (!canvas || typeof Chart === 'undefined') return;
    const ctx = canvas.getContext('2d');
    if (lineChartInstance) lineChartInstance.destroy();
    lineChartInstance = new Chart(ctx, {
        type: 'line',
        data: {
            labels: config.labels,
            datasets: [{
                label: 'Rescates',
                data: config.data,
                borderColor: '#2c70ff',
                backgroundColor: 'rgba(44, 112, 255, 0.08)',
                borderWidth: 2,
                pointBackgroundColor: '#2c70ff',
                pointRadius: 4,
                fill: true,
                tension: 0.4
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false },
                tooltip: {
                    callbacks: {
                        label: ctx => ` ${ctx.parsed.y} rescate${ctx.parsed.y !== 1 ? 's' : ''}`
                    }
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    ticks: { precision: 0, color: '#64748b', font: { size: 12 } },
                    grid: { color: 'rgba(0,0,0,0.05)' }
                },
                x: {
                    ticks: { color: '#64748b', font: { size: 12 } },
                    grid: { display: false }
                }
            }
        }
    });
}

function renderRiskChart(config) {
    const canvas = document.getElementById('graficoRiesgo');
    if (!canvas || typeof Chart === 'undefined') return;
    const ctx = canvas.getContext('2d');
    if (riskChartInstance) riskChartInstance.destroy();
    const total = (config.data || []).reduce((a, b) => a + b, 0);
    riskChartInstance = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: config.labels,
            datasets: [{
                data: config.data,
                backgroundColor: ['#ef4444', '#f59e0b', '#10b981'],
                borderWidth: 2,
                borderColor: '#fff',
                hoverOffset: 6
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            cutout: '65%',
            plugins: {
                legend: {
                    position: 'bottom',
                    labels: { font: { size: 12 }, padding: 16, usePointStyle: true }
                },
                tooltip: {
                    callbacks: {
                        label: ctx => {
                            const pct = total > 0 ? Math.round(ctx.parsed / total * 100) : 0;
                            return ` ${ctx.parsed} lote${ctx.parsed !== 1 ? 's' : ''} (${pct}%)`;
                        }
                    }
                }
            }
        }
    });
}

function renderTransacciones(transacciones) {
    const cuerpo = document.getElementById('tabla-transacciones');
    if (!cuerpo) return;
    cuerpo.innerHTML = '';
    if (!transacciones || !transacciones.length) {
        const fila = document.createElement('tr');
        fila.innerHTML = '<td colspan="6" style="text-align:center;color:#64748b;padding:20px;">Sin transacciones registradas</td>';
        cuerpo.appendChild(fila);
        return;
    }
    transacciones.forEach(item => {
        const fila = document.createElement('tr');
        fila.innerHTML = `
            <td><code style="font-size:12px;color:#64748b;">${item.id}</code></td>
            <td>${item.usuario}</td>
            <td>${item.producto}</td>
            <td style="color:#16a34a;font-weight:700;">${formatearMoneda(item.ahorro)}</td>
            <td style="font-weight:600;">${formatearMoneda(item.recaudo)}</td>
            <td><span class="badge badge-active">${item.estado}</span></td>
        `;
        cuerpo.appendChild(fila);
    });
}

function setEstado(msg, isError) {
    const el = document.getElementById('dash-estado');
    if (!el) return;
    el.textContent = msg;
    el.style.color = isError ? '#ef4444' : '#64748b';
}

async function cargarDashboard() {
    setEstado('Actualizando...');
    try {
        const response = await fetch(`${API_BASE}/api/dashboard/operacion`, { cache: 'no-store' });
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        const data = await response.json();

        const kpis = data.kpis || {};
        setText('kpi-recaudo', formatearMoneda(kpis.recaudo));
        setText('kpi-desperdicio', `${Number(kpis.desperdicio_kg || 0).toFixed(2)} Kg`);
        setText('kpi-retiros', kpis.retiros_hoy ?? 0);
        setText('kpi-xp', `${kpis.xp_total ?? 0} XP`);

        renderLineChart(data.charts?.retiros || { labels: [], data: [] });
        renderRiskChart(data.charts?.riesgo || { labels: [], data: [] });
        renderTransacciones(data.transacciones || []);
        setEstado('Actualizado');
    } catch (error) {
        setEstado('Sin conexion al servidor', true);
        renderLineChart({ labels: [], data: [] });
        renderRiskChart({ labels: [], data: [] });
        renderTransacciones([]);
    }
}

document.addEventListener('DOMContentLoaded', () => {
    cargarDashboard();
    const btn = document.getElementById('btn-actualizar');
    if (btn) btn.addEventListener('click', cargarDashboard);
});
