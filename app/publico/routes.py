"""Rutas públicas para clientes (sin login)."""
from flask import Blueprint, render_template
from app.db import consultar_uno

publico_bp = Blueprint("publico", __name__)


@publico_bp.route("/")
def inicio():
    """Página de inicio pública con información básica y accesos a reservar y pedir."""
    config = consultar_uno("SELECT nombre_local, abierto, aforo_personas FROM config_local WHERE config_id = 1")
    nombre_local = config["nombre_local"] if config else "Quero Gastrobar"
    abierto = config["abierto"] if config else True
    return render_template("publico/index.html", nombre_local=nombre_local, abierto=abierto)
