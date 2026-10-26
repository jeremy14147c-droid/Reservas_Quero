"""Modelo y funciones de usuario para autenticación de Flask-Login."""
from flask_login import UserMixin, current_user
from app.db import consultar_uno


class UsuarioStaff(UserMixin):
    """Representa a un miembro del personal (admin o empleado) autenticado."""

    def __init__(self, datos):
        self.id = datos["personal_id"]
        self.personal_id = datos["personal_id"]
        self.nombre = datos["nombre"]
        self.correo = datos["correo"]
        self.rol = datos["rol"]
        self.activo = datos["activo"]
        self.debe_cambiar_clave = datos["debe_cambiar_clave"]

    @property
    def is_active(self):
        """Requerido por Flask-Login: comprueba si la cuenta está activa."""
        return self.activo

    def es_admin(self):
        return self.rol == "admin"

    def es_empleado(self):
        return self.rol == "empleado"


def cargar_usuario(personal_id):
    """Carga el usuario desde la base de datos por su ID para Flask-Login."""
    try:
        fila = consultar_uno(
            "SELECT personal_id, nombre, correo, rol, activo, debe_cambiar_clave "
            "FROM personal WHERE personal_id = %s",
            (int(personal_id),)
        )
        if fila and fila["activo"]:
            return UsuarioStaff(fila)
    except Exception:
        return None
    return None


def obtener_usuario_actual():
    """ÚNICA forma autorizada para obtener la identidad del usuario actual (AGENTS.md sección 4b).
    Devuelve la instancia de UsuarioStaff o None si es anónimo.
    """
    if current_user.is_authenticated:
        return current_user
    return None
