"""Pruebas de la Fase 3: Pedidos, cobro y cocina.
Cubre: transiciones válidas e inválidas de transicion_pedido, que no se pague de más,
la regla "cocina solo cuando queda cobrado", la edición de líneas solo en pendiente,
el pedido local que nace en_preparación, validaciones de líneas (plato agotado,
cantidad, cliente y consentimiento) y el formato de las rutas JSON de cola y cocina
(incluido el 401 sin sesión).
"""
import pytest

from app.db import consultar_uno, ejecutar
from app.servicios import pedidos as servicio_pedidos

TELS_F3 = ('955666001', '955666002', '955666003')


@pytest.fixture
def limpiar_pedidos_f3(app):
    """Limpia pedidos, pagos y clientes de prueba de la Fase 3 tras cada prueba."""
    yield
    with app.app_context():
        ejecutar("""DELETE FROM pago WHERE pedido_id IN (
            SELECT p.pedido_id FROM pedido p
            JOIN cliente c ON c.cliente_id = p.cliente_id
            WHERE c.telefono = ANY(%s))""", (list(TELS_F3),))
        ejecutar("""DELETE FROM detalle_pedido WHERE pedido_id IN (
            SELECT p.pedido_id FROM pedido p
            JOIN cliente c ON c.cliente_id = p.cliente_id
            WHERE c.telefono = ANY(%s))""", (list(TELS_F3),))
        ejecutar("""DELETE FROM pedido WHERE cliente_id IN (
            SELECT cliente_id FROM cliente WHERE telefono = ANY(%s))""", (list(TELS_F3),))
        ejecutar("DELETE FROM cliente WHERE telefono = ANY(%s)", (list(TELS_F3),))


def consultar_cliente(telefono):
    return consultar_uno("SELECT cliente_id FROM cliente WHERE telefono = %s", (telefono,))


def personal_que_registra():
    """Un personal activo cualquiera: los pagos siempre llevan confirmado_por (NOT NULL)."""
    fila = consultar_uno("SELECT personal_id FROM personal WHERE activo = TRUE LIMIT 1")
    return fila["personal_id"]


def pedidos_y_plato():
    """Un plato disponible para armar pedidos de prueba."""
    return consultar_uno(
        "SELECT plato_id, precio, nombre FROM plato "
        "WHERE disponible = TRUE AND activo = TRUE ORDER BY plato_id LIMIT 1"
    )


def datos_recojo(plato_id, telefono, nombre="Cliente F3", cantidad=2):
    """Datos válidos de un pedido de recojo (se ajustan en cada prueba según convenga)."""
    return {
        "nombre": nombre,
        "telefono": telefono,
        "correo": "",
        "acepta_datos": "si",
        "items": [{"plato_id": plato_id, "cantidad": cantidad}],
    }


# ---------------------------------------------------------------- transiciones

def test_transiciones_validas_e_invalidas(app, limpiar_pedidos_f3):
    with app.app_context():
        plato = pedidos_y_plato()
        pedido = servicio_pedidos.crear_pedido_recojo_web(
            datos_recojo(plato["plato_id"], TELS_F3[0]))
        pid = pedido["pedido_id"]

        # válido: pendiente -> aceptado (y también se llena aceptado_en)
        fila = servicio_pedidos.transicion_pedido(pid, "aceptado")
        assert fila["estado"] == "aceptado"
        marcado = consultar_uno(
            "SELECT aceptado_en FROM pedido WHERE pedido_id = %s", (pid,))
        assert marcado["aceptado_en"] is not None

        # inválido: de aceptado no se salta directo a listo
        with pytest.raises(ValueError, match="No se puede pasar"):
            servicio_pedidos.transicion_pedido(pid, "listo")

        # inválido: rechazar exige motivo
        ped2 = servicio_pedidos.crear_pedido_recojo_web(
            datos_recojo(plato["plato_id"], TELS_F3[1]))
        with pytest.raises(ValueError, match="motivo"):
            servicio_pedidos.transicion_pedido(ped2["pedido_id"], "rechazado")
        # con motivo sí se rechaza
        out2 = servicio_pedidos.transicion_pedido(
            ped2["pedido_id"], "rechazado", motivo_rechazo="llegamos muy tarde")
        assert out2["estado"] == "rechazado"

        # inválido: los estados finales no cambian (rechazado está final)
        with pytest.raises(ValueError, match="estado final"):
            servicio_pedidos.transicion_pedido(ped2["pedido_id"], "cancelado")


def test_cocina_solo_cuando_queda_cobrado(app, limpiar_pedidos_f3):
    with app.app_context():
        plato = pedidos_y_plato()
        pedido = servicio_pedidos.crear_pedido_recojo_web(
            datos_recojo(plato["plato_id"], TELS_F3[0]))
        pid = pedido["pedido_id"]

        servicio_pedidos.transicion_pedido(pid, "aceptado")

        # a cocina sin cobrar se bloquea
        with pytest.raises(ValueError, match="cobrado"):
            servicio_pedidos.transicion_pedido(pid, "en_preparacion")

        # al registrar el pago completo el pedido pasa SOLO a en_preparacion
        staff = personal_que_registra()
        total = float(consultar_uno(
            "SELECT total FROM v_pedido_resumen WHERE pedido_id = %s", (pid,))["total"])
        resumen = servicio_pedidos.registrar_pago(pid, "yape", total, "REF1", staff)
        assert resumen["cobrado"] is True
        assert resumen["estado"] == "en_preparacion"

        # y el detalle queda fijo: ya no se puede editar
        with pytest.raises(ValueError, match="pendiente"):
            servicio_pedidos.actualizar_lineas(
                pid, datos_recojo(plato["plato_id"], TELS_F3[0])["items"])


def test_no_se_puede_pagar_de_mas(app, limpiar_pedidos_f3):
    with app.app_context():
        plato = pedidos_y_plato()
        pedido = servicio_pedidos.crear_pedido_recojo_web(
            datos_recojo(plato["plato_id"], TELS_F3[2]))
        pid = pedido["pedido_id"]
        servicio_pedidos.transicion_pedido(pid, "aceptado")

        total = float(servicio_pedidos.obtener_resumen(pid)["total"])
        staff = personal_que_registra()

        # pagar de más se rechaza (el saldo no alcanza)
        with pytest.raises(ValueError, match="pagar de más"):
            servicio_pedidos.registrar_pago(pid, "yape", total + 5, "REF", staff)

        # pago parcial: sigue 'aceptado' y sin cobrar (el staff muestra el saldo)
        resumen = servicio_pedidos.registrar_pago(pid, "yape", round(total / 2, 2), "REF", staff)
        assert resumen["cobrado"] is False
        assert resumen["estado"] == "aceptado"

        # el pago del resto completa el cobro: entra directo a cocina
        saldo = float(resumen["total"]) - float(resumen["pagado"])
        resumen2 = servicio_pedidos.registrar_pago(pid, "efectivo", saldo, "", staff)
        assert resumen2["cobrado"] is True
        assert resumen2["estado"] == "en_preparacion"


def test_resumen_y_pedido_local_staff(app, limpiar_pedidos_f3):
    with app.app_context():
        plato = pedidos_y_plato()
        precio = float(plato["precio"])
        pedido = servicio_pedidos.crear_pedido_recojo_web(
            datos_recojo(plato["plato_id"], TELS_F3[0], cantidad=3))
        pid = pedido["pedido_id"]

        # v_pedido_resumen: lo calculado nunca se guarda (sale de la vista)
        resumen = consultar_uno(
            "SELECT total, pagado, cobrado FROM v_pedido_resumen WHERE pedido_id = %s", (pid,))
        assert abs(float(resumen["total"]) - precio * 3) < 0.01
        assert float(resumen["pagado"]) == 0.0
        assert resumen["cobrado"] is False

        # pedido en local del staff: nace en_preparacion (cocina desde ya)
        pedido_local = servicio_pedidos.crear_pedido_local_staff(
            {"nombre": "", "telefono": "", "mesa_referencia": "Mesa 2", "nota": "",
             "items": [{"plato_id": plato["plato_id"], "cantidad": 1}]}, personal_id=None)

        fila = consultar_uno(
            "SELECT estado, preparacion_en FROM pedido WHERE pedido_id = %s",
            (pedido_local["pedido_id"],))
        assert fila["estado"] == "en_preparacion"
        assert fila["preparacion_en"] is not None

        # transición inválida: en_preparacion no vuelve a aceptado
        with pytest.raises(ValueError, match="No se puede pasar"):
            servicio_pedidos.transicion_pedido(pedido_local["pedido_id"], "aceptado")


# ---------------------------------------------------------------- validaciones de líneas

def test_lineas_plato_agotado_y_cantidad(app, limpiar_pedidos_f3):
    with app.app_context():
        plato = pedidos_y_plato()
        try:
            # agotar el plato y crear el pedido se rechaza
            ejecutar("UPDATE plato SET disponible = FALSE WHERE plato_id = %s",
                     (plato["plato_id"],))
            with pytest.raises(ValueError, match="agotado"):
                servicio_pedidos.crear_pedido_recojo_web(
                    datos_recojo(plato["plato_id"], TELS_F3[0]))
        finally:
            ejecutar("UPDATE plato SET disponible = TRUE WHERE plato_id = %s",
                     (plato["plato_id"],))

        # cantidad 0 se rechaza
        with pytest.raises(ValueError, match="cantidad"):
            servicio_pedidos.crear_pedido_recojo_web(
                datos_recojo(plato["plato_id"], TELS_F3[0], cantidad=0))

        # plato inexistente se rechaza
        with pytest.raises(ValueError):
            servicio_pedidos.crear_pedido_recojo_web(
                datos_recojo(999999, TELS_F3[0]))


def test_recojo_por_la_web_exige_cliente(app, limpiar_pedidos_f3):
    with app.app_context():
        plato = pedidos_y_plato()

        # nombre vacío
        with pytest.raises(ValueError, match="obligatorio"):
            datos = datos_recojo(plato["plato_id"], TELS_F3[0])
            datos["nombre"] = ""
            servicio_pedidos.crear_pedido_recojo_web(datos)

        # teléfono inválido (no empieza en 9 y tiene 9 dígitos)
        with pytest.raises(ValueError, match="teléfono"):
            servicio_pedidos.crear_pedido_recojo_web(
                datos_recojo(plato["plato_id"], "299988877"))

        # sin consentimiento de datos
        with pytest.raises(ValueError, match="consentimiento"):
            datos = datos_recojo(plato["plato_id"], TELS_F3[0])
            datos["acepta_datos"] = ""
            servicio_pedidos.crear_pedido_recojo_web(datos)


# ---------------------------------------------------------------- API JSON

def test_api_cola_y_cocina_formato(app, cliente, usuario_prueba):
    cliente.post("/auth/login", data={"correo": "admin_test@quero.pe", "password": "clave123"})

    resp = cliente.get("/api/v1/pedidos/cola")
    assert resp.status_code == 200
    datos = resp.get_json()["datos"]
    for columna in ("pendientes", "por_cobrar", "en_cocina", "listos", "entregados"):
        assert columna in datos
        assert isinstance(datos[columna], list)

    resp2 = cliente.get("/api/v1/pedidos/cocina")
    assert resp2.status_code == 200
    datos2 = resp2.get_json()["datos"]
    assert "pedidos" in datos2 and "umbral_preparacion_min" in datos2
    for pedido in datos2["pedidos"]:
        # cada tarjeta de cocina trae el tiempo transcurrido y si va atrasada
        assert "minutos" in pedido and "atrasado" in pedido


def test_api_sin_sesion_401(app, cliente):
    for url in ("/api/v1/pedidos/cola", "/api/v1/pedidos/cocina"):
        resp = cliente.get(url)
        assert resp.status_code == 401
        assert resp.get_json()["error"]["codigo"] == "NO_AUTORIZADO"


def test_api_pedidos_acciones(app, cliente, usuario_prueba, limpiar_pedidos_f3):
    cliente.post("/auth/login", data={"correo": "admin_test@quero.pe", "password": "clave123"})

    with app.app_context():
        plato = pedidos_y_plato()
        pedido = servicio_pedidos.crear_pedido_recojo_web(
            datos_recojo(plato["plato_id"], TELS_F3[0]))
        pid = pedido["pedido_id"]

    # aceptar por API
    r = cliente.post(f"/api/v1/pedidos/{pid}/aceptar")
    assert r.status_code == 200
    assert r.get_json()["datos"]["estado"] == "aceptado"

    with app.app_context():
        total = float(servicio_pedidos.obtener_resumen(pid)["total"])

    # pagar de más por API: 400 con el mensaje claro del servicio
    r2 = cliente.post(f"/api/v1/pedidos/{pid}/pagar",
                      json={"medio": "yape", "monto": total + 9})
    assert r2.status_code == 400
    assert "pagar de más" in r2.get_json()["error"]["mensaje"]
    assert r2.get_json()["error"]["codigo"] == "ERROR_NEGOCIO"

    # pagar el total: entra directo a cocina
    r3 = cliente.post(f"/api/v1/pedidos/{pid}/pagar", json={"medio": "yape", "monto": total})
    assert r3.status_code == 200
    assert r3.get_json()["datos"]["cobrado"] is True

    # transición inválida vía API: en_preparacion no vuelve a aceptado
    r4 = cliente.post(f"/api/v1/pedidos/{pid}/aceptar")
    assert r4.status_code == 400
    assert r4.get_json()["error"]["codigo"] == "ERROR_NEGOCIO"

    # listo y entregar por API (estados finales)
    r5 = cliente.post(f"/api/v1/pedidos/{pid}/listo")
    assert r5.status_code == 200
    assert r5.get_json()["datos"]["estado"] == "listo"
    r6 = cliente.post(f"/api/v1/pedidos/{pid}/entregar")
    assert r6.status_code == 200
    assert r6.get_json()["datos"]["estado"] == "entregado"

    # pedido local del staff por API: nace en_preparacion
    r7 = cliente.post("/api/v1/pedidos/local", json={
        "nombre": "Cliente Local F3",
        "telefono": TELS_F3[0],
        "mesa_referencia": "Mesa 5",
        "items": [{"plato_id": plato["plato_id"], "cantidad": 1}],
    })
    assert r7.status_code == 201
    local = r7.get_json()["datos"]
    assert local["estado"] == "en_preparacion"

    # limpieza del pedido local por si la fixture de clientes no lo cubre
    with app.app_context():
        ejecutar("DELETE FROM detalle_pedido WHERE pedido_id = %s", (local["pedido_id"],))
        ejecutar("DELETE FROM pedido WHERE pedido_id = %s", (local["pedido_id"],))
