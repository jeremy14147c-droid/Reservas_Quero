"""Servicio de negocio para la gestión de la carta (categorías y platos).
Independiente de Flask: recibe datos y retorna resultados o lanza excepciones de negocio.
"""
import unicodedata
from app.dao.carta_dao import CartaDAO

# Instancia por defecto del DAO
carta_dao_default = CartaDAO()


def _normalizar_texto(texto):
    """Convierte texto a minúsculas y elimina tildes/acentos para comparaciones."""
    if not texto:
        return ""
    descompuesto = unicodedata.normalize("NFD", str(texto))
    sin_tildes = "".join(c for c in descompuesto if unicodedata.category(c) != "Mn")
    return sin_tildes.lower().strip()


def obtener_carta_publica(dao=None):
    """Devuelve las categorías activas con sus platos activos ordenados.
    Los platos con disponible = False vienen marcados para mostrarse como 'Agotado'.
    Los platos con activo = False se omiten por completo.
    Incluye el código del plato cuando exista.
    """
    dao = dao or carta_dao_default
    categorias = dao.listar_categorias_activas()
    platos = dao.listar_platos_activos()

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
                "orden": c.get("orden", 0),
                "es_complemento": bool(c.get("es_complemento", False)),
                "platos": lista_platos
            })

    return resultado


def filtrar_platos_complementarios(categorias, platos, limite=3):
    """Regla PURA (sin base de datos): devuelve hasta `limite` platos disponibles
    que pertenezcan a categorías activas marcadas como complemento (es_complemento = True).
    Si no hay categorías de complemento o no hay platos disponibles, retorna lista vacía.
    """
    if not categorias or not platos:
        return []

    # Identificar IDs de categorías activas que sean complementos
    cats_complemento = {
        c["categoria_id"]
        for c in categorias
        if c.get("activa", True) and c.get("es_complemento", False)
    }

    if not cats_complemento:
        return []

    # Mapear orden de categorías para mantener prelación
    orden_cats = {c["categoria_id"]: c.get("orden", 0) for c in categorias}

    candidatos = []
    for p in platos:
        if (
            p.get("categoria_id") in cats_complemento
            and p.get("activo", True)
            and p.get("disponible", True)
        ):
            candidatos.append(p)

    # Ordenar por orden de categoría y luego por código o nombre
    candidatos.sort(
        key=lambda p: (
            orden_cats.get(p.get("categoria_id"), 0),
            p.get("codigo") or 999999,
            p.get("nombre", "")
        )
    )

    return candidatos[:limite]


def obtener_platos_complementarios(limite=3, dao=None):
    """Devuelve hasta `limite` platos complementarios activos y disponibles."""
    dao = dao or carta_dao_default
    categorias = dao.listar_categorias_activas()
    platos = dao.listar_platos_activos()
    return filtrar_platos_complementarios(categorias, platos, limite=limite)


def obtener_carta_staff(dao=None):
    """Devuelve todas las categorías y platos activos para la gestión del personal."""
    dao = dao or carta_dao_default
    categorias = dao.listar_todas_categorias()
    platos = dao.listar_platos_staff()
    return {"categorias": categorias, "platos": platos}


def buscar_platos(texto, dao=None):
    """Busca platos activos por código numérico exacto o por nombre (sin distinguir mayúsculas ni tildes).
    - Si texto son solo dígitos: coincidencia EXACTA por plato.codigo (1 no trae 10 ni 11).
    - Si no: búsqueda por coincidencia parcial en el nombre normalizado.
    """
    dao = dao or carta_dao_default
    termino = (texto or "").strip()
    if not termino:
        return dao.listar_platos_staff()

    # 1. Búsqueda por código numérico EXACTO
    if termino.isdigit():
        return dao.buscar_platos_por_codigo_exacto(int(termino))

    # 2. Búsqueda por nombre insensible a mayúsculas y tildes
    platos_activos = dao.listar_platos_staff()
    termino_norm = _normalizar_texto(termino)
    coincidentes = []
    for p in platos_activos:
        nombre_norm = _normalizar_texto(p["nombre"])
        cat_norm = _normalizar_texto(p.get("categoria_nombre", ""))
        if termino_norm in nombre_norm or termino_norm in cat_norm:
            coincidentes.append(p)

    return coincidentes


def cambiar_disponibilidad_plato(plato_id, disponible, dao=None):
    """Cambia el interruptor 'disponible' (agotado o no) de un plato."""
    dao = dao or carta_dao_default
    plato = dao.buscar_plato_por_id(plato_id)
    if not plato or not plato["activo"]:
        raise ValueError("El plato especificado no existe o está inactivo.")

    dao.cambiar_disponibilidad(plato_id, bool(disponible))
    return {"plato_id": plato_id, "nombre": plato["nombre"], "disponible": bool(disponible)}


def actualizar_precio_plato(plato_id, nuevo_precio, dao=None):
    """Actualiza el precio de un plato."""
    dao = dao or carta_dao_default
    try:
        precio_val = float(nuevo_precio)
        if precio_val < 0:
            raise ValueError("El precio no puede ser negativo.")
    except (TypeError, ValueError):
        raise ValueError("El precio debe ser un número válido mayor o igual a 0.")

    plato = dao.buscar_plato_por_id(plato_id)
    if not plato or not plato["activo"]:
        raise ValueError("El plato especificado no existe o está inactivo.")

    dao.cambiar_precio(plato_id, precio_val)
    return {"plato_id": plato_id, "nombre": plato["nombre"], "precio": precio_val}


def crear_plato(categoria_id, nombre, precio, descripcion=None, codigo=None, dao=None):
    """Registra un nuevo plato (solo rol admin).
    Soporta plato.codigo único y opcional (> 0).
    """
    dao = dao or carta_dao_default
    nombre_limpio = (nombre or "").strip()
    if not nombre_limpio:
        raise ValueError("El nombre del plato es obligatorio.")

    try:
        precio_val = float(precio)
        if precio_val < 0:
            raise ValueError("El precio no puede ser negativo.")
    except (TypeError, ValueError):
        raise ValueError("El precio debe ser un valor numérico válido.")

    categoria = dao.buscar_categoria_por_id(categoria_id)
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

        existente = dao.buscar_plato_por_codigo(codigo_val)
        if existente:
            estado_txt = " (inactivo)" if not existente["activo"] else ""
            raise ValueError(f"El código {codigo_val} ya está asignado al plato '{existente['nombre']}'{estado_txt}.")

    desc_limpia = (descripcion or "").strip() or None
    return dao.insertar_plato(categoria_id, codigo_val, nombre_limpio, desc_limpia, precio_val)


def editar_plato(plato_id, categoria_id, nombre, precio, descripcion=None, codigo=None, dao=None):
    """Edita los datos de un plato existente."""
    dao = dao or carta_dao_default
    nombre_limpio = (nombre or "").strip()
    if not nombre_limpio:
        raise ValueError("El nombre del plato es obligatorio.")

    try:
        precio_val = float(precio)
        if precio_val < 0:
            raise ValueError("El precio no puede ser negativo.")
    except (TypeError, ValueError):
        raise ValueError("El precio debe ser un valor numérico válido.")

    plato = dao.buscar_plato_por_id(plato_id)
    if not plato:
        raise ValueError("El plato no existe.")

    categoria = dao.buscar_categoria_por_id(categoria_id)
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

        existente = dao.buscar_plato_por_codigo(codigo_val, excluir_plato_id=plato_id)
        if existente:
            estado_txt = " (inactivo)" if not existente["activo"] else ""
            raise ValueError(f"El código {codigo_val} ya está asignado al plato '{existente['nombre']}'{estado_txt}.")

    desc_limpia = (descripcion or "").strip() or None
    return dao.actualizar_plato(plato_id, categoria_id, codigo_val, nombre_limpio, precio_val, desc_limpia)


def desactivar_plato(plato_id, dao=None):
    """Desactiva un plato (NUNCA se borra físicamente; conserva su código reservado)."""
    dao = dao or carta_dao_default
    plato = dao.buscar_plato_por_id(plato_id)
    if not plato:
        raise ValueError("El plato no existe.")

    dao.desactivar_plato(plato_id)
    return {"plato_id": plato_id, "nombre": plato["nombre"], "codigo": plato["codigo"], "activo": False}


def crear_categoria(nombre, orden=0, es_complemento=False, dao=None):
    """Crea una nueva categoría de platos."""
    dao = dao or carta_dao_default
    nombre_limpio = (nombre or "").strip()
    if not nombre_limpio:
        raise ValueError("El nombre de la categoría es obligatorio.")

    existente = dao.buscar_categoria_por_nombre(nombre_limpio)
    if existente:
        raise ValueError("Ya existe una categoría con ese nombre.")

    return dao.insertar_categoria(nombre_limpio, int(orden or 0), bool(es_complemento))


def cambiar_categoria_complemento(categoria_id, es_complemento, dao=None):
    """Actualiza si una categoría es sugerida como complemento."""
    dao = dao or carta_dao_default
    categoria = dao.buscar_categoria_por_id(categoria_id)
    if not categoria:
        raise ValueError("La categoría no existe.")

    dao.cambiar_categoria_complemento(categoria_id, bool(es_complemento))
    return {
        "categoria_id": categoria_id,
        "nombre": categoria["nombre"],
        "es_complemento": bool(es_complemento)
    }
