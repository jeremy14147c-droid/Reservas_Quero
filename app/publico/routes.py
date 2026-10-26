"""Rutas públicas para clientes (sin login)."""
from flask import Blueprint, render_template
from app.db import consultar_uno
from app.servicios import carta as servicio_carta

publico_bp = Blueprint("publico", __name__)


@publico_bp.route("/")
def inicio():
    """Página de inicio pública con información básica y accesos a reservar y pedir."""
    config = consultar_uno("SELECT nombre_local, abierto, aforo_personas FROM config_local WHERE config_id = 1")
    nombre_local = config["nombre_local"] if config else "Quero Gastrobar"
    abierto = config["abierto"] if config else True
    return render_template("publico/index.html", nombre_local=nombre_local, abierto=abierto)


@publico_bp.route("/carta")
def carta():
    """Carta pública de platos para clientes, agrupada por categorías activas."""
    carta_datos = servicio_carta.obtener_carta_publica()
    config = consultar_uno("SELECT nombre_local FROM config_local WHERE config_id = 1")
    nombre_local = config["nombre_local"] if config else "Quero Gastrobar"
    return render_template("publico/carta.html", carta=carta_datos, nombre_local=nombre_local)
