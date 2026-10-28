"""Pruebas de la Fase 3.2: duración de estadía por tamaño del grupo + pizarra clara.
- fn_duracion_estadia devuelve 30/60/90 según el grupo (límites 1, 3, 4, 7, 8, 12, 13)
- fn_hay_cupo mezcla grupos de distintos tamaños a la misma hora
- fn_carga_dia: 8 pax llena 3 franjas, 5 pax llena 2, 2 pax llena 1
- La API del día incluye "hasta" y conserva todos los campos anteriores
- Configuración valida las 3 duraciones (enteros > 0, múltiplos de 5)
"""
from datetime import date, timedelta

import pytest

from app.db import consultar_todos, consultar_uno, ejecutar
from app.servicios import configuracion as servicio_config
from app.servicios import reservas as servicio_reservas

# Teléfonos únicos de la fase 3.2 (9 dígitos que empiezan en 9)
TELS_F32 = ["955772001", "955772002", "955772003", "955772004"]


@pytest.fixture
def limpiar_f32(app):
    """Limpia las reservas y clientes de prueba de la Fase 3.2."""
    yield
    with app.app_context():
        ejecutar(
            "DELETE FROM reserva WHERE cliente_id IN "
            "(SELECT cliente_id FROM cliente WHERE telefono = ANY(%s))",
            (TELS_F32,)
        )
        ejecutar("DELETE FROM cliente WHERE telefono = ANY(%s)", (TELS_F32,))
        # por si un test alteró la config
        ejecutar(
            "UPDATE config_local SET duracion_1_3_min = 30, duracion_4_7_min = 60, duracion_8_mas_min = 90 "
            "WHERE config_id = 1"
        )


def _fecha_futura():
    """Fecha de prueba dentro del rango de anticipación permitido (hoy + 1)."""
    return date.today() + timedelta(days=1)


def test_fn_duracion_estadia_por_tamano(app, limpiar_f32):
    """1 y 3 personas -> 30; 4 y 7 -> 60; 8 o más -> 90 (config por defecto)."""
    with app.app_context():
        esperado = {1: 30, 3: 30, 4: 60, 7: 60, 8: 90, 12: 90, 13: 90}
        # llamar a la MISMA función SQL de schema.sql
        filas = consultar_todos(
            "SELECT p.personas, fn_duracion_estadia(p.personas) AS dur "
            "FROM (VALUES (1),(3),(4),(7),(8),(12),(13)) AS p(personas)"
        )
        for fila in filas:
            assert fila["dur"] == esperado[fila["personas"]], fila["personas"]


def test_fn_hay_cupo_grupos_mixtos_misma_hora(app, limpiar_f32):
    """Un salón chico mezcla grupos 2, 5 y grupos nuevos de 4 (cabe) y de 10 (no cabe por mesas)."""
    with app.app_context():
        # encoger el salón temporalmente para que las mezclas se noten
        original = consultar_uno(
            "SELECT aforo_personas, total_mesas, personas_por_mesa FROM config_local WHERE config_id = 1")
        try:
            ejecutar(
                "UPDATE config_local SET aforo_personas = 20, total_mesas = 5, personas_por_mesa = 4 "
                "WHERE config_id = 1")
            fecha = _fecha_futura()
            hora = "19:00"
            # un grupo de 2 (1 mesa) y uno de 5 (2 mesas): 3 personas en 3 mesas...
            servicio_reservas.crear_reserva_staff(
                {"nombre": "F32 A", "telefono": TELS_F32[0], "fecha": fecha, "hora": hora,
                 "personas": 2}, personal_id=None)
            servicio_reservas.crear_reserva_staff(
                {"nombre": "F32 B", "telefono": TELS_F32[1], "fecha": fecha, "hora": hora,
                 "personas": 5}, personal_id=None)

            # personas: 2+5+4 = 11 (<= 20) ... pero mesas: 1 + 2 + 1 = 4 (<= 5): CABE
            assert servicio_reservas.hay_cupo(fecha, hora, 4) is True
            # personas: 2+5+10 = 17 (<= 20) ... mesas: 1 + 2 + 3 = 6 (> 5): NO cabe
            assert servicio_reservas.hay_cupo(fecha, hora, 10) is False
        finally:
            ejecutar(
                "UPDATE config_local SET aforo_personas = %s, total_mesas = %s, personas_por_mesa = %s "
                "WHERE config_id = 1",
                (original["aforo_personas"], original["total_mesas"], original["personas_por_mesa"]))


def test_fn_carga_dia_franjas_por_tamano(app, limpiar_f32):
    """8 pax ocupan 3 franjas (90 min), 5 pax ocupan 2 (60) y 2 pax ocupan 1 (30)."""
    with app.app_context():
        fecha = _fecha_futura()
        # horas separadas para que las estadías no se solapen entre sí
        servicio_reservas.crear_reserva_staff(
            {"nombre": "F32 Grande", "telefono": TELS_F32[0], "fecha": fecha,
             "hora": "19:00", "personas": 8}, personal_id=None)
        servicio_reservas.crear_reserva_staff(
            {"nombre": "F32 Medio", "telefono": TELS_F32[1], "fecha": fecha,
             "hora": "20:30", "personas": 5}, personal_id=None)
        servicio_reservas.crear_reserva_staff(
            {"nombre": "F32 Chico", "telefono": TELS_F32[2], "fecha": fecha,
             "hora": "21:30", "personas": 2}, personal_id=None)

        carga = servicio_reservas.carga_dia(fecha)
        personas_por_inicio = {f["franja_inicio"].strftime("%H:%M"): f["personas"] for f in carga}
        # 90 min = 3 franjas de 30
        assert personas_por_inicio["19:00"] == 8
        assert personas_por_inicio["19:30"] == 8
        assert personas_por_inicio["20:00"] == 8
        # 60 min = 2 franjas
        assert personas_por_inicio["20:30"] == 5
        assert personas_por_inicio["21:00"] == 5
        # 30 min = 1 franja
        assert personas_por_inicio["21:30"] == 2
        # y ya no se arrastra a las franjas siguientes
        assert personas_por_inicio["22:00"] == 0


def test_api_dia_incluye_hasta_y_conserva_campos(cliente, usuario_prueba, limpiar_f32):
    """La pizarra JSON trae 'hasta' (hora + fn_duracion_estadia) sin perder campos previos."""
    cliente.post("/auth/login", data={"correo": "admin_test@quero.pe", "password": "clave123"})
    with cliente.application.app_context():
        fecha = _fecha_futura()
        servicio_reservas.crear_reserva_staff(
            {"nombre": "F32 API", "telefono": TELS_F32[3], "fecha": fecha,
             "hora": "19:00", "personas": 8}, personal_id=None)

    resp = cliente.get("/api/v1/reservas/dia?fecha=" + fecha.isoformat())
    assert resp.status_code == 200
    datos = resp.get_json()["datos"]
    reservas = [r for f in datos["franjas"] for r in f["ocupan"]]
    la_nuestra = [r for r in reservas if r["cliente_nombre"] == "F32 API"]
    assert la_nuestra, "la reserva no aparece en las franjas"
    r = la_nuestra[0]

    # campo NUEVO: 8 pax + 90 min = 19:00 -> 20:30
    assert r["hasta"] == "20:30"
    assert r["duracion_min"] == 90
    # campos ANTERIORES se conservan
    for campo in ("reserva_id", "codigo", "fecha", "hora", "cantidad_personas",
                  "estado", "canal", "excede_cupo", "nota", "cliente_nombre",
                  "cliente_telefono", "cliente_correo"):
        assert campo in r, campo
    assert r["hora"] == "19:00"
    assert r["cantidad_personas"] == 8
    assert r["estado"] == "confirmada"
    # la reserva completa solo se dibuja en su franja de inicio: en las franjas
    # 19:30 y 20:00 aparece con la marca "continua" (2 veces) y luego se acaba
    copias = [x for x in reservas if x["reserva_id"] == r["reserva_id"]]
    assert len(copias) == 3
    assert len([x for x in copias if x["continua"]]) == 2


def test_validacion_duracion_config(app):
    """Las 3 duraciones exigen enteros > 0 y múltiplos de 5 (los errores salen ANTES de tocar la BD)."""
    with app.app_context():
        # base con los datos previos ya válidos para que el error SIEMPRE sea el de la duración probada
        base = {
            "nombre_local": "Test F32",
            "aforo_personas": 20,
            "total_mesas": 5,
            "personas_por_mesa": 4,
            "duracion_1_3_min": 30,
            "duracion_4_7_min": 60,
            "duracion_8_mas_min": 90,
        }
        # cero
        with pytest.raises(ValueError, match="1 a 3"):
            servicio_config.actualizar_config_local({**base, "duracion_1_3_min": 0})
        # negativo
        with pytest.raises(ValueError, match="4 a 7"):
            servicio_config.actualizar_config_local({**base, "duracion_4_7_min": -60})
        # no es número
        with pytest.raises(ValueError, match="8 o más"):
            servicio_config.actualizar_config_local({**base, "duracion_8_mas_min": "abc"})
        # no es múltiplo de 5
        with pytest.raises(ValueError, match="múltiplo de 5"):
            servicio_config.actualizar_config_local(
                {**base, "duracion_1_3_min": 12, "duracion_4_7_min": 60, "duracion_8_mas_min": 90})
        # cada campo se valida por su cuenta
        with pytest.raises(ValueError, match="múltiplo de 5"):
            servicio_config.actualizar_config_local(
                {**base, "duracion_1_3_min": 30, "duracion_4_7_min": 44, "duracion_8_mas_min": 90})
