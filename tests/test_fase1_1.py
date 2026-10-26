"""Pruebas para la Fase 1.1: Código de plato, búsqueda exacta y platos con dos precios."""
import pytest
from app.servicios import carta as servicio_carta
from app.db import consultar_uno, ejecutar


def test_busqueda_codigo_exacto_no_trae_parciales(app):
    """Buscar '1' debe devolver ÚNICAMENTE el plato con código 1, sin traer el 10 ni el 11."""
    with app.app_context():
        resultados = servicio_carta.buscar_platos("1")
        assert len(resultados) == 1
        assert resultados[0]["codigo"] == 1
        assert "Personal" in resultados[0]["nombre"]

        # Buscar '10' solo debe traer el plato con código 10
        res_10 = servicio_carta.buscar_platos("10")
        assert len(res_10) == 1
        assert res_10[0]["codigo"] == 10


def test_busqueda_nombre_ignora_mayusculas_y_tildes(app):
    """La búsqueda por texto ignora mayúsculas y acentos (tildes)."""
    with app.app_context():
        # Buscar con minúscula y sin tildes
        res_cevi = servicio_carta.buscar_platos("cevi")
        assert len(res_cevi) >= 4
        for r in res_cevi:
            assert "cevi" in r["nombre"].lower() or "cevi" in r["categoria_nombre"].lower()

        # Buscar con tilde y mayúscula
        res_trio = servicio_carta.buscar_platos("TRÍO")
        assert len(res_trio) >= 1
        nombres = [r["nombre"].lower() for r in res_trio]
        assert any("trío" in n or "trio" in n for n in nombres)


def test_codigo_repetido_se_rechaza_con_mensaje_claro(app):
    """Intentar registrar un código ya asignado debe lanzar ValueError amigable."""
    with app.app_context():
        cat = consultar_uno("SELECT categoria_id FROM categoria LIMIT 1")
        cat_id = cat["categoria_id"]

        # Código 1 ya está en uso por Ceviche de Pescado
        with pytest.raises(ValueError, match="El código 1 ya está asignado"):
            servicio_carta.crear_plato(cat_id, "Plato Repetido", 10.00, codigo=1)


def test_dos_platos_sin_codigo_son_validos(app):
    """Múltiples platos pueden crearse con código vacío (None)."""
    with app.app_context():
        cat = consultar_uno("SELECT categoria_id FROM categoria LIMIT 1")
        cat_id = cat["categoria_id"]

        p1 = servicio_carta.crear_plato(cat_id, "Plato Sin Codigo 1", 12.00, codigo=None)
        p2 = servicio_carta.crear_plato(cat_id, "Plato Sin Codigo 2", 14.00, codigo=None)

        assert p1["codigo"] is None
        assert p2["codigo"] is None

        # Limpiar
        ejecutar("DELETE FROM plato WHERE plato_id IN (%s, %s)", (p1["plato_id"], p2["plato_id"]))


def test_plato_desactivado_conserva_codigo(app):
    """Un plato desactivado conserva su código reservado y no permite que otro lo use."""
    with app.app_context():
        cat = consultar_uno("SELECT categoria_id FROM categoria LIMIT 1")
        cat_id = cat["categoria_id"]

        # Crear plato con código 999
        plato_temporal = servicio_carta.crear_plato(cat_id, "Plato Temporal 999", 15.00, codigo=999)

        # Desactivarlo
        servicio_carta.desactivar_plato(plato_temporal["plato_id"])

        # Verificar que en la base de datos conserva el código 999
        p = consultar_uno("SELECT codigo, activo FROM plato WHERE plato_id = %s", (plato_temporal["plato_id"],))
        assert p["activo"] is False
        assert p["codigo"] == 999

        # Intentar crear otro plato con código 999 debe ser rechazado
        with pytest.raises(ValueError, match="El código 999 ya está asignado"):
            servicio_carta.crear_plato(cat_id, "Otro Plato 999", 20.00, codigo=999)

        # Limpiar
        ejecutar("DELETE FROM plato WHERE plato_id = %s", (plato_temporal["plato_id"],))


def test_empleado_no_puede_crear_ni_editar_platos(cliente, usuario_prueba):
    """Un empleado no tiene permisos (403) para crear o editar platos."""
    # Iniciar sesión como empleado
    cliente.post("/auth/login", data={"correo": "empleado_test@quero.pe", "password": "clave123"})
    cliente.post("/auth/cambiar-clave", data={
        "clave_actual": "clave123",
        "nueva_clave": "nuevaClave456",
        "confirmar_clave": "nuevaClave456"
    })

    # Intentar crear plato
    resp_crear = cliente.post("/staff/carta/plato/crear", data={
        "categoria_id": 1,
        "nombre": "Plato No Autorizado",
        "precio": 15.00,
        "codigo": 888
    }, follow_redirects=False)
    assert resp_crear.status_code == 403

    # Intentar editar plato
    resp_editar = cliente.post("/staff/carta/plato/1/editar", data={
        "categoria_id": 1,
        "nombre": "Plato Editado Ilegal",
        "precio": 15.00
    }, follow_redirects=False)
    assert resp_editar.status_code == 403


def test_api_buscar_platos(cliente, usuario_prueba):
    """Verifica que el endpoint GET /api/v1/platos/buscar responda el JSON esperado."""
    cliente.post("/auth/login", data={"correo": "admin_test@quero.pe", "password": "clave123"})

    resp = cliente.get("/api/v1/platos/buscar?q=1")
    assert resp.status_code == 200
    datos = resp.get_json()
    assert datos["ok"] is True
    assert len(datos["datos"]) == 1
    assert datos["datos"][0]["codigo"] == 1
    assert "Personal" in datos["datos"][0]["nombre"]
