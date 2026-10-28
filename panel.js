const rawUser = sessionStorage.getItem('usuario_quero');
if (!rawUser) window.location.href = '/login.html';
const user = JSON.parse(rawUser);

document.getElementById('user-info').textContent = `${user.nombre} (${user.rol.toUpperCase()})`;
document.getElementById('btn-logout').onclick = () => {
  sessionStorage.removeItem('usuario_quero');
  window.location.href = '/login.html';
};

if (user.rol === 'admin') {
  document.querySelectorAll('.admin-only').forEach(el => el.style.display = 'block');
}

document.querySelectorAll('.tab-btn').forEach(btn => {
  btn.onclick = () => {
    document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
    document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
    btn.classList.add('active');
    document.getElementById(btn.dataset.tab).classList.add('active');
  };
});

async function cargarReservas() {
  const res = await fetch('/api/staff/reservas');
  const data = await res.json();
  const cont = document.getElementById('lista-reservas');
  if (!data.ok || !data.reservas.length) {
    cont.innerHTML = '<p style="color:var(--suave)">No hay reservas registradas.</p>';
    return;
  }

  cont.innerHTML = `<table>
    <thead><tr><th>Código</th><th>Cliente</th><th>Fecha/Hora</th><th>Pers.</th><th>Estado</th><th>Acciones</th></tr></thead>
    <tbody>
      ${data.reservas.map(r => `
        <tr>
          <td><strong>${r.codigo}</strong></td>
          <td>${r.cliente_nombre}<br><small style="color:var(--suave)">${r.cliente_telefono}</small></td>
          <td>${r.fecha.split('T')[0]} · ${r.hora.slice(0,5)}</td>
          <td>${r.cantidad_personas}</td>
          <td><span class="badge ${r.estado === 'confirmada' ? 'badge-ok' : (r.estado === 'pendiente' ? 'badge-alerta' : '')}">${r.estado}</span></td>
          <td>
            ${r.estado === 'pendiente' ? `
              <button class="btn btn-ok" onclick="cambiarReserva(${r.reserva_id}, 'confirmada')">Confirmar</button>
              <button class="btn btn-no" onclick="cambiarReserva(${r.reserva_id}, 'rechazada')">Rechazar</button>
            ` : (r.estado === 'confirmada' ? `
              <button class="btn btn-no" style="font-size:0.75rem; padding:0.3rem 0.6rem;" onclick="cambiarReserva(${r.reserva_id}, 'cancelada')">Anular Reserva</button>
            ` : `<small style="color:var(--suave)">${r.estado}</small>`)}
          </td>
        </tr>
      `).join('')}
    </tbody>
  </table>`;
}

window.cambiarReserva = async (id, estado) => {
  let motivo = null;
  if (estado === 'cancelada') {
    motivo = prompt('Motivo de la anulación (opcional):', 'Cliente canceló por WhatsApp o teléfono');
    if (motivo === null) return;
  }

  await fetch(`/api/staff/reservas/${id}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ estado, motivo })
  });
  cargarReservas();
};

let platosDisponibles = [];
let comandaActual = [];

async function cargarOpcionesPlatos() {
  const res = await fetch('/api/carta');
  const data = await res.json();
  if (data.ok) {
    platosDisponibles = data.platos.filter(p => p.disponible);
    const sel = document.getElementById('comanda-plato');
    sel.innerHTML = platosDisponibles.map(p => `
      <option value="${p.plato_id}">${p.nombre} - S/ ${parseFloat(p.precio).toFixed(2)}</option>
    `).join('');
  }
}

window.abrirModalComanda = () => {
  comandaActual = [];
  document.getElementById('comanda-mesa').value = '';
  document.getElementById('comanda-cant').value = '1';
  renderizarItemsComanda();
  document.getElementById('box-comanda').style.display = 'block';
  cargarOpcionesPlatos();
};

window.cerrarModalComanda = () => {
  comandaActual = [];
  document.getElementById('box-comanda').style.display = 'none';
};

window.agregarItemComanda = () => {
  const platoId = parseInt(document.getElementById('comanda-plato').value);
  const cant = parseInt(document.getElementById('comanda-cant').value) || 1;
  const plato = platosDisponibles.find(p => p.plato_id === platoId);

  if (!plato) return alert('Selecciona un plato válido');

  const existente = comandaActual.find(it => it.plato_id === platoId);
  if (existente) {
    existente.cantidad += cant;
  } else {
    comandaActual.push({
      plato_id: plato.plato_id,
      nombre: plato.nombre,
      cantidad: cant,
      precio: parseFloat(plato.precio)
    });
  }

  document.getElementById('comanda-cant').value = '1';
  renderizarItemsComanda();
};

window.quitarItemComanda = (index) => {
  comandaActual.splice(index, 1);
  renderizarItemsComanda();
};

function renderizarItemsComanda() {
  const cont = document.getElementById('comanda-items-lista');
  const totalTxt = document.getElementById('comanda-total-txt');

  if (comandaActual.length === 0) {
    cont.innerHTML = '<p style="color:var(--suave); font-size:0.85rem; margin:0;">No has agregado platos a esta comanda aún.</p>';
    totalTxt.textContent = 'S/ 0.00';
    return;
  }

  let total = 0;
  cont.innerHTML = comandaActual.map((it, idx) => {
    const subtotal = it.cantidad * it.precio;
    total += subtotal;
    return `
      <div style="display:flex; justify-content:space-between; align-items:center; padding:0.4rem 0; border-bottom:1px solid var(--borde);">
        <div>
          <strong style="color:var(--verde);">${it.cantidad}x</strong> ${it.nombre}
          <small style="color:var(--suave); margin-left:0.5rem;">(c/u S/ ${it.precio.toFixed(2)})</small>
        </div>
        <div style="display:flex; align-items:center; gap:0.8rem;">
          <strong>S/ ${subtotal.toFixed(2)}</strong>
          <button type="button" onclick="quitarItemComanda(${idx})" style="background:transparent; border:none; color:var(--mal-tx); cursor:pointer; font-weight:bold; font-size:1rem;" title="Quitar">❌</button>
        </div>
      </div>
    `;
  }).join('');

  totalTxt.textContent = `S/ ${total.toFixed(2)}`;
}

window.enviarComandaFinal = async () => {
  const mesa = document.getElementById('comanda-mesa').value.trim() || 'Mesa 1';
  if (comandaActual.length === 0) {
    return alert('Agrega al menos un plato a la comanda antes de mandar a cocina');
  }

  const res = await fetch('/api/pedidos', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      mesa_referencia: mesa,
      creado_por: user.id,
      items: comandaActual
    })
  });

  const data = await res.json();
  if (data.ok) {
    cerrarModalComanda();
    cargarPedidos();
  } else {
    alert('Error al enviar comanda: ' + (data.error || 'Error desconocido'));
  }
};

async function cargarPedidos() {
  const res = await fetch('/api/pedidos');
  const data = await res.json();
  const cont = document.getElementById('lista-pedidos');
  if (!data.ok || !data.pedidos.length) {
    cont.innerHTML = '<p style="color:var(--suave)">No hay comandas activas.</p>';
    return;
  }

  cont.innerHTML = `<table>
    <thead><tr><th>Mesa</th><th>Platos</th><th>Total</th><th>Estado</th><th>Acción</th></tr></thead>
    <tbody>
      ${data.pedidos.map(p => `
        <tr>
          <td><strong>${p.mesa_referencia}</strong></td>
          <td>${p.platos.map(it => `${it.cantidad}x ${it.nombre}`).join(', ')}</td>
          <td><strong>S/ ${parseFloat(p.total).toFixed(2)}</strong></td>
          <td><span class="badge ${p.estado === 'entregado' ? 'badge-ok' : 'badge-alerta'}">${p.estado}</span></td>
          <td>
            ${p.estado === 'en_preparacion' ? `
              <button class="btn btn-ok" onclick="cambiarEstadoPedido(${p.pedido_id}, 'listo')">¡Plato Listo!</button>
            ` : (p.estado === 'listo' ? `
              <button class="btn btn-ok" onclick="cobrarPedido(${p.pedido_id}, ${p.total})">Cobrar (Yape/Efectivo)</button>
            ` : '<small style="color:var(--suave)">Cobrado y cerrado</small>')}
          </td>
        </tr>
      `).join('')}
    </tbody>
  </table>`;
}

window.cambiarEstadoPedido = async (id, estado) => {
  await fetch(`/api/pedidos/${id}/estado`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ estado })
  });
  cargarPedidos();
};

window.cobrarPedido = async (id, total) => {
  const medio = prompt('¿Cómo paga el cliente? Escribe: efectivo o yape', 'yape');
  if (!medio) return;

  await fetch('/api/pagos', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      pedido_id: id,
      monto: total,
      medio: medio.toLowerCase(),
      confirmado_por: user.id
    })
  });
  alert('¡Pago registrado con éxito!');
  cargarPedidos();
};

async function cargarCarta() {
  if (user.rol !== 'admin') return;
  const res = await fetch('/api/carta');
  const data = await res.json();
  const tbody = document.getElementById('tabla-carta');
  if (!data.ok) return;

  tbody.innerHTML = data.platos.map(p => `
    <tr>
      <td><small style="color:var(--suave)">${p.categoria}</small></td>
      <td><strong>${p.nombre}</strong></td>
      <td>S/ ${parseFloat(p.precio).toFixed(2)}</td>
      <td><span class="badge ${p.disponible ? 'badge-ok' : 'badge-alerta'}">${p.disponible ? 'Disponible' : 'Agotado'}</span></td>
      <td>
        <button class="btn ${p.disponible ? 'btn-no' : 'btn-ok'}" onclick="togglePlato(${p.plato_id})">
          ${p.disponible ? 'Pausar (Agotado)' : 'Habilitar'}
        </button>
      </td>
    </tr>
  `).join('');
}

window.togglePlato = async (id) => {
  await fetch(`/api/platos/${id}/toggle`, { method: 'PATCH' });
  cargarCarta();
};

async function cargarConfig() {
  if (user.rol !== 'admin') return;
  const res = await fetch('/api/config');
  const data = await res.json();
  if (data.ok && data.config) {
    document.getElementById('cfg-aforo').value = data.config.aforo_personas;
    document.getElementById('cfg-mesas').value = data.config.total_mesas;
    document.getElementById('cfg-yape-num').value = data.config.yape_numero || '';
    document.getElementById('cfg-yape-tit').value = data.config.yape_titular || '';
  }
}

document.getElementById('form-config').onsubmit = async (e) => {
  e.preventDefault();
  const payload = {
    aforo_personas: document.getElementById('cfg-aforo').value,
    total_mesas: document.getElementById('cfg-mesas').value,
    yape_numero: document.getElementById('cfg-yape-num').value,
    yape_titular: document.getElementById('cfg-yape-tit').value
  };
  const res = await fetch('/api/config', {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload)
  });
  const data = await res.json();
  if (data.ok) alert('¡Configuración actualizada en PostgreSQL!');
};

cargarReservas();
cargarPedidos();
cargarCarta();
cargarConfig();