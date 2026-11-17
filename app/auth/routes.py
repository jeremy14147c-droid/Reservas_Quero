"""Rutas para autenticación del personal: login, logout y cambio de contraseña (Fase S1)."""
from datetime import datetime, timedelta, timezone
from flask import Blueprint, render_template, request, redirect, url_for, flash, session, current_app
from flask_login import login_user, logout_user, login_required
from werkzeug.security import check_password_hash, generate_password_hash

from app.db import consultar_uno, consultar_todos, ejecutar
from app.auth.usuario import UsuarioStaff, obtener_usuario_actual
from app.auth.seguridad import (
    destino_seguro,
    debe_bloquear,
    validar_politica_contrasena,
    HASH_FALSO_DUMMY
)
from app.config import Config

auth_bp = Blueprint("auth", __name__, url_prefix="/auth")


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    """Inicio de sesión para personal (admin o empleado)."""
    usuario = obtener_usuario_actual()
    if usuario:
        if usuario.debe_cambiar_clave:
            return redirect(url_for("auth.cambiar_clave"))
        return redirect(url_for("publico.inicio"))

    if request.method == "POST":
        correo = request.form.get("correo", "").strip().lower()
        password = request.form.get("password", "")
        ip = request.remote_addr or "127.0.0.1"

        if not correo or not password:
            flash("Por favor, ingresa tu correo y contraseña.", "danger")
            return render_template("auth/login.html")

        ahora = datetime.now(timezone.utc)
        ventana_min = current_app.config.get("LOGIN_VENTANA_MIN", Config.LOGIN_VENTANA_MIN)
        limite_tiempo = ahora - timedelta(minutes=ventana_min)

        # H-2: Consultar intentos fallidos recientes para correo e IP
        filas_intentos = consultar_todos(
            """
            SELECT creado_en, correo_lower, ip
            FROM intento_login
            WHERE exitoso = FALSE AND creado_en >= %s AND (correo_lower = %s OR ip = %s)
            """,
            (limite_tiempo, correo, ip)
        )
        recientes_correo = [f["creado_en"] for f in filas_intentos if f["correo_lower"] == correo]
        recientes_ip = [f["creado_en"] for f in filas_intentos if f["ip"] == ip]

        bloqueado, motivo = debe_bloquear(
            recientes_correo,
            recientes_ip,
            ahora,
            max_correo=current_app.config.get("LOGIN_MAX_INTENTOS_CORREO", Config.LOGIN_MAX_INTENTOS_CORREO),
            max_ip=current_app.config.get("LOGIN_MAX_INTENTOS_IP", Config.LOGIN_MAX_INTENTOS_IP),
            ventana_minutos=ventana_min
        )

        if bloqueado:
            flash(motivo, "danger")
            return render_template("auth/login.html")

        # Buscar usuario en la base de datos
        fila = consultar_uno(
            """
            SELECT personal_id, nombre, correo, password_hash, rol, activo, debe_cambiar_clave, sesion_version
            FROM personal WHERE lower(correo) = %s
            """,
            (correo,)
        )

        # H-4: Mitigar ataque de tiempo: si usuario no existe o está inactivo, calcular hash igualmente
        if not fila or not fila["activo"]:
            check_password_hash(HASH_FALSO_DUMMY, password)
            credenciales_validas = False
        else:
            credenciales_validas = check_password_hash(fila["password_hash"], password)

        if not credenciales_validas:
            # Registrar intento fallido
            ejecutar(
                "INSERT INTO intento_login (correo_lower, ip, exitoso, creado_en) VALUES (%s, %s, FALSE, %s)",
                (correo, ip, ahora)
            )
            flash("Credenciales incorrectas o cuenta inactiva.", "danger")
            return render_template("auth/login.html")

        # Credenciales correctas: limpiar intentos fallidos de ese correo
        ejecutar("DELETE FROM intento_login WHERE correo_lower = %s", (correo,))
        ejecutar(
            "INSERT INTO intento_login (correo_lower, ip, exitoso, creado_en) VALUES (%s, %s, TRUE, %s)",
            (correo, ip, ahora)
        )

        # Iniciar sesión y guardar sesion_version (H-1)
        usuario_staff = UsuarioStaff(fila)
        login_user(usuario_staff)
        session["sesion_version"] = fila.get("sesion_version", 1)

        # Si debe cambiar clave, obligar a ir a la pantalla de cambio
        if usuario_staff.debe_cambiar_clave:
            flash("Por seguridad, debes cambiar tu contraseña antes de continuar.", "warning")
            return redirect(url_for("auth.cambiar_clave"))

        # H-3: Redirección segura contra open redirect
        next_raw = request.args.get("next")
        next_page = destino_seguro(next_raw)

        flash(f"¡Bienvenido(a), {usuario_staff.nombre}!", "success")
        return redirect(next_page or url_for("publico.inicio"))

    return render_template("auth/login.html")


@auth_bp.route("/logout", methods=["POST"])
@login_required
def logout():
    """Cierra la sesión del usuario actual e invalida sesiones previas (H-1, H-8)."""
    usuario = obtener_usuario_actual()
    if usuario:
        # Incrementar sesion_version en BD para invalidar cookies clonadas
        ejecutar(
            "UPDATE personal SET sesion_version = sesion_version + 1 WHERE personal_id = %s",
            (usuario.id,)
        )
    logout_user()
    session.clear()
    flash("Has cerrado sesión correctamente.", "info")
    return redirect(url_for("publico.inicio"))


@auth_bp.route("/cambiar-clave", methods=["GET", "POST"])
@login_required
def cambiar_clave():
    """Cambio obligatorio o voluntario de contraseña."""
    usuario = obtener_usuario_actual()

    if request.method == "POST":
        clave_actual = request.form.get("clave_actual", "")
        nueva_clave = request.form.get("nueva_clave", "")
        confirmar_clave = request.form.get("confirmar_clave", "")

        if not clave_actual or not nueva_clave or not confirmar_clave:
            flash("Todos los campos son obligatorios.", "danger")
            return render_template("auth/cambiar_clave.html")

        # H-9: Política de contraseñas de al menos 10 caracteres
        valida, err = validar_politica_contrasena(nueva_clave)
        if not valida:
            flash(err, "danger")
            return render_template("auth/cambiar_clave.html")

        if nueva_clave != confirmar_clave:
            flash("Las contraseñas nuevas no coinciden.", "danger")
            return render_template("auth/cambiar_clave.html")

        # Verificar clave actual en base de datos
        fila = consultar_uno(
            "SELECT password_hash, sesion_version FROM personal WHERE personal_id = %s",
            (usuario.id,)
        )

        if not fila or not check_password_hash(fila["password_hash"], clave_actual):
            flash("La contraseña actual no es correcta.", "danger")
            return render_template("auth/cambiar_clave.html")

        # Actualizar contraseña, quitar debe_cambiar_clave e incrementar sesion_version (H-1)
        nuevo_hash = generate_password_hash(nueva_clave)
        nueva_version = fila.get("sesion_version", 1) + 1
        ejecutar(
            """
            UPDATE personal
            SET password_hash = %s, debe_cambiar_clave = FALSE, sesion_version = %s
            WHERE personal_id = %s
            """,
            (nuevo_hash, nueva_version, usuario.id)
        )
        usuario.debe_cambiar_clave = False
        usuario.sesion_version = nueva_version
        session["sesion_version"] = nueva_version

        flash("Contraseña actualizada con éxito.", "success")
        return redirect(url_for("publico.inicio"))

    return render_template("auth/cambiar_clave.html")
