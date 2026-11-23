"""Pruebas de la Fase 3.4: identidad visual del cliente.

Comprueban que las páginas públicas usan la plantilla del cliente (sin menú de
staff), que los datos de contacto salen de `config_local` y que Administración
valida los enlaces de marca antes de guardarlos.
"""
import pytest

from app.db import consultar_uno, ejecutar

CAMPOS_CONTACTO = (
    "whatsapp_numero",
    "direccion",
    "maps_url",
    "instagram_url",
    "facebook_url",
    "eslogan",
)


def _login_admin(cliente):
    respuesta = cliente.post(
        "/auth/login",
        data={"correo": "admin_test@quero.pe", "password": "clave123"},
    )
    assert respuesta.status_code == 302


def _datos_config(config, **cambios):
    """Arma el formulario completo de configuración a partir de la fila actual."""
    datos = {
        "nombre_local": config["nombre_local"],
        "aforo_personas": config["aforo_personas"],
        "total_mesas": config["total_mesas"],
        "personas_por_mesa": config["personas_por_mesa"],
        "duracion_1_3_min": config["duracion_1_3_min"],
        "duracion_4_7_min": config["duracion_4_7_min"],
        "duracion_8_mas_min": config["duracion_8_mas_min"],
        "franja_min": config["franja_min"],
        "tolerancia_min": config["tolerancia_min"],
        "umbral_preparacion_min": config["umbral_preparacion_min"],
        "max_reservas_web_por_telefono": config["max_reservas_web_por_telefono"],
        "umbral_alerta_pct": config["umbral_alerta_pct"],
        "hora_apertura": config["hora_apertura"].strftime("%H:%M"),
        "hora_cierre": config["hora_cierre"].strftime("%H:%M"),
        "dias_max_anticipacion": config["dias_max_anticipacion"],
        "anticipacion_min_min": config["anticipacion_min_min"],
        "porcentaje_reservable": config["porcentaje_reservable"],
        "abierto": "abierto" if config["abierto"] else "",
        "yape_numero": config["yape_numero"],
        "yape_titular": config["yape_titular"],
        "mensaje_pago": config["mensaje_pago"],
        "whatsapp_numero": config.get("whatsapp_numero"),
        "direccion": config.get("direccion"),
        "maps_url": config.get("maps_url"),
        "instagram_url": config.get("instagram_url"),
        "facebook_url": config.get("facebook_url"),
        "eslogan": config.get("eslogan"),
    }
    datos.update(cambios)
    return datos


@pytest.fixture
def contacto_temporal(app):
    """Carga datos de contacto de prueba y los restaura al terminar."""
    with app.app_context():
        original = consultar_uno("SELECT * FROM config_local WHERE config_id = 1")
        ejecutar(
            "UPDATE config_local SET whatsapp_numero = %s, direccion = %s, maps_url = %s, "
            "instagram_url = %s, facebook_url = %s, eslogan = %s WHERE config_id = 1",
            (
                "996908138",
                "Av. Inca Garcilaso de la Vega 54, Villa María del Triunfo 15816",
                "https://maps.app.goo.gl/rATMHp75PEziVzCQ8",
                "https://www.instagram.com/quero_gastrobar",
                "https://www.facebook.com/GastrobarPiqueosTragos/",
                "El sabor del mar y lo criollo, en un solo lugar.",
            ),
        )
    yield
    with app.app_context():
        valores = tuple(original.get(campo) for campo in CAMPOS_CONTACTO)
        ejecutar(
            "UPDATE config_local SET whatsapp_numero = %s, direccion = %s, maps_url = %s, "
            "instagram_url = %s, facebook_url = %s, eslogan = %s WHERE config_id = 1",
            valores,
        )


@pytest.mark.parametrize("ruta", ["/", "/carta", "/reservar", "/pedir"])
def test_paginas_publicas_responden_200(cliente, ruta):
    assert cliente.get(ruta).status_code == 200


def test_paginas_publicas_no_muestran_menu_de_staff_aunque_haya_sesion(
    cliente, usuario_prueba
):
    _login_admin(cliente)
    for ruta in ("/", "/carta", "/reservar", "/pedir"):
        html = cliente.get(ruta).get_data(as_text=True)
        assert "Carta Staff" not in html, f"{ruta} muestra el menú de staff"
        assert "Acceso Staff" not in html, f"{ruta} muestra el acceso de staff"
        assert "Sesión de staff" in html, f"{ruta} no avisa de la sesión abierta"
        assert "Volver al panel" in html, f"{ruta} no ofrece volver al panel"


def test_inicio_muestra_identidad_y_datos_del_local(cliente, contacto_temporal):
    html = cliente.get("/").get_data(as_text=True)
    assert "Quero Gastrobar" in html
    assert "El sabor del mar y lo criollo" in html
    assert "Av. Inca Garcilaso de la Vega 54" in html
    assert "Reservar" in html and "Pedir" in html and "Carta" in html


def test_boton_flotante_de_whatsapp_usa_el_numero_del_local(cliente, contacto_temporal):
    html = cliente.get("/").get_data(as_text=True)
    assert "https://wa.me/51996908138" in html
    assert "wa.me/message/" not in html


def test_sin_numero_configurado_no_aparece_boton_de_whatsapp(app, cliente, contacto_temporal):
    with app.app_context():
        ejecutar("UPDATE config_local SET whatsapp_numero = NULL WHERE config_id = 1")
    html = cliente.get("/").get_data(as_text=True)
    assert "wa.me/51" not in html


def test_admin_rechaza_enlace_peligroso_y_no_lo_guarda(app, cliente, usuario_prueba):
    _login_admin(cliente)
    with app.app_context():
        config = consultar_uno("SELECT * FROM config_local WHERE config_id = 1")
    datos = _datos_config(config, instagram_url="javascript:alert(1)")

    respuesta = cliente.post("/admin/config", data=datos, follow_redirects=True)
    html = respuesta.get_data(as_text=True)
    assert "https://" in html  # mensaje de error visible

    with app.app_context():
        despues = consultar_uno("SELECT instagram_url FROM config_local WHERE config_id = 1")
    assert despues["instagram_url"] == config.get("instagram_url")


def test_admin_normaliza_y_guarda_el_whatsapp(app, cliente, usuario_prueba):
    _login_admin(cliente)
    with app.app_context():
        original = consultar_uno("SELECT whatsapp_numero FROM config_local WHERE config_id = 1")
        config = consultar_uno("SELECT * FROM config_local WHERE config_id = 1")
    datos = _datos_config(config, whatsapp_numero="+51 996-908-138")
    try:
        cliente.post("/admin/config", data=datos, follow_redirects=True)
        with app.app_context():
            despues = consultar_uno("SELECT whatsapp_numero FROM config_local WHERE config_id = 1")
        assert despues["whatsapp_numero"] == "996908138"
    finally:
        with app.app_context():
            ejecutar(
                "UPDATE config_local SET whatsapp_numero = %s WHERE config_id = 1",
                (original["whatsapp_numero"],),
            )
