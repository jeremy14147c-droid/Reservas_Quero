class ReservaService {
  constructor(databaseProvider) {
    if (!databaseProvider) throw new Error("Se requiere un proveedor de base de datos");
    this.db = databaseProvider;
  }

  async crearReservaWeb({ nombre, telefono, fecha, hora, cantidad_personas, acepta_datos }) {
    if (!nombre || !telefono || !fecha || !hora || !cantidad_personas) {
      throw new Error('Faltan datos obligatorios para la reserva');
    }

    const client = await this.db.connect();
    try {
      await client.query('BEGIN');

      const clienteRes = await client.query(
        `INSERT INTO cliente (nombre, telefono, acepta_datos)
         VALUES ($1, $2, $3)
         ON CONFLICT (telefono) DO UPDATE SET nombre = EXCLUDED.nombre
         RETURNING cliente_id`,
        [nombre, telefono, acepta_datos !== false]
      );
      const cliente_id = clienteRes.rows[0].cliente_id;

      const codigo = 'RES-' + Math.random().toString(36).substring(2, 6).toUpperCase();

      const reservaRes = await client.query(
        `INSERT INTO reserva (codigo, cliente_id, fecha, hora, cantidad_personas, estado, canal)
         VALUES ($1, $2, $3::date, $4::time, $5, 'pendiente', 'web')
         RETURNING *`,
        [codigo, cliente_id, fecha, hora, cantidad_personas]
      );

      await client.query('COMMIT');
      return reservaRes.rows[0];
    } catch (err) {
      await client.query('ROLLBACK');
      throw err;
    } finally {
      client.release();
    }
  }

  async listarReservasStaff() {
    const { rows } = await this.db.query(
      `SELECT r.*, c.nombre AS cliente_nombre, c.telefono AS cliente_telefono
       FROM reserva r
       JOIN cliente c ON c.cliente_id = r.cliente_id
       ORDER BY r.creado_en DESC`
    );
    return rows;
  }

  async actualizarEstadoReserva(id, estado, motivo) {
    const { rows } = await this.db.query(
      `UPDATE reserva
       SET estado = $1, motivo = $2, actualizado_en = now()
       WHERE reserva_id = $3
       RETURNING *`,
      [estado, motivo || null, id]
    );
    return rows[0];
  }
}

module.exports = { ReservaService };