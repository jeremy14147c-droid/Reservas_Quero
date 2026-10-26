"""Rutas para autenticación del personal: login, logout y cambio de contraseña."""
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_user, logout_user, login_required
from werkzeug.security import check_password_hash, generate_password_hash
from app.db import consultar_uno, ejecutar
from app.auth.usuario import UsuarioStaff, obtener_usuario_actual

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

        if not correo or not password:
            flash("Por favor, ingresa tu correo y contraseña.", "danger")
            return render_template("auth/login.html")

        # Buscar usuario en la base de datos
        fila = consultar_uno(
            "SELECT personal_id, nombre, correo, password_hash, rol, activo, debe_cambiar_clave "
            "FROM personal WHERE lower(correo) = %s",
            (correo,)
        )

        if not fila or not fila["activo"] or not check_password_hash(fila["password_hash"], password):
            flash("Credenciales incorrectas o cuenta inactiva.", "danger")
            return render_template("auth/login.html")

        # Iniciar sesión
        usuario_staff = UsuarioStaff(fila)
        login_user(usuario_staff)

        # Si debe cambiar clave, obligar a ir a la pantalla de cambio
        if usuario_staff.debe_cambiar_clave:
            flash("Por seguridad, debes cambiar tu contraseña antes de continuar.", "warning")
            return redirect(url_for("auth.cambiar_clave"))

        next_page = request.args.get("next")
        flash(f"¡Bienvenido(a), {usuario_staff.nombre}!", "success")
        return redirect(next_page or url_for("publico.inicio"))

    return render_template("auth/login.html")


@auth_bp.route("/logout")
@login_required
def logout():
    """Cierra la sesión del usuario actual."""
    logout_user()
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

        if len(nueva_clave) < 6:
            flash("La nueva contraseña debe tener al menos 6 caracteres.", "danger")
            return render_template("auth/cambiar_clave.html")

        if nueva_clave != confirmar_clave:
            flash("Las contraseñas nuevas no coinciden.", "danger")
            return render_template("auth/cambiar_clave.html")

        # Verificar clave actual en base de datos
        fila = consultar_uno(
            "SELECT password_hash FROM personal WHERE personal_id = %s",
            (usuario.id,)
        )

        if not fila or not check_password_hash(fila["password_hash"], clave_actual):
            flash("La contraseña actual no es correcta.", "danger")
            return render_template("auth/cambiar_clave.html")

        # Actualizar contraseña y quitar bandera debe_cambiar_clave
        nuevo_hash = generate_password_hash(nueva_clave)
        ejecutar(
            "UPDATE personal SET password_hash = %s, debe_cambiar_clave = FALSE WHERE personal_id = %s",
            (nuevo_hash, usuario.id)
        )
        usuario.debe_cambiar_clave = False

        flash("Contraseña actualizada con éxito.", "success")
        return redirect(url_for("publico.inicio"))

    return render_template("auth/cambiar_clave.html")
