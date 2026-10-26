"""Pruebas unitarias y de integración para la Fase 1: Carta, Configuración y Personal."""
import pytest
from app.servicios import carta as servicio_carta
from app.servicios import configuracion as servicio_config
from app.servicios import personal as servicio_personal
from app.db import consultar_uno, ejecutar


@pytest.fixture
def datos_prueba(app):
    """Crea una categoría y plato de prueba."""
    with app.app_context():
        # Limpiar posibles datos residuales de prueba
        ejecutar("DELETE FROM plato WHERE nombre LIKE %s", ("Plato Test %",))
        ejecutar("DELETE FROM categoria WHERE nombre = %s", ("Cat Test",))

        cat = servicio_carta.crear_categoria("Cat Test", orden=99)
        plato = servicio_carta.crear_plato(cat["categoria_id"], "Plato Test Alfa", 20.00, "Descripción test")

    yield {"cat_id": cat["categoria_id"], "plato_id": plato["plato_id"]}

    with app.app_context():
        ejecutar("DELETE FROM plato WHERE nombre LIKE %s", ("Plato Test %",))
        ejecutar("DELETE FROM categoria WHERE nombre = %s", ("Cat Test",))


def test_carta_publica_muestra_platos_disponibles(cliente, datos_prueba):
    """Comprueba que la carta pública liste el plato creado."""
    resp = cliente.get("/carta")
    assert resp.status_code == 200
    assert b"Plato Test Alfa" in resp.data
    assert b"S/ 20.00" in resp.data


def test_interruptor_disponibilidad_y_reflejo_en_carta(cliente, usuario_prueba, datos_prueba):
    """Verifica el endpoint de disponibilidad y que la carta pública lo marque 'Agotado'."""
    plato_id = datos_prueba["plato_id"]

    # Iniciar sesión como empleado
    cliente.post("/auth/login", data={"correo": "admin_test@quero.pe", "password": "clave123"})

    # 1. Cambiar a disponible = False
    resp_api = cliente.post(f"/api/v1/platos/{plato_id}/disponible", json={"disponible": False})
    assert resp_api.status_code == 200
    cuerpo = resp_api.get_json()
    assert cuerpo["ok"] is True
    assert cuerpo["datos"]["disponible"] is False

    # 2. En la carta pública debe salir como 'Agotado'
    resp_pub = cliente.get("/carta")
    assert b"Plato Test Alfa" in resp_pub.data
    assert b"Agotado por hoy" in resp_pub.data

    # 3. Volver a activar a True
    cliente.post(f"/api/v1/platos/{plato_id}/disponible", json={"disponible": True})
    resp_pub_act = cliente.get("/carta")
    assert b"Agotado por hoy" not in resp_pub_act.data


def test_actualizar_precio_api(cliente, usuario_prueba, datos_prueba, app):
    """Verifica actualización de precio vía API y rechazo de precios negativos."""
    plato_id = datos_prueba["plato_id"]
    cliente.post("/auth/login", data={"correo": "admin_test@quero.pe", "password": "clave123"})

    # Precio negativo debe dar error 400
    resp_neg = cliente.post(f"/api/v1/platos/{plato_id}/precio", json={"precio": -5.0})
    assert resp_neg.status_code == 400

    # Precio válido
    resp_ok = cliente.post(f"/api/v1/platos/{plato_id}/precio", json={"precio": 28.50})
    assert resp_ok.status_code == 200

    with app.app_context():
        p = consultar_uno("SELECT precio FROM plato WHERE plato_id = %s", (plato_id,))
        assert float(p["precio"]) == 28.50


def test_plato_desactivado_no_aparece_en_carta_publica(cliente, datos_prueba, app):
    """Un plato con activo = False nunca debe borrarse de la BD pero no debe aparecer en /carta."""
    plato_id = datos_prueba["plato_id"]
    with app.app_context():
        servicio_carta.desactivar_plato(plato_id)

        # Comprobar que sigue existiendo en BD pero inactivo
        p = consultar_uno("SELECT activo FROM plato WHERE plato_id = %s", (plato_id,))
        assert p is not None
        assert p["activo"] is False

    # No debe aparecer en la carta pública
    resp = cliente.get("/carta")
    assert b"Plato Test Alfa" not in resp.data


def test_validaciones_config_local(app):
    """Comprueba que actualizar_config_local rechace valores inválidos."""
    with app.app_context():
        # Aforo cero o negativo
        with pytest.raises(ValueError, match="aforo"):
            servicio_config.actualizar_config_local({"nombre_local": "Test", "aforo_personas": 0})

        # Hora cierre <= hora apertura
        with pytest.raises(ValueError, match="posterior a la hora de apertura"):
            servicio_config.actualizar_config_local({
                "nombre_local": "Test",
                "aforo_personas": 40,
                "total_mesas": 10,
                "personas_por_mesa": 4,
                "duracion_estadia_min": 90,
                "franja_min": 30,
                "tolerancia_min": 15,
                "umbral_preparacion_min": 20,
                "max_reservas_web_por_telefono": 2,
                "umbral_alerta_pct": 80,
                "hora_apertura": "14:00",
                "hora_cierre": "12:00"
            })


def test_admin_no_puede_auto_desactivarse(app):
    """Un administrador no puede desactivar su propia cuenta."""
    with app.app_context():
        admin = consultar_uno("SELECT personal_id FROM personal WHERE rol = 'admin' AND activo = TRUE LIMIT 1")
        admin_id = admin["personal_id"]

        with pytest.raises(ValueError, match="No puedes desactivar tu propia cuenta"):
            servicio_personal.cambiar_estado_personal(admin_id, False, solicitante_id=admin_id)


def test_creacion_empleado_obliga_cambiar_clave(cliente, app):
    """Un empleado recién creado tiene debe_cambiar_clave = TRUE y se le exige cambiarla."""
    with app.app_context():
        ejecutar("DELETE FROM personal WHERE correo = %s", ("mozo_nuevo@quero.pe",))
        nuevo = servicio_personal.crear_personal("Mozo Nuevo", "mozo_nuevo@quero.pe", "empleado", "temporal123")
        assert nuevo["debe_cambiar_clave"] is True

    # Iniciar sesión con este empleado
    resp_login = cliente.post("/auth/login", data={
        "correo": "mozo_nuevo@quero.pe",
        "password": "temporal123"
    }, follow_redirects=False)

    assert resp_login.status_code == 302
    assert "/auth/cambiar-clave" in resp_login.headers["Location"]

    # Limpiar
    with app.app_context():
        ejecutar("DELETE FROM personal WHERE correo = %s", ("mozo_nuevo@quero.pe",))
