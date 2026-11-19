"""Capa de Acceso a Datos (Data Access Object - DAO).
Contiene TODO el SQL del sistema Quero Gastrobar.
Las rutas y los servicios nunca escriben SQL directamente.
"""
from app.dao.config_dao import ConfigDAO
from app.dao.cliente_dao import ClienteDAO
from app.dao.personal_dao import PersonalDAO
from app.dao.carta_dao import CartaDAO
from app.dao.reserva_dao import ReservaDAO
from app.dao.pedido_dao import PedidoDAO

__all__ = [
    "ConfigDAO",
    "ClienteDAO",
    "PersonalDAO",
    "CartaDAO",
    "ReservaDAO",
    "PedidoDAO"
]
