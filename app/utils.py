"""Utilidades de formato, normalización y generación de códigos."""
import re
import secrets
import string


def normalizar_telefono(telefono):
    """Limpia caracteres no numéricos y valida que sea un teléfono móvil de Perú (9 dígitos comenzando con 9).
    Devuelve los 9 dígitos limpios o None si no es válido.
    """
    if not telefono:
        return None
    limpio = re.sub(r"\D", "", str(telefono))
    # Si viene con prefijo país 51 y tiene 11 dígitos
    if len(limpio) == 11 and limpio.startswith("519"):
        limpio = limpio[2:]
    if len(limpio) == 9 and limpio.startswith("9"):
        return limpio
    return None


def generar_codigo_reserva(longitud=6):
    """Genera un código alfanumérico corto y legible para tickets de reserva (ej. QR-4X9A)."""
    caracteres = string.ascii_uppercase + string.digits
    # Excluir caracteres confusos como O, 0, I, 1
    caracteres_claros = "".join(c for c in caracteres if c not in "OI01")
    aleatorio = "".join(secrets.choice(caracteres_claros) for _ in range(longitud))
    return f"Q-{aleatorio}"
