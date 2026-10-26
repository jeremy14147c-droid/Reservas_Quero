"""Helpers para respuestas JSON uniformes según AGENTS.md regla 4b."""
from flask import jsonify


def respuesta_ok(datos=None, codigo_http=200):
    """Devuelve una respuesta JSON exitosa uniforme: {"ok": true, "datos": ...}."""
    cuerpo = {"ok": True}
    if datos is not None:
        cuerpo["datos"] = datos
    return jsonify(cuerpo), codigo_http


def respuesta_error(codigo_error, mensaje, codigo_http=400):
    """Devuelve una respuesta JSON de error uniforme:
    {"ok": false, "error": {"codigo": "...", "mensaje": "..."}}
    """
    return jsonify({
        "ok": False,
        "error": {
            "codigo": codigo_error,
            "mensaje": mensaje
        }
    }), codigo_http
