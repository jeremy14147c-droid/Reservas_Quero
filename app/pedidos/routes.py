"""Rutas del módulo de pedidos para el staff.
Las páginas (cola, cocina, detalle, ticket) piden sus datos a /api/v1/pedidos/... con fetch
cada ~10 s; las acciones van por la API JSON. Toda la lógica vive en app/servicios/pedidos.py.
"""
from flask import Blueprint, render_template
from flask import current_app
from app.auth.decoradores import requiere_rol
from app.servicios import pedidos as servicio_pedidos
from app.utils import generar_qr_data_url

pedidos_bp = Blueprint("pedidos", __name__, url_prefix="/staff")


@pedidos_bp.route("/pedidos")
@requiere_rol("admin", "empleado")
def cola():
    """Cola del staff: Pendientes · Por cobrar · En cocina · Listos (fetch cada ~10 s)."""
    return render_template("pedidos/cola.html")


@pedidos_bp.route("/pedidos/cocina")
@requiere_rol("admin", "empleado")
def cocina():
    """Tablero kanban de cocina con temporizador y pantalla siempre encendida."""
    config = servicio_pedidos.obtener_config()
    return render_template("pedidos/cocina.html", umbral_min=config["umbral_preparacion_min"])


@pedidos_bp.route("/pedidos/nuevo")
@requiere_rol("admin", "empleado")
def nuevo():
    """Nuevo pedido en local: búsqueda por nombre, categoría o número de plato."""
    return render_template("pedidos/nuevo.html")


@pedidos_bp.route("/pedido/<int:pedido_id>")
@requiere_rol("admin", "empleado")
def detalle(pedido_id):
    """Detalle del pedido (a donde apunta el QR del ticket) con botones según el estado."""
    pedido = servicio_pedidos.obtener_pedido_detalle(pedido_id)
    if not pedido:
        return render_template("errores/404.html"), 404
    return render_template("pedidos/detalle.html", pedido=pedido)


@pedidos_bp.route("/pedido/<int:pedido_id>/ticket")
@requiere_rol("admin", "empleado")
def ticket(pedido_id):
    """Ticket de pedido imprimible con QR hacia el detalle."""
    pedido = servicio_pedidos.obtener_pedido_detalle(pedido_id)
    if not pedido:
        return render_template("errores/404.html"), 404
    base_url = current_app.config.get("BASE_URL") or "http://localhost:5000"
    url_detalle = f"{base_url}/staff/pedido/{pedido_id}"
    return render_template("pedidos/ticket.html", pedido=pedido, qr=generar_qr_data_url(url_detalle))
