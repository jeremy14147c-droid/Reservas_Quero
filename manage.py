"""Script de gestión en consola para Quero Gastrobar.
Comandos disponibles:
  python manage.py init-db
  python manage.py cargar-ejemplo
  python manage.py crear-admin
"""
import os
import sys
import click
from werkzeug.security import generate_password_hash
from app import create_app
from app.db import obtener_db, ejecutar, consultar_uno

app = create_app()


@app.cli.command("init-db")
def init_db():
    """Ejecuta el archivo schema.sql en la base de datos."""
    ruta_schema = os.path.join(os.path.dirname(__file__), "schema.sql")
    if not os.path.exists(ruta_schema):
        click.secho(f"Error: No se encontró {ruta_schema}", fg="red")
        return

    with open(ruta_schema, "r", encoding="utf-8") as f:
        sql = f.read()

    click.echo("Ejecutando schema.sql...")
    db = obtener_db()
    with db.cursor() as cur:
        cur.execute(sql)
    db.commit()
    click.secho("Base de datos inicializada correctamente con schema.sql.", fg="green")


@app.cli.command("cargar-ejemplo")
def cargar_ejemplo():
    """Ejecuta el archivo seed.sql con datos de ejemplo."""
    ruta_seed = os.path.join(os.path.dirname(__file__), "seed.sql")
    if not os.path.exists(ruta_seed):
        click.secho(f"Error: No se encontró {ruta_seed}", fg="red")
        return

    with open(ruta_seed, "r", encoding="utf-8") as f:
        sql = f.read()

    click.echo("Cargando datos de ejemplo desde seed.sql...")
    db = obtener_db()
    with db.cursor() as cur:
        cur.execute(sql)
    db.commit()
    click.secho("Datos de ejemplo cargados exitosamente.", fg="green")


@app.cli.command("crear-admin")
@click.option("--nombre", prompt="Nombre completo del administrador", help="Nombre del administrador")
@click.option("--correo", prompt="Correo electrónico", help="Correo electrónico")
@click.option("--password", prompt=True, hide_input=True, confirmation_prompt=True, help="Contraseña")
def crear_admin(nombre, correo, password):
    """Crea una cuenta inicial de administrador con debe_cambiar_clave en FALSE."""
    correo_limpio = correo.strip().lower()

    existente = consultar_uno("SELECT personal_id FROM personal WHERE lower(correo) = %s", (correo_limpio,))
    if existente:
        click.secho(f"Error: Ya existe un usuario registrado con el correo {correo_limpio}.", fg="red")
        return

    password_hash = generate_password_hash(password)

    ejecutar(
        "INSERT INTO personal (nombre, correo, password_hash, rol, activo, debe_cambiar_clave) "
        "VALUES (%s, %s, %s, 'admin', TRUE, FALSE)",
        (nombre.strip(), correo_limpio, password_hash)
    )

    click.secho(f"¡Administrador '{nombre.strip()}' ({correo_limpio}) creado exitosamente!", fg="green")


if __name__ == "__main__":
    app.cli()
