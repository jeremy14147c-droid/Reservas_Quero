/* =====================================================================
   Cola de pedidos del staff (Fase 3)
   - Datos: GET /api/v1/pedidos/cola (recarga cada 10 s)
   - Acciones por la API JSON; errores con mensaje claro.
   - Insignia + sonido OPCIONAL cuando aparece un pendiente nuevo.
   ===================================================================== */

const CSRF_Q = document.querySelector('meta[name="csrf-token"]').content;
const ESTADOS_TXT = {
    pendiente: 'Pendiente',
    aceptado: 'Aceptado (por cobrar)',
    en_preparacion: 'En cocina',
    listo: 'Listo',
    entregado: 'Entregado',
    rechazado: 'Rechazado',
    cancelado: 'Cancelado'
};

let datosCola = null;
let idsPendPrev = null;
let sonidoQ = false;
let contextoAudioQ = null;

document.addEventListener('DOMContentLoaded', () => {
    document.getElementById('btn-sonido').addEventListener('click', function () {
        sonidoQ = !sonidoQ;
        if (sonidoQ && !contextoAudioQ) {
            contextoAudioQ = new (window.AudioContext || window.webkitAudioContext)();
        }
        this.innerHTML = sonidoQ
            ? '<i class="bi bi-volume-up me-1"></i> Sonido activado'
            : '<i class="bi bi-volume-mute me-1"></i> Activar sonido';
        this.classList.toggle('btn-success', sonidoQ);
        this.classList.toggle('btn-outline-secondary', !sonidoQ);
    });

    /* Casilla "Imprimir al pasar a cocina" (apagada por defecto; recuerda su elección) */
    const casilla = document.getElementById('imprimir-auto');
    casilla.checked = localStorage.getItem('imprimir_al_cocinar') === 'si';
    casilla.addEventListener('change', () => {
        localStorage.setItem('imprimir_al_cocinar', casilla.checked ? 'si' : 'no');
    });

    refrescarCola();
    setInterval(refrescarCola, 10000);
});

function pesos(valor) {
    return 'S/ ' + (parseFloat(valor || 0)).toFixed(2);
}

async function apiQ(url, cuerpo) {
    const opciones = {
        method: cuerpo ? 'POST' : 'GET',
        headers: { 'Content-Type': 'application/json', 'X-CSRFToken': CSRF_Q }
    };
    if (cuerpo) opciones.body = JSON.stringify(cuerpo);
    const respuesta = await fetch(url, opciones);
    const cuerpoJson = await respuesta.json();
    return { estado: respuesta.status, cuerpo: cuerpoJson };
}

function mostrarToast(texto, esError) {
    const toast = document.getElementById(esError ? 'toast-error' : 'toast-aviso');
    toast.textContent = texto;
    toast.classList.remove('d-none');
    setTimeout(() => toast.classList.add('d-none'), 4000);
}

async function refrescarCola() {
    try {
        const r = await fetch('/api/v1/pedidos/cola', { headers: { 'X-CSRFToken': CSRF_Q } });
        const json = await r.json();
        if (!json.ok) throw new Error(json.error ? json.error.mensaje : 'Error de servidor');
        datosCola = json.datos;
        pintarCola();
        detectarPendientesNuevos();
        detectarNuevosEnCocina();
    } catch (e) {
        // el banner "Sin conexión" lo maneja main.js; aquí solo avisamos p. ej. sesión vencida
        console.warn('No se pudo refrescar la cola:', e.message);
    }
}

function pintarCola() {
    pintarColumna('pendientes', 'col-pendientes', 'n-pendientes', true);
    pintarColumna('por_cobrar', 'col-cobrar', 'n-cobrar', false);
    pintarColumna('en_cocina', 'col-cocina', 'n-cocina', false);
    pintarColumna('listos', 'col-listos', 'n-listos', false);
    document.getElementById('n-entregados').textContent = (datosCola.entregados || []).length;

    const insignia = document.getElementById('insignia-pendientes');
    insignia.textContent = (datosCola.pendientes || []).length;
    insignia.classList.toggle('d-none', (datosCola.pendientes || []).length === 0);
}

function pintarColumna(nombreLista, idCol, idConteo, esPendiente) {
    document.getElementById(idConteo).textContent = (datosCola[nombreLista] || []).length;
    const col = document.getElementById(idCol);
    if (!(datosCola[nombreLista] || []).length) {
        col.innerHTML = '<p class="text-muted small text-center mb-0 py-3">Nada por aquí.</p>';
        return;
    }
    let html = '';
    (datosCola[nombreLista] || []).forEach(p => { html += tarjetaPedido(p, esPendiente); });
    col.innerHTML = html;
}

function tarjetaPedido(p, esPendiente) {
    const tipoMarca = p.tipo === 'recojo'
        ? '<span class="badge bg-warning text-dark">Recojo web</span>'
        : '<span class="badge bg-primary">Local</span>';
    const cliente = p.cliente_nombre
        ? `<strong>${esc(p.cliente_nombre)}</strong><div class="small"><i class="bi bi-telephone"></i> ${esc(p.cliente_telefono || '')}</div>`
        : (p.tipo === 'local' && p.mesa_referencia
            ? `<strong>${esc(p.mesa_referencia)}</strong>`
            : '<strong>Cliente del local</strong>');

    let acciones = '';
    if (p.estado === 'pendiente') {
        acciones = `
        <div class="d-flex gap-1 mt-2">
            <button class="btn btn-success btn-sm flex-fill" onclick="aceptarPedido(${p.pedido_id})"><i class="bi bi-check2"></i> Aceptar</button>
            <button class="btn btn-outline-danger btn-sm" onclick="rechazarPedido(${p.pedido_id})"><i class="bi bi-x-lg"></i> Rechazar</button>
        </div>`;
    } else if (p.estado === 'aceptado') {
        acciones = `
        <div class="mt-2 d-flex gap-1">
            <a class="btn btn-primary btn-sm flex-fill" href="/staff/pedido/${p.pedido_id}">
                <i class="bi bi-cash-coin"></i> Registrar pago</a>
        </div>`;
    } else if (p.estado === 'en_preparacion') {
        acciones = `
        <div class="d-flex gap-1 mt-2">
            <button class="btn btn-success btn-sm flex-fill" onclick="marcarListo(${p.pedido_id})"><i class="bi bi-check2"></i> Listo</button>
        </div>`;
    } else if (p.estado === 'listo') {
        acciones = `
        <div class="d-flex gap-1 mt-2">
            <button class="btn btn-dark btn-sm flex-fill" onclick="entregarPedido(${p.pedido_id})"><i class="bi bi-box-arrow-right"></i> Entregado</button>
        </div>`;
    } else if (p.estado === 'entregado') {
        acciones = '<div class="small text-success mt-2"><i class="bi bi-check2-all"></i> Entregado</div>';
    }

    const chipCobro = p.cobrado ? '<span class="badge bg-success">Cobrado</span>'
        : `<span class="badge bg-secondary">${pesos(p.total)}</span>`;

    return `
    <div class="card mb-2 card-pedido ${p.tipo === 'recojo' ? 'recojo' : 'local'}">
        <div class="card-body p-2">
            <div class="d-flex justify-content-between align-items-start">
                <div>
                    ${cliente}
                    ${p.tipo === 'recojo' && p.actividad_24h ? '<span class="badge bg-info">ya pidió hace menos de 24 h</span>' : ''}
                    <div class="small mt-1">${tipoMarca} ${chipCobro} <span class="text-muted">N° ${p.pedido_id}</span></div>
                </div>
                <div class="dropdown menu-acciones">
                    <button class="btn btn-sm btn-outline-secondary" data-bs-toggle="dropdown">${'&#8942;'}</button>
                    ${menuPedido(p)}
                </div>
            </div>
            <div class="small text-muted">A las ${horaCorta(p.creado_en)}</div>
            ${acciones}
        </div>
    </div>`;
}

function menuPedido(p) {
    const id = p.pedido_id;
    let items = '';
    if (p.cliente_telefono) {
        const msj = `Hola ${p.cliente_nombre || ''}, le escribimos de Quero Gastrobar: su pedido N° ${id} está ${ESTADOS_TXT[p.estado]}.`;
        items += `<li><a class="dropdown-item" target="_blank" rel="noopener"
                      href="https://wa.me/51${esc(p.cliente_telefono)}?text=${encodeURIComponent(msj)}">
                      <i class="bi bi-whatsapp text-success me-2"></i>WhatsApp</a></li>
                  <li><a class="dropdown-item" href="tel:+51${esc(p.cliente_telefono)}"><i class="bi bi-telephone me-2"></i>Llamar</a></li>`;
        if (p.cliente_correo) {
            items += `<li><a class="dropdown-item" href="mailto:${esc(p.cliente_correo)}"><i class="bi bi-envelope me-2"></i>Correo</a></li>`;
        }
        items += `<li><hr class="dropdown-divider"></li>`;
    }
    items += `
        <li><a class="dropdown-item" href="/staff/pedido/${id}"><i class="bi bi-eye me-2"></i>Ver detalle</a></li>
        <li><a class="dropdown-item" href="/staff/pedido/${id}/ticket" target="_blank"><i class="bi bi-printer me-2"></i>Imprimir ticket</a></li>
        <li><a class="dropdown-item" href="/pedido/${p.token}" target="_blank"><i class="bi bi-link-45deg me-2"></i>Ver página del cliente</a></li>`;
    if (['pendiente', 'aceptado', 'en_preparacion', 'listo'].includes(p.estado)) {
        items += `<li><a class="dropdown-item text-danger" href="#" onclick="cancelarPedido(${id}); return false;"><i class="bi bi-slash-circle me-2"></i>Cancelar</a></li>`;
    }
    return `<ul class="dropdown-menu dropdown-menu-end">${items}</ul>`;
}

/* ------------------------- acciones ------------------------- */
async function aceptarPedido(id) {
    const r = await apiQ('/api/v1/pedidos/' + id + '/aceptar', {});
    r.cuerpo.ok ? mostrarToast('Pedido aceptado: ya puede pagarle al cliente.')
                : mostrarToast(r.cuerpo.error.mensaje, true);
    refrescarCola();
}
async function rechazarPedido(id) {
    const motivo = prompt('Motivo del rechazo (obligatorio):');
    if (!motivo || !motivo.trim()) return;
    const r = await apiQ('/api/v1/pedidos/' + id + '/rechazar', { motivo: motivo.trim() });
    r.cuerpo.ok ? mostrarToast('Pedido rechazado.')
                : mostrarToast(r.cuerpo.error.mensaje, true);
    refrescarCola();
}
async function marcarListo(id) {
    const r = await apiQ('/api/v1/pedidos/' + id + '/listo', {});
    r.cuerpo.ok ? mostrarToast('Pedido LISTO para recoger.')
                : mostrarToast(r.cuerpo.error.mensaje, true);
    refrescarCola();
}
async function entregarPedido(id) {
    const r = await apiQ('/api/v1/pedidos/' + id + '/entregar', {});
    r.cuerpo.ok ? mostrarToast('Pedido entregado. ¡Buen provecho!')
                : mostrarToast(r.cuerpo.error.mensaje, true);
    refrescarCola();
}
async function cancelarPedido(id) {
    if (!confirm('¿Cancelar este pedido?')) return;
    const r = await apiQ('/api/v1/pedidos/' + id + '/cancelar', {});
    r.cuerpo.ok ? mostrarToast('Pedido cancelado.')
                : mostrarToast(r.cuerpo.error.mensaje, true);
    refrescarCola();
}

/* ------------------------- insignia y sonido ------------------------- */
function detectarPendientesNuevos() {
    const ids = (datosCola.pendientes || []).map(p => p.pedido_id);
    if (idsPendPrev === null) { idsPendPrev = ids; return; }
    const nuevos = ids.filter(id => !idsPendPrev.includes(id));
    if (nuevos.length) {
        sonarQ();
        mostrarToast('Hay ' + nuevos.length + ' pedido(s) nuevo(s) por revisar.');
    }
    idsPendPrev = ids;
}

/* ------------------------- impresión al pasar a cocina (nivel 2) ------------------------- */
let idsCocinaPrev = null;
function detectarNuevosEnCocina() {
    const casilla = document.getElementById('imprimir-auto');
    const ids = (datosCola.en_cocina || []).map(p => p.pedido_id);
    if (idsCocinaPrev === null) { idsCocinaPrev = ids; return; }
    const nuevos = ids.filter(id => !idsCocinaPrev.includes(id));
    if (nuevos.length && casilla && casilla.checked) {
        // abre el ticket de CADA pedido nuevo; con ?auto=1 el ticket imprime al cargar
        nuevos.forEach(id => window.open('/staff/pedido/' + id + '/ticket?auto=1', '_blank'));
    }
    idsCocinaPrev = ids;
}

function sonarQ() {
    if (!sonidoQ || !contextoAudioQ) return;
    const osc = contextoAudioQ.createOscillator();
    const vol = contextoAudioQ.createGain();
    osc.connect(vol); vol.connect(contextoAudioQ.destination);
    osc.frequency.value = 880; vol.gain.value = 0.25;
    osc.start();
    setTimeout(() => osc.stop(), 350);
}

function horaCorta(iso) {
    return iso ? iso.substring(11, 16) : '';
}
