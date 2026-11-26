"""Pruebas de integración para la Fase 3.6: Cocina: imprimir y recojo primero."""
import pytest
from app.db import consultar_uno, ejecutar, ejecutar_retornando


def test_orden_cola_y_cocina_con_pedidos_mezclados(cliente, app, usuario_prueba):
    """Verifica que en cocina y en la cola ('en_cocina' y 'listos'),
    los pedidos de recojo aparezcan antes que los locales, incluso si los locales
    entraron antes a preparación."""
    cliente.post("/auth/login", data={"correo": "admin_test@quero.pe", "password": "clave123"})

    ids_creados = []
    cliente_temp_id = None
    with app.app_context():
        # Cliente para el pedido de recojo (exigido por ck_pedido_cliente)
        c_fila = ejecutar_retornando(
            "INSERT INTO cliente (nombre, telefono, acepta_datos) VALUES ('Cliente Recojo Test', '999888777', TRUE) RETURNING cliente_id"
        )
        cliente_temp_id = c_fila["cliente_id"]

        # Obtener un plato para las líneas
        plato = consultar_uno("SELECT plato_id, precio FROM plato WHERE disponible = TRUE AND activo = TRUE LIMIT 1")
        pid = plato["plato_id"]
        precio = plato["precio"]

        # Pedido Local 1 (hace 10 minutos)
        p_loc1 = ejecutar_retornando(
            """
            INSERT INTO pedido (tipo, canal, estado, preparacion_en, mesa_referencia)
            VALUES ('local', 'staff', 'en_preparacion', now() - interval '10 minutes', 'Mesa 1')
            RETURNING pedido_id
            """
        )
        ids_creados.append(p_loc1["pedido_id"])

        # Pedido Local 2 (hace 5 minutos)
        p_loc2 = ejecutar_retornando(
            """
            INSERT INTO pedido (tipo, canal, estado, preparacion_en, mesa_referencia)
            VALUES ('local', 'staff', 'en_preparacion', now() - interval '5 minutes', 'Mesa 2')
            RETURNING pedido_id
            """
        )
        ids_creados.append(p_loc2["pedido_id"])

        # Pedido Recojo (hace 1 minuto - más reciente)
        p_rec = ejecutar_retornando(
            """
            INSERT INTO pedido (cliente_id, tipo, canal, estado, preparacion_en, nota)
            VALUES (%s, 'recojo', 'web', 'en_preparacion', now() - interval '1 minute', 'Para llevar urgente')
            RETURNING pedido_id
            """,
            (cliente_temp_id,)
        )
        ids_creados.append(p_rec["pedido_id"])

        for p_id in ids_creados:
            ejecutar(
                "INSERT INTO detalle_pedido (pedido_id, plato_id, cantidad, precio_venta) VALUES (%s, %s, 1, %s)",
                (p_id, pid, precio),
                commit=True
            )

    try:
        # Verificar API cocina
        resp_cocina = cliente.get("/api/v1/pedidos/cocina")
        assert resp_cocina.status_code == 200
        datos_cocina = resp_cocina.get_json()["datos"]["pedidos"]
        ids_cocina = [p["pedido_id"] for p in datos_cocina if p["pedido_id"] in ids_creados]

        # El recojo debe estar primero a pesar de haber sido preparado después
        assert ids_cocina[0] == p_rec["pedido_id"], f"Se esperaba recojo {p_rec['pedido_id']} primero, pero llegó {ids_cocina}"
        assert ids_cocina[1:] == [p_loc1["pedido_id"], p_loc2["pedido_id"]]

        # Verificar API cola
        resp_cola = cliente.get("/api/v1/pedidos/cola")
        assert resp_cola.status_code == 200
        en_cocina_cola = resp_cola.get_json()["datos"]["en_cocina"]
        ids_cola_cocina = [p["pedido_id"] for p in en_cocina_cola if p["pedido_id"] in ids_creados]
        assert ids_cola_cocina[0] == p_rec["pedido_id"]

    finally:
        with app.app_context():
            for p_id in ids_creados:
                ejecutar("DELETE FROM detalle_pedido WHERE pedido_id = %s", (p_id,))
                ejecutar("DELETE FROM pedido WHERE pedido_id = %s", (p_id,), commit=True)
            if cliente_temp_id:
                ejecutar("DELETE FROM cliente WHERE cliente_id = %s", (cliente_temp_id,), commit=True)


def test_ticket_imprimible_responde_para_pedido_en_cocina(cliente, app, usuario_prueba):
    """Comprueba que /staff/pedido/<id>/ticket responda 200 para un pedido en preparación."""
    cliente.post("/auth/login", data={"correo": "admin_test@quero.pe", "password": "clave123"})

    with app.app_context():
        p = ejecutar_retornando(
            "INSERT INTO pedido (tipo, canal, estado, preparacion_en) VALUES ('local', 'staff', 'en_preparacion', now()) RETURNING pedido_id"
        )
        pid = p["pedido_id"]

    try:
        resp = cliente.get(f"/staff/pedido/{pid}/ticket")
        assert resp.status_code == 200
        assert b"PEDIDO" in resp.data
        assert str(pid).encode("utf-8") in resp.data
    finally:
        with app.app_context():
            ejecutar("DELETE FROM pedido WHERE pedido_id = %s", (pid,), commit=True)


def test_vista_cocina_html_contiene_controles_impresion(cliente, usuario_prueba):
    """Comprueba que la pantalla /staff/cocina contenga la casilla de autoimpresión y su advertencia."""
    cliente.post("/auth/login", data={"correo": "admin_test@quero.pe", "password": "clave123"})
    resp = cliente.get("/staff/cocina")
    assert resp.status_code == 200
    html = resp.get_data(as_text=True)
    assert "Imprimir automáticamente" in html
    assert "Activa la impresión automática en un solo equipo" in html
