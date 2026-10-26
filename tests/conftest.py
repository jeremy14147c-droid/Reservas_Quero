"""Configuración común para las pruebas con pytest."""
import pytest
from app import create_app
from app.config import Config


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
