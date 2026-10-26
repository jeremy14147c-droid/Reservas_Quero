"""Servicio de negocio para la gestión de la carta (categorías y platos).
Independiente de Flask: recibe datos y retorna resultados o lanza excepciones de negocio.
"""
import unicodedata
from app.db import consultar_todos, consultar_uno, ejecutar, ejecutar_retornando


def _normalizar_texto(texto):
    """Convierte texto a minúsculas y elimina tildes/acentos para comparaciones."""
    if not texto:
        return ""
    descompuesto = unicodedata.normalize("NFD", str(texto))
    sin_tildes = "".join(c for c in descompuesto if unicodedata.category(c) != "Mn")
    return sin_tildes.lower().strip()


def obtener_carta_publica():
    """Devuelve las categorías activas con sus platos activos ordenados.
    Los platos con disponible = False vienen marcados para mostrarse como 'Agotado'.
    Los platos con activo = False se omiten por completo.
    Incluye el código del plato cuando exista.
    """
    categorias = consultar_todos(
        "SELECT categoria_id, nombre, orden "
        "FROM categoria WHERE activa = TRUE ORDER BY orden, nombre"
    )

    platos = consultar_todos(
        "SELECT plato_id, categoria_id, codigo, nombre, descripcion, precio, disponible "
        "FROM plato WHERE activo = TRUE ORDER BY codigo NULLS LAST, nombre"
    )

    platos_por_cat = {}
    for p in platos:
        cat_id = p["categoria_id"]
        if cat_id not in platos_por_cat:
            platos_por_cat[cat_id] = []
        platos_por_cat[cat_id].append(p)

    resultado = []
    for c in categorias:
        lista_platos = platos_por_cat.get(c["categoria_id"], [])
        if lista_platos:
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
        "p.codigo, p.nombre, p.descripcion, p.precio, p.disponible, p.activo "
        "FROM plato p "
        "JOIN categoria c ON p.categoria_id = c.categoria_id "
        "WHERE p.activo = TRUE "
        "ORDER BY c.orden, c.nombre, p.codigo NULLS LAST, p.nombre"
    )

    return {"categorias": categorias, "platos": platos}


def buscar_platos(texto):
    """Busca platos activos por código numérico exacto o por nombre (sin distinguir mayúsculas ni tildes).
    - Si texto son solo dígitos: coincidencia EXACTA por plato.codigo (1 no trae 10 ni 11).
    - Si no: búsqueda por coincidencia parcial en el nombre normalizado.
    """
    termino = (texto or "").strip()
    if not termino:
        # Si la búsqueda está vacía, devuelve todos los platos activos
        return consultar_todos(
            "SELECT p.plato_id, p.codigo, p.nombre, p.precio, p.disponible, c.nombre AS categoria_nombre "
            "FROM plato p "
            "JOIN categoria c ON p.categoria_id = c.categoria_id "
            "WHERE p.activo = TRUE "
            "ORDER BY c.orden, p.codigo NULLS LAST, p.nombre"
        )

    # 1. Búsqueda por código numérico EXACTO
    if termino.isdigit():
        codigo_num = int(termino)
        return consultar_todos(
            "SELECT p.plato_id, p.codigo, p.nombre, p.precio, p.disponible, c.nombre AS categoria_nombre "
            "FROM plato p "
            "JOIN categoria c ON p.categoria_id = c.categoria_id "
            "WHERE p.activo = TRUE AND p.codigo = %s "
            "ORDER BY p.nombre",
            (codigo_num,)
        )

    # 2. Búsqueda por nombre insensible a mayúsculas y tildes
    platos_activos = consultar_todos(
        "SELECT p.plato_id, p.codigo, p.nombre, p.precio, p.disponible, c.nombre AS categoria_nombre "
        "FROM plato p "
        "JOIN categoria c ON p.categoria_id = c.categoria_id "
        "WHERE p.activo = TRUE "
        "ORDER BY c.orden, p.nombre"
    )

    termino_norm = _normalizar_texto(termino)
    coincidentes = []
    for p in platos_activos:
        nombre_norm = _normalizar_texto(p["nombre"])
        cat_norm = _normalizar_texto(p["categoria_nombre"])
        if termino_norm in nombre_norm or termino_norm in cat_norm:
            coincidentes.append(p)

    return coincidentes


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


def crear_plato(categoria_id, nombre, precio, descripcion=None, codigo=None):
    """Registra un nuevo plato (solo rol admin).
    Soporta plato.codigo único y opcional (> 0).
    """
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

    # Validar código
    codigo_val = None
    if codigo not in (None, "", "null", "None"):
        try:
            codigo_val = int(codigo)
            if codigo_val <= 0:
                raise ValueError("El código del plato debe ser un número entero mayor a 0.")
        except (TypeError, ValueError):
            raise ValueError("El código del plato debe ser un número entero positivo.")

        # Verificar unicidad (incluso con platos inactivos para conservar código reservado)
        existente = consultar_uno(
            "SELECT plato_id, nombre, activo FROM plato WHERE codigo = %s",
            (codigo_val,)
        )
        if existente:
            estado_txt = " (inactivo)" if not existente["activo"] else ""
            raise ValueError(f"El código {codigo_val} ya está asignado al plato '{existente['nombre']}'{estado_txt}.")

    desc_limpia = (descripcion or "").strip() or None

    fila = ejecutar_retornando(
        """
        INSERT INTO plato (categoria_id, codigo, nombre, descripcion, precio, disponible, activo)
        VALUES (%s, %s, %s, %s, %s, TRUE, TRUE)
        RETURNING plato_id, codigo, nombre, precio
        """,
        (categoria_id, codigo_val, nombre_limpio, desc_limpia, precio_val)
    )
    return fila


def editar_plato(plato_id, categoria_id, nombre, precio, descripcion=None, codigo=None):
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

    # Validar código
    codigo_val = None
    if codigo not in (None, "", "null", "None"):
        try:
            codigo_val = int(codigo)
            if codigo_val <= 0:
                raise ValueError("El código del plato debe ser un número entero mayor a 0.")
        except (TypeError, ValueError):
            raise ValueError("El código del plato debe ser un número entero positivo.")

        existente = consultar_uno(
            "SELECT plato_id, nombre, activo FROM plato WHERE codigo = %s AND plato_id != %s",
            (codigo_val, plato_id)
        )
        if existente:
            estado_txt = " (inactivo)" if not existente["activo"] else ""
            raise ValueError(f"El código {codigo_val} ya está asignado al plato '{existente['nombre']}'{estado_txt}.")

    desc_limpia = (descripcion or "").strip() or None

    ejecutar(
        """
        UPDATE plato
        SET categoria_id = %s, codigo = %s, nombre = %s, precio = %s, descripcion = %s
        WHERE plato_id = %s
        """,
        (categoria_id, codigo_val, nombre_limpio, precio_val, desc_limpia, plato_id)
    )
    return {"plato_id": plato_id, "codigo": codigo_val, "nombre": nombre_limpio, "precio": precio_val}


def desactivar_plato(plato_id):
    """Desactiva un plato (NUNCA se borra físicamente; conserva su código reservado)."""
    plato = consultar_uno("SELECT plato_id, nombre, codigo FROM plato WHERE plato_id = %s", (plato_id,))
    if not plato:
        raise ValueError("El plato no existe.")

    # Se marca activo = FALSE y disponible = FALSE, pero se preserva el código
    ejecutar("UPDATE plato SET activo = FALSE, disponible = FALSE WHERE plato_id = %s", (plato_id,))
    return {"plato_id": plato_id, "nombre": plato["nombre"], "codigo": plato["codigo"], "activo": False}


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
