"""Servicio de negocio para los clientes (fichas identificadas por teléfono).
Reglas de AGENTS.md sección 7:
- El teléfono es la llave del cliente (9 dígitos que empiezan en 9, obligatorio).
- Si el teléfono ya existe se REUTILIZA la ficha y NO se sobrescriben nombre ni correo.
- El correo es opcional y NO es único (nunca se fusionan fichas por correo).
- Sin cuenta, sin contraseña, sin login de cliente.
"""
from app.db import consultar_todos, consultar_uno, ejecutar_retornando
from app.utils import normalizar_telefono


def obtener_o_crear_cliente(nombre, telefono, correo=None):
    """Devuelve la ficha del cliente con ese teléfono; si no existe, la crea.
    El nombre y el correo solo se guardan cuando el cliente es nuevo: si ya existía
    una ficha con ese teléfono, se conserva su información inicial.
    """
    tel = normalizar_telefono(telefono)
    if not tel:
        raise ValueError("El teléfono debe ser un número de 9 dígitos que empiece en 9 (celular de Perú).")

    existente = consultar_uno(
        "SELECT cliente_id, nombre, telefono, correo, acepta_datos FROM cliente WHERE telefono = %s",
        (tel,)
    )
    if existente:
        return existente

    nombre_limpio = (nombre or "").strip()
    if not nombre_limpio:
        raise ValueError("El nombre del cliente es obligatorio.")

    correo_limpio = (correo or "").strip() or None
    if correo_limpio and "@" not in correo_limpio:
        raise ValueError("El correo es opcional, pero si se escribe debe ser válido.")

    try:
        return ejecutar_retornando(
            "INSERT INTO cliente (nombre, telefono, correo, acepta_datos) "
            "VALUES (%s, %s, %s, TRUE) RETURNING cliente_id, nombre, telefono, correo, acepta_datos",
            (nombre_limpio, tel, correo_limpio)
        )
    except Exception as e:
        # pgcode 23505 = violación de unicidad (dos personas asignando el teléfono a la vez)
        if getattr(e, "pgcode", None) == "23505":
            raise ValueError("El cliente con ese teléfono ya existe. Intenta nuevamente.")
        raise


def actividad_24h(cliente_id):
    """Devuelve la fila de la vista v_cliente_actividad_24h para un cliente.
    pedidos_24h + reservas_24h se usan para la insignia de aviso al staff.
    """
    if not cliente_id:
        return None
    return consultar_uno(
        "SELECT cliente_id, pedidos_24h, reservas_24h, reservas_web_24h "
        "FROM v_cliente_actividad_24h WHERE cliente_id = %s",
        (cliente_id,)
    )


def reservas_web_24h(cliente_id):
    """Cuántas reservas pedidas por la web tiene activas este cliente en las últimas 24 h.
    Se compara con config_local.max_reservas_web_por_telefono (solo para solicitudes de la web).
    """
    fila = actividad_24h(cliente_id)
    if not fila:
        return 0
    return fila["reservas_web_24h"]


def tiene_actividad_reciente(cliente_id):
    """Insignia para el staff: si el cliente pidió o reservó algo (no rechazado/cancelado) en 24 h."""
    fila = actividad_24h(cliente_id)
    if not fila:
        return False
    return (fila["pedidos_24h"] + fila["reservas_24h"]) > 0
