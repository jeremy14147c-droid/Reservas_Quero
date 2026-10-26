"""Utilidades de formato, normalización y generación de códigos."""
import base64
import io
import re
import secrets
import string
from datetime import date, time, datetime


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


# ---------- Formato Perú (AGENTS.md sección 11) ----------

def _a_hora(valor):
    """Convierte distintos formatos de hora (time, datetime, str 'HH:MM') a un objeto time."""
    if isinstance(valor, time):
        return valor
    if isinstance(valor, datetime):
        return valor.time()
    if isinstance(valor, str):
        partes = valor.strip().split(":")
        try:
            return time(int(partes[0]), int(partes[1]) if len(partes) > 1 else 0)
        except (ValueError, IndexError):
            return None
    return None


def formato_hora_12h(valor):
    """Da formato de hora en 12 h con am/pm (ej. '1:00 pm'), como se acostumbra en Perú."""
    hora = _a_hora(valor)
    if hora is None:
        return ""
    am_pm = "am" if hora.hour < 12 else "pm"
    horas_12 = hora.hour % 12
    if horas_12 == 0:
        horas_12 = 12
    return f"{horas_12}:{hora.minute:02d} {am_pm}"


def formato_fecha_ddmm(valor):
    """Da formato de fecha dd/mm/aaaa. Acepta date, datetime o la cadena 'YYYY-MM-DD'."""
    if isinstance(valor, str):
        valor = datetime.strptime(valor, "%Y-%m-%d").date()
    elif isinstance(valor, datetime):
        valor = valor.date()
    if isinstance(valor, date):
        return valor.strftime("%d/%m/%Y")
    return str(valor or "")


# ---------- Enlaces de contacto del menú ⋮ (MVP: solo enlaces, sin API) ----------

def enlace_whatsapp(telefono, mensaje):
    """Construye el enlace https://wa.me/51XXXXXXXXX?text=... para escribir al cliente.
    El mensaje se codifica para URL (los espacios van como %20)."""
    from urllib.parse import quote
    tel = normalizar_telefono(telefono)
    if not tel:
        return None
    texto = str(mensaje or "").strip()
    if texto:
        return f"https://wa.me/51{tel}?text={quote(texto)}"
    return f"https://wa.me/51{tel}"


def enlace_llamar(telefono):
    """Construye el enlace tel:+51XXXXXXXXX para llamar al cliente."""
    tel = normalizar_telefono(telefono)
    if not tel:
        return None
    return f"tel:+51{tel}"


def enlace_correo(correo, asunto=None):
    """Construye el enlace mailto: (solo si hay correo)."""
    correo_limpio = (correo or "").strip()
    if not correo_limpio or "@" not in correo_limpio:
        return None
    if asunto:
        return f"mailto:{correo_limpio}?subject={asunto}"
    return f"mailto:{correo_limpio}"


# ---------- QR para los tickets (AGENTS.md sección 10) ----------

def generar_qr_data_url(texto):
    """Genera un QR como imagen en base64 (data URI) para incrustar directo en un <img>.
    Se usa en los tickets: el staff lo escanea con la cámara del celular.
    """
    import qrcode

    img = qrcode.make(str(texto), box_size=6, border=2)
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    datos = base64.b64encode(buffer.getvalue()).decode("ascii")
    return f"data:image/png;base64,{datos}"
