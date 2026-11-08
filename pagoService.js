class MetodoPago {
  constructor(nombre) {
    this.nombre = nombre;
  }

  async procesar({ pedido_id, monto, referencia, confirmado_por }, db) {
    throw new Error(`El método procesar() debe ser implementado por ${this.nombre}`);
  }
}

class PagoEfectivo extends MetodoPago {
  constructor() {
    super('Efectivo');
  }

  async procesar({ pedido_id, monto, confirmado_por }, db) {
    const { rows } = await db.query(
      `INSERT INTO pago (pedido_id, monto, medio, referencia, confirmado_por)
       VALUES ($1, $2, 'efectivo', 'PAGO_EN_MESA', $3) RETURNING *`,
      [pedido_id, monto, confirmado_por]
    );
    return rows[0];
  }
}

class PagoYape extends MetodoPago {
  constructor() {
    super('Yape');
  }

  async procesar({ pedido_id, monto, referencia, confirmado_por }, db) {
    const ref = referencia || `YAPE-${Math.random().toString(36).substring(2, 7).toUpperCase()}`;
    const { rows } = await db.query(
      `INSERT INTO pago (pedido_id, monto, medio, referencia, confirmado_por)
       VALUES ($1, $2, 'yape', $3, $4) RETURNING *`,
      [pedido_id, monto, ref, confirmado_por]
    );
    return rows[0];
  }
}

class PagoPlin extends MetodoPago {
  constructor() {
    super('Plin');
  }

  async procesar({ pedido_id, monto, referencia, confirmado_por }, db) {
    const ref = referencia || `PLIN-${Math.random().toString(36).substring(2, 7).toUpperCase()}`;
    const { rows } = await db.query(
      `INSERT INTO pago (pedido_id, monto, medio, referencia, confirmado_por)
       VALUES ($1, $2, 'plin', $3, $4) RETURNING *`,
      [pedido_id, monto, ref, confirmado_por]
    );
    return rows[0];
  }
}

class ProcesadorPagos {
  constructor(databaseProvider) {
    this.db = databaseProvider;
    this.estrategias = {
      efectivo: new PagoEfectivo(),
      yape: new PagoYape(),
      plin: new PagoPlin()
    };
  }

  async ejecutarPago(medio, datos) {
    const estrategia = this.estrategias[medio.toLowerCase()];
    if (!estrategia) {
      throw new Error(`El método de pago '${medio}' no está soportado`);
    }

    const pago = await estrategia.procesar(datos, this.db);

    await this.db.query(
      `UPDATE pedido SET estado = 'entregado', entregado_en = now() WHERE pedido_id = $1`,
      [datos.pedido_id]
    );

    return pago;
  }
}

module.exports = {
  MetodoPago,
  PagoEfectivo,
  PagoYape,
  PagoPlin,
  ProcesadorPagos
};