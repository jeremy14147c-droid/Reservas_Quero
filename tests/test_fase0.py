"""Pruebas unitarias y de integración para la Fase 0."""
import pytest
from app.db import consultar_uno, consultar_todos
from app.auth.usuario import obtener_usuario_actual


def test_db_conexion(app):
    """Comprueba que la base de datos responde y contiene config_local."""
    with app.app_context():
        local = consultar_uno("SELECT config_id, nombre_local FROM config_local WHERE config_id = 1")
        assert local is not None
        assert local["config_id"] == 1


def test_api_salud(cliente):
    """Verifica que GET /api/v1/salud devuelva el JSON uniforme esperado."""
    resp = cliente.get("/api/v1/salud")
    assert resp.status_code == 200
    datos = resp.get_json()
    assert datos["ok"] is True
    assert datos["datos"]["estado"] == "vivo"


def test_pagina_inicio_publica(cliente):
    """Comprueba que la página de inicio pública cargue con código 200."""
    resp = cliente.get("/")
    assert resp.status_code == 200
    assert b"QUERO" in resp.data
    assert b"Reservar Mesa" in resp.data
    assert b"Hacer Pedido" in resp.data


def test_proteccion_rutas_staff_sin_login(cliente):
    """Comprueba que intentar entrar a /staff sin login redirija al login con el next correspondiente."""
    resp = cliente.get("/staff", follow_redirects=False)
    assert resp.status_code == 302
    assert "/auth/login" in resp.headers["Location"]


def test_proteccion_rutas_admin_sin_login(cliente):
    """Comprueba que intentar entrar a /admin sin login redirija a /auth/login."""
    resp = cliente.get("/admin", follow_redirects=False)
    assert resp.status_code == 302
    assert "/auth/login" in resp.headers["Location"]


def test_error_404_html_y_json(cliente):
    """Verifica que una ruta 404 fuera de /api/ devuelva HTML y bajo /api/ devuelva JSON uniforme."""
    resp_html = cliente.get("/ruta-inexistente")
    assert resp_html.status_code == 404
    assert b"404 - P" in resp_html.data

    resp_json = cliente.get("/api/v1/no-existe")
    assert resp_json.status_code == 404
    cuerpo = resp_json.get_json()
    assert cuerpo["ok"] is False
    assert cuerpo["error"]["codigo"] == "NO_ENCONTRADO"
