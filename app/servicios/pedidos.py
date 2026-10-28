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

Excepciones: ValueError con mensaje claro para el usuario (las rutas lo traducen a JSON/flash).
"""
from datetime import datetime, timedelta

from app.db import consultar_todos, consultar_uno, ejecutar, ejecutar_retornando
from app.utils import normalizar_telefono
from app.servicios import clientes as servicio_clientes

# Única fuente de verdad de los estados
TRANSICIONES_VALIDAS = {
    "pendiente": {"aceptado", "rechazado", "cancelado"},
    "aceptado": {"en_preparacion", "cancelado"},
    "en_preparacion": {"listo", "cancelado"},
    "listo": {"entregado"},
}

MEDIOS_PAGO = ("efectivo", "yape", "plin", "transferencia", "otro")

MAX_CANTIDAD = 99   # tope por línea: nadie pide 100 de lo mismo en un MVP


# ---------------------------------------------------------------- configuración

def obtener_config():
    """Config del local (fila única). Reutiliza el servicio de reservas."""
    from app.servicios.reservas import obtener_config as config_reservas
    return config_reservas()


# ---------------------------------------------------------------- validaciones

def _validar_items(items):
    """Valida la lista de líneas del pedido. Devuelve [{plato_id, cantidad, nota, precio_venta,...}]
    con el precio copiado del plato (precio_venta NO es editable por el cliente).
    - Cada plato debe existir, estar activo y disponible.
    - Cantidad entre 1 y MAX_CANTIDAD; nota de línea hasta 200 caracteres.
    """
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

        plato = consultar_uno(
            "SELECT plato_id, nombre, precio, disponible, activo FROM plato WHERE plato_id = %s",
            (plato_id,)
        )
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
            "precio_venta": float(plato["precio"]),   # se copia del plato, nunca se edita
        })

    # Si el mismo plato aparece varias veces, se suman las cantidades
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


def _insertar_lineas(pedido_id, lineas):
    """Guarda las líneas del pedido (detalle_pedido) con el precio copiado."""
    for linea in lineas:
        ejecutar(
            "INSERT INTO detalle_pedido (pedido_id, plato_id, cantidad, precio_venta, nota) "
            "VALUES (%s, %s, %s, %s, %s)",
            (pedido_id, linea["plato_id"], linea["cantidad"], linea["precio_venta"], linea["nota"])
        )


# ---------------------------------------------------------------- creación

def crear_pedido_recojo_web(datos):
    """Pedido de recojo pedido por la web: nace 'pendiente' (el staff decide si lo acepta).
    Exige cliente (nombre + teléfono 9... + consentimiento). Solo platos disponibles.
    No hay tope por actividad para pedidos: si el cliente repite, es solo un AVISO al staff
    (la insignia 'ya pidió hace menos de 24 h' se calcula en la cola).
    """
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

    lineas = _validar_items(datos.get("items"))

    # La llave del cliente es el teléfono: se reutiliza la ficha sin sobrescribir nada
    cliente = servicio_clientes.obtener_o_crear_cliente(nombre, telefono, correo)

    fila_pedido = ejecutar_retornando(
        "INSERT INTO pedido (cliente_id, tipo, canal, estado, nota) "
        "VALUES (%s, 'recojo', 'web', 'pendiente', %s) "
        "RETURNING pedido_id, token, tipo, canal, estado",
        (cliente["cliente_id"], nota)
    )
    _insertar_lineas(fila_pedido["pedido_id"], lineas)
    return fila_pedido


def crear_pedido_local_staff(datos, personal_id):
    """Pedido en local creado por el staff: nace 'en_preparacion' (entra luego a cocina de una vez).
    Cliente opcional (take-away de alguien conocido o cliente de mesa anónimo).
    'mesa_referencia' es texto libre (mezcla, mesa 3, barra...).
    """
    cliente_id = None
    telefono = normalizar_telefono(datos.get("telefono"))
    nombre = (datos.get("nombre") or "").strip()
    if telefono or nombre:
        if not telefono:
            raise ValueError("Si registras un cliente, su teléfono de 9 dígitos (que empiece en 9) es obligatorio.")
        cliente = servicio_clientes.obtener_o_crear_cliente(nombre or "Cliente del local", telefono,
                                                            datos.get("correo") or None)
        cliente_id = cliente["cliente_id"]

    mesa = (datos.get("mesa_referencia") or "").strip() or None
    if mesa and len(mesa) > 20:
        raise ValueError("La referencia de mesa es demasiado larga (máximo 20 caracteres).")

    nota = (datos.get("nota") or "").strip() or None
    if nota and len(nota) > 300:
        raise ValueError("La nota es demasiado larga (máximo 300 caracteres).")

    lineas = _validar_items(datos.get("items"))

    fila_pedido = ejecutar_retornando(
        "INSERT INTO pedido (cliente_id, tipo, canal, estado, mesa_referencia, nota, creado_por, "
        "preparacion_en) "
        "VALUES (%s, 'local', 'staff', 'en_preparacion', %s, %s, %s, now()) "
        "RETURNING pedido_id, token, tipo, canal, estado",
        (cliente_id, mesa, nota, personal_id)
    )
    _insertar_lineas(fila_pedido["pedido_id"], lineas)
    return fila_pedido


# ---------------------------------------------------------------- transiciones

def transicion_pedido(pedido_id, nuevo_estado, motivo_rechazo=None):
    """ÚNICA función que cambia el estado de un pedido. Rechaza las transiciones inválidas
    y llena aceptado_en, preparacion_en, listo_en y entregado_en según el destino.
    Un recojo 'aceptado' SOLO pasa a cocina si ya está cobrado.
    """
    resumen = obtener_resumen(pedido_id)
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
    if estado_actual == "aceptado" and nuevo_estado == "en_preparacion" and not resumen["cobrado"]:
        raise ValueError(
            "El pedido pasa a cocina solo cuando queda cobrado. Registra el pago (monta real "
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

    fila = ejecutar_retornando(
        f"""UPDATE pedido
            SET estado = %s, {asignado}motivo_rechazo = COALESCE(%s, motivo_rechazo)
            WHERE pedido_id = %s
            RETURNING pedido_id, token, tipo, canal, estado""",
        (nuevo_estado, motivo, pedido_id)
    )
    return fila


# ---------------------------------------------------------------- edición de líneas

def actualizar_lineas(pedido_id, items):
    """Ajusta (agrega, quita o cambia cantidades de) las líneas de un pedido RECOJO pendiente.
    Al aceptar el pedido el monto queda fijo y esto ya no se puede usar.
    """
    pedido = consultar_uno("SELECT pedido_id, estado FROM pedido WHERE pedido_id = %s", (pedido_id,))
    if not pedido:
        raise ValueError("El pedido no existe.")
    if pedido["estado"] != "pendiente":
        raise ValueError("Solo se puede editar el detalle mientras el pedido está pendiente. "
                         "Al aceptarlo el monto queda fijo.")

    lineas = _validar_items(items)
    ejecutar("DELETE FROM detalle_pedido WHERE pedido_id = %s", (pedido_id,))
    _insertar_lineas(pedido_id, lineas)
    return obtener_pedido_detalle(pedido_id)


# ---------------------------------------------------------------- pagos

def registrar_pago(pedido_id, medio, monto, referencia=None, personal_id=None):
    """Registra un pago REAL confirmado por el staff (mirando el Yape/Plin o cobrando efectivo).
    - Nunca se paga de más: monto + lo ya pagado no puede superar el total.
    - Solo en estados donde el cobro tiene sentido (nunca en pendientes de revisión ni finales).
    - Si con este pago el pedido queda cobrado y estaba 'aceptado', pasa SOLO a 'en_preparacion'.
    """
    monto_val = _a_monto(monto)
    resumen = obtener_resumen(pedido_id)
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
    if monto_val > saldo + 0.001:   # tolerancia de centavos por redondeo
        raise ValueError(
            f"No se puede pagar de más. El saldo por cobrar es S/ {saldo:.2f} "
            f"(total S/ {float(resumen['total']):.2f}, ya pagado S/ {float(resumen['pagado']):.2f})."
        )

    referencia_txt = (str(referencia) if referencia is not None else "").strip() or None
    if referencia_txt and len(referencia_txt) > 60:
        raise ValueError("La referencia de pago es demasiado larga (máximo 60 caracteres).")

    ejecutar(
        "INSERT INTO pago (pedido_id, monto, medio, referencia, confirmado_por) "
        "VALUES (%s, %s, %s, %s, %s)",
        (pedido_id, monto_val, medio, referencia_txt, personal_id)
    )

    # Dinero ya completo y seguía esperando el cobro: entra directo a cocina
    if float(resumen["pagado"]) + monto_val >= float(resumen["total"]) - 0.001 \
            and resumen["estado"] == "aceptado":
        transicion_pedido(pedido_id, "en_preparacion")

    return obtener_resumen(pedido_id)


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

def obtener_resumen(pedido_id):
    """Fila de v_pedido_resumen (total, pagado, cobrado) + datos del pedido (lo calculado NO se guarda)."""
    return consultar_uno(
        """SELECT p.pedido_id, p.token, p.tipo, p.canal, p.estado, p.mesa_referencia,
                  p.nota, p.motivo_rechazo, p.creado_por,
                  p.creado_en, p.aceptado_en, p.preparacion_en, p.listo_en, p.entregado_en,
                  r.total, r.pagado, r.cobrado
           FROM pedido p JOIN v_pedido_resumen r ON r.pedido_id = p.pedido_id
           WHERE p.pedido_id = %s""",
        (pedido_id,)
    )


def obtener_pedido_detalle(pedido_id):
    """Detalle completo para el panel del staff: pedido + líneas + cliente (sin datos de más)."""
    detalle = consultar_uno(
        """SELECT p.pedido_id, p.token, p.tipo, p.canal, p.estado, p.mesa_referencia,
                  p.nota, p.motivo_rechazo, p.creado_en, p.aceptado_en, p.preparacion_en,
                  p.listo_en, p.entregado_en,
                  r.total, r.pagado, r.cobrado,
                  c.cliente_id, c.nombre AS cliente_nombre, c.telefono AS cliente_telefono,
                  c.correo AS cliente_correo
           FROM pedido p
           JOIN v_pedido_resumen r ON r.pedido_id = p.pedido_id
           LEFT JOIN cliente c ON c.cliente_id = p.cliente_id
           WHERE p.pedido_id = %s""",
        (pedido_id,)
    )
    if not detalle:
        return None

    detalle["lineas"] = consultar_todos(
        """SELECT d.detalle_id, d.plato_id, d.cantidad, d.precio_venta, d.nota,
                  pl.nombre AS plato_nombre, pl.codigo AS plato_codigo, pl.disponible
           FROM detalle_pedido d
           JOIN plato pl ON pl.plato_id = d.plato_id
           WHERE d.pedido_id = %s
           ORDER BY d.detalle_id""",
        (pedido_id,)
    )
    detalle["pagos"] = consultar_todos(
        """SELECT monto, medio, referencia, confirmado_en
           FROM pago WHERE pedido_id = %s ORDER BY pago_id""",
        (pedido_id,)
    )
    # Insignia de actividad reciente (solo aviso al staff)
    if detalle["cliente_id"]:
        actividad = servicio_clientes.actividad_24h(detalle["cliente_id"])
        detalle["actividad_24h"] = bool(
            actividad and (actividad["pedidos_24h"] + actividad["reservas_24h"]) > 0
        )
    else:
        detalle["actividad_24h"] = False
    return detalle


def obtener_cola():
    """Datos de la cola del staff (4 columnas): pendientes, por cobrar, en cocina, listos.
    También incluye entregados del día para que el staff los vea unos momentos.
    """
    filas = consultar_todos(
        """SELECT p.pedido_id, p.token, p.tipo, p.canal, p.estado, p.mesa_referencia, p.nota,
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
           ORDER BY p.creado_en, p.pedido_id"""
    )

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
        # 'aceptado' ya cobrado tarda un instante en pasar a cocina: lo dejamos en por_cobrar
        elif fila["estado"] == "aceptado":
            cola["por_cobrar"].append(fila)
    return cola


def obtener_cocina():
    """Tablero de cocina: pedidos en preparación con minutos transcurridos desde preparacion_en.
    'atrasado' (rojo, solo visual) cuando supera umbral_preparacion_min de config_local.
    """
    config = obtener_config()
    # la BD guarda TIMESTAMPTZ: se usa la hora local CON zona para restar bien
    ahora = datetime.now().astimezone()

    filas = consultar_todos(
        """SELECT p.pedido_id, p.token, p.tipo, p.estado, p.mesa_referencia, p.nota,
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
           ORDER BY p.preparacion_en, p.pedido_id"""
    )

    cocina = []
    for fila in filas:
        fila = dict(fila)
        inicio = fila["preparacion_en"]
        minutos = 0
        if inicio is not None:
            minutos = int((ahora - inicio).total_seconds() // 60)
        fila["minutos"] = minutos
        # 'preparacion_en' llega con zona horaria; se compara contra el umbral directo
        fila["atrasado"] = inicio is not None and minutos >= config["umbral_preparacion_min"]
        cocina.append(fila)
    return cocina


def obtener_pedido_publico(token):
    """Datos del pedido para la página del cliente (nunca va nada interno del local)."""
    pedido = consultar_uno(
        """SELECT p.pedido_id, p.token, p.tipo, p.estado, p.motivo_rechazo,
                  p.creado_en, p.aceptado_en, p.preparacion_en, p.listo_en, p.entregado_en,
                  r.total, r.pagado, r.cobrado
           FROM pedido p JOIN v_pedido_resumen r ON r.pedido_id = p.pedido_id
           WHERE p.token = %s""",
        (token,)
    )
    if not pedido:
        return None

    pedido["lineas"] = consultar_todos(
        """SELECT d.cantidad, d.precio_venta, d.nota, pl.nombre AS plato_nombre
           FROM detalle_pedido d JOIN plato pl ON pl.plato_id = d.plato_id
           WHERE d.pedido_id = %s ORDER BY d.detalle_id""",
        (pedido["pedido_id"],)
    )
    if pedido["estado"] == "aceptado" and not pedido["cobrado"]:
        # Instrucciones de pago con los datos Yape de config_local
        config = obtener_config()
        pedido["instrucciones_pago"] = {
            "yape_numero": config["yape_numero"],
            "yape_titular": config["yape_titular"],
            "mensaje_pago": config["mensaje_pago"],
            "total": float(pedido["total"]),
        }
    else:
        pedido["instrucciones_pago"] = None
    return pedido
