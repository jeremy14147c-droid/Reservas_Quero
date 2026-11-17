"""Servicio para la gestión de usuarios del personal (solo rol admin)."""
from werkzeug.security import generate_password_hash
from app.db import consultar_todos, consultar_uno, ejecutar, ejecutar_retornando
from app.auth.seguridad import validar_politica_contrasena


def listar_personal():
    """Devuelve la lista del personal registrado, omitiendo siempre password_hash."""
    return consultar_todos(
        "SELECT personal_id, nombre, correo, rol, activo, debe_cambiar_clave, sesion_version, creado_en "
        "FROM personal ORDER BY personal_id"
    )


def obtener_personal_por_id(personal_id):
    """Devuelve un miembro del personal por su ID (sin password_hash)."""
    return consultar_uno(
        "SELECT personal_id, nombre, correo, rol, activo, debe_cambiar_clave, sesion_version, creado_en "
        "FROM personal WHERE personal_id = %s",
        (personal_id,)
    )


def crear_personal(nombre, correo, rol, password_inicial):
    """Crea una nueva cuenta de personal con debe_cambiar_clave en TRUE y valida política de contraseña (H-9)."""
    nombre_limpio = (nombre or "").strip()
    correo_limpio = (correo or "").strip().lower()

    if not nombre_limpio:
        raise ValueError("El nombre del colaborador es obligatorio.")
    if not correo_limpio or "@" not in correo_limpio:
        raise ValueError("El correo electrónico es inválido.")
    if rol not in ("admin", "empleado"):
        raise ValueError("El rol debe ser 'admin' o 'empleado'.")

    # H-9: Validación de contraseña robusta
    valida, err = validar_politica_contrasena(password_inicial)
    if not valida:
        raise ValueError(err)

    # Verificar si el correo ya existe
    existente = consultar_uno("SELECT personal_id FROM personal WHERE lower(correo) = %s", (correo_limpio,))
    if existente:
        raise ValueError("Ya existe una cuenta registrada con este correo electrónico.")

    password_hash = generate_password_hash(password_inicial)

    fila = ejecutar_retornando(
        """
        INSERT INTO personal (nombre, correo, password_hash, rol, activo, debe_cambiar_clave, sesion_version)
        VALUES (%s, %s, %s, %s, TRUE, TRUE, 1)
        RETURNING personal_id, nombre, correo, rol, activo, debe_cambiar_clave
        """,
        (nombre_limpio, correo_limpio, password_hash, rol)
    )
    return fila


def cambiar_estado_personal(personal_id, nuevo_estado_activo, solicitante_id):
    """Activa o desactiva la cuenta de un trabajador.
    Regla estricta: un administrador NO puede desactivarse a sí mismo.
    Si se desactiva, incrementa sesion_version para revocar cualquier sesión abierta (H-1).
    """
    if int(personal_id) == int(solicitante_id) and not nuevo_estado_activo:
        raise ValueError("No puedes desactivar tu propia cuenta de administrador.")

    usuario = consultar_uno("SELECT personal_id, nombre FROM personal WHERE personal_id = %s", (personal_id,))
    if not usuario:
        raise ValueError("El usuario no existe.")

    if not nuevo_estado_activo:
        ejecutar(
            "UPDATE personal SET activo = FALSE, sesion_version = sesion_version + 1 WHERE personal_id = %s",
            (personal_id,)
        )
    else:
        ejecutar(
            "UPDATE personal SET activo = TRUE WHERE personal_id = %s",
            (personal_id,)
        )
    return {"personal_id": personal_id, "activo": bool(nuevo_estado_activo)}


def restablecer_password(personal_id, nueva_clave_temporal):
    """Restablece la contraseña de un usuario, valida política e incrementa sesion_version (H-1, H-9)."""
    valida, err = validar_politica_contrasena(nueva_clave_temporal)
    if not valida:
        raise ValueError(err)

    usuario = consultar_uno("SELECT personal_id, nombre FROM personal WHERE personal_id = %s", (personal_id,))
    if not usuario:
        raise ValueError("El usuario no existe.")

    password_hash = generate_password_hash(nueva_clave_temporal)
    ejecutar(
        """
        UPDATE personal
        SET password_hash = %s, debe_cambiar_clave = TRUE, sesion_version = sesion_version + 1
        WHERE personal_id = %s
        """,
        (password_hash, personal_id)
    )
    return {"personal_id": personal_id, "nombre": usuario["nombre"], "debe_cambiar_clave": True}
