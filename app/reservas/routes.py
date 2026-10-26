"""Rutas del módulo de reservas para el staff."""
from flask import Blueprint, render_template
from app.auth.decoradores import requiere_rol

reservas_bp = Blueprint("reservas", __name__, url_prefix="/staff")


@reservas_bp.route("")
@reservas_bp.route("/reservas")
@requiere_rol("admin", "empleado")
def pizarra():
    """Tablero principal de reservas del staff (Fase 2)."""
    return render_template("reservas/pizarra.html")
