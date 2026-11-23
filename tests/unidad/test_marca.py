"""Pruebas unitarias de los datos de contacto y marca del local (Fase 3.4).
Son funciones PURAS: no tocan la base de datos ni Flask.
"""
import pytest

from app.servicios.marca import (
    ESLOGAN_POR_DEFECTO,
    construir_marca,
    validar_url_segura,
    validar_whatsapp,
)


# ---------------------------------------------------------------- WhatsApp

def test_whatsapp_acepta_nueve_digitos_que_empiezan_en_9():
    assert validar_whatsapp("996908138") == "996908138"


def test_whatsapp_limpia_espacios_guiones_y_prefijo_51():
    assert validar_whatsapp("+51 996-908-138") == "996908138"


def test_whatsapp_vacio_devuelve_none():
    assert validar_whatsapp("") is None
    assert validar_whatsapp(None) is None


def test_whatsapp_invalido_lanza_error_claro():
    with pytest.raises(ValueError, match="WhatsApp"):
        validar_whatsapp("12345")
    with pytest.raises(ValueError, match="WhatsApp"):
        validar_whatsapp("896908138")  # no empieza en 9


# ---------------------------------------------------------------- URL de marca

def test_url_https_valida_se_conserva():
    url = "https://maps.app.goo.gl/rATMHp75PEziVzCQ8"
    assert validar_url_segura(url, "enlace del mapa") == url


def test_url_vacia_devuelve_none():
    assert validar_url_segura("", "Instagram") is None
    assert validar_url_segura(None, "Instagram") is None


def test_url_http_se_rechaza_porque_no_es_https():
    with pytest.raises(ValueError, match="Instagram"):
        validar_url_segura("http://instagram.com/quero_gastrobar", "Instagram")


@pytest.mark.parametrize(
    "peligrosa",
    [
        "javascript:alert(1)",
        "data:text/html;base64,PHNjcmlwdD4=",
        "vbscript:msgbox(1)",
        "file:///etc/passwd",
    ],
)
def test_esquemas_peligrosos_se_rechazan(peligrosa):
    with pytest.raises(ValueError, match="Facebook"):
        validar_url_segura(peligrosa, "Facebook")


# ---------------------------------------------------------------- marca para plantillas

def _config_con_contacto(**cambios):
    config = {
        "nombre_local": "Quero Gastrobar",
        "eslogan": "El sabor del mar y lo criollo, en un solo lugar.",
        "abierto": True,
        "hora_apertura": "12:00",
        "hora_cierre": "23:00",
        "whatsapp_numero": "996908138",
        "direccion": "Av. Inca Garcilaso de la Vega 54, Villa MarÃ­a del Triunfo 15816",
        "maps_url": "https://maps.app.goo.gl/rATMHp75PEziVzCQ8",
        "instagram_url": "https://www.instagram.com/quero_gastrobar",
        "facebook_url": "https://www.facebook.com/GastrobarPiqueosTragos/",
    }
    config.update(cambios)
    return config


def test_construir_marca_arma_enlace_wa_me_con_prefijo_51():
    marca = construir_marca(_config_con_contacto())
    assert marca["whatsapp_numero"] == "996908138"
    assert marca["whatsapp_url"].startswith("https://wa.me/51996908138")
    assert marca["telefono_url"] == "tel:+51996908138"


def test_construir_marca_mensaje_por_defecto_se_codifica():
    marca = construir_marca(_config_con_contacto())
    assert "?text=" in marca["whatsapp_url"]
    assert " " not in marca["whatsapp_url"]


def test_sin_numero_no_hay_enlace_de_whatsapp():
    marca = construir_marca(_config_con_contacto(whatsapp_numero=None))
    assert marca["whatsapp_url"] is None
    assert marca["telefono_url"] is None


def test_construir_marca_usa_eslogan_por_defecto_si_falta():
    marca = construir_marca(_config_con_contacto(eslogan=None))
    assert marca["eslogan"] == ESLOGAN_POR_DEFECTO


def test_construir_marca_formatea_el_horario_en_12_horas():
    marca = construir_marca(_config_con_contacto())
    assert marca["horario"] == "12:00 pm a 11:00 pm"
