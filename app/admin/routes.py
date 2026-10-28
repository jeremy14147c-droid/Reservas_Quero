"""Rutas del módulo de administración (exclusivo para rol admin)."""
from flask import Blueprint, render_template, request, redirect, url_for, flash
from app.auth.decoradores import requiere_rol
from app.auth.usuario import obtener_usuario_actual
from app.servicios import configuracion as servicio_config
from app.servicios import personal as servicio_personal

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")


@admin_bp.route("")
@admin_bp.route("/config", methods=["GET", "POST"])
@requiere_rol("admin")
def config():
    """Formulario para consultar y actualizar la configuración operativa del local."""
    if request.method == "POST":
        datos = {
            "nombre_local": request.form.get("nombre_local"),
            "aforo_personas": request.form.get("aforo_personas"),
            "total_mesas": request.form.get("total_mesas"),
            "personas_por_mesa": request.form.get("personas_por_mesa"),
            "duracion_1_3_min": request.form.get("duracion_1_3_min"),
            "duracion_4_7_min": request.form.get("duracion_4_7_min"),
            "duracion_8_mas_min": request.form.get("duracion_8_mas_min"),
            "franja_min": request.form.get("franja_min"),
            "tolerancia_min": request.form.get("tolerancia_min"),
            "umbral_preparacion_min": request.form.get("umbral_preparacion_min"),
            "max_reservas_web_por_telefono": request.form.get("max_reservas_web_por_telefono"),
            "umbral_alerta_pct": request.form.get("umbral_alerta_pct"),
            "hora_apertura": request.form.get("hora_apertura"),
            "hora_cierre": request.form.get("hora_cierre"),
            "dias_max_anticipacion": request.form.get("dias_max_anticipacion"),
            "porcentaje_reservable": request.form.get("porcentaje_reservable"),
            "abierto": "abierto" in request.form,
            "yape_numero": request.form.get("yape_numero"),
            "yape_titular": request.form.get("yape_titular"),
            "mensaje_pago": request.form.get("mensaje_pago")
        }

        try:
            servicio_config.actualizar_config_local(datos)
            flash("Configuración del local actualizada correctamente.", "success")
            return redirect(url_for("admin.config"))
        except ValueError as e:
            flash(str(e), "danger")
        except Exception:
            flash("Ocurrió un error inesperado al guardar la configuración.", "danger")

    config_actual = servicio_config.obtener_config_local()
    return render_template("admin/config.html", config=config_actual)


@admin_bp.route("/personal")
@requiere_rol("admin")
def personal():
    """Listado y gestión del personal del restaurante."""
    lista = servicio_personal.listar_personal()
    usuario_actual = obtener_usuario_actual()
    return render_template("admin/personal.html", personal=lista, usuario_actual=usuario_actual)


@admin_bp.route("/personal/crear", methods=["POST"])
@requiere_rol("admin")
def crear_personal():
    """Crea un nuevo usuario de staff con contraseña inicial obligatoria a cambiar."""
    nombre = request.form.get("nombre")
    correo = request.form.get("correo")
    rol = request.form.get("rol")
    password = request.form.get("password")

    try:
        nuevo = servicio_personal.crear_personal(nombre, correo, rol, password)
        flash(f"Colaborador {nuevo['nombre']} registrado exitosamente (deberá cambiar su clave al ingresar).", "success")
    except ValueError as e:
        flash(str(e), "danger")
    except Exception:
        flash("Ocurrió un error al registrar al colaborador.", "danger")

    return redirect(url_for("admin.personal"))


@admin_bp.route("/personal/<int:personal_id>/estado", methods=["POST"])
@requiere_rol("admin")
def cambiar_estado_personal(personal_id):
    """Activa o desactiva la cuenta de un trabajador."""
    usuario_actual = obtener_usuario_actual()
    activo = request.form.get("activo") == "true"

    try:
        servicio_personal.cambiar_estado_personal(personal_id, activo, usuario_actual.id)
        estado_texto = "activada" if activo else "desactivada"
        flash(f"Cuenta de usuario {estado_texto} correctamente.", "info")
    except ValueError as e:
        flash(str(e), "danger")
    except Exception:
        flash("Ocurrió un error al cambiar el estado del usuario.", "danger")

    return redirect(url_for("admin.personal"))


@admin_bp.route("/personal/<int:personal_id>/restablecer-clave", methods=["POST"])
@requiere_rol("admin")
def restablecer_clave_personal(personal_id):
    """Asigna una nueva clave temporal al colaborador."""
    nueva_clave = request.form.get("nueva_clave")

    try:
        servicio_personal.restablecer_password(personal_id, nueva_clave)
        flash("Contraseña restablecida. El colaborador deberá cambiarla al iniciar sesión.", "success")
    except ValueError as e:
        flash(str(e), "danger")
    except Exception:
        flash("Ocurrió un error al restablecer la contraseña.", "danger")

    return redirect(url_for("admin.personal"))
