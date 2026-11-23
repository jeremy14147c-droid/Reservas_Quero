"""Servicio para consultar y actualizar la configuración operativa del local (config_local)."""
from datetime import time
from app.dao.config_dao import ConfigDAO
from app.servicios.marca import validar_url_segura, validar_whatsapp

# Instancia por defecto del DAO
config_dao_default = ConfigDAO()


def obtener_config_local(dao=None):
    """Devuelve la fila de configuración del local (config_id = 1)."""
    dao = dao or config_dao_default
    return dao.obtener()


def actualizar_config_local(datos, dao=None):
    """Valida y actualiza los parámetros operativos del local en config_local.
    Lanza ValueError con mensaje claro si alguna validación falla.
    """
    dao = dao or config_dao_default
    nombre_local = (datos.get("nombre_local") or "").strip()
    if not nombre_local:
        raise ValueError("El nombre del local es obligatorio.")

    try:
        aforo = int(datos.get("aforo_personas", 0))
        if aforo <= 0:
            raise ValueError("El aforo debe ser mayor a 0 personas.")
    except (TypeError, ValueError):
        raise ValueError("El aforo de personas debe ser un número entero positivo.")

    try:
        total_mesas = int(datos.get("total_mesas", 0))
        if total_mesas <= 0:
            raise ValueError("El número total de mesas debe ser mayor a 0.")
    except (TypeError, ValueError):
        raise ValueError("El total de mesas debe ser un número entero positivo.")

    try:
        personas_por_mesa = int(datos.get("personas_por_mesa", 0))
        if personas_por_mesa <= 0:
            raise ValueError("Las personas por mesa deben ser mayor a 0.")
    except (TypeError, ValueError):
        raise ValueError("Personas por mesa debe ser un número entero positivo.")

    # Duración de estadía según el tamaño del grupo (3 valores, múltiplos de 5 minutos)
    duraciones = {}
    for campo, etiqueta in (
        ("duracion_1_3_min", "duración de grupos de 1 a 3 personas"),
        ("duracion_4_7_min", "duración de grupos de 4 a 7 personas"),
        ("duracion_8_mas_min", "duración de grupos de 8 o más personas"),
    ):
        try:
            valor = int(datos.get(campo, 0))
        except (TypeError, ValueError):
            raise ValueError(f"La {etiqueta} debe ser un número entero positivo (múltiplo de 5).")
        if valor <= 0:
            raise ValueError(f"La {etiqueta} debe ser mayor a 0 minutos.")
        if valor % 5 != 0:
            raise ValueError(f"La {etiqueta} debe ser un múltiplo de 5 minutos.")
        duraciones[campo] = valor

    try:
        franja = int(datos.get("franja_min", 30))
        if franja not in (15, 30, 60):
            raise ValueError("La franja horaria debe ser de 15, 30 o 60 minutos.")
    except (TypeError, ValueError):
        raise ValueError("La franja horaria debe ser un número válido.")

    try:
        tolerancia = int(datos.get("tolerancia_min", 0))
        if tolerancia < 0:
            raise ValueError("La tolerancia debe ser mayor o igual a 0 minutos.")
    except (TypeError, ValueError):
        raise ValueError("La tolerancia debe ser un número entero.")

    try:
        umbral_prep = int(datos.get("umbral_preparacion_min", 0))
        if umbral_prep <= 0:
            raise ValueError("El tiempo de preparación en cocina debe ser mayor a 0 minutos.")
    except (TypeError, ValueError):
        raise ValueError("El tiempo de preparación en cocina debe ser un número entero positivo.")

    try:
        max_web_tel = int(datos.get("max_reservas_web_por_telefono", 2))
        if max_web_tel < 1:
            raise ValueError("El tope de reservas web por teléfono debe ser al menos 1.")
    except (TypeError, ValueError):
        raise ValueError("El tope de reservas web por teléfono debe ser un número entero.")

    try:
        umbral_alerta = int(datos.get("umbral_alerta_pct", 80))
        if not (1 <= umbral_alerta <= 100):
            raise ValueError("El umbral de alerta debe estar entre 1% y 100%.")
    except (TypeError, ValueError):
        raise ValueError("El umbral de alerta de ocupación debe ser un número entero entre 1 y 100.")

    def _parsear_hora(valor_str, nombre_campo):
        if not valor_str:
            raise ValueError(f"El campo {nombre_campo} es obligatorio.")
        try:
            partes = str(valor_str).strip().split(":")
            h, m = int(partes[0]), int(partes[1])
            return time(h, m)
        except Exception:
            raise ValueError(f"Formato de hora inválido en {nombre_campo} (use HH:MM).")

    hora_apertura = _parsear_hora(datos.get("hora_apertura"), "hora de apertura")
    hora_cierre = _parsear_hora(datos.get("hora_cierre"), "hora de cierre")

    if hora_apertura >= hora_cierre:
        raise ValueError("La hora de cierre debe ser posterior a la hora de apertura.")

    try:
        dias_max = int(datos.get("dias_max_anticipacion", 0))
        if dias_max < 0:
            raise ValueError("Los días de anticipación deben ser mayores o iguales a 0.")
    except (TypeError, ValueError):
        raise ValueError("Los días de anticipación deben ser un número entero positivo.")

    try:
        anticipacion_min = int(datos.get("anticipacion_min_min", 30))
        if anticipacion_min < 0:
            raise ValueError("Los minutos de anticipación mínima deben ser mayores o iguales a 0.")
    except (TypeError, ValueError):
        raise ValueError("La anticipación mínima debe ser un número entero mayor o igual a 0.")

    porc_reservable = datos.get("porcentaje_reservable")
    porc_reservable_val = None
    if porc_reservable not in (None, ""):
        try:
            porc_reservable_val = int(porc_reservable)
            if not (1 <= porc_reservable_val <= 100):
                raise ValueError("El porcentaje reservable debe estar entre 1 y 100.")
        except (TypeError, ValueError):
            raise ValueError("El porcentaje reservable debe ser un número entre 1 y 100, o vacío.")

    abierto = bool(datos.get("abierto", True))
    yape_numero = (datos.get("yape_numero") or "").strip() or None
    yape_titular = (datos.get("yape_titular") or "").strip() or None
    mensaje_pago = (datos.get("mensaje_pago") or "").strip() or None

    # Contacto y marca (Fase 3.4). Las URL solo aceptan https:// y el WhatsApp
    # reusa la regla del teléfono del cliente (9 dígitos que empiezan en 9).
    whatsapp_numero = validar_whatsapp(datos.get("whatsapp_numero"))
    direccion = (datos.get("direccion") or "").strip() or None
    if direccion and len(direccion) > 150:
        raise ValueError("La dirección no puede superar los 150 caracteres.")
    maps_url = validar_url_segura(datos.get("maps_url"), "enlace del mapa")
    instagram_url = validar_url_segura(datos.get("instagram_url"), "enlace de Instagram")
    facebook_url = validar_url_segura(datos.get("facebook_url"), "enlace de Facebook")
    eslogan = (datos.get("eslogan") or "").strip() or None
    if eslogan and len(eslogan) > 150:
        raise ValueError("El eslogan no puede superar los 150 caracteres.")

    params = (
        nombre_local,
        aforo,
        total_mesas,
        personas_por_mesa,
        duraciones["duracion_1_3_min"],
        duraciones["duracion_4_7_min"],
        duraciones["duracion_8_mas_min"],
        franja,
        tolerancia,
        umbral_prep,
        max_web_tel,
        umbral_alerta,
        hora_apertura,
        hora_cierre,
        dias_max,
        anticipacion_min,
        porc_reservable_val,
        abierto,
        whatsapp_numero,
        direccion,
        maps_url,
        instagram_url,
        facebook_url,
        eslogan,
        yape_numero,
        yape_titular,
        mensaje_pago
    )

    dao.actualizar(params)
    return dao.obtener()
