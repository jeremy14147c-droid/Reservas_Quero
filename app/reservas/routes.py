"""Rutas del módulo de reservas para el staff.
La pizarra toma sus datos de GET /api/v1/reservas/dia (fetch cada ~10 s);
las acciones (confirmar, rechazar, cambiar hora...) van por la API JSON.
Aquí solo se sirven las páginas: pizarra, detalle (destino del QR) y ticket.
"""
from flask import Blueprint, render_template, request
from app.auth.decoradores import requiere_rol
from app.servicios import reservas as servicio_reservas

reservas_bp = Blueprint("reservas", __name__, url_prefix="/staff")


@reservas_bp.route("")
@reservas_bp.route("/reservas")
@requiere_rol("admin", "empleado")
def pizarra():
    """Tablero principal de reservas del día (hoy por defecto)."""
    fecha_sel = request.args.get("fecha") or servicio_reservas.hoy().isoformat()
    nombre_local = servicio_reservas.obtener_config()["nombre_local"]
    return render_template("reservas/pizarra.html", fecha_sel=fecha_sel,
                           hoy_iso=servicio_reservas.hoy().isoformat(), nombre_local=nombre_local)


@reservas_bp.route("/reserva/<int:reserva_id>")
@requiere_rol("admin", "empleado")
def detalle(reserva_id):
    """Detalle de una reserva (a donde apunta el QR del ticket) con botones de acción."""
    reserva = servicio_reservas.obtener_reserva_detalle(reserva_id)
    if not reserva:
        return render_template("errores/404.html"), 404
    return render_template("reservas/detalle.html", reserva=reserva)


@reservas_bp.route("/reserva/<int:reserva_id>/ticket")
@requiere_rol("admin", "empleado")
def ticket(reserva_id):
    """Ticket de reserva listo para imprimir en la tiquetera (con QR del detalle)."""
    from flask import current_app
    from app.utils import generar_qr_data_url
    reserva = servicio_reservas.obtener_reserva_detalle(reserva_id)
    if not reserva:
        return render_template("errores/404.html"), 404
    base_url = current_app.config.get("BASE_URL") or "http://localhost:5000"
    url_detalle = f"{base_url}/staff/reserva/{reserva_id}"
    return render_template("reservas/ticket.html", reserva=reserva, qr=generar_qr_data_url(url_detalle))
