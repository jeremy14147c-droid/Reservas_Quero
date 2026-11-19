"""Servicio de negocio para los clientes (fichas identificadas por teléfono).
Reglas de AGENTS.md sección 7:
- El teléfono es la llave del cliente (9 dígitos que empiezan en 9, obligatorio).
- Si el teléfono ya existe se REUTILIZA la ficha y NO se sobrescriben nombre ni correo.
- El correo es opcional y NO es único (nunca se fusionan fichas por correo).
- Sin cuenta, sin contraseña, sin login de cliente.
"""
from app.dao.cliente_dao import ClienteDAO
from app.utils import normalizar_telefono

# Instancia por defecto del DAO
cliente_dao_default = ClienteDAO()


def obtener_o_crear_cliente(nombre, telefono, correo=None, dao=None):
    """Devuelve la ficha del cliente con ese teléfono; si no existe, la crea.
    El nombre y el correo solo se guardan cuando el cliente es nuevo: si ya existía
    una ficha con ese teléfono, se conserva su información inicial.
    """
    dao = dao or cliente_dao_default
    tel = normalizar_telefono(telefono)
    if not tel:
        raise ValueError("El teléfono debe ser un número de 9 dígitos que empiece en 9 (celular de Perú).")

    existente = dao.buscar_por_telefono(tel)
    if existente:
        return existente

    nombre_limpio = (nombre or "").strip()
    if not nombre_limpio:
        raise ValueError("El nombre del cliente es obligatorio.")

    correo_limpio = (correo or "").strip() or None
    if correo_limpio and "@" not in correo_limpio:
        raise ValueError("El correo es opcional, pero si se escribe debe ser válido.")

    try:
        return dao.insertar(nombre_limpio, tel, correo_limpio)
    except Exception as e:
        # pgcode 23505 = violación de unicidad (dos personas asignando el teléfono a la vez)
        if getattr(e, "pgcode", None) == "23505":
            raise ValueError("El cliente con ese teléfono ya existe. Intenta nuevamente.")
        raise


def actividad_24h(cliente_id, dao=None):
    """Devuelve la fila de la vista v_cliente_actividad_24h para un cliente.
    pedidos_24h + reservas_24h se usan para la insignia de aviso al staff.
    """
    dao = dao or cliente_dao_default
    if not cliente_id:
        return None
    return dao.obtener_actividad_24h(cliente_id)


def reservas_web_24h(cliente_id, dao=None):
    """Devuelve el total de reservas pedidas por la web en las últimas 24 h por ese cliente.
    Se compara contra config_local.max_reservas_web_por_telefono.
    """
    dao = dao or cliente_dao_default
    return dao.contar_reservas_web_24h(cliente_id)
