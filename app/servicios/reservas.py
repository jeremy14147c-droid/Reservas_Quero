"""Servicio de negocio para las reservas (toda la lógica vive aquí, no en las rutas).
Reglas de AGENTS.md sección 7:
- Estados: pendiente -> confirmada | rechazada | cancelada ; confirmada -> llego | no_llego | cancelada.
  Los estados finales no cambian.
- La web usa fn_hay_cupo como filtro DURO (la hora llena no se puede enviar).
- El staff NUNCA queda bloqueado por el cupo: se advierte y puede forzar (excede_cupo = TRUE).
- Tolerancia: es solo una alerta visual; el staff decide liberar o cambiar la hora.
- Lo calculado (carga del día, niveles) sale de las funciones SQL, no de Python.

Excepciones que las rutas traducen a mensajes claros (nunca 500):
- ValueError (o CupoNoDisponible, que hereda de él): validación de datos o de negocio.
"""
import psycopg
from datetime import date, datetime, time, timedelta

from app.db import consultar_todos, consultar_uno, ejecutar, ejecutar_retornando
from app.utils import normalizar_telefono, generar_codigo_reserva, formato_hora_12h
from app.servicios import clientes as servicio_clientes
from app.config import Config

# Transiciones permitidas (única fuente de verdad de los estados)
TRANSICIONES_VALIDAS = {
    "pendiente": {"confirmada", "rechazada", "cancelada"},
    "confirmada": {"llego", "no_llego", "cancelada"},
}


class CupoNoDisponible(ValueError):
    """No hay cupo para la reserva en la hora pedida.
    Para la web es un rechazo final; para el staff es una advertencia que permite forzar.
    """


# ---------------------------------------------------------------- zona horaria
# La app opera en America/Lima. El servidor local corre con esa hora, así que
# usamos la hora local del equipo (datetime.now) para calendarios y tolerancia.


def hoy():
    """Fecha local de hoy (solo se usa como base del calendario público)."""
    return datetime.now().date()


def ahora_local():
    """Fecha y hora local completas (se usa para la alerta de tolerancia)."""
    return datetime.now()


# ---------------------------------------------------------------- configuración

def obtener_config():
    """Config del local (fila única de config_local)."""
    return consultar_uno("SELECT * FROM config_local WHERE config_id = 1")


# ---------------------------------------------------------------- validaciones

def validar_fecha(fecha_str):
    """Convierte el texto de fecha (YYYY-MM-DD) y valida que esté entre hoy y hoy + dias_max_anticipacion."""
    try:
        fecha = datetime.strptime(str(fecha_str), "%Y-%m-%d").date()
    except (ValueError, TypeError):
        raise ValueError("La fecha tiene un formato inválido.")
    config = obtener_config()
    maximo = hoy() + timedelta(days=config["dias_max_anticipacion"])
    if fecha < hoy():
        raise ValueError("La fecha no puede ser anterior a hoy. Elige una fecha futura.")
    if fecha > maximo:
        raise ValueError(
            f"Solo se puede reservar hasta {config['dias_max_anticipacion']} día(s) de anticipación."
        )
    return fecha


def validar_personas(personas_str):
    """Las personas deben ser un entero entre 1 y el aforo del local."""
    try:
        personas = int(personas_str)
    except (ValueError, TypeError):
        raise ValueError("La cantidad de personas es inválida.")
    if personas < 1:
        raise ValueError("La reserva debe ser para al menos 1 persona.")
    config = obtener_config()
    if personas > config["aforo_personas"]:
        raise ValueError(f"Como máximo se puede reservar para {config['aforo_personas']} personas (aforo del local).")
    return personas


def validar_hora_en_franjas(fecha, hora_str):
    """La hora debe coincidir con el inicio de una franja del horario del local ese día."""
    hora = _a_hora(hora_str)
    if hora is None:
        raise ValueError("La hora tiene un formato inválido.")
    franjas = consultar_todos("SELECT franja_inicio FROM fn_carga_dia(%s)", (fecha,))
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

def hay_cupo(fecha, hora, personas, excluir_reserva=None):
    """Consulta directo a fn_hay_cupo de schema.sql (nada de reimplementar la lógica)."""
    fila = consultar_uno(
        "SELECT fn_hay_cupo(%s, %s, %s, %s) AS hay_cupo",
        (fecha, hora, personas, excluir_reserva)
    )
    return bool(fila["hay_cupo"])


def carga_dia(fecha, excluir_reserva=None):
    """Consulta directo a fn_carga_dia de schema.sql (franjas con personas, mesas, nivel)."""
    return consultar_todos("SELECT * FROM fn_carga_dia(%s, %s)", (fecha, excluir_reserva))


# ---------------------------------------------------------------- semáforo público

def horarios_con_semaforo(fecha):
    """Lista de franjas del día con el semáforo del cliente: disponible / pocas / lleno.
    NUNCA se muestran números de capacidad (AGENTS.md sección 7).
      - lleno : ya no cabe nadie (personas_libres <= 0 o mesas_libres <= 0)
      - pocas : la ocupación alcanzó el 100% - PORC_POCAS % (ej. 75% con PORC_POCAS = 25)
      - disponible : el resto
    """
    resultado = []
    for franja in carga_dia(fecha):
        personas_libres = franja["personas_libres"]
        mesas_libres = franja["mesas_libres"]
        if personas_libres <= 0 or mesas_libres <= 0:
            semaforo = "lleno"
        else:
            limite_personas = franja["limite_personas"] or 0
            limite_mesas = franja["limite_mesas"] or 0
            ocupacion = 0.0
            if limite_personas:
                ocupacion = max(ocupacion, franja["personas"] / limite_personas * 100)
            if limite_mesas:
                ocupacion = max(ocupacion, franja["mesas"] / limite_mesas * 100)
            semaforo = "pocas" if ocupacion >= (100 - Config.PORC_POCAS) else "disponible"
        hora = franja["franja_inicio"]
        resultado.append({
            "hora": hora.isoformat("minutes") if isinstance(hora, time) else str(hora),
            "semaforo": semaforo,
        })
    return resultado


# ---------------------------------------------------------------- creación

def _datos_comunes_validados(datos, exigir_consentimiento=True):
    """Validaciones compartidas por la web y el staff. Devuelve (nombre, telefono, correo, fecha, personas).
    El consentimiento es obligatorio SOLO en el formulario público; el staff lo toma presencialmente.
    """
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

    fecha = validar_fecha(datos.get("fecha"))
    personas = validar_personas(datos.get("personas"))
    return nombre, telefono, correo, fecha, personas


def _generar_codigo_unico():
    """Genera un código de reserva (Q-XXXXXX) comprobando que no exista ya."""
    for _ in range(15):
        codigo = generar_codigo_reserva()
        existe = consultar_uno("SELECT 1 FROM reserva WHERE codigo = %s", (codigo,))
        if not existe:
            return codigo
    raise ValueError("No se pudo generar un código de reserva. Intenta nuevamente.")


def _rechazo_por_reserva_duplicada(cliente_id, fecha, hora):
    """Mensaje claro si el cliente ya tiene una reserva activa a esa fecha y hora
    (el índice único ux_reserva_cliente_fecha_hora lo respalda)."""
    existe = consultar_uno(
        """SELECT reserva_id, estado FROM reserva
           WHERE cliente_id = %s AND fecha = %s AND hora = %s
             AND estado IN ('pendiente','confirmada','llego')""",
        (cliente_id, fecha, hora)
    )
    if existe:
        raise ValueError(
            "Este cliente ya tiene una reserva activa para esa fecha y hora. "
            "Puede cambiar la hora desde su tarjeta o cancelarla primero."
        )


def crear_reserva_web(datos):
    """Crea una reserva pedida por la web: nace 'pendiente' y NO cuenta para la capacidad.
    El cupo es un filtro duro y el tope de reservas por teléfono en 24 h se aplica aquí.
    """
    nombre, telefono, correo, fecha, personas = _datos_comunes_validados(datos)
    hora = validar_hora_en_franjas(fecha, datos.get("hora"))

    nota = (datos.get("nota") or "").strip() or None
    if nota and len(nota) > 300:
        raise ValueError("La nota es demasiado larga (máximo 300 caracteres).")

    # Filtro duro de cupo para la web
    if not hay_cupo(fecha, hora, personas):
        raise CupoNoDisponible(
            "Lo sentimos: esa hora ya está llena. Elige otro horario disponible."
        )

    # Reutilizar ficha del cliente (nunca sobrescribe sus datos)
    cliente = servicio_clientes.obtener_o_crear_cliente(nombre, telefono, correo)

    # Tope de reservas web por teléfono en las últimas 24 h
    config = obtener_config()
    contador = servicio_clientes.reservas_web_24h(cliente["cliente_id"])
    if contador >= config["max_reservas_web_por_telefono"]:
        raise ValueError(
            "Este teléfono ya alcanzó el límite de reservas por la web en las últimas 24 horas. "
            "Llámanos o escríbenos por WhatsApp para atender tu solicitud."
        )

    _rechazo_por_reserva_duplicada(cliente["cliente_id"], fecha, hora)

    try:
        return ejecutar_retornando(
            """INSERT INTO reserva (codigo, cliente_id, fecha, hora, cantidad_personas,
                                     estado, canal, nota)
               VALUES (%s, %s, %s, %s, %s, 'pendiente', 'web', %s)
               RETURNING reserva_id, codigo, token, estado, canal, fecha, hora,
                         cantidad_personas, nota""",
            (_generar_codigo_unico(), cliente["cliente_id"], fecha, hora, personas, nota)
        )
    except psycopg.errors.UniqueViolation:
        _rechazo_por_reserva_duplicada(cliente["cliente_id"], fecha, hora)
        raise ValueError("No se pudo registrar la reserva. Verifica los datos e intenta nuevamente.")


def crear_reserva_staff(datos, personal_id, forzar=False):
    """Crea una reserva desde el staff: nace 'confirmada'.
    Si no hay cupo se lanza CupoNoDisponible (advertencia); con forzar=True se registra
    igual y queda marcada con excede_cupo = TRUE (el staff nunca queda bloqueado).
    """
    nombre, telefono, correo, fecha, personas = _datos_comunes_validados(datos, exigir_consentimiento=False)
    hora = validar_hora_en_franjas(fecha, datos.get("hora"))

    nota = (datos.get("nota") or "").strip() or None
    if nota and len(nota) > 300:
        raise ValueError("La nota es demasiado larga (máximo 300 caracteres).")

    cliente = servicio_clientes.obtener_o_crear_cliente(nombre, telefono, correo)
    _rechazo_por_reserva_duplicada(cliente["cliente_id"], fecha, hora)

    forzado = False
    if not hay_cupo(fecha, hora, personas):
        if not forzar:
            # Advertencia para el staff: puede repetir la acción con "forzar"
            raise CupoNoDisponible(
                f"ATENCIÓN: no hay cupo para {personas} persona(s) a las {_hora_txt(hora)} el {fecha.isoformat()}. "
                "Puedes forzar la reserva si la dueña lo autoriza."
            )
        forzado = True

    try:
        return ejecutar_retornando(
            """INSERT INTO reserva (codigo, cliente_id, fecha, hora, cantidad_personas,
                                     estado, canal, excede_cupo, nota, creado_por)
               VALUES (%s, %s, %s, %s, %s, 'confirmada', 'staff', %s, %s, %s)
               RETURNING reserva_id, codigo, estado, canal, fecha, hora, cantidad_personas""",
            (_generar_codigo_unico(), cliente["cliente_id"], fecha, hora, personas,
             forzado, nota, personal_id)
        )
    except psycopg.errors.UniqueViolation:
        _rechazo_por_reserva_duplicada(cliente["cliente_id"], fecha, hora)
        raise ValueError("No se pudo registrar la reserva. Verifica los datos e intenta nuevamente.")


# ---------------------------------------------------------------- transiciones

def transicion_reserva(reserva_id, nuevo_estado, motivo=None, excede_cupo=None):
    """ÚNICA función que cambia el estado de una reserva. Rechaza las transiciones inválidas.
    El motivo es obligatorio al rechazar. excede_cupo permite marcar el forzado al confirmar.
    """
    reserva = consultar_uno(
        "SELECT reserva_id, estado, motivo FROM reserva WHERE reserva_id = %s", (reserva_id,)
    )
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

    campos = ["estado = %s", "motivo = COALESCE(%s, motivo)", "actualizado_en = now()"]
    params = [nuevo_estado, motivo_txt]
    if excede_cupo is not None:
        campos[0] = "estado = %s, excede_cupo = %s"
        params.insert(1, bool(excede_cupo))

    fila = ejecutar_retornando(
        f"""UPDATE reserva SET {', '.join(campos)} WHERE reserva_id = %s
            RETURNING reserva_id, codigo, estado, excede_cupo""",
        (*params, reserva_id)
    )
    return fila


def confirmar_reserva(reserva_id, forzar=False):
    """Confirma una solicitud (la reserva pasa a ocupar capacidad).
    Si ya no cabe, se advierte; con forzar=True se confirma marcando excede_cupo = TRUE.
    """
    reserva = consultar_uno(
        "SELECT reserva_id, estado, fecha, hora, cantidad_personas FROM reserva WHERE reserva_id = %s",
        (reserva_id,)
    )
    if not reserva:
        raise ValueError("La reserva no existe.")

    if reserva["estado"] == "pendiente":
        if not hay_cupo(reserva["fecha"], reserva["hora"], reserva["cantidad_personas"]):
            if not forzar:
                raise CupoNoDisponible(
                    "ATENCIÓN: confirmar esta solicitud ya no cabe en el cupo. Puedes forzarla "
                    "y quedará marcada con excede_cupo."
                )
            return transicion_reserva(reserva_id, "confirmada", excede_cupo=True)

    return transicion_reserva(reserva_id, "confirmada")


def rechazar_reserva(reserva_id, motivo):
    return transicion_reserva(reserva_id, "rechazada", motivo=motivo)


def cancelar_reserva(reserva_id, motivo=None):
    return transicion_reserva(reserva_id, "cancelada", motivo=motivo)


def marcar_llego(reserva_id):
    return transicion_reserva(reserva_id, "llego")


def marcar_no_llego(reserva_id):
    """Liberar la mesa: el cliente no apareció. Es un estado FINAL (si aparece después,
    el staff crea una reserva nueva: el índice único ignora las no_llego)."""
    return transicion_reserva(reserva_id, "no_llego")


# ---------------------------------------------------------------- cambiar hora

def cambiar_hora(reserva_id, nueva_hora_str, forzar=False):
    """Cambia la hora de una reserva CONFIRMADA (en dos toques desde la tarjeta).
    - Guarda la hora previa en hora_anterior (solo el último cambio).
    - Valida con fn_hay_cupo excluyendo la propia reserva.
    - Se permite aunque haya pasado la tolerancia, mientras siga confirmada.
    - Con forzar=True se marca excede_cupo = TRUE (el staff decide).
    """
    reserva = consultar_uno(
        "SELECT reserva_id, estado, fecha, hora, hora_anterior, cantidad_personas, cliente_id FROM reserva WHERE reserva_id = %s",
        (reserva_id,)
    )
    if not reserva:
        raise ValueError("La reserva no existe.")
    if reserva["estado"] != "confirmada":
        raise ValueError(
            "Solo se puede cambiar la hora de una reserva confirmada. "
            "Confírmala primero (o crea una reserva nueva si quedó liberada)."
        )

    nueva_hora = validar_hora_en_franjas(reserva["fecha"], nueva_hora_str)
    if nueva_hora == reserva["hora"]:
        raise ValueError("La hora elegida es la misma que ya tiene la reserva.")

    _rechazo_por_reserva_duplicada(reserva["cliente_id"], reserva["fecha"], nueva_hora)

    forzado = False
    if not hay_cupo(reserva["fecha"], nueva_hora, reserva["cantidad_personas"], excluir_reserva=reserva_id):
        if not forzar:
            raise CupoNoDisponible(
                f"ATENCIÓN: mover la reserva a las {_hora_txt(nueva_hora)} supera el cupo. "
                "Puedes forzar el cambio si la dueña lo autoriza."
            )
        forzado = True

    return ejecutar_retornando(
        """UPDATE reserva
           SET hora = %s, hora_anterior = %s,
               excede_cupo = CASE WHEN %s THEN TRUE ELSE excede_cupo END,
               actualizado_en = now()
           WHERE reserva_id = %s
           RETURNING reserva_id, codigo, fecha, hora, hora_anterior, excede_cupo""",
        (nueva_hora, reserva["hora"], forzado, reserva_id)
    )


# ---------------------------------------------------------------- consultas

def _hora_txt(hora):
    """Hora legible '4:00 pm' para los mensajes."""
    return formato_hora_12h(hora)


def obtener_reserva_detalle(reserva_id):
    """Detalle completo de una reserva para el panel (sin datos sensibles de más)."""
    return consultar_uno(
        """SELECT r.reserva_id, r.codigo, r.token, r.fecha, r.hora, r.hora_anterior,
                  r.cantidad_personas, r.estado, r.canal, r.excede_cupo, r.nota, r.motivo,
                  r.creado_en,
                  c.cliente_id, c.nombre AS cliente_nombre, c.telefono AS cliente_telefono,
                  c.correo AS cliente_correo
           FROM reserva r JOIN cliente c ON r.cliente_id = c.cliente_id
           WHERE r.reserva_id = %s""",
        (reserva_id,)
    )


def obtener_reserva_publica(token):
    """Reserva para la página de seguimiento del cliente (los datos operativos del local
    y el detalle del staff no van al público)."""
    return consultar_uno(
        """SELECT r.reserva_id, r.codigo, r.fecha, r.hora, r.hora_anterior,
                  r.cantidad_personas, r.estado, r.nota, r.motivo
           FROM reserva r WHERE r.token = %s""",
        (token,)
    )


def obtener_pizarra(fecha):
    """Todo lo que la pizarra digital necesita para un día:
    - franjas: la salida de fn_carga_dia (personas, mesas, libres, limita, nivel)
    - ocupan: reservas confirmadas/llego que cubren cada franja (con marca 'continúa')
    - pendientes: solicitudes de la web (aparte; no ocupan franjas)
    - atrasadas: confirmadas pasadas de hora + tolerancia (solo alerta visual)
    La duración de CADA reserva sale de fn_duracion_estadia (SQL): no se calcula en Python.
    """
    config = obtener_config()
    franjas_sql = carga_dia(fecha)
    tolerancia = timedelta(minutes=config["tolerancia_min"])
    ahora = ahora_local()

    reservas_del_dia = consultar_todos(
        """SELECT r.reserva_id, r.codigo, r.cliente_id, r.fecha, r.hora, r.hora_anterior,
                  r.cantidad_personas, r.estado, r.canal, r.excede_cupo, r.nota, r.motivo,
                  fn_duracion_estadia(r.cantidad_personas) AS duracion_min,
                  (r.hora + make_interval(mins => fn_duracion_estadia(r.cantidad_personas)))::time AS hasta,
                  c.nombre AS cliente_nombre, c.telefono AS cliente_telefono,
                  c.correo AS cliente_correo
           FROM reserva r JOIN cliente c ON r.cliente_id = c.cliente_id
           WHERE r.fecha = %s
           ORDER BY r.hora, r.reserva_id""",
        (fecha,)
    )

    def _fecha_hora(r):
        fecha_r = r["fecha"]
        fecha_r = fecha_r if isinstance(fecha_r, date) else datetime.strptime(fecha_r, "%Y-%m-%d").date()
        hora_r = r["hora"]
        hora_r = hora_r if isinstance(hora_r, time) else datetime.strptime(str(hora_r)[:5], "%H:%M").time()
        return datetime.combine(fecha_r, hora_r)

    pendientes = []
    ocupadas = []
    for r in reservas_del_dia:
        if r["estado"] == "pendiente":
            actividad = servicio_clientes.actividad_24h(r.get("cliente_id") or 0)
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
    for f in franjas_sql:
        ini = datetime.combine(fecha if isinstance(fecha, date) else datetime.strptime(str(fecha), "%Y-%m-%d").date(),
                               f["franja_inicio"])
        fin = datetime.combine(fecha if isinstance(fecha, date) else datetime.strptime(str(fecha), "%Y-%m-%d").date(),
                               f["franja_fin"])
        ocupan_esta = []
        for r in ocupadas:
            inicio_reserva = _fecha_hora(r)
            # la ocupación de mesa dura lo que manda fn_duracion_estadia (columna duracion_min del SELECT)
            fin_reserva = inicio_reserva + timedelta(minutes=r["duracion_min"])
            if inicio_reserva < fin and fin_reserva > ini:
                r = dict(r)
                r["continua"] = inicio_reserva < ini  # empezó en una franja anterior
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
