"""Servicio de negocio para las reservas (toda la lógica vive aquí, no en las rutas).
Reglas de AGENTS.md sección 7:
- Estados: pendiente -> confirmada | rechazada | cancelada ; confirmada -> llego | no_llego | cancelada.
  Los estados finales no cambian.
- La web usa fn_hay_cupo como filtro DURO (la hora llena no se puede enviar).
- El staff NUNCA queda bloqueado por el cupo: se advierte y puede forzar (excede_cupo = TRUE).
- Tolerancia: es solo una alerta visual; el staff decide liberar o cambiar la hora.
- Lo calculado (carga del día, niveles) sale de las funciones SQL a través del DAO, no de Python.

Excepciones que las rutas traducen a mensajes claros (nunca 500):
- ValueError (o CupoNoDisponible, que hereda de él): validación de datos o de negocio.
"""
from datetime import date, datetime, time, timedelta
import psycopg

from app.dao.reserva_dao import ReservaDAO
from app.dao.cliente_dao import ClienteDAO
from app.dao.config_dao import ConfigDAO
from app.utils import normalizar_telefono, generar_codigo_reserva, formato_hora_12h, hoy, ahora_local, ZONA_HORARIA_LIMA
from app.servicios import clientes as servicio_clientes
from app.config import Config

# Instancias por defecto de los DAOs
reserva_dao_default = ReservaDAO()
cliente_dao_default = ClienteDAO()
config_dao_default = ConfigDAO()

# Transiciones permitidas (única fuente de verdad de los estados)
TRANSICIONES_VALIDAS = {
    "pendiente": {"confirmada", "rechazada", "cancelada"},
    "confirmada": {"llego", "no_llego", "cancelada"},
}


class CupoNoDisponible(ValueError):
    """No hay cupo para la reserva en la hora pedida.
    Para la web es un rechazo final; para el staff es una advertencia que permite forzar.
    """


# ---------------------------------------------------------------- configuración

def obtener_config(config_dao=None):
    """Config del local (fila única de config_local)."""
    config_dao = config_dao or config_dao_default
    return config_dao.obtener()


# ---------------------------------------------------------------- validaciones

def validar_fecha(fecha_str, config_dao=None):
    """Convierte el texto de fecha (YYYY-MM-DD) y valida que esté entre hoy y hoy + dias_max_anticipacion."""
    config_dao = config_dao or config_dao_default
    try:
        fecha = datetime.strptime(str(fecha_str), "%Y-%m-%d").date()
    except (ValueError, TypeError):
        raise ValueError("La fecha tiene un formato inválido.")
    config = obtener_config(config_dao)
    maximo = hoy() + timedelta(days=config["dias_max_anticipacion"])
    if fecha < hoy():
        raise ValueError("La fecha no puede ser anterior a hoy. Elige una fecha futura.")
    if fecha > maximo:
        raise ValueError(
            f"Solo se puede reservar hasta {config['dias_max_anticipacion']} día(s) de anticipación."
        )
    return fecha


def validar_personas(personas_str, config_dao=None):
    """Las personas deben ser un entero entre 1 y el aforo del local."""
    config_dao = config_dao or config_dao_default
    try:
        personas = int(personas_str)
    except (ValueError, TypeError):
        raise ValueError("La cantidad de personas es inválida.")
    if personas < 1:
        raise ValueError("La reserva debe ser para al menos 1 persona.")
    config = obtener_config(config_dao)
    if personas > config["aforo_personas"]:
        raise ValueError(f"Como máximo se puede reservar para {config['aforo_personas']} personas (aforo del local).")
    return personas


def validar_hora_en_franjas(fecha, hora_str, dao=None, config_dao=None):
    """La hora debe coincidir con el inicio de una franja del horario del local ese día."""
    dao = dao or reserva_dao_default
    hora = _a_hora(hora_str)
    if hora is None:
        raise ValueError("La hora tiene un formato inválido.")
    franjas = dao.consultar_carga_dia(fecha)
    horarios = [f["franja_inicio"] for f in franjas]
    if not horarios:
        raise ValueError("No hay franjas de atención para esa fecha. Revisa el horario del local.")
    if hora not in horarios:
        raise ValueError("La hora elegida está fuera del horario de atención o no coincide con una franja.")
    return hora


def _a_hora(valor):
    """Convierte 'HH:MM' (texto) a un objeto time, o devuelve el time que ya llegó."""
    if isinstance(valor, time):
        return valor
    try:
        partes = str(valor).strip().split(":")
        return time(int(partes[0]), int(partes[1]))
    except (ValueError, IndexError, TypeError):
        return None


# ---------------------------------------------------------------- cupo (funciones SQL)

def hay_cupo(fecha, hora, personas, excluir_reserva=None, dao=None):
    """Consulta directo a fn_hay_cupo de schema.sql a través del DAO."""
    dao = dao or reserva_dao_default
    return dao.hay_cupo(fecha, hora, personas, excluir_reserva)


def carga_dia(fecha, excluir_reserva=None, dao=None):
    """Consulta directo a fn_carga_dia de schema.sql a través del DAO."""
    dao = dao or reserva_dao_default
    return dao.consultar_carga_dia(fecha, excluir_reserva)


# ---------------------------------------------------------------- semáforo público

def horarios_con_semaforo(fecha, dao=None):
    """Lista de franjas del día con el semáforo del cliente: disponible / pocas / lleno."""
    dao = dao or reserva_dao_default
    resultado = []
    for franja in carga_dia(fecha, dao=dao):
        personas_libres = franja["personas_libres"]
        mesas_libres = franja["mesas_libres"]
        if personas_libres <= 0 or mesas_libres <= 0:
            semaforo = "lleno"
        else:
            limite_personas = franja["limite_personas"] or 0
            ocupacion = 0.0
            if limite_personas:
                ocupacion = max(ocupacion, franja["personas"] / limite_personas * 100)
            semaforo = "pocas" if ocupacion >= (100 - Config.PORC_POCAS) else "disponible"

        resultado.append({
            "hora": franja["franja_inicio"],
            "hora_12h": formato_hora_12h(franja["franja_inicio"]),
            "semaforo": semaforo,
            "disponible": semaforo != "lleno",
        })
    return resultado


# ---------------------------------------------------------------- creación

def _datos_comunes_validados(datos, exigir_consentimiento=True, config_dao=None):
    """Validaciones compartidas por la web y el staff."""
    config_dao = config_dao or config_dao_default
    nombre = (datos.get("nombre") or "").strip()
    if not nombre:
        raise ValueError("El nombre del cliente es obligatorio.")
    if len(nombre) > 100:
        raise ValueError("El nombre es demasiado largo (máximo 100 caracteres).")

    telefono = normalizar_telefono(datos.get("telefono"))
    if not telefono:
        raise ValueError("El teléfono debe ser un número de 9 dígitos que empiece en 9 (celular de Perú).")

    correo = (datos.get("correo") or "").strip() or None
    if correo and ("@" not in correo or len(correo) > 120):
        raise ValueError("El correo es opcional, pero si se escribe debe ser válido.")

    if exigir_consentimiento and not datos.get("acepta_datos"):
        raise ValueError("Se necesita tu consentimiento para tratar los datos de la reserva.")

    fecha = validar_fecha(datos.get("fecha"), config_dao=config_dao)
    personas = validar_personas(datos.get("personas"), config_dao=config_dao)
    return nombre, telefono, correo, fecha, personas


def _generar_codigo_unico(dao=None):
    """Genera un código de reserva (Q-XXXXXX) comprobando que no exista ya."""
    dao = dao or reserva_dao_default
    for _ in range(15):
        codigo = generar_codigo_reserva()
        if not dao.existe_codigo(codigo):
            return codigo
    raise ValueError("No se pudo generar un código de reserva. Intenta nuevamente.")


def _rechazo_por_reserva_duplicada(cliente_id, fecha, hora, dao=None):
    """Mensaje claro si el cliente ya tiene una reserva activa a esa fecha y hora."""
    dao = dao or reserva_dao_default
    existe = dao.existe_activa_cliente(cliente_id, fecha, hora)
    if existe:
        raise ValueError(
            "Este cliente ya tiene una reserva activa para esa fecha y hora. "
            "Puede cambiar la hora desde su tarjeta o cancelarla primero."
        )


def crear_reserva_web(datos, dao=None, cliente_dao=None, config_dao=None):
    """Crea una reserva pedida por la web: nace 'pendiente' y NO cuenta para la capacidad.
    El cupo es un filtro duro y el tope de reservas por teléfono en 24 h se aplica aquí.
    """
    dao = dao or reserva_dao_default
    cliente_dao = cliente_dao or cliente_dao_default
    config_dao = config_dao or config_dao_default

    nombre, telefono, correo, fecha, personas = _datos_comunes_validados(datos, config_dao=config_dao)
    hora = validar_hora_en_franjas(fecha, datos.get("hora"), dao=dao, config_dao=config_dao)

    nota = (datos.get("nota") or "").strip() or None
    if nota and len(nota) > 300:
        raise ValueError("La nota es demasiado larga (máximo 300 caracteres).")

    # Filtro duro de cupo para la web
    if not hay_cupo(fecha, hora, personas, dao=dao):
        raise CupoNoDisponible(
            "Lo sentimos: esa hora ya está llena. Elige otro horario disponible."
        )

    # Reutilizar ficha del cliente (nunca sobrescribe sus datos)
    cliente = servicio_clientes.obtener_o_crear_cliente(nombre, telefono, correo, dao=cliente_dao)

    # Tope de reservas web por teléfono en las últimas 24 h
    config = obtener_config(config_dao)
    contador = servicio_clientes.reservas_web_24h(cliente["cliente_id"], dao=cliente_dao)
    if contador >= config["max_reservas_web_por_telefono"]:
        raise ValueError(
            "Este teléfono ya alcanzó el límite de reservas por la web en las últimas 24 horas. "
            "Llámanos o escríbenos por WhatsApp para atender tu solicitud."
        )

    _rechazo_por_reserva_duplicada(cliente["cliente_id"], fecha, hora, dao=dao)

    try:
        return dao.insertar({
            "codigo": _generar_codigo_unico(dao),
            "cliente_id": cliente["cliente_id"],
            "fecha": fecha,
            "hora": hora,
            "cantidad_personas": personas,
            "estado": "pendiente",
            "canal": "web",
            "nota": nota,
            "excede_cupo": False
        })
    except Exception as e:
        if isinstance(e, psycopg.errors.UniqueViolation) or getattr(e, "pgcode", None) == "23505":
            _rechazo_por_reserva_duplicada(cliente["cliente_id"], fecha, hora, dao=dao)
        raise ValueError("No se pudo registrar la reserva. Verifica los datos e intenta nuevamente.")


def crear_reserva_staff(datos, personal_id, forzar=False, dao=None, cliente_dao=None, config_dao=None):
    """Crea una reserva desde el staff: nace 'confirmada'."""
    dao = dao or reserva_dao_default
    cliente_dao = cliente_dao or cliente_dao_default
    config_dao = config_dao or config_dao_default

    nombre, telefono, correo, fecha, personas = _datos_comunes_validados(datos, exigir_consentimiento=False, config_dao=config_dao)
    hora = validar_hora_en_franjas(fecha, datos.get("hora"), dao=dao, config_dao=config_dao)

    nota = (datos.get("nota") or "").strip() or None
    if nota and len(nota) > 300:
        raise ValueError("La nota es demasiado larga (máximo 300 caracteres).")

    cliente = servicio_clientes.obtener_o_crear_cliente(nombre, telefono, correo, dao=cliente_dao)
    _rechazo_por_reserva_duplicada(cliente["cliente_id"], fecha, hora, dao=dao)

    forzado = False
    if not hay_cupo(fecha, hora, personas, dao=dao):
        if not forzar:
            raise CupoNoDisponible(
                f"ATENCIÓN: no hay cupo para {personas} persona(s) a las {_hora_txt(hora)} el {fecha.isoformat()}. "
                "Puedes forzar la reserva si la dueña lo autoriza."
            )
        forzado = True

    try:
        return dao.insertar({
            "codigo": _generar_codigo_unico(dao),
            "cliente_id": cliente["cliente_id"],
            "fecha": fecha,
            "hora": hora,
            "cantidad_personas": personas,
            "estado": "confirmada",
            "canal": "staff",
            "excede_cupo": forzado,
            "nota": nota,
            "creado_por": personal_id
        })
    except Exception as e:
        if isinstance(e, psycopg.errors.UniqueViolation) or getattr(e, "pgcode", None) == "23505":
            _rechazo_por_reserva_duplicada(cliente["cliente_id"], fecha, hora, dao=dao)
        raise ValueError("No se pudo registrar la reserva. Verifica los datos e intenta nuevamente.")


# ---------------------------------------------------------------- transiciones

def transicion_reserva(reserva_id, nuevo_estado, motivo=None, excede_cupo=None, dao=None):
    """ÚNICA función que cambia el estado de una reserva. Rechaza las transiciones inválidas."""
    dao = dao or reserva_dao_default
    reserva = dao.buscar_por_id(reserva_id)
    if not reserva:
        raise ValueError("La reserva no existe.")

    estado_actual = reserva["estado"]
    if estado_actual not in TRANSICIONES_VALIDAS:
        raise ValueError(
            f"La reserva ya está en el estado final '{estado_actual}'; no se puede cambiar."
        )
    if nuevo_estado not in TRANSICIONES_VALIDAS[estado_actual]:
        raise ValueError(f"No se puede pasar de '{estado_actual}' a '{nuevo_estado}'.")

    motivo_txt = (motivo or "").strip() or None
    if nuevo_estado == "rechazada" and not motivo_txt:
        raise ValueError("Para rechazar la reserva debes indicar el motivo.")
    if motivo_txt and len(motivo_txt) > 200:
        raise ValueError("El motivo es demasiado largo (máximo 200 caracteres).")

    return dao.actualizar_estado(reserva_id, nuevo_estado, motivo=motivo_txt, excede_cupo=excede_cupo)


def confirmar_reserva(reserva_id, forzar=False, dao=None):
    """Confirma una solicitud (la reserva pasa a ocupar capacidad)."""
    dao = dao or reserva_dao_default
    reserva = dao.buscar_por_id(reserva_id)
    if not reserva:
        raise ValueError("La reserva no existe.")

    if reserva["estado"] == "pendiente":
        if not hay_cupo(reserva["fecha"], reserva["hora"], reserva["cantidad_personas"], dao=dao):
            if not forzar:
                raise CupoNoDisponible(
                    "ATENCIÓN: confirmar esta solicitud ya no cabe en el cupo. Puedes forzarla "
                    "y quedará marcada con excede_cupo."
                )
            return transicion_reserva(reserva_id, "confirmada", excede_cupo=True, dao=dao)

    return transicion_reserva(reserva_id, "confirmada", dao=dao)


def rechazar_reserva(reserva_id, motivo, dao=None):
    return transicion_reserva(reserva_id, "rechazada", motivo=motivo, dao=dao)


def cancelar_reserva(reserva_id, motivo=None, dao=None):
    return transicion_reserva(reserva_id, "cancelada", motivo=motivo, dao=dao)


def marcar_llego(reserva_id, dao=None):
    return transicion_reserva(reserva_id, "llego", dao=dao)


def marcar_no_llego(reserva_id, dao=None):
    return transicion_reserva(reserva_id, "no_llego", dao=dao)


# ---------------------------------------------------------------- cambiar hora

def cambiar_hora(reserva_id, nueva_hora_str, forzar=False, dao=None, config_dao=None):
    """Cambia la hora de una reserva CONFIRMADA."""
    dao = dao or reserva_dao_default
    config_dao = config_dao or config_dao_default

    reserva = dao.buscar_por_id(reserva_id)
    if not reserva:
        raise ValueError("La reserva no existe.")
    if reserva["estado"] != "confirmada":
        raise ValueError(
            "Solo se puede cambiar la hora de una reserva confirmada. "
            "Confírmala primero (o crea una reserva nueva si quedó liberada)."
        )

    nueva_hora = validar_hora_en_franjas(reserva["fecha"], nueva_hora_str, dao=dao, config_dao=config_dao)
    if nueva_hora == reserva["hora"]:
        raise ValueError("La hora elegida es la misma que ya tiene la reserva.")

    _rechazo_por_reserva_duplicada(reserva["cliente_id"], reserva["fecha"], nueva_hora, dao=dao)

    forzado = False
    if not hay_cupo(reserva["fecha"], nueva_hora, reserva["cantidad_personas"], excluir_reserva=reserva_id, dao=dao):
        if not forzar:
            raise CupoNoDisponible(
                f"ATENCIÓN: mover la reserva a las {_hora_txt(nueva_hora)} supera el cupo. "
                "Puedes forzar el cambio si la dueña lo autoriza."
            )
        forzado = True

    return dao.actualizar_hora(reserva_id, nueva_hora, hora_anterior=reserva["hora"], excede_cupo=forzado)


# ---------------------------------------------------------------- consultas

def _hora_txt(hora):
    return formato_hora_12h(hora)


def obtener_reserva_detalle(reserva_id, dao=None):
    """Detalle completo de una reserva para el panel."""
    dao = dao or reserva_dao_default
    return dao.obtener_detalle(reserva_id)


def obtener_reserva_publica(token, dao=None):
    """Reserva para la página de seguimiento del cliente."""
    dao = dao or reserva_dao_default
    return dao.buscar_por_token(token)


def obtener_pizarra(fecha, dao=None, config_dao=None, cliente_dao=None):
    """Todo lo que la pizarra digital necesita para un día."""
    dao = dao or reserva_dao_default
    config_dao = config_dao or config_dao_default
    cliente_dao = cliente_dao or cliente_dao_default

    config = obtener_config(config_dao)
    franjas_sql = carga_dia(fecha, dao=dao)
    tolerancia = timedelta(minutes=config["tolerancia_min"])
    ahora = ahora_local()

    reservas_del_dia = dao.listar_del_dia(fecha)

    def _fecha_hora(r):
        fecha_r = r["fecha"]
        fecha_r = fecha_r if isinstance(fecha_r, date) else datetime.strptime(fecha_r, "%Y-%m-%d").date()
        hora_r = r["hora"]
        hora_r = hora_r if isinstance(hora_r, time) else datetime.strptime(str(hora_r)[:5], "%H:%M").time()
        return datetime.combine(fecha_r, hora_r, tzinfo=ZONA_HORARIA_LIMA)

    pendientes = []
    ocupadas = []
    for r in reservas_del_dia:
        if r["estado"] == "pendiente":
            actividad = servicio_clientes.actividad_24h(r.get("cliente_id") or 0, dao=cliente_dao)
            r = dict(r)
            r["actividad_24h"] = bool(
                actividad and (actividad["pedidos_24h"] + actividad["reservas_24h"]) > 0
            )
            pendientes.append(r)
        elif r["estado"] in ("confirmada", "llego"):
            r = dict(r)
            r["atrasada"] = (
                r["estado"] == "confirmada" and ahora > _fecha_hora(r) + tolerancia
            )
            ocupadas.append(r)

    franjas = []
    fecha_dt = fecha if isinstance(fecha, date) else datetime.strptime(str(fecha), "%Y-%m-%d").date()
    for f in franjas_sql:
        ini = datetime.combine(fecha_dt, f["franja_inicio"], tzinfo=ZONA_HORARIA_LIMA)
        fin = datetime.combine(fecha_dt, f["franja_fin"], tzinfo=ZONA_HORARIA_LIMA)
        ocupan_esta = []
        for r in ocupadas:
            inicio_reserva = _fecha_hora(r)
            fin_reserva = inicio_reserva + timedelta(minutes=r["duracion_min"])
            if inicio_reserva < fin and fin_reserva > ini:
                r = dict(r)
                r["continua"] = inicio_reserva < ini
                ocupan_esta.append(r)
        franjas.append({
            "franja_inicio": f["franja_inicio"],
            "franja_fin": f["franja_fin"],
            "reservas_totales": f["reservas"],
            "personas": f["personas"],
            "mesas": f["mesas"],
            "limite_personas": f["limite_personas"],
            "limite_mesas": f["limite_mesas"],
            "personas_libres": f["personas_libres"],
            "mesas_libres": f["mesas_libres"],
            "limita": f["limita"],
            "nivel": f["nivel"],
            "ocupan": ocupan_esta,
        })

    return {
        "fecha": fecha,
        "nombre_local": config["nombre_local"],
        "franjas": franjas,
        "pendientes": pendientes,
    }
