"""Pruebas para autenticación, cambio de contraseña y control de acceso por roles."""
import pytest
from werkzeug.security import generate_password_hash, check_password_hash
from app.db import ejecutar, consultar_uno


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


def test_login_exitoso_admin(cliente, usuario_prueba):
    """Verifica inicio de sesión exitoso de un admin."""
    resp = cliente.post("/auth/login", data={
        "correo": "admin_test@quero.pe",
        "password": "clave123"
    }, follow_redirects=True)

    assert resp.status_code == 200
    assert b"Admin Prueba" in resp.data
    assert b"ADMIN" in resp.data


def test_login_credenciales_invalidas(cliente, usuario_prueba):
    """Verifica rechazo con contraseña incorrecta."""
    resp = cliente.post("/auth/login", data={
        "correo": "admin_test@quero.pe",
        "password": "clave_equivocada"
    }, follow_redirects=True)

    assert resp.status_code == 200
    assert b"Credenciales incorrectas" in resp.data


def test_obligacion_cambiar_clave_primer_ingreso(cliente, usuario_prueba):
    """Si debe_cambiar_clave es TRUE, redirige obligatoriamente a /auth/cambiar-clave."""
    resp = cliente.post("/auth/login", data={
        "correo": "empleado_test@quero.pe",
        "password": "clave123"
    }, follow_redirects=False)

    assert resp.status_code == 302
    assert "/auth/cambiar-clave" in resp.headers["Location"]


def test_cambio_clave_exitoso(cliente, usuario_prueba, app):
    """Permite cambiar la contraseña y quita la bandera debe_cambiar_clave."""
    # Login empleado
    cliente.post("/auth/login", data={
        "correo": "empleado_test@quero.pe",
        "password": "clave123"
    })

    # Cambiar contraseña
    resp = cliente.post("/auth/cambiar-clave", data={
        "clave_actual": "clave123",
        "nueva_clave": "nuevaClave456",
        "confirmar_clave": "nuevaClave456"
    }, follow_redirects=True)

    assert resp.status_code == 200
    assert b"actualizada con" in resp.data

    # Comprobar en base de datos
    with app.app_context():
        user = consultar_uno("SELECT password_hash, debe_cambiar_clave FROM personal WHERE correo = 'empleado_test@quero.pe'")
        assert user["debe_cambiar_clave"] is False
        assert check_password_hash(user["password_hash"], "nuevaClave456")


def test_restriccion_rol_empleado_en_admin(cliente, usuario_prueba):
    """Un empleado no puede acceder a /admin (recibe 403)."""
    # Primero cambiarle la clave al empleado para que no esté obligado a cambiar clave
    cliente.post("/auth/login", data={
        "correo": "empleado_test@quero.pe",
        "password": "clave123"
    })
    cliente.post("/auth/cambiar-clave", data={
        "clave_actual": "clave123",
        "nueva_clave": "nuevaClave456",
        "confirmar_clave": "nuevaClave456"
    })

    # Intentar acceder a /admin
    resp = cliente.get("/admin", follow_redirects=False)
    assert resp.status_code == 403
