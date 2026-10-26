"""Decoradores de autorización por rol para el personal."""
from functools import wraps
from flask import request, redirect, url_for, abort, jsonify
from app.auth.usuario import obtener_usuario_actual


def requiere_rol(*roles_permitidos):
    """Decorador que verifica que el usuario esté autenticado y tenga uno de los roles permitidos.
    Usa EXCLUSIVAMENTE obtener_usuario_actual() como exige AGENTS.md regla 4b.
    """
    def decorador(f):
        @wraps(f)
        def envoltura(*args, **kwargs):
            usuario = obtener_usuario_actual()

            # Si no ha iniciado sesión
            if not usuario:
                if request.path.startswith("/api/"):
                    return jsonify({
                        "ok": False,
                        "error": {
                            "codigo": "NO_AUTORIZADO",
                            "mensaje": "Se requiere autenticación para acceder a este recurso."
                        }
                    }), 401
                return redirect(url_for("auth.login", next=request.url))

            # Si debe cambiar clave y está accediendo a otra ruta protegida
            if usuario.debe_cambiar_clave and request.endpoint != "auth.cambiar_clave" and request.endpoint != "auth.logout":
                return redirect(url_for("auth.cambiar_clave"))

            # Verificar si el rol del usuario está permitido
            if roles_permitidos and usuario.rol not in roles_permitidos:
                if request.path.startswith("/api/"):
                    return jsonify({
                        "ok": False,
                        "error": {
                            "codigo": "ACCESO_DENEGADO",
                            "mensaje": "No tienes permisos suficientes para realizar esta acción."
                        }
                    }), 403
                abort(403)

            return f(*args, **kwargs)
        return envoltura
    return decorador
