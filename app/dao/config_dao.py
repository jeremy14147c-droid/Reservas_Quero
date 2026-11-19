"""DAO para la configuración del local (config_local)."""
from app.db import consultar_uno, ejecutar


class ConfigDAO:
    """Acceso a datos de la tabla config_local (fila única)."""

    def obtener(self):
        """Devuelve la configuración completa del local."""
        return consultar_uno("SELECT * FROM config_local WHERE config_id = 1")

    def actualizar(self, params):
        """Actualiza los parámetros operativos del local."""
        ejecutar(
            """
            UPDATE config_local
            SET nombre_local = %s,
                aforo_personas = %s,
                total_mesas = %s,
                personas_por_mesa = %s,
                duracion_1_3_min = %s,
                duracion_4_7_min = %s,
                duracion_8_mas_min = %s,
                franja_min = %s,
                tolerancia_min = %s,
                umbral_preparacion_min = %s,
                max_reservas_web_por_telefono = %s,
                umbral_alerta_pct = %s,
                hora_apertura = %s,
                hora_cierre = %s,
                dias_max_anticipacion = %s,
                porcentaje_reservable = %s,
                abierto = %s,
                yape_numero = %s,
                yape_titular = %s,
                mensaje_pago = %s
            WHERE config_id = 1
            """,
            params
        )
