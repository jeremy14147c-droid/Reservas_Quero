"""Servicio de negocio para pedidos, cobros y cocina (TODA la lógica vive aquí).
Reglas de AGENTS.md sección 8:
- Tipos: 'local' (cliente presente, lo registra el staff) y 'recojo' (lo pide el cliente por la web; exige cliente).
- Estados: pendiente -> aceptado | rechazado | cancelado ; aceptado -> en_preparacion | cancelado ;
  en_preparacion -> listo | cancelado ; listo -> entregado. Las finales no cambian.
- TODAS las transiciones pasan por transicion_pedido() (única función; llena las marcas de tiempo).
- El detalle de un recojo solo se edita mientras está 'pendiente'; al aceptar el monto queda fijo.
- Pago: lo confirma SIEMPRE el staff mirando el Yape/Plin real. Nunca se paga de más.
- Un recojo aceptado pasa a cocina SOLO cuando queda cobrado. Un local del staff nace en_preparacion.
- precio_venta se copia del precio del plato; no se puede pedir un plato no disponible/inactivo.
- Los pedidos NO se limitan por aforo ni mesas.

Excepciones: ValueError con mensaje claro para el usuario.
"""
from datetime import datetime, timedelta

from app.dao.pedido_dao import PedidoDAO
from app.dao.carta_dao import CartaDAO
from app.dao.cliente_dao import ClienteDAO
from app.dao.config_dao import ConfigDAO
from app.utils import normalizar_telefono
from app.servicios import clientes as servicio_clientes

pedido_dao_default = PedidoDAO()
carta_dao_default = CartaDAO()
cliente_dao_default = ClienteDAO()
config_dao_default = ConfigDAO()

# Única fuente de verdad de los estados
TRANSICIONES_VALIDAS = {
    "pendiente": {"aceptado", "rechazado", "cancelado"},
    "aceptado": {"en_preparacion", "cancelado"},
    "en_preparacion": {"listo", "cancelado"},
    "listo": {"entregado"},
}

MEDIOS_PAGO = ("efectivo", "yape", "plin", "transferencia", "otro")
MAX_CANTIDAD = 99


# ---------------------------------------------------------------- configuración

def obtener_config(config_dao=None):
    """Config del local (fila única)."""
    config_dao = config_dao or config_dao_default
    return config_dao.obtener()


# ---------------------------------------------------------------- validaciones

def _validar_items(items, carta_dao=None):
    """Valida la lista de líneas del pedido con el precio copiado del plato."""
    carta_dao = carta_dao or carta_dao_default
    if not items or not isinstance(items, list):
        raise ValueError("Agrega al menos un plato al pedido.")

    lineas = []
    for item in items:
        try:
            plato_id = int(item.get("plato_id"))
        except (TypeError, ValueError):
            raise ValueError("Hay una línea del pedido con plato inválido.")
        try:
            cantidad = int(item.get("cantidad"))
        except (TypeError, ValueError):
            raise ValueError("La cantidad de cada plato debe ser un número.")
        if cantidad < 1 or cantidad > MAX_CANTIDAD:
            raise ValueError(f"La cantidad por plato va de 1 a {MAX_CANTIDAD}.")

        plato = carta_dao.buscar_plato_por_id(plato_id)
        if not plato or not plato["activo"]:
            raise ValueError("Uno de los platos ya no existe en la carta. Actualiza la página.")
        if not plato["disponible"]:
            raise ValueError(f"El plato '{plato['nombre']}' está agotado. Quítalo del pedido.")

        nota = (item.get("nota") or "").strip() or None
        if nota and len(nota) > 200:
            raise ValueError("La nota de un plato es demasiado larga (máximo 200 caracteres).")

        lineas.append({
            "plato_id": plato_id,
            "nombre": plato["nombre"],
            "cantidad": cantidad,
            "nota": nota,
            "precio_venta": float(plato["precio"]),
        })

    combinadas = {}
    for linea in lineas:
        base = combinadas.get(linea["plato_id"])
        if base is None:
            combinadas[linea["plato_id"]] = dict(linea)
        else:
            base["cantidad"] += linea["cantidad"]
            notas = [nota for nota in (base["nota"], linea["nota"]) if nota]
            base["nota"] = "; ".join(notas) if notas else None
    return list(combinadas.values())


# ---------------------------------------------------------------- creación

def crear_pedido_recojo_web(datos, dao=None, cliente_dao=None, carta_dao=None):
    """Pedido de recojo pedido por la web: nace 'pendiente'."""
    dao = dao or pedido_dao_default
    cliente_dao = cliente_dao or cliente_dao_default
    carta_dao = carta_dao or carta_dao_default

    nombre = (datos.get("nombre") or "").strip()
    if not nombre:
        raise ValueError("Tu nombre es obligatorio.")
    if len(nombre) > 100:
        raise ValueError("Tu nombre es demasiado largo (máximo 100 caracteres).")

    telefono = normalizar_telefono(datos.get("telefono"))
    if not telefono:
        raise ValueError("El teléfono debe ser un número de 9 dígitos que empiece en 9 (celular de Perú).")

    if not datos.get("acepta_datos"):
        raise ValueError("Se necesita tu consentimiento para tratar tus datos.")

    correo = (datos.get("correo") or "").strip() or None
    if correo and ("@" not in correo or len(correo) > 120):
        raise ValueError("El correo es opcional, pero si lo escribe debe ser válido.")

    nota = (datos.get("nota") or "").strip() or None
    if nota and len(nota) > 300:
        raise ValueError("La nota es demasiado larga (máximo 300 caracteres).")

    lineas = _validar_items(datos.get("items"), carta_dao=carta_dao)
    cliente = servicio_clientes.obtener_o_crear_cliente(nombre, telefono, correo, dao=cliente_dao)

    fila_pedido = dao.insertar_recojo(cliente["cliente_id"], nota)
    dao.insertar_lineas(fila_pedido["pedido_id"], lineas)
    return fila_pedido


def crear_pedido_local_staff(datos, personal_id, dao=None, cliente_dao=None, carta_dao=None):
    """Pedido en local creado por el staff: nace 'en_preparacion'."""
    dao = dao or pedido_dao_default
    cliente_dao = cliente_dao or cliente_dao_default
    carta_dao = carta_dao or carta_dao_default

    cliente_id = None
    telefono = normalizar_telefono(datos.get("telefono"))
    nombre = (datos.get("nombre") or "").strip()
    if telefono or nombre:
        if not telefono:
            raise ValueError("Si registras un cliente, su teléfono de 9 dígitos (que empiece en 9) es obligatorio.")
        cliente = servicio_clientes.obtener_o_crear_cliente(
            nombre or "Cliente del local", telefono, datos.get("correo") or None, dao=cliente_dao
        )
        cliente_id = cliente["cliente_id"]

    mesa = (datos.get("mesa_referencia") or "").strip() or None
    if mesa and len(mesa) > 20:
        raise ValueError("La referencia de mesa es demasiado larga (máximo 20 caracteres).")

    nota = (datos.get("nota") or "").strip() or None
    if nota and len(nota) > 300:
        raise ValueError("La nota es demasiado larga (máximo 300 caracteres).")

    lineas = _validar_items(datos.get("items"), carta_dao=carta_dao)
    fila_pedido = dao.insertar_local(cliente_id, mesa, nota, personal_id)
    dao.insertar_lineas(fila_pedido["pedido_id"], lineas)
    return fila_pedido


# ---------------------------------------------------------------- transiciones

def transicion_pedido(pedido_id, nuevo_estado, motivo_rechazo=None, dao=None):
    """ÚNICA función que cambia el estado de un pedido."""
    dao = dao or pedido_dao_default
    resumen = dao.obtener_resumen(pedido_id)
    if not resumen:
        raise ValueError("El pedido no existe.")

    estado_actual = resumen["estado"]
    if estado_actual in ("entregado", "rechazado", "cancelado"):
        raise ValueError(f"El pedido ya está en el estado final '{estado_actual}'; no se puede cambiar.")
    if estado_actual not in TRANSICIONES_VALIDAS:
        raise ValueError(f"No se reconoce el estado actual '{estado_actual}'.")
    if nuevo_estado not in TRANSICIONES_VALIDAS[estado_actual]:
        raise ValueError(f"No se puede pasar de '{estado_actual}' a '{nuevo_estado}'.")

    motivo = (motivo_rechazo or "").strip() or None
    if nuevo_estado == "rechazado" and not motivo:
        raise ValueError("Para rechazar el pedido debes indicar el motivo.")
    if motivo and len(motivo) > 200:
        raise ValueError("El motivo es demasiado largo (máximo 200 caracteres).")

    # Regla especial: de aceptado a cocina solo si el dinero ya entró
    if estado_actual == "aceptado" and nuevo_estado == "en_preparacion" and not resumen.get("cobrado"):
        raise ValueError(
            "El pedido pasa a cocina solo cuando queda cobrado. Registra el pago (monto real "
            "visto en Yape/Plin o efectivo) primero."
        )

    marcas = {
        "aceptado": "aceptado_en = now()",
        "en_preparacion": "preparacion_en = now()",
        "listo": "listo_en = now()",
        "entregado": "entregado_en = now()",
    }
    sql_marca = marcas.get(nuevo_estado, "")
    asignado = f"{sql_marca}, " if sql_marca else ""

    return dao.actualizar_estado(pedido_id, nuevo_estado, asignado_tiempo_sql=asignado, motivo_rechazo=motivo)


def aceptar_pedido(pedido_id, dao=None):
    return transicion_pedido(pedido_id, "aceptado", dao=dao)


def rechazar_pedido(pedido_id, motivo, dao=None):
    return transicion_pedido(pedido_id, "rechazado", motivo_rechazo=motivo, dao=dao)


def cancelar_pedido(pedido_id, motivo=None, dao=None):
    return transicion_pedido(pedido_id, "cancelado", motivo_rechazo=motivo, dao=dao)


def pasar_a_preparacion(pedido_id, dao=None):
    return transicion_pedido(pedido_id, "en_preparacion", dao=dao)


def marcar_listo(pedido_id, dao=None):
    return transicion_pedido(pedido_id, "listo", dao=dao)


def marcar_entregado(pedido_id, dao=None):
    return transicion_pedido(pedido_id, "entregado", dao=dao)


# ---------------------------------------------------------------- edición de líneas

def actualizar_lineas(pedido_id, items, dao=None, carta_dao=None):
    """Ajusta las líneas de un pedido RECOJO pendiente."""
    dao = dao or pedido_dao_default
    carta_dao = carta_dao or carta_dao_default

    pedido = dao.buscar_por_id(pedido_id)
    if not pedido:
        raise ValueError("El pedido no existe.")
    if pedido["estado"] != "pendiente":
        raise ValueError("Solo se puede editar el detalle mientras el pedido está pendiente. "
                         "Al aceptarlo el monto queda fijo.")

    lineas = _validar_items(items, carta_dao=carta_dao)
    dao.limpiar_lineas(pedido_id)
    dao.insertar_lineas(pedido_id, lineas)
    return obtener_pedido_detalle(pedido_id, dao=dao)


# ---------------------------------------------------------------- pagos

def registrar_pago(pedido_id, medio, monto, referencia=None, personal_id=None, dao=None):
    """Registra un pago REAL confirmado por el staff."""
    dao = dao or pedido_dao_default
    monto_val = _a_monto(monto)
    resumen = dao.obtener_resumen(pedido_id)
    if not resumen:
        raise ValueError("El pedido no existe.")

    if resumen["estado"] not in ("aceptado", "en_preparacion", "listo"):
        raise ValueError(
            "No se puede registrar el pago en este estado: revisa primero el pedido "
            "(los pendientes se aceptan o rechazan antes de cobrar)."
        )

    if medio not in MEDIOS_PAGO:
        raise ValueError("El medio de pago no es válido.")

    saldo = float(resumen["total"]) - float(resumen["pagado"])
    if monto_val > saldo + 0.001:
        raise ValueError(
            f"No se puede pagar de más. El saldo por cobrar es S/ {saldo:.2f} "
            f"(total S/ {float(resumen['total']):.2f}, ya pagado S/ {float(resumen['pagado']):.2f})."
        )

    referencia_txt = (str(referencia) if referencia is not None else "").strip() or None
    if referencia_txt and len(referencia_txt) > 60:
        raise ValueError("La referencia de pago es demasiado larga (máximo 60 caracteres).")

    dao.registrar_pago(pedido_id, monto_val, medio, referencia_txt, personal_id)

    # Dinero ya completo y seguía esperando el cobro: entra directo a cocina
    if float(resumen["pagado"]) + monto_val >= float(resumen["total"]) - 0.001 \
            and resumen["estado"] == "aceptado":
        transicion_pedido(pedido_id, "en_preparacion", dao=dao)

    return dao.obtener_resumen(pedido_id)


def _a_monto(valor):
    """Convierte el monto texto/número a float válido (> 0)."""
    try:
        monto_val = round(float(str(valor).replace(",", ".").strip()), 2)
    except (TypeError, ValueError):
        raise ValueError("El monto del pago debe ser un número.")
    if monto_val <= 0:
        raise ValueError("El monto del pago debe ser mayor a 0.")
    return monto_val


# ---------------------------------------------------------------- consultas

def obtener_resumen(pedido_id, dao=None):
    """Fila de v_pedido_resumen (total, pagado, cobrado) + datos del pedido."""
    dao = dao or pedido_dao_default
    return dao.obtener_resumen(pedido_id)


def obtener_pedido_detalle(pedido_id, dao=None, cliente_dao=None):
    """Detalle completo para el panel del staff: pedido + líneas + cliente."""
    dao = dao or pedido_dao_default
    cliente_dao = cliente_dao or cliente_dao_default

    detalle = dao.obtener_pedido_detalle(pedido_id)
    if not detalle:
        return None

    detalle["lineas"] = dao.obtener_lineas_detalle(pedido_id)
    detalle["pagos"] = dao.obtener_pagos(pedido_id)

    if detalle.get("cliente_id"):
        actividad = servicio_clientes.actividad_24h(detalle["cliente_id"], dao=cliente_dao)
        detalle["actividad_24h"] = bool(
            actividad and (actividad["pedidos_24h"] + actividad["reservas_24h"]) > 0
        )
    else:
        detalle["actividad_24h"] = False
    return detalle


def obtener_cola(dao=None):
    """Datos de la cola del staff (4 columnas): pendientes, por cobrar, en cocina, listos."""
    dao = dao or pedido_dao_default
    filas = dao.listar_cola()

    cola = {"pendientes": [], "por_cobrar": [], "en_cocina": [], "listos": [], "entregados": []}
    for fila in filas:
        fila = dict(fila)
        fila["es_recojo"] = fila["tipo"] == "recojo"
        if fila["estado"] == "pendiente":
            cola["pendientes"].append(fila)
        elif fila["estado"] == "aceptado" and not fila["cobrado"]:
            cola["por_cobrar"].append(fila)
        elif fila["estado"] == "en_preparacion":
            cola["en_cocina"].append(fila)
        elif fila["estado"] == "listo":
            cola["listos"].append(fila)
        elif fila["estado"] == "entregado":
            cola["entregados"].append(fila)
        elif fila["estado"] == "aceptado":
            cola["por_cobrar"].append(fila)
    return cola


def obtener_cocina(dao=None, config_dao=None):
    """Tablero de cocina: pedidos en preparación con minutos transcurridos."""
    dao = dao or pedido_dao_default
    config_dao = config_dao or config_dao_default

    config = obtener_config(config_dao)
    from app.utils import ahora_local
    ahora = ahora_local()

    filas = dao.listar_cocina()

    cocina = []
    for fila in filas:
        fila = dict(fila)
        inicio = fila["preparacion_en"]
        minutos = 0
        if inicio is not None:
            minutos = int((ahora - inicio).total_seconds() // 60)
        fila["minutos"] = minutos
        fila["atrasado"] = inicio is not None and minutos >= config["umbral_preparacion_min"]
        cocina.append(fila)
    return cocina


def obtener_pedido_publico(token, dao=None, config_dao=None):
    """Datos del pedido para la página del cliente."""
    dao = dao or pedido_dao_default
    config_dao = config_dao or config_dao_default

    pedido = dao.obtener_pedido_publico(token)
    if not pedido:
        return None

    pedido["lineas"] = dao.obtener_lineas_publicas(pedido["pedido_id"])
    if pedido["estado"] == "aceptado" and not pedido["cobrado"]:
        config = obtener_config(config_dao)
        pedido["instrucciones_pago"] = {
            "yape_numero": config["yape_numero"],
            "yape_titular": config["yape_titular"],
            "mensaje_pago": config["mensaje_pago"],
            "total": float(pedido["total"]),
        }
    else:
        pedido["instrucciones_pago"] = None
    return pedido
