"""Rutas para la gestión interna de la carta por el staff y administración."""
from flask import Blueprint, render_template, request, redirect, url_for, flash
from app.auth.decoradores import requiere_rol
from app.servicios import carta as servicio_carta

carta_bp = Blueprint("carta", __name__, url_prefix="/staff/carta")


@carta_bp.route("")
@requiere_rol("admin", "empleado")
def listar():
    """Vista de gestión de platos para el staff con interruptores de disponibilidad."""
    datos = servicio_carta.obtener_carta_staff()
    return render_template("carta/staff_carta.html", categorias=datos["categorias"], platos=datos["platos"])


@carta_bp.route("/plato/crear", methods=["POST"])
@requiere_rol("admin")
def crear_plato():
    """Crea un nuevo plato (solo rol admin)."""
    categoria_id = request.form.get("categoria_id")
    codigo = request.form.get("codigo")
    nombre = request.form.get("nombre")
    precio = request.form.get("precio")
    descripcion = request.form.get("descripcion")

    try:
        servicio_carta.crear_plato(categoria_id, nombre, precio, descripcion, codigo=codigo)
        flash("Plato creado exitosamente.", "success")
    except ValueError as e:
        flash(str(e), "danger")
    except Exception:
        flash("Ocurrió un error al registrar el plato.", "danger")

    return redirect(url_for("carta.listar"))


@carta_bp.route("/plato/<int:plato_id>/editar", methods=["POST"])
@requiere_rol("admin")
def editar_plato(plato_id):
    """Edita un plato existente (solo rol admin)."""
    categoria_id = request.form.get("categoria_id")
    codigo = request.form.get("codigo")
    nombre = request.form.get("nombre")
    precio = request.form.get("precio")
    descripcion = request.form.get("descripcion")

    try:
        servicio_carta.editar_plato(plato_id, categoria_id, nombre, precio, descripcion, codigo=codigo)
        flash("Plato actualizado exitosamente.", "success")
    except ValueError as e:
        flash(str(e), "danger")
    except Exception:
        flash("Ocurrió un error al actualizar el plato.", "danger")

    return redirect(url_for("carta.listar"))


@carta_bp.route("/plato/<int:plato_id>/desactivar", methods=["POST"])
@requiere_rol("admin")
def desactivar_plato(plato_id):
    """Desactiva un plato (solo rol admin, nunca se borra físicamente)."""
    try:
        servicio_carta.desactivar_plato(plato_id)
        flash("Plato desactivado de la carta.", "info")
    except ValueError as e:
        flash(str(e), "danger")
    except Exception:
        flash("Ocurrió un error al desactivar el plato.", "danger")

    return redirect(url_for("carta.listar"))


@carta_bp.route("/categoria/crear", methods=["POST"])
@requiere_rol("admin")
def crear_categoria():
    """Crea una nueva categoría (solo rol admin)."""
    nombre = request.form.get("nombre")
    orden = request.form.get("orden", 0)
    es_complemento = bool(request.form.get("es_complemento"))

    try:
        servicio_carta.crear_categoria(nombre, orden, es_complemento=es_complemento)
        flash("Categoría creada exitosamente.", "success")
    except ValueError as e:
        flash(str(e), "danger")
    except Exception:
        flash("Ocurrió un error al registrar la categoría.", "danger")

    return redirect(url_for("carta.listar"))


@carta_bp.route("/categoria/<int:categoria_id>/complemento", methods=["POST"])
@requiere_rol("admin")
def cambiar_complemento(categoria_id):
    """Cambia si una categoría se sugiere como complemento al armar pedidos (solo admin)."""
    es_comp = request.form.get("es_complemento") == "1" or request.form.get("es_complemento") == "true"
    try:
        cat = servicio_carta.cambiar_categoria_complemento(categoria_id, es_comp)
        estado_txt = "marcada como complemento sugerido" if cat["es_complemento"] else "desmarcada de complementos"
        flash(f"Categoría '{cat['nombre']}' {estado_txt}.", "success")
    except ValueError as e:
        flash(str(e), "danger")
    except Exception:
        flash("Ocurrió un error al actualizar la categoría.", "danger")

    return redirect(url_for("carta.listar"))
