"""Pruebas de integración para la Fase 3.5: Carta y pedido en celular."""
import json
import pytest
from app.db import consultar_todos, consultar_uno, ejecutar


def test_pedir_get_renderiza_categorias_y_platos(cliente):
    """Comprueba que GET /pedir responda 200 y contenga la estructura de categorías y complementos."""
    resp = cliente.get("/pedir")
    assert resp.status_code == 200
    assert b"Pedido para recojo" in resp.data
    assert b"barra-categorias-sticky" in resp.data
    assert b"offcanvasPedido" in resp.data
    assert b"Tu Pedido para Recojo" in resp.data


def test_carta_publica_solo_lectura_acordeon(cliente):
    """Comprueba que GET /carta responda 200 y contenga el nuevo diseño de acordeón y botón de pedir."""
    resp = cliente.get("/carta")
    assert resp.status_code == 200
    assert b"Nuestra Carta" in resp.data
    assert b"Hacer pedido para recojo" in resp.data
    assert b"acordeonCartaPublica" in resp.data


def test_post_pedir_crea_pedido_recojo(cliente, app):
    """Verifica que enviar un pedido válido por POST /pedir lo registre en la BD y redirija a su seguimiento.

    Al terminar borra el pedido de prueba para no dejar pedidos falsos en la
    cola real del staff (la base de pruebas es la misma del local).
    """
    with app.app_context():
        plato = consultar_uno("SELECT plato_id, nombre, precio FROM plato WHERE disponible = TRUE AND activo = TRUE LIMIT 1")
        ultimo_antes = consultar_uno("SELECT COALESCE(MAX(pedido_id), 0) AS ultimo FROM pedido")["ultimo"]
    assert plato is not None

    items = [{"plato_id": plato["plato_id"], "cantidad": 2}]
    datos = {
        "nombre": "Cliente Fase 3.5",
        "telefono": "987654321",
        "correo": "cliente35@gmail.com",
        "nota": "Sin picante por favor",
        "acepta_datos": "si",
        "items": json.dumps(items),
        "pagina_web": "" # Honeypot vacío
    }

    try:
        resp = cliente.post("/pedir", data=datos, follow_redirects=False)
        assert resp.status_code == 302
        assert "/pedido/" in resp.headers["Location"]

        # Verificar que el pedido existe en la BD
        with app.app_context():
            pedido = consultar_uno("SELECT pedido_id, tipo, estado FROM pedido WHERE cliente_id IN (SELECT cliente_id FROM cliente WHERE telefono = '987654321') ORDER BY pedido_id DESC LIMIT 1")
        assert pedido is not None
        assert pedido["tipo"] == "recojo"
        assert pedido["estado"] == "pendiente"
    finally:
        # Limpieza: borrar SOLO el pedido que creó esta prueba
        with app.app_context():
            nuevos = consultar_todos(
                "SELECT pedido_id FROM pedido WHERE pedido_id > %s", (ultimo_antes,)
            )
            for fila in nuevos:
                ejecutar("DELETE FROM detalle_pedido WHERE pedido_id = %s", (fila["pedido_id"],))
                ejecutar("DELETE FROM pedido WHERE pedido_id = %s", (fila["pedido_id"],))
            ejecutar(
                "DELETE FROM cliente WHERE telefono = '987654321' "
                "AND NOT EXISTS (SELECT 1 FROM pedido p WHERE p.cliente_id = cliente.cliente_id)"
            )


def test_post_pedir_rechaza_plato_agotado(cliente, app):
    """Comprueba que intentar pedir un plato con disponible = FALSE sea rechazado por el servidor.

    Si la base no tiene ningún plato agotado, esta prueba marca uno temporalmente
    y lo devuelve a disponible al terminar (nunca deja un plato real agotado).
    """
    restaurado = False
    with app.app_context():
        # Buscar o crear un plato agotado
        plato = consultar_uno("SELECT plato_id FROM plato WHERE disponible = FALSE AND activo = TRUE LIMIT 1")
        if not plato:
            plato = consultar_uno("SELECT plato_id FROM plato WHERE activo = TRUE ORDER BY plato_id LIMIT 1")
            ejecutar("UPDATE plato SET disponible = FALSE WHERE plato_id = %s", (plato["plato_id"],), commit=True)
            restaurado = True

    items = [{"plato_id": plato["plato_id"], "cantidad": 1}]
    datos = {
        "nombre": "Cliente Rechazo Agotado",
        "telefono": "987654322",
        "acepta_datos": "si",
        "items": json.dumps(items),
        "pagina_web": ""
    }

    try:
        resp = cliente.post("/pedir", data=datos, follow_redirects=True)
        assert resp.status_code == 200
        assert b"agotado" in resp.data.lower() or b"no est\xc3\xa1 disponible" in resp.data.lower()
    finally:
        with app.app_context():
            if restaurado:
                ejecutar("UPDATE plato SET disponible = TRUE WHERE plato_id = %s", (plato["plato_id"],), commit=True)
            ejecutar(
                "DELETE FROM cliente WHERE telefono = '987654322' "
                "AND NOT EXISTS (SELECT 1 FROM pedido p WHERE p.cliente_id = cliente.cliente_id)"
            )


def test_admin_puede_cambiar_categoria_complemento(cliente, app, usuario_prueba):
    """Comprueba que un administrador pueda alternar el estado es_complemento de una categoría.

    Se verifica con el mensaje flash de la respuesta redirigida. Necesita el
    fixture `usuario_prueba` porque el login exige que `admin_test@quero.pe`
    exista en la tabla `personal`. Al final restaura el valor original para
    que la prueba sea repetible y no deje la base cambiada.
    """
    # Autenticar como admin
    login_resp = cliente.post("/auth/login", data={"correo": "admin_test@quero.pe", "password": "clave123"}, follow_redirects=True)
    assert login_resp.status_code == 200

    with app.app_context():
        cat = consultar_uno("SELECT categoria_id, es_complemento FROM categoria LIMIT 1")
    cat_id = cat["categoria_id"]
    valor_original = bool(cat["es_complemento"])

    try:
        # Marcar como complemento (valor "1")
        resp = cliente.post(f"/staff/carta/categoria/{cat_id}/complemento", data={"es_complemento": "1"}, follow_redirects=True)
        assert resp.status_code == 200
        assert "complemento sugerido" in resp.data.decode("utf-8").lower()

        # Desmarcar como complemento (valor "0")
        resp2 = cliente.post(f"/staff/carta/categoria/{cat_id}/complemento", data={"es_complemento": "0"}, follow_redirects=True)
        assert resp2.status_code == 200
        assert "desmarcada" in resp2.data.decode("utf-8").lower()
    finally:
        with app.app_context():
            ejecutar(
                "UPDATE categoria SET es_complemento = %s WHERE categoria_id = %s",
                (valor_original, cat_id),
                commit=True,
            )
