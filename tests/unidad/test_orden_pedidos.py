"""Pruebas unitarias para las reglas de ordenamiento de pedidos.
Fase 3.6: Cocina: imprimir y recojo primero.
Regla PURA (sin base de datos):
- En 'En cocina' y 'Listos' van primero los de tipo 'recojo' (para llevar) y luego 'local'.
- Cada grupo se ordena por preparacion_en y luego por pedido_id.
- En pendientes y por cobrar el orden se mantiene por llegada.
"""
from datetime import datetime, timezone
import pytest
from app.servicios.pedidos import ordenar_pedidos_cocina_y_listos


def test_orden_recojo_primero_en_cocina_y_listos():
    """Verifica que los pedidos de tipo 'recojo' vayan antes que 'local',
    incluso si el pedido local entró antes a cocina."""
    t1 = datetime(2026, 11, 26, 12, 0, 0, tzinfo=timezone.utc)
    t2 = datetime(2026, 11, 26, 12, 5, 0, tzinfo=timezone.utc)
    t3 = datetime(2026, 11, 26, 12, 10, 0, tzinfo=timezone.utc)

    pedidos = [
        {"pedido_id": 1, "tipo": "local", "preparacion_en": t1},
        {"pedido_id": 2, "tipo": "local", "preparacion_en": t2},
        {"pedido_id": 3, "tipo": "recojo", "preparacion_en": t3},
    ]

    ordenados = ordenar_pedidos_cocina_y_listos(pedidos)

    # El pedido 3 (recojo) debe quedar de primero
    assert [p["pedido_id"] for p in ordenados] == [3, 1, 2]


def test_orden_mismo_tipo_por_preparacion_y_id():
    """Dentro del mismo tipo, se ordenan cronológicamente por preparacion_en y luego por pedido_id."""
    t1 = datetime(2026, 11, 26, 12, 0, 0, tzinfo=timezone.utc)
    t2 = datetime(2026, 11, 26, 12, 5, 0, tzinfo=timezone.utc)

    pedidos = [
        {"pedido_id": 10, "tipo": "local", "preparacion_en": t2},
        {"pedido_id": 20, "tipo": "recojo", "preparacion_en": t2},
        {"pedido_id": 5, "tipo": "local", "preparacion_en": t1},
        {"pedido_id": 15, "tipo": "recojo", "preparacion_en": t1},
    ]

    ordenados = ordenar_pedidos_cocina_y_listos(pedidos)

    # Recojos primero (15 a las 12:00, 20 a las 12:05), luego locales (5 a las 12:00, 10 a las 12:05)
    assert [p["pedido_id"] for p in ordenados] == [15, 20, 5, 10]


def test_orden_desempate_por_pedido_id_si_misma_hora():
    """Si dos pedidos del mismo tipo tienen el mismo timestamp, desempata por pedido_id ascendente."""
    t = datetime(2026, 11, 26, 12, 0, 0, tzinfo=timezone.utc)
    pedidos = [
        {"pedido_id": 4, "tipo": "recojo", "preparacion_en": t},
        {"pedido_id": 2, "tipo": "recojo", "preparacion_en": t},
    ]

    ordenados = ordenar_pedidos_cocina_y_listos(pedidos)
    assert [p["pedido_id"] for p in ordenados] == [2, 4]
