"""Configuración general de la aplicación Quero Gastrobar.
Lee las variables de entorno desde el archivo .env en la raíz.
"""
import os
from datetime import timedelta
from dotenv import load_dotenv

# Carga las variables de entorno desde .env
load_dotenv()


class Config:
    """Configuración base de Flask."""
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key-cambiar-en-produccion")
    DATABASE_URL = os.getenv("DATABASE_URL")
    BASE_URL = os.getenv("BASE_URL", "http://localhost:5000")

    # Constante para semáforo de disponibilidad (AGENTS.md sección 7)
    PORC_POCAS = 25

    # Zona horaria oficial del restaurante
    TIMEZONE = "America/Lima"

    # Configuración de sesión y cookies endurecidas (H-5)
    SESSION_COOKIE_HTTPONLY = True
    REMEMBER_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    PERMANENT_SESSION_LIFETIME = timedelta(hours=12)

    # En producción las cookies van estrictamente sobre HTTPS
    PRODUCCION = os.getenv("PRODUCCION", "0") == "1"
    SESSION_COOKIE_SECURE = PRODUCCION
    REMEMBER_COOKIE_SECURE = PRODUCCION

    # Parámetros de bloqueo por intentos fallidos de login (H-2)
    LOGIN_MAX_INTENTOS_CORREO = 5
    LOGIN_MAX_INTENTOS_IP = 20
    LOGIN_VENTANA_MIN = 10
    LOGIN_BLOQUEO_MIN = 10

    # Servidor SMTP (para notificaciones en proyecto final)
    SMTP_HOST = os.getenv("SMTP_HOST")
    SMTP_PORT = int(os.getenv("SMTP_PORT", 587))
    SMTP_USER = os.getenv("SMTP_USER")
    SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")
    SMTP_FROM = os.getenv("SMTP_FROM", "Quero Gastrobar <notificaciones@querogastrobar.pe>")
