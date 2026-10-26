"""Rutas base de la API interna /api/v1/..."""
from flask import Blueprint
from app.api.helpers import respuesta_ok

api_bp = Blueprint("api", __name__, url_prefix="/api/v1")


@api_bp.route("/salud", methods=["GET"])
def salud():
    """Endpoint de comprobación de salud del sistema."""
    return respuesta_ok({"estado": "vivo"})
