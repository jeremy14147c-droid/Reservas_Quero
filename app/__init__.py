"""Fábrica de la aplicación Flask (Application Factory)."""
import os

from flask import Flask, render_template, request
from flask_login import LoginManager
from flask_wtf.csrf import CSRFProtect

from app.config import Config, validar_secret_key
from app.db import cerrar_db
from app.auth.usuario import cargar_usuario, obtener_usuario_actual
from app.api.helpers import respuesta_error
from app.servicios import configuracion as servicio_configuracion
from app.servicios.marca import construir_marca
from app.utils import formato_hora_12h, formato_fecha_ddmm

# Extensiones globales
login_manager = LoginManager()
csrf = CSRFProtect()


def create_app(config_class=Config):
    """Crea y configura una instancia de la aplicación Flask."""
    app = Flask(__name__)
    app.config.from_object(config_class)

    # H-10: Validar que en producción la clave secreta sea robusta y no la por defecto
    validar_secret_key(app.config.get("SECRET_KEY"), app.config.get("PRODUCCION", False))

    # Configurar ProxyFix solo en producción para leer IP real del cliente tras proxy/Render (H-2)
    if app.config.get("PRODUCCION"):
        from werkzeug.middleware.proxy_fix import ProxyFix
        app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)

    # Inicializar base de datos
    app.teardown_appcontext(cerrar_db)

    # Inicializar LoginManager
    login_manager.init_app(app)
    login_manager.login_view = "auth.login"
    login_manager.login_message = "Por favor, inicia sesión para acceder al panel."
    login_manager.login_message_category = "warning"
    login_manager.user_loader(cargar_usuario)

    # Inicializar protección CSRF
    csrf.init_app(app)

    # Inyectar variables globales a todas las plantillas Jinja2
    @app.context_processor
    def inyectar_contexto():
        # Datos de contacto y marca para las páginas públicas (Fase 3.4).
        # Si la base falla, la web pública se muestra con los textos por defecto.
        try:
            config_local = servicio_configuracion.obtener_config_local()
        except Exception:
            config_local = None
        return {
            "usuario_actual": obtener_usuario_actual(),
            "marca": construir_marca(config_local),
            "logo_existe": os.path.exists(os.path.join(app.static_folder, "img", "logo.png")),
            "utils_hora12": formato_hora_12h,
            "utils_fecha": formato_fecha_ddmm
        }

    # H-6: Cabeceras HTTP de seguridad en cada respuesta
    @app.after_request
    def agregar_cabeceras_seguridad(response):
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        if app.config.get("PRODUCCION"):
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"

        csp = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
            "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://fonts.googleapis.com; "
            "font-src 'self' https://cdn.jsdelivr.net https://fonts.gstatic.com; "
            "img-src 'self' data:; "
            "connect-src 'self';"
        )
        response.headers["Content-Security-Policy"] = csp
        return response

    # Registrar blueprints
    from app.publico import publico_bp
    from app.auth import auth_bp
    from app.api import api_bp
    from app.reservas import reservas_bp
    from app.carta import carta_bp
    from app.admin import admin_bp
    from app.pedidos import pedidos_bp

    app.register_blueprint(publico_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(api_bp)
    app.register_blueprint(reservas_bp)
    app.register_blueprint(carta_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(pedidos_bp)

    # Manejo uniforme de errores (JSON en /api/, HTML en el resto)
    registrar_manejadores_error(app)

    # Bootstrap idempotente: si la base no tiene ningun admin, crear las
    # cuentas por defecto publicadas en USUARIOS_Y_CLAVES.md. No sobrescribe
    # las cuentas que el admin haya creado. Nunca rompe el arranque.
    try:
        with app.app_context():
            from app.db import consultar_uno, ejecutar
            cuentas = [
                ("Admin Quero", "admin@quero.pe",
                 "scrypt:32768:8:1$CUsd8EC3cYmDfv6y$a70eb1f40db259aa1ad52724eb3bef500729926529195e592d60b24de42b3578031e8af7a4cd772263bcb1d159e0ed60ccc0cdc3e0ba3d2286234a44bf686192",
                 "admin"),
                ("Mozo 1", "mozo1@quero.pe",
                 "scrypt:32768:8:1$fWPmtWXkWqcVAl5v$b35bb7e50ade669b707230cf5f7ea0359c4b0fee1709945550a2d78e7d92334c9c9b008700ed159b689fd7ff5fcd72b37369d08bd006cd6a82f30d847e33561d",
                 "empleado"),
            ]
            for nombre, correo, hsh, rol in cuentas:
                ejecutar(
                    "INSERT INTO personal (nombre, correo, password_hash, rol, activo, debe_cambiar_clave) "
                    "SELECT %s, %s, %s, %s, TRUE, FALSE "
                    "WHERE NOT EXISTS (SELECT 1 FROM personal WHERE lower(correo) = %s)",
                    (nombre, correo, hsh, rol, correo.lower()),
                    commit=True,
                )
    except Exception:
        pass

    return app


def registrar_manejadores_error(app):
    """Manejo centralizado de errores HTTP."""

    @app.errorhandler(400)
    def error_bad_request(e):
        if request.path.startswith("/api/"):
            return respuesta_error("PETICION_INVALIDA", "Los datos enviados no son válidos.", 400)
        return render_template("errores/400.html"), 400

    @app.errorhandler(401)
    def error_no_autorizado(e):
        if request.path.startswith("/api/"):
            return respuesta_error("NO_AUTORIZADO", "Se requiere inicio de sesión.", 401)
        return render_template("errores/401.html"), 401

    @app.errorhandler(403)
    def error_prohibido(e):
        if request.path.startswith("/api/"):
            return respuesta_error("ACCESO_DENEGADO", "No tienes permisos para este recurso.", 403)
        return render_template("errores/403.html"), 403

    @app.errorhandler(404)
    def error_no_encontrado(e):
        if request.path.startswith("/api/"):
            return respuesta_error("NO_ENCONTRADO", "El recurso solicitado no existe.", 404)
        return render_template("errores/404.html"), 404

    @app.errorhandler(500)
    def error_servidor(e):
        if request.path.startswith("/api/"):
            return respuesta_error("ERROR_INTERNO", "Ocurrió un error inesperado en el servidor.", 500)
        return render_template("errores/500.html"), 500
