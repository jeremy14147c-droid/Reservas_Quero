"""DAO para la entidad Reserva (tabla reserva y funciones SQL fn_hay_cupo, fn_carga_dia, fn_duracion_estadia)."""
from app.db import consultar_todos, consultar_uno, ejecutar_retornando, ejecutar_retornando_todos


class ReservaDAO:
    """Acceso a datos de reservas y funciones de cupo."""

    def existe_codigo(self, codigo):
        """Comprueba si un código de reserva (Q-XXXXXX) ya existe."""
        fila = consultar_uno("SELECT 1 FROM reserva WHERE codigo = %s", (codigo,))
        return fila is not None

    def existe_activa_cliente(self, cliente_id, fecha, hora):
        """Comprueba si el cliente ya tiene una reserva activa para esa fecha y hora."""
        return consultar_uno(
            """
            SELECT reserva_id, estado FROM reserva
            WHERE cliente_id = %s AND fecha = %s AND hora = %s
              AND estado IN ('pendiente','confirmada','llego')
            """,
            (cliente_id, fecha, hora)
        )

    def hay_cupo(self, fecha, hora, personas, excluir_reserva_id=None):
        """Llama a la función SQL fn_hay_cupo."""
        fila = consultar_uno(
            "SELECT fn_hay_cupo(%s, %s, %s, %s) AS hay_cupo",
            (fecha, hora, personas, excluir_reserva_id)
        )
        return bool(fila["hay_cupo"]) if fila else False

    def obtener_duracion_estadia(self, personas):
        """Llama a la función SQL fn_duracion_estadia."""
        fila = consultar_uno("SELECT fn_duracion_estadia(%s) AS duracion", (personas,))
        return int(fila["duracion"]) if fila else 30

    def consultar_carga_dia(self, fecha, excluir_reserva_id=None):
        """Llama a la función SQL fn_carga_dia para un día completo."""
        return consultar_todos(
            """
            SELECT franja_inicio, franja_fin, reservas, personas, mesas,
                   limite_personas, limite_mesas, personas_libres, mesas_libres, limita, nivel
            FROM fn_carga_dia(%s, %s)
            """,
            (fecha, excluir_reserva_id)
        )

    def insertar(self, datos):
        """Inserta una reserva y devuelve sus datos insertados."""
        return ejecutar_retornando(
            """
            INSERT INTO reserva (
                codigo, cliente_id, fecha, hora, cantidad_personas,
                nota, estado, excede_cupo
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING reserva_id, codigo, token, fecha, hora, cantidad_personas, estado, excede_cupo, creado_en
            """,
            (
                datos["codigo"],
                datos["cliente_id"],
                datos["fecha"],
                datos["hora"],
                datos["cantidad_personas"],
                datos.get("nota"),
                datos["estado"],
                datos.get("excede_cupo", False)
            )
        )

    def buscar_por_id(self, reserva_id):
        """Busca el registro básico de una reserva por ID."""
        return consultar_uno(
            """
            SELECT reserva_id, codigo, token, cliente_id, fecha, hora, hora_anterior,
                   cantidad_personas, nota, estado, motivo, excede_cupo, creado_en
            FROM reserva WHERE reserva_id = %s
            """,
            (reserva_id,)
        )

    def obtener_detalle(self, reserva_id):
        """Obtiene la reserva con datos del cliente y duración calculada."""
        return consultar_uno(
            """
            SELECT r.reserva_id, r.codigo, r.token, r.fecha, r.hora, r.hora_anterior,
                   r.cantidad_personas, r.estado, r.motivo, r.nota, r.excede_cupo,
                   r.creado_en, r.actualizado_en,
                   c.cliente_id, c.nombre AS cliente_nombre, c.telefono AS cliente_telefono,
                   c.correo AS cliente_correo,
                   fn_duracion_estadia(r.cantidad_personas) AS duracion_min
            FROM reserva r
            JOIN cliente c ON r.cliente_id = c.cliente_id
            WHERE r.reserva_id = %s
            """,
            (reserva_id,)
        )

    def buscar_por_codigo(self, codigo):
        """Busca una reserva por su código visible (Q-XXXXXX)."""
        return consultar_uno(
            """
            SELECT r.reserva_id, r.codigo, r.token, r.fecha, r.hora, r.hora_anterior,
                   r.cantidad_personas, r.estado, r.canal, r.motivo, r.nota, r.excede_cupo,
                   r.creado_en,
                   c.cliente_id, c.nombre AS cliente_nombre, c.telefono AS cliente_telefono,
                   c.correo AS cliente_correo,
                   fn_duracion_estadia(r.cantidad_personas) AS duracion_min,
                   (r.hora + make_interval(mins => fn_duracion_estadia(r.cantidad_personas)))::time AS hasta
            FROM reserva r
            JOIN cliente c ON r.cliente_id = c.cliente_id
            WHERE r.codigo = %s
            """,
            (codigo,)
        )

    def buscar_por_token(self, token):
        """Busca una reserva por su token UUID para consulta pública."""
        return consultar_uno(
            """
            SELECT r.reserva_id, r.codigo, r.token, r.fecha, r.hora, r.hora_anterior,
                   r.cantidad_personas, r.estado, r.motivo, r.nota, r.excede_cupo,
                   r.creado_en,
                   c.nombre AS cliente_nombre, c.telefono AS cliente_telefono,
                   c.correo AS cliente_correo,
                   fn_duracion_estadia(r.cantidad_personas) AS duracion_min
            FROM reserva r
            JOIN cliente c ON r.cliente_id = c.cliente_id
            WHERE r.token = %s
            """,
            (token,)
        )

    def listar_del_dia(self, fecha):
        """Lista las reservas de un día con datos del cliente y duración."""
        return consultar_todos(
            """
            SELECT r.reserva_id, r.codigo, r.token, r.fecha, r.hora, r.hora_anterior,
                   r.cantidad_personas, r.estado, r.canal, r.motivo, r.nota, r.excede_cupo,
                   r.creado_en,
                   c.cliente_id, c.nombre AS cliente_nombre, c.telefono AS cliente_telefono,
                   c.correo AS cliente_correo,
                   fn_duracion_estadia(r.cantidad_personas) AS duracion_min,
                   (r.hora + make_interval(mins => fn_duracion_estadia(r.cantidad_personas)))::time AS hasta
            FROM reserva r
            JOIN cliente c ON r.cliente_id = c.cliente_id
            WHERE r.fecha = %s
            ORDER BY r.hora, r.reserva_id
            """,
            (fecha,)
        )

    def actualizar_estado(self, reserva_id, nuevo_estado, motivo=None, excede_cupo=None):
        """Actualiza el estado de la reserva."""
        return ejecutar_retornando(
            """
            UPDATE reserva
            SET estado = %s,
                motivo = %s,
                excede_cupo = COALESCE(%s, excede_cupo),
                actualizado_en = now()
            WHERE reserva_id = %s
            RETURNING reserva_id, estado, motivo, excede_cupo
            """,
            (nuevo_estado, motivo, excede_cupo, reserva_id)
        )

    def actualizar_hora(self, reserva_id, nueva_hora, hora_anterior=None, excede_cupo=None):
        """Actualiza la hora de la reserva guardando la hora previa."""
        return ejecutar_retornando(
            """
            UPDATE reserva
            SET hora = %s,
                hora_anterior = %s,
                excede_cupo = COALESCE(%s, excede_cupo),
                actualizado_en = now()
            WHERE reserva_id = %s
            RETURNING reserva_id, hora, hora_anterior, excede_cupo
            """,
            (nueva_hora, hora_anterior, excede_cupo, reserva_id)
        )

    def liberar_pendientes_vencidas(self, ahora):
        """Cierra reservas pendientes cuya hora ya pasó a 'rechazada'."""
        filas = ejecutar_retornando_todos(
            """
            UPDATE reserva
            SET estado = 'rechazada',
                motivo = 'Vencida: nadie la atendió a tiempo',
                actualizado_en = %s
            WHERE estado = 'pendiente'
              AND (fecha < %s OR (fecha = %s AND hora <= %s))
            RETURNING reserva_id
            """,
            (ahora, ahora.date(), ahora.date(), ahora.time())
        )
        return len(filas)

    def liberar_confirmadas_vencidas(self, ahora):
        """Cierra reservas confirmadas cuya ocupación de mesa ya terminó a 'no_llego'."""
        filas = ejecutar_retornando_todos(
            """
            UPDATE reserva r
            SET estado = 'no_llego',
                motivo = 'Automático: no se registró la llegada',
                actualizado_en = %s
            WHERE r.estado = 'confirmada'
              AND ((r.fecha + r.hora) + make_interval(mins => fn_duracion_estadia(r.cantidad_personas))) <= %s
            RETURNING r.reserva_id
            """,
            (ahora, ahora)
        )
        return len(filas)
