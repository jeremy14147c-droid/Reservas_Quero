"""Servicio para consultar y actualizar la configuración operativa del local (config_local)."""
from datetime import time
from app.db import consultar_uno, ejecutar


def obtener_config_local():
    """Devuelve la fila de configuración del local (config_id = 1)."""
    return consultar_uno("SELECT * FROM config_local WHERE config_id = 1")


def actualizar_config_local(datos):
    """Valida y actualiza los parámetros operativos del local en config_local.
    Lanza ValueError con mensaje claro si alguna validación falla.
    """
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

    try:
        duracion_estadia = int(datos.get("duracion_estadia_min", 0))
        if duracion_estadia <= 0:
            raise ValueError("La duración de estadía debe ser mayor a 0 minutos.")
    except (TypeError, ValueError):
        raise ValueError("La duración de estadía debe ser un número entero positivo.")

    try:
        franja = int(datos.get("franja_min", 30))
        if franja not in (15, 30, 60):
            raise ValueError("La franja horaria debe ser de 15, 30 o 60 minutos.")
    except (TypeError, ValueError):
        raise ValueError("La franja horaria debe ser 15, 30 o 60 minutos.")

    try:
        tolerancia = int(datos.get("tolerancia_min", 0))
        if tolerancia < 0:
            raise ValueError("La tolerancia no puede ser negativa.")
    except (TypeError, ValueError):
        raise ValueError("La tolerancia debe ser un número entero igual o mayor a 0.")

    try:
        umbral_prep = int(datos.get("umbral_preparacion_min", 0))
        if umbral_prep <= 0:
            raise ValueError("El umbral de preparación de cocina debe ser mayor a 0 minutos.")
    except (TypeError, ValueError):
        raise ValueError("El umbral de preparación de cocina debe ser un número entero positivo.")

    try:
        max_web_tel = int(datos.get("max_reservas_web_por_telefono", 2))
        if max_web_tel < 1:
            raise ValueError("El máximo de reservas web por teléfono debe ser al menos 1.")
    except (TypeError, ValueError):
        raise ValueError("El máximo de reservas web por teléfono debe ser un número entero mayor o igual a 1.")

    try:
        umbral_alerta = int(datos.get("umbral_alerta_pct", 80))
        if not (1 <= umbral_alerta <= 100):
            raise ValueError("El umbral de alerta de ocupación debe estar entre 1% y 100%.")
    except (TypeError, ValueError):
        raise ValueError("El umbral de alerta de ocupación debe ser un número entre 1 y 100.")

    # Horarios de apertura y cierre
    hora_apertura = datos.get("hora_apertura")
    hora_cierre = datos.get("hora_cierre")
    if not hora_apertura or not hora_cierre:
        raise ValueError("Los horarios de apertura y cierre son obligatorios.")

    if str(hora_cierre) <= str(hora_apertura):
        raise ValueError("La hora de cierre debe ser posterior a la hora de apertura.")

    try:
        dias_max = int(datos.get("dias_max_anticipacion", 0))
        if dias_max < 0:
            raise ValueError("Los días de anticipación no pueden ser negativos.")
    except (TypeError, ValueError):
        raise ValueError("Los días de anticipación deben ser un número entero igual o mayor a 0.")

    porc_reservable = datos.get("porcentaje_reservable")
    if porc_reservable in (None, "", "null", "None"):
        porc_reservable_val = None
    else:
        try:
            porc_reservable_val = int(porc_reservable)
            if not (1 <= porc_reservable_val <= 100):
                raise ValueError("El porcentaje reservable debe estar entre 1% y 100%.")
        except (TypeError, ValueError):
            raise ValueError("El porcentaje reservable debe ser un número entre 1 y 100 o dejarse vacío.")

    abierto = bool(datos.get("abierto", True))
    yape_numero = (datos.get("yape_numero") or "").strip() or None
    yape_titular = (datos.get("yape_titular") or "").strip() or None
    mensaje_pago = (datos.get("mensaje_pago") or "").strip() or None

    ejecutar(
        """
        UPDATE config_local
        SET nombre_local = %s,
            aforo_personas = %s,
            total_mesas = %s,
            personas_por_mesa = %s,
            duracion_estadia_min = %s,
            franja_min = %s,
            tolerancia_min = %s,
            umbral_preparacion_min = %s,
            max_reservas_web_por_telefono = %s,
            umbral_alerta_pct = %s,
            hora_apertura = %s,
            hora_cierre = %s,
            dias_max_anticipacion = %s,
            porcentaje_reservable = %s,
            abierto = %s,
            yape_numero = %s,
            yape_titular = %s,
            mensaje_pago = %s
        WHERE config_id = 1
        """,
        (
            nombre_local,
            aforo,
            total_mesas,
            personas_por_mesa,
            duracion_estadia,
            franja,
            tolerancia,
            umbral_prep,
            max_web_tel,
            umbral_alerta,
            hora_apertura,
            hora_cierre,
            dias_max,
            porc_reservable_val,
            abierto,
            yape_numero,
            yape_titular,
            mensaje_pago
        )
    )

    return obtener_config_local()
