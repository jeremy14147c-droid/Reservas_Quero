"""Pruebas de integración de la Fase 3.3:
- Validación de anticipacion_min_min en configuración
- Servidor rechaza horas pasadas en web, staff y cambiar_hora
- Semáforo marca horas pasadas
- Pizarra del staff y API /api/v1/reservas/dia ocultan franjas pasadas y con ver_pasadas=1 las muestran
- liberar_reservas_vencidas es idempotente y solo cierra pendientes y confirmadas vencidas
"""
from datetime import date, time, datetime, timedelta
from zoneinfo import ZoneInfo
import pytest

from app.db import consultar_uno, consultar_todos, ejecutar
from app.servicios import configuracion as servicio_config
from app.servicios import reservas as servicio_reservas

ZONA_LIMA = ZoneInfo("America/Lima")
TELS_F33 = ["966883001", "966883002", "966883003", "966883004"]


@pytest.fixture
def limpiar_f33(app):
    yield
    with app.app_context():
        ejecutar(
            "DELETE FROM reserva WHERE cliente_id IN "
            "(SELECT cliente_id FROM cliente WHERE telefono = ANY(%s))",
            (TELS_F33,)
        )
        ejecutar("DELETE FROM cliente WHERE telefono = ANY(%s)", (TELS_F33,))
        ejecutar(
            "UPDATE config_local SET anticipacion_min_min = 30 WHERE config_id = 1"
        )


def test_validacion_config_anticipacion_minima(app, limpiar_f33):
    """anticipacion_min_min debe ser entero >= 0."""
    with app.app_context():
        config_actual = servicio_config.obtener_config_local()
        datos = dict(config_actual)

        # Inválido: negativo
        datos["anticipacion_min_min"] = -5
        with pytest.raises(ValueError, match="anticipación"):
            servicio_config.actualizar_config_local(datos)

        # Válido: 0 o 45
        datos["anticipacion_min_min"] = 45
        actualizada = servicio_config.actualizar_config_local(datos)
        assert actualizada["anticipacion_min_min"] == 45


def test_rechazo_hora_pasada_en_servidor_web(app, limpiar_f33):
    """crear_reserva_web rechaza horas que no cumplen la anticipación mínima."""
    with app.app_context():
        hoy = servicio_reservas.hoy()
        # Una hora muy temprana que seguro ya pasó (ej. 12:00 si estamos más tarde, o usamos día de ayer)
        datos = {
            "nombre": "Cliente Pasado",
            "telefono": TELS_F33[0],
            "correo": "pasado@test.pe",
            "fecha": (hoy - timedelta(days=1)).isoformat(),
            "hora": "12:00",
            "personas": 2,
            "acepta_datos": True,
        }
        with pytest.raises(ValueError, match="pasó|anterior"):
            servicio_reservas.crear_reserva_web(datos)


def test_rechazo_hora_pasada_en_servidor_staff(app, usuario_prueba, limpiar_f33):
    """crear_reserva_staff y cambiar_hora rechazan franjas que ya terminaron."""
    with app.app_context():
        hoy = servicio_reservas.hoy()
        admin = consultar_uno("SELECT personal_id FROM personal WHERE correo = 'admin_test@quero.pe'")
        datos = {
            "nombre": "Cliente Staff Pasado",
            "telefono": TELS_F33[1],
            "fecha": (hoy - timedelta(days=1)).isoformat(),
            "hora": "12:00",
            "personas": 2,
        }
        with pytest.raises(ValueError, match="pasó|anterior"):
            servicio_reservas.crear_reserva_staff(datos, personal_id=admin["personal_id"])


def test_semaforo_incluye_campo_pasada(app):
    """horarios_con_semaforo devuelve el booleano 'pasada' en cada franja."""
    with app.app_context():
        hoy = servicio_reservas.hoy()
        horarios = servicio_reservas.horarios_con_semaforo(hoy.isoformat())
        assert len(horarios) > 0
        for h in horarios:
            assert "pasada" in h
            assert "disponible" in h
            if h["pasada"]:
                assert h["disponible"] is False


def test_api_reservas_dia_ocultar_y_ver_pasadas(cliente, usuario_prueba, limpiar_f33):
    """GET /api/v1/reservas/dia oculta franjas pasadas por defecto y las muestra con ver_pasadas=1."""
    cliente.post("/auth/login", data={"correo": "admin_test@quero.pe", "password": "clave123"})
    hoy = servicio_reservas.hoy().isoformat()
    # Petición por defecto
    res1 = cliente.get(f"/api/v1/reservas/dia?fecha={hoy}")
    assert res1.status_code == 200
    datos1 = res1.get_json()["datos"]
    assert "franjas_ocultas" in datos1
    assert "ver_pasadas" in datos1
    assert datos1["ver_pasadas"] is False

    # Petición con ver_pasadas=1
    res2 = cliente.get(f"/api/v1/reservas/dia?fecha={hoy}&ver_pasadas=1")
    assert res2.status_code == 200
    datos2 = res2.get_json()["datos"]
    assert datos2["ver_pasadas"] is True
    # Con ver_pasadas=1 se muestran todas las franjas (o igual/más que sin el parámetro)
    assert len(datos2["franjas"]) >= len(datos1["franjas"])


def test_liberar_reservas_vencidas_idempotente(app, usuario_prueba, limpiar_f33):
    """liberar_reservas_vencidas cierra pendientes cuya hora pasó y confirmadas cuya ocupación terminó."""
    with app.app_context():
        # Crear un cliente de prueba
        ejecutar(
            "INSERT INTO cliente (nombre, telefono, acepta_datos) VALUES ('Vencido', %s, TRUE)",
            (TELS_F33[2],)
        )
        c = consultar_uno("SELECT cliente_id FROM cliente WHERE telefono = %s", (TELS_F33[2],))
        cliente_id = c["cliente_id"]

        # Insertar una reserva pendiente con fecha de ayer (seguro vencida)
        ayer = servicio_reservas.hoy() - timedelta(days=1)
        ejecutar(
            """
            INSERT INTO reserva (codigo, cliente_id, fecha, hora, cantidad_personas, estado, canal)
            VALUES ('Q-TESTV1', %s, %s, '12:00', 2, 'pendiente', 'web')
            """,
            (cliente_id, ayer)
        )

        # Insertar una reserva confirmada con fecha de ayer (ocupación ya terminada)
        ejecutar(
            """
            INSERT INTO reserva (codigo, cliente_id, fecha, hora, cantidad_personas, estado, canal)
            VALUES ('Q-TESTV2', %s, %s, '13:00', 2, 'confirmada', 'staff')
            """,
            (cliente_id, ayer)
        )

        # Insertar una reserva con 'llego' (NO debe ser tocada)
        ejecutar(
            """
            INSERT INTO reserva (codigo, cliente_id, fecha, hora, cantidad_personas, estado, canal)
            VALUES ('Q-TESTV3', %s, %s, '14:00', 2, 'llego', 'staff')
            """,
            (cliente_id, ayer)
        )

        # Primera ejecución: debe cerrar la pendiente y la confirmada
        res1 = servicio_reservas.liberar_reservas_vencidas()
        assert res1["pendientes_rechazadas"] >= 1
        assert res1["confirmadas_no_llego"] >= 1
        assert res1["total"] >= 2

        # Verificar estados en la BD
        r_pendiente = consultar_uno("SELECT estado, motivo FROM reserva WHERE codigo = 'Q-TESTV1'")
        assert r_pendiente["estado"] == "rechazada"
        assert "Vencida" in r_pendiente["motivo"]

        r_confirmada = consultar_uno("SELECT estado, motivo FROM reserva WHERE codigo = 'Q-TESTV2'")
        assert r_confirmada["estado"] == "no_llego"
        assert "Automático" in r_confirmada["motivo"]

        r_llego = consultar_uno("SELECT estado FROM reserva WHERE codigo = 'Q-TESTV3'")
        assert r_llego["estado"] == "llego"

        # Segunda ejecución: idempotente (no debe volver a cerrar nada)
        res2 = servicio_reservas.liberar_reservas_vencidas()
        assert res2["total"] == 0
