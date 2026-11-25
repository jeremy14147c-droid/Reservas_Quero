const C = { aforo: 40, mesas: 10, ppm: 4, est: 90, fr: 30, ap: 720, ci: 1320, alerta: 80 };
let R = [];
let sel = null;

const $ = id => document.getElementById(id);
const hm = m => String(Math.floor(m / 60)).padStart(2, "0") + ":" + String(m % 60).padStart(2, "0");
const mesasDe = p => Math.ceil(p / C.ppm);
const slots = () => { const a = []; for (let m = C.ap; m <= C.ci - C.fr; m += C.fr) a.push(m); return a; };
const esc = t => String(t).replace(/[&<>"]/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));

async function cargarReservas() {
  try {
    const res = await fetch('/api/staff/reservas');
    const data = await res.json();
    if (data.ok) {
      R = data.reservas.map(r => {
        const [hh, mm] = r.hora.split(':').map(Number);
        return {
          id: r.reserva_id,
          cod: r.codigo,
          nombre: r.cliente_nombre,
          min: hh * 60 + mm,
          p: r.cantidad_personas,
          e: r.estado,
          motivo: r.motivo
        };
      });
      pintarHoras();
    }
  } catch (err) {
    console.error("Error al cargar reservas:", err);
  }
}

function carga(s) {
  let p = 0, m = 0, k = 0;
  for (const r of R) {
    if (r.e !== "confirmada" && r.e !== "llego") continue;
    if (r.min < s + C.fr && r.min + C.est > s) { p += r.p; m += mesasDe(r.p); k++; }
  }
  return { p, m, k };
}

function estadoHora(h, n) {
  let ok = true, peor = 0;
  for (const s of slots()) {
    if (s < h + C.est && s + C.fr > h) {
      const c = carga(s), p = c.p + n, m = c.m + mesasDe(n);
      if (p > C.aforo || m > C.mesas) ok = false;
      peor = Math.max(peor, p / C.aforo, m / C.mesas);
    }
  }
  return !ok ? "lleno" : (peor * 100 >= C.alerta ? "pocas" : "libre");
}

function pintarHoras() {
  const n = Math.max(1, parseInt($("n").value) || 1);
  const txt = { libre: "Disponible", pocas: "Pocas mesas", lleno: "Lleno" };
  $("horas").innerHTML = slots().map(h => {
    const e = estadoHora(h, n);
    return `<button type="button" class="hora ${e}" data-h="${h}" ${e === "lleno" ? "disabled" : ""} aria-pressed="${sel === h}">${hm(h)}<small>${txt[e]}</small></button>`;
  }).join("");
  if (sel !== null && estadoHora(sel, n) === "lleno") sel = null;
}

$("horas").addEventListener("click", e => {
  const b = e.target.closest(".hora");
  if (!b || b.disabled) return;
  sel = +b.dataset.h;
  pintarHoras();
});

$("n").addEventListener("input", pintarHoras);

$("enviar").addEventListener("click", async () => {
  const n = parseInt($("n").value) || 0,
    nom = $("nom").value.trim(),
    tel = $("tel").value.trim(),
    out = $("res-cli");

  const err = t => { out.innerHTML = `<div style="background:var(--mal-bg); color:var(--mal-tx); padding:0.8rem; border-radius:6px; margin-top:1rem;">${t}</div>`; };
  if (n < 1) return err("Indica cuántas personas son.");
  if (sel === null) return err("Elige una hora disponible.");
  if (!nom) return err("Escribe tu nombre.");
  if (!/^9\d{8}$/.test(tel)) return err("El teléfono debe tener 9 dígitos y empezar con 9.");
  if (!$("acepta").checked) return err("Debes aceptar el uso de tus datos para continuar.");

  const fechaHoy = new Date().toISOString().split('T')[0];
  out.innerHTML = `<div style="color:var(--suave); margin-top:1rem;">Guardando reserva en la base de datos...</div>`;

  try {
    const res = await fetch('/api/reservas', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        nombre: nom,
        telefono: tel,
        fecha: fechaHoy,
        hora: hm(sel),
        cantidad_personas: n,
        acepta_datos: true
      })
    });

    const data = await res.json();
    if (!data.ok) throw new Error(data.error || 'Error al guardar');

    const cod = data.reserva.codigo;
    const msgWsp = encodeURIComponent(
      `Hola Quero 👋, acabo de solicitar una reserva en su web:\n\n` +
      `📌 *Código:* ${cod}\n👤 *Nombre:* ${nom}\n📅 *Fecha:* ${fechaHoy}\n⏰ *Hora:* ${hm(sel)}\n👥 *Personas:* ${n}\n\n` +
      `Quedo atento a su confirmación. ¡Muchas gracias!`
    );
    const linkWsp = `https://wa.me/51996908138?text=${msgWsp}`;

    out.innerHTML = `
      <div style="background:var(--sup); border:2px dashed var(--verde); border-radius:12px; padding:1.5rem; margin-top:1.5rem; text-align:center;">
        <div style="font-size:0.8rem; text-transform:uppercase; color:var(--suave);">Solicitud Registrada</div>
        <div style="font-size:2rem; font-weight:bold; color:var(--verde); margin:0.3rem 0;">${cod}</div>
        <div style="background:var(--fondo); border:1px solid var(--borde); border-radius:8px; padding:0.8rem; margin:1rem 0; text-align:left; font-size:0.9rem;">
          <div><strong>Titular:</strong> ${esc(nom)}</div>
          <div><strong>Fecha y Hora:</strong> ${fechaHoy} a las ${hm(sel)}</div>
          <div><strong>Asistentes:</strong> ${n} personas</div>
        </div>
        <a href="${linkWsp}" target="_blank" style="display:inline-block; background:#25d366; color:#fff; font-weight:bold; padding:0.8rem 1.2rem; border-radius:8px; text-decoration:none; margin-top:0.5rem;">
          📲 Enviar datos a WhatsApp
        </a>
      </div>
        <div style="margin-top:1rem;">
          <button type="button" onclick="cancelarReservaCliente('${cod}')" style="background:transparent; border:1px solid var(--mal-tx); color:var(--mal-tx); padding:0.5rem 1rem; border-radius:6px; cursor:pointer; font-size:0.85rem;">
            ❌ Cancelar mi reserva
          </button>
        </div>
    `;

    sel = null;
    $("nom").value = "";
    $("tel").value = "";
    await cargarReservas();
  } catch (e) {
    err("Error al guardar reserva: " + e.message);
  }
});

async function cargarCartaCliente() {
  const cont = $("lista-carta-cliente");
  cont.innerHTML = "<p style='color:var(--suave)'>Consultando carta...</p>";
  try {
    const res = await fetch('/api/carta');
    const data = await res.json();
    if (!data.ok || !data.platos.length) {
      cont.innerHTML = '<p style="color:var(--suave)">No hay platos registrados en la carta aún.</p>';
      return;
    }
    cont.innerHTML = data.platos.map(p => `
      <div style="background:var(--sup); border:1px solid var(--borde); border-radius:10px; padding:1.2rem; display:flex; justify-content:space-between; align-items:center;">
        <div>
          <span style="font-size:0.75rem; color:var(--verde); text-transform:uppercase; font-weight:bold;">${p.categoria}</span>
          <h3 style="font-size:1.15rem; margin:0.2rem 0;">${p.nombre}</h3>
          <p style="font-size:0.85rem; color:var(--suave); margin:0;">${p.descripcion || ''}</p>
        </div>
        <div style="text-align:right;">
          <div style="font-size:1.2rem; font-weight:bold;">S/ ${parseFloat(p.precio).toFixed(2)}</div>
          <span style="display:inline-block; margin-top:0.3rem; font-size:0.75rem; padding:0.2rem 0.5rem; border-radius:4px; font-weight:bold; ${p.disponible ? 'background:#17513c; color:#dcefe6;' : 'background:#481d19; color:#f4a9a0;'}">
            ${p.disponible ? 'Disponible' : 'Agotado'}
          </span>
        </div>
      </div>
    `).join('');
  } catch (err) {
    cont.innerHTML = `<p style="color:var(--mal-tx)">Error al cargar carta: ${err.message}</p>`;
  }
}

function ir(v) {
  $("v-cli").hidden = (v !== "cli");
  $("v-carta").hidden = (v !== "carta");
  $("t-cli").setAttribute("aria-selected", v === "cli");
  $("t-carta").setAttribute("aria-selected", v === "carta");
  if (v === "carta") cargarCartaCliente();
}

$("t-cli").onclick = () => ir("cli");
$("t-carta").onclick = () => ir("carta");

cargarReservas();

// Función para cancelar reserva desde la web del cliente
window.cancelarReservaCliente = async (cod) => {
  if (!confirm(`¿Estás seguro de cancelar la reserva ${cod}? Se liberará tu mesa.`)) return;

  try {
    const res = await fetch('/api/reservas/cancelar', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ codigo: cod, motivo: 'Cancelada por el cliente desde la web' })
    });
    const data = await res.json();
    if (!data.ok) throw new Error(data.error);

    alert(`Tu reserva ${cod} ha sido cancelada con éxito. Tu mesa ha sido liberada.`);
    $("res-cli").innerHTML = `<div style="background:var(--mal-bg); color:var(--mal-tx); padding:1rem; border-radius:8px; margin-top:1rem; text-align:center;">Tu reserva <strong>${cod}</strong> fue cancelada.</div>`;
    await cargarReservas();
  } catch (err) {
    alert('Error al cancelar: ' + err.message);
  }
};