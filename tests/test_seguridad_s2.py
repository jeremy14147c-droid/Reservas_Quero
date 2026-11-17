"""Pruebas de la Fase S2: Cabeceras de seguridad, UUID y clave secreta (SEGURIDAD_QUERO.md)."""
import pytest
from app.config import validar_secret_key


def test_rutas_publicas_uuid_invalido_devuelve_404(cliente):
    """H-7: Parámetros no-UUID en /reserva/<uuid:token> y /pedido/<uuid:token> deben devolver 404 sin error 500."""
    # /reserva/1 y /reserva/texto
    resp1 = cliente.get("/reserva/1")
    assert resp1.status_code == 404

    resp2 = cliente.get("/reserva/no-es-uuid")
    assert resp2.status_code == 404

    # /pedido/1 y /pedido/abc
    resp3 = cliente.get("/pedido/1")
    assert resp3.status_code == 404

    resp4 = cliente.get("/pedido/abc")
    assert resp4.status_code == 404


def test_cabeceras_de_seguridad_presentes(cliente):
    """H-6: Cabeceras de seguridad presentes en las respuestas HTTP."""
    resp = cliente.get("/")
    assert resp.status_code == 200

    headers = resp.headers
    assert headers.get("X-Content-Type-Options") == "nosniff"
    assert headers.get("X-Frame-Options") == "DENY"
    assert headers.get("Referrer-Policy") == "strict-origin-when-cross-origin"
    assert headers.get("Permissions-Policy") == "camera=(), microphone=(), geolocation=()"
    assert "Content-Security-Policy" in headers
    assert "default-src 'self'" in headers["Content-Security-Policy"]


def test_validacion_secret_key_en_produccion():
    """H-10: Validación de SECRET_KEY en producción (falla si es la por defecto o corta)."""
    # Clave de desarrollo en producción -> falla
    with pytest.raises(ValueError, match="SECRET_KEY"):
        validar_secret_key("dev-secret-key-cambiar-en-produccion", produccion=True)

    # Clave menor a 32 caracteres en producción -> falla
    with pytest.raises(ValueError, match="32 caracteres"):
        validar_secret_key("clave_corta_12345", produccion=True)

    # Clave válida de al menos 32 caracteres en producción -> éxito
    assert validar_secret_key("clave-de-mas-de-32-caracteres-muy-segura-2026-prod", produccion=True) is True

    # En desarrollo (produccion=False) no bloquea el arranque
    assert validar_secret_key("dev-secret-key-cambiar-en-produccion", produccion=False) is True
