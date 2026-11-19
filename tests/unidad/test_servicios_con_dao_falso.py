"""Pruebas unitarias de servicios de negocio usando DAOs falsos en memoria (SIN base de datos).
Fase 3.R: Evidencia de MVC + Servicios + DAO e Inversión de Dependencias (AGENTS.md sección 4b).
Estas pruebas se ejecutan sin conexión a PostgreSQL.
"""
import pytest
from datetime import date, time, datetime, timedelta
from app.servicios.reservas import transicion_reserva, crear_reserva_web
from app.servicios.pedidos import transicion_pedido


class FalsoReservaDAO:
    """Implementación en memoria de ReservaDAO para pruebas unitarias sin BD."""
    def __init__(self, reserva_inicial=None):
        self.reserva = reserva_inicial or {
            "reserva_id": 1,
            "estado": "pendiente",
            "motivo": None,
            "excede_cupo": False
        }
        self.actualizada = False

    def buscar_por_id(self, reserva_id):
        if self.reserva and self.reserva.get("reserva_id") == reserva_id:
            return dict(self.reserva)
        return None

    def actualizar_estado(self, reserva_id, nuevo_estado, motivo=None, excede_cupo=None):
        self.reserva["estado"] = nuevo_estado
        self.reserva["motivo"] = motivo
        if excede_cupo is not None:
            self.reserva["excede_cupo"] = excede_cupo
        self.actualizada = True
        return dict(self.reserva)

    def existe_codigo(self, codigo):
        return False

    def hay_cupo(self, fecha, hora, personas, excluir_reserva_id=None):
        return True

    def existe_activa_cliente(self, cliente_id, fecha, hora):
        return False

    def consultar_carga_dia(self, fecha, excluir_reserva_id=None):
        return [{"franja_inicio": time(13, 0), "franja_fin": time(13, 30)}]

    def insertar(self, datos):
        return {"reserva_id": 99, "codigo": "Q-ABCDEF", "token": "uuid-test-99", **datos}


class FalsoPedidoDAO:
    """Implementación en memoria de PedidoDAO para pruebas unitarias sin BD."""
    def __init__(self, pedido_inicial=None):
        self.pedido = pedido_inicial or {
            "pedido_id": 1,
            "tipo": "recojo",
            "estado": "aceptado",
            "cobrado": False
        }

    def obtener_resumen(self, pedido_id):
        return dict(self.pedido)

    def actualizar_estado(self, pedido_id, nuevo_estado, asignado_tiempo_sql="", motivo_rechazo=None):
        self.pedido["estado"] = nuevo_estado
        self.pedido["motivo_rechazo"] = motivo_rechazo
        return dict(self.pedido)


class FalsoClienteDAO:
    """Implementación en memoria de ClienteDAO para pruebas unitarias sin BD."""
    def __init__(self, reservas_web_24h_val=0):
        self.reservas_web_24h_val = reservas_web_24h_val

    def buscar_por_telefono(self, telefono):
        return {"cliente_id": 10, "nombre": "Juan Pérez", "telefono": telefono, "correo": None}

    def insertar(self, nombre, telefono, correo=None):
        return {"cliente_id": 10, "nombre": nombre, "telefono": telefono, "correo": correo}

    def contar_reservas_web_24h(self, cliente_id):
        return self.reservas_web_24h_val


class FalsoConfigDAO:
    """Implementación en memoria de ConfigDAO para pruebas unitarias sin BD."""
    def __init__(self, max_reservas=2):
        self.max_reservas = max_reservas

    def obtener(self):
        return {
            "config_id": 1,
            "nombre_local": "Quero Gastrobar",
            "aforo_personas": 60,
            "total_mesas": 15,
            "personas_por_mesa": 4,
            "franja_min": 30,
            "tolerancia_min": 20,
            "hora_apertura": time(12, 0),
            "hora_cierre": time(23, 0),
            "dias_max_anticipacion": 7,
            "porcentaje_reservable": 100,
            "max_reservas_web_por_telefono": self.max_reservas,
            "abierto": True
        }


def test_transicion_reserva_rechaza_rechazada_a_confirmada():
    """Regla: Un estado final (rechazada) no puede pasar a confirmada (AGENTS.md sección 7)."""
    falso_dao = FalsoReservaDAO(reserva_inicial={
        "reserva_id": 1,
        "estado": "rechazada",
        "motivo": "Cancelado"
    })

    with pytest.raises(ValueError, match="no se puede cambiar"):
        transicion_reserva(1, "confirmada", dao=falso_dao)


def test_pedido_recojo_no_pasa_a_cocina_sin_estar_cobrado():
    """Regla: Un pedido recojo aceptado SOLO pasa a cocina si ya está cobrado (AGENTS.md sección 8)."""
    falso_dao = FalsoPedidoDAO(pedido_inicial={
        "pedido_id": 5,
        "tipo": "recojo",
        "estado": "aceptado",
        "cobrado": False
    })

    with pytest.raises(ValueError, match="queda cobrado"):
        transicion_pedido(5, "en_preparacion", dao=falso_dao)


def test_tope_reservas_web_por_telefono():
    """Regla: No permite crear reserva web si superó max_reservas_web_por_telefono en 24h."""
    falso_cliente_dao = FalsoClienteDAO(reservas_web_24h_val=2)
    falso_config_dao = FalsoConfigDAO(max_reservas=2)
    falso_reserva_dao = FalsoReservaDAO()

    fecha_manana = (date.today() + timedelta(days=1)).strftime("%Y-%m-%d")
    datos = {
        "nombre": "Juan Pérez",
        "telefono": "987654321",
        "correo": "juan@test.pe",
        "fecha": fecha_manana,
        "hora": "13:00",
        "personas": 4,
        "acepta_datos": "1"
    }

    with pytest.raises(ValueError, match="alcanzó el límite"):
        crear_reserva_web(
            datos,
            dao=falso_reserva_dao,
            cliente_dao=falso_cliente_dao,
            config_dao=falso_config_dao
        )
