"""Rutas base de la API interna /api/v1/...
Las páginas web (pizarra, seguimiento) consumen estas rutas con fetch cada ~10 s.
Toda la lógica vive en app/servicios/.
"""
from datetime import date, time, datetime
from flask import Blueprint, request
from app.api.helpers import respuesta_ok, respuesta_error
from app.auth.decoradores import requiere_rol
from app.servicios import carta as servicio_carta
from app.servicios import reservas as servicio_reservas

api_bp = Blueprint("api", __name__, url_prefix="/api/v1")

CODIGO_CUPO = "CUPO_NO_DISPONIBLE"


def _iso(valor):
    """Serializa date/time/datetime a ISO 8601 (fechas y horas en formato uniforme)."""
    if isinstance(valor, (date, datetime)):
        return valor.isoformat()
    if isinstance(valor, time):
        return valor.isoformat("minutes")
    return valor


def _serializar_reserva(r):
    """Fila de reserva lista para JSON (sin datos sensibles internos)."""
    datos = dict(r)
    for campo in ("fecha", "hora", "hora_anterior", "creado_en"):
        if datos.get(campo) is not None:
            datos[campo] = _iso(datos[campo])
    return datos


@api_bp.route("/salud", methods=["GET"])
def salud():
    """Endpoint de comprobación de salud del sistema."""
    return respuesta_ok({"estado": "vivo"})


@api_bp.route("/platos/buscar", methods=["GET"])
@requiere_rol("admin", "empleado")
def buscar_platos():
    """Busca platos activos por código numérico exacto o por nombre (insensible a tildes y mayúsculas).
    Retorna id, codigo, nombre, precio, disponible y categoria_nombre.
    """
    query = request.args.get("q", "")
    platos = servicio_carta.buscar_platos(query)
    # Formatear salida uniforme
    datos = [
        {
            "id": p["plato_id"],
            "codigo": p["codigo"],
            "nombre": p["nombre"],
            "precio": float(p["precio"]),
            "disponible": p["disponible"],
            "categoria": p["categoria_nombre"]
        }
        for p in platos
    ]
    return respuesta_ok(datos)


@api_bp.route("/platos/<int:plato_id>/disponible", methods=["POST"])
@requiere_rol("admin", "empleado")
def cambiar_disponible(plato_id):
    """Interruptor rápido para cambiar la disponibilidad de un plato (agotado / disponible)."""
    datos = request.get_json(silent=True) or {}
    if "disponible" not in datos:
        return respuesta_error("DATOS_INCOMPLETOS", "Se requiere el campo 'disponible' (true o false).", 400)

    try:
        resultado = servicio_carta.cambiar_disponibilidad_plato(plato_id, datos["disponible"])
        return respuesta_ok(resultado)
    except ValueError as e:
        return respuesta_error("ERROR_OPERACION", str(e), 400)
    except Exception:
        return respuesta_error("ERROR_INTERNO", "No se pudo actualizar la disponibilidad del plato.", 500)


@api_bp.route("/platos/<int:plato_id>/precio", methods=["POST"])
@requiere_rol("admin", "empleado")
def cambiar_precio(plato_id):
    """Actualiza el precio de un plato vía AJAX."""
    datos = request.get_json(silent=True) or {}
    if "precio" not in datos:
        return respuesta_error("DATOS_INCOMPLETOS", "Se requiere el campo 'precio'.", 400)

    try:
        resultado = servicio_carta.actualizar_precio_plato(plato_id, datos["precio"])
        return respuesta_ok(resultado)
    except ValueError as e:
        return respuesta_error("ERROR_OPERACION", str(e), 400)
    except Exception:
        return respuesta_error("ERROR_INTERNO", "No se pudo actualizar el precio.", 500)


# ---------------------------------------------------------------- reservas (Fase 2)

def _manejar_error_negocio(error):
    """Traduce los errores de negocio del servicio a errores JSON uniformes.
    CUPO_NO_DISPONIBLE devuelve 409: la pizarra lo usa para preguntar si el staff fuerza.
    """
    from app.servicios.reservas import CupoNoDisponible
    if isinstance(error, CupoNoDisponible):
        return respuesta_error(CODIGO_CUPO, str(error), 409)
    if isinstance(error, ValueError):
        return respuesta_error("ERROR_NEGOCIO", str(error), 400)
    return respuesta_error("ERROR_INTERNO", "Ocurrió un error inesperado en la operación.", 500)


@api_bp.route("/reservas/dia", methods=["GET"])
@requiere_rol("admin", "empleado")
def reservas_dia():
    """Pizarra digital del día: franjas con fn_carga_dia, reservas por franja y solicitudes pendientes.
    Ej: GET /api/v1/reservas/dia?fecha=2026-10-20
    """
    fecha = request.args.get("fecha")
    if not fecha:
        fecha = servicio_reservas.hoy().isoformat()
    try:
        fecha_date = datetime.strptime(fecha, "%Y-%m-%d").date()
    except ValueError:
        return respuesta_error("PARAMETRO_INVALIDO", "La fecha debe tener el formato YYYY-MM-DD.", 400)

    try:
        pizarra = servicio_reservas.obtener_pizarra(fecha_date)
    except ValueError as e:
        return respuesta_error("ERROR_NEGOCIO", str(e), 400)

    franjas = []
    for f in pizarra["franjas"]:
        franja_datos = {
            "franja_inicio": _iso(f["franja_inicio"]),
            "franja_fin": _iso(f["franja_fin"]),
            "reservas": f["reservas_totales"],
            "personas": f["personas"],
            "mesas": f["mesas"],
            "limite_personas": f["limite_personas"],
            "limite_mesas": f["limite_mesas"],
            "personas_libres": f["personas_libres"],
            "mesas_libres": f["mesas_libres"],
            "limita": f["limita"],
            "nivel": f["nivel"],
            "ocupan": [_serializar_reserva(r) for r in f["ocupan"]],
        }
        franjas.append(franja_datos)

    return respuesta_ok({
        "fecha": _iso(pizarra["fecha"]),
        "franjas": franjas,
        "pendientes": [_serializar_reserva(r) for r in pizarra["pendientes"]],
    })


@api_bp.route("/reservas/<int:reserva_id>", methods=["GET"])
@requiere_rol("admin", "empleado")
def reserva_detalle(reserva_id):
    """Detalle de una reserva para el panel (el QR del ticket apunta a su vista HTML)."""
    try:
        reserva = servicio_reservas.obtener_reserva_detalle(reserva_id)
    except ValueError as e:
        return _manejar_error_negocio(e)
    if not reserva:
        return respuesta_error("NO_ENCONTRADO", "La reserva no existe.", 404)
    return respuesta_ok(_serializar_reserva(reserva))


@api_bp.route("/reservas", methods=["POST"])
@requiere_rol("admin", "empleado")
def crear_reserva():
    """Nueva reserva creada desde el staff: nace 'confirmada'.
    Si no hay cupo responde 409 y el tablero pregunta si se fuerza (excede_cupo = TRUE).
    """
    datos = request.get_json(silent=True) or {}
    from app.auth.usuario import obtener_usuario_actual
    usuario = obtener_usuario_actual()

    try:
        reserva = servicio_reservas.crear_reserva_staff(
            datos,
            personal_id=usuario.id if usuario else None,
            forzar=bool(datos.get("forzar")),
        )
        return respuesta_ok(_serializar_reserva(reserva), 201)
    except Exception as e:
        return _manejar_error_negocio(e)


@api_bp.route("/reservas/<int:reserva_id>/confirmar", methods=["POST"])
@requiere_rol("admin", "empleado")
def confirmar_reserva(reserva_id):
    """Confirma una solicitud pendiente. Con forzar=true la confirma aun sin cupo."""
    datos = request.get_json(silent=True) or {}
    try:
        resultado = servicio_reservas.confirmar_reserva(reserva_id, forzar=bool(datos.get("forzar")))
        return respuesta_ok(_serializar_reserva(resultado))
    except Exception as e:
        return _manejar_error_negocio(e)


@api_bp.route("/reservas/<int:reserva_id>/rechazar", methods=["POST"])
@requiere_rol("admin", "empleado")
def rechazar_reserva(reserva_id):
    """Rechaza una solicitud (motivo obligatorio)."""
    datos = request.get_json(silent=True) or {}
    try:
        resultado = servicio_reservas.rechazar_reserva(reserva_id, datos.get("motivo"))
        return respuesta_ok(_serializar_reserva(resultado))
    except Exception as e:
        return _manejar_error_negocio(e)


@api_bp.route("/reservas/<int:reserva_id>/cancelar", methods=["POST"])
@requiere_rol("admin", "empleado")
def cancelar_reserva(reserva_id):
    """Cancela una reserva (pendiente o confirmada)."""
    datos = request.get_json(silent=True) or {}
    try:
        resultado = servicio_reservas.cancelar_reserva(reserva_id, datos.get("motivo"))
        return respuesta_ok(_serializar_reserva(resultado))
    except Exception as e:
        return _manejar_error_negocio(e)


@api_bp.route("/reservas/<int:reserva_id>/llego", methods=["POST"])
@requiere_rol("admin", "empleado")
def llego_reserva(reserva_id):
    """El cliente llegó: la marca como 'llego' (sigue ocupando capacidad)."""
    try:
        resultado = servicio_reservas.marcar_llego(reserva_id)
        return respuesta_ok(_serializar_reserva(resultado))
    except Exception as e:
        return _manejar_error_negocio(e)


@api_bp.route("/reservas/<int:reserva_id>/no_llego", methods=["POST"])
@requiere_rol("admin", "empleado")
def no_llego_reserva(reserva_id):
    """Liberar la mesa: el cliente no apareció. Estado final (solo alerta previa)."""
    try:
        resultado = servicio_reservas.marcar_no_llego(reserva_id)
        return respuesta_ok(_serializar_reserva(resultado))
    except Exception as e:
        return _manejar_error_negocio(e)


@api_bp.route("/reservas/<int:reserva_id>/cambiar-hora", methods=["POST"])
@requiere_rol("admin", "empleado")
def cambiar_hora_reserva(reserva_id):
    """Cambia la hora de una reserva confirmada (dos toques).
    Valida con fn_hay_cupo excluyendo la propia reserva; con forzar=true se marca excede_cupo.
    Funciona incluso pasada la tolerancia, mientras siga 'confirmada'.
    """
    datos = request.get_json(silent=True) or {}
    if not datos.get("hora"):
        return respuesta_error("DATOS_INCOMPLETOS", "Se requiere la nueva 'hora'.", 400)
    try:
        resultado = servicio_reservas.cambiar_hora(
            reserva_id, datos["hora"], forzar=bool(datos.get("forzar"))
        )
        return respuesta_ok(_serializar_reserva(resultado))
    except Exception as e:
        return _manejar_error_negocio(e)
