"""Servicio para la gestión de usuarios del personal (solo rol admin)."""
from werkzeug.security import generate_password_hash
from app.db import consultar_todos, consultar_uno, ejecutar, ejecutar_retornando


def listar_personal():
    """Devuelve la lista del personal registrado, omitiendo siempre password_hash."""
    return consultar_todos(
        "SELECT personal_id, nombre, correo, rol, activo, debe_cambiar_clave, creado_en "
        "FROM personal ORDER BY personal_id"
    )


def obtener_personal_por_id(personal_id):
    """Devuelve un miembro del personal por su ID (sin password_hash)."""
    return consultar_uno(
        "SELECT personal_id, nombre, correo, rol, activo, debe_cambiar_clave, creado_en "
        "FROM personal WHERE personal_id = %s",
        (personal_id,)
    )


def crear_personal(nombre, correo, rol, password_inicial):
    """Crea una nueva cuenta de personal con debe_cambiar_clave en TRUE."""
    nombre_limpio = (nombre or "").strip()
    correo_limpio = (correo or "").strip().lower()

    if not nombre_limpio:
        raise ValueError("El nombre del colaborador es obligatorio.")
    if not correo_limpio or "@" not in correo_limpio:
        raise ValueError("El correo electrónico es inválido.")
    if rol not in ("admin", "empleado"):
        raise ValueError("El rol debe ser 'admin' o 'empleado'.")
    if not password_inicial or len(password_inicial) < 6:
        raise ValueError("La contraseña inicial debe tener al menos 6 caracteres.")

    # Verificar si el correo ya existe
    existente = consultar_uno("SELECT personal_id FROM personal WHERE lower(correo) = %s", (correo_limpio,))
    if existente:
        raise ValueError("Ya existe una cuenta registrada con este correo electrónico.")

    password_hash = generate_password_hash(password_inicial)

    fila = ejecutar_retornando(
        """
        INSERT INTO personal (nombre, correo, password_hash, rol, activo, debe_cambiar_clave)
        VALUES (%s, %s, %s, %s, TRUE, TRUE)
        RETURNING personal_id, nombre, correo, rol, activo, debe_cambiar_clave
        """,
        (nombre_limpio, correo_limpio, password_hash, rol)
    )
    return fila


def cambiar_estado_personal(personal_id, nuevo_estado_activo, solicitante_id):
    """Activa o desactiva la cuenta de un trabajador.
    Regla estricta: un administrador NO puede desactivarse a sí mismo.
    """
    if int(personal_id) == int(solicitante_id) and not nuevo_estado_activo:
        raise ValueError("No puedes desactivar tu propia cuenta de administrador.")

    usuario = consultar_uno("SELECT personal_id, nombre FROM personal WHERE personal_id = %s", (personal_id,))
    if not usuario:
        raise ValueError("El usuario no existe.")

    ejecutar(
        "UPDATE personal SET activo = %s WHERE personal_id = %s",
        (bool(nuevo_estado_activo), personal_id)
    )
    return {"personal_id": personal_id, "activo": bool(nuevo_estado_activo)}


def restablecer_password(personal_id, nueva_clave_temporal):
    """Restablece la contraseña de un usuario y lo obliga a cambiarla en su siguiente acceso."""
    if not nueva_clave_temporal or len(nueva_clave_temporal) < 6:
        raise ValueError("La contraseña temporal debe tener al menos 6 caracteres.")

    usuario = consultar_uno("SELECT personal_id, nombre FROM personal WHERE personal_id = %s", (personal_id,))
    if not usuario:
        raise ValueError("El usuario no existe.")

    password_hash = generate_password_hash(nueva_clave_temporal)
    ejecutar(
        "UPDATE personal SET password_hash = %s, debe_cambiar_clave = TRUE WHERE personal_id = %s",
        (password_hash, personal_id)
    )
    return {"personal_id": personal_id, "nombre": usuario["nombre"], "debe_cambiar_clave": True}
