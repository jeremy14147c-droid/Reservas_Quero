"""Pruebas unitarias sin base de datos para las reglas de franja_reservable (Fase 3.3)."""
from datetime import date, time, datetime
from zoneinfo import ZoneInfo
import pytest

from app.servicios.reservas import franja_reservable

ZONA_LIMA = ZoneInfo("America/Lima")


def test_dia_futuro_siempre_reservable():
    ahora = datetime(2026, 11, 20, 15, 0, tzinfo=ZONA_LIMA)
    fecha_futura = date(2026, 11, 21)
    hora = time(12, 0)
    
    reservable_web, motivo_web = franja_reservable(fecha_futura, hora, 30, ahora, canal="web", anticipacion_min=30)
    assert reservable_web is True
    assert motivo_web is None

    reservable_staff, motivo_staff = franja_reservable(fecha_futura, hora, 30, ahora, canal="staff")
    assert reservable_staff is True
    assert motivo_staff is None


def test_dia_pasado_nunca_reservable():
    ahora = datetime(2026, 11, 20, 15, 0, tzinfo=ZONA_LIMA)
    fecha_pasada = date(2026, 11, 19)
    hora = time(18, 0)

    reservable_web, motivo_web = franja_reservable(fecha_pasada, hora, 30, ahora, canal="web", anticipacion_min=30)
    assert reservable_web is False
    assert "pasó" in motivo_web.lower()

    reservable_staff, motivo_staff = franja_reservable(fecha_pasada, hora, 30, ahora, canal="staff")
    assert reservable_staff is False
    assert "pasó" in motivo_staff.lower()


def test_web_anticipacion_minima_limites():
    # Son las 14:00. Con anticipación de 30 min, la primera franja válida es >= 14:30.
    ahora = datetime(2026, 11, 20, 14, 0, tzinfo=ZONA_LIMA)
    hoy = ahora.date()

    # 13:30 ya pasó
    res, mot = franja_reservable(hoy, time(13, 30), 30, ahora, canal="web", anticipacion_min=30)
    assert res is False
    assert "anticipación" in mot.lower()

    # 14:00 (misma hora que ahora, faltan 30 min para cumplir el margen) -> no reservable
    res, mot = franja_reservable(hoy, time(14, 0), 30, ahora, canal="web", anticipacion_min=30)
    assert res is False
    assert "anticipación" in mot.lower()

    # 14:15 -> no reservable
    res, mot = franja_reservable(hoy, time(14, 15), 30, ahora, canal="web", anticipacion_min=30)
    assert res is False

    # 14:30 -> exactamente en el límite (ahora + 30 min) -> reservable
    res, mot = franja_reservable(hoy, time(14, 30), 30, ahora, canal="web", anticipacion_min=30)
    assert res is True
    assert mot is None

    # 15:00 -> posterior al límite -> reservable
    res, mot = franja_reservable(hoy, time(15, 0), 30, ahora, canal="web", anticipacion_min=30)
    assert res is True
    assert mot is None


def test_staff_puede_usar_franja_en_curso():
    # Son las 14:15. Franja de 14:00 a 14:30 (duración 30 min).
    ahora = datetime(2026, 11, 20, 14, 15, tzinfo=ZONA_LIMA)
    hoy = ahora.date()

    # Franja en curso: 14:00 (termina a las 14:30 > 14:15) -> staff puede
    res, mot = franja_reservable(hoy, time(14, 0), 30, ahora, canal="staff")
    assert res is True
    assert mot is None

    # Franja terminada: 13:30 (terminó a las 14:00 <= 14:15) -> staff no puede
    res, mot = franja_reservable(hoy, time(13, 30), 30, ahora, canal="staff")
    assert res is False
    assert "terminó" in mot.lower() or "pasó" in mot.lower()

    # Franja que termina exactamente ahora: 13:45 con 30 min termina a las 14:15 == ahora -> ya terminó
    res, mot = franja_reservable(hoy, time(13, 45), 30, ahora, canal="staff")
    assert res is False
