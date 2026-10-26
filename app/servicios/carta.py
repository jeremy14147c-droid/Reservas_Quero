"""Servicio de negocio para la gestión de la carta (categorías y platos).
Independiente de Flask: recibe datos y retorna resultados o lanza excepciones de negocio.
"""
from app.db import consultar_todos, consultar_uno, ejecutar, ejecutar_retornando


def obtener_carta_publica():
    """Devuelve las categorías activas con sus platos activos ordenados.
    Los platos con disponible = False vienen marcados para mostrarse como 'Agotado'.
    Los platos con activo = False se omiten por completo.
    """
    categorias = consultar_todos(
        "SELECT categoria_id, nombre, orden "
        "FROM categoria WHERE activa = TRUE ORDER BY orden, nombre"
    )

    platos = consultar_todos(
        "SELECT plato_id, categoria_id, nombre, descripcion, precio, disponible "
        "FROM plato WHERE activo = TRUE ORDER BY nombre"
    )

    # Agrupar platos por categoría
    platos_por_cat = {}
    for p in platos:
        cat_id = p["categoria_id"]
        if cat_id not in platos_por_cat:
            platos_por_cat[cat_id] = []
        platos_por_cat[cat_id].append(p)

    resultado = []
    for c in categorias:
        lista_platos = platos_por_cat.get(c["categoria_id"], [])
        if lista_platos:  # Solo incluir categorías que tengan platos activos
            resultado.append({
                "categoria_id": c["categoria_id"],
                "nombre": c["nombre"],
                "platos": lista_platos
            })

    return resultado


def obtener_carta_staff():
    """Devuelve todas las categorías y platos activos para la gestión del personal."""
    categorias = consultar_todos(
        "SELECT categoria_id, nombre, orden, activa "
        "FROM categoria ORDER BY orden, nombre"
    )

    platos = consultar_todos(
        "SELECT p.plato_id, p.categoria_id, c.nombre AS categoria_nombre, "
        "p.nombre, p.descripcion, p.precio, p.disponible, p.activo "
        "FROM plato p "
        "JOIN categoria c ON p.categoria_id = c.categoria_id "
        "WHERE p.activo = TRUE "
        "ORDER BY c.orden, c.nombre, p.nombre"
    )

    return {"categorias": categorias, "platos": platos}


def cambiar_disponibilidad_plato(plato_id, disponible):
    """Cambia el interruptor 'disponible' (agotado o no) de un plato."""
    plato = consultar_uno("SELECT plato_id, nombre, disponible, activo FROM plato WHERE plato_id = %s", (plato_id,))
    if not plato or not plato["activo"]:
        raise ValueError("El plato especificado no existe o está inactivo.")

    ejecutar(
        "UPDATE plato SET disponible = %s WHERE plato_id = %s",
        (bool(disponible), plato_id)
    )
    return {"plato_id": plato_id, "nombre": plato["nombre"], "disponible": bool(disponible)}


def actualizar_precio_plato(plato_id, nuevo_precio):
    """Actualiza el precio de un plato."""
    try:
        precio_val = float(nuevo_precio)
        if precio_val < 0:
            raise ValueError("El precio no puede ser negativo.")
    except (TypeError, ValueError):
        raise ValueError("El precio debe ser un número válido mayor o igual a 0.")

    plato = consultar_uno("SELECT plato_id, nombre, activo FROM plato WHERE plato_id = %s", (plato_id,))
    if not plato or not plato["activo"]:
        raise ValueError("El plato especificado no existe o está inactivo.")

    ejecutar(
        "UPDATE plato SET precio = %s WHERE plato_id = %s",
        (precio_val, plato_id)
    )
    return {"plato_id": plato_id, "nombre": plato["nombre"], "precio": precio_val}


def crear_plato(categoria_id, nombre, precio, descripcion=None):
    """Registra un nuevo plato (solo rol admin)."""
    nombre_limpio = (nombre or "").strip()
    if not nombre_limpio:
        raise ValueError("El nombre del plato es obligatorio.")

    try:
        precio_val = float(precio)
        if precio_val < 0:
            raise ValueError("El precio no puede ser negativo.")
    except (TypeError, ValueError):
        raise ValueError("El precio debe ser un valor numérico válido.")

    categoria = consultar_uno("SELECT categoria_id FROM categoria WHERE categoria_id = %s", (categoria_id,))
    if not categoria:
        raise ValueError("La categoría seleccionada no existe.")

    desc_limpia = (descripcion or "").strip() or None

    fila = ejecutar_retornando(
        "INSERT INTO plato (categoria_id, nombre, descripcion, precio, disponible, activo) "
        "VALUES (%s, %s, %s, %s, TRUE, TRUE) RETURNING plato_id, nombre, precio",
        (categoria_id, nombre_limpio, desc_limpia, precio_val)
    )
    return fila


def editar_plato(plato_id, categoria_id, nombre, precio, descripcion=None):
    """Edita los datos de un plato existente."""
    nombre_limpio = (nombre or "").strip()
    if not nombre_limpio:
        raise ValueError("El nombre del plato es obligatorio.")

    try:
        precio_val = float(precio)
        if precio_val < 0:
            raise ValueError("El precio no puede ser negativo.")
    except (TypeError, ValueError):
        raise ValueError("El precio debe ser un valor numérico válido.")

    plato = consultar_uno("SELECT plato_id FROM plato WHERE plato_id = %s", (plato_id,))
    if not plato:
        raise ValueError("El plato no existe.")

    categoria = consultar_uno("SELECT categoria_id FROM categoria WHERE categoria_id = %s", (categoria_id,))
    if not categoria:
        raise ValueError("La categoría no existe.")

    desc_limpia = (descripcion or "").strip() or None

    ejecutar(
        "UPDATE plato SET categoria_id = %s, nombre = %s, precio = %s, descripcion = %s "
        "WHERE plato_id = %s",
        (categoria_id, nombre_limpio, precio_val, desc_limpia, plato_id)
    )
    return {"plato_id": plato_id, "nombre": nombre_limpio, "precio": precio_val}


def desactivar_plato(plato_id):
    """Desactiva un plato (NUNCA se borra físicamente para preservar integridad histórica)."""
    plato = consultar_uno("SELECT plato_id, nombre FROM plato WHERE plato_id = %s", (plato_id,))
    if not plato:
        raise ValueError("El plato no existe.")

    ejecutar("UPDATE plato SET activo = FALSE, disponible = FALSE WHERE plato_id = %s", (plato_id,))
    return {"plato_id": plato_id, "nombre": plato["nombre"], "activo": False}


def crear_categoria(nombre, orden=0):
    """Crea una nueva categoría de platos."""
    nombre_limpio = (nombre or "").strip()
    if not nombre_limpio:
        raise ValueError("El nombre de la categoría es obligatorio.")

    existente = consultar_uno("SELECT categoria_id FROM categoria WHERE lower(nombre) = lower(%s)", (nombre_limpio,))
    if existente:
        raise ValueError("Ya existe una categoría con ese nombre.")

    fila = ejecutar_retornando(
        "INSERT INTO categoria (nombre, orden, activa) VALUES (%s, %s, TRUE) RETURNING categoria_id, nombre",
        (nombre_limpio, int(orden or 0))
    )
    return fila
