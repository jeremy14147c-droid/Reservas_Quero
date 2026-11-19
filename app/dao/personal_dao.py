"""DAO para la gestión de personal e intentos de login (tablas personal e intento_login)."""
from app.db import consultar_todos, consultar_uno, ejecutar, ejecutar_retornando


class PersonalDAO:
    """Acceso a datos de personal y control de acceso/intentos."""

    def listar(self):
        """Lista todo el personal sin password_hash."""
        return consultar_todos(
            "SELECT personal_id, nombre, correo, rol, activo, debe_cambiar_clave, sesion_version, creado_en "
            "FROM personal ORDER BY personal_id"
        )

    def buscar_por_id(self, personal_id):
        """Busca un usuario por su ID sin password_hash."""
        return consultar_uno(
            "SELECT personal_id, nombre, correo, rol, activo, debe_cambiar_clave, sesion_version, creado_en "
            "FROM personal WHERE personal_id = %s",
            (personal_id,)
        )

    def buscar_por_correo(self, correo):
        """Busca un usuario por su correo electrónico (incluye password_hash para autenticación)."""
        return consultar_uno(
            "SELECT personal_id, nombre, correo, password_hash, rol, activo, debe_cambiar_clave, sesion_version "
            "FROM personal WHERE lower(correo) = %s",
            (correo.lower().strip(),)
        )

    def existe_correo(self, correo):
        """Comprueba si un correo ya está registrado."""
        fila = consultar_uno(
            "SELECT personal_id FROM personal WHERE lower(correo) = %s",
            (correo.lower().strip(),)
        )
        return fila is not None

    def insertar(self, nombre, correo, password_hash, rol):
        """Inserta un nuevo miembro del personal."""
        return ejecutar_retornando(
            """
            INSERT INTO personal (nombre, correo, password_hash, rol, activo, debe_cambiar_clave, sesion_version)
            VALUES (%s, %s, %s, %s, TRUE, TRUE, 1)
            RETURNING personal_id, nombre, correo, rol, activo, debe_cambiar_clave
            """,
            (nombre, correo.lower().strip(), password_hash, rol)
        )

    def actualizar_password(self, personal_id, password_hash, debe_cambiar_clave=False, nueva_version=None):
        """Actualiza la contraseña y version de sesión de un colaborador."""
        if nueva_version is not None:
            ejecutar(
                """
                UPDATE personal
                SET password_hash = %s, debe_cambiar_clave = %s, sesion_version = %s
                WHERE personal_id = %s
                """,
                (password_hash, debe_cambiar_clave, nueva_version, personal_id)
            )
        else:
            ejecutar(
                """
                UPDATE personal
                SET password_hash = %s, debe_cambiar_clave = %s, sesion_version = sesion_version + 1
                WHERE personal_id = %s
                """,
                (password_hash, debe_cambiar_clave, personal_id)
            )

    def cambiar_activo(self, personal_id, activo):
        """Activa o desactiva a un colaborador. Si desactiva, incrementa sesion_version."""
        if not activo:
            ejecutar(
                "UPDATE personal SET activo = FALSE, sesion_version = sesion_version + 1 WHERE personal_id = %s",
                (personal_id,)
            )
        else:
            ejecutar(
                "UPDATE personal SET activo = TRUE WHERE personal_id = %s",
                (personal_id,)
            )

    def incrementar_sesion_version(self, personal_id):
        """Incrementa la versión de sesión para revocar tokens/cookies activos."""
        ejecutar(
            "UPDATE personal SET sesion_version = sesion_version + 1 WHERE personal_id = %s",
            (personal_id,)
        )

    def consultar_intentos_fallidos(self, limite_tiempo, correo, ip):
        """Consulta los intentos fallidos recientes para correo e IP."""
        return consultar_todos(
            """
            SELECT creado_en, correo_lower, ip
            FROM intento_login
            WHERE exitoso = FALSE AND creado_en >= %s AND (correo_lower = %s OR ip = %s)
            """,
            (limite_tiempo, correo.lower().strip(), ip)
        )

    def registrar_intento(self, correo, ip, exitoso, creado_en):
        """Registra un intento de login en la bitácora."""
        ejecutar(
            "INSERT INTO intento_login (correo_lower, ip, exitoso, creado_en) VALUES (%s, %s, %s, %s)",
            (correo.lower().strip(), ip, exitoso, creado_en)
        )

    def limpiar_intentos(self, correo):
        """Limpia los intentos de un correo tras login exitoso."""
        ejecutar("DELETE FROM intento_login WHERE correo_lower = %s", (correo.lower().strip(),))
