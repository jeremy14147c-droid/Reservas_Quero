"""Rutas públicas para clientes (sin login).
Aquí se piden reservas y se sigue su estado; toda la lógica vive en app/servicios/.
"""
from datetime import timedelta
from flask import Blueprint, render_template, request, redirect, url_for, flash
from app.db import consultar_uno
from app.servicios import carta as servicio_carta
from app.servicios import reservas as servicio_reservas

publico_bp = Blueprint("publico", __name__)


def _config_basica():
    config = consultar_uno("SELECT nombre_local, abierto FROM config_local WHERE config_id = 1")
    return {
        "nombre_local": config["nombre_local"] if config else "Quero Gastrobar",
        "abierto": config["abierto"] if config else True,
    }


@publico_bp.route("/")
def inicio():
    """Página de inicio pública con información básica y accesos a reservar y pedir."""
    config = consultar_uno("SELECT nombre_local, abierto, aforo_personas FROM config_local WHERE config_id = 1")
    nombre_local = config["nombre_local"] if config else "Quero Gastrobar"
    abierto = config["abierto"] if config else True
    return render_template("publico/index.html", nombre_local=nombre_local, abierto=abierto)


@publico_bp.route("/carta")
def carta():
    """Carta pública de platos para clientes, agrupada por categorías activas."""
    carta_datos = servicio_carta.obtener_carta_publica()
    config = consultar_uno("SELECT nombre_local FROM config_local WHERE config_id = 1")
    nombre_local = config["nombre_local"] if config else "Quero Gastrobar"
    return render_template("publico/carta.html", carta=carta_datos, nombre_local=nombre_local)


# ---------------------------------------------------------------- reservar

@publico_bp.route("/reservar", methods=["GET", "POST"])
def reservar():
    """Formulario público de reserva. La hora llena NO se puede enviar (filtro duro de cupo)
    y las validaciones se repiten en el servidor con el servicio de reservas."""
    config = _config_basica()

    # Rango de fechas permitidas: hoy .. hoy + dias_max_anticipacion
    fecha_default = servicio_reservas.hoy()
    config_local = servicio_reservas.obtener_config()
    fecha_max = fecha_default + timedelta(days=config_local["dias_max_anticipacion"])
    fechas_permitidas = []
    fecha_iter = fecha_default
    while fecha_iter <= fecha_max:
        fechas_permitidas.append(fecha_iter.isoformat())
        fecha_iter += timedelta(days=1)

    # Fecha seleccionada (por defecto, hoy). Si es inválida se revierte a hoy.
    fecha_sel = request.values.get("fecha", fecha_default.isoformat())
    if fecha_sel not in fechas_permitidas:
        fecha_sel = fecha_default.isoformat()

    # Franjas con semáforo (disponible / pocas / lleno). NUNCA números de capacidad.
    horarios = servicio_reservas.horarios_con_semaforo(fecha_sel)

    if request.method == "POST":
        # Campo trampa (honeypot): los bots lo rellenan; un humano no lo ve.
        if (request.form.get("pagina_web") or "").strip():
            flash("No se pudo registrar la reserva. Verifica los datos e intenta nuevamente.", "danger")
        else:
            datos = {
                "nombre": request.form.get("nombre"),
                "telefono": request.form.get("telefono"),
                "correo": request.form.get("correo"),
                "fecha": fecha_sel,
                "hora": request.form.get("hora"),
                "personas": request.form.get("personas"),
                "nota": request.form.get("nota"),
                "acepta_datos": request.form.get("acepta_datos"),
            }
            try:
                reserva = servicio_reservas.crear_reserva_web(datos)
                flash(f"¡Tu solicitud fue enviada! Te avisaremos cuando la confirmemos. Código: {reserva['codigo']}", "success")
                return redirect(url_for("publico.reserva_estado", token=reserva["token"]))
            except ValueError as error:
                # Los errores de negocio llegan con un mensaje claro para el cliente
                flash(str(error), "danger")

    return render_template(
        "publico/reservar.html", config=config, horarios=horarios,
        fecha_sel=fecha_sel, fechas_permitidas=fechas_permitidas,
        aforo=config_local["aforo_personas"],
    )


@publico_bp.route("/reserva/<token>")
def reserva_estado(token):
    """Seguimiento público de la reserva por token UUID (se refresca sola)."""
    reserva = servicio_reservas.obtener_reserva_publica(token)
    if not reserva:
        return render_template("errores/404.html"), 404
    config = _config_basica()
    return render_template("publico/reserva_estado.html", reserva=reserva, config=config)
