"""Pruebas de la Fase 2: Reservas (núcleo).
Cubre: transiciones, normalización de teléfono, enlace de WhatsApp, formato del API
del día, forzado de cupo, bloqueo en la web, tope de reservas por teléfono,
cambio de hora pasada la tolerancia y reserva duplicada con mensaje claro.
"""
import secrets
import pytest
from datetime import datetime

from app.db import consultar_uno, ejecutar, ejecutar_retornando
from app.servicios import reservas as servicio_reservas
from app.servicios import clientes as servicio_clientes
from app.servicios.reservas import CupoNoDisponible
from app.utils import normalizar_telefono, enlace_whatsapp

TELS_F2 = ('977777101', '977777102', '977777103')


# ---------------------------------------------------------------- utilidades

@pytest.fixture
def limpiar_reservas_f2(app):
    """Limpia las reservas y clientes de prueba de la Fase 2 después de cada prueba."""
    yield
    with app.app_context():
        ejecutar("DELETE FROM reserva WHERE cliente_id IN "
                 "(SELECT cliente_id FROM cliente WHERE telefono = ANY(%s))", (list(TELS_F2),))
        ejecutar("DELETE FROM cliente WHERE telefono = ANY(%s)", (list(TELS_F2),))


def _insertar_reserva(cliente_id, fecha, hora, personas=2, estado='confirmada',
                      canal='staff', creado_en=None):
    """Prepara un escenario insertando una reserva directo en la base de datos."""
    codigo = "Q-" + "".join(secrets.choice("23456789ABCDEFGHJKLMNPQRSTUVWXYZ") for _ in range(6))
    return ejecutar_retornando(
        """INSERT INTO reserva (codigo, cliente_id, fecha, hora, cantidad_personas,
                                estado, canal, creado_en)
           VALUES (%s, %s, %s, %s, %s, %s, %s, COALESCE(%s, now()))
           RETURNING reserva_id, estado""",
        (codigo, cliente_id, fecha, hora, personas, estado, canal, creado_en)
    )


def _fecha_valida():
    """Fecha dentro del rango permitido (hoy cumple la anticipación)."""
    return servicio_reservas.hoy()


def _codigos_franja(fecha):
    """Horas de inicio de franja del día (ej. ['12:00','12:30',...])."""
    return [f["franja_inicio"].strftime("%H:%M") for f in servicio_reservas.carga_dia(fecha)]


# ---------------------------------------------------------------- teléfono y WhatsApp

def test_normalizacion_telefono():
    assert normalizar_telefono("9 991 234 5") is None         # 8 dígitos: inválido
    assert normalizar_telefono("999123456") == "999123456"    # válido
    assert normalizar_telefono("+51 999123456") == "999123456"  # con prefijo país
    assert normalizar_telefono("21 99123456") is None         # no empieza en 9


def test_enlace_whatsapp_formato():
    enlace = enlace_whatsapp("999123456", "Hola, su reserva está confirmada")
    assert enlace.startswith("https://wa.me/51999123456")
    assert "?text=" in enlace
    assert "%20" in enlace  # el mensaje va codificado para URL
    assert enlace_whatsapp("12345", "hola") is None  # teléfono inválido


# ---------------------------------------------------------------- transiciones

def test_transiciones_validas_e_invalidas(app, limpiar_reservas_f2):
    with app.app_context():
        cliente = servicio_clientes.obtener_o_crear_cliente("Cliente Trans F2", TELS_F2[0])
        fecha = _fecha_valida()
        franjas = _codigos_franja(fecha)
        r = _insertar_reserva(cliente["cliente_id"], fecha, franjas[0], estado='pendiente', canal='web')

        # válido: pendiente -> confirmada
        out = servicio_reservas.transicion_reserva(r["reserva_id"], "confirmada")
        assert out["estado"] == "confirmada"

        # inválido: confirmada -> pendiente
        with pytest.raises(ValueError, match="No se puede pasar"):
            servicio_reservas.transicion_reserva(r["reserva_id"], "pendiente")

        # válido: confirmada -> no_llego (estado final)
        out2 = servicio_reservas.transicion_reserva(r["reserva_id"], "no_llego")
        assert out2["estado"] == "no_llego"

        # inválido: un estado final no cambia
        with pytest.raises(ValueError, match="estado final"):
            servicio_reservas.transicion_reserva(r["reserva_id"], "llego")

        # rechazar exige motivo
        r2 = _insertar_reserva(cliente["cliente_id"], fecha, franjas[1], estado='pendiente', canal='web')
        with pytest.raises(ValueError, match="motivo"):
            servicio_reservas.transicion_reserva(r2["reserva_id"], "rechazada")


# ---------------------------------------------------------------- la web NO reserva hora llena

def test_web_bloqueada_con_hora_llena(app, limpiar_reservas_f2):
    with app.app_context():
        fecha = _fecha_valida()
        # se llena la franja con el aforo completo de config_local (aforo = 0 personas libres)
        config = servicio_reservas.obtener_config()
        cliente_lleno = servicio_clientes.obtener_o_crear_cliente("Cliente Lleno F2", TELS_F2[1])
        franjas = _codigos_franja(fecha)
        _insertar_reserva(cliente_lleno["cliente_id"], fecha, franjas[0],
                          personas=config["aforo_personas"])

        with pytest.raises(CupoNoDisponible):
            servicio_reservas.crear_reserva_web({
                "nombre": "Otro Cliente F2", "telefono": TELS_F2[0],
                "fecha": fecha.isoformat(), "hora": franjas[0], "personas": 2,
                "acepta_datos": "si"
            })


# ---------------------------------------------------------------- el staff fuerza y queda marcada

def test_staff_puede_forzar_y_queda_marcada(app, limpiar_reservas_f2):
    with app.app_context():
        fecha = _fecha_valida()
        # mismo escenario de franja llena según el aforo real de config_local
        config = servicio_reservas.obtener_config()
        cliente_lleno = servicio_clientes.obtener_o_crear_cliente("Cliente Lleno F2b", TELS_F2[1])
        franjas = _codigos_franja(fecha)
        _insertar_reserva(cliente_lleno["cliente_id"], fecha, franjas[0],
                          personas=config["aforo_personas"])

        # Sin forzar: advertencia (no se registra)
        with pytest.raises(CupoNoDisponible):
            servicio_reservas.crear_reserva_staff({
                "nombre": "Cliente Forzado F2", "telefono": TELS_F2[2],
                "fecha": fecha.isoformat(), "hora": franjas[0], "personas": 2
            }, personal_id=None, forzar=False)

        # Forzando: se registra y queda con excede_cupo = TRUE
        forzada = servicio_reservas.crear_reserva_staff({
            "nombre": "Cliente Forzado F2", "telefono": TELS_F2[2],
            "fecha": fecha.isoformat(), "hora": franjas[0], "personas": 2
        }, personal_id=None, forzar=True)
        assert forzada["estado"] == "confirmada"
        fila = consultar_uno("SELECT excede_cupo FROM reserva WHERE reserva_id = %s",
                             (forzada["reserva_id"],))
        assert fila["excede_cupo"] is True


# ---------------------------------------------------------------- tope de reservas web por teléfono

def test_web_rechaza_tope_y_staff_sin_tope(app, limpiar_reservas_f2):
    with app.app_context():
        fecha = _fecha_valida()
        franjas = _codigos_franja(fecha)
        cliente = servicio_clientes.obtener_o_crear_cliente("Cliente Tope F2", TELS_F2[0])
        ahora = datetime.now()

        # dos reservas web creadas hace unos minutos (el tope por defecto es 2 en 24 h)
        for hora in franjas[:2]:
            _insertar_reserva(cliente["cliente_id"], fecha, hora,
                              estado='pendiente', canal='web', creado_en=ahora)

        # la tercera por la web se rechaza con mensaje claro
        with pytest.raises(ValueError, match="24 horas"):
            servicio_reservas.crear_reserva_web({
                "nombre": "Cliente Tope F2", "telefono": TELS_F2[0],
                "fecha": fecha.isoformat(), "hora": franjas[2], "personas": 2,
                "acepta_datos": "si"
            })

        # el staff NO tiene ese tope: la registra igual, nace confirmada
        ok_staff = servicio_reservas.crear_reserva_staff({
            "nombre": "Cliente Tope F2", "telefono": TELS_F2[0],
            "fecha": fecha.isoformat(), "hora": franjas[2], "personas": 2
        }, personal_id=None)
        assert ok_staff["estado"] == "confirmada"


# ---------------------------------------------------------------- cambiar hora pasada de tolerancia

def test_cambiar_hora_pasada_la_tolerancia(app, limpiar_reservas_f2):
    with app.app_context():
        fecha = _fecha_valida()
        cliente = servicio_clientes.obtener_o_crear_cliente("Cliente Hora F2", TELS_F2[0])
        franjas = _codigos_franja(fecha)
        r = _insertar_reserva(cliente["cliente_id"], fecha, franjas[0])  # confirmada

        nueva = franjas[1]
        out = servicio_reservas.cambiar_hora(r["reserva_id"], nueva)
        assert out["hora_anterior"] is not None
        assert out["hora"].strftime("%H:%M") == nueva

        # una vez en 'llego' ya no se puede cambiar su hora
        servicio_reservas.transicion_reserva(r["reserva_id"], "llego")
        with pytest.raises(ValueError, match="confirmada"):
            servicio_reservas.cambiar_hora(r["reserva_id"], franjas[2])


# ---------------------------------------------------------------- reserva duplicada (índice único)

def test_reserva_duplicada_mensaje_claro(app, limpiar_reservas_f2):
    with app.app_context():
        fecha = _fecha_valida()
        cliente = servicio_clientes.obtener_o_crear_cliente("Cliente Duplicado F2", TELS_F2[0])
        franjas = _codigos_franja(fecha)
        _insertar_reserva(cliente["cliente_id"], fecha, franjas[0], estado='pendiente', canal='web')

        with pytest.raises(ValueError, match="ya tiene una reserva activa"):
            servicio_reservas.crear_reserva_web({
                "nombre": "Cliente Duplicado F2", "telefono": TELS_F2[0],
                "fecha": fecha.isoformat(), "hora": franjas[0], "personas": 2,
                "acepta_datos": "si"
            })


# ---------------------------------------------------------------- API de la pizarra del día

def test_api_reservas_dia_formato(cliente, usuario_prueba):
    cliente.post("/auth/login", data={"correo": "admin_test@quero.pe", "password": "clave123"})
    resp = cliente.get("/api/v1/reservas/dia")
    assert resp.status_code == 200
    datos = resp.get_json()["datos"]
    assert "fecha" in datos and "franjas" in datos and "pendientes" in datos
    franja = datos["franjas"][0]
    assert franja["nivel"] in ("ok", "alerta", "excedido")
    assert franja["limita"] in ("personas", "mesas")
    for campo in ("personas_libres", "mesas_libres", "limite_personas", "limite_mesas"):
        assert campo in franja


def test_api_sin_sesion_devuelve_401(cliente):
    resp = cliente.get("/api/v1/reservas/dia")
    assert resp.status_code == 401
    assert resp.get_json()["error"]["codigo"] == "NO_AUTORIZADO"
