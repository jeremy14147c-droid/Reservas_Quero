"""Módulo de conexión y utilidades para PostgreSQL usando psycopg 3.
Todas las consultas se realizan con SQL explícito y parámetros seguros.
"""
import psycopg
from psycopg.rows import dict_row
from flask import g, current_app


def obtener_db():
    """Obtiene o crea una conexión a la base de datos para la petición actual."""
    if "db" not in g:
        database_url = current_app.config.get("DATABASE_URL")
        if not database_url:
            raise ValueError("DATABASE_URL no está configurada en el archivo .env")

        # Conectar usando dict_row para acceder a las columnas por nombre
        g.db = psycopg.connect(database_url, row_factory=dict_row)
    return g.db


def cerrar_db(e=None):
    """Cierra la conexión al finalizar la petición."""
    db = g.pop("db", None)
    if db is not None and not db.closed:
        db.close()


def consultar_todos(sql, params=None):
    """Ejecuta una consulta SELECT y devuelve una lista de diccionarios."""
    db = obtener_db()
    with db.cursor() as cur:
        cur.execute(sql, params or ())
        return cur.fetchall()


def consultar_uno(sql, params=None):
    """Ejecuta una consulta SELECT y devuelve una fila como diccionario o None."""
    db = obtener_db()
    with db.cursor() as cur:
        cur.execute(sql, params or ())
        return cur.fetchone()


def ejecutar(sql, params=None, commit=True):
    """Ejecuta una sentencia INSERT, UPDATE, DELETE o DDL."""
    db = obtener_db()
    with db.cursor() as cur:
        cur.execute(sql, params or ())
    if commit:
        db.commit()


def ejecutar_retornando(sql, params=None, commit=True):
    """Ejecuta una sentencia con RETURNING y devuelve la fila afectada."""
    db = obtener_db()
    with db.cursor() as cur:
        cur.execute(sql, params or ())
        resultado = cur.fetchone()
    if commit:
        db.commit()
    return resultado
