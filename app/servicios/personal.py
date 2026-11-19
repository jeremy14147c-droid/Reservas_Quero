"""Servicio para la gestión de usuarios del personal (solo rol admin)."""
from werkzeug.security import generate_password_hash
from app.dao.personal_dao import PersonalDAO
from app.auth.seguridad import validar_politica_contrasena

# Instancia por defecto del DAO
personal_dao_default = PersonalDAO()


def listar_personal(dao=None):
    """Devuelve la lista del personal registrado, omitiendo siempre password_hash."""
    dao = dao or personal_dao_default
    return dao.listar()


def obtener_personal_por_id(personal_id, dao=None):
    """Devuelve un miembro del personal por su ID (sin password_hash)."""
    dao = dao or personal_dao_default
    return dao.buscar_por_id(personal_id)


def crear_personal(nombre, correo, rol, password_inicial, dao=None):
    """Crea una nueva cuenta de personal con debe_cambiar_clave en TRUE y valida política de contraseña (H-9)."""
    dao = dao or personal_dao_default
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
    if dao.existe_correo(correo_limpio):
        raise ValueError("Ya existe una cuenta registrada con este correo electrónico.")

    password_hash = generate_password_hash(password_inicial)
    return dao.insertar(nombre_limpio, correo_limpio, password_hash, rol)


def cambiar_estado_personal(personal_id, nuevo_estado_activo, solicitante_id, dao=None):
    """Activa o desactiva la cuenta de un trabajador.
    Regla estricta: un administrador NO puede desactivarse a sí mismo.
    Si se desactiva, incrementa sesion_version para revocar cualquier sesión abierta (H-1).
    """
    dao = dao or personal_dao_default
    if int(personal_id) == int(solicitante_id) and not nuevo_estado_activo:
        raise ValueError("No puedes desactivar tu propia cuenta de administrador.")

    usuario = dao.buscar_por_id(personal_id)
    if not usuario:
        raise ValueError("El usuario no existe.")

    dao.cambiar_activo(personal_id, bool(nuevo_estado_activo))
    return {"personal_id": personal_id, "activo": bool(nuevo_estado_activo)}


def restablecer_password(personal_id, nueva_clave_temporal, dao=None):
    """Restablece la contraseña de un usuario, valida política e incrementa sesion_version (H-1, H-9)."""
    dao = dao or personal_dao_default
    valida, err = validar_politica_contrasena(nueva_clave_temporal)
    if not valida:
        raise ValueError(err)

    usuario = dao.buscar_por_id(personal_id)
    if not usuario:
        raise ValueError("El usuario no existe.")

    password_hash = generate_password_hash(nueva_clave_temporal)
    dao.actualizar_password(personal_id, password_hash, debe_cambiar_clave=True)
    return {"personal_id": personal_id, "nombre": usuario["nombre"], "debe_cambiar_clave": True}
