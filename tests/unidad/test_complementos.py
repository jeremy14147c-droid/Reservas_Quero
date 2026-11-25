"""Pruebas unitarias para la regla pura de complementos ('Complementa tu pedido').
Fase 3.5: Carta y pedido en celular.
Se prueban SIN base de datos (funciones puras).
"""
import pytest
from app.servicios.carta import filtrar_platos_complementarios


def test_complementos_vacio_si_no_hay_datos():
    """Si no hay categorías o platos, devuelve lista vacía."""
    assert filtrar_platos_complementarios([], []) == []
    assert filtrar_platos_complementarios(None, None) == []


def test_complementos_vacio_si_ninguna_categoria_es_complemento():
    """Si ninguna categoría tiene es_complemento = True, no sugiere nada."""
    categorias = [
        {"categoria_id": 1, "nombre": "Ceviches", "orden": 1, "activa": True, "es_complemento": False},
        {"categoria_id": 2, "nombre": "Fondos", "orden": 2, "activa": True, "es_complemento": False},
    ]
    platos = [
        {"plato_id": 10, "categoria_id": 1, "nombre": "Ceviche Clásico", "precio": 35.0, "disponible": True, "activo": True},
        {"plato_id": 11, "categoria_id": 2, "nombre": "Lomo Saltado", "precio": 32.0, "disponible": True, "activo": True},
    ]
    resultado = filtrar_platos_complementarios(categorias, platos)
    assert resultado == []


def test_complementos_filtra_solo_disponibles_y_activos():
    """Solo incluye platos con disponible=True y activo=True de categorías complemento activas."""
    categorias = [
        {"categoria_id": 1, "nombre": "Bebidas", "orden": 1, "activa": True, "es_complemento": True},
        {"categoria_id": 2, "nombre": "Postres", "orden": 2, "activa": False, "es_complemento": True}, # Cat inactiva
    ]
    platos = [
        {"plato_id": 101, "categoria_id": 1, "nombre": "Chicha Morada 1L", "precio": 12.0, "disponible": True, "activo": True},
        {"plato_id": 102, "categoria_id": 1, "nombre": "Limonada Frozen", "precio": 14.0, "disponible": False, "activo": True}, # Agotado
        {"plato_id": 103, "categoria_id": 1, "nombre": "Gaseosa Inka Cola", "precio": 7.0, "disponible": True, "activo": False}, # Inactivo
        {"plato_id": 104, "categoria_id": 2, "nombre": "Pie de Limón", "precio": 15.0, "disponible": True, "activo": True}, # Cat inactiva
    ]
    resultado = filtrar_platos_complementarios(categorias, platos)
    assert len(resultado) == 1
    assert resultado[0]["plato_id"] == 101


def test_complementos_limita_a_tres_por_defecto():
    """Por defecto devuelve como máximo 3 platos ordenados por orden de categoría y código/nombre."""
    categorias = [
        {"categoria_id": 1, "nombre": "Bebidas", "orden": 1, "activa": True, "es_complemento": True},
        {"categoria_id": 2, "nombre": "Piqueos", "orden": 2, "activa": True, "es_complemento": True},
    ]
    platos = [
        {"plato_id": 1, "categoria_id": 1, "codigo": 50, "nombre": "Chicha Morada", "precio": 10.0, "disponible": True, "activo": True},
        {"plato_id": 2, "categoria_id": 1, "codigo": 51, "nombre": "Limonada", "precio": 10.0, "disponible": True, "activo": True},
        {"plato_id": 3, "categoria_id": 2, "codigo": 60, "nombre": "Tequeños de Queso", "precio": 18.0, "disponible": True, "activo": True},
        {"plato_id": 4, "categoria_id": 2, "codigo": 61, "nombre": "Yuquitas Fritas", "precio": 14.0, "disponible": True, "activo": True},
        {"plato_id": 5, "categoria_id": 2, "codigo": 62, "nombre": "Alitas BBQ", "precio": 22.0, "disponible": True, "activo": True},
    ]
    resultado = filtrar_platos_complementarios(categorias, platos, limite=3)
    assert len(resultado) == 3
    assert [p["plato_id"] for p in resultado] == [1, 2, 3]
