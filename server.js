require('dotenv').config();
const express = require('express');
const path = require('path');
const pool = require('./db');

// Principio SOLID: Inyección de Dependencias (DIP) y Responsabilidad Única (SRP)
const { ReservaService } = require('./services/reservaService');
const { ProcesadorPagos } = require('./services/pagoService');

const app = express();
app.use(express.json());
app.use(express.static(path.join(__dirname, 'public')));

// Instancias de servicios (DIP: se inyecta la base de datos por constructor)
const reservaService = new ReservaService(pool);
const procesadorPagos = new ProcesadorPagos(pool);

// 1. Health check
app.get('/api/health', async (req, res) => {
  try {
    const { rows } = await pool.query(
      `SELECT now() AT TIME ZONE 'America/Lima' AS hora_lima,
              (SELECT abierto FROM config_local WHERE config_id = 1) AS local_abierto,
              (SELECT count(*) FROM fn_carga_dia((now() AT TIME ZONE 'America/Lima')::date))::int AS franjas_hoy`
    );
    res.json({ ok: true, ...rows[0] });
  } catch (err) {
    console.error(err);
    res.status(500).json({ ok: false, error: 'Error de conexión con la base de datos' });
  }
});

// 2. Consulta de carga por franjas
app.get('/api/carga-dia', async (req, res) => {
  try {
    const fecha = req.query.fecha || new Date().toISOString().split('T')[0];
    const { rows } = await pool.query(`SELECT * FROM fn_carga_dia($1::date)`, [fecha]);
    res.json({ ok: true, fecha, franjas: rows });
  } catch (err) {
    res.status(500).json({ ok: false, error: err.message });
  }
});

// 3. Crear Reserva (Usa ReservaService - SRP / ISP)
app.post('/api/reservas', async (req, res) => {
  try {
    const reserva = await reservaService.crearReservaWeb(req.body);
    res.json({ ok: true, reserva });
  } catch (err) {
    console.error(err);
    res.status(500).json({ ok: false, error: err.message });
  }
});

// Cancelar reserva por código (Cliente)
app.post('/api/reservas/cancelar', async (req, res) => {
  const { codigo, motivo } = req.body;
  try {
    const { rows } = await pool.query(
      `UPDATE reserva 
       SET estado = 'cancelada', motivo = $1, actualizado_en = now()
       WHERE codigo = $2 AND estado IN ('pendiente', 'confirmada')
       RETURNING *`,
      [motivo || 'Cancelado por el cliente', codigo]
    );

    if (rows.length === 0) {
      return res.status(404).json({ ok: false, error: 'No se encontró la reserva o ya estaba cancelada' });
    }

    res.json({ ok: true, reserva: rows[0] });
  } catch (err) {
    res.status(500).json({ ok: false, error: err.message });
  }
});

// 4. Listar Reservas Staff (Usa ReservaService - SRP / ISP)
app.get('/api/staff/reservas', async (req, res) => {
  try {
    const reservas = await reservaService.listarReservasStaff();
    res.json({ ok: true, reservas });
  } catch (err) {
    res.status(500).json({ ok: false, error: err.message });
  }
});

// 5. Actualizar Reserva Staff
app.patch('/api/staff/reservas/:id', async (req, res) => {
  const { id } = req.params;
  const { estado, motivo } = req.body;
  try {
    const reserva = await reservaService.actualizarEstadoReserva(id, estado, motivo);
    res.json({ ok: true, reserva });
  } catch (err) {
    res.status(500).json({ ok: false, error: err.message });
  }
});

// 6. Login para Personal
app.post('/api/auth/login', async (req, res) => {
  const { correo, password } = req.body;
  if (!correo || !password) {
    return res.status(400).json({ ok: false, error: 'Ingresa correo y contraseña' });
  }

  try {
    const { rows } = await pool.query(
      `SELECT personal_id, nombre, correo, password_hash, rol, activo 
       FROM personal 
       WHERE lower(correo) = lower($1)`,
      [correo.trim()]
    );

    if (rows.length === 0 || rows[0].password_hash !== password) {
      return res.status(401).json({ ok: false, error: 'Correo o contraseña incorrectos' });
    }

    const usuario = rows[0];
    if (!usuario.activo) {
      return res.status(403).json({ ok: false, error: 'Usuario desactivado' });
    }

    res.json({
      ok: true,
      usuario: {
        id: usuario.personal_id,
        nombre: usuario.nombre,
        correo: usuario.correo,
        rol: usuario.rol
      }
    });
  } catch (err) {
    res.status(500).json({ ok: false, error: err.message });
  }
});

// 7. Carta de platos
app.get('/api/carta', async (req, res) => {
  try {
    const { rows } = await pool.query(
      `SELECT p.plato_id, p.nombre, p.descripcion, p.precio, p.disponible, c.nombre AS categoria
       FROM plato p
       JOIN categoria c ON c.categoria_id = p.categoria_id
       WHERE p.activo = true AND c.activa = true
       ORDER BY c.orden, p.nombre`
    );
    res.json({ ok: true, platos: rows });
  } catch (err) {
    res.status(500).json({ ok: false, error: err.message });
  }
});

// 8. Cambiar disponibilidad de plato (Agotado/Habilitado)
app.patch('/api/platos/:id/toggle', async (req, res) => {
  try {
    const { rows } = await pool.query(
      `UPDATE plato SET disponible = NOT disponible WHERE plato_id = $1 RETURNING *`,
      [req.params.id]
    );
    res.json({ ok: true, plato: rows[0] });
  } catch (err) {
    res.status(500).json({ ok: false, error: err.message });
  }
});

// 9. Configuración del Local
app.get('/api/config', async (req, res) => {
  try {
    const { rows } = await pool.query(`SELECT * FROM config_local WHERE config_id = 1`);
    res.json({ ok: true, config: rows[0] });
  } catch (err) {
    res.status(500).json({ ok: false, error: err.message });
  }
});

app.put('/api/config', async (req, res) => {
  const { aforo_personas, total_mesas, yape_numero, yape_titular } = req.body;
  try {
    const { rows } = await pool.query(
      `UPDATE config_local 
       SET aforo_personas = $1, total_mesas = $2, yape_numero = $3, yape_titular = $4 
       WHERE config_id = 1 RETURNING *`,
      [aforo_personas, total_mesas, yape_numero, yape_titular]
    );
    res.json({ ok: true, config: rows[0] });
  } catch (err) {
    res.status(500).json({ ok: false, error: err.message });
  }
});

// 10. Crear Comanda
app.post('/api/pedidos', async (req, res) => {
  const { mesa_referencia, items, creado_por } = req.body;
  if (!items || items.length === 0) {
    return res.status(400).json({ ok: false, error: 'Debe agregar al menos un plato' });
  }

  const client = await pool.connect();
  try {
    await client.query('BEGIN');
    const pedidoRes = await client.query(
      `INSERT INTO pedido (tipo, canal, estado, mesa_referencia, creado_por, aceptado_en, preparacion_en)
       VALUES ('local', 'staff', 'en_preparacion', $1, $2, now(), now())
       RETURNING *`,
      [mesa_referencia || 'Mesa Barra', creado_por || null]
    );
    const pedido_id = pedidoRes.rows[0].pedido_id;

    for (const it of items) {
      await client.query(
        `INSERT INTO detalle_pedido (pedido_id, plato_id, cantidad, precio_venta)
         VALUES ($1, $2, $3, $4)`,
        [pedido_id, it.plato_id, it.cantidad, it.precio]
      );
    }

    await client.query('COMMIT');
    res.json({ ok: true, pedido: pedidoRes.rows[0] });
  } catch (err) {
    await client.query('ROLLBACK');
    res.status(500).json({ ok: false, error: err.message });
  } finally {
    client.release();
  }
});

// 11. Listar Comandas Activas
app.get('/api/pedidos', async (req, res) => {
  try {
    const { rows } = await pool.query(
      `SELECT p.pedido_id, p.mesa_referencia, p.estado, p.creado_en,
              COALESCE(SUM(d.cantidad * d.precio_venta), 0) AS total,
              JSON_AGG(JSON_BUILD_OBJECT('nombre', pl.nombre, 'cantidad', d.cantidad, 'precio', d.precio_venta)) AS platos
       FROM pedido p
       JOIN detalle_pedido d ON d.pedido_id = p.pedido_id
       JOIN plato pl ON pl.plato_id = d.plato_id
       GROUP BY p.pedido_id
       ORDER BY p.creado_en DESC`
    );
    res.json({ ok: true, pedidos: rows });
  } catch (err) {
    res.status(500).json({ ok: false, error: err.message });
  }
});

// 12. Cambiar estado de Comanda
app.patch('/api/pedidos/:id/estado', async (req, res) => {
  const { estado } = req.body;
  try {
    const timestampCol = estado === 'listo' ? ', listo_en = now()' : (estado === 'entregado' ? ', entregado_en = now()' : '');
    const { rows } = await pool.query(
      `UPDATE pedido SET estado = $1 ${timestampCol} WHERE pedido_id = $2 RETURNING *`,
      [estado, req.params.id]
    );
    res.json({ ok: true, pedido: rows[0] });
  } catch (err) {
    res.status(500).json({ ok: false, error: err.message });
  }
});

// 13. Registrar Pago (Usa ProcesadorPagos - OCP / LSP)
app.post('/api/pagos', async (req, res) => {
  const { pedido_id, monto, medio, referencia, confirmado_por } = req.body;
  try {
    const pago = await procesadorPagos.ejecutarPago(medio, {
      pedido_id,
      monto,
      referencia,
      confirmado_por
    });
    res.json({ ok: true, pago });
  } catch (err) {
    res.status(500).json({ ok: false, error: err.message });
  }
});

const PORT = process.env.PORT || 3000;
app.listen(PORT, () => console.log(`Servidor Quero listo en http://localhost:${PORT}`));