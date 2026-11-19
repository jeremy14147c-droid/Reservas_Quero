"""DAO para la gestión de la carta (categorías y platos)."""
from app.db import consultar_todos, consultar_uno, ejecutar, ejecutar_retornando


class CartaDAO:
    """Acceso a datos de categorías y platos."""

    def listar_categorias_activas(self):
        """Lista las categorías activas ordenadas por orden y nombre."""
        return consultar_todos(
            "SELECT categoria_id, nombre, orden "
            "FROM categoria WHERE activa = TRUE ORDER BY orden, nombre"
        )

    def listar_todas_categorias(self):
        """Lista todas las categorías (activas e inactivas) para el staff."""
        return consultar_todos(
            "SELECT categoria_id, nombre, orden, activa "
            "FROM categoria ORDER BY orden, nombre"
        )

    def buscar_categoria_por_id(self, categoria_id):
        """Busca una categoría por su ID."""
        return consultar_uno(
            "SELECT categoria_id, nombre, orden, activa FROM categoria WHERE categoria_id = %s",
            (categoria_id,)
        )

    def buscar_categoria_por_nombre(self, nombre):
        """Busca una categoría por su nombre sin distinguir mayúsculas."""
        return consultar_uno(
            "SELECT categoria_id, nombre, activa FROM categoria WHERE lower(nombre) = lower(%s)",
            (nombre.strip(),)
        )

    def insertar_categoria(self, nombre, orden):
        """Crea una nueva categoría."""
        return ejecutar_retornando(
            "INSERT INTO categoria (nombre, orden, activa) VALUES (%s, %s, TRUE) "
            "RETURNING categoria_id, nombre, orden, activa",
            (nombre, orden)
        )

    def listar_platos_activos(self):
        """Lista los platos activos para la carta pública."""
        return consultar_todos(
            "SELECT plato_id, categoria_id, codigo, nombre, descripcion, precio, disponible "
            "FROM plato WHERE activo = TRUE ORDER BY codigo NULLS LAST, nombre"
        )

    def listar_platos_staff(self):
        """Lista los platos activos con categoría para la gestión del personal."""
        return consultar_todos(
            "SELECT p.plato_id, p.categoria_id, c.nombre AS categoria_nombre, "
            "p.codigo, p.nombre, p.descripcion, p.precio, p.disponible, p.activo "
            "FROM plato p "
            "JOIN categoria c ON p.categoria_id = c.categoria_id "
            "WHERE p.activo = TRUE "
            "ORDER BY c.orden, c.nombre, p.codigo NULLS LAST, p.nombre"
        )

    def buscar_platos_por_codigo_exacto(self, codigo_num):
        """Busca plato activo por coincidencia exacta de código."""
        return consultar_todos(
            "SELECT p.plato_id, p.codigo, p.nombre, p.precio, p.disponible, c.nombre AS categoria_nombre "
            "FROM plato p "
            "JOIN categoria c ON p.categoria_id = c.categoria_id "
            "WHERE p.activo = TRUE AND p.codigo = %s "
            "ORDER BY p.nombre",
            (codigo_num,)
        )

    def buscar_plato_por_id(self, plato_id):
        """Busca un plato por su ID."""
        return consultar_uno(
            "SELECT plato_id, categoria_id, codigo, nombre, descripcion, precio, disponible, activo "
            "FROM plato WHERE plato_id = %s",
            (plato_id,)
        )

    def buscar_plato_por_codigo(self, codigo, excluir_plato_id=None):
        """Busca si ya existe un plato con el código dado (incluso inactivos para no reutilizar código)."""
        if excluir_plato_id:
            return consultar_uno(
                "SELECT plato_id, nombre, activo FROM plato WHERE codigo = %s AND plato_id != %s",
                (codigo, excluir_plato_id)
            )
        return consultar_uno(
            "SELECT plato_id, nombre, activo FROM plato WHERE codigo = %s",
            (codigo,)
        )

    def cambiar_disponibilidad(self, plato_id, disponible):
        """Actualiza la disponibilidad de un plato."""
        ejecutar(
            "UPDATE plato SET disponible = %s WHERE plato_id = %s",
            (bool(disponible), plato_id)
        )

    def cambiar_precio(self, plato_id, nuevo_precio):
        """Actualiza el precio de un plato."""
        ejecutar(
            "UPDATE plato SET precio = %s WHERE plato_id = %s",
            (nuevo_precio, plato_id)
        )

    def insertar_plato(self, categoria_id, codigo, nombre, descripcion, precio):
        """Inserta un nuevo plato en la carta."""
        return ejecutar_retornando(
            """
            INSERT INTO plato (categoria_id, codigo, nombre, descripcion, precio, disponible, activo)
            VALUES (%s, %s, %s, %s, %s, TRUE, TRUE)
            RETURNING plato_id, codigo, nombre, precio
            """,
            (categoria_id, codigo, nombre, descripcion, precio)
        )

    def actualizar_plato(self, plato_id, categoria_id, codigo, nombre, precio, descripcion=None):
        """Actualiza la información de un plato existente."""
        ejecutar(
            """
            UPDATE plato
            SET categoria_id = %s, codigo = %s, nombre = %s, precio = %s, descripcion = %s
            WHERE plato_id = %s
            """,
            (categoria_id, codigo, nombre, precio, descripcion, plato_id)
        )
        return {"plato_id": plato_id, "codigo": codigo, "nombre": nombre, "precio": precio}

    def desactivar_plato(self, plato_id):
        """Desactiva un plato (baja lógica)."""
        ejecutar(
            "UPDATE plato SET activo = FALSE, disponible = FALSE WHERE plato_id = %s",
            (plato_id,)
        )
