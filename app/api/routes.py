"""Rutas base de la API interna /api/v1/..."""
from flask import Blueprint, request
from app.api.helpers import respuesta_ok, respuesta_error
from app.auth.decoradores import requiere_rol
from app.servicios import carta as servicio_carta

api_bp = Blueprint("api", __name__, url_prefix="/api/v1")


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
