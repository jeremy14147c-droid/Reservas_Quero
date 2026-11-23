"""Datos de contacto y marca del local (Fase 3.4).

Funciones PURAS (sin Flask y sin SQL): validan lo que la dueña escribe en
Configuración y arman los enlaces que usan las plantillas públicas.
La fuente de verdad sigue siendo la tabla `config_local`.
"""
from app.utils import (
    enlace_whatsapp,
    formato_hora_12h,
    normalizar_telefono,
)

# Texto provisional mientras la dueña define su eslogan definitivo.
# Es editable desde Administración > Configuración.
ESLOGAN_POR_DEFECTO = "El sabor del mar y lo criollo, en un solo lugar."

# Mensaje con el que se abre WhatsApp desde el botón flotante y los accesos.
MENSAJE_WHATSAPP_POR_DEFECTO = "¡Hola Quero Gastrobar! Quisiera hacer una consulta."


def validar_whatsapp(valor):
    """Devuelve los 9 dígitos del WhatsApp o None si está vacío.

    Reutiliza `normalizar_telefono` (misma regla que los clientes: 9 dígitos
    que empiezan en 9). Si viene algo que no es un celular válido, lanza
    ValueError con un mensaje claro para mostrar en el formulario.
    """
    texto = (str(valor).strip() if valor is not None else "")
    if not texto:
        return None
    telefono = normalizar_telefono(texto)
    if not telefono:
        raise ValueError("El WhatsApp debe tener 9 dígitos y empezar con 9 (ejemplo: 996908138).")
    return telefono


def validar_url_segura(valor, etiqueta):
    """Valida un enlace de marca: vacío → None; si viene, debe ser https://.

    Se rechazan `http://` y esquemas peligrosos (`javascript:`, `data:`,
    `vbscript:`, `file:`), que son el vector clásico de XSS en un enlace.
    """
    texto = (str(valor).strip() if valor is not None else "")
    if not texto:
        return None
    minuscula = texto.lower()
    if not minuscula.startswith("https://") or len(texto) <= len("https://"):
        raise ValueError(f"El {etiqueta} debe empezar por https:// y ser un enlace válido.")
    if any(caracter.isspace() for caracter in texto):
        raise ValueError(f"El {etiqueta} no puede contener espacios.")
    return texto


def construir_marca(config):
    """Arma el diccionario `marca` que reciben las plantillas públicas.

    No lanza errores: si un dato falta, devuelve None y la plantilla muestra
    el marcador "Pendiente: ...". Así una configuración incompleta nunca rompe
    la página del cliente.
    """
    config = config or {}
    numero = normalizar_telefono(config.get("whatsapp_numero"))
    apertura = config.get("hora_apertura")
    cierre = config.get("hora_cierre")

    horario = None
    if apertura and cierre:
        horario = f"{formato_hora_12h(apertura)} a {formato_hora_12h(cierre)}"

    return {
        "nombre": (config.get("nombre_local") or "Quero Gastrobar").strip(),
        "eslogan": (config.get("eslogan") or ESLOGAN_POR_DEFECTO).strip(),
        "abierto": bool(config.get("abierto", True)),
        "whatsapp_numero": numero,
        "whatsapp_url": enlace_whatsapp(numero, MENSAJE_WHATSAPP_POR_DEFECTO) if numero else None,
        "telefono_url": f"tel:+51{numero}" if numero else None,
        "direccion": (config.get("direccion") or "").strip() or None,
        "maps_url": (config.get("maps_url") or "").strip() or None,
        "instagram_url": (config.get("instagram_url") or "").strip() or None,
        "facebook_url": (config.get("facebook_url") or "").strip() or None,
        "horario": horario,
    }
