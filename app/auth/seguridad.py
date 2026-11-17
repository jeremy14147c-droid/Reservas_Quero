"""Módulo de seguridad para autenticación y sesiones (Fase S1).
Reglas puras y utilidades contra vulnerabilidades OWASP (H-1 a H-5, H-8, H-9).
"""
from datetime import datetime, timedelta, timezone
from werkzeug.security import generate_password_hash

# Hash falso constante para mitigar ataques de temporización (H-4)
HASH_FALSO_DUMMY = generate_password_hash("contrasena_dummy_para_timing_attack_seguridad")

# Lista de contraseñas débiles/comunes bloqueadas (H-9)
CLAVES_COMUNES = {
    "1234567890",
    "password123",
    "contrasena123",
    "qwerty12345",
    "admin123456",
    "quero123456",
    "administrador",
    "12345678901",
    "abcdefghij"
}


def destino_seguro(target: str | None) -> str | None:
    """Valida que una URL de redirección sea estrictamente interna (H-3).
    Evita open redirect hacia sitios externos o esquemas maliciosos.
    """
    if not target or not isinstance(target, str):
        return None

    target = target.strip()
    # Debe ser relativa a la raíz
    if not target.startswith("/"):
        return None

    # Rechazar inicios tipo // (protocol-relative), /\, \\
    if target.startswith("//") or target.startswith("/\\") or target.startswith(r"\ "):
        return None

    # Rechazar barras invertidas (evita bypasses en navegadores)
    if "\\" in target:
        return None

    # Rechazar esquemas (evita javascript:, data:, https:)
    if ":" in target:
        return None

    return target


def debe_bloquear(
    recientes_correo: list,
    recientes_ip: list,
    ahora: datetime | None = None,
    max_correo: int = 5,
    max_ip: int = 20,
    ventana_minutos: int = 10
) -> tuple[bool, str | None]:
    """Regla pura: bloquea el login si hay 5 fallos en 10 min por correo o 20 por IP (H-2)."""
    if ahora is None:
        ahora = datetime.now(timezone.utc)

    limite = ahora - timedelta(minutes=ventana_minutos)

    def _es_reciente(dt):
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt >= limite

    fallos_correo = sum(1 for dt in recientes_correo if _es_reciente(dt))
    fallos_ip = sum(1 for dt in recientes_ip if _es_reciente(dt))

    if fallos_correo >= max_correo or fallos_ip >= max_ip:
        return True, "Demasiados intentos. Espera unos minutos."

    return False, None


def validar_politica_contrasena(password: str | None) -> tuple[bool, str | None]:
    """Valida longitud mínima (10 caracteres) y rechaza claves comunes (H-9)."""
    if not password or not isinstance(password, str):
        return False, "La contraseña no puede estar vacía."

    if len(password) < 10:
        return False, "La contraseña debe tener al menos 10 caracteres."

    if password.lower() in CLAVES_COMUNES:
        return False, "Esa contraseña es muy común e insegura. Elige una más robusta."

    return True, None
