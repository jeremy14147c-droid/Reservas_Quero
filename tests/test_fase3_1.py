"""Pruebas de la Fase 3.1: arreglos urgentes.
- que /static/js/main.js defina esc() UNA sola vez (y que las otras páginas no la copien)
- que crear un pedido local SIN mesa funcione
- que /api/v1/platos/buscar devuelva resultados por nombre y por código exacto
"""
import pytest

from app.db import consultar_uno, ejecutar
from app.servicios import pedidos as servicio_pedidos

TEL_F31 = '955771001'


@pytest.fixture
def limpiar_f31(app):
    """Limpia los datos de prueba de la Fase 3.1."""
    yield
    with app.app_context():
        ejecutar("""DELETE FROM pago WHERE pedido_id IN (
            SELECT p.pedido_id FROM pedido p
            JOIN cliente c ON c.cliente_id = p.cliente_id
            WHERE c.telefono = %s)""", (TEL_F31,))
        ejecutar("""DELETE FROM detalle_pedido WHERE pedido_id IN (
            SELECT p.pedido_id FROM pedido p
            JOIN cliente c ON c.cliente_id = p.cliente_id
            WHERE c.telefono = %s)""", (TEL_F31,))
        ejecutar("""DELETE FROM pedido WHERE cliente_id IN (
            SELECT cliente_id FROM cliente WHERE telefono = %s)""", (TEL_F31,))
        ejecutar("DELETE FROM cliente WHERE telefono = %s", (TEL_F31,))


def test_main_js_define_esc_una_sola_vez(app):
    with open("app/static/js/main.js", encoding="utf-8") as archivo:
        contenido = archivo.read()
    assert "function esc(" in contenido
    # y las demás páginas ya no tienen su propia copia
    for ruta in ("app/templates/reservas/pizarra.html",
                 "app/templates/pedidos/cocina.html",
                 "app/static/js/js_pedidos.js"):
        with open(ruta, encoding="utf-8") as archivo:
            assert "function esc(" not in archivo.read(), ruta


def test_pedido_local_sin_mesa_y_sin_cliente(app, limpiar_f31):
    with app.app_context():
        plato = consultar_uno(
            "SELECT plato_id FROM plato WHERE disponible = TRUE AND activo = TRUE LIMIT 1")
        # sin cliente y sin mesa: cliente anónimo de la mesa o bar
        pedido = servicio_pedidos.crear_pedido_local_staff({
            "nombre": "", "telefono": "",
            "items": [{"plato_id": plato["plato_id"], "cantidad": 1}],
        }, personal_id=None)
        assert pedido["estado"] == "en_preparacion"

        detalle = servicio_pedidos.obtener_pedido_detalle(pedido["pedido_id"])
        assert detalle["mesa_referencia"] is None   # vacía: no se muestra nunca
        assert detalle["cliente_nombre"] is None

        # con mesa tampoco se exige nada raro (es texto libre opcional)
        pedido2 = servicio_pedidos.crear_pedido_local_staff({
            "nombre": "", "telefono": "", "mesa_referencia": "Barra",
            "items": [{"plato_id": plato["plato_id"], "cantidad": 2}],
        }, personal_id=None)
        detalle2 = servicio_pedidos.obtener_pedido_detalle(pedido2["pedido_id"])
        assert detalle2["mesa_referencia"] == "Barra"


def test_buscar_platos_por_nombre_y_por_codigo(app, cliente, usuario_prueba):
    cliente.post("/auth/login", data={"correo": "admin_test@quero.pe", "password": "clave123"})

    with app.app_context():
        plato = consultar_uno(
            "SELECT plato_id, nombre FROM plato WHERE disponible = TRUE AND activo = TRUE "
            "ORDER BY plato_id LIMIT 1")
        # asegura un código único y temporal para la prueba de número exacto
        ejecutar("UPDATE plato SET codigo = NULL WHERE codigo = 909")
        ejecutar("UPDATE plato SET codigo = 909 WHERE plato_id = %s", (plato["plato_id"],))
        try:
            # por nombre (sin importar mayúsculas ni tildes)
            r = cliente.get("/api/v1/platos/buscar?q=" + plato["nombre"][:10])
            assert r.status_code == 200
            datos = r.get_json()["datos"]
            assert any(p["id"] == plato["plato_id"] for p in datos)

            # por número: coincidencia EXACTA (909 no trae al 9 ni al 910)
            r2 = cliente.get("/api/v1/platos/buscar?q=909")
            datos2 = r2.get_json()["datos"]
            assert len(datos2) == 1
            assert datos2[0]["id"] == plato["plato_id"]
            assert datos2[0]["codigo"] == 909
        finally:
            ejecutar("UPDATE plato SET codigo = NULL WHERE codigo = 909")
