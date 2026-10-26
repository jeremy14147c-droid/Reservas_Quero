"""Rutas del módulo de administración (exclusivo para rol admin)."""
from flask import Blueprint, render_template
from app.auth.decoradores import requiere_rol

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")


@admin_bp.route("")
@admin_bp.route("/config")
@requiere_rol("admin")
def config():
    """Panel de configuración del local y personal (Fase 1)."""
    return render_template("admin/config.html")
