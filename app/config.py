"""Configuración general de la aplicación Quero Gastrobar.
Lee las variables de entorno desde el archivo .env en la raíz.
"""
import os
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

    # Configuración de sesión y cookies
    SESSION_COOKIE_HTTPONLY = True
    REMEMBER_COOKIE_HTTPONLY = True

    # Servidor SMTP (para notificaciones en proyecto final)
    SMTP_HOST = os.getenv("SMTP_HOST")
    SMTP_PORT = int(os.getenv("SMTP_PORT", 587))
    SMTP_USER = os.getenv("SMTP_USER")
    SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")
    SMTP_FROM = os.getenv("SMTP_FROM", "Quero Gastrobar <notificaciones@querogastrobar.pe>")
