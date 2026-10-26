"""Configuración común para las pruebas con pytest."""
import pytest
from werkzeug.security import generate_password_hash
from app import create_app
from app.config import Config
from app.db import ejecutar


class TestConfig(Config):
    TESTING = True
    WTF_CSRF_ENABLED = False  # Desactivar CSRF durante tests automatizados de formularios


@pytest.fixture
def app():
    """Instancia de la aplicación configurada para pruebas."""
    aplicacion = create_app(TestConfig)
    return aplicacion


@pytest.fixture
def cliente(app):
    """Cliente de pruebas de Flask."""
    return app.test_client()


@pytest.fixture
def usuario_prueba(app):
    """Crea usuarios de prueba para admin y empleado."""
    with app.app_context():
        # Limpiar usuarios de prueba si existían
        ejecutar("DELETE FROM personal WHERE correo IN ('admin_test@quero.pe', 'empleado_test@quero.pe')")

        hash_clave = generate_password_hash("clave123")
        ejecutar(
            "INSERT INTO personal (nombre, correo, password_hash, rol, activo, debe_cambiar_clave) "
            "VALUES (%s, %s, %s, 'admin', TRUE, FALSE)",
            ("Admin Prueba", "admin_test@quero.pe", hash_clave)
        )
        ejecutar(
            "INSERT INTO personal (nombre, correo, password_hash, rol, activo, debe_cambiar_clave) "
            "VALUES (%s, %s, %s, 'empleado', TRUE, TRUE)",
            ("Mozo Prueba", "empleado_test@quero.pe", hash_clave)
        )

    yield

    with app.app_context():
        ejecutar("DELETE FROM personal WHERE correo IN ('admin_test@quero.pe', 'empleado_test@quero.pe')")
