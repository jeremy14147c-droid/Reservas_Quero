"""DAO para la entidad Cliente (tabla cliente y vista v_cliente_actividad_24h)."""
from app.db import consultar_uno, ejecutar_retornando


class ClienteDAO:
    """Acceso a datos de clientes."""

    def buscar_por_telefono(self, telefono):
        """Busca un cliente por su número de teléfono."""
        return consultar_uno(
            "SELECT cliente_id, nombre, telefono, correo, acepta_datos FROM cliente WHERE telefono = %s",
            (telefono,)
        )

    def insertar(self, nombre, telefono, correo=None):
        """Inserta un nuevo cliente y retorna su ficha completa."""
        return ejecutar_retornando(
            "INSERT INTO cliente (nombre, telefono, correo, acepta_datos) "
            "VALUES (%s, %s, %s, TRUE) RETURNING cliente_id, nombre, telefono, correo, acepta_datos",
            (nombre, telefono, correo)
        )

    def obtener_actividad_24h(self, cliente_id):
        """Obtiene la actividad del cliente en las últimas 24 horas desde la vista SQL."""
        if not cliente_id:
            return None
        return consultar_uno(
            "SELECT cliente_id, pedidos_24h, reservas_24h, reservas_web_24h "
            "FROM v_cliente_actividad_24h WHERE cliente_id = %s",
            (cliente_id,)
        )

    def contar_reservas_web_24h(self, cliente_id):
        """Devuelve el total de reservas pedidas por la web en las últimas 24 h."""
        fila = self.obtener_actividad_24h(cliente_id)
        return int(fila["reservas_web_24h"]) if fila and fila.get("reservas_web_24h") is not None else 0
