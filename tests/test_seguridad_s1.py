"""Pruebas de la Fase S1: Endurecimiento de login y sesión (SEGURIDAD_QUERO.md)."""
import pytest
from datetime import datetime, timedelta, timezone
from app.auth.seguridad import (
    destino_seguro,
    debe_bloquear,
    validar_politica_contrasena,
    HASH_FALSO_DUMMY
)
from app.db import ejecutar


def test_destino_seguro_rutas():
    """H-3: destino_seguro solo permite rutas relativas internas seguras."""
    # Rutas válidas
    assert destino_seguro("/staff/reservas") == "/staff/reservas"
    assert destino_seguro("/admin/personal") == "/admin/personal"
    assert destino_seguro("/staff/carta?categoria=1") == "/staff/carta?categoria=1"

    # Destinos externos o peligrosos rechazados
    assert destino_seguro("https://evil.example") is None
    assert destino_seguro("http://evil.example") is None
    assert destino_seguro("//evil.example/robo") is None
    assert destino_seguro(r"/\evil.example") is None
    assert destino_seguro(r"\\evil.example") is None
    assert destino_seguro("javascript:alert(1)") is None
    assert destino_seguro("data:text/html,hack") is None
    assert destino_seguro("") is None
    assert destino_seguro(None) is None


def test_login_evita_open_redirect(cliente, usuario_prueba):
    """H-3: Si next es externo, tras login se redirige al inicio del staff, no al externo."""
    resp = cliente.post("/auth/login?next=https://evil.example/robo", data={
        "correo": "admin_test@quero.pe",
        "password": "clave123"
    }, follow_redirects=False)

    assert resp.status_code == 302
    # La ubicación debe ser interna
    loc = resp.headers["Location"]
    assert not loc.startswith("https://evil.example")
    assert not loc.startswith("//evil.example")
    assert loc.startswith("/") or "localhost" in loc or "127.0.0.1" in loc


def test_regla_pura_debe_bloquear():
    """H-2: Regla pura de bloqueo por intentos fallidos."""
    ahora = datetime.now(timezone.utc)
    recientes_correo = [ahora - timedelta(minutes=i) for i in range(4)]
    recientes_ip = [ahora - timedelta(minutes=i) for i in range(10)]

    # 4 fallos de correo y 10 de IP -> no bloquea
    bloqueado, motivo = debe_bloquear(recientes_correo, recientes_ip, ahora)
    assert bloqueado is False
    assert motivo is None

    # 5 fallos de correo -> bloquea
    recientes_correo_5 = [ahora - timedelta(minutes=i) for i in range(5)]
    bloqueado, motivo = debe_bloquear(recientes_correo_5, recientes_ip, ahora)
    assert bloqueado is True
    assert "Demasiados intentos" in motivo

    # 20 fallos de IP dentro de la ventana de 10 min -> bloquea
    recientes_ip_20 = [ahora - timedelta(seconds=i*25) for i in range(20)]
    bloqueado, motivo = debe_bloquear(recientes_correo, recientes_ip_20, ahora)
    assert bloqueado is True
    assert "Demasiados intentos" in motivo

    # Intentos viejos (> 10 min) no bloquean
    viejos = [ahora - timedelta(minutes=15) for _ in range(6)]
    bloqueado, _ = debe_bloquear(viejos, [], ahora)
    assert bloqueado is False


def test_login_bloqueo_por_intentos_fallidos(cliente, usuario_prueba):
    """H-2: Tras 5 fallos seguidos, el intento 6 incluso con clave correcta es bloqueado."""
    # 5 fallos seguidos
    for _ in range(5):
        resp = cliente.post("/auth/login", data={
            "correo": "admin_test@quero.pe",
            "password": "clave_incorrecta"
        }, follow_redirects=True)
        assert resp.status_code == 200

    # 6to intento: con contraseña correcta, pero el sistema debe bloquear
    resp_bloqueado = cliente.post("/auth/login", data={
        "correo": "admin_test@quero.pe",
        "password": "clave123"
    }, follow_redirects=True)

    assert resp_bloqueado.status_code == 200
    assert b"Demasiados intentos" in resp_bloqueado.data
    # Asegurar que no inició sesión (no ve el panel del admin)
    assert b"ADMIN" not in resp_bloqueado.data


def test_politica_contrasena_minimo_10():
    """H-9: Mínimo 10 caracteres y rechazo de contraseñas comunes."""
    # Menos de 10 caracteres
    ok, err = validar_politica_contrasena("corta99")
    assert ok is False
    assert "al menos 10 caracteres" in err

    # Común
    ok, err = validar_politica_contrasena("1234567890")
    assert ok is False
    assert "contrase\u00f1a com\u00fan" in err.lower() or "muy com\u00fan" in err.lower() or "insegura" in err.lower()

    # Válida
    ok, err = validar_politica_contrasena("Segura2026!Quero")
    assert ok is True
    assert err is None


def test_logout_por_get_responde_405(cliente):
    """H-8: El logout no debe funcionar por GET (debe devolver 405 Method Not Allowed)."""
    resp = cliente.get("/auth/logout")
    assert resp.status_code == 405


def test_sesion_revocable_invalida_cookie_copiada(cliente, usuario_prueba):
    """H-1 (PS-05 b): Una cookie copiada antes de hacer logout NO permite reabrir el panel."""
    # 1. Iniciar sesión como admin
    resp = cliente.post("/auth/login", data={
        "correo": "admin_test@quero.pe",
        "password": "clave123"
    }, follow_redirects=False)
    assert resp.status_code == 302

    # 2. Acceder al panel para confirmar que la sesión funciona
    resp_panel = cliente.get("/staff/reservas")
    assert resp_panel.status_code == 200
    assert b"Reservas" in resp_panel.data

    # 3. Guardar el valor de la cookie de sesión actual
    cookie_copiada = cliente.get_cookie("session")
    assert cookie_copiada is not None

    # 4. Cerrar sesión por POST
    resp_logout = cliente.post("/auth/logout", follow_redirects=False)
    assert resp_logout.status_code == 302

    # 5. Volver a inyectar la cookie vieja copiada
    cliente.set_cookie("session", cookie_copiada.value)

    # 6. Intentar acceder al panel con la cookie vieja: DEBE redirigir al login (302) y no abrir el panel
    resp_reintento = cliente.get("/staff/reservas", follow_redirects=False)
    assert resp_reintento.status_code == 302
    assert "/auth/login" in resp_reintento.headers["Location"]
