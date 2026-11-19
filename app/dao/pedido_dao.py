"""DAO para la entidad Pedido (tablas pedido, detalle_pedido, pago y vista v_pedido_resumen)."""
from app.db import consultar_todos, consultar_uno, ejecutar, ejecutar_retornando


class PedidoDAO:
    """Acceso a datos de pedidos, líneas de detalle y cobros."""

    def insertar_recojo(self, cliente_id, nota=None):
        """Inserta un pedido de tipo 'recojo' (nace 'pendiente')."""
        return ejecutar_retornando(
            """
            INSERT INTO pedido (cliente_id, tipo, canal, estado, nota)
            VALUES (%s, 'recojo', 'web', 'pendiente', %s)
            RETURNING pedido_id, token, tipo, canal, estado
            """,
            (cliente_id, nota)
        )

    def insertar_local(self, cliente_id, mesa_referencia, nota, personal_id):
        """Inserta un pedido de tipo 'local' (nace 'en_preparacion')."""
        return ejecutar_retornando(
            """
            INSERT INTO pedido (cliente_id, tipo, canal, estado, mesa_referencia, nota, creado_por, preparacion_en)
            VALUES (%s, 'local', 'staff', 'en_preparacion', %s, %s, %s, now())
            RETURNING pedido_id, token, tipo, canal, estado, mesa_referencia
            """,
            (cliente_id, mesa_referencia, nota, personal_id)
        )

    def insertar_lineas(self, pedido_id, lineas):
        """Inserta las líneas en detalle_pedido con su precio_venta copiado."""
        for linea in lineas:
            ejecutar(
                """
                INSERT INTO detalle_pedido (pedido_id, plato_id, cantidad, precio_venta, nota)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (pedido_id, linea["plato_id"], linea["cantidad"], linea["precio_venta"], linea["nota"])
            )

    def limpiar_lineas(self, pedido_id):
        """Elimina las líneas de detalle de un pedido."""
        ejecutar("DELETE FROM detalle_pedido WHERE pedido_id = %s", (pedido_id,))

    def buscar_por_id(self, pedido_id):
        """Busca el registro básico de un pedido."""
        return consultar_uno("SELECT pedido_id, estado, tipo FROM pedido WHERE pedido_id = %s", (pedido_id,))

    def obtener_resumen(self, pedido_id):
        """Obtiene la fila de v_pedido_resumen con total, pagado y cobrado."""
        return consultar_uno(
            """
            SELECT p.pedido_id, p.token, p.tipo, p.canal, p.estado, p.mesa_referencia,
                   p.nota, p.motivo_rechazo, p.creado_por,
                   p.creado_en, p.aceptado_en, p.preparacion_en, p.listo_en, p.entregado_en,
                   r.total, r.pagado, r.cobrado
            FROM pedido p JOIN v_pedido_resumen r ON r.pedido_id = p.pedido_id
            WHERE p.pedido_id = %s
            """,
            (pedido_id,)
        )

    def actualizar_estado(self, pedido_id, nuevo_estado, asignado_tiempo_sql="", motivo_rechazo=None):
        """Actualiza el estado y marca temporal correspondiente."""
        return ejecutar_retornando(
            f"""
            UPDATE pedido
            SET estado = %s, {asignado_tiempo_sql}motivo_rechazo = COALESCE(%s, motivo_rechazo)
            WHERE pedido_id = %s
            RETURNING pedido_id, token, tipo, canal, estado
            """,
            (nuevo_estado, motivo_rechazo, pedido_id)
        )

    def registrar_pago(self, pedido_id, monto, medio, referencia, personal_id):
        """Inserta un registro en la tabla pago."""
        return ejecutar_retornando(
            """
            INSERT INTO pago (pedido_id, monto, medio, referencia, confirmado_por)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING pago_id, pedido_id, monto, medio, referencia, confirmado_en
            """,
            (pedido_id, monto, medio, referencia, personal_id)
        )

    def obtener_pedido_detalle(self, pedido_id):
        """Obtiene la cabecera completa del pedido con datos del cliente."""
        return consultar_uno(
            """
            SELECT p.pedido_id, p.token, p.tipo, p.canal, p.estado, p.mesa_referencia,
                   p.nota, p.motivo_rechazo, p.creado_en, p.aceptado_en, p.preparacion_en,
                   p.listo_en, p.entregado_en,
                   r.total, r.pagado, r.cobrado,
                   c.cliente_id, c.nombre AS cliente_nombre, c.telefono AS cliente_telefono,
                   c.correo AS cliente_correo
            FROM pedido p
            JOIN v_pedido_resumen r ON r.pedido_id = p.pedido_id
            LEFT JOIN cliente c ON c.cliente_id = p.cliente_id
            WHERE p.pedido_id = %s
            """,
            (pedido_id,)
        )

    def obtener_lineas_detalle(self, pedido_id):
        """Obtiene las líneas de detalle con información del plato."""
        return consultar_todos(
            """
            SELECT d.detalle_id, d.plato_id, d.cantidad, d.precio_venta, d.nota,
                   pl.nombre AS plato_nombre, pl.codigo AS plato_codigo, pl.disponible
            FROM detalle_pedido d
            JOIN plato pl ON pl.plato_id = d.plato_id
            WHERE d.pedido_id = %s
            ORDER BY d.detalle_id
            """,
            (pedido_id,)
        )

    def obtener_pagos(self, pedido_id):
        """Obtiene los pagos asociados a un pedido."""
        return consultar_todos(
            "SELECT monto, medio, referencia, confirmado_en FROM pago WHERE pedido_id = %s ORDER BY pago_id",
            (pedido_id,)
        )

    def listar_cola(self):
        """Lista los pedidos de la cola del staff (pendientes, cobro, cocina, listos, entregados de hoy)."""
        return consultar_todos(
            """
            SELECT p.pedido_id, p.token, p.tipo, p.canal, p.estado, p.mesa_referencia, p.nota,
                   p.creado_en, p.preparacion_en,
                   r.total, r.pagado, r.cobrado,
                   c.nombre AS cliente_nombre, c.telefono AS cliente_telefono,
                   c.correo AS cliente_correo, c.cliente_id,
                   (CASE WHEN p.cliente_id IS NOT NULL THEN (
                         SELECT coalesce(a.pedidos_24h + a.reservas_24h, 0)
                         FROM v_cliente_actividad_24h a WHERE a.cliente_id = p.cliente_id
                     ) ELSE 0 END) > 0 AS actividad_24h
            FROM pedido p
            JOIN v_pedido_resumen r ON r.pedido_id = p.pedido_id
            LEFT JOIN cliente c ON c.cliente_id = p.cliente_id
            WHERE (p.estado IN ('pendiente','aceptado','en_preparacion','listo'))
               OR (p.estado = 'entregado' AND p.creado_en::date = CURRENT_DATE)
            ORDER BY p.creado_en, p.pedido_id
            """
        )

    def listar_cocina(self):
        """Lista los pedidos en preparación con agregación JSON de sus líneas."""
        return consultar_todos(
            """
            SELECT p.pedido_id, p.token, p.tipo, p.estado, p.mesa_referencia, p.nota,
                   p.preparacion_en,
                   r.total, r.cobrado,
                   c.nombre AS cliente_nombre,
                   json_agg(json_build_object(
                         'nombre', pl.nombre,
                         'cantidad', d.cantidad,
                         'nota', d.nota
                   ) ORDER BY d.detalle_id) AS lineas
            FROM pedido p
            JOIN v_pedido_resumen r ON r.pedido_id = p.pedido_id
            LEFT JOIN cliente c ON c.cliente_id = p.cliente_id
            LEFT JOIN detalle_pedido d ON d.pedido_id = p.pedido_id
            LEFT JOIN plato pl ON pl.plato_id = d.plato_id
            WHERE p.estado = 'en_preparacion'
            GROUP BY p.pedido_id, r.total, r.cobrado, c.nombre
            ORDER BY p.preparacion_en, p.pedido_id
            """
        )

    def obtener_pedido_publico(self, token):
        """Obtiene la cabecera para el seguimiento público del cliente."""
        return consultar_uno(
            """
            SELECT p.pedido_id, p.token, p.tipo, p.estado, p.motivo_rechazo,
                   p.creado_en, p.aceptado_en, p.preparacion_en, p.listo_en, p.entregado_en,
                   r.total, r.pagado, r.cobrado
            FROM pedido p JOIN v_pedido_resumen r ON r.pedido_id = p.pedido_id
            WHERE p.token = %s
            """,
            (token,)
        )

    def obtener_lineas_publicas(self, pedido_id):
        """Obtiene las líneas de detalle para el seguimiento público."""
        return consultar_todos(
            """
            SELECT d.cantidad, d.precio_venta, d.nota, pl.nombre AS plato_nombre
            FROM detalle_pedido d JOIN plato pl ON pl.plato_id = d.plato_id
            WHERE d.pedido_id = %s ORDER BY d.detalle_id
            """,
            (pedido_id,)
        )
